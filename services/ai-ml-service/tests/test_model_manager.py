"""
Test Model Manager

Tests for ML model loading, caching, and lifecycle management.
"""

import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from collections import OrderedDict

from src.services.model_manager import ModelManager, ModelInfo
from src.core.exceptions import ModelLoadError, ModelNotFoundError
from src.core.config import settings


class TestModelInfo:
    """Test cases for ModelInfo class."""
    
    def test_model_info_creation(self):
        """Test ModelInfo initialization."""
        mock_model = Mock()
        info = ModelInfo("test_model", "test_type", mock_model, {"version": "1.0"})
        
        assert info.name == "test_model"
        assert info.model_type == "test_type"
        assert info.model == mock_model
        assert info.metadata == {"version": "1.0"}
        assert info.access_count == 0
        assert info.load_time > 0
        assert info.last_access > 0
    
    def test_model_info_accessed(self):
        """Test marking model as accessed."""
        mock_model = Mock()
        info = ModelInfo("test_model", "test_type", mock_model)
        
        initial_access_time = info.last_access
        initial_count = info.access_count
        
        # Wait a tiny bit to ensure time difference
        time.sleep(0.01)
        
        info.accessed()
        
        assert info.access_count == initial_count + 1
        assert info.last_access > initial_access_time


class TestModelManager:
    """Test cases for ModelManager class."""
    
    @pytest.fixture
    def temp_model_path(self, tmp_path):
        """Create temporary model storage path."""
        model_path = tmp_path / "models"
        model_path.mkdir()
        return model_path
    
    @pytest.fixture
    def manager(self, temp_model_path):
        """Create ModelManager instance with temporary path."""
        with patch.object(settings, 'MODEL_STORAGE_PATH', str(temp_model_path)):
            return ModelManager()
    
    async def test_initialize_no_models(self, manager):
        """Test initialization with no models enabled."""
        with patch.multiple(
            settings,
            ENABLE_OBJECT_DETECTION=False,
            ENABLE_FACE_DETECTION=False,
            ENABLE_SPEECH_TO_TEXT=False,
            ENABLE_CONTENT_MODERATION=False,
            ENABLE_SENTIMENT_ANALYSIS=False,
            ENABLE_LANGUAGE_DETECTION=False,
            ENABLE_SPEAKER_DIARIZATION=False,
            ENABLE_KEYWORD_EXTRACTION=False
        ):
            await manager.initialize()
            assert len(manager._models) == 0
    
    async def test_initialize_with_models(self, manager):
        """Test initialization with models enabled."""
        with patch.multiple(
            settings,
            ENABLE_OBJECT_DETECTION=True,
            ENABLE_FACE_DETECTION=True,
            ENABLE_SPEECH_TO_TEXT=False,
            ENABLE_CONTENT_MODERATION=False,
            ENABLE_SENTIMENT_ANALYSIS=False,
            ENABLE_LANGUAGE_DETECTION=False,
            ENABLE_SPEAKER_DIARIZATION=False,
            ENABLE_KEYWORD_EXTRACTION=False
        ):
            # Mock model loading
            with patch.object(manager, '_load_model_async', new_callable=AsyncMock) as mock_load:
                await manager.initialize()
                
                # Should attempt to load enabled models
                assert mock_load.call_count == 2
                call_args = [call[0][0] for call in mock_load.call_args_list]
                assert "object_detection" in call_args
                assert "face_detection" in call_args
    
    async def test_load_model_async(self, manager):
        """Test async model loading."""
        mock_model = Mock()
        mock_model_info = ModelInfo("test", "test", mock_model)
        
        with patch.object(manager, '_load_model', return_value=mock_model_info) as mock_load:
            await manager._load_model_async("test_model")
            mock_load.assert_called_once_with("test_model")
    
    async def test_load_model_async_error(self, manager):
        """Test async model loading with error."""
        with patch.object(manager, '_load_model', side_effect=Exception("Load failed")):
            # Should not raise exception (errors are logged)
            await manager._load_model_async("test_model")
    
    def test_load_model_cache_hit(self, manager):
        """Test loading model that's already in cache."""
        mock_model = Mock()
        model_info = ModelInfo("test_model", "test_type", mock_model)
        manager._models["test_model"] = model_info
        
        initial_access_count = model_info.access_count
        
        result = manager._load_model("test_model")
        
        assert result == model_info
        assert model_info.access_count == initial_access_count + 1
        # Model should be moved to end (MRU)
        assert list(manager._models.keys())[-1] == "test_model"
    
    def test_load_model_cache_miss(self, manager):
        """Test loading model that's not in cache."""
        mock_model = Mock()
        mock_model_info = ModelInfo("test_model", "test_type", mock_model)
        
        with patch.object(manager, '_create_model', return_value=mock_model_info):
            with patch.object(manager, '_maybe_evict_models'):
                result = manager._load_model("test_model")
                
                assert result == mock_model_info
                assert "test_model" in manager._models
                manager._maybe_evict_models.assert_called_once()
    
    def test_create_model_unknown(self, manager):
        """Test creating unknown model type."""
        with pytest.raises(ModelNotFoundError, match="Unknown model"):
            manager._create_model("unknown_model")
    
    @patch('src.services.model_manager.YOLO')
    def test_create_object_detection_model(self, mock_yolo, manager):
        """Test creating object detection model."""
        mock_model = Mock()
        mock_model.names = {"0": "person", "1": "car"}
        mock_yolo.return_value = mock_model
        
        with patch.object(settings, 'OBJECT_DETECTION_MODEL', 'yolov8n.pt'):
            model_info = manager._create_object_detection_model()
            
            assert model_info.name == "object_detection"
            assert model_info.model_type == "object_detection"
            assert model_info.model == mock_model
            assert model_info.metadata["classes"] == {"0": "person", "1": "car"}
    
    def test_create_face_detection_model_mtcnn(self, manager):
        """Test creating face detection model with MTCNN."""
        mock_mtcnn = Mock()
        
        with patch('src.services.model_manager.mtcnn') as mtcnn_module:
            mtcnn_module.MTCNN.return_value = mock_mtcnn
            
            with patch.object(settings, 'FACE_DETECTION_MODEL', 'mtcnn'):
                model_info = manager._create_face_detection_model()
                
                assert model_info.name == "face_detection"
                assert model_info.model == mock_mtcnn
                assert model_info.metadata["model_name"] == "mtcnn"
    
    @patch('src.services.model_manager.cv2')
    def test_create_face_detection_model_opencv(self, mock_cv2, manager):
        """Test creating face detection model with OpenCV fallback."""
        # Make mtcnn import fail
        with patch('src.services.model_manager.mtcnn', side_effect=ImportError):
            mock_cascade = Mock()
            mock_cv2.CascadeClassifier.return_value = mock_cascade
            mock_cv2.data.haarcascades = "/path/to/cascades/"
            
            model_info = manager._create_face_detection_model()
            
            assert model_info.name == "face_detection"
            assert model_info.model == mock_cascade
            assert model_info.metadata["type"] == "haar_cascade"
    
    def test_create_speech_to_text_model_whisper(self, manager):
        """Test creating speech-to-text model with Whisper."""
        mock_whisper_model = Mock()
        
        with patch('src.services.model_manager.whisper') as whisper_module:
            whisper_module.load_model.return_value = mock_whisper_model
            
            model_info = manager._create_speech_to_text_model()
            
            assert model_info.name == "speech_to_text"
            assert model_info.model == mock_whisper_model
            assert model_info.metadata["model_name"] == "whisper-base"
    
    def test_create_speech_to_text_model_transformers(self, manager):
        """Test creating speech-to-text model with transformers fallback."""
        # Make whisper import fail
        with patch('src.services.model_manager.whisper', side_effect=ImportError):
            mock_processor = Mock()
            mock_model = Mock()
            
            with patch('src.services.model_manager.AutoProcessor') as auto_proc:
                with patch('src.services.model_manager.AutoModelForSpeechSeq2Seq') as auto_model:
                    auto_proc.from_pretrained.return_value = mock_processor
                    auto_model.from_pretrained.return_value = mock_model
                    
                    model_info = manager._create_speech_to_text_model()
                    
                    assert model_info.name == "speech_to_text"
                    assert model_info.model == mock_model
                    assert model_info.metadata["processor"] == mock_processor
    
    def test_create_content_moderation_model(self, manager):
        """Test creating content moderation model."""
        mock_tokenizer = Mock()
        mock_model = Mock()
        
        with patch('src.services.model_manager.AutoTokenizer') as auto_tok:
            with patch('src.services.model_manager.AutoModelForSequenceClassification') as auto_model:
                auto_tok.from_pretrained.return_value = mock_tokenizer
                auto_model.from_pretrained.return_value = mock_model
                
                model_info = manager._create_content_moderation_model()
                
                assert model_info.name == "content_moderation"
                assert model_info.model == mock_model
                assert model_info.metadata["tokenizer"] == mock_tokenizer
                assert "labels" in model_info.metadata
    
    def test_create_sentiment_analysis_model(self, manager):
        """Test creating sentiment analysis model."""
        mock_tokenizer = Mock()
        mock_model = Mock()
        
        with patch('src.services.model_manager.AutoTokenizer') as auto_tok:
            with patch('src.services.model_manager.AutoModelForSequenceClassification') as auto_model:
                auto_tok.from_pretrained.return_value = mock_tokenizer
                auto_model.from_pretrained.return_value = mock_model
                
                model_info = manager._create_sentiment_analysis_model()
                
                assert model_info.name == "sentiment_analysis"
                assert model_info.model == mock_model
                assert model_info.metadata["labels"] == ["negative", "neutral", "positive"]
    
    def test_create_language_detection_model(self, manager):
        """Test creating language detection model."""
        model_info = manager._create_language_detection_model()
        
        assert model_info.name == "language_detection"
        assert model_info.model == "langdetect"
        assert len(model_info.metadata["supported_languages"]) > 50
    
    async def test_get_model(self, manager):
        """Test getting a model."""
        mock_model = Mock()
        mock_model_info = ModelInfo("test_model", "test_type", mock_model)
        
        with patch.object(manager, '_load_model', return_value=mock_model_info):
            result = await manager.get_model("test_model")
            
            assert result == mock_model_info
    
    def test_model_eviction(self, manager):
        """Test model eviction when cache is full."""
        # Set max models to 3
        with patch.object(settings, 'MAX_MODELS_IN_MEMORY', 3):
            # Add 3 models
            for i in range(3):
                model_info = ModelInfo(f"model_{i}", "test", Mock())
                manager._models[f"model_{i}"] = model_info
            
            # Add 4th model should trigger eviction
            new_model = ModelInfo("model_3", "test", Mock())
            manager._models["model_3"] = new_model
            
            manager._maybe_evict_models()
            
            # Should have only 3 models
            assert len(manager._models) == 3
            # Oldest model should be evicted
            assert "model_0" not in manager._models
            assert "model_3" in manager._models
    
    def test_unload_model(self, manager):
        """Test unloading a specific model."""
        mock_model = Mock()
        model_info = ModelInfo("test_model", "test", mock_model)
        manager._models["test_model"] = model_info
        
        manager.unload_model("test_model")
        
        assert "test_model" not in manager._models
    
    def test_unload_model_not_found(self, manager):
        """Test unloading non-existent model."""
        # Should not raise exception
        manager.unload_model("non_existent")
    
    async def test_list_models(self, manager):
        """Test listing loaded models."""
        # Add some models
        model1 = ModelInfo("model1", "type1", Mock())
        model2 = ModelInfo("model2", "type2", Mock())
        manager._models["model1"] = model1
        manager._models["model2"] = model2
        
        models = await manager.list_models()
        
        assert len(models) == 2
        assert models[0]["name"] == "model1"
        assert models[0]["type"] == "type1"
        assert models[1]["name"] == "model2"
    
    async def test_get_model_info(self, manager):
        """Test getting model information."""
        mock_model = Mock()
        model_info = ModelInfo("test_model", "test_type", mock_model, {"version": "1.0"})
        model_info.access_count = 5
        manager._models["test_model"] = model_info
        
        info = await manager.get_model_info("test_model")
        
        assert info["name"] == "test_model"
        assert info["type"] == "test_type"
        assert info["metadata"]["version"] == "1.0"
        assert info["access_count"] == 5
        assert "load_time" in info
        assert "last_access" in info
    
    async def test_get_model_info_not_found(self, manager):
        """Test getting info for non-existent model."""
        info = await manager.get_model_info("non_existent")
        assert info is None
    
    async def test_shutdown(self, manager):
        """Test manager shutdown."""
        # Add mock executor
        manager._executor = Mock()
        manager._executor.shutdown = Mock()
        
        await manager.shutdown()
        
        manager._executor.shutdown.assert_called_once_with(wait=True)
    
    def test_concurrent_model_loading(self, manager):
        """Test thread safety of model loading."""
        mock_model = Mock()
        call_count = 0
        
        def create_model_slow(name):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # Simulate slow model loading
            return ModelInfo(name, "test", mock_model)
        
        with patch.object(manager, '_create_model', side_effect=create_model_slow):
            # Load same model from multiple threads
            import threading
            results = []
            
            def load_model():
                result = manager._load_model("test_model")
                results.append(result)
            
            threads = [threading.Thread(target=load_model) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # Should only create model once
            assert call_count == 1
            # All results should be the same model
            assert all(r == results[0] for r in results)
    
    def test_model_memory_usage_tracking(self, manager):
        """Test memory usage tracking for models."""
        mock_model = Mock()
        model_info = ModelInfo("test_model", "test", mock_model)
        manager._models["test_model"] = model_info
        
        memory_stats = manager.get_memory_stats()
        
        assert "total_models" in memory_stats
        assert memory_stats["total_models"] == 1
        assert "models" in memory_stats
        assert len(memory_stats["models"]) == 1