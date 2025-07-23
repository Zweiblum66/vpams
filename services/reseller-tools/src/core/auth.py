"""Authentication and authorization utilities"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from datetime import datetime
from typing import Optional
import httpx
import logging

from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer()


class User:
    """User model for authentication"""
    def __init__(self, id: str, email: str, roles: list = None):
        self.id = id
        self.email = email
        self.roles = roles or []


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        return User(id=user_id, email=email, roles=roles)
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_reseller_user(current_user: User = Depends(get_current_user)) -> User:
    """Require reseller role"""
    if "reseller" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reseller access required"
        )
    return current_user


async def validate_user_with_external_service(user_id: str) -> Optional[dict]:
    """Validate user with User Management Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.user_management_url}/api/v1/users/{user_id}",
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"User validation failed: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error validating user with external service: {e}")
        return None