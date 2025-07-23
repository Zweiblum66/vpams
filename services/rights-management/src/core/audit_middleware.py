"""
Audit Middleware for automatic request context capture
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import uuid
import time

from ..core.logger import get_logger

logger = get_logger(__name__)


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture request context for audit trails"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate session ID if not present
        session_id = request.headers.get("x-session-id", str(uuid.uuid4()))
        
        # Store audit context in request state
        request.state.audit_context = {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "session_id": session_id,
            "request_id": str(uuid.uuid4()),
            "request_path": request.url.path,
            "request_method": request.method
        }
        
        # Track request timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate request duration
        process_time = time.time() - start_time
        
        # Add audit headers to response
        response.headers["X-Request-ID"] = request.state.audit_context["request_id"]
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {process_time:.3f}s - "
            f"Request ID: {request.state.audit_context['request_id']}"
        )
        
        return response


class AuditLoggingMiddleware:
    """Middleware to automatically log certain actions to audit trail"""
    
    # Define paths that should trigger automatic audit logging
    AUDIT_PATHS = {
        "POST": [
            "/api/v1/rights/parties",
            "/api/v1/rights/licenses",
            "/api/v1/rights/usage",
            "/api/v1/rights/reports",
            "/api/v1/rights/bulk/"
        ],
        "PUT": [
            "/api/v1/rights/parties/",
            "/api/v1/rights/licenses/",
            "/api/v1/rights/usage/",
            "/api/v1/rights/compliance/alerts/"
        ],
        "DELETE": [
            "/api/v1/rights/parties/",
            "/api/v1/rights/licenses/",
            "/api/v1/rights/usage/"
        ],
        "PATCH": [
            "/api/v1/rights/parties/",
            "/api/v1/rights/licenses/",
            "/api/v1/rights/usage/"
        ]
    }
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Check if this path should be audited
        should_audit = False
        method = request.method
        path = request.url.path
        
        if method in self.AUDIT_PATHS:
            for audit_path in self.AUDIT_PATHS[method]:
                if path.startswith(audit_path):
                    should_audit = True
                    break
        
        # Mark request for audit logging
        request.state.should_audit = should_audit
        
        # Process request
        response = await call_next(request)
        
        return response