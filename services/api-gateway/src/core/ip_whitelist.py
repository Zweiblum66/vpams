"""
IP Whitelisting Middleware

Provides IP address-based access control for the API Gateway.
Supports individual IPs, CIDR ranges, and wildcard patterns.
"""

import ipaddress
import re
from typing import List, Optional, Union, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import BaseModel, Field, validator
import logging
from datetime import datetime, timedelta

from core.config import get_settings
from core.exceptions import APIException
from core.redis import get_redis_client

logger = logging.getLogger(__name__)
settings = get_settings()


class IPAccessDeniedException(APIException):
    """IP access denied exception"""
    
    def __init__(self, message: str = "Access denied from this IP address", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="IP_ACCESS_DENIED",
            details=details
        )


class IPWhitelistConfig(BaseModel):
    """Configuration for IP whitelisting"""
    
    # Enable/disable IP whitelisting
    enabled: bool = Field(default=False, description="Enable IP whitelisting")
    
    # Whitelist mode: 'whitelist' (allow only listed IPs) or 'blacklist' (block listed IPs)
    mode: str = Field(default="whitelist", description="Whitelist mode: 'whitelist' or 'blacklist'")
    
    # List of allowed IP addresses/ranges
    allowed_ips: List[str] = Field(
        default_factory=list,
        description="List of allowed IP addresses, CIDR ranges, or patterns"
    )
    
    # List of blocked IP addresses/ranges (for blacklist mode)
    blocked_ips: List[str] = Field(
        default_factory=list,
        description="List of blocked IP addresses, CIDR ranges, or patterns"
    )
    
    # Paths to exclude from IP checking
    excluded_paths: List[str] = Field(
        default_factory=lambda: ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        description="Paths to exclude from IP whitelisting"
    )
    
    # Administrative IP addresses (always allowed)
    admin_ips: List[str] = Field(
        default_factory=list,
        description="Administrative IP addresses (always allowed)"
    )
    
    # Trust proxy headers
    trust_proxy_headers: bool = Field(
        default=True,
        description="Trust X-Forwarded-For and X-Real-IP headers"
    )
    
    # Maximum proxy chain depth
    max_proxy_depth: int = Field(
        default=3,
        description="Maximum number of proxies in X-Forwarded-For chain"
    )
    
    # Environment-specific settings
    environment: str = Field(
        default="production",
        description="Environment (development, staging, production)"
    )
    
    # Enable IP-based rate limiting
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable IP-based rate limiting"
    )
    
    # Rate limiting configuration
    rate_limit_requests: int = Field(
        default=1000,
        description="Number of requests per window per IP"
    )
    
    rate_limit_window: int = Field(
        default=3600,
        description="Rate limit window in seconds"
    )
    
    # Logging configuration
    log_blocked_requests: bool = Field(
        default=True,
        description="Log blocked requests"
    )
    
    log_allowed_requests: bool = Field(
        default=False,
        description="Log allowed requests"
    )
    
    # Redis key prefix for IP data
    redis_key_prefix: str = Field(
        default="ip_whitelist",
        description="Redis key prefix for IP whitelist data"
    )
    
    @validator("mode")
    def validate_mode(cls, v):
        """Validate whitelist mode"""
        if v not in ["whitelist", "blacklist"]:
            raise ValueError("Mode must be 'whitelist' or 'blacklist'")
        return v
    
    @validator("allowed_ips", "blocked_ips", "admin_ips")
    def validate_ip_list(cls, v):
        """Validate IP address list"""
        if not v:
            return v
        
        validated_ips = []
        for ip_entry in v:
            try:
                # Try to parse as IP address or network
                if "/" in ip_entry:
                    # CIDR notation
                    ipaddress.ip_network(ip_entry, strict=False)
                elif "*" in ip_entry:
                    # Wildcard pattern - validate format
                    if not re.match(r'^(\d{1,3}|\*)\.(\d{1,3}|\*)\.(\d{1,3}|\*)\.(\d{1,3}|\*)$', ip_entry):
                        raise ValueError(f"Invalid wildcard pattern: {ip_entry}")
                else:
                    # Single IP address
                    ipaddress.ip_address(ip_entry)
                validated_ips.append(ip_entry)
            except ValueError as e:
                logger.warning(f"Invalid IP entry '{ip_entry}': {e}")
                continue
        
        return validated_ips


class IPMatcher:
    """Utility class for matching IP addresses"""
    
    def __init__(self, ip_list: List[str]):
        self.ip_list = ip_list
        self.networks = []
        self.addresses = []
        self.patterns = []
        
        # Pre-process IP list for faster matching
        for ip_entry in ip_list:
            try:
                if "/" in ip_entry:
                    # CIDR notation
                    self.networks.append(ipaddress.ip_network(ip_entry, strict=False))
                elif "*" in ip_entry:
                    # Wildcard pattern
                    self.patterns.append(ip_entry)
                else:
                    # Single IP address
                    self.addresses.append(ipaddress.ip_address(ip_entry))
            except ValueError as e:
                logger.warning(f"Failed to parse IP entry '{ip_entry}': {e}")
    
    def matches(self, ip: str) -> bool:
        """Check if IP matches any entry in the list"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            
            # Check direct IP addresses
            if ip_addr in self.addresses:
                return True
            
            # Check networks
            for network in self.networks:
                if ip_addr in network:
                    return True
            
            # Check wildcard patterns
            for pattern in self.patterns:
                if self._matches_pattern(ip, pattern):
                    return True
            
            return False
            
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return False
    
    def _matches_pattern(self, ip: str, pattern: str) -> bool:
        """Check if IP matches wildcard pattern"""
        ip_parts = ip.split('.')
        pattern_parts = pattern.split('.')
        
        if len(ip_parts) != 4 or len(pattern_parts) != 4:
            return False
        
        for ip_part, pattern_part in zip(ip_parts, pattern_parts):
            if pattern_part != '*' and ip_part != pattern_part:
                return False
        
        return True


class IPWhitelistManager:
    """Manager for IP whitelist operations"""
    
    def __init__(self, config: IPWhitelistConfig):
        self.config = config
        self.allowed_matcher = IPMatcher(config.allowed_ips)
        self.blocked_matcher = IPMatcher(config.blocked_ips)
        self.admin_matcher = IPMatcher(config.admin_ips)
        self.blocked_requests = []
        self.max_blocked_requests = 1000
    
    def extract_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check if we should trust proxy headers
        if self.config.trust_proxy_headers:
            # Check X-Forwarded-For header
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Take the first IP (original client)
                ips = [ip.strip() for ip in forwarded_for.split(",")]
                if ips and len(ips) <= self.config.max_proxy_depth:
                    return ips[0]
            
            # Check X-Real-IP header
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        if not self.config.enabled:
            return True
        
        # Admin IPs are always allowed
        if self.admin_matcher.matches(ip):
            return True
        
        if self.config.mode == "whitelist":
            # In whitelist mode, IP must be in allowed list
            return self.allowed_matcher.matches(ip)
        else:
            # In blacklist mode, IP must NOT be in blocked list
            return not self.blocked_matcher.matches(ip)
    
    def should_check_path(self, path: str) -> bool:
        """Check if path should be subject to IP whitelisting"""
        for excluded_path in self.config.excluded_paths:
            if path.startswith(excluded_path):
                return False
        return True
    
    async def record_blocked_request(self, request: Request, ip: str, reason: str):
        """Record a blocked request"""
        blocked_request = {
            "timestamp": datetime.utcnow().isoformat(),
            "ip": ip,
            "path": str(request.url.path),
            "method": request.method,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "referer": request.headers.get("referer", "unknown"),
            "reason": reason
        }
        
        # Store in memory
        self.blocked_requests.append(blocked_request)
        if len(self.blocked_requests) > self.max_blocked_requests:
            self.blocked_requests = self.blocked_requests[-self.max_blocked_requests:]
        
        # Store in Redis for persistence
        try:
            redis_client = await get_redis_client()
            key = f"{self.config.redis_key_prefix}:blocked_requests"
            await redis_client.lpush(key, str(blocked_request))
            await redis_client.ltrim(key, 0, self.max_blocked_requests - 1)
            await redis_client.expire(key, 86400)  # 24 hours
        except Exception as e:
            logger.warning(f"Failed to store blocked request in Redis: {e}")
        
        # Log blocked request
        if self.config.log_blocked_requests:
            logger.warning(
                f"Blocked request from IP {ip}",
                extra={
                    "ip": ip,
                    "path": str(request.url.path),
                    "method": request.method,
                    "user_agent": request.headers.get("user-agent"),
                    "reason": reason
                }
            )
    
    async def record_allowed_request(self, request: Request, ip: str):
        """Record an allowed request"""
        if not self.config.log_allowed_requests:
            return
        
        logger.info(
            f"Allowed request from IP {ip}",
            extra={
                "ip": ip,
                "path": str(request.url.path),
                "method": request.method,
                "user_agent": request.headers.get("user-agent")
            }
        )
    
    async def check_rate_limit(self, ip: str) -> bool:
        """Check IP-based rate limit"""
        if not self.config.enable_rate_limiting:
            return True
        
        try:
            redis_client = await get_redis_client()
            key = f"{self.config.redis_key_prefix}:rate_limit:{ip}"
            
            # Get current count
            current_count = await redis_client.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            
            # Check if limit exceeded
            if current_count >= self.config.rate_limit_requests:
                return False
            
            # Increment counter
            await redis_client.incr(key)
            await redis_client.expire(key, self.config.rate_limit_window)
            
            return True
            
        except Exception as e:
            logger.warning(f"Rate limit check failed for IP {ip}: {e}")
            return True  # Allow request if Redis is unavailable
    
    def get_blocked_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent blocked requests"""
        return self.blocked_requests[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get IP whitelist statistics"""
        total_blocked = len(self.blocked_requests)
        
        # Count by IP
        ip_counts = {}
        for request in self.blocked_requests:
            ip = request["ip"]
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        # Count by reason
        reason_counts = {}
        for request in self.blocked_requests:
            reason = request["reason"]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "enabled": self.config.enabled,
            "mode": self.config.mode,
            "total_blocked_requests": total_blocked,
            "unique_blocked_ips": len(ip_counts),
            "top_blocked_ips": sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "block_reasons": reason_counts,
            "allowed_ip_count": len(self.config.allowed_ips),
            "blocked_ip_count": len(self.config.blocked_ips),
            "admin_ip_count": len(self.config.admin_ips)
        }


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP Whitelisting Middleware
    
    Provides IP address-based access control for the API Gateway.
    Supports both whitelist and blacklist modes, CIDR ranges, and wildcard patterns.
    """
    
    def __init__(self, app: ASGIApp, config: Optional[IPWhitelistConfig] = None):
        super().__init__(app)
        self.config = config or IPWhitelistConfig()
        self.manager = IPWhitelistManager(self.config)
        
        # Environment-specific adjustments
        self._adjust_for_environment()
        
        logger.info(
            f"IP Whitelist middleware initialized",
            extra={
                "enabled": self.config.enabled,
                "mode": self.config.mode,
                "allowed_ips": len(self.config.allowed_ips),
                "blocked_ips": len(self.config.blocked_ips),
                "admin_ips": len(self.config.admin_ips),
                "environment": self.config.environment
            }
        )
    
    def _adjust_for_environment(self):
        """Adjust configuration based on environment"""
        if self.config.environment == "development":
            # Be more permissive in development
            if not self.config.allowed_ips:
                self.config.allowed_ips = ["127.0.0.1", "::1", "10.0.0.0/8", "192.168.0.0/16"]
            self.config.log_allowed_requests = True
            self.config.log_blocked_requests = True
        
        elif self.config.environment == "staging":
            # Moderate restrictions in staging
            self.config.log_allowed_requests = False
            self.config.log_blocked_requests = True
        
        elif self.config.environment == "production":
            # Strict restrictions in production
            self.config.log_allowed_requests = False
            self.config.log_blocked_requests = True
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and check IP whitelist"""
        # Skip IP checking for excluded paths
        if not self.manager.should_check_path(request.url.path):
            return await call_next(request)
        
        # Extract client IP
        client_ip = self.manager.extract_client_ip(request)
        
        # Check if IP is allowed
        if not self.manager.is_ip_allowed(client_ip):
            # Record blocked request
            await self.manager.record_blocked_request(
                request, client_ip, f"IP not in {self.config.mode}"
            )
            
            # Raise IP access denied exception
            raise IPAccessDeniedException(
                f"Access denied from IP address {client_ip}",
                details={
                    "ip": client_ip,
                    "mode": self.config.mode,
                    "path": str(request.url.path)
                }
            )
        
        # Check rate limit
        if not await self.manager.check_rate_limit(client_ip):
            # Record blocked request
            await self.manager.record_blocked_request(
                request, client_ip, "Rate limit exceeded"
            )
            
            # Raise IP access denied exception
            raise IPAccessDeniedException(
                f"Rate limit exceeded for IP address {client_ip}",
                details={
                    "ip": client_ip,
                    "rate_limit": self.config.rate_limit_requests,
                    "window": self.config.rate_limit_window
                }
            )
        
        # Record allowed request
        await self.manager.record_allowed_request(request, client_ip)
        
        # Add IP to request state
        request.state.client_ip = client_ip
        
        # Process request
        response = await call_next(request)
        
        # Add IP information to response headers (for debugging)
        if self.config.environment == "development":
            response.headers["X-Client-IP"] = client_ip
        
        return response


def get_ip_whitelist_config() -> IPWhitelistConfig:
    """Get IP whitelist configuration"""
    return IPWhitelistConfig(
        environment=settings.environment,
        enabled=getattr(settings, 'ip_whitelist_enabled', False),
        mode=getattr(settings, 'ip_whitelist_mode', 'whitelist'),
        allowed_ips=getattr(settings, 'ip_whitelist_allowed_ips', []),
        blocked_ips=getattr(settings, 'ip_whitelist_blocked_ips', []),
        admin_ips=getattr(settings, 'ip_whitelist_admin_ips', []),
        trust_proxy_headers=getattr(settings, 'ip_whitelist_trust_proxy_headers', True),
        enable_rate_limiting=getattr(settings, 'ip_whitelist_enable_rate_limiting', True),
        rate_limit_requests=getattr(settings, 'ip_whitelist_rate_limit_requests', 1000),
        rate_limit_window=getattr(settings, 'ip_whitelist_rate_limit_window', 3600)
    )


# Global IP whitelist manager
ip_whitelist_manager = None


def get_ip_whitelist_manager() -> IPWhitelistManager:
    """Get IP whitelist manager instance"""
    global ip_whitelist_manager
    if ip_whitelist_manager is None:
        config = get_ip_whitelist_config()
        ip_whitelist_manager = IPWhitelistManager(config)
    return ip_whitelist_manager


def create_ip_whitelist_middleware(app: ASGIApp) -> IPWhitelistMiddleware:
    """Create IP whitelist middleware with default configuration"""
    config = get_ip_whitelist_config()
    return IPWhitelistMiddleware(app, config)