"""
Integration Service Main Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from .api import integrations, webhooks, graphql_api, grpc_api, export, marketplace
from .core.config import settings
from .core.exceptions import MAMSException
from .db.database import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MAMS Integration Service",
    description="API integration and export service for MAMS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handlers
@app.exception_handler(MAMSException)
async def mams_exception_handler(request: Request, exc: MAMSException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
    )

# Include routers
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(graphql_api.router, prefix="/api/v1")
app.include_router(grpc_api.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(marketplace.router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "integration-service",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Integration Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Starting MAMS Integration Service...")
    
    # Initialize database
    await init_db()
    
    logger.info("MAMS Integration Service started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down MAMS Integration Service...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )