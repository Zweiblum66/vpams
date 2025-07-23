"""
Main application entry point for Disaster Recovery Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
from contextlib import asynccontextmanager

from .api import routes
from .core.config import settings
from .core.logging import get_logger
from .core.database import init_db
from .services.disaster_recovery_service import DisasterRecoveryService

logger = get_logger(__name__)

# Initialize services
dr_service = DisasterRecoveryService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Disaster Recovery Service...")
    
    # Initialize database
    await init_db()
    
    # Initialize disaster recovery service
    await dr_service.initialize()
    
    logger.info("Disaster Recovery Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Disaster Recovery Service...")
    
    # Cleanup tasks
    for task in dr_service.monitoring_tasks:
        task.cancel()
    
    logger.info("Disaster Recovery Service stopped")


# Create FastAPI app
app = FastAPI(
    title="MAMS Disaster Recovery Service",
    description="Comprehensive disaster recovery and business continuity service for MAMS platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Include routers
app.include_router(routes.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": type(exc).__name__,
                "request_id": request.headers.get("X-Request-ID")
            }
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check service components
        redis_healthy = await dr_service.redis_client.ping() if dr_service.redis_client else False
        
        # Calculate monitoring task health
        active_tasks = sum(1 for task in dr_service.monitoring_tasks if not task.done())
        total_tasks = len(dr_service.monitoring_tasks)
        
        health_status = {
            "status": "healthy" if redis_healthy else "degraded",
            "service": "disaster-recovery",
            "version": "1.0.0",
            "components": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "monitoring_tasks": f"{active_tasks}/{total_tasks} active",
                "recovery_operations": "ready" if not dr_service.recovery_in_progress else "busy"
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "disaster-recovery",
            "error": str(e)
        }


# Service info endpoint
@app.get("/info")
async def service_info():
    """Get service information"""
    return {
        "service": "disaster-recovery",
        "version": "1.0.0",
        "description": "Disaster Recovery and Business Continuity Service",
        "capabilities": [
            "disaster_recovery_planning",
            "automated_backup_management",
            "failover_orchestration",
            "recovery_testing",
            "business_continuity_planning",
            "real_time_monitoring",
            "recovery_runbooks",
            "compliance_tracking"
        ],
        "supported_disaster_types": [
            "hardware_failure",
            "software_failure",
            "network_outage",
            "data_corruption",
            "cyber_attack",
            "natural_disaster",
            "power_outage",
            "human_error",
            "provider_outage",
            "complete_datacenter_loss"
        ],
        "recovery_tiers": {
            "critical": {"rto": "< 1 hour", "rpo": "< 15 minutes"},
            "high": {"rto": "< 4 hours", "rpo": "< 1 hour"},
            "medium": {"rto": "< 24 hours", "rpo": "< 4 hours"},
            "low": {"rto": "< 72 hours", "rpo": "< 24 hours"}
        }
    }


# Metrics endpoint
@app.get("/metrics/summary")
async def metrics_summary():
    """Get service metrics summary"""
    try:
        # Get cached metrics
        metrics = {
            "active_plans": await dr_service.redis_client.get("dr:metrics:active_plans") or 0,
            "total_backups_24h": await dr_service.redis_client.get("dr:metrics:backups_24h") or 0,
            "successful_backups_24h": await dr_service.redis_client.get("dr:metrics:successful_backups_24h") or 0,
            "active_incidents": await dr_service.redis_client.get("dr:metrics:active_incidents") or 0,
            "recovery_tests_this_month": await dr_service.redis_client.get("dr:metrics:tests_month") or 0,
            "average_readiness_score": await dr_service.redis_client.get("dr:metrics:avg_readiness") or 0.0
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        return {
            "error": "Failed to retrieve metrics",
            "message": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["default"],
            },
        }
    )