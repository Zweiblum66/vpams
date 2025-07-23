"""
Model Manager for AI/ML Service

This module handles loading, caching, and managing ML models.
"""

import asyncio
import time
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import threading

import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer, AutoProcessor
from ultralytics import YOLO
import cv2
import structlog

from ..core.config import settings
from ..core.logging import MLLogger
from ..core.exceptions import ModelLoadError, ModelNotFoundError


class ModelInfo:
    """Information about a loaded model."""
    
    def __init__(self, name: str, model_type: str, model: Any, 
                 metadata: Optional[Dict] = None):
        self.name = name
        self.model_type = model_type
        self.model = model
        self.metadata = metadata or {}
        self.load_time = time.time()
        self.access_count = 0
        self.last_access = time.time()
    
    def accessed(self):
        """Mark model as accessed."""
        self.access_count += 1
        self.last_access = time.time()


class ModelManager:
    """Manages ML model loading, caching, and lifecycle."""
    
    def __init__(self):
        self.logger = MLLogger("model_manager")
        self._models: OrderedDict[str, ModelInfo] = OrderedDict()
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._initialization_tasks = {}
        
        # Create models directory if it doesn't exist
        self.models_path = Path(settings.MODEL_STORAGE_PATH)
        self.models_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize the model manager."""
        self.logger.logger.info("Initializing model manager")
        
        # Pre-load critical models
        critical_models = []
        
        if settings.ENABLE_OBJECT_DETECTION:
            critical_models.append("object_detection")
        
        if settings.ENABLE_FACE_DETECTION:
            critical_models.append("face_detection")
        
        if settings.ENABLE_SPEECH_TO_TEXT:
            critical_models.append("speech_to_text")
        
        if settings.ENABLE_CONTENT_MODERATION:
            critical_models.append("content_moderation")
        
        if settings.ENABLE_SENTIMENT_ANALYSIS:
            critical_models.append("sentiment_analysis")
        
        if settings.ENABLE_LANGUAGE_DETECTION:
            critical_models.append("language_detection")
        
        if settings.ENABLE_SPEAKER_DIARIZATION:
            critical_models.append("speaker_diarization")
        
        if settings.ENABLE_KEYWORD_EXTRACTION:
            critical_models.append("keyword_extraction")
        
        # Load critical models concurrently
        tasks = []
        for model_name in critical_models:
            task = asyncio.create_task(self._load_model_async(model_name))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.logger.info("Model manager initialized", loaded_models=len(self._models))
    
    async def _load_model_async(self, model_name: str) -> None:
        """Load a model asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, self._load_model, model_name)
        except Exception as e:
            self.logger.log_error("model_load", str(e), model_name=model_name)
    
    def _load_model(self, model_name: str) -> ModelInfo:
        """Load a specific model."""
        start_time = time.time()
        
        with self._lock:
            # Check if model is already loaded
            if model_name in self._models:
                model_info = self._models[model_name]
                model_info.accessed()
                # Move to end (most recently used)
                self._models.move_to_end(model_name)
                self.logger.log_cache_hit(model_name, model_name)
                return model_info
            
            self.logger.log_cache_miss(model_name, model_name)
            
            # Load the model
            model_info = self._create_model(model_name)
            
            # Add to cache
            self._models[model_name] = model_info
            
            # Check cache size and evict if necessary
            self._maybe_evict_models()
            
            load_time = time.time() - start_time
            self.logger.log_model_load(model_name, model_info.model_type, load_time)
            
            return model_info
    
    def _create_model(self, model_name: str) -> ModelInfo:
        """Create a model instance based on the model name."""
        if model_name == "object_detection":
            return self._create_object_detection_model()
        elif model_name == "face_detection":
            return self._create_face_detection_model()
        elif model_name == "scene_detection":
            return self._create_scene_detection_model()
        elif model_name == "speech_to_text":
            return self._create_speech_to_text_model()
        elif model_name == "content_moderation":
            return self._create_content_moderation_model()
        elif model_name == "sentiment_analysis":
            return self._create_sentiment_analysis_model()
        elif model_name == "entity_recognition":
            return self._create_entity_recognition_model()
        elif model_name == "language_detection":
            return self._create_language_detection_model()
        elif model_name == "speaker_diarization":
            return self._create_speaker_diarization_model()
        elif model_name == "keyword_extraction":
            return self._create_keyword_extraction_model()
        else:
            raise ModelNotFoundError(f"Unknown model: {model_name}")
    
    def _create_object_detection_model(self) -> ModelInfo:
        """Create object detection model."""
        model_path = self.models_path / "object_detection"
        
        # Load YOLOv8 model
        model = YOLO(settings.OBJECT_DETECTION_MODEL)
        
        metadata = {
            "model_name": settings.OBJECT_DETECTION_MODEL,
            "input_format": "image",
            "output_format": "detections",
            "classes": model.names if hasattr(model, 'names') else None
        }
        
        return ModelInfo("object_detection", "object_detection", model, metadata)
    
    def _create_face_detection_model(self) -> ModelInfo:
        """Create face detection model."""
        try:
            import mtcnn
            model = mtcnn.MTCNN()
            
            metadata = {
                "model_name": settings.FACE_DETECTION_MODEL,
                "input_format": "image",
                "output_format": "face_detections",
                "min_face_size": 20
            }
            
            return ModelInfo("face_detection", "face_detection", model, metadata)
        except ImportError:
            # Fallback to OpenCV Haar cascades
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            model = cv2.CascadeClassifier(cascade_path)
            
            metadata = {
                "model_name": "opencv_haar",
                "input_format": "image",
                "output_format": "face_detections",
                "type": "haar_cascade"
            }
            
            return ModelInfo("face_detection", "face_detection", model, metadata)
    
    def _create_scene_detection_model(self) -> ModelInfo:
        """Create scene detection model."""
        from transformers import AutoFeatureExtractor, AutoModelForImageClassification
        
        model_name = "microsoft/resnet-50"
        feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        model = AutoModelForImageClassification.from_pretrained(model_name)
        
        metadata = {
            "model_name": model_name,
            "input_format": "image",
            "output_format": "scene_classifications",
            "feature_extractor": feature_extractor
        }
        
        return ModelInfo("scene_detection", "scene_detection", model, metadata)
    
    def _create_speech_to_text_model(self) -> ModelInfo:
        """Create speech-to-text model."""
        try:
            import whisper
            model = whisper.load_model("base")
            
            metadata = {
                "model_name": "whisper-base",
                "input_format": "audio",
                "output_format": "text",
                "languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
            }
            
            return ModelInfo("speech_to_text", "speech_to_text", model, metadata)
        except ImportError:
            # Fallback to transformers-based model
            from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
            
            processor = AutoProcessor.from_pretrained("openai/whisper-base")
            model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-base")
            
            metadata = {
                "model_name": "whisper-base-transformers",
                "input_format": "audio",
                "output_format": "text",
                "processor": processor
            }
            
            return ModelInfo("speech_to_text", "speech_to_text", model, metadata)
    
    def _create_content_moderation_model(self) -> ModelInfo:
        """Create content moderation model."""
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        model_name = "unitary/toxic-bert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        metadata = {
            "model_name": model_name,
            "input_format": "text",
            "output_format": "toxicity_scores",
            "tokenizer": tokenizer,
            "labels": ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
        }
        
        return ModelInfo("content_moderation", "content_moderation", model, metadata)
    
    def _create_sentiment_analysis_model(self) -> ModelInfo:
        """Create sentiment analysis model."""
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        metadata = {
            "model_name": model_name,
            "input_format": "text",
            "output_format": "sentiment_scores",
            "tokenizer": tokenizer,
            "labels": ["negative", "neutral", "positive"]
        }
        
        return ModelInfo("sentiment_analysis", "sentiment_analysis", model, metadata)
    
    def _create_entity_recognition_model(self) -> ModelInfo:
        """Create entity recognition model."""
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        
        model_name = "dbmdz/bert-large-cased-finetuned-conll03-english"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        metadata = {
            "model_name": model_name,
            "input_format": "text",
            "output_format": "entities",
            "tokenizer": tokenizer,
            "labels": ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC", "B-MISC", "I-MISC"]
        }
        
        return ModelInfo("entity_recognition", "entity_recognition", model, metadata)
    
    def _create_language_detection_model(self) -> ModelInfo:
        """Create language detection model."""
        # Language detection doesn't require a specific model - we use langdetect library
        # This is a placeholder model that will be used by the detection logic
        model = "langdetect"
        
        metadata = {
            "model_name": "langdetect",
            "input_format": "text",
            "output_format": "language_probabilities",
            "supported_languages": [
                "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi", "tr", "pl", "nl",
                "sv", "da", "no", "fi", "cs", "hu", "el", "he", "th", "vi", "id", "ms", "tl", "uk", "bg",
                "hr", "sk", "sl", "et", "lv", "lt", "ro", "ca", "eu", "gl", "cy", "ga", "is", "mt", "sq",
                "mk", "be", "ka", "hy", "az", "kk", "ky", "uz", "mn", "ne", "si", "my", "km", "lo", "bn",
                "ta", "te", "ml", "kn", "gu", "pa", "or", "mr", "as", "ur", "fa", "ps", "sw", "yo", "zu",
                "xh", "af", "am", "so", "ha", "ig"
            ],
            "fallback_method": "character_heuristics"
        }
        
        return ModelInfo("language_detection", "language_detection", model, metadata)
    
    def _create_speaker_diarization_model(self) -> ModelInfo:
        """Create speaker diarization model."""
        try:
            # Try to use pyannote.audio for speaker diarization
            from pyannote.audio import Pipeline
            
            # Use a pre-trained speaker diarization pipeline
            model = Pipeline.from_pretrained("pyannote/speaker-diarization")
            
            metadata = {
                "model_name": "pyannote/speaker-diarization",
                "input_format": "audio",
                "output_format": "speaker_segments",
                "type": "pyannote",
                "min_speakers": 1,
                "max_speakers": 20,
                "supported_formats": ["wav", "mp3", "flac", "m4a"]
            }
            
            return ModelInfo("speaker_diarization", "speaker_diarization", model, metadata)
        except ImportError:
            # Fallback to energy-based segmentation
            model = "energy_based"
            
            metadata = {
                "model_name": "energy_based_diarization",
                "input_format": "audio",
                "output_format": "speaker_segments",
                "type": "energy_based",
                "min_speakers": 1,
                "max_speakers": 10,
                "fallback_method": "energy_segmentation"
            }
            
            return ModelInfo("speaker_diarization", "speaker_diarization", model, metadata)
    
    def _create_keyword_extraction_model(self) -> ModelInfo:
        """Create keyword extraction model."""
        try:
            # Try to use a sentence transformer model for BERT-based keyword extraction
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            metadata = {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "input_format": "text",
                "output_format": "keywords",
                "type": "sentence_transformer",
                "algorithms": ["bert", "tfidf", "textrank", "yake"],
                "max_keywords": 20,
                "supported_languages": ["en", "multi"]
            }
            
            return ModelInfo("keyword_extraction", "keyword_extraction", model, metadata)
        except ImportError:
            # Fallback to a placeholder model for other algorithms
            model = "algorithm_based"
            
            metadata = {
                "model_name": "algorithm_based_keyword_extraction",
                "input_format": "text",
                "output_format": "keywords",
                "type": "algorithm_based",
                "algorithms": ["tfidf", "textrank", "yake", "frequency"],
                "max_keywords": 20,
                "supported_languages": ["en"],
                "fallback_method": "tfidf"
            }
            
            return ModelInfo("keyword_extraction", "keyword_extraction", model, metadata)
    
    def _maybe_evict_models(self) -> None:
        """Evict models if cache is full."""
        while len(self._models) > settings.MODEL_CACHE_SIZE:
            # Remove least recently used model
            oldest_model_name = next(iter(self._models))
            removed_model = self._models.pop(oldest_model_name)
            self.logger.logger.info(
                "Model evicted from cache",
                model_name=oldest_model_name,
                access_count=removed_model.access_count
            )
    
    async def get_model(self, model_name: str) -> ModelInfo:
        """Get a model, loading it if necessary."""
        # Check if model is already loaded
        with self._lock:
            if model_name in self._models:
                model_info = self._models[model_name]
                model_info.accessed()
                self._models.move_to_end(model_name)
                return model_info
        
        # Load model asynchronously
        loop = asyncio.get_event_loop()
        model_info = await loop.run_in_executor(self._executor, self._load_model, model_name)
        return model_info
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a model."""
        with self._lock:
            if model_name in self._models:
                model_info = self._models[model_name]
                return {
                    "name": model_info.name,
                    "type": model_info.model_type,
                    "metadata": model_info.metadata,
                    "load_time": model_info.load_time,
                    "access_count": model_info.access_count,
                    "last_access": model_info.last_access
                }
        return None
    
    def list_loaded_models(self) -> List[str]:
        """List all loaded models."""
        with self._lock:
            return list(self._models.keys())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "loaded_models": len(self._models),
                "cache_size_limit": settings.MODEL_CACHE_SIZE,
                "models": [
                    {
                        "name": info.name,
                        "type": info.model_type,
                        "access_count": info.access_count,
                        "last_access": info.last_access
                    }
                    for info in self._models.values()
                ]
            }
    
    async def unload_model(self, model_name: str) -> bool:
        """Unload a specific model."""
        with self._lock:
            if model_name in self._models:
                self._models.pop(model_name)
                self.logger.logger.info("Model unloaded", model_name=model_name)
                return True
            return False
    
    async def clear_cache(self) -> None:
        """Clear all loaded models."""
        with self._lock:
            model_count = len(self._models)
            self._models.clear()
            self.logger.logger.info("Model cache cleared", models_cleared=model_count)
    
    async def shutdown(self) -> None:
        """Shutdown the model manager."""
        self.logger.logger.info("Shutting down model manager")
        await self.clear_cache()
        self._executor.shutdown(wait=True)
        self.logger.logger.info("Model manager shutdown complete")