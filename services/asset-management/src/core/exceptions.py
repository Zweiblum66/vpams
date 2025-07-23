"""
Custom exceptions for Asset Management Service

This module defines service-specific exceptions.
"""


class AssetManagementError(Exception):
    """Base exception for Asset Management Service"""
    pass


class AssetNotFoundError(AssetManagementError):
    """Raised when an asset is not found"""
    pass


class DuplicateAssetError(AssetManagementError):
    """Raised when attempting to create a duplicate asset"""
    pass


class StorageError(AssetManagementError):
    """Raised when storage operations fail"""
    pass


class ValidationError(AssetManagementError):
    """Raised when validation fails"""
    pass


class QuotaExceededError(AssetManagementError):
    """Raised when storage quota is exceeded"""
    pass


class PermissionError(AssetManagementError):
    """Raised when user lacks required permissions"""
    pass


class UnauthorizedError(AssetManagementError):
    """Raised when authentication fails"""
    pass


class ResourceNotFoundError(AssetManagementError):
    """Raised when a requested resource is not found"""
    pass


class DuplicateResourceError(AssetManagementError):
    """Raised when attempting to create a duplicate resource"""
    pass


class ConflictError(AssetManagementError):
    """Raised when an operation would cause a conflict"""
    pass


class ServiceUnavailableError(AssetManagementError):
    """Raised when a required service is unavailable"""
    pass