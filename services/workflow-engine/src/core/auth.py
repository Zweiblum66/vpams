"""
Authentication utilities for Workflow Engine Service
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional
import jwt
from datetime import datetime, timedelta

from .config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, any]:
    """
    Get current user from JWT token.
    
    In a real implementation, this would:
    1. Validate the JWT token
    2. Extract user information
    3. Verify with user service
    
    For now, we'll return a mock user.
    """
    token = credentials.credentials
    
    try:
        # In production, validate JWT token
        # payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # Mock user for development
        return {
            "user_id": "user_123",
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["user", "approver"],
            "is_admin": False
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(
    current_user: Dict[str, any] = Depends(get_current_user)
) -> Dict[str, any]:
    """Verify current user is an admin"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # In production, use actual JWT encoding
    # encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    
    # Mock token for development
    return "mock_jwt_token"