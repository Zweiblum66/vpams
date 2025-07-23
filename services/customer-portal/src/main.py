"""
Customer Portal Service - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import logging
from contextlib import asynccontextmanager

from src.api import (
    account,
    subscription,
    support,
    resources,
    analytics,
    billing
)
from src.core.config import settings
from src.core.logging import setup_logging
from src.db.base import init_db

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Customer Portal Service...")
    
    # Initialize database
    await init_db()
    
    yield
    
    logger.info("Shutting down Customer Portal Service...")


# Create FastAPI app
app = FastAPI(
    title="MAMS Customer Portal API",
    description="Self-service portal for MAMS customers",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add Prometheus metrics
if settings.ENABLE_METRICS:
    Instrumentator().instrument(app).expose(app)

# Include routers
app.include_router(
    account.router,
    prefix="/api/v1/account",
    tags=["Account Management"]
)

app.include_router(
    subscription.router,
    prefix="/api/v1/subscription",
    tags=["Subscription Management"]
)

app.include_router(
    support.router,
    prefix="/api/v1/support",
    tags=["Support"]
)

app.include_router(
    resources.router,
    prefix="/api/v1/resources",
    tags=["Resources"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)

app.include_router(
    billing.router,
    prefix="/api/v1/billing",
    tags=["Billing"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Customer Portal",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "customer-portal",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # TODO: Add actual readiness checks (DB connection, etc.)
    return {
        "status": "ready",
        "checks": {
            "database": "connected",
            "redis": "connected",
            "dependencies": "available"
        }
    }