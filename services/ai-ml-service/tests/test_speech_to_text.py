"""
Test Speech-to-Text Service

Tests for speech-to-text transcription using Whisper and other models.
"""

import pytest
import asyncio
import numpy as np
import io
import time
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from pathlib import Path
import uuid
import librosa
import torch

from src.services.speech_to_text_service import SpeechToTextService
from src.core.exceptions import InferenceError, ValidationError, ProcessingError
from src.services.model_manager import ModelInfo


class MockModelInfo:
    """Mock model info object."""
    def __init__(self, name="speech_to_text"):
        self.name = name
        self.model_type = "speech_to_text"
        self.model = Mock()
        self.metadata = {
            "version": "1.0",
            "languages": ["en", "es", "fr", "de", "it", "pt", "ja", "zh"]
        }


class TestSpeechToTextService:
    """Test cases for SpeechToTextService."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_model = AsyncMock()
        return manager
    
    @pytest.fixture
    def service(self, model_manager):
        """Create speech-to-text service instance."""
        return SpeechToTextService(model_manager)
    
    @pytest.fixture
    def sample_audio(self):
        """Create sample audio data."""
        # 1 second of audio at 16kHz
        return np.random.random(16000).astype(np.float32)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session
    
    async def test_transcribe_audio_with_numpy(self, service, model_manager, sample_audio):
        """Test audio transcription with numpy array input."""
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "This is a test transcription",
            "language": "en",
            "language_probability": 0.99,
            "duration": 1.0,
            "segments": [
                {
                    "id": 0,
                    "seek": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "text": "This is a test transcription",
                    "tokens": [1, 2, 3, 4, 5],
                    "temperature": 0.0,
                    "avg_logprob": -0.1,
                    "compression_ratio": 1.2,
                    "no_speech_prob": 0.01
                }
            ]
        })
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.transcribe_audio(
            sample_audio,
            language="en",
            return_segments=True,
            return_word_timestamps=False
        )
        
        # Assertions
        assert result["text"] == "This is a test transcription"
        assert result["language"] == "en"
        assert result["language_probability"] == 0.99
        assert result["duration"] == 1.0
        assert len(result["segments"]) == 1
        assert result["model_name"] == "speech_to_text"
        assert "processing_time" in result
    
    async def test_transcribe_audio_with_bytes(self, service, model_manager):
        """Test audio transcription with bytes input."""
        # Create audio bytes (mock WAV data)
        audio_bytes = b"RIFF" + b"\x00" * 100  # Simplified mock
        
        # Setup mocks
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Test transcription from bytes",
            "language": "en",
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        # Mock librosa.load for bytes
        with patch('librosa.load') as mock_librosa:
            mock_librosa.return_value = (np.random.random(16000).astype(np.float32), 16000)
            
            result = await service.transcribe_audio(audio_bytes)
            
            # Assertions
            assert result["text"] == "Test transcription from bytes"
            assert mock_librosa.called
    
    async def test_transcribe_audio_with_file_path(self, service, model_manager, tmp_path):
        """Test audio transcription with file path input."""
        # Create temporary audio file
        audio_file = tmp_path / "test_audio.wav"
        # Write some dummy data
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
        
        # Setup mocks
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Test transcription from file",
            "language": "en",
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        # Mock librosa.load for file
        with patch('librosa.load') as mock_librosa:
            mock_librosa.return_value = (np.random.random(16000).astype(np.float32), 16000)
            
            # Test with string path
            result = await service.transcribe_audio(str(audio_file))
            assert result["text"] == "Test transcription from file"
            
            # Test with Path object
            result = await service.transcribe_audio(audio_file)
            assert result["text"] == "Test transcription from file"
    
    async def test_transcribe_audio_with_word_timestamps(self, service, model_manager, sample_audio):
        """Test transcription with word-level timestamps."""
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Hello world",
            "language": "en",
            "segments": [
                {
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 1.0,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                        {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.98}
                    ]
                }
            ],
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.98}
            ]
        })
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.transcribe_audio(
            sample_audio,
            return_segments=True,
            return_word_timestamps=True
        )
        
        # Assertions
        assert len(result["words"]) == 2
        assert result["words"][0]["word"] == "Hello"
        assert result["segments"][0]["words"][0]["word"] == "Hello"
    
    async def test_transcribe_audio_with_options(self, service, model_manager, sample_audio):
        """Test transcription with various options."""
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Test with options",
            "language": "en",
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        # Test with custom options
        result = await service.transcribe_audio(
            sample_audio,
            language="es",
            temperature=0.5,
            beam_size=10,
            initial_prompt="Este es un test",
            fp16=False,
            compression_ratio_threshold=2.0,
            no_speech_threshold=0.8
        )
        
        # Verify options were passed
        call_args = mock_model.transcribe.call_args
        assert call_args[1]["language"] == "es"
        assert call_args[1]["temperature"] == 0.5
        assert call_args[1]["beam_size"] == 10
        assert call_args[1]["initial_prompt"] == "Este es un test"
    
    async def test_transcribe_audio_with_database_logging(self, service, model_manager, sample_audio, mock_db_session):
        """Test transcription with database logging."""
        asset_id = str(uuid.uuid4())
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Test with logging",
            "language": "en",
            "language_probability": 0.99,
            "duration": 1.0,
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        with patch('src.services.speech_to_text_service.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            result = await service.transcribe_audio(sample_audio, asset_id=asset_id)
            
            # Verify database operations
            assert mock_db_session.add.call_count >= 2  # Job and result
            assert mock_db_session.commit.called
    
    async def test_transcribe_video(self, service, model_manager, tmp_path):
        """Test video transcription."""
        # Create temporary video file
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake_video_data")
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Video transcription",
            "language": "en",
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        # Mock audio extraction
        with patch.object(service, '_extract_audio_from_video', new_callable=AsyncMock) as mock_extract:
            audio_file = tmp_path / "extracted_audio.wav"
            audio_file.write_bytes(b"fake_audio_data")
            mock_extract.return_value = str(audio_file)
            
            # Mock librosa for extracted audio
            with patch('librosa.load') as mock_librosa:
                mock_librosa.return_value = (np.random.random(16000).astype(np.float32), 16000)
                
                result = await service.transcribe_video(video_file, extract_audio=True)
                
                # Assertions
                assert result["text"] == "Video transcription"
                assert result["video_path"] == str(video_file)
                assert result["extracted_audio"] is True
                assert "total_processing_time" in result
                mock_extract.assert_called_once()
    
    async def test_transcribe_video_without_extraction(self, service, model_manager, tmp_path):
        """Test video transcription without audio extraction."""
        # Create temporary file
        video_file = tmp_path / "test_video.wav"
        video_file.write_bytes(b"fake_audio_data")
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={
            "text": "Direct audio transcription",
            "language": "en",
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        with patch('librosa.load') as mock_librosa:
            mock_librosa.return_value = (np.random.random(16000).astype(np.float32), 16000)
            
            result = await service.transcribe_video(video_file, extract_audio=False)
            
            assert result["text"] == "Direct audio transcription"
            assert result["extracted_audio"] is False
    
    async def test_transcribe_batch(self, service, model_manager):
        """Test batch transcription."""
        # Create batch of audio data
        audio_batch = [
            np.random.random(16000).astype(np.float32),
            np.random.random(16000).astype(np.float32),
            np.random.random(16000).astype(np.float32)
        ]
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        transcription_results = [
            {"text": "First audio", "language": "en", "segments": []},
            {"text": "Second audio", "language": "en", "segments": []},
            {"text": "Third audio", "language": "en", "segments": []}
        ]
        mock_model.transcribe = Mock(side_effect=transcription_results)
        model_manager.get_model.return_value = model_info
        
        # Test
        results = await service.transcribe_batch(audio_batch)
        
        # Assertions
        assert len(results) == 3
        assert results[0]["text"] == "First audio"
        assert results[1]["text"] == "Second audio"
        assert results[2]["text"] == "Third audio"
    
    async def test_transcribe_batch_with_failures(self, service, model_manager):
        """Test batch transcription with some failures."""
        # Create batch
        audio_batch = [
            np.random.random(16000).astype(np.float32),
            b"invalid_audio_data",  # This should fail
            np.random.random(16000).astype(np.float32)
        ]
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(return_value={"text": "Success", "language": "en", "segments": []})
        model_manager.get_model.return_value = model_info
        
        # Mock librosa to fail for bytes
        with patch('librosa.load') as mock_librosa:
            def side_effect(data, sr=None):
                if isinstance(data, io.BytesIO):
                    raise Exception("Invalid audio format")
                return np.random.random(16000).astype(np.float32), 16000
            
            mock_librosa.side_effect = side_effect
            
            results = await service.transcribe_batch(audio_batch)
            
            # Assertions
            assert len(results) == 3
            assert results[0] is not None
            assert results[1] is None  # Failed
            assert results[2] is not None
    
    async def test_transformers_model_inference(self, service, model_manager, sample_audio):
        """Test inference with transformers model."""
        # Setup mock for transformers model
        model_info = MockModelInfo()
        mock_model = Mock()
        mock_model.__class__.__name__ = "WhisperForConditionalGeneration"
        mock_model.transcribe = None  # No transcribe method
        
        # Mock processor
        mock_processor = Mock()
        mock_processor.return_value = {"input_features": torch.randn(1, 80, 3000)}
        mock_processor.batch_decode = Mock(return_value=["Transformers transcription"])
        mock_model.processor = mock_processor
        
        # Mock generate
        mock_model.generate = Mock(return_value=torch.tensor([[1, 2, 3, 4]]))
        
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.transcribe_audio(sample_audio)
        
        # Assertions
        assert result["text"] == "Transformers transcription"
        mock_processor.batch_decode.assert_called_once()
    
    async def test_extract_audio_from_video(self, service, tmp_path):
        """Test audio extraction from video."""
        # Create temporary video file
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake_video_data")
        
        # Mock subprocess
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            audio_path = await service._extract_audio_from_video(video_file)
            
            # Assertions
            assert audio_path.endswith(".wav")
            mock_run.assert_called_once()
            
            # Check ffmpeg command
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "ffmpeg"
            assert str(video_file) in call_args
            assert "-ar" in call_args
            assert "16000" in call_args
    
    async def test_extract_audio_from_video_failure(self, service, tmp_path):
        """Test audio extraction failure."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake_video_data")
        
        # Mock subprocess failure
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "FFmpeg error"
            mock_run.return_value = mock_result
            
            with pytest.raises(ProcessingError, match="FFmpeg failed"):
                await service._extract_audio_from_video(video_file)
    
    async def test_get_supported_languages(self, service, model_manager):
        """Test getting supported languages."""
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        languages = await service.get_supported_languages()
        
        # Assertions
        assert len(languages) > 0
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
    
    async def test_get_supported_languages_default(self, service, model_manager):
        """Test getting default languages when not specified."""
        # Setup mock without languages in metadata
        model_info = MockModelInfo()
        model_info.metadata = {"version": "1.0"}
        model_manager.get_model.return_value = model_info
        
        languages = await service.get_supported_languages()
        
        # Should return default Whisper languages
        assert len(languages) >= 20
        assert "en" in languages
    
    async def test_get_model_info(self, service, model_manager):
        """Test getting model information."""
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        info = await service.get_model_info()
        
        # Assertions
        assert info["name"] == "speech_to_text"
        assert info["type"] == "speech_to_text"
        assert "metadata" in info
        assert len(info["supported_languages"]) > 0
    
    async def test_detect_language(self, service, model_manager, sample_audio):
        """Test language detection."""
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.detect_language = Mock(return_value={
            "en": 0.95,
            "es": 0.03,
            "fr": 0.02
        })
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.detect_language(sample_audio, duration=10.0)
        
        # Assertions
        assert result["language"] == "en"
        assert result["confidence"] == 0.95
        assert "all_probabilities" in result
        assert result["duration_analyzed"] == 10.0
    
    async def test_detect_language_fallback(self, service, model_manager, sample_audio):
        """Test language detection fallback when model doesn't support it."""
        # Setup mock without detect_language method
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.detect_language = None
        mock_model.transcribe = Mock(return_value={
            "text": "Test",
            "language": "en",
            "language_probability": 0.99,
            "segments": []
        })
        model_manager.get_model.return_value = model_info
        
        # Test
        result = await service.detect_language(sample_audio)
        
        # Assertions
        assert result["language"] == "en"
        assert result["confidence"] == 0.99
        mock_model.transcribe.assert_called_once()
    
    async def test_invalid_audio_data_type(self, service):
        """Test with invalid audio data type."""
        with pytest.raises(ValidationError, match="Unsupported audio data type"):
            await service.transcribe_audio({"invalid": "data"})
    
    async def test_error_handling(self, service, model_manager, sample_audio):
        """Test error handling in transcription."""
        # Model loading error
        model_manager.get_model.side_effect = Exception("Model load failed")
        
        with pytest.raises(InferenceError, match="Speech-to-text transcription failed"):
            await service.transcribe_audio(sample_audio)
        
        # Reset and test inference error
        model_manager.get_model.side_effect = None
        model_info = MockModelInfo()
        mock_model = model_info.model
        mock_model.transcribe = Mock(side_effect=Exception("Inference failed"))
        model_manager.get_model.return_value = model_info
        
        with pytest.raises(InferenceError):
            await service.transcribe_audio(sample_audio)
    
    async def test_concurrent_transcriptions(self, service, model_manager):
        """Test concurrent transcription requests."""
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        call_count = 0
        
        def transcribe_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "text": f"Transcription {call_count}",
                "language": "en",
                "segments": []
            }
        
        mock_model.transcribe = Mock(side_effect=transcribe_side_effect)
        model_manager.get_model.return_value = model_info
        
        # Create concurrent tasks
        audio_samples = [np.random.random(16000).astype(np.float32) for _ in range(5)]
        tasks = [service.transcribe_audio(audio) for audio in audio_samples]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Assertions
        assert len(results) == 5
        assert call_count == 5
        for i, result in enumerate(results):
            assert "Transcription" in result["text"]
    
    async def test_audio_duration_limiting(self, service, model_manager):
        """Test audio duration limiting for language detection."""
        # Create long audio (60 seconds)
        long_audio = np.random.random(60 * 16000).astype(np.float32)
        
        # Setup mock
        model_info = MockModelInfo()
        mock_model = model_info.model
        
        # Track the audio length passed to detect_language
        detected_audio_length = None
        
        def detect_language_side_effect(audio):
            nonlocal detected_audio_length
            detected_audio_length = len(audio)
            return {"en": 0.99}
        
        mock_model.detect_language = Mock(side_effect=detect_language_side_effect)
        model_manager.get_model.return_value = model_info
        
        # Test with 30 second limit
        await service.detect_language(long_audio, duration=30.0)
        
        # Should have limited to 30 seconds (30 * 16000 samples)
        assert detected_audio_length == 30 * 16000