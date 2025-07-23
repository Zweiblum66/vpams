"""
Sharding Middleware for Asset Management Service

This middleware handles shard routing, cross-shard query coordination,
and shard health monitoring.
"""

from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import time
import logging
from uuid import UUID

from ...db.sharding import get_shard_router, ShardedSession
from ...core.sharding_config import load_sharding_config

logger = logging.getLogger(__name__)


class ShardingMiddleware:
    """Middleware to handle sharding logic for requests"""
    
    def __init__(self, app):
        self.app = app
        self.config = load_sharding_config()
        self._shard_health: Dict[str, Dict[str, Any]] = {}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with sharding context"""
        
        # Skip middleware if sharding is disabled
        if not self.config.enabled:
            return await call_next(request)
        
        # Extract shard hints from request
        shard_hint = self._extract_shard_hint(request)
        if shard_hint:
            request.state.shard_hint = shard_hint
        
        # Add shard router to request state
        request.state.shard_router = await get_shard_router()
        
        # Track request timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add shard info to response headers
            if hasattr(request.state, "used_shards"):
                response.headers["X-Shard-Count"] = str(len(request.state.used_shards))
                response.headers["X-Shards-Used"] = ",".join(request.state.used_shards)
            
            # Track successful request
            duration = time.time() - start_time
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in sharding middleware: {str(e)}")
            raise
    
    def _extract_shard_hint(self, request: Request) -> Optional[str]:
        """Extract shard hint from request headers or query params"""
        
        # Check headers first
        shard_hint = request.headers.get("X-Shard-Hint")
        if shard_hint:
            return shard_hint
        
        # Check query parameters
        if "shard_hint" in request.query_params:
            return request.query_params["shard_hint"]
        
        # Try to extract from path parameters
        path_parts = request.url.path.split("/")
        
        # Look for common shard key patterns in path
        for i, part in enumerate(path_parts):
            if part == "projects" and i + 1 < len(path_parts):
                # Next part should be project ID
                try:
                    project_id = path_parts[i + 1]
                    UUID(project_id)  # Validate it's a UUID
                    return project_id
                except (ValueError, IndexError):
                    pass
            
            elif part == "assets" and i + 1 < len(path_parts):
                # For asset operations, we might need to look up the shard
                # This is handled by the repository layer
                pass
        
        return None


class ShardHealthCheckMiddleware:
    """Middleware to monitor shard health"""
    
    def __init__(self, app):
        self.app = app
        self.check_interval = 30  # seconds
        self.last_check = 0
        self.shard_status: Dict[str, Dict[str, Any]] = {}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Check shard health periodically"""
        
        current_time = time.time()
        
        # Perform health check if interval has passed
        if current_time - self.last_check > self.check_interval:
            await self._check_shard_health()
            self.last_check = current_time
        
        # Add health status to request
        request.state.shard_health = self.shard_status
        
        return await call_next(request)
    
    async def _check_shard_health(self):
        """Check health of all configured shards"""
        router = await get_shard_router()
        
        for shard_id, shard_config in router.shards.items():
            try:
                # Simple connectivity check
                engine = await shard_config.get_engine()
                async with engine.connect() as conn:
                    result = await conn.execute("SELECT 1")
                    await result.fetchone()
                
                self.shard_status[shard_id] = {
                    "status": "healthy",
                    "last_check": time.time(),
                    "response_time_ms": 0
                }
                
            except Exception as e:
                logger.error(f"Shard {shard_id} health check failed: {str(e)}")
                self.shard_status[shard_id] = {
                    "status": "unhealthy",
                    "last_check": time.time(),
                    "error": str(e)
                }


class CrossShardQueryMiddleware:
    """Middleware to handle cross-shard query coordination"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Coordinate cross-shard queries"""
        
        # Check if this is a search or aggregation query
        if self._is_cross_shard_query(request):
            request.state.cross_shard_query = True
            
            # Add query coordination headers
            if "X-Max-Shards" in request.headers:
                request.state.max_shards = int(request.headers["X-Max-Shards"])
            else:
                request.state.max_shards = None
            
            if "X-Query-Timeout" in request.headers:
                request.state.query_timeout = int(request.headers["X-Query-Timeout"])
            else:
                request.state.query_timeout = 30  # Default 30 seconds
        
        return await call_next(request)
    
    def _is_cross_shard_query(self, request: Request) -> bool:
        """Determine if request requires cross-shard coordination"""
        
        # Check for explicit header
        if request.headers.get("X-Cross-Shard-Query", "").lower() == "true":
            return True
        
        # Check for search endpoints
        path = request.url.path
        cross_shard_patterns = [
            "/search",
            "/analytics",
            "/reports",
            "/statistics"
        ]
        
        return any(pattern in path for pattern in cross_shard_patterns)


def create_shard_aware_response(
    data: Any,
    shard_info: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a response with shard information"""
    
    response_data = {
        "data": data
    }
    
    # Add metadata if provided
    if meta:
        response_data["meta"] = meta
    else:
        response_data["meta"] = {}
    
    # Add shard information
    if shard_info:
        response_data["meta"]["shard_info"] = shard_info
    
    return JSONResponse(content=response_data)


async def get_sharded_db(request: Request) -> ShardedSession:
    """Dependency to get sharded database session"""
    
    if not hasattr(request.state, "shard_router"):
        router = await get_shard_router()
    else:
        router = request.state.shard_router
    
    return ShardedSession(router)


# Exception handlers for sharding-specific errors
async def shard_not_available_handler(request: Request, exc: Exception):
    """Handle shard availability errors"""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "SHARD_UNAVAILABLE",
                "message": "The requested shard is temporarily unavailable",
                "details": {
                    "shard_hint": getattr(request.state, "shard_hint", None)
                }
            }
        }
    )


async def cross_shard_timeout_handler(request: Request, exc: Exception):
    """Handle cross-shard query timeouts"""
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": {
                "code": "CROSS_SHARD_TIMEOUT",
                "message": "Cross-shard query timed out",
                "details": {
                    "timeout_seconds": getattr(request.state, "query_timeout", 30)
                }
            }
        }
    )