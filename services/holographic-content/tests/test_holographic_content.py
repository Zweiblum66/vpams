"""Tests for Holographic Content Service"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from src.main import app

client = TestClient(app)


class TestHolographicContent:
    """Test holographic content endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "holographic-content"
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "MAMS Holographic Content Service"
        assert "volumetric_capture" in data["capabilities"]
        assert "holographic_projection" in data["capabilities"]
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "python_info" in response.text


class TestDeviceEndpoints:
    """Test device listing endpoints"""
    
    def test_get_supported_devices(self):
        """Test getting supported devices"""
        response = client.get("/api/v1/holographic/devices")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "devices" in data
        assert "capture_devices" in data["devices"]
        assert "display_devices" in data["devices"]
    
    def test_get_capabilities(self):
        """Test getting holographic capabilities"""
        response = client.get("/api/v1/holographic/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "capabilities" in data


class TestCaptureEndpoints:
    """Test volumetric capture endpoints"""
    
    def test_start_capture_default(self):
        """Test starting capture with default settings"""
        response = client.post(
            "/api/v1/holographic/capture/start",
            json={"device": "azure_kinect"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "capture_id" in data
        assert data["device"] == "azure_kinect"
        assert data["status"] == "started"
    
    def test_start_capture_with_config(self):
        """Test starting capture with custom config"""
        response = client.post(
            "/api/v1/holographic/capture/start",
            json={
                "device": "intel_realsense",
                "duration": 30,
                "fps": 60,
                "quality": "ultra"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device"] == "intel_realsense"
    
    def test_start_capture_invalid_device(self):
        """Test starting capture with invalid device"""
        response = client.post(
            "/api/v1/holographic/capture/start",
            json={"device": "invalid_device"}
        )
        assert response.status_code == 422  # Validation error


class TestProcessingEndpoints:
    """Test holographic processing endpoints"""
    
    def test_neural_rendering(self):
        """Test neural rendering processing"""
        response = client.post(
            "/api/v1/holographic/processing/neural",
            json={
                "hologram_id": "test_hologram_123",
                "model": "instant_ngp",
                "quality": "high"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "render_id" in data
        assert data["model"] == "instant_ngp"
        assert data["status"] == "started"
    
    def test_neural_rendering_gaussian_splatting(self):
        """Test Gaussian Splatting rendering"""
        response = client.post(
            "/api/v1/holographic/processing/neural",
            json={
                "hologram_id": "test_hologram_123",
                "model": "gaussian_splatting",
                "quality": "ultra"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "gaussian_splatting"
    
    def test_light_field_processing(self):
        """Test light field processing"""
        response = client.post(
            "/api/v1/holographic/processing/light-field",
            json={
                "hologram_id": "test_hologram_123",
                "target_display": "looking_glass_portrait",
                "ai_enhance": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "process_id" in data
        assert data["hologram_id"] == "test_hologram_123"


class TestDisplayEndpoints:
    """Test holographic display endpoints"""
    
    def test_light_field_display(self):
        """Test light field display"""
        response = client.post(
            "/api/v1/holographic/display/light-field",
            json={
                "hologram_id": "test_hologram_123",
                "device": "looking_glass_8k",
                "zoom": 1.5,
                "brightness": 0.9
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "display_id" in data
        assert data["device"] == "looking_glass_8k"
        assert data["status"] == "started"
    
    def test_holographic_projection(self):
        """Test holographic projection"""
        response = client.post(
            "/api/v1/holographic/display/projection",
            json={
                "hologram_id": "test_hologram_123",
                "device": "hololens2",
                "position": [0, 1, 3],
                "scale": [2, 2, 2]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "projection_id" in data
        assert data["device"] == "hololens2"


class TestInteractionEndpoints:
    """Test spatial interaction endpoints"""
    
    def test_create_interaction_session(self):
        """Test creating interaction session"""
        response = client.post(
            "/api/v1/holographic/interaction/session",
            json={
                "hologram_id": "test_hologram_123",
                "methods": ["hand_tracking", "voice_control"],
                "haptic_enabled": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "hand_tracking" in data["enabled_methods"]
        assert "voice_control" in data["enabled_methods"]
    
    def test_process_gesture(self):
        """Test processing hand gesture"""
        # First create a session
        session_response = client.post(
            "/api/v1/holographic/interaction/session",
            json={"hologram_id": "test_hologram_123"}
        )
        session_id = session_response.json()["session_id"]
        
        # Process gesture
        response = client.post(
            f"/api/v1/holographic/interaction/{session_id}/gesture",
            json={
                "gesture_type": "tap",
                "hand": "right",
                "confidence": 0.95
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gesture_received"] == "tap"
    
    def test_process_voice_command(self):
        """Test processing voice command"""
        # First create a session
        session_response = client.post(
            "/api/v1/holographic/interaction/session",
            json={"hologram_id": "test_hologram_123"}
        )
        session_id = session_response.json()["session_id"]
        
        # Process voice command
        response = client.post(
            f"/api/v1/holographic/interaction/{session_id}/voice",
            json={
                "command": "rotate left",
                "confidence": 0.88,
                "language": "en"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "rotate left"
        assert data["action"] == "rotate_hologram"


class TestStreamingEndpoints:
    """Test holographic streaming endpoints"""
    
    def test_start_webrtc_streaming(self):
        """Test starting WebRTC streaming"""
        response = client.post(
            "/api/v1/holographic/streaming/start",
            json={
                "hologram_id": "test_hologram_123",
                "protocol": "webrtc",
                "quality": "standard",
                "adaptive_bitrate": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "stream_id" in data
        assert data["protocol"] == "webrtc"
        assert "endpoints" in data
        assert "websocket" in data["endpoints"]
    
    def test_start_adaptive_streaming(self):
        """Test starting HLS/DASH streaming"""
        response = client.post(
            "/api/v1/holographic/streaming/start",
            json={
                "hologram_id": "test_hologram_123",
                "protocol": "hls_dash",
                "quality": "high"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["protocol"] == "hls_dash"
        assert "hls_playlist" in data["endpoints"]
        assert "dash_manifest" in data["endpoints"]
    
    def test_add_viewer_to_stream(self):
        """Test adding viewer to stream"""
        # First start a stream
        stream_response = client.post(
            "/api/v1/holographic/streaming/start",
            json={
                "hologram_id": "test_hologram_123",
                "protocol": "webrtc"
            }
        )
        stream_id = stream_response.json()["stream_id"]
        
        # Add viewer
        response = client.post(
            f"/api/v1/holographic/streaming/{stream_id}/viewer",
            json={
                "device": "oculus_quest_2",
                "location": "US-West",
                "quality": "high",
                "bandwidth": 50000000
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "viewer_id" in data
        assert data["status"] == "connected"


@pytest.mark.asyncio
class TestAsyncServices:
    """Test async service functionality"""
    
    async def test_hologram_manager_initialization(self):
        """Test hologram manager initialization"""
        from src.services.hologram_manager import HologramManager
        
        manager = HologramManager()
        assert manager is not None
        assert not manager.initialized
        
        # Mock initialization
        with patch.object(manager, 'initialize', new_callable=AsyncMock):
            await manager.initialize()
            manager.initialize.assert_called_once()
    
    async def test_volumetric_capture_service(self):
        """Test volumetric capture service"""
        from src.services.volumetric_capture_service import VolumetricCaptureService
        
        service = VolumetricCaptureService()
        assert service is not None
        assert not service.initialized
    
    async def test_neural_rendering_service(self):
        """Test neural rendering service"""
        from src.services.neural_rendering_service import NeuralRenderingService
        
        service = NeuralRenderingService()
        assert service is not None
        assert not service.initialized
    
    async def test_light_field_service(self):
        """Test light field service"""
        from src.services.light_field_service import LightFieldService
        
        service = LightFieldService()
        assert service is not None
        assert not service.initialized
    
    async def test_streaming_service(self):
        """Test streaming service"""
        from src.services.hologram_streaming_service import HologramStreamingService
        
        service = HologramStreamingService()
        assert service is not None
        assert not service.initialized


class TestConfiguration:
    """Test configuration and environment variables"""
    
    def test_config_loading(self):
        """Test that configuration loads properly"""
        from src.core.config import settings
        
        assert settings.SERVICE_NAME == "holographic-content"
        assert settings.SERVICE_PORT == 8023
        assert hasattr(settings, 'AZURE_KINECT_ENABLED')
        assert hasattr(settings, 'NEURAL_RADIANCE_FIELDS')
    
    def test_feature_flags(self):
        """Test that feature flags are available"""
        from src.core.config import settings
        
        feature_flags = [
            'ENABLE_VOLUMETRIC_CAPTURE',
            'ENABLE_LIGHT_FIELD_DISPLAY',
            'ENABLE_HOLOGRAPHIC_PROJECTION',
            'ENABLE_NEURAL_RENDERING',
            'ENABLE_REAL_TIME_STREAMING',
            'ENABLE_HAPTIC_FEEDBACK'
        ]
        
        for flag in feature_flags:
            assert hasattr(settings, flag)


# Fixtures
@pytest.fixture
def mock_hologram_manager():
    """Mock hologram manager"""
    manager = Mock()
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    manager.get_supported_devices = AsyncMock(return_value={
        "capture_devices": ["azure_kinect", "intel_realsense"],
        "display_devices": ["looking_glass_portrait"],
        "projection_devices": ["hololens2"]
    })
    return manager


@pytest.fixture
def sample_hologram_data():
    """Sample hologram data for testing"""
    return {
        "hologram_id": "test_hologram_123",
        "format": "point_cloud",
        "size_bytes": 125_000_000,
        "duration_seconds": 10.0,
        "metadata": {
            "capture_device": "azure_kinect",
            "resolution": "1024x1024",
            "fps": 30,
            "point_count": 1_000_000
        }
    }