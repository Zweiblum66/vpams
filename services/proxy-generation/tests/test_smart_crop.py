"""
Tests for smart cropping functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
from datetime import datetime
from PIL import Image
import numpy as np

from src.services.image_processing_service import ImageProcessingService, CropMode
from src.services.proxy_processor import ProxyProcessor
from src.services.queue_service import ProxyJob, JobStatus
from src.core.exceptions import InvalidMediaError, ProxyGenerationError


@pytest.fixture
def mock_image_service():
    """Create a mock image processing service"""
    service = Mock(spec=ImageProcessingService)
    
    # Mock smart crop
    service.smart_crop = AsyncMock(return_value={
        "output_path": "/tmp/cropped_image.jpg",
        "original_size": (3840, 2160),
        "output_size": (1280, 720),
        "crop_mode": "smart",
        "crop_box": (1280, 720, 2560, 1440),
        "quality": 95,
        "processing_time": 0.5
    })
    
    # Mock batch smart crop
    service.batch_smart_crop = AsyncMock(return_value=[
        {
            "input_path": "/path/to/image1.jpg",
            "output_path": "/tmp/cropped_1.jpg",
            "success": True,
            "original_size": (3840, 2160),
            "output_size": (1280, 720),
            "crop_mode": "face",
            "crop_box": (1000, 500, 2280, 1220),
            "processing_time": 0.6
        },
        {
            "input_path": "/path/to/image2.jpg",
            "output_path": "/tmp/cropped_2.jpg",
            "success": True,
            "original_size": (2560, 1440),
            "output_size": (1280, 720),
            "crop_mode": "smart",
            "crop_box": (640, 360, 1920, 1080),
            "processing_time": 0.4
        },
        {
            "input_path": "/path/to/image3.jpg",
            "success": False,
            "error": "Invalid image format"
        }
    ])
    
    return service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service"""
    service = Mock()
    service.generate_storage_key = Mock(return_value="smart_crop/asset123/1280x720_smart.jpg")
    service.store_file = AsyncMock(return_value="https://storage.example.com/smart_crop/asset123/1280x720_smart.jpg")
    return service


@pytest.fixture
def proxy_processor(mock_image_service, mock_storage_service):
    """Create a proxy processor with mocked services"""
    processor = ProxyProcessor()
    processor.image_service = mock_image_service
    processor.storage_service = mock_storage_service
    processor._temp_dir = tempfile.mkdtemp()
    return processor


@pytest.fixture
def sample_image():
    """Create a sample test image"""
    # Create a simple test image with a face-like pattern
    img = Image.new('RGB', (1920, 1080), color='white')
    pixels = img.load()
    
    # Draw a simple face pattern (for testing face detection)
    # Eyes
    for x in range(600, 700):
        for y in range(400, 450):
            pixels[x, y] = (0, 0, 0)
    
    for x in range(1220, 1320):
        for y in range(400, 450):
            pixels[x, y] = (0, 0, 0)
    
    # Mouth
    for x in range(760, 1160):
        for y in range(600, 650):
            pixels[x, y] = (0, 0, 0)
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        img.save(f.name, 'JPEG')
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


class TestSmartCropping:
    """Test smart cropping functionality"""
    
    @pytest.mark.asyncio
    async def test_smart_crop_request_validation(self):
        """Test smart crop request validation"""
        from src.api.routes import SmartCropRequest
        
        # Valid request
        request = SmartCropRequest(
            asset_id="asset123",
            input_path="/path/to/image.jpg",
            output_width=1280,
            output_height=720,
            crop_mode="smart",
            quality=95,
            face_padding=1.5,
            priority="normal"
        )
        
        assert request.asset_id == "asset123"
        assert request.output_width == 1280
        assert request.output_height == 720
        assert request.crop_mode == "smart"
        assert request.quality == 95
        assert request.face_padding == 1.5
        
    @pytest.mark.asyncio
    async def test_invalid_dimensions(self):
        """Test validation of output dimensions"""
        from src.api.routes import SmartCropRequest
        
        # Test invalid width
        with pytest.raises(ValueError):
            SmartCropRequest(
                asset_id="asset123",
                input_path="/path/to/image.jpg",
                output_width=0,  # Invalid
                output_height=720
            )
        
        # Test invalid height
        with pytest.raises(ValueError):
            SmartCropRequest(
                asset_id="asset123",
                input_path="/path/to/image.jpg",
                output_width=1280,
                output_height=10000  # Too large
            )
    
    @pytest.mark.asyncio
    async def test_crop_mode_validation(self):
        """Test crop mode validation"""
        from src.api.routes import SmartCropRequest
        
        # Valid crop modes
        valid_modes = ["center", "smart", "face", "saliency", "entropy", "edge"]
        for mode in valid_modes:
            request = SmartCropRequest(
                asset_id="asset123",
                input_path="/path/to/image.jpg",
                output_width=1280,
                output_height=720,
                crop_mode=mode
            )
            assert request.crop_mode == mode
        
        # Invalid crop mode
        with pytest.raises(ValueError):
            SmartCropRequest(
                asset_id="asset123",
                input_path="/path/to/image.jpg",
                output_width=1280,
                output_height=720,
                crop_mode="invalid_mode"
            )
    
    @pytest.mark.asyncio
    async def test_smart_crop_processing(self, proxy_processor):
        """Test smart crop job processing"""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_output = f.name
        
        # Mock the output path
        proxy_processor.image_service.smart_crop.return_value["output_path"] = temp_output
        
        # Create empty file to simulate cropped image
        open(temp_output, 'a').close()
        
        job = ProxyJob(
            job_id="test-job-1",
            asset_id="asset123",
            input_path="/path/to/image.jpg",
            job_type="smart_crop",
            parameters={
                "output_size": (1280, 720),
                "crop_mode": "smart",
                "quality": 95,
                "face_padding": 1.5
            },
            status=JobStatus.PROCESSING
        )
        
        result = await proxy_processor._process_smart_crop(job)
        
        assert result["job_id"] == "test-job-1"
        assert result["asset_id"] == "asset123"
        assert result["crop_type"] == "smart_crop"
        assert result["output_size"] == (1280, 720)
        assert result["crop_mode"] == "smart"
        assert result["quality"] == 95
        assert "storage_key" in result
        assert "storage_url" in result
        assert result["processing_time"] == 0.5
        
        # Verify file was deleted
        assert not os.path.exists(temp_output)
    
    @pytest.mark.asyncio
    async def test_smart_crop_with_focus_point(self, proxy_processor):
        """Test smart crop with custom focus point"""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_output = f.name
        
        proxy_processor.image_service.smart_crop.return_value["output_path"] = temp_output
        open(temp_output, 'a').close()
        
        job = ProxyJob(
            job_id="test-job-2",
            asset_id="asset124",
            input_path="/path/to/image.jpg",
            job_type="smart_crop",
            parameters={
                "output_size": (800, 600),
                "crop_mode": "center",
                "quality": 90,
                "focus_point": (0.3, 0.7)  # Custom focus point
            },
            status=JobStatus.PROCESSING
        )
        
        result = await proxy_processor._process_smart_crop(job)
        
        # Verify focus point was passed to service
        proxy_processor.image_service.smart_crop.assert_called_with(
            input_path="/path/to/image.jpg",
            output_size=(800, 600),
            crop_mode=CropMode.CENTER,
            quality=90,
            face_padding=1.5,
            custom_focus_point=(0.3, 0.7)
        )
        
        assert result["output_size"] == (800, 600)
        assert result["crop_mode"] == "center"
        
        # Cleanup
        if os.path.exists(temp_output):
            os.unlink(temp_output)
    
    @pytest.mark.asyncio
    async def test_batch_smart_crop_processing(self, proxy_processor):
        """Test batch smart crop processing"""
        # Create temporary output files
        temp_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_files.append(f.name)
                open(f.name, 'a').close()
        
        # Update mock to use temp files
        results = proxy_processor.image_service.batch_smart_crop.return_value
        for i, temp_file in enumerate(temp_files):
            if i < len(results) and results[i].get("success"):
                results[i]["output_path"] = temp_file
        
        job = ProxyJob(
            job_id="test-batch-1",
            asset_id="batch_20240115_120000",
            input_path="batch",
            job_type="batch_smart_crop",
            parameters={
                "images": [
                    {
                        "asset_id": "asset001",
                        "input_path": "/path/to/image1.jpg",
                        "output_size": [1280, 720],
                        "crop_mode": "face"
                    },
                    {
                        "asset_id": "asset002",
                        "input_path": "/path/to/image2.jpg",
                        "output_size": [1280, 720],
                        "crop_mode": "smart"
                    },
                    {
                        "asset_id": "asset003",
                        "input_path": "/path/to/image3.jpg",
                        "output_size": [1280, 720],
                        "crop_mode": "entropy"
                    }
                ],
                "default_output_size": (1280, 720),
                "default_crop_mode": "smart",
                "parallel_workers": 4
            },
            status=JobStatus.PROCESSING
        )
        
        result = await proxy_processor._process_batch_smart_crop(job)
        
        assert result["job_id"] == "test-batch-1"
        assert result["batch_type"] == "smart_crop"
        assert result["total_images"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        assert len(result["results"]) == 3
        
        # Check successful results
        assert result["results"][0]["success"] is True
        assert result["results"][0]["asset_id"] == "asset001"
        assert result["results"][1]["success"] is True
        assert result["results"][1]["asset_id"] == "asset002"
        
        # Check failed result
        assert result["results"][2]["success"] is False
        assert result["results"][2]["asset_id"] == "asset003"
        assert "error" in result["results"][2]
        
        # Cleanup
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_center_crop_calculation(self):
        """Test center crop calculation"""
        service = ImageProcessingService()
        
        # Test landscape image with portrait output
        crop_box = service._get_center_crop(
            img_size=(1920, 1080),
            output_size=(720, 1280)
        )
        assert crop_box == (600, 0, 1320, 1080)
        
        # Test portrait image with landscape output
        crop_box = service._get_center_crop(
            img_size=(1080, 1920),
            output_size=(1280, 720)
        )
        assert crop_box == (0, 600, 1080, 1320)
        
        # Test same aspect ratio
        crop_box = service._get_center_crop(
            img_size=(1920, 1080),
            output_size=(1280, 720)
        )
        assert crop_box == (0, 0, 1920, 1080)
    
    @pytest.mark.asyncio
    async def test_entropy_crop(self, sample_image):
        """Test entropy-based cropping"""
        service = ImageProcessingService()
        
        with Image.open(sample_image) as img:
            crop_box = service._get_entropy_crop(img, (800, 600))
            
            # Verify crop box dimensions
            assert crop_box[2] - crop_box[0] >= 800
            assert crop_box[3] - crop_box[1] >= 600
            
            # Verify crop box is within image bounds
            assert crop_box[0] >= 0
            assert crop_box[1] >= 0
            assert crop_box[2] <= img.size[0]
            assert crop_box[3] <= img.size[1]
    
    @pytest.mark.asyncio
    async def test_smart_crop_error_handling(self, proxy_processor):
        """Test error handling in smart crop processing"""
        # Make smart crop fail
        proxy_processor.image_service.smart_crop.side_effect = Exception("Processing failed")
        
        job = ProxyJob(
            job_id="test-job-fail",
            asset_id="asset999",
            input_path="/path/to/invalid.jpg",
            job_type="smart_crop",
            parameters={
                "output_size": (1280, 720),
                "crop_mode": "smart"
            },
            status=JobStatus.PROCESSING
        )
        
        with pytest.raises(ProxyGenerationError, match="Smart crop processing failed"):
            await proxy_processor._process_smart_crop(job)


class TestCropModes:
    """Test different crop modes"""
    
    @pytest.mark.asyncio
    async def test_face_detection_crop(self):
        """Test face detection cropping mode"""
        service = ImageProcessingService()
        
        # Create test image with mock face
        img = Image.new('RGB', (1920, 1080), color='white')
        
        # Mock face detection
        with patch('cv2.CascadeClassifier.detectMultiScale') as mock_detect:
            # Mock detected face at specific location
            mock_detect.return_value = np.array([[700, 300, 520, 520]])
            
            crop_box = await service._get_face_crop(img, (800, 600), padding=1.5)
            
            # Verify crop is centered on face
            face_center_x = 700 + 520 // 2
            crop_center_x = (crop_box[0] + crop_box[2]) // 2
            
            # Allow some tolerance
            assert abs(crop_center_x - face_center_x) < 100
    
    @pytest.mark.asyncio 
    async def test_saliency_crop(self):
        """Test saliency-based cropping"""
        service = ImageProcessingService()
        
        # Create test image
        img = Image.new('RGB', (1920, 1080), color='white')
        
        # Mock saliency detection
        with patch('cv2.saliency.StaticSaliencySpectralResidual_create') as mock_saliency:
            mock_detector = MagicMock()
            mock_saliency.return_value = mock_detector
            
            # Mock saliency map
            saliency_map = np.zeros((1080, 1920), dtype=np.float32)
            saliency_map[400:600, 800:1200] = 1.0  # High saliency region
            mock_detector.computeSaliency.return_value = (True, saliency_map)
            
            crop_box = await service._get_saliency_crop(img, (800, 600))
            
            # Verify crop includes salient region
            assert crop_box[0] < 1200  # Should include right edge of salient region
            assert crop_box[2] > 800   # Should include left edge of salient region
            assert crop_box[1] < 600   # Should include bottom edge of salient region
            assert crop_box[3] > 400   # Should include top edge of salient region
    
    @pytest.mark.asyncio
    async def test_edge_detection_crop(self):
        """Test edge detection cropping"""
        service = ImageProcessingService()
        
        # Create test image with edges
        img = Image.new('RGB', (1920, 1080), color='white')
        draw = Image.Draw.Draw(img)
        # Draw rectangle with strong edges
        draw.rectangle([800, 400, 1120, 680], outline='black', width=5)
        
        crop_box = await service._get_edge_crop(img, (800, 600))
        
        # Verify crop box is reasonable
        assert crop_box[2] - crop_box[0] >= 800
        assert crop_box[3] - crop_box[1] >= 600
        assert crop_box[0] >= 0
        assert crop_box[1] >= 0


class TestBatchProcessing:
    """Test batch processing functionality"""
    
    @pytest.mark.asyncio
    async def test_batch_request_validation(self):
        """Test batch smart crop request validation"""
        from src.api.routes import BatchSmartCropRequest
        
        request = BatchSmartCropRequest(
            images=[
                {
                    "asset_id": "asset123",
                    "input_path": "/path/to/image1.jpg",
                    "output_size": [800, 600],
                    "crop_mode": "face"
                },
                {
                    "asset_id": "asset124", 
                    "input_path": "/path/to/image2.jpg",
                    "focus_point": [0.3, 0.4]
                }
            ],
            default_output_width=1280,
            default_output_height=720,
            default_crop_mode="smart",
            parallel_workers=4,
            priority="normal"
        )
        
        assert len(request.images) == 2
        assert request.default_output_width == 1280
        assert request.default_output_height == 720
        assert request.default_crop_mode == "smart"
        assert request.parallel_workers == 4
    
    @pytest.mark.asyncio
    async def test_parallel_worker_validation(self):
        """Test parallel worker count validation"""
        from src.api.routes import BatchSmartCropRequest
        
        # Valid worker count
        request = BatchSmartCropRequest(
            images=[{"asset_id": "a1", "input_path": "/path/to/img.jpg"}],
            default_output_width=1280,
            default_output_height=720,
            parallel_workers=8
        )
        assert request.parallel_workers == 8
        
        # Invalid worker count (too high)
        with pytest.raises(ValueError):
            BatchSmartCropRequest(
                images=[{"asset_id": "a1", "input_path": "/path/to/img.jpg"}],
                default_output_width=1280,
                default_output_height=720,
                parallel_workers=20  # Too high
            )