"""
API Gateway Exception Classes

Custom exceptions for the API Gateway service with proper error codes
and HTTP status mapping.
"""

from typing import Any, Dict, Optional
from fastapi import status


class APIException(Exception):
    """Base API exception class"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationException(APIException):
    """Authentication related exceptions"""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_REQUIRED",
            details=details
        )


class InvalidTokenException(APIException):
    """Invalid or expired token exceptions"""
    
    def __init__(self, message: str = "Invalid or expired token", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            details=details
        )


class AuthorizationException(APIException):
    """Authorization/permission exceptions"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details
        )


class RateLimitException(APIException):
    """Rate limit exceeded exceptions"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class ValidationException(APIException):
    """Request validation exceptions"""
    
    def __init__(self, message: str = "Invalid request data", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ServiceUnavailableException(APIException):
    """Service unavailable exceptions"""
    
    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details
        )


class BadGatewayException(APIException):
    """Bad gateway exceptions for downstream service errors"""
    
    def __init__(self, message: str = "Bad gateway", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="BAD_GATEWAY",
            details=details
        )


class GatewayTimeoutException(APIException):
    """Gateway timeout exceptions"""
    
    def __init__(self, message: str = "Gateway timeout", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="GATEWAY_TIMEOUT",
            details=details
        )


class CircuitBreakerException(APIException):
    """Circuit breaker open exceptions"""
    
    def __init__(self, message: str = "Circuit breaker is open", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="CIRCUIT_BREAKER_OPEN",
            details=details
        )


class RequestTooLargeException(APIException):
    """Request too large exceptions"""
    
    def __init__(self, message: str = "Request entity too large", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="REQUEST_TOO_LARGE",
            details=details
        )


class NotFoundError(APIException):
    """Resource not found exceptions"""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details=details
        )


class ConflictError(APIException):
    """Conflict exceptions"""
    
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            details=details
        )


class UnsupportedMediaTypeException(APIException):
    """Unsupported media type exceptions"""
    
    def __init__(self, message: str = "Unsupported media type", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="UNSUPPORTED_MEDIA_TYPE",
            details=details
        )


class MaintenanceModeException(APIException):
    """Maintenance mode exceptions"""
    
    def __init__(self, message: str = "System is in maintenance mode", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="MAINTENANCE_MODE",
            details=details
        )


class InvalidAPIVersionException(APIException):
    """Invalid API version exceptions"""
    
    def __init__(self, message: str = "Invalid API version", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_API_VERSION",
            details=details
        )


class QuotaExceededException(APIException):
    """Quota exceeded exceptions"""
    
    def __init__(self, message: str = "Quota exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="QUOTA_EXCEEDED",
            details=details
        )


class IPAccessDeniedException(APIException):
    """IP access denied exceptions"""
    
    def __init__(self, message: str = "Access denied from this IP address", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="IP_ACCESS_DENIED",
            details=details
        )