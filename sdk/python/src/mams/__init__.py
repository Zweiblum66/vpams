"""
MAMS Python SDK

Official Python SDK for MAMS (Media Asset Management System)
"""

from .client import MAMSClient, AsyncMAMSClient
from .config import Config
from .exceptions import (
    MAMSError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
)
from .auth import OAuth2Provider, APIKeyAuth, JWTAuth

__version__ = "1.0.0"
__all__ = [
    "MAMSClient",
    "AsyncMAMSClient",
    "Config",
    "MAMSError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "OAuth2Provider",
    "APIKeyAuth",
    "JWTAuth",
]