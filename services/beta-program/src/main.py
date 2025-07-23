"""
Beta Program Service

FastAPI service for managing beta testing program including user registration,
feature flags, feedback collection, and analytics.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import init_db
from .api import beta_users, features, feedback, analytics

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("beta_program_service_startup")
    await init_db()
    yield
    # Shutdown
    logger.info("beta_program_service_shutdown")

app = FastAPI(
    title="MAMS Beta Program Service",
    description="Beta testing program management for MAMS platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": request.url.path
            }
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "beta-program",
        "version": "1.0.0"
    }

# Include API routes
app.include_router(beta_users.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )