"""
Onboarding Service - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.api import flows, steps, progress, tutorials, analytics
from src.core.config import settings
from src.core.logging import setup_logging
from src.db.base import init_db

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Onboarding Service...")
    
    # Initialize database
    await init_db()
    
    # Initialize sample data in development
    if settings.DEBUG:
        from src.services.sample_data import create_sample_flows
        await create_sample_flows()
    
    yield
    
    logger.info("Shutting down Onboarding Service...")


# Create FastAPI app
app = FastAPI(
    title="MAMS Onboarding Service API",
    description="User onboarding and guided setup for MAMS platform",
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

# Include routers
app.include_router(
    flows.router,
    prefix="/api/v1/onboarding/flows",
    tags=["Onboarding Flows"]
)

app.include_router(
    steps.router,
    prefix="/api/v1/onboarding/steps",
    tags=["Onboarding Steps"]
)

app.include_router(
    progress.router,
    prefix="/api/v1/onboarding/progress",
    tags=["Progress Tracking"]
)

app.include_router(
    tutorials.router,
    prefix="/api/v1/onboarding/tutorials",
    tags=["Tutorials"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/onboarding/analytics",
    tags=["Analytics"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Onboarding Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "onboarding",
        "version": "1.0.0"
    }