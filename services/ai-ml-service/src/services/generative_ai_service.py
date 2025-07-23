"""Generative AI service for creative content generation"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import base64
from io import BytesIO
import numpy as np
from PIL import Image

import openai
import anthropic
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    pipeline,
    BlipProcessor,
    BlipForConditionalGeneration,
    CLIPModel,
    CLIPProcessor,
)
import torch
import replicate
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import httpx

from ..models.schemas import (
    GenerativeRequest,
    GenerativeResponse,
    TextGenerationRequest,
    ImageGenerationRequest,
    VideoGenerationRequest,
    AudioGenerationRequest,
    ContentEnhancementRequest,
    StoryboardRequest,
    ScriptGenerationRequest,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class GenerativeAIService:
    """Service for generative AI features including text, image, video, and audio generation"""
    
    def __init__(self):
        """Initialize generative AI service"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize API clients
        self.openai_client = None
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.openai_client = openai
            
        self.anthropic_client = None
        if settings.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            
        self.replicate_client = None
        if settings.replicate_api_token:
            self.replicate_client = replicate
            
        self.stability_client = None
        if settings.stability_api_key:
            self.stability_client = client.StabilityInference(
                key=settings.stability_api_key,
                verbose=True,
            )
            
        # Initialize local models if enabled
        self.text_model = None
        self.image_caption_model = None
        self.clip_model = None
        
        if settings.enable_local_models:
            self._initialize_local_models()
            
    def _initialize_local_models(self):
        """Initialize local AI models"""
        try:
            # Text generation model
            logger.info("Loading local text generation model")
            self.text_tokenizer = AutoTokenizer.from_pretrained("gpt2-medium")
            self.text_model = AutoModelForCausalLM.from_pretrained("gpt2-medium")
            self.text_model.to(self.device)
            
            # Image captioning model
            logger.info("Loading BLIP model for image captioning")
            self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.image_caption_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            self.image_caption_model.to(self.device)
            
            # CLIP model for image-text similarity
            logger.info("Loading CLIP model")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model.to(self.device)
            
        except Exception as e:
            logger.error(f"Failed to initialize local models: {e}")
            
    async def generate_text(
        self,
        request: TextGenerationRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate text content based on prompt"""
        try:
            start_time = datetime.utcnow()
            
            # Select provider based on request or settings
            provider = request.provider or settings.default_text_provider
            
            if provider == "openai" and self.openai_client:
                result = await self._generate_text_openai(request)
            elif provider == "anthropic" and self.anthropic_client:
                result = await self._generate_text_anthropic(request)
            elif provider == "local" and self.text_model:
                result = await self._generate_text_local(request)
            else:
                raise ValueError(f"Text generation provider {provider} not available")
                
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result=result,
                provider=provider,
                model_used=result.get("model", "unknown"),
                processing_time=processing_time,
                usage_metrics={
                    "tokens_used": result.get("tokens_used", 0),
                    "cost_estimate": result.get("cost_estimate", 0.0)
                },
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _generate_text_openai(self, request: TextGenerationRequest) -> Dict[str, Any]:
        """Generate text using OpenAI"""
        model = request.model or "gpt-4"
        
        # Prepare messages
        messages = [{"role": "system", "content": request.system_prompt or "You are a helpful assistant."}]
        messages.append({"role": "user", "content": request.prompt})
        
        # Generate response
        response = await asyncio.to_thread(
            self.openai_client.ChatCompletion.create,
            model=model,
            messages=messages,
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
            top_p=request.top_p or 0.9,
            presence_penalty=request.presence_penalty or 0,
            frequency_penalty=request.frequency_penalty or 0,
            n=request.num_outputs or 1
        )
        
        # Extract results
        outputs = [choice.message.content for choice in response.choices]
        tokens_used = response.usage.total_tokens
        
        # Estimate cost
        cost_per_1k_tokens = 0.03 if "gpt-4" in model else 0.002
        cost_estimate = (tokens_used / 1000) * cost_per_1k_tokens
        
        return {
            "outputs": outputs,
            "model": model,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "finish_reason": response.choices[0].finish_reason
        }
        
    async def _generate_text_anthropic(self, request: TextGenerationRequest) -> Dict[str, Any]:
        """Generate text using Anthropic Claude"""
        model = request.model or "claude-3-opus-20240229"
        
        # Generate response
        response = await asyncio.to_thread(
            self.anthropic_client.messages.create,
            model=model,
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
            system=request.system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": request.prompt}]
        )
        
        # Extract results
        outputs = [response.content[0].text]
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        # Estimate cost
        cost_per_1k_tokens = 0.015  # Claude pricing
        cost_estimate = (tokens_used / 1000) * cost_per_1k_tokens
        
        return {
            "outputs": outputs,
            "model": model,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "finish_reason": response.stop_reason
        }
        
    async def _generate_text_local(self, request: TextGenerationRequest) -> Dict[str, Any]:
        """Generate text using local model"""
        # Tokenize input
        inputs = self.text_tokenizer.encode(request.prompt, return_tensors="pt")
        inputs = inputs.to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.text_model.generate(
                inputs,
                max_length=request.max_tokens or 1000,
                temperature=request.temperature or 0.7,
                top_p=request.top_p or 0.9,
                num_return_sequences=request.num_outputs or 1,
                do_sample=True,
                pad_token_id=self.text_tokenizer.eos_token_id
            )
            
        # Decode outputs
        generated_texts = [
            self.text_tokenizer.decode(output, skip_special_tokens=True)
            for output in outputs
        ]
        
        # Remove prompt from outputs
        outputs_clean = [
            text[len(request.prompt):].strip()
            for text in generated_texts
        ]
        
        return {
            "outputs": outputs_clean,
            "model": "gpt2-medium",
            "tokens_used": sum(len(output) for output in outputs),
            "cost_estimate": 0.0,  # Local model
            "finish_reason": "length"
        }
        
    async def generate_image(
        self,
        request: ImageGenerationRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate images based on text prompts"""
        try:
            start_time = datetime.utcnow()
            
            # Select provider
            provider = request.provider or settings.default_image_provider
            
            if provider == "openai" and self.openai_client:
                result = await self._generate_image_openai(request)
            elif provider == "stability" and self.stability_client:
                result = await self._generate_image_stability(request)
            elif provider == "replicate" and self.replicate_client:
                result = await self._generate_image_replicate(request)
            else:
                raise ValueError(f"Image generation provider {provider} not available")
                
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result=result,
                provider=provider,
                model_used=result.get("model", "unknown"),
                processing_time=processing_time,
                usage_metrics={
                    "images_generated": len(result.get("images", [])),
                    "cost_estimate": result.get("cost_estimate", 0.0)
                },
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _generate_image_openai(self, request: ImageGenerationRequest) -> Dict[str, Any]:
        """Generate images using OpenAI DALL-E"""
        # Generate images
        response = await asyncio.to_thread(
            self.openai_client.Image.create,
            prompt=request.prompt,
            n=request.num_images or 1,
            size=f"{request.width}x{request.height}" if request.width else "1024x1024",
            quality=request.quality or "standard",
            style=request.style or "natural"
        )
        
        # Extract image URLs
        images = []
        for img_data in response.data:
            if request.output_format == "base64":
                # Download and convert to base64
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(img_data.url)
                    base64_img = base64.b64encode(img_response.content).decode()
                    images.append({
                        "base64": base64_img,
                        "format": "png"
                    })
            else:
                images.append({
                    "url": img_data.url,
                    "format": "png"
                })
                
        # Calculate cost
        cost_per_image = 0.02 if request.quality == "hd" else 0.016
        cost_estimate = len(images) * cost_per_image
        
        return {
            "images": images,
            "model": "dall-e-3",
            "cost_estimate": cost_estimate
        }
        
    async def _generate_image_stability(self, request: ImageGenerationRequest) -> Dict[str, Any]:
        """Generate images using Stability AI"""
        # Configure generation parameters
        answers = await asyncio.to_thread(
            self.stability_client.generate,
            prompt=request.prompt,
            seed=request.seed,
            steps=request.steps or 30,
            cfg_scale=request.cfg_scale or 7.0,
            width=request.width or 1024,
            height=request.height or 1024,
            samples=request.num_images or 1,
            sampler=generation.SAMPLER_K_DPM_2_ANCESTRAL
        )
        
        # Process results
        images = []
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.type == generation.ARTIFACT_IMAGE:
                    img_data = artifact.binary
                    if request.output_format == "base64":
                        base64_img = base64.b64encode(img_data).decode()
                        images.append({
                            "base64": base64_img,
                            "format": "png"
                        })
                    else:
                        # Save to temporary location
                        images.append({
                            "data": img_data,
                            "format": "png"
                        })
                        
        # Calculate cost
        cost_per_step = 0.002
        total_steps = (request.steps or 30) * len(images)
        cost_estimate = (total_steps / 1000) * cost_per_step
        
        return {
            "images": images,
            "model": "stable-diffusion-xl",
            "cost_estimate": cost_estimate
        }
        
    async def _generate_image_replicate(self, request: ImageGenerationRequest) -> Dict[str, Any]:
        """Generate images using Replicate"""
        model = request.model or "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        
        # Run generation
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input={
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt or "",
                "width": request.width or 1024,
                "height": request.height or 1024,
                "num_outputs": request.num_images or 1,
                "num_inference_steps": request.steps or 30,
                "guidance_scale": request.cfg_scale or 7.5,
                "seed": request.seed
            }
        )
        
        # Process results
        images = []
        for img_url in output:
            if request.output_format == "base64":
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(img_url)
                    base64_img = base64.b64encode(img_response.content).decode()
                    images.append({
                        "base64": base64_img,
                        "format": "png"
                    })
            else:
                images.append({
                    "url": img_url,
                    "format": "png"
                })
                
        # Estimate cost
        cost_estimate = len(images) * 0.01  # Replicate pricing varies
        
        return {
            "images": images,
            "model": model.split("/")[-1],
            "cost_estimate": cost_estimate
        }
        
    async def generate_video(
        self,
        request: VideoGenerationRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate video content"""
        try:
            start_time = datetime.utcnow()
            
            # Select provider
            provider = request.provider or "replicate"
            
            if provider == "replicate" and self.replicate_client:
                result = await self._generate_video_replicate(request)
            else:
                raise ValueError(f"Video generation provider {provider} not available")
                
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result=result,
                provider=provider,
                model_used=result.get("model", "unknown"),
                processing_time=processing_time,
                usage_metrics={
                    "duration_seconds": result.get("duration", 0),
                    "cost_estimate": result.get("cost_estimate", 0.0)
                },
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _generate_video_replicate(self, request: VideoGenerationRequest) -> Dict[str, Any]:
        """Generate video using Replicate models"""
        # Select model based on type
        if request.video_type == "text_to_video":
            model = "deforum/deforum_stable_diffusion:e22e77495f2fb83c34d5fae2ad8ab63c0a87b6b573b6208e1535b23b89ea66d6"
        elif request.video_type == "image_to_video":
            model = "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438"
        else:
            model = request.model
            
        # Prepare input
        input_data = {
            "prompt": request.prompt,
            "num_frames": request.duration * request.fps,
            "fps": request.fps,
            "width": request.width or 1024,
            "height": request.height or 576,
            "seed": request.seed
        }
        
        # Add image if provided
        if request.init_image:
            input_data["init_image"] = request.init_image
            
        # Run generation
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input=input_data
        )
        
        # Estimate cost
        cost_per_second = 0.05  # Approximate
        cost_estimate = request.duration * cost_per_second
        
        return {
            "video_url": output,
            "model": model.split("/")[-1],
            "duration": request.duration,
            "fps": request.fps,
            "resolution": f"{request.width or 1024}x{request.height or 576}",
            "cost_estimate": cost_estimate
        }
        
    async def generate_audio(
        self,
        request: AudioGenerationRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate audio content"""
        try:
            start_time = datetime.utcnow()
            
            # Select provider
            provider = request.provider or settings.default_audio_provider
            
            if provider == "openai" and self.openai_client:
                result = await self._generate_audio_openai(request)
            elif provider == "replicate" and self.replicate_client:
                result = await self._generate_audio_replicate(request)
            else:
                raise ValueError(f"Audio generation provider {provider} not available")
                
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result=result,
                provider=provider,
                model_used=result.get("model", "unknown"),
                processing_time=processing_time,
                usage_metrics={
                    "duration_seconds": result.get("duration", 0),
                    "cost_estimate": result.get("cost_estimate", 0.0)
                },
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _generate_audio_openai(self, request: AudioGenerationRequest) -> Dict[str, Any]:
        """Generate audio using OpenAI TTS"""
        # Generate speech
        response = await asyncio.to_thread(
            self.openai_client.audio.speech.create,
            model=request.model or "tts-1-hd",
            voice=request.voice or "alloy",
            input=request.text,
            speed=request.speed or 1.0
        )
        
        # Get audio data
        audio_data = response.content
        
        # Convert to base64 if requested
        if request.output_format == "base64":
            audio_base64 = base64.b64encode(audio_data).decode()
            audio_result = {
                "base64": audio_base64,
                "format": "mp3"
            }
        else:
            audio_result = {
                "data": audio_data,
                "format": "mp3"
            }
            
        # Estimate duration and cost
        # Approximate: 150 words per minute at normal speed
        word_count = len(request.text.split())
        duration = (word_count / 150) * 60 / request.speed  # in seconds
        cost_per_1k_chars = 0.015 if "hd" in request.model else 0.006
        cost_estimate = (len(request.text) / 1000) * cost_per_1k_chars
        
        return {
            "audio": audio_result,
            "model": request.model or "tts-1-hd",
            "voice": request.voice or "alloy",
            "duration": duration,
            "cost_estimate": cost_estimate
        }
        
    async def _generate_audio_replicate(self, request: AudioGenerationRequest) -> Dict[str, Any]:
        """Generate audio using Replicate models"""
        if request.audio_type == "music":
            model = "meta/musicgen:b05b1dff1d8c6dc63d14b0cdb42135378dcb87f6373b0d3d341ede46e59e2b38"
            input_data = {
                "prompt": request.text,
                "duration": request.duration or 10,
                "top_k": 250,
                "top_p": 0.95,
                "temperature": 1.0,
                "seed": request.seed
            }
        else:
            # Text to speech
            model = "suno-ai/bark:b76242b40d67c76ab6742e987628a2a9ac019e11d56ab96c4e91ce03b79b2787"
            input_data = {
                "prompt": request.text,
                "text_temp": 0.7,
                "waveform_temp": 0.7
            }
            
        # Run generation
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input=input_data
        )
        
        # Process result
        if request.output_format == "base64":
            async with httpx.AsyncClient() as client:
                audio_response = await client.get(output)
                audio_base64 = base64.b64encode(audio_response.content).decode()
                audio_result = {
                    "base64": audio_base64,
                    "format": "wav"
                }
        else:
            audio_result = {
                "url": output,
                "format": "wav"
            }
            
        # Estimate cost
        cost_per_second = 0.01  # Approximate
        duration = request.duration or 10
        cost_estimate = duration * cost_per_second
        
        return {
            "audio": audio_result,
            "model": model.split("/")[-1],
            "duration": duration,
            "cost_estimate": cost_estimate
        }
        
    async def enhance_content(
        self,
        request: ContentEnhancementRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Enhance existing content using AI"""
        try:
            start_time = datetime.utcnow()
            
            if request.enhancement_type == "upscale_image":
                result = await self._upscale_image(request)
            elif request.enhancement_type == "denoise_audio":
                result = await self._denoise_audio(request)
            elif request.enhancement_type == "stabilize_video":
                result = await self._stabilize_video(request)
            elif request.enhancement_type == "rewrite_text":
                result = await self._rewrite_text(request)
            elif request.enhancement_type == "translate":
                result = await self._translate_content(request)
            else:
                raise ValueError(f"Unknown enhancement type: {request.enhancement_type}")
                
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result=result,
                provider=result.get("provider", "unknown"),
                model_used=result.get("model", "unknown"),
                processing_time=processing_time,
                usage_metrics=result.get("usage_metrics", {}),
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Content enhancement error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _upscale_image(self, request: ContentEnhancementRequest) -> Dict[str, Any]:
        """Upscale image using AI"""
        if not self.replicate_client:
            raise ValueError("Replicate client not available for image upscaling")
            
        model = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"
        
        # Run upscaling
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input={
                "image": request.content_url,
                "scale": request.parameters.get("scale", 4),
                "face_enhance": request.parameters.get("face_enhance", False)
            }
        )
        
        return {
            "enhanced_url": output,
            "provider": "replicate",
            "model": "real-esrgan",
            "enhancement_type": "upscale",
            "scale_factor": request.parameters.get("scale", 4),
            "usage_metrics": {
                "cost_estimate": 0.01
            }
        }
        
    async def _denoise_audio(self, request: ContentEnhancementRequest) -> Dict[str, Any]:
        """Denoise audio using AI"""
        if not self.replicate_client:
            raise ValueError("Replicate client not available for audio denoising")
            
        model = "afiaka87/audio-denoising:0108d333125bb0e4263fb207d6751ba3cbcfc3e2b007ebe41f0f016b0df66be3"
        
        # Run denoising
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input={
                "audio": request.content_url,
                "noise_level": request.parameters.get("noise_level", 0.5)
            }
        )
        
        return {
            "enhanced_url": output,
            "provider": "replicate",
            "model": "audio-denoising",
            "enhancement_type": "denoise",
            "usage_metrics": {
                "cost_estimate": 0.02
            }
        }
        
    async def _stabilize_video(self, request: ContentEnhancementRequest) -> Dict[str, Any]:
        """Stabilize video using AI"""
        if not self.replicate_client:
            raise ValueError("Replicate client not available for video stabilization")
            
        model = "arielreplicate/video_stabilization:4b9763a022768f3b26380450de7b5d58a5fd68e1e6e62d967c548090bb22a1cc"
        
        # Run stabilization
        output = await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input={
                "video": request.content_url,
                "smoothing": request.parameters.get("smoothing", 30),
                "crop_black": request.parameters.get("crop_black", True)
            }
        )
        
        return {
            "enhanced_url": output,
            "provider": "replicate",
            "model": "video-stabilization",
            "enhancement_type": "stabilize",
            "usage_metrics": {
                "cost_estimate": 0.05
            }
        }
        
    async def _rewrite_text(self, request: ContentEnhancementRequest) -> Dict[str, Any]:
        """Rewrite text content"""
        text_request = TextGenerationRequest(
            prompt=f"Rewrite the following text {request.parameters.get('style', 'professionally')}:\n\n{request.content_data}",
            max_tokens=request.parameters.get("max_tokens", 1000),
            temperature=request.parameters.get("temperature", 0.7)
        )
        
        # Use text generation
        result = await self.generate_text(text_request, request.user_id)
        
        return {
            "enhanced_text": result.result["outputs"][0],
            "provider": result.provider,
            "model": result.model_used,
            "enhancement_type": "rewrite",
            "usage_metrics": result.usage_metrics
        }
        
    async def _translate_content(self, request: ContentEnhancementRequest) -> Dict[str, Any]:
        """Translate content to another language"""
        target_language = request.parameters.get("target_language", "en")
        
        if request.content_type == "text":
            # Text translation
            text_request = TextGenerationRequest(
                prompt=f"Translate the following text to {target_language}:\n\n{request.content_data}",
                max_tokens=request.parameters.get("max_tokens", 2000),
                temperature=0.3  # Lower temperature for translation
            )
            
            result = await self.generate_text(text_request, request.user_id)
            
            return {
                "translated_text": result.result["outputs"][0],
                "provider": result.provider,
                "model": result.model_used,
                "enhancement_type": "translate",
                "target_language": target_language,
                "usage_metrics": result.usage_metrics
            }
        else:
            raise ValueError(f"Translation not supported for content type: {request.content_type}")
            
    async def generate_storyboard(
        self,
        request: StoryboardRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate storyboard from script"""
        try:
            start_time = datetime.utcnow()
            
            # Parse script into scenes
            scenes = await self._parse_script_scenes(request.script)
            
            # Generate storyboard frames
            storyboard_frames = []
            total_cost = 0.0
            
            for i, scene in enumerate(scenes):
                # Generate scene description
                scene_prompt = await self._create_scene_prompt(
                    scene,
                    request.style,
                    request.aspect_ratio
                )
                
                # Generate image for scene
                img_request = ImageGenerationRequest(
                    prompt=scene_prompt,
                    style=request.style,
                    width=1920 if request.aspect_ratio == "16:9" else 1080,
                    height=1080,
                    num_images=1
                )
                
                img_result = await self.generate_image(img_request, user_id)
                
                if img_result.status == "completed":
                    storyboard_frames.append({
                        "scene_number": i + 1,
                        "description": scene["description"],
                        "dialogue": scene.get("dialogue", ""),
                        "image": img_result.result["images"][0],
                        "duration": scene.get("duration", 5)
                    })
                    total_cost += img_result.usage_metrics.get("cost_estimate", 0)
                    
            # Generate summary
            summary = {
                "total_scenes": len(scenes),
                "total_duration": sum(f["duration"] for f in storyboard_frames),
                "frames_generated": len(storyboard_frames),
                "style": request.style,
                "aspect_ratio": request.aspect_ratio
            }
            
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result={
                    "storyboard": storyboard_frames,
                    "summary": summary
                },
                provider="mixed",
                model_used="multiple",
                processing_time=processing_time,
                usage_metrics={
                    "frames_generated": len(storyboard_frames),
                    "cost_estimate": total_cost
                },
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Storyboard generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _parse_script_scenes(self, script: str) -> List[Dict[str, Any]]:
        """Parse script into individual scenes"""
        # Use AI to parse script
        parse_request = TextGenerationRequest(
            prompt=f"""Parse the following script into individual scenes. 
            For each scene, extract:
            1. Scene description
            2. Location
            3. Characters present
            4. Key dialogue
            5. Estimated duration
            
            Return as JSON array.
            
            Script:
            {script}""",
            temperature=0.3,
            max_tokens=2000
        )
        
        result = await self.generate_text(parse_request, "system")
        
        # Parse JSON response
        try:
            scenes = json.loads(result.result["outputs"][0])
            return scenes
        except:
            # Fallback to simple parsing
            lines = script.strip().split("\n")
            scenes = []
            current_scene = None
            
            for line in lines:
                if line.strip().upper().startswith(("INT.", "EXT.", "SCENE")):
                    if current_scene:
                        scenes.append(current_scene)
                    current_scene = {
                        "description": line.strip(),
                        "dialogue": "",
                        "duration": 5
                    }
                elif current_scene and line.strip():
                    current_scene["dialogue"] += line + "\n"
                    
            if current_scene:
                scenes.append(current_scene)
                
            return scenes
            
    async def _create_scene_prompt(
        self,
        scene: Dict[str, Any],
        style: str,
        aspect_ratio: str
    ) -> str:
        """Create image generation prompt for scene"""
        # Build prompt
        prompt_parts = []
        
        # Add style
        if style:
            prompt_parts.append(f"{style} style")
            
        # Add scene description
        prompt_parts.append(scene["description"])
        
        # Add characters if present
        if "characters" in scene:
            prompt_parts.append(f"featuring {', '.join(scene['characters'])}")
            
        # Add mood/atmosphere
        if "mood" in scene:
            prompt_parts.append(f"{scene['mood']} atmosphere")
            
        # Add technical requirements
        prompt_parts.append(f"cinematic composition, {aspect_ratio} aspect ratio")
        
        return ", ".join(prompt_parts)
        
    async def generate_script(
        self,
        request: ScriptGenerationRequest,
        user_id: str
    ) -> GenerativeResponse:
        """Generate script from outline or treatment"""
        try:
            start_time = datetime.utcnow()
            
            # Build prompt based on script type
            if request.script_type == "screenplay":
                system_prompt = """You are a professional screenwriter. 
                Write in standard screenplay format with:
                - Scene headings (INT./EXT.)
                - Character names (CENTERED, CAPS)
                - Dialogue
                - Action lines
                - Parentheticals when needed"""
            elif request.script_type == "commercial":
                system_prompt = """You are a commercial scriptwriter.
                Write in commercial script format with:
                - Scene descriptions
                - Voice over (V.O.)
                - On-screen text
                - Music/SFX cues
                - Duration markers"""
            elif request.script_type == "documentary":
                system_prompt = """You are a documentary scriptwriter.
                Write in documentary format with:
                - Narration (V.O.)
                - Interview segments
                - B-roll descriptions
                - Lower thirds
                - Archival footage notes"""
            else:
                system_prompt = "You are a professional scriptwriter."
                
            # Create prompt
            prompt = f"""Write a {request.script_type} script based on the following:
            
            Genre: {request.genre}
            Duration: {request.duration} minutes
            Target Audience: {request.target_audience or 'General'}
            
            Outline/Treatment:
            {request.outline}
            
            {f'Characters: {json.dumps(request.characters)}' if request.characters else ''}
            {f'Tone: {request.tone}' if request.tone else ''}
            
            Write a complete, properly formatted script."""
            
            # Generate script
            text_request = TextGenerationRequest(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.8
            )
            
            result = await self.generate_text(text_request, user_id)
            
            # Post-process script
            script_text = result.result["outputs"][0]
            
            # Format script properly
            formatted_script = await self._format_script(script_text, request.script_type)
            
            # Extract metadata
            script_metadata = await self._extract_script_metadata(formatted_script)
            
            # Calculate metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return GenerativeResponse(
                request_id=request.request_id,
                status="completed",
                result={
                    "script": formatted_script,
                    "metadata": script_metadata,
                    "format": request.script_type,
                    "estimated_duration": script_metadata.get("estimated_duration", request.duration)
                },
                provider=result.provider,
                model_used=result.model_used,
                processing_time=processing_time,
                usage_metrics=result.usage_metrics,
                metadata=request.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return GenerativeResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                processing_time=0
            )
            
    async def _format_script(self, script_text: str, script_type: str) -> str:
        """Format script according to industry standards"""
        # This would implement proper formatting
        # For now, return as-is
        return script_text
        
    async def _extract_script_metadata(self, script: str) -> Dict[str, Any]:
        """Extract metadata from script"""
        lines = script.split("\n")
        
        # Count scenes
        scene_count = sum(1 for line in lines if line.strip().upper().startswith(("INT.", "EXT.")))
        
        # Count characters
        characters = set()
        for line in lines:
            if line.strip() and line.strip().isupper() and len(line.strip()) < 50:
                # Likely a character name
                characters.add(line.strip())
                
        # Estimate duration (1 page ≈ 1 minute)
        page_count = len(script) / 3000  # Approximate characters per page
        estimated_duration = round(page_count)
        
        return {
            "scene_count": scene_count,
            "character_count": len(characters),
            "characters": list(characters),
            "estimated_duration": estimated_duration,
            "word_count": len(script.split()),
            "line_count": len(lines)
        }
        
    async def analyze_media_with_ai(
        self,
        media_url: str,
        media_type: str,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze media content using AI"""
        try:
            if media_type == "image":
                return await self._analyze_image(media_url, analysis_type)
            elif media_type == "video":
                return await self._analyze_video(media_url, analysis_type)
            elif media_type == "audio":
                return await self._analyze_audio(media_url, analysis_type)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")
                
        except Exception as e:
            logger.error(f"Media analysis error: {e}")
            raise
            
    async def _analyze_image(self, image_url: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze image using AI models"""
        results = {}
        
        if analysis_type in ["all", "caption"] and self.image_caption_model:
            # Generate caption
            caption = await self._generate_image_caption(image_url)
            results["caption"] = caption
            
        if analysis_type in ["all", "objects"] and self.openai_client:
            # Detect objects using vision model
            objects = await self._detect_image_objects(image_url)
            results["objects"] = objects
            
        if analysis_type in ["all", "similarity"] and self.clip_model:
            # Generate embeddings for similarity search
            embeddings = await self._generate_image_embeddings(image_url)
            results["embeddings"] = embeddings
            
        return results
        
    async def _generate_image_caption(self, image_url: str) -> str:
        """Generate caption for image"""
        # Load image
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            image = Image.open(BytesIO(response.content))
            
        # Process image
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)
        
        # Generate caption
        with torch.no_grad():
            out = self.image_caption_model.generate(**inputs, max_length=50)
            caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            
        return caption
        
    async def _detect_image_objects(self, image_url: str) -> List[Dict[str, Any]]:
        """Detect objects in image using vision model"""
        response = await asyncio.to_thread(
            self.openai_client.ChatCompletion.create,
            model="gpt-4-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Detect and list all objects in this image with their locations."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            max_tokens=500
        )
        
        # Parse response
        objects_text = response.choices[0].message.content
        # This would need proper parsing
        objects = []
        
        return objects
        
    async def _generate_image_embeddings(self, image_url: str) -> List[float]:
        """Generate CLIP embeddings for image"""
        # Load image
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            image = Image.open(BytesIO(response.content))
            
        # Process image
        inputs = self.clip_processor(images=image, return_tensors="pt")
        
        # Generate embeddings
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
            embeddings = image_features.squeeze().cpu().numpy().tolist()
            
        return embeddings
        
    async def _analyze_video(self, video_url: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze video content"""
        # This would implement video analysis
        # For now, return placeholder
        return {
            "analysis_type": analysis_type,
            "status": "not_implemented"
        }
        
    async def _analyze_audio(self, audio_url: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze audio content"""
        # This would implement audio analysis
        # For now, return placeholder
        return {
            "analysis_type": analysis_type,
            "status": "not_implemented"
        }


# Global service instance
generative_ai_service = GenerativeAIService()