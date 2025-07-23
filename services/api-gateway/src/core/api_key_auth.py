"""
API Key Authentication

Provides API key authentication support for the gateway.
"""

from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from db.base import AsyncSessionLocal
from services.api_key_service import APIKeyService
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# API Key extractors
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Optional[str] = None,
    query_key: Optional[str] = None
) -> Optional[str]:
    """
    Extract API key from request
    
    Args:
        header_key: API key from header
        query_key: API key from query parameter
        
    Returns:
        API key string or None
    """
    # Prefer header over query parameter
    return header_key or query_key


async def validate_api_key(
    request: Request,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Validate API key and return associated data
    
    Args:
        request: FastAPI request
        api_key: API key to validate
        
    Returns:
        Dictionary with API key data or None
    """
    if not api_key:
        return None
    
    async with AsyncSessionLocal() as db:
        service = APIKeyService(db)
        key_model = await service.validate_api_key(api_key)
        
        if not key_model:
            return None
        
        # Log usage asynchronously (fire and forget)
        try:
            await service.log_api_key_usage(
                api_key_id=str(key_model.id),
                request_id=getattr(request.state, 'request_id', None),
                method=request.method,
                path=request.url.path,
                status_code=200,  # Will be updated by middleware
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                response_time_ms=None  # Will be updated by middleware
            )
        except Exception as e:
            logger.error(f"Failed to log API key usage: {e}")
        
        return {
            "api_key_id": str(key_model.id),
            "api_key_name": key_model.name,
            "scopes": key_model.scopes,
            "user_id": str(key_model.user_id) if key_model.user_id else None,
            "application_id": str(key_model.application_id) if key_model.application_id else None,
            "rate_limit_override": key_model.rate_limit_override,
            "metadata": key_model.metadata
        }


async def require_api_key(
    request: Request,
    header_key: Optional[str] = api_key_header,
    query_key: Optional[str] = api_key_query
) -> Dict[str, Any]:
    """
    Require valid API key for request
    
    Args:
        request: FastAPI request
        header_key: API key from header
        query_key: API key from query parameter
        
    Returns:
        API key data
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    api_key = await get_api_key(header_key, query_key)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    key_data = await validate_api_key(request, api_key)
    
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Store in request state for later use
    request.state.api_key_data = key_data
    
    return key_data


def require_api_key_scopes(*required_scopes: str):
    """
    Require specific scopes from API key
    
    Args:
        required_scopes: Required scope names
        
    Returns:
        Dependency function
    """
    async def check_scopes(
        request: Request,
        api_key_data: Dict[str, Any] = require_api_key
    ) -> Dict[str, Any]:
        """Check if API key has required scopes"""
        key_scopes = set(api_key_data.get("scopes", []))
        required = set(required_scopes)
        
        if not required.issubset(key_scopes):
            missing = required - key_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}"
            )
        
        return api_key_data
    
    return check_scopes


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication
    
    This middleware:
    - Extracts API keys from requests
    - Validates them if present
    - Adds key data to request state
    - Updates usage logs with response data
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.exclude_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request with API key authentication"""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract API key
        header_key = request.headers.get("X-API-Key")
        query_key = request.query_params.get("api_key")
        api_key = header_key or query_key
        
        # Validate if present
        if api_key:
            try:
                key_data = await validate_api_key(request, api_key)
                if key_data:
                    # Add to request state
                    request.state.api_key_data = key_data
                    request.state.auth_method = "api_key"
                    
                    # Add rate limit override if present
                    if key_data.get("rate_limit_override"):
                        request.state.rate_limit_override = key_data["rate_limit_override"]
                    
                    logger.debug(f"API key authenticated: {key_data['api_key_name']}")
                else:
                    logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            except Exception as e:
                logger.error(f"Error validating API key: {e}")
        
        # Process request
        response = await call_next(request)
        
        # Update usage log with response data if API key was used
        if hasattr(request.state, 'api_key_data') and request.state.api_key_data:
            try:
                # Get response time if available
                response_time = None
                if hasattr(request.state, 'start_time'):
                    import time
                    response_time = int((time.time() - request.state.start_time) * 1000)
                
                # Update usage log asynchronously
                async with AsyncSessionLocal() as db:
                    service = APIKeyService(db)
                    await service.log_api_key_usage(
                        api_key_id=request.state.api_key_data["api_key_id"],
                        request_id=getattr(request.state, 'request_id', None),
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        response_time_ms=response_time
                    )
            except Exception as e:
                logger.error(f"Failed to update API key usage log: {e}")
        
        return response


def check_api_key_or_jwt(
    request: Request,
    header_key: Optional[str] = api_key_header,
    query_key: Optional[str] = api_key_query
) -> bool:
    """
    Check if request has valid API key or JWT token
    
    This allows endpoints to accept either authentication method.
    
    Args:
        request: FastAPI request
        header_key: API key from header
        query_key: API key from query parameter
        
    Returns:
        True if authenticated via API key or JWT
    """
    # Check if already authenticated via JWT
    if hasattr(request.state, 'user') and request.state.user:
        return True
    
    # Check API key
    api_key = header_key or query_key
    if api_key:
        key_data = validate_api_key(request, api_key)
        if key_data:
            request.state.api_key_data = key_data
            request.state.auth_method = "api_key"
            return True
    
    return False