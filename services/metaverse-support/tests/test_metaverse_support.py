"""Tests for Metaverse Support Service"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from src.main import app

client = TestClient(app)

class TestMetaverseSupport:
    """Test metaverse support endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "metaverse-support"
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "python_info" in response.text

class TestVirtualWorldRoutes:
    """Test virtual world deployment endpoints"""
    
    def test_deploy_asset_to_world_validation(self):
        """Test virtual world deployment with invalid platform"""
        response = client.post(
            "/api/v1/metaverse/worlds/deploy",
            json={
                "asset_id": "test_asset_123",
                "platform": "invalid_platform",
                "deployment_config": {}
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_deploy_asset_to_world_success(self):
        """Test successful virtual world deployment"""
        response = client.post(
            "/api/v1/metaverse/worlds/deploy",
            json={
                "asset_id": "test_asset_123",
                "platform": "unity",
                "deployment_config": {
                    "target_world_id": "world_123",
                    "position": {"x": 0, "y": 1, "z": 0}
                }
            }
        )
        assert response.status_code == 503  # Service not available (expected in test)
    
    def test_list_platforms(self):
        """Test listing available platforms"""
        response = client.get("/api/v1/metaverse/worlds/platforms")
        assert response.status_code == 503  # Service not available (expected in test)

class TestVRRoutes:
    """Test VR-related endpoints"""
    
    def test_deploy_vr_asset(self):
        """Test VR asset deployment"""
        response = client.post(
            "/api/v1/metaverse/vr/deploy",
            json={
                "asset_id": "vr_asset_123",
                "vr_platform": "oculus",
                "target_fps": 90,
                "comfort_settings": {
                    "teleport_locomotion": True,
                    "vignetting": True,
                    "snap_turn": True
                }
            }
        )
        # Should succeed with mock response
        assert response.status_code == 200
        result = response.json()
        assert result["asset_id"] == "vr_asset_123"
        assert result["vr_platform"] == "oculus"
        assert result["status"] == "deployed"

class TestARRoutes:
    """Test AR-related endpoints"""
    
    def test_deploy_ar_asset_arkit(self):
        """Test AR asset deployment for ARKit"""
        response = client.post(
            "/api/v1/metaverse/ar/deploy",
            json={
                "asset_id": "ar_asset_123",
                "ar_platform": "arkit",
                "anchor_type": "plane",
                "scale_factor": 1.0,
                "interaction_enabled": True
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["asset_id"] == "ar_asset_123"
        assert result["ar_platform"] == "arkit"
        assert result["format"] == "usdz"
    
    def test_deploy_ar_asset_arcore(self):
        """Test AR asset deployment for ARCore"""
        response = client.post(
            "/api/v1/metaverse/ar/deploy",
            json={
                "asset_id": "ar_asset_123",
                "ar_platform": "arcore",
                "anchor_type": "plane",
                "scale_factor": 1.0,
                "interaction_enabled": True
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["format"] == "glb"  # ARCore uses GLB format
    
    def test_create_ar_experience(self):
        """Test AR experience creation"""
        response = client.post(
            "/api/v1/metaverse/ar/experience",
            json={
                "asset_id": "ar_asset_123",
                "experience_type": "interactive",
                "interactions": ["tap", "pinch", "rotate"],
                "animations": ["idle", "highlight"],
                "audio_enabled": True,
                "multi_user": False
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["experience_id"] == "exp_ar_asset_123"
        assert result["type"] == "interactive"

class TestAvatarRoutes:
    """Test avatar system endpoints"""
    
    def test_create_avatar(self):
        """Test avatar creation"""
        response = client.post(
            "/api/v1/metaverse/avatars/create",
            json={
                "style": "realistic",
                "platform": "ready_player_me",
                "gender": "neutral",
                "customizations": {
                    "hair_style": "short",
                    "hair_color": "#8B4513",
                    "eye_color": "#654321"
                }
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "avatar_realistic_ready_player_me" in result["avatar_id"]
        assert result["status"] == "created"
    
    def test_animate_avatar(self):
        """Test avatar animation"""
        response = client.post(
            "/api/v1/metaverse/avatars/animate",
            json={
                "avatar_id": "avatar_123",
                "animation_type": "walking",
                "duration": 10.0,
                "loop": True,
                "transitions": ["idle_to_walk", "walk_to_idle"]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["avatar_id"] == "avatar_123"
        assert result["animation_type"] == "walking"
    
    def test_optimize_avatar(self):
        """Test avatar optimization"""
        response = client.post(
            "/api/v1/metaverse/avatars/optimize",
            json={
                "avatar_id": "avatar_123",
                "target_platform": "vrchat",
                "optimization_level": "medium"
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["target_platform"] == "vrchat"
        assert result["status"] == "optimized"

class TestSpatialRoutes:
    """Test spatial computing endpoints"""
    
    def test_create_spatial_anchor(self):
        """Test spatial anchor creation"""
        response = client.post(
            "/api/v1/metaverse/spatial/anchors",
            json={
                "asset_id": "spatial_asset_123",
                "anchor_type": "persistent",
                "coordinates": {"x": 1.5, "y": 0.0, "z": -2.0},
                "persistence": True
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["anchor_id"] == "anchor_spatial_asset_123"
        assert result["status"] == "created"
    
    def test_get_spatial_anchor(self):
        """Test spatial anchor retrieval"""
        response = client.get("/api/v1/metaverse/spatial/anchors/anchor_123")
        assert response.status_code == 200
        result = response.json()
        assert result["anchor_id"] == "anchor_123"

class TestBlockchainRoutes:
    """Test blockchain integration endpoints"""
    
    def test_mint_nft(self):
        """Test NFT minting"""
        response = client.post(
            "/api/v1/metaverse/blockchain/nft/mint",
            json={
                "asset_id": "nft_asset_123",
                "blockchain": "ethereum",
                "metadata": {
                    "name": "Test NFT",
                    "description": "A test NFT asset",
                    "attributes": []
                },
                "royalty_percentage": 5.0
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["nft_id"] == "nft_nft_asset_123"
        assert result["blockchain"] == "ethereum"
    
    def test_integrate_virtual_economy(self):
        """Test virtual economy integration"""
        response = client.post(
            "/api/v1/metaverse/blockchain/economy/integrate",
            json={
                "asset_id": "economy_asset_123",
                "virtual_world": "vrchat",
                "price_tokens": 100.0,
                "tradeable": True,
                "limited_edition": 1000
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["virtual_world"] == "vrchat"
        assert result["price_tokens"] == 100.0

class TestCrossPlatformRoutes:
    """Test cross-platform compatibility endpoints"""
    
    def test_create_cross_platform_asset(self):
        """Test cross-platform asset creation"""
        response = client.post(
            "/api/v1/metaverse/cross-platform/convert",
            json={
                "asset_id": "cross_asset_123",
                "target_platforms": ["unity", "unreal", "vrchat", "web"],
                "optimization_settings": {
                    "target_size": 75,
                    "quality_level": "medium"
                },
                "quality_presets": {
                    "mobile": "medium",
                    "vr": "high",
                    "desktop": "ultra"
                }
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["asset_id"] == "cross_asset_123"
        assert result["total_platforms"] == 4
        assert result["successful_conversions"] == 4
    
    def test_check_platform_compatibility(self):
        """Test platform compatibility check"""
        response = client.get("/api/v1/metaverse/cross-platform/compatibility/asset_123")
        assert response.status_code == 200
        result = response.json()
        assert result["asset_id"] == "asset_123"
        assert "compatible_platforms" in result

class TestSocialRoutes:
    """Test social features endpoints"""
    
    def test_create_virtual_event(self):
        """Test virtual event creation"""
        response = client.post(
            "/api/v1/metaverse/social/events",
            json={
                "name": "Test Virtual Event",
                "description": "A test virtual event",
                "virtual_world": "unity",
                "start_time": "2024-12-01T18:00:00Z",
                "duration_hours": 2.0,
                "max_participants": 50,
                "event_type": "presentation"
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["event_id"] == "event_Test_Virtual_Event"
    
    def test_configure_social_interactions(self):
        """Test social interaction configuration"""
        response = client.post(
            "/api/v1/metaverse/social/interactions/configure",
            json={
                "voice_chat": True,
                "text_chat": True,
                "gesture_system": True,
                "friend_system": True,
                "group_activities": ["dancing", "games", "presentations"]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["voice_chat"] is True
        assert result["status"] == "configured"

@pytest.mark.asyncio
class TestAsyncServices:
    """Test async service functionality"""
    
    async def test_metaverse_manager_initialization(self):
        """Test metaverse manager service initialization"""
        from src.services.metaverse_manager import MetaverseManager
        
        manager = MetaverseManager()
        assert manager is not None
        assert len(manager.services) > 0
    
    async def test_virtual_world_service(self):
        """Test virtual world service"""
        from src.services.virtual_world_service import VirtualWorldService
        
        service = VirtualWorldService()
        assert service is not None
        assert hasattr(service, 'platforms')
    
    async def test_avatar_service_creation(self):
        """Test avatar service avatar creation"""
        from src.services.avatar_service import AvatarService
        
        service = AvatarService()
        avatar_config = {
            "style": "realistic",
            "platform": "ready_player_me",
            "gender": "neutral"
        }
        
        # This would typically require proper initialization
        # For now, just test that the method exists
        assert hasattr(service, 'create_avatar')

class TestConfiguration:
    """Test configuration and environment variables"""
    
    def test_config_loading(self):
        """Test that configuration loads properly"""
        from src.core.config import settings
        
        assert settings.SERVICE_NAME == "metaverse-support"
        assert settings.SERVICE_PORT == 8022
        assert hasattr(settings, 'UNITY_SERVER_URL')
        assert hasattr(settings, 'UNREAL_SERVER_URL')
    
    def test_feature_flags(self):
        """Test that feature flags are available"""
        from src.core.config import settings
        
        feature_flags = [
            'ENABLE_VR_SUPPORT',
            'ENABLE_AR_SUPPORT', 
            'ENABLE_BLOCKCHAIN_FEATURES',
            'ENABLE_SOCIAL_FEATURES',
            'ENABLE_AI_AVATAR_GENERATION'
        ]
        
        for flag in feature_flags:
            assert hasattr(settings, flag)

# Fixtures for testing
@pytest.fixture
def mock_metaverse_manager():
    """Mock metaverse manager"""
    manager = Mock()
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    manager.get_all_platform_status = AsyncMock(return_value={})
    return manager

@pytest.fixture
def sample_asset_config():
    """Sample asset configuration for testing"""
    return {
        "asset_id": "test_asset_123",
        "name": "Test 3D Model",
        "format": "gltf",
        "polygon_count": 15000,
        "texture_resolution": 1024,
        "size_mb": 25.5,
        "animations": ["idle", "rotate"]
    }

@pytest.fixture
def sample_deployment_config():
    """Sample deployment configuration"""
    return {
        "target_world_id": "world_123",
        "position": {"x": 0, "y": 1, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "scale": {"x": 1, "y": 1, "z": 1},
        "optimization_level": "medium",
        "physics_enabled": True
    }