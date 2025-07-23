"""
Web Application Firewall Engine - Core protection logic
"""

import re
import time
import asyncio
import ipaddress
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog
import geoip2.database
import geoip2.errors
from user_agents import parse as parse_user_agent

from .config import Settings

logger = structlog.get_logger()


@dataclass
class WAFRequest:
    """WAF request data structure"""
    ip: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class WAFResult:
    """WAF analysis result"""
    allowed: bool
    rule_triggered: Optional[str] = None
    threat_level: str = "low"  # low, medium, high, critical
    block_reason: Optional[str] = None
    score: int = 0  # threat score 0-100
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLInjectionDetector:
    """SQL injection detection engine"""
    
    def __init__(self, sensitivity: str = "medium"):
        self.sensitivity = sensitivity
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[re.Pattern]:
        """Load SQL injection patterns based on sensitivity"""
        # Basic patterns (always included)
        basic_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(\b(or|and)\s+\d+\s*=\s*\d+)",
            r"(\b(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bconcat\s*\()",
            r"(\bchar\s*\(\d+\))",
            r"(\bhex\s*\()",
            r"(\bload_file\s*\()",
            r"(\binto\s+outfile\b)",
            r"(\binto\s+dumpfile\b)",
        ]
        
        # Medium sensitivity patterns
        medium_patterns = [
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)",
            r"(\bsp_oacreate\b)",
            r"(\bsp_oamethod\b)",
            r"(\bwaitfor\s+delay\b)",
            r"(\bbenchmark\s*\()",
            r"(\bsleep\s*\()",
            r"(\bpg_sleep\s*\()",
            r"(\bdbms_pipe\.receive_message\b)",
            r"(\bextractvalue\s*\()",
            r"(\bupdatexml\s*\()",
        ]
        
        # High sensitivity patterns
        high_patterns = [
            r"('.*'.*=.*'.*')",
            r"(\d+\s*=\s*\d+)",
            r"(\w+\s*=\s*\w+)",
            r"(\blike\s+['\"]%)",
            r"(\bin\s*\(['\"])",
            r"(\bexists\s*\()",
            r"(\bhaving\s+\d+)",
            r"(\border\s+by\s+\d+)",
            r"(\blimit\s+\d+)",
            r"(\boffset\s+\d+)",
        ]
        
        patterns = basic_patterns
        if self.sensitivity in ["medium", "high"]:
            patterns.extend(medium_patterns)
        if self.sensitivity == "high":
            patterns.extend(high_patterns)
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """Detect SQL injection attempts"""
        if not text:
            return False, []
        
        matches = []
        for pattern in self.patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        
        return len(matches) > 0, matches


class XSSDetector:
    """Cross-Site Scripting detection engine"""
    
    def __init__(self, sensitivity: str = "medium"):
        self.sensitivity = sensitivity
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> List[re.Pattern]:
        """Load XSS patterns based on sensitivity"""
        # Basic patterns
        basic_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>",
            r"<applet[^>]*>.*?</applet>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"onfocus\s*=",
            r"onblur\s*=",
            r"onchange\s*=",
            r"onsubmit\s*=",
        ]
        
        # Medium sensitivity patterns
        medium_patterns = [
            r"<link[^>]*href[^>]*javascript:",
            r"<meta[^>]*http-equiv[^>]*refresh",
            r"<form[^>]*action[^>]*javascript:",
            r"<img[^>]*src[^>]*javascript:",
            r"<input[^>]*type[^>]*image[^>]*src[^>]*javascript:",
            r"eval\s*\(",
            r"setTimeout\s*\(",
            r"setInterval\s*\(",
            r"Function\s*\(",
            r"document\.write\s*\(",
            r"document\.writeln\s*\(",
            r"innerHTML\s*=",
            r"outerHTML\s*=",
        ]
        
        # High sensitivity patterns
        high_patterns = [
            r"<[^>]*on\w+[^>]*=",
            r"<[^>]*style[^>]*=.*expression\s*\(",
            r"<[^>]*style[^>]*=.*javascript:",
            r"<[^>]*href[^>]*=.*javascript:",
            r"<[^>]*src[^>]*=.*javascript:",
            r"<[^>]*action[^>]*=.*javascript:",
            r"data:text/html",
            r"data:text/javascript",
            r"data:application/javascript",
        ]
        
        patterns = basic_patterns
        if self.sensitivity in ["medium", "high"]:
            patterns.extend(medium_patterns)
        if self.sensitivity == "high":
            patterns.extend(high_patterns)
        
        return [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns]
    
    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """Detect XSS attempts"""
        if not text:
            return False, []
        
        # Decode common encodings
        decoded_text = self._decode_text(text)
        
        matches = []
        for pattern in self.patterns:
            if pattern.search(decoded_text):
                matches.append(pattern.pattern)
        
        return len(matches) > 0, matches
    
    def _decode_text(self, text: str) -> str:
        """Decode common XSS encoding techniques"""
        import html
        import urllib.parse
        
        # HTML entity decoding
        decoded = html.unescape(text)
        
        # URL decoding
        decoded = urllib.parse.unquote(decoded)
        decoded = urllib.parse.unquote_plus(decoded)
        
        # Double URL decoding (common evasion)
        decoded = urllib.parse.unquote(decoded)
        
        return decoded


class BotDetector:
    """Bot and automated traffic detection"""
    
    def __init__(self, sensitivity: str = "medium"):
        self.sensitivity = sensitivity
        self.known_bots = self._load_bot_patterns()
        self.suspicious_patterns = self._load_suspicious_patterns()
    
    def _load_bot_patterns(self) -> List[re.Pattern]:
        """Load known bot user agent patterns"""
        bot_patterns = [
            r"bot",
            r"crawler",
            r"spider",
            r"scraper",
            r"curl",
            r"wget",
            r"python-requests",
            r"httpie",
            r"postman",
            r"insomnia",
            r"selenium",
            r"phantomjs",
            r"headless",
            r"automation",
            r"test",
            r"monitor",
            r"check",
            r"scan",
            r"probe",
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in bot_patterns]
    
    def _load_suspicious_patterns(self) -> List[re.Pattern]:
        """Load suspicious behavior patterns"""
        patterns = [
            r"^$",  # Empty user agent
            r"^\s*$",  # Whitespace only
            r"^.{1,3}$",  # Very short user agent
            r"^.{200,}$",  # Very long user agent
        ]
        
        return [re.compile(pattern) for pattern in patterns]
    
    def detect(self, user_agent: str, headers: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
        """Detect bot traffic"""
        if not user_agent:
            return True, "missing_user_agent", {"reason": "No user agent provided"}
        
        # Check for known bot patterns
        for pattern in self.known_bots:
            if pattern.search(user_agent):
                return True, "known_bot", {"pattern": pattern.pattern, "user_agent": user_agent}
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.match(user_agent):
                return True, "suspicious_user_agent", {"pattern": pattern.pattern, "user_agent": user_agent}
        
        # Parse user agent for detailed analysis
        try:
            parsed_ua = parse_user_agent(user_agent)
            metadata = {
                "browser": parsed_ua.browser.family,
                "os": parsed_ua.os.family,
                "device": parsed_ua.device.family,
                "is_mobile": parsed_ua.is_mobile,
                "is_tablet": parsed_ua.is_tablet,
                "is_pc": parsed_ua.is_pc,
                "is_bot": parsed_ua.is_bot,
            }
            
            # Check if user-agents library detected it as a bot
            if parsed_ua.is_bot:
                return True, "parsed_bot", metadata
            
            # Additional heuristics
            if self.sensitivity == "high":
                # Very old browsers (potential spoofing)
                if parsed_ua.browser.version and len(parsed_ua.browser.version) > 0:
                    major_version = int(parsed_ua.browser.version[0])
                    if parsed_ua.browser.family == "Chrome" and major_version < 80:
                        return True, "outdated_browser", metadata
                    elif parsed_ua.browser.family == "Firefox" and major_version < 70:
                        return True, "outdated_browser", metadata
            
            return False, "legitimate", metadata
            
        except Exception as e:
            logger.warning("Failed to parse user agent", user_agent=user_agent, error=str(e))
            return True, "parse_error", {"error": str(e), "user_agent": user_agent}


class GeoBlocker:
    """Geographic IP blocking"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.reader = None
        if settings.geo_blocking_enabled:
            try:
                self.reader = geoip2.database.Reader(settings.geoip_database_path)
            except Exception as e:
                logger.error("Failed to load GeoIP database", error=str(e))
    
    def check_ip(self, ip: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Check if IP should be blocked based on geography"""
        if not self.settings.geo_blocking_enabled or not self.reader:
            return False, None, {}
        
        try:
            response = self.reader.country(ip)
            country_code = response.country.iso_code
            country_name = response.country.name
            
            metadata = {
                "country_code": country_code,
                "country_name": country_name,
                "continent": response.continent.name,
            }
            
            # Check blocked countries
            if self.settings.blocked_countries and country_code in self.settings.blocked_countries:
                return True, f"Country {country_name} ({country_code}) is blocked", metadata
            
            # Check allowed countries (if whitelist is configured)
            if self.settings.allowed_countries and country_code not in self.settings.allowed_countries:
                return True, f"Country {country_name} ({country_code}) is not in allowed list", metadata
            
            return False, None, metadata
            
        except geoip2.errors.AddressNotFoundError:
            return False, "IP not found in GeoIP database", {"ip": ip}
        except Exception as e:
            logger.error("GeoIP lookup failed", ip=ip, error=str(e))
            return False, f"GeoIP lookup error: {str(e)}", {"ip": ip, "error": str(e)}


class RateLimiter:
    """Rate limiting with Redis backend"""
    
    def __init__(self, redis_client, settings: Settings):
        self.redis = redis_client
        self.settings = settings
    
    async def check_rate_limit(self, key: str, window: int = 60, limit: int = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if rate limit is exceeded"""
        if not self.settings.rate_limit_enabled:
            return False, {}
        
        if limit is None:
            limit = self.settings.rate_limit_requests_per_minute
        
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_start = now - window
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            current_count = results[1]
            
            metadata = {
                "current_count": current_count,
                "limit": limit,
                "window": window,
                "remaining": max(0, limit - current_count)
            }
            
            if current_count >= limit:
                return True, metadata
            
            return False, metadata
            
        except Exception as e:
            logger.error("Rate limit check failed", key=key, error=str(e))
            return False, {"error": str(e)}


class WAFEngine:
    """Main WAF engine coordinating all protection modules"""
    
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self.redis = redis_client
        
        # Initialize protection modules
        self.sql_detector = SQLInjectionDetector(settings.sql_injection_sensitivity)
        self.xss_detector = XSSDetector(settings.xss_sensitivity)
        self.bot_detector = BotDetector(settings.bot_detection_sensitivity)
        self.geo_blocker = GeoBlocker(settings)
        self.rate_limiter = RateLimiter(redis_client, settings) if redis_client else None
        
        # Statistics
        self.stats = {
            "requests_processed": 0,
            "requests_blocked": 0,
            "sql_injection_attempts": 0,
            "xss_attempts": 0,
            "bot_requests": 0,
            "rate_limited": 0,
            "geo_blocked": 0,
        }
    
    async def analyze_request(self, request: WAFRequest) -> WAFResult:
        """Analyze request and return WAF result"""
        if not self.settings.waf_enabled:
            return WAFResult(allowed=True)
        
        self.stats["requests_processed"] += 1
        
        result = WAFResult(allowed=True, metadata={})
        threats = []
        
        try:
            # IP-based checks
            ip_blocked, ip_reason = self._check_ip_lists(request.ip)
            if ip_blocked:
                self.stats["requests_blocked"] += 1
                return WAFResult(
                    allowed=False,
                    rule_triggered="ip_blacklist",
                    threat_level="high",
                    block_reason=ip_reason,
                    score=100
                )
            
            # Geographic blocking
            geo_blocked, geo_reason, geo_metadata = self.geo_blocker.check_ip(request.ip)
            if geo_blocked:
                self.stats["geo_blocked"] += 1
                self.stats["requests_blocked"] += 1
                return WAFResult(
                    allowed=False,
                    rule_triggered="geo_blocking",
                    threat_level="medium",
                    block_reason=geo_reason,
                    score=80,
                    metadata=geo_metadata
                )
            result.metadata.update(geo_metadata)
            
            # Rate limiting
            if self.rate_limiter:
                rate_limited, rate_metadata = await self.rate_limiter.check_rate_limit(f"rate_limit:{request.ip}")
                if rate_limited:
                    self.stats["rate_limited"] += 1
                    self.stats["requests_blocked"] += 1
                    return WAFResult(
                        allowed=False,
                        rule_triggered="rate_limit",
                        threat_level="medium",
                        block_reason="Rate limit exceeded",
                        score=60,
                        metadata=rate_metadata
                    )
                result.metadata.update(rate_metadata)
            
            # Bot detection
            if self.settings.bot_protection_enabled and request.user_agent:
                is_bot, bot_type, bot_metadata = self.bot_detector.detect(request.user_agent, request.headers)
                if is_bot:
                    self.stats["bot_requests"] += 1
                    threats.append(("bot_detected", bot_type, 30))
                    result.metadata.update(bot_metadata)
                    
                    if self.settings.challenge_bad_bots and bot_type in ["suspicious_user_agent", "parse_error"]:
                        self.stats["requests_blocked"] += 1
                        return WAFResult(
                            allowed=False,
                            rule_triggered="bot_protection",
                            threat_level="medium",
                            block_reason=f"Bot detected: {bot_type}",
                            score=70,
                            metadata=bot_metadata
                        )
            
            # Request size limits
            size_violation = self._check_request_size(request)
            if size_violation:
                self.stats["requests_blocked"] += 1
                return WAFResult(
                    allowed=False,
                    rule_triggered="request_size_limit",
                    threat_level="medium",
                    block_reason=size_violation,
                    score=50
                )
            
            # SQL injection detection
            if self.settings.sql_injection_protection:
                sql_detected, sql_patterns = await self._check_sql_injection(request)
                if sql_detected:
                    self.stats["sql_injection_attempts"] += 1
                    threats.append(("sql_injection", sql_patterns, 90))
                    result.metadata["sql_patterns"] = sql_patterns
            
            # XSS detection
            if self.settings.xss_protection:
                xss_detected, xss_patterns = await self._check_xss(request)
                if xss_detected:
                    self.stats["xss_attempts"] += 1
                    threats.append(("xss_attempt", xss_patterns, 85))
                    result.metadata["xss_patterns"] = xss_patterns
            
            # Calculate final threat score and decision
            if threats:
                result.score = max(threat[2] for threat in threats)
                result.rule_triggered = threats[0][0]  # Most severe threat
                
                if result.score >= 90:
                    result.threat_level = "critical"
                elif result.score >= 70:
                    result.threat_level = "high"
                elif result.score >= 40:
                    result.threat_level = "medium"
                else:
                    result.threat_level = "low"
                
                # Block if in blocking mode and high threat
                if self.settings.waf_mode == "blocking" and result.score >= 70:
                    self.stats["requests_blocked"] += 1
                    result.allowed = False
                    result.block_reason = f"Multiple threats detected (score: {result.score})"
            
            return result
            
        except Exception as e:
            logger.error("WAF analysis failed", error=str(e), ip=request.ip)
            # Fail open in case of WAF engine error
            return WAFResult(allowed=True, metadata={"error": str(e)})
    
    def _check_ip_lists(self, ip: str) -> Tuple[bool, Optional[str]]:
        """Check IP against whitelist and blacklist"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            
            # Check whitelist first
            if self.settings.ip_whitelist:
                for allowed_ip in self.settings.ip_whitelist:
                    if ip_addr in ipaddress.ip_network(allowed_ip, strict=False):
                        return False, None
                # If whitelist exists and IP not in it, block
                return True, f"IP {ip} not in whitelist"
            
            # Check blacklist
            if self.settings.ip_blacklist:
                for blocked_ip in self.settings.ip_blacklist:
                    if ip_addr in ipaddress.ip_network(blocked_ip, strict=False):
                        return True, f"IP {ip} is blacklisted"
            
            return False, None
            
        except ValueError:
            logger.warning("Invalid IP address", ip=ip)
            return True, f"Invalid IP address: {ip}"
    
    def _check_request_size(self, request: WAFRequest) -> Optional[str]:
        """Check request size limits"""
        # Check URL length
        if len(request.url) > self.settings.max_url_length:
            return f"URL too long: {len(request.url)} > {self.settings.max_url_length}"
        
        # Check header sizes
        for name, value in request.headers.items():
            if len(f"{name}: {value}") > self.settings.max_header_size:
                return f"Header too large: {name}"
        
        # Check body size
        if request.body and len(request.body.encode('utf-8')) > self.settings.max_request_size:
            return f"Request body too large: {len(request.body)} > {self.settings.max_request_size}"
        
        return None
    
    async def _check_sql_injection(self, request: WAFRequest) -> Tuple[bool, List[str]]:
        """Check for SQL injection attempts"""
        all_patterns = []
        
        # Check URL
        detected, patterns = self.sql_detector.detect(request.url)
        if detected:
            all_patterns.extend(patterns)
        
        # Check headers
        for name, value in request.headers.items():
            detected, patterns = self.sql_detector.detect(value)
            if detected:
                all_patterns.extend(patterns)
        
        # Check body
        if request.body:
            detected, patterns = self.sql_detector.detect(request.body)
            if detected:
                all_patterns.extend(patterns)
        
        return len(all_patterns) > 0, all_patterns
    
    async def _check_xss(self, request: WAFRequest) -> Tuple[bool, List[str]]:
        """Check for XSS attempts"""
        all_patterns = []
        
        # Check URL
        detected, patterns = self.xss_detector.detect(request.url)
        if detected:
            all_patterns.extend(patterns)
        
        # Check headers
        for name, value in request.headers.items():
            detected, patterns = self.xss_detector.detect(value)
            if detected:
                all_patterns.extend(patterns)
        
        # Check body
        if request.body:
            detected, patterns = self.xss_detector.detect(request.body)
            if detected:
                all_patterns.extend(patterns)
        
        return len(all_patterns) > 0, all_patterns
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WAF statistics"""
        stats = self.stats.copy()
        if stats["requests_processed"] > 0:
            stats["block_rate"] = (stats["requests_blocked"] / stats["requests_processed"]) * 100
        else:
            stats["block_rate"] = 0
        
        return stats
    
    def reset_stats(self):
        """Reset WAF statistics"""
        for key in self.stats:
            self.stats[key] = 0