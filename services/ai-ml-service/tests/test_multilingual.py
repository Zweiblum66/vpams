"""
Tests for multi-language support functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.services.ml_service import MLService
from src.services.model_manager import ModelManager, ModelInfo
from src.core.exceptions import ValidationError, InferenceError


class TestMultilingualSupport:
    """Test multi-language support functionality."""
    
    @pytest.fixture
    def model_manager(self):
        """Create a mock model manager."""
        manager = Mock(spec=ModelManager)
        return manager
    
    @pytest.fixture
    def ml_service(self, model_manager):
        """Create ML service with mocked model manager."""
        service = MLService(model_manager)
        service.logger = Mock()
        service._processing_semaphore = AsyncMock()
        service._processing_semaphore.__aenter__ = AsyncMock(return_value=None)
        service._processing_semaphore.__aexit__ = AsyncMock(return_value=None)
        return service
    
    @pytest.fixture
    def mock_language_detection_model(self):
        """Create mock model info for language detection."""
        model = "langdetect"
        
        model_info = ModelInfo(
            name="language_detection",
            model_type="language_detection",
            model=model,
            metadata={
                "model_name": "langdetect",
                "input_format": "text",
                "output_format": "language_probabilities",
                "supported_languages": ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"]
            }
        )
        
        return model_info
    
    @pytest.mark.asyncio
    async def test_detect_language_english(self, ml_service, model_manager, mock_language_detection_model):
        """Test language detection with English text."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock langdetect
        with patch('src.services.ml_service.detect_langs') as mock_detect:
            mock_lang = Mock()
            mock_lang.lang = "en"
            mock_lang.prob = 0.95
            mock_detect.return_value = [mock_lang]
            
            # Test data
            test_text = "This is a test message in English language."
            
            # Execute
            result = await ml_service.detect_language(test_text)
            
            # Verify
            assert result["detected_language"] == "en"
            assert result["language_name"] == "English"
            assert result["confidence"] == 0.95
            assert result["confidence_level"] == "high"
            assert result["is_reliable"] == True
            assert result["text_length"] == len(test_text)
            
            # Verify detailed scores
            assert len(result["language_scores"]) == 1
            assert result["language_scores"][0]["language"] == "en"
            assert result["language_scores"][0]["confidence"] == 0.95
            assert result["language_scores"][0]["is_confident"] == True
    
    @pytest.mark.asyncio
    async def test_detect_language_spanish(self, ml_service, model_manager, mock_language_detection_model):
        """Test language detection with Spanish text."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock langdetect
        with patch('src.services.ml_service.detect_langs') as mock_detect:
            mock_lang = Mock()
            mock_lang.lang = "es"
            mock_lang.prob = 0.87
            mock_detect.return_value = [mock_lang]
            
            # Test data
            test_text = "Este es un mensaje de prueba en español."
            
            # Execute
            result = await ml_service.detect_language(test_text)
            
            # Verify
            assert result["detected_language"] == "es"
            assert result["language_name"] == "Spanish"
            assert result["confidence"] == 0.87
            assert result["confidence_level"] == "high"
            assert result["is_reliable"] == True
    
    @pytest.mark.asyncio
    async def test_detect_language_multiple_candidates(self, ml_service, model_manager, mock_language_detection_model):
        """Test language detection with multiple language candidates."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock langdetect
        with patch('src.services.ml_service.detect_langs') as mock_detect:
            mock_lang1 = Mock()
            mock_lang1.lang = "en"
            mock_lang1.prob = 0.65
            
            mock_lang2 = Mock()
            mock_lang2.lang = "fr"
            mock_lang2.prob = 0.35
            
            mock_detect.return_value = [mock_lang1, mock_lang2]
            
            # Test data
            test_text = "This could be English or French text."
            
            # Execute
            result = await ml_service.detect_language(test_text)
            
            # Verify
            assert result["detected_language"] == "en"  # Higher confidence
            assert result["confidence"] == 0.65
            assert result["confidence_level"] == "medium"
            assert len(result["language_scores"]) == 2
            
            # Check both languages are present
            languages = [score["language"] for score in result["language_scores"]]
            assert "en" in languages
            assert "fr" in languages
    
    @pytest.mark.asyncio
    async def test_detect_language_fallback_method(self, ml_service, model_manager, mock_language_detection_model):
        """Test language detection fallback method when langdetect fails."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock langdetect to raise ImportError
        with patch('src.services.ml_service.detect_langs', side_effect=ImportError("langdetect not available")):
            # Test data with Chinese characters
            test_text = "这是中文测试文本"
            
            # Execute
            result = await ml_service.detect_language(test_text)
            
            # Verify fallback was used
            assert result["detected_language"] == "zh"
            assert result["language_name"] == "Chinese"
            assert result["model_name"] == "heuristic"
            assert result["confidence"] == 0.7
    
    @pytest.mark.asyncio
    async def test_detect_language_validation_error(self, ml_service):
        """Test language detection with invalid input."""
        # Test empty text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.detect_language("")
        
        # Test None text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.detect_language(None)
        
        # Test non-string text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.detect_language(123)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_multilingual_whisper(self, ml_service, model_manager):
        """Test multilingual transcription with Whisper model."""
        # Setup mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Hello, this is a test.",
            "language": "en",
            "language_probability": 0.95,
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Hello, this is a test."
                }
            ]
        }
        
        model_info = ModelInfo(
            name="speech_to_text",
            model_type="speech_to_text",
            model=mock_model,
            metadata={
                "model_name": "whisper-base",
                "input_format": "audio",
                "output_format": "text"
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        # Execute
        result = await ml_service.transcribe_audio_multilingual(test_audio, auto_detect_language=True)
        
        # Verify
        assert result["text"] == "Hello, this is a test."
        assert result["language"] == "en"
        assert result["language_probability"] == 0.95
        assert result["auto_detected"] == True
        assert result["supports_multilingual"] == True
        assert len(result["segments"]) == 1
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_multilingual_non_whisper(self, ml_service, model_manager):
        """Test multilingual transcription with non-Whisper model."""
        # Setup mock non-Whisper model
        mock_model = Mock()
        mock_tokenizer = Mock()
        mock_processor = Mock()
        mock_processor.return_value = {"input_features": Mock()}
        mock_model.generate.return_value = [Mock()]
        mock_processor.batch_decode.return_value = ["This is a test transcription."]
        
        model_info = ModelInfo(
            name="speech_to_text",
            model_type="speech_to_text",
            model=mock_model,
            metadata={
                "model_name": "some-other-model",
                "processor": mock_processor
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock language detection for post-processing
        with patch.object(ml_service, 'detect_language') as mock_detect:
            mock_detect.return_value = {
                "detected_language": "en",
                "confidence": 0.8
            }
            
            # Test data
            test_audio = np.random.random(16000).astype(np.float32)
            
            # Execute
            result = await ml_service.transcribe_audio_multilingual(
                test_audio, 
                auto_detect_language=True
            )
            
            # Verify
            assert result["text"] == "This is a test transcription."
            assert result["language"] == "en"
            assert result["language_probability"] == 0.8
            assert result["auto_detected"] == True
            assert result["supports_multilingual"] == False
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_multilingual_specified_language(self, ml_service, model_manager):
        """Test multilingual transcription with specified language."""
        # Setup mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Bonjour, ceci est un test.",
            "language": "fr",
            "language_probability": 0.92,
            "segments": []
        }
        
        model_info = ModelInfo(
            name="speech_to_text",
            model_type="speech_to_text",
            model=mock_model,
            metadata={
                "model_name": "whisper-base"
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        # Execute
        result = await ml_service.transcribe_audio_multilingual(
            test_audio, 
            language="fr",
            auto_detect_language=False
        )
        
        # Verify
        assert result["text"] == "Bonjour, ceci est un test."
        assert result["language"] == "fr"
        assert result["auto_detected"] == False
        assert result["supports_multilingual"] == True
    
    @pytest.mark.asyncio
    async def test_fallback_language_detection_character_heuristics(self, ml_service):
        """Test fallback language detection using character heuristics."""
        test_cases = [
            ("Hello world", "en", 0.5),
            ("这是中文测试", "zh", 0.7),
            ("これは日本語のテストです", "ja", 0.7),
            ("안녕하세요 한국어 테스트", "ko", 0.7),
            ("Привет мир", "ru", 0.6),
            ("مرحبا بالعالم", "ar", 0.6),
            ("", "en", 0.1),  # Empty text defaults to English
        ]
        
        for text, expected_lang, expected_confidence in test_cases:
            result = await ml_service._fallback_language_detection(text)
            
            assert result["detected_language"] == expected_lang
            assert abs(result["confidence"] - expected_confidence) < 0.1
            assert result["model_name"] == "heuristic"
    
    @pytest.mark.asyncio
    async def test_language_detection_cached_result(self, ml_service, model_manager):
        """Test language detection with cached result."""
        # Setup
        cached_result = {
            "detected_language": "en",
            "language_name": "English",
            "confidence": 0.95,
            "confidence_level": "high",
            "language_scores": [{"language": "en", "confidence": 0.95}],
            "threshold": 0.5,
            "model_name": "language_detection",
            "text_length": 25,
            "is_reliable": True
        }
        
        ml_service._get_cached_result = AsyncMock(return_value=cached_result)
        
        # Test data
        test_text = "This is a test message."
        
        # Execute
        result = await ml_service.detect_language(test_text)
        
        # Verify
        assert result == cached_result
        # Model should not be loaded when using cached result
        model_manager.get_model.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_confidence_level_classification(self, ml_service, model_manager, mock_language_detection_model):
        """Test confidence level classification."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        test_cases = [
            (0.9, "high"),
            (0.8, "high"),
            (0.7, "medium"),
            (0.6, "medium"),
            (0.5, "low"),
            (0.3, "low")
        ]
        
        for confidence, expected_level in test_cases:
            with patch('src.services.ml_service.detect_langs') as mock_detect:
                mock_lang = Mock()
                mock_lang.lang = "en"
                mock_lang.prob = confidence
                mock_detect.return_value = [mock_lang]
                
                result = await ml_service.detect_language("test text")
                
                assert result["confidence_level"] == expected_level
                assert result["confidence"] == confidence
    
    @pytest.mark.asyncio
    async def test_language_detection_threshold(self, ml_service, model_manager, mock_language_detection_model):
        """Test language detection threshold functionality."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_language_detection_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        with patch('src.services.ml_service.detect_langs') as mock_detect:
            mock_lang1 = Mock()
            mock_lang1.lang = "en"
            mock_lang1.prob = 0.7
            
            mock_lang2 = Mock()
            mock_lang2.lang = "fr"
            mock_lang2.prob = 0.3
            
            mock_detect.return_value = [mock_lang1, mock_lang2]
            
            # Test with high threshold
            result = await ml_service.detect_language("test text", confidence_threshold=0.8)
            
            # Verify
            assert result["threshold"] == 0.8
            assert result["language_scores"][0]["is_confident"] == False  # 0.7 < 0.8
            assert result["language_scores"][1]["is_confident"] == False  # 0.3 < 0.8
            assert result["is_reliable"] == False  # Max confidence (0.7) < threshold (0.8)
            
            # Test with low threshold
            result = await ml_service.detect_language("test text", confidence_threshold=0.5)
            
            # Verify
            assert result["threshold"] == 0.5
            assert result["language_scores"][0]["is_confident"] == True  # 0.7 >= 0.5
            assert result["language_scores"][1]["is_confident"] == False  # 0.3 < 0.5
            assert result["is_reliable"] == True  # Max confidence (0.7) >= threshold (0.5)