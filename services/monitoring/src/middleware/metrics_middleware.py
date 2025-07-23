"""
Prometheus metrics middleware for FastAPI applications

This middleware automatically tracks HTTP request metrics for any FastAPI service.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import sys
from typing import Callable

from ..core.metrics import MetricsCollector


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect HTTP metrics for FastAPI applications
    
    Usage:
        from monitoring.middleware import PrometheusMetricsMiddleware
        
        app = FastAPI()
        app.add_middleware(
            PrometheusMetricsMiddleware,
            service_name="my-service",
            version="1.0.0"
        )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        service_name: str,
        version: str = "1.0.0",
        environment: str = "production",
        skip_paths: list = None
    ):
        super().__init__(app)
        self.service_name = service_name
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector(
            service_name=service_name,
            version=version,
            environment=environment
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics"""
        # Skip metrics collection for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Get request size
        request_size = 0
        if request.headers.get("content-length"):
            try:
                request_size = int(request.headers["content-length"])
            except ValueError:
                pass
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Track error
            self.metrics_collector.track_error(
                error_type=type(e).__name__,
                severity="error"
            )
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Get response size
            response_size = 0
            if hasattr(response, "headers") and response.headers.get("content-length"):
                try:
                    response_size = int(response.headers["content-length"])
                except ValueError:
                    pass
            
            # Track metrics
            self.metrics_collector.track_request(
                method=request.method,
                endpoint=self._normalize_path(request.url.path),
                status=status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metrics to avoid high cardinality
        
        Replaces path parameters with placeholders:
        /api/v1/assets/123 -> /api/v1/assets/{id}
        """
        parts = path.strip("/").split("/")
        normalized_parts = []
        
        for i, part in enumerate(parts):
            # Common patterns for IDs
            if part.isdigit() or self._is_uuid(part):
                normalized_parts.append("{id}")
            elif i > 0 and parts[i-1] in ["user", "asset", "project", "workflow"]:
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)
        
        return "/" + "/".join(normalized_parts)
    
    def _is_uuid(self, value: str) -> bool:
        """Check if a string is a UUID"""
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))