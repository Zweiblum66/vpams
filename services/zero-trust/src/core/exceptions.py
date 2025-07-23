"""Custom exceptions for Zero Trust Service."""

from typing import Dict, Any, Optional


class ZeroTrustException(Exception):
    """Base exception for zero-trust related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "ZERO_TRUST_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class TrustEvaluationError(ZeroTrustException):
    """Trust evaluation specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="TRUST_EVALUATION_ERROR",
            status_code=500,
            details=details
        )


class AccessDeniedError(ZeroTrustException):
    """Access denied errors."""
    
    def __init__(self, reason: str, trust_score: float = 0.0):
        super().__init__(
            message=f"Access denied: {reason}",
            error_code="ACCESS_DENIED",
            status_code=403,
            details={"reason": reason, "trust_score": trust_score}
        )


class InsufficientTrustError(ZeroTrustException):
    """Insufficient trust level errors."""
    
    def __init__(self, current_trust: float, required_trust: float):
        super().__init__(
            message=f"Insufficient trust level: {current_trust:.2f} < {required_trust:.2f}",
            error_code="INSUFFICIENT_TRUST",
            status_code=403,
            details={"current_trust": current_trust, "required_trust": required_trust}
        )


class DeviceNotTrustedError(ZeroTrustException):
    """Device not trusted errors."""
    
    def __init__(self, device_id: str, reason: str = "Unknown device"):
        super().__init__(
            message=f"Device not trusted: {device_id}",
            error_code="DEVICE_NOT_TRUSTED",
            status_code=403,
            details={"device_id": device_id, "reason": reason}
        )


class LocationRestrictedError(ZeroTrustException):
    """Location restricted errors."""
    
    def __init__(self, location: str, restriction_type: str):
        super().__init__(
            message=f"Access restricted from location: {location}",
            error_code="LOCATION_RESTRICTED",
            status_code=403,
            details={"location": location, "restriction_type": restriction_type}
        )


class TimeRestrictedError(ZeroTrustException):
    """Time-based access restriction errors."""
    
    def __init__(self, current_time: str, allowed_hours: str):
        super().__init__(
            message=f"Access restricted at current time: {current_time}",
            error_code="TIME_RESTRICTED",
            status_code=403,
            details={"current_time": current_time, "allowed_hours": allowed_hours}
        )


class MFARequiredError(ZeroTrustException):
    """Multi-factor authentication required errors."""
    
    def __init__(self, mfa_methods: list, session_id: str):
        super().__init__(
            message="Multi-factor authentication required",
            error_code="MFA_REQUIRED",
            status_code=401,
            details={"required_mfa_methods": mfa_methods, "session_id": session_id}
        )


class PolicyViolationError(ZeroTrustException):
    """Policy violation errors."""
    
    def __init__(self, policy_name: str, violation_details: str):
        super().__init__(
            message=f"Policy violation: {policy_name}",
            error_code="POLICY_VIOLATION",
            status_code=403,
            details={"policy": policy_name, "violation": violation_details}
        )


class AnomalousActivityError(ZeroTrustException):
    """Anomalous activity detection errors."""
    
    def __init__(self, activity_type: str, confidence: float):
        super().__init__(
            message=f"Anomalous activity detected: {activity_type}",
            error_code="ANOMALOUS_ACTIVITY",
            status_code=403,
            details={"activity_type": activity_type, "confidence": confidence}
        )


class HighRiskSessionError(ZeroTrustException):
    """High risk session errors."""
    
    def __init__(self, risk_score: float, risk_factors: list):
        super().__init__(
            message=f"High risk session detected: risk score {risk_score:.2f}",
            error_code="HIGH_RISK_SESSION",
            status_code=403,
            details={"risk_score": risk_score, "risk_factors": risk_factors}
        )


class NetworkNotTrustedError(ZeroTrustException):
    """Network not trusted errors."""
    
    def __init__(self, network: str, reason: str):
        super().__init__(
            message=f"Network not trusted: {network}",
            error_code="NETWORK_NOT_TRUSTED",
            status_code=403,
            details={"network": network, "reason": reason}
        )


class SessionExpiredError(ZeroTrustException):
    """Session expired errors."""
    
    def __init__(self, session_id: str, expiry_reason: str):
        super().__init__(
            message=f"Session expired: {expiry_reason}",
            error_code="SESSION_EXPIRED",
            status_code=401,
            details={"session_id": session_id, "reason": expiry_reason}
        )


class ThreatDetectedError(ZeroTrustException):
    """Threat detected errors."""
    
    def __init__(self, threat_type: str, threat_level: str, details: Dict[str, Any]):
        super().__init__(
            message=f"Threat detected: {threat_type} (level: {threat_level})",
            error_code="THREAT_DETECTED",
            status_code=403,
            details={"threat_type": threat_type, "threat_level": threat_level, **details}
        )


class ConfigurationError(ZeroTrustException):
    """Configuration related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class ValidationError(ZeroTrustException):
    """Input validation errors."""
    
    def __init__(self, message: str, field: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, **(details or {})}
        )


class ResourceNotFoundError(ZeroTrustException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class RateLimitExceededError(ZeroTrustException):
    """Rate limit exceeded errors."""
    
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"limit": limit, "window": window}
        )