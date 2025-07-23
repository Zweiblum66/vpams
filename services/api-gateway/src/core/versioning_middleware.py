"""
API Versioning Middleware

Middleware for handling API versioning, deprecation warnings,
and version-specific behavior.
"""

import time
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from core.versioning import (
    extract_request_version,
    version_registry,
    APIVersion,
    get_default_version,
    get_supported_versions
)
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning
    
    Features:
    - Extract API version from requests
    - Add version headers to responses
    - Handle deprecation warnings
    - Version-based request transformation
    - Version metrics collection
    """
    
    def __init__(self, app, default_version: Optional[str] = None):
        super().__init__(app)
        self.default_version = default_version or get_default_version()
        self.version_metrics: Dict[str, Dict[str, int]] = {}
        
        # Initialize metrics for all versions
        for version in get_supported_versions():
            self.version_metrics[version] = {
                "requests": 0,
                "errors": 0,
                "deprecated_calls": 0
            }
    
    async def dispatch(self, request: Request, call_next):
        """Process the request with version handling"""
        start_time = time.time()
        
        # Extract API version from request
        try:
            version = await extract_request_version(request)
            if version is None:
                version = APIVersion(self.default_version)
        except Exception as e:
            logger.error(f"Failed to extract API version: {e}")
            version = APIVersion(self.default_version)
        
        # Store version in request state
        request.state.api_version = version
        version_str = str(version)
        
        # Update metrics
        if version_str in self.version_metrics:
            self.version_metrics[version_str]["requests"] += 1
        
        # Check if version is supported
        if not version_registry.is_version_supported(version):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "UNSUPPORTED_API_VERSION",
                        "message": f"API version {version} is not supported",
                        "supported_versions": get_supported_versions(),
                        "default_version": self.default_version
                    }
                }
            )
        
        # Apply version-specific request transformations
        request = await self._transform_request(request, version)
        
        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            # Update error metrics
            if version_str in self.version_metrics:
                self.version_metrics[version_str]["errors"] += 1
            raise
        
        # Add version headers to response
        response.headers["X-API-Version"] = version_str
        response.headers["X-API-Version-Status"] = self._get_version_status(version)
        response.headers["X-API-Supported-Versions"] = ", ".join(get_supported_versions())
        
        # Add deprecation headers if applicable
        deprecation_info = version_registry.get_deprecation_info(version)
        if deprecation_info:
            response.headers["X-API-Deprecation"] = "true"
            response.headers["X-API-Deprecation-Date"] = deprecation_info.get("deprecation_date", "TBD")
            response.headers["X-API-Deprecation-Info"] = deprecation_info["message"]
            response.headers["X-API-Sunset"] = deprecation_info.get("deprecation_date", "TBD")
            
            # Update deprecation metrics
            if version_str in self.version_metrics:
                self.version_metrics[version_str]["deprecated_calls"] += 1
        
        # Add performance header
        duration = (time.time() - start_time) * 1000
        response.headers["X-API-Response-Time"] = f"{duration:.2f}ms"
        
        # Log version usage
        logger.info(
            f"API request - Version: {version}, "
            f"Method: {request.method}, "
            f"Path: {request.url.path}, "
            f"Status: {response.status_code}, "
            f"Duration: {duration:.2f}ms"
        )
        
        return response
    
    async def _transform_request(self, request: Request, version: APIVersion) -> Request:
        """
        Apply version-specific request transformations
        
        This allows for handling breaking changes between versions.
        """
        version_str = str(version)
        
        # Add version to headers for downstream services
        if hasattr(request.headers, '_list'):
            request.headers._list.append(
                (b"x-api-version", version_str.encode())
            )
        
        # Version-specific transformations
        if version.major == 1:
            # V1 specific transformations
            pass
        
        elif version.major == 2:
            # V2 specific transformations
            # Example: Transform old header names to new ones
            if "X-Auth-Token" in request.headers:
                auth_value = request.headers["X-Auth-Token"]
                if hasattr(request.headers, '_list'):
                    request.headers._list.append(
                        (b"authorization", f"Bearer {auth_value}".encode())
                    )
        
        return request
    
    def _get_version_status(self, version: APIVersion) -> str:
        """Get the status of a version"""
        config = version_registry.get_version_config(version)
        if config:
            return config.status
        return "unknown"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get version usage metrics"""
        total_requests = sum(m["requests"] for m in self.version_metrics.values())
        total_errors = sum(m["errors"] for m in self.version_metrics.values())
        
        metrics = {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "by_version": {}
        }
        
        for version, data in self.version_metrics.items():
            if data["requests"] > 0:
                metrics["by_version"][version] = {
                    "requests": data["requests"],
                    "errors": data["errors"],
                    "error_rate": (data["errors"] / data["requests"] * 100),
                    "usage_percentage": (data["requests"] / total_requests * 100),
                    "deprecated_calls": data["deprecated_calls"]
                }
        
        return metrics


class VersionValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate version-specific requirements
    
    Ensures that requests meet version-specific validation rules.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Validate request based on API version"""
        # Get version from request state (set by APIVersioningMiddleware)
        version = getattr(request.state, 'api_version', None)
        
        if version:
            # Perform version-specific validation
            validation_error = await self._validate_request(request, version)
            
            if validation_error:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "VERSION_VALIDATION_ERROR",
                            "message": validation_error,
                            "version": str(version)
                        }
                    }
                )
        
        return await call_next(request)
    
    async def _validate_request(self, request: Request, version: APIVersion) -> Optional[str]:
        """
        Perform version-specific validation
        
        Returns error message if validation fails, None otherwise.
        """
        config = version_registry.get_version_config(version)
        
        if not config:
            return None
        
        # Check minimum client version if specified
        if config.min_client_version:
            client_version = request.headers.get("X-Client-Version")
            if client_version:
                try:
                    client_ver = APIVersion(client_version)
                    min_ver = APIVersion(config.min_client_version)
                    
                    if client_ver < min_ver:
                        return f"Client version {client_version} is too old. Minimum required: {config.min_client_version}"
                except ValueError:
                    return f"Invalid client version format: {client_version}"
        
        # Version-specific validation rules
        if version.major == 2:
            # V2 requires certain headers
            if not request.headers.get("X-Request-ID"):
                return "API v2 requires X-Request-ID header"
        
        return None


class VersionMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect detailed version metrics
    
    Tracks API version usage patterns for analytics.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "version_transitions": {},  # Track version upgrades/downgrades
            "endpoint_usage": {},       # Track which endpoints are used per version
            "client_versions": {}       # Track client version distribution
        }
    
    async def dispatch(self, request: Request, call_next):
        """Collect version metrics"""
        version = getattr(request.state, 'api_version', None)
        
        if version:
            version_str = str(version)
            
            # Track endpoint usage
            endpoint_key = f"{version_str}:{request.method}:{request.url.path}"
            if endpoint_key not in self.metrics["endpoint_usage"]:
                self.metrics["endpoint_usage"][endpoint_key] = 0
            self.metrics["endpoint_usage"][endpoint_key] += 1
            
            # Track client versions
            client_version = request.headers.get("X-Client-Version")
            if client_version:
                if client_version not in self.metrics["client_versions"]:
                    self.metrics["client_versions"][client_version] = {}
                
                if version_str not in self.metrics["client_versions"][client_version]:
                    self.metrics["client_versions"][client_version][version_str] = 0
                
                self.metrics["client_versions"][client_version][version_str] += 1
            
            # Track version transitions (from previous version header)
            prev_version = request.headers.get("X-Previous-API-Version")
            if prev_version and prev_version != version_str:
                transition_key = f"{prev_version}->{version_str}"
                if transition_key not in self.metrics["version_transitions"]:
                    self.metrics["version_transitions"][transition_key] = 0
                self.metrics["version_transitions"][transition_key] += 1
        
        return await call_next(request)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self.metrics