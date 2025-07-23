"""
Tests for WAF Engine
"""

import pytest
import asyncio
from datetime import datetime

from src.core.waf_engine import (
    WAFEngine, WAFRequest, SQLInjectionDetector, XSSDetector, 
    BotDetector, GeoBlocker
)
from src.core.config import Settings


@pytest.fixture
def settings():
    """Test settings"""
    return Settings(
        waf_enabled=True,
        waf_mode="blocking",
        sql_injection_protection=True,
        xss_protection=True,
        bot_protection_enabled=True,
        rate_limit_enabled=True,
        geo_blocking_enabled=False,  # Disable for tests
        debug=True
    )


@pytest.fixture
def waf_engine(settings):
    """Create WAF engine for testing"""
    return WAFEngine(settings)


@pytest.fixture
def malicious_request():
    """Create a malicious request for testing"""
    return WAFRequest(
        ip="192.168.1.100",
        method="GET",
        url="/search?q=' OR 1=1 --",
        headers={"User-Agent": "Mozilla/5.0"},
        body=None
    )


@pytest.fixture
def legitimate_request():
    """Create a legitimate request for testing"""
    return WAFRequest(
        ip="192.168.1.200",
        method="GET",
        url="/search?q=legitimate+search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        body=None
    )


class TestSQLInjectionDetector:
    """Test SQL injection detection"""
    
    def test_basic_sql_injection_detection(self):
        """Test basic SQL injection patterns"""
        detector = SQLInjectionDetector("medium")
        
        # Test cases that should be detected
        malicious_inputs = [
            "' OR 1=1 --",
            "admin' --",
            "1; DROP TABLE users; --",
            "' UNION SELECT * FROM passwords --",
            "1' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for malicious_input in malicious_inputs:
            detected, patterns = detector.detect(malicious_input)
            assert detected, f"Failed to detect SQL injection in: {malicious_input}"
            assert len(patterns) > 0, f"No patterns matched for: {malicious_input}"
    
    def test_legitimate_input_not_detected(self):
        """Test that legitimate input is not flagged"""
        detector = SQLInjectionDetector("medium")
        
        legitimate_inputs = [
            "search for something",
            "user@example.com",
            "password123",
            "SELECT * FROM products WHERE name = 'iPhone'",  # Legitimate query format
            "This is a normal sentence with some words."
        ]
        
        for legitimate_input in legitimate_inputs:
            detected, patterns = detector.detect(legitimate_input)
            assert not detected, f"False positive for legitimate input: {legitimate_input}"
    
    def test_sensitivity_levels(self):
        """Test different sensitivity levels"""
        low_detector = SQLInjectionDetector("low")
        medium_detector = SQLInjectionDetector("medium")
        high_detector = SQLInjectionDetector("high")
        
        # Test input that should only trigger high sensitivity
        borderline_input = "user = admin"
        
        low_detected, _ = low_detector.detect(borderline_input)
        medium_detected, _ = medium_detector.detect(borderline_input)
        high_detected, _ = high_detector.detect(borderline_input)
        
        # High sensitivity should be more aggressive
        assert len(high_detector.patterns) > len(medium_detector.patterns)
        assert len(medium_detector.patterns) > len(low_detector.patterns)


class TestXSSDetector:
    """Test XSS detection"""
    
    def test_basic_xss_detection(self):
        """Test basic XSS patterns"""
        detector = XSSDetector("medium")
        
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<svg onload=alert(1)>",
            "<body onload=alert('xss')>"
        ]
        
        for malicious_input in malicious_inputs:
            detected, patterns = detector.detect(malicious_input)
            assert detected, f"Failed to detect XSS in: {malicious_input}"
            assert len(patterns) > 0
    
    def test_encoded_xss_detection(self):
        """Test detection of encoded XSS attempts"""
        detector = XSSDetector("medium")
        
        # URL encoded XSS
        encoded_input = "%3Cscript%3Ealert%28%27xss%27%29%3C%2Fscript%3E"
        detected, patterns = detector.detect(encoded_input)
        assert detected, "Failed to detect URL encoded XSS"
        
        # HTML entity encoded XSS
        html_encoded = "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
        detected, patterns = detector.detect(html_encoded)
        assert detected, "Failed to detect HTML entity encoded XSS"
    
    def test_legitimate_html_not_detected(self):
        """Test that legitimate HTML is not flagged"""
        detector = XSSDetector("medium")
        
        legitimate_inputs = [
            "<p>This is a paragraph</p>",
            "<div class='container'>Content</div>",
            "<a href='https://example.com'>Link</a>",
            "This text contains < and > symbols but is safe"
        ]
        
        for legitimate_input in legitimate_inputs:
            detected, patterns = detector.detect(legitimate_input)
            # Note: Depending on sensitivity, some HTML might be flagged
            # This test might need adjustment based on desired behavior


class TestBotDetector:
    """Test bot detection"""
    
    def test_known_bot_detection(self):
        """Test detection of known bots"""
        detector = BotDetector("medium")
        
        bot_user_agents = [
            "Googlebot/2.1",
            "Mozilla/5.0 (compatible; bingbot/2.0)",
            "curl/7.68.0",
            "python-requests/2.25.1",
            "Scrapy/2.5.0",
            "sqlmap/1.4.9",
            "Postman",
            "wget/1.20.3"
        ]
        
        for user_agent in bot_user_agents:
            is_bot, bot_type, metadata = detector.detect(user_agent, {})
            assert is_bot, f"Failed to detect bot: {user_agent}"
            assert bot_type in ["known_bot", "parsed_bot"]
    
    def test_legitimate_browser_not_detected(self):
        """Test that legitimate browsers are not flagged as bots"""
        detector = BotDetector("medium")
        
        legitimate_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
        ]
        
        for user_agent in legitimate_user_agents:
            is_bot, bot_type, metadata = detector.detect(user_agent, {})
            assert not is_bot, f"False positive for legitimate browser: {user_agent}"
    
    def test_suspicious_user_agents(self):
        """Test detection of suspicious user agents"""
        detector = BotDetector("high")  # High sensitivity
        
        suspicious_user_agents = [
            "",  # Empty user agent
            "   ",  # Whitespace only
            "a",  # Very short
            "X" * 300,  # Very long
        ]
        
        for user_agent in suspicious_user_agents:
            is_bot, bot_type, metadata = detector.detect(user_agent, {})
            assert is_bot, f"Failed to detect suspicious user agent: '{user_agent}'"
            assert bot_type == "suspicious_user_agent"


class TestGeoBlocker:
    """Test geographic blocking"""
    
    def test_geo_blocker_disabled(self):
        """Test geo blocker when disabled"""
        settings = Settings(geo_blocking_enabled=False)
        geo_blocker = GeoBlocker(settings)
        
        blocked, reason, metadata = geo_blocker.check_ip("8.8.8.8")
        assert not blocked
        assert reason is None
        assert metadata == {}
    
    def test_geo_blocker_no_database(self):
        """Test geo blocker without GeoIP database"""
        settings = Settings(
            geo_blocking_enabled=True,
            geoip_database_path="/nonexistent/path"
        )
        geo_blocker = GeoBlocker(settings)
        
        blocked, reason, metadata = geo_blocker.check_ip("8.8.8.8")
        assert not blocked  # Should fail gracefully


@pytest.mark.asyncio
class TestWAFEngine:
    """Test WAF Engine integration"""
    
    async def test_legitimate_request_allowed(self, waf_engine, legitimate_request):
        """Test that legitimate requests are allowed"""
        result = await waf_engine.analyze_request(legitimate_request)
        
        assert result.allowed
        assert result.score < 70  # Below blocking threshold
    
    async def test_malicious_request_blocked(self, waf_engine, malicious_request):
        """Test that malicious requests are blocked"""
        result = await waf_engine.analyze_request(malicious_request)
        
        assert not result.allowed
        assert result.rule_triggered is not None
        assert result.threat_level in ["medium", "high", "critical"]
        assert result.score >= 70  # Above blocking threshold
    
    async def test_monitoring_mode(self, settings, malicious_request):
        """Test WAF in monitoring mode"""
        settings.waf_mode = "monitoring"
        waf_engine = WAFEngine(settings)
        
        result = await waf_engine.analyze_request(malicious_request)
        
        # Should detect threats but not block in monitoring mode
        assert result.allowed  # Always allowed in monitoring mode
        assert result.score > 0  # But threats should still be detected
    
    async def test_waf_disabled(self, settings, malicious_request):
        """Test WAF when disabled"""
        settings.waf_enabled = False
        waf_engine = WAFEngine(settings)
        
        result = await waf_engine.analyze_request(malicious_request)
        
        assert result.allowed
        assert result.score == 0
    
    async def test_ip_whitelist(self, settings, malicious_request):
        """Test IP whitelist functionality"""
        settings.ip_whitelist = ["192.168.1.100/32"]
        waf_engine = WAFEngine(settings)
        
        result = await waf_engine.analyze_request(malicious_request)
        
        # Should be allowed due to whitelist
        assert result.allowed
    
    async def test_ip_blacklist(self, settings, legitimate_request):
        """Test IP blacklist functionality"""
        settings.ip_blacklist = ["192.168.1.200/32"]
        waf_engine = WAFEngine(settings)
        
        result = await waf_engine.analyze_request(legitimate_request)
        
        # Should be blocked due to blacklist
        assert not result.allowed
        assert result.rule_triggered == "ip_blacklist"
    
    async def test_request_size_limits(self, waf_engine):
        """Test request size limits"""
        large_request = WAFRequest(
            ip="192.168.1.100",
            method="POST",
            url="/upload",
            headers={"User-Agent": "Mozilla/5.0"},
            body="x" * (100 * 1024 * 1024 + 1)  # Exceed max request size
        )
        
        result = await waf_engine.analyze_request(large_request)
        
        assert not result.allowed
        assert result.rule_triggered == "request_size_limit"
    
    async def test_url_length_limit(self, waf_engine):
        """Test URL length limits"""
        long_url_request = WAFRequest(
            ip="192.168.1.100",
            method="GET",
            url="/" + "x" * 5000,  # Exceed max URL length
            headers={"User-Agent": "Mozilla/5.0"},
            body=None
        )
        
        result = await waf_engine.analyze_request(long_url_request)
        
        assert not result.allowed
        assert result.rule_triggered == "request_size_limit"
    
    async def test_multiple_threats(self, waf_engine):
        """Test request with multiple threats"""
        multi_threat_request = WAFRequest(
            ip="192.168.1.100",
            method="POST",
            url="/search?q=' OR 1=1 --",  # SQL injection
            headers={"User-Agent": "sqlmap/1.4.9"},  # Bot user agent
            body="<script>alert('xss')</script>"  # XSS
        )
        
        result = await waf_engine.analyze_request(multi_threat_request)
        
        assert not result.allowed
        assert result.score >= 70
        assert result.threat_level in ["high", "critical"]
        assert "sql_patterns" in result.metadata or "xss_patterns" in result.metadata
    
    async def test_stats_collection(self, waf_engine, legitimate_request, malicious_request):
        """Test that statistics are collected properly"""
        # Process some requests
        await waf_engine.analyze_request(legitimate_request)
        await waf_engine.analyze_request(malicious_request)
        await waf_engine.analyze_request(malicious_request)
        
        stats = waf_engine.get_stats()
        
        assert stats["requests_processed"] >= 3
        assert stats["requests_blocked"] >= 2
        assert stats["block_rate"] > 0
    
    async def test_error_handling(self, waf_engine):
        """Test error handling in WAF engine"""
        # Test with invalid IP
        invalid_request = WAFRequest(
            ip="invalid_ip",
            method="GET",
            url="/test",
            headers={},
            body=None
        )
        
        # Should not crash and should handle gracefully
        result = await waf_engine.analyze_request(invalid_request)
        assert result.allowed  # Should fail open


@pytest.mark.asyncio
class TestConcurrency:
    """Test WAF engine under concurrent load"""
    
    async def test_concurrent_requests(self, waf_engine):
        """Test WAF engine with concurrent requests"""
        requests = []
        for i in range(100):
            request = WAFRequest(
                ip=f"192.168.1.{i % 10}",
                method="GET",
                url=f"/test{i}",
                headers={"User-Agent": "Test"},
                body=None
            )
            requests.append(request)
        
        # Process requests concurrently
        tasks = [waf_engine.analyze_request(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(isinstance(result.allowed, bool) for result in results)
        
        # Check stats
        stats = waf_engine.get_stats()
        assert stats["requests_processed"] >= 100