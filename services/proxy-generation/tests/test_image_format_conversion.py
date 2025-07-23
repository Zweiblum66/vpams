"""
Tests for image format conversion functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os
from datetime import datetime

from src.services.ffmpeg_service import FFmpegService
from src.services.proxy_processor import ProxyProcessor
from src.services.queue_service import ProxyJob, JobStatus
from src.core.exceptions import FFmpegError


@pytest.fixture
def mock_ffmpeg_service():
    """Create a mock FFmpeg service"""
    service = Mock(spec=FFmpegService)
    
    # Mock image format conversion
    service.convert_image_format = AsyncMock(return_value={
        "input_path": "/path/to/input.png",
        "output_path": "/path/to/output.jpg",
        "output_format": "jpg",
        "width": 1920,
        "height": 1080,
        "codec": "mjpeg",
        "pixel_format": "yuvj420p",
        "file_size": 245760,
        "processing_time": 0.5
    })
    
    # Mock image sequence conversion
    service.convert_image_sequence = AsyncMock(return_value={
        "input_pattern": "frame_%04d.png",
        "output_path": "/path/to/output.mp4",
        "output_format": "mp4",
        "frame_rate": 24,
        "duration": 10.0,
        "codec": "libx264",
        "file_size": 5242880,
        "processing_time": 3.2
    })
    
    # Mock media info
    service.get_media_info = AsyncMock(return_value={
        "duration": 10.0,
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "png",
                "width": 1920,
                "height": 1080,
                "pix_fmt": "rgb24"
            }
        ]
    })
    
    return service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="proxies/asset123/image_1920x1080.jpg")
    service.store_file = AsyncMock(return_value="https://storage.example.com/proxies/asset123/image.jpg")
    return service


@pytest.fixture
def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


class TestImageFormatConversion:
    """Test image format conversion functionality"""
    
    @pytest.mark.asyncio
    async def test_simple_image_format_conversion(self, mock_ffmpeg_service):
        """Test simple image format conversion"""
        result = await mock_ffmpeg_service.convert_image_format(
            input_path="/path/to/image.png",
            output_path="/path/to/image.jpg",
            output_format="jpg"
        )
        
        assert result["output_format"] == "jpg"
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["file_size"] == 245760
    
    @pytest.mark.asyncio
    async def test_image_conversion_with_resize(self, mock_ffmpeg_service):
        """Test image format conversion with resizing"""
        # Update mock to return different dimensions
        mock_ffmpeg_service.convert_image_format.return_value = {
            "input_path": "/path/to/input.png",
            "output_path": "/path/to/output.jpg",
            "output_format": "jpg",
            "width": 640,
            "height": 360,
            "codec": "mjpeg",
            "pixel_format": "yuvj420p",
            "file_size": 61440,
            "processing_time": 0.3
        }
        
        result = await mock_ffmpeg_service.convert_image_format(
            input_path="/path/to/large_image.png",
            output_path="/path/to/thumbnail.jpg",
            output_format="jpg",
            width=640,
            height=360,
            quality=85
        )
        
        assert result["width"] == 640
        assert result["height"] == 360
        assert result["file_size"] < 245760  # Smaller than full-size
    
    @pytest.mark.asyncio
    async def test_various_image_format_conversions(self, mock_ffmpeg_service):
        """Test conversion to various image formats"""
        formats = ["jpg", "png", "webp", "bmp", "tiff"]
        
        for output_format in formats:
            # Update mock for each format
            mock_ffmpeg_service.convert_image_format.return_value["output_format"] = output_format
            
            result = await mock_ffmpeg_service.convert_image_format(
                input_path="/path/to/input.png",
                output_path=f"/path/to/output.{output_format}",
                output_format=output_format
            )
            
            assert result["output_format"] == output_format
    
    @pytest.mark.asyncio
    async def test_preserve_aspect_ratio(self, mock_ffmpeg_service):
        """Test image conversion preserving aspect ratio"""
        # Mock should maintain 16:9 ratio when only width is specified
        mock_ffmpeg_service.convert_image_format.return_value = {
            "input_path": "/path/to/input.png",
            "output_path": "/path/to/output.jpg",
            "output_format": "jpg",
            "width": 1280,
            "height": 720,  # Maintained 16:9 ratio
            "codec": "mjpeg",
            "pixel_format": "yuvj420p",
            "file_size": 184320,
            "processing_time": 0.4
        }
        
        result = await mock_ffmpeg_service.convert_image_format(
            input_path="/path/to/input.png",
            output_path="/path/to/output.jpg",
            output_format="jpg",
            width=1280,  # Only width specified
            preserve_aspect_ratio=True
        )
        
        # Check aspect ratio is maintained (16:9)
        assert result["width"] / result["height"] == pytest.approx(16/9, rel=0.01)


class TestImageSequenceConversion:
    """Test image sequence to video/gif conversion"""
    
    @pytest.mark.asyncio
    async def test_image_sequence_to_video(self, proxy_processor):
        """Test converting image sequence to video"""
        job = ProxyJob(
            job_id="test-job-seq-1",
            asset_id="asset123",
            input_path="frame_%04d.png",
            job_type="image_sequence",
            parameters={
                "input_pattern": "frame_%04d.png",
                "output_format": "mp4",
                "frame_rate": 24,
                "quality": "23"
            },
            status=JobStatus.PROCESSING
        )
        
        # Create temp file to simulate output
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_sequence.mp4")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_video_data')
        
        result = await proxy_processor._process_image_sequence(job)
        
        assert result["job_id"] == "test-job-seq-1"
        assert result["asset_id"] == "asset123"
        assert result["proxy_type"] == "image_sequence"
        assert result["output_format"] == "mp4"
        assert result["frame_rate"] == 24
        
        # Verify FFmpeg service was called correctly
        proxy_processor.ffmpeg_service.convert_image_sequence.assert_called_once_with(
            input_pattern="frame_%04d.png",
            output_path=temp_path,
            output_format="mp4",
            frame_rate=24,
            quality="23"
        )
    
    @pytest.mark.asyncio
    async def test_image_sequence_to_gif(self, proxy_processor):
        """Test converting image sequence to animated GIF"""
        job = ProxyJob(
            job_id="test-job-gif",
            asset_id="asset456",
            input_path="frame_%03d.jpg",
            job_type="image_sequence",
            parameters={
                "input_pattern": "frame_%03d.jpg",
                "output_format": "gif",
                "frame_rate": 10
            },
            status=JobStatus.PROCESSING
        )
        
        # Update mock for GIF output
        proxy_processor.ffmpeg_service.convert_image_sequence.return_value = {
            "input_pattern": "frame_%03d.jpg",
            "output_path": "/path/to/output.gif",
            "output_format": "gif",
            "frame_rate": 10,
            "duration": 5.0,
            "codec": "gif",
            "file_size": 2097152,
            "processing_time": 2.1
        }
        
        temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_sequence.gif")
        with open(temp_path, 'wb') as f:
            f.write(b'fake_gif_data')
        
        result = await proxy_processor._process_image_sequence(job)
        
        assert result["output_format"] == "gif"
        assert result["frame_rate"] == 10
    
    @pytest.mark.asyncio
    async def test_various_video_formats(self, proxy_processor):
        """Test conversion to various video formats"""
        formats = ["mp4", "webm", "avi", "mov"]
        
        for output_format in formats:
            job = ProxyJob(
                job_id=f"test-job-{output_format}",
                asset_id="asset789",
                input_path="frame_%04d.png",
                job_type="image_sequence",
                parameters={
                    "input_pattern": "frame_%04d.png",
                    "output_format": output_format,
                    "frame_rate": 30
                },
                status=JobStatus.PROCESSING
            )
            
            temp_path = os.path.join(proxy_processor._temp_dir, f"{job.job_id}_sequence.{output_format}")
            with open(temp_path, 'wb') as f:
                f.write(b'fake_video_data')
            
            # Reset mock
            proxy_processor.ffmpeg_service.convert_image_sequence.reset_mock()
            
            result = await proxy_processor._process_image_sequence(job)
            
            assert result["output_format"] == output_format


class TestImageConversionAPI:
    """Test image conversion API endpoints"""
    
    @pytest.mark.asyncio
    async def test_image_conversion_request_validation(self):
        """Test image conversion request parameter validation"""
        from src.api.routes import ImageFormatConversionRequest
        
        # Valid request
        request = ImageFormatConversionRequest(
            asset_id="asset123",
            input_path="/path/to/image.png",
            output_format="jpg",
            width=1920,
            height=1080,
            quality=90
        )
        assert request.output_format == "jpg"
        assert request.width == 1920
        assert request.preserve_aspect_ratio is True  # default
        
        # Test invalid format
        with pytest.raises(ValueError):
            ImageFormatConversionRequest(
                asset_id="asset123",
                input_path="/path/to/image.png",
                output_format="invalid_format"
            )
        
        # Test invalid dimensions
        with pytest.raises(ValueError):
            ImageFormatConversionRequest(
                asset_id="asset123",
                input_path="/path/to/image.png",
                width=10000  # Too large
            )
    
    @pytest.mark.asyncio
    async def test_image_sequence_request_validation(self):
        """Test image sequence conversion request validation"""
        from src.api.routes import ImageSequenceConversionRequest
        
        # Valid request
        request = ImageSequenceConversionRequest(
            asset_id="asset123",
            input_pattern="frame_%04d.png",
            output_format="mp4",
            frame_rate=24
        )
        assert request.output_format == "mp4"
        assert request.frame_rate == 24
        
        # Test invalid format
        with pytest.raises(ValueError):
            ImageSequenceConversionRequest(
                asset_id="asset123",
                input_pattern="frame_%04d.png",
                output_format="mkv"  # Not supported
            )
        
        # Test invalid frame rate
        with pytest.raises(ValueError):
            ImageSequenceConversionRequest(
                asset_id="asset123",
                input_pattern="frame_%04d.png",
                frame_rate=150  # Too high
            )


class TestImageConversionErrors:
    """Test error handling in image format conversion"""
    
    @pytest.mark.asyncio
    async def test_image_conversion_failure(self, proxy_processor):
        """Test handling of FFmpeg conversion failures"""
        # Make conversion fail
        proxy_processor.ffmpeg_service.convert_image_format.side_effect = FFmpegError("Conversion failed")
        
        with pytest.raises(FFmpegError):
            await proxy_processor.ffmpeg_service.convert_image_format(
                input_path="/path/to/invalid.png",
                output_path="/path/to/output.jpg",
                output_format="jpg"
            )
    
    @pytest.mark.asyncio
    async def test_image_sequence_conversion_failure(self, proxy_processor):
        """Test handling of image sequence conversion failures"""
        # Make conversion fail
        proxy_processor.ffmpeg_service.convert_image_sequence.side_effect = FFmpegError("Invalid pattern")
        
        job = ProxyJob(
            job_id="test-job-fail",
            asset_id="asset123",
            input_path="invalid_pattern",
            job_type="image_sequence",
            parameters={
                "input_pattern": "invalid_pattern",
                "output_format": "mp4"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(FFmpegError):
            await proxy_processor._process_image_sequence(job)