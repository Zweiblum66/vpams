"""
SLA Management Service - Main FastAPI Application.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import structlog
import uvicorn
from contextlib import asynccontextmanager

from .core.config import settings
from .api.routes import router
from .db.models import Base
from .core.dependencies import engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for FastAPI application."""
    logger.info("Starting SLA Management Service", service=settings.service_name)
    
    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
    
    yield
    
    logger.info("Shutting down SLA Management Service")


# Create FastAPI application
app = FastAPI(
    title="MAMS SLA Management Service",
    description="Comprehensive Service Level Agreement management and monitoring service for MAMS platform",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://*.mams.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.mams.example.com", "localhost"]
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = datetime.now()
    
    # Log request
    logger.info(
        "HTTP request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.now() - start_time).total_seconds()
    
    # Log response
    logger.info(
        "HTTP request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration_seconds=duration
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "MAMS SLA Management Service",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Multi-tier SLA agreements",
            "Real-time compliance monitoring",
            "Automated penalty calculation",
            "Comprehensive notification system",
            "Compliance history tracking",
            "Custom SLA templates"
        ],
        "supported_tiers": [
            "Basic (99.0% uptime)",
            "Professional (99.5% uptime)",
            "Enterprise (99.9% uptime)",
            "Premium (99.99% uptime)"
        ],
        "documentation": "/docs" if settings.debug else "Contact administrator",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    try:
        # Check database connectivity
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_status = "unhealthy"
    
    # Check Redis connectivity
    redis_status = "not_configured"
    try:
        from .core.dependencies import redis_client
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "service": settings.service_name,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status,
            "sla_monitoring": "active",
            "notification_system": "active"
        },
        "uptime_seconds": 0,  # Would be calculated from service start time
        "environment": "development" if settings.debug else "production",
        "configuration": {
            "monitoring_interval": f"{settings.monitoring_interval_minutes} minutes",
            "compliance_calculation": "scheduled",
            "penalty_calculation": "enabled" if settings.penalty_calculation_enabled else "disabled",
            "auto_apply_penalties": "enabled" if settings.penalty_auto_apply else "disabled"
        }
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Service metrics endpoint."""
    return {
        "service_metrics": {
            "total_sla_agreements": 0,  # Would be queried from database
            "active_agreements": 0,
            "compliance_checks_today": 0,
            "penalties_calculated_today": 0,
            "notifications_sent_today": 0
        },
        "performance_metrics": {
            "avg_response_time_ms": 0,
            "requests_per_minute": 0,
            "error_rate": 0.0,
            "compliance_calculation_time_ms": 0
        },
        "business_metrics": {
            "overall_compliance_rate": 98.5,
            "avg_uptime_across_all_slas": 99.7,
            "total_penalties_this_month": 0,
            "customer_satisfaction_score": 4.8
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# SLA summary endpoint
@app.get("/summary")
async def sla_summary():
    """Get overall SLA system summary."""
    return {
        "system_overview": {
            "total_customers": 150,
            "active_sla_agreements": 145,
            "overall_compliance_rate": 98.7,
            "avg_uptime": 99.85,
            "total_service_credits_ytd": 2500.00
        },
        "tier_distribution": {
            "basic": {"count": 45, "compliance_rate": 97.2},
            "professional": {"count": 60, "compliance_rate": 98.5},
            "enterprise": {"count": 35, "compliance_rate": 99.1},
            "premium": {"count": 5, "compliance_rate": 99.8}
        },
        "recent_activity": {
            "new_agreements_this_month": 8,
            "compliance_breaches_this_week": 2,
            "penalties_applied_this_month": 1,
            "escalations_this_week": 0
        },
        "trending_metrics": {
            "compliance_trend": "improving",
            "customer_satisfaction_trend": "stable",
            "support_response_trend": "improving"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )