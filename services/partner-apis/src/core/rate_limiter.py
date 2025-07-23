"""Rate limiting middleware and utilities"""

import time
import json
from typing import Dict, Any, Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
import hashlib
import logging

from .config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API requests"""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get Redis client for rate limiting"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.redis_url)
        return self.redis_client
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Skip if rate limiting is disabled
        if not settings.enable_rate_limiting:
            return await call_next(request)
        
        # Extract API key from request
        api_key = await self._extract_api_key(request)
        if not api_key:
            # No API key, apply default rate limiting by IP
            identifier = self._get_client_ip(request)
            rate_limit = settings.default_rate_limit
            burst_limit = settings.default_burst_limit
        else:
            # Use API key for rate limiting
            identifier = f"api_key:{api_key}"
            # In production, we'd fetch rate limits from database
            # For now, use default settings
            rate_limit = settings.default_rate_limit
            burst_limit = settings.default_burst_limit
        
        # Check rate limit
        allowed, reset_time, remaining = await self._check_rate_limit(
            identifier, rate_limit, burst_limit
        )
        
        if not allowed:
            # Rate limit exceeded
            response = Response(
                content=json.dumps({
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded",
                        "details": {
                            "reset_time": reset_time,
                            "retry_after": max(0, reset_time - int(time.time()))
                        }
                    }
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(self._parse_rate_limit(rate_limit)[0]),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(max(0, reset_time - int(time.time())))
                }
            )
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        limit, _ = self._parse_rate_limit(rate_limit)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    async def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers or query params"""
        
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header
        
        # Check query parameter
        api_key_param = request.query_params.get("api_key")
        if api_key_param:
            return api_key_param
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(
        self, 
        identifier: str, 
        rate_limit: str, 
        burst_limit: int
    ) -> Tuple[bool, int, int]:
        """Check if request is within rate limit"""
        
        try:
            redis_client = await self.get_redis_client()
            
            limit, window_seconds = self._parse_rate_limit(rate_limit)
            current_time = int(time.time())
            window_start = current_time - (current_time % window_seconds)
            
            # Redis key for this rate limit window
            key = f"rate_limit:{identifier}:{window_start}"
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            
            current_count = results[0]
            reset_time = window_start + window_seconds
            remaining = max(0, limit - current_count)
            
            # Check if within limit
            allowed = current_count <= limit
            
            return allowed, reset_time, remaining
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # If Redis is down, allow the request
            return True, int(time.time()) + 3600, 1000
    
    def _parse_rate_limit(self, rate_limit: str) -> Tuple[int, int]:
        """Parse rate limit string like '1000/hour' into (limit, seconds)"""
        
        try:
            limit_str, period = rate_limit.split("/")
            limit = int(limit_str)
            
            period_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(period, 3600)
            
            return limit, period_seconds
            
        except (ValueError, KeyError):
            # Default to 1000/hour if parsing fails
            return 1000, 3600


class RateLimitService:
    """Service for managing rate limits"""
    
    def __init__(self):
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get Redis client"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.redis_url)
        return self.redis_client
    
    async def check_api_key_limit(
        self, 
        api_key_id: str, 
        rate_limit: str,
        burst_limit: int
    ) -> Dict[str, Any]:
        """Check rate limit for specific API key"""
        
        try:
            redis_client = await self.get_redis_client()
            
            limit, window_seconds = self._parse_rate_limit(rate_limit)
            current_time = int(time.time())
            window_start = current_time - (current_time % window_seconds)
            
            key = f"api_key_limit:{api_key_id}:{window_start}"
            
            # Get current count
            current_count = await redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            reset_time = window_start + window_seconds
            remaining = max(0, limit - current_count)
            
            return {
                "allowed": current_count < limit,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return {
                "allowed": True,
                "limit": 1000,
                "remaining": 1000,
                "reset_time": int(time.time()) + 3600,
                "current_count": 0
            }
    
    async def increment_api_key_usage(self, api_key_id: str, rate_limit: str):
        """Increment usage counter for API key"""
        
        try:
            redis_client = await self.get_redis_client()
            
            _, window_seconds = self._parse_rate_limit(rate_limit)
            current_time = int(time.time())
            window_start = current_time - (current_time % window_seconds)
            
            key = f"api_key_limit:{api_key_id}:{window_start}"
            
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Rate limit increment error: {e}")
    
    async def reset_api_key_limit(self, api_key_id: str):
        """Reset rate limit for API key (admin function)"""
        
        try:
            redis_client = await self.get_redis_client()
            
            # Find and delete all rate limit keys for this API key
            pattern = f"api_key_limit:{api_key_id}:*"
            keys = await redis_client.keys(pattern)
            
            if keys:
                await redis_client.delete(*keys)
                
        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")
    
    def _parse_rate_limit(self, rate_limit: str) -> Tuple[int, int]:
        """Parse rate limit string"""
        
        try:
            limit_str, period = rate_limit.split("/")
            limit = int(limit_str)
            
            period_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(period, 3600)
            
            return limit, period_seconds
            
        except (ValueError, KeyError):
            return 1000, 3600


# Global rate limit service instance
rate_limit_service = RateLimitService()