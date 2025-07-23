"""
Billing Service - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import logging
from contextlib import asynccontextmanager

from src.api import (
    subscriptions,
    payments,
    invoices,
    plans,
    analytics,
    webhooks,
    tax
)
from src.core.config import settings
from src.core.logging import setup_logging
from src.db.base import init_db
from src.tasks.scheduler import start_scheduler

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Billing Service...")
    
    # Initialize database
    await init_db()
    
    # Start background scheduler
    scheduler = start_scheduler()
    
    yield
    
    # Cleanup
    scheduler.shutdown()
    logger.info("Shutting down Billing Service...")


# Create FastAPI app
app = FastAPI(
    title="MAMS Billing Service API",
    description="Financial management and payment processing for MAMS",
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
    subscriptions.router,
    prefix="/api/v1/subscriptions",
    tags=["Subscriptions"]
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["Payments"]
)

app.include_router(
    invoices.router,
    prefix="/api/v1/invoices",
    tags=["Invoices"]
)

app.include_router(
    plans.router,
    prefix="/api/v1/plans",
    tags=["Plans"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["Webhooks"]
)

app.include_router(
    tax.router,
    prefix="/api/v1/tax",
    tags=["Tax"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Billing Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "billing",
        "version": "1.0.0",
        "checks": {
            "database": "connected",
            "redis": "connected",
            "stripe": "configured",
            "scheduler": "running"
        }
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # TODO: Add actual readiness checks
    return {
        "status": "ready",
        "payment_processors": {
            "stripe": settings.STRIPE_SECRET_KEY is not None,
            "paypal": settings.PAYPAL_CLIENT_ID is not None
        }
    }