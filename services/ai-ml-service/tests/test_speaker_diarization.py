"""
Tests for speaker diarization functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.services.ml_service import MLService
from src.services.model_manager import ModelManager, ModelInfo
from src.core.exceptions import ValidationError, InferenceError


class TestSpeakerDiarization:
    """Test speaker diarization functionality."""
    
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
    def mock_pyannote_model(self):
        """Create mock model info for pyannote speaker diarization."""
        # Mock pyannote pipeline
        mock_pipeline = Mock()
        mock_pipeline.return_value = Mock()
        
        model_info = ModelInfo(
            name="speaker_diarization",
            model_type="speaker_diarization",
            model=mock_pipeline,
            metadata={
                "model_name": "pyannote/speaker-diarization",
                "input_format": "audio",
                "output_format": "speaker_segments",
                "type": "pyannote",
                "min_speakers": 1,
                "max_speakers": 20
            }
        )
        
        return model_info
    
    @pytest.fixture
    def mock_energy_model(self):
        """Create mock model info for energy-based speaker diarization."""
        model_info = ModelInfo(
            name="speaker_diarization",
            model_type="speaker_diarization",
            model="energy_based",
            metadata={
                "model_name": "energy_based_diarization",
                "input_format": "audio",
                "output_format": "speaker_segments",
                "type": "energy_based",
                "min_speakers": 1,
                "max_speakers": 10
            }
        )
        
        return model_info
    
    @pytest.mark.asyncio
    async def test_diarize_speakers_pyannote(self, ml_service, model_manager, mock_pyannote_model):
        """Test speaker diarization with pyannote.audio."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_pyannote_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock pyannote pipeline output
        mock_annotation = Mock()
        mock_annotation.labels.return_value = ["SPEAKER_00", "SPEAKER_01"]
        mock_annotation.get_timeline.return_value = [
            Mock(start=0.0, end=5.0),
            Mock(start=5.0, end=10.0)
        ]
        
        # Mock segment iteration
        mock_segments = [
            Mock(start=0.0, end=5.0),
            Mock(start=5.0, end=10.0)
        ]
        mock_annotation.__iter__ = Mock(return_value=iter(mock_segments))
        
        # Mock annotation access
        def mock_getitem(segment):
            if segment.start == 0.0:
                return "SPEAKER_00"
            else:
                return "SPEAKER_01"
        
        mock_annotation.__getitem__ = Mock(side_effect=mock_getitem)
        
        # Mock pipeline call
        mock_pyannote_model.model.return_value = mock_annotation
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        # Mock librosa.load for file path handling
        with patch('librosa.load') as mock_load:
            mock_load.return_value = (test_audio, 16000)
            
            # Execute
            result = await ml_service.diarize_speakers(
                audio_data=test_audio,
                num_speakers=2,
                min_speakers=1,
                max_speakers=10
            )
            
            # Verify
            assert result["num_speakers"] == 2
            assert result["model_name"] == "pyannote/speaker-diarization"
            assert result["model_type"] == "pyannote"
            assert len(result["speakers"]) == 2
            assert result["speakers"]["SPEAKER_00"]["label"] == "SPEAKER_00"
            assert result["speakers"]["SPEAKER_01"]["label"] == "SPEAKER_01"
            assert len(result["segments"]) == 2
            assert result["segments"][0]["speaker"] == "SPEAKER_00"
            assert result["segments"][1]["speaker"] == "SPEAKER_01"
    
    @pytest.mark.asyncio
    async def test_diarize_speakers_energy_based(self, ml_service, model_manager, mock_energy_model):
        """Test speaker diarization with energy-based fallback."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_energy_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data - create audio with clear energy patterns
        test_audio = np.concatenate([
            np.random.random(8000) * 0.8,  # High energy - Speaker 1
            np.random.random(8000) * 0.1,  # Low energy - Silence
            np.random.random(8000) * 0.7,  # High energy - Speaker 2
        ]).astype(np.float32)
        
        # Execute
        result = await ml_service.diarize_speakers(
            audio_data=test_audio,
            num_speakers=2,
            min_speakers=1,
            max_speakers=10
        )
        
        # Verify
        assert result["num_speakers"] >= 1
        assert result["model_name"] == "energy_based_diarization"
        assert result["model_type"] == "energy_based"
        assert "speakers" in result
        assert "segments" in result
        assert len(result["segments"]) > 0
        
        # Verify segment structure
        for segment in result["segments"]:
            assert "start" in segment
            assert "end" in segment
            assert "speaker" in segment
            assert "confidence" in segment
            assert segment["start"] >= 0
            assert segment["end"] > segment["start"]
            assert 0 <= segment["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_diarize_speakers_automatic_detection(self, ml_service, model_manager, mock_pyannote_model):
        """Test speaker diarization with automatic speaker count detection."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_pyannote_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Mock pyannote pipeline output with 3 speakers
        mock_annotation = Mock()
        mock_annotation.labels.return_value = ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]
        
        mock_segments = [
            Mock(start=0.0, end=3.0),
            Mock(start=3.0, end=6.0),
            Mock(start=6.0, end=9.0)
        ]
        mock_annotation.__iter__ = Mock(return_value=iter(mock_segments))
        
        def mock_getitem(segment):
            if segment.start == 0.0:
                return "SPEAKER_00"
            elif segment.start == 3.0:
                return "SPEAKER_01"
            else:
                return "SPEAKER_02"
        
        mock_annotation.__getitem__ = Mock(side_effect=mock_getitem)
        mock_pyannote_model.model.return_value = mock_annotation
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        with patch('librosa.load') as mock_load:
            mock_load.return_value = (test_audio, 16000)
            
            # Execute without specifying num_speakers
            result = await ml_service.diarize_speakers(
                audio_data=test_audio,
                num_speakers=None,
                min_speakers=1,
                max_speakers=10
            )
            
            # Verify
            assert result["num_speakers"] == 3
            assert len(result["speakers"]) == 3
            assert len(result["segments"]) == 3
            assert result["auto_detected_speakers"] == True
    
    @pytest.mark.asyncio
    async def test_transcribe_with_speakers(self, ml_service, model_manager):
        """Test combined transcription and speaker diarization."""
        # Setup mock STT model
        mock_stt_model = Mock()
        mock_stt_model.transcribe.return_value = {
            "text": "Hello world. How are you?",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello world."},
                {"start": 2.0, "end": 4.0, "text": "How are you?"}
            ]
        }
        
        stt_model_info = ModelInfo(
            name="speech_to_text",
            model_type="speech_to_text",
            model=mock_stt_model,
            metadata={"model_name": "whisper-base"}
        )
        
        # Setup mock speaker diarization
        mock_diarization_model = Mock()
        diarization_model_info = ModelInfo(
            name="speaker_diarization",
            model_type="speaker_diarization",
            model="energy_based",
            metadata={"model_name": "energy_based_diarization"}
        )
        
        # Mock get_model to return appropriate models
        async def mock_get_model(model_name):
            if model_name == "speech_to_text":
                return stt_model_info
            elif model_name == "speaker_diarization":
                return diarization_model_info
            else:
                raise ValueError(f"Unknown model: {model_name}")
        
        model_manager.get_model = AsyncMock(side_effect=mock_get_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        # Execute
        result = await ml_service.transcribe_with_speakers(
            audio_data=test_audio,
            language="en",
            num_speakers=2,
            min_speakers=1,
            max_speakers=10
        )
        
        # Verify
        assert result["text"] == "Hello world. How are you?"
        assert "transcription" in result
        assert "diarization" in result
        assert "combined_segments" in result
        assert result["transcription"]["text"] == "Hello world. How are you?"
        assert result["diarization"]["num_speakers"] >= 1
        assert len(result["combined_segments"]) > 0
        
        # Verify combined segments have both text and speaker info
        for segment in result["combined_segments"]:
            assert "start" in segment
            assert "end" in segment
            assert "text" in segment
            assert "speaker" in segment
    
    @pytest.mark.asyncio
    async def test_diarize_speakers_validation_errors(self, ml_service):
        """Test speaker diarization with invalid input."""
        # Test invalid audio data
        with pytest.raises(ValidationError, match="Audio data is required"):
            await ml_service.diarize_speakers(None)
        
        with pytest.raises(ValidationError, match="Audio data is required"):
            await ml_service.diarize_speakers("")
        
        # Test invalid speaker counts
        test_audio = np.random.random(16000).astype(np.float32)
        
        with pytest.raises(ValidationError, match="Number of speakers must be positive"):
            await ml_service.diarize_speakers(test_audio, num_speakers=0)
        
        with pytest.raises(ValidationError, match="Number of speakers must be positive"):
            await ml_service.diarize_speakers(test_audio, num_speakers=-1)
        
        with pytest.raises(ValidationError, match="Minimum speakers must be positive"):
            await ml_service.diarize_speakers(test_audio, min_speakers=0)
        
        with pytest.raises(ValidationError, match="Maximum speakers must be positive"):
            await ml_service.diarize_speakers(test_audio, max_speakers=0)
        
        with pytest.raises(ValidationError, match="Minimum speakers cannot be greater than maximum"):
            await ml_service.diarize_speakers(test_audio, min_speakers=5, max_speakers=3)
    
    @pytest.mark.asyncio
    async def test_diarize_speakers_cached_result(self, ml_service, model_manager):
        """Test speaker diarization with cached result."""
        # Setup
        cached_result = {
            "num_speakers": 2,
            "model_name": "pyannote/speaker-diarization",
            "model_type": "pyannote",
            "speakers": {
                "SPEAKER_00": {"label": "SPEAKER_00", "total_duration": 5.0},
                "SPEAKER_01": {"label": "SPEAKER_01", "total_duration": 5.0}
            },
            "segments": [
                {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00", "confidence": 0.95},
                {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01", "confidence": 0.92}
            ],
            "total_duration": 10.0,
            "auto_detected_speakers": False
        }
        
        ml_service._get_cached_result = AsyncMock(return_value=cached_result)
        
        # Test data
        test_audio = np.random.random(16000).astype(np.float32)
        
        # Execute
        result = await ml_service.diarize_speakers(test_audio, num_speakers=2)
        
        # Verify
        assert result == cached_result
        # Model should not be loaded when using cached result
        model_manager.get_model.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_energy_based_speaker_detection(self, ml_service):
        """Test energy-based speaker detection algorithm."""
        # Create test audio with distinct energy patterns
        # High energy segment (Speaker 1)
        high_energy = np.random.random(8000) * 0.8
        # Low energy segment (Silence)
        silence = np.random.random(4000) * 0.05
        # Medium energy segment (Speaker 2)
        medium_energy = np.random.random(8000) * 0.6
        
        test_audio = np.concatenate([high_energy, silence, medium_energy]).astype(np.float32)
        
        # Test the energy-based detection method directly
        result = await ml_service._energy_based_speaker_diarization(
            audio_data=test_audio,
            num_speakers=2,
            min_speakers=1,
            max_speakers=10
        )
        
        # Verify
        assert result["num_speakers"] >= 1
        assert result["model_name"] == "energy_based_diarization"
        assert result["model_type"] == "energy_based"
        assert "speakers" in result
        assert "segments" in result
        assert len(result["segments"]) > 0
        
        # Verify energy-based segments make sense
        total_duration = len(test_audio) / 16000  # Assuming 16kHz sample rate
        assert result["total_duration"] == pytest.approx(total_duration, rel=1e-2)
        
        # Verify segments don't overlap and cover the audio
        segments = result["segments"]
        for i in range(len(segments) - 1):
            assert segments[i]["end"] <= segments[i + 1]["start"]
    
    @pytest.mark.asyncio
    async def test_speaker_diarization_with_short_audio(self, ml_service, model_manager, mock_energy_model):
        """Test speaker diarization with very short audio."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_energy_model)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data - very short audio (0.5 seconds)
        test_audio = np.random.random(8000).astype(np.float32)
        
        # Execute
        result = await ml_service.diarize_speakers(
            audio_data=test_audio,
            num_speakers=None,
            min_speakers=1,
            max_speakers=10
        )
        
        # Verify
        assert result["num_speakers"] >= 1
        assert result["total_duration"] == pytest.approx(0.5, rel=1e-2)
        assert len(result["segments"]) >= 1
        
        # For very short audio, should have at least one segment
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] > 0.0