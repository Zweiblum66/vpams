"""GDPR Compliance Service - Main Application"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from prometheus_client import make_asgi_app

from .core.config import settings
from .api import routes
from .db.base import init_db
from .utils.startup import (
    check_database_connection,
    check_mongodb_connection,
    check_redis_connection,
    check_storage_access,
    check_email_service
)

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    logger.info("Starting GDPR Compliance Service...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Run health checks
    health_status = {
        "postgresql": await check_database_connection(),
        "mongodb": await check_mongodb_connection(),
        "redis": await check_redis_connection(),
        "storage": await check_storage_access(),
        "email": await check_email_service()
    }
    
    for service, status in health_status.items():
        if not status:
            logger.warning(f"{service} health check failed")
    
    logger.info("GDPR Compliance Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down GDPR Compliance Service...")


# Create FastAPI app
app = FastAPI(
    title="GDPR Compliance Service",
    description="Service for managing GDPR compliance, data privacy, and user rights",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routes
app.include_router(routes.router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request.headers.get("X-Request-ID", "unknown")
            }
        }
    )

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Service health check"""
    health_status = {
        "status": "healthy",
        "service": "gdpr-compliance",
        "version": "1.0.0",
        "checks": {
            "database": await check_database_connection(),
            "mongodb": await check_mongodb_connection(),
            "redis": await check_redis_connection(),
            "storage": await check_storage_access(),
            "email": await check_email_service()
        }
    }
    
    # Determine overall health
    if not all(health_status["checks"].values()):
        health_status["status"] = "degraded"
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )