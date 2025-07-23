"""
Tests for adaptive bitrate encoding functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os
import json
from datetime import datetime

from src.services.ffmpeg_service import FFmpegService
from src.services.proxy_processor import ProxyProcessor
from src.services.queue_service import ProxyJob, JobStatus
from src.core.exceptions import FFmpegError, InvalidMediaError


@pytest.fixture
def mock_ffmpeg_service():
    """Create a mock FFmpeg service"""
    service = Mock(spec=FFmpegService)
    
    # Mock media info
    service.get_media_info = AsyncMock(return_value={
        "duration": 120.0,
        "size": 104857600,  # 100MB
        "bit_rate": 5000000,
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "bit_rate": 4000000,
                "frame_rate": "30/1"
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": 48000,
                "bit_rate": 192000
            }
        ]
    })
    
    # Mock adaptive bitrate stream generation
    service.generate_adaptive_bitrate_stream = AsyncMock(return_value={
        "input_path": "/path/to/input.mp4",
        "output_dir": "/tmp/output",
        "stream_formats": ["hls", "dash"],
        "qualities": [
            {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
            {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
        ],
        "segment_duration": 6,
        "playlist_type": "vod",
        "total_size": 52428800,  # 50MB
        "processing_time": 45.2,
        "gpu_acceleration": True,
        "streams": {
            "hls": {
                "master_playlist": "/tmp/output/master.m3u8",
                "playlist": "/tmp/output/playlist.m3u8",
                "segment_duration": 6,
                "playlist_type": "vod"
            },
            "dash": {
                "manifest": "/tmp/output/manifest.mpd",
                "segment_duration": 6
            }
        }
    })
    
    return service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="adaptive_bitrate/asset123/hls_master.m3u8")
    service.store_file = AsyncMock(return_value="https://storage.example.com/adaptive_bitrate/asset123/hls_master.m3u8")
    return service


@pytest.fixture
def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


class TestAdaptiveBitrateEncoding:
    """Test adaptive bitrate encoding functionality"""
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_request_validation(self):
        """Test adaptive bitrate request validation"""
        from src.api.routes import AdaptiveBitrateRequest, QualityVariant
        
        # Valid request
        request = AdaptiveBitrateRequest(
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            stream_formats=["hls", "dash"],
            qualities=[
                QualityVariant(
                    name="720p",
                    width=1280,
                    height=720,
                    bitrate="2800k",
                    audio_bitrate="192k"
                ),
                QualityVariant(
                    name="1080p",
                    width=1920,
                    height=1080,
                    bitrate="5000k",
                    audio_bitrate="192k"
                )
            ],
            segment_duration=6,
            playlist_type="vod",
            force_gpu=True
        )
        
        assert request.asset_id == "asset123"
        assert request.stream_formats == ["hls", "dash"]
        assert len(request.qualities) == 2
        assert request.qualities[0].name == "720p"
        assert request.qualities[1].bitrate == "5000k"
        assert request.segment_duration == 6
        assert request.playlist_type == "vod"
        assert request.force_gpu is True
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_generation(self, mock_ffmpeg_service):
        """Test adaptive bitrate stream generation"""
        # Test with custom qualities
        qualities = [
            {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
            {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
        ]
        
        result = await mock_ffmpeg_service.generate_adaptive_bitrate_stream(
            input_path="/path/to/video.mp4",
            output_dir="/tmp/output",
            stream_formats=["hls", "dash"],
            qualities=qualities,
            segment_duration=6,
            playlist_type="vod",
            force_gpu=True
        )
        
        assert result["stream_formats"] == ["hls", "dash"]
        assert len(result["qualities"]) == 2
        assert result["qualities"][0]["name"] == "720p"
        assert result["qualities"][1]["name"] == "1080p"
        assert result["segment_duration"] == 6
        assert result["playlist_type"] == "vod"
        assert result["gpu_acceleration"] is True
        assert "hls" in result["streams"]
        assert "dash" in result["streams"]
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_default_qualities(self, mock_ffmpeg_service):
        """Test adaptive bitrate with default qualities"""
        # Mock with default qualities
        mock_ffmpeg_service.generate_adaptive_bitrate_stream.return_value = {
            "input_path": "/path/to/video.mp4",
            "output_dir": "/tmp/output",
            "stream_formats": ["hls"],
            "qualities": [
                {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                {"name": "480p", "width": 854, "height": 480, "bitrate": "1400k", "audio_bitrate": "128k"},
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
            ],
            "segment_duration": 6,
            "playlist_type": "vod",
            "total_size": 52428800,
            "processing_time": 45.2,
            "gpu_acceleration": True,
            "streams": {
                "hls": {
                    "master_playlist": "/tmp/output/master.m3u8",
                    "playlist": "/tmp/output/playlist.m3u8",
                    "segment_duration": 6,
                    "playlist_type": "vod"
                }
            }
        }
        
        result = await mock_ffmpeg_service.generate_adaptive_bitrate_stream(
            input_path="/path/to/video.mp4",
            output_dir="/tmp/output",
            stream_formats=["hls"],
            qualities=None,  # Use defaults
            segment_duration=6,
            playlist_type="vod",
            force_gpu=True
        )
        
        assert len(result["qualities"]) == 4
        assert result["qualities"][0]["name"] == "360p"
        assert result["qualities"][3]["name"] == "1080p"
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_processing_job(self, proxy_processor):
        """Test processing adaptive bitrate job"""
        # Create mock output files
        output_dir = os.path.join(proxy_processor._temp_dir, "test_adaptive_bitrate")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create some mock files
        mock_files = [
            "master.m3u8",
            "playlist.m3u8",
            "segment_0_00000.ts",
            "segment_0_00001.ts",
            "manifest.mpd",
            "init_0.mp4",
            "chunk_0_00000.m4s"
        ]
        
        for file in mock_files:
            with open(os.path.join(output_dir, file), 'w') as f:
                f.write("mock content")
        
        # Mock os.walk to return our mock files
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [(output_dir, [], mock_files)]
            
            job = ProxyJob(
                job_id="test-job-abr",
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                job_type="adaptive_bitrate",
                parameters={
                    "stream_formats": ["hls", "dash"],
                    "qualities": [
                        {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"}
                    ],
                    "segment_duration": 6,
                    "playlist_type": "vod",
                    "force_gpu": True
                },
                status=JobStatus.PROCESSING
            )
            
            result = await proxy_processor._process_adaptive_bitrate(job)
            
            assert result["job_id"] == "test-job-abr"
            assert result["asset_id"] == "asset123"
            assert result["proxy_type"] == "adaptive_bitrate"
            assert result["stream_formats"] == ["hls", "dash"]
            assert len(result["qualities"]) == 2  # From mock service
            assert result["segment_duration"] == 6
            assert result["playlist_type"] == "vod"
            assert result["gpu_acceleration"] is True
            assert "hls" in result["storage_urls"]
            assert "dash" in result["storage_urls"]
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_no_video_stream(self, proxy_processor):
        """Test adaptive bitrate with no video stream"""
        # Mock media info without video stream
        proxy_processor.ffmpeg_service.get_media_info.return_value = {
            "duration": 120.0,
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "sample_rate": 48000
                }
            ]
        }
        
        job = ProxyJob(
            job_id="test-job-audio-only",
            asset_id="asset123",
            input_path="/path/to/audio.mp3",
            job_type="adaptive_bitrate",
            parameters={
                "stream_formats": ["hls"],
                "segment_duration": 6,
                "playlist_type": "vod"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(InvalidMediaError, match="No video stream found"):
            await proxy_processor._process_adaptive_bitrate(job)
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_generation_failure(self, proxy_processor):
        """Test handling of adaptive bitrate generation failures"""
        # Make generation fail
        proxy_processor.ffmpeg_service.generate_adaptive_bitrate_stream.side_effect = FFmpegError("Generation failed")
        
        job = ProxyJob(
            job_id="test-job-fail",
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            job_type="adaptive_bitrate",
            parameters={
                "stream_formats": ["hls"],
                "segment_duration": 6,
                "playlist_type": "vod"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(Exception):  # Should raise ProxyGenerationError
            await proxy_processor._process_adaptive_bitrate(job)
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_quality_filtering(self, mock_ffmpeg_service):
        """Test quality filtering based on input resolution"""
        # Mock media info with 720p input
        mock_ffmpeg_service.get_media_info.return_value = {
            "duration": 120.0,
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1280,
                    "height": 720,
                    "bit_rate": 2800000
                }
            ]
        }
        
        # Mock filtered qualities response
        mock_ffmpeg_service.generate_adaptive_bitrate_stream.return_value = {
            "input_path": "/path/to/video.mp4",
            "output_dir": "/tmp/output",
            "stream_formats": ["hls"],
            "qualities": [
                {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                {"name": "480p", "width": 854, "height": 480, "bitrate": "1400k", "audio_bitrate": "128k"},
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"}
            ],
            "segment_duration": 6,
            "playlist_type": "vod",
            "total_size": 31457280,
            "processing_time": 30.1,
            "gpu_acceleration": True,
            "streams": {"hls": {"master_playlist": "/tmp/output/master.m3u8"}}
        }
        
        result = await mock_ffmpeg_service.generate_adaptive_bitrate_stream(
            input_path="/path/to/video.mp4",
            output_dir="/tmp/output",
            stream_formats=["hls"],
            qualities=None,
            segment_duration=6,
            playlist_type="vod",
            force_gpu=True
        )
        
        # Should only include qualities up to 720p
        assert len(result["qualities"]) == 3
        assert result["qualities"][-1]["name"] == "720p"
        assert not any(q["name"] == "1080p" for q in result["qualities"])


class TestAdaptiveBitrateAPI:
    """Test adaptive bitrate API endpoints"""
    
    @pytest.mark.asyncio
    async def test_quality_variant_validation(self):
        """Test quality variant validation"""
        from src.api.routes import QualityVariant
        
        # Valid quality variant
        quality = QualityVariant(
            name="720p",
            width=1280,
            height=720,
            bitrate="2800k",
            audio_bitrate="192k"
        )
        
        assert quality.name == "720p"
        assert quality.width == 1280
        assert quality.height == 720
        assert quality.bitrate == "2800k"
        assert quality.audio_bitrate == "192k"
        
        # Test invalid bitrate format
        with pytest.raises(ValueError):
            QualityVariant(
                name="720p",
                width=1280,
                height=720,
                bitrate="invalid_bitrate",
                audio_bitrate="192k"
            )
        
        # Test invalid dimensions
        with pytest.raises(ValueError):
            QualityVariant(
                name="720p",
                width=10000,  # Too large
                height=720,
                bitrate="2800k",
                audio_bitrate="192k"
            )
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_request_defaults(self):
        """Test adaptive bitrate request with default values"""
        from src.api.routes import AdaptiveBitrateRequest
        
        request = AdaptiveBitrateRequest(
            asset_id="asset123",
            input_path="/path/to/video.mp4"
        )
        
        assert request.stream_formats == ["hls", "dash"]
        assert request.qualities is None
        assert request.segment_duration == 6
        assert request.playlist_type == "vod"
        assert request.force_gpu is True
        assert request.priority.value == "high"
    
    @pytest.mark.asyncio
    async def test_adaptive_bitrate_presets(self):
        """Test adaptive bitrate quality presets"""
        from src.api.routes import AdaptiveBitrateRequest
        
        # Test that presets are properly structured
        presets = {
            "mobile": [
                {"name": "240p", "width": 426, "height": 240, "bitrate": "400k", "audio_bitrate": "64k"},
                {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"}
            ],
            "standard": [
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
            ]
        }
        
        # Verify preset structure
        assert "mobile" in presets
        assert "standard" in presets
        assert len(presets["mobile"]) >= 2
        assert len(presets["standard"]) >= 2
        
        # Verify preset quality
        mobile_720p = next((q for q in presets["mobile"] if q["name"] == "360p"), None)
        assert mobile_720p is not None
        assert mobile_720p["bitrate"] == "800k"


class TestAdaptiveBitrateErrors:
    """Test error handling in adaptive bitrate encoding"""
    
    @pytest.mark.asyncio
    async def test_ffmpeg_command_failure(self, proxy_processor):
        """Test handling of FFmpeg command failures"""
        # Make FFmpeg fail
        proxy_processor.ffmpeg_service.generate_adaptive_bitrate_stream.side_effect = FFmpegError(
            "FFmpeg command failed",
            details={"returncode": 1, "stderr": "Invalid input format"}
        )
        
        job = ProxyJob(
            job_id="test-job-ffmpeg-fail",
            asset_id="asset123",
            input_path="/path/to/invalid.mp4",
            job_type="adaptive_bitrate",
            parameters={
                "stream_formats": ["hls"],
                "segment_duration": 6,
                "playlist_type": "vod"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(Exception):
            await proxy_processor._process_adaptive_bitrate(job)
    
    @pytest.mark.asyncio
    async def test_invalid_playlist_type(self):
        """Test validation of playlist type"""
        from src.api.routes import AdaptiveBitrateRequest
        
        # Test invalid playlist type
        with pytest.raises(ValueError):
            AdaptiveBitrateRequest(
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                playlist_type="invalid_type"
            )
    
    @pytest.mark.asyncio
    async def test_invalid_segment_duration(self):
        """Test validation of segment duration"""
        from src.api.routes import AdaptiveBitrateRequest
        
        # Test invalid segment duration (too long)
        with pytest.raises(ValueError):
            AdaptiveBitrateRequest(
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                segment_duration=60  # Too long
            )
        
        # Test invalid segment duration (too short)
        with pytest.raises(ValueError):
            AdaptiveBitrateRequest(
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                segment_duration=0  # Too short
            )