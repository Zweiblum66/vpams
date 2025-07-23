"""Custom exceptions for the Reseller Tools Service"""


class ResellerToolsException(Exception):
    """Base exception for reseller tools service"""
    pass


class NotFoundError(ResellerToolsException):
    """Raised when a resource is not found"""
    pass


class ValidationError(ResellerToolsException):
    """Raised when validation fails"""
    pass


class DuplicateError(ResellerToolsException):
    """Raised when trying to create a duplicate resource"""
    pass


class AuthenticationError(ResellerToolsException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(ResellerToolsException):
    """Raised when user lacks permission for an action"""
    pass


class ExternalServiceError(ResellerToolsException):
    """Raised when external service call fails"""
    pass


class PaymentError(ResellerToolsException):
    """Raised when payment processing fails"""
    pass