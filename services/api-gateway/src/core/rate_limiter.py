"""
Rate Limiting Module

Implements various rate limiting strategies using Redis for distributed rate limiting.
"""

import time
import hashlib
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json

from .config import get_settings
from .redis import get_redis_client
from .exceptions import RateLimitException
from .logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitResult:
    """Rate limit check result"""
    
    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset: int,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset = reset
        self.retry_after = retry_after


class RateLimiter:
    """Base rate limiter class"""
    
    def __init__(
        self,
        key_prefix: str = "rate_limit",
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    ):
        self.key_prefix = key_prefix
        self.strategy = strategy
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        cost: int = 1
    ) -> RateLimitResult:
        """
        Check if request is within rate limit
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            cost: Cost of this request (default: 1)
            
        Returns:
            RateLimitResult object
        """
        if self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_limit(identifier, limit, window, cost)
        elif self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_limit(identifier, limit, window, cost)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_limit(identifier, limit, window, cost)
        else:
            # Default to sliding window
            return await self._sliding_window_limit(identifier, limit, window, cost)
    
    async def _sliding_window_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        cost: int
    ) -> RateLimitResult:
        """Sliding window rate limiting"""
        redis_client = await get_redis_client()
        key = f"{self.key_prefix}:sliding:{identifier}"
        
        current_time = time.time()
        window_start = current_time - window
        
        pipe = redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_requests = results[1]
        
        # Check if limit exceeded
        if current_requests + cost > limit:
            # Calculate when the oldest request will expire
            oldest_request = await redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                reset_time = int(oldest_request[0][1] + window)
                retry_after = reset_time - int(current_time)
            else:
                reset_time = int(current_time + window)
                retry_after = window
            
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=max(0, limit - current_requests),
                reset=reset_time,
                retry_after=retry_after
            )
        
        # Add current request(s)
        pipe = redis_client.pipeline()
        for _ in range(cost):
            pipe.zadd(key, {f"{current_time}:{hash(current_time)}": current_time})
        pipe.expire(key, window)
        await pipe.execute()
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - current_requests - cost,
            reset=int(current_time + window)
        )
    
    async def _fixed_window_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        cost: int
    ) -> RateLimitResult:
        """Fixed window rate limiting"""
        redis_client = await get_redis_client()
        
        # Calculate window key
        current_time = int(time.time())
        window_id = current_time // window
        key = f"{self.key_prefix}:fixed:{identifier}:{window_id}"
        
        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incrby(key, cost)
        pipe.expire(key, window)
        results = await pipe.execute()
        
        current_count = results[0]
        
        # Calculate reset time
        reset_time = (window_id + 1) * window
        
        if current_count > limit:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset=reset_time,
                retry_after=reset_time - current_time
            )
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - current_count,
            reset=reset_time
        )
    
    async def _token_bucket_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        cost: int
    ) -> RateLimitResult:
        """Token bucket rate limiting"""
        redis_client = await get_redis_client()
        key = f"{self.key_prefix}:bucket:{identifier}"
        
        current_time = time.time()
        refill_rate = limit / window  # tokens per second
        
        # Get current bucket state
        bucket_data = await redis_client.get(key)
        
        if bucket_data:
            bucket = json.loads(bucket_data)
            tokens = bucket['tokens']
            last_update = bucket['last_update']
            
            # Calculate tokens to add
            time_passed = current_time - last_update
            tokens_to_add = time_passed * refill_rate
            tokens = min(limit, tokens + tokens_to_add)
        else:
            tokens = limit
            last_update = current_time
        
        if tokens < cost:
            # Not enough tokens
            tokens_needed = cost - tokens
            time_to_wait = tokens_needed / refill_rate
            
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=int(tokens),
                reset=int(current_time + time_to_wait),
                retry_after=int(time_to_wait)
            )
        
        # Consume tokens
        tokens -= cost
        
        # Update bucket
        bucket_data = {
            'tokens': tokens,
            'last_update': current_time
        }
        
        await redis_client.set(
            key,
            json.dumps(bucket_data),
            ex=window * 2  # Expire after 2x window
        )
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=int(tokens),
            reset=int(current_time + window)
        )


class AdvancedRateLimiter(RateLimiter):
    """Advanced rate limiter with multiple tiers and rules"""
    
    def __init__(self):
        super().__init__()
        self.rules = self._load_rate_limit_rules()
    
    def _load_rate_limit_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load rate limit rules from configuration"""
        return {
            # Authentication endpoints
            "auth:login": {
                "limit": 5,
                "window": 60,  # 5 attempts per minute
                "strategy": RateLimitStrategy.SLIDING_WINDOW,
                "burst": 2
            },
            "auth:register": {
                "limit": 3,
                "window": 300,  # 3 registrations per 5 minutes
                "strategy": RateLimitStrategy.FIXED_WINDOW
            },
            "auth:password_reset": {
                "limit": 3,
                "window": 3600,  # 3 attempts per hour
                "strategy": RateLimitStrategy.FIXED_WINDOW
            },
            
            # API endpoints
            "api:read": {
                "limit": 1000,
                "window": 60,  # 1000 reads per minute
                "strategy": RateLimitStrategy.SLIDING_WINDOW,
                "burst": 50
            },
            "api:write": {
                "limit": 100,
                "window": 60,  # 100 writes per minute
                "strategy": RateLimitStrategy.TOKEN_BUCKET
            },
            "api:upload": {
                "limit": 10,
                "window": 300,  # 10 uploads per 5 minutes
                "strategy": RateLimitStrategy.TOKEN_BUCKET
            },
            
            # Default limits
            "default": {
                "limit": settings.rate_limit_requests,
                "window": settings.rate_limit_window,
                "strategy": RateLimitStrategy.SLIDING_WINDOW,
                "burst": settings.rate_limit_burst
            }
        }
    
    async def check_endpoint_limit(
        self,
        endpoint: str,
        identifier: str,
        method: str = "GET",
        user_tier: str = "free"
    ) -> RateLimitResult:
        """
        Check rate limit for specific endpoint
        
        Args:
            endpoint: API endpoint path
            identifier: User identifier (user_id or IP)
            method: HTTP method
            user_tier: User subscription tier
            
        Returns:
            RateLimitResult
        """
        # Determine rule to apply
        rule_key = self._get_rule_key(endpoint, method)
        rule = self.rules.get(rule_key, self.rules["default"])
        
        # Apply tier multiplier
        tier_multiplier = self._get_tier_multiplier(user_tier)
        limit = int(rule["limit"] * tier_multiplier)
        
        # Set strategy
        self.strategy = rule.get("strategy", RateLimitStrategy.SLIDING_WINDOW)
        
        # Check rate limit
        return await self.check_rate_limit(
            identifier=f"{endpoint}:{identifier}",
            limit=limit,
            window=rule["window"],
            cost=1
        )
    
    def _get_rule_key(self, endpoint: str, method: str) -> str:
        """Get rule key based on endpoint and method"""
        # Special handling for auth endpoints
        if endpoint.startswith("/api/v1/auth/"):
            if "login" in endpoint:
                return "auth:login"
            elif "register" in endpoint:
                return "auth:register"
            elif "password" in endpoint:
                return "auth:password_reset"
        
        # General API endpoints
        if method in ["GET", "HEAD"]:
            return "api:read"
        elif method in ["POST", "PUT", "PATCH"]:
            if "upload" in endpoint:
                return "api:upload"
            return "api:write"
        elif method == "DELETE":
            return "api:write"
        
        return "default"
    
    def _get_tier_multiplier(self, tier: str) -> float:
        """Get rate limit multiplier based on user tier"""
        multipliers = {
            "free": 1.0,
            "basic": 2.0,
            "premium": 5.0,
            "enterprise": 10.0,
            "unlimited": 1000.0
        }
        return multipliers.get(tier, 1.0)


class IPRateLimiter(RateLimiter):
    """IP-based rate limiter"""
    
    def __init__(self):
        super().__init__(key_prefix="rate_limit:ip")
    
    def _hash_ip(self, ip: str) -> str:
        """Hash IP address for privacy"""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    async def check_ip_limit(
        self,
        ip_address: str,
        endpoint: Optional[str] = None
    ) -> RateLimitResult:
        """Check rate limit for IP address"""
        identifier = self._hash_ip(ip_address)
        
        if endpoint:
            identifier = f"{identifier}:{endpoint}"
        
        # Stricter limits for IPs without authentication
        return await self.check_rate_limit(
            identifier=identifier,
            limit=50,  # 50 requests per minute for unauthenticated
            window=60,
            cost=1
        )


class DistributedRateLimiter:
    """
    Distributed rate limiter that works across multiple instances
    Uses Redis for coordination
    """
    
    def __init__(self):
        self.advanced_limiter = AdvancedRateLimiter()
        self.ip_limiter = IPRateLimiter()
    
    async def check_request_limit(
        self,
        request_info: Dict[str, Any]
    ) -> RateLimitResult:
        """
        Check rate limit for a request
        
        Args:
            request_info: Dictionary containing:
                - endpoint: API endpoint
                - method: HTTP method
                - user_id: User ID (optional)
                - ip_address: Client IP
                - user_tier: User subscription tier
                
        Returns:
            RateLimitResult
        """
        endpoint = request_info.get("endpoint", "/")
        method = request_info.get("method", "GET")
        user_id = request_info.get("user_id")
        ip_address = request_info.get("ip_address", "unknown")
        user_tier = request_info.get("user_tier", "free")
        
        # Check user-based limit if authenticated
        if user_id:
            result = await self.advanced_limiter.check_endpoint_limit(
                endpoint=endpoint,
                identifier=user_id,
                method=method,
                user_tier=user_tier
            )
            
            if not result.allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint}",
                    extra={
                        "user_id": user_id,
                        "endpoint": endpoint,
                        "limit": result.limit,
                        "window": result.reset - int(time.time())
                    }
                )
                return result
        
        # Always check IP-based limit as secondary protection
        ip_result = await self.ip_limiter.check_ip_limit(
            ip_address=ip_address,
            endpoint=endpoint
        )
        
        if not ip_result.allowed:
            logger.warning(
                f"Rate limit exceeded for IP {ip_address} on {endpoint}",
                extra={
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                    "limit": ip_result.limit
                }
            )
            return ip_result
        
        # Return the more restrictive result
        if user_id:
            return result
        return ip_result
    
    async def get_rate_limit_info(
        self,
        identifier: str,
        endpoint: str = "default"
    ) -> Dict[str, Any]:
        """Get current rate limit information for identifier"""
        # This would check current usage and limits
        redis_client = await get_redis_client()
        
        # Get all keys for this identifier
        pattern = f"rate_limit:*:{identifier}*"
        keys = await redis_client.keys(pattern)
        
        info = {
            "identifier": identifier,
            "endpoint": endpoint,
            "limits": {},
            "current_usage": {}
        }
        
        # Gather information about current usage
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if "sliding" in key_str:
                count = await redis_client.zcard(key_str)
                info["current_usage"][key_str] = count
            elif "fixed" in key_str:
                count = await redis_client.get(key_str)
                info["current_usage"][key_str] = int(count) if count else 0
        
        return info


# Global rate limiter instance
rate_limiter = DistributedRateLimiter()