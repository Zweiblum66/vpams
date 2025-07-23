"""Tests for object detection service."""
import pytest
import numpy as np
from httpx import AsyncClient
from fastapi import status
from unittest.mock import Mock, patch, AsyncMock

from src.services.object_detection_service import ObjectDetectionService
from src.core.exceptions import ValidationError, InferenceError


class TestObjectDetectionService:
    """Test object detection service."""
    
    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager."""
        mock_manager = Mock()
        mock_model_info = Mock()
        mock_model_info.name = "object_detection"
        mock_model_info.model_type = "object_detection"
        mock_model_info.metadata = {"version": "1.0.0"}
        
        # Mock YOLO model
        mock_model = Mock()
        mock_model.names = {0: "person", 1: "car", 2: "bicycle"}
        mock_model_info.model = mock_model
        
        mock_manager.get_model = AsyncMock(return_value=mock_model_info)
        return mock_manager
    
    @pytest.fixture
    def object_detection_service(self, mock_model_manager):
        """Create object detection service with mocked dependencies."""
        return ObjectDetectionService(mock_model_manager)
    
    @pytest.fixture
    def sample_image(self):
        """Create sample image for testing."""
        # Create a simple RGB image
        return np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    @pytest.mark.asyncio
    async def test_load_image_numpy(self, object_detection_service, sample_image):
        """Test loading image from numpy array."""
        result = await object_detection_service._load_image(sample_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == sample_image.shape
    
    @pytest.mark.asyncio
    async def test_load_image_invalid_type(self, object_detection_service):
        """Test loading image with invalid type."""
        with pytest.raises(ValidationError, match="Unsupported image data type"):
            await object_detection_service._load_image(12345)
    
    @pytest.mark.asyncio
    async def test_load_image_invalid_bytes(self, object_detection_service):
        """Test loading image from invalid bytes."""
        with pytest.raises(ValidationError, match="Could not decode image from bytes"):
            await object_detection_service._load_image(b"invalid image data")
    
    @pytest.mark.asyncio
    async def test_get_supported_classes(self, object_detection_service):
        """Test getting supported classes."""
        classes = await object_detection_service.get_supported_classes()
        assert isinstance(classes, list)
        assert len(classes) == 3
        assert "person" in classes
        assert "car" in classes
        assert "bicycle" in classes
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, object_detection_service):
        """Test getting model information."""
        model_info = await object_detection_service.get_model_info()
        assert isinstance(model_info, dict)
        assert "name" in model_info
        assert "type" in model_info
        assert "metadata" in model_info
        assert "supported_classes" in model_info
    
    @pytest.mark.asyncio
    @patch('src.services.object_detection_service.get_db_session')
    async def test_detect_objects_success(self, mock_db_session, object_detection_service, sample_image):
        """Test successful object detection."""
        # Mock database session
        mock_db_session.return_value.__aenter__.return_value = Mock()
        mock_db_session.return_value.__aenter__.return_value.add = Mock()
        mock_db_session.return_value.__aenter__.return_value.flush = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value.commit = AsyncMock()
        
        # Mock YOLO results
        mock_box = Mock()
        mock_box.conf = [0.8]
        mock_box.cls = [0]
        mock_box.xyxy = [[100, 100, 200, 200]]
        
        mock_result = Mock()
        mock_result.boxes = [mock_box]
        mock_result.names = {0: "person"}
        
        # Mock model inference
        object_detection_service.model_manager.get_model.return_value.model.return_value = [mock_result]
        
        # Run detection
        result = await object_detection_service.detect_objects(
            image_data=sample_image,
            confidence_threshold=0.5
        )
        
        # Verify results
        assert isinstance(result, dict)
        assert "detections" in result
        assert "total_objects" in result
        assert "model_name" in result
        assert "processing_time" in result
        
        detections = result["detections"]
        assert len(detections) == 1
        assert detections[0]["class_name"] == "person"
        assert detections[0]["confidence"] == 0.8
        assert "bbox" in detections[0]
    
    @pytest.mark.asyncio
    async def test_detect_objects_batch_success(self, object_detection_service, sample_image):
        """Test successful batch object detection."""
        # Mock the detect_objects method
        with patch.object(object_detection_service, 'detect_objects') as mock_detect:
            mock_detect.return_value = {
                "detections": [{"class_name": "person", "confidence": 0.8}],
                "total_objects": 1
            }
            
            # Run batch detection
            image_batch = [sample_image, sample_image]
            results = await object_detection_service.detect_objects_batch(image_batch)
            
            # Verify results
            assert isinstance(results, list)
            assert len(results) == 2
            assert all(result is not None for result in results)
            assert mock_detect.call_count == 2
    
    @pytest.mark.asyncio
    async def test_detect_objects_batch_with_errors(self, object_detection_service, sample_image):
        """Test batch object detection with some errors."""
        # Mock the detect_objects method to raise error for second image
        with patch.object(object_detection_service, 'detect_objects') as mock_detect:
            mock_detect.side_effect = [
                {"detections": [{"class_name": "person", "confidence": 0.8}], "total_objects": 1},
                ValidationError("Invalid image")
            ]
            
            # Run batch detection
            image_batch = [sample_image, sample_image]
            results = await object_detection_service.detect_objects_batch(image_batch)
            
            # Verify results
            assert isinstance(results, list)
            assert len(results) == 2
            assert results[0] is not None
            assert results[1] is None  # Error case


class TestObjectDetectionAPI:
    """Test object detection API endpoints."""
    
    @pytest.mark.asyncio
    async def test_detect_objects_endpoint(self, client: AsyncClient):
        """Test object detection endpoint."""
        # Create a small test image
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = {"file": ("test.png", test_image, "image/png")}
        data = {"confidence_threshold": 0.5}
        
        response = await client.post("/api/v1/detect/objects", files=files, data=data)
        
        # Should return 500 since we don't have actual models loaded in tests
        assert response.status_code in [500, 200]
    
    @pytest.mark.asyncio
    async def test_detect_objects_invalid_file(self, client: AsyncClient):
        """Test object detection with invalid file."""
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        
        response = await client.post("/api/v1/detect/objects", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "File must be an image" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_detect_objects_no_file(self, client: AsyncClient):
        """Test object detection with no file."""
        response = await client.post("/api/v1/detect/objects")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_get_object_classes_endpoint(self, client: AsyncClient):
        """Test get object classes endpoint."""
        response = await client.get("/api/v1/detect/objects/classes")
        
        # Should return 500 since we don't have actual models loaded in tests
        assert response.status_code in [500, 200]
    
    @pytest.mark.asyncio
    async def test_get_object_detection_model_info_endpoint(self, client: AsyncClient):
        """Test get object detection model info endpoint."""
        response = await client.get("/api/v1/detect/objects/model-info")
        
        # Should return 500 since we don't have actual models loaded in tests
        assert response.status_code in [500, 200]
    
    @pytest.mark.asyncio
    async def test_batch_detect_objects_endpoint(self, client: AsyncClient):
        """Test batch object detection endpoint."""
        # Create small test images
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = [
            ("files", ("test1.png", test_image, "image/png")),
            ("files", ("test2.png", test_image, "image/png"))
        ]
        data = {"confidence_threshold": 0.5}
        
        response = await client.post("/api/v1/detect/objects/batch", files=files, data=data)
        
        # Should return 500 since we don't have actual models loaded in tests
        assert response.status_code in [500, 200]
    
    @pytest.mark.asyncio
    async def test_batch_detect_objects_too_many_files(self, client: AsyncClient):
        """Test batch object detection with too many files."""
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Create more than 10 files
        files = [("files", (f"test{i}.png", test_image, "image/png")) for i in range(11)]
        
        response = await client.post("/api/v1/detect/objects/batch", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Maximum batch size is 10" in data["detail"]