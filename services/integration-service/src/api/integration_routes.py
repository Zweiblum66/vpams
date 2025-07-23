"""
Integration management API routes
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..core.auth import get_current_user
from ..models.schemas import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
    IntegrationTestResponse, IntegrationType
)
from ..services.integration_service import IntegrationService
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    skip: int = 0,
    limit: int = 20,
    integration_type: Optional[IntegrationType] = None,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List integrations for the current user"""
    service = IntegrationService(db)
    
    return await service.list_integrations(
        skip=skip,
        limit=limit,
        integration_type=integration_type.value if integration_type else None,
        enabled=enabled,
        user_id=current_user["user_id"]
    )


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new integration"""
    service = IntegrationService(db)
    
    try:
        return await service.create_integration(
            integration,
            current_user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get integration details"""
    service = IntegrationService(db)
    
    integration = await service.get_integration(
        integration_id,
        current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return integration


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    update_data: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update an integration"""
    service = IntegrationService(db)
    
    try:
        integration = await service.update_integration(
            integration_id,
            update_data,
            current_user["user_id"]
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        return integration
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete an integration"""
    service = IntegrationService(db)
    
    success = await service.delete_integration(
        integration_id,
        current_user["user_id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Test an integration connection"""
    service = IntegrationService(db)
    
    result = await service.test_integration(
        integration_id,
        current_user["user_id"]
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return result


@router.post("/{integration_id}/enable", response_model=IntegrationResponse)
async def enable_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Enable an integration"""
    service = IntegrationService(db)
    
    integration = await service.enable_integration(
        integration_id,
        current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return integration


@router.post("/{integration_id}/disable", response_model=IntegrationResponse)
async def disable_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Disable an integration"""
    service = IntegrationService(db)
    
    integration = await service.disable_integration(
        integration_id,
        current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return integration


@router.get("/{integration_id}/events")
async def get_integration_events(
    integration_id: UUID,
    skip: int = 0,
    limit: int = 20,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get events for an integration"""
    service = IntegrationService(db)
    
    events = await service.get_integration_events(
        integration_id,
        current_user["user_id"],
        skip=skip,
        limit=limit,
        event_type=event_type,
        status=status
    )
    
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return {"data": events, "total": len(events)}