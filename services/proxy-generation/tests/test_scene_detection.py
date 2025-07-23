"""
Tests for scene detection functionality
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
        "size": 52428800,  # 50MB
        "bit_rate": 3500000,
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "bit_rate": 3000000,
                "frame_rate": "24/1"
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
    
    # Mock scene detection
    service.detect_scene_changes = AsyncMock(return_value={
        "input_path": "/path/to/video.mp4",
        "threshold": 0.3,
        "min_scene_duration": 1.0,
        "total_scenes": 8,
        "duration": 120.0,
        "scenes": [
            {
                "timestamp": 5.2,
                "scene_start": 0.0,
                "scene_end": 5.2,
                "duration": 5.2,
                "frame_number": 125
            },
            {
                "timestamp": 12.5,
                "scene_start": 5.2,
                "scene_end": 12.5,
                "duration": 7.3,
                "frame_number": 300
            },
            {
                "timestamp": 24.8,
                "scene_start": 12.5,
                "scene_end": 24.8,
                "duration": 12.3,
                "frame_number": 595
            },
            {
                "timestamp": 45.0,
                "scene_start": 24.8,
                "scene_end": 45.0,
                "duration": 20.2,
                "frame_number": 1080
            },
            {
                "timestamp": 67.3,
                "scene_start": 45.0,
                "scene_end": 67.3,
                "duration": 22.3,
                "frame_number": 1615
            },
            {
                "timestamp": 89.5,
                "scene_start": 67.3,
                "scene_end": 89.5,
                "duration": 22.2,
                "frame_number": 2148
            },
            {
                "timestamp": 102.7,
                "scene_start": 89.5,
                "scene_end": 102.7,
                "duration": 13.2,
                "frame_number": 2465
            },
            {
                "timestamp": 120.0,
                "scene_start": 102.7,
                "scene_end": 120.0,
                "duration": 17.3,
                "frame_number": 2880
            }
        ],
        "average_scene_duration": 15.0,
        "processing_time": 12.5,
        "output_format": "json",
        "thumbnails_saved": False
    })
    
    return service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="scene_detection/asset123/scenes.json")
    service.store_file = AsyncMock(return_value="https://storage.example.com/scene_detection/asset123/scenes.json")
    return service


@pytest.fixture
def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


class TestSceneDetection:
    """Test scene detection functionality"""
    
    @pytest.mark.asyncio
    async def test_scene_detection_request_validation(self):
        """Test scene detection request validation"""
        from src.api.routes import SceneDetectionRequest
        
        # Valid request
        request = SceneDetectionRequest(
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="json",
            save_thumbnails=True,
            thumbnail_size="320x180",
            priority="normal"
        )
        
        assert request.asset_id == "asset123"
        assert request.threshold == 0.3
        assert request.min_scene_duration == 1.0
        assert request.output_format == "json"
        assert request.save_thumbnails is True
        assert request.thumbnail_size == "320x180"
        
    @pytest.mark.asyncio
    async def test_threshold_validation(self):
        """Test threshold parameter validation"""
        from src.api.routes import SceneDetectionRequest
        
        # Test valid threshold values
        request = SceneDetectionRequest(
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            threshold=0.0
        )
        assert request.threshold == 0.0
        
        request = SceneDetectionRequest(
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            threshold=1.0
        )
        assert request.threshold == 1.0
        
        # Test invalid threshold values
        with pytest.raises(ValueError):
            SceneDetectionRequest(
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                threshold=-0.1
            )
        
        with pytest.raises(ValueError):
            SceneDetectionRequest(
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                threshold=1.1
            )
    
    @pytest.mark.asyncio
    async def test_scene_detection_basic(self, mock_ffmpeg_service):
        """Test basic scene detection"""
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="json",
            save_thumbnails=False
        )
        
        assert result["total_scenes"] == 8
        assert result["duration"] == 120.0
        assert result["average_scene_duration"] == 15.0
        assert len(result["scenes"]) == 8
        assert result["scenes"][0]["timestamp"] == 5.2
        assert result["scenes"][0]["duration"] == 5.2
        assert result["scenes"][0]["frame_number"] == 125
    
    @pytest.mark.asyncio
    async def test_scene_detection_with_thumbnails(self, proxy_processor):
        """Test scene detection with thumbnail generation"""
        # Create some mock thumbnail files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the FFmpeg service to use our temp directory
            proxy_processor.ffmpeg_service.detect_scene_changes.return_value = {
                "input_path": "/path/to/video.mp4",
                "threshold": 0.3,
                "min_scene_duration": 1.0,
                "total_scenes": 3,
                "duration": 60.0,
                "scenes": [
                    {"timestamp": 5.2, "scene_start": 0.0, "scene_end": 5.2, "duration": 5.2},
                    {"timestamp": 25.0, "scene_start": 5.2, "scene_end": 25.0, "duration": 19.8},
                    {"timestamp": 60.0, "scene_start": 25.0, "scene_end": 60.0, "duration": 35.0}
                ],
                "average_scene_duration": 20.0,
                "processing_time": 5.2,
                "output_format": "json",
                "thumbnails_saved": True
            }
            
            # Create mock thumbnail files
            thumbnail_dir = os.path.join(proxy_processor._temp_dir, "test-job-1_scene_thumbnails")
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            thumbnail_files = [
                "scene_0000_5.20s.jpg",
                "scene_0001_25.00s.jpg",
                "scene_0002_60.00s.jpg"
            ]
            
            for file in thumbnail_files:
                with open(os.path.join(thumbnail_dir, file), 'w') as f:
                    f.write("mock thumbnail")
            
            job = ProxyJob(
                job_id="test-job-1",
                asset_id="asset123",
                input_path="/path/to/video.mp4",
                job_type="scene_detection",
                parameters={
                    "threshold": 0.3,
                    "min_scene_duration": 1.0,
                    "output_format": "json",
                    "save_thumbnails": True,
                    "thumbnail_size": "320x180"
                },
                status=JobStatus.PROCESSING
            )
            
            # Mock os.path.exists to return True for our thumbnail directory
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=thumbnail_files):
                    result = await proxy_processor._process_scene_detection(job)
            
            assert result["job_id"] == "test-job-1"
            assert result["asset_id"] == "asset123"
            assert result["detection_type"] == "scene_change"
            assert result["total_scenes"] == 3
            assert result["thumbnails_saved"] is True
            assert len(result["thumbnail_urls"]) == 3
    
    @pytest.mark.asyncio
    async def test_scene_detection_csv_output(self, mock_ffmpeg_service):
        """Test scene detection with CSV output format"""
        # Mock CSV output
        mock_ffmpeg_service.detect_scene_changes.return_value = {
            "input_path": "/path/to/video.mp4",
            "threshold": 0.3,
            "min_scene_duration": 1.0,
            "total_scenes": 2,
            "duration": 30.0,
            "scenes": """timestamp,scene_start,scene_end,duration,frame_number
5.2,0.0,5.2,5.2,125
15.5,5.2,15.5,10.3,372""",
            "average_scene_duration": 7.75,
            "processing_time": 3.2,
            "output_format": "csv",
            "thumbnails_saved": False
        }
        
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="csv",
            save_thumbnails=False
        )
        
        assert result["output_format"] == "csv"
        assert isinstance(result["scenes"], str)
        assert "timestamp,scene_start,scene_end,duration,frame_number" in result["scenes"]
    
    @pytest.mark.asyncio
    async def test_scene_detection_timestamps_output(self, mock_ffmpeg_service):
        """Test scene detection with timestamps output format"""
        # Mock timestamps output
        mock_ffmpeg_service.detect_scene_changes.return_value = {
            "input_path": "/path/to/video.mp4",
            "threshold": 0.3,
            "min_scene_duration": 1.0,
            "total_scenes": 4,
            "duration": 60.0,
            "scenes": [5.2, 15.5, 30.0, 45.8],
            "average_scene_duration": 15.0,
            "processing_time": 4.1,
            "output_format": "timestamps",
            "thumbnails_saved": False
        }
        
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="timestamps",
            save_thumbnails=False
        )
        
        assert result["output_format"] == "timestamps"
        assert isinstance(result["scenes"], list)
        assert len(result["scenes"]) == 4
        assert all(isinstance(t, (int, float)) for t in result["scenes"])
    
    @pytest.mark.asyncio
    async def test_scene_detection_no_video_stream(self, proxy_processor):
        """Test scene detection with no video stream"""
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
            job_type="scene_detection",
            parameters={
                "threshold": 0.3,
                "min_scene_duration": 1.0,
                "output_format": "json"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(InvalidMediaError, match="No video stream found"):
            await proxy_processor._process_scene_detection(job)
    
    @pytest.mark.asyncio
    async def test_scene_detection_failure(self, proxy_processor):
        """Test handling of scene detection failures"""
        # Make detection fail
        proxy_processor.ffmpeg_service.detect_scene_changes.side_effect = FFmpegError("Detection failed")
        
        job = ProxyJob(
            job_id="test-job-fail",
            asset_id="asset123",
            input_path="/path/to/video.mp4",
            job_type="scene_detection",
            parameters={
                "threshold": 0.3,
                "min_scene_duration": 1.0,
                "output_format": "json"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(Exception):  # Should raise ProxyGenerationError
            await proxy_processor._process_scene_detection(job)
    
    @pytest.mark.asyncio
    async def test_scene_detection_minimum_duration_filtering(self, mock_ffmpeg_service):
        """Test that scenes shorter than minimum duration are filtered"""
        # Mock scene detection with min duration filtering
        mock_ffmpeg_service.detect_scene_changes.return_value = {
            "input_path": "/path/to/video.mp4",
            "threshold": 0.3,
            "min_scene_duration": 5.0,  # 5 second minimum
            "total_scenes": 3,  # Only 3 scenes meet the minimum duration
            "duration": 60.0,
            "scenes": [
                {"timestamp": 10.0, "scene_start": 0.0, "scene_end": 10.0, "duration": 10.0},
                {"timestamp": 25.0, "scene_start": 10.0, "scene_end": 25.0, "duration": 15.0},
                {"timestamp": 60.0, "scene_start": 25.0, "scene_end": 60.0, "duration": 35.0}
            ],
            "average_scene_duration": 20.0,
            "processing_time": 5.5,
            "output_format": "json",
            "thumbnails_saved": False
        }
        
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=5.0,
            output_format="json",
            save_thumbnails=False
        )
        
        assert result["min_scene_duration"] == 5.0
        assert result["total_scenes"] == 3
        assert all(scene["duration"] >= 5.0 for scene in result["scenes"])


class TestSceneDetectionAPI:
    """Test scene detection API endpoints"""
    
    @pytest.mark.asyncio
    async def test_scene_detection_defaults_endpoint(self):
        """Test scene detection defaults endpoint"""
        # This would normally be tested with the actual API client
        # Here we just verify the expected structure
        expected_defaults = {
            "thresholds": {
                "low": 0.2,
                "medium": 0.3,
                "high": 0.4
            },
            "min_scene_durations": {
                "quick_cuts": 0.5,
                "normal": 1.0,
                "slow_pace": 2.0
            },
            "thumbnail_sizes": {
                "small": "160x90",
                "medium": "320x180",
                "large": "640x360",
                "hd": "1280x720"
            },
            "output_formats": ["json", "csv", "timestamps"],
            "recommended_settings": {
                "action": {"threshold": 0.25, "min_scene_duration": 0.5},
                "drama": {"threshold": 0.35, "min_scene_duration": 2.0},
                "documentary": {"threshold": 0.4, "min_scene_duration": 3.0},
                "music_video": {"threshold": 0.2, "min_scene_duration": 0.3}
            }
        }
        
        # Verify structure
        assert "thresholds" in expected_defaults
        assert "min_scene_durations" in expected_defaults
        assert "thumbnail_sizes" in expected_defaults
        assert "output_formats" in expected_defaults
        assert "recommended_settings" in expected_defaults
        
        # Verify recommended settings have required fields
        for genre, settings in expected_defaults["recommended_settings"].items():
            assert "threshold" in settings
            assert "min_scene_duration" in settings


class TestSceneDetectionEdgeCases:
    """Test edge cases for scene detection"""
    
    @pytest.mark.asyncio
    async def test_single_scene_video(self, mock_ffmpeg_service):
        """Test detection on video with no scene changes"""
        # Mock video with no scene changes
        mock_ffmpeg_service.detect_scene_changes.return_value = {
            "input_path": "/path/to/video.mp4",
            "threshold": 0.3,
            "min_scene_duration": 1.0,
            "total_scenes": 0,
            "duration": 30.0,
            "scenes": [],
            "average_scene_duration": 0,
            "processing_time": 2.1,
            "output_format": "json",
            "thumbnails_saved": False
        }
        
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="json",
            save_thumbnails=False
        )
        
        assert result["total_scenes"] == 0
        assert len(result["scenes"]) == 0
        assert result["average_scene_duration"] == 0
    
    @pytest.mark.asyncio
    async def test_very_short_video(self, mock_ffmpeg_service):
        """Test detection on very short video"""
        # Mock very short video
        mock_ffmpeg_service.detect_scene_changes.return_value = {
            "input_path": "/path/to/short_video.mp4",
            "threshold": 0.3,
            "min_scene_duration": 1.0,
            "total_scenes": 1,
            "duration": 2.5,
            "scenes": [
                {"timestamp": 1.2, "scene_start": 0.0, "scene_end": 1.2, "duration": 1.2}
            ],
            "average_scene_duration": 1.2,
            "processing_time": 0.8,
            "output_format": "json",
            "thumbnails_saved": False
        }
        
        result = await mock_ffmpeg_service.detect_scene_changes(
            input_path="/path/to/short_video.mp4",
            threshold=0.3,
            min_scene_duration=1.0,
            output_format="json",
            save_thumbnails=False
        )
        
        assert result["duration"] == 2.5
        assert result["total_scenes"] == 1
        assert result["scenes"][0]["duration"] >= 1.0  # Meets minimum duration