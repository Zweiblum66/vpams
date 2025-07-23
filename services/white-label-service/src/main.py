"""
Main application for White-Label Service

This service provides comprehensive white-label customization capabilities
for partners to brand and configure the MAMS platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .db.base import init_db
from .api.routes import router

# Configure logging
configure_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting White-Label Service")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down White-Label Service")

# Create FastAPI application
app = FastAPI(
    title="MAMS White-Label Service",
    description="White-label customization service for the Media Asset Management System",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# Include routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS White-Label Service",
        "version": settings.service_version,
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "white-label-service",
        "version": settings.service_version
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )