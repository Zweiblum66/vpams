"""
Branding configuration API routes
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..models.schemas import BrandingCreate, BrandingUpdate, BrandingResponse
from ..services.branding_service import BrandingService
from ..core.exceptions import (
    BrandingNotFoundError, ThemeNotFoundError, 
    InvalidConfigurationError, DuplicateResourceError
)
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
branding_service = BrandingService()


@router.post("/", response_model=BrandingResponse, status_code=status.HTTP_201_CREATED)
async def create_branding(
    branding_data: BrandingCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create branding configuration for a tenant"""
    try:
        branding = await branding_service.create_branding(db, tenant_id, branding_data)
        return BrandingResponse.model_validate(branding)
    except DuplicateResourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ThemeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=Optional[BrandingResponse])
async def get_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get branding configuration for a tenant"""
    try:
        branding = await branding_service.get_branding_by_tenant(db, tenant_id)
        if branding:
            return BrandingResponse.model_validate(branding)
        return None
    except Exception as e:
        logger.error(f"Failed to get branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/", response_model=BrandingResponse)
async def update_branding(
    branding_data: BrandingUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update branding configuration for a tenant"""
    try:
        branding = await branding_service.update_branding(db, tenant_id, branding_data)
        return BrandingResponse.model_validate(branding)
    except BrandingNotFoundError:
        raise HTTPException(status_code=404, detail="Branding configuration not found")
    except ThemeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete branding configuration for a tenant"""
    try:
        await branding_service.delete_branding(db, tenant_id)
    except BrandingNotFoundError:
        raise HTTPException(status_code=404, detail="Branding configuration not found")
    except Exception as e:
        logger.error(f"Failed to delete branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/activate", response_model=BrandingResponse)
async def activate_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Activate branding configuration for a tenant"""
    try:
        branding = await branding_service.activate_branding(db, tenant_id)
        return BrandingResponse.model_validate(branding)
    except BrandingNotFoundError:
        raise HTTPException(status_code=404, detail="Branding configuration not found")
    except InvalidConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to activate branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/deactivate", response_model=BrandingResponse)
async def deactivate_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate branding configuration for a tenant"""
    try:
        branding = await branding_service.deactivate_branding(db, tenant_id)
        return BrandingResponse.model_validate(branding)
    except BrandingNotFoundError:
        raise HTTPException(status_code=404, detail="Branding configuration not found")
    except Exception as e:
        logger.error(f"Failed to deactivate branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/public", response_model=Dict[str, Any])
async def get_public_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get public branding information (safe for client-side use)"""
    try:
        branding = await branding_service.get_public_branding(db, tenant_id)
        return branding
    except Exception as e:
        logger.error(f"Failed to get public branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/email", response_model=Dict[str, Any])
async def get_email_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get email branding configuration"""
    try:
        branding = await branding_service.get_email_branding(db, tenant_id)
        return branding
    except Exception as e:
        logger.error(f"Failed to get email branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api", response_model=Dict[str, Any])
async def get_api_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get API documentation branding"""
    try:
        branding = await branding_service.get_api_branding(db, tenant_id)
        return branding
    except Exception as e:
        logger.error(f"Failed to get API branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/validate", response_model=Dict[str, Any])
async def validate_branding(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Validate branding configuration completeness"""
    try:
        validation_result = await branding_service.validate_branding_configuration(db, tenant_id)
        return validation_result
    except Exception as e:
        logger.error(f"Failed to validate branding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")