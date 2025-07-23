"""
Webhook management routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import hmac
import hashlib
from datetime import datetime

from ..db.base import get_db
from ..models.schemas import (
    WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookListResponse, WebhookEventResponse
)
from ..services.webhook_service import WebhookService
from ..core.auth import get_current_user
from ..core.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = 0,
    limit: int = 20,
    event_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all webhooks for the current user
    """
    service = WebhookService(db)
    webhooks = await service.list_webhooks(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        event_type=event_type,
        enabled=enabled
    )
    
    return WebhookListResponse(
        webhooks=webhooks,
        total=len(webhooks),
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new webhook
    
    - **name**: Display name for the webhook
    - **url**: Endpoint URL to receive webhook events
    - **events**: List of event types to subscribe to
    - **secret**: Optional secret for webhook signature verification
    """
    service = WebhookService(db)
    
    try:
        created = await service.create_webhook(
            webhook,
            user_id=current_user["user_id"]
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get webhook details
    """
    service = WebhookService(db)
    webhook = await service.get_webhook(
        webhook_id,
        user_id=current_user["user_id"]
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    webhook: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a webhook
    """
    service = WebhookService(db)
    
    try:
        updated = await service.update_webhook(
            webhook_id,
            webhook,
            user_id=current_user["user_id"]
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a webhook
    """
    service = WebhookService(db)
    deleted = await service.delete_webhook(
        webhook_id,
        user_id=current_user["user_id"]
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a test event to the webhook
    """
    service = WebhookService(db)
    
    try:
        result = await service.test_webhook(
            webhook_id,
            user_id=current_user["user_id"]
        )
        
        if result is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.utcnow()
        }


@router.get("/{webhook_id}/events", response_model=List[WebhookEventResponse])
async def get_webhook_events(
    webhook_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get event history for a webhook
    """
    service = WebhookService(db)
    events = await service.get_webhook_events(
        webhook_id,
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        status=status
    )
    
    if events is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return events


@router.post("/incoming/{endpoint_id}")
async def receive_webhook(
    endpoint_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive incoming webhooks from external systems
    
    This endpoint is used for bidirectional webhooks where external
    systems can send events back to MAMS.
    """
    # Get request body
    body = await request.body()
    
    # Verify signature if provided
    signature = request.headers.get("X-Webhook-Signature")
    if signature:
        # Verify HMAC signature
        expected_signature = hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook
    service = WebhookService(db)
    
    try:
        result = await service.process_incoming_webhook(
            endpoint_id,
            headers=dict(request.headers),
            body=body.decode("utf-8"),
            source_ip=request.client.host if request.client else None
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {"status": "received", "timestamp": datetime.utcnow()}
        
    except Exception as e:
        # Log error but return success to avoid retries
        # Most webhook providers retry on error responses
        return {"status": "error", "message": str(e)}


@router.get("/event-types")
async def get_webhook_event_types():
    """
    Get available webhook event types
    """
    return {
        "event_types": [
            {
                "type": "asset.created",
                "description": "Triggered when a new asset is created",
                "sample_payload": {
                    "event_type": "asset.created",
                    "asset_id": "uuid",
                    "asset_name": "example.mp4",
                    "created_by": "user_id",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            },
            {
                "type": "asset.updated",
                "description": "Triggered when an asset is updated",
                "sample_payload": {
                    "event_type": "asset.updated",
                    "asset_id": "uuid",
                    "changes": ["metadata", "tags"],
                    "updated_by": "user_id",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            },
            {
                "type": "asset.deleted",
                "description": "Triggered when an asset is deleted",
                "sample_payload": {
                    "event_type": "asset.deleted",
                    "asset_id": "uuid",
                    "deleted_by": "user_id",
                    "deleted_at": "2024-01-01T00:00:00Z"
                }
            },
            {
                "type": "workflow.started",
                "description": "Triggered when a workflow is started",
                "sample_payload": {
                    "event_type": "workflow.started",
                    "workflow_id": "uuid",
                    "workflow_type": "transcoding",
                    "started_by": "user_id",
                    "started_at": "2024-01-01T00:00:00Z"
                }
            },
            {
                "type": "workflow.completed",
                "description": "Triggered when a workflow completes successfully",
                "sample_payload": {
                    "event_type": "workflow.completed",
                    "workflow_id": "uuid",
                    "workflow_type": "transcoding",
                    "duration_seconds": 120,
                    "completed_at": "2024-01-01T00:00:00Z"
                }
            },
            {
                "type": "workflow.failed",
                "description": "Triggered when a workflow fails",
                "sample_payload": {
                    "event_type": "workflow.failed",
                    "workflow_id": "uuid",
                    "workflow_type": "transcoding",
                    "error": "Processing failed",
                    "failed_at": "2024-01-01T00:00:00Z"
                }
            }
        ]
    }