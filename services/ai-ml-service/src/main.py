"""
AI/ML Service - Main Application Entry Point

This service provides ML model serving infrastructure and AI-powered features
for the MAMS platform, including:
- Object detection for images
- Scene detection for videos
- Facial recognition
- Content moderation
- Speech-to-text processing
- Sentiment analysis
- Entity recognition
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from .core.config import settings
from .core.logging import setup_logging
from .api.routes import router as api_router
from .api.generative_routes import router as generative_router
from .db.base import init_db
from .services.model_manager import ModelManager
from .services.ml_service import MLService


# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan context manager."""
    logger.info("Starting AI/ML Service", version=settings.VERSION)
    
    # Initialize database
    await init_db()
    
    # Initialize model manager
    model_manager = ModelManager()
    await model_manager.initialize()
    
    # Initialize ML service
    ml_service = MLService(model_manager)
    await ml_service.initialize()
    
    # Store instances in app state
    app.state.model_manager = model_manager
    app.state.ml_service = ml_service
    
    logger.info("AI/ML Service initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down AI/ML Service")
    await ml_service.shutdown()
    await model_manager.shutdown()
    logger.info("AI/ML Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MAMS AI/ML Service",
    description="AI/ML model serving and processing service for Media Asset Management System",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        exc_info=True,
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    
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
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-ml-service",
        "version": settings.VERSION
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")
# Include Generative AI routes
if settings.ENABLE_GENERATIVE_AI:
    app.include_router(generative_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )