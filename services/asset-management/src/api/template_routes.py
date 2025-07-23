"""
API routes for Project Template operations

This module defines all REST API endpoints for project template management.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .dependencies import get_db, get_current_user_id, PaginationParams
from ..services.template_service import ProjectTemplateService
from ..models.schemas import (
    ProjectTemplateCreate, ProjectTemplateUpdate, ProjectTemplateResponse,
    PaginatedResponse
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError,
    PermissionError
)

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/v1/templates", tags=["project-templates"])


@router.post("/", response_model=ProjectTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ProjectTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new project template
    
    Creates a new template that can be used to quickly create projects
    with predefined folder structures and settings.
    
    The structure field should contain a JSON object defining the hierarchy:
    ```json
    {
        "children": [
            {
                "name": "raw-footage",
                "display_name": "Raw Footage",
                "type": "folder",
                "children": [
                    {
                        "name": "camera-a",
                        "display_name": "Camera A",
                        "type": "bin"
                    }
                ]
            }
        ]
    }
    ```
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.create_template(template_data)
        
    except DuplicateResourceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("template_creation_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create template")


@router.get("/", response_model=PaginatedResponse)
async def list_templates(
    pagination: PaginationParams = Depends(),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    is_system: Optional[bool] = Query(None, description="Filter system templates"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List available project templates
    
    Returns templates that are:
    - Public templates
    - Templates owned by the current user
    - System templates (if is_system=True)
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.list_templates(
            pagination=pagination,
            category=category,
            search=search,
            is_system=is_system
        )
        
    except Exception as e:
        logger.error("template_listing_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list templates")


@router.get("/categories", response_model=List[str])
async def list_template_categories(
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get all available template categories
    
    Returns a list of unique category names used across all templates.
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.get_categories()
        
    except Exception as e:
        logger.error("category_listing_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list categories")


@router.get("/{template_id}", response_model=ProjectTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get template by ID
    
    Returns detailed information about a specific template including
    its structure definition.
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.get_template(template_id)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("template_retrieval_failed", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve template")


@router.patch("/{template_id}", response_model=ProjectTemplateResponse)
async def update_template(
    template_id: UUID,
    update_data: ProjectTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update template properties
    
    Only the template owner can update their templates.
    System templates cannot be modified.
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.update_template(template_id, update_data)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("template_update_failed", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update template")


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a template
    
    Only the template owner can delete their templates.
    System templates cannot be deleted.
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        await service.delete_template(template_id)
        
        logger.info(
            "template_deleted",
            template_id=str(template_id),
            user_id=str(current_user_id)
        )
        
        return None
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("template_deletion_failed", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete template")


@router.post("/{template_id}/duplicate", response_model=ProjectTemplateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_template(
    template_id: UUID,
    new_name: str = Body(..., description="Name for the duplicated template"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Duplicate an existing template
    
    Creates a copy of an existing template with a new name.
    Useful for creating variations of system templates.
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.duplicate_template(template_id, new_name)
        
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateResourceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("template_duplication_failed", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to duplicate template")


# System template management (admin only)
@router.post("/system", response_model=List[ProjectTemplateResponse])
async def initialize_system_templates(
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Initialize default system templates
    
    Creates the default set of system templates. This is typically
    called during initial setup or to reset system templates.
    
    Note: Requires admin privileges (not implemented in this example).
    """
    try:
        service = ProjectTemplateService(db, current_user_id)
        return await service.initialize_system_templates()
        
    except Exception as e:
        logger.error("system_template_init_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize system templates")