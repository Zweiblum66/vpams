"""
API Gateway Middleware

Custom middleware for authentication, rate limiting, logging, and error handling.
"""

import time
import uuid
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import logging

from .config import get_settings
from .exceptions import (
    AuthenticationException,
    RateLimitException,
    APIException,
    RequestTooLargeException,
    MaintenanceModeException,
    InvalidAPIVersionException
)
from .security import token_manager
from .logging import log_request, log_error
from .redis import get_redis_client
from .rate_limiter import rate_limiter

settings = get_settings()
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add request ID to request state"""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle errors and exceptions"""
        try:
            response = await call_next(request)
            return response
        except APIException as e:
            # Log API exceptions
            log_error(
                e,
                request_id=getattr(request.state, 'request_id', 'unknown'),
                context={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": dict(request.query_params)
                }
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "timestamp": time.time(),
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                }
            )
        except Exception as e:
            # Log unexpected exceptions
            log_error(
                e,
                request_id=getattr(request.state, 'request_id', 'unknown'),
                context={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": dict(request.query_params)
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "timestamp": time.time(),
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                }
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request and response information"""
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = str(request.url.path)
        query_params = dict(request.query_params)
        headers = dict(request.headers)
        client_ip = request.client.host if request.client else None
        user_agent = headers.get("user-agent")
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Get user ID if authenticated
        user_id = getattr(request.state, 'user_id', None)
        
        # Log request
        log_request(
            method=method,
            path=path,
            status_code=response.status_code,
            response_time=response_time,
            request_id=request_id,
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            extra_data={
                "query_params": query_params,
                "response_size": response.headers.get("content-length", 0)
            }
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate limiting"""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)
        
        # Get request information
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, 'user_id', None)
        user_tier = getattr(request.state, 'user_tier', 'free')
        
        # Prepare rate limit request info
        request_info = {
            "endpoint": str(request.url.path),
            "method": request.method,
            "user_id": user_id,
            "ip_address": client_ip,
            "user_tier": user_tier
        }
        
        # Check rate limit using the new comprehensive rate limiter
        try:
            result = await rate_limiter.check_request_limit(request_info)
            
            if not result.allowed:
                # Add rate limit headers to exception response
                headers = {
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset),
                    "Retry-After": str(result.retry_after)
                }
                
                raise RateLimitException(
                    f"Rate limit exceeded. Retry after {result.retry_after} seconds",
                    details={
                        "limit": result.limit,
                        "window": result.reset - int(time.time()),
                        "remaining": result.remaining,
                        "retry_after": result.retry_after
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful response
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            response.headers["X-RateLimit-Reset"] = str(result.reset)
            
            return response
            
        except RateLimitException:
            raise
        except Exception as e:
            logger.warning(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis is unavailable
            return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/health/ready",
            "/health/live",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Authenticate requests"""
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Check for authentication header
        auth_header = request.headers.get(settings.auth_header_name)
        api_key_header = request.headers.get(settings.api_key_header_name)
        
        if not auth_header and not api_key_header:
            raise AuthenticationException("Authentication required")
        
        try:
            if auth_header:
                # JWT token authentication
                if not auth_header.startswith(f"{settings.auth_header_prefix} "):
                    raise AuthenticationException("Invalid authentication header format")
                
                token = auth_header.split(" ", 1)[1]
                payload = token_manager.verify_token(token, "access")
                
                # Check if token is blacklisted
                from core.redis import get_redis_client
                try:
                    redis_client = await get_redis_client()
                    if await redis_client.exists(f"blacklist:{token}"):
                        raise AuthenticationException("Token has been revoked")
                except Exception as e:
                    logger.warning(f"Failed to check token blacklist: {e}")
                
                # Add user information to request state
                request.state.user_id = payload.get("user_id")
                request.state.user_subject = payload.get("sub")
                request.state.user_permissions = payload.get("permissions", [])
                
            elif api_key_header:
                # API key authentication
                # This would typically validate against a database
                # For now, we'll skip API key validation
                request.state.user_id = "api_key_user"
                request.state.user_subject = "api_key"
                request.state.user_permissions = []
            
            return await call_next(request)
            
        except Exception as e:
            logger.warning(f"Authentication error: {e}")
            raise AuthenticationException(f"Authentication failed: {str(e)}")


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Request size limiting middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check request size limits"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > settings.max_request_size:
                    raise RequestTooLargeException(
                        f"Request too large. Maximum size: {settings.max_request_size} bytes",
                        details={"max_size": settings.max_request_size, "actual_size": size}
                    )
            except ValueError:
                pass  # Invalid content-length header, let it through
        
        return await call_next(request)


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Maintenance mode middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check for maintenance mode"""
        # Check if maintenance mode is enabled
        try:
            redis_client = await get_redis_client()
            maintenance_mode = await redis_client.get("maintenance_mode")
            
            if maintenance_mode == "true":
                # Allow health checks during maintenance
                if request.url.path in ["/health", "/health/ready", "/health/live"]:
                    return await call_next(request)
                
                raise MaintenanceModeException("System is currently in maintenance mode")
            
        except Exception as e:
            logger.warning(f"Maintenance mode check error: {e}")
            # Continue if Redis is unavailable
            pass
        
        return await call_next(request)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """API version validation middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate API version"""
        # Skip version check for non-API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Extract version from path
        path_parts = request.url.path.split("/")
        if len(path_parts) >= 3 and path_parts[1] == "api":
            version = path_parts[2]
            
            # Validate version format
            if not version.startswith("v") or not version[1:].isdigit():
                raise InvalidAPIVersionException(
                    f"Invalid API version format: {version}",
                    details={"supported_versions": ["v1"]}
                )
            
            # Check if version is supported
            supported_versions = ["v1"]
            if version not in supported_versions:
                raise InvalidAPIVersionException(
                    f"Unsupported API version: {version}",
                    details={"supported_versions": supported_versions}
                )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add security headers"""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP header for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        
        return response