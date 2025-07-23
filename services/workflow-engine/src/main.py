"""
Workflow Engine Service

This service provides workflow automation and orchestration capabilities for the MAMS platform.
It enables users to create, manage, and execute automated workflows for media processing,
approval processes, and content distribution.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from prometheus_client import make_asgi_app, REGISTRY

from .core.config import settings
from .api import routes
from .api import designer_routes
from .api import approval_routes
from .api import approval_routing_routes
from .api import escalation_routes
from .api import approval_dashboard_routes
from .db.base import init_db
from .services.rabbitmq_service import rabbitmq_service

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    logger.info("Starting Workflow Engine Service", 
                version=settings.VERSION,
                environment=settings.ENVIRONMENT)
    
    # Initialize database
    await init_db()
    
    # Connect to RabbitMQ
    try:
        await rabbitmq_service.connect()
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.error("Failed to connect to RabbitMQ", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Workflow Engine Service")
    
    # Disconnect from RabbitMQ
    await rabbitmq_service.disconnect()


# Create FastAPI application
app = FastAPI(
    title="MAMS Workflow Engine Service",
    description="Workflow automation and orchestration for media asset management",
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
app.include_router(designer_routes.router, prefix="/api/v1")
app.include_router(approval_routes.router)
app.include_router(approval_routing_routes.router)
app.include_router(escalation_routes.router)
app.include_router(approval_dashboard_routes.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "workflow-engine",
        "version": settings.VERSION
    }

# Prometheus metrics endpoint
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app(REGISTRY)
    app.mount("/metrics", metrics_app)

# RabbitMQ queue status endpoint
@app.get("/api/v1/queue/status")
async def queue_status():
    """Get RabbitMQ queue statistics"""
    try:
        stats = await rabbitmq_service.get_queue_stats()
        return {
            "status": "ok",
            "data": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )