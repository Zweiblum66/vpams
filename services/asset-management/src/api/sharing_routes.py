"""
API routes for Container Sharing operations

This module defines all REST API endpoints for container sharing management.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .dependencies import get_db, get_current_user_id, PaginationParams
from ..services.sharing_service import ContainerSharingService
from ..models.schemas import (
    ContainerShareCreate, ContainerShareUpdate, ContainerShareResponse,
    PaginatedResponse
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError,
    PermissionError
)

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/v1/shares", tags=["container-sharing"])


@router.post("/", response_model=ContainerShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    share_data: ContainerShareCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Share a container with a user or group
    
    Grants specific permissions to access a container. The user creating
    the share must either own the container or have share permission.
    
    Permission hierarchy (higher includes lower):
    - can_view: Basic read access
    - can_add_assets: Can add new assets to the container
    - can_edit: Can modify container properties and assets
    - can_delete: Can delete assets and sub-containers
    - can_share: Can share the container with others
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        return await service.create_share(share_data)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateResourceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("share_creation_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create share")


@router.get("/", response_model=PaginatedResponse)
async def list_user_shares(
    pagination: PaginationParams = Depends(),
    share_type: Optional[str] = Query(None, pattern="^(received|given)$", description="Filter by share type"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List shares for the current user
    
    Returns shares based on share_type:
    - received: Containers shared with the user
    - given: Containers shared by the user
    - None: All shares involving the user
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        return await service.list_user_shares(
            pagination=pagination,
            share_type=share_type
        )
        
    except Exception as e:
        logger.error("share_listing_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list shares")


@router.get("/container/{container_id}", response_model=PaginatedResponse)
async def list_container_shares(
    container_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List all shares for a specific container
    
    Only the container owner or users with share permission can view
    the list of shares for a container.
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        return await service.list_container_shares(
            container_id=container_id,
            pagination=pagination
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_shares_listing_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list container shares")


@router.get("/{share_id}", response_model=ContainerShareResponse)
async def get_share(
    share_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get share details
    
    Returns detailed information about a specific share.
    Only visible to the share creator, recipient, or container owner.
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        share = await service.get_share(share_id)
        
        # Record access if user is the recipient
        if share.shared_with_id == current_user_id and share.shared_with_type == 'user':
            await service.record_access(share_id)
        
        return share
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("share_retrieval_failed", error=str(e), share_id=str(share_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve share")


@router.patch("/{share_id}", response_model=ContainerShareResponse)
async def update_share(
    share_id: UUID,
    update_data: ContainerShareUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update share permissions
    
    Modify the permissions or settings of an existing share.
    Only the container owner or users with share permission can update shares.
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        return await service.update_share(share_id, update_data)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("share_update_failed", error=str(e), share_id=str(share_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update share")


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    share_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Revoke a share
    
    Removes sharing permissions. Only the container owner or users with
    share permission can revoke shares.
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        await service.revoke_share(share_id)
        
        logger.info(
            "share_revoked",
            share_id=str(share_id),
            user_id=str(current_user_id)
        )
        
        return None
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("share_revocation_failed", error=str(e), share_id=str(share_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke share")


# Utility endpoints

@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_shares(
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Clean up expired shares
    
    Removes all shares that have passed their expiration date.
    This is typically called by a scheduled job, but can be triggered manually.
    
    Note: In production, this should be restricted to admin users.
    """
    try:
        service = ContainerSharingService(db, current_user_id)
        deleted_count = await service.cleanup_expired_shares()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Removed {deleted_count} expired shares"
        }
        
    except Exception as e:
        logger.error("share_cleanup_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cleanup expired shares")