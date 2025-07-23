"""
Main FastAPI application for the Proxy Generation Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.exceptions import ProxyGenerationError
from .api.routes import router as api_router
from .services.queue_service import QueueService, get_queue_service
from .services.ffmpeg_service import FFmpegService, get_ffmpeg_service
from .services.storage_service import StorageService, get_storage_service
from .services.proxy_processor import ProxyProcessor, get_proxy_processor

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Proxy Generation Service", version=settings.service_version)
    
    # Initialize services
    try:
        # Initialize queue service
        queue_service = await get_queue_service()
        app.state.queue_service = queue_service
        
        # Initialize FFmpeg service
        ffmpeg_service = await get_ffmpeg_service()
        app.state.ffmpeg_service = ffmpeg_service
        
        # Initialize storage service
        storage_service = await get_storage_service()
        app.state.storage_service = storage_service
        
        # Initialize proxy processor
        proxy_processor = await get_proxy_processor()
        app.state.proxy_processor = proxy_processor
        
        # Register job handlers
        queue_service.register_handler("video_proxy", proxy_processor.process_job)
        queue_service.register_handler("audio_proxy", proxy_processor.process_job)
        queue_service.register_handler("thumbnail", proxy_processor.process_job)
        queue_service.register_handler("contact_sheet", proxy_processor.process_job)
        queue_service.register_handler("waveform", proxy_processor.process_job)
        
        # Register 8K and Ultra HD job handlers
        queue_service.register_handler("8k_proxy", proxy_processor.process_job)
        queue_service.register_handler("8k_proxy_batch", proxy_processor.process_job)
        queue_service.register_handler("ultra_hd_analysis", proxy_processor.process_job)
        
        # Register HDR processing job handlers
        queue_service.register_handler("hdr_processing", proxy_processor.process_job)
        queue_service.register_handler("hdr_analysis", proxy_processor.process_job)
        queue_service.register_handler("hdr_to_sdr", proxy_processor.process_job)
        queue_service.register_handler("sdr_to_hdr", proxy_processor.process_job)
        queue_service.register_handler("hdr_delivery_optimization", proxy_processor.process_job)
        
        # Register spherical video job handlers
        queue_service.register_handler("spherical_analysis", proxy_processor.process_job)
        queue_service.register_handler("spherical_conversion", proxy_processor.process_job)
        queue_service.register_handler("vr_optimization", proxy_processor.process_job)
        queue_service.register_handler("spatial_metadata", proxy_processor.process_job)
        
        # Register VR content job handlers
        queue_service.register_handler("vr_content_analysis", proxy_processor.process_job)
        queue_service.register_handler("vr_content_processing", proxy_processor.process_job)
        queue_service.register_handler("vr_preview", proxy_processor.process_job)
        queue_service.register_handler("vr_motion_extraction", proxy_processor.process_job)
        queue_service.register_handler("vr_streaming_optimization", proxy_processor.process_job)
        queue_service.register_handler("vr_thumbnail_sequence", proxy_processor.process_job)
        
        # Register spatial audio job handlers
        queue_service.register_handler("spatial_audio_analysis", proxy_processor.process_job)
        queue_service.register_handler("spatial_audio_conversion", proxy_processor.process_job)
        queue_service.register_handler("ambisonic_encoding", proxy_processor.process_job)
        queue_service.register_handler("binaural_rendering", proxy_processor.process_job)
        queue_service.register_handler("room_acoustics", proxy_processor.process_job)
        queue_service.register_handler("spatial_mix", proxy_processor.process_job)
        
        # Register live streaming job handlers
        queue_service.register_handler("live_stream_start", proxy_processor.process_job)
        queue_service.register_handler("live_stream_stop", proxy_processor.process_job)
        queue_service.register_handler("adaptive_stream", proxy_processor.process_job)
        queue_service.register_handler("stream_overlay", proxy_processor.process_job)
        queue_service.register_handler("stream_recording", proxy_processor.process_job)
        
        # Register remote production job handlers
        queue_service.register_handler("remote_production_create", proxy_processor.process_job)
        queue_service.register_handler("remote_participant_add", proxy_processor.process_job)
        queue_service.register_handler("remote_source_add", proxy_processor.process_job)
        queue_service.register_handler("tally_update", proxy_processor.process_job)
        queue_service.register_handler("return_feed_config", proxy_processor.process_job)
        
        # Register cloud switching job handlers
        queue_service.register_handler("cloud_switching_create", proxy_processor.process_job)
        queue_service.register_handler("switching_input_add", proxy_processor.process_job)
        queue_service.register_handler("switching_switch", proxy_processor.process_job)
        queue_service.register_handler("switching_output_config", proxy_processor.process_job)
        queue_service.register_handler("switching_macro_create", proxy_processor.process_job)
        
        # Register virtual studio job handlers
        queue_service.register_handler("virtual_studio_create", proxy_processor.process_job)
        queue_service.register_handler("virtual_studio_chroma_config", proxy_processor.process_job)
        queue_service.register_handler("virtual_studio_set_load", proxy_processor.process_job)
        queue_service.register_handler("virtual_studio_ar_add", proxy_processor.process_job)
        queue_service.register_handler("virtual_studio_tracking_update", proxy_processor.process_job)
        
        # Register live graphics job handlers
        queue_service.register_handler("live_graphics_create", proxy_processor.process_job)
        queue_service.register_handler("live_graphics_template_load", proxy_processor.process_job)
        queue_service.register_handler("live_graphics_show", proxy_processor.process_job)
        queue_service.register_handler("live_graphics_data_update", proxy_processor.process_job)
        queue_service.register_handler("live_graphics_playlist_create", proxy_processor.process_job)
        
        # Start queue consumer in background
        app.state.consumer_task = asyncio.create_task(queue_service.start_consumer())
        
        logger.info("Proxy Generation Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start Proxy Generation Service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Proxy Generation Service")
    
    try:
        # Stop queue consumer
        if hasattr(app.state, 'consumer_task'):
            app.state.consumer_task.cancel()
            try:
                await app.state.consumer_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(app.state, 'queue_service'):
            await app.state.queue_service.stop_consumer()
            await app.state.queue_service.close()
        
        # Cleanup processor
        if hasattr(app.state, 'proxy_processor'):
            await app.state.proxy_processor.cleanup()
        
        # Close storage service
        if hasattr(app.state, 'storage_service'):
            await app.state.storage_service.close()
        
        logger.info("Proxy Generation Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MAMS Proxy Generation Service",
    description="Media proxy generation service for the Media Asset Management System",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://*.mams.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ProxyGenerationError)
async def proxy_generation_exception_handler(request: Request, exc: ProxyGenerationError):
    """Handle custom proxy generation exceptions"""
    logger.error(
        "Proxy generation error",
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
                "details": {} if not settings.debug else {"error": str(exc)},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "path": str(request.url.path)
            }
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_config=None  # Use our custom logging configuration
    )