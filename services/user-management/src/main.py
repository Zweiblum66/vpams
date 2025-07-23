"""
MAMS User Management Service

Main application entry point for the User Management Service.
Provides user authentication, authorization, and profile management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn

from src.core.config import get_settings
from src.db.base import init_db, close_db, check_db_health
from src.db.migrations import seed_database, check_database_health
from src.api.routes import router, auth_router
from src.api.mfa_routes import router as mfa_router
from src.api.oauth2_routes import oauth2_router
from src.api.saml_routes import saml_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting MAMS User Management Service")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Check if database needs seeding
        if not await check_database_health():
            logger.info("Database appears empty, seeding with initial data...")
            await seed_database()
        
        logger.info("User Management Service startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize User Management Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MAMS User Management Service")
    
    try:
        await close_db()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="MAMS User Management Service",
    description="User authentication, authorization, and profile management service",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(router)
app.include_router(auth_router)
app.include_router(mfa_router)
app.include_router(oauth2_router)
app.include_router(saml_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS User Management Service",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connectivity
        db_healthy = await check_db_health()
        
        if not db_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unhealthy"
            )
        
        return {
            "status": "healthy",
            "service": "user-management",
            "version": "1.0.0",
            "environment": settings.environment,
            "database": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check database health
        db_healthy = await check_database_health()
        
        if not db_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
        
        return {
            "status": "ready",
            "service": "user-management",
            "checks": {
                "database": "healthy",
                "migrations": "complete"
            }
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@app.get("/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service": "MAMS User Management Service",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "authentication": "JWT + refresh tokens",
            "authorization": "RBAC with permissions",
            "external_auth": {
                "ldap": settings.enable_ldap,
                "oauth2": settings.enable_oauth2,
                "saml": settings.enable_saml
            },
            "mfa": "TOTP + backup codes",
            "password_policy": "Configurable",
            "session_management": "Redis-backed",
            "audit_logging": settings.enable_audit_log
        },
        "endpoints": {
            "health": "/health",
            "readiness": "/health/ready",
            "info": "/info",
            "docs": "/docs" if settings.debug else None
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.debug else None
            }
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )