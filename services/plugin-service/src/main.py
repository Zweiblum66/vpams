"""
Main FastAPI application for Plugin Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
from datetime import datetime

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.exceptions import PluginError
from .core.plugin_manager import PluginManager
from .core.plugin_registry import PluginRegistry
from .db.base import init_db, engine
from .api import routes
from .api.dependencies import set_plugin_manager, set_plugin_registry

# Configure logging
configure_logging()
logger = get_logger(__name__)


# Global instances
plugin_manager: PluginManager = None
plugin_registry: PluginRegistry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Plugin Service", version=settings.service_version)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize plugin registry
        global plugin_registry
        plugin_registry = PluginRegistry(settings.plugin_registry_path)
        app.state.plugin_registry = plugin_registry
        set_plugin_registry(plugin_registry)
        
        # Initialize plugin manager
        global plugin_manager
        plugin_manager = PluginManager(settings.plugins_dir)
        await plugin_manager.initialize()
        app.state.plugin_manager = plugin_manager
        set_plugin_manager(plugin_manager)
        
        logger.info("Plugin Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start Plugin Service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Plugin Service")
    
    try:
        if plugin_manager:
            await plugin_manager.cleanup()
        
        await engine.dispose()
        
        logger.info("Plugin Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MAMS Plugin Service",
    description="Plugin management service for the Media Asset Management System",
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


@app.exception_handler(PluginError)
async def plugin_exception_handler(request: Request, exc: PluginError):
    """Handle plugin exceptions"""
    logger.error(
        "Plugin error",
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
    plugin_health = {}
    
    try:
        if plugin_manager:
            plugin_health = await plugin_manager.get_plugin_health_status()
    except Exception as e:
        logger.error("Failed to get plugin health", error=str(e))
    
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment,
        "plugins": {
            "total": len(plugin_health),
            "enabled": len([p for p in plugin_health.values() if p.get('enabled', False)]),
            "health": plugin_health
        }
    }


# Include API routes
app.include_router(routes.router, prefix="/api/v1")

# Include marketplace routes
from .api import marketplace_routes
app.include_router(marketplace_routes.router, prefix="/api/v1")

# Include revenue sharing routes
from .api import revenue_routes
app.include_router(revenue_routes.router, prefix="/api/v1")

# Include certification routes
from .api import certification_routes
app.include_router(certification_routes.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_config=None  # Use our custom logging configuration
    )