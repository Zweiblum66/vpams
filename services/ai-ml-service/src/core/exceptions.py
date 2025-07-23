"""
Custom exceptions for AI/ML Service
"""

class AIMLServiceException(Exception):
    """Base exception class for AI/ML service."""
    pass


class ModelLoadError(AIMLServiceException):
    """Exception raised when model loading fails."""
    pass


class ModelNotFoundError(AIMLServiceException):
    """Exception raised when requested model is not found."""
    pass


class InferenceError(AIMLServiceException):
    """Exception raised during model inference."""
    pass


class ValidationError(AIMLServiceException):
    """Exception raised for input validation errors."""
    pass


class ProcessingError(AIMLServiceException):
    """Exception raised during media processing."""
    pass


class ResourceError(AIMLServiceException):
    """Exception raised for resource-related errors."""
    pass


class ConfigurationError(AIMLServiceException):
    """Exception raised for configuration-related errors."""
    pass


class CacheError(AIMLServiceException):
    """Exception raised for cache-related errors."""
    pass


class QueueError(AIMLServiceException):
    """Exception raised for queue-related errors."""
    pass