"""
API Dependencies for Plugin Service
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any

from ..core.plugin_manager import PluginManager
from ..core.plugin_registry import PluginRegistry
from ..core.logging import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()

# Global instances (initialized in main.py)
_plugin_manager: Optional[PluginManager] = None
_plugin_registry: Optional[PluginRegistry] = None


def set_plugin_manager(manager: PluginManager):
    """Set the global plugin manager instance"""
    global _plugin_manager
    _plugin_manager = manager


def set_plugin_registry(registry: PluginRegistry):
    """Set the global plugin registry instance"""
    global _plugin_registry
    _plugin_registry = registry


async def get_plugin_manager() -> PluginManager:
    """Get the plugin manager instance"""
    if _plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized")
    return _plugin_manager


async def get_plugin_registry() -> PluginRegistry:
    """Get the plugin registry instance"""
    if _plugin_registry is None:
        raise RuntimeError("Plugin registry not initialized")
    return _plugin_registry


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get the current authenticated user"""
    # TODO: Implement actual JWT validation
    # For now, return a mock user
    return {
        "id": "user_123",
        "tenant_id": "tenant_123",
        "username": "test_user",
        "is_superuser": True,  # For development
        "permissions": ["plugin.read", "plugin.write", "plugin.admin"]
    }


async def require_permission(permission: str):
    """Require a specific permission"""
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


async def require_superuser(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require superuser privileges"""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user