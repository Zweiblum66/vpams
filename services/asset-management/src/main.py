"""
Asset Management Service - Main Application

This is the entry point for the Asset Management microservice.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import make_asgi_app
import structlog
import uvicorn

from .api import router
from .core.config import get_settings
from .core.logging import setup_logging
from .core.sharding_config import load_sharding_config
from .db.base import engine
from .db.sharding import get_shard_router
from .api.middleware.sharding import (
    ShardingMiddleware, 
    ShardHealthCheckMiddleware,
    CrossShardQueryMiddleware
)

# Configure structured logging
setup_logging()
logger = structlog.get_logger()

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    logger.info(
        "service_starting",
        service="asset-management",
        version="1.0.0",
        environment=settings.environment
    )
    
    # Initialize sharding if enabled
    sharding_config = load_sharding_config()
    if sharding_config.enabled:
        logger.info(
            "initializing_sharding",
            strategy=sharding_config.strategy,
            shard_key=sharding_config.shard_key,
            shard_count=len(sharding_config.shards)
        )
        # Pre-initialize shard router
        await get_shard_router()
    
    yield
    
    # Shutdown
    logger.info("service_stopping")
    await engine.dispose()
    
    # Close shard connections
    if sharding_config.enabled:
        router = await get_shard_router()
        for shard in router.shards.values():
            await shard.close()


# Create FastAPI app
app = FastAPI(
    title="Asset Management Service",
    description="Microservice for managing digital media assets",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add sharding middlewares if enabled
sharding_config = load_sharding_config()
if sharding_config.enabled:
    app.add_middleware(CrossShardQueryMiddleware)
    app.add_middleware(ShardHealthCheckMiddleware)
    app.add_middleware(ShardingMiddleware)

# Include routers
app.include_router(router)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "service": "asset-management",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )