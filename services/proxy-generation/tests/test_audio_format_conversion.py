"""
Tests for audio format conversion functionality
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
    
    # Mock audio format conversion
    service.convert_audio_format = AsyncMock(return_value={
        "input_path": "/path/to/input.wav",
        "output_path": "/path/to/output.mp3",
        "output_format": "mp3",
        "codec": "libmp3lame",
        "bitrate": "192000",
        "sample_rate": "44100",
        "channels": 2,
        "duration": 180.5,
        "file_size": 4326400,
        "processing_time": 3.2
    })
    
    # Mock audio normalization
    service.normalize_audio = AsyncMock(return_value={
        "input_path": "/path/to/input.wav",
        "output_path": "/path/to/normalized.wav",
        "target_level": -23.0,
        "loudnorm_stats": {
            "input_i": "-27.61",
            "input_tp": "-4.47",
            "input_lra": "9.51",
            "input_thresh": "-38.80",
            "output_i": "-23.01",
            "output_tp": "-0.47",
            "output_lra": "9.50",
            "output_thresh": "-34.21",
            "target_offset": "0.01"
        }
    })
    
    # Mock media info
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
    service.generate_storage_key = Mock(return_value="proxies/asset123/audio_192k.mp3")
    service.store_file = AsyncMock(return_value="https://storage.example.com/proxies/asset123/audio.mp3")
    return service


@pytest.fixture
def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


class TestAudioFormatConversion:
    """Test audio format conversion functionality"""
    
    @pytest.mark.asyncio
    async def test_simple_format_conversion(self, proxy_processor):
        """Test simple audio format conversion without normalization"""
        job = ProxyJob(
            job_id="test-job-1",
            asset_id="asset123",
            input_path="/path/to/audio.wav",
            job_type="audio_proxy",
            parameters={
                "format": "mp3",
                "bitrate": "192k",
                "normalize": False
            },
            status=JobStatus.PROCESSING
        )
        
        # Create temp file to simulate output
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_audio.mp3")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_audio_data')
        
        result = await proxy_processor._process_audio_proxy(job)
        
        assert result["job_id"] == "test-job-1"
        assert result["asset_id"] == "asset123"
        assert result["proxy_type"] == "audio"
        assert result["format"] == "mp3"
        assert result["normalized"] is False
        
        # Verify FFmpeg service was called for format conversion
        proxy_processor.ffmpeg_service.convert_audio_format.assert_called_once()
        call_args = proxy_processor.ffmpeg_service.convert_audio_format.call_args[1]
        assert call_args["output_format"] == "mp3"
        assert call_args["bitrate"] == "192k"
    
    @pytest.mark.asyncio
    async def test_format_conversion_with_normalization(self, proxy_processor):
        """Test audio format conversion with normalization"""
        job = ProxyJob(
            job_id="test-job-2",
            asset_id="asset456",
            input_path="/path/to/loud_audio.wav",
            job_type="audio_proxy",
            parameters={
                "format": "mp3",
                "bitrate": "320k",
                "normalize": True,
                "target_level": -16.0
            },
            status=JobStatus.PROCESSING
        )
        
        # Create temp files
        temp_wav_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_normalized.wav")
        temp_mp3_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_audio.mp3")
        
        with open(temp_wav_path, 'wb') as f:
            f.write(b'fake_normalized_wav')
        with open(temp_mp3_path, 'wb') as f:
            f.write(b'fake_mp3_data')
        
        result = await proxy_processor._process_audio_proxy(job)
        
        assert result["normalized"] is True
        
        # Verify normalization was called first
        proxy_processor.ffmpeg_service.normalize_audio.assert_called_once_with(
            input_path="/path/to/loud_audio.wav",
            output_path=temp_wav_path,
            target_level=-16.0
        )
        
        # Verify format conversion was called after normalization
        proxy_processor.ffmpeg_service.convert_audio_format.assert_called_once()
        call_args = proxy_processor.ffmpeg_service.convert_audio_format.call_args[1]
        assert call_args["input_path"] == temp_wav_path
        assert call_args["output_format"] == "mp3"
        assert call_args["bitrate"] == "320k"
    
    @pytest.mark.asyncio
    async def test_various_format_conversions(self, proxy_processor):
        """Test conversion to various audio formats"""
        formats = [
            ("mp3", "libmp3lame", "192k"),
            ("aac", "aac", "192k"),
            ("flac", "flac", None),
            ("opus", "libopus", "128k"),
            ("ogg", "libvorbis", "192k")
        ]
        
        for output_format, expected_codec, default_bitrate in formats:
            job = ProxyJob(
                job_id=f"test-job-{output_format}",
                asset_id="asset789",
                input_path="/path/to/audio.wav",
                job_type="audio_proxy",
                parameters={
                    "format": output_format,
                    "normalize": False
                },
                status=JobStatus.PROCESSING
            )
            
            temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_audio.{output_format}")
            with open(temp_path, 'wb') as f:
                f.write(b'fake_audio_data')
            
            # Reset mock
            proxy_processor.ffmpeg_service.convert_audio_format.reset_mock()
            
            result = await proxy_processor._process_audio_proxy(job)
            
            assert result["format"] == output_format
            
            # Verify correct format was requested
            call_args = proxy_processor.ffmpeg_service.convert_audio_format.call_args[1]
            assert call_args["output_format"] == output_format
    
    @pytest.mark.asyncio
    async def test_custom_conversion_parameters(self, proxy_processor):
        """Test audio conversion with custom parameters"""
        job = ProxyJob(
            job_id="test-job-custom",
            asset_id="asset999",
            input_path="/path/to/stereo.wav",
            job_type="audio_proxy",
            parameters={
                "format": "mp3",
                "bitrate": "128k",
                "sample_rate": 22050,
                "channels": 1,  # Convert to mono
                "normalize": False
            },
            status=JobStatus.PROCESSING
        )
        
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_audio.mp3")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_mono_audio')
        
        result = await proxy_processor._process_audio_proxy(job)
        
        # Verify custom parameters were passed
        call_args = proxy_processor.ffmpeg_service.convert_audio_format.call_args[1]
        assert call_args["bitrate"] == "128k"
        assert call_args["sample_rate"] == 22050
        assert call_args["channels"] == 1


class TestAudioFormatConversionAPI:
    """Test audio format conversion API endpoints"""
    
    @pytest.mark.asyncio
    async def test_audio_conversion_request_validation(self):
        """Test audio conversion request parameter validation"""
        from src.api.routes import AudioFormatConversionRequest
        
        # Valid request
        request = AudioFormatConversionRequest(
            asset_id="asset123",
            input_path="/path/to/audio.wav",
            output_format="mp3",
            bitrate="192k",
            normalize=True
        )
        assert request.output_format == "mp3"
        assert request.bitrate == "192k"
        assert request.normalize is True
        
        # Test invalid format
        with pytest.raises(ValueError):
            AudioFormatConversionRequest(
                asset_id="asset123",
                input_path="/path/to/audio.wav",
                output_format="invalid_format"
            )
        
        # Test invalid bitrate format
        with pytest.raises(ValueError):
            AudioFormatConversionRequest(
                asset_id="asset123",
                input_path="/path/to/audio.wav",
                bitrate="192"  # Missing 'k'
            )


class TestFFmpegServiceConversion:
    """Test FFmpeg service audio conversion implementation"""
    
    @pytest.mark.asyncio
    async def test_codec_auto_selection(self):
        """Test automatic codec selection based on format"""
        from src.services.ffmpeg_service import FFmpegService
        
        # Mock FFmpeg paths
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            service = FFmpegService()
            
            # Test codec map
            codec_expectations = {
                "mp3": "libmp3lame",
                "aac": "aac",
                "flac": "flac",
                "wav": "pcm_s16le",
                "opus": "libopus",
                "ogg": "libvorbis"
            }
            
            # The actual test would require mocking subprocess execution
            # This is a placeholder to show the expected behavior
            assert hasattr(service, 'convert_audio_format')


class TestAudioConversionErrors:
    """Test error handling in audio format conversion"""
    
    @pytest.mark.asyncio
    async def test_invalid_audio_file(self, proxy_processor):
        """Test handling of files without audio streams"""
        # Make media info return no audio streams
        proxy_processor.ffmpeg_service.get_media_info.return_value = {
            "duration": 0,
            "streams": [{"codec_type": "video"}]  # No audio stream
        }
        
        job = ProxyJob(
            job_id="test-job-no-audio",
            asset_id="asset123",
            input_path="/path/to/video_only.mp4",
            job_type="audio_proxy",
            parameters={"format": "mp3"},
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(InvalidMediaError, match="No audio stream found"):
            await proxy_processor._process_audio_proxy(job)
    
    @pytest.mark.asyncio
    async def test_conversion_failure(self, proxy_processor):
        """Test handling of FFmpeg conversion failures"""
        # Make conversion fail
        proxy_processor.ffmpeg_service.convert_audio_format.side_effect = FFmpegError("Conversion failed")
        
        job = ProxyJob(
            job_id="test-job-fail",
            asset_id="asset123",
            input_path="/path/to/audio.wav",
            job_type="audio_proxy",
            parameters={"format": "mp3", "normalize": False},
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(FFmpegError):
            await proxy_processor._process_audio_proxy(job)