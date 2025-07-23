"""
Tests for origin client
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from datetime import datetime, timedelta

from src.core.origin_client import OriginClient, OriginError
from src.core.config import Settings


class TestOriginClient:
    """Test origin client"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, test_settings):
        """Test client initialization"""
        client = OriginClient(test_settings)
        
        assert client.settings == test_settings
        assert client.client is None
        
        await client.initialize()
        assert client.client is not None
        
        await client.shutdown()
        assert client.client._closed is True
    
    @pytest.mark.asyncio
    async def test_fetch_success(self, origin_client):
        """Test successful fetch from origin"""
        with patch.object(origin_client.client, 'get') as mock_get:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"test content"
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.raise_for_status = Mock()
            
            mock_get.return_value = mock_response
            
            content, status, headers = await origin_client.fetch("/test/path")
            
            assert content == b"test content"
            assert status == 200
            assert headers["content-type"] == "text/plain"
            
            # Check request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/test/path"
    
    @pytest.mark.asyncio
    async def test_fetch_404(self, origin_client):
        """Test 404 response handling"""
        with patch.object(origin_client.client, 'get') as mock_get:
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.content = b""
            mock_response.headers = {}
            mock_response.raise_for_status = Mock()
            
            mock_get.return_value = mock_response
            
            content, status, headers = await origin_client.fetch("/not/found")
            
            assert content == b""
            assert status == 404
    
    @pytest.mark.asyncio
    async def test_fetch_server_error_retry(self, origin_client):
        """Test retry on server error"""
        with patch.object(origin_client.client, 'get') as mock_get:
            # First two calls fail, third succeeds
            mock_response_error = Mock()
            mock_response_error.status_code = 500
            mock_response_error.raise_for_status = Mock(side_effect=OriginError("Server error"))
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.content = b"success"
            mock_response_success.headers = {}
            mock_response_success.raise_for_status = Mock()
            
            mock_get.side_effect = [
                mock_response_error,
                mock_response_error,
                mock_response_success
            ]
            
            # Should retry and eventually succeed
            content, status, headers = await origin_client.fetch("/retry/test")
            
            assert content == b"success"
            assert status == 200
            assert mock_get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_range(self, origin_client):
        """Test range request"""
        with patch.object(origin_client.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 206
            mock_response.content = b"partial content"
            mock_response.headers = {"content-range": "bytes 100-199/1000"}
            mock_response.raise_for_status = Mock()
            
            mock_get.return_value = mock_response
            
            content, status, headers = await origin_client.fetch_range(
                "/video.mp4",
                start=100,
                end=199
            )
            
            assert content == b"partial content"
            assert status == 206
            assert headers["content-range"] == "bytes 100-199/1000"
            
            # Check range header was set
            call_args = mock_get.call_args
            assert call_args[1]["headers"]["Range"] == "bytes=100-199"
    
    @pytest.mark.asyncio
    async def test_head_request(self, origin_client):
        """Test HEAD request"""
        with patch.object(origin_client.client, 'head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                "content-type": "image/png",
                "content-length": "12345"
            }
            
            mock_head.return_value = mock_response
            
            status, headers = await origin_client.head("/image.png")
            
            assert status == 200
            assert headers["content-type"] == "image/png"
            assert headers["content-length"] == "12345"
    
    @pytest.mark.asyncio
    async def test_validate_cached_content_not_modified(self, origin_client):
        """Test validation with 304 Not Modified"""
        with patch.object(origin_client, 'fetch') as mock_fetch:
            # Simulate 304 response by raising exception
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Not Modified",
                request=Mock(),
                response=Mock(status_code=304, headers={})
            )
            
            is_valid, new_content, headers = await origin_client.validate_cached_content(
                "/asset.jpg",
                etag='"abc123"',
                last_modified="Mon, 01 Jan 2024 00:00:00 GMT"
            )
            
            assert is_valid is True
            assert new_content is None
    
    @pytest.mark.asyncio
    async def test_validate_cached_content_modified(self, origin_client):
        """Test validation when content has changed"""
        with patch.object(origin_client, 'fetch') as mock_fetch:
            mock_fetch.return_value = (
                b"new content",
                200,
                {"etag": '"def456"'}
            )
            
            is_valid, new_content, headers = await origin_client.validate_cached_content(
                "/asset.jpg",
                etag='"abc123"'
            )
            
            assert is_valid is False
            assert new_content == b"new content"
            assert headers["etag"] == '"def456"'
    
    def test_parse_cache_control(self, origin_client):
        """Test Cache-Control header parsing"""
        # Simple directives
        headers = {"cache-control": "public, max-age=3600"}
        directives = origin_client.parse_cache_control(headers)
        
        assert directives["public"] is True
        assert directives["max_age"] == 3600
        
        # Complex directives
        headers = {
            "cache-control": 'private, no-cache="Set-Cookie", max-age=0, s-maxage=86400'
        }
        directives = origin_client.parse_cache_control(headers)
        
        assert directives["private"] is True
        assert directives["no_cache"] == "Set-Cookie"
        assert directives["max_age"] == 0
        assert directives["s_maxage"] == 86400
        
        # No cache control
        assert origin_client.parse_cache_control({}) == {}
    
    def test_should_cache(self, origin_client):
        """Test cache decision logic"""
        # Cacheable responses
        assert origin_client.should_cache(200, {"cache-control": "max-age=3600"}) is True
        assert origin_client.should_cache(301, {}) is True
        assert origin_client.should_cache(404, {}) is True
        
        # Non-cacheable responses
        assert origin_client.should_cache(500, {}) is False
        assert origin_client.should_cache(200, {"cache-control": "no-store"}) is False
        
        # Private content (depends on settings)
        origin_client.settings.cache_private_content = False
        assert origin_client.should_cache(200, {"cache-control": "private"}) is False
        
        origin_client.settings.cache_private_content = True
        assert origin_client.should_cache(200, {"cache-control": "private"}) is True
    
    def test_calculate_ttl(self, origin_client):
        """Test TTL calculation"""
        default_ttl = 300
        
        # From s-maxage
        headers = {"cache-control": "s-maxage=7200, max-age=3600"}
        ttl = origin_client.calculate_ttl(headers, default_ttl)
        assert ttl == 7200
        
        # From max-age
        headers = {"cache-control": "max-age=1800"}
        ttl = origin_client.calculate_ttl(headers, default_ttl)
        assert ttl == 1800
        
        # From Expires header
        future_date = (datetime.utcnow() + timedelta(hours=1)).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        headers = {"expires": future_date}
        ttl = origin_client.calculate_ttl(headers, default_ttl)
        assert 3500 <= ttl <= 3700  # Approximately 1 hour
        
        # Default TTL
        headers = {}
        ttl = origin_client.calculate_ttl(headers, default_ttl)
        assert ttl == default_ttl
    
    @pytest.mark.asyncio
    async def test_prefetch(self, origin_client):
        """Test prefetch functionality"""
        with patch.object(origin_client, 'fetch') as mock_fetch:
            mock_fetch.return_value = (b"prefetched", 200, {})
            
            content = await origin_client.prefetch("/prefetch/me", priority=7)
            
            assert content == b"prefetched"
            
            # Test failed prefetch
            mock_fetch.side_effect = Exception("Network error")
            content = await origin_client.prefetch("/fail", priority=5)
            
            assert content is None
    
    def test_generate_request_id(self, origin_client):
        """Test request ID generation"""
        request_id1 = origin_client._generate_request_id()
        request_id2 = origin_client._generate_request_id()
        
        # Should include edge location
        assert origin_client.settings.edge_location in request_id1
        
        # Should be unique
        assert request_id1 != request_id2
        
        # Should have expected format
        parts = request_id1.split("-")
        assert len(parts) >= 2