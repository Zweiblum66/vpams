"""
Rate Limit Management API

Endpoints for viewing and managing rate limits.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from core.config import get_settings
from core.rate_limiter import rate_limiter
from core.exceptions import AuthorizationException
from api.dependencies import get_current_user, require_permissions

settings = get_settings()
router = APIRouter(prefix="/api/v1/rate-limits", tags=["rate-limits"])


class RateLimitInfo(BaseModel):
    """Rate limit information response"""
    endpoint: str
    limit: int
    window: int
    remaining: int
    reset: int
    strategy: str


class RateLimitStatus(BaseModel):
    """Current rate limit status"""
    identifier: str
    limits: Dict[str, RateLimitInfo]
    current_usage: Dict[str, int]


class RateLimitOverride(BaseModel):
    """Rate limit override request"""
    identifier: str = Field(..., description="User ID or IP to override")
    endpoint: str = Field(default="*", description="Endpoint pattern (* for all)")
    limit: int = Field(..., ge=0, description="New limit (0 to block)")
    window: int = Field(default=60, ge=1, description="Window in seconds")
    duration: int = Field(default=3600, ge=60, description="Override duration in seconds")


@router.get("/me", response_model=RateLimitStatus)
async def get_my_rate_limits(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current user's rate limit status
    
    Returns current rate limit information for the authenticated user.
    """
    # Get rate limit info for current user
    info = await rate_limiter.get_rate_limit_info(
        identifier=current_user["user_id"],
        endpoint="default"
    )
    
    # Get limits for different endpoints
    limits = {}
    endpoints = ["/api/v1/assets", "/api/v1/auth/login", "/api/v1/upload"]
    
    for endpoint in endpoints:
        request_info = {
            "endpoint": endpoint,
            "method": "GET",
            "user_id": current_user["user_id"],
            "user_tier": current_user.get("tier", "free")
        }
        
        # Check without consuming
        result = await rate_limiter.advanced_limiter.check_endpoint_limit(
            endpoint=endpoint,
            identifier=current_user["user_id"],
            user_tier=current_user.get("tier", "free")
        )
        
        limits[endpoint] = RateLimitInfo(
            endpoint=endpoint,
            limit=result.limit,
            window=60,  # Default window
            remaining=result.remaining,
            reset=result.reset,
            strategy="sliding_window"
        )
    
    return RateLimitStatus(
        identifier=current_user["user_id"],
        limits=limits,
        current_usage=info.get("current_usage", {})
    )


@router.get("/user/{user_id}", response_model=RateLimitStatus)
async def get_user_rate_limits(
    user_id: str,
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.read"))
):
    """
    Get rate limit status for specific user
    
    Requires admin permissions.
    """
    # Get rate limit info for specified user
    info = await rate_limiter.get_rate_limit_info(
        identifier=user_id,
        endpoint="default"
    )
    
    # Get limits for different endpoints
    limits = {}
    endpoints = ["/api/v1/assets", "/api/v1/auth/login", "/api/v1/upload"]
    
    for endpoint in endpoints:
        # Check without consuming
        result = await rate_limiter.advanced_limiter.check_endpoint_limit(
            endpoint=endpoint,
            identifier=user_id,
            user_tier="free"  # Default tier, should get from user service
        )
        
        limits[endpoint] = RateLimitInfo(
            endpoint=endpoint,
            limit=result.limit,
            window=60,
            remaining=result.remaining,
            reset=result.reset,
            strategy="sliding_window"
        )
    
    return RateLimitStatus(
        identifier=user_id,
        limits=limits,
        current_usage=info.get("current_usage", {})
    )


@router.get("/ip/{ip_address}", response_model=RateLimitStatus)
async def get_ip_rate_limits(
    ip_address: str,
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.read"))
):
    """
    Get rate limit status for specific IP address
    
    Requires admin permissions.
    """
    # Hash IP for privacy
    identifier = rate_limiter.ip_limiter._hash_ip(ip_address)
    
    # Get rate limit info
    info = await rate_limiter.get_rate_limit_info(
        identifier=identifier,
        endpoint="default"
    )
    
    # Get IP-specific limit
    result = await rate_limiter.ip_limiter.check_ip_limit(
        ip_address=ip_address
    )
    
    limits = {
        "global": RateLimitInfo(
            endpoint="*",
            limit=result.limit,
            window=60,
            remaining=result.remaining,
            reset=result.reset,
            strategy="sliding_window"
        )
    }
    
    return RateLimitStatus(
        identifier=ip_address,
        limits=limits,
        current_usage=info.get("current_usage", {})
    )


@router.post("/override")
async def override_rate_limit(
    override: RateLimitOverride,
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.write"))
):
    """
    Override rate limit for specific user or IP
    
    Temporarily changes rate limits for a user or IP address.
    Requires admin permissions.
    """
    # Store override in Redis
    from core.redis import get_redis_client
    redis_client = await get_redis_client()
    
    override_key = f"rate_limit:override:{override.identifier}:{override.endpoint}"
    override_data = {
        "limit": override.limit,
        "window": override.window,
        "created_by": current_user["user_id"],
        "created_at": int(time.time())
    }
    
    await redis_client.set(
        override_key,
        json.dumps(override_data),
        ex=override.duration
    )
    
    return {
        "message": "Rate limit override created",
        "identifier": override.identifier,
        "endpoint": override.endpoint,
        "limit": override.limit,
        "window": override.window,
        "expires_in": override.duration
    }


@router.delete("/override/{identifier}")
async def remove_rate_limit_override(
    identifier: str,
    endpoint: str = Query(default="*", description="Endpoint pattern"),
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.write"))
):
    """
    Remove rate limit override
    
    Removes a temporary rate limit override.
    Requires admin permissions.
    """
    from core.redis import get_redis_client
    redis_client = await get_redis_client()
    
    override_key = f"rate_limit:override:{identifier}:{endpoint}"
    deleted = await redis_client.delete(override_key)
    
    if deleted:
        return {
            "message": "Rate limit override removed",
            "identifier": identifier,
            "endpoint": endpoint
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate limit override not found"
        )


@router.post("/reset/{identifier}")
async def reset_rate_limit(
    identifier: str,
    endpoint: str = Query(default="*", description="Endpoint pattern"),
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.write"))
):
    """
    Reset rate limit counters
    
    Clears rate limit counters for a user or IP.
    Requires admin permissions.
    """
    from core.redis import get_redis_client
    redis_client = await get_redis_client()
    
    # Find and delete rate limit keys
    if endpoint == "*":
        pattern = f"rate_limit:*:{identifier}*"
    else:
        pattern = f"rate_limit:*:{identifier}:{endpoint}*"
    
    keys = await redis_client.keys(pattern)
    deleted_count = 0
    
    if keys:
        deleted_count = await redis_client.delete(*keys)
    
    return {
        "message": "Rate limit counters reset",
        "identifier": identifier,
        "endpoint": endpoint,
        "keys_deleted": deleted_count
    }


@router.get("/config")
async def get_rate_limit_config(
    current_user: Dict = Depends(require_permissions("admin", "rate_limit.read"))
):
    """
    Get rate limit configuration
    
    Returns the current rate limit rules and configuration.
    Requires admin permissions.
    """
    # Get configuration from rate limiter
    rules = rate_limiter.advanced_limiter.rules
    
    return {
        "default_limit": settings.rate_limit_requests,
        "default_window": settings.rate_limit_window,
        "burst_limit": settings.rate_limit_burst,
        "rules": rules,
        "tier_multipliers": {
            "free": 1.0,
            "basic": 2.0,
            "premium": 5.0,
            "enterprise": 10.0,
            "unlimited": 1000.0
        }
    }


# Import required modules
import time
import json