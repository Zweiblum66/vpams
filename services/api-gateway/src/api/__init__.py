"""
API Gateway API Routes

Main API routing module for the API Gateway service.
"""

from .routes import api_router
from .health import health_router
from .auth import router as auth_router
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_permissions,
    require_any_permission,
    get_optional_user,
    PermissionChecker
)

__all__ = [
    "api_router",
    "health_router",
    "auth_router",
    "get_current_user",
    "get_current_active_user",
    "require_permissions",
    "require_any_permission",
    "get_optional_user",
    "PermissionChecker"
]