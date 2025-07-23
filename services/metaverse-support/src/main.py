"""MAMS Metaverse Support Service

Provides comprehensive metaverse integration capabilities including:
- Virtual world media asset deployment
- VR/AR content adaptation
- Spatial computing integration
- Avatar systems integration
- Blockchain-based virtual economies
- Cross-platform metaverse compatibility
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from .api import (
    virtual_world_routes,
    vr_routes,
    ar_routes,
    spatial_routes,
    avatar_routes,
    blockchain_routes,
    nft_routes,
    social_routes,
    cross_platform_routes
)
from .core.config import settings
from .core.logging import setup_logging
from .db.base import init_db, close_db
from .services.metaverse_manager import MetaverseManager
from .services.virtual_world_service import VirtualWorldService
from .services.avatar_service import AvatarService
from .services.spatial_service import SpatialService

# Prometheus metrics
REQUEST_COUNT = Counter(
    'mams_metaverse_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'mams_metaverse_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

# Setup logging
logger = setup_logging()

# Global services
metaverse_manager: MetaverseManager = None
virtual_world_service: VirtualWorldService = None
avatar_service: AvatarService = None
spatial_service: SpatialService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global metaverse_manager, virtual_world_service, avatar_service, spatial_service
    
    logger.info("Starting MAMS Metaverse Support Service")
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize services
        metaverse_manager = MetaverseManager()
        virtual_world_service = VirtualWorldService()
        avatar_service = AvatarService()
        spatial_service = SpatialService()
        
        # Initialize metaverse platforms
        await metaverse_manager.initialize()
        
        # Start background services
        await metaverse_manager.start_background_services()
        
        logger.info("Metaverse Support Service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize Metaverse Support Service: {e}")
        raise
    finally:
        # Cleanup
        if metaverse_manager:
            await metaverse_manager.shutdown()
        
        await close_db()
        logger.info("Metaverse Support Service stopped")

# Create FastAPI application
app = FastAPI(
    title="MAMS Metaverse Support Service",
    description="Comprehensive metaverse integration for digital media asset management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics"""
    method = request.method
    path = request.url.path
    
    # Start timer
    with REQUEST_DURATION.labels(method=method, endpoint=path).time():
        response = await call_next(request)
    
    # Count requests
    REQUEST_COUNT.labels(
        method=method,
        endpoint=path,
        status_code=response.status_code
    ).inc()
    
    return response

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        from .db.base import engine
        
        # Check service status
        services_status = {}
        
        if metaverse_manager:
            services_status["metaverse_manager"] = await metaverse_manager.health_check()
        
        if virtual_world_service:
            services_status["virtual_worlds"] = await virtual_world_service.health_check()
        
        if avatar_service:
            services_status["avatars"] = await avatar_service.health_check()
        
        if spatial_service:
            services_status["spatial_computing"] = await spatial_service.health_check()
        
        return {
            "status": "healthy",
            "service": "metaverse-support",
            "version": "1.0.0",
            "services": services_status,
            "platform_integrations": await get_platform_status() if metaverse_manager else {}
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "metaverse-support",
                "error": str(e)
            }
        )

@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# API Routes
app.include_router(
    virtual_world_routes.router,
    prefix="/api/v1/metaverse/worlds",
    tags=["virtual-worlds"]
)

app.include_router(
    vr_routes.router,
    prefix="/api/v1/metaverse/vr",
    tags=["virtual-reality"]
)

app.include_router(
    ar_routes.router,
    prefix="/api/v1/metaverse/ar",
    tags=["augmented-reality"]
)

app.include_router(
    spatial_routes.router,
    prefix="/api/v1/metaverse/spatial",
    tags=["spatial-computing"]
)

app.include_router(
    avatar_routes.router,
    prefix="/api/v1/metaverse/avatars",
    tags=["avatar-system"]
)

app.include_router(
    blockchain_routes.router,
    prefix="/api/v1/metaverse/blockchain",
    tags=["blockchain-integration"]
)

app.include_router(
    nft_routes.router,
    prefix="/api/v1/metaverse/nfts",
    tags=["nft-assets"]
)

app.include_router(
    social_routes.router,
    prefix="/api/v1/metaverse/social",
    tags=["social-features"]
)

app.include_router(
    cross_platform_routes.router,
    prefix="/api/v1/metaverse/cross-platform",
    tags=["cross-platform"]
)

# Helper functions
async def get_platform_status() -> Dict[str, Any]:
    """Get status of all connected metaverse platforms"""
    if not metaverse_manager:
        return {}
    
    return await metaverse_manager.get_all_platform_status()

# Service dependencies for dependency injection
def get_metaverse_manager() -> MetaverseManager:
    """Get metaverse manager instance"""
    if not metaverse_manager:
        raise HTTPException(status_code=503, detail="Metaverse manager not initialized")
    return metaverse_manager

def get_virtual_world_service() -> VirtualWorldService:
    """Get virtual world service instance"""
    if not virtual_world_service:
        raise HTTPException(status_code=503, detail="Virtual world service not initialized")
    return virtual_world_service

def get_avatar_service() -> AvatarService:
    """Get avatar service instance"""
    if not avatar_service:
        raise HTTPException(status_code=503, detail="Avatar service not initialized")
    return avatar_service

def get_spatial_service() -> SpatialService:
    """Get spatial service instance"""
    if not spatial_service:
        raise HTTPException(status_code=503, detail="Spatial service not initialized")
    return spatial_service

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_config=None  # We handle logging ourselves
    )