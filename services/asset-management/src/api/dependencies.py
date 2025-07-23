"""
API Dependencies for Asset Management Service

This module provides shared dependencies for API routes.
"""

from typing import Optional, Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import InvalidTokenError

from ..db.base import AsyncSessionLocal
from ..core.config import get_settings
from ..core.exceptions import UnauthorizedError
from ..db.sharding import get_replica_aware_session
from ..db.read_replicas import ReadPreference
from ..core.sharding_config import load_sharding_config


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(
    authorization: Annotated[Optional[str], Header()] = None
) -> UUID:
    """
    Extract user ID from JWT token
    
    This is a simplified version - in production, this would validate
    the token with the User Management Service
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        # Extract bearer token
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        
        # Decode JWT token
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return UUID(user_id)
        
    except (ValueError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


class PaginationParams:
    """Common pagination parameters"""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1"
            )
        
        if page_size < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be >= 1"
            )
        
        if page_size > max_page_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page size must be <= {max_page_size}"
            )
        
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


async def get_read_db():
    """Get database session optimized for read operations"""
    config = load_sharding_config()
    
    if config.enabled:
        # For sharded setup, we'll return regular DB for now
        # The actual read replica routing will be handled by the service layer
        # which has access to the shard key (e.g., project_id)
        async with AsyncSessionLocal() as session:
            yield session
    else:
        # Fall back to regular database session
        async with AsyncSessionLocal() as session:
            yield session


async def get_write_db():
    """Get database session for write operations"""
    # For now, both read and write use the same session
    # The actual sharding logic is handled by the service layer
    async with AsyncSessionLocal() as session:
        yield session