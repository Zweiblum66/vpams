"""
API Routes for Edge Cache Service

This module provides the HTTP endpoints for the edge cache service including
cache management, content delivery, and monitoring.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Response, HTTPException, Query, Header, Path
from fastapi.responses import StreamingResponse
import structlog
import time
from datetime import datetime

from ..core.cache_manager import CacheManager
from ..core.origin_client import OriginClient
from ..core.config import get_settings, get_cache_key


logger = structlog.get_logger()
router = APIRouter()

# Global instances (initialized in main.py)
cache_manager: Optional[CacheManager] = None
origin_client: Optional[OriginClient] = None


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "edge-cache",
        "timestamp": datetime.utcnow().isoformat(),
        "location": get_settings().edge_location
    }


@router.get("/api/v1/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
    
    stats = await cache_manager.get_stats()
    stats["location"] = get_settings().edge_location
    stats["region"] = get_settings().edge_region
    
    return stats


@router.delete("/api/v1/cache")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Key pattern to clear (e.g., 'asset:*')")
):
    """Clear cache entries"""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
    
    if pattern:
        count = await cache_manager.invalidate_pattern(pattern)
        return {"cleared": count, "pattern": pattern}
    else:
        count = await cache_manager.backend.clear()
        return {"cleared": count, "pattern": "*"}


@router.post("/api/v1/cache/invalidate")
async def invalidate_cache(
    request: Request
):
    """
    Invalidate cache entries based on invalidation rules
    
    Expected body:
    {
        "type": "asset|project|user",
        "id": "resource_id",
        "cascade": true/false
    }
    """
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
    
    body = await request.json()
    resource_type = body.get("type")
    resource_id = body.get("id")
    cascade = body.get("cascade", False)
    
    if not resource_type or not resource_id:
        raise HTTPException(status_code=400, detail="Missing type or id")
    
    patterns = []
    
    # Build invalidation patterns
    if resource_type == "asset":
        patterns.extend([
            f"*:asset:{resource_id}:*",
            f"*:metadata:{resource_id}",
            f"*:thumb:{resource_id}:*",
            f"*:proxy:{resource_id}:*"
        ])
    elif resource_type == "project":
        patterns.append(f"*:project:{resource_id}")
        if cascade:
            # Invalidate all assets in project
            patterns.append(f"*:asset:*:project_{resource_id}")
    elif resource_type == "user":
        patterns.append(f"*:user:{resource_id}")
    
    total_cleared = 0
    for pattern in patterns:
        count = await cache_manager.invalidate_pattern(pattern)
        total_cleared += count
    
    logger.info(
        "cache_invalidated",
        resource_type=resource_type,
        resource_id=resource_id,
        patterns=patterns,
        cleared=total_cleared
    )
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "patterns": patterns,
        "cleared": total_cleared
    }


@router.get("/api/v1/cache/keys")
async def list_cache_keys(
    pattern: str = Query("*", description="Key pattern to match"),
    limit: int = Query(100, ge=1, le=1000)
):
    """List cache keys matching pattern"""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
    
    keys = await cache_manager.backend.get_keys(pattern)
    
    return {
        "pattern": pattern,
        "total": len(keys),
        "keys": keys[:limit]
    }


@router.get("/{path:path}")
async def cached_proxy(
    request: Request,
    path: str = Path(..., description="Resource path"),
    # Cache control headers
    cache_control: Optional[str] = Header(None),
    if_none_match: Optional[str] = Header(None),
    if_modified_since: Optional[str] = Header(None),
    # Range request headers
    range_header: Optional[str] = Header(None, alias="range")
):
    """
    Main caching proxy endpoint
    
    Handles all GET requests, checking cache first and falling back to origin.
    """
    if not cache_manager or not origin_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    # Generate cache key
    cache_key = cache_manager.generate_cache_key(
        path,
        dict(request.headers)
    )
    
    # Check if client has cached version
    if if_none_match or if_modified_since:
        # Try to validate with origin
        is_valid, new_content, headers = await origin_client.validate_cached_content(
            path,
            etag=if_none_match,
            last_modified=if_modified_since
        )
        
        if is_valid:
            # Return 304 Not Modified
            return Response(
                status_code=304,
                headers={
                    "X-Edge-Cache": "VALIDATED",
                    "X-Edge-Location": get_settings().edge_location
                }
            )
    
    # Try cache first
    cached_data = await cache_manager.get(cache_key)
    
    if cached_data:
        content, headers = cached_data
        
        # Add cache headers
        headers.update({
            "X-Edge-Cache": "HIT",
            "X-Edge-Location": get_settings().edge_location,
            "X-Edge-Response-Time": f"{(time.time() - start_time) * 1000:.2f}ms"
        })
        
        # Handle range requests
        if range_header and get_settings().enable_range_requests:
            return _handle_range_request(content, headers, range_header)
        
        return Response(
            content=content,
            headers=headers,
            media_type=headers.get("content-type", "application/octet-stream")
        )
    
    # Cache miss - fetch from origin
    try:
        # Handle range requests to origin
        if range_header and get_settings().enable_range_requests:
            start, end = _parse_range_header(range_header)
            content, status_code, headers = await origin_client.fetch_range(
                path,
                start,
                end,
                headers=dict(request.headers)
            )
        else:
            content, status_code, headers = await origin_client.fetch(
                path,
                headers=dict(request.headers)
            )
        
        # Check if we should cache this response
        if origin_client.should_cache(status_code, headers):
            ttl = origin_client.calculate_ttl(headers, get_settings().cache_ttl_seconds)
            
            # Determine content type
            content_type = headers.get("content-type", "application/octet-stream")
            
            # Cache the response
            await cache_manager.set(
                cache_key,
                content,
                content_type,
                ttl=ttl,
                headers=headers
            )
        
        # Add cache headers
        headers.update({
            "X-Edge-Cache": "MISS",
            "X-Edge-Location": get_settings().edge_location,
            "X-Edge-Response-Time": f"{(time.time() - start_time) * 1000:.2f}ms"
        })
        
        return Response(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=headers.get("content-type", "application/octet-stream")
        )
        
    except Exception as e:
        logger.error(
            "proxy_error",
            path=path,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000
        )
        raise HTTPException(status_code=502, detail="Origin server error")


def _parse_range_header(range_header: str) -> tuple[int, Optional[int]]:
    """Parse Range header and return start, end positions"""
    try:
        # Format: "bytes=start-end"
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else None
        
        return start, end
    except:
        return 0, None


def _handle_range_request(
    content: bytes,
    headers: Dict[str, str],
    range_header: str
) -> Response:
    """Handle HTTP range requests"""
    start, end = _parse_range_header(range_header)
    
    if end is None:
        end = len(content) - 1
    
    # Ensure valid range
    start = max(0, start)
    end = min(end, len(content) - 1)
    
    if start > end:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{len(content)}"}
        )
    
    # Extract requested range
    range_content = content[start:end + 1]
    
    # Update headers
    headers.update({
        "Content-Range": f"bytes {start}-{end}/{len(content)}",
        "Content-Length": str(len(range_content))
    })
    
    return Response(
        content=range_content,
        status_code=206,
        headers=headers,
        media_type=headers.get("content-type", "application/octet-stream")
    )


@router.post("/api/v1/cache/prefetch")
async def prefetch_content(
    request: Request
):
    """
    Prefetch content into cache
    
    Expected body:
    {
        "urls": ["url1", "url2", ...],
        "priority": 5
    }
    """
    if not cache_manager or not origin_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    body = await request.json()
    urls = body.get("urls", [])
    priority = body.get("priority", 5)
    
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    results = []
    
    for url in urls[:100]:  # Limit to 100 URLs
        try:
            # Generate cache key
            cache_key = cache_manager.generate_cache_key(url, {})
            
            # Check if already cached
            if await cache_manager.backend.exists(cache_key):
                results.append({"url": url, "status": "already_cached"})
                continue
            
            # Prefetch from origin
            content = await origin_client.prefetch(url, priority)
            
            if content:
                # Cache it
                await cache_manager.set(
                    cache_key,
                    content,
                    "application/octet-stream",
                    priority=priority
                )
                results.append({"url": url, "status": "prefetched"})
            else:
                results.append({"url": url, "status": "failed"})
                
        except Exception as e:
            logger.error("prefetch_error", url=url, error=str(e))
            results.append({"url": url, "status": "error", "error": str(e)})
    
    return {
        "total": len(urls),
        "results": results
    }


@router.get("/api/v1/edge/locations")
async def get_edge_locations():
    """Get available edge locations"""
    from ..core.config import EDGE_LOCATIONS
    
    current_location = get_settings().edge_location
    current_region = get_settings().edge_region
    
    return {
        "current_location": current_location,
        "current_region": current_region,
        "regions": EDGE_LOCATIONS
    }


@router.get("/api/v1/edge/nearest/{user_location}")
async def get_nearest_edge(
    user_location: str = Path(..., description="User location code")
):
    """Get nearest edge location for a user location"""
    from ..core.config import get_nearest_edge_location
    
    nearest = get_nearest_edge_location(user_location)
    
    return {
        "user_location": user_location,
        "nearest_edge": nearest
    }