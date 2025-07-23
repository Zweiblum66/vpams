"""
MAMS API Gateway Service

Central entry point for all MAMS microservices providing:
- Authentication and authorization
- Request routing to downstream services
- Rate limiting and throttling
- Request/response logging
- API versioning
- Health checks
"""

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from src.core.config import get_settings
from src.core.exceptions import APIException
from src.core.logging import setup_logging
from src.core.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    RequestIDMiddleware
)
from src.core.enhanced_middleware import (
    CorrelationIDMiddleware,
    EnhancedLoggingMiddleware,
    AuditLoggingMiddleware,
    MetricsMiddleware
)
from src.core.versioning_middleware import (
    APIVersioningMiddleware,
    VersionValidationMiddleware,
    VersionMetricsMiddleware
)
from src.core.api_key_auth import APIKeyAuthMiddleware
from src.core.validation_middleware import (
    ValidationMiddleware,
    RequestSizeMiddleware
)
from src.core.security_headers import SecurityHeadersMiddleware
from src.core.ip_whitelist import IPWhitelistMiddleware
from src.core.openapi import setup_openapi_configuration
from src.api.routes import api_router
from src.api.health import health_router
from src.core.cors import setup_cors

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting MAMS API Gateway Service")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize services
    try:
        # Initialize Redis connection for rate limiting
        from core.redis import init_redis
        await init_redis()
        
        # Initialize service discovery
        from core.service_discovery import init_service_discovery
        await init_service_discovery()
        
        logger.info("API Gateway startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize API Gateway: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MAMS API Gateway Service")
    
    # Cleanup resources
    try:
        from core.redis import close_redis
        await close_redis()
        
        from core.service_discovery import cleanup_service_discovery
        await cleanup_service_discovery()
        
        logger.info("API Gateway shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title="MAMS API Gateway",
    description="Media Asset Management System - API Gateway Service",
    version="1.0.0",
    docs_url=None,  # Will be handled by custom OpenAPI setup
    redoc_url=None,  # Will be handled by custom OpenAPI setup
    openapi_url=None,  # Will be handled by custom OpenAPI setup
    lifespan=lifespan
)

# Security middleware
if settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

# CORS configuration - moved to after custom middleware setup

# Custom middleware (order matters!)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)  # Enhanced security headers
app.add_middleware(IPWhitelistMiddleware)  # IP-based access control
app.add_middleware(VersionMetricsMiddleware)
app.add_middleware(VersionValidationMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(EnhancedLoggingMiddleware)
app.add_middleware(LoggingMiddleware)  # Keep basic logging as fallback
app.add_middleware(ValidationMiddleware)  # Request validation and sanitization
app.add_middleware(RequestSizeMiddleware)  # Request size limiting
app.add_middleware(RateLimitMiddleware)
app.add_middleware(APIKeyAuthMiddleware)  # API key authentication
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(APIVersioningMiddleware)  # Must be after correlation ID

# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": time.time(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": time.time(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

# Setup CORS after all middleware
setup_cors(app)

# Setup OpenAPI documentation
setup_openapi_configuration(app)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(api_router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS API Gateway",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )