"""
Shared dependencies for API endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import logging

from src.core.config import settings
from src.models.schemas import User
from src.db.mongodb import get_database

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


async def get_db():
    """
    Get MongoDB database instance
    """
    try:
        db = await get_database()
        yield db
    finally:
        # MongoDB motor client handles connection pooling automatically
        pass


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Validate JWT token and return current user
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # TODO: Verify user exists in User Management Service
        # For now, return a mock user
        return User(
            id=user_id,
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", [])
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the current user is active
    """
    # TODO: Check if user is active
    return current_user


def check_permission(permission: str):
    """
    Dependency to check if user has specific permission
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return permission_checker


def check_role(role: str):
    """
    Dependency to check if user has specific role
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        if role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return role_checker