"""
Tests for CDN API endpoints
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.main import app
from src.services.cdn_manager import GlobalCDNManager
from src.models.schemas import (
    CDNProvider,
    CDNDistribution,
    CDNMetrics,
    PurgeRequest,
    PrefetchRequest,
    CDNProviderType
)


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_cdn_manager(monkeypatch):
    """Mock CDN manager for testing"""
    manager = Mock(spec=GlobalCDNManager)
    
    # Mock providers
    manager.providers = {
        "cloudfront": CDNProvider(
            provider_id="cloudfront",
            provider_type=CDNProviderType.CLOUDFRONT,
            name="AWS CloudFront",
            enabled=True
        )
    }
    
    # Mock distributions
    manager.distributions = {}
    
    # Mock methods
    manager.create_distribution = AsyncMock()
    manager.update_distribution = AsyncMock()
    manager.purge_cache = AsyncMock()
    manager.prefetch_content = AsyncMock()
    manager.get_metrics = AsyncMock()
    manager.get_edge_locations = AsyncMock(return_value=[])
    manager.optimize_content = AsyncMock()
    manager.get_bandwidth_usage = AsyncMock(return_value=[])
    
    # Patch the dependency
    async def mock_get_cdn_manager():
        return manager
    
    monkeypatch.setattr("src.api.routes.get_cdn_manager", mock_get_cdn_manager)
    monkeypatch.setattr("src.core.deps.get_cdn_manager", mock_get_cdn_manager)
    
    return manager


@pytest.fixture
def auth_headers():
    """Create authentication headers"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_current_user(monkeypatch):
    """Mock current user for testing"""
    user = Mock()
    user.id = "user123"
    user.username = "testuser"
    
    async def mock_get_current_user():
        return user
    
    monkeypatch.setattr("src.api.routes.get_current_user", mock_get_current_user)
    monkeypatch.setattr("src.core.deps.get_current_user", mock_get_current_user)
    
    return user


class TestCDNAPI:
    """Test CDN API endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_providers(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test listing CDN providers"""
        response = await client.get("/api/v1/cdn/providers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider_id"] == "cloudfront"
    
    @pytest.mark.asyncio
    async def test_create_distribution(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test creating a CDN distribution"""
        distribution = CDNDistribution(
            distribution_id="dist-123",
            provider_id="cloudfront",
            name="test-distribution",
            status="deploying",
            origins=[],
            cache_rules=[]
        )
        
        mock_cdn_manager.create_distribution.return_value = distribution
        
        request_data = {
            "name": "test-distribution",
            "origins": [{
                "origin_id": "origin-1",
                "domain_name": "origin.example.com"
            }],
            "cache_rules": [{
                "path_pattern": "*.jpg",
                "cache_enabled": True
            }],
            "provider_id": "cloudfront"
        }
        
        response = await client.post(
            "/api/v1/cdn/distributions",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["distribution_id"] == "dist-123"
        assert data["name"] == "test-distribution"
    
    @pytest.mark.asyncio
    async def test_get_distribution(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test getting a CDN distribution"""
        distribution = CDNDistribution(
            distribution_id="dist-123",
            provider_id="cloudfront",
            name="test-distribution",
            status="deployed",
            origins=[],
            cache_rules=[]
        )
        
        mock_cdn_manager.distributions["dist-123"] = distribution
        
        response = await client.get("/api/v1/cdn/distributions/dist-123", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["distribution_id"] == "dist-123"
    
    @pytest.mark.asyncio
    async def test_update_distribution(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test updating a CDN distribution"""
        distribution = CDNDistribution(
            distribution_id="dist-123",
            provider_id="cloudfront",
            name="test-distribution",
            status="deployed",
            enabled=True,
            origins=[],
            cache_rules=[]
        )
        
        mock_cdn_manager.update_distribution.return_value = distribution
        
        update_data = {
            "enabled": False,
            "cache_rules": [{
                "path_pattern": "*.mp4",
                "cache_enabled": True,
                "default_ttl": 7200
            }]
        }
        
        response = await client.put(
            "/api/v1/cdn/distributions/dist-123",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        mock_cdn_manager.update_distribution.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_purge_cache(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test purging CDN cache"""
        purge_request = PurgeRequest(
            request_id="purge-123",
            distribution_id="dist-123",
            paths=["/images/*", "/videos/*"],
            status="pending"
        )
        
        mock_cdn_manager.purge_cache.return_value = purge_request
        
        request_data = {
            "paths": ["/images/*", "/videos/*"]
        }
        
        response = await client.post(
            "/api/v1/cdn/distributions/dist-123/purge",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "purge-123"
        assert len(data["paths"]) == 2
    
    @pytest.mark.asyncio
    async def test_prefetch_content(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test prefetching content"""
        prefetch_request = PrefetchRequest(
            request_id="prefetch-123",
            distribution_id="dist-123",
            urls=["https://example.com/video1.mp4"],
            priority="high",
            status="pending"
        )
        
        mock_cdn_manager.prefetch_content.return_value = prefetch_request
        
        request_data = {
            "urls": ["https://example.com/video1.mp4"],
            "priority": "high"
        }
        
        response = await client.post(
            "/api/v1/cdn/distributions/dist-123/prefetch",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "prefetch-123"
        assert data["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test getting CDN metrics"""
        metrics = CDNMetrics(
            distribution_id="dist-123",
            period_start=datetime.utcnow() - timedelta(hours=1),
            period_end=datetime.utcnow(),
            requests_total=1000000,
            cache_hit_rate=0.95
        )
        
        mock_cdn_manager.get_metrics.return_value = metrics
        
        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = datetime.utcnow().isoformat()
        
        response = await client.get(
            f"/api/v1/cdn/distributions/dist-123/metrics?start_time={start_time}&end_time={end_time}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["distribution_id"] == "dist-123"
        assert data["requests_total"] == 1000000
        assert data["cache_hit_rate"] == 0.95
    
    @pytest.mark.asyncio
    async def test_get_edge_locations(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test getting edge locations"""
        response = await client.get("/api/v1/cdn/edge-locations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/api/v1/cdn/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cdn"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client, mock_cdn_manager, mock_current_user, auth_headers):
        """Test error handling"""
        # Test 404 error
        response = await client.get("/api/v1/cdn/distributions/nonexistent", headers=auth_headers)
        assert response.status_code == 404
        
        # Test validation error
        response = await client.post(
            "/api/v1/cdn/distributions",
            json={"invalid": "data"},
            headers=auth_headers
        )
        assert response.status_code == 422