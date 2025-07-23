"""Main application entry point for Broadcast Automation Service"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import structlog

from .core.config import settings
from .db import init_db, close_db
from .services import automation_service
from .api import (
    device_router,
    camera_router,
    switcher_router,
    audio_router,
    macro_router,
    show_router,
    control_router,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure standard logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(
        "Starting Broadcast Automation Service",
        service_name=settings.service_name,
        environment=settings.environment,
        host=settings.service_host,
        port=settings.service_port
    )
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize automation service
        await automation_service.initialize()
        logger.info("Automation service initialized")
        
        yield
        
    finally:
        # Shutdown automation service
        await automation_service.shutdown()
        logger.info("Automation service shutdown")
        
        # Close database
        await close_db()
        logger.info("Database connections closed")
        
        logger.info("Broadcast Automation Service stopped")


# Create FastAPI application
app = FastAPI(
    title="Broadcast Automation Service",
    description="Comprehensive broadcast automation for studio equipment control",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(device_router)
app.include_router(camera_router)
app.include_router(switcher_router)
app.include_router(audio_router)
app.include_router(macro_router)
app.include_router(show_router)
app.include_router(control_router)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Broadcast Automation Service",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        # This would typically check if DB is accessible
        
        # Check service health
        connected_devices = len(automation_service._device_adapters)
        active_macros = len(automation_service._active_macros)
        active_shows = len(automation_service._active_shows)
        
        return {
            "status": "healthy",
            "service": settings.service_name,
            "environment": settings.environment,
            "connected_devices": connected_devices,
            "active_macros": active_macros,
            "active_shows": active_shows,
            "emergency_override": automation_service._emergency_override
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "type": "ValueError"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "type": type(exc).__name__
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )