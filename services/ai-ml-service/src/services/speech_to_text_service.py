"""
Speech-to-Text Service

This service handles speech-to-text transcription using Whisper and other models.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
from pathlib import Path
import io
import tempfile
import os

import numpy as np
import librosa
import torch
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from ..db.models import MLProcessingJob, MLProcessingResult
from ..db.base import get_db_session


class SpeechToTextService:
    """Service for speech-to-text transcription."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.logger = MLLogger("speech_to_text")
        
    async def transcribe_audio(
        self,
        audio_data: Union[np.ndarray, bytes, str, Path],
        language: Optional[str] = None,
        return_segments: bool = True,
        return_word_timestamps: bool = False,
        temperature: float = 0.0,
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0,
        length_penalty: float = 1.0,
        suppress_tokens: Optional[List[int]] = None,
        initial_prompt: Optional[str] = None,
        condition_on_previous_text: bool = True,
        fp16: bool = True,
        compression_ratio_threshold: float = 2.4,
        logprob_threshold: float = -1.0,
        no_speech_threshold: float = 0.6,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Audio data (numpy array, bytes, file path, or Path object)
            language: Language code (e.g., 'en', 'es', 'fr')
            return_segments: Whether to return segment-level timestamps
            return_word_timestamps: Whether to return word-level timestamps
            temperature: Temperature for sampling
            beam_size: Number of beams for beam search
            best_of: Number of candidates to consider
            patience: Patience for beam search
            length_penalty: Length penalty for beam search
            suppress_tokens: List of token IDs to suppress
            initial_prompt: Initial prompt for the model
            condition_on_previous_text: Whether to condition on previous text
            fp16: Whether to use FP16 precision
            compression_ratio_threshold: Threshold for compression ratio
            logprob_threshold: Threshold for log probability
            no_speech_threshold: Threshold for no speech detection
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing transcription results
        """
        start_time = time.time()
        
        try:
            # Load and validate audio
            audio = await self._load_audio(audio_data)
            
            # Get model
            model_info = await self.model_manager.get_model("speech_to_text")
            model = model_info.model
            
            # Prepare transcription options
            options = {
                "language": language,
                "task": "transcribe",
                "temperature": temperature,
                "beam_size": beam_size,
                "best_of": best_of,
                "patience": patience,
                "length_penalty": length_penalty,
                "suppress_tokens": suppress_tokens or [-1],
                "initial_prompt": initial_prompt,
                "condition_on_previous_text": condition_on_previous_text,
                "fp16": fp16,
                "compression_ratio_threshold": compression_ratio_threshold,
                "logprob_threshold": logprob_threshold,
                "no_speech_threshold": no_speech_threshold,
                "word_timestamps": return_word_timestamps
            }
            
            # Run inference
            result = await self._run_inference(model, audio, options)
            
            # Process results
            transcription_result = await self._process_results(
                result, return_segments, return_word_timestamps
            )
            
            # Create response
            response = {
                "text": transcription_result["text"],
                "language": transcription_result.get("language", language or "unknown"),
                "language_probability": transcription_result.get("language_probability", 0.0),
                "duration": transcription_result.get("duration", 0.0),
                "segments": transcription_result.get("segments", []) if return_segments else [],
                "words": transcription_result.get("words", []) if return_word_timestamps else [],
                "model_name": model_info.name,
                "model_version": model_info.metadata.get("version", "unknown"),
                "processing_time": time.time() - start_time,
                "options": options
            }
            
            # Log to database if asset_id provided
            if asset_id:
                await self._log_to_database(asset_id, response)
            
            # Log inference
            self.logger.log_inference(
                "speech_to_text", 
                "audio", 
                response["processing_time"],
                batch_size=1
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("speech_to_text", str(e), asset_id=asset_id)
            raise InferenceError(f"Speech-to-text transcription failed: {e}")
    
    async def transcribe_video(
        self,
        video_path: Union[str, Path],
        extract_audio: bool = True,
        language: Optional[str] = None,
        return_segments: bool = True,
        return_word_timestamps: bool = False,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from a video file.
        
        Args:
            video_path: Path to video file
            extract_audio: Whether to extract audio from video
            language: Language code
            return_segments: Whether to return segment-level timestamps
            return_word_timestamps: Whether to return word-level timestamps
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing transcription results
        """
        start_time = time.time()
        
        try:
            # Extract audio from video
            audio_path = None
            if extract_audio:
                audio_path = await self._extract_audio_from_video(video_path)
            else:
                audio_path = video_path
            
            try:
                # Transcribe audio
                result = await self.transcribe_audio(
                    audio_data=audio_path,
                    language=language,
                    return_segments=return_segments,
                    return_word_timestamps=return_word_timestamps,
                    asset_id=asset_id
                )
                
                # Add video information
                result["video_path"] = str(video_path)
                result["extracted_audio"] = extract_audio
                result["total_processing_time"] = time.time() - start_time
                
                return result
                
            finally:
                # Clean up extracted audio file
                if extract_audio and audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
            
        except Exception as e:
            self.logger.log_error("video_transcription", str(e), asset_id=asset_id)
            raise InferenceError(f"Video transcription failed: {e}")
    
    async def transcribe_batch(
        self,
        audio_batch: List[Union[np.ndarray, bytes, str, Path]],
        language: Optional[str] = None,
        return_segments: bool = True,
        return_word_timestamps: bool = False,
        asset_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe a batch of audio files.
        
        Args:
            audio_batch: List of audio data
            language: Language code
            return_segments: Whether to return segment-level timestamps
            return_word_timestamps: Whether to return word-level timestamps
            asset_ids: List of asset IDs for database logging
            
        Returns:
            List of transcription results
        """
        start_time = time.time()
        
        try:
            # Create tasks for batch processing
            tasks = []
            for i, audio_data in enumerate(audio_batch):
                asset_id = asset_ids[i] if asset_ids and i < len(asset_ids) else None
                task = self.transcribe_audio(
                    audio_data=audio_data,
                    language=language,
                    return_segments=return_segments,
                    return_word_timestamps=return_word_timestamps,
                    asset_id=asset_id
                )
                tasks.append(task)
            
            # Process batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    self.logger.log_error("batch_transcription", str(result), batch_index=i)
                    successful_results.append(None)
                else:
                    successful_results.append(result)
            
            # Log batch processing
            processing_time = time.time() - start_time
            self.logger.log_batch_processing(
                batch_size=len(audio_batch),
                processing_time=processing_time,
                success_count=len(audio_batch) - failed_count,
                error_count=failed_count
            )
            
            return successful_results
            
        except Exception as e:
            self.logger.log_error("batch_transcription", str(e))
            raise InferenceError(f"Batch transcription failed: {e}")
    
    async def _load_audio(self, audio_data: Union[np.ndarray, bytes, str, Path]) -> np.ndarray:
        """Load and validate audio data."""
        if isinstance(audio_data, np.ndarray):
            return audio_data
        elif isinstance(audio_data, bytes):
            # Convert bytes to audio
            audio_buffer = io.BytesIO(audio_data)
            audio, sr = librosa.load(audio_buffer, sr=16000)
            return audio
        elif isinstance(audio_data, (str, Path)):
            # Load from file path
            audio, sr = librosa.load(str(audio_data), sr=16000)
            return audio
        else:
            raise ValidationError(f"Unsupported audio data type: {type(audio_data)}")
    
    async def _run_inference(
        self,
        model,
        audio: np.ndarray,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run speech-to-text inference."""
        # Check if using Whisper or transformers
        model_name = getattr(model, '__class__', {}).get('__name__', 'unknown')
        
        if "whisper" in model_name.lower() or hasattr(model, 'transcribe'):
            # OpenAI Whisper model
            result = model.transcribe(audio, **options)
        else:
            # Transformers model
            # This is a simplified implementation for transformers models
            processor = getattr(model, 'processor', None)
            if not processor:
                raise ProcessingError("No processor found for transformers model")
            
            inputs = processor(audio, return_tensors="pt", sampling_rate=16000)
            generated_ids = model.generate(inputs["input_features"])
            transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)
            
            result = {
                "text": transcription[0] if transcription else "",
                "language": options.get("language", "unknown"),
                "segments": [],
                "words": []
            }
        
        return result
    
    async def _process_results(
        self,
        result: Dict[str, Any],
        return_segments: bool,
        return_word_timestamps: bool
    ) -> Dict[str, Any]:
        """Process transcription results."""
        processed_result = {
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "language_probability": result.get("language_probability", 0.0),
            "duration": result.get("duration", 0.0)
        }
        
        if return_segments and "segments" in result:
            processed_result["segments"] = []
            for segment in result["segments"]:
                processed_segment = {
                    "id": segment.get("id", 0),
                    "seek": segment.get("seek", 0),
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "text": segment.get("text", ""),
                    "tokens": segment.get("tokens", []),
                    "temperature": segment.get("temperature", 0.0),
                    "avg_logprob": segment.get("avg_logprob", 0.0),
                    "compression_ratio": segment.get("compression_ratio", 0.0),
                    "no_speech_prob": segment.get("no_speech_prob", 0.0)
                }
                
                if return_word_timestamps and "words" in segment:
                    processed_segment["words"] = segment["words"]
                
                processed_result["segments"].append(processed_segment)
        
        if return_word_timestamps and "words" in result:
            processed_result["words"] = result["words"]
        
        return processed_result
    
    async def _extract_audio_from_video(self, video_path: Union[str, Path]) -> str:
        """Extract audio from video file."""
        try:
            import subprocess
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                audio_path = tmp_file.name
            
            # Use ffmpeg to extract audio
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", "16000",
                "-y",  # Overwrite output file
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise ProcessingError(f"FFmpeg failed: {result.stderr}")
            
            return audio_path
            
        except Exception as e:
            raise ProcessingError(f"Audio extraction failed: {e}")
    
    async def _log_to_database(
        self,
        asset_id: str,
        response: Dict[str, Any]
    ) -> None:
        """Log transcription results to database."""
        try:
            async with get_db_session() as session:
                # Create processing job
                job = MLProcessingJob(
                    asset_id=uuid.UUID(asset_id),
                    job_type="speech_to_text",
                    status="completed",
                    input_data={
                        "language": response["language"],
                        "duration": response["duration"],
                        "options": response["options"]
                    },
                    results=response,
                    model_name=response["model_name"],
                    model_version=response["model_version"],
                    processing_time=response["processing_time"],
                    completed_at=time.time()
                )
                
                session.add(job)
                await session.flush()
                
                # Create result record for the full transcription
                result = MLProcessingResult(
                    job_id=job.id,
                    result_type="speech_to_text",
                    result_data={
                        "text": response["text"],
                        "language": response["language"],
                        "language_probability": response["language_probability"],
                        "duration": response["duration"]
                    },
                    confidence=response["language_probability"],
                    metadata={
                        "word_count": len(response["text"].split()),
                        "segment_count": len(response.get("segments", [])),
                        "word_timestamp_count": len(response.get("words", []))
                    }
                )
                session.add(result)
                
                # Create result records for segments if available
                for segment in response.get("segments", []):
                    segment_result = MLProcessingResult(
                        job_id=job.id,
                        result_type="speech_to_text_segment",
                        result_data=segment,
                        confidence=segment.get("avg_logprob", 0.0),
                        start_time=segment.get("start", 0.0),
                        end_time=segment.get("end", 0.0),
                        metadata={
                            "segment_id": segment.get("id", 0),
                            "tokens": segment.get("tokens", []),
                            "temperature": segment.get("temperature", 0.0),
                            "compression_ratio": segment.get("compression_ratio", 0.0),
                            "no_speech_prob": segment.get("no_speech_prob", 0.0)
                        }
                    )
                    session.add(segment_result)
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("database_logging", str(e), asset_id=asset_id)
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        try:
            model_info = await self.model_manager.get_model("speech_to_text")
            supported_languages = model_info.metadata.get("languages", [])
            
            # Default Whisper languages if not specified
            if not supported_languages:
                supported_languages = [
                    "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                    "ar", "tr", "pl", "ca", "nl", "sv", "he", "no", "fi", "uk"
                ]
            
            return supported_languages
        except Exception as e:
            self.logger.log_error("get_languages", str(e))
            return []
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get speech-to-text model information."""
        try:
            model_info = await self.model_manager.get_model("speech_to_text")
            return {
                "name": model_info.name,
                "type": model_info.model_type,
                "metadata": model_info.metadata,
                "supported_languages": await self.get_supported_languages()
            }
        except Exception as e:
            self.logger.log_error("get_model_info", str(e))
            return {}
    
    async def detect_language(
        self,
        audio_data: Union[np.ndarray, bytes, str, Path],
        duration: float = 30.0
    ) -> Dict[str, Any]:
        """
        Detect language of audio.
        
        Args:
            audio_data: Audio data
            duration: Duration of audio to analyze (in seconds)
            
        Returns:
            Dictionary containing language detection results
        """
        try:
            # Load audio
            audio = await self._load_audio(audio_data)
            
            # Limit duration for language detection
            if len(audio) > duration * 16000:  # 16kHz sample rate
                audio = audio[:int(duration * 16000)]
            
            # Get model
            model_info = await self.model_manager.get_model("speech_to_text")
            model = model_info.model
            
            # Detect language (Whisper-specific)
            if hasattr(model, 'detect_language'):
                probs = model.detect_language(audio)
                detected_language = max(probs, key=probs.get)
                confidence = probs[detected_language]
                
                return {
                    "language": detected_language,
                    "confidence": confidence,
                    "all_probabilities": probs,
                    "duration_analyzed": duration
                }
            else:
                # Fallback: run transcription and get language
                result = await self.transcribe_audio(
                    audio_data=audio,
                    return_segments=False,
                    return_word_timestamps=False
                )
                
                return {
                    "language": result.get("language", "unknown"),
                    "confidence": result.get("language_probability", 0.0),
                    "duration_analyzed": duration
                }
                
        except Exception as e:
            self.logger.log_error("language_detection", str(e))
            raise InferenceError(f"Language detection failed: {e}")