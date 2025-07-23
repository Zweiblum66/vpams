"""
Authentication and authorization utilities
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get the current authenticated user from JWT token"""
    
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        
        # Extract user information
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # In production, fetch full user details from database
        # For now, return the token payload
        return {
            "id": user_id,
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, current_user: Dict = Depends(get_current_user), **kwargs):
            if permission not in current_user.get("permissions", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """Decorator to require specific role"""
    def decorator(func):
        async def wrapper(*args, current_user: Dict = Depends(get_current_user), **kwargs):
            if role not in current_user.get("roles", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator