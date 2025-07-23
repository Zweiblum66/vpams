"""
Tenant middleware for request isolation and routing.

Handles tenant identification, context injection, and request isolation.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any
import structlog
from urllib.parse import urlparse

from .config import get_settings
from .exceptions import TenantNotFoundError, TenantIsolationError
from ..services.tenant_resolver import TenantResolver


logger = structlog.get_logger()


class TenantContext:
    """Thread-local tenant context storage."""
    
    def __init__(self):
        self._tenant_id: Optional[str] = None
        self._tenant_data: Optional[Dict[str, Any]] = None
    
    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id
    
    @tenant_id.setter
    def tenant_id(self, value: str):
        self._tenant_id = value
    
    @property
    def tenant_data(self) -> Optional[Dict[str, Any]]:
        return self._tenant_data
    
    @tenant_data.setter
    def tenant_data(self, value: Dict[str, Any]):
        self._tenant_data = value
    
    def clear(self):
        self._tenant_id = None
        self._tenant_data = None


# Global tenant context
tenant_context = TenantContext()


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware for multi-tenant request handling.
    
    Identifies tenant from request and sets up tenant context for
    downstream processing.
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.settings = get_settings()
        self.tenant_resolver = TenantResolver()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with tenant context."""
        # Skip tenant resolution for health checks and system endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        try:
            # Clear any existing tenant context
            tenant_context.clear()
            
            # Resolve tenant from request
            tenant_info = await self._resolve_tenant(request)
            
            if not tenant_info:
                # No tenant found and multi-tenancy is enabled
                if self.settings.multi_tenancy_enabled:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": {
                                "code": "TENANT_REQUIRED",
                                "message": "Tenant identification required"
                            }
                        }
                    )
            else:
                # Set tenant context
                tenant_context.tenant_id = tenant_info["tenant_id"]
                tenant_context.tenant_data = tenant_info
                
                # Add tenant info to request state
                request.state.tenant_id = tenant_info["tenant_id"]
                request.state.tenant_data = tenant_info
                
                # Log tenant context
                logger.debug(
                    "Tenant context established",
                    tenant_id=tenant_info["tenant_id"],
                    path=request.url.path
                )
            
            # Process request with tenant context
            response = await call_next(request)
            
            # Add tenant header to response
            if tenant_info:
                response.headers["X-Tenant-ID"] = tenant_info["tenant_id"]
            
            return response
            
        except TenantNotFoundError as e:
            logger.warning("Tenant not found", error=str(e))
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "TENANT_NOT_FOUND",
                        "message": str(e)
                    }
                }
            )
            
        except TenantIsolationError as e:
            logger.error("Tenant isolation violation", error=str(e))
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "TENANT_ISOLATION_ERROR",
                        "message": str(e)
                    }
                }
            )
            
        except Exception as e:
            logger.error("Error in tenant middleware", error=str(e))
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "TENANT_MIDDLEWARE_ERROR",
                        "message": "Internal server error"
                    }
                }
            )
        
        finally:
            # Clear tenant context after request
            tenant_context.clear()
    
    async def _resolve_tenant(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Resolve tenant from request.
        
        Attempts multiple resolution strategies:
        1. Domain-based (subdomain or custom domain)
        2. Header-based (X-Tenant-ID)
        3. URL path-based (/tenant/{tenant_id}/...)
        4. JWT token claims
        """
        
        # Strategy 1: Domain-based resolution
        tenant_info = await self._resolve_from_domain(request)
        if tenant_info:
            return tenant_info
        
        # Strategy 2: Header-based resolution
        tenant_info = await self._resolve_from_header(request)
        if tenant_info:
            return tenant_info
        
        # Strategy 3: URL path-based resolution
        tenant_info = await self._resolve_from_path(request)
        if tenant_info:
            return tenant_info
        
        # Strategy 4: JWT token-based resolution
        tenant_info = await self._resolve_from_token(request)
        if tenant_info:
            return tenant_info
        
        return None
    
    async def _resolve_from_domain(self, request: Request) -> Optional[Dict[str, Any]]:
        """Resolve tenant from domain (subdomain or custom domain)."""
        host = request.headers.get("host", "").lower()
        
        if not host:
            return None
        
        # Remove port if present
        host = host.split(":")[0]
        
        # Check for subdomain pattern (e.g., tenant1.mams.com)
        if "." in host:
            parts = host.split(".")
            if len(parts) >= 3:  # subdomain.domain.tld
                potential_tenant = parts[0]
                
                # Validate against reserved subdomains
                reserved = ["www", "api", "admin", "app", "dashboard"]
                if potential_tenant not in reserved:
                    tenant_info = await self.tenant_resolver.resolve_by_subdomain(potential_tenant)
                    if tenant_info:
                        return tenant_info
        
        # Check for custom domain
        tenant_info = await self.tenant_resolver.resolve_by_domain(host)
        if tenant_info:
            return tenant_info
        
        return None
    
    async def _resolve_from_header(self, request: Request) -> Optional[Dict[str, Any]]:
        """Resolve tenant from X-Tenant-ID header."""
        tenant_id = request.headers.get("x-tenant-id")
        
        if not tenant_id:
            return None
        
        tenant_info = await self.tenant_resolver.resolve_by_id(tenant_id)
        return tenant_info
    
    async def _resolve_from_path(self, request: Request) -> Optional[Dict[str, Any]]:
        """Resolve tenant from URL path."""
        path = request.url.path
        
        # Check for /api/v1/tenant/{tenant_id}/... pattern
        if path.startswith("/api/v1/tenant/"):
            parts = path.split("/")
            if len(parts) >= 5:
                tenant_id = parts[4]
                
                tenant_info = await self.tenant_resolver.resolve_by_id(tenant_id)
                if tenant_info:
                    # Modify request path to remove tenant segment
                    # This allows downstream routes to work normally
                    new_path = "/api/v1/" + "/".join(parts[5:])
                    request._url = request.url.replace(path=new_path)
                    
                    return tenant_info
        
        return None
    
    async def _resolve_from_token(self, request: Request) -> Optional[Dict[str, Any]]:
        """Resolve tenant from JWT token claims."""
        auth_header = request.headers.get("authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        
        # Extract tenant from token claims
        tenant_info = await self.tenant_resolver.resolve_from_token(token)
        return tenant_info


def get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from context."""
    return tenant_context.tenant_id


def get_current_tenant_data() -> Optional[Dict[str, Any]]:
    """Get current tenant data from context."""
    return tenant_context.tenant_data


def require_tenant_context(tenant_id: Optional[str] = None) -> str:
    """
    Require tenant context, optionally matching specific tenant.
    
    Args:
        tenant_id: Optional specific tenant ID to match
        
    Returns:
        Current tenant ID
        
    Raises:
        TenantIsolationError: If no tenant context or wrong tenant
    """
    current_tenant = get_current_tenant_id()
    
    if not current_tenant:
        raise TenantIsolationError("No tenant context available", "unknown")
    
    if tenant_id and current_tenant != tenant_id:
        raise TenantIsolationError(
            f"Tenant mismatch: expected {tenant_id}, got {current_tenant}",
            current_tenant,
            tenant_id
        )
    
    return current_tenant