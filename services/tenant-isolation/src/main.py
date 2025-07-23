"""
MAMS Tenant Isolation Service

Provides comprehensive tenant isolation mechanisms including database,
storage, network, and application-level isolation.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from contextlib import asynccontextmanager

from .api.routes import router
from .core.config import get_settings
from .core.exceptions import TenantIsolationException
from .db.base import init_db
from .services.isolation_manager import IsolationManager
from .services.database import DatabaseService


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize isolation manager
    isolation_manager = IsolationManager()
    await isolation_manager.initialize()
    app.state.isolation_manager = isolation_manager
    logger.info("Isolation manager initialized")
    
    # Initialize database service
    db_service = DatabaseService()
    app.state.db_service = db_service
    logger.info("Database service initialized")
    
    logger.info("Tenant Isolation Service started", port=settings.service_port)
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'isolation_manager'):
        await app.state.isolation_manager.cleanup()
    logger.info("Tenant Isolation Service stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="MAMS Tenant Isolation Service",
        description="Comprehensive tenant isolation for data, storage, and network security",
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
            "service": "tenant-isolation",
            "version": "1.0.0"
        }
    
    @app.exception_handler(TenantIsolationException)
    async def tenant_isolation_exception_handler(request: Request, exc: TenantIsolationException):
        """Handle tenant isolation specific exceptions."""
        logger.error("Tenant isolation exception", error=str(exc), path=request.url.path)
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