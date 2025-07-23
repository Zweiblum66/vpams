"""
Tests for IP Whitelist Middleware

Comprehensive tests for IP whitelisting functionality, including
IP matching, CIDR ranges, wildcard patterns, and API endpoints.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json
from datetime import datetime, timedelta

from core.ip_whitelist import (
    IPWhitelistConfig,
    IPMatcher,
    IPWhitelistManager,
    IPWhitelistMiddleware,
    get_ip_whitelist_config,
    get_ip_whitelist_manager,
    IPAccessDeniedException
)
from api.ip_whitelist_routes import (
    IPWhitelistStatusResponse,
    IPWhitelistConfigResponse,
    BlockedRequestResponse,
    IPWhitelistStatsResponse
)


class TestIPMatcher:
    """Test cases for IP matching functionality"""
    
    def test_single_ip_matching(self):
        """Test single IP address matching"""
        matcher = IPMatcher(["192.168.1.1", "10.0.0.1"])
        
        assert matcher.matches("192.168.1.1") is True
        assert matcher.matches("10.0.0.1") is True
        assert matcher.matches("192.168.1.2") is False
        assert matcher.matches("10.0.0.2") is False
        assert matcher.matches("invalid") is False
    
    def test_cidr_range_matching(self):
        """Test CIDR range matching"""
        matcher = IPMatcher(["192.168.1.0/24", "10.0.0.0/8"])
        
        assert matcher.matches("192.168.1.1") is True
        assert matcher.matches("192.168.1.254") is True
        assert matcher.matches("192.168.2.1") is False
        assert matcher.matches("10.0.0.1") is True
        assert matcher.matches("10.255.255.255") is True
        assert matcher.matches("172.16.0.1") is False
    
    def test_wildcard_matching(self):
        """Test wildcard pattern matching"""
        matcher = IPMatcher(["192.168.1.*", "10.0.*.1"])
        
        assert matcher.matches("192.168.1.1") is True
        assert matcher.matches("192.168.1.255") is True
        assert matcher.matches("192.168.2.1") is False
        assert matcher.matches("10.0.0.1") is True
        assert matcher.matches("10.0.255.1") is True
        assert matcher.matches("10.0.0.2") is False
    
    def test_mixed_patterns(self):
        """Test mixed IP patterns"""
        matcher = IPMatcher([
            "192.168.1.1",          # Single IP
            "10.0.0.0/16",          # CIDR range
            "172.16.1.*"            # Wildcard
        ])
        
        assert matcher.matches("192.168.1.1") is True
        assert matcher.matches("10.0.0.1") is True
        assert matcher.matches("10.0.255.1") is True
        assert matcher.matches("172.16.1.1") is True
        assert matcher.matches("172.16.1.255") is True
        assert matcher.matches("172.16.2.1") is False
    
    def test_empty_list(self):
        """Test empty IP list"""
        matcher = IPMatcher([])
        
        assert matcher.matches("192.168.1.1") is False
        assert matcher.matches("10.0.0.1") is False
    
    def test_invalid_patterns(self):
        """Test handling of invalid patterns"""
        # Should skip invalid patterns and continue with valid ones
        matcher = IPMatcher([
            "192.168.1.1",
            "invalid.ip",
            "10.0.0.0/24"
        ])
        
        assert matcher.matches("192.168.1.1") is True
        assert matcher.matches("10.0.0.1") is True
        assert matcher.matches("invalid.ip") is False


class TestIPWhitelistConfig:
    """Test cases for IP whitelist configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = IPWhitelistConfig()
        
        assert config.enabled is False
        assert config.mode == "whitelist"
        assert config.allowed_ips == []
        assert config.blocked_ips == []
        assert config.admin_ips == []
        assert config.trust_proxy_headers is True
        assert config.max_proxy_depth == 3
        assert config.enable_rate_limiting is True
        assert config.rate_limit_requests == 1000
        assert config.rate_limit_window == 3600
        assert config.log_blocked_requests is True
        assert config.log_allowed_requests is False
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = IPWhitelistConfig(
            enabled=True,
            mode="blacklist",
            allowed_ips=["192.168.1.1", "10.0.0.0/8"],
            blocked_ips=["192.168.1.100"],
            admin_ips=["192.168.1.10"],
            trust_proxy_headers=False,
            enable_rate_limiting=False,
            rate_limit_requests=500,
            rate_limit_window=1800
        )
        
        assert config.enabled is True
        assert config.mode == "blacklist"
        assert config.allowed_ips == ["192.168.1.1", "10.0.0.0/8"]
        assert config.blocked_ips == ["192.168.1.100"]
        assert config.admin_ips == ["192.168.1.10"]
        assert config.trust_proxy_headers is False
        assert config.enable_rate_limiting is False
        assert config.rate_limit_requests == 500
        assert config.rate_limit_window == 1800
    
    def test_invalid_mode(self):
        """Test invalid mode validation"""
        with pytest.raises(ValueError, match="Mode must be 'whitelist' or 'blacklist'"):
            IPWhitelistConfig(mode="invalid")
    
    def test_ip_validation(self):
        """Test IP list validation"""
        # Valid IPs should be accepted
        config = IPWhitelistConfig(
            allowed_ips=["192.168.1.1", "10.0.0.0/8", "172.16.1.*"]
        )
        assert len(config.allowed_ips) == 3
        
        # Invalid IPs should be filtered out (with warnings)
        config = IPWhitelistConfig(
            allowed_ips=["192.168.1.1", "invalid.ip", "10.0.0.0/8"]
        )
        # Should only keep valid IPs
        assert "192.168.1.1" in config.allowed_ips
        assert "10.0.0.0/8" in config.allowed_ips
        assert "invalid.ip" not in config.allowed_ips


class TestIPWhitelistManager:
    """Test cases for IP whitelist manager"""
    
    @pytest.fixture
    def whitelist_config(self):
        """Create whitelist configuration"""
        return IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=["192.168.1.0/24", "10.0.0.1"],
            blocked_ips=["192.168.1.100"],
            admin_ips=["192.168.1.10"],
            trust_proxy_headers=True,
            max_proxy_depth=2
        )
    
    @pytest.fixture
    def blacklist_config(self):
        """Create blacklist configuration"""
        return IPWhitelistConfig(
            enabled=True,
            mode="blacklist",
            blocked_ips=["192.168.1.100", "10.0.0.0/8"],
            admin_ips=["192.168.1.10"]
        )
    
    @pytest.fixture
    def manager(self, whitelist_config):
        """Create IP whitelist manager"""
        return IPWhitelistManager(whitelist_config)
    
    def test_extract_client_ip_direct(self, manager):
        """Test extracting client IP from direct connection"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        ip = manager.extract_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_extract_client_ip_forwarded_for(self, manager):
        """Test extracting client IP from X-Forwarded-For header"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        
        ip = manager.extract_client_ip(request)
        assert ip == "203.0.113.1"
    
    def test_extract_client_ip_real_ip(self, manager):
        """Test extracting client IP from X-Real-IP header"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {"X-Real-IP": "203.0.113.1"}
        
        ip = manager.extract_client_ip(request)
        assert ip == "203.0.113.1"
    
    def test_extract_client_ip_proxy_depth_limit(self, manager):
        """Test proxy depth limit"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1, 10.0.0.1, 172.16.1.1"}
        
        # Should fall back to direct client IP if proxy chain is too long
        ip = manager.extract_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_extract_client_ip_no_trust_proxy(self, manager):
        """Test not trusting proxy headers"""
        manager.config.trust_proxy_headers = False
        
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {"X-Forwarded-For": "203.0.113.1"}
        
        ip = manager.extract_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_is_ip_allowed_whitelist_mode(self, manager):
        """Test IP allowance in whitelist mode"""
        # Admin IPs are always allowed
        assert manager.is_ip_allowed("192.168.1.10") is True
        
        # Allowed IPs
        assert manager.is_ip_allowed("192.168.1.1") is True
        assert manager.is_ip_allowed("10.0.0.1") is True
        
        # Not allowed IPs
        assert manager.is_ip_allowed("192.168.2.1") is False
        assert manager.is_ip_allowed("10.0.0.2") is False
    
    def test_is_ip_allowed_blacklist_mode(self, blacklist_config):
        """Test IP allowance in blacklist mode"""
        manager = IPWhitelistManager(blacklist_config)
        
        # Admin IPs are always allowed
        assert manager.is_ip_allowed("192.168.1.10") is True
        
        # Blocked IPs
        assert manager.is_ip_allowed("192.168.1.100") is False
        assert manager.is_ip_allowed("10.0.0.1") is False
        
        # Not blocked IPs
        assert manager.is_ip_allowed("192.168.1.1") is True
        assert manager.is_ip_allowed("172.16.1.1") is True
    
    def test_is_ip_allowed_disabled(self, manager):
        """Test IP allowance when disabled"""
        manager.config.enabled = False
        
        # All IPs should be allowed when disabled
        assert manager.is_ip_allowed("192.168.1.1") is True
        assert manager.is_ip_allowed("10.0.0.1") is True
        assert manager.is_ip_allowed("203.0.113.1") is True
    
    def test_should_check_path(self, manager):
        """Test path exclusion logic"""
        # Excluded paths
        assert manager.should_check_path("/health") is False
        assert manager.should_check_path("/metrics") is False
        assert manager.should_check_path("/docs") is False
        
        # Non-excluded paths
        assert manager.should_check_path("/api/v1/test") is True
        assert manager.should_check_path("/admin") is True
    
    @pytest.mark.asyncio
    async def test_record_blocked_request(self, manager):
        """Test recording blocked requests"""
        request = MagicMock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.headers = {"user-agent": "test-client", "referer": "test-referer"}
        
        await manager.record_blocked_request(request, "192.168.1.1", "IP not in whitelist")
        
        assert len(manager.blocked_requests) == 1
        blocked_request = manager.blocked_requests[0]
        assert blocked_request["ip"] == "192.168.1.1"
        assert blocked_request["path"] == "/api/v1/test"
        assert blocked_request["method"] == "GET"
        assert blocked_request["reason"] == "IP not in whitelist"
    
    @pytest.mark.asyncio
    async def test_check_rate_limit(self, manager):
        """Test rate limiting functionality"""
        with patch('core.ip_whitelist.get_redis_client') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            # First request - should be allowed
            mock_client.get.return_value = None
            result = await manager.check_rate_limit("192.168.1.1")
            assert result is True
            
            # Request within limit - should be allowed
            mock_client.get.return_value = "500"
            result = await manager.check_rate_limit("192.168.1.1")
            assert result is True
            
            # Request exceeding limit - should be denied
            mock_client.get.return_value = "1000"
            result = await manager.check_rate_limit("192.168.1.1")
            assert result is False
    
    def test_get_stats(self, manager):
        """Test getting statistics"""
        # Add some test blocked requests
        manager.blocked_requests = [
            {
                "ip": "192.168.1.1",
                "reason": "IP not in whitelist"
            },
            {
                "ip": "192.168.1.1",
                "reason": "Rate limit exceeded"
            },
            {
                "ip": "10.0.0.1",
                "reason": "IP not in whitelist"
            }
        ]
        
        stats = manager.get_stats()
        
        assert stats["enabled"] is True
        assert stats["mode"] == "whitelist"
        assert stats["total_blocked_requests"] == 3
        assert stats["unique_blocked_ips"] == 2
        assert stats["top_blocked_ips"] == [("192.168.1.1", 2), ("10.0.0.1", 1)]
        assert stats["block_reasons"] == {"IP not in whitelist": 2, "Rate limit exceeded": 1}


class TestIPWhitelistMiddleware:
    """Test cases for IP whitelist middleware"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        return app
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=["192.168.1.0/24"],
            admin_ips=["192.168.1.10"],
            excluded_paths=["/health", "/metrics"],
            trust_proxy_headers=True,
            environment="test"
        )
    
    @pytest.fixture
    def client(self, app, config):
        """Create test client with IP whitelist middleware"""
        app.add_middleware(IPWhitelistMiddleware, config=config)
        return TestClient(app)
    
    def test_middleware_allows_whitelisted_ip(self, client):
        """Test that middleware allows whitelisted IPs"""
        # Mock the client IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.1"
            
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
    
    def test_middleware_blocks_non_whitelisted_ip(self, client):
        """Test that middleware blocks non-whitelisted IPs"""
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "10.0.0.1"
            
            response = client.get("/test")
            assert response.status_code == 403
            assert "IP_ACCESS_DENIED" in response.json()["error"]["code"]
    
    def test_middleware_allows_admin_ip(self, client):
        """Test that middleware allows admin IPs"""
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.10"
            
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
    
    def test_middleware_skips_excluded_paths(self, client):
        """Test that middleware skips excluded paths"""
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "10.0.0.1"  # Non-whitelisted IP
            
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    
    def test_middleware_disabled(self, app):
        """Test middleware when disabled"""
        config = IPWhitelistConfig(enabled=False)
        app.add_middleware(IPWhitelistMiddleware, config=config)
        client = TestClient(app)
        
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "10.0.0.1"
            
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
    
    def test_middleware_blacklist_mode(self, app):
        """Test middleware in blacklist mode"""
        config = IPWhitelistConfig(
            enabled=True,
            mode="blacklist",
            blocked_ips=["192.168.1.100"],
            environment="test"
        )
        app.add_middleware(IPWhitelistMiddleware, config=config)
        client = TestClient(app)
        
        # Allowed IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.1"
            
            response = client.get("/test")
            assert response.status_code == 200
        
        # Blocked IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.100"
            
            response = client.get("/test")
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_middleware_rate_limiting(self, app):
        """Test middleware rate limiting"""
        config = IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=["192.168.1.0/24"],
            enable_rate_limiting=True,
            rate_limit_requests=1,
            rate_limit_window=60,
            environment="test"
        )
        app.add_middleware(IPWhitelistMiddleware, config=config)
        client = TestClient(app)
        
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.1"
            
            with patch('core.ip_whitelist.IPWhitelistManager.check_rate_limit') as mock_rate_limit:
                # First request - allowed
                mock_rate_limit.return_value = True
                response = client.get("/test")
                assert response.status_code == 200
                
                # Second request - rate limited
                mock_rate_limit.return_value = False
                response = client.get("/test")
                assert response.status_code == 403
                assert "Rate limit exceeded" in response.json()["error"]["message"]
    
    def test_middleware_development_environment(self, app):
        """Test middleware in development environment"""
        config = IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=[],  # Empty allowed IPs
            environment="development"
        )
        app.add_middleware(IPWhitelistMiddleware, config=config)
        client = TestClient(app)
        
        # Should add default development IPs
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "127.0.0.1"
            
            response = client.get("/test")
            assert response.status_code == 200


class TestIPWhitelistRoutes:
    """Test cases for IP whitelist management routes"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with IP whitelist routes"""
        app = FastAPI()
        
        from api.ip_whitelist_routes import router
        app.include_router(router)
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        user = MagicMock()
        user.id = "user-123"
        user.is_admin = True
        return user
    
    def test_get_status_endpoint(self, client, mock_user):
        """Test IP whitelist status endpoint"""
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=mock_user):
            with patch('api.ip_whitelist_routes.get_ip_whitelist_manager') as mock_manager:
                mock_manager.return_value.get_stats.return_value = {
                    "enabled": True,
                    "mode": "whitelist",
                    "total_blocked_requests": 10,
                    "unique_blocked_ips": 5,
                    "allowed_ip_count": 3,
                    "blocked_ip_count": 2,
                    "admin_ip_count": 1
                }
                mock_manager.return_value.config.enable_rate_limiting = True
                mock_manager.return_value.config.trust_proxy_headers = True
                
                response = client.get("/api/v1/ip-whitelist/status")
                
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["mode"] == "whitelist"
                assert data["total_blocked_requests"] == 10
                assert data["unique_blocked_ips"] == 5
    
    def test_get_config_endpoint(self, client, mock_user):
        """Test IP whitelist config endpoint"""
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=mock_user):
            with patch('api.ip_whitelist_routes.get_ip_whitelist_manager') as mock_manager:
                mock_config = MagicMock()
                mock_config.enabled = True
                mock_config.mode = "whitelist"
                mock_config.allowed_ips = ["192.168.1.0/24"]
                mock_config.blocked_ips = ["192.168.1.100"]
                mock_config.admin_ips = ["192.168.1.10"]
                mock_config.excluded_paths = ["/health"]
                mock_config.trust_proxy_headers = True
                mock_config.max_proxy_depth = 3
                mock_config.enable_rate_limiting = True
                mock_config.rate_limit_requests = 1000
                mock_config.rate_limit_window = 3600
                mock_config.log_blocked_requests = True
                mock_config.log_allowed_requests = False
                
                mock_manager.return_value.config = mock_config
                
                response = client.get("/api/v1/ip-whitelist/config")
                
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["mode"] == "whitelist"
                assert data["allowed_ips"] == ["192.168.1.0/24"]
                assert data["blocked_ips"] == ["192.168.1.100"]
                assert data["admin_ips"] == ["192.168.1.10"]
    
    def test_get_blocked_requests_endpoint(self, client, mock_user):
        """Test blocked requests endpoint"""
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=mock_user):
            with patch('api.ip_whitelist_routes.get_ip_whitelist_manager') as mock_manager:
                mock_manager.return_value.get_blocked_requests.return_value = [
                    {
                        "timestamp": "2024-01-01T10:00:00",
                        "ip": "192.168.1.1",
                        "path": "/api/v1/test",
                        "method": "GET",
                        "user_agent": "test-client",
                        "referer": "test-referer",
                        "reason": "IP not in whitelist"
                    }
                ]
                
                response = client.get("/api/v1/ip-whitelist/blocked-requests")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["ip"] == "192.168.1.1"
                assert data[0]["path"] == "/api/v1/test"
                assert data[0]["reason"] == "IP not in whitelist"
    
    def test_add_ip_endpoint(self, client, mock_user):
        """Test add IP endpoint"""
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=mock_user):
            with patch('api.ip_whitelist_routes.get_ip_whitelist_manager') as mock_manager:
                mock_config = MagicMock()
                mock_config.allowed_ips = []
                mock_manager.return_value.config = mock_config
                
                # Mock the get_ip_whitelist_config function call
                with patch('api.ip_whitelist_routes.get_ip_whitelist_config') as mock_get_config:
                    mock_get_config.return_value = mock_config
                    
                    data = {
                        "ip": "192.168.1.1",
                        "list_type": "allowed",
                        "description": "Test IP"
                    }
                    
                    response = client.post("/api/v1/ip-whitelist/ip/add", json=data)
                    
                    assert response.status_code == 200
                    assert "192.168.1.1" in mock_config.allowed_ips
    
    def test_test_ip_endpoint(self, client, mock_user):
        """Test IP testing endpoint"""
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=mock_user):
            with patch('api.ip_whitelist_routes.get_ip_whitelist_manager') as mock_manager:
                mock_manager.return_value.is_ip_allowed.return_value = True
                mock_manager.return_value.config.mode = "whitelist"
                mock_manager.return_value.config.enabled = True
                mock_manager.return_value.admin_matcher.matches.return_value = False
                mock_manager.return_value.allowed_matcher.matches.return_value = True
                mock_manager.return_value.blocked_matcher.matches.return_value = False
                
                response = client.get("/api/v1/ip-whitelist/test-ip/192.168.1.1")
                
                assert response.status_code == 200
                data = response.json()
                assert data["ip"] == "192.168.1.1"
                assert data["allowed"] is True
                assert data["mode"] == "whitelist"
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints"""
        response = client.get("/api/v1/ip-whitelist/status")
        assert response.status_code == 401
        
        response = client.get("/api/v1/ip-whitelist/config")
        assert response.status_code == 401
        
        response = client.get("/api/v1/ip-whitelist/blocked-requests")
        assert response.status_code == 401
    
    def test_non_admin_access(self, client):
        """Test non-admin access to admin endpoints"""
        non_admin_user = MagicMock()
        non_admin_user.id = "user-456"
        non_admin_user.is_admin = False
        
        with patch('api.ip_whitelist_routes.get_current_active_user', return_value=non_admin_user):
            data = {
                "ip": "192.168.1.1",
                "list_type": "allowed"
            }
            
            response = client.post("/api/v1/ip-whitelist/ip/add", json=data)
            assert response.status_code == 403
            
            response = client.delete("/api/v1/ip-whitelist/blocked-requests")
            assert response.status_code == 403


class TestIPWhitelistIntegration:
    """Integration tests for IP whitelist system"""
    
    def test_full_ip_whitelist_pipeline(self):
        """Test complete IP whitelist pipeline"""
        app = FastAPI()
        
        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add IP whitelist middleware
        config = IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=["192.168.1.0/24"],
            admin_ips=["192.168.1.10"],
            environment="test"
        )
        app.add_middleware(IPWhitelistMiddleware, config=config)
        
        client = TestClient(app)
        
        # Test allowed IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.1"
            
            response = client.get("/api/v1/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
        
        # Test blocked IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "10.0.0.1"
            
            response = client.get("/api/v1/test")
            assert response.status_code == 403
            assert "IP_ACCESS_DENIED" in response.json()["error"]["code"]
        
        # Test admin IP
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "192.168.1.10"
            
            response = client.get("/api/v1/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
    
    def test_environment_specific_behavior(self):
        """Test environment-specific behavior"""
        # Test development environment
        dev_app = FastAPI()
        dev_config = IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=[],
            environment="development"
        )
        dev_app.add_middleware(IPWhitelistMiddleware, config=dev_config)
        
        @dev_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        dev_client = TestClient(dev_app)
        
        # Development should allow localhost
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "127.0.0.1"
            
            response = dev_client.get("/test")
            assert response.status_code == 200
        
        # Test production environment
        prod_app = FastAPI()
        prod_config = IPWhitelistConfig(
            enabled=True,
            mode="whitelist",
            allowed_ips=["192.168.1.0/24"],
            environment="production"
        )
        prod_app.add_middleware(IPWhitelistMiddleware, config=prod_config)
        
        @prod_app.get("/test")
        async def prod_test_endpoint():
            return {"message": "test"}
        
        prod_client = TestClient(prod_app)
        
        # Production should be strict
        with patch('core.ip_whitelist.IPWhitelistManager.extract_client_ip') as mock_extract:
            mock_extract.return_value = "127.0.0.1"
            
            response = prod_client.get("/test")
            # Should be blocked unless explicitly allowed
            assert response.status_code == 403