"""
Custom exceptions for Partner Service
"""

from typing import Dict, Any, Optional


class PartnerError(Exception):
    """Base exception for partner-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PARTNER_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class PartnerNotFoundError(PartnerError):
    """Partner not found error"""
    
    def __init__(self, partner_id: str):
        super().__init__(
            message=f"Partner with ID {partner_id} not found",
            error_code="PARTNER_NOT_FOUND",
            status_code=404,
            details={"partner_id": partner_id}
        )


class PartnerApplicationError(PartnerError):
    """Partner application related errors"""
    
    def __init__(self, message: str, application_id: str = None):
        super().__init__(
            message=message,
            error_code="PARTNER_APPLICATION_ERROR",
            status_code=400,
            details={"application_id": application_id} if application_id else {}
        )


class PartnerPermissionError(PartnerError):
    """Partner permission denied error"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="PARTNER_PERMISSION_DENIED",
            status_code=403
        )


class PartnerValidationError(PartnerError):
    """Partner data validation error"""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            error_code="PARTNER_VALIDATION_ERROR",
            status_code=422,
            details={"field": field} if field else {}
        )


class PartnerResourceError(PartnerError):
    """Partner resource access error"""
    
    def __init__(self, message: str, resource_id: str = None):
        super().__init__(
            message=message,
            error_code="PARTNER_RESOURCE_ERROR",
            status_code=404,
            details={"resource_id": resource_id} if resource_id else {}
        )


class PartnerQuotaExceededError(PartnerError):
    """Partner quota exceeded error"""
    
    def __init__(self, message: str, quota_type: str = None):
        super().__init__(
            message=message,
            error_code="PARTNER_QUOTA_EXCEEDED",
            status_code=429,
            details={"quota_type": quota_type} if quota_type else {}
        )