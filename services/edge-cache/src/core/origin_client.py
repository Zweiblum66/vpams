"""
Origin Client for Edge Cache Service

This module handles communication with the origin server to fetch content
when it's not available in the cache.
"""

from typing import Dict, Optional, Tuple, Any
import httpx
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_retry,
    after_retry
)
import structlog
from datetime import datetime
import time

from .config import Settings


logger = structlog.get_logger()


class OriginError(Exception):
    """Origin server error"""
    pass


class OriginClient:
    """Client for fetching content from origin server"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    
    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            base_url=self.settings.origin_url,
            timeout=httpx.Timeout(
                connect=10.0,
                read=self.settings.origin_timeout,
                write=30.0,
                pool=5.0
            ),
            limits=httpx.Limits(
                max_connections=self.settings.max_concurrent_requests,
                max_keepalive_connections=20,
                keepalive_expiry=self.settings.keepalive_timeout
            ),
            follow_redirects=True
        )
    
    async def shutdown(self):
        """Shutdown HTTP client"""
        if self.client:
            await self.client.aclose()
    
    def _log_before_retry(self, retry_state):
        """Log before retry attempt"""
        logger.warning(
            "origin_request_retry",
            attempt=retry_state.attempt_number,
            wait_time=retry_state.next_action.sleep if retry_state.next_action else 0
        )
    
    def _log_after_retry(self, retry_state):
        """Log after retry attempt"""
        if retry_state.outcome.failed:
            logger.error(
                "origin_request_failed",
                attempt=retry_state.attempt_number,
                exception=str(retry_state.outcome.exception())
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, OriginError)),
        before=_log_before_retry,
        after=_log_after_retry
    )
    async def fetch(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Tuple[bytes, int, Dict[str, str]]:
        """
        Fetch content from origin server
        
        Returns:
            Tuple of (content, status_code, headers)
        """
        async with self._semaphore:
            start_time = time.time()
            
            try:
                # Prepare headers
                request_headers = headers or {}
                
                # Add edge cache headers
                request_headers.update({
                    "X-Edge-Location": self.settings.edge_location,
                    "X-Edge-Region": self.settings.edge_region,
                    "X-Edge-Request-ID": self._generate_request_id()
                })
                
                # Make request
                response = await self.client.get(
                    path,
                    headers=request_headers,
                    params=params
                )
                
                # Check response
                if response.status_code >= 500:
                    raise OriginError(f"Origin server error: {response.status_code}")
                
                if response.status_code == 404:
                    # Don't retry 404s
                    return b"", 404, dict(response.headers)
                
                response.raise_for_status()
                
                # Log successful fetch
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "origin_fetch_success",
                    path=path,
                    status=response.status_code,
                    size=len(response.content),
                    duration_ms=round(duration_ms, 2)
                )
                
                return response.content, response.status_code, dict(response.headers)
                
            except httpx.HTTPError as e:
                logger.error(
                    "origin_fetch_error",
                    path=path,
                    error=str(e),
                    duration_ms=round((time.time() - start_time) * 1000, 2)
                )
                raise
    
    async def fetch_range(
        self,
        path: str,
        start: int,
        end: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bytes, int, Dict[str, str]]:
        """
        Fetch partial content from origin using range requests
        
        Args:
            path: Resource path
            start: Start byte position
            end: End byte position (optional)
            headers: Additional headers
            
        Returns:
            Tuple of (content, status_code, headers)
        """
        request_headers = headers or {}
        
        # Add range header
        if end is not None:
            request_headers["Range"] = f"bytes={start}-{end}"
        else:
            request_headers["Range"] = f"bytes={start}-"
        
        return await self.fetch(path, headers=request_headers)
    
    async def head(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Dict[str, str]]:
        """
        Send HEAD request to origin
        
        Returns:
            Tuple of (status_code, headers)
        """
        async with self._semaphore:
            try:
                response = await self.client.head(
                    path,
                    headers=headers or {}
                )
                
                return response.status_code, dict(response.headers)
                
            except httpx.HTTPError as e:
                logger.error("origin_head_error", path=path, error=str(e))
                raise
    
    async def validate_cached_content(
        self,
        path: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None
    ) -> Tuple[bool, Optional[bytes], Dict[str, str]]:
        """
        Validate cached content with origin using conditional requests
        
        Args:
            path: Resource path
            etag: Cached ETag
            last_modified: Cached Last-Modified date
            
        Returns:
            Tuple of (is_valid, new_content, headers)
            - is_valid: True if cached content is still valid
            - new_content: New content if cache is stale, None if valid
            - headers: Response headers
        """
        headers = {}
        
        if etag:
            headers["If-None-Match"] = etag
        
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        
        if not headers:
            # No validation headers, must fetch
            content, status, resp_headers = await self.fetch(path)
            return False, content, resp_headers
        
        try:
            content, status, resp_headers = await self.fetch(path, headers=headers)
            
            if status == 304:
                # Not Modified - cache is valid
                return True, None, resp_headers
            else:
                # Content has changed
                return False, content, resp_headers
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 304:
                return True, None, dict(e.response.headers)
            raise
    
    async def prefetch(
        self,
        path: str,
        priority: int = 5
    ) -> Optional[bytes]:
        """
        Prefetch content from origin (low priority)
        
        Args:
            path: Resource path
            priority: Request priority (1-10, lower is higher priority)
            
        Returns:
            Content if successful, None otherwise
        """
        try:
            # Use shorter timeout for prefetch
            old_timeout = self.settings.origin_timeout
            self.settings.origin_timeout = min(10, old_timeout)
            
            content, status, _ = await self.fetch(path)
            
            self.settings.origin_timeout = old_timeout
            
            if status == 200:
                return content
            
        except Exception as e:
            logger.debug("prefetch_failed", path=path, error=str(e))
        
        return None
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return f"{self.settings.edge_location}-{uuid.uuid4().hex[:8]}"
    
    def parse_cache_control(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse Cache-Control header
        
        Returns:
            Dictionary with cache control directives
        """
        cache_control = headers.get("cache-control", "")
        directives = {}
        
        if not cache_control:
            return directives
        
        for directive in cache_control.split(","):
            directive = directive.strip()
            
            if "=" in directive:
                key, value = directive.split("=", 1)
                key = key.strip().lower().replace("-", "_")
                value = value.strip().strip('"')
                
                # Convert numeric values
                if key in ["max_age", "s_maxage", "min_fresh", "max_stale"]:
                    try:
                        directives[key] = int(value)
                    except ValueError:
                        directives[key] = value
                else:
                    directives[key] = value
            else:
                # Boolean directives
                key = directive.lower().replace("-", "_")
                directives[key] = True
        
        return directives
    
    def should_cache(self, status_code: int, headers: Dict[str, str]) -> bool:
        """
        Determine if response should be cached based on status and headers
        
        Args:
            status_code: HTTP status code
            headers: Response headers
            
        Returns:
            True if response should be cached
        """
        # Don't cache error responses (except 404 which might be cached briefly)
        if status_code >= 400 and status_code != 404:
            return False
        
        # Check Cache-Control
        cache_control = self.parse_cache_control(headers)
        
        # Respect no-store directive
        if cache_control.get("no_store"):
            return False
        
        # Don't cache private responses if configured
        if cache_control.get("private") and not self.settings.cache_private_content:
            return False
        
        # Check for explicit caching headers
        if "max_age" in cache_control or "s_maxage" in cache_control:
            return True
        
        # Check Expires header
        if "expires" in headers:
            try:
                expires = datetime.fromisoformat(headers["expires"].replace("GMT", "+00:00"))
                if expires > datetime.utcnow():
                    return True
            except:
                pass
        
        # Default caching for successful responses
        return status_code in [200, 203, 206, 300, 301, 404]
    
    def calculate_ttl(self, headers: Dict[str, str], default_ttl: int) -> int:
        """
        Calculate TTL from response headers
        
        Args:
            headers: Response headers
            default_ttl: Default TTL if not specified in headers
            
        Returns:
            TTL in seconds
        """
        cache_control = self.parse_cache_control(headers)
        
        # Check s-maxage first (for shared caches)
        if "s_maxage" in cache_control:
            return cache_control["s_maxage"]
        
        # Then max-age
        if "max_age" in cache_control:
            return cache_control["max_age"]
        
        # Check Expires header
        if "expires" in headers:
            try:
                expires = datetime.fromisoformat(headers["expires"].replace("GMT", "+00:00"))
                ttl = int((expires - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    return ttl
            except:
                pass
        
        # Use default
        return default_ttl