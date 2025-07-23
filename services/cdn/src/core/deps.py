"""
Dependencies for CDN service
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from datetime import datetime

from ..db.base import get_db
from ..core.config import settings
from ..models.database import User
from ..services.cdn_manager import GlobalCDNManager

# Security scheme
security = HTTPBearer()

# Global CDN manager instance
_cdn_manager: Optional[GlobalCDNManager] = None


async def get_cdn_manager() -> GlobalCDNManager:
    """Get CDN manager instance"""
    global _cdn_manager
    
    if _cdn_manager is None:
        _cdn_manager = GlobalCDNManager()
        await _cdn_manager.initialize()
    
    return _cdn_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In a real implementation, fetch user from database
    # For now, return a mock user
    user = User(
        id=user_id,
        username="admin",
        email="admin@mams.io"
    )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    # In a real implementation, check if user is active
    return current_user