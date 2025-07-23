"""
Shared dependencies for Partner Service API
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Dict, Any

from ..core.config import settings

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Extract and validate user from JWT token"""
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Return user information from token
        return {
            "id": user_id,
            "email": payload.get("email"),
            "name": payload.get("name"),
            "is_superuser": payload.get("is_superuser", False),
            "permissions": payload.get("permissions", [])
        }
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensure user has admin privileges"""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_partner_manager(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensure user can manage partners"""
    permissions = current_user.get("permissions", [])
    
    if not (current_user.get("is_superuser", False) or "partner_manager" in permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner management privileges required"
        )
    
    return current_user