"""
Edge Cache Service

Main entry point for the edge cache service that provides content caching
at edge locations for improved performance and reduced latency.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from prometheus_client import make_asgi_app
import uvicorn

from .core.config import get_settings
from .core.cache_manager import CacheManager
from .core.origin_client import OriginClient
from .api import routes


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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# Global instances
cache_manager: CacheManager = None
origin_client: OriginClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global cache_manager, origin_client
    
    settings = get_settings()
    
    # Initialize cache manager
    cache_manager = CacheManager(settings)
    await cache_manager.initialize()
    
    # Initialize origin client
    origin_client = OriginClient(settings)
    await origin_client.initialize()
    
    # Set instances in routes module
    routes.cache_manager = cache_manager
    routes.origin_client = origin_client
    
    logger.info(
        "edge_cache_started",
        location=settings.edge_location,
        region=settings.edge_region,
        backend=settings.storage_backend.value,
        cache_size_mb=settings.cache_size_mb
    )
    
    yield
    
    # Cleanup
    await cache_manager.shutdown()
    await origin_client.shutdown()
    
    logger.info("edge_cache_stopped")


# Create FastAPI app
app = FastAPI(
    title="MAMS Edge Cache Service",
    description="Edge caching service for media assets",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests"""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Add to request state
    request.state.request_id = request_id
    
    # Process request
    response = await call_next(request)
    
    # Add to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log response
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2)
    )
    
    return response


# Include routers
app.include_router(routes.router)


# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )