"""
Main application entry point for Advanced AI Service
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
        "Starting Advanced AI Service",
        port=settings.SERVICE_PORT,
        environment=settings.ENVIRONMENT
    )
    
    # Initialize database
    await init_db()
    
    # Download models if needed
    logger.info("Loading AI models...")
    # Model loading would happen here
    
    yield
    
    # Cleanup
    logger.info("Shutting down Advanced AI Service")
    await cleanup_dependencies()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="MAMS Advanced AI Service",
    description="Predictive analytics, intelligent recommendations, and advanced ML capabilities",
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
        "service": "advanced-ai",
        "version": "1.0.0",
        "features": [
            "usage_prediction",
            "storage_optimization",
            "content_recommendations",
            "predictive_maintenance",
            "cost_optimization",
            "video_summarization",
            "auto_tagging",
            "content_clustering",
            "ai_search"
        ],
        "models": settings.USAGE_PREDICTION_MODELS
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