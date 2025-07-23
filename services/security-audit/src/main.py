"""
Main FastAPI application for Security Audit Service
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
import uvicorn

from .core.config import get_settings
from .services.database import init_database, create_tables, close_database
from .api.routes import audit_router, scan_router, compliance_router, health_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
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
    """Application lifespan management"""
    settings = get_settings()
    
    # Startup
    logger.info("Starting Security Audit Service", version="1.0.0")
    
    try:
        # Initialize database
        init_database()
        await create_tables()
        logger.info("Database initialized")
        
        # Start background tasks if needed
        # await start_background_tasks()
        
        logger.info("Security Audit Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Security Audit Service")
    
    try:
        # Stop background tasks
        # await stop_background_tasks()
        
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
    
    logger.info("Security Audit Service shut down complete")


# Create FastAPI application
app = FastAPI(
    title="Security Audit Service",
    description="Comprehensive security auditing and compliance checking service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Configure middleware
settings = get_settings()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Custom exception handler
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error("Value error", error=str(exc), path=request.url.path)
    raise HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    raise HTTPException(status_code=500, detail="Internal server error")


# Include routers
app.include_router(audit_router)
app.include_router(scan_router)
app.include_router(compliance_router)
app.include_router(health_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Security Audit Service",
        "version": "1.0.0",
        "description": "Comprehensive security auditing and compliance checking",
        "docs": "/docs",
        "health": "/health"
    }


# Development server
if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )