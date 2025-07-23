"""
API routes for Project Container operations

This module defines all REST API endpoints for project container management.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .dependencies import get_db, get_current_user_id, PaginationParams
from ..services.project_service import ProjectContainerService
from ..models.schemas import (
    ProjectContainerCreate, ProjectContainerUpdate, ProjectContainerResponse,
    ProjectContainerTree, PaginatedResponse, ContainerType
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError,
    PermissionError, ConflictError
)

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/v1/containers", tags=["project-containers"])


@router.post("/", response_model=ProjectContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_container(
    container_data: ProjectContainerCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new project container
    
    Creates a new container of the specified type. For containers other than
    projects, a parent_id must be provided.
    
    Container type hierarchy:
    - PROJECT: Root level containers
    - FOLDER: Can contain other folders, bins, shotlists, or sequences
    - BIN: Contains shot items (clips)
    - SHOTLIST: Contains organized shot items
    - SEQUENCE: Contains timeline with arranged clips
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.create_container(container_data)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_creation_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create container")


@router.get("/", response_model=PaginatedResponse)
async def list_containers(
    pagination: PaginationParams = Depends(),
    container_type: Optional[ContainerType] = Query(None, description="Filter by container type"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent container"),
    search: Optional[str] = Query(None, description="Search in name, display_name, description"),
    include_children: bool = Query(False, description="Include children in tree structure"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List project containers
    
    Returns a paginated list of containers that the user has access to.
    Can filter by type, parent, or search term. Optionally returns
    containers in tree structure with children.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.list_containers(
            pagination=pagination,
            container_type=container_type,
            parent_id=parent_id,
            search=search,
            include_children=include_children
        )
        
    except Exception as e:
        logger.error("container_listing_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list containers")


@router.get("/{container_id}", response_model=ProjectContainerResponse)
async def get_container(
    container_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get container by ID
    
    Returns detailed information about a specific container.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.get_container(container_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_retrieval_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve container")


@router.get("/{container_id}/tree", response_model=ProjectContainerTree)
async def get_container_tree(
    container_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get container with full tree structure
    
    Returns the container and all its descendants in a hierarchical tree structure.
    Useful for displaying project organization in UI.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.get_container_tree(container_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_tree_retrieval_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve container tree")


@router.get("/{container_id}/breadcrumb")
async def get_container_breadcrumb(
    container_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get breadcrumb trail for a container
    
    Returns the path from the root to the specified container,
    useful for navigation breadcrumbs in the UI.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.get_breadcrumb(container_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("breadcrumb_retrieval_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve breadcrumb")


@router.patch("/{container_id}", response_model=ProjectContainerResponse)
async def update_container(
    container_id: UUID,
    update_data: ProjectContainerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update container properties
    
    Updates modifiable fields of a container. Only the container owner can update.
    Note: Container type and parent cannot be changed through this endpoint.
    Use the move endpoint to change parent.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.update_container(container_id, update_data)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_update_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update container")


@router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_container(
    container_id: UUID,
    force: bool = Query(False, description="Force delete even if container has children or assets"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a container
    
    By default performs a soft delete (marks as deleted but keeps data).
    Use force=true to permanently delete the container and all its contents.
    
    Warning: Force delete will remove all child containers and assets!
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        await service.delete_container(container_id, force)
        
        logger.info(
            "container_deleted",
            container_id=str(container_id),
            user_id=str(current_user_id),
            force=force
        )
        
        return None
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("container_deletion_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete container")


@router.post("/{container_id}/move", response_model=ProjectContainerResponse)
async def move_container(
    container_id: UUID,
    new_parent_id: Optional[UUID] = Query(None, description="New parent container ID (null for root)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Move container to a new parent
    
    Moves a container and all its contents to a new parent container.
    Set new_parent_id to null to move to root level (only for PROJECT type).
    
    The operation will fail if:
    - The move would create a circular reference
    - The container type is not allowed in the new parent
    - You don't have permission on both containers
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.move_container(container_id, new_parent_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_move_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to move container")


@router.post("/from-template", response_model=ProjectContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_from_template(
    template_id: UUID = Query(..., description="Template ID to use"),
    name: str = Query(..., description="Name for the new project"),
    parent_id: Optional[UUID] = Query(None, description="Parent container (for sub-projects)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create project from template
    
    Creates a new project container with pre-defined structure from a template.
    The template defines the folder hierarchy and default settings.
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        return await service.create_from_template(template_id, name, parent_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("template_creation_failed", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create from template")


# Container statistics endpoint
@router.get("/{container_id}/stats")
async def get_container_stats(
    container_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get container statistics
    
    Returns statistics about the container including:
    - Total assets count
    - Total size
    - Asset type breakdown
    - Child container counts by type
    - Recent activity
    """
    try:
        service = ProjectContainerService(db, current_user_id)
        container = await service.get_container(container_id)
        
        # TODO: Implement detailed statistics gathering
        # For now, return basic stats from the container response
        
        return {
            "container_id": container.id,
            "asset_count": container.asset_count,
            "child_count": container.child_count,
            "container_type": container.container_type,
            "created_at": container.created_at,
            "updated_at": container.updated_at
        }
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("container_stats_failed", error=str(e), container_id=str(container_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get container statistics")