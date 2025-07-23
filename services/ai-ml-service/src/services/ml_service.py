"""
ML Service - Main service class for AI/ML operations

This service coordinates between different ML models and provides
a unified interface for AI/ML processing operations.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime, timedelta

import numpy as np
import cv2
from PIL import Image
import torch
import librosa
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from .model_manager import ModelManager, ModelInfo
from ..db.models import MLProcessingJob, MLProcessingResult, MLCache
from ..db.base import get_db_session


class MLService:
    """Main ML service for coordinating AI/ML operations."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.logger = MLLogger("ml_service")
        self._processing_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self._cache = {}  # In-memory cache for frequent operations
        
    async def initialize(self) -> None:
        """Initialize the ML service."""
        self.logger.logger.info("Initializing ML Service")
        
        # Warm up critical models
        await self._warm_up_models()
        
        self.logger.logger.info("ML Service initialized successfully")
    
    async def _warm_up_models(self) -> None:
        """Warm up critical models by performing dummy inference."""
        warmup_tasks = []
        
        if settings.ENABLE_OBJECT_DETECTION:
            warmup_tasks.append(self._warm_up_object_detection())
        
        if settings.ENABLE_FACE_DETECTION:
            warmup_tasks.append(self._warm_up_face_detection())
        
        if settings.ENABLE_CONTENT_MODERATION:
            warmup_tasks.append(self._warm_up_content_moderation())
        
        if settings.ENABLE_SENTIMENT_ANALYSIS:
            warmup_tasks.append(self._warm_up_sentiment_analysis())
        
        if settings.ENABLE_LANGUAGE_DETECTION:
            warmup_tasks.append(self._warm_up_language_detection())
        
        if settings.ENABLE_SPEAKER_DIARIZATION:
            warmup_tasks.append(self._warm_up_speaker_diarization())
        
        if settings.ENABLE_KEYWORD_EXTRACTION:
            warmup_tasks.append(self._warm_up_keyword_extraction())
        
        if settings.ENABLE_ENTITY_RECOGNITION:
            warmup_tasks.append(self._warm_up_entity_recognition())
        
        if warmup_tasks:
            await asyncio.gather(*warmup_tasks, return_exceptions=True)
    
    async def _warm_up_object_detection(self) -> None:
        """Warm up object detection model."""
        try:
            model_info = await self.model_manager.get_model("object_detection")
            # Create a dummy image for warmup
            dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
            await self._run_object_detection(dummy_image, model_info)
            self.logger.logger.info("Object detection model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up object detection: {e}")
    
    async def _warm_up_face_detection(self) -> None:
        """Warm up face detection model."""
        try:
            model_info = await self.model_manager.get_model("face_detection")
            # Create a dummy image for warmup
            dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
            await self._run_face_detection(dummy_image, model_info)
            self.logger.logger.info("Face detection model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up face detection: {e}")
    
    async def _warm_up_content_moderation(self) -> None:
        """Warm up content moderation model."""
        try:
            model_info = await self.model_manager.get_model("content_moderation")
            # Create a dummy text for warmup
            dummy_text = "This is a test text for warming up the content moderation model."
            await self._run_content_moderation(dummy_text, model_info)
            self.logger.logger.info("Content moderation model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up content moderation: {e}")
    
    async def _warm_up_sentiment_analysis(self) -> None:
        """Warm up sentiment analysis model."""
        try:
            model_info = await self.model_manager.get_model("sentiment_analysis")
            # Create a dummy text for warmup
            dummy_text = "This is a test text for warming up the sentiment analysis model."
            await self._run_sentiment_analysis(dummy_text, model_info)
            self.logger.logger.info("Sentiment analysis model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up sentiment analysis: {e}")
    
    async def _warm_up_language_detection(self) -> None:
        """Warm up language detection model."""
        try:
            model_info = await self.model_manager.get_model("language_detection")
            # Create a dummy text for warmup
            dummy_text = "This is a test text for warming up the language detection model."
            await self._run_language_detection(dummy_text, model_info)
            self.logger.logger.info("Language detection model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up language detection: {e}")
    
    async def _warm_up_speaker_diarization(self) -> None:
        """Warm up speaker diarization model."""
        try:
            model_info = await self.model_manager.get_model("speaker_diarization")
            # Create a dummy audio for warmup
            dummy_audio = np.random.random(16000).astype(np.float32)
            await self._run_speaker_diarization(dummy_audio, model_info)
            self.logger.logger.info("Speaker diarization model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up speaker diarization: {e}")
    
    async def _warm_up_keyword_extraction(self) -> None:
        """Warm up keyword extraction model."""
        try:
            model_info = await self.model_manager.get_model("keyword_extraction")
            # Create a dummy text for warmup
            dummy_text = "This is a test text for warming up the keyword extraction model."
            await self._run_keyword_extraction(dummy_text, model_info)
            self.logger.logger.info("Keyword extraction model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up keyword extraction: {e}")
    
    async def _warm_up_entity_recognition(self) -> None:
        """Warm up entity recognition model."""
        try:
            model_info = await self.model_manager.get_model("entity_recognition")
            # Create a dummy text for warmup
            dummy_text = "This is a test text for warming up the entity recognition model with John Smith from Microsoft."
            await self._run_entity_recognition(dummy_text, model_info)
            self.logger.logger.info("Entity recognition model warmed up")
        except Exception as e:
            self.logger.log_error("warmup", f"Failed to warm up entity recognition: {e}")
    
    async def detect_objects(self, image_data: Union[np.ndarray, bytes, str], 
                           confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Detect objects in an image."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if isinstance(image_data, str):
                    # Assume it's a file path
                    image = cv2.imread(image_data)
                    if image is None:
                        raise ValidationError(f"Could not load image from path: {image_data}")
                elif isinstance(image_data, bytes):
                    # Convert bytes to image
                    nparr = np.frombuffer(image_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if image is None:
                        raise ValidationError("Could not decode image from bytes")
                else:
                    image = image_data
                
                # Check cache
                cache_key = self._generate_cache_key("object_detection", image, confidence_threshold)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("object_detection")
                
                # Run inference
                results = await self._run_object_detection(image, model_info, confidence_threshold)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("object_detection", "image", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("object_detection", str(e))
                raise InferenceError(f"Object detection failed: {e}")
    
    async def _run_object_detection(self, image: np.ndarray, model_info: ModelInfo, 
                                  confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Run object detection inference."""
        model = model_info.model
        
        # Run inference
        results = model(image)
        
        # Process results
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    confidence = float(box.conf[0])
                    if confidence >= confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id] if hasattr(model, 'names') else str(class_id)
                        
                        detections.append({
                            "class_name": class_name,
                            "class_id": class_id,
                            "confidence": confidence,
                            "bbox": {
                                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                "width": x2 - x1, "height": y2 - y1
                            }
                        })
        
        return {
            "detections": detections,
            "total_objects": len(detections),
            "model_name": model_info.name,
            "confidence_threshold": confidence_threshold
        }
    
    async def detect_faces(self, image_data: Union[np.ndarray, bytes, str], 
                          min_face_size: int = 20) -> Dict[str, Any]:
        """Detect faces in an image."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate and process input
                if isinstance(image_data, str):
                    image = cv2.imread(image_data)
                    if image is None:
                        raise ValidationError(f"Could not load image from path: {image_data}")
                elif isinstance(image_data, bytes):
                    nparr = np.frombuffer(image_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if image is None:
                        raise ValidationError("Could not decode image from bytes")
                else:
                    image = image_data
                
                # Check cache
                cache_key = self._generate_cache_key("face_detection", image, min_face_size)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("face_detection")
                
                # Run inference
                results = await self._run_face_detection(image, model_info, min_face_size)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("face_detection", "image", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("face_detection", str(e))
                raise InferenceError(f"Face detection failed: {e}")
    
    async def _run_face_detection(self, image: np.ndarray, model_info: ModelInfo, 
                                min_face_size: int = 20) -> Dict[str, Any]:
        """Run face detection inference."""
        model = model_info.model
        
        # Check if using MTCNN or OpenCV
        if "mtcnn" in model_info.metadata.get("model_name", "").lower():
            # MTCNN model
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = model.detect_faces(rgb_image, min_face_size=min_face_size)
            
            faces = []
            for result in results:
                if result['confidence'] > 0.9:  # High confidence threshold
                    x, y, w, h = result['box']
                    faces.append({
                        "confidence": result['confidence'],
                        "bbox": {
                            "x": x, "y": y, "width": w, "height": h,
                            "x1": x, "y1": y, "x2": x + w, "y2": y + h
                        },
                        "landmarks": result.get('keypoints', {})
                    })
        else:
            # OpenCV Haar cascade
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces_detected = model.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            
            faces = []
            for (x, y, w, h) in faces_detected:
                faces.append({
                    "confidence": 1.0,  # Haar cascades don't provide confidence
                    "bbox": {
                        "x": x, "y": y, "width": w, "height": h,
                        "x1": x, "y1": y, "x2": x + w, "y2": y + h
                    }
                })
        
        return {
            "faces": faces,
            "total_faces": len(faces),
            "model_name": model_info.name
        }
    
    async def transcribe_audio(self, audio_data: Union[np.ndarray, bytes, str], 
                             language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio to text."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Process audio input
                if isinstance(audio_data, str):
                    # Load audio file
                    audio, sr = librosa.load(audio_data, sr=16000)
                elif isinstance(audio_data, bytes):
                    # Convert bytes to audio
                    import io
                    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)
                else:
                    audio = audio_data
                    sr = 16000
                
                # Check cache
                cache_key = self._generate_cache_key("speech_to_text", audio, language)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("speech_to_text")
                
                # Run inference
                results = await self._run_speech_to_text(audio, model_info, language)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("speech_to_text", "audio", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("speech_to_text", str(e))
                raise InferenceError(f"Speech-to-text failed: {e}")
    
    async def _run_speech_to_text(self, audio: np.ndarray, model_info: ModelInfo, 
                                language: Optional[str] = None) -> Dict[str, Any]:
        """Run speech-to-text inference."""
        model = model_info.model
        
        # Check if using Whisper or transformers
        if "whisper" in model_info.metadata.get("model_name", "").lower():
            # Whisper model
            result = model.transcribe(audio, language=language)
            
            return {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "model_name": model_info.name
            }
        else:
            # Transformers model
            processor = model_info.metadata.get("processor")
            if processor:
                inputs = processor(audio, return_tensors="pt", sampling_rate=16000)
                generated_ids = model.generate(inputs["input_features"])
                transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)
                
                return {
                    "text": transcription[0] if transcription else "",
                    "language": language or "unknown",
                    "model_name": model_info.name
                }
            else:
                raise ProcessingError("No processor found for transformers model")
    
    async def moderate_content(self, text: str, 
                              threshold: float = 0.5) -> Dict[str, Any]:
        """Moderate text content for toxicity and inappropriate content."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if not text or not isinstance(text, str):
                    raise ValidationError("Text input is required and must be a string")
                
                # Truncate very long text
                if len(text) > 5000:
                    text = text[:5000]
                
                # Check cache
                cache_key = self._generate_cache_key("content_moderation", text, threshold)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("content_moderation")
                
                # Run inference
                results = await self._run_content_moderation(text, model_info, threshold)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("content_moderation", "text", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("content_moderation", str(e))
                raise InferenceError(f"Content moderation failed: {e}")
    
    async def _run_content_moderation(self, text: str, model_info: ModelInfo, 
                                    threshold: float = 0.5) -> Dict[str, Any]:
        """Run content moderation inference."""
        model = model_info.model
        tokenizer = model_info.metadata.get("tokenizer")
        labels = model_info.metadata.get("labels", [])
        
        if not tokenizer:
            raise ProcessingError("No tokenizer found for content moderation model")
        
        # Tokenize input
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.sigmoid(outputs.logits).cpu().numpy()[0]
        
        # Process results
        moderation_results = []
        flagged_categories = []
        max_score = 0.0
        
        for i, label in enumerate(labels):
            score = float(predictions[i])
            is_flagged = score > threshold
            
            if is_flagged:
                flagged_categories.append(label)
            
            max_score = max(max_score, score)
            
            moderation_results.append({
                "category": label,
                "score": score,
                "flagged": is_flagged
            })
        
        # Overall assessment
        is_toxic = len(flagged_categories) > 0
        severity = "high" if max_score > 0.8 else "medium" if max_score > 0.5 else "low"
        
        return {
            "is_toxic": is_toxic,
            "severity": severity,
            "overall_score": max_score,
            "flagged_categories": flagged_categories,
            "detailed_scores": moderation_results,
            "threshold": threshold,
            "model_name": model_info.name,
            "text_length": len(text)
        }
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text content."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if not text or not isinstance(text, str):
                    raise ValidationError("Text input is required and must be a string")
                
                # Truncate very long text
                if len(text) > 5000:
                    text = text[:5000]
                
                # Check cache
                cache_key = self._generate_cache_key("sentiment_analysis", text)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("sentiment_analysis")
                
                # Run inference
                results = await self._run_sentiment_analysis(text, model_info)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("sentiment_analysis", "text", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("sentiment_analysis", str(e))
                raise InferenceError(f"Sentiment analysis failed: {e}")
    
    async def _run_sentiment_analysis(self, text: str, model_info: ModelInfo) -> Dict[str, Any]:
        """Run sentiment analysis inference."""
        model = model_info.model
        tokenizer = model_info.metadata.get("tokenizer")
        labels = model_info.metadata.get("labels", ["negative", "neutral", "positive"])
        
        if not tokenizer:
            raise ProcessingError("No tokenizer found for sentiment analysis model")
        
        # Tokenize input
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
        
        # Process results
        sentiment_scores = []
        max_score = 0.0
        predicted_label = ""
        
        for i, label in enumerate(labels):
            score = float(predictions[i])
            sentiment_scores.append({
                "label": label,
                "score": score
            })
            
            if score > max_score:
                max_score = score
                predicted_label = label
        
        # Determine confidence level
        confidence = "high" if max_score > 0.8 else "medium" if max_score > 0.6 else "low"
        
        # Create compound score (negative: -1, neutral: 0, positive: 1)
        if "negative" in labels and "positive" in labels:
            neg_idx = labels.index("negative")
            pos_idx = labels.index("positive")
            compound_score = float(predictions[pos_idx] - predictions[neg_idx])
        else:
            compound_score = max_score if predicted_label == "positive" else -max_score if predicted_label == "negative" else 0.0
        
        return {
            "sentiment": predicted_label,
            "confidence": confidence,
            "compound_score": compound_score,
            "max_score": max_score,
            "detailed_scores": sentiment_scores,
            "model_name": model_info.name,
            "text_length": len(text)
        }
    
    async def detect_language(self, text: str, 
                            confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Detect the language of text content."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if not text or not isinstance(text, str):
                    raise ValidationError("Text input is required and must be a string")
                
                # Check cache
                cache_key = self._generate_cache_key("language_detection", text, confidence_threshold)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("language_detection")
                
                # Run inference
                results = await self._run_language_detection(text, model_info, confidence_threshold)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("language_detection", "text", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("language_detection", str(e))
                raise InferenceError(f"Language detection failed: {e}")
    
    async def _run_language_detection(self, text: str, model_info: ModelInfo, 
                                    confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Run language detection inference."""
        model = model_info.model
        
        # Use langdetect library for language detection
        try:
            from langdetect import detect_langs, detect
            
            # Detect language probabilities
            languages = detect_langs(text)
            
            # Process results
            language_scores = []
            detected_language = ""
            max_confidence = 0.0
            
            for lang in languages:
                confidence = float(lang.prob)
                is_confident = confidence >= confidence_threshold
                
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_language = lang.lang
                
                language_scores.append({
                    "language": lang.lang,
                    "confidence": confidence,
                    "is_confident": is_confident
                })
            
            # Get language name mappings
            language_names = {
                "en": "English",
                "es": "Spanish", 
                "fr": "French",
                "de": "German",
                "it": "Italian",
                "pt": "Portuguese",
                "ru": "Russian",
                "zh": "Chinese",
                "ja": "Japanese",
                "ko": "Korean",
                "ar": "Arabic",
                "hi": "Hindi",
                "tr": "Turkish",
                "pl": "Polish",
                "nl": "Dutch",
                "sv": "Swedish",
                "da": "Danish",
                "no": "Norwegian",
                "fi": "Finnish",
                "cs": "Czech",
                "hu": "Hungarian",
                "el": "Greek",
                "he": "Hebrew",
                "th": "Thai",
                "vi": "Vietnamese",
                "id": "Indonesian",
                "ms": "Malay",
                "tl": "Filipino",
                "uk": "Ukrainian",
                "bg": "Bulgarian",
                "hr": "Croatian",
                "sk": "Slovak",
                "sl": "Slovenian",
                "et": "Estonian",
                "lv": "Latvian",
                "lt": "Lithuanian",
                "ro": "Romanian",
                "ca": "Catalan",
                "eu": "Basque",
                "gl": "Galician",
                "cy": "Welsh",
                "ga": "Irish",
                "is": "Icelandic",
                "mt": "Maltese",
                "sq": "Albanian",
                "mk": "Macedonian",
                "be": "Belarusian",
                "ka": "Georgian",
                "hy": "Armenian",
                "az": "Azerbaijani",
                "kk": "Kazakh",
                "ky": "Kyrgyz",
                "uz": "Uzbek",
                "mn": "Mongolian",
                "ne": "Nepali",
                "si": "Sinhala",
                "my": "Myanmar",
                "km": "Khmer",
                "lo": "Lao",
                "bn": "Bengali",
                "ta": "Tamil",
                "te": "Telugu",
                "ml": "Malayalam",
                "kn": "Kannada",
                "gu": "Gujarati",
                "pa": "Punjabi",
                "or": "Oriya",
                "mr": "Marathi",
                "as": "Assamese",
                "ur": "Urdu",
                "fa": "Persian",
                "ps": "Pashto",
                "sw": "Swahili",
                "yo": "Yoruba",
                "zu": "Zulu",
                "xh": "Xhosa",
                "af": "Afrikaans",
                "am": "Amharic",
                "so": "Somali",
                "ha": "Hausa",
                "ig": "Igbo"
            }
            
            # Add language names to scores
            for score in language_scores:
                score["language_name"] = language_names.get(score["language"], score["language"])
            
            # Determine confidence level
            confidence_level = "high" if max_confidence > 0.8 else "medium" if max_confidence > 0.6 else "low"
            
            return {
                "detected_language": detected_language,
                "language_name": language_names.get(detected_language, detected_language),
                "confidence": max_confidence,
                "confidence_level": confidence_level,
                "language_scores": language_scores,
                "threshold": confidence_threshold,
                "model_name": model_info.name,
                "text_length": len(text),
                "is_reliable": max_confidence >= confidence_threshold
            }
            
        except ImportError:
            # Fallback to a simple heuristic-based approach
            return await self._fallback_language_detection(text, confidence_threshold)
        except Exception as e:
            self.logger.log_error("language_detection", str(e))
            # Return English as default with low confidence
            return {
                "detected_language": "en",
                "language_name": "English",
                "confidence": 0.1,
                "confidence_level": "low",
                "language_scores": [{"language": "en", "language_name": "English", "confidence": 0.1, "is_confident": False}],
                "threshold": confidence_threshold,
                "model_name": model_info.name,
                "text_length": len(text),
                "is_reliable": False,
                "error": str(e)
            }
    
    async def _fallback_language_detection(self, text: str, 
                                         confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Fallback language detection using simple heuristics."""
        # Simple character-based heuristics
        char_counts = {}
        
        # Count character types
        latin_count = sum(1 for c in text if c.isalpha() and ord(c) < 256)
        cyrillic_count = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
        arabic_count = sum(1 for c in text if 0x0600 <= ord(c) <= 0x06FF)
        chinese_count = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)
        japanese_count = sum(1 for c in text if 0x3040 <= ord(c) <= 0x309F or 0x30A0 <= ord(c) <= 0x30FF)
        korean_count = sum(1 for c in text if 0xAC00 <= ord(c) <= 0xD7AF)
        
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            detected_language = "en"
            confidence = 0.1
        elif chinese_count / total_chars > 0.3:
            detected_language = "zh"
            confidence = 0.7
        elif japanese_count / total_chars > 0.3:
            detected_language = "ja"
            confidence = 0.7
        elif korean_count / total_chars > 0.3:
            detected_language = "ko"
            confidence = 0.7
        elif cyrillic_count / total_chars > 0.3:
            detected_language = "ru"
            confidence = 0.6
        elif arabic_count / total_chars > 0.3:
            detected_language = "ar"
            confidence = 0.6
        else:
            detected_language = "en"
            confidence = 0.5
        
        language_names = {
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "ar": "Arabic"
        }
        
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        
        return {
            "detected_language": detected_language,
            "language_name": language_names.get(detected_language, detected_language),
            "confidence": confidence,
            "confidence_level": confidence_level,
            "language_scores": [{
                "language": detected_language,
                "language_name": language_names.get(detected_language, detected_language),
                "confidence": confidence,
                "is_confident": confidence >= confidence_threshold
            }],
            "threshold": confidence_threshold,
            "model_name": "heuristic",
            "text_length": len(text),
            "is_reliable": confidence >= confidence_threshold
        }
    
    async def transcribe_audio_multilingual(self, audio_data: Union[np.ndarray, bytes, str], 
                                          language: Optional[str] = None,
                                          auto_detect_language: bool = True) -> Dict[str, Any]:
        """Transcribe audio with automatic language detection and multi-language support."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Process audio input
                if isinstance(audio_data, str):
                    # Load audio file
                    audio, sr = librosa.load(audio_data, sr=16000)
                elif isinstance(audio_data, bytes):
                    # Convert bytes to audio
                    import io
                    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)
                else:
                    audio = audio_data
                    sr = 16000
                
                # Check cache
                cache_key = self._generate_cache_key("multilingual_transcription", audio, language, auto_detect_language)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("speech_to_text")
                
                # Run multilingual transcription
                results = await self._run_multilingual_transcription(audio, model_info, language, auto_detect_language)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("multilingual_transcription", "audio", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("multilingual_transcription", str(e))
                raise InferenceError(f"Multilingual transcription failed: {e}")
    
    async def _run_multilingual_transcription(self, audio: np.ndarray, model_info: ModelInfo, 
                                            language: Optional[str] = None,
                                            auto_detect_language: bool = True) -> Dict[str, Any]:
        """Run multilingual speech-to-text inference."""
        model = model_info.model
        
        # Check if using Whisper (which supports multilingual)
        if "whisper" in model_info.metadata.get("model_name", "").lower():
            # Whisper model with multilingual support
            result = model.transcribe(audio, language=language if not auto_detect_language else None)
            
            # Extract detected language if auto-detection was used
            detected_language = result.get("language", "unknown")
            language_probability = result.get("language_probability", 0.0)
            
            return {
                "text": result["text"],
                "language": detected_language,
                "language_probability": language_probability,
                "auto_detected": auto_detect_language and language is None,
                "segments": result.get("segments", []),
                "model_name": model_info.name,
                "supports_multilingual": True
            }
        else:
            # For non-Whisper models, use regular transcription
            regular_result = await self._run_speech_to_text(audio, model_info, language)
            
            # Add multilingual information
            regular_result["auto_detected"] = False
            regular_result["language_probability"] = 1.0 if language else 0.0
            regular_result["supports_multilingual"] = False
            
            # If auto-detection is requested and no language specified, try to detect from text
            if auto_detect_language and not language and regular_result.get("text"):
                try:
                    lang_result = await self.detect_language(regular_result["text"])
                    regular_result["language"] = lang_result["detected_language"]
                    regular_result["language_probability"] = lang_result["confidence"]
                    regular_result["auto_detected"] = True
                except Exception:
                    pass
            
            return regular_result
    
    async def diarize_speakers(self, audio_data: Union[np.ndarray, bytes, str], 
                              num_speakers: Optional[int] = None,
                              min_speakers: int = 1,
                              max_speakers: int = 10) -> Dict[str, Any]:
        """Perform speaker diarization on audio to identify different speakers."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Process audio input
                if isinstance(audio_data, str):
                    # Load audio file
                    audio, sr = librosa.load(audio_data, sr=16000)
                elif isinstance(audio_data, bytes):
                    # Convert bytes to audio
                    import io
                    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)
                else:
                    audio = audio_data
                    sr = 16000
                
                # Validate parameters
                if num_speakers is not None and (num_speakers < 1 or num_speakers > 20):
                    raise ValidationError("Number of speakers must be between 1 and 20")
                
                if min_speakers < 1 or min_speakers > 20:
                    raise ValidationError("Minimum speakers must be between 1 and 20")
                
                if max_speakers < min_speakers or max_speakers > 20:
                    raise ValidationError("Maximum speakers must be >= minimum speakers and <= 20")
                
                # Check cache
                cache_key = self._generate_cache_key("speaker_diarization", audio, num_speakers, min_speakers, max_speakers)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("speaker_diarization")
                
                # Run speaker diarization
                results = await self._run_speaker_diarization(audio, model_info, num_speakers, min_speakers, max_speakers)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("speaker_diarization", "audio", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("speaker_diarization", str(e))
                raise InferenceError(f"Speaker diarization failed: {e}")
    
    async def _run_speaker_diarization(self, audio: np.ndarray, model_info: ModelInfo, 
                                     num_speakers: Optional[int] = None,
                                     min_speakers: int = 1,
                                     max_speakers: int = 10) -> Dict[str, Any]:
        """Run speaker diarization inference."""
        try:
            # Try to use pyannote.audio for speaker diarization
            from pyannote.audio import Pipeline
            
            # Check if we have a pre-trained pipeline or need to create one
            if hasattr(model_info.model, 'pipeline'):
                pipeline = model_info.model.pipeline
            else:
                # Use default pipeline
                pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
            
            # Convert audio to the expected format
            import torch
            import tempfile
            import soundfile as sf
            
            # Save audio to temporary file (required by pyannote)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, audio, 16000)
                tmp_file_path = tmp_file.name
            
            try:
                # Run diarization
                diarization = pipeline(tmp_file_path, num_speakers=num_speakers, 
                                     min_speakers=min_speakers, max_speakers=max_speakers)
                
                # Process results
                segments = []
                speakers = set()
                
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    speakers.add(speaker)
                    segments.append({
                        "start": float(turn.start),
                        "end": float(turn.end),
                        "duration": float(turn.end - turn.start),
                        "speaker": speaker
                    })
                
                # Sort segments by start time
                segments.sort(key=lambda x: x["start"])
                
                # Create speaker statistics
                speaker_stats = {}
                for speaker in speakers:
                    speaker_segments = [s for s in segments if s["speaker"] == speaker]
                    total_duration = sum(s["duration"] for s in speaker_segments)
                    
                    speaker_stats[speaker] = {
                        "total_duration": total_duration,
                        "segment_count": len(speaker_segments),
                        "percentage": (total_duration / len(audio) * 16000) * 100 if len(audio) > 0 else 0
                    }
                
                return {
                    "segments": segments,
                    "speakers": list(speakers),
                    "num_speakers": len(speakers),
                    "speaker_stats": speaker_stats,
                    "total_duration": float(len(audio) / 16000),
                    "model_name": model_info.name
                }
                
            finally:
                # Clean up temporary file
                import os
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except ImportError:
            # Fallback to simple audio segmentation
            return await self._fallback_speaker_diarization(audio, num_speakers, min_speakers, max_speakers)
        except Exception as e:
            self.logger.log_error("speaker_diarization", str(e))
            # Return fallback result
            return await self._fallback_speaker_diarization(audio, num_speakers, min_speakers, max_speakers)
    
    async def _fallback_speaker_diarization(self, audio: np.ndarray, 
                                          num_speakers: Optional[int] = None,
                                          min_speakers: int = 1,
                                          max_speakers: int = 10) -> Dict[str, Any]:
        """Fallback speaker diarization using simple audio segmentation."""
        # Simple energy-based segmentation
        frame_length = 2048
        hop_length = 512
        
        # Calculate energy
        energy = np.array([
            sum(abs(audio[i:i+frame_length]**2))
            for i in range(0, len(audio), hop_length)
        ])
        
        # Smooth energy
        from scipy.ndimage import gaussian_filter1d
        energy = gaussian_filter1d(energy, sigma=2)
        
        # Find speech segments based on energy threshold
        threshold = np.percentile(energy, 30)
        speech_frames = energy > threshold
        
        # Group consecutive speech frames
        segments = []
        current_start = None
        speaker_id = 0
        
        for i, is_speech in enumerate(speech_frames):
            time_sec = i * hop_length / 16000
            
            if is_speech and current_start is None:
                current_start = time_sec
            elif not is_speech and current_start is not None:
                # End of speech segment
                segments.append({
                    "start": current_start,
                    "end": time_sec,
                    "duration": time_sec - current_start,
                    "speaker": f"SPEAKER_{speaker_id % (num_speakers or 2)}"
                })
                speaker_id += 1
                current_start = None
        
        # Handle case where audio ends during speech
        if current_start is not None:
            segments.append({
                "start": current_start,
                "end": len(audio) / 16000,
                "duration": (len(audio) / 16000) - current_start,
                "speaker": f"SPEAKER_{speaker_id % (num_speakers or 2)}"
            })
        
        # Estimate number of speakers if not provided
        if num_speakers is None:
            estimated_speakers = min(max(len(segments) // 3, min_speakers), max_speakers)
        else:
            estimated_speakers = num_speakers
        
        # Reassign speakers more evenly
        for i, segment in enumerate(segments):
            segment["speaker"] = f"SPEAKER_{i % estimated_speakers}"
        
        # Create speaker list and statistics
        speakers = list(set(s["speaker"] for s in segments))
        speaker_stats = {}
        
        for speaker in speakers:
            speaker_segments = [s for s in segments if s["speaker"] == speaker]
            total_duration = sum(s["duration"] for s in speaker_segments)
            
            speaker_stats[speaker] = {
                "total_duration": total_duration,
                "segment_count": len(speaker_segments),
                "percentage": (total_duration / (len(audio) / 16000)) * 100 if len(audio) > 0 else 0
            }
        
        return {
            "segments": segments,
            "speakers": speakers,
            "num_speakers": len(speakers),
            "speaker_stats": speaker_stats,
            "total_duration": float(len(audio) / 16000),
            "model_name": "fallback_energy_based",
            "note": "Fallback method used - results may be less accurate"
        }
    
    async def transcribe_with_speakers(self, audio_data: Union[np.ndarray, bytes, str], 
                                     language: Optional[str] = None,
                                     num_speakers: Optional[int] = None,
                                     min_speakers: int = 1,
                                     max_speakers: int = 10) -> Dict[str, Any]:
        """Transcribe audio with speaker diarization."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Process audio input
                if isinstance(audio_data, str):
                    # Load audio file
                    audio, sr = librosa.load(audio_data, sr=16000)
                elif isinstance(audio_data, bytes):
                    # Convert bytes to audio
                    import io
                    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000)
                else:
                    audio = audio_data
                    sr = 16000
                
                # Run both transcription and diarization concurrently
                transcription_task = self.transcribe_audio_multilingual(audio, language)
                diarization_task = self.diarize_speakers(audio, num_speakers, min_speakers, max_speakers)
                
                transcription_result, diarization_result = await asyncio.gather(
                    transcription_task, diarization_task
                )
                
                # Combine results by aligning transcription segments with speaker segments
                combined_segments = []
                
                if transcription_result.get("segments"):
                    # Use transcription segments and assign speakers
                    for trans_segment in transcription_result["segments"]:
                        trans_start = trans_segment.get("start", 0)
                        trans_end = trans_segment.get("end", trans_start + 1)
                        
                        # Find overlapping speaker segment
                        assigned_speaker = "UNKNOWN"
                        max_overlap = 0
                        
                        for speaker_segment in diarization_result["segments"]:
                            speaker_start = speaker_segment["start"]
                            speaker_end = speaker_segment["end"]
                            
                            # Calculate overlap
                            overlap_start = max(trans_start, speaker_start)
                            overlap_end = min(trans_end, speaker_end)
                            overlap_duration = max(0, overlap_end - overlap_start)
                            
                            if overlap_duration > max_overlap:
                                max_overlap = overlap_duration
                                assigned_speaker = speaker_segment["speaker"]
                        
                        combined_segments.append({
                            "start": trans_start,
                            "end": trans_end,
                            "duration": trans_end - trans_start,
                            "text": trans_segment.get("text", ""),
                            "speaker": assigned_speaker,
                            "confidence": trans_segment.get("confidence", 0.0)
                        })
                else:
                    # No transcription segments, use diarization segments
                    for speaker_segment in diarization_result["segments"]:
                        combined_segments.append({
                            "start": speaker_segment["start"],
                            "end": speaker_segment["end"],
                            "duration": speaker_segment["duration"],
                            "text": "[Speech detected]",
                            "speaker": speaker_segment["speaker"],
                            "confidence": 0.5
                        })
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("transcribe_with_speakers", "audio", inference_time)
                
                return {
                    "text": transcription_result.get("text", ""),
                    "language": transcription_result.get("language", "unknown"),
                    "speakers": diarization_result["speakers"],
                    "num_speakers": diarization_result["num_speakers"],
                    "segments": combined_segments,
                    "speaker_stats": diarization_result["speaker_stats"],
                    "transcription_model": transcription_result.get("model_name", "unknown"),
                    "diarization_model": diarization_result.get("model_name", "unknown"),
                    "total_duration": diarization_result["total_duration"]
                }
                
            except Exception as e:
                self.logger.log_error("transcribe_with_speakers", str(e))
                raise InferenceError(f"Transcription with speakers failed: {e}")
    
    async def extract_keywords(self, text: str, 
                             max_keywords: int = 10,
                             algorithm: str = "tfidf") -> Dict[str, Any]:
        """Extract keywords from text content."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if not text or not isinstance(text, str):
                    raise ValidationError("Text input is required and must be a string")
                
                # Truncate very long text
                if len(text) > 10000:
                    text = text[:10000]
                
                # Check cache
                cache_key = self._generate_cache_key("keyword_extraction", text, max_keywords, algorithm)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("keyword_extraction")
                
                # Run inference
                results = await self._run_keyword_extraction(text, model_info, max_keywords, algorithm)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("keyword_extraction", "text", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("keyword_extraction", str(e))
                raise InferenceError(f"Keyword extraction failed: {e}")
    
    async def _run_keyword_extraction(self, text: str, model_info: ModelInfo, 
                                    max_keywords: int = 10,
                                    algorithm: str = "tfidf") -> Dict[str, Any]:
        """Run keyword extraction inference."""
        model = model_info.model
        
        # Use different algorithms based on the specified method
        if algorithm == "tfidf":
            keywords = await self._extract_keywords_tfidf(text, max_keywords)
        elif algorithm == "textrank":
            keywords = await self._extract_keywords_textrank(text, max_keywords)
        elif algorithm == "yake":
            keywords = await self._extract_keywords_yake(text, max_keywords)
        elif algorithm == "bert":
            keywords = await self._extract_keywords_bert(text, model_info, max_keywords)
        else:
            # Default to TF-IDF
            keywords = await self._extract_keywords_tfidf(text, max_keywords)
        
        # Language detection for better processing
        try:
            language_result = await self.detect_language(text)
            detected_language = language_result.get("detected_language", "en")
            language_confidence = language_result.get("confidence", 0.0)
        except Exception:
            detected_language = "en"
            language_confidence = 0.0
        
        # Post-process keywords
        processed_keywords = []
        for keyword in keywords:
            # Normalize keyword data
            if isinstance(keyword, dict):
                processed_keywords.append({
                    "keyword": keyword.get("keyword", ""),
                    "score": float(keyword.get("score", 0.0)),
                    "relevance": keyword.get("relevance", "medium"),
                    "category": keyword.get("category", "general")
                })
            else:
                # Handle case where keyword is just a string
                processed_keywords.append({
                    "keyword": str(keyword),
                    "score": 0.5,
                    "relevance": "medium",
                    "category": "general"
                })
        
        # Sort by score
        processed_keywords.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "keywords": processed_keywords[:max_keywords],
            "total_keywords": len(processed_keywords),
            "algorithm": algorithm,
            "language": detected_language,
            "language_confidence": language_confidence,
            "text_length": len(text),
            "model_name": model_info.name,
            "processing_time": time.time() - start_time if 'start_time' in locals() else 0.0
        }
    
    async def _extract_keywords_tfidf(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords using TF-IDF algorithm."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
            import re
            
            # Preprocessing
            text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
            sentences = [s.strip() for s in text_clean.split('.') if s.strip()]
            
            if len(sentences) < 2:
                sentences = [text_clean]
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=max_keywords * 3,
                stop_words=list(ENGLISH_STOP_WORDS),
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.8
            )
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get scores
            scores = tfidf_matrix.sum(axis=0).A1
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            keywords = []
            for keyword, score in keyword_scores[:max_keywords]:
                relevance = "high" if score > 0.3 else "medium" if score > 0.1 else "low"
                keywords.append({
                    "keyword": keyword,
                    "score": float(score),
                    "relevance": relevance,
                    "category": "tfidf"
                })
            
            return keywords
            
        except ImportError:
            # Fallback to simple word frequency
            return await self._extract_keywords_frequency(text, max_keywords)
    
    async def _extract_keywords_textrank(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords using TextRank algorithm."""
        try:
            import networkx as nx
            from collections import defaultdict
            import re
            
            # Preprocessing
            text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
            words = [word for word in text_clean.split() if len(word) > 3]
            
            if len(words) < 4:
                return await self._extract_keywords_frequency(text, max_keywords)
            
            # Build word co-occurrence graph
            window_size = 4
            graph = nx.Graph()
            
            for i in range(len(words) - window_size + 1):
                window = words[i:i + window_size]
                for j in range(len(window)):
                    for k in range(j + 1, len(window)):
                        word1, word2 = window[j], window[k]
                        if word1 != word2:
                            if graph.has_edge(word1, word2):
                                graph[word1][word2]['weight'] += 1
                            else:
                                graph.add_edge(word1, word2, weight=1)
            
            # Run PageRank
            if len(graph.nodes()) > 0:
                scores = nx.pagerank(graph, weight='weight')
                sorted_words = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                
                keywords = []
                for word, score in sorted_words[:max_keywords]:
                    relevance = "high" if score > 0.01 else "medium" if score > 0.005 else "low"
                    keywords.append({
                        "keyword": word,
                        "score": float(score),
                        "relevance": relevance,
                        "category": "textrank"
                    })
                
                return keywords
            else:
                return await self._extract_keywords_frequency(text, max_keywords)
                
        except ImportError:
            return await self._extract_keywords_frequency(text, max_keywords)
    
    async def _extract_keywords_yake(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords using YAKE algorithm."""
        try:
            import yake
            
            # YAKE configuration
            language = "en"
            max_ngram_size = 2
            deduplication_threshold = 0.7
            
            kw_extractor = yake.KeywordExtractor(
                lan=language,
                n=max_ngram_size,
                dedupLim=deduplication_threshold,
                top=max_keywords
            )
            
            yake_keywords = kw_extractor.extract_keywords(text)
            
            keywords = []
            for score, keyword in yake_keywords:
                # YAKE scores are inverted (lower is better)
                normalized_score = 1.0 / (1.0 + score)
                relevance = "high" if normalized_score > 0.3 else "medium" if normalized_score > 0.1 else "low"
                
                keywords.append({
                    "keyword": keyword,
                    "score": float(normalized_score),
                    "relevance": relevance,
                    "category": "yake"
                })
            
            return keywords
            
        except ImportError:
            return await self._extract_keywords_frequency(text, max_keywords)
    
    async def _extract_keywords_bert(self, text: str, model_info: ModelInfo, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords using BERT-based models."""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Get BERT model from model_info or use default
            if hasattr(model_info.model, 'encode'):
                # Use sentence transformer
                model = model_info.model
                
                # Extract candidate keywords (noun phrases, named entities)
                candidates = self._extract_candidate_phrases(text)
                
                if not candidates:
                    return await self._extract_keywords_frequency(text, max_keywords)
                
                # Encode document and candidates
                doc_embedding = model.encode([text])
                candidate_embeddings = model.encode(candidates)
                
                # Calculate similarity
                similarities = cosine_similarity(doc_embedding, candidate_embeddings)[0]
                
                # Create keyword results
                keywords = []
                for i, candidate in enumerate(candidates):
                    score = float(similarities[i])
                    relevance = "high" if score > 0.7 else "medium" if score > 0.5 else "low"
                    
                    keywords.append({
                        "keyword": candidate,
                        "score": score,
                        "relevance": relevance,
                        "category": "bert"
                    })
                
                # Sort by score and return top keywords
                keywords.sort(key=lambda x: x["score"], reverse=True)
                return keywords[:max_keywords]
                
            else:
                # Fallback to TF-IDF
                return await self._extract_keywords_tfidf(text, max_keywords)
                
        except ImportError:
            return await self._extract_keywords_tfidf(text, max_keywords)
    
    def _extract_candidate_phrases(self, text: str) -> List[str]:
        """Extract candidate phrases from text."""
        try:
            import spacy
            
            # Load spaCy model
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            
            candidates = []
            
            # Extract noun phrases
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3:  # Max 3 words
                    candidates.append(chunk.text.lower().strip())
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG", "PRODUCT", "EVENT", "WORK_OF_ART"]:
                    candidates.append(ent.text.lower().strip())
            
            # Remove duplicates
            candidates = list(set(candidates))
            
            return candidates
            
        except ImportError:
            # Fallback to simple phrase extraction
            import re
            
            # Extract phrases using regex patterns
            phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            phrases.extend(re.findall(r'\b[a-z]+(?:\s+[a-z]+){1,2}\b', text))
            
            # Clean and deduplicate
            candidates = []
            for phrase in phrases:
                clean_phrase = phrase.lower().strip()
                if len(clean_phrase) > 3 and clean_phrase not in candidates:
                    candidates.append(clean_phrase)
            
            return candidates[:50]  # Limit to avoid too many candidates
    
    async def _extract_keywords_frequency(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Fallback keyword extraction using word frequency."""
        from collections import Counter
        import re
        
        # Basic stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'can', 'may', 'might', 'must', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        # Clean text and extract words
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        words = [word for word in text_clean.split() if len(word) > 3 and word not in stop_words]
        
        # Count word frequencies
        word_counts = Counter(words)
        total_words = len(words)
        
        keywords = []
        for word, count in word_counts.most_common(max_keywords):
            score = count / total_words
            relevance = "high" if score > 0.05 else "medium" if score > 0.02 else "low"
            
            keywords.append({
                "keyword": word,
                "score": float(score),
                "relevance": relevance,
                "category": "frequency"
            })
        
        return keywords
    
    async def recognize_entities(self, text: str, 
                               confidence_threshold: float = 0.8,
                               entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Recognize named entities in text."""
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Validate input
                if not text:
                    raise ValidationError("Text content is required")
                
                if not isinstance(text, str):
                    raise ValidationError("Text must be a string")
                
                # Validate confidence threshold
                if confidence_threshold < 0.0 or confidence_threshold > 1.0:
                    raise ValidationError("Confidence threshold must be between 0.0 and 1.0")
                
                # Check cache
                cache_key = self._generate_cache_key("entity_recognition", text, confidence_threshold, entity_types)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
                
                # Get model
                model_info = await self.model_manager.get_model("entity_recognition")
                
                # Run entity recognition
                results = await self._run_entity_recognition(text, model_info, confidence_threshold, entity_types)
                
                # Cache result
                await self._cache_result(cache_key, results)
                
                # Log inference
                inference_time = time.time() - start_time
                self.logger.log_inference("entity_recognition", "text", inference_time)
                
                return results
                
            except Exception as e:
                self.logger.log_error("entity_recognition", str(e))
                raise InferenceError(f"Entity recognition failed: {e}")
    
    async def _run_entity_recognition(self, text: str, model_info: ModelInfo, 
                                    confidence_threshold: float = 0.8,
                                    entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run entity recognition inference."""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            import torch
            
            model = model_info.model
            tokenizer = model_info.metadata.get("tokenizer")
            
            if not tokenizer:
                raise ProcessingError("No tokenizer found in model metadata")
            
            # Tokenize text
            tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # Run inference
            with torch.no_grad():
                outputs = model(**tokens)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_token_class = predictions.argmax(-1)
            
            # Get model labels
            labels = model_info.metadata.get("labels", [])
            if not labels:
                # Default NER labels
                labels = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC", "B-MISC", "I-MISC"]
            
            # Convert tokens back to words and extract entities
            input_ids = tokens["input_ids"][0].tolist()
            token_predictions = predicted_token_class[0].tolist()
            token_confidences = predictions[0].max(-1).values.tolist()
            
            # Decode tokens
            decoded_tokens = tokenizer.convert_ids_to_tokens(input_ids)
            
            # Extract entities
            entities = []
            current_entity = None
            
            for i, (token, label_id, confidence) in enumerate(zip(decoded_tokens, token_predictions, token_confidences)):
                if token in ["[CLS]", "[SEP]", "[PAD]"]:
                    continue
                
                label = labels[label_id] if label_id < len(labels) else "O"
                
                # Filter by confidence threshold
                if confidence < confidence_threshold:
                    continue
                
                # Parse BIO tags
                if label.startswith("B-"):
                    # Begin new entity
                    if current_entity:
                        entities.append(current_entity)
                    
                    entity_type = label[2:]
                    current_entity = {
                        "text": token.replace("##", ""),
                        "label": entity_type,
                        "confidence": float(confidence),
                        "start": i,
                        "end": i + 1
                    }
                
                elif label.startswith("I-") and current_entity:
                    # Continue current entity
                    entity_type = label[2:]
                    if entity_type == current_entity["label"]:
                        current_entity["text"] += token.replace("##", "")
                        current_entity["end"] = i + 1
                        # Update confidence (average)
                        current_entity["confidence"] = (current_entity["confidence"] + confidence) / 2
                
                elif label == "O":
                    # Outside entity
                    if current_entity:
                        entities.append(current_entity)
                        current_entity = None
            
            # Add last entity if exists
            if current_entity:
                entities.append(current_entity)
            
            # Clean up entities
            cleaned_entities = []
            for entity in entities:
                # Clean text
                entity_text = entity["text"].replace("##", "").strip()
                if len(entity_text) > 1:  # Filter out single characters
                    # Filter by entity types if specified
                    if entity_types is None or entity["label"] in entity_types:
                        cleaned_entities.append({
                            "text": entity_text,
                            "label": entity["label"],
                            "confidence": entity["confidence"],
                            "start_char": entity["start"],
                            "end_char": entity["end"]
                        })
            
            # Group entities by type
            entities_by_type = {}
            for entity in cleaned_entities:
                entity_type = entity["label"]
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            # Calculate statistics
            total_entities = len(cleaned_entities)
            unique_entities = len(set(entity["text"].lower() for entity in cleaned_entities))
            
            # Average confidence
            avg_confidence = sum(entity["confidence"] for entity in cleaned_entities) / total_entities if total_entities > 0 else 0.0
            
            return {
                "entities": cleaned_entities,
                "entities_by_type": entities_by_type,
                "statistics": {
                    "total_entities": total_entities,
                    "unique_entities": unique_entities,
                    "entity_types": list(entities_by_type.keys()),
                    "avg_confidence": float(avg_confidence)
                },
                "model_name": model_info.name,
                "confidence_threshold": confidence_threshold,
                "text_length": len(text),
                "processing_time": time.time() - start_time if 'start_time' in locals() else 0.0
            }
            
        except Exception as e:
            self.logger.log_error("entity_recognition_inference", str(e))
            # Fallback to simple pattern-based entity recognition
            return await self._run_simple_entity_recognition(text, confidence_threshold, entity_types)
    
    async def _run_simple_entity_recognition(self, text: str, 
                                           confidence_threshold: float = 0.8,
                                           entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Simple pattern-based entity recognition fallback."""
        import re
        
        entities = []
        
        # Simple patterns for common entity types
        patterns = {
            "PERSON": [
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
                r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\b'  # Title Name
            ],
            "ORG": [
                r'\b[A-Z][a-z]+\s+(?:Inc|Corp|LLC|Ltd|Co)\b',  # Company suffixes
                r'\b[A-Z][A-Z]+\b'  # Acronyms
            ],
            "LOC": [
                r'\b[A-Z][a-z]+,\s+[A-Z][a-z]+\b',  # City, State
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'  # Location names
            ],
            "MISC": [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Dates
                r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b',  # Times
                r'\b[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\b'  # Month Day, Year
            ]
        }
        
        # Extract entities using patterns
        for entity_type, pattern_list in patterns.items():
            if entity_types and entity_type not in entity_types:
                continue
                
            for pattern in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity_text = match.group().strip()
                    
                    # Simple confidence scoring based on pattern complexity
                    base_confidence = 0.6
                    if len(entity_text) > 10:
                        base_confidence += 0.1
                    if entity_text.count(' ') > 0:
                        base_confidence += 0.1
                    
                    if base_confidence >= confidence_threshold:
                        entities.append({
                            "text": entity_text,
                            "label": entity_type,
                            "confidence": base_confidence,
                            "start_char": match.start(),
                            "end_char": match.end()
                        })
        
        # Remove duplicates
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["text"].lower(), entity["label"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        # Group entities by type
        entities_by_type = {}
        for entity in unique_entities:
            entity_type = entity["label"]
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        # Calculate statistics
        total_entities = len(unique_entities)
        unique_entity_texts = len(set(entity["text"].lower() for entity in unique_entities))
        avg_confidence = sum(entity["confidence"] for entity in unique_entities) / total_entities if total_entities > 0 else 0.0
        
        return {
            "entities": unique_entities,
            "entities_by_type": entities_by_type,
            "statistics": {
                "total_entities": total_entities,
                "unique_entities": unique_entity_texts,
                "entity_types": list(entities_by_type.keys()),
                "avg_confidence": float(avg_confidence)
            },
            "model_name": "pattern_based_ner",
            "confidence_threshold": confidence_threshold,
            "text_length": len(text),
            "processing_time": 0.0,
            "fallback_mode": True
        }
    
    def _generate_cache_key(self, operation: str, data: Any, *args) -> str:
        """Generate a cache key for the given operation and data."""
        # Create a hash of the data and parameters
        if isinstance(data, np.ndarray):
            data_hash = hashlib.md5(data.tobytes()).hexdigest()
        elif isinstance(data, (str, bytes)):
            data_hash = hashlib.md5(str(data).encode()).hexdigest()
        else:
            data_hash = hashlib.md5(str(data).encode()).hexdigest()
        
        # Include operation and additional parameters
        cache_data = f"{operation}:{data_hash}:{':'.join(map(str, args))}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available."""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select
                stmt = select(MLCache).where(MLCache.cache_key == cache_key)
                result = await session.execute(stmt)
                cache_entry = result.scalar_one_or_none()
                
                if cache_entry:
                    # Check if expired
                    if cache_entry.expires_at and cache_entry.expires_at < datetime.utcnow():
                        # Cache expired, delete it
                        await session.delete(cache_entry)
                        await session.commit()
                        return None
                    
                    # Update hit count and last accessed
                    cache_entry.hit_count += 1
                    cache_entry.last_accessed = datetime.utcnow()
                    await session.commit()
                    
                    return cache_entry.result_data
                
        except Exception as e:
            self.logger.log_error("cache_get", str(e))
        
        return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache result for future use."""
        try:
            async with get_db_session() as session:
                cache_entry = MLCache(
                    cache_key=cache_key,
                    model_name=result.get("model_name", "unknown"),
                    input_hash=cache_key[:32],  # Use first 32 chars of cache key
                    result_data=result,
                    expires_at=datetime.utcnow() + timedelta(seconds=settings.CACHE_TTL)
                )
                
                session.add(cache_entry)
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("cache_set", str(e))
    
    async def shutdown(self) -> None:
        """Shutdown the ML service."""
        self.logger.logger.info("Shutting down ML Service")
        # Clear in-memory cache
        self._cache.clear()
        self.logger.logger.info("ML Service shutdown complete")