"""
Tests for Security Headers Middleware

Comprehensive tests for security headers middleware, CSP violation reporting,
and security configuration management.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json
from datetime import datetime, timedelta

from core.security_headers import (
    SecurityHeadersConfig,
    SecurityHeadersBuilder,
    SecurityHeadersMiddleware,
    CSPViolationReporter,
    get_security_headers_config,
    get_csp_reporter
)
from api.security_routes import (
    CSPViolationReport,
    SecurityHeadersStatus,
    SecurityHeadersConfigResponse,
    ViolationStats
)


class TestSecurityHeadersConfig:
    """Test cases for security headers configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = SecurityHeadersConfig()
        
        assert config.csp_default_src == ["'self'"]
        assert config.csp_script_src == ["'self'", "'unsafe-inline'"]
        assert config.csp_style_src == ["'self'", "'unsafe-inline'"]
        assert config.csp_img_src == ["'self'", "data:", "https:"]
        assert config.csp_font_src == ["'self'", "https:"]
        assert config.csp_connect_src == ["'self'", "https:", "wss:"]
        assert config.csp_media_src == ["'self'", "https:"]
        assert config.csp_object_src == ["'none'"]
        assert config.csp_base_uri == ["'self'"]
        assert config.csp_form_action == ["'self'"]
        assert config.csp_frame_ancestors == ["'none'"]
        assert config.csp_report_uri is None
        assert config.csp_report_only is False
        
        assert config.hsts_max_age == 31536000
        assert config.hsts_include_subdomains is True
        assert config.hsts_preload is False
        
        assert config.frame_options == "DENY"
        assert config.content_type_options == "nosniff"
        assert config.xss_protection == "1; mode=block"
        assert config.referrer_policy == "strict-origin-when-cross-origin"
        
        assert config.cross_origin_embedder_policy == "require-corp"
        assert config.cross_origin_opener_policy == "same-origin"
        assert config.cross_origin_resource_policy == "same-origin"
        
        assert config.server_header is None
        assert config.x_powered_by is None
        
        assert config.x_dns_prefetch_control == "off"
        assert config.x_download_options == "noopen"
        assert config.x_permitted_cross_domain_policies == "none"
        
        assert config.environment == "production"
        assert config.enable_csp is True
        assert config.enable_hsts is True
        assert config.log_security_headers is False
        assert config.log_violations is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = SecurityHeadersConfig(
            csp_default_src=["'self'", "https://example.com"],
            hsts_max_age=86400,
            frame_options="SAMEORIGIN",
            environment="development",
            enable_hsts=False,
            log_security_headers=True
        )
        
        assert config.csp_default_src == ["'self'", "https://example.com"]
        assert config.hsts_max_age == 86400
        assert config.frame_options == "SAMEORIGIN"
        assert config.environment == "development"
        assert config.enable_hsts is False
        assert config.log_security_headers is True
    
    def test_permissions_policy_config(self):
        """Test permissions policy configuration"""
        config = SecurityHeadersConfig()
        
        assert "camera" in config.permissions_policy
        assert "microphone" in config.permissions_policy
        assert "geolocation" in config.permissions_policy
        assert "payment" in config.permissions_policy
        assert "usb" in config.permissions_policy
        assert "autoplay" in config.permissions_policy
        assert "fullscreen" in config.permissions_policy
        
        assert config.permissions_policy["camera"] == []
        assert config.permissions_policy["autoplay"] == ["'self'"]
        assert config.permissions_policy["fullscreen"] == ["'self'"]


class TestSecurityHeadersBuilder:
    """Test cases for security headers builder"""
    
    @pytest.fixture
    def builder(self):
        """Create builder instance"""
        config = SecurityHeadersConfig()
        return SecurityHeadersBuilder(config)
    
    def test_build_csp_header_basic(self, builder):
        """Test basic CSP header building"""
        csp = builder.build_csp_header()
        
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data: https:" in csp
        assert "font-src 'self' https:" in csp
        assert "connect-src 'self' https: wss:" in csp
        assert "media-src 'self' https:" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_build_csp_header_with_report_uri(self):
        """Test CSP header with report URI"""
        config = SecurityHeadersConfig(csp_report_uri="https://example.com/csp-report")
        builder = SecurityHeadersBuilder(config)
        
        csp = builder.build_csp_header()
        assert "report-uri https://example.com/csp-report" in csp
    
    def test_build_csp_header_disabled(self):
        """Test CSP header when disabled"""
        config = SecurityHeadersConfig(enable_csp=False)
        builder = SecurityHeadersBuilder(config)
        
        csp = builder.build_csp_header()
        assert csp is None
    
    def test_build_hsts_header_basic(self, builder):
        """Test basic HSTS header building"""
        hsts = builder.build_hsts_header()
        
        assert hsts is not None
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" not in hsts
    
    def test_build_hsts_header_with_preload(self):
        """Test HSTS header with preload"""
        config = SecurityHeadersConfig(hsts_preload=True)
        builder = SecurityHeadersBuilder(config)
        
        hsts = builder.build_hsts_header()
        assert "preload" in hsts
    
    def test_build_hsts_header_disabled(self):
        """Test HSTS header when disabled"""
        config = SecurityHeadersConfig(enable_hsts=False)
        builder = SecurityHeadersBuilder(config)
        
        hsts = builder.build_hsts_header()
        assert hsts is None
    
    def test_build_permissions_policy_header(self, builder):
        """Test permissions policy header building"""
        policy = builder.build_permissions_policy_header()
        
        assert policy is not None
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy
        assert "autoplay=('self')" in policy
        assert "fullscreen=('self')" in policy
    
    def test_build_permissions_policy_header_disabled(self):
        """Test permissions policy header when disabled"""
        config = SecurityHeadersConfig(enable_permissions_policy=False)
        builder = SecurityHeadersBuilder(config)
        
        policy = builder.build_permissions_policy_header()
        assert policy is None
    
    def test_build_all_headers_basic(self, builder):
        """Test building all headers"""
        # Mock request and response
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock()
        
        headers = builder.build_all_headers(request, response)
        
        assert "Content-Security-Policy" in headers
        assert "Strict-Transport-Security" in headers
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers
        assert "Cross-Origin-Embedder-Policy" in headers
        assert "Cross-Origin-Opener-Policy" in headers
        assert "Cross-Origin-Resource-Policy" in headers
        assert "X-DNS-Prefetch-Control" in headers
        assert "X-Download-Options" in headers
        assert "X-Permitted-Cross-Domain-Policies" in headers
        
        # Check that server identification headers are removed
        assert headers.get("Server") == ""
        assert headers.get("X-Powered-By") == ""
    
    def test_build_all_headers_http_scheme(self, builder):
        """Test building headers for HTTP scheme (no HSTS)"""
        request = MagicMock()
        request.url.scheme = "http"
        response = MagicMock()
        
        headers = builder.build_all_headers(request, response)
        
        assert "Content-Security-Policy" in headers
        assert "Strict-Transport-Security" not in headers  # No HSTS for HTTP
        assert "X-Frame-Options" in headers
    
    def test_build_all_headers_report_only(self):
        """Test CSP report-only mode"""
        config = SecurityHeadersConfig(csp_report_only=True)
        builder = SecurityHeadersBuilder(config)
        
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock()
        
        headers = builder.build_all_headers(request, response)
        
        assert "Content-Security-Policy-Report-Only" in headers
        assert "Content-Security-Policy" not in headers


class TestCSPViolationReporter:
    """Test cases for CSP violation reporter"""
    
    @pytest.fixture
    def reporter(self):
        """Create reporter instance"""
        return CSPViolationReporter()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Test Browser)",
            "referer": "https://example.com/page"
        }
        return request
    
    @pytest.mark.asyncio
    async def test_report_violation_basic(self, reporter, mock_request):
        """Test basic violation reporting"""
        violation_data = {
            "document-uri": "https://example.com/page",
            "violated-directive": "script-src",
            "blocked-uri": "https://malicious.com/script.js",
            "original-policy": "script-src 'self'"
        }
        
        initial_count = len(reporter.violations)
        
        await reporter.report_violation(mock_request, violation_data)
        
        assert len(reporter.violations) == initial_count + 1
        
        violation = reporter.violations[-1]
        assert violation["client_ip"] == "192.168.1.1"
        assert violation["user_agent"] == "Mozilla/5.0 (Test Browser)"
        assert violation["referer"] == "https://example.com/page"
        assert violation["violation"] == violation_data
        assert "timestamp" in violation
    
    @pytest.mark.asyncio
    async def test_report_violation_limit(self, reporter, mock_request):
        """Test violation storage limit"""
        violation_data = {
            "document-uri": "https://example.com/page",
            "violated-directive": "script-src",
            "blocked-uri": "https://malicious.com/script.js"
        }
        
        # Add violations beyond the limit
        for i in range(1005):
            await reporter.report_violation(mock_request, violation_data)
        
        # Should not exceed max violations
        assert len(reporter.violations) <= reporter.max_violations
    
    def test_get_violations_all(self, reporter):
        """Test getting all violations"""
        # Add some test violations
        reporter.violations = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "client_ip": "192.168.1.1",
                "violation": {"violated-directive": "script-src"}
            },
            {
                "timestamp": "2024-01-01T11:00:00",
                "client_ip": "192.168.1.2",
                "violation": {"violated-directive": "style-src"}
            }
        ]
        
        violations = reporter.get_violations()
        assert len(violations) == 2
    
    def test_get_violations_since(self, reporter):
        """Test getting violations since specific time"""
        # Add test violations with different timestamps
        reporter.violations = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "violation": {"violated-directive": "script-src"}
            },
            {
                "timestamp": "2024-01-01T12:00:00",
                "violation": {"violated-directive": "style-src"}
            }
        ]
        
        since = datetime(2024, 1, 1, 11, 0, 0)
        violations = reporter.get_violations(since=since)
        
        assert len(violations) == 1
        assert violations[0]["timestamp"] == "2024-01-01T12:00:00"
    
    def test_get_violation_stats(self, reporter):
        """Test getting violation statistics"""
        # Add test violations
        reporter.violations = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "client_ip": "192.168.1.1",
                "violation": {"violated-directive": "script-src"}
            },
            {
                "timestamp": "2024-01-01T11:00:00",
                "client_ip": "192.168.1.1",
                "violation": {"violated-directive": "script-src"}
            },
            {
                "timestamp": "2024-01-01T12:00:00",
                "client_ip": "192.168.1.2",
                "violation": {"violated-directive": "style-src"}
            }
        ]
        
        stats = reporter.get_violation_stats()
        
        assert stats["total"] == 3
        assert stats["by_type"]["script-src"] == 2
        assert stats["by_type"]["style-src"] == 1
        assert stats["by_ip"]["192.168.1.1"] == 2
        assert stats["by_ip"]["192.168.1.2"] == 1
        assert stats["latest"] == "2024-01-01T12:00:00"
    
    def test_get_violation_stats_empty(self, reporter):
        """Test getting violation statistics when empty"""
        stats = reporter.get_violation_stats()
        
        assert stats["total"] == 0
        assert stats["by_type"] == {}
        assert stats["by_ip"] == {}
        assert stats["latest"] is None


class TestSecurityHeadersMiddleware:
    """Test cases for security headers middleware"""
    
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
    def client(self, app):
        """Create test client with security headers middleware"""
        config = SecurityHeadersConfig(environment="test")
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        return TestClient(app)
    
    def test_middleware_adds_security_headers(self, client):
        """Test that middleware adds security headers"""
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check that security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        assert "Cross-Origin-Embedder-Policy" in response.headers
        assert "Cross-Origin-Opener-Policy" in response.headers
        assert "Cross-Origin-Resource-Policy" in response.headers
        assert "X-DNS-Prefetch-Control" in response.headers
        assert "X-Download-Options" in response.headers
        assert "X-Permitted-Cross-Domain-Policies" in response.headers
        
        # Check header values
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["X-DNS-Prefetch-Control"] == "off"
        assert response.headers["X-Download-Options"] == "noopen"
        assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    
    def test_middleware_skips_excluded_paths(self, client):
        """Test that middleware skips excluded paths"""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Health endpoint should not have security headers
        assert "Content-Security-Policy" not in response.headers
        assert "X-Frame-Options" not in response.headers
    
    def test_middleware_development_environment(self, app):
        """Test middleware in development environment"""
        config = SecurityHeadersConfig(environment="development")
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Should have CSP but no HSTS in development
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" not in response.headers
        
        # CSP should be more permissive in development
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-eval'" in csp
        assert "http://localhost:" in csp
    
    def test_middleware_production_environment(self, app):
        """Test middleware in production environment"""
        config = SecurityHeadersConfig(environment="production")
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        
        # Mock HTTPS request
        with patch('fastapi.Request') as mock_request:
            mock_request.url.scheme = "https"
            client = TestClient(app)
            
            response = client.get("/test")
            
            assert response.status_code == 200
            
            # Should have strict CSP and HSTS in production
            assert "Content-Security-Policy" in response.headers
            
            # CSP should be strict in production
            csp = response.headers["Content-Security-Policy"]
            assert "'unsafe-eval'" not in csp
            assert "http://localhost:" not in csp
    
    def test_middleware_csp_report_only_mode(self, app):
        """Test CSP report-only mode"""
        config = SecurityHeadersConfig(csp_report_only=True)
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Should have CSP report-only header
        assert "Content-Security-Policy-Report-Only" in response.headers
        assert "Content-Security-Policy" not in response.headers
    
    def test_middleware_removes_server_headers(self, client):
        """Test that middleware removes server identification headers"""
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Server identification headers should be removed or empty
        assert response.headers.get("Server") in [None, ""]
        assert response.headers.get("X-Powered-By") in [None, ""]
    
    def test_middleware_custom_server_headers(self, app):
        """Test middleware with custom server headers"""
        config = SecurityHeadersConfig(
            server_header="Custom-Server/1.0",
            x_powered_by="Custom-Framework"
        )
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.headers["Server"] == "Custom-Server/1.0"
        assert response.headers["X-Powered-By"] == "Custom-Framework"
    
    def test_middleware_disabled_features(self, app):
        """Test middleware with disabled features"""
        config = SecurityHeadersConfig(
            enable_csp=False,
            enable_hsts=False,
            enable_frame_options=False,
            enable_permissions_policy=False
        )
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Disabled headers should not be present
        assert "Content-Security-Policy" not in response.headers
        assert "Strict-Transport-Security" not in response.headers
        assert "X-Frame-Options" not in response.headers
        assert "Permissions-Policy" not in response.headers
        
        # Other headers should still be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


class TestSecurityRoutes:
    """Test cases for security management routes"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with security routes"""
        app = FastAPI()
        
        from api.security_routes import router
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
    
    def test_csp_violation_report_endpoint(self, client):
        """Test CSP violation report endpoint"""
        violation_data = {
            "csp-report": {
                "document-uri": "https://example.com/page",
                "violated-directive": "script-src",
                "blocked-uri": "https://malicious.com/script.js",
                "original-policy": "script-src 'self'"
            }
        }
        
        response = client.post("/api/v1/security/csp-report", json=violation_data)
        
        assert response.status_code == 204
    
    def test_security_status_endpoint(self, client, mock_user):
        """Test security status endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.get("/api/v1/security/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "environment" in data
            assert "csp_enabled" in data
            assert "hsts_enabled" in data
            assert "total_violations" in data
            assert "recent_violations" in data
    
    def test_security_config_endpoint(self, client, mock_user):
        """Test security config endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.get("/api/v1/security/config")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "environment" in data
            assert "csp_policy" in data
            assert "enabled_features" in data
            assert "configuration" in data
    
    def test_violations_endpoint(self, client, mock_user):
        """Test violations endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.get("/api/v1/security/violations")
            
            assert response.status_code == 200
            data = response.json()
            
            assert isinstance(data, list)
    
    def test_violation_stats_endpoint(self, client, mock_user):
        """Test violation stats endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.get("/api/v1/security/violations/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "total" in data
            assert "by_type" in data
            assert "by_ip" in data
            assert "time_period" in data
    
    def test_update_config_endpoint(self, client, mock_user):
        """Test update config endpoint"""
        update_data = {
            "csp_report_only": True,
            "log_security_headers": True
        }
        
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.post("/api/v1/security/config/update", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "environment" in data
            assert "configuration" in data
    
    def test_clear_violations_endpoint(self, client, mock_user):
        """Test clear violations endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.delete("/api/v1/security/violations")
            
            assert response.status_code == 204
    
    def test_test_headers_endpoint(self, client, mock_user):
        """Test security headers test endpoint"""
        with patch('api.security_routes.get_current_active_user', return_value=mock_user):
            response = client.get("/api/v1/security/headers/test")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "message" in data
            assert "timestamp" in data
            assert data["message"] == "Security headers test"
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints"""
        response = client.get("/api/v1/security/status")
        assert response.status_code == 401
        
        response = client.get("/api/v1/security/config")
        assert response.status_code == 401
        
        response = client.get("/api/v1/security/violations")
        assert response.status_code == 401
    
    def test_non_admin_access(self, client):
        """Test non-admin access to admin endpoints"""
        non_admin_user = MagicMock()
        non_admin_user.id = "user-456"
        non_admin_user.is_admin = False
        
        with patch('api.security_routes.get_current_active_user', return_value=non_admin_user):
            response = client.post("/api/v1/security/config/update", json={})
            assert response.status_code == 403
            
            response = client.delete("/api/v1/security/violations")
            assert response.status_code == 403


class TestSecurityHeadersIntegration:
    """Integration tests for security headers system"""
    
    def test_full_security_pipeline(self):
        """Test complete security headers pipeline"""
        app = FastAPI()
        
        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add security headers middleware
        config = SecurityHeadersConfig(environment="production")
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        
        client = TestClient(app)
        
        response = client.get("/api/v1/test")
        
        assert response.status_code == 200
        
        # Check that all security headers are present
        expected_headers = [
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy",
            "X-DNS-Prefetch-Control",
            "X-Download-Options",
            "X-Permitted-Cross-Domain-Policies"
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Missing header: {header}"
        
        # Check that server identification headers are removed
        assert response.headers.get("Server") in [None, ""]
        assert response.headers.get("X-Powered-By") in [None, ""]
    
    def test_csp_violation_flow(self):
        """Test CSP violation reporting flow"""
        app = FastAPI()
        
        from api.security_routes import router
        app.include_router(router)
        
        client = TestClient(app)
        
        # Report a CSP violation
        violation_data = {
            "csp-report": {
                "document-uri": "https://example.com/page",
                "violated-directive": "script-src",
                "blocked-uri": "https://malicious.com/script.js",
                "original-policy": "script-src 'self'"
            }
        }
        
        response = client.post("/api/v1/security/csp-report", json=violation_data)
        assert response.status_code == 204
        
        # Check that violation was stored
        reporter = get_csp_reporter()
        violations = reporter.get_violations()
        assert len(violations) > 0
        
        # Check violation details
        violation = violations[-1]
        assert violation["violation"]["violated-directive"] == "script-src"
        assert violation["violation"]["blocked-uri"] == "https://malicious.com/script.js"
    
    def test_environment_specific_behavior(self):
        """Test environment-specific behavior"""
        # Test development environment
        dev_app = FastAPI()
        dev_config = SecurityHeadersConfig(environment="development")
        dev_app.add_middleware(SecurityHeadersMiddleware, config=dev_config)
        
        @dev_app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        dev_client = TestClient(dev_app)
        dev_response = dev_client.get("/test")
        
        # Development should have permissive CSP and no HSTS
        dev_csp = dev_response.headers.get("Content-Security-Policy", "")
        assert "'unsafe-eval'" in dev_csp
        assert "http://localhost:" in dev_csp
        assert "Strict-Transport-Security" not in dev_response.headers
        
        # Test production environment
        prod_app = FastAPI()
        prod_config = SecurityHeadersConfig(environment="production")
        prod_app.add_middleware(SecurityHeadersMiddleware, config=prod_config)
        
        @prod_app.get("/test")
        async def prod_test_endpoint():
            return {"message": "test"}
        
        prod_client = TestClient(prod_app)
        prod_response = prod_client.get("/test")
        
        # Production should have strict CSP
        prod_csp = prod_response.headers.get("Content-Security-Policy", "")
        assert "'unsafe-eval'" not in prod_csp
        assert "http://localhost:" not in prod_csp
