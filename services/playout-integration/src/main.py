"""Main FastAPI application for playout integration service"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import time
import uuid

from .core.config import settings
from .api.routes import router as api_router
from .db.base import create_tables, engine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Playout Integration Service")
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database initialization completed")
        
        # TODO: Initialize playout system adapters
        # TODO: Start background tasks for monitoring
        
        logger.info("Service startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Playout Integration Service")
        
        # Close database connections
        await engine.dispose()
        
        logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="MAMS Playout Integration Service",
    description="""
    Playout Integration Service for the Media Asset Management System (MAMS).
    
    This service provides integration with broadcast playout systems including:
    - Grass Valley
    - Harmonic MediaOS
    - Imagine Communications
    - Evertz
    - Pebble Beach Systems
    - PlayBox Technology
    - Aveco
    
    Features:
    - Multi-vendor playout system support
    - Schedule management and validation
    - Content delivery and transfer
    - Device monitoring and control
    - As-run log processing
    - Alert management
    """,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    # Generate request ID if not provided
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Log request
    start_time = time.time()
    logger.info(
        f"Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("User-Agent"),
        }
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}s"
            }
        )
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed",
            extra={
                "request_id": request_id,
                "error": str(e),
                "process_time": f"{process_time:.4f}s"
            }
        )
        raise


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
                "timestamp": time.time()
            }
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred" if not settings.debug else str(exc),
                "request_id": request_id,
                "timestamp": time.time()
            }
        },
        headers={"X-Request-ID": request_id}
    )


# Include API routes
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "playout-integration",
        "version": "1.0.0",
        "status": "running",
        "description": "MAMS Playout Integration Service",
        "docs_url": "/docs" if settings.debug else None,
        "health_url": "/api/v1/health"
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="MAMS Playout Integration Service",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Custom docs
if settings.debug:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui-bundle.min.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui.min.css",
        )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.service_host}:{settings.service_port}")
    
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )