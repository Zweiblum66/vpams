"""
Rights Management Service - Main Application
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import init_db
from .core.logger import setup_logging, get_logger
from .api import routes
from .api import restriction_routes
from .api import geo_blocking_routes
from .api import blockchain_routes

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Rights Management Service...")
    
    # Initialize database
    await init_db()
    
    yield
    
    logger.info("Shutting down Rights Management Service...")


# Create FastAPI app
app = FastAPI(
    title="Rights Management Service",
    description="Comprehensive license tracking, compliance monitoring, and usage analytics for digital assets",
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

# Include routers
app.include_router(routes.router)
app.include_router(restriction_routes.router)
app.include_router(geo_blocking_routes.router)
app.include_router(blockchain_routes.router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint"""
    return {
        "service": "Rights Management Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rights-management",
        "version": "1.0.0"
    }


@app.get("/readiness", tags=["health"])
async def readiness_check():
    """Readiness check endpoint"""
    # In a real implementation, check database connectivity, etc.
    return {
        "status": "ready",
        "service": "rights-management",
        "checks": {
            "database": "connected",
            "cache": "available"
        }
    }


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "The requested resource was not found",
            "details": {
                "path": str(request.url.path)
            }
        }
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred",
            "details": {}
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )