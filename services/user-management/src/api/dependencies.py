"""
FastAPI dependencies for User Management Service

Common dependencies used across API endpoints.
"""

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
import logging

from db.base import AsyncSessionLocal
from db.models import User, Role, Permission
from core.security import verify_token, get_password_hash, TokenData
from core.config import get_settings
from models.schemas import PaginationParams, SortParams, FilterParams
from services.rbac_service import RBACService

logger = logging.getLogger(__name__)
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncSession:
    """Database dependency"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify and decode token
        token_data = verify_token(token)
        if token_data is None:
            raise credentials_exception
            
        user_id = token_data.sub
        if user_id is None:
            raise credentials_exception
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User)
        .where(User.id == UUID(user_id))
        .where(User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_permission(permission_name: str, include_inherited: bool = True):
    """
    Dependency factory for permission-based access control with inheritance support
    
    Args:
        permission_name: Required permission name (e.g., 'asset:read', 'user:write')
        include_inherited: Include permissions from parent roles
    """
    async def check_permission(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        try:
            # Use RBAC service for proper permission checking
            rbac_service = RBACService()
            has_permission = await rbac_service.check_user_permission(
                db, current_user.id, permission_name, include_inherited
            )
            
            if not has_permission:
                logger.warning(f"User {current_user.email} denied access - missing permission: {permission_name}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission_name}' required"
                )
            
            logger.debug(f"User {current_user.email} granted access - permission: {permission_name}")
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check failed for {permission_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return check_permission


def require_role(role_name: str, include_inherited: bool = True):
    """
    Dependency factory for role-based access control with inheritance support
    
    Args:
        role_name: Required role name
        include_inherited: Include roles from parent hierarchy
    """
    async def check_role(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        try:
            # Load user roles with relationships
            await db.refresh(current_user, ["roles"])
            
            # Check direct roles
            user_roles = {role.name for role in current_user.roles if role.is_active}
            
            # Check inheritance if requested
            if include_inherited:
                rbac_service = RBACService()
                for role in current_user.roles:
                    if role.parent_role_id:
                        parent_role = await rbac_service.get_role_by_id(db, role.parent_role_id)
                        if parent_role and parent_role.name == role_name:
                            user_roles.add(parent_role.name)
            
            if role_name not in user_roles:
                logger.warning(f"User {current_user.email} denied access - missing role: {role_name}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role_name}' required"
                )
            
            logger.debug(f"User {current_user.email} granted access - role: {role_name}")
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Role check failed for {role_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role check failed"
            )
    
    return check_role


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """Get pagination parameters"""
    return PaginationParams(page=page, limit=limit)


async def get_sort_params(
    sort: Optional[str] = Query("created_at", description="Sort field"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Sort order")
) -> SortParams:
    """Get sorting parameters"""
    return SortParams(sort=sort, order=order)


async def get_filter_params(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    role: Optional[str] = Query(None, description="Filter by role name"),
    department: Optional[str] = Query(None, description="Filter by department"),
    organization: Optional[str] = Query(None, description="Filter by organization")
) -> FilterParams:
    """Get filter parameters"""
    return FilterParams(
        is_active=is_active,
        is_verified=is_verified,
        role=role,
        department=department,
        organization=organization
    )


async def get_current_user_or_none(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user or None if not authenticated"""
    if not token:
        return None
    
    try:
        token_data = verify_token(token)
        if token_data is None:
            return None
            
        user_id = token_data.sub
        if user_id is None:
            return None
            
        result = await db.execute(
            select(User)
            .where(User.id == UUID(user_id))
            .where(User.is_active == True)
        )
        user = result.scalar_one_or_none()
        return user
        
    except Exception as e:
        logger.error(f"Optional auth failed: {e}")
        return None


async def require_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require superuser privileges"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user


async def require_verified_email(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require verified email address"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


def require_any_permission(*permission_names: str, include_inherited: bool = True):
    """
    Dependency factory that requires ANY of the specified permissions
    
    Args:
        *permission_names: List of permission names (user needs at least one)
        include_inherited: Include permissions from parent roles
    """
    async def check_any_permission(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        try:
            rbac_service = RBACService()
            
            # Check each permission until one is found
            for permission_name in permission_names:
                has_permission = await rbac_service.check_user_permission(
                    db, current_user.id, permission_name, include_inherited
                )
                if has_permission:
                    logger.debug(f"User {current_user.email} granted access - permission: {permission_name}")
                    return current_user
            
            # No permissions found
            logger.warning(f"User {current_user.email} denied access - missing any of: {', '.join(permission_names)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following permissions required: {', '.join(permission_names)}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check failed for {permission_names}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return check_any_permission


def require_all_permissions(*permission_names: str, include_inherited: bool = True):
    """
    Dependency factory that requires ALL of the specified permissions
    
    Args:
        *permission_names: List of permission names (user needs all of them)
        include_inherited: Include permissions from parent roles
    """
    async def check_all_permissions(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        try:
            rbac_service = RBACService()
            
            # Check all permissions
            for permission_name in permission_names:
                has_permission = await rbac_service.check_user_permission(
                    db, current_user.id, permission_name, include_inherited
                )
                if not has_permission:
                    logger.warning(f"User {current_user.email} denied access - missing permission: {permission_name}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission '{permission_name}' required"
                    )
            
            logger.debug(f"User {current_user.email} granted access - all permissions: {', '.join(permission_names)}")
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check failed for {permission_names}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return check_all_permissions


def require_resource_permission(resource: str, action: str, include_inherited: bool = True):
    """
    Dependency factory for resource-action based permissions
    
    Args:
        resource: Resource name (e.g., 'asset', 'user', 'project')
        action: Action name (e.g., 'read', 'write', 'delete')
        include_inherited: Include permissions from parent roles
    """
    permission_name = f"{resource}:{action}"
    return require_permission(permission_name, include_inherited)


async def get_user_permissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    Get all permissions for the current user
    """
    try:
        rbac_service = RBACService()
        permissions = await rbac_service.get_user_permissions(db, current_user.id)
        return list(permissions)
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        return []


async def get_user_roles(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    Get all roles for the current user
    """
    try:
        await db.refresh(current_user, ["roles"])
        return [role.name for role in current_user.roles if role.is_active]
    except Exception as e:
        logger.error(f"Failed to get user roles: {e}")
        return []


def check_ownership_or_permission(permission_name: str, user_id_field: str = "user_id"):
    """
    Dependency factory that checks if user owns resource OR has permission
    
    Args:
        permission_name: Permission needed if not owner
        user_id_field: Field name that contains the owner user ID
    """
    async def check_ownership_or_perm(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        **kwargs
    ) -> User:
        try:
            # Check if user owns the resource
            resource_user_id = kwargs.get(user_id_field)
            if resource_user_id and str(current_user.id) == str(resource_user_id):
                logger.debug(f"User {current_user.email} granted access - resource owner")
                return current_user
            
            # Check permission
            rbac_service = RBACService()
            has_permission = await rbac_service.check_user_permission(
                db, current_user.id, permission_name, True
            )
            
            if not has_permission:
                logger.warning(f"User {current_user.email} denied access - not owner and missing permission: {permission_name}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Resource ownership or permission '{permission_name}' required"
                )
            
            logger.debug(f"User {current_user.email} granted access - permission: {permission_name}")
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ownership/permission check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Access check failed"
            )
    
    return check_ownership_or_perm