"""
Search Engine Service

FastAPI service for handling search operations using OpenSearch.
Provides full-text search, metadata search, and advanced search capabilities.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.exceptions import SearchEngineError
from .api.routes import router as api_router
from .api.optimized_routes import router as optimized_router
from .api.optimized_routes import cleanup as optimization_cleanup
from .api.ai_search_routes import router as ai_search_router
from .db.opensearch import get_opensearch_client, initialize_indices
from .core.async_opensearch import get_opensearch_client as get_async_client, close_opensearch_client
from .services.ai_search_service import ai_search_service

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("search_engine_startup_begin")
    try:
        # Initialize OpenSearch connection and indices
        opensearch_client = await get_opensearch_client()
        await initialize_indices(opensearch_client)
        
        # Initialize async OpenSearch client for optimizations
        settings = get_settings()
        async_client = await get_async_client(settings)
        
        # Initialize AI search service
        await ai_search_service.initialize()
        
        logger.info("search_engine_startup_complete")
        yield
    except Exception as e:
        logger.error("search_engine_startup_failed", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("search_engine_shutdown")
        
        # Cleanup optimization resources
        await optimization_cleanup()
        await ai_search_service.shutdown()
        await close_opensearch_client()

app = FastAPI(
    title="MAMS Search Engine Service",
    description="Search engine service for the Digital Media Asset Management System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
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
@app.exception_handler(SearchEngineError)
async def search_engine_exception_handler(request: Request, exc: SearchEngineError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": exc.timestamp.isoformat(),
                "request_id": getattr(request.state, "request_id", None)
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
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": "",
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        opensearch_client = await get_opensearch_client()
        cluster_health = await opensearch_client.cluster.health()
        
        return {
            "status": "healthy",
            "service": "search-engine",
            "opensearch_status": cluster_health.get("status", "unknown"),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "search-engine",
                "error": str(e)
            }
        )

# Include API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(optimized_router)
app.include_router(ai_search_router)

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )