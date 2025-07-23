"""
Tests for cache utilities
"""

import pytest
from src.utils.cache import CacheKeyGenerator


@pytest.fixture
def cache_key_generator():
    """Create cache key generator instance"""
    return CacheKeyGenerator()


class TestCacheKeyGenerator:
    """Test cache key generation utilities"""
    
    def test_generate_cache_key_basic(self, cache_key_generator):
        """Test basic cache key generation"""
        url = "https://cdn.example.com/images/logo.png"
        key = cache_key_generator.generate_cache_key(url)
        
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
    
    def test_generate_cache_key_with_query_params(self, cache_key_generator):
        """Test cache key with query parameters"""
        url = "https://cdn.example.com/api/data?id=123&format=json"
        
        # Test with no query string behavior
        key1 = cache_key_generator.generate_cache_key(url, query_string_behavior="none")
        
        # Test with all query params
        key2 = cache_key_generator.generate_cache_key(url, query_string_behavior="all")
        
        # Keys should be different
        assert key1 != key2
    
    def test_generate_cache_key_with_whitelist(self, cache_key_generator):
        """Test cache key with whitelisted query parameters"""
        url = "https://cdn.example.com/api/data?id=123&format=json&utm_source=email"
        
        key = cache_key_generator.generate_cache_key(
            url,
            query_string_behavior="whitelist",
            query_string_keys=["id", "format"]
        )
        
        # Should include id and format but not utm_source
        assert isinstance(key, str)
    
    def test_generate_cache_key_with_headers(self, cache_key_generator):
        """Test cache key with headers"""
        url = "https://cdn.example.com/api/data"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "User-Agent": "Mozilla/5.0"
        }
        
        # Test with whitelisted headers
        key = cache_key_generator.generate_cache_key(
            url,
            headers=headers,
            headers_behavior="whitelist",
            headers_whitelist=["Accept", "Accept-Language"]
        )
        
        assert isinstance(key, str)
    
    def test_is_cacheable_by_extension(self, cache_key_generator):
        """Test checking if URL is cacheable by extension"""
        assert cache_key_generator.is_cacheable_by_extension("https://example.com/image.jpg")
        assert cache_key_generator.is_cacheable_by_extension("https://example.com/script.js")
        assert cache_key_generator.is_cacheable_by_extension("https://example.com/style.css")
        assert cache_key_generator.is_cacheable_by_extension("https://example.com/video.mp4")
        assert not cache_key_generator.is_cacheable_by_extension("https://example.com/api/data")
    
    def test_get_content_type(self, cache_key_generator):
        """Test content type detection"""
        assert cache_key_generator.get_content_type("https://example.com/image.jpg") == "image/jpeg"
        assert cache_key_generator.get_content_type("https://example.com/script.js") == "application/javascript"
        assert cache_key_generator.get_content_type("https://example.com/style.css") == "text/css"
        assert cache_key_generator.get_content_type("https://example.com/video.mp4") == "video/mp4"
        assert cache_key_generator.get_content_type("https://example.com/unknown") == "application/octet-stream"
    
    def test_normalize_url(self, cache_key_generator):
        """Test URL normalization"""
        # Test removing default ports
        assert cache_key_generator.normalize_url("http://example.com:80/path") == "http://example.com/path"
        assert cache_key_generator.normalize_url("https://example.com:443/path") == "https://example.com/path"
        
        # Test removing trailing slashes
        assert cache_key_generator.normalize_url("https://example.com/path/") == "https://example.com/path"
        
        # Test preserving query strings
        assert cache_key_generator.normalize_url("https://example.com/path?q=1") == "https://example.com/path?q=1"
    
    def test_extract_cache_tags(self, cache_key_generator):
        """Test cache tag extraction"""
        url = "https://example.com/media/videos/movie.mp4"
        headers = {
            "X-Tenant-ID": "tenant123",
            "X-User-ID": "user456",
            "Cache-Tag": "featured,new-release"
        }
        
        tags = cache_key_generator.extract_cache_tags(url, headers)
        
        assert "path:media" in tags
        assert "path:media/videos" in tags
        assert "path:media/videos/movie.mp4" in tags
        assert "type:video" in tags
        assert "mime:video/mp4" in tags
        assert "tenant:tenant123" in tags
        assert "user:user456" in tags
        assert "featured" in tags
        assert "new-release" in tags
    
    def test_should_bypass_cache(self, cache_key_generator):
        """Test cache bypass logic"""
        # Non-GET/HEAD methods should bypass
        assert cache_key_generator.should_bypass_cache("https://example.com/api", "POST")
        assert cache_key_generator.should_bypass_cache("https://example.com/api", "PUT")
        assert not cache_key_generator.should_bypass_cache("https://example.com/api", "GET")
        
        # No-cache headers should bypass
        headers_no_cache = {"Cache-Control": "no-cache"}
        assert cache_key_generator.should_bypass_cache("https://example.com/api", "GET", headers_no_cache)
        
        headers_no_store = {"Cache-Control": "no-store"}
        assert cache_key_generator.should_bypass_cache("https://example.com/api", "GET", headers_no_store)
        
        # Authorization header should bypass
        headers_auth = {"Authorization": "Bearer token"}
        assert cache_key_generator.should_bypass_cache("https://example.com/api", "GET", headers_auth)
        
        # Dynamic content patterns should bypass
        assert cache_key_generator.should_bypass_cache("https://example.com/api/data", "GET")
        assert cache_key_generator.should_bypass_cache("https://example.com/admin/panel", "GET")
        assert cache_key_generator.should_bypass_cache("https://example.com/auth/login", "GET")
    
    def test_calculate_ttl(self, cache_key_generator):
        """Test TTL calculation"""
        # Test content-type based TTLs
        assert cache_key_generator.calculate_ttl("https://example.com/image.jpg") == 86400 * 30  # 30 days
        assert cache_key_generator.calculate_ttl("https://example.com/video.mp4") == 86400 * 7   # 7 days
        assert cache_key_generator.calculate_ttl("https://example.com/style.css") == 86400 * 7   # 7 days
        assert cache_key_generator.calculate_ttl("https://example.com/data.json") == 300         # 5 minutes
        
        # Test with explicit cache control
        headers = {"Cache-Control": "max-age=3600"}
        assert cache_key_generator.calculate_ttl("https://example.com/data", headers=headers) == 3600
    
    def test_generate_vary_key(self, cache_key_generator):
        """Test vary key generation"""
        base_key = "abc123"
        vary_headers = ["Accept", "Accept-Language"]
        request_headers = {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "User-Agent": "Mozilla/5.0"
        }
        
        vary_key = cache_key_generator.generate_vary_key(base_key, vary_headers, request_headers)
        
        assert isinstance(vary_key, str)
        assert len(vary_key) == 32  # MD5 hash length
    
    def test_parse_cache_control(self, cache_key_generator):
        """Test Cache-Control parsing"""
        cache_control = "public, max-age=3600, must-revalidate, stale-while-revalidate=86400"
        directives = cache_key_generator.parse_cache_control(cache_control)
        
        assert directives["public"] is None
        assert directives["max-age"] == "3600"
        assert directives["must-revalidate"] is None
        assert directives["stale-while-revalidate"] == "86400"
    
    def test_is_stale(self, cache_key_generator):
        """Test stale content detection"""
        import time
        
        # Test basic TTL expiration
        cached_time = time.time() - 3700  # Cached 1 hour and 100 seconds ago
        ttl = 3600  # 1 hour TTL
        assert cache_key_generator.is_stale(cached_time, ttl)
        
        # Test fresh content
        cached_time = time.time() - 1800  # Cached 30 minutes ago
        assert not cache_key_generator.is_stale(cached_time, ttl)
        
        # Test with must-revalidate
        cache_control = "must-revalidate"
        assert cache_key_generator.is_stale(cached_time, ttl, cache_control)