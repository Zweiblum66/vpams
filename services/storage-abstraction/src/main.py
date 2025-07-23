"""
MAMS Storage Abstraction Service

Main application entry point for the Storage Abstraction Service.
Provides unified access to multiple storage backends.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.core.config import get_settings
from src.api import router
from src.services import get_storage_service, close_storage_service
from src.services.resume_upload_service import get_resume_service, close_resume_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting MAMS Storage Abstraction Service")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    try:
        # Initialize storage service
        storage_service = await get_storage_service()
        logger.info("Storage service initialized")
        
        # Initialize resume upload service
        resume_service = await get_resume_service()
        logger.info("Resume upload service initialized")
        
        # Log available drivers
        driver_info = await storage_service.get_driver_info()
        logger.info(f"Available storage drivers: {list(driver_info.keys())}")
        logger.info(f"Default driver: {storage_service._default_driver}")
        
    except Exception as e:
        logger.error(f"Failed to initialize Storage Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MAMS Storage Abstraction Service")
    
    try:
        await close_resume_service()
        logger.info("Resume upload service closed")
        
        await close_storage_service()
        logger.info("Storage service closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="MAMS Storage Abstraction Service",
    description="Unified storage interface supporting multiple backends",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Storage Abstraction Service",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        storage_service = await get_storage_service()
        driver_info = await storage_service.get_driver_info()
        
        # Check if at least one driver is healthy
        healthy_drivers = [
            name for name, info in driver_info.items()
            if info.get("initialized", False) and "error" not in info
        ]
        
        if not healthy_drivers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No healthy storage drivers"
            )
        
        return {
            "status": "healthy",
            "service": "storage-abstraction",
            "version": "1.0.0",
            "environment": settings.environment,
            "storage_drivers": {
                "total": len(driver_info),
                "healthy": len(healthy_drivers),
                "drivers": list(healthy_drivers)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        storage_service = await get_storage_service()
        
        if not storage_service._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
        
        # Test default driver
        default_driver = storage_service.get_driver()
        quota = await default_driver.get_quota()
        
        return {
            "status": "ready",
            "service": "storage-abstraction",
            "checks": {
                "storage_service": "initialized",
                "default_driver": storage_service._default_driver,
                "quota_check": "passed"
            }
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@app.get("/info")
async def service_info():
    """Service information endpoint"""
    storage_service = await get_storage_service()
    
    return {
        "service": "MAMS Storage Abstraction Service",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "drivers": list(settings.storage_drivers.keys()),
            "default_driver": settings.default_storage_driver,
            "chunked_upload": True,
            "multipart_upload": True,
            "presigned_urls": True,
            "storage_tiers": settings.enable_storage_tiers,
            "quotas": settings.enable_quotas,
            "encryption": settings.enable_encryption,
            "virus_scan": settings.enable_virus_scan
        },
        "limits": {
            "max_upload_size": settings.max_upload_size,
            "chunk_size": settings.chunk_size,
            "multipart_threshold": settings.multipart_threshold,
            "multipart_chunk_size": settings.multipart_chunk_size,
            "presigned_url_max_expiry": settings.max_presigned_url_expiry
        },
        "endpoints": {
            "health": "/health",
            "readiness": "/health/ready",
            "info": "/info",
            "api": "/api/v1/storage",
            "docs": "/docs" if settings.debug else None
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.debug else None
            }
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )