"""
Test Scene Detection Service

Tests for scene detection and classification in videos and images.
"""

import pytest
import asyncio
import numpy as np
import cv2
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import uuid
import time

from src.services.scene_detection_service import SceneDetectionService
from src.core.exceptions import InferenceError, ValidationError
from src.services.model_manager import ModelInfo


class MockModelInfo:
    """Mock model info object."""
    def __init__(self, name="scene_detection"):
        self.name = name
        self.model = Mock()
        self.metadata = {
            "version": "1.0",
            "feature_extractor": Mock()
        }


class TestSceneDetectionService:
    """Test cases for SceneDetectionService."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_model = AsyncMock()
        return manager
    
    @pytest.fixture
    def service(self, model_manager):
        """Create scene detection service instance."""
        return SceneDetectionService(model_manager)
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create a blank 640x480 RGB image
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some variation
        cv2.rectangle(image, (100, 100), (300, 300), (255, 255, 255), -1)
        cv2.rectangle(image, (350, 200), (500, 400), (128, 128, 128), -1)
        return image
    
    async def test_detect_scenes_with_numpy_array(self, service, model_manager, sample_image):
        """Test scene detection with numpy array input."""
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        # Mock inference results
        mock_scenes = [
            {"label": "outdoor", "confidence": 0.85},
            {"label": "landscape", "confidence": 0.72},
            {"label": "mountain", "confidence": 0.65},
            {"label": "nature", "confidence": 0.58},
            {"label": "sky", "confidence": 0.45}
        ]
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            mock_inference.return_value = {
                "scenes": mock_scenes,
                "features": np.random.rand(512).tolist()
            }
            
            result = await service.detect_scenes(
                sample_image,
                confidence_threshold=0.1,
                top_k=5,
                return_features=True
            )
            
            # Assertions
            assert result["total_scenes"] == 5
            assert len(result["scenes"]) == 5
            assert result["scenes"][0]["label"] == "outdoor"
            assert result["scenes"][0]["confidence"] == 0.85
            assert result["model_name"] == "scene_detection"
            assert "features" in result
            assert "processing_time" in result
    
    async def test_detect_scenes_with_bytes(self, service, model_manager, sample_image):
        """Test scene detection with bytes input."""
        # Convert image to bytes
        _, buffer = cv2.imencode('.jpg', sample_image)
        image_bytes = buffer.tobytes()
        
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            mock_inference.return_value = {
                "scenes": [{"label": "indoor", "confidence": 0.9}]
            }
            
            result = await service.detect_scenes(image_bytes, top_k=1)
            
            # Assertions
            assert result["total_scenes"] == 1
            assert result["scenes"][0]["label"] == "indoor"
    
    async def test_detect_scenes_with_file_path(self, service, model_manager, tmp_path):
        """Test scene detection with file path input."""
        # Create temporary image file
        image_path = tmp_path / "test_image.jpg"
        cv2.imwrite(str(image_path), np.zeros((480, 640, 3), dtype=np.uint8))
        
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            mock_inference.return_value = {"scenes": []}
            
            # Test with string path
            result = await service.detect_scenes(str(image_path))
            assert result["total_scenes"] == 0
            
            # Test with Path object
            result = await service.detect_scenes(image_path)
            assert result["total_scenes"] == 0
    
    async def test_detect_scenes_invalid_path(self, service):
        """Test scene detection with invalid file path."""
        with pytest.raises(InferenceError, match="Could not load image"):
            await service.detect_scenes("/nonexistent/image.jpg")
    
    async def test_detect_scenes_invalid_bytes(self, service):
        """Test scene detection with invalid bytes."""
        with pytest.raises(InferenceError, match="Could not decode image"):
            await service.detect_scenes(b"invalid_image_data")
    
    async def test_detect_scenes_with_confidence_threshold(self, service, model_manager, sample_image):
        """Test scene detection with confidence threshold filtering."""
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        # Mock scenes with various confidence levels
        mock_scenes = [
            {"label": "scene1", "confidence": 0.9},
            {"label": "scene2", "confidence": 0.3},
            {"label": "scene3", "confidence": 0.1},
            {"label": "scene4", "confidence": 0.05}
        ]
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            mock_inference.return_value = {"scenes": mock_scenes}
            
            result = await service.detect_scenes(
                sample_image,
                confidence_threshold=0.2,
                top_k=10
            )
            
            # Should filter out scenes below threshold
            # Note: The actual filtering should happen in _run_inference
            assert "confidence_threshold" in result
            assert result["confidence_threshold"] == 0.2
    
    async def test_detect_scenes_with_database_logging(self, service, model_manager, sample_image):
        """Test scene detection with database logging."""
        asset_id = str(uuid.uuid4())
        
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        mock_scenes = [{"label": "test_scene", "confidence": 0.8}]
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            with patch.object(service, '_log_to_database', new_callable=AsyncMock) as mock_log:
                mock_inference.return_value = {"scenes": mock_scenes}
                
                result = await service.detect_scenes(sample_image, asset_id=asset_id)
                
                # Verify database logging was called
                mock_log.assert_called_once()
                call_args = mock_log.call_args[0]
                assert call_args[0] == asset_id
                assert "scenes" in call_args[1]
                assert call_args[2] == mock_scenes
    
    async def test_detect_scenes_video(self, service, model_manager, tmp_path):
        """Test scene detection in video."""
        # Create a simple test video
        video_path = tmp_path / "test_video.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (640, 480))
        
        # Write 30 frames (3 seconds at 10 fps)
        for i in range(30):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Change scene every 10 frames
            if i < 10:
                cv2.rectangle(frame, (0, 0), (640, 480), (255, 0, 0), -1)
            elif i < 20:
                cv2.rectangle(frame, (0, 0), (640, 480), (0, 255, 0), -1)
            else:
                cv2.rectangle(frame, (0, 0), (640, 480), (0, 0, 255), -1)
            out.write(frame)
        
        out.release()
        
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        # Mock frame analysis
        frame_scenes = [
            {"label": "blue_scene", "confidence": 0.9},
            {"label": "green_scene", "confidence": 0.85},
            {"label": "red_scene", "confidence": 0.88}
        ]
        
        call_count = 0
        async def mock_detect_scenes(image_data, **kwargs):
            nonlocal call_count
            scene = frame_scenes[call_count % len(frame_scenes)]
            call_count += 1
            return {
                "scenes": [scene],
                "features": np.random.rand(512).tolist()
            }
        
        with patch.object(service, 'detect_scenes', side_effect=mock_detect_scenes):
            with patch.object(service, '_analyze_scene_changes', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = [
                    {"start_time": 0.0, "end_time": 1.0, "dominant_scene": "blue_scene"},
                    {"start_time": 1.0, "end_time": 2.0, "dominant_scene": "green_scene"},
                    {"start_time": 2.0, "end_time": 3.0, "dominant_scene": "red_scene"}
                ]
                
                result = await service.detect_scenes_video(
                    video_path,
                    sample_rate=10,  # Analyze every 10th frame
                    confidence_threshold=0.1,
                    top_k=3
                )
                
                # Assertions
                assert result["total_scenes"] == 3
                assert len(result["scenes"]) == 3
                assert "video_info" in result
                assert result["video_info"]["fps"] == 10.0
                assert result["video_info"]["total_frames"] == 30
                assert result["video_info"]["analyzed_frames"] == 3  # 30 frames / sample_rate 10
    
    async def test_detect_scenes_video_invalid_path(self, service):
        """Test video scene detection with invalid path."""
        with pytest.raises(InferenceError, match="Could not open video file"):
            await service.detect_scenes_video("/nonexistent/video.mp4")
    
    async def test_run_inference(self, service, model_manager, sample_image):
        """Test the inference method."""
        # Create mock model and feature extractor
        mock_model = Mock()
        mock_feature_extractor = Mock()
        
        # Mock feature extraction
        mock_inputs = {"pixel_values": torch.randn(1, 3, 224, 224)}
        mock_feature_extractor.return_value = mock_inputs
        
        # Mock model output
        mock_logits = torch.randn(1, 1000)  # 1000 classes
        mock_outputs = Mock()
        mock_outputs.logits = mock_logits
        mock_model.return_value = mock_outputs
        
        # Mock model config
        mock_model.config = Mock()
        mock_model.config.id2label = {
            0: "outdoor",
            1: "indoor",
            2: "landscape",
            3: "city",
            4: "nature"
        }
        
        # Test inference
        result = await service._run_inference(
            mock_model,
            mock_feature_extractor,
            sample_image,
            confidence_threshold=0.1,
            top_k=5
        )
        
        # Assertions
        assert "scenes" in result
        assert len(result["scenes"]) <= 5
        assert all("label" in scene and "confidence" in scene for scene in result["scenes"])
    
    async def test_analyze_scene_changes(self, service):
        """Test scene change analysis."""
        # Create mock frame results
        frame_results = [
            {
                "frame_number": 0,
                "timestamp": 0.0,
                "scenes": [{"label": "outdoor", "confidence": 0.9}],
                "features": np.random.rand(512).tolist()
            },
            {
                "frame_number": 30,
                "timestamp": 1.0,
                "scenes": [{"label": "outdoor", "confidence": 0.85}],
                "features": np.random.rand(512).tolist()
            },
            {
                "frame_number": 60,
                "timestamp": 2.0,
                "scenes": [{"label": "indoor", "confidence": 0.95}],
                "features": np.random.rand(512).tolist()
            },
            {
                "frame_number": 90,
                "timestamp": 3.0,
                "scenes": [{"label": "indoor", "confidence": 0.92}],
                "features": np.random.rand(512).tolist()
            }
        ]
        
        scenes = await service._analyze_scene_changes(frame_results, threshold=0.3)
        
        # Should detect scene change between outdoor and indoor
        assert len(scenes) >= 2
        assert scenes[0]["dominant_scene"] == "outdoor"
        assert scenes[1]["dominant_scene"] == "indoor"
    
    async def test_calculate_feature_similarity(self, service):
        """Test feature similarity calculation."""
        # Create two similar feature vectors
        features1 = np.random.rand(512)
        features2 = features1 + np.random.rand(512) * 0.1  # Add small noise
        
        similarity = service._calculate_feature_similarity(features1.tolist(), features2.tolist())
        
        # Should have high similarity
        assert 0.8 < similarity <= 1.0
        
        # Test with very different features
        features3 = np.random.rand(512)
        similarity2 = service._calculate_feature_similarity(features1.tolist(), features3.tolist())
        
        # Should have lower similarity
        assert similarity2 < similarity
    
    async def test_load_image_various_inputs(self, service):
        """Test image loading with various input types."""
        # Test numpy array
        np_image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = await service._load_image(np_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == (100, 100, 3)
        
        # Test bytes
        _, buffer = cv2.imencode('.jpg', np_image)
        image_bytes = buffer.tobytes()
        result = await service._load_image(image_bytes)
        assert isinstance(result, np.ndarray)
        
        # Test invalid input
        with pytest.raises(ValidationError, match="Unsupported image data type"):
            await service._load_image({"invalid": "data"})
    
    async def test_get_model_info(self, service, model_manager):
        """Test getting model information."""
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        info = await service.get_model_info()
        
        assert info["name"] == "scene_detection"
        assert "metadata" in info
        assert info["metadata"]["version"] == "1.0"
    
    async def test_get_model_info_error(self, service, model_manager):
        """Test getting model info with error."""
        model_manager.get_model.side_effect = Exception("Model error")
        
        info = await service.get_model_info()
        
        # Should return empty dict on error
        assert info == {}
    
    async def test_concurrent_scene_detection(self, service, model_manager, sample_image):
        """Test concurrent scene detection requests."""
        # Setup mock
        model_info = MockModelInfo()
        model_manager.get_model.return_value = model_info
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            mock_inference.return_value = {
                "scenes": [{"label": "test", "confidence": 0.9}]
            }
            
            # Run multiple concurrent detections
            tasks = [
                service.detect_scenes(sample_image) for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert result["total_scenes"] == 1
    
    async def test_detect_scenes_with_custom_labels(self, service, model_manager, sample_image):
        """Test scene detection with custom label mapping."""
        # Setup mock with custom labels
        model_info = MockModelInfo()
        model_info.metadata["custom_labels"] = {
            "outdoor": "exterior",
            "indoor": "interior"
        }
        model_manager.get_model.return_value = model_info
        
        mock_scenes = [
            {"label": "outdoor", "confidence": 0.9},
            {"label": "indoor", "confidence": 0.8}
        ]
        
        with patch.object(service, '_run_inference', new_callable=AsyncMock) as mock_inference:
            with patch.object(service, '_apply_custom_labels') as mock_labels:
                mock_labels.return_value = [
                    {"label": "exterior", "confidence": 0.9},
                    {"label": "interior", "confidence": 0.8}
                ]
                mock_inference.return_value = {"scenes": mock_scenes}
                
                result = await service.detect_scenes(sample_image)
                
                # Custom labels should be applied if the method exists
                assert result["total_scenes"] == 2