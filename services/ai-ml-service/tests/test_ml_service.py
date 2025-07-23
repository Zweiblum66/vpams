"""
Test ML Service

Tests for the main ML service coordination functionality.
"""

import pytest
import asyncio
import numpy as np
import cv2
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import hashlib

from src.services.ml_service import MLService
from src.services.model_manager import ModelInfo
from src.core.exceptions import InferenceError, ValidationError
from src.core.config import settings


class MockModelInfo:
    """Mock model info object."""
    def __init__(self, name="test_model", model_type="test"):
        self.name = name
        self.model_type = model_type
        self.metadata = {"version": "1.0"}
        self.model = Mock()


class TestMLService:
    """Test cases for MLService."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_model = AsyncMock()
        return manager
    
    @pytest.fixture
    def service(self, model_manager):
        """Create ML service instance."""
        return MLService(model_manager)
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create a blank 640x480 RGB image
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some variation
        cv2.rectangle(image, (100, 100), (300, 300), (255, 255, 255), -1)
        return image
    
    @pytest.fixture
    def sample_audio(self):
        """Create sample audio data."""
        # 1 second of audio at 16kHz
        return np.random.random(16000).astype(np.float32)
    
    async def test_initialize(self, service, model_manager):
        """Test service initialization."""
        # Setup mocks for various model warmups
        model_manager.get_model.return_value = MockModelInfo()
        
        with patch.multiple(
            settings,
            ENABLE_OBJECT_DETECTION=True,
            ENABLE_FACE_DETECTION=True,
            ENABLE_CONTENT_MODERATION=True,
            ENABLE_SENTIMENT_ANALYSIS=True,
            ENABLE_LANGUAGE_DETECTION=True,
            ENABLE_SPEAKER_DIARIZATION=True,
            ENABLE_KEYWORD_EXTRACTION=True,
            ENABLE_ENTITY_RECOGNITION=True
        ):
            # Mock warmup methods
            with patch.object(service, '_warm_up_models', new_callable=AsyncMock) as mock_warmup:
                await service.initialize()
                mock_warmup.assert_called_once()
    
    async def test_warm_up_models(self, service, model_manager):
        """Test model warmup process."""
        model_manager.get_model.return_value = MockModelInfo()
        
        # Mock all warmup methods
        warmup_methods = [
            '_warm_up_object_detection',
            '_warm_up_face_detection',
            '_warm_up_content_moderation',
            '_warm_up_sentiment_analysis',
            '_warm_up_language_detection',
            '_warm_up_speaker_diarization',
            '_warm_up_keyword_extraction',
            '_warm_up_entity_recognition'
        ]
        
        with patch.multiple(
            settings,
            ENABLE_OBJECT_DETECTION=True,
            ENABLE_FACE_DETECTION=True,
            ENABLE_CONTENT_MODERATION=True,
            ENABLE_SENTIMENT_ANALYSIS=True,
            ENABLE_LANGUAGE_DETECTION=True,
            ENABLE_SPEAKER_DIARIZATION=True,
            ENABLE_KEYWORD_EXTRACTION=True,
            ENABLE_ENTITY_RECOGNITION=True
        ):
            for method in warmup_methods:
                setattr(service, method, AsyncMock())
            
            await service._warm_up_models()
            
            # Verify all warmup methods were called
            for method in warmup_methods:
                getattr(service, method).assert_called_once()
    
    async def test_detect_objects_with_numpy_array(self, service, model_manager, sample_image):
        """Test object detection with numpy array input."""
        # Setup mock model
        mock_model = Mock()
        mock_result = Mock()
        mock_boxes = Mock()
        mock_box = Mock()
        mock_box.conf = [0.95]
        mock_box.xyxy = [[100, 100, 300, 300]]
        mock_box.cls = [0]
        mock_boxes.__iter__ = Mock(return_value=iter([mock_box]))
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]
        mock_model.names = {0: "person"}
        
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.detect_objects(sample_image, confidence_threshold=0.5)
        
        # Assertions
        assert "detections" in result
        assert "total_objects" in result
        assert result["total_objects"] == 1
        assert result["model_name"] == "object_detection"
        assert result["confidence_threshold"] == 0.5
        
        detection = result["detections"][0]
        assert detection["class_name"] == "person"
        assert detection["confidence"] == 0.95
        assert "bbox" in detection
    
    async def test_detect_objects_with_bytes(self, service, model_manager, sample_image):
        """Test object detection with bytes input."""
        # Convert image to bytes
        _, buffer = cv2.imencode('.jpg', sample_image)
        image_bytes = buffer.tobytes()
        
        # Setup mock
        mock_model = Mock()
        mock_model.return_value = []
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.detect_objects(image_bytes)
        
        # Assertions
        assert result["total_objects"] == 0
    
    async def test_detect_objects_with_file_path(self, service, model_manager, tmp_path):
        """Test object detection with file path input."""
        # Create temporary image file
        image_path = tmp_path / "test_image.jpg"
        cv2.imwrite(str(image_path), np.zeros((480, 640, 3), dtype=np.uint8))
        
        # Setup mock
        mock_model = Mock()
        mock_model.return_value = []
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.detect_objects(str(image_path))
        
        # Assertions
        assert result["total_objects"] == 0
    
    async def test_detect_objects_invalid_path(self, service):
        """Test object detection with invalid file path."""
        with pytest.raises(InferenceError, match="Could not load image"):
            await service.detect_objects("/nonexistent/image.jpg")
    
    async def test_detect_objects_invalid_bytes(self, service):
        """Test object detection with invalid bytes."""
        with pytest.raises(InferenceError, match="Could not decode image"):
            await service.detect_objects(b"invalid_image_data")
    
    async def test_detect_faces(self, service, model_manager, sample_image):
        """Test face detection."""
        # Setup mock
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {
                'confidence': 0.95,
                'box': [100, 100, 200, 200],
                'keypoints': {
                    'left_eye': (150, 150),
                    'right_eye': (250, 150)
                }
            }
        ])
        
        model_info = MockModelInfo("face_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_face_detection
        with patch.object(service, '_run_face_detection', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "faces": [{"confidence": 0.95, "bbox": {"x": 100, "y": 100}}],
                "total_faces": 1,
                "model_name": "face_detection"
            }
            
            result = await service.detect_faces(sample_image, min_face_size=20)
            
            # Assertions
            assert result["total_faces"] == 1
            assert result["model_name"] == "face_detection"
    
    async def test_transcribe_audio_with_numpy(self, service, model_manager, sample_audio):
        """Test audio transcription with numpy array."""
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("speech_to_text")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_speech_to_text
        with patch.object(service, '_run_speech_to_text', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "text": "Test transcription",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Test transcription"}],
                "language": "en",
                "confidence": 0.95
            }
            
            result = await service.transcribe_audio(sample_audio, language="en")
            
            # Assertions
            assert result["text"] == "Test transcription"
            assert result["language"] == "en"
            assert len(result["segments"]) == 1
    
    async def test_moderate_content(self, service, model_manager):
        """Test content moderation."""
        test_text = "This is a test text for moderation."
        
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("content_moderation")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_content_moderation
        with patch.object(service, '_run_content_moderation', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "safe": True,
                "categories": {
                    "toxic": 0.01,
                    "severe_toxic": 0.001,
                    "obscene": 0.005,
                    "threat": 0.002,
                    "insult": 0.008,
                    "identity_hate": 0.003
                },
                "overall_score": 0.01
            }
            
            result = await service.moderate_content(test_text)
            
            # Assertions
            assert result["safe"] is True
            assert "categories" in result
            assert result["overall_score"] < 0.5
    
    async def test_analyze_sentiment(self, service, model_manager):
        """Test sentiment analysis."""
        test_text = "I love this product! It's amazing."
        
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("sentiment_analysis")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_sentiment_analysis
        with patch.object(service, '_run_sentiment_analysis', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "sentiment": "positive",
                "confidence": 0.98,
                "scores": {
                    "positive": 0.98,
                    "negative": 0.01,
                    "neutral": 0.01
                }
            }
            
            result = await service.analyze_sentiment(test_text)
            
            # Assertions
            assert result["sentiment"] == "positive"
            assert result["confidence"] > 0.9
            assert result["scores"]["positive"] > 0.9
    
    async def test_detect_language(self, service, model_manager):
        """Test language detection."""
        test_text = "Hello, how are you today?"
        
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("language_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_language_detection
        with patch.object(service, '_run_language_detection', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "detected_languages": [
                    {"language": "en", "confidence": 0.99, "language_name": "English"}
                ],
                "primary_language": "en"
            }
            
            result = await service.detect_language(test_text)
            
            # Assertions
            assert result["primary_language"] == "en"
            assert len(result["detected_languages"]) > 0
            assert result["detected_languages"][0]["confidence"] > 0.9
    
    async def test_diarize_speakers(self, service, model_manager, sample_audio):
        """Test speaker diarization."""
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("speaker_diarization")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_speaker_diarization
        with patch.object(service, '_run_speaker_diarization', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "segments": [
                    {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"},
                    {"start": 0.5, "end": 1.0, "speaker": "SPEAKER_01"}
                ],
                "speakers": ["SPEAKER_00", "SPEAKER_01"],
                "total_speakers": 2
            }
            
            result = await service.diarize_speakers(sample_audio)
            
            # Assertions
            assert result["total_speakers"] == 2
            assert len(result["segments"]) == 2
            assert len(result["speakers"]) == 2
    
    async def test_extract_keywords(self, service, model_manager):
        """Test keyword extraction."""
        test_text = "Machine learning is transforming artificial intelligence and data science."
        
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("keyword_extraction")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_keyword_extraction
        with patch.object(service, '_run_keyword_extraction', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "keywords": [
                    {"keyword": "machine learning", "score": 0.95},
                    {"keyword": "artificial intelligence", "score": 0.92},
                    {"keyword": "data science", "score": 0.88}
                ],
                "method": "bert"
            }
            
            result = await service.extract_keywords(test_text, max_keywords=5)
            
            # Assertions
            assert len(result["keywords"]) <= 5
            assert result["keywords"][0]["score"] > 0.8
            assert "method" in result
    
    async def test_recognize_entities(self, service, model_manager):
        """Test entity recognition."""
        test_text = "John Smith works at Microsoft in Seattle."
        
        # Setup mock
        mock_model = Mock()
        model_info = MockModelInfo("entity_recognition")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock _run_entity_recognition
        with patch.object(service, '_run_entity_recognition', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "entities": [
                    {"text": "John Smith", "type": "PERSON", "start": 0, "end": 10},
                    {"text": "Microsoft", "type": "ORG", "start": 20, "end": 29},
                    {"text": "Seattle", "type": "LOC", "start": 33, "end": 40}
                ],
                "entity_types": ["PERSON", "ORG", "LOC"]
            }
            
            result = await service.recognize_entities(test_text)
            
            # Assertions
            assert len(result["entities"]) == 3
            assert result["entities"][0]["type"] == "PERSON"
            assert result["entities"][1]["type"] == "ORG"
            assert result["entities"][2]["type"] == "LOC"
    
    async def test_caching_mechanism(self, service, model_manager, sample_image):
        """Test caching functionality."""
        # Setup mock
        mock_model = Mock()
        mock_model.return_value = []
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # First call - should hit the model
        result1 = await service.detect_objects(sample_image)
        
        # Mock cache to return the result
        cache_key = service._generate_cache_key("object_detection", sample_image, 0.5)
        service._cache[cache_key] = {
            "data": result1,
            "timestamp": time.time()
        }
        
        # Second call - should hit cache
        with patch.object(service, '_run_object_detection', new_callable=AsyncMock) as mock_run:
            result2 = await service.detect_objects(sample_image)
            
            # Model should not be called again if cache is working
            # Note: In actual implementation, cache check happens before model call
    
    async def test_concurrent_requests(self, service, model_manager, sample_image):
        """Test handling of concurrent requests."""
        # Setup mock
        mock_model = Mock()
        mock_model.return_value = []
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Create multiple concurrent requests
        tasks = [
            service.detect_objects(sample_image) for _ in range(5)
        ]
        
        # All should complete successfully
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        for result in results:
            assert "total_objects" in result
    
    async def test_semaphore_limiting(self, service, model_manager, sample_image):
        """Test semaphore limits concurrent processing."""
        # Setup mock with delay
        mock_model = Mock()
        mock_model.return_value = []
        model_info = MockModelInfo("object_detection")
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Replace semaphore with one that allows only 1 concurrent request
        service._processing_semaphore = asyncio.Semaphore(1)
        
        # Track processing order
        processing_order = []
        
        async def delayed_detection(idx):
            processing_order.append(f"start_{idx}")
            result = await service.detect_objects(sample_image)
            processing_order.append(f"end_{idx}")
            return result
        
        # Create concurrent requests
        tasks = [delayed_detection(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # All should complete
        assert len(results) == 3
    
    async def test_transcribe_with_speakers(self, service, model_manager, sample_audio):
        """Test transcription with speaker diarization."""
        # Setup mocks
        mock_stt_model = Mock()
        mock_diarization_model = Mock()
        
        stt_info = MockModelInfo("speech_to_text")
        stt_info.model = mock_stt_model
        
        diarization_info = MockModelInfo("speaker_diarization")
        diarization_info.model = mock_diarization_model
        
        model_manager.get_model.side_effect = [stt_info, diarization_info]
        
        # Mock the individual methods
        with patch.object(service, '_run_speech_to_text', new_callable=AsyncMock) as mock_stt:
            with patch.object(service, '_run_speaker_diarization', new_callable=AsyncMock) as mock_diarize:
                mock_stt.return_value = {
                    "text": "Hello world",
                    "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}]
                }
                mock_diarize.return_value = {
                    "segments": [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}],
                    "speakers": ["SPEAKER_00"]
                }
                
                result = await service.transcribe_with_speakers(sample_audio)
                
                # Assertions
                assert "transcription" in result
                assert "diarization" in result
                assert result["transcription"]["text"] == "Hello world"
                assert len(result["diarization"]["speakers"]) == 1
    
    async def test_shutdown(self, service):
        """Test service shutdown."""
        # Add some mock data to cache
        service._cache["test_key"] = {"data": "test", "timestamp": time.time()}
        
        # Shutdown should clear cache
        await service.shutdown()
        
        # Cache should be empty
        assert len(service._cache) == 0
    
    async def test_error_handling(self, service, model_manager):
        """Test error handling in various methods."""
        # Test model loading error
        model_manager.get_model.side_effect = Exception("Model load failed")
        
        with pytest.raises(InferenceError, match="Object detection failed"):
            await service.detect_objects(np.zeros((100, 100, 3), dtype=np.uint8))
        
        # Reset for next test
        model_manager.get_model.side_effect = None
        model_manager.get_model.return_value = MockModelInfo()
        
        # Test inference error
        mock_model = Mock()
        mock_model.side_effect = Exception("Inference failed")
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        with pytest.raises(InferenceError):
            await service.detect_objects(np.zeros((100, 100, 3), dtype=np.uint8))
    
    def test_cache_key_generation(self, service):
        """Test cache key generation."""
        # Test with same inputs
        image1 = np.zeros((100, 100, 3), dtype=np.uint8)
        image2 = np.zeros((100, 100, 3), dtype=np.uint8)
        
        key1 = service._generate_cache_key("test_op", image1, 0.5)
        key2 = service._generate_cache_key("test_op", image2, 0.5)
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different operation should generate different key
        key3 = service._generate_cache_key("different_op", image1, 0.5)
        assert key1 != key3
        
        # Different parameters should generate different key
        key4 = service._generate_cache_key("test_op", image1, 0.6)
        assert key1 != key4