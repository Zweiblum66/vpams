"""
Custom exceptions for Integration Catalog Service
"""

from typing import Dict, Any, Optional


class IntegrationError(Exception):
    """Base exception for integration-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTEGRATION_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class IntegrationNotFoundError(IntegrationError):
    """Integration not found error"""
    
    def __init__(self, integration_id: str):
        super().__init__(
            message=f"Integration with ID {integration_id} not found",
            error_code="INTEGRATION_NOT_FOUND",
            status_code=404,
            details={"integration_id": integration_id}
        )


class IntegrationValidationError(IntegrationError):
    """Integration validation error"""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            error_code="INTEGRATION_VALIDATION_ERROR",
            status_code=422,
            details={"field": field} if field else {}
        )


class IntegrationTestError(IntegrationError):
    """Integration testing error"""
    
    def __init__(self, message: str, test_results: dict = None):
        super().__init__(
            message=message,
            error_code="INTEGRATION_TEST_ERROR",
            status_code=400,
            details={"test_results": test_results} if test_results else {}
        )


class IntegrationPermissionError(IntegrationError):
    """Integration permission denied error"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="INTEGRATION_PERMISSION_DENIED",
            status_code=403
        )


class IntegrationConfigError(IntegrationError):
    """Integration configuration error"""
    
    def __init__(self, message: str, config_field: str = None):
        super().__init__(
            message=message,
            error_code="INTEGRATION_CONFIG_ERROR",
            status_code=400,
            details={"config_field": config_field} if config_field else {}
        )