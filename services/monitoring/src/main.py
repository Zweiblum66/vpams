"""
MAMS Monitoring Service

This service provides centralized monitoring, metrics collection, and observability
for the entire MAMS platform. It exposes Prometheus metrics, health checks,
and system-wide monitoring capabilities.
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from prometheus_client import generate_latest

from .core.config import settings
from .core.metrics import (
    REGISTRY, MetricsCollector, service_health, service_uptime,
    users_total, projects_total, assets_total, asset_storage_bytes,
    processing_queue_size, workflow_active_instances,
    db_connections_active, cache_size_bytes, active_sessions
)
from .api import routes
from .db.base import init_db

logger = structlog.get_logger()

# Initialize metrics collector
metrics_collector = MetricsCollector(
    service_name="monitoring",
    version=settings.VERSION,
    environment=settings.ENVIRONMENT
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    logger.info("Starting Monitoring Service", 
                version=settings.VERSION,
                environment=settings.ENVIRONMENT)
    
    # Initialize database
    await init_db()
    
    # Set initial service health
    metrics_collector.update_service_health(True)
    
    # Start background tasks for metrics collection
    # TODO: Add background tasks for collecting system-wide metrics
    
    yield
    
    # Shutdown
    logger.info("Shutting down Monitoring Service")
    metrics_collector.update_service_health(False)


# Create FastAPI application
app = FastAPI(
    title="MAMS Monitoring Service",
    description="Centralized monitoring and observability for MAMS platform",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api/v1")


# Prometheus metrics endpoint
@app.get("/metrics", response_class=Response)
async def metrics():
    """
    Expose Prometheus metrics
    
    This endpoint returns all collected metrics in Prometheus text format.
    Prometheus server will scrape this endpoint periodically.
    """
    metrics_collector.update_uptime()
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "monitoring",
        "version": settings.VERSION,
        "metrics_endpoint": "/metrics"
    }


# Service info endpoint
@app.get("/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service": "monitoring",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "features": [
            "prometheus_metrics",
            "health_monitoring",
            "system_metrics",
            "service_discovery",
            "alerting_rules"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )