"""
Security Headers Middleware

Comprehensive security headers middleware for protecting against
various web application attacks and vulnerabilities.
"""

import re
import time
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import BaseModel, Field
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityHeadersConfig(BaseModel):
    """Configuration for security headers"""
    
    # Content Security Policy
    csp_default_src: List[str] = Field(
        default_factory=lambda: ["'self'"],
        description="Default source directive for CSP"
    )
    csp_script_src: List[str] = Field(
        default_factory=lambda: ["'self'", "'unsafe-inline'"],
        description="Script source directive for CSP"
    )
    csp_style_src: List[str] = Field(
        default_factory=lambda: ["'self'", "'unsafe-inline'"],
        description="Style source directive for CSP"
    )
    csp_img_src: List[str] = Field(
        default_factory=lambda: ["'self'", "data:", "https:"],
        description="Image source directive for CSP"
    )
    csp_font_src: List[str] = Field(
        default_factory=lambda: ["'self'", "https:"],
        description="Font source directive for CSP"
    )
    csp_connect_src: List[str] = Field(
        default_factory=lambda: ["'self'", "https:", "wss:"],
        description="Connect source directive for CSP"
    )
    csp_media_src: List[str] = Field(
        default_factory=lambda: ["'self'", "https:"],
        description="Media source directive for CSP"
    )
    csp_object_src: List[str] = Field(
        default_factory=lambda: ["'none'"],
        description="Object source directive for CSP"
    )
    csp_base_uri: List[str] = Field(
        default_factory=lambda: ["'self'"],
        description="Base URI directive for CSP"
    )
    csp_form_action: List[str] = Field(
        default_factory=lambda: ["'self'"],
        description="Form action directive for CSP"
    )
    csp_frame_ancestors: List[str] = Field(
        default_factory=lambda: ["'none'"],
        description="Frame ancestors directive for CSP"
    )
    csp_report_uri: Optional[str] = Field(
        default=None,
        description="CSP report URI for violation reporting"
    )
    csp_report_only: bool = Field(
        default=False,
        description="Whether to use CSP report-only mode"
    )
    
    # HSTS (HTTP Strict Transport Security)
    hsts_max_age: int = Field(
        default=31536000,  # 1 year
        description="HSTS max age in seconds"
    )
    hsts_include_subdomains: bool = Field(
        default=True,
        description="Whether to include subdomains in HSTS"
    )
    hsts_preload: bool = Field(
        default=False,
        description="Whether to enable HSTS preload"
    )
    
    # X-Frame-Options
    frame_options: str = Field(
        default="DENY",
        description="X-Frame-Options value (DENY, SAMEORIGIN, ALLOW-FROM)"
    )
    
    # X-Content-Type-Options
    content_type_options: str = Field(
        default="nosniff",
        description="X-Content-Type-Options value"
    )
    
    # X-XSS-Protection
    xss_protection: str = Field(
        default="1; mode=block",
        description="X-XSS-Protection value"
    )
    
    # Referrer Policy
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        description="Referrer Policy value"
    )
    
    # Permissions Policy
    permissions_policy: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "camera": [],
            "microphone": [],
            "geolocation": [],
            "payment": [],
            "usb": [],
            "magnetometer": [],
            "gyroscope": [],
            "accelerometer": [],
            "ambient-light-sensor": [],
            "autoplay": ["'self'"],
            "encrypted-media": ["'self'"],
            "fullscreen": ["'self'"],
            "picture-in-picture": ["'self'"]
        },
        description="Permissions Policy directives"
    )
    
    # Cross-Origin Policies
    cross_origin_embedder_policy: str = Field(
        default="require-corp",
        description="Cross-Origin-Embedder-Policy value"
    )
    cross_origin_opener_policy: str = Field(
        default="same-origin",
        description="Cross-Origin-Opener-Policy value"
    )
    cross_origin_resource_policy: str = Field(
        default="same-origin",
        description="Cross-Origin-Resource-Policy value"
    )
    
    # Server identification
    server_header: Optional[str] = Field(
        default=None,
        description="Server header value (None to remove)"
    )
    x_powered_by: Optional[str] = Field(
        default=None,
        description="X-Powered-By header value (None to remove)"
    )
    
    # Additional security headers
    x_dns_prefetch_control: str = Field(
        default="off",
        description="X-DNS-Prefetch-Control value"
    )
    x_download_options: str = Field(
        default="noopen",
        description="X-Download-Options value"
    )
    x_permitted_cross_domain_policies: str = Field(
        default="none",
        description="X-Permitted-Cross-Domain-Policies value"
    )
    
    # Environment-specific settings
    environment: str = Field(
        default="production",
        description="Environment (development, staging, production)"
    )
    
    # Feature flags
    enable_csp: bool = Field(default=True, description="Enable Content Security Policy")
    enable_hsts: bool = Field(default=True, description="Enable HTTP Strict Transport Security")
    enable_frame_options: bool = Field(default=True, description="Enable X-Frame-Options")
    enable_content_type_options: bool = Field(default=True, description="Enable X-Content-Type-Options")
    enable_xss_protection: bool = Field(default=True, description="Enable X-XSS-Protection")
    enable_referrer_policy: bool = Field(default=True, description="Enable Referrer Policy")
    enable_permissions_policy: bool = Field(default=True, description="Enable Permissions Policy")
    enable_cross_origin_policies: bool = Field(default=True, description="Enable Cross-Origin policies")
    enable_additional_headers: bool = Field(default=True, description="Enable additional security headers")
    
    # Logging and monitoring
    log_security_headers: bool = Field(default=False, description="Log security headers")
    log_violations: bool = Field(default=True, description="Log security violations")


class SecurityHeadersBuilder:
    """Builder for security headers"""
    
    def __init__(self, config: SecurityHeadersConfig):
        self.config = config
    
    def build_csp_header(self) -> Optional[str]:
        """Build Content Security Policy header"""
        if not self.config.enable_csp:
            return None
        
        directives = []
        
        # Default source
        if self.config.csp_default_src:
            directives.append(f"default-src {' '.join(self.config.csp_default_src)}")
        
        # Script source
        if self.config.csp_script_src:
            directives.append(f"script-src {' '.join(self.config.csp_script_src)}")
        
        # Style source
        if self.config.csp_style_src:
            directives.append(f"style-src {' '.join(self.config.csp_style_src)}")
        
        # Image source
        if self.config.csp_img_src:
            directives.append(f"img-src {' '.join(self.config.csp_img_src)}")
        
        # Font source
        if self.config.csp_font_src:
            directives.append(f"font-src {' '.join(self.config.csp_font_src)}")
        
        # Connect source
        if self.config.csp_connect_src:
            directives.append(f"connect-src {' '.join(self.config.csp_connect_src)}")
        
        # Media source
        if self.config.csp_media_src:
            directives.append(f"media-src {' '.join(self.config.csp_media_src)}")
        
        # Object source
        if self.config.csp_object_src:
            directives.append(f"object-src {' '.join(self.config.csp_object_src)}")
        
        # Base URI
        if self.config.csp_base_uri:
            directives.append(f"base-uri {' '.join(self.config.csp_base_uri)}")
        
        # Form action
        if self.config.csp_form_action:
            directives.append(f"form-action {' '.join(self.config.csp_form_action)}")
        
        # Frame ancestors
        if self.config.csp_frame_ancestors:
            directives.append(f"frame-ancestors {' '.join(self.config.csp_frame_ancestors)}")
        
        # Report URI
        if self.config.csp_report_uri:
            directives.append(f"report-uri {self.config.csp_report_uri}")
        
        return "; ".join(directives)
    
    def build_hsts_header(self) -> Optional[str]:
        """Build HTTP Strict Transport Security header"""
        if not self.config.enable_hsts:
            return None
        
        parts = [f"max-age={self.config.hsts_max_age}"]
        
        if self.config.hsts_include_subdomains:
            parts.append("includeSubDomains")
        
        if self.config.hsts_preload:
            parts.append("preload")
        
        return "; ".join(parts)
    
    def build_permissions_policy_header(self) -> Optional[str]:
        """Build Permissions Policy header"""
        if not self.config.enable_permissions_policy:
            return None
        
        policies = []
        
        for feature, allowlist in self.config.permissions_policy.items():
            if allowlist:
                policy = f"{feature}=({' '.join(allowlist)})"
            else:
                policy = f"{feature}=()"
            policies.append(policy)
        
        return ", ".join(policies)
    
    def build_all_headers(self, request: Request, response: Response) -> Dict[str, str]:
        """Build all security headers"""
        headers = {}
        
        # Content Security Policy
        if self.config.enable_csp:
            csp_header = self.build_csp_header()
            if csp_header:
                header_name = "Content-Security-Policy-Report-Only" if self.config.csp_report_only else "Content-Security-Policy"
                headers[header_name] = csp_header
        
        # HTTP Strict Transport Security
        if self.config.enable_hsts and request.url.scheme == "https":
            hsts_header = self.build_hsts_header()
            if hsts_header:
                headers["Strict-Transport-Security"] = hsts_header
        
        # X-Frame-Options
        if self.config.enable_frame_options:
            headers["X-Frame-Options"] = self.config.frame_options
        
        # X-Content-Type-Options
        if self.config.enable_content_type_options:
            headers["X-Content-Type-Options"] = self.config.content_type_options
        
        # X-XSS-Protection
        if self.config.enable_xss_protection:
            headers["X-XSS-Protection"] = self.config.xss_protection
        
        # Referrer Policy
        if self.config.enable_referrer_policy:
            headers["Referrer-Policy"] = self.config.referrer_policy
        
        # Permissions Policy
        if self.config.enable_permissions_policy:
            permissions_header = self.build_permissions_policy_header()
            if permissions_header:
                headers["Permissions-Policy"] = permissions_header
        
        # Cross-Origin policies
        if self.config.enable_cross_origin_policies:
            headers["Cross-Origin-Embedder-Policy"] = self.config.cross_origin_embedder_policy
            headers["Cross-Origin-Opener-Policy"] = self.config.cross_origin_opener_policy
            headers["Cross-Origin-Resource-Policy"] = self.config.cross_origin_resource_policy
        
        # Additional security headers
        if self.config.enable_additional_headers:
            headers["X-DNS-Prefetch-Control"] = self.config.x_dns_prefetch_control
            headers["X-Download-Options"] = self.config.x_download_options
            headers["X-Permitted-Cross-Domain-Policies"] = self.config.x_permitted_cross_domain_policies
        
        # Remove server identification headers
        if self.config.server_header is None:
            headers["Server"] = ""  # Remove server header
        elif self.config.server_header:
            headers["Server"] = self.config.server_header
        
        if self.config.x_powered_by is None:
            headers["X-Powered-By"] = ""  # Remove X-Powered-By header
        elif self.config.x_powered_by:
            headers["X-Powered-By"] = self.config.x_powered_by
        
        return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware
    
    This middleware adds various security headers to protect against:
    - Cross-Site Scripting (XSS)
    - Clickjacking
    - MIME type sniffing
    - Mixed content attacks
    - Information disclosure
    - And other common web vulnerabilities
    """
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityHeadersConfig] = None):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()
        self.builder = SecurityHeadersBuilder(self.config)
        
        # Environment-specific adjustments
        self._adjust_for_environment()
        
        # Paths to exclude from security headers
        self.excluded_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        # Content types that should have security headers
        self.secured_content_types = [
            "text/html",
            "application/xhtml+xml",
            "application/xml",
            "text/xml",
            "application/json",
            "application/javascript",
            "text/javascript",
            "text/css"
        ]
        
        logger.info(f"Security headers middleware initialized for {self.config.environment} environment")
    
    def _adjust_for_environment(self):
        """Adjust configuration based on environment"""
        if self.config.environment == "development":
            # More permissive CSP for development
            self.config.csp_script_src.extend(["'unsafe-eval'", "http://localhost:*"])
            self.config.csp_connect_src.extend(["http://localhost:*", "ws://localhost:*"])
            self.config.csp_img_src.extend(["http://localhost:*"])
            
            # Disable HSTS in development
            self.config.enable_hsts = False
            
            # Enable detailed logging
            self.config.log_security_headers = True
        
        elif self.config.environment == "staging":
            # Staging-specific adjustments
            self.config.csp_report_only = True  # Report-only mode for testing
            self.config.log_security_headers = True
        
        elif self.config.environment == "production":
            # Production security settings
            self.config.enable_hsts = True
            self.config.hsts_preload = True
            self.config.log_security_headers = False
            
            # Strict CSP
            if "'unsafe-inline'" in self.config.csp_script_src:
                self.config.csp_script_src.remove("'unsafe-inline'")
            if "'unsafe-eval'" in self.config.csp_script_src:
                self.config.csp_script_src.remove("'unsafe-eval'")
    
    def _should_apply_headers(self, request: Request, response: Response) -> bool:
        """Check if security headers should be applied"""
        # Skip excluded paths
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return False
        
        # Only apply to specific content types
        content_type = response.headers.get("content-type", "")
        if content_type:
            content_type = content_type.split(";")[0].strip().lower()
            return content_type in self.secured_content_types
        
        return True
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers"""
        # Process request
        response = await call_next(request)
        
        # Check if security headers should be applied
        if not self._should_apply_headers(request, response):
            return response
        
        # Build and apply security headers
        security_headers = self.builder.build_all_headers(request, response)
        
        for header_name, header_value in security_headers.items():
            if header_value == "":
                # Remove header by setting it to empty string
                if header_name in response.headers:
                    del response.headers[header_name]
            else:
                response.headers[header_name] = header_value
        
        # Log security headers if enabled
        if self.config.log_security_headers:
            logger.debug(
                f"Applied security headers to {request.url.path}",
                extra={
                    "headers": list(security_headers.keys()),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code
                }
            )
        
        return response


class CSPViolationReporter:
    """Handler for CSP violation reports"""
    
    def __init__(self):
        self.violations = []
        self.max_violations = 1000
    
    async def report_violation(self, request: Request, violation_data: Dict[str, Any]):
        """Handle CSP violation report"""
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
            "violation": violation_data
        }
        
        # Store violation
        self.violations.append(violation)
        
        # Limit stored violations
        if len(self.violations) > self.max_violations:
            self.violations = self.violations[-self.max_violations:]
        
        # Log violation
        logger.warning(
            "CSP violation reported",
            extra={
                "violation": violation_data,
                "client_ip": violation["client_ip"],
                "user_agent": violation["user_agent"],
                "referer": violation["referer"]
            }
        )
    
    def get_violations(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get stored violations"""
        if since is None:
            return self.violations
        
        since_str = since.isoformat()
        return [v for v in self.violations if v["timestamp"] >= since_str]
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """Get violation statistics"""
        if not self.violations:
            return {"total": 0, "by_type": {}, "by_ip": {}}
        
        by_type = {}
        by_ip = {}
        
        for violation in self.violations:
            # Count by violation type
            violated_directive = violation["violation"].get("violated-directive", "unknown")
            by_type[violated_directive] = by_type.get(violated_directive, 0) + 1
            
            # Count by IP
            ip = violation["client_ip"] or "unknown"
            by_ip[ip] = by_ip.get(ip, 0) + 1
        
        return {
            "total": len(self.violations),
            "by_type": by_type,
            "by_ip": by_ip,
            "latest": self.violations[-1]["timestamp"] if self.violations else None
        }


def get_security_headers_config() -> SecurityHeadersConfig:
    """Get security headers configuration"""
    return SecurityHeadersConfig(
        environment=settings.environment,
        csp_report_uri=f"{settings.base_url}/api/v1/security/csp-report" if hasattr(settings, 'base_url') else None
    )


def create_security_headers_middleware(app: ASGIApp) -> SecurityHeadersMiddleware:
    """Create security headers middleware with default configuration"""
    config = get_security_headers_config()
    return SecurityHeadersMiddleware(app, config)


# Global CSP violation reporter
csp_reporter = CSPViolationReporter()


def get_csp_reporter() -> CSPViolationReporter:
    """Get CSP violation reporter instance"""
    return csp_reporter
