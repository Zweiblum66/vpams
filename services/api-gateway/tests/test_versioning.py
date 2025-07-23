"""
Tests for API versioning system
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from core.versioning import (
    APIVersion,
    VersionRegistry,
    VersionExtractor,
    VersioningStrategy,
    VersionConfig
)


class TestAPIVersion:
    """Test APIVersion class"""
    
    def test_version_parsing(self):
        """Test version parsing from various formats"""
        # Test different formats
        v1 = APIVersion("1")
        assert v1.major == 1
        assert v1.minor == 0
        assert v1.patch == 0
        assert str(v1) == "v1"
        
        v1_2 = APIVersion("1.2")
        assert v1_2.major == 1
        assert v1_2.minor == 2
        assert v1_2.patch == 0
        assert str(v1_2) == "v1.2"
        
        v1_2_3 = APIVersion("1.2.3")
        assert v1_2_3.major == 1
        assert v1_2_3.minor == 2
        assert v1_2_3.patch == 3
        assert str(v1_2_3) == "v1.2.3"
        
        # Test with 'v' prefix
        v_prefixed = APIVersion("v2.1")
        assert v_prefixed.major == 2
        assert v_prefixed.minor == 1
        assert str(v_prefixed) == "v2.1"
    
    def test_version_comparison(self):
        """Test version comparison operations"""
        v1 = APIVersion("1.0.0")
        v1_1 = APIVersion("1.1.0")
        v2 = APIVersion("2.0.0")
        
        assert v1 < v1_1
        assert v1_1 < v2
        assert v1 <= v1
        assert v1 == APIVersion("1.0.0")
        assert v1 != v2
    
    def test_version_compatibility(self):
        """Test version compatibility checking"""
        v1 = APIVersion("1.0.0")
        v1_1 = APIVersion("1.1.0")
        v1_0_1 = APIVersion("1.0.1")
        v2 = APIVersion("2.0.0")
        
        # Same major version, higher minor/patch is compatible
        assert v1_1.is_compatible_with(v1)
        assert v1_0_1.is_compatible_with(v1)
        
        # Different major version is not compatible
        assert not v2.is_compatible_with(v1)
        
        # Lower version is not compatible
        assert not v1.is_compatible_with(v1_1)
    
    def test_invalid_version_format(self):
        """Test invalid version format handling"""
        with pytest.raises(ValueError):
            APIVersion("invalid")
        
        with pytest.raises(ValueError):
            APIVersion("1.a.0")


class TestVersionRegistry:
    """Test VersionRegistry class"""
    
    def test_register_version(self):
        """Test version registration"""
        registry = VersionRegistry()
        
        config = VersionConfig(
            version="3",
            status="experimental",
            features=["Test feature"]
        )
        
        registry.register_version(config)
        
        assert registry.is_version_supported("3")
        assert registry.is_version_supported(APIVersion("3"))
        
        retrieved_config = registry.get_version_config("3")
        assert retrieved_config.status == "experimental"
    
    def test_deprecation_info(self):
        """Test deprecation information"""
        registry = VersionRegistry()
        
        # Non-deprecated version
        assert registry.get_deprecation_info("1") is None
        
        # Register deprecated version
        from datetime import date
        deprecated_config = VersionConfig(
            version="0.9",
            status="deprecated",
            deprecated=True,
            deprecation_date=date(2024, 12, 31),
            features=[]
        )
        
        registry.register_version(deprecated_config)
        
        deprecation_info = registry.get_deprecation_info("0.9")
        assert deprecation_info is not None
        assert deprecation_info["deprecated"] is True
        assert "2024-12-31" in deprecation_info["deprecation_date"]


class TestVersionExtractor:
    """Test VersionExtractor class"""
    
    @pytest.mark.asyncio
    async def test_extract_from_url(self):
        """Test version extraction from URL path"""
        extractor = VersionExtractor(VersioningStrategy.URL_PATH)
        
        # Mock request
        request = MagicMock()
        
        # Test /api/v1 pattern
        request.url.path = "/api/v1/users"
        version = await extractor.extract_version(request)
        assert version == APIVersion("1")
        
        # Test /api/v2 pattern
        request.url.path = "/api/v2/assets"
        version = await extractor.extract_version(request)
        assert version == APIVersion("2")
        
        # Test /v1 pattern
        request.url.path = "/v1/health"
        version = await extractor.extract_version(request)
        assert version == APIVersion("1")
        
        # Test no version in path
        request.url.path = "/api/users"
        version = await extractor.extract_version(request)
        assert version is None
    
    @pytest.mark.asyncio
    async def test_extract_from_header(self):
        """Test version extraction from header"""
        extractor = VersionExtractor(VersioningStrategy.HEADER)
        
        request = MagicMock()
        request.url.path = "/api/users"
        
        # With version header
        request.headers.get.return_value = "2"
        version = await extractor.extract_version(request)
        assert version == APIVersion("2")
        
        # Without version header
        request.headers.get.return_value = None
        version = await extractor.extract_version(request)
        assert version is None
    
    @pytest.mark.asyncio
    async def test_extract_from_query_param(self):
        """Test version extraction from query parameter"""
        extractor = VersionExtractor(VersioningStrategy.QUERY_PARAM)
        
        request = MagicMock()
        request.url.path = "/api/users"
        
        # With version param
        request.query_params.get.return_value = "1"
        version = await extractor.extract_version(request)
        assert version == APIVersion("1")
        
        # Without version param
        request.query_params.get.return_value = None
        version = await extractor.extract_version(request)
        assert version is None
    
    @pytest.mark.asyncio
    async def test_extract_from_accept_header(self):
        """Test version extraction from Accept header"""
        extractor = VersionExtractor(VersioningStrategy.ACCEPT_HEADER)
        
        request = MagicMock()
        request.url.path = "/api/users"
        
        # With version in Accept header
        request.headers.get.return_value = "application/vnd.mams.v2+json"
        version = await extractor.extract_version(request)
        assert version == APIVersion("2")
        
        # Without version in Accept header
        request.headers.get.return_value = "application/json"
        version = await extractor.extract_version(request)
        assert version is None


@pytest.mark.asyncio
class TestVersionedEndpoints:
    """Test versioned API endpoints"""
    
    async def test_version_info_endpoint(self, client: AsyncClient):
        """Test /api/version endpoint"""
        response = await client.get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "current_version" in data
        assert "default_version" in data
        assert "supported_versions" in data
        assert len(data["supported_versions"]) > 0
    
    async def test_versions_list_endpoint(self, client: AsyncClient):
        """Test /api/versions endpoint"""
        response = await client.get("/api/versions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "versions" in data
        assert "current" in data
        assert "default" in data
        assert "v1" in data["versions"]
    
    async def test_v1_endpoint(self, client: AsyncClient):
        """Test v1 API endpoint"""
        response = await client.get("/api/v1/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["api_version"] == "v1"
        assert data["status"] == "stable"
        assert "available_services" in data
    
    async def test_v2_endpoint(self, client: AsyncClient):
        """Test v2 API endpoint"""
        response = await client.get("/api/v2/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["api_version"] == "v2"
        assert data["status"] == "beta"
        assert "features" in data
    
    async def test_unsupported_version(self, client: AsyncClient):
        """Test unsupported version handling"""
        response = await client.get("/api/v99/users")
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error" in data
        assert "UNSUPPORTED_VERSION" in str(data)
    
    async def test_version_headers(self, client: AsyncClient):
        """Test version headers in response"""
        response = await client.get("/api/v1/")
        
        assert "X-API-Version" in response.headers
        assert "X-API-Supported-Versions" in response.headers
        assert response.headers["X-API-Version"] == "v1"
    
    async def test_migration_guide(self, client: AsyncClient):
        """Test migration guide endpoint"""
        response = await client.get("/api/version/migration-guide/v1/v2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["from_version"] == "v1"
        assert data["to_version"] == "v2"
        assert "breaking_changes" in data
        assert "migration_steps" in data
    
    async def test_version_changelog(self, client: AsyncClient):
        """Test version changelog endpoint"""
        response = await client.get("/api/version/changelog/v1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["version"] == "v1"
        assert "changes" in data
        assert "features" in data["changes"]
    
    async def test_version_metrics_requires_auth(self, client: AsyncClient):
        """Test version metrics requires authentication"""
        response = await client.get("/api/version/metrics")
        
        assert response.status_code == 401
    
    async def test_version_metrics_with_auth(self, client: AsyncClient, auth_headers):
        """Test version metrics with authentication"""
        response = await client.get("/api/version/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have some response even if no actual metrics
        assert isinstance(data, dict)


@pytest.mark.asyncio
class TestVersioningMiddleware:
    """Test versioning middleware functionality"""
    
    async def test_default_version_used(self, client: AsyncClient):
        """Test default version is used when none specified"""
        # Request without version should use default
        response = await client.get("/api/")
        
        # Check that some version was used
        assert "X-API-Version" in response.headers
    
    async def test_deprecation_headers(self, client: AsyncClient):
        """Test deprecation headers for deprecated versions"""
        # This would require setting up a deprecated version
        # For now, test that non-deprecated versions don't have deprecation headers
        response = await client.get("/api/v1/")
        
        assert "X-API-Deprecation" not in response.headers
        assert "X-API-Sunset" not in response.headers
    
    async def test_invalid_version_format_error(self, client: AsyncClient):
        """Test error handling for invalid version format"""
        response = await client.get("/api/vinvalid/users")
        
        assert response.status_code == 400
        data = response.json()
        assert "INVALID_VERSION_FORMAT" in str(data) or "error" in data