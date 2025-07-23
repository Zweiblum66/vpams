"""
Zapier integration API routes
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..db.base import get_db
from ..core.auth import get_current_user
from ..models.schemas import (
    IntegrationCreate, IntegrationResponse, IntegrationType, AuthType
)
from ..services.integration_service import IntegrationService
from ..services.zapier_service import ZapierService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/integrations/zapier", tags=["zapier"])


@router.post("/setup", response_model=IntegrationResponse)
async def setup_zapier_integration(
    webhook_url: str,
    api_key: Optional[str] = None,
    secret: Optional[str] = None,
    instance_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Setup Zapier integration with webhook URL
    """
    zapier_service = ZapierService(db)
    
    # Create integration
    integration_data = IntegrationCreate(
        name=f"Zapier - {instance_name or 'Default'}",
        type=IntegrationType.ZAPIER,
        description="Zapier automation integration",
        enabled=True,
        config={
            "webhook_url": webhook_url,
            "instance_name": instance_name or "default"
        },
        auth_type=AuthType.API_KEY if api_key else AuthType.NONE,
        auth_config={
            "api_key": api_key,
            "secret": secret
        } if api_key or secret else {}
    )
    
    integration_service = IntegrationService(db)
    integration = await integration_service.create_integration(
        integration_data,
        current_user["user_id"]
    )
    
    logger.info(
        "Zapier integration created",
        integration_id=integration.id,
        user_id=current_user["user_id"]
    )
    
    return integration


@router.post("/webhook/{integration_id}")
async def handle_zapier_webhook(
    integration_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_zapier_signature: Optional[str] = Header(None)
):
    """
    Handle incoming webhook from Zapier
    """
    zapier_service = ZapierService(db)
    
    # Get request body
    body = await request.json()
    headers = dict(request.headers)
    
    # Add signature header if present
    if x_zapier_signature:
        headers["X-Zapier-Signature"] = x_zapier_signature
    
    try:
        result = await zapier_service.handle_incoming_webhook(
            integration_id=integration_id,
            headers=headers,
            body=body
        )
        
        # Return appropriate response based on action
        if body.get("action") == "subscribe":
            # For subscription, return sample data
            return Response(
                content=result.get("sample", "{}"),
                media_type="application/json",
                status_code=200
            )
        else:
            # For other actions, return result
            return result
            
    except Exception as e:
        logger.error(f"Zapier webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/triggers", response_model=Dict[str, Any])
async def create_zapier_trigger(
    event_types: List[str],
    target_url: str,
    options: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a Zapier trigger (for Zapier app development)
    """
    zapier_service = ZapierService(db)
    
    result = await zapier_service.create_trigger(
        user_id=current_user["user_id"],
        event_types=event_types,
        target_url=target_url,
        options=options
    )
    
    return result


@router.get("/triggers", response_model=List[Dict[str, Any]])
async def list_zapier_triggers(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all Zapier triggers for the user
    """
    zapier_service = ZapierService(db)
    
    triggers = await zapier_service.list_triggers(
        user_id=current_user["user_id"]
    )
    
    return triggers


@router.delete("/triggers/{trigger_id}")
async def delete_zapier_trigger(
    trigger_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a Zapier trigger
    """
    zapier_service = ZapierService(db)
    
    success = await zapier_service.delete_trigger(
        trigger_id=trigger_id,
        user_id=current_user["user_id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    return {"success": True}


@router.get("/sample-data/{event_type}", response_model=Dict[str, Any])
async def get_sample_data(
    event_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get sample data for a specific event type (for Zapier field mapping)
    """
    zapier_service = ZapierService(None)  # No DB needed for sample data
    
    sample = await zapier_service.get_sample_data(event_type)
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sample data available for event type: {event_type}"
        )
    
    return sample


@router.post("/test/{integration_id}", response_model=Dict[str, Any])
async def test_zapier_integration(
    integration_id: UUID,
    test_data: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Test Zapier integration by sending a test event
    """
    zapier_service = ZapierService(db)
    
    result = await zapier_service.test_integration(
        integration_id=integration_id,
        user_id=current_user["user_id"],
        test_data=test_data
    )
    
    return result


# Zapier Developer Platform endpoints
@router.get("/auth/test")
async def test_auth(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Test authentication endpoint for Zapier app
    """
    # Verify API key
    zapier_service = ZapierService(db)
    
    is_valid = await zapier_service.verify_api_key(x_api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return {
        "success": True,
        "message": "Authentication successful"
    }


@router.post("/searches/assets")
async def search_assets_for_zapier(
    query: Dict[str, Any],
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Search assets endpoint for Zapier searches
    """
    zapier_service = ZapierService(db)
    
    # Verify API key
    is_valid = await zapier_service.verify_api_key(x_api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Perform search
    results = await zapier_service.search_assets(query)
    
    return results


@router.post("/searches/projects")
async def search_projects_for_zapier(
    query: Dict[str, Any],
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Search projects endpoint for Zapier searches
    """
    zapier_service = ZapierService(db)
    
    # Verify API key
    is_valid = await zapier_service.verify_api_key(x_api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Perform search
    results = await zapier_service.search_projects(query)
    
    return results


@router.post("/actions/create-asset")
async def create_asset_from_zapier(
    data: Dict[str, Any],
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Create asset action for Zapier
    """
    zapier_service = ZapierService(db)
    
    # Verify API key
    is_valid = await zapier_service.verify_api_key(x_api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Create asset
    result = await zapier_service.create_asset(data)
    
    return result


@router.post("/actions/update-metadata")
async def update_metadata_from_zapier(
    asset_id: str,
    metadata: Dict[str, Any],
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Update asset metadata action for Zapier
    """
    zapier_service = ZapierService(db)
    
    # Verify API key
    is_valid = await zapier_service.verify_api_key(x_api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Update metadata
    result = await zapier_service.update_asset_metadata(asset_id, metadata)
    
    return result