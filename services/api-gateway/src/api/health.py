"""
Health Check Endpoints

Health check endpoints for monitoring and load balancer health checks.
"""

import time
from typing import Dict, Any, Optional
import logging
from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import get_settings
from core.redis import health_check as redis_health_check
from core.service_discovery import get_service_status
from core.health import health_checker, HealthStatus, ComponentHealth
from api.dependencies import get_current_user, require_permissions

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Timestamp of the check")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    response_time_ms: float = Field(..., description="Health check response time")
    components: Optional[list] = Field(None, description="Component health details")
    dependencies: Optional[list] = Field(None, description="Dependency health details")
    system: Optional[dict] = Field(None, description="System information")


class HealthMetric(BaseModel):
    """Health metric model"""
    name: str
    value: float
    unit: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@router.get("/", response_model=HealthResponse)
async def health_check(
    include_details: bool = Query(default=False, description="Include detailed component information"),
    check_dependencies: bool = Query(default=False, description="Check downstream service dependencies")
):
    """
    Basic health check endpoint
    
    This endpoint provides a quick health status of the API Gateway.
    Use the query parameters to get more detailed information:
    - include_details: Shows individual component health status
    - check_dependencies: Checks the health of downstream services
    """
    result = await health_checker.check_health(
        include_details=include_details,
        check_dependencies=check_dependencies
    )
    
    return HealthResponse(**result)


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint
    
    Checks if the service is ready to accept requests.
    Returns 503 if any critical component is unhealthy.
    
    This endpoint is typically used by:
    - Kubernetes readiness probes
    - Load balancers to determine if instance should receive traffic
    - Deployment automation to verify successful startup
    """
    # Perform comprehensive health check
    result = await health_checker.check_health(
        include_details=True,
        check_dependencies=False  # Don't check dependencies for readiness
    )
    
    # Extract overall status
    overall_status = result["status"]
    is_ready = overall_status in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value]
    
    # Build response
    response_data = {
        "ready": is_ready,
        "status": overall_status,
        "timestamp": result["timestamp"],
        "checks": {}
    }
    
    # Add component statuses
    if "components" in result:
        for component in result["components"]:
            response_data["checks"][component["name"]] = {
                "status": component["status"],
                "message": component.get("message", "")
            }
    
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint
    
    Simple check to verify the service is alive and responding.
    This should always return 200 unless the service is completely broken.
    """
    return {
        "status": "alive",
        "service": "MAMS API Gateway",
        "version": "1.0.0",
        "timestamp": time.time(),
        "uptime": time.time() - settings.startup_time if hasattr(settings, 'startup_time') else 0
    }


@router.get("/services")
async def service_health_status(
    check_health: bool = Query(default=True, description="Perform active health checks"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get health status of all downstream services
    
    Returns detailed health information for all registered services.
    Requires authentication to prevent abuse of health checks.
    
    Parameters:
    - check_health: If true, performs active health checks on services
    """
    try:
        if check_health:
            # Perform active health checks
            result = await health_checker.check_health(
                include_details=True,
                check_dependencies=True
            )
            
            # Extract dependency information
            dependencies = result.get("dependencies", [])
            
            # Build service health summary
            service_health = {}
            for dep in dependencies:
                if dep["name"].startswith("service:"):
                    service_name = dep["name"].replace("service:", "")
                    service_health[service_name] = {
                        "status": dep["status"],
                        "message": dep.get("message", ""),
                        "response_time_ms": dep.get("response_time_ms"),
                        "details": dep.get("details", {})
                    }
            
            return {
                "status": result["status"],
                "timestamp": result["timestamp"],
                "services": service_health
            }
        else:
            # Just return service registry status
            service_status = await get_service_status()
            
            # Calculate overall statistics
            total_instances = 0
            healthy_instances = 0
            
            service_summary = {}
            for service_name, instances in service_status.items():
                healthy_count = 0
                for instance_url, instance_info in instances.items():
                    total_instances += 1
                    if instance_info.get("healthy", False):
                        healthy_instances += 1
                        healthy_count += 1
                
                service_summary[service_name] = {
                    "total_instances": len(instances),
                    "healthy_instances": healthy_count,
                    "status": "healthy" if healthy_count > 0 else "unhealthy"
                }
            
            return {
                "status": "healthy" if healthy_instances > 0 else "unhealthy",
                "timestamp": time.time(),
                "summary": {
                    "total_instances": total_instances,
                    "healthy_instances": healthy_instances,
                    "health_percentage": (healthy_instances / total_instances * 100) if total_instances > 0 else 0
                },
                "services": service_summary
            }
        
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )


@router.get("/metrics")
async def health_metrics():
    """
    Get basic health metrics
    
    Returns metrics that can be consumed by monitoring systems.
    """
    try:
        # Get service status
        service_status = await get_service_status()
        
        # Calculate service metrics
        service_metrics = {}
        total_healthy = 0
        total_unhealthy = 0
        
        for service_name, instances in service_status.items():
            healthy_count = sum(1 for is_healthy in instances.values() if is_healthy)
            unhealthy_count = len(instances) - healthy_count
            
            service_metrics[service_name] = {
                "healthy_instances": healthy_count,
                "unhealthy_instances": unhealthy_count,
                "total_instances": len(instances)
            }
            
            total_healthy += healthy_count
            total_unhealthy += unhealthy_count
        
        # Check Redis health
        redis_healthy = await redis_health_check()
        
        return {
            "timestamp": time.time(),
            "gateway": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": settings.environment
            },
            "redis": {
                "status": "healthy" if redis_healthy else "unhealthy"
            },
            "services": {
                "total_healthy": total_healthy,
                "total_unhealthy": total_unhealthy,
                "total_instances": total_healthy + total_unhealthy,
                "by_service": service_metrics
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health metrics: {str(e)}"
        )


@router.get("/startup")
async def startup_check():
    """
    Startup probe endpoint
    
    Used by Kubernetes to know when the container has started.
    This should return 200 as soon as the basic application is running,
    even if some components are still initializing.
    """
    return {
        "status": "started",
        "timestamp": time.time(),
        "version": getattr(settings, 'version', '1.0.0'),
        "environment": settings.environment
    }


@router.get("/diagnostics")
async def diagnostic_check(
    current_user: Dict = Depends(require_permissions("admin", "health.diagnostics"))
):
    """
    Detailed diagnostic information
    
    Provides comprehensive diagnostic data for troubleshooting.
    Requires admin permissions due to sensitive information exposure.
    """
    # Run full health check
    health_result = await health_checker.check_health(
        include_details=True,
        check_dependencies=True
    )
    
    # Add additional diagnostic information
    diagnostics = {
        **health_result,
        "configuration": {
            "environment": settings.environment,
            "debug_mode": settings.debug,
            "allowed_hosts": settings.allowed_hosts,
            "cors_origins": settings.cors_origins,
            "rate_limit_enabled": hasattr(settings, 'rate_limit_enabled') and settings.rate_limit_enabled
        },
        "performance": await _get_performance_diagnostics(),
        "errors": await _get_recent_errors(),
        "connections": await _get_connection_pool_stats()
    }
    
    return diagnostics


async def _get_performance_diagnostics() -> Dict[str, Any]:
    """Get performance diagnostic information"""
    try:
        from core.enhanced_logging import performance_logger
        
        metrics = ["request_duration", "downstream_call_duration", "database_query_duration"]
        performance_data = {}
        
        for metric in metrics:
            stats = await performance_logger.get_stats(metric)
            if stats:
                performance_data[metric] = stats
        
        return performance_data
    except Exception as e:
        logger.error(f"Failed to get performance diagnostics: {e}")
        return {"error": str(e)}


async def _get_recent_errors() -> Dict[str, Any]:
    """Get recent error information"""
    try:
        # This would typically query your logging system
        # For now, return a placeholder
        return {
            "recent_errors_count": 0,
            "last_error_timestamp": None,
            "error_rate_per_minute": 0
        }
    except Exception as e:
        logger.error(f"Failed to get error information: {e}")
        return {"error": str(e)}


async def _get_connection_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics"""
    try:
        stats = {}
        
        # Database connection pool stats
        try:
            from db.base import engine
            pool = engine.pool
            stats["database"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total": pool.total()
            }
        except Exception:
            stats["database"] = {"status": "unavailable"}
        
        # Redis connection pool stats
        try:
            redis = await get_redis_client()
            pool_stats = await redis.connection_pool.get_stats()
            stats["redis"] = pool_stats
        except Exception:
            stats["redis"] = {"status": "unavailable"}
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get connection pool stats: {e}")
        return {"error": str(e)}


@router.post("/checks/{check_name}")
async def register_custom_check(
    check_name: str,
    current_user: Dict = Depends(require_permissions("admin"))
):
    """
    Register a custom health check
    
    This endpoint allows registering custom health checks dynamically.
    Note: In production, this would need proper validation and security.
    """
    return {
        "message": "Custom health check registration would be implemented here",
        "check_name": check_name,
        "note": "This is a placeholder for the actual implementation"
    }


@router.get("/history")
async def health_history(
    hours: int = Query(default=24, le=168, description="Hours of history to retrieve"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get health check history
    
    Returns historical health check data for trend analysis.
    Limited to last 7 days (168 hours).
    """
    # This would typically query a time-series database
    # For now, return a placeholder response
    return {
        "message": "Health history would be retrieved from time-series storage",
        "requested_hours": hours,
        "data_points": [],
        "summary": {
            "average_response_time_ms": 0,
            "uptime_percentage": 100,
            "total_checks": 0,
            "failed_checks": 0
        }
    }


# Export health router
health_router = router