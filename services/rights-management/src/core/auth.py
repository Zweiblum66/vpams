"""
Rights Management Service - Authentication
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
import httpx

from .config import settings
from .logger import get_logger
from ..models.schemas import User

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        email: str = payload.get("email")
        
        if user_id is None:
            raise credentials_exception
        
        # Create user object from token data
        user = User(
            user_id=user_id,
            username=username or f"user_{user_id}",
            email=email or f"{user_id}@example.com"
        )
        
        return user
        
    except JWTError:
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise credentials_exception


async def require_permission(permission: str):
    """Dependency to require specific permission"""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        # In a real implementation, check user permissions from database
        # For now, we'll assume all authenticated users have all permissions
        return current_user
    
    return permission_checker