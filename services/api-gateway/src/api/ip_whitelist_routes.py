"""
IP Whitelist Management Routes

Provides endpoints for managing IP whitelisting configuration,
viewing blocked requests, and monitoring IP access patterns.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field
import logging

from core.ip_whitelist import (
    get_ip_whitelist_manager,
    IPWhitelistConfig,
    IPWhitelistManager
)
from core.auth import get_current_active_user
from models.user import User
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ip-whitelist", tags=["ip-whitelist"])


class IPWhitelistStatusResponse(BaseModel):
    """IP whitelist status response"""
    enabled: bool = Field(..., description="Whether IP whitelisting is enabled")
    mode: str = Field(..., description="Whitelist mode (whitelist/blacklist)")
    allowed_ip_count: int = Field(..., description="Number of allowed IPs")
    blocked_ip_count: int = Field(..., description="Number of blocked IPs")
    admin_ip_count: int = Field(..., description="Number of admin IPs")
    total_blocked_requests: int = Field(..., description="Total blocked requests")
    unique_blocked_ips: int = Field(..., description="Number of unique blocked IPs")
    rate_limiting_enabled: bool = Field(..., description="Whether rate limiting is enabled")
    trust_proxy_headers: bool = Field(..., description="Whether proxy headers are trusted")


class IPWhitelistConfigResponse(BaseModel):
    """IP whitelist configuration response"""
    enabled: bool = Field(..., description="Whether IP whitelisting is enabled")
    mode: str = Field(..., description="Whitelist mode")
    allowed_ips: List[str] = Field(..., description="List of allowed IPs")
    blocked_ips: List[str] = Field(..., description="List of blocked IPs")
    admin_ips: List[str] = Field(..., description="List of admin IPs")
    excluded_paths: List[str] = Field(..., description="Paths excluded from checking")
    trust_proxy_headers: bool = Field(..., description="Trust proxy headers")
    max_proxy_depth: int = Field(..., description="Maximum proxy depth")
    enable_rate_limiting: bool = Field(..., description="Enable rate limiting")
    rate_limit_requests: int = Field(..., description="Rate limit requests per window")
    rate_limit_window: int = Field(..., description="Rate limit window in seconds")
    log_blocked_requests: bool = Field(..., description="Log blocked requests")
    log_allowed_requests: bool = Field(..., description="Log allowed requests")


class BlockedRequestResponse(BaseModel):
    """Blocked request response"""
    timestamp: str = Field(..., description="Request timestamp")
    ip: str = Field(..., description="Client IP address")
    path: str = Field(..., description="Request path")
    method: str = Field(..., description="HTTP method")
    user_agent: str = Field(..., description="User agent")
    referer: str = Field(..., description="Referer header")
    reason: str = Field(..., description="Block reason")


class IPWhitelistStatsResponse(BaseModel):
    """IP whitelist statistics response"""
    enabled: bool = Field(..., description="Whether IP whitelisting is enabled")
    mode: str = Field(..., description="Whitelist mode")
    total_blocked_requests: int = Field(..., description="Total blocked requests")
    unique_blocked_ips: int = Field(..., description="Number of unique blocked IPs")
    top_blocked_ips: List[tuple] = Field(..., description="Top blocked IPs with counts")
    block_reasons: Dict[str, int] = Field(..., description="Block reasons with counts")
    allowed_ip_count: int = Field(..., description="Number of allowed IPs")
    blocked_ip_count: int = Field(..., description="Number of blocked IPs")
    admin_ip_count: int = Field(..., description="Number of admin IPs")


class IPWhitelistConfigUpdate(BaseModel):
    """IP whitelist configuration update"""
    enabled: Optional[bool] = Field(None, description="Enable/disable IP whitelisting")
    mode: Optional[str] = Field(None, description="Whitelist mode")
    allowed_ips: Optional[List[str]] = Field(None, description="List of allowed IPs")
    blocked_ips: Optional[List[str]] = Field(None, description="List of blocked IPs")
    admin_ips: Optional[List[str]] = Field(None, description="List of admin IPs")
    trust_proxy_headers: Optional[bool] = Field(None, description="Trust proxy headers")
    enable_rate_limiting: Optional[bool] = Field(None, description="Enable rate limiting")
    rate_limit_requests: Optional[int] = Field(None, description="Rate limit requests")
    rate_limit_window: Optional[int] = Field(None, description="Rate limit window")
    log_blocked_requests: Optional[bool] = Field(None, description="Log blocked requests")
    log_allowed_requests: Optional[bool] = Field(None, description="Log allowed requests")


class IPAddRequest(BaseModel):
    """Request to add IP to whitelist/blacklist"""
    ip: str = Field(..., description="IP address or CIDR range")
    list_type: str = Field(..., description="List type: allowed, blocked, or admin")
    description: Optional[str] = Field(None, description="Description of the IP")


class IPRemoveRequest(BaseModel):
    """Request to remove IP from whitelist/blacklist"""
    ip: str = Field(..., description="IP address or CIDR range")
    list_type: str = Field(..., description="List type: allowed, blocked, or admin")


@router.get("/status", response_model=IPWhitelistStatusResponse)
async def get_ip_whitelist_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get IP whitelist status
    
    Returns the current status of IP whitelisting and basic statistics.
    Requires authentication.
    """
    try:
        manager = get_ip_whitelist_manager()
        stats = manager.get_stats()
        
        return IPWhitelistStatusResponse(
            enabled=stats["enabled"],
            mode=stats["mode"],
            allowed_ip_count=stats["allowed_ip_count"],
            blocked_ip_count=stats["blocked_ip_count"],
            admin_ip_count=stats["admin_ip_count"],
            total_blocked_requests=stats["total_blocked_requests"],
            unique_blocked_ips=stats["unique_blocked_ips"],
            rate_limiting_enabled=manager.config.enable_rate_limiting,
            trust_proxy_headers=manager.config.trust_proxy_headers
        )
        
    except Exception as e:
        logger.error(f"Failed to get IP whitelist status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IP whitelist status"
        )


@router.get("/config", response_model=IPWhitelistConfigResponse)
async def get_ip_whitelist_config(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get IP whitelist configuration
    
    Returns the current IP whitelist configuration.
    Requires authentication.
    """
    try:
        manager = get_ip_whitelist_manager()
        config = manager.config
        
        return IPWhitelistConfigResponse(
            enabled=config.enabled,
            mode=config.mode,
            allowed_ips=config.allowed_ips,
            blocked_ips=config.blocked_ips,
            admin_ips=config.admin_ips,
            excluded_paths=config.excluded_paths,
            trust_proxy_headers=config.trust_proxy_headers,
            max_proxy_depth=config.max_proxy_depth,
            enable_rate_limiting=config.enable_rate_limiting,
            rate_limit_requests=config.rate_limit_requests,
            rate_limit_window=config.rate_limit_window,
            log_blocked_requests=config.log_blocked_requests,
            log_allowed_requests=config.log_allowed_requests
        )
        
    except Exception as e:
        logger.error(f"Failed to get IP whitelist config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IP whitelist config"
        )


@router.get("/blocked-requests", response_model=List[BlockedRequestResponse])
async def get_blocked_requests(
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent blocked requests
    
    Returns a list of recent blocked requests for analysis.
    Requires authentication.
    """
    try:
        manager = get_ip_whitelist_manager()
        blocked_requests = manager.get_blocked_requests(limit)
        
        return [
            BlockedRequestResponse(
                timestamp=req["timestamp"],
                ip=req["ip"],
                path=req["path"],
                method=req["method"],
                user_agent=req["user_agent"],
                referer=req["referer"],
                reason=req["reason"]
            )
            for req in blocked_requests
        ]
        
    except Exception as e:
        logger.error(f"Failed to get blocked requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blocked requests"
        )


@router.get("/stats", response_model=IPWhitelistStatsResponse)
async def get_ip_whitelist_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get IP whitelist statistics
    
    Returns detailed statistics about IP whitelisting.
    Requires authentication.
    """
    try:
        manager = get_ip_whitelist_manager()
        stats = manager.get_stats()
        
        return IPWhitelistStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get IP whitelist stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IP whitelist stats"
        )


@router.post("/config/update", response_model=IPWhitelistConfigResponse)
async def update_ip_whitelist_config(
    config_update: IPWhitelistConfigUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update IP whitelist configuration
    
    Updates the IP whitelist configuration.
    Requires authentication with admin privileges.
    
    Note: This endpoint updates the runtime configuration only.
    For persistent changes, update the configuration file.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        manager = get_ip_whitelist_manager()
        config = manager.config
        
        # Update configuration
        if config_update.enabled is not None:
            config.enabled = config_update.enabled
        
        if config_update.mode is not None:
            if config_update.mode not in ["whitelist", "blacklist"]:
                raise ValidationException("Mode must be 'whitelist' or 'blacklist'")
            config.mode = config_update.mode
        
        if config_update.allowed_ips is not None:
            config.allowed_ips = config_update.allowed_ips
            manager.allowed_matcher = manager.allowed_matcher.__class__(config.allowed_ips)
        
        if config_update.blocked_ips is not None:
            config.blocked_ips = config_update.blocked_ips
            manager.blocked_matcher = manager.blocked_matcher.__class__(config.blocked_ips)
        
        if config_update.admin_ips is not None:
            config.admin_ips = config_update.admin_ips
            manager.admin_matcher = manager.admin_matcher.__class__(config.admin_ips)
        
        if config_update.trust_proxy_headers is not None:
            config.trust_proxy_headers = config_update.trust_proxy_headers
        
        if config_update.enable_rate_limiting is not None:
            config.enable_rate_limiting = config_update.enable_rate_limiting
        
        if config_update.rate_limit_requests is not None:
            config.rate_limit_requests = config_update.rate_limit_requests
        
        if config_update.rate_limit_window is not None:
            config.rate_limit_window = config_update.rate_limit_window
        
        if config_update.log_blocked_requests is not None:
            config.log_blocked_requests = config_update.log_blocked_requests
        
        if config_update.log_allowed_requests is not None:
            config.log_allowed_requests = config_update.log_allowed_requests
        
        # Log configuration change
        logger.info(
            "IP whitelist configuration updated",
            extra={
                "user_id": str(current_user.id),
                "changes": config_update.dict(exclude_none=True)
            }
        )
        
        # Return updated configuration
        return await get_ip_whitelist_config(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update IP whitelist config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update IP whitelist config"
        )


@router.post("/ip/add", response_model=IPWhitelistConfigResponse)
async def add_ip_to_list(
    ip_request: IPAddRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Add IP to whitelist/blacklist
    
    Adds an IP address to the specified list (allowed, blocked, or admin).
    Requires authentication with admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        manager = get_ip_whitelist_manager()
        config = manager.config
        
        # Validate list type
        if ip_request.list_type not in ["allowed", "blocked", "admin"]:
            raise ValidationException("List type must be 'allowed', 'blocked', or 'admin'")
        
        # Add IP to appropriate list
        if ip_request.list_type == "allowed":
            if ip_request.ip not in config.allowed_ips:
                config.allowed_ips.append(ip_request.ip)
                manager.allowed_matcher = manager.allowed_matcher.__class__(config.allowed_ips)
        elif ip_request.list_type == "blocked":
            if ip_request.ip not in config.blocked_ips:
                config.blocked_ips.append(ip_request.ip)
                manager.blocked_matcher = manager.blocked_matcher.__class__(config.blocked_ips)
        elif ip_request.list_type == "admin":
            if ip_request.ip not in config.admin_ips:
                config.admin_ips.append(ip_request.ip)
                manager.admin_matcher = manager.admin_matcher.__class__(config.admin_ips)
        
        # Log IP addition
        logger.info(
            f"IP {ip_request.ip} added to {ip_request.list_type} list",
            extra={
                "user_id": str(current_user.id),
                "ip": ip_request.ip,
                "list_type": ip_request.list_type,
                "description": ip_request.description
            }
        )
        
        # Return updated configuration
        return await get_ip_whitelist_config(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add IP to list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add IP to list"
        )


@router.post("/ip/remove", response_model=IPWhitelistConfigResponse)
async def remove_ip_from_list(
    ip_request: IPRemoveRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove IP from whitelist/blacklist
    
    Removes an IP address from the specified list (allowed, blocked, or admin).
    Requires authentication with admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        manager = get_ip_whitelist_manager()
        config = manager.config
        
        # Validate list type
        if ip_request.list_type not in ["allowed", "blocked", "admin"]:
            raise ValidationException("List type must be 'allowed', 'blocked', or 'admin'")
        
        # Remove IP from appropriate list
        if ip_request.list_type == "allowed":
            if ip_request.ip in config.allowed_ips:
                config.allowed_ips.remove(ip_request.ip)
                manager.allowed_matcher = manager.allowed_matcher.__class__(config.allowed_ips)
        elif ip_request.list_type == "blocked":
            if ip_request.ip in config.blocked_ips:
                config.blocked_ips.remove(ip_request.ip)
                manager.blocked_matcher = manager.blocked_matcher.__class__(config.blocked_ips)
        elif ip_request.list_type == "admin":
            if ip_request.ip in config.admin_ips:
                config.admin_ips.remove(ip_request.ip)
                manager.admin_matcher = manager.admin_matcher.__class__(config.admin_ips)
        
        # Log IP removal
        logger.info(
            f"IP {ip_request.ip} removed from {ip_request.list_type} list",
            extra={
                "user_id": str(current_user.id),
                "ip": ip_request.ip,
                "list_type": ip_request.list_type
            }
        )
        
        # Return updated configuration
        return await get_ip_whitelist_config(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove IP from list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove IP from list"
        )


@router.delete("/blocked-requests", status_code=status.HTTP_204_NO_CONTENT)
async def clear_blocked_requests(
    current_user: User = Depends(get_current_active_user)
):
    """
    Clear blocked requests history
    
    Clears all stored blocked requests.
    Requires authentication with admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        manager = get_ip_whitelist_manager()
        manager.blocked_requests.clear()
        
        logger.info(
            "Blocked requests history cleared",
            extra={
                "user_id": str(current_user.id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear blocked requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear blocked requests"
        )


@router.get("/test-ip/{ip}")
async def test_ip_access(
    ip: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test IP access
    
    Tests whether a specific IP address would be allowed or blocked.
    Requires authentication.
    """
    try:
        manager = get_ip_whitelist_manager()
        is_allowed = manager.is_ip_allowed(ip)
        
        return {
            "ip": ip,
            "allowed": is_allowed,
            "mode": manager.config.mode,
            "enabled": manager.config.enabled,
            "reason": "IP matches admin list" if manager.admin_matcher.matches(ip) else
                     "IP matches allowed list" if manager.allowed_matcher.matches(ip) else
                     "IP matches blocked list" if manager.blocked_matcher.matches(ip) else
                     "IP not in any list"
        }
        
    except Exception as e:
        logger.error(f"Failed to test IP access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test IP access"
        )