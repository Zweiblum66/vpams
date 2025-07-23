"""
Tests for Rate Limiting

Tests various rate limiting strategies and scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.core.rate_limiter import (
    RateLimiter,
    RateLimitStrategy,
    RateLimitResult,
    AdvancedRateLimiter,
    IPRateLimiter,
    DistributedRateLimiter
)


@pytest.mark.asyncio
class TestRateLimiter:
    """Test base rate limiter functionality"""
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client"""
        with patch('src.core.rate_limiter.get_redis_client') as mock:
            client = AsyncMock()
            client.pipeline.return_value = client
            client.execute = AsyncMock(return_value=[None, 0])
            mock.return_value = client
            yield client
    
    async def test_sliding_window_allow(self, redis_mock):
        """Test sliding window allows requests within limit"""
        limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
        
        # Mock Redis responses
        redis_mock.zcard = AsyncMock(return_value=5)
        redis_mock.zadd = AsyncMock()
        redis_mock.expire = AsyncMock()
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is True
        assert result.limit == 10
        assert result.remaining == 4  # 10 - 5 (current) - 1 (cost)
        assert redis_mock.zadd.called
    
    async def test_sliding_window_deny(self, redis_mock):
        """Test sliding window denies requests over limit"""
        limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
        
        # Mock Redis responses - at limit
        redis_mock.zcard = AsyncMock(return_value=10)
        redis_mock.zrange = AsyncMock(return_value=[(b"key", time.time() - 30)])
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is False
        assert result.limit == 10
        assert result.remaining == 0
        assert result.retry_after is not None
        assert not redis_mock.zadd.called
    
    async def test_fixed_window_allow(self, redis_mock):
        """Test fixed window allows requests within limit"""
        limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
        
        # Mock Redis responses
        redis_mock.execute = AsyncMock(return_value=[5, True])  # count, expire result
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is True
        assert result.limit == 10
        assert result.remaining == 5  # 10 - 5
    
    async def test_fixed_window_deny(self, redis_mock):
        """Test fixed window denies requests over limit"""
        limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
        
        # Mock Redis responses - over limit
        redis_mock.execute = AsyncMock(return_value=[11, True])
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is False
        assert result.limit == 10
        assert result.remaining == 0
        assert result.retry_after > 0
    
    async def test_token_bucket_allow(self, redis_mock):
        """Test token bucket allows requests when tokens available"""
        limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
        
        # Mock Redis responses - bucket with tokens
        bucket_data = '{"tokens": 5.0, "last_update": ' + str(time.time()) + '}'
        redis_mock.get = AsyncMock(return_value=bucket_data)
        redis_mock.set = AsyncMock()
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is True
        assert result.remaining >= 4
        assert redis_mock.set.called
    
    async def test_token_bucket_deny(self, redis_mock):
        """Test token bucket denies requests when no tokens"""
        limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
        
        # Mock Redis responses - bucket empty
        bucket_data = '{"tokens": 0.5, "last_update": ' + str(time.time()) + '}'
        redis_mock.get = AsyncMock(return_value=bucket_data)
        
        result = await limiter.check_rate_limit(
            identifier="test_user",
            limit=10,
            window=60,
            cost=1
        )
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after > 0


@pytest.mark.asyncio
class TestAdvancedRateLimiter:
    """Test advanced rate limiter with rules"""
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client"""
        with patch('src.core.rate_limiter.get_redis_client') as mock:
            client = AsyncMock()
            client.pipeline.return_value = client
            client.execute = AsyncMock(return_value=[None, 0])
            client.zcard = AsyncMock(return_value=2)
            mock.return_value = client
            yield client
    
    async def test_endpoint_specific_limits(self, redis_mock):
        """Test different limits for different endpoints"""
        limiter = AdvancedRateLimiter()
        
        # Test auth endpoint (stricter limit)
        result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/auth/login",
            identifier="user123",
            method="POST"
        )
        
        assert result.limit == 5  # Login limit from rules
        
        # Test regular read endpoint
        result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/assets",
            identifier="user123",
            method="GET"
        )
        
        assert result.limit == 1000  # Read limit from rules
    
    async def test_tier_multipliers(self, redis_mock):
        """Test rate limit multipliers based on user tier"""
        limiter = AdvancedRateLimiter()
        
        # Free tier
        result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/assets",
            identifier="user123",
            method="GET",
            user_tier="free"
        )
        free_limit = result.limit
        
        # Premium tier
        result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/assets",
            identifier="user456",
            method="GET",
            user_tier="premium"
        )
        premium_limit = result.limit
        
        assert premium_limit == free_limit * 5  # Premium gets 5x
    
    async def test_method_based_limits(self, redis_mock):
        """Test different limits for different HTTP methods"""
        limiter = AdvancedRateLimiter()
        
        # GET request
        get_result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/assets",
            identifier="user123",
            method="GET"
        )
        
        # POST request
        post_result = await limiter.check_endpoint_limit(
            endpoint="/api/v1/assets",
            identifier="user123",
            method="POST"
        )
        
        assert get_result.limit > post_result.limit  # Reads have higher limit


@pytest.mark.asyncio
class TestIPRateLimiter:
    """Test IP-based rate limiting"""
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client"""
        with patch('src.core.rate_limiter.get_redis_client') as mock:
            client = AsyncMock()
            client.pipeline.return_value = client
            client.execute = AsyncMock(return_value=[None, 0])
            client.zcard = AsyncMock(return_value=45)
            mock.return_value = client
            yield client
    
    async def test_ip_hash_privacy(self):
        """Test IP addresses are hashed for privacy"""
        limiter = IPRateLimiter()
        
        ip1_hash = limiter._hash_ip("192.168.1.1")
        ip2_hash = limiter._hash_ip("192.168.1.2")
        
        assert ip1_hash != ip2_hash
        assert len(ip1_hash) == 16
        assert "192.168" not in ip1_hash
    
    async def test_ip_rate_limit(self, redis_mock):
        """Test IP-based rate limiting"""
        limiter = IPRateLimiter()
        
        result = await limiter.check_ip_limit(
            ip_address="192.168.1.1",
            endpoint="/api/v1/assets"
        )
        
        assert result.allowed is True
        assert result.limit == 50  # IP limit


@pytest.mark.asyncio
class TestDistributedRateLimiter:
    """Test distributed rate limiter"""
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client"""
        with patch('src.core.rate_limiter.get_redis_client') as mock:
            client = AsyncMock()
            client.pipeline.return_value = client
            client.execute = AsyncMock(return_value=[None, 0])
            client.zcard = AsyncMock(return_value=0)
            client.keys = AsyncMock(return_value=[])
            mock.return_value = client
            yield client
    
    async def test_authenticated_user_limits(self, redis_mock):
        """Test limits for authenticated users"""
        limiter = DistributedRateLimiter()
        
        request_info = {
            "endpoint": "/api/v1/assets",
            "method": "GET",
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "user_tier": "premium"
        }
        
        result = await limiter.check_request_limit(request_info)
        
        assert result.allowed is True
        assert result.limit == 5000  # Premium tier on read endpoint
    
    async def test_unauthenticated_ip_limits(self, redis_mock):
        """Test stricter limits for unauthenticated requests"""
        limiter = DistributedRateLimiter()
        
        request_info = {
            "endpoint": "/api/v1/assets",
            "method": "GET",
            "user_id": None,
            "ip_address": "192.168.1.1",
            "user_tier": "free"
        }
        
        result = await limiter.check_request_limit(request_info)
        
        assert result.allowed is True
        assert result.limit == 50  # IP-based limit
    
    async def test_rate_limit_info(self, redis_mock):
        """Test getting rate limit information"""
        limiter = DistributedRateLimiter()
        
        # Mock Redis keys
        redis_mock.keys = AsyncMock(return_value=[
            b"rate_limit:sliding:user123",
            b"rate_limit:fixed:user123:12345"
        ])
        redis_mock.zcard = AsyncMock(return_value=5)
        redis_mock.get = AsyncMock(return_value=b"10")
        
        info = await limiter.get_rate_limit_info(
            identifier="user123",
            endpoint="/api/v1/assets"
        )
        
        assert info["identifier"] == "user123"
        assert "current_usage" in info
        assert len(info["current_usage"]) > 0


@pytest.mark.asyncio
class TestRateLimitIntegration:
    """Integration tests for rate limiting"""
    
    @pytest.fixture
    async def app_client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from src.main import app
        return TestClient(app)
    
    async def test_rate_limit_headers(self, app_client):
        """Test rate limit headers in responses"""
        response = app_client.get("/api/v1/assets")
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    async def test_rate_limit_exceeded_response(self, app_client):
        """Test response when rate limit exceeded"""
        # This would need to make many requests to exceed limit
        # For now, we'll mock the rate limiter response
        with patch('src.core.middleware.rate_limiter.check_request_limit') as mock:
            mock.return_value = RateLimitResult(
                allowed=False,
                limit=10,
                remaining=0,
                reset=int(time.time()) + 60,
                retry_after=60
            )
            
            response = app_client.get("/api/v1/assets")
            
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"