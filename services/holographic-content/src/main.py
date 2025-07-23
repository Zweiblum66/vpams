"""
MAMS Holographic Content Service

Comprehensive holographic content management for next-generation immersive media.
Supports holographic capture, processing, display, and interactive experiences.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from .core.config import settings
from .api import routes
from .services.hologram_manager import HologramManager

# Configure structured logging
logger = structlog.get_logger()

# Service instances
hologram_manager: HologramManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global hologram_manager
    
    logger.info("Starting Holographic Content Service", port=settings.SERVICE_PORT)
    
    # Initialize services
    hologram_manager = HologramManager()
    await hologram_manager.initialize()
    
    # Store services in app state
    app.state.hologram_manager = hologram_manager
    
    yield
    
    # Cleanup
    logger.info("Shutting down Holographic Content Service")
    await hologram_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title="MAMS Holographic Content Service",
    description="Next-generation holographic content management for immersive media experiences",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.hologram_router, prefix="/api/v1/holographic", tags=["hologram"])
app.include_router(routes.capture_router, prefix="/api/v1/holographic/capture", tags=["capture"])
app.include_router(routes.processing_router, prefix="/api/v1/holographic/processing", tags=["processing"])
app.include_router(routes.display_router, prefix="/api/v1/holographic/display", tags=["display"])
app.include_router(routes.interaction_router, prefix="/api/v1/holographic/interaction", tags=["interaction"])
app.include_router(routes.streaming_router, prefix="/api/v1/holographic/streaming", tags=["streaming"])

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        health = await app.state.hologram_manager.health_check()
        return {
            "status": "healthy",
            "service": "holographic-content",
            "version": "1.0.0",
            "components": health
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Holographic Content Service",
        "version": "1.0.0",
        "status": "operational",
        "capabilities": [
            "volumetric_capture",
            "light_field_display",
            "holographic_projection",
            "real_time_rendering",
            "spatial_interaction",
            "neural_processing"
        ]
    }