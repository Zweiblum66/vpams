"""
Rights Management Service - Custom Exceptions
"""


class RightsManagementError(Exception):
    """Base exception for rights management service"""
    pass


class LicenseNotFoundError(RightsManagementError):
    """Raised when a license is not found"""
    pass


class ComplianceError(RightsManagementError):
    """Raised when there's a compliance violation"""
    pass


class RestrictionError(RightsManagementError):
    """Raised when a restriction check fails"""
    pass


class GeoBlockingError(RightsManagementError):
    """Raised when geo-blocking check fails"""
    pass


class UsageLimitExceededError(RightsManagementError):
    """Raised when usage limits are exceeded"""
    pass


class ValidationError(RightsManagementError):
    """Raised when validation fails"""
    pass


class BlockchainError(RightsManagementError):
    """Raised when blockchain operations fail"""
    pass


class SmartContractError(RightsManagementError):
    """Raised when smart contract operations fail"""
    pass