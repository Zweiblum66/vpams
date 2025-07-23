"""
Custom exceptions for White-Label Service
"""

from fastapi import HTTPException, status


class WhiteLabelException(Exception):
    """Base exception for white-label service"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ThemeNotFoundError(WhiteLabelException):
    """Raised when a theme is not found"""
    pass


class BrandingNotFoundError(WhiteLabelException):
    """Raised when branding configuration is not found"""
    pass


class DomainNotFoundError(WhiteLabelException):
    """Raised when a custom domain is not found"""
    pass


class TemplateNotFoundError(WhiteLabelException):
    """Raised when an email template is not found"""
    pass


class MobileAppNotFoundError(WhiteLabelException):
    """Raised when mobile app configuration is not found"""
    pass


class InvalidConfigurationError(WhiteLabelException):
    """Raised when configuration is invalid"""
    pass


class DuplicateResourceError(WhiteLabelException):
    """Raised when trying to create a duplicate resource"""
    pass


class PermissionDeniedError(WhiteLabelException):
    """Raised when user doesn't have permission"""
    pass


class ResourceLimitExceededError(WhiteLabelException):
    """Raised when resource limits are exceeded"""
    pass


class FileUploadError(WhiteLabelException):
    """Raised when file upload fails"""
    pass


class ThemeValidationError(WhiteLabelException):
    """Raised when theme validation fails"""
    pass


class DomainValidationError(WhiteLabelException):
    """Raised when domain validation fails"""
    pass


class SSLProvisioningError(WhiteLabelException):
    """Raised when SSL provisioning fails"""
    pass


def theme_not_found_exception(theme_id: str):
    """Create HTTP exception for theme not found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Theme {theme_id} not found"
    )


def branding_not_found_exception(tenant_id: str):
    """Create HTTP exception for branding not found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Branding configuration for tenant {tenant_id} not found"
    )


def domain_not_found_exception(domain: str):
    """Create HTTP exception for domain not found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Domain {domain} not found"
    )


def template_not_found_exception(template_id: str):
    """Create HTTP exception for template not found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Email template {template_id} not found"
    )


def mobile_app_not_found_exception(app_id: str):
    """Create HTTP exception for mobile app not found"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Mobile app configuration {app_id} not found"
    )


def invalid_configuration_exception(message: str):
    """Create HTTP exception for invalid configuration"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid configuration: {message}"
    )


def duplicate_resource_exception(resource: str, identifier: str):
    """Create HTTP exception for duplicate resource"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{resource} with identifier {identifier} already exists"
    )


def permission_denied_exception(action: str):
    """Create HTTP exception for permission denied"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied for action: {action}"
    )


def resource_limit_exceeded_exception(resource: str, limit: int):
    """Create HTTP exception for resource limit exceeded"""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"{resource} limit of {limit} exceeded"
    )


def file_upload_exception(message: str):
    """Create HTTP exception for file upload error"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"File upload error: {message}"
    )


def theme_validation_exception(errors: list):
    """Create HTTP exception for theme validation error"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Theme validation failed: {errors}"
    )


def domain_validation_exception(domain: str, message: str):
    """Create HTTP exception for domain validation error"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Domain validation failed for {domain}: {message}"
    )


def ssl_provisioning_exception(domain: str, message: str):
    """Create HTTP exception for SSL provisioning error"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"SSL provisioning failed for {domain}: {message}"
    )