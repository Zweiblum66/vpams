"""
API Dependencies

Common dependencies for API endpoints including authentication and permissions.
"""

from typing import Dict, List, Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from core.security import token_manager
from core.exceptions import AuthenticationException, AuthorizationException
from core.redis import get_cache
from core.logging import get_logger

logger = get_logger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Dict[str, any]:
    """
    Get current authenticated user from JWT token
    
    Args:
        request: FastAPI request object
        token: JWT token from Authorization header
        
    Returns:
        Dictionary with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        # Check for API key as alternative
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # TODO: Implement API key validation
            return {
                "user_id": "api_key_user",
                "username": "api_key",
                "permissions": ["api_access"],
                "auth_method": "api_key"
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify JWT token
        payload = token_manager.verify_token(token, "access")
        
        # Check if token is blacklisted
        cache = await get_cache()
        if await cache.exists(f"blacklist:{token}"):
            raise AuthenticationException("Token has been revoked")
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("sub"),
            "permissions": payload.get("permissions", []),
            "auth_method": "jwt"
        }
        
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, any]:
    """
    Get current active user (non-disabled)
    
    Args:
        current_user: Current user from token
        
    Returns:
        User dictionary if active
        
    Raises:
        HTTPException: If user is disabled
    """
    # TODO: Check if user is active in database
    # For now, assume all authenticated users are active
    return current_user


def require_permissions(*required_permissions: str) -> Callable:
    """
    Dependency factory for requiring specific permissions
    
    Args:
        *required_permissions: List of required permissions
        
    Returns:
        Dependency function that checks permissions
        
    Example:
        @router.get("/admin", dependencies=[Depends(require_permissions("admin.read"))])
    """
    async def permission_checker(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_permissions = set(current_user.get("permissions", []))
        required = set(required_permissions)
        
        # Check if user has all required permissions
        if not required.issubset(user_permissions):
            missing = required - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}"
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(*permissions: str) -> Callable:
    """
    Dependency factory for requiring any of the specified permissions
    
    Args:
        *permissions: List of permissions (user needs at least one)
        
    Returns:
        Dependency function that checks permissions
    """
    async def permission_checker(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_permissions = set(current_user.get("permissions", []))
        
        # Check if user has any of the required permissions
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(permissions)}"
            )
        
        return current_user
    
    return permission_checker


class PermissionChecker:
    """
    Class-based permission checker for more complex scenarios
    """
    
    def __init__(self, permissions: List[str], require_all: bool = True):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(
        self,
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_permissions = set(current_user.get("permissions", []))
        required = set(self.permissions)
        
        if self.require_all:
            # User must have all permissions
            if not required.issubset(user_permissions):
                missing = required - user_permissions
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(missing)}"
                )
        else:
            # User must have at least one permission
            if not any(perm in user_permissions for perm in self.permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {', '.join(self.permissions)}"
                )
        
        return current_user


# Pre-defined permission checkers for common scenarios
is_admin = PermissionChecker(["admin", "super_admin"], require_all=False)
can_read_assets = PermissionChecker(["assets.read", "assets.write", "admin"], require_all=False)
can_write_assets = PermissionChecker(["assets.write", "admin"], require_all=False)
can_manage_users = PermissionChecker(["users.admin", "admin"], require_all=False)


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Dict[str, any]]:
    """
    Get current user if authenticated, None otherwise
    
    Useful for endpoints that have different behavior for authenticated users
    
    Args:
        request: FastAPI request object
        token: JWT token from Authorization header
        
    Returns:
        User dictionary or None
    """
    if not token:
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # TODO: Implement API key validation
            return {
                "user_id": "api_key_user",
                "username": "api_key",
                "permissions": ["api_access"],
                "auth_method": "api_key"
            }
        return None
    
    try:
        payload = token_manager.verify_token(token, "access")
        
        # Check if token is blacklisted
        cache = await get_cache()
        if await cache.exists(f"blacklist:{token}"):
            return None
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("sub"),
            "permissions": payload.get("permissions", []),
            "auth_method": "jwt"
        }
    except Exception:
        return None


# Usage examples in comments:
"""
Example usage in routes:

from fastapi import APIRouter, Depends
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_permissions,
    is_admin,
    can_write_assets
)

router = APIRouter()

# Require authentication
@router.get("/profile")
async def get_profile(current_user: Dict = Depends(get_current_user)):
    return current_user

# Require specific permission
@router.post("/assets")
async def create_asset(
    data: dict,
    current_user: Dict = Depends(require_permissions("assets.write"))
):
    # Only users with assets.write permission can access
    pass

# Require admin role
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict = Depends(is_admin)
):
    # Only admins can delete users
    pass

# Optional authentication
@router.get("/public-assets")
async def list_assets(
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    if current_user:
        # Return more data for authenticated users
        return {"assets": [...], "private_data": [...]}
    else:
        # Return public data only
        return {"assets": [...]}
"""