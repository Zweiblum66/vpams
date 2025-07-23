"""
Metadata Service - Main FastAPI Application
Handles flexible metadata schemas, extraction, and enrichment for MAMS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .api.routes import get_router
from .core.config import settings
from .db.database import init_db, close_db, health_check

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events
    """
    # Startup
    logger.info("Starting Metadata Service...")
    await init_db()
    logger.info("MongoDB connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Metadata Service...")
    await close_db()
    logger.info("MongoDB connection closed")


# Create FastAPI application
app = FastAPI(
    title="MAMS Metadata Service",
    description="Flexible metadata management with schema validation and enrichment",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(get_router())

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check_endpoint():
    """
    Check service health status
    """
    try:
        # Check MongoDB connection
        db_healthy = await health_check()
        
        if db_healthy:
            return {
                "status": "healthy",
                "service": "metadata-service",
                "version": "1.0.0",
                "database": "healthy"
            }
        else:
            return {
                "status": "unhealthy",
                "service": "metadata-service",
                "version": "1.0.0",
                "database": "unhealthy"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "metadata-service",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )