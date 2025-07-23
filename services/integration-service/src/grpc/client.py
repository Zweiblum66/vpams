"""
gRPC client for Integration Service
"""

import grpc
from grpc import aio
import asyncio
from typing import Optional, List, Dict, Any, AsyncIterator
from google.protobuf import struct_pb2
import structlog

from . import integration_service_pb2 as proto
from . import integration_service_pb2_grpc as proto_grpc

logger = structlog.get_logger()


class IntegrationServiceClient:
    """gRPC client for Integration Service"""
    
    def __init__(self, host: str = "localhost", port: int = 50051, auth_token: Optional[str] = None):
        self.channel = None
        self.stub = None
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self._metadata = []
        
        if auth_token:
            self._metadata = [("authorization", f"Bearer {auth_token}")]
    
    async def connect(self):
        """Connect to the gRPC server"""
        self.channel = aio.insecure_channel(f"{self.host}:{self.port}")
        self.stub = proto_grpc.IntegrationServiceStub(self.channel)
        logger.info(f"Connected to gRPC server at {self.host}:{self.port}")
    
    async def close(self):
        """Close the connection"""
        if self.channel:
            await self.channel.close()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _dict_to_struct(self, data: Dict[str, Any]) -> struct_pb2.Struct:
        """Convert dict to protobuf struct"""
        struct = struct_pb2.Struct()
        struct.update(data)
        return struct
    
    async def list_integrations(
        self,
        integration_type: Optional[proto.IntegrationType] = None,
        enabled_only: bool = False,
        page_size: int = 20
    ) -> List[proto.Integration]:
        """List integrations"""
        request = proto.ListIntegrationsRequest(
            page_size=page_size,
            type=integration_type or proto.INTEGRATION_TYPE_UNSPECIFIED,
            enabled_only=enabled_only
        )
        
        response = await self.stub.ListIntegrations(request, metadata=self._metadata)
        return response.integrations
    
    async def get_integration(self, integration_id: str) -> proto.Integration:
        """Get integration details"""
        request = proto.GetIntegrationRequest(id=integration_id)
        return await self.stub.GetIntegration(request, metadata=self._metadata)
    
    async def create_integration(
        self,
        name: str,
        integration_type: proto.IntegrationType,
        description: str = "",
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        auth_type: proto.AuthType = proto.AUTH_TYPE_NONE,
        auth_config: Optional[Dict[str, Any]] = None
    ) -> proto.Integration:
        """Create a new integration"""
        request = proto.CreateIntegrationRequest(
            name=name,
            type=integration_type,
            description=description,
            enabled=enabled,
            config=self._dict_to_struct(config or {}),
            auth_type=auth_type,
            auth_config=self._dict_to_struct(auth_config or {})
        )
        
        return await self.stub.CreateIntegration(request, metadata=self._metadata)
    
    async def update_integration(
        self,
        integration_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[Dict[str, Any]] = None,
        auth_config: Optional[Dict[str, Any]] = None
    ) -> proto.Integration:
        """Update an integration"""
        request = proto.UpdateIntegrationRequest(id=integration_id)
        
        if name is not None:
            request.name = name
        if description is not None:
            request.description = description
        if enabled is not None:
            request.enabled = enabled
        if config is not None:
            request.config.CopyFrom(self._dict_to_struct(config))
        if auth_config is not None:
            request.auth_config.CopyFrom(self._dict_to_struct(auth_config))
        
        return await self.stub.UpdateIntegration(request, metadata=self._metadata)
    
    async def delete_integration(self, integration_id: str) -> None:
        """Delete an integration"""
        request = proto.DeleteIntegrationRequest(id=integration_id)
        await self.stub.DeleteIntegration(request, metadata=self._metadata)
    
    async def test_integration(self, integration_id: str) -> proto.TestIntegrationResponse:
        """Test an integration"""
        request = proto.TestIntegrationRequest(id=integration_id)
        return await self.stub.TestIntegration(request, metadata=self._metadata)
    
    async def send_event(
        self,
        integration_id: str,
        event_type: proto.EventType,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> proto.SendEventResponse:
        """Send an event to an integration"""
        request = proto.SendEventRequest(
            integration_id=integration_id,
            event_type=event_type,
            event_data=self._dict_to_struct(event_data),
            metadata=self._dict_to_struct(metadata or {})
        )
        
        return await self.stub.SendEvent(request, metadata=self._metadata)
    
    async def stream_events(
        self,
        integration_id: str,
        event_types: Optional[List[proto.EventType]] = None,
        include_historical: bool = False
    ) -> AsyncIterator[proto.IntegrationEvent]:
        """Stream events from an integration"""
        request = proto.StreamEventsRequest(
            integration_id=integration_id,
            event_types=event_types or [],
            include_historical=include_historical
        )
        
        async for event in self.stub.StreamEvents(request, metadata=self._metadata):
            yield event
    
    async def create_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        retry_count: int = 3,
        enabled: bool = True
    ) -> proto.Webhook:
        """Create a webhook"""
        request = proto.CreateWebhookRequest(
            name=name,
            url=url,
            events=events,
            secret=secret or "",
            headers=headers or {},
            timeout=timeout,
            retry_count=retry_count,
            enabled=enabled
        )
        
        return await self.stub.CreateWebhook(request, metadata=self._metadata)
    
    async def list_webhooks(
        self,
        event_type: Optional[str] = None,
        enabled_only: bool = False,
        page_size: int = 20
    ) -> List[proto.Webhook]:
        """List webhooks"""
        request = proto.ListWebhooksRequest(
            page_size=page_size,
            event_type=event_type or "",
            enabled_only=enabled_only
        )
        
        response = await self.stub.ListWebhooks(request, metadata=self._metadata)
        return response.webhooks


# Example usage
async def example_usage():
    """Example of using the gRPC client"""
    # Create client with authentication
    client = IntegrationServiceClient(
        host="localhost",
        port=50051,
        auth_token="your-jwt-token-here"
    )
    
    async with client:
        # List integrations
        integrations = await client.list_integrations(
            integration_type=proto.INTEGRATION_TYPE_SLACK,
            enabled_only=True
        )
        
        for integration in integrations:
            print(f"Integration: {integration.name} ({integration.type})")
        
        # Create a new webhook integration
        webhook = await client.create_integration(
            name="My Webhook",
            integration_type=proto.INTEGRATION_TYPE_WEBHOOK,
            description="Test webhook integration",
            config={
                "endpoint": "https://example.com/webhook"
            }
        )
        print(f"Created integration: {webhook.id}")
        
        # Send an event
        response = await client.send_event(
            integration_id=webhook.id,
            event_type=proto.EVENT_TYPE_ASSET_CREATED,
            event_data={
                "asset_id": "asset123",
                "asset_name": "test.mp4",
                "asset_type": "video"
            }
        )
        print(f"Event sent: {response.success}")
        
        # Stream events
        print("Streaming events...")
        async for event in client.stream_events(
            integration_id=webhook.id,
            include_historical=True
        ):
            print(f"Event: {event.id} - {event.event_type}")
            # Break after first event for demo
            break


if __name__ == "__main__":
    asyncio.run(example_usage())