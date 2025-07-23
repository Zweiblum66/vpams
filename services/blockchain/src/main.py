"""
Main FastAPI application for Blockchain Service.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from .core.config import settings
from .api.routes import router as api_router
from .api.nft_routes import router as nft_router
from .api.smart_contract_routes import router as smart_contract_router
from .api.provenance_routes import router as provenance_router
from .api.crypto_payments_routes import router as crypto_payments_router
from .db.base import engine, init_db


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Blockchain Service...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Test blockchain connections
        from .services.blockchain_service import BlockchainService
        blockchain_service = BlockchainService()
        network_stats = await blockchain_service.get_network_stats()
        logger.info(f"Blockchain networks status: {network_stats}")
        
        # Test IPFS connection
        from .services.ipfs_service import IPFSService
        ipfs_service = IPFSService()
        ipfs_info = await ipfs_service.get_node_info()
        logger.info(f"IPFS node status: {ipfs_info.get('connected', False)}")
        
        logger.info("Blockchain Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Blockchain Service...")
    
    try:
        # Close database connections
        await engine.dispose()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Blockchain Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MAMS Blockchain Service",
    description="Distributed Ledger Technology (DLT) service for media rights management",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", extra={
        "path": request.url.path,
        "method": request.method,
        "client": request.client.host if request.client else None
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred",
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}", extra={
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
    )


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log incoming requests."""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info("Request received", extra={
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    })
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = asyncio.get_event_loop().time() - start_time
    
    # Log response
    logger.info("Request completed", extra={
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    })
    
    return response


# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["blockchain"])
app.include_router(nft_router, prefix="/api/v1/nft", tags=["nft"])
app.include_router(smart_contract_router, prefix="/api/v1/contracts", tags=["smart-contracts"])
app.include_router(provenance_router, tags=["provenance"])
app.include_router(crypto_payments_router, tags=["crypto-payments"])


# Root endpoint
@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "MAMS Blockchain Service",
        "version": settings.service_version,
        "description": "Distributed Ledger Technology (DLT) service for media rights management",
        "features": [
            "Media rights NFT minting",
            "License creation and management",
            "Rights ownership verification",
            "Royalty payments",
            "IPFS content storage",
            "Multi-blockchain support",
            "Smart contract deployment and management",
            "Comprehensive provenance tracking",
            "Asset authenticity verification",
            "Digital asset lineage tracing",
            "Cryptocurrency payment processing",
            "Subscription plan management",
            "Invoice creation and payment",
            "Escrow transaction support",
            "Multi-currency support"
        ],
        "supported_networks": settings.supported_networks,
        "default_network": settings.default_network,
        "status": "operational"
    }


# Health check endpoint
@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Comprehensive health check."""
    try:
        from .services.blockchain_service import BlockchainService
        from .services.ipfs_service import IPFSService
        
        # Check database
        from .db.base import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        db_status = "healthy"
        
        # Check blockchain networks
        blockchain_service = BlockchainService()
        network_stats = await blockchain_service.get_network_stats()
        connected_networks = [
            net for net, stats in network_stats.items() 
            if stats.get("connected", False)
        ]
        
        # Check IPFS
        ipfs_service = IPFSService()
        ipfs_info = await ipfs_service.get_node_info()
        ipfs_status = "healthy" if ipfs_info.get("connected", False) else "unhealthy"
        
        # Determine overall health
        overall_status = "healthy"
        if not connected_networks:
            overall_status = "degraded"
        if ipfs_status == "unhealthy":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "service": "blockchain-service",
            "version": settings.service_version,
            "components": {
                "database": db_status,
                "blockchain_networks": {
                    "connected": connected_networks,
                    "total": len(settings.supported_networks),
                    "status": "healthy" if connected_networks else "unhealthy"
                },
                "ipfs": ipfs_status
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "blockchain-service",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


# Metrics endpoint (if enabled)
if settings.enable_metrics:
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )