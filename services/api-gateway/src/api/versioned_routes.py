"""
Versioned API Routes

Implements version-aware routing for the API Gateway.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import logging

from core.config import get_settings
from core.versioning import (
    extract_request_version,
    get_supported_versions,
    get_current_version,
    get_default_version,
    version_registry,
    APIVersion
)
from api.routes import (
    proxy_request,
    get_service_name_from_path,
    build_downstream_path,
    SERVICE_ROUTES
)

settings = get_settings()
logger = logging.getLogger(__name__)


class VersionedAPIRouter:
    """Router that handles multiple API versions"""
    
    def __init__(self):
        self.routers: Dict[str, APIRouter] = {}
        self.version_middleware: Dict[str, list] = {}
        
        # Initialize routers for each supported version
        for version in get_supported_versions():
            self.routers[version] = APIRouter()
            self.version_middleware[version] = []
    
    def get_router(self, version: str) -> APIRouter:
        """Get router for specific version"""
        if version not in self.routers:
            raise ValueError(f"Unsupported API version: {version}")
        return self.routers[version]
    
    def add_middleware(self, version: str, middleware: callable):
        """Add version-specific middleware"""
        if version in self.version_middleware:
            self.version_middleware[version].append(middleware)


# Create versioned router instance
versioned_router = VersionedAPIRouter()


# Version 1 Routes
v1_router = versioned_router.get_router("v1")


@v1_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def v1_proxy_to_service(request: Request, path: str):
    """
    V1 API - Proxy requests to appropriate downstream services
    
    This is the stable API version with basic functionality.
    """
    # Build full path with version
    full_path = f"/api/v1/{path}"
    service_name = get_service_name_from_path(full_path)
    
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service found for path: {full_path}"
        )
    
    # Build downstream path
    downstream_path = build_downstream_path(full_path)
    
    # Add version header for downstream service
    request.headers.__dict__["_list"].append((b"x-api-version", b"1"))
    
    # Proxy request
    response = await proxy_request(request, service_name, downstream_path)
    
    # Add version information to response headers
    response.headers["X-API-Version"] = "1"
    response.headers["X-API-Version-Status"] = "stable"
    
    return response


@v1_router.get("/")
async def v1_api_root():
    """V1 API root endpoint"""
    return {
        "service": "MAMS API Gateway",
        "version": "1.0.0",
        "api_version": "v1",
        "status": "stable",
        "available_services": list(SERVICE_ROUTES.keys()),
        "documentation": "/docs/v1",
        "health_check": "/health",
        "deprecation": None
    }


# Version 2 Routes (Beta)
v2_router = versioned_router.get_router("v2")


@v2_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def v2_proxy_to_service(request: Request, path: str):
    """
    V2 API - Enhanced proxy with additional features
    
    This is the beta API version with new features and improvements.
    """
    # Build full path with version
    full_path = f"/api/v2/{path}"
    service_name = get_service_name_from_path(full_path)
    
    if not service_name:
        # V2 provides more detailed error response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "SERVICE_NOT_FOUND",
                "message": f"No service found for path: {full_path}",
                "available_services": list(SERVICE_ROUTES.keys()),
                "suggestion": "Check the API documentation for valid service paths"
            }
        )
    
    # Build downstream path
    downstream_path = build_downstream_path(full_path)
    
    # Add version header for downstream service
    request.headers.__dict__["_list"].append((b"x-api-version", b"2"))
    
    # V2 feature: Add request context
    request.headers.__dict__["_list"].append((b"x-request-context", b"v2-enhanced"))
    
    # Proxy request
    response = await proxy_request(request, service_name, downstream_path)
    
    # Add version information to response headers
    response.headers["X-API-Version"] = "2"
    response.headers["X-API-Version-Status"] = "beta"
    response.headers["X-API-Features"] = "enhanced-errors,request-context,graphql-ready"
    
    return response


@v2_router.get("/")
async def v2_api_root():
    """V2 API root endpoint with enhanced information"""
    return {
        "service": "MAMS API Gateway",
        "version": "2.0.0-beta",
        "api_version": "v2",
        "status": "beta",
        "available_services": {
            name: {
                "status": "active",
                "endpoints": f"/api/v2/{name}",
                "health": f"/api/v2/{name}/health"
            }
            for name in SERVICE_ROUTES.keys()
        },
        "features": [
            "Enhanced error responses",
            "Request context tracking",
            "GraphQL support (coming soon)",
            "WebSocket subscriptions (coming soon)"
        ],
        "documentation": "/docs/v2",
        "health_check": "/health",
        "deprecation": None,
        "migration_guide": "/docs/migration/v1-to-v2"
    }


# Main versioned router
router = APIRouter()


@router.get("/versions")
async def list_api_versions():
    """List all available API versions"""
    versions_info = []
    
    for version in get_supported_versions():
        config = version_registry.get_version_config(version)
        if config:
            versions_info.append({
                "version": version,
                "status": config.status,
                "deprecated": config.deprecated,
                "deprecation_date": config.deprecation_date.isoformat() if config.deprecation_date else None,
                "features": config.features,
                "breaking_changes": config.breaking_changes
            })
    
    return {
        "current_version": get_current_version(),
        "default_version": get_default_version(),
        "supported_versions": versions_info,
        "versioning_strategy": "url_path",
        "documentation": "/docs/api-versioning"
    }


@router.api_route("/v{version}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def versioned_proxy(request: Request, version: str, path: str):
    """
    Main versioned routing endpoint
    
    Routes requests to appropriate version handlers.
    """
    try:
        # Parse version
        api_version = APIVersion(version)
        
        # Check if version is supported
        if not version_registry.is_version_supported(api_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "UNSUPPORTED_VERSION",
                    "message": f"API version {version} is not supported",
                    "supported_versions": get_supported_versions(),
                    "default_version": get_default_version()
                }
            )
        
        # Check for deprecation
        deprecation_info = version_registry.get_deprecation_info(api_version)
        
        # Route to appropriate version handler
        version_str = f"v{api_version.major}"
        
        if version_str == "v1":
            response = await v1_proxy_to_service(request, path)
        elif version_str == "v2":
            response = await v2_proxy_to_service(request, path)
        else:
            # Fallback to v1 for older versions
            response = await v1_proxy_to_service(request, path)
        
        # Add deprecation warning if applicable
        if deprecation_info:
            response.headers["X-API-Deprecation-Warning"] = deprecation_info["message"]
            response.headers["X-API-Deprecation-Date"] = deprecation_info["deprecation_date"] or "TBD"
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_VERSION_FORMAT",
                "message": f"Invalid version format: {version}",
                "expected_format": "Major version number (e.g., 1, 2)",
                "example": "/api/v1/users"
            }
        )


@router.get("/v{version}")
async def versioned_root(version: str):
    """Version-specific API root"""
    try:
        api_version = APIVersion(version)
        
        if not version_registry.is_version_supported(api_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API version {version} is not supported"
            )
        
        version_str = f"v{api_version.major}"
        
        if version_str == "v1":
            return await v1_api_root()
        elif version_str == "v2":
            return await v2_api_root()
        else:
            return await v1_api_root()
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid version format: {version}"
        )


# Version negotiation middleware
async def version_negotiation_middleware(request: Request, call_next):
    """
    Middleware to handle version negotiation
    
    Adds version information to request state and response headers.
    """
    # Extract version from request
    version = await extract_request_version(request)
    
    # Store in request state
    request.state.api_version = version
    
    # Process request
    response = await call_next(request)
    
    # Add version headers to response
    response.headers["X-API-Version"] = str(version)
    
    # Add supported versions header
    response.headers["X-API-Supported-Versions"] = ", ".join(get_supported_versions())
    
    return response


# Export the main router
api_versioned_router = router