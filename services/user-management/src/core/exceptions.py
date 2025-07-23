"""
Custom exceptions for User Management Service

This module defines all custom exceptions used throughout the
User Management Service for consistent error handling.
"""

from typing import Optional, Dict, Any


class UserManagementException(Exception):
    """Base exception for User Management Service"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class UserNotFoundError(UserManagementException):
    """Exception raised when a user is not found"""
    
    def __init__(self, user_id: Optional[str] = None, email: Optional[str] = None):
        identifier = user_id or email or "unknown"
        message = f"User not found: {identifier}"
        details = {}
        if user_id:
            details["user_id"] = user_id
        if email:
            details["email"] = email
        super().__init__(message, "USER_NOT_FOUND", details)


class UserAlreadyExistsError(UserManagementException):
    """Exception raised when attempting to create a user that already exists"""
    
    def __init__(self, email: str, username: Optional[str] = None):
        message = f"User already exists with email: {email}"
        details = {"email": email}
        if username:
            details["username"] = username
        super().__init__(message, "USER_ALREADY_EXISTS", details)


class InvalidCredentialsError(UserManagementException):
    """Exception raised when login credentials are invalid"""
    
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, "INVALID_CREDENTIALS")


class AccountLockedError(UserManagementException):
    """Exception raised when account is locked due to failed login attempts"""
    
    def __init__(self, locked_until: Optional[str] = None):
        message = "Account is locked due to failed login attempts"
        details = {}
        if locked_until:
            details["locked_until"] = locked_until
        super().__init__(message, "ACCOUNT_LOCKED", details)


class EmailNotVerifiedError(UserManagementException):
    """Exception raised when email is not verified"""
    
    def __init__(self, email: str):
        message = f"Email not verified: {email}"
        details = {"email": email}
        super().__init__(message, "EMAIL_NOT_VERIFIED", details)


class PermissionDeniedError(UserManagementException):
    """Exception raised when user lacks required permissions"""
    
    def __init__(self, required_permission: str, user_id: Optional[str] = None):
        message = f"Permission denied: {required_permission}"
        details = {"required_permission": required_permission}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, "PERMISSION_DENIED", details)


class RoleNotFoundError(UserManagementException):
    """Exception raised when a role is not found"""
    
    def __init__(self, role_id: Optional[str] = None, role_name: Optional[str] = None):
        identifier = role_id or role_name or "unknown"
        message = f"Role not found: {identifier}"
        details = {}
        if role_id:
            details["role_id"] = role_id
        if role_name:
            details["role_name"] = role_name
        super().__init__(message, "ROLE_NOT_FOUND", details)


class PermissionNotFoundError(UserManagementException):
    """Exception raised when a permission is not found"""
    
    def __init__(self, permission_id: Optional[str] = None, permission_name: Optional[str] = None):
        identifier = permission_id or permission_name or "unknown"
        message = f"Permission not found: {identifier}"
        details = {}
        if permission_id:
            details["permission_id"] = permission_id
        if permission_name:
            details["permission_name"] = permission_name
        super().__init__(message, "PERMISSION_NOT_FOUND", details)


class ValidationError(UserManagementException):
    """Exception raised when validation fails"""
    
    def __init__(self, message: str, field_errors: Optional[Dict[str, list]] = None):
        details = {}
        if field_errors:
            details["field_errors"] = field_errors
        super().__init__(message, "VALIDATION_ERROR", details)


class PasswordPolicyError(UserManagementException):
    """Exception raised when password doesn't meet policy requirements"""
    
    def __init__(self, message: str, requirements: Optional[Dict[str, bool]] = None):
        details = {}
        if requirements:
            details["requirements"] = requirements
        super().__init__(message, "PASSWORD_POLICY_ERROR", details)


class TokenExpiredError(UserManagementException):
    """Exception raised when token has expired"""
    
    def __init__(self, token_type: str = "token"):
        message = f"{token_type.capitalize()} has expired"
        details = {"token_type": token_type}
        super().__init__(message, "TOKEN_EXPIRED", details)


class TokenInvalidError(UserManagementException):
    """Exception raised when token is invalid"""
    
    def __init__(self, token_type: str = "token"):
        message = f"Invalid {token_type}"
        details = {"token_type": token_type}
        super().__init__(message, "TOKEN_INVALID", details)


class MFARequiredError(UserManagementException):
    """Exception raised when MFA is required"""
    
    def __init__(self, user_id: str):
        message = "Multi-factor authentication required"
        details = {"user_id": user_id}
        super().__init__(message, "MFA_REQUIRED", details)


class MFAInvalidError(UserManagementException):
    """Exception raised when MFA code is invalid"""
    
    def __init__(self, message: str = "Invalid MFA code"):
        super().__init__(message, "MFA_INVALID")


class SessionExpiredError(UserManagementException):
    """Exception raised when session has expired"""
    
    def __init__(self, session_id: Optional[str] = None):
        message = "Session has expired"
        details = {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, "SESSION_EXPIRED", details)


class SessionInvalidError(UserManagementException):
    """Exception raised when session is invalid"""
    
    def __init__(self, session_id: Optional[str] = None):
        message = "Invalid session"
        details = {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, "SESSION_INVALID", details)


class TooManySessionsError(UserManagementException):
    """Exception raised when user has too many active sessions"""
    
    def __init__(self, max_sessions: int, current_sessions: int):
        message = f"Too many active sessions. Maximum: {max_sessions}, Current: {current_sessions}"
        details = {
            "max_sessions": max_sessions,
            "current_sessions": current_sessions
        }
        super().__init__(message, "TOO_MANY_SESSIONS", details)


class ExternalAuthError(UserManagementException):
    """Exception raised when external authentication fails"""
    
    def __init__(self, provider: str, message: str = "External authentication failed"):
        full_message = f"{message} (provider: {provider})"
        details = {"provider": provider}
        super().__init__(full_message, "EXTERNAL_AUTH_ERROR", details)


class ConfigurationError(UserManagementException):
    """Exception raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, "CONFIGURATION_ERROR", details)


class DatabaseError(UserManagementException):
    """Exception raised when database operation fails"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, "DATABASE_ERROR", details)


class RateLimitExceededError(UserManagementException):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: int, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        details = {
            "limit": limit,
            "window": window
        }
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


class MFANotEnabledError(UserManagementException):
    """Exception raised when MFA operation is attempted but MFA is not enabled"""
    
    def __init__(self, message: str = "MFA is not enabled for this user"):
        super().__init__(message, "MFA_NOT_ENABLED")


class InvalidMFACodeError(UserManagementException):
    """Exception raised when MFA code is invalid"""
    
    def __init__(self, message: str = "Invalid MFA code"):
        super().__init__(message, "INVALID_MFA_CODE")


class MFAAlreadyEnabledError(UserManagementException):
    """Exception raised when attempting to enable MFA when it's already enabled"""
    
    def __init__(self, message: str = "MFA is already enabled for this user"):
        super().__init__(message, "MFA_ALREADY_ENABLED")