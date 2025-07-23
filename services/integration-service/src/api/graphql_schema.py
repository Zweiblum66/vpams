"""
GraphQL schema for Integration Service
"""

import strawberry
from strawberry.types import Info
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import asyncio

from ..services.integration_service import IntegrationService
from ..services.webhook_service import WebhookService
from ..models.schemas import (
    IntegrationType as DBIntegrationType,
    AuthType as DBAuthType,
    EventType as DBEventType
)
from ..db.base import get_db


# GraphQL Type Definitions
@strawberry.enum
class IntegrationType:
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    ZAPIER = "zapier"
    CUSTOM = "custom"


@strawberry.enum
class AuthType:
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


@strawberry.enum
class EventType:
    ASSET_CREATED = "asset.created"
    ASSET_UPDATED = "asset.updated"
    ASSET_DELETED = "asset.deleted"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    CUSTOM = "custom"


@strawberry.type
class Integration:
    id: UUID
    name: str
    type: IntegrationType
    description: Optional[str]
    enabled: bool
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]
    last_used_at: Optional[datetime]
    event_count: int
    error_count: int


@strawberry.type
class IntegrationTestResult:
    success: bool
    message: str
    details: Optional[dict]


@strawberry.type
class Webhook:
    id: UUID
    integration_id: UUID
    name: str
    url: str
    events: List[str]
    enabled: bool
    verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_triggered_at: Optional[datetime]
    success_count: int
    failure_count: int


@strawberry.type
class IntegrationEvent:
    id: UUID
    integration_id: UUID
    event_type: str
    event_data: dict
    status: str
    attempts: int
    response_status: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]


# Input Types
@strawberry.input
class CreateIntegrationInput:
    name: str
    type: IntegrationType
    description: Optional[str] = None
    enabled: bool = True
    config: Optional[dict] = None
    auth_type: AuthType = AuthType.NONE
    auth_config: Optional[dict] = None


@strawberry.input
class UpdateIntegrationInput:
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None
    auth_config: Optional[dict] = None


@strawberry.input
class CreateWebhookInput:
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    headers: Optional[dict] = None
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True


@strawberry.input
class UpdateWebhookInput:
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    headers: Optional[dict] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None
    enabled: Optional[bool] = None


@strawberry.input
class SendEventInput:
    integration_id: UUID
    event_type: EventType
    event_data: dict
    metadata: Optional[dict] = None


# Queries
@strawberry.type
class Query:
    @strawberry.field
    async def integrations(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 20,
        type: Optional[IntegrationType] = None,
        enabled: Optional[bool] = None
    ) -> List[Integration]:
        """List all integrations for the current user"""
        # Get current user from context
        current_user = info.context["current_user"]
        
        # Get database session
        async with get_db() as db:
            service = IntegrationService(db)
            
            integrations = await service.list_integrations(
                skip=skip,
                limit=limit,
                integration_type=type.value if type else None,
                enabled=enabled,
                user_id=current_user["user_id"]
            )
            
            return [
                Integration(
                    id=i.id,
                    name=i.name,
                    type=IntegrationType[i.type.upper()],
                    description=i.description,
                    enabled=i.enabled,
                    user_id=i.user_id,
                    created_at=i.created_at,
                    updated_at=i.updated_at,
                    last_used_at=i.last_used_at,
                    event_count=i.event_count,
                    error_count=i.error_count
                )
                for i in integrations
            ]
    
    @strawberry.field
    async def integration(self, info: Info, id: UUID) -> Optional[Integration]:
        """Get a specific integration by ID"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            integration = await service.get_integration(id, current_user["user_id"])
            
            if not integration:
                return None
            
            return Integration(
                id=integration.id,
                name=integration.name,
                type=IntegrationType[integration.type.upper()],
                description=integration.description,
                enabled=integration.enabled,
                user_id=integration.user_id,
                created_at=integration.created_at,
                updated_at=integration.updated_at,
                last_used_at=integration.last_used_at,
                event_count=integration.event_count,
                error_count=integration.error_count
            )
    
    @strawberry.field
    async def webhooks(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 20,
        event_type: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List[Webhook]:
        """List all webhooks for the current user"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            webhooks = await service.list_webhooks(
                user_id=current_user["user_id"],
                skip=skip,
                limit=limit,
                event_type=event_type,
                enabled=enabled
            )
            
            return [
                Webhook(
                    id=w.id,
                    integration_id=w.integration_id,
                    name=w.name,
                    url=w.url,
                    events=w.events,
                    enabled=w.enabled,
                    verified=w.verified,
                    created_at=w.created_at,
                    updated_at=w.updated_at,
                    last_triggered_at=w.last_triggered_at,
                    success_count=w.success_count,
                    failure_count=w.failure_count
                )
                for w in webhooks
            ]
    
    @strawberry.field
    async def webhook(self, info: Info, id: UUID) -> Optional[Webhook]:
        """Get a specific webhook by ID"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            webhook = await service.get_webhook(id, current_user["user_id"])
            
            if not webhook:
                return None
            
            return Webhook(
                id=webhook.id,
                integration_id=webhook.integration_id,
                name=webhook.name,
                url=webhook.url,
                events=webhook.events,
                enabled=webhook.enabled,
                verified=webhook.verified,
                created_at=webhook.created_at,
                updated_at=webhook.updated_at,
                last_triggered_at=webhook.last_triggered_at,
                success_count=webhook.success_count,
                failure_count=webhook.failure_count
            )
    
    @strawberry.field
    async def integration_events(
        self,
        info: Info,
        integration_id: UUID,
        skip: int = 0,
        limit: int = 20,
        event_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[IntegrationEvent]:
        """Get events for a specific integration"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            events = await service.get_integration_events(
                integration_id=integration_id,
                user_id=current_user["user_id"],
                skip=skip,
                limit=limit,
                event_type=event_type,
                status=status
            )
            
            if events is None:
                return []
            
            return [
                IntegrationEvent(
                    id=e["id"],
                    integration_id=integration_id,
                    event_type=e["event_type"],
                    event_data=e["event_data"],
                    status=e["status"],
                    attempts=e["attempts"],
                    response_status=e["response_status"],
                    error_message=e["error_message"],
                    created_at=e["created_at"],
                    sent_at=e["sent_at"],
                    completed_at=e["completed_at"]
                )
                for e in events
            ]


# Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_integration(
        self,
        info: Info,
        input: CreateIntegrationInput
    ) -> Integration:
        """Create a new integration"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            from ..models.schemas import IntegrationCreate
            
            integration_data = IntegrationCreate(
                name=input.name,
                type=DBIntegrationType(input.type.value),
                description=input.description,
                enabled=input.enabled,
                config=input.config or {},
                auth_type=DBAuthType(input.auth_type.value),
                auth_config=input.auth_config or {}
            )
            
            integration = await service.create_integration(
                integration_data,
                current_user["user_id"]
            )
            
            return Integration(
                id=integration.id,
                name=integration.name,
                type=IntegrationType[integration.type.upper()],
                description=integration.description,
                enabled=integration.enabled,
                user_id=integration.user_id,
                created_at=integration.created_at,
                updated_at=integration.updated_at,
                last_used_at=integration.last_used_at,
                event_count=integration.event_count,
                error_count=integration.error_count
            )
    
    @strawberry.mutation
    async def update_integration(
        self,
        info: Info,
        id: UUID,
        input: UpdateIntegrationInput
    ) -> Optional[Integration]:
        """Update an existing integration"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            from ..models.schemas import IntegrationUpdate
            
            update_data = IntegrationUpdate(
                name=input.name,
                description=input.description,
                enabled=input.enabled,
                config=input.config,
                auth_config=input.auth_config
            )
            
            integration = await service.update_integration(
                id,
                update_data,
                current_user["user_id"]
            )
            
            if not integration:
                return None
            
            return Integration(
                id=integration.id,
                name=integration.name,
                type=IntegrationType[integration.type.upper()],
                description=integration.description,
                enabled=integration.enabled,
                user_id=integration.user_id,
                created_at=integration.created_at,
                updated_at=integration.updated_at,
                last_used_at=integration.last_used_at,
                event_count=integration.event_count,
                error_count=integration.error_count
            )
    
    @strawberry.mutation
    async def delete_integration(
        self,
        info: Info,
        id: UUID
    ) -> bool:
        """Delete an integration"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            return await service.delete_integration(id, current_user["user_id"])
    
    @strawberry.mutation
    async def test_integration(
        self,
        info: Info,
        id: UUID
    ) -> IntegrationTestResult:
        """Test an integration connection"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            result = await service.test_integration(id, current_user["user_id"])
            
            if not result:
                return IntegrationTestResult(
                    success=False,
                    message="Integration not found",
                    details=None
                )
            
            return IntegrationTestResult(
                success=result.success,
                message=result.message,
                details=result.details
            )
    
    @strawberry.mutation
    async def create_webhook(
        self,
        info: Info,
        input: CreateWebhookInput
    ) -> Webhook:
        """Create a new webhook"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            from ..models.schemas import WebhookCreate
            from pydantic import HttpUrl
            
            webhook_data = WebhookCreate(
                name=input.name,
                url=HttpUrl(input.url),
                events=input.events,
                secret=input.secret,
                headers=input.headers,
                timeout=input.timeout,
                retry_count=input.retry_count,
                enabled=input.enabled
            )
            
            webhook = await service.create_webhook(
                webhook_data,
                current_user["user_id"]
            )
            
            return Webhook(
                id=webhook.id,
                integration_id=webhook.integration_id,
                name=webhook.name,
                url=webhook.url,
                events=webhook.events,
                enabled=webhook.enabled,
                verified=webhook.verified,
                created_at=webhook.created_at,
                updated_at=webhook.updated_at,
                last_triggered_at=webhook.last_triggered_at,
                success_count=webhook.success_count,
                failure_count=webhook.failure_count
            )
    
    @strawberry.mutation
    async def update_webhook(
        self,
        info: Info,
        id: UUID,
        input: UpdateWebhookInput
    ) -> Optional[Webhook]:
        """Update an existing webhook"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            from ..models.schemas import WebhookUpdate
            from pydantic import HttpUrl
            
            update_data = WebhookUpdate(
                name=input.name,
                url=HttpUrl(input.url) if input.url else None,
                events=input.events,
                secret=input.secret,
                headers=input.headers,
                timeout=input.timeout,
                retry_count=input.retry_count,
                enabled=input.enabled
            )
            
            webhook = await service.update_webhook(
                id,
                update_data,
                current_user["user_id"]
            )
            
            if not webhook:
                return None
            
            return Webhook(
                id=webhook.id,
                integration_id=webhook.integration_id,
                name=webhook.name,
                url=webhook.url,
                events=webhook.events,
                enabled=webhook.enabled,
                verified=webhook.verified,
                created_at=webhook.created_at,
                updated_at=webhook.updated_at,
                last_triggered_at=webhook.last_triggered_at,
                success_count=webhook.success_count,
                failure_count=webhook.failure_count
            )
    
    @strawberry.mutation
    async def delete_webhook(
        self,
        info: Info,
        id: UUID
    ) -> bool:
        """Delete a webhook"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            return await service.delete_webhook(id, current_user["user_id"])
    
    @strawberry.mutation
    async def test_webhook(
        self,
        info: Info,
        id: UUID
    ) -> dict:
        """Test a webhook by sending a test event"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = WebhookService(db)
            
            result = await service.test_webhook(id, current_user["user_id"])
            
            return result or {"success": False, "error": "Webhook not found"}
    
    @strawberry.mutation
    async def send_event(
        self,
        info: Info,
        input: SendEventInput
    ) -> dict:
        """Send an event to an integration"""
        current_user = info.context["current_user"]
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            # Verify user owns the integration
            integration = await service.get_integration(
                input.integration_id,
                current_user["user_id"]
            )
            
            if not integration:
                return {"success": False, "error": "Integration not found"}
            
            from ..core.integration_framework import EventType as FrameworkEventType
            
            return await service.send_event(
                integration_id=input.integration_id,
                event_type=FrameworkEventType(input.event_type.value),
                event_data=input.event_data,
                metadata=input.metadata
            )


# Subscriptions
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def integration_events(
        self,
        info: Info,
        integration_id: UUID
    ) -> IntegrationEvent:
        """Subscribe to events for a specific integration"""
        current_user = info.context["current_user"]
        
        # This is a simplified implementation
        # In production, you'd use Redis PubSub or similar
        while True:
            # Check for new events every second
            await asyncio.sleep(1)
            
            async with get_db() as db:
                service = IntegrationService(db)
                
                # Get latest event
                events = await service.get_integration_events(
                    integration_id=integration_id,
                    user_id=current_user["user_id"],
                    skip=0,
                    limit=1
                )
                
                if events:
                    event = events[0]
                    yield IntegrationEvent(
                        id=event["id"],
                        integration_id=integration_id,
                        event_type=event["event_type"],
                        event_data=event["event_data"],
                        status=event["status"],
                        attempts=event["attempts"],
                        response_status=event["response_status"],
                        error_message=event["error_message"],
                        created_at=event["created_at"],
                        sent_at=event["sent_at"],
                        completed_at=event["completed_at"]
                    )
    
    @strawberry.subscription
    async def webhook_status(
        self,
        info: Info,
        webhook_id: UUID
    ) -> Webhook:
        """Subscribe to webhook status updates"""
        current_user = info.context["current_user"]
        
        while True:
            await asyncio.sleep(2)
            
            async with get_db() as db:
                service = WebhookService(db)
                
                webhook = await service.get_webhook(webhook_id, current_user["user_id"])
                
                if webhook:
                    yield Webhook(
                        id=webhook.id,
                        integration_id=webhook.integration_id,
                        name=webhook.name,
                        url=webhook.url,
                        events=webhook.events,
                        enabled=webhook.enabled,
                        verified=webhook.verified,
                        created_at=webhook.created_at,
                        updated_at=webhook.updated_at,
                        last_triggered_at=webhook.last_triggered_at,
                        success_count=webhook.success_count,
                        failure_count=webhook.failure_count
                    )


# Create GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)