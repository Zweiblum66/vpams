"""
Main entry point for failover service
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import structlog
import time

from .api.routes import router
from .core.config import settings
from .core.deps import get_failover_manager
from .db.base import init_db
from .utils.metrics import MetricsCollector

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
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting failover service", version=settings.SERVICE_VERSION)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize failover manager
    failover_manager = await get_failover_manager()
    logger.info("Failover manager initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down failover service")
    await failover_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title=f"{settings.SERVICE_NAME} API",
    version=settings.SERVICE_VERSION,
    description="Region failover management service for MAMS",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Request timing middleware
@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    """Add request timing headers"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request
    logger.info(
        "Request processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response


# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    failover_manager = await get_failover_manager()
    status = await failover_manager.get_failover_status()
    
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "active_region": status.active_region,
        "failover_state": status.current_state
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        failover_manager = await get_failover_manager()
        status = await failover_manager.get_failover_status()
        
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "active_region": status.active_region,
            "monitored_regions": len(failover_manager.regions)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.SERVICE_NAME,
                "error": str(e)
            }
        )


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found",
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "json": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "formatter": "json" if settings.LOG_FORMAT == "json" else "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                }
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["default"]
            }
        }
    )