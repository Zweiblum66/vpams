"""
API Dependencies for Proxy Generation Service
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status, Header, Request
import jwt
from jwt import PyJWTError

from ..core.config import settings
from ..core.logging import get_logger
from ..services.queue_service import QueueService
from ..services.storage_service import StorageService
from ..services.proxy_processor import ProxyProcessor

logger = get_logger(__name__)


async def get_current_user(authorization: Annotated[str, Header()] = None) -> dict:
    """Get current user from JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extract token
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", [])
        }
        
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_queue_service(request: Request) -> QueueService:
    """Get queue service from app state"""
    return request.app.state.queue_service


def get_storage_service(request: Request) -> StorageService:
    """Get storage service from app state"""
    return request.app.state.storage_service


def get_proxy_processor(request: Request) -> ProxyProcessor:
    """Get proxy processor from app state"""
    return request.app.state.proxy_processor


def require_role(required_role: str):
    """Require specific role for endpoint access"""
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_user)]
    ) -> dict:
        if required_role not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    
    return role_checker