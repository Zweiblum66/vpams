"""
Main FastAPI application for Integration Catalog Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
from datetime import datetime

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.exceptions import IntegrationError
from .db.base import init_db, engine
from .api import routes

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Integration Catalog Service", version=settings.service_version)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        logger.info("Integration Catalog Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start Integration Catalog Service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Integration Catalog Service")
    
    try:
        await engine.dispose()
        logger.info("Integration Catalog Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MAMS Integration Catalog Service",
    description="Integration catalog service for discovering and managing API integrations",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if not settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrationError)
async def integration_exception_handler(request: Request, exc: IntegrationError):
    """Handle integration exceptions"""
    logger.error(
        "Integration error",
        error_code=exc.error_code,
        error_message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        details=exc.details
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)} if settings.debug else {},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "path": str(request.url.path)
            }
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment
    }


# Include API routes
app.include_router(routes.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_config=None  # Use our custom logging configuration
    )