"""
API package for User Management Service

This package contains FastAPI routes and dependencies.
"""

from .dependencies import (
    get_db,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_role,
    get_pagination_params,
    get_sort_params,
    get_filter_params
)

from .routes import router as api_router

__all__ = [
    "api_router",
    "get_db",
    "get_current_user", 
    "get_current_active_user",
    "require_permission",
    "require_role",
    "get_pagination_params",
    "get_sort_params",
    "get_filter_params"
]