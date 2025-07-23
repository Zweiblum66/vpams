"""
Theme management API routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..db.models import ThemeTypeEnum
from ..models.schemas import ThemeCreate, ThemeUpdate, ThemeResponse
from ..services.theme_service import ThemeService
from ..core.exceptions import (
    ThemeNotFoundError, DuplicateResourceError, 
    ResourceLimitExceededError, ThemeValidationError
)
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
theme_service = ThemeService()


@router.post("/", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    theme_data: ThemeCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new white-label theme"""
    try:
        theme = await theme_service.create_theme(db, tenant_id, theme_data)
        return ThemeResponse.model_validate(theme)
    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ResourceLimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ThemeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[ThemeResponse])
async def list_themes(
    tenant_id: str = Query(..., description="Tenant ID"),
    skip: int = Query(0, ge=0, description="Number of themes to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of themes to return"),
    theme_type: Optional[ThemeTypeEnum] = Query(None, description="Filter by theme type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search themes by name or description"),
    db: AsyncSession = Depends(get_db)
):
    """List white-label themes for a tenant"""
    try:
        themes = await theme_service.get_themes(
            db, tenant_id, skip, limit, theme_type, is_active, search
        )
        return [ThemeResponse.model_validate(theme) for theme in themes]
    except Exception as e:
        logger.error(f"Failed to list themes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific white-label theme"""
    try:
        theme = await theme_service.get_theme_by_id(db, tenant_id, theme_id)
        return ThemeResponse.model_validate(theme)
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except Exception as e:
        logger.error(f"Failed to get theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    theme_data: ThemeUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update a white-label theme"""
    try:
        theme = await theme_service.update_theme(db, tenant_id, theme_id, theme_data)
        return ThemeResponse.model_validate(theme)
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except ThemeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    theme_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a white-label theme"""
    try:
        await theme_service.delete_theme(db, tenant_id, theme_id)
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except Exception as e:
        logger.error(f"Failed to delete theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{theme_id}/set-default", response_model=ThemeResponse)
async def set_default_theme(
    theme_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Set a theme as the default for a tenant"""
    try:
        theme = await theme_service.set_default_theme(db, tenant_id, theme_id)
        return ThemeResponse.model_validate(theme)
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except Exception as e:
        logger.error(f"Failed to set default theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{theme_id}/duplicate", response_model=ThemeResponse)
async def duplicate_theme(
    theme_id: str,
    new_name: str = Query(..., description="Name for the duplicated theme"),
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Duplicate an existing theme"""
    try:
        theme = await theme_service.duplicate_theme(db, tenant_id, theme_id, new_name)
        return ThemeResponse.model_validate(theme)
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ResourceLimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to duplicate theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{theme_id}/css")
async def get_theme_css(
    theme_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Generate CSS from theme configuration"""
    try:
        css = await theme_service.generate_css(db, tenant_id, theme_id)
        return Response(content=css, media_type="text/css")
    except ThemeNotFoundError:
        raise HTTPException(status_code=404, detail="Theme not found")
    except Exception as e:
        logger.error(f"Failed to generate theme CSS: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/default/current", response_model=Optional[ThemeResponse])
async def get_default_theme(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get the current default theme for a tenant"""
    try:
        theme = await theme_service.get_default_theme(db, tenant_id)
        if theme:
            return ThemeResponse.model_validate(theme)
        return None
    except Exception as e:
        logger.error(f"Failed to get default theme: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/usage", response_model=Dict[str, Any])
async def get_theme_analytics(
    tenant_id: str = Query(..., description="Tenant ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    db: AsyncSession = Depends(get_db)
):
    """Get theme usage analytics"""
    try:
        analytics = await theme_service.get_theme_analytics(db, tenant_id, days)
        return analytics
    except Exception as e:
        logger.error(f"Failed to get theme analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")