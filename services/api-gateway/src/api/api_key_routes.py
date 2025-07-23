"""
API Key Management Routes

Provides endpoints for creating, managing, and monitoring API keys.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from db.base import get_db
from services.api_key_service import APIKeyService
from core.api_key_auth import require_api_key, require_api_key_scopes
from core.auth import get_current_active_user
from models.user import User
from schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyUpdate,
    APIKeyRotateResponse,
    APIKeyUsageStats
)
from core.exceptions import NotFoundException, ValidationException
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new API key
    
    Requires authentication via JWT token.
    The created key will be associated with the current user.
    
    **Important**: The raw API key is only returned once during creation.
    Store it securely as it cannot be retrieved later.
    """
    service = APIKeyService(db)
    
    try:
        # Create the API key
        api_key, raw_key = await service.create_api_key(
            name=key_data.name,
            description=key_data.description,
            user_id=str(current_user.id),
            application_id=key_data.application_id,
            scopes=key_data.scopes,
            expires_in_days=key_data.expires_in_days,
            rate_limit_override=key_data.rate_limit_override,
            metadata=key_data.metadata
        )
        
        # Return response with raw key
        return APIKeyResponse(
            id=str(api_key.id),
            key=raw_key,  # Only returned on creation
            name=api_key.name,
            description=api_key.description,
            prefix=api_key.prefix,
            last_four=api_key.last_four,
            scopes=api_key.scopes,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List API keys for the current user
    
    Returns a paginated list of API keys associated with the authenticated user.
    """
    service = APIKeyService(db)
    
    # Get keys for current user
    keys, total_count = await service.list_api_keys(
        user_id=str(current_user.id),
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    # Convert to response models
    key_responses = [
        APIKeyResponse(
            id=str(key.id),
            key=None,  # Never return raw key in list
            name=key.name,
            description=key.description,
            prefix=key.prefix,
            last_four=key.last_four,
            scopes=key.scopes,
            expires_at=key.expires_at,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            usage_count=key.usage_count
        )
        for key in keys
    ]
    
    return APIKeyListResponse(
        items=key_responses,
        total=total_count,
        skip=skip,
        limit=limit
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific API key
    
    Returns detailed information about an API key.
    Only the owner can view their key details.
    """
    service = APIKeyService(db)
    
    try:
        api_key = await service.get_api_key(key_id)
        
        # Check ownership
        if api_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this API key"
            )
        
        return APIKeyResponse(
            id=str(api_key.id),
            key=None,  # Never return raw key
            name=api_key.name,
            description=api_key.description,
            prefix=api_key.prefix,
            last_four=api_key.last_four,
            scopes=api_key.scopes,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count,
            metadata=api_key.metadata
        )
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    update_data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an API key
    
    Allows updating name, description, scopes, rate limits, and metadata.
    Only the owner can update their key.
    """
    service = APIKeyService(db)
    
    try:
        # Get the key first to check ownership
        api_key = await service.get_api_key(key_id)
        
        if api_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this API key"
            )
        
        # Update the key
        updated_key = await service.update_api_key(
            key_id=key_id,
            name=update_data.name,
            description=update_data.description,
            scopes=update_data.scopes,
            rate_limit_override=update_data.rate_limit_override,
            metadata=update_data.metadata
        )
        
        return APIKeyResponse(
            id=str(updated_key.id),
            key=None,
            name=updated_key.name,
            description=updated_key.description,
            prefix=updated_key.prefix,
            last_four=updated_key.last_four,
            scopes=updated_key.scopes,
            expires_at=updated_key.expires_at,
            is_active=updated_key.is_active,
            created_at=updated_key.created_at,
            last_used_at=updated_key.last_used_at,
            usage_count=updated_key.usage_count,
            metadata=updated_key.metadata
        )
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    reason: Optional[str] = Query(None, description="Reason for revocation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Revoke an API key
    
    Immediately deactivates the API key. This action cannot be undone.
    Only the owner can revoke their key.
    """
    service = APIKeyService(db)
    
    try:
        # Get the key first to check ownership
        api_key = await service.get_api_key(key_id)
        
        if api_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to revoke this API key"
            )
        
        # Revoke the key
        await service.revoke_api_key(key_id, reason)
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{key_id}/rotate", response_model=APIKeyRotateResponse)
async def rotate_api_key(
    key_id: str,
    revoke_old: bool = Query(True, description="Whether to revoke the old key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Rotate an API key
    
    Creates a new API key with the same settings as the old one.
    By default, the old key is revoked immediately.
    
    **Important**: The raw API key is only returned once.
    Store it securely as it cannot be retrieved later.
    """
    service = APIKeyService(db)
    
    try:
        # Get the key first to check ownership
        old_key = await service.get_api_key(key_id)
        
        if old_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to rotate this API key"
            )
        
        # Rotate the key
        new_key, raw_key = await service.rotate_api_key(key_id, revoke_old)
        
        return APIKeyRotateResponse(
            old_key_id=key_id,
            old_key_revoked=revoke_old,
            new_key=APIKeyResponse(
                id=str(new_key.id),
                key=raw_key,  # Only returned on creation
                name=new_key.name,
                description=new_key.description,
                prefix=new_key.prefix,
                last_four=new_key.last_four,
                scopes=new_key.scopes,
                expires_at=new_key.expires_at,
                is_active=new_key.is_active,
                created_at=new_key.created_at,
                last_used_at=new_key.last_used_at,
                usage_count=new_key.usage_count
            )
        )
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.get("/{key_id}/usage", response_model=APIKeyUsageStats)
async def get_api_key_usage(
    key_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get usage statistics for an API key
    
    Returns detailed usage statistics including request counts,
    success rates, and response times.
    """
    service = APIKeyService(db)
    
    try:
        # Get the key first to check ownership
        api_key = await service.get_api_key(key_id)
        
        if api_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view usage for this API key"
            )
        
        # Get usage stats
        stats = await service.get_api_key_usage_stats(key_id, days)
        
        return APIKeyUsageStats(**stats)
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


# Admin endpoints (require admin scope)

@router.get("/admin/all", response_model=APIKeyListResponse)
async def list_all_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    application_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_api_key_scopes("admin"))
):
    """
    List all API keys (admin only)
    
    Returns a paginated list of all API keys in the system.
    Requires admin scope.
    """
    service = APIKeyService(db)
    
    # Get all keys with optional filters
    keys, total_count = await service.list_api_keys(
        user_id=user_id,
        application_id=application_id,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    # Convert to response models
    key_responses = [
        APIKeyResponse(
            id=str(key.id),
            key=None,  # Never return raw key
            name=key.name,
            description=key.description,
            prefix=key.prefix,
            last_four=key.last_four,
            scopes=key.scopes,
            expires_at=key.expires_at,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            usage_count=key.usage_count,
            user_id=str(key.user_id) if key.user_id else None,
            application_id=str(key.application_id) if key.application_id else None
        )
        for key in keys
    ]
    
    return APIKeyListResponse(
        items=key_responses,
        total=total_count,
        skip=skip,
        limit=limit
    )


@router.delete("/admin/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_revoke_api_key(
    key_id: str,
    reason: str = Query(..., description="Reason for revocation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_api_key_scopes("admin"))
):
    """
    Revoke any API key (admin only)
    
    Allows administrators to revoke any API key in the system.
    Requires admin scope and a reason must be provided.
    """
    service = APIKeyService(db)
    
    try:
        # Admin can revoke any key
        await service.revoke_api_key(key_id, f"Admin revocation: {reason}")
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
