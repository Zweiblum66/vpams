"""
Enhanced Middleware for Comprehensive Logging

Provides advanced request/response logging with correlation tracking,
performance monitoring, and audit logging.
"""

import time
import uuid
from typing import Optional, Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp
import structlog

from .enhanced_logging import (
    request_response_logger,
    performance_logger,
    audit_logger,
    log_aggregator
)
from .config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Adds correlation ID to requests for distributed tracing"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID')
        request_id = request.headers.get('X-Request-ID')
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        
        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id
        )
        
        # Process request
        response = await call_next(request)
        
        # Add correlation headers to response
        response.headers['X-Correlation-ID'] = correlation_id
        response.headers['X-Request-ID'] = request_id
        
        return response


class EnhancedLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced logging middleware with request/response body logging"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timing
        start_time = time.time()
        
        # Get request ID
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Override request.body() to capture body
        original_body_method = request.body
        
        async def new_body_method():
            if hasattr(request.state, '_body'):
                return request.state._body
            body = await original_body_method()
            request.state._body = body
            return body
        
        request.body = new_body_method
        
        # Log request
        request_data = await request_response_logger.log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Handle streaming responses
            if isinstance(response, StreamingResponse):
                # For streaming responses, we can't easily capture the body
                response_time = time.time() - start_time
                await self._log_streaming_response(
                    request, response, request_data, response_time, request_id
                )
            else:
                # For regular responses, capture the body
                response_body = b''
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Create new response with captured body
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                response.body = response_body
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # Log response
                await request_response_logger.log_response(
                    request, response, request_data, response_time, request_id
                )
            
            # Log performance metrics
            await performance_logger.log_metric(
                "request_duration",
                response_time,
                tags={
                    "method": request.method,
                    "path": str(request.url.path),
                    "status": str(response.status_code)
                },
                request_id=request_id
            )
            
            # Aggregate metrics
            await log_aggregator.aggregate_request(
                str(request.url.path),
                request.method,
                response.status_code,
                response_time
            )
            
            return response
            
        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            logger.error(
                "Request processing failed",
                request_id=request_id,
                error=str(e),
                response_time=response_time,
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    async def _log_streaming_response(
        self,
        request: Request,
        response: StreamingResponse,
        request_data: dict,
        response_time: float,
        request_id: str
    ):
        """Log streaming response without capturing body"""
        response_data = {
            "request_id": request_id,
            "status_code": response.status_code,
            "response_time": round(response_time * 1000, 2),
            "headers": dict(response.headers),
            "body": "<Streaming response>"
        }
        
        log_entry = {
            **request_data,
            "response": response_data
        }
        
        if response.status_code >= 500:
            logger.error("Streaming request completed with error", **log_entry)
        elif response.status_code >= 400:
            logger.warning("Streaming request completed with client error", **log_entry)
        else:
            logger.info("Streaming request completed", **log_entry)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging of security events"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Process request
        response = await call_next(request)
        
        # Log authentication events
        if request.url.path.startswith("/api/v1/auth/"):
            await self._log_auth_event(request, response)
        
        # Log data access events for sensitive endpoints
        sensitive_endpoints = ["/api/v1/users", "/api/v1/rights", "/api/v1/audit"]
        if any(request.url.path.startswith(ep) for ep in sensitive_endpoints):
            await self._log_data_access(request, response)
        
        return response
    
    async def _log_auth_event(self, request: Request, response: Response):
        """Log authentication events"""
        request_id = getattr(request.state, 'request_id', None)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get('user-agent')
        
        if request.url.path == "/api/v1/auth/login":
            # Extract username from request body if available
            user_id = None
            if hasattr(request.state, '_body'):
                try:
                    import json
                    body = json.loads(request.state._body)
                    user_id = body.get('username') or body.get('email')
                except:
                    pass
            
            await audit_logger.log_authentication(
                event_type="login",
                user_id=user_id,
                success=response.status_code == 200,
                method="password",
                ip_address=client_ip,
                user_agent=user_agent,
                reason=None if response.status_code == 200 else "Invalid credentials",
                request_id=request_id
            )
        
        elif request.url.path == "/api/v1/auth/logout":
            user_id = getattr(request.state, 'user_id', None)
            await audit_logger.log_authentication(
                event_type="logout",
                user_id=user_id,
                success=True,
                method="manual",
                ip_address=client_ip,
                user_agent=user_agent,
                request_id=request_id
            )
    
    async def _log_data_access(self, request: Request, response: Response):
        """Log data access events"""
        user_id = getattr(request.state, 'user_id', 'anonymous')
        request_id = getattr(request.state, 'request_id', None)
        
        # Determine resource type and ID from path
        path_parts = request.url.path.strip('/').split('/')
        resource_type = path_parts[2] if len(path_parts) > 2 else "unknown"
        resource_id = path_parts[3] if len(path_parts) > 3 else "list"
        
        # Map HTTP methods to actions
        action_map = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }
        action = action_map.get(request.method, "unknown")
        
        await audit_logger.log_data_access(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=response.status_code < 400,
            data_classification="sensitive" if resource_type == "users" else "internal",
            request_id=request_id
        )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting and exposing metrics"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await self._get_metrics(request)
        
        # Increment request count
        self.request_count += 1
        
        # Process request
        response = await call_next(request)
        
        # Count errors
        if response.status_code >= 400:
            self.error_count += 1
        
        return response
    
    async def _get_metrics(self, request: Request) -> Response:
        """Return metrics in Prometheus format"""
        uptime = time.time() - self.start_time
        
        # Get performance stats
        stats = {}
        for metric in ["request_duration"]:
            metric_stats = await performance_logger.get_stats(metric)
            if metric_stats:
                stats[metric] = metric_stats
        
        # Get aggregated data
        summary = await log_aggregator.get_summary()
        
        # Format as Prometheus metrics
        metrics_lines = [
            "# HELP api_gateway_requests_total Total number of requests",
            "# TYPE api_gateway_requests_total counter",
            f"api_gateway_requests_total {self.request_count}",
            "",
            "# HELP api_gateway_errors_total Total number of errors",
            "# TYPE api_gateway_errors_total counter",
            f"api_gateway_errors_total {self.error_count}",
            "",
            "# HELP api_gateway_uptime_seconds Uptime in seconds",
            "# TYPE api_gateway_uptime_seconds gauge",
            f"api_gateway_uptime_seconds {uptime}",
            ""
        ]
        
        # Add performance metrics
        if "request_duration" in stats:
            duration_stats = stats["request_duration"]
            metrics_lines.extend([
                "# HELP api_gateway_request_duration_seconds Request duration statistics",
                "# TYPE api_gateway_request_duration_seconds summary",
                f"api_gateway_request_duration_seconds{{quantile=\"0.5\"}} {duration_stats.get('p50', 0)}",
                f"api_gateway_request_duration_seconds{{quantile=\"0.9\"}} {duration_stats.get('p90', 0)}",
                f"api_gateway_request_duration_seconds{{quantile=\"0.95\"}} {duration_stats.get('p95', 0)}",
                f"api_gateway_request_duration_seconds{{quantile=\"0.99\"}} {duration_stats.get('p99', 0)}",
                f"api_gateway_request_duration_seconds_sum {duration_stats.get('avg', 0) * duration_stats.get('count', 0)}",
                f"api_gateway_request_duration_seconds_count {duration_stats.get('count', 0)}",
                ""
            ])
        
        # Add endpoint-specific metrics
        for endpoint, count in summary.get("request_counts", {}).items():
            method, path = endpoint.split(":", 1)
            metrics_lines.extend([
                f"api_gateway_endpoint_requests_total{{method=\"{method}\",path=\"{path}\"}} {count}"
            ])
        
        metrics_text = "\n".join(metrics_lines)
        
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )