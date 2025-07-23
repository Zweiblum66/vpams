"""
MAMS Partner APIs Service

This service provides comprehensive API access for partners to integrate with the MAMS platform.
It includes API key management, rate limiting, usage analytics, and partner-specific API endpoints.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import logging
from pathlib import Path

from .core.config import settings
from .core.database import init_db
from .core.rate_limiter import RateLimitMiddleware
from .api.routes import router as api_router
from .api.webhooks import router as webhook_router
from .api.partner_v1 import router as partner_v1_router
from .api.partner_v2 import router as partner_v2_router
from .api.admin import router as admin_router


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
    logger.info("Starting Partner APIs Service...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Partner APIs Service...")


# Create FastAPI application
app = FastAPI(
    title="MAMS Partner APIs Service",
    description="Comprehensive API access for partners to integrate with the MAMS platform",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "API Keys",
            "description": "API key management and authentication"
        },
        {
            "name": "Partner API v1",
            "description": "Partner API version 1 endpoints"
        },
        {
            "name": "Partner API v2", 
            "description": "Partner API version 2 endpoints with enhanced features"
        },
        {
            "name": "Webhooks",
            "description": "Webhook management and delivery"
        },
        {
            "name": "Usage Analytics",
            "description": "API usage statistics and analytics"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints for API management"
        }
    ]
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/webhooks")
app.include_router(partner_v1_router, prefix="/partner/v1")
app.include_router(partner_v2_router, prefix="/partner/v2")
app.include_router(admin_router, prefix="/admin")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "partner-apis",
        "version": settings.service_version
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Partner APIs Service",
        "version": settings.service_version,
        "docs": "/docs" if settings.debug else None,
        "api_versions": {
            "v1": "/partner/v1",
            "v2": "/partner/v2"
        },
        "webhooks": "/webhooks",
        "management": "/api/v1"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )