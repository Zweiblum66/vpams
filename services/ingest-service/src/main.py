"""
Main FastAPI application for the Ingest Service
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.exceptions import IngestServiceError
from .api.routes import router as api_router
from .services.queue_service import QueueService, get_queue_service
from .services.watch_folder_service import WatchFolderService, get_watch_folder_service
from .services.hot_folder_service import HotFolderService, get_hot_folder_service
from .services.scheduler_service import SchedulerService, get_scheduler_service
from .services.ingest_service import IngestService, get_ingest_service


# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Ingest Service", version=settings.service_version)
    
    # Initialize services
    try:
        # Initialize queue service
        queue_service = await get_queue_service()
        app.state.queue_service = queue_service
        
        # Initialize ingest service
        ingest_service = await get_ingest_service()
        app.state.ingest_service = ingest_service
        
        # Initialize watch folder service
        watch_folder_service = await get_watch_folder_service()
        await watch_folder_service.initialize(ingest_service)
        app.state.watch_folder_service = watch_folder_service
        
        # Initialize hot folder service
        hot_folder_service = await get_hot_folder_service()
        await hot_folder_service.initialize(ingest_service)
        app.state.hot_folder_service = hot_folder_service
        
        # Initialize scheduler service if enabled
        if settings.enable_scheduled_ingest:
            scheduler_service = await get_scheduler_service()
            await scheduler_service.initialize(ingest_service)
            app.state.scheduler_service = scheduler_service
        
        logger.info("Ingest Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start Ingest Service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Ingest Service")
    
    try:
        # Stop queue service
        if hasattr(app.state, 'queue_service'):
            await app.state.queue_service.close()
        
        # Stop watch folder service
        if hasattr(app.state, 'watch_folder_service'):
            await app.state.watch_folder_service.stop_monitoring()
        
        # Stop hot folder service
        if hasattr(app.state, 'hot_folder_service'):
            await app.state.hot_folder_service.stop_monitoring()
        
        # Stop scheduler service
        if hasattr(app.state, 'scheduler_service'):
            await app.state.scheduler_service.shutdown()
        
        logger.info("Ingest Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MAMS Ingest Service",
    description="Advanced file ingestion service for the Media Asset Management System",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://*.mams.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IngestServiceError)
async def ingest_service_exception_handler(request: Request, exc: IngestServiceError):
    """Handle custom ingest service exceptions"""
    logger.error(
        "Ingest service error",
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
                "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
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
                "details": {} if not settings.debug else {"error": str(exc)},
                "timestamp": "2024-01-01T00:00:00Z",
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
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_config=None  # Use our custom logging configuration
    )