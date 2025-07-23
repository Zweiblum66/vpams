"""
Tests for API routes
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from src.core.cache_manager import CacheManager, CacheEntry
from src.core.origin_client import OriginClient
from src.api import routes


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns correct status"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "edge-cache"
        assert "timestamp" in data
        assert "location" in data


class TestCacheManagementEndpoints:
    """Test cache management endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client):
        """Test cache statistics endpoint"""
        # Mock cache manager
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.get_stats.return_value = {
            "hits": 100,
            "misses": 20,
            "hit_rate": 0.833,
            "total_size": 1024000
        }
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.get("/api/v1/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["hits"] == 100
        assert data["misses"] == 20
        assert "location" in data
        assert "region" in data
    
    @pytest.mark.asyncio
    async def test_clear_cache_all(self, client):
        """Test clearing all cache entries"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.backend = AsyncMock()
        mock_manager.backend.clear.return_value = 50
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.delete("/api/v1/cache")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cleared"] == 50
        assert data["pattern"] == "*"
    
    @pytest.mark.asyncio
    async def test_clear_cache_pattern(self, client):
        """Test clearing cache with pattern"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.invalidate_pattern.return_value = 10
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.delete("/api/v1/cache?pattern=asset:*")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cleared"] == 10
        assert data["pattern"] == "asset:*"
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, client):
        """Test cache invalidation"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.invalidate_pattern.return_value = 5
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.post(
                "/api/v1/cache/invalidate",
                json={
                    "type": "asset",
                    "id": "123",
                    "cascade": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resource_type"] == "asset"
        assert data["resource_id"] == "123"
        assert len(data["patterns"]) > 0
        assert data["cleared"] >= 0
    
    @pytest.mark.asyncio
    async def test_list_cache_keys(self, client):
        """Test listing cache keys"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.backend = AsyncMock()
        mock_manager.backend.get_keys.return_value = [
            "asset:123",
            "asset:456",
            "metadata:789"
        ]
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.get("/api/v1/cache/keys?pattern=asset:*")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pattern"] == "asset:*"
        assert data["total"] == 3
        assert len(data["keys"]) == 3


class TestCachedProxyEndpoint:
    """Test main caching proxy endpoint"""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, client):
        """Test cache hit scenario"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.get.return_value = (
            b"cached content",
            {"content-type": "text/plain"}
        )
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.get("/test/resource.txt")
        
        assert response.status_code == 200
        assert response.content == b"cached content"
        assert response.headers["X-Edge-Cache"] == "HIT"
        assert "X-Edge-Location" in response.headers
        assert "X-Edge-Response-Time" in response.headers
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, client):
        """Test cache miss scenario"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        mock_origin = AsyncMock(spec=OriginClient)
        mock_origin.fetch.return_value = (
            b"origin content",
            200,
            {"content-type": "text/plain"}
        )
        mock_origin.should_cache.return_value = True
        mock_origin.calculate_ttl.return_value = 300
        
        with patch.object(routes, 'cache_manager', mock_manager):
            with patch.object(routes, 'origin_client', mock_origin):
                response = await client.get("/test/resource.txt")
        
        assert response.status_code == 200
        assert response.content == b"origin content"
        assert response.headers["X-Edge-Cache"] == "MISS"
        
        # Should have cached the response
        mock_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conditional_request_not_modified(self, client):
        """Test conditional request returning 304"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_origin = AsyncMock(spec=OriginClient)
        
        mock_origin.validate_cached_content.return_value = (True, None, {})
        
        with patch.object(routes, 'cache_manager', mock_manager):
            with patch.object(routes, 'origin_client', mock_origin):
                response = await client.get(
                    "/test/resource.txt",
                    headers={"If-None-Match": '"abc123"'}
                )
        
        assert response.status_code == 304
        assert response.headers["X-Edge-Cache"] == "VALIDATED"
    
    @pytest.mark.asyncio
    async def test_range_request(self, client):
        """Test range request handling"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.get.return_value = (
            b"0123456789" * 10,  # 100 bytes
            {"content-type": "text/plain"}
        )
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.get(
                "/test/file.txt",
                headers={"Range": "bytes=10-19"}
            )
        
        assert response.status_code == 206
        assert response.content == b"0123456789"
        assert response.headers["Content-Range"] == "bytes 10-19/100"
        assert response.headers["Content-Length"] == "10"
    
    @pytest.mark.asyncio
    async def test_origin_error(self, client):
        """Test origin server error handling"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.get.return_value = None
        
        mock_origin = AsyncMock(spec=OriginClient)
        mock_origin.fetch.side_effect = Exception("Connection failed")
        
        with patch.object(routes, 'cache_manager', mock_manager):
            with patch.object(routes, 'origin_client', mock_origin):
                response = await client.get("/test/resource.txt")
        
        assert response.status_code == 502
        assert "Origin server error" in response.json()["detail"]


class TestPrefetchEndpoint:
    """Test prefetch endpoint"""
    
    @pytest.mark.asyncio
    async def test_prefetch_success(self, client):
        """Test successful prefetch"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.backend = AsyncMock()
        mock_manager.backend.exists.return_value = False
        mock_manager.set.return_value = True
        
        mock_origin = AsyncMock(spec=OriginClient)
        mock_origin.prefetch.return_value = b"prefetched content"
        
        with patch.object(routes, 'cache_manager', mock_manager):
            with patch.object(routes, 'origin_client', mock_origin):
                response = await client.post(
                    "/api/v1/cache/prefetch",
                    json={
                        "urls": ["/resource1.jpg", "/resource2.jpg"],
                        "priority": 6
                    }
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_prefetch_already_cached(self, client):
        """Test prefetch when content already cached"""
        mock_manager = AsyncMock(spec=CacheManager)
        mock_manager.generate_cache_key.return_value = "test_key"
        mock_manager.backend = AsyncMock()
        mock_manager.backend.exists.return_value = True
        
        with patch.object(routes, 'cache_manager', mock_manager):
            response = await client.post(
                "/api/v1/cache/prefetch",
                json={"urls": ["/cached.jpg"]}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"][0]["status"] == "already_cached"


class TestEdgeLocationEndpoints:
    """Test edge location endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_edge_locations(self, client):
        """Test getting edge locations"""
        response = await client.get("/api/v1/edge/locations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "current_location" in data
        assert "current_region" in data
        assert "regions" in data
        assert isinstance(data["regions"], dict)
    
    @pytest.mark.asyncio
    async def test_get_nearest_edge(self, client):
        """Test getting nearest edge location"""
        response = await client.get("/api/v1/edge/nearest/us")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_location"] == "us"
        assert "nearest_edge" in data