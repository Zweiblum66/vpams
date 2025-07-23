"""
CORS (Cross-Origin Resource Sharing) Configuration

Provides comprehensive CORS configuration for the API Gateway with:
- Environment-specific configurations
- Dynamic origin validation
- Preflight request handling
- Custom header management
- Credential support
"""

from typing import List, Optional, Union, Pattern, Dict, Any
import re
import logging
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CORSConfig:
    """CORS configuration class"""
    
    def __init__(
        self,
        allowed_origins: Optional[List[str]] = None,
        allowed_origin_patterns: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        exposed_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 86400,  # 24 hours
        allow_all_origins: bool = False
    ):
        """
        Initialize CORS configuration
        
        Args:
            allowed_origins: List of allowed origin URLs
            allowed_origin_patterns: List of regex patterns for allowed origins
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed request headers
            exposed_headers: List of headers exposed to the browser
            allow_credentials: Whether to allow credentials
            max_age: Preflight cache duration in seconds
            allow_all_origins: Whether to allow all origins (development only)
        """
        self.allowed_origins = allowed_origins or []
        self.allowed_origin_patterns = allowed_origin_patterns or []
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"]
        self.allowed_headers = allowed_headers or ["*"]
        self.exposed_headers = exposed_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        self.allow_all_origins = allow_all_origins
        
        # Compile regex patterns
        self.compiled_patterns: List[Pattern] = []
        for pattern in self.allowed_origin_patterns:
            try:
                self.compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
        
        # Add default exposed headers
        self.exposed_headers.extend([
            "X-Total-Count",
            "X-Page-Count",
            "X-Current-Page",
            "X-Per-Page",
            "X-Request-ID",
            "X-API-Version",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ])
        
        # Remove duplicates
        self.exposed_headers = list(set(self.exposed_headers))
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin is allowed
        
        Args:
            origin: The origin to check
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if self.allow_all_origins:
            return True
        
        # Check exact matches
        if origin in self.allowed_origins:
            return True
        
        # Check wildcard
        if "*" in self.allowed_origins:
            return True
        
        # Check patterns
        for pattern in self.compiled_patterns:
            if pattern.match(origin):
                return True
        
        return False
    
    def get_cors_headers(self, origin: Optional[str], method: str) -> Dict[str, str]:
        """
        Get CORS headers for a response
        
        Args:
            origin: The request origin
            method: The request method
            
        Returns:
            Dictionary of CORS headers
        """
        headers = {}
        
        if not origin:
            return headers
        
        if self.is_origin_allowed(origin):
            headers["Access-Control-Allow-Origin"] = origin
            
            if self.allow_credentials:
                headers["Access-Control-Allow-Credentials"] = "true"
            
            if self.exposed_headers:
                headers["Access-Control-Expose-Headers"] = ", ".join(self.exposed_headers)
        
        return headers
    
    def get_preflight_headers(self, origin: Optional[str], method: str) -> Dict[str, str]:
        """
        Get CORS headers for preflight requests
        
        Args:
            origin: The request origin
            method: The requested method
            
        Returns:
            Dictionary of CORS headers for preflight
        """
        headers = self.get_cors_headers(origin, method)
        
        if origin and self.is_origin_allowed(origin):
            headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            headers["Access-Control-Max-Age"] = str(self.max_age)
        
        return headers


class EnhancedCORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with additional features
    
    Features:
    - Dynamic origin validation
    - Regex pattern support
    - Environment-specific configurations
    - Request logging
    - Custom header management
    """
    
    def __init__(self, app: ASGIApp, config: Optional[CORSConfig] = None):
        super().__init__(app)
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> CORSConfig:
        """Get default CORS configuration based on environment"""
        environment = settings.environment
        
        if environment == "development":
            # Permissive configuration for development
            return CORSConfig(
                allowed_origins=["*"],
                allow_all_origins=True,
                allow_credentials=True
            )
        
        elif environment == "staging":
            # More restrictive for staging
            return CORSConfig(
                allowed_origins=[
                    "https://staging.mams.example.com",
                    "https://staging-app.mams.example.com"
                ],
                allowed_origin_patterns=[
                    r"https://.*\.staging\.mams\.example\.com"
                ],
                allow_credentials=True
            )
        
        elif environment == "production":
            # Strict configuration for production
            return CORSConfig(
                allowed_origins=[
                    "https://app.mams.example.com",
                    "https://www.mams.example.com"
                ],
                allowed_origin_patterns=[
                    r"https://.*\.mams\.example\.com"
                ],
                allow_credentials=True,
                allowed_headers=[
                    "Accept",
                    "Accept-Language",
                    "Content-Type",
                    "Authorization",
                    "X-API-Key",
                    "X-Request-ID",
                    "X-Client-Version"
                ]
            )
        
        else:
            # Default configuration from settings
            return CORSConfig(
                allowed_origins=settings.cors_origins,
                allow_credentials=True
            )
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS for requests"""
        # Get origin from request
        origin = request.headers.get("origin")
        method = request.method
        
        # Handle preflight requests
        if method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # Log CORS request
        if origin:
            logger.debug(f"CORS request from origin: {origin}, method: {method}")
        
        # Check if origin is allowed
        if origin and not self.config.is_origin_allowed(origin):
            logger.warning(f"Blocked CORS request from unauthorized origin: {origin}")
            # Still process the request but without CORS headers
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to response
        cors_headers = self.config.get_cors_headers(origin, method)
        for header, value in cors_headers.items():
            response.headers[header] = value
        
        # Add Vary header to indicate that response varies by Origin
        vary_headers = response.headers.get("Vary", "")
        if vary_headers:
            vary_headers = f"{vary_headers}, Origin"
        else:
            vary_headers = "Origin"
        response.headers["Vary"] = vary_headers
        
        return response
    
    def _handle_preflight(self, request: Request, origin: Optional[str]) -> Response:
        """Handle preflight OPTIONS requests"""
        requested_method = request.headers.get("Access-Control-Request-Method", "")
        
        # Check if the requested method is allowed
        if requested_method and requested_method not in self.config.allowed_methods:
            logger.warning(f"Preflight request for disallowed method: {requested_method}")
            return Response(status_code=403)
        
        # Get preflight headers
        headers = self.config.get_preflight_headers(origin, requested_method)
        
        # Return preflight response
        return Response(
            status_code=200,
            headers=headers
        )


def get_cors_config() -> CORSConfig:
    """
    Get CORS configuration for the current environment
    
    Returns:
        CORSConfig instance
    """
    # Load from settings
    allowed_origins = settings.cors_origins if hasattr(settings, 'cors_origins') else []
    
    # Parse additional CORS settings from environment
    allowed_origin_patterns = []
    if hasattr(settings, 'cors_origin_patterns'):
        allowed_origin_patterns = settings.cors_origin_patterns
    
    # Check for development mode
    allow_all_origins = settings.environment == "development" and "*" in allowed_origins
    
    return CORSConfig(
        allowed_origins=allowed_origins,
        allowed_origin_patterns=allowed_origin_patterns,
        allow_all_origins=allow_all_origins,
        allow_credentials=True
    )


def setup_cors(app: ASGIApp) -> None:
    """
    Setup CORS for the application
    
    Args:
        app: The ASGI application
    """
    config = get_cors_config()
    
    # Use FastAPI's built-in CORS middleware for basic setup
    # This handles the standard cases efficiently
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins if not config.allow_all_origins else ["*"],
        allow_credentials=config.allow_credentials,
        allow_methods=config.allowed_methods,
        allow_headers=config.allowed_headers,
        expose_headers=config.exposed_headers,
        max_age=config.max_age
    )
    
    # Add our enhanced middleware for additional features
    # Only if we have patterns or need advanced features
    if config.allowed_origin_patterns or not config.allow_all_origins:
        app.add_middleware(EnhancedCORSMiddleware, config=config)
    
    logger.info(f"CORS configured for environment: {settings.environment}")
    if config.allow_all_origins:
        logger.warning("CORS is configured to allow ALL origins - suitable for development only!")
    else:
        logger.info(f"CORS allowed origins: {config.allowed_origins}")
        if config.allowed_origin_patterns:
            logger.info(f"CORS allowed patterns: {config.allowed_origin_patterns}")


# Utility functions for CORS validation
def validate_origin(origin: str) -> bool:
    """
    Validate if an origin URL is properly formatted
    
    Args:
        origin: The origin URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(origin)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False


def normalize_origin(origin: str) -> str:
    """
    Normalize an origin URL
    
    Args:
        origin: The origin URL to normalize
        
    Returns:
        Normalized origin URL
    """
    parsed = urlparse(origin)
    # Reconstruct with only scheme and netloc
    return f"{parsed.scheme}://{parsed.netloc}"


def get_origin_from_referer(request: Request) -> Optional[str]:
    """
    Extract origin from Referer header as fallback
    
    Args:
        request: The incoming request
        
    Returns:
        Origin URL or None
    """
    referer = request.headers.get("referer")
    if referer:
        try:
            return normalize_origin(referer)
        except Exception:
            return None
    return None