"""Main application for Broadcast Integration Service"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.config import settings
from .db.base import create_tables
from .api.routes import router


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Set up logging
logging.basicConfig(
    format="%(message)s",
    level=getattr(logging, settings.log_level),
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Broadcast Integration Service", version=settings.service_version)
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created/verified")
        
        # TODO: Initialize newsroom connections
        # TODO: Initialize automation systems
        # TODO: Start WebSocket server for real-time updates
        
        logger.info("Broadcast Integration Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Broadcast Integration Service")
        
        # TODO: Close newsroom connections
        # TODO: Disconnect automation systems
        # TODO: Stop WebSocket server
        
        logger.info("Broadcast Integration Service stopped")


# Create FastAPI application
app = FastAPI(
    title="Broadcast Integration Service",
    description="Advanced newsroom and broadcast production integration for MAMS",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Broadcast Integration Service",
        "version": settings.service_version,
        "status": "operational",
        "endpoints": {
            "api": "/api/v1/broadcast",
            "health": "/api/v1/broadcast/health",
            "docs": "/docs" if settings.debug else None,
            "openapi": "/openapi.json" if settings.debug else None
        }
    }


# Health check at root level
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "broadcast-integration",
        "version": settings.service_version,
        "features": {
            "rundown_management": True,
            "script_engine": True,
            "graphics_control": True,
            "live_production": True,
            "automation": settings.automation_enabled,
            "templates": settings.feature_templates,
            "approval_workflow": settings.feature_approval_workflow
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )