"""
Security utilities for failover service
"""

from typing import List
from fastapi import HTTPException, status

from ..models.database import User


async def require_permission(user: User, permission: str):
    """Check if user has required permission"""
    # In a real implementation, check user permissions from database
    # For now, allow all permissions for authenticated users
    user_permissions = [
        "failover.read",
        "failover.execute",
        "failover.test",
        "failover.consistency",
        "failover.admin"
    ]
    
    if permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have permission: {permission}"
        )


async def require_permissions(user: User, permissions: List[str]):
    """Check if user has all required permissions"""
    for permission in permissions:
        await require_permission(user, permission)