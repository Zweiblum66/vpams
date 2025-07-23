"""Custom exceptions for Intrusion Detection Service."""

from typing import Dict, Any, Optional


class IDSException(Exception):
    """Base exception for IDS-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "IDS_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class DetectionEngineError(IDSException):
    """Detection engine specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DETECTION_ENGINE_ERROR",
            status_code=500,
            details=details
        )


class NetworkMonitorError(IDSException):
    """Network monitoring specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="NETWORK_MONITOR_ERROR",
            status_code=500,
            details=details
        )


class AnomalyDetectionError(IDSException):
    """Anomaly detection specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ANOMALY_DETECTION_ERROR",
            status_code=500,
            details=details
        )


class ThreatIntelligenceError(IDSException):
    """Threat intelligence specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="THREAT_INTEL_ERROR",
            status_code=500,
            details=details
        )


class ConfigurationError(IDSException):
    """Configuration related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=400,
            details=details
        )


class AlertingError(IDSException):
    """Alerting system errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ALERTING_ERROR",
            status_code=500,
            details=details
        )


class ValidationError(IDSException):
    """Input validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class ResourceNotFoundError(IDSException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class PermissionDeniedError(IDSException):
    """Permission denied errors."""
    
    def __init__(self, action: str, resource: str = ""):
        super().__init__(
            message=f"Permission denied for action: {action}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"action": action, "resource": resource}
        )


class RateLimitExceededError(IDSException):
    """Rate limit exceeded errors."""
    
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"limit": limit, "window": window}
        )