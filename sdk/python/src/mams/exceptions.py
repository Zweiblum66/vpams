"""
SDK Exceptions
"""

from typing import Optional, Dict, Any
import httpx


class MAMSError(Exception):
    """Base exception for MAMS SDK"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[httpx.Response] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(MAMSError):
    """Authentication failed"""
    pass


class NotFoundError(MAMSError):
    """Resource not found"""
    pass


class ValidationError(MAMSError):
    """Request validation failed"""
    
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.errors = errors or {}


class RateLimitError(MAMSError):
    """Rate limit exceeded"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(MAMSError):
    """Server error (5xx)"""
    pass


class ConflictError(MAMSError):
    """Resource conflict (409)"""
    pass


class PermissionError(MAMSError):
    """Permission denied (403)"""
    pass


def handle_error_response(response: httpx.Response):
    """Handle error response from API"""
    try:
        error_data = response.json()
        message = error_data.get("message", "Unknown error")
        error_code = error_data.get("code")
        details = error_data.get("details", {})
    except:
        message = f"HTTP {response.status_code}: {response.text}"
        error_code = None
        details = {}
    
    # Map status codes to exceptions
    if response.status_code == 401:
        raise AuthenticationError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code == 403:
        raise PermissionError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code == 404:
        raise NotFoundError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code == 409:
        raise ConflictError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code == 422:
        validation_errors = details.get("errors", {})
        raise ValidationError(
            message,
            errors=validation_errors,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            message,
            retry_after=int(retry_after) if retry_after else None,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    elif response.status_code >= 500:
        raise ServerError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )
    else:
        raise MAMSError(
            message,
            status_code=response.status_code,
            response=response,
            error_code=error_code,
            details=details
        )