"""
API Gateway Main Routes

Main routing logic for proxying requests to downstream services.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import httpx

from core.config import get_settings
from core.service_discovery import get_service_client
from core.exceptions import (
    BadGatewayException,
    GatewayTimeoutException,
    ServiceUnavailableException
)
from core.logging import log_service_call

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()

# Service routing configuration
SERVICE_ROUTES = {
    "users": "user-management",
    "auth": "user-management",
    "assets": "asset-management",
    "metadata": "metadata-service",
    "search": "search-engine",
    "storage": "storage-abstraction",
    "ingest": "ingest-service",
    "proxy": "proxy-generation",
    "workflows": "workflow-engine",
    "ai": "ai-ml-service",
    "rights": "rights-management",
    "monitoring": "monitoring-logging",
    "integrations": "integration-service"
}


def get_service_name_from_path(path: str) -> Optional[str]:
    """
    Extract service name from request path
    
    Args:
        path: Request path (e.g., /api/v1/users/123)
        
    Returns:
        Service name or None if not found
    """
    path_parts = path.strip("/").split("/")
    
    # Expected format: api/v1/service/...
    if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "v1":
        service_prefix = path_parts[2]
        return SERVICE_ROUTES.get(service_prefix)
    
    return None


def build_downstream_path(original_path: str) -> str:
    """
    Build downstream service path from original path
    
    Args:
        original_path: Original request path
        
    Returns:
        Path for downstream service
    """
    # Remove /api/v1 prefix and keep the rest
    path_parts = original_path.strip("/").split("/")
    
    if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "v1":
        # Keep everything after /api/v1/service_name
        downstream_parts = path_parts[2:]  # Include service name
        return "/" + "/".join(downstream_parts)
    
    return original_path


async def proxy_request(
    request: Request,
    service_name: str,
    downstream_path: str
) -> Response:
    """
    Proxy request to downstream service with enhanced routing
    
    Args:
        request: FastAPI request object
        service_name: Name of the downstream service
        downstream_path: Path for the downstream service
        
    Returns:
        Response from downstream service
        
    Raises:
        HTTPException: If service is unavailable or request fails
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    start_time = time.time()
    
    try:
        # Get service client
        service_client = get_service_client(service_name)
        
        # Prepare headers
        headers = dict(request.headers)
        
        # Remove hop-by-hop headers
        hop_by_hop_headers = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
            'upgrade', 'host'
        }
        
        headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop_headers}
        
        # Add request ID for tracing
        headers['X-Request-ID'] = request_id
        
        # Add user context if available
        if hasattr(request.state, 'user_id'):
            headers['X-User-ID'] = request.state.user_id
        
        # Read request body
        body = await request.body()
        
        # Prepare context for load balancing
        context = {
            'client_ip': request.client.host if request.client else None,
            'user_id': getattr(request.state, 'user_id', None),
            'request_id': request_id
        }
        
        # Make request to downstream service
        response = await service_client.request(
            method=request.method,
            path=downstream_path,
            headers=headers,
            params=dict(request.query_params),
            data=body if body else None,
            context=context
        )
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log service call
        log_service_call(
            service_name=service_name,
            method=request.method,
            path=downstream_path,
            status_code=response.status_code,
            response_time=response_time,
            request_id=request_id,
            success=200 <= response.status_code < 400
        )
        
        # Create response
        response_headers = dict(response.headers)
        
        # Remove hop-by-hop headers from response
        response_headers = {k: v for k, v in response_headers.items() 
                          if k.lower() not in hop_by_hop_headers}
        
        # Add gateway headers
        response_headers['X-Gateway'] = 'MAMS-API-Gateway'
        response_headers['X-Response-Time'] = str(response_time)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type', 'application/json')
        )
        
    except httpx.TimeoutException as e:
        response_time = time.time() - start_time
        log_service_call(
            service_name=service_name,
            method=request.method,
            path=downstream_path,
            status_code=504,
            response_time=response_time,
            request_id=request_id,
            success=False,
            error_message=str(e)
        )
        raise GatewayTimeoutException(f"Request to {service_name} timed out")
        
    except httpx.ConnectError as e:
        response_time = time.time() - start_time
        log_service_call(
            service_name=service_name,
            method=request.method,
            path=downstream_path,
            status_code=503,
            response_time=response_time,
            request_id=request_id,
            success=False,
            error_message=str(e)
        )
        raise ServiceUnavailableException(f"Service {service_name} is unavailable")
        
    except httpx.HTTPStatusError as e:
        response_time = time.time() - start_time
        log_service_call(
            service_name=service_name,
            method=request.method,
            path=downstream_path,
            status_code=e.response.status_code,
            response_time=response_time,
            request_id=request_id,
            success=False,
            error_message=str(e)
        )
        raise BadGatewayException(f"Bad response from {service_name}: {e.response.status_code}")
        
    except Exception as e:
        response_time = time.time() - start_time
        log_service_call(
            service_name=service_name,
            method=request.method,
            path=downstream_path,
            status_code=500,
            response_time=response_time,
            request_id=request_id,
            success=False,
            error_message=str(e)
        )
        logger.error(f"Unexpected error proxying to {service_name}: {e}", exc_info=True)
        raise BadGatewayException(f"Error communicating with {service_name}")


@router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy_to_service(request: Request, path: str):
    """
    Proxy requests to appropriate downstream services
    
    Args:
        request: FastAPI request object
        path: Request path after /api/v1/
        
    Returns:
        Response from downstream service
    """
    # Get service name from path
    full_path = f"/api/v1/{path}"
    service_name = get_service_name_from_path(full_path)
    
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service found for path: {full_path}"
        )
    
    # Build downstream path
    downstream_path = build_downstream_path(full_path)
    
    # Proxy request
    return await proxy_request(request, service_name, downstream_path)


@router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "service": "MAMS API Gateway",
        "version": "1.0.0",
        "api_version": "v1",
        "available_services": list(SERVICE_ROUTES.keys()),
        "documentation": "/docs",
        "health_check": "/health"
    }


@router.get("/status")
async def gateway_status():
    """Gateway status endpoint with enhanced service information"""
    from core.service_discovery import get_service_status
    
    try:
        status_info = await get_service_status()
        service_status = status_info.get("services", {})
        circuit_breakers = status_info.get("circuit_breakers", {})
        
        # Calculate service health summary
        total_instances = 0
        healthy_instances = 0
        total_requests = 0
        failed_requests = 0
        
        for service_name, instances in service_status.items():
            for instance_url, instance_info in instances.items():
                total_instances += 1
                if instance_info.get("healthy", False):
                    healthy_instances += 1
                total_requests += instance_info.get("total_requests", 0)
                failed_requests += instance_info.get("failed_requests", 0)
        
        # Calculate circuit breaker summary
        open_circuits = sum(1 for cb in circuit_breakers.values() if cb.get("state") == "open")
        half_open_circuits = sum(1 for cb in circuit_breakers.values() if cb.get("state") == "half_open")
        
        return {
            "gateway": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": settings.environment,
                "uptime": time.time() - getattr(gateway_status, '_start_time', time.time())
            },
            "services": {
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "unhealthy_instances": total_instances - healthy_instances,
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "success_rate": round((total_requests - failed_requests) / total_requests * 100, 2) if total_requests > 0 else 100,
                "details": service_status
            },
            "circuit_breakers": {
                "total": len(circuit_breakers),
                "open": open_circuits,
                "half_open": half_open_circuits,
                "closed": len(circuit_breakers) - open_circuits - half_open_circuits,
                "details": circuit_breakers
            },
            "routing": {
                "available_routes": SERVICE_ROUTES,
                "api_version": "v1",
                "load_balancing_enabled": True,
                "retry_enabled": True,
                "circuit_breaker_enabled": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting gateway status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get gateway status"
        )

# Store start time for uptime calculation
gateway_status._start_time = time.time()


# Import time module for timing
import time

# Import auth, rate limit, service management, logs, versioned, version info, CORS management, API key, security, and IP whitelist routers
from .auth import router as auth_router
from .rate_limit import router as rate_limit_router
from .service_management import router as service_management_router
from .logs import router as logs_router
from .versioned_routes import api_versioned_router
from .version_info import version_info_router
from .cors_management import cors_management_router
from .api_key_routes import router as api_key_router
from .security_routes import router as security_router
from .ip_whitelist_routes import router as ip_whitelist_router

# Combine routers
api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(rate_limit_router)
api_router.include_router(service_management_router)
api_router.include_router(logs_router)
api_router.include_router(version_info_router)  # Add version info routes
api_router.include_router(cors_management_router)  # Add CORS management routes
api_router.include_router(api_key_router)  # Add API key routes
api_router.include_router(security_router)  # Add security routes
api_router.include_router(ip_whitelist_router)  # Add IP whitelist routes
api_router.include_router(api_versioned_router)  # Add versioned routes
api_router.include_router(router)