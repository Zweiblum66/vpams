"""Main application for MOS Integration Service"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.config import settings
from .db.base import create_tables
from .api.routes import router
from .services.mos_server import MOSServer


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

# Global MOS server instance
mos_server: MOSServer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global mos_server
    
    logger.info("Starting MOS Integration Service", version=settings.service_version)
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created/verified")
        
        # Start MOS server
        mos_server = MOSServer()
        
        # Start MOS server in background task
        server_task = asyncio.create_task(mos_server.start())
        
        logger.info("MOS Integration Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down MOS Integration Service")
        
        if mos_server:
            await mos_server.stop()
        
        # Cancel server task
        if 'server_task' in locals():
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MOS Integration Service stopped")


# Create FastAPI application
app = FastAPI(
    title="MOS Integration Service",
    description="Media Object Server (MOS) Protocol Integration for MAMS",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": "2024-01-01T00:00:00Z"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "description": "Media Object Server (MOS) Protocol Integration",
        "docs_url": "/docs" if settings.debug else None,
        "mos_server": {
            "port": settings.mos_listen_port,
            "server_id": settings.mos_server_id,
            "status": "running" if mos_server and mos_server.is_running else "stopped"
        }
    }


# Server info endpoint
@app.get("/server-info")
async def server_info():
    """Get MOS server information"""
    if not mos_server:
        return {"status": "not_initialized"}
    
    return {
        "status": "running" if mos_server.is_running else "stopped",
        "active_connections": mos_server.get_connection_count(),
        "connection_info": mos_server.get_connection_info(),
        "configuration": {
            "listen_port": settings.mos_listen_port,
            "upper_port": settings.mos_upper_port,
            "query_port": settings.mos_query_port,
            "server_id": settings.mos_server_id,
            "heartbeat_interval": settings.mos_heartbeat_interval,
            "timeout": settings.mos_timeout,
            "max_concurrent_messages": settings.max_concurrent_messages
        }
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return {
        "error": "Internal server error",
        "message": "An unexpected error occurred",
        "path": request.url.path
    }


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    asyncio.create_task(shutdown())


async def shutdown():
    """Graceful shutdown"""
    global mos_server
    
    if mos_server:
        await mos_server.stop()


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8011,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )