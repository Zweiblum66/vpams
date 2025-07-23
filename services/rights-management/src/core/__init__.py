"""
Rights Management Service - Core Module
"""

from .config import settings
from .database import get_db, init_db
from .auth import get_current_user, require_permission
from .logger import get_logger, setup_logging
from .exceptions import (
    RightsManagementError,
    LicenseNotFoundError,
    ComplianceError,
    RestrictionError,
    GeoBlockingError,
    UsageLimitExceededError,
    ValidationError,
    BlockchainError,
    SmartContractError
)

__all__ = [
    # Config
    "settings",
    
    # Database
    "get_db",
    "init_db",
    
    # Auth
    "get_current_user",
    "require_permission",
    
    # Logging
    "get_logger",
    "setup_logging",
    
    # Exceptions
    "RightsManagementError",
    "LicenseNotFoundError",
    "ComplianceError",
    "RestrictionError",
    "GeoBlockingError",
    "UsageLimitExceededError",
    "ValidationError",
    "BlockchainError",
    "SmartContractError"
]