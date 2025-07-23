"""
Custom exceptions for Metadata Service
"""


class MetadataServiceError(Exception):
    """Base exception for metadata service"""
    pass


class NotFoundError(MetadataServiceError):
    """Resource not found"""
    pass


class ValidationError(MetadataServiceError):
    """Validation error"""
    pass


class DuplicateError(MetadataServiceError):
    """Duplicate resource error"""
    pass


class SchemaValidationError(ValidationError):
    """Schema validation failed"""
    pass


class ExtractionError(MetadataServiceError):
    """Metadata extraction failed"""
    pass


class StorageError(MetadataServiceError):
    """Storage operation failed"""
    pass


class AuthenticationError(MetadataServiceError):
    """Authentication failed"""
    pass


class AuthorizationError(MetadataServiceError):
    """Authorization failed"""
    pass


class ServiceUnavailableError(MetadataServiceError):
    """External service unavailable"""
    pass


class ConfigurationError(MetadataServiceError):
    """Configuration error"""
    pass