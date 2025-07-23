"""
Multi-tenant middleware for request isolation and context injection.

Provides tenant context resolution and isolation for all requests.
"""

import time
import uuid
from typing import Optional, Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from .core.config import get_settings
from .core.exceptions import TenantNotFoundError, TenantSuspendedError
from .services.tenant_resolver import TenantResolver
from .models.schemas import TenantContext


logger = structlog.get_logger()


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware for multi-tenant request handling.
    
    Responsibilities:
    - Resolve tenant context from request
    - Inject tenant context into request state
    - Enforce tenant isolation
    - Add tenant-specific headers to responses
    - Track request metrics per tenant
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.resolver = TenantResolver()
        
        # Paths that don't require tenant context
        self.public_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        }
        
        # System paths that bypass tenant resolution
        self.system_paths = {
            "/api/v1/tenants",  # Tenant management endpoints
            "/api/v1/system"    # System admin endpoints
        }
        
        # Request tracking
        self.request_counts: Dict[str, int] = {}
        self.request_times: Dict[str, float] = {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to state
        request.state.request_id = request_id
        
        # Skip tenant resolution for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        try:
            # Resolve tenant context
            tenant_context = await self._resolve_tenant_context(request)
            
            if tenant_context:
                # Inject tenant context into request
                request.state.tenant_context = tenant_context
                request.state.tenant_id = tenant_context.tenant_id
                
                # Log request with tenant context
                logger.info(
                    "Request started",
                    request_id=request_id,
                    tenant_id=tenant_context.tenant_id,
                    method=request.method,
                    path=request.url.path,
                    resolved_from=tenant_context.resolved_from
                )
                
                # Track metrics
                self._track_request(tenant_context.tenant_id)
                
            else:
                # Check if this is a system path
                if not self._is_system_path(request.url.path):
                    # Tenant context required but not found
                    logger.warning(
                        "No tenant context resolved",
                        request_id=request_id,
                        host=request.headers.get("host"),
                        path=request.url.path
                    )
                    
                    if self.settings.require_tenant_context:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "Tenant context required",
                                "request_id": request_id
                            }
                        )
            
            # Process request
            response = await call_next(request)
            
            # Add tenant headers to response
            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                response.headers["X-Request-ID"] = request_id
            
            # Log request completion
            duration = time.time() - start_time
            logger.info(
                "Request completed",
                request_id=request_id,
                tenant_id=tenant_context.tenant_id if tenant_context else None,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            
            return response
            
        except TenantNotFoundError as e:
            logger.error(
                "Tenant not found",
                request_id=request_id,
                tenant_id=e.tenant_id,
                error=str(e)
            )
            
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Tenant not found",
                    "request_id": request_id
                }
            )
            
        except TenantSuspendedError as e:
            logger.warning(
                "Access denied - tenant suspended",
                request_id=request_id,
                tenant_id=e.tenant_id,
                error=str(e)
            )
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Tenant suspended",
                    "request_id": request_id
                }
            )
            
        except Exception as e:
            logger.error(
                "Middleware error",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                }
            )
    
    async def _resolve_tenant_context(self, request: Request) -> Optional[TenantContext]:
        """Resolve tenant context from request."""
        # Extract request information
        host = request.headers.get("host")
        headers = dict(request.headers)
        
        # Extract API key if present
        api_key = None
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer mams_"):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
        elif "x-api-key" in headers:
            api_key = headers["x-api-key"]
        
        # Extract JWT claims if present
        token_claims = None
        if hasattr(request.state, "user") and request.state.user:
            # User already authenticated, extract claims
            token_claims = {
                "tenant_id": getattr(request.state.user, "tenant_id", None),
                "user_id": getattr(request.state.user, "user_id", None)
            }
        
        # Resolve tenant
        tenant_context = await self.resolver.resolve_tenant(
            host=host,
            headers=headers,
            token_claims=token_claims,
            api_key=api_key
        )
        
        # Validate tenant is active
        if tenant_context and not tenant_context.is_active:
            raise TenantSuspendedError(tenant_context.tenant_id)
        
        return tenant_context
    
    def _is_system_path(self, path: str) -> bool:
        """Check if path is a system management path."""
        for system_path in self.system_paths:
            if path.startswith(system_path):
                return True
        return False
    
    def _track_request(self, tenant_id: str) -> None:
        """Track request metrics per tenant."""
        # Increment request count
        if tenant_id not in self.request_counts:
            self.request_counts[tenant_id] = 0
        self.request_counts[tenant_id] += 1
        
        # Track last request time
        self.request_times[tenant_id] = time.time()


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing strict tenant isolation.
    
    This middleware works in conjunction with TenantMiddleware to:
    - Validate all database queries include tenant context
    - Prevent cross-tenant data access
    - Audit suspicious access patterns
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Track cross-tenant access attempts
        self.violation_counts: Dict[str, int] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce tenant isolation rules."""
        # Only enforce if tenant context exists
        if not hasattr(request.state, "tenant_context"):
            return await call_next(request)
        
        tenant_context = request.state.tenant_context
        
        # Set isolation context for this request
        request.state.isolation_context = {
            "tenant_id": tenant_context.tenant_id,
            "user_id": getattr(request.state, "user_id", None),
            "request_id": request.state.request_id,
            "strict_mode": self.settings.strict_isolation_mode
        }
        
        # Process request
        response = await call_next(request)
        
        # Check for isolation violations in response
        if hasattr(request.state, "isolation_violations"):
            violations = request.state.isolation_violations
            
            if violations:
                # Track violations
                self._track_violations(tenant_context.tenant_id, violations)
                
                # Log violations
                logger.warning(
                    "Isolation violations detected",
                    tenant_id=tenant_context.tenant_id,
                    violations=len(violations),
                    request_id=request.state.request_id
                )
                
                # In strict mode, return error
                if self.settings.strict_isolation_mode:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Tenant isolation violation",
                            "violations": violations,
                            "request_id": request.state.request_id
                        }
                    )
        
        return response
    
    def _track_violations(self, tenant_id: str, violations: list) -> None:
        """Track isolation violations per tenant."""
        if tenant_id not in self.violation_counts:
            self.violation_counts[tenant_id] = 0
        
        self.violation_counts[tenant_id] += len(violations)
        
        # Alert if threshold exceeded
        if self.violation_counts[tenant_id] > self.settings.violation_threshold:
            logger.error(
                "Tenant isolation violation threshold exceeded",
                tenant_id=tenant_id,
                violations=self.violation_counts[tenant_id]
            )


def get_tenant_context(request: Request) -> Optional[TenantContext]:
    """Get tenant context from request state."""
    return getattr(request.state, "tenant_context", None)


def require_tenant_context(request: Request) -> TenantContext:
    """Get tenant context or raise error if not present."""
    context = get_tenant_context(request)
    
    if not context:
        raise HTTPException(
            status_code=400,
            detail="Tenant context required"
        )
    
    return context


def get_tenant_id(request: Request) -> Optional[str]:
    """Get tenant ID from request state."""
    context = get_tenant_context(request)
    return context.tenant_id if context else None