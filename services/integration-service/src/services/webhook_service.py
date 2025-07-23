"""
Webhook service for managing webhook integrations
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..db.models import Integration, Webhook, IntegrationEvent, IntegrationType as DBIntegrationType
from ..models.schemas import (
    WebhookCreate, WebhookUpdate, WebhookResponse,
    IntegrationCreate, IntegrationType, AuthType
)
from ..services.integration_service import IntegrationService
from ..core.integration_framework import (
    IntegrationConfig, IntegrationEvent as FrameworkEvent,
    EventType, WebhookIntegration
)
import structlog

logger = structlog.get_logger()


class WebhookService:
    """Service for managing webhook integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_service = IntegrationService(db)
    
    async def list_webhooks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        event_type: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List[WebhookResponse]:
        """List webhooks for a user"""
        # First get all webhook integrations for the user
        query = (
            select(Integration, Webhook)
            .join(Webhook, Integration.id == Webhook.integration_id)
            .where(
                and_(
                    Integration.user_id == user_id,
                    Integration.type == DBIntegrationType.WEBHOOK
                )
            )
        )
        
        if enabled is not None:
            query = query.where(Webhook.enabled == enabled)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        webhooks = []
        for integration, webhook in rows:
            # Filter by event type if specified
            if event_type and event_type not in webhook.events:
                continue
            
            webhooks.append(
                WebhookResponse(
                    id=webhook.id,
                    integration_id=webhook.integration_id,
                    name=webhook.name,
                    url=webhook.url,
                    events=webhook.events,
                    secret=webhook.secret,
                    headers=webhook.headers,
                    timeout=webhook.timeout,
                    retry_count=webhook.retry_count,
                    enabled=webhook.enabled,
                    verified=webhook.verified,
                    created_at=webhook.created_at,
                    updated_at=webhook.updated_at,
                    last_triggered_at=webhook.last_triggered_at,
                    success_count=webhook.success_count,
                    failure_count=webhook.failure_count
                )
            )
        
        return webhooks
    
    async def create_webhook(
        self,
        data: WebhookCreate,
        user_id: str
    ) -> WebhookResponse:
        """Create a new webhook"""
        # First create an integration
        integration_data = IntegrationCreate(
            name=data.name,
            type=IntegrationType.WEBHOOK,
            description=f"Webhook: {data.url}",
            enabled=data.enabled,
            config={
                "endpoint": str(data.url),
                "headers": data.headers or {},
                "timeout": data.timeout,
                "retry_count": data.retry_count
            },
            auth_type=AuthType.CUSTOM if data.secret else AuthType.NONE,
            auth_config={"secret": data.secret} if data.secret else {}
        )
        
        integration = await self.integration_service.create_integration(
            integration_data,
            user_id
        )
        
        # Create webhook record
        webhook = Webhook(
            integration_id=integration.id,
            name=data.name,
            url=str(data.url),
            secret=data.secret,
            events=data.events,
            headers=data.headers,
            timeout=data.timeout,
            retry_count=data.retry_count,
            enabled=data.enabled
        )
        
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        
        return WebhookResponse(
            id=webhook.id,
            integration_id=webhook.integration_id,
            name=webhook.name,
            url=webhook.url,
            events=webhook.events,
            secret=webhook.secret,
            headers=webhook.headers,
            timeout=webhook.timeout,
            retry_count=webhook.retry_count,
            enabled=webhook.enabled,
            verified=webhook.verified,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
            success_count=0,
            failure_count=0
        )
    
    async def get_webhook(
        self,
        webhook_id: UUID,
        user_id: str
    ) -> Optional[WebhookResponse]:
        """Get webhook details"""
        query = (
            select(Integration, Webhook)
            .join(Webhook, Integration.id == Webhook.integration_id)
            .where(
                and_(
                    Webhook.id == webhook_id,
                    Integration.user_id == user_id
                )
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        integration, webhook = row
        
        return WebhookResponse(
            id=webhook.id,
            integration_id=webhook.integration_id,
            name=webhook.name,
            url=webhook.url,
            events=webhook.events,
            secret=webhook.secret,
            headers=webhook.headers,
            timeout=webhook.timeout,
            retry_count=webhook.retry_count,
            enabled=webhook.enabled,
            verified=webhook.verified,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
            last_triggered_at=webhook.last_triggered_at,
            success_count=webhook.success_count,
            failure_count=webhook.failure_count
        )
    
    async def update_webhook(
        self,
        webhook_id: UUID,
        data: WebhookUpdate,
        user_id: str
    ) -> Optional[WebhookResponse]:
        """Update a webhook"""
        # Get webhook with integration
        query = (
            select(Integration, Webhook)
            .join(Webhook, Integration.id == Webhook.integration_id)
            .where(
                and_(
                    Webhook.id == webhook_id,
                    Integration.user_id == user_id
                )
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        integration, webhook = row
        
        # Update webhook fields
        if data.name is not None:
            webhook.name = data.name
            integration.name = data.name
        
        if data.url is not None:
            webhook.url = str(data.url)
            integration.config["endpoint"] = str(data.url)
        
        if data.events is not None:
            webhook.events = data.events
        
        if data.secret is not None:
            webhook.secret = data.secret
            if data.secret:
                integration.auth_type = AuthType.CUSTOM.value
                integration.auth_config = {"secret": data.secret}
            else:
                integration.auth_type = AuthType.NONE.value
                integration.auth_config = {}
        
        if data.headers is not None:
            webhook.headers = data.headers
            integration.config["headers"] = data.headers
        
        if data.timeout is not None:
            webhook.timeout = data.timeout
            integration.config["timeout"] = data.timeout
        
        if data.retry_count is not None:
            webhook.retry_count = data.retry_count
            integration.config["retry_count"] = data.retry_count
        
        if data.enabled is not None:
            webhook.enabled = data.enabled
            integration.enabled = data.enabled
        
        webhook.updated_at = datetime.utcnow()
        integration.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(webhook)
        
        return await self.get_webhook(webhook_id, user_id)
    
    async def delete_webhook(
        self,
        webhook_id: UUID,
        user_id: str
    ) -> bool:
        """Delete a webhook"""
        # Get webhook with integration
        query = (
            select(Integration, Webhook)
            .join(Webhook, Integration.id == Webhook.integration_id)
            .where(
                and_(
                    Webhook.id == webhook_id,
                    Integration.user_id == user_id
                )
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return False
        
        integration, webhook = row
        
        # Delete webhook and integration (cascade will handle webhook)
        await self.integration_service.delete_integration(integration.id, user_id)
        
        return True
    
    async def test_webhook(
        self,
        webhook_id: UUID,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Test a webhook by sending a test event"""
        webhook = await self.get_webhook(webhook_id, user_id)
        
        if not webhook:
            return None
        
        # Create test event
        test_event = FrameworkEvent(
            id="test-" + str(UUID()),
            type=EventType.CUSTOM,
            source="webhook-test",
            data={
                "test": True,
                "webhook_id": str(webhook_id),
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata={
                "test_event": True
            }
        )
        
        # Send test event via integration service
        result = await self.integration_service.send_event(
            integration_id=webhook.integration_id,
            event_type=EventType.CUSTOM,
            event_data=test_event.data,
            metadata=test_event.metadata
        )
        
        # Update webhook stats
        webhook_obj = await self.db.get(Webhook, webhook_id)
        if result["success"]:
            webhook_obj.success_count += 1
            webhook_obj.verified = True
        else:
            webhook_obj.failure_count += 1
        
        webhook_obj.last_triggered_at = datetime.utcnow()
        await self.db.commit()
        
        return result
    
    async def get_webhook_events(
        self,
        webhook_id: UUID,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get event history for a webhook"""
        # Verify webhook belongs to user
        webhook = await self.get_webhook(webhook_id, user_id)
        if not webhook:
            return None
        
        # Get events from integration service
        return await self.integration_service.get_integration_events(
            integration_id=webhook.integration_id,
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status
        )
    
    async def process_incoming_webhook(
        self,
        endpoint_id: str,
        headers: Dict[str, str],
        body: str,
        source_ip: Optional[str] = None
    ) -> bool:
        """Process an incoming webhook from an external system"""
        # Find webhook by endpoint ID
        # This would typically involve looking up a webhook by a unique endpoint identifier
        # For now, we'll log it
        logger.info(
            "Incoming webhook received",
            endpoint_id=endpoint_id,
            source_ip=source_ip,
            headers=headers
        )
        
        # TODO: Implement incoming webhook processing
        # - Find the webhook configuration
        # - Verify signature if configured
        # - Parse and validate the payload
        # - Transform to internal event format
        # - Trigger appropriate workflows
        
        return True