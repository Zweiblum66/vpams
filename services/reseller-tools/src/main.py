"""
MAMS Reseller Tools Service

This service provides comprehensive tools for partners to resell the MAMS platform,
including customer management, pricing configuration, billing integration, and analytics.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import logging
from pathlib import Path

from .core.config import settings
from .core.database import init_db
from .api.routes import router as api_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Reseller Tools Service...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Reseller Tools Service...")


# Create FastAPI application
app = FastAPI(
    title="MAMS Reseller Tools Service",
    description="Reseller management and sales tools for the Media Asset Management System",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "reseller-tools",
        "version": settings.service_version
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Reseller Tools Service",
        "version": settings.service_version,
        "docs": "/docs" if settings.debug else None
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )