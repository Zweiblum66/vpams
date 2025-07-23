"""
Test Facial Recognition Service

Tests for facial recognition and identification functionality.
"""

import pytest
import asyncio
import numpy as np
import cv2
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import base64
import hashlib

from src.services.facial_recognition_service import FacialRecognitionService
from src.core.exceptions import InferenceError, ValidationError


class MockModelInfo:
    """Mock model info object."""
    def __init__(self, name="face_detection", model_type="mtcnn"):
        self.name = name
        self.model_type = model_type
        self.metadata = {"version": "1.0"}
        self.model = Mock()


class TestFacialRecognitionService:
    """Test cases for FacialRecognitionService."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_model = AsyncMock()
        return manager
    
    @pytest.fixture
    def service(self, model_manager):
        """Create facial recognition service instance."""
        return FacialRecognitionService(model_manager)
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create a blank 640x480 RGB image
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some variation to make it more realistic
        cv2.rectangle(image, (100, 100), (300, 300), (255, 255, 255), -1)
        return image
    
    @pytest.fixture
    def sample_face_detections(self):
        """Create sample face detection results."""
        return [
            {
                "confidence": 0.95,
                "bbox": {
                    "x": 100, "y": 100, "width": 200, "height": 200,
                    "x1": 100, "y1": 100, "x2": 300, "y2": 300
                },
                "landmarks": {
                    "left_eye": (150, 150),
                    "right_eye": (250, 150),
                    "nose": (200, 200),
                    "mouth_left": (150, 250),
                    "mouth_right": (250, 250)
                }
            },
            {
                "confidence": 0.85,
                "bbox": {
                    "x": 400, "y": 200, "width": 150, "height": 150,
                    "x1": 400, "y1": 200, "x2": 550, "y2": 350
                }
            }
        ]
    
    async def test_detect_and_recognize_faces_with_numpy_array(self, service, model_manager, sample_image, sample_face_detections):
        """Test face detection and recognition with numpy array input."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {
                'confidence': 0.95,
                'box': [100, 100, 200, 200],
                'keypoints': {
                    'left_eye': (150, 150),
                    'right_eye': (250, 150),
                    'nose': (200, 200),
                    'mouth_left': (150, 250),
                    'mouth_right': (250, 250)
                }
            }
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test detection
        result = await service.detect_and_recognize_faces(
            sample_image,
            confidence_threshold=0.6,
            return_face_crops=True,
            return_embeddings=True
        )
        
        # Assertions
        assert result["total_faces"] == 1
        assert len(result["faces"]) == 1
        assert result["model_name"] == "face_detection"
        assert result["model_version"] == "1.0"
        assert "processing_time" in result
        
        face = result["faces"][0]
        assert face["detection"]["confidence"] == 0.95
        assert "face_id" in face
        assert "face_crop" in face
        assert "embedding" in face
    
    async def test_detect_and_recognize_faces_with_bytes(self, service, model_manager, sample_image):
        """Test face detection with bytes input."""
        # Convert image to bytes
        _, buffer = cv2.imencode('.jpg', sample_image)
        image_bytes = buffer.tobytes()
        
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test detection
        result = await service.detect_and_recognize_faces(image_bytes)
        
        # Assertions
        assert result["total_faces"] == 0
        assert len(result["faces"]) == 0
    
    async def test_detect_and_recognize_faces_with_file_path(self, service, model_manager, tmp_path):
        """Test face detection with file path input."""
        # Create a temporary image file
        image_path = tmp_path / "test_image.jpg"
        sample_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite(str(image_path), sample_image)
        
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test with string path
        result = await service.detect_and_recognize_faces(str(image_path))
        assert result["total_faces"] == 0
        
        # Test with Path object
        result = await service.detect_and_recognize_faces(image_path)
        assert result["total_faces"] == 0
    
    async def test_face_recognition_with_known_faces(self, service, model_manager, sample_image):
        """Test face recognition against known faces."""
        # Setup known faces
        known_embedding = np.random.rand(512)  # Mock embedding
        known_faces = {"person_1": known_embedding}
        
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock face embedding generation to return similar embedding
        with patch.object(service, '_get_face_embedding', return_value=known_embedding + np.random.rand(512) * 0.1):
            result = await service.detect_and_recognize_faces(
                sample_image,
                known_faces=known_faces,
                distance_threshold=0.6
            )
        
        # Assertions
        assert result["total_faces"] == 1
        face = result["faces"][0]
        assert face["recognition"] is not None
        assert face["recognition"]["person_id"] == "person_1"
        assert "distance" in face["recognition"]
        assert "confidence" in face["recognition"]
    
    async def test_add_known_face(self, service, model_manager, sample_image):
        """Test adding a known face to the database."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Add known face
        result = await service.add_known_face("person_1", sample_image)
        
        # Assertions
        assert result["person_id"] == "person_1"
        assert "face_id" in result
        assert "embedding_shape" in result
        assert result["status"] == "added"
        
        # Check if face was added to database
        db_info = await service.get_face_database_info()
        assert db_info["total_faces"] == 1
        assert "person_1" in db_info["persons"]
    
    async def test_add_known_face_with_bbox(self, service, model_manager, sample_image):
        """Test adding a known face with specified bounding box."""
        face_bbox = {"x1": 100, "y1": 100, "x2": 300, "y2": 300}
        
        # Add known face
        result = await service.add_known_face("person_2", sample_image, face_bbox)
        
        # Assertions
        assert result["person_id"] == "person_2"
        assert result["bbox"] == face_bbox
        assert result["status"] == "added"
    
    async def test_add_known_face_no_face_detected(self, service, model_manager, sample_image):
        """Test adding a known face when no face is detected."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[])  # No faces detected
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test
        with pytest.raises(ValidationError, match="No faces detected"):
            await service.add_known_face("person_3", sample_image)
    
    async def test_search_similar_faces(self, service, model_manager, sample_image):
        """Test searching for similar faces."""
        # Add some known faces first
        service.face_database = {
            "person_1": {"face_id": "face1", "embedding": np.random.rand(512), "bbox": {}},
            "person_2": {"face_id": "face2", "embedding": np.random.rand(512), "bbox": {}},
            "person_3": {"face_id": "face3", "embedding": np.random.rand(512), "bbox": {}}
        }
        
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Search for similar faces
        with patch.object(service, '_get_face_embedding', return_value=service.face_database["person_1"]["embedding"]):
            results = await service.search_similar_faces(sample_image, similarity_threshold=0.5, max_results=2)
        
        # Assertions
        assert len(results) <= 2
        if results:
            assert results[0]["person_id"] == "person_1"  # Should match itself
            assert results[0]["similarity"] >= 0.5
    
    async def test_search_similar_faces_no_face(self, service, model_manager, sample_image):
        """Test searching when no face is detected in query image."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[])  # No faces
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Search
        results = await service.search_similar_faces(sample_image)
        
        # Should return empty list
        assert results == []
    
    async def test_remove_known_face(self, service):
        """Test removing a known face from the database."""
        # Add a face
        service.face_database["person_1"] = {"face_id": "face1", "embedding": np.random.rand(512)}
        
        # Remove it
        result = await service.remove_known_face("person_1")
        assert result is True
        
        # Check it's gone
        db_info = await service.get_face_database_info()
        assert db_info["total_faces"] == 0
        
        # Try to remove non-existent face
        result = await service.remove_known_face("person_1")
        assert result is False
    
    async def test_opencv_haar_cascade_detection(self, service, model_manager, sample_image):
        """Test face detection using OpenCV Haar Cascade."""
        # Setup mock Haar cascade model
        mock_model = Mock()
        mock_model.detectMultiScale = Mock(return_value=np.array([[100, 100, 200, 200]]))
        # Remove the detect_faces attribute to simulate Haar cascade
        mock_model.detect_faces = None
        if hasattr(mock_model, 'detect_faces'):
            delattr(mock_model, 'detect_faces')
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Test detection
        result = await service.detect_and_recognize_faces(sample_image)
        
        # Assertions
        assert result["total_faces"] == 1
        assert len(result["faces"]) == 1
        face = result["faces"][0]
        assert face["detection"]["confidence"] == 1.0  # Haar cascades don't provide confidence
    
    async def test_invalid_image_data(self, service):
        """Test with invalid image data."""
        with pytest.raises(ValidationError, match="Unsupported image data type"):
            await service.detect_and_recognize_faces({"invalid": "data"})
    
    async def test_invalid_image_bytes(self, service):
        """Test with invalid image bytes."""
        invalid_bytes = b"not_an_image"
        
        with pytest.raises(ValidationError, match="Could not decode image from bytes"):
            await service.detect_and_recognize_faces(invalid_bytes)
    
    async def test_invalid_image_path(self, service):
        """Test with invalid image file path."""
        with pytest.raises(ValidationError, match="Could not load image from path"):
            await service.detect_and_recognize_faces("/nonexistent/path/to/image.jpg")
    
    async def test_face_id_generation(self, service):
        """Test face ID generation from embeddings."""
        embedding1 = np.random.rand(512)
        embedding2 = np.random.rand(512)
        
        face_id1 = service._generate_face_id(embedding1)
        face_id2 = service._generate_face_id(embedding2)
        face_id1_again = service._generate_face_id(embedding1)
        
        # Same embedding should produce same ID
        assert face_id1 == face_id1_again
        # Different embeddings should produce different IDs
        assert face_id1 != face_id2
        # Should be valid MD5 hash (32 hex characters)
        assert len(face_id1) == 32
        assert all(c in '0123456789abcdef' for c in face_id1)
    
    async def test_face_crop_encoding(self, service):
        """Test face crop encoding to base64."""
        face_crop = np.zeros((160, 160, 3), dtype=np.uint8)
        encoded = service._encode_face_crop(face_crop)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(encoded)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Invalid base64 encoding")
    
    async def test_lbp_calculation(self, service):
        """Test Local Binary Pattern calculation."""
        test_image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        lbp_result = service._calculate_lbp(test_image)
        
        # Should return same shape as input
        assert lbp_result.shape == test_image.shape
        assert lbp_result.dtype == np.uint8
    
    async def test_get_model_info(self, service, model_manager):
        """Test getting model information."""
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        info = await service.get_model_info()
        
        assert info["name"] == "face_detection"
        assert info["type"] == "mtcnn"
        assert info["face_database_size"] == 0
    
    async def test_get_model_info_error(self, service, model_manager):
        """Test getting model info with error."""
        model_manager.get_model.side_effect = Exception("Model error")
        
        info = await service.get_model_info()
        
        # Should return empty dict on error
        assert info == {}
    
    async def test_database_logging(self, service, model_manager, sample_image):
        """Test database logging functionality."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock database session
        with patch('src.services.facial_recognition_service.get_db_session') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            
            # Test with asset_id to trigger database logging
            result = await service.detect_and_recognize_faces(
                sample_image,
                asset_id="123e4567-e89b-12d3-a456-426614174000"
            )
            
            # Verify database methods were called
            assert mock_session.add.called
            assert mock_session.flush.called
            assert mock_session.commit.called
    
    async def test_processing_error_handling(self, service, model_manager, sample_image):
        """Test error handling during face processing."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Mock face embedding to raise error
        with patch.object(service, '_get_face_embedding', side_effect=Exception("Embedding error")):
            result = await service.detect_and_recognize_faces(sample_image)
        
        # Should continue processing and return empty results
        assert result["total_faces"] == 0
    
    async def test_concurrent_face_detection(self, service, model_manager, sample_image):
        """Test concurrent face detection requests."""
        # Setup mocks
        mock_model = Mock()
        mock_model.detect_faces = Mock(return_value=[
            {'confidence': 0.95, 'box': [100, 100, 200, 200]}
        ])
        
        model_info = MockModelInfo()
        model_info.model = mock_model
        model_manager.get_model.return_value = model_info
        
        # Run multiple concurrent detections
        tasks = [
            service.detect_and_recognize_faces(sample_image)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result["total_faces"] == 1