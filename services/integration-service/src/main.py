"""
MAMS Integration Service

This service provides integration capabilities with external systems including
webhooks, APIs, messaging platforms, and third-party services.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from .core.config import settings
from .core.integration_framework import IntegrationRegistry
from .api import integration_routes
from .api import webhook_routes
from .api import slack_routes
from .api import teams_routes
from .api import graphql_routes
from .api import zapier_routes
from .db.base import init_db

logger = structlog.get_logger()

# Global integration registry
integration_registry = IntegrationRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    logger.info("Starting Integration Service", 
                version=settings.VERSION,
                environment=settings.ENVIRONMENT)
    
    # Initialize database
    await init_db()
    
    # Initialize integrations from database
    # TODO: Load saved integrations
    
    yield
    
    # Shutdown
    logger.info("Shutting down Integration Service")
    await integration_registry.close_all()


# Create FastAPI application
app = FastAPI(
    title="MAMS Integration Service",
    description="External system integration and automation for MAMS platform",
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
app.include_router(integration_routes.router)
app.include_router(webhook_routes.router)
app.include_router(slack_routes.router)
app.include_router(teams_routes.router)
app.include_router(graphql_routes.router)
app.include_router(zapier_routes.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "integration-service",
        "version": settings.VERSION
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # TODO: Implement Prometheus metrics
    return "# Metrics endpoint"

async def start_grpc_server():
    """Start gRPC server if enabled"""
    if getattr(settings, "GRPC_ENABLED", False):
        from .grpc import serve
        grpc_port = getattr(settings, "GRPC_PORT", 50051)
        logger.info(f"Starting gRPC server on port {grpc_port}")
        asyncio.create_task(serve(grpc_port))


if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Optionally start gRPC server
    if getattr(settings, "GRPC_ENABLED", False):
        asyncio.run(start_grpc_server())
    
    # Start FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )