"""
Main application for geo-replication service
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from .api import routes
from .core.config import settings
from .services.replication_manager import GeoReplicationManager
from .db.base import init_db
from .utils.logging import setup_logging

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)

# Global replication manager instance
replication_manager: Optional[GeoReplicationManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global replication_manager
    
    logger.info("Starting geo-replication service", 
                service=settings.SERVICE_NAME,
                version=settings.SERVICE_VERSION,
                environment=settings.ENVIRONMENT)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize replication manager
        replication_manager = GeoReplicationManager()
        await replication_manager.initialize()
        logger.info("Replication manager initialized")
        
        # Store in app state for dependency injection
        app.state.replication_manager = replication_manager
        
        yield
        
    finally:
        # Cleanup
        logger.info("Shutting down geo-replication service")
        
        if replication_manager:
            await replication_manager.shutdown()
        
        logger.info("Geo-replication service stopped")


# Create FastAPI app
app = FastAPI(
    title="MAMS Geo-Replication Service",
    description="Manages cross-region data replication for MAMS",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.error("Validation error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error("Unexpected error", 
                error=str(exc), 
                error_type=type(exc).__name__,
                path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info("Request received",
                method=request.method,
                path=request.url.path,
                client=request.client.host if request.client else None)
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = asyncio.get_event_loop().time() - start_time
    
    # Log response
    logger.info("Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2))
    
    return response


# Include routers
app.include_router(routes.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "region": settings.CURRENT_REGION,
        "status": "operational"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "region": settings.CURRENT_REGION,
        "checks": {}
    }
    
    # Check replication manager
    if replication_manager and replication_manager._initialized:
        health_status["checks"]["replication_manager"] = "healthy"
        
        # Check region health
        region_health = {}
        for region_id, region_info in replication_manager.regions.items():
            region_health[region_id] = region_info.status
        
        health_status["checks"]["regions"] = region_health
    else:
        health_status["status"] = "unhealthy"
        health_status["checks"]["replication_manager"] = "not_initialized"
    
    return health_status


# Ready check endpoint
@app.get("/ready")
async def ready_check():
    """Readiness check endpoint"""
    if replication_manager and replication_manager._initialized:
        # Check if primary region is active
        primary_region = replication_manager.regions.get(settings.PRIMARY_REGION)
        if primary_region and primary_region.status == "active":
            return {"ready": True}
    
    return JSONResponse(
        status_code=503,
        content={"ready": False, "reason": "Service not ready"}
    )


# Metrics endpoint (Prometheus format)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.PROMETHEUS_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"detail": "Metrics not enabled"}
        )
    
    # In a real implementation, this would return Prometheus-formatted metrics
    metrics_data = []
    
    if replication_manager:
        # Add replication metrics
        metrics_data.append("# HELP replication_lag_seconds Replication lag in seconds")
        metrics_data.append("# TYPE replication_lag_seconds gauge")
        
        for region_id, region_info in replication_manager.regions.items():
            if not region_info.is_primary:
                lag = await replication_manager._get_replication_lag(
                    settings.PRIMARY_REGION, region_id
                )
                metrics_data.append(
                    f'replication_lag_seconds{{source="{settings.PRIMARY_REGION}",target="{region_id}"}} {lag}'
                )
    
    return "\n".join(metrics_data)


def run():
    """Run the application"""
    uvicorn.run(
        "src.main:app",
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


if __name__ == "__main__":
    run()