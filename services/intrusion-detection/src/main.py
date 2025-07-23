"""
MAMS Intrusion Detection Service

Comprehensive intrusion detection system providing network and host-based
security monitoring with machine learning-powered anomaly detection.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from contextlib import asynccontextmanager

from .api.routes import router
from .core.config import get_settings
from .core.exceptions import IDSException
from .db.base import init_db
from .services.detection_engine import DetectionEngine
from .services.database import DatabaseService


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize detection engine
    detection_engine = DetectionEngine()
    await detection_engine.initialize()
    app.state.detection_engine = detection_engine
    logger.info("Detection engine initialized")
    
    # Initialize database service
    db_service = DatabaseService()
    app.state.db_service = db_service
    logger.info("Database service initialized")
    
    logger.info("Intrusion Detection Service started", port=settings.service_port)
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'detection_engine'):
        await app.state.detection_engine.cleanup()
    logger.info("Intrusion Detection Service stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="MAMS Intrusion Detection Service",
        description="Comprehensive intrusion detection with network monitoring and anomaly detection",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "intrusion-detection",
            "version": "1.0.0"
        }
    
    @app.exception_handler(IDSException)
    async def ids_exception_handler(request: Request, exc: IDSException):
        """Handle IDS-specific exceptions."""
        logger.error("IDS exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error("Unexpected error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": str(exc) if settings.debug else None
                }
            }
        )
    
    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )