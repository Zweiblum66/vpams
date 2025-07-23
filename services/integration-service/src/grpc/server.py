"""
gRPC server implementation for Integration Service
"""

import grpc
from grpc import aio
import asyncio
from typing import AsyncIterator, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog
from google.protobuf import empty_pb2, timestamp_pb2, struct_pb2
from sqlalchemy.ext.asyncio import AsyncSession

from . import integration_service_pb2 as proto
from . import integration_service_pb2_grpc as proto_grpc
from ..db.base import get_db
from ..services.integration_service import IntegrationService
from ..services.webhook_service import WebhookService
from ..models.schemas import (
    IntegrationCreate, IntegrationUpdate,
    WebhookCreate, WebhookUpdate,
    IntegrationType as DBIntegrationType,
    AuthType as DBAuthType,
    EventType as DBEventType
)
from ..core.integration_framework import EventType
from ..core.auth import verify_token

logger = structlog.get_logger()


class IntegrationServicer(proto_grpc.IntegrationServiceServicer):
    """gRPC service implementation for Integration Service"""
    
    def __init__(self):
        self.event_subscribers: Dict[str, asyncio.Queue] = {}
    
    async def _get_user_from_context(self, context: grpc.aio.ServicerContext) -> Dict[str, Any]:
        """Extract and verify user from gRPC metadata"""
        metadata = dict(context.invocation_metadata())
        auth_token = metadata.get("authorization", "").replace("Bearer ", "")
        
        if not auth_token:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing authorization token")
        
        try:
            user_data = verify_token(auth_token)
            return {
                "user_id": user_data["sub"],
                "email": user_data.get("email"),
                "roles": user_data.get("roles", [])
            }
        except Exception as e:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, f"Invalid token: {str(e)}")
    
    def _map_integration_type_to_proto(self, db_type: str) -> proto.IntegrationType:
        """Map database integration type to proto enum"""
        mapping = {
            "webhook": proto.INTEGRATION_TYPE_WEBHOOK,
            "slack": proto.INTEGRATION_TYPE_SLACK,
            "teams": proto.INTEGRATION_TYPE_TEAMS,
            "email": proto.INTEGRATION_TYPE_EMAIL,
            "rest_api": proto.INTEGRATION_TYPE_REST_API,
            "graphql": proto.INTEGRATION_TYPE_GRAPHQL,
            "grpc": proto.INTEGRATION_TYPE_GRPC,
            "zapier": proto.INTEGRATION_TYPE_ZAPIER,
            "custom": proto.INTEGRATION_TYPE_CUSTOM
        }
        return mapping.get(db_type, proto.INTEGRATION_TYPE_UNSPECIFIED)
    
    def _map_proto_to_integration_type(self, proto_type: proto.IntegrationType) -> DBIntegrationType:
        """Map proto enum to database integration type"""
        mapping = {
            proto.INTEGRATION_TYPE_WEBHOOK: DBIntegrationType.WEBHOOK,
            proto.INTEGRATION_TYPE_SLACK: DBIntegrationType.SLACK,
            proto.INTEGRATION_TYPE_TEAMS: DBIntegrationType.TEAMS,
            proto.INTEGRATION_TYPE_EMAIL: DBIntegrationType.EMAIL,
            proto.INTEGRATION_TYPE_REST_API: DBIntegrationType.REST_API,
            proto.INTEGRATION_TYPE_GRAPHQL: DBIntegrationType.GRAPHQL,
            proto.INTEGRATION_TYPE_GRPC: DBIntegrationType.GRPC,
            proto.INTEGRATION_TYPE_ZAPIER: DBIntegrationType.ZAPIER,
            proto.INTEGRATION_TYPE_CUSTOM: DBIntegrationType.CUSTOM
        }
        return mapping.get(proto_type, DBIntegrationType.CUSTOM)
    
    def _map_auth_type_to_proto(self, db_type: Optional[str]) -> proto.AuthType:
        """Map database auth type to proto enum"""
        if not db_type:
            return proto.AUTH_TYPE_NONE
        
        mapping = {
            "none": proto.AUTH_TYPE_NONE,
            "api_key": proto.AUTH_TYPE_API_KEY,
            "bearer_token": proto.AUTH_TYPE_BEARER_TOKEN,
            "oauth2": proto.AUTH_TYPE_OAUTH2,
            "basic": proto.AUTH_TYPE_BASIC,
            "custom": proto.AUTH_TYPE_CUSTOM
        }
        return mapping.get(db_type, proto.AUTH_TYPE_UNSPECIFIED)
    
    def _map_proto_to_auth_type(self, proto_type: proto.AuthType) -> DBAuthType:
        """Map proto enum to database auth type"""
        mapping = {
            proto.AUTH_TYPE_NONE: DBAuthType.NONE,
            proto.AUTH_TYPE_API_KEY: DBAuthType.API_KEY,
            proto.AUTH_TYPE_BEARER_TOKEN: DBAuthType.BEARER_TOKEN,
            proto.AUTH_TYPE_OAUTH2: DBAuthType.OAUTH2,
            proto.AUTH_TYPE_BASIC: DBAuthType.BASIC,
            proto.AUTH_TYPE_CUSTOM: DBAuthType.CUSTOM
        }
        return mapping.get(proto_type, DBAuthType.NONE)
    
    def _datetime_to_timestamp(self, dt: Optional[datetime]) -> Optional[timestamp_pb2.Timestamp]:
        """Convert datetime to protobuf timestamp"""
        if not dt:
            return None
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(dt)
        return ts
    
    def _dict_to_struct(self, data: Optional[Dict[str, Any]]) -> struct_pb2.Struct:
        """Convert dict to protobuf struct"""
        struct = struct_pb2.Struct()
        if data:
            struct.update(data)
        return struct
    
    def _struct_to_dict(self, struct: struct_pb2.Struct) -> Dict[str, Any]:
        """Convert protobuf struct to dict"""
        return dict(struct)
    
    async def ListIntegrations(
        self,
        request: proto.ListIntegrationsRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.ListIntegrationsResponse:
        """List integrations"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            # Map request parameters
            integration_type = None
            if request.type != proto.INTEGRATION_TYPE_UNSPECIFIED:
                integration_type = self._map_proto_to_integration_type(request.type).value
            
            integrations = await service.list_integrations(
                skip=0,  # Calculate from page token
                limit=request.page_size or 20,
                integration_type=integration_type,
                enabled=request.enabled_only if request.enabled_only else None,
                user_id=user["user_id"]
            )
            
            # Convert to proto
            proto_integrations = []
            for integration in integrations:
                proto_integration = proto.Integration(
                    id=str(integration.id),
                    name=integration.name,
                    type=self._map_integration_type_to_proto(integration.type),
                    description=integration.description or "",
                    enabled=integration.enabled,
                    config=self._dict_to_struct(integration.config),
                    auth_type=self._map_auth_type_to_proto(integration.auth_type),
                    user_id=integration.user_id,
                    created_at=self._datetime_to_timestamp(integration.created_at),
                    updated_at=self._datetime_to_timestamp(integration.updated_at),
                    last_used_at=self._datetime_to_timestamp(integration.last_used_at),
                    event_count=integration.event_count,
                    error_count=integration.error_count
                )
                proto_integrations.append(proto_integration)
            
            return proto.ListIntegrationsResponse(
                integrations=proto_integrations,
                next_page_token="",  # TODO: Implement pagination
                total_count=len(proto_integrations)
            )
    
    async def GetIntegration(
        self,
        request: proto.GetIntegrationRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.Integration:
        """Get integration details"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            integration = await service.get_integration(
                UUID(request.id),
                user["user_id"]
            )
            
            if not integration:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Integration not found")
            
            return proto.Integration(
                id=str(integration.id),
                name=integration.name,
                type=self._map_integration_type_to_proto(integration.type),
                description=integration.description or "",
                enabled=integration.enabled,
                config=self._dict_to_struct(integration.config),
                auth_type=self._map_auth_type_to_proto(integration.auth_type),
                user_id=integration.user_id,
                created_at=self._datetime_to_timestamp(integration.created_at),
                updated_at=self._datetime_to_timestamp(integration.updated_at),
                last_used_at=self._datetime_to_timestamp(integration.last_used_at),
                event_count=integration.event_count,
                error_count=integration.error_count
            )
    
    async def CreateIntegration(
        self,
        request: proto.CreateIntegrationRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.Integration:
        """Create a new integration"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            # Create integration
            integration_data = IntegrationCreate(
                name=request.name,
                type=self._map_proto_to_integration_type(request.type),
                description=request.description,
                enabled=request.enabled,
                config=self._struct_to_dict(request.config),
                auth_type=self._map_proto_to_auth_type(request.auth_type),
                auth_config=self._struct_to_dict(request.auth_config)
            )
            
            try:
                integration = await service.create_integration(
                    integration_data,
                    user["user_id"]
                )
                
                return proto.Integration(
                    id=str(integration.id),
                    name=integration.name,
                    type=self._map_integration_type_to_proto(integration.type),
                    description=integration.description or "",
                    enabled=integration.enabled,
                    config=self._dict_to_struct(integration.config),
                    auth_type=self._map_auth_type_to_proto(integration.auth_type),
                    user_id=integration.user_id,
                    created_at=self._datetime_to_timestamp(integration.created_at),
                    updated_at=self._datetime_to_timestamp(integration.updated_at),
                    event_count=0,
                    error_count=0
                )
            except ValueError as e:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
    
    async def UpdateIntegration(
        self,
        request: proto.UpdateIntegrationRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.Integration:
        """Update an integration"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            # Update integration
            update_data = IntegrationUpdate(
                name=request.name if request.name else None,
                description=request.description if request.description else None,
                enabled=request.enabled,
                config=self._struct_to_dict(request.config) if request.config else None,
                auth_config=self._struct_to_dict(request.auth_config) if request.auth_config else None
            )
            
            try:
                integration = await service.update_integration(
                    UUID(request.id),
                    update_data,
                    user["user_id"]
                )
                
                if not integration:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Integration not found")
                
                return proto.Integration(
                    id=str(integration.id),
                    name=integration.name,
                    type=self._map_integration_type_to_proto(integration.type),
                    description=integration.description or "",
                    enabled=integration.enabled,
                    config=self._dict_to_struct(integration.config),
                    auth_type=self._map_auth_type_to_proto(integration.auth_type),
                    user_id=integration.user_id,
                    created_at=self._datetime_to_timestamp(integration.created_at),
                    updated_at=self._datetime_to_timestamp(integration.updated_at),
                    last_used_at=self._datetime_to_timestamp(integration.last_used_at),
                    event_count=integration.event_count,
                    error_count=integration.error_count
                )
            except ValueError as e:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
    
    async def DeleteIntegration(
        self,
        request: proto.DeleteIntegrationRequest,
        context: grpc.aio.ServicerContext
    ) -> empty_pb2.Empty:
        """Delete an integration"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            success = await service.delete_integration(
                UUID(request.id),
                user["user_id"]
            )
            
            if not success:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Integration not found")
            
            return empty_pb2.Empty()
    
    async def TestIntegration(
        self,
        request: proto.TestIntegrationRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.TestIntegrationResponse:
        """Test an integration"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            result = await service.test_integration(
                UUID(request.id),
                user["user_id"]
            )
            
            if not result:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Integration not found")
            
            return proto.TestIntegrationResponse(
                success=result.success,
                message=result.message,
                details=self._dict_to_struct(result.details)
            )
    
    async def SendEvent(
        self,
        request: proto.SendEventRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.SendEventResponse:
        """Send an event to an integration"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = IntegrationService(db)
            
            # Map event type
            event_type_mapping = {
                proto.EVENT_TYPE_ASSET_CREATED: EventType.ASSET_CREATED,
                proto.EVENT_TYPE_ASSET_UPDATED: EventType.ASSET_UPDATED,
                proto.EVENT_TYPE_ASSET_DELETED: EventType.ASSET_DELETED,
                proto.EVENT_TYPE_WORKFLOW_STARTED: EventType.WORKFLOW_STARTED,
                proto.EVENT_TYPE_WORKFLOW_COMPLETED: EventType.WORKFLOW_COMPLETED,
                proto.EVENT_TYPE_WORKFLOW_FAILED: EventType.WORKFLOW_FAILED,
                proto.EVENT_TYPE_USER_CREATED: EventType.USER_CREATED,
                proto.EVENT_TYPE_USER_UPDATED: EventType.USER_UPDATED,
                proto.EVENT_TYPE_PROJECT_CREATED: EventType.PROJECT_CREATED,
                proto.EVENT_TYPE_PROJECT_UPDATED: EventType.PROJECT_UPDATED,
                proto.EVENT_TYPE_CUSTOM: EventType.CUSTOM
            }
            
            event_type = event_type_mapping.get(
                request.event_type,
                EventType.CUSTOM
            )
            
            result = await service.send_event(
                integration_id=UUID(request.integration_id),
                event_type=event_type,
                event_data=self._struct_to_dict(request.event_data),
                metadata=self._struct_to_dict(request.metadata)
            )
            
            return proto.SendEventResponse(
                success=result.get("success", False),
                event_id=result.get("event_id", ""),
                error=result.get("error", ""),
                response=self._dict_to_struct(result.get("response", {}))
            )
    
    async def StreamEvents(
        self,
        request: proto.StreamEventsRequest,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[proto.IntegrationEvent]:
        """Stream integration events in real-time"""
        user = await self._get_user_from_context(context)
        
        # Create event queue for this subscriber
        subscriber_id = f"{user['user_id']}_{request.integration_id}"
        event_queue = asyncio.Queue()
        self.event_subscribers[subscriber_id] = event_queue
        
        try:
            # If historical events requested, fetch and send them first
            if request.include_historical:
                async with get_db() as db:
                    service = IntegrationService(db)
                    
                    events = await service.get_integration_events(
                        integration_id=UUID(request.integration_id),
                        user_id=user["user_id"],
                        skip=0,
                        limit=100  # Last 100 events
                    )
                    
                    if events:
                        for event in events:
                            proto_event = proto.IntegrationEvent(
                                id=str(event["id"]),
                                integration_id=request.integration_id,
                                event_type=proto.EVENT_TYPE_CUSTOM,  # Map properly
                                event_data=self._dict_to_struct(event["event_data"]),
                                status=event["status"],
                                attempts=event["attempts"],
                                response_status=event["response_status"] or 0,
                                error_message=event["error_message"] or "",
                                created_at=self._datetime_to_timestamp(event["created_at"]),
                                sent_at=self._datetime_to_timestamp(event["sent_at"]),
                                completed_at=self._datetime_to_timestamp(event["completed_at"])
                            )
                            yield proto_event
            
            # Stream new events
            while True:
                try:
                    # Wait for new events with timeout
                    event = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=30.0  # 30 second timeout
                    )
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    if context.is_active():
                        continue
                    else:
                        break
                
        finally:
            # Cleanup subscriber
            del self.event_subscribers[subscriber_id]
    
    # Implement remaining webhook methods similarly...
    
    async def ListWebhooks(
        self,
        request: proto.ListWebhooksRequest,
        context: grpc.aio.ServicerContext
    ) -> proto.ListWebhooksResponse:
        """List webhooks"""
        user = await self._get_user_from_context(context)
        
        async with get_db() as db:
            service = WebhookService(db)
            
            webhooks = await service.list_webhooks(
                user_id=user["user_id"],
                skip=0,
                limit=request.page_size or 20,
                event_type=request.event_type if request.event_type else None,
                enabled=request.enabled_only if request.enabled_only else None
            )
            
            proto_webhooks = []
            for webhook in webhooks:
                proto_webhook = proto.Webhook(
                    id=str(webhook.id),
                    integration_id=str(webhook.integration_id),
                    name=webhook.name,
                    url=webhook.url,
                    events=webhook.events,
                    secret=webhook.secret or "",
                    headers=dict(webhook.headers) if webhook.headers else {},
                    timeout=webhook.timeout,
                    retry_count=webhook.retry_count,
                    enabled=webhook.enabled,
                    verified=webhook.verified,
                    created_at=self._datetime_to_timestamp(webhook.created_at),
                    updated_at=self._datetime_to_timestamp(webhook.updated_at),
                    last_triggered_at=self._datetime_to_timestamp(webhook.last_triggered_at),
                    success_count=webhook.success_count,
                    failure_count=webhook.failure_count
                )
                proto_webhooks.append(proto_webhook)
            
            return proto.ListWebhooksResponse(
                webhooks=proto_webhooks,
                next_page_token="",
                total_count=len(proto_webhooks)
            )


async def serve(port: int = 50051):
    """Start the gRPC server"""
    server = aio.server()
    proto_grpc.add_IntegrationServiceServicer_to_server(
        IntegrationServicer(), server
    )
    
    # Enable reflection for debugging
    from grpc_reflection.v1alpha import reflection
    SERVICE_NAMES = (
        proto.DESCRIPTOR.services_by_name['IntegrationService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    
    # Listen on port
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting gRPC server on {listen_addr}")
    
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())