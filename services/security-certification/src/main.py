"""
Security Certification Service - Main FastAPI Application.
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
from .core.exceptions import SecurityCertificationError
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
    logger.info("Starting Security Certification Service", service=settings.service_name)
    
    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
    
    yield
    
    logger.info("Shutting down Security Certification Service")


# Create FastAPI application
app = FastAPI(
    title="MAMS Security Certification Service",
    description="Comprehensive security certification and compliance service for MAMS platform",
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
@app.exception_handler(SecurityCertificationError)
async def security_certification_exception_handler(request: Request, exc: SecurityCertificationError):
    """Handle security certification specific exceptions."""
    logger.error(
        "Security certification error",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


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
        "service": "MAMS Security Certification Service",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Comprehensive security audits",
            "Vulnerability assessments", 
            "Compliance checking",
            "Security certification",
            "Risk assessment",
            "Automated reporting"
        ],
        "supported_standards": [
            "ISO 27001",
            "SOC 2 Type II",
            "GDPR",
            "PCI DSS",
            "NIST Cybersecurity Framework"
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
    
    # Check Redis connectivity (if available)
    redis_status = "not_configured"
    try:
        from .core.dependencies import redis_client
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "service": settings.service_name,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status,
            "security_tools": "available"
        },
        "uptime_seconds": 0,  # Would be calculated from service start time
        "environment": "development" if settings.debug else "production"
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Service metrics endpoint."""
    return {
        "service_metrics": {
            "total_audits": 0,  # Would be queried from database
            "active_scans": 0,
            "compliance_checks_today": 0,
            "security_findings": 0
        },
        "performance_metrics": {
            "avg_response_time_ms": 0,
            "requests_per_minute": 0,
            "error_rate": 0.0
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