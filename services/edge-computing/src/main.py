"""
Main application entry point for Edge Computing Service
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog
import uvicorn

from .core.config import settings
from .core.deps import cleanup_dependencies
from .db.base import init_db, close_db
from .api.routes import router


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

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(
        "Starting Edge Computing Service",
        node_id=settings.NODE_ID,
        location=settings.NODE_LOCATION,
        is_master=settings.IS_MASTER_NODE
    )
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    logger.info("Shutting down Edge Computing Service")
    await cleanup_dependencies()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="MAMS Edge Computing Service",
    description="Distributed compute capabilities at edge locations for real-time processing",
    version="1.0.0",
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

# Add routes
app.include_router(router)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "edge-computing",
        "version": "1.0.0",
        "node_id": settings.NODE_ID,
        "location": settings.NODE_LOCATION,
        "type": settings.NODE_TYPE,
        "is_master": settings.IS_MASTER_NODE,
        "capabilities": settings.NODE_CAPABILITIES
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
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
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )