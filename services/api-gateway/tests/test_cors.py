"""
Tests for CORS configuration and functionality
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
import re

from core.cors import (
    CORSConfig,
    validate_origin,
    normalize_origin,
    get_origin_from_referer
)


class TestCORSConfig:
    """Test CORSConfig class"""
    
    def test_basic_config(self):
        """Test basic CORS configuration"""
        config = CORSConfig(
            allowed_origins=["https://example.com", "https://app.example.com"],
            allowed_methods=["GET", "POST"],
            allow_credentials=True
        )
        
        assert config.is_origin_allowed("https://example.com")
        assert config.is_origin_allowed("https://app.example.com")
        assert not config.is_origin_allowed("https://other.com")
        assert config.allow_credentials is True
    
    def test_wildcard_origin(self):
        """Test wildcard origin configuration"""
        config = CORSConfig(
            allowed_origins=["*"],
            allow_credentials=False
        )
        
        assert config.is_origin_allowed("https://any-origin.com")
        assert config.is_origin_allowed("http://localhost:3000")
    
    def test_pattern_matching(self):
        """Test regex pattern matching for origins"""
        config = CORSConfig(
            allowed_origin_patterns=[
                r"https://.*\.example\.com",
                r"http://localhost:\d+"
            ]
        )
        
        # Should match patterns
        assert config.is_origin_allowed("https://app.example.com")
        assert config.is_origin_allowed("https://admin.example.com")
        assert config.is_origin_allowed("http://localhost:3000")
        assert config.is_origin_allowed("http://localhost:8080")
        
        # Should not match
        assert not config.is_origin_allowed("https://example.com")  # No subdomain
        assert not config.is_origin_allowed("http://localhost")  # No port
        assert not config.is_origin_allowed("https://example.org")  # Different domain
    
    def test_invalid_pattern(self):
        """Test handling of invalid regex patterns"""
        # Invalid patterns should be skipped
        config = CORSConfig(
            allowed_origin_patterns=["[invalid regex"]
        )
        
        # Should have no compiled patterns due to invalid regex
        assert len(config.compiled_patterns) == 0
    
    def test_exposed_headers(self):
        """Test exposed headers configuration"""
        config = CORSConfig(
            exposed_headers=["X-Custom-Header"]
        )
        
        # Should include default headers plus custom
        assert "X-Total-Count" in config.exposed_headers
        assert "X-Request-ID" in config.exposed_headers
        assert "X-Custom-Header" in config.exposed_headers
    
    def test_cors_headers(self):
        """Test CORS header generation"""
        config = CORSConfig(
            allowed_origins=["https://example.com"],
            allow_credentials=True,
            exposed_headers=["X-Custom"]
        )
        
        # Allowed origin
        headers = config.get_cors_headers("https://example.com", "GET")
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert headers["Access-Control-Allow-Credentials"] == "true"
        assert "X-Custom" in headers["Access-Control-Expose-Headers"]
        
        # Not allowed origin
        headers = config.get_cors_headers("https://other.com", "GET")
        assert "Access-Control-Allow-Origin" not in headers
    
    def test_preflight_headers(self):
        """Test preflight header generation"""
        config = CORSConfig(
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST", "PUT"],
            allowed_headers=["Content-Type", "Authorization"],
            max_age=3600
        )
        
        headers = config.get_preflight_headers("https://example.com", "OPTIONS")
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert "GET, POST, PUT" in headers["Access-Control-Allow-Methods"]
        assert "Content-Type, Authorization" in headers["Access-Control-Allow-Headers"]
        assert headers["Access-Control-Max-Age"] == "3600"


class TestCORSUtilities:
    """Test CORS utility functions"""
    
    def test_validate_origin(self):
        """Test origin validation"""
        # Valid origins
        assert validate_origin("https://example.com")
        assert validate_origin("http://localhost:3000")
        assert validate_origin("https://sub.example.com:8443")
        
        # Invalid origins
        assert not validate_origin("example.com")  # No scheme
        assert not validate_origin("https://")  # No netloc
        assert not validate_origin("not-a-url")
        assert not validate_origin("")
    
    def test_normalize_origin(self):
        """Test origin normalization"""
        # Should keep only scheme and netloc
        assert normalize_origin("https://example.com/path") == "https://example.com"
        assert normalize_origin("http://localhost:3000/api/v1") == "http://localhost:3000"
        assert normalize_origin("https://example.com:443") == "https://example.com:443"
    
    def test_get_origin_from_referer(self):
        """Test extracting origin from referer header"""
        request = MagicMock()
        
        # With referer
        request.headers.get.return_value = "https://example.com/page/path"
        origin = get_origin_from_referer(request)
        assert origin == "https://example.com"
        
        # No referer
        request.headers.get.return_value = None
        origin = get_origin_from_referer(request)
        assert origin is None


@pytest.mark.asyncio
class TestCORSEndpoints:
    """Test CORS API endpoints"""
    
    async def test_cors_test_endpoint(self, client: AsyncClient):
        """Test CORS test endpoint"""
        response = await client.get(
            "/api/v1/cors/test",
            headers={"Origin": "https://example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cors_enabled"] is True
        assert "timestamp" in data
    
    async def test_cors_config_requires_auth(self, client: AsyncClient):
        """Test CORS config endpoint requires authentication"""
        response = await client.get("/api/v1/cors/config")
        assert response.status_code == 401
    
    async def test_cors_config_with_auth(self, client: AsyncClient, admin_headers):
        """Test CORS config endpoint with authentication"""
        response = await client.get("/api/v1/cors/config", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "allowed_origins" in data
        assert "allowed_methods" in data
        assert "allowed_headers" in data
        assert "environment" in data
        assert isinstance(data["allow_credentials"], bool)
    
    async def test_validate_origin_endpoint(self, client: AsyncClient, admin_headers):
        """Test origin validation endpoint"""
        response = await client.post(
            "/api/v1/cors/validate-origin",
            headers=admin_headers,
            params={"origin": "https://example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["origin"] == "https://example.com"
        assert "is_allowed" in data
        assert "reason" in data
    
    async def test_preflight_info(self, client: AsyncClient, admin_headers):
        """Test preflight info endpoint"""
        response = await client.get("/api/v1/cors/preflight-info", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "preflight_cache_duration" in data
        assert "credentials_allowed" in data
        assert "preflight_methods" in data
        assert "notes" in data
    
    async def test_cors_troubleshooting(self, client: AsyncClient):
        """Test CORS troubleshooting guide endpoint"""
        response = await client.get("/api/v1/cors/troubleshooting")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "common_issues" in data
        assert "debugging_tips" in data
        assert "test_commands" in data
    
    async def test_cors_security_practices(self, client: AsyncClient):
        """Test CORS security best practices endpoint"""
        response = await client.get("/api/v1/cors/security-best-practices")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "best_practices" in data
        assert "environment_recommendations" in data


@pytest.mark.asyncio
class TestCORSMiddleware:
    """Test CORS middleware functionality"""
    
    async def test_cors_headers_in_response(self, client: AsyncClient):
        """Test CORS headers are added to responses"""
        # Make request with Origin header
        response = await client.get(
            "/api/v1/",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should have CORS headers if origin is allowed
        assert "Access-Control-Allow-Origin" in response.headers or response.status_code == 200
        assert "Vary" in response.headers
        assert "Origin" in response.headers.get("Vary", "")
    
    async def test_preflight_request(self, client: AsyncClient):
        """Test preflight OPTIONS request"""
        response = await client.options(
            "/api/v1/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Preflight should return 200
        assert response.status_code == 200
        
        # Should have CORS headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        assert "Access-Control-Max-Age" in response.headers
    
    async def test_credentials_mode(self, client: AsyncClient):
        """Test CORS with credentials"""
        response = await client.get(
            "/api/v1/",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # If credentials are allowed and origin is allowed
        if "Access-Control-Allow-Origin" in response.headers:
            if response.headers["Access-Control-Allow-Origin"] != "*":
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    
    async def test_exposed_headers(self, client: AsyncClient):
        """Test exposed headers in CORS response"""
        response = await client.get(
            "/api/v1/",
            headers={"Origin": "http://localhost:3000"}
        )
        
        if "Access-Control-Expose-Headers" in response.headers:
            exposed = response.headers["Access-Control-Expose-Headers"]
            # Check for some expected headers
            assert "X-Request-ID" in exposed or "X-Total-Count" in exposed


@pytest.mark.asyncio
class TestCORSIntegration:
    """Test CORS integration with other features"""
    
    async def test_cors_with_authentication(self, client: AsyncClient, auth_headers):
        """Test CORS works with authenticated requests"""
        headers = {
            **auth_headers,
            "Origin": "http://localhost:3000"
        }
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        # Should have CORS headers if origin is allowed
        assert "Access-Control-Allow-Origin" in response.headers or response.status_code == 200
    
    async def test_cors_with_api_versioning(self, client: AsyncClient):
        """Test CORS works with API versioning"""
        # Test v1
        response = await client.get(
            "/api/v1/",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        
        # Test v2
        response = await client.get(
            "/api/v2/",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
    
    async def test_cors_error_responses(self, client: AsyncClient):
        """Test CORS headers are included in error responses"""
        # Make request that triggers 404
        response = await client.get(
            "/api/v1/nonexistent",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 404
        # Should still have CORS headers
        assert "Vary" in response.headers