"""Custom exceptions for Security Scanning Service."""

from typing import Dict, Any, Optional


class SecurityScanningException(Exception):
    """Base exception for security scanning related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SECURITY_SCANNING_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ScanExecutionError(SecurityScanningException):
    """Scan execution specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SCAN_EXECUTION_ERROR",
            status_code=500,
            details=details
        )


class NetworkScanError(SecurityScanningException):
    """Network scanning specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NETWORK_SCAN_ERROR",
            status_code=500,
            details=details
        )


class WebScanError(SecurityScanningException):
    """Web application scanning specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="WEB_SCAN_ERROR",
            status_code=500,
            details=details
        )


class VulnerabilityScanError(SecurityScanningException):
    """Vulnerability scanning specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VULNERABILITY_SCAN_ERROR",
            status_code=500,
            details=details
        )


class SSLScanError(SecurityScanningException):
    """SSL/TLS scanning specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SSL_SCAN_ERROR",
            status_code=500,
            details=details
        )


class ConfigurationError(SecurityScanningException):
    """Configuration related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=400,
            details=details
        )


class ScanTimeoutError(SecurityScanningException):
    """Scan timeout errors."""
    
    def __init__(self, scan_type: str, timeout: int):
        super().__init__(
            message=f"{scan_type} scan timed out after {timeout} seconds",
            error_code="SCAN_TIMEOUT",
            status_code=408,
            details={"scan_type": scan_type, "timeout": timeout}
        )


class InvalidTargetError(SecurityScanningException):
    """Invalid scan target errors."""
    
    def __init__(self, target: str, reason: str):
        super().__init__(
            message=f"Invalid scan target: {target}. Reason: {reason}",
            error_code="INVALID_TARGET",
            status_code=400,
            details={"target": target, "reason": reason}
        )


class ScanLimitExceededError(SecurityScanningException):
    """Scan rate limit exceeded errors."""
    
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Scan rate limit exceeded: {limit} scans per {window}",
            error_code="SCAN_LIMIT_EXCEEDED",
            status_code=429,
            details={"limit": limit, "window": window}
        )


class ToolNotFoundError(SecurityScanningException):
    """Scanning tool not found errors."""
    
    def __init__(self, tool_name: str, tool_path: str):
        super().__init__(
            message=f"Scanning tool not found: {tool_name} at {tool_path}",
            error_code="TOOL_NOT_FOUND",
            status_code=500,
            details={"tool_name": tool_name, "tool_path": tool_path}
        )


class ReportGenerationError(SecurityScanningException):
    """Report generation errors."""
    
    def __init__(self, format_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Failed to generate {format_type} report",
            error_code="REPORT_GENERATION_ERROR",
            status_code=500,
            details=details
        )


class DatabaseError(SecurityScanningException):
    """Database operation errors."""
    
    def __init__(self, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database operation failed: {operation}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class ResourceNotFoundError(SecurityScanningException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class PermissionDeniedError(SecurityScanningException):
    """Permission denied errors."""
    
    def __init__(self, action: str, resource: str = ""):
        super().__init__(
            message=f"Permission denied for action: {action}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"action": action, "resource": resource}
        )