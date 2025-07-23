"""
Tests for thumbnail generation functionality
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from src.services.ffmpeg_service import FFmpegService, GPUType
from src.services.proxy_processor import ProxyProcessor
from src.services.queue_service import ProxyJob, JobPriority


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.ffmpeg_path = "ffmpeg"
    settings.ffprobe_path = "ffprobe"
    settings.ffmpeg_threads = 4
    settings.enable_gpu_acceleration = False
    settings.default_video_codec = "libx264"
    settings.default_audio_codec = "aac"
    settings.processing_timeout = 300
    return settings


@pytest.fixture
def mock_ffmpeg_service(mock_settings):
    """Mock FFmpeg service"""
    with patch('src.services.ffmpeg_service.settings', mock_settings):
        service = FFmpegService()
        return service


@pytest.fixture
def mock_storage_service():
    """Mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="test/storage/key.jpg")
    service.store_file = AsyncMock(return_value="https://storage.example.com/test/storage/key.jpg")
    return service


@pytest.fixture
async def proxy_processor(mock_ffmpeg_service, mock_storage_service):
    """Create proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.ffmpeg_service = mock_ffmpeg_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    yield processor
    # Cleanup
    if os.path.exists(processor._temp_dir):
        import shutil
        shutil.rmtree(processor._temp_dir)


class TestThumbnailGeneration:
    """Test thumbnail generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_single_thumbnail(self, mock_ffmpeg_service):
        """Test single thumbnail generation"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            output_path = tmp.name
            
        try:
            # Mock get_media_info
            mock_ffmpeg_service.get_media_info = AsyncMock(return_value={
                "duration": 120.0,
                "format": {"duration": "120.0"},
                "streams": [{"codec_type": "video"}]
            })
            
            # Mock subprocess execution
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b'', b''))
                mock_subprocess.return_value = mock_process
                
                # Create dummy output file
                with open(output_path, 'wb') as f:
                    f.write(b'dummy thumbnail data')
                
                result = await mock_ffmpeg_service.generate_single_thumbnail(
                    input_path="/test/video.mp4",
                    output_path=output_path,
                    time_offset="auto",
                    width=640,
                    height=360
                )
                
                assert result["path"] == output_path
                assert result["time_offset"] == 12.0  # 10% of 120s
                assert result["width"] == 640
                assert result["height"] == 360
                assert result["format"] == "jpg"
                assert result["size"] > 0
                
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail_batch(self, mock_ffmpeg_service):
        """Test batch thumbnail generation"""
        output_pattern = "/tmp/test_thumb_%d.jpg"
        
        # Mock get_media_info
        mock_ffmpeg_service.get_media_info = AsyncMock(return_value={
            "duration": 100.0,
            "format": {"duration": "100.0"},
            "streams": [{"codec_type": "video"}]
        })
        
        # Mock subprocess execution
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'', b''))
            mock_subprocess.return_value = mock_process
            
            # Create dummy output files
            temp_files = []
            for i in range(5):
                path = f"/tmp/test_thumb_{i}.jpg"
                with open(path, 'wb') as f:
                    f.write(b'dummy thumbnail data')
                temp_files.append(path)
            
            try:
                with patch('glob.glob', return_value=temp_files):
                    result = await mock_ffmpeg_service.generate_thumbnails(
                        input_path="/test/video.mp4",
                        output_pattern=output_pattern,
                        count=5,
                        width=320,
                        height=180,
                        method="interval"
                    )
                    
                    assert result["count"] == 5
                    assert len(result["thumbnails"]) == 5
                    assert result["method"] == "interval"
                    assert all(t["width"] == 320 for t in result["thumbnails"])
                    assert all(t["height"] == 180 for t in result["thumbnails"])
                    
            finally:
                for path in temp_files:
                    if os.path.exists(path):
                        os.remove(path)
    
    @pytest.mark.asyncio
    async def test_generate_contact_sheet(self, mock_ffmpeg_service):
        """Test contact sheet generation"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            output_path = tmp.name
            
        try:
            # Mock get_media_info
            mock_ffmpeg_service.get_media_info = AsyncMock(return_value={
                "duration": 120.0,
                "format": {"duration": "120.0"},
                "streams": [{"codec_type": "video"}]
            })
            
            # Mock subprocess execution
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(return_value=(b'', b''))
                mock_subprocess.return_value = mock_process
                
                # Create dummy output file
                with open(output_path, 'wb') as f:
                    f.write(b'dummy contact sheet data')
                
                result = await mock_ffmpeg_service.generate_contact_sheet(
                    input_path="/test/video.mp4",
                    output_path=output_path,
                    grid_size=(3, 3),
                    thumb_width=160,
                    thumb_height=90,
                    include_timestamps=True
                )
                
                assert result["path"] == output_path
                assert result["grid"]["columns"] == 3
                assert result["grid"]["rows"] == 3
                assert result["thumbnail_count"] == 9
                assert result["size"] > 0
                
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestThumbnailProcessing:
    """Test thumbnail processing in proxy processor"""
    
    @pytest.mark.asyncio
    async def test_process_single_thumbnail_job(self, proxy_processor):
        """Test processing single thumbnail job"""
        job = ProxyJob(
            job_id="test-job-123",
            asset_id="asset-456",
            input_path="/test/video.mp4",
            job_type="thumbnail_single",
            parameters={
                "time_offset": "auto",
                "width": 640,
                "height": 360,
                "format": "jpg",
                "quality": 90
            },
            priority=JobPriority.NORMAL
        )
        
        # Mock FFmpeg service methods
        proxy_processor.ffmpeg_service.generate_single_thumbnail = AsyncMock(return_value={
            "path": f"{proxy_processor._temp_dir}/test-job-123_thumb_single.jpg",
            "time_offset": 10.0,
            "size": 50000,
            "width": 640,
            "height": 360,
            "format": "jpg"
        })
        
        # Create dummy file
        output_path = f"{proxy_processor._temp_dir}/test-job-123_thumb_single.jpg"
        with open(output_path, 'wb') as f:
            f.write(b'dummy data')
        
        result = await proxy_processor._process_thumbnail_single(job)
        
        assert result["job_id"] == "test-job-123"
        assert result["asset_id"] == "asset-456"
        assert result["proxy_type"] == "thumbnail_single"
        assert result["time_offset"] == 10.0
        assert result["storage_key"] == "test/storage/key.jpg"
        assert result["storage_url"] == "https://storage.example.com/test/storage/key.jpg"
    
    @pytest.mark.asyncio
    async def test_process_thumbnail_batch_job(self, proxy_processor):
        """Test processing thumbnail batch job"""
        job = ProxyJob(
            job_id="test-job-789",
            asset_id="asset-101",
            input_path="/test/video.mp4",
            job_type="thumbnail_batch",
            parameters={
                "count": 3,
                "width": 320,
                "height": 180,
                "method": "interval"
            },
            priority=JobPriority.HIGH
        )
        
        # Create dummy thumbnail files
        thumbnails = []
        for i in range(3):
            path = f"{proxy_processor._temp_dir}/test-job-789_thumb_{i}.jpg"
            with open(path, 'wb') as f:
                f.write(b'dummy thumb data')
            thumbnails.append({
                "path": path,
                "index": i,
                "size": 10000 + i * 1000,
                "width": 320,
                "height": 180,
                "format": "jpg"
            })
        
        # Mock FFmpeg service methods
        proxy_processor.ffmpeg_service.generate_thumbnails = AsyncMock(return_value={
            "count": 3,
            "thumbnails": thumbnails,
            "method": "interval",
            "total_size": sum(t["size"] for t in thumbnails)
        })
        
        result = await proxy_processor._process_thumbnail_batch(job)
        
        assert result["job_id"] == "test-job-789"
        assert result["asset_id"] == "asset-101"
        assert result["proxy_type"] == "thumbnail_batch"
        assert result["count"] == 3
        assert len(result["thumbnails"]) == 3
        assert result["method"] == "interval"
    
    @pytest.mark.asyncio
    async def test_process_contact_sheet_job(self, proxy_processor):
        """Test processing contact sheet job"""
        job = ProxyJob(
            job_id="test-job-contact",
            asset_id="asset-contact",
            input_path="/test/video.mp4",
            job_type="contact_sheet",
            parameters={
                "grid_size": [4, 3],
                "thumb_width": 200,
                "thumb_height": 112,
                "include_timestamps": True
            },
            priority=JobPriority.NORMAL
        )
        
        # Mock FFmpeg service methods
        proxy_processor.ffmpeg_service.generate_contact_sheet = AsyncMock(return_value={
            "path": f"{proxy_processor._temp_dir}/test-job-contact_contact_sheet.jpg",
            "size": 150000,
            "dimensions": {"width": 830, "height": 351},
            "grid": {"columns": 4, "rows": 3},
            "thumbnail_count": 12,
            "thumbnail_size": {"width": 200, "height": 112}
        })
        
        # Create dummy file
        output_path = f"{proxy_processor._temp_dir}/test-job-contact_contact_sheet.jpg"
        with open(output_path, 'wb') as f:
            f.write(b'dummy contact sheet')
        
        result = await proxy_processor._process_contact_sheet(job)
        
        assert result["job_id"] == "test-job-contact"
        assert result["asset_id"] == "asset-contact"
        assert result["proxy_type"] == "contact_sheet"
        assert result["grid"]["columns"] == 4
        assert result["grid"]["rows"] == 3
        assert result["thumbnail_count"] == 12
        assert result["storage_key"] == "test/storage/key.jpg"


class TestThumbnailMethods:
    """Test different thumbnail selection methods"""
    
    @pytest.mark.asyncio
    async def test_scene_detection_method(self, mock_ffmpeg_service):
        """Test thumbnail generation with scene detection"""
        # Mock get_media_info
        mock_ffmpeg_service.get_media_info = AsyncMock(return_value={
            "duration": 60.0,
            "streams": [{"codec_type": "video"}]
        })
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'', b''))
            mock_subprocess.return_value = mock_process
            
            # Test scene detection filter is used
            await mock_ffmpeg_service.generate_thumbnails(
                input_path="/test/video.mp4",
                output_pattern="/tmp/scene_%d.jpg",
                count=5,
                method="scene"
            )
            
            # Verify scene detection filter was used
            args = mock_subprocess.call_args[0]
            assert any("select='gt(scene,0.3)'" in arg for arg in args)
    
    @pytest.mark.asyncio
    async def test_keyframe_method(self, mock_ffmpeg_service):
        """Test thumbnail generation with keyframe selection"""
        # Mock get_media_info
        mock_ffmpeg_service.get_media_info = AsyncMock(return_value={
            "duration": 60.0,
            "streams": [{"codec_type": "video"}]
        })
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'', b''))
            mock_subprocess.return_value = mock_process
            
            # Test keyframe filter is used
            await mock_ffmpeg_service.generate_thumbnails(
                input_path="/test/video.mp4",
                output_pattern="/tmp/keyframe_%d.jpg",
                count=5,
                method="keyframe"
            )
            
            # Verify keyframe filter was used
            args = mock_subprocess.call_args[0]
            assert any("select='eq(pict_type,I)'" in arg for arg in args)