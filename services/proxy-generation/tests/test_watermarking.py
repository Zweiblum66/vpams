"""
Tests for watermarking functionality
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.services.proxy_processor import ProxyProcessor
from src.services.image_processing_service import ImageProcessingService
from src.services.ffmpeg_service import FFmpegService
from src.services.queue_service import ProxyJob, JobStatus, JobPriority
from src.core.exceptions import ProxyGenerationError


@pytest.fixture
async def proxy_processor():
    """Create proxy processor instance for testing"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = AsyncMock(spec=FFmpegService)
    processor.storage_service = AsyncMock()
    processor.image_service = AsyncMock(spec=ImageProcessingService)
    processor._temp_dir = tempfile.mkdtemp()
    
    # Mock storage service methods
    processor.storage_service.generate_storage_key = Mock(return_value="test-storage-key")
    processor.storage_service.store_file = AsyncMock(return_value="https://storage.example.com/test-key")
    
    yield processor
    
    # Cleanup
    if os.path.exists(processor._temp_dir):
        import shutil
        shutil.rmtree(processor._temp_dir)


class TestImageWatermarking:
    """Test image watermarking functionality"""
    
    @pytest.mark.asyncio
    async def test_process_image_watermark(self, proxy_processor):
        """Test processing image watermark job"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-123",
            asset_id="asset-123",
            input_path="/storage/images/test.jpg",
            job_type="image_watermark",
            parameters={
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "bottom-right",
                "opacity": 0.8,
                "scale": 0.2,
                "margin": 20,
                "output_format": "jpg",
                "quality": 95
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service response
        proxy_processor.image_service.add_watermark.return_value = {
            "output_path": "/tmp/watermarked.jpg",
            "original_size": (1920, 1080),
            "watermark_size": (384, 216),
            "watermark_position": (1496, 844),
            "position": "bottom-right",
            "opacity": 0.8,
            "scale": 0.2,
            "quality": 95,
            "output_format": "jpg",
            "processing_time": 0.5
        }
        
        # Process job
        result = await proxy_processor._process_image_watermark(job)
        
        # Verify image service was called correctly
        proxy_processor.image_service.add_watermark.assert_called_once_with(
            input_path="/storage/images/test.jpg",
            watermark_path="/storage/watermarks/logo.png",
            position="bottom-right",
            opacity=0.8,
            scale=0.2,
            margin=20,
            output_format="jpg",
            quality=95
        )
        
        # Verify storage was called
        proxy_processor.storage_service.store_file.assert_called_once()
        
        # Verify result
        assert result["job_id"] == "test-job-123"
        assert result["asset_id"] == "asset-123"
        assert result["storage_key"] == "test-storage-key"
        assert result["storage_url"] == "https://storage.example.com/test-key"
        assert result["watermark_position"] == (1496, 844)
        assert result["processing_time"] == 0.5
    
    @pytest.mark.asyncio
    async def test_process_text_watermark(self, proxy_processor):
        """Test processing text watermark job"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-124",
            asset_id="asset-124",
            input_path="/storage/images/test.jpg",
            job_type="text_watermark",
            parameters={
                "text": "© 2024 My Company",
                "font_size": 36,
                "font_color": (255, 255, 255, 180),
                "position": "bottom-right",
                "margin": 20,
                "background_color": (0, 0, 0, 100),
                "background_padding": 10,
                "output_format": "jpg",
                "quality": 95
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service response
        proxy_processor.image_service.add_text_watermark.return_value = {
            "output_path": "/tmp/text_watermarked.jpg",
            "original_size": (1920, 1080),
            "text": "© 2024 My Company",
            "text_size": (300, 40),
            "text_position": (1600, 1020),
            "position": "bottom-right",
            "font_size": 36,
            "font_color": (255, 255, 255, 180),
            "background_color": (0, 0, 0, 100),
            "quality": 95,
            "output_format": "jpg",
            "processing_time": 0.3
        }
        
        # Process job
        result = await proxy_processor._process_text_watermark(job)
        
        # Verify image service was called correctly
        proxy_processor.image_service.add_text_watermark.assert_called_once_with(
            input_path="/storage/images/test.jpg",
            text="© 2024 My Company",
            font_path=None,
            font_size=36,
            font_color=(255, 255, 255, 180),
            position="bottom-right",
            margin=20,
            background_color=(0, 0, 0, 100),
            background_padding=10,
            output_format="jpg",
            quality=95
        )
        
        # Verify result
        assert result["job_id"] == "test-job-124"
        assert result["asset_id"] == "asset-124"
        assert result["text"] == "© 2024 My Company"
        assert result["text_position"] == (1600, 1020)
        assert result["processing_time"] == 0.3


class TestVideoWatermarking:
    """Test video watermarking functionality"""
    
    @pytest.mark.asyncio
    async def test_process_video_watermark(self, proxy_processor):
        """Test processing video watermark job"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-125",
            asset_id="asset-125",
            input_path="/storage/videos/test.mp4",
            job_type="video_watermark",
            parameters={
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "bottom-right",
                "scale": 0.2,
                "opacity": 0.8,
                "margin": 20,
                "video_codec": None,
                "audio_codec": "copy",
                "quality_preset": "medium"
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock FFmpeg service response
        proxy_processor.ffmpeg_service.add_video_watermark.return_value = {
            "output_path": os.path.join(proxy_processor._temp_dir, "asset-125_watermarked.mp4"),
            "duration": 120.5,
            "file_size": 50000000,
            "encoding_time": 15.2,
            "video_codec": "h264",
            "audio_codec": "copy"
        }
        
        # Process job
        result = await proxy_processor._process_video_watermark(job)
        
        # Verify FFmpeg service was called correctly
        proxy_processor.ffmpeg_service.add_video_watermark.assert_called_once()
        call_args = proxy_processor.ffmpeg_service.add_video_watermark.call_args[1]
        assert call_args["input_path"] == "/storage/videos/test.mp4"
        assert call_args["watermark_path"] == "/storage/watermarks/logo.png"
        assert call_args["position"] == "bottom-right"
        assert call_args["scale"] == 0.2
        assert call_args["opacity"] == 0.8
        assert call_args["margin"] == 20
        assert call_args["quality_preset"] == "medium"
        
        # Verify result
        assert result["job_id"] == "test-job-125"
        assert result["asset_id"] == "asset-125"
        assert result["duration"] == 120.5
        assert result["file_size"] == 50000000
        assert result["encoding_time"] == 15.2
    
    @pytest.mark.asyncio
    async def test_video_watermark_with_custom_codec(self, proxy_processor):
        """Test video watermarking with custom codec"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-126",
            asset_id="asset-126",
            input_path="/storage/videos/test.mp4",
            job_type="video_watermark",
            parameters={
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "top-left",
                "scale": 0.15,
                "opacity": 0.5,
                "margin": 30,
                "video_codec": "libx265",
                "audio_codec": "aac",
                "quality_preset": "high"
            },
            priority=JobPriority.HIGH,
            status=JobStatus.PROCESSING
        )
        
        # Mock FFmpeg service response
        proxy_processor.ffmpeg_service.add_video_watermark.return_value = {
            "output_path": os.path.join(proxy_processor._temp_dir, "asset-126_watermarked.mp4"),
            "duration": 180.0,
            "file_size": 40000000,
            "encoding_time": 25.5,
            "video_codec": "libx265",
            "audio_codec": "aac"
        }
        
        # Process job
        result = await proxy_processor._process_video_watermark(job)
        
        # Verify codec parameters were passed
        call_args = proxy_processor.ffmpeg_service.add_video_watermark.call_args[1]
        assert call_args["video_codec"] == "libx265"
        assert call_args["audio_codec"] == "aac"
        assert call_args["quality_preset"] == "high"


class TestBatchWatermarking:
    """Test batch watermarking functionality"""
    
    @pytest.mark.asyncio
    async def test_process_batch_watermark(self, proxy_processor):
        """Test processing batch watermark job"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-127",
            asset_id="batch_watermark_20240118_120000",
            input_path="batch",
            job_type="batch_watermark",
            parameters={
                "images": [
                    {
                        "asset_id": "asset-200",
                        "input_path": "/storage/images/photo1.jpg",
                        "position": "top-right"
                    },
                    {
                        "asset_id": "asset-201",
                        "input_path": "/storage/images/photo2.jpg",
                        "opacity": 0.5
                    },
                    {
                        "asset_id": "asset-202",
                        "input_path": "/storage/images/photo3.jpg"
                    }
                ],
                "default_watermark_path": "/storage/watermarks/logo.png",
                "default_position": "bottom-right",
                "default_opacity": 0.8,
                "default_scale": 0.2,
                "parallel_workers": 4
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service response
        proxy_processor.image_service.batch_watermark.return_value = [
            {
                "input_path": "/storage/images/photo1.jpg",
                "output_path": "/tmp/photo1_watermarked.jpg",
                "success": True,
                "position": "top-right",
                "processing_time": 0.4
            },
            {
                "input_path": "/storage/images/photo2.jpg",
                "output_path": "/tmp/photo2_watermarked.jpg",
                "success": True,
                "opacity": 0.5,
                "processing_time": 0.5
            },
            {
                "input_path": "/storage/images/photo3.jpg",
                "success": False,
                "error": "Failed to open image"
            }
        ]
        
        # Process job
        result = await proxy_processor._process_batch_watermark(job)
        
        # Verify image service was called correctly
        proxy_processor.image_service.batch_watermark.assert_called_once_with(
            images=job.parameters["images"],
            default_watermark_path="/storage/watermarks/logo.png",
            default_position="bottom-right",
            default_opacity=0.8,
            default_scale=0.2,
            parallel_workers=4
        )
        
        # Verify result
        assert result["job_id"] == "test-job-127"
        assert result["batch_type"] == "watermark"
        assert result["total_images"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        assert result["total_processing_time"] == 0.9
        assert len(result["results"]) == 3
        
        # Verify storage was called for successful images
        assert proxy_processor.storage_service.store_file.call_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_watermark_all_successful(self, proxy_processor):
        """Test batch watermarking with all images successful"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-128",
            asset_id="batch_watermark_20240118_130000",
            input_path="batch",
            job_type="batch_watermark",
            parameters={
                "images": [
                    {"asset_id": f"asset-{i}", "input_path": f"/storage/images/photo{i}.jpg"}
                    for i in range(1, 6)
                ],
                "default_watermark_path": "/storage/watermarks/logo.png",
                "default_position": "center",
                "default_opacity": 0.5,
                "default_scale": 0.3,
                "parallel_workers": 2
            },
            priority=JobPriority.HIGH,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service response - all successful
        proxy_processor.image_service.batch_watermark.return_value = [
            {
                "input_path": f"/storage/images/photo{i}.jpg",
                "output_path": f"/tmp/photo{i}_watermarked.jpg",
                "success": True,
                "processing_time": 0.3 + i * 0.1
            }
            for i in range(1, 6)
        ]
        
        # Process job
        result = await proxy_processor._process_batch_watermark(job)
        
        # Verify result
        assert result["successful"] == 5
        assert result["failed"] == 0
        assert result["total_processing_time"] == sum(0.3 + i * 0.1 for i in range(1, 6))
        
        # Verify storage was called for all images
        assert proxy_processor.storage_service.store_file.call_count == 5


class TestErrorHandling:
    """Test error handling in watermarking"""
    
    @pytest.mark.asyncio
    async def test_image_watermark_processing_error(self, proxy_processor):
        """Test error handling in image watermark processing"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-129",
            asset_id="asset-129",
            input_path="/storage/images/test.jpg",
            job_type="image_watermark",
            parameters={
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "bottom-right"
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service to raise exception
        proxy_processor.image_service.add_watermark.side_effect = Exception("Watermark processing failed")
        
        # Process job should raise exception
        with pytest.raises(ProxyGenerationError) as exc_info:
            await proxy_processor._process_image_watermark(job)
        
        assert "Image watermark processing failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_video_watermark_invalid_parameters(self, proxy_processor):
        """Test video watermarking with invalid parameters"""
        # Create test job with missing watermark path
        job = ProxyJob(
            job_id="test-job-130",
            asset_id="asset-130",
            input_path="/storage/videos/test.mp4",
            job_type="video_watermark",
            parameters={
                "position": "bottom-right"
                # Missing watermark_path
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock FFmpeg service to raise exception
        proxy_processor.ffmpeg_service.add_video_watermark.side_effect = ValueError("Missing watermark path")
        
        # Process job should raise exception
        with pytest.raises(ProxyGenerationError):
            await proxy_processor._process_video_watermark(job)
    
    @pytest.mark.asyncio
    async def test_batch_watermark_partial_failure(self, proxy_processor):
        """Test batch watermarking with partial failures"""
        # Create test job
        job = ProxyJob(
            job_id="test-job-131",
            asset_id="batch_watermark_20240118_140000",
            input_path="batch",
            job_type="batch_watermark",
            parameters={
                "images": [
                    {"input_path": f"/storage/images/photo{i}.jpg"}
                    for i in range(1, 4)
                ],
                "default_watermark_path": "/storage/watermarks/logo.png"
            },
            priority=JobPriority.NORMAL,
            status=JobStatus.PROCESSING
        )
        
        # Mock image service response with one success
        proxy_processor.image_service.batch_watermark.return_value = [
            {
                "input_path": "/storage/images/photo1.jpg",
                "output_path": "/tmp/photo1_watermarked.jpg",
                "success": True,
                "processing_time": 0.5
            },
            {
                "input_path": "/storage/images/photo2.jpg",
                "success": False,
                "error": "Invalid image format"
            },
            {
                "input_path": "/storage/images/photo3.jpg",
                "success": False,
                "error": "Watermark file not found"
            }
        ]
        
        # Mock storage to fail on the successful image
        proxy_processor.storage_service.store_file.side_effect = Exception("Storage error")
        
        # Process job
        result = await proxy_processor._process_batch_watermark(job)
        
        # Verify result shows all as failed (1 due to storage error, 2 original failures)
        assert result["successful"] == 0
        assert result["failed"] == 3
        assert result["total_processing_time"] == 0  # No successful storage