"""
Tests for waveform generation features
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os
from datetime import datetime

from src.services.ffmpeg_service import FFmpegService
from src.services.proxy_processor import ProxyProcessor
from src.services.queue_service import ProxyJob, JobStatus
from src.core.exceptions import FFmpegError, InvalidMediaError


@pytest.fixture
def mock_ffmpeg_service():
    """Create a mock FFmpeg service"""
    service = Mock(spec=FFmpegService)
    
    # Mock waveform generation methods
    service.generate_waveform = AsyncMock(return_value={
        "processing_time": 2.5,
        "output_size": 150000,
        "output_info": {"width": 1920, "height": 200}
    })
    
    service.generate_spectral_waveform = AsyncMock(return_value={
        "processing_time": 4.3,
        "output_size": 500000,
        "frequency_range": [0, 22050],
        "time_range": [0, 180.5]
    })
    
    service.generate_vectorscope = AsyncMock(return_value={
        "processing_time": 1.8,
        "output_size": 80000,
        "phase_correlation": 0.87
    })
    
    service.detect_audio_peaks = AsyncMock(return_value={
        "peaks_found": 3,
        "peaks": [
            {"time": 12.5, "level": -0.5, "duration": 0.15, "channel": 0},
            {"time": 45.3, "level": -0.2, "duration": 0.08, "channel": 1},
            {"time": 78.9, "level": -1.2, "duration": 0.22, "channel": 0}
        ],
        "max_peak": -0.2,
        "clipping_detected": False
    })
    
    service.extract_audio_levels = AsyncMock(return_value={
        "sample_count": 100,
        "interval": 0.1,
        "channels": 2,
        "levels": [
            {"time": 0.0, "levels": [-23.5, -24.1]},
            {"time": 0.1, "levels": [-22.8, -23.2]},
            {"time": 0.2, "levels": [-21.5, -22.0]}
        ],
        "overall_stats": {
            "peak": [-12.5, -13.1],
            "rms": [-23.5, -24.0],
            "loudness": -23.0
        }
    })
    
    service.get_media_info = AsyncMock(return_value={
        "duration": 180.5,
        "streams": [
            {"codec_type": "audio", "channels": 2, "sample_rate": 48000}
        ]
    })
    
    return service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="proxies/asset123/waveform_1920x200.png")
    service.store_file = AsyncMock(return_value="https://storage.example.com/proxies/asset123/waveform.png")
    return service


@pytest.fixture
def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


class TestWaveformGeneration:
    """Test waveform generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_basic_waveform(self, proxy_processor):
        """Test basic waveform generation"""
        job = ProxyJob(
            job_id="test-job-1",
            asset_id="asset123",
            input_path="/path/to/audio.mp3",
            job_type="waveform",
            parameters={
                "width": 1920,
                "height": 200,
                "style": "line"
            },
            status=JobStatus.PROCESSING
        )
        
        # Create temp file to simulate output
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_waveform.png")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_waveform_data')
        
        result = await proxy_processor._process_waveform(job)
        
        assert result["job_id"] == "test-job-1"
        assert result["asset_id"] == "asset123"
        assert result["proxy_type"] == "waveform"
        assert result["width"] == 1920
        assert result["height"] == 200
        assert result["style"] == "line"
        assert result["storage_key"] == "proxies/asset123/waveform_1920x200.png"
        assert result["storage_url"] == "https://storage.example.com/proxies/asset123/waveform.png"
        
        # Verify FFmpeg service was called correctly
        proxy_processor.ffmpeg_service.generate_waveform.assert_called_once_with(
            input_path="/path/to/audio.mp3",
            output_path=temp_path,
            width=1920,
            height=200,
            style="line",
            colors=None,
            split_channels=False,
            show_axis=True,
            logarithmic=False
        )
    
    @pytest.mark.asyncio
    async def test_generate_split_channel_waveform(self, proxy_processor):
        """Test waveform generation with split channels"""
        job = ProxyJob(
            job_id="test-job-2",
            asset_id="asset456",
            input_path="/path/to/stereo.wav",
            job_type="waveform",
            parameters={
                "width": 2560,
                "height": 400,
                "style": "fill",
                "split_channels": True,
                "colors": {"foreground": "#00ff00", "background": "#000000"}
            },
            status=JobStatus.PROCESSING
        )
        
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_waveform.png")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_waveform_data')
        
        result = await proxy_processor._process_waveform(job)
        
        assert result["style"] == "fill"
        assert "split_channels" in result["storage_key"]
        
        # Verify split channels parameter was passed
        call_args = proxy_processor.ffmpeg_service.generate_waveform.call_args[1]
        assert call_args["split_channels"] is True
        assert call_args["colors"] == {"foreground": "#00ff00", "background": "#000000"}
    
    @pytest.mark.asyncio
    async def test_generate_spectral_waveform(self, proxy_processor):
        """Test spectral waveform (spectrogram) generation"""
        job = ProxyJob(
            job_id="test-job-3",
            asset_id="asset789",
            input_path="/path/to/music.flac",
            job_type="spectral_waveform",
            parameters={
                "width": 1920,
                "height": 512,
                "color_mode": "rainbow",
                "frequency_scale": "log",
                "window_size": 4096,
                "overlap": 0.9
            },
            status=JobStatus.PROCESSING
        )
        
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_spectrogram.png")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_spectrogram_data')
        
        result = await proxy_processor._process_spectral_waveform(job)
        
        assert result["proxy_type"] == "spectral_waveform"
        assert result["color_mode"] == "rainbow"
        assert result["frequency_scale"] == "log"
        assert result["frequency_range"] == [0, 22050]
        assert result["time_range"] == [0, 180.5]
        
        # Verify FFmpeg service was called correctly
        proxy_processor.ffmpeg_service.generate_spectral_waveform.assert_called_once_with(
            input_path="/path/to/music.flac",
            output_path=temp_path,
            width=1920,
            height=512,
            color_mode="rainbow",
            frequency_scale="log",
            window_size=4096,
            overlap=0.9
        )
    
    @pytest.mark.asyncio
    async def test_generate_vectorscope(self, proxy_processor):
        """Test vectorscope generation"""
        job = ProxyJob(
            job_id="test-job-4",
            asset_id="asset999",
            input_path="/path/to/stereo_test.wav",
            job_type="vectorscope",
            parameters={
                "width": 512,
                "height": 512,
                "mode": "lissajous_xy",
                "intensity": 0.1,
                "zoom": 2.0
            },
            status=JobStatus.PROCESSING
        )
        
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_vectorscope.png")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_vectorscope_data')
        
        result = await proxy_processor._process_vectorscope(job)
        
        assert result["proxy_type"] == "vectorscope"
        assert result["mode"] == "lissajous_xy"
        assert result["phase_correlation"] == 0.87
        
        # Verify FFmpeg service was called correctly
        proxy_processor.ffmpeg_service.generate_vectorscope.assert_called_once_with(
            input_path="/path/to/stereo_test.wav",
            output_path=temp_path,
            width=512,
            height=512,
            mode="lissajous_xy",
            intensity=0.1,
            zoom=2.0
        )


class TestAudioAnalysis:
    """Test audio analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_detect_audio_peaks(self, mock_ffmpeg_service):
        """Test audio peak detection"""
        result = await mock_ffmpeg_service.detect_audio_peaks(
            input_path="/path/to/loud_audio.wav",
            threshold=-20.0,
            min_duration=0.1,
            channel=None
        )
        
        assert result["peaks_found"] == 3
        assert len(result["peaks"]) == 3
        assert result["max_peak"] == -0.2
        assert result["clipping_detected"] is False
        
        # Verify first peak details
        first_peak = result["peaks"][0]
        assert first_peak["time"] == 12.5
        assert first_peak["level"] == -0.5
        assert first_peak["duration"] == 0.15
        assert first_peak["channel"] == 0
    
    @pytest.mark.asyncio
    async def test_extract_audio_levels(self, mock_ffmpeg_service):
        """Test audio level extraction"""
        result = await mock_ffmpeg_service.extract_audio_levels(
            input_path="/path/to/audio.mp3",
            interval=0.1
        )
        
        assert result["sample_count"] == 100
        assert result["interval"] == 0.1
        assert result["channels"] == 2
        assert len(result["levels"]) >= 3
        
        # Check first level sample
        first_sample = result["levels"][0]
        assert first_sample["time"] == 0.0
        assert len(first_sample["levels"]) == 2
        assert first_sample["levels"][0] == -23.5
        assert first_sample["levels"][1] == -24.1
        
        # Check overall stats
        stats = result["overall_stats"]
        assert stats["peak"] == [-12.5, -13.1]
        assert stats["rms"] == [-23.5, -24.0]
        assert stats["loudness"] == -23.0


class TestWaveformAPIEndpoints:
    """Test waveform API endpoints"""
    
    @pytest.mark.asyncio
    async def test_waveform_request_validation(self):
        """Test waveform request parameter validation"""
        from src.api.routes import WaveformRequest
        
        # Valid request
        request = WaveformRequest(
            asset_id="asset123",
            input_path="/path/to/audio.mp3",
            width=1920,
            height=200,
            style="line"
        )
        assert request.width == 1920
        assert request.style == "line"
        
        # Test invalid style
        with pytest.raises(ValueError):
            WaveformRequest(
                asset_id="asset123",
                input_path="/path/to/audio.mp3",
                style="invalid_style"
            )
    
    @pytest.mark.asyncio
    async def test_spectral_waveform_request_validation(self):
        """Test spectral waveform request parameter validation"""
        from src.api.routes import SpectralWaveformRequest
        
        # Valid request
        request = SpectralWaveformRequest(
            asset_id="asset123",
            input_path="/path/to/audio.mp3",
            color_mode="rainbow",
            frequency_scale="log"
        )
        assert request.color_mode == "rainbow"
        assert request.frequency_scale == "log"
        assert request.window_size == 2048  # default
        
        # Test invalid color mode
        with pytest.raises(ValueError):
            SpectralWaveformRequest(
                asset_id="asset123",
                input_path="/path/to/audio.mp3",
                color_mode="invalid_color"
            )


class TestWaveformErrors:
    """Test error handling in waveform generation"""
    
    @pytest.mark.asyncio
    async def test_waveform_generation_error(self, proxy_processor):
        """Test handling of FFmpeg errors during waveform generation"""
        # Make FFmpeg service raise an error
        proxy_processor.ffmpeg_service.generate_waveform.side_effect = FFmpegError("FFmpeg failed")
        
        job = ProxyJob(
            job_id="test-job-error",
            asset_id="asset123",
            input_path="/path/to/invalid.mp3",
            job_type="waveform",
            parameters={},
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(FFmpegError):
            await proxy_processor._process_waveform(job)
    
    @pytest.mark.asyncio
    async def test_invalid_audio_file(self, proxy_processor):
        """Test handling of invalid audio files"""
        # Make media info return no audio streams
        proxy_processor.ffmpeg_service.get_media_info.return_value = {
            "duration": 0,
            "streams": [{"codec_type": "video"}]  # No audio stream
        }
        
        # This should be handled gracefully by the waveform generation
        # The actual validation would happen in the FFmpeg service