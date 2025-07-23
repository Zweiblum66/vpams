"""
Tests for CDN Manager
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.services.cdn_manager import GlobalCDNManager, CDNProviderType, OptimizationType
from src.models.schemas import (
    CDNOrigin,
    CacheRule,
    SecurityPolicy,
    GeoRestriction
)


@pytest.fixture
async def cdn_manager():
    """Create CDN manager instance for testing"""
    manager = GlobalCDNManager()
    
    # Mock Redis client
    manager.redis_client = AsyncMock()
    manager.redis_client.set = AsyncMock()
    manager.redis_client.get = AsyncMock(return_value=None)
    manager.redis_client.scan = AsyncMock(return_value=(0, []))
    
    # Mock HTTP session
    manager.http_session = AsyncMock()
    
    # Mark as initialized
    manager._initialized = True
    
    return manager


@pytest.fixture
def sample_origin():
    """Create sample CDN origin"""
    return CDNOrigin(
        origin_id="origin-1",
        domain_name="origin.mams.io",
        origin_path="/media",
        protocol="https",
        port=443,
        custom_headers={"X-Origin-Auth": "secret"}
    )


@pytest.fixture
def sample_cache_rule():
    """Create sample cache rule"""
    return CacheRule(
        rule_id="rule-1",
        path_pattern="*.jpg",
        cache_enabled=True,
        default_ttl=86400,
        max_ttl=31536000,
        min_ttl=0,
        compress=True
    )


@pytest.fixture
def sample_security_policy():
    """Create sample security policy"""
    return SecurityPolicy(
        minimum_protocol_version="TLSv1.2",
        waf_enabled=True,
        geo_restriction=GeoRestriction(
            restriction_type="whitelist",
            locations=["US", "CA", "GB"]
        )
    )


class TestCDNManager:
    """Test CDN Manager functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, cdn_manager):
        """Test CDN manager initialization"""
        # Reset initialization
        cdn_manager._initialized = False
        
        with patch('src.services.cdn_manager.aioredis.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            await cdn_manager.initialize()
            
            assert cdn_manager._initialized
            assert cdn_manager.redis_client is not None
            assert cdn_manager.http_session is not None
    
    @pytest.mark.asyncio
    async def test_create_distribution(self, cdn_manager, sample_origin, sample_cache_rule):
        """Test creating a CDN distribution"""
        # Enable CloudFront provider
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT,
            enabled=True
        )
        
        # Mock CloudFront client
        cdn_manager.cloudfront_client = AsyncMock()
        cdn_manager.cloudfront_client.create_distribution = AsyncMock(
            return_value={
                "Distribution": {
                    "Id": "ABCDEFGHIJKLMN",
                    "DomainName": "d12345.cloudfront.net",
                    "Status": "InProgress",
                    "ARN": "arn:aws:cloudfront::123456789012:distribution/ABCDEFGHIJKLMN"
                }
            }
        )
        
        distribution = await cdn_manager.create_distribution(
            name="test-distribution",
            origins=[sample_origin],
            cache_rules=[sample_cache_rule],
            provider_id="cloudfront"
        )
        
        assert distribution.name == "test-distribution"
        assert distribution.provider_id == "cloudfront"
        assert distribution.status == "deploying"
        assert len(distribution.origins) == 1
        assert len(distribution.cache_rules) == 1
        
        # Verify distribution was saved
        cdn_manager.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_distribution(self, cdn_manager, sample_cache_rule):
        """Test updating a CDN distribution"""
        # Create a test distribution
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront",
            cache_rules=[],
            updated_at=None
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock update method
        cdn_manager._update_cloudfront_distribution = AsyncMock()
        
        updated = await cdn_manager.update_distribution(
            distribution_id=distribution_id,
            cache_rules=[sample_cache_rule],
            enabled=False
        )
        
        assert len(updated.cache_rules) == 1
        assert updated.enabled == False
        assert updated.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_purge_cache(self, cdn_manager):
        """Test cache purging"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront",
            provider_distribution_id="ABCDEFGHIJKLMN"
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock CloudFront client
        cdn_manager.cloudfront_client = AsyncMock()
        cdn_manager.cloudfront_client.create_invalidation = AsyncMock(
            return_value={
                "Invalidation": {
                    "Id": "I1234567890ABC",
                    "Status": "InProgress"
                }
            }
        )
        
        purge_request = await cdn_manager.purge_cache(
            distribution_id=distribution_id,
            paths=["/images/*", "/videos/*"]
        )
        
        assert purge_request.distribution_id == distribution_id
        assert len(purge_request.paths) == 2
        assert purge_request.status == "pending"
        
        # Verify CloudFront invalidation was created
        cdn_manager.cloudfront_client.create_invalidation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_prefetch_content(self, cdn_manager):
        """Test content prefetching"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront",
            domain_name="d12345.cloudfront.net"
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock HTTP requests for cache warming
        cdn_manager._make_cache_warming_request = AsyncMock()
        
        urls = ["/video1.mp4", "/video2.mp4", "/video3.mp4"]
        prefetch_request = await cdn_manager.prefetch_content(
            distribution_id=distribution_id,
            urls=urls,
            priority="high"
        )
        
        assert prefetch_request.distribution_id == distribution_id
        assert len(prefetch_request.urls) == 3
        assert prefetch_request.priority == "high"
        assert prefetch_request.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, cdn_manager):
        """Test getting CDN metrics"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront"
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock metrics retrieval
        cdn_manager._get_cloudfront_metrics = AsyncMock(
            return_value={
                "requests": 1000000,
                "cached_requests": 950000,
                "hit_rate": 0.95,
                "bandwidth": 1024 * 1024 * 1024 * 100,
                "unique_visitors": 50000,
                "error_rate": 0.001,
                "avg_response_time": 50.0
            }
        )
        
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        metrics = await cdn_manager.get_metrics(
            distribution_id=distribution_id,
            start_time=start_time,
            end_time=end_time
        )
        
        assert metrics.distribution_id == distribution_id
        assert metrics.requests_total == 1000000
        assert metrics.cache_hit_rate == 0.95
        assert metrics.error_rate == 0.001
    
    @pytest.mark.asyncio
    async def test_optimize_content(self, cdn_manager):
        """Test content optimization configuration"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id
        )
        
        # Mock optimization configuration
        cdn_manager._configure_image_optimization = AsyncMock()
        
        settings = {
            "auto_webp": True,
            "quality": 85,
            "responsive_sizes": [320, 640, 1024, 1920]
        }
        
        optimization = await cdn_manager.optimize_content(
            distribution_id=distribution_id,
            optimization_type=OptimizationType.IMAGE_OPTIMIZATION,
            settings=settings
        )
        
        assert optimization.distribution_id == distribution_id
        assert optimization.optimization_type == OptimizationType.IMAGE_OPTIMIZATION
        assert optimization.settings["auto_webp"] is True
        assert optimization.enabled is True
    
    @pytest.mark.asyncio
    async def test_get_edge_locations(self, cdn_manager):
        """Test getting edge locations"""
        # Mock edge locations loading
        cdn_manager._load_edge_locations = AsyncMock()
        
        # Test getting all locations
        all_locations = await cdn_manager.get_edge_locations()
        assert isinstance(all_locations, list)
        
        # Test getting locations for specific distribution
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront"
        )
        
        locations = await cdn_manager.get_edge_locations(distribution_id)
        assert isinstance(locations, list)
    
    @pytest.mark.asyncio
    async def test_configure_custom_headers(self, cdn_manager):
        """Test configuring custom headers"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront"
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock header update
        cdn_manager._update_cloudfront_headers = AsyncMock()
        
        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=31536000"
        }
        
        await cdn_manager.configure_custom_headers(distribution_id, headers)
        
        cdn_manager._update_cloudfront_headers.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enable_real_time_logs(self, cdn_manager):
        """Test enabling real-time logs"""
        distribution_id = "dist-test123"
        cdn_manager.distributions[distribution_id] = Mock(
            distribution_id=distribution_id,
            provider_id="cloudfront",
            name="test-distribution",
            realtime_logs_enabled=False
        )
        
        cdn_manager.providers["cloudfront"] = Mock(
            provider_type=CDNProviderType.CLOUDFRONT
        )
        
        # Mock CloudFront client
        cdn_manager.cloudfront_client = AsyncMock()
        cdn_manager.cloudfront_client.create_realtime_log_config = AsyncMock(
            return_value={
                "RealtimeLogConfig": {
                    "ARN": "arn:aws:cloudfront::123456789012:realtime-log-config/test"
                }
            }
        )
        
        log_destination = "arn:aws:kinesis:us-east-1:123456789012:stream/cdn-logs"
        
        await cdn_manager.enable_real_time_logs(distribution_id, log_destination)
        
        cdn_manager.cloudfront_client.create_realtime_log_config.assert_called_once()
        assert cdn_manager.distributions[distribution_id].realtime_logs_enabled is True