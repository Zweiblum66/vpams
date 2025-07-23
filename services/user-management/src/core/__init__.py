"""
Core package for User Management Service

This package contains core configuration, security, and utility modules.
"""

from .config import get_settings, Settings
from .exceptions import (
    UserManagementException,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    AccountLockedError,
    EmailNotVerifiedError,
    PermissionDeniedError,
    RoleNotFoundError,
    ValidationError
)

__all__ = [
    "get_settings",
    "Settings",
    "UserManagementException",
    "UserNotFoundError", 
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "EmailNotVerifiedError",
    "PermissionDeniedError",
    "RoleNotFoundError",
    "ValidationError"
]