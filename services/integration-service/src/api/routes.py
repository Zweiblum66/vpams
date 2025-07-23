"""
Main API routes for the Integration Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..db.base import get_db
from ..models.schemas import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
    IntegrationListResponse, IntegrationTestResponse
)
from ..services.integration_service import IntegrationService
from ..core.auth import get_current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/", response_model=IntegrationListResponse)
async def list_integrations(
    skip: int = 0,
    limit: int = 20,
    integration_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all integrations
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **integration_type**: Filter by integration type
    - **enabled**: Filter by enabled status
    """
    service = IntegrationService(db)
    integrations = await service.list_integrations(
        skip=skip,
        limit=limit,
        integration_type=integration_type,
        enabled=enabled,
        user_id=current_user["user_id"]
    )
    
    return IntegrationListResponse(
        integrations=integrations,
        total=len(integrations),
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new integration
    
    - **name**: Unique name for the integration
    - **type**: Type of integration (webhook, slack, teams, etc.)
    - **config**: Integration-specific configuration
    """
    service = IntegrationService(db)
    
    try:
        created = await service.create_integration(
            integration,
            user_id=current_user["user_id"]
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get integration details
    """
    service = IntegrationService(db)
    integration = await service.get_integration(
        integration_id,
        user_id=current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return integration


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    integration: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an integration
    """
    service = IntegrationService(db)
    
    try:
        updated = await service.update_integration(
            integration_id,
            integration,
            user_id=current_user["user_id"]
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an integration
    """
    service = IntegrationService(db)
    deleted = await service.delete_integration(
        integration_id,
        user_id=current_user["user_id"]
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Test an integration connection
    """
    service = IntegrationService(db)
    
    try:
        result = await service.test_integration(
            integration_id,
            user_id=current_user["user_id"]
        )
        
        if result is None:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            message=str(e),
            details={"error": str(e)}
        )


@router.post("/{integration_id}/enable", response_model=IntegrationResponse)
async def enable_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Enable an integration
    """
    service = IntegrationService(db)
    integration = await service.enable_integration(
        integration_id,
        user_id=current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return integration


@router.post("/{integration_id}/disable", response_model=IntegrationResponse)
async def disable_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Disable an integration
    """
    service = IntegrationService(db)
    integration = await service.disable_integration(
        integration_id,
        user_id=current_user["user_id"]
    )
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
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
    """
    Get events for an integration
    """
    service = IntegrationService(db)
    events = await service.get_integration_events(
        integration_id,
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        event_type=event_type,
        status=status
    )
    
    if events is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {
        "events": events,
        "total": len(events),
        "skip": skip,
        "limit": limit
    }