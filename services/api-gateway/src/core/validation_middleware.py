"""
Validation Middleware

Middleware for request validation and sanitization that integrates
with the FastAPI application.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import time

from core.validation import RequestValidator, get_validator
from core.exceptions import ValidationException
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request validation and sanitization
    
    This middleware:
    - Validates request size and structure
    - Sanitizes headers, query parameters, and body
    - Blocks malicious content
    - Logs security violations
    - Provides sanitized data to downstream handlers
    """
    
    def __init__(self, app: ASGIApp, validator: Optional[RequestValidator] = None):
        super().__init__(app)
        self.validator = validator or get_validator()
        self.excluded_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/static"
        ]
        self.excluded_methods = ["OPTIONS"]
        
        # Rate limiting for validation (simple in-memory)
        self.validation_requests = {}
        self.validation_window = 60  # seconds
        self.max_validation_requests = 1000
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with validation and sanitization"""
        start_time = time.time()
        
        # Skip validation for excluded paths and methods
        if self._should_skip_validation(request):
            return await call_next(request)
        
        # Rate limiting for validation
        if not self._check_validation_rate_limit(request):
            logger.warning(f"Validation rate limit exceeded for IP: {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "VALIDATION_RATE_LIMIT_EXCEEDED",
                        "message": "Too many validation requests. Please try again later.",
                        "timestamp": time.time(),
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                }
            )
        
        try:
            # Validate and sanitize request
            await self._validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            # Log successful validation
            processing_time = time.time() - start_time
            logger.debug(f"Request validated successfully in {processing_time:.3f}s")
            
            return response
            
        except ValidationException as e:
            # Log validation failure
            logger.warning(
                f"Request validation failed: {e}",
                extra={
                    "client_ip": request.client.host if request.client else None,
                    "method": request.method,
                    "path": request.url.path,
                    "user_agent": request.headers.get("user-agent"),
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": str(e),
                        "timestamp": time.time(),
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                }
            )
            
        except Exception as e:
            # Log unexpected validation errors
            logger.error(
                f"Unexpected validation error: {e}",
                exc_info=True,
                extra={
                    "client_ip": request.client.host if request.client else None,
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred during validation",
                        "timestamp": time.time(),
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                }
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request"""
        # Skip excluded paths
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return True
        
        # Skip excluded methods
        if request.method in self.excluded_methods:
            return True
        
        return False
    
    def _check_validation_rate_limit(self, request: Request) -> bool:
        """Check validation rate limit"""
        if not request.client:
            return True
        
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        self.validation_requests = {
            ip: timestamps for ip, timestamps in self.validation_requests.items()
            if any(ts > current_time - self.validation_window for ts in timestamps)
        }
        
        # Check rate limit
        if client_ip not in self.validation_requests:
            self.validation_requests[client_ip] = []
        
        # Remove old timestamps
        self.validation_requests[client_ip] = [
            ts for ts in self.validation_requests[client_ip]
            if ts > current_time - self.validation_window
        ]
        
        # Check if limit exceeded
        if len(self.validation_requests[client_ip]) >= self.max_validation_requests:
            return False
        
        # Add current request
        self.validation_requests[client_ip].append(current_time)
        return True
    
    async def _validate_request(self, request: Request) -> None:
        """Validate and sanitize request"""
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length_int = int(content_length)
                self.validator.validate_content_length(content_length_int)
            except (ValueError, ValidationException) as e:
                raise ValidationException(f"Invalid content length: {e}")
        
        # Validate and sanitize headers
        try:
            sanitized_headers = self.validator.validate_headers(dict(request.headers))
            # Store sanitized headers in request state
            request.state.sanitized_headers = sanitized_headers
        except ValidationException as e:
            raise ValidationException(f"Header validation failed: {e}")
        
        # Validate and sanitize query parameters
        try:
            sanitized_params = self.validator.validate_query_params(dict(request.query_params))
            # Store sanitized params in request state
            request.state.sanitized_query_params = sanitized_params
        except ValidationException as e:
            raise ValidationException(f"Query parameter validation failed: {e}")
        
        # Validate request body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request)
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate and sanitize request body"""
        content_type = request.headers.get("content-type", "").lower()
        
        try:
            if content_type.startswith("application/json"):
                # Parse and validate JSON body
                body = await request.body()
                if body:
                    try:
                        json_data = json.loads(body)
                        sanitized_json = self.validator.validate_json_body(json_data)
                        # Store sanitized JSON in request state
                        request.state.sanitized_json = sanitized_json
                    except json.JSONDecodeError as e:
                        raise ValidationException(f"Invalid JSON: {e}")
                    except ValidationException:
                        raise
                    except Exception as e:
                        raise ValidationException(f"JSON validation failed: {e}")
            
            elif content_type.startswith("application/x-www-form-urlencoded"):
                # Parse and validate form data
                form_data = await request.form()
                sanitized_form = self.validator.validate_form_data(dict(form_data))
                # Store sanitized form data in request state
                request.state.sanitized_form = sanitized_form
            
            elif content_type.startswith("multipart/form-data"):
                # Validate multipart form data and files
                await self._validate_multipart_form(request)
            
            elif content_type.startswith("text/"):
                # Validate plain text body
                body = await request.body()
                if body:
                    text_data = body.decode('utf-8')
                    sanitized_text = self.validator.sanitizer.sanitize_string(
                        text_data, self.validator.config.max_text_length
                    )
                    # Store sanitized text in request state
                    request.state.sanitized_text = sanitized_text
        
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Body validation failed: {e}")
    
    async def _validate_multipart_form(self, request: Request) -> None:
        """Validate multipart form data"""
        try:
            form_data = await request.form()
            sanitized_form = {}
            
            for field_name, field_value in form_data.items():
                if hasattr(field_value, 'filename'):
                    # File upload
                    if field_value.filename:
                        # Validate file upload
                        file_size = len(await field_value.read())
                        await field_value.seek(0)  # Reset file pointer
                        
                        self.validator.validate_file_upload(
                            field_value.filename,
                            field_value.content_type or "",
                            file_size
                        )
                        
                        # Store file info in sanitized form
                        sanitized_form[field_name] = {
                            "filename": self.validator.sanitizer.sanitize_filename(field_value.filename),
                            "content_type": field_value.content_type,
                            "size": file_size
                        }
                else:
                    # Regular form field
                    sanitized_form[field_name] = self.validator.sanitizer.sanitize_string(str(field_value))
            
            # Store sanitized form data in request state
            request.state.sanitized_multipart_form = sanitized_form
            
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Multipart form validation failed: {e}")


class ContentSecurityMiddleware(BaseHTTPMiddleware):
    """
    Content Security Policy middleware
    
    Adds security headers to responses to prevent various attacks.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https: wss:; "
                "frame-ancestors 'none';"
            ),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Request size limiting middleware
    
    Prevents large requests from consuming too much memory.
    """
    
    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Check request size before processing"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int > self.max_size:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"Request size {content_length_int} exceeds maximum {self.max_size} bytes",
                                "timestamp": time.time(),
                                "request_id": getattr(request.state, 'request_id', None)
                            }
                        }
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": "INVALID_CONTENT_LENGTH",
                            "message": "Invalid Content-Length header",
                            "timestamp": time.time(),
                            "request_id": getattr(request.state, 'request_id', None)
                        }
                    }
                )
        
        return await call_next(request)


# Helper functions for accessing sanitized data

def get_sanitized_headers(request: Request) -> Dict[str, str]:
    """Get sanitized headers from request state"""
    return getattr(request.state, 'sanitized_headers', {})


def get_sanitized_query_params(request: Request) -> Dict[str, Any]:
    """Get sanitized query parameters from request state"""
    return getattr(request.state, 'sanitized_query_params', {})


def get_sanitized_json(request: Request) -> Any:
    """Get sanitized JSON body from request state"""
    return getattr(request.state, 'sanitized_json', None)


def get_sanitized_form(request: Request) -> Dict[str, Any]:
    """Get sanitized form data from request state"""
    return getattr(request.state, 'sanitized_form', {})


def get_sanitized_text(request: Request) -> str:
    """Get sanitized text body from request state"""
    return getattr(request.state, 'sanitized_text', '')


def get_sanitized_multipart_form(request: Request) -> Dict[str, Any]:
    """Get sanitized multipart form data from request state"""
    return getattr(request.state, 'sanitized_multipart_form', {})
