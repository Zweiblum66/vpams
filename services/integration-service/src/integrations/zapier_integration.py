"""
Zapier integration implementation
"""

from typing import Dict, Any, Optional, List
import httpx
import json
from datetime import datetime
import hmac
import hashlib

from ..core.integration_framework import (
    BaseIntegration, IntegrationConfig, IntegrationEvent,
    IntegrationResponse, IntegrationType, AuthType, EventType,
    IntegrationStatus
)
import structlog

logger = structlog.get_logger()


class ZapierIntegration(BaseIntegration[Dict[str, Any]]):
    """
    Zapier integration for MAMS
    
    This integration allows MAMS to trigger Zaps and be triggered by Zaps
    through webhooks and the Zapier Developer Platform.
    """
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.webhook_url = None
        self.api_key = None
        self.secret = None
    
    async def connect(self) -> bool:
        """Initialize Zapier connection"""
        try:
            # Extract configuration
            self.webhook_url = self.config.custom_config.get("webhook_url")
            self.api_key = self.config.auth_config.get("api_key")
            self.secret = self.config.auth_config.get("secret")
            
            if not self.webhook_url:
                logger.error("No webhook URL found in Zapier configuration")
                self.status = IntegrationStatus.ERROR
                return False
            
            # Zapier webhooks don't require connection testing
            # They're validated when first used
            self.status = IntegrationStatus.CONNECTED
            return True
                
        except Exception as e:
            logger.error(f"Failed to initialize Zapier integration: {e}")
            self.status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Zapier"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = IntegrationStatus.DISCONNECTED
    
    async def send_event(self, event: IntegrationEvent) -> IntegrationResponse:
        """Send an event to Zapier"""
        start_time = datetime.utcnow()
        
        try:
            # Transform event to Zapier format
            zapier_data = self._transform_event_to_zapier(event)
            
            # Add authentication if configured
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            # Calculate signature if secret is provided
            if self.secret:
                signature = self._calculate_signature(zapier_data)
                headers["X-Zapier-Signature"] = signature
            
            # Send to Zapier webhook
            response = await self._make_request(
                "POST",
                self.webhook_url,
                json=zapier_data,
                headers=headers
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Zapier returns specific status codes
            success = response.status_code in [200, 201, 202]
            
            return IntegrationResponse(
                success=success,
                data=response.json() if response.content else {},
                status_code=response.status_code,
                error=None if success else f"HTTP {response.status_code}",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to send Zapier event: {e}")
            return IntegrationResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def test_connection(self) -> bool:
        """Test Zapier webhook"""
        try:
            # Send a test event
            test_event = IntegrationEvent(
                id="test-" + str(datetime.utcnow().timestamp()),
                type=EventType.CUSTOM,
                source="zapier-test",
                data={
                    "test": True,
                    "timestamp": datetime.utcnow().isoformat(),
                    "integration": "MAMS"
                }
            )
            
            response = await self.send_event(test_event)
            return response.success
            
        except Exception as e:
            logger.error(f"Zapier connection test failed: {e}")
            return False
    
    def _transform_event_to_zapier(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Transform MAMS event to Zapier format"""
        # Zapier expects flat data structure for easier mapping
        zapier_data = {
            "id": event.id,
            "type": event.type.value,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "mams_instance": self.config.custom_config.get("instance_name", "default")
        }
        
        # Flatten event data
        for key, value in event.data.items():
            if isinstance(value, (str, int, float, bool)):
                zapier_data[f"data_{key}"] = value
            elif isinstance(value, (list, dict)):
                zapier_data[f"data_{key}"] = json.dumps(value)
            else:
                zapier_data[f"data_{key}"] = str(value)
        
        # Add metadata
        for key, value in event.metadata.items():
            zapier_data[f"meta_{key}"] = value
        
        # Add event-specific fields for common types
        if event.type == EventType.ASSET_CREATED:
            zapier_data["asset_id"] = event.data.get("asset_id", "")
            zapier_data["asset_name"] = event.data.get("asset_name", "")
            zapier_data["asset_type"] = event.data.get("asset_type", "")
            zapier_data["file_size"] = event.data.get("file_size", 0)
            zapier_data["file_path"] = event.data.get("file_path", "")
        
        elif event.type == EventType.WORKFLOW_COMPLETED:
            zapier_data["workflow_id"] = event.data.get("workflow_id", "")
            zapier_data["workflow_type"] = event.data.get("workflow_type", "")
            zapier_data["workflow_result"] = event.data.get("result", "")
            zapier_data["workflow_duration"] = event.data.get("duration", 0)
        
        elif event.type == EventType.PROJECT_CREATED:
            zapier_data["project_id"] = event.data.get("project_id", "")
            zapier_data["project_name"] = event.data.get("project_name", "")
            zapier_data["project_description"] = event.data.get("description", "")
            zapier_data["created_by"] = event.data.get("created_by", "")
        
        return zapier_data
    
    def _calculate_signature(self, data: Dict[str, Any]) -> str:
        """Calculate HMAC signature for request validation"""
        # Sort keys for consistent signature
        sorted_data = json.dumps(data, sort_keys=True)
        
        # Calculate HMAC-SHA256
        signature = hmac.new(
            self.secret.encode(),
            sorted_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def handle_incoming_webhook(
        self,
        headers: Dict[str, str],
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle incoming webhook from Zapier"""
        try:
            # Verify signature if secret is configured
            if self.secret:
                provided_signature = headers.get("X-Zapier-Signature", "")
                expected_signature = self._calculate_signature(body)
                
                if not hmac.compare_digest(provided_signature, expected_signature):
                    logger.warning("Invalid Zapier webhook signature")
                    return {"success": False, "error": "Invalid signature"}
            
            # Process the incoming data
            action = body.get("action", "trigger")
            
            if action == "subscribe":
                # Handle subscription request
                return await self._handle_subscription(body)
            elif action == "unsubscribe":
                # Handle unsubscription request
                return await self._handle_unsubscription(body)
            else:
                # Handle regular webhook trigger
                return await self._handle_trigger(body)
                
        except Exception as e:
            logger.error(f"Error handling Zapier webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_subscription(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Zapier subscription request"""
        # Store subscription details
        subscription_id = data.get("subscription_id")
        target_url = data.get("target_url")
        event_types = data.get("event_types", [])
        
        logger.info(
            "Zapier subscription created",
            subscription_id=subscription_id,
            event_types=event_types
        )
        
        # Return sample data for Zapier to use in mapping
        return {
            "success": True,
            "subscription_id": subscription_id,
            "sample": self._get_sample_data(event_types)
        }
    
    async def _handle_unsubscription(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Zapier unsubscription request"""
        subscription_id = data.get("subscription_id")
        
        logger.info(
            "Zapier subscription removed",
            subscription_id=subscription_id
        )
        
        return {"success": True}
    
    async def _handle_trigger(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Zapier trigger"""
        # Extract trigger data
        trigger_type = data.get("type", "manual")
        trigger_data = data.get("data", {})
        
        logger.info(
            "Zapier trigger received",
            trigger_type=trigger_type
        )
        
        # Process based on trigger type
        if trigger_type == "asset_search":
            # Search for assets based on criteria
            return await self._search_assets(trigger_data)
        elif trigger_type == "project_list":
            # List projects
            return await self._list_projects(trigger_data)
        else:
            # Generic trigger response
            return {
                "success": True,
                "trigger_type": trigger_type,
                "data": trigger_data
            }
    
    def _get_sample_data(self, event_types: List[str]) -> Dict[str, Any]:
        """Get sample data for Zapier field mapping"""
        samples = {}
        
        if "asset.created" in event_types:
            samples["asset_created"] = {
                "id": "evt_123456",
                "type": "asset.created",
                "timestamp": datetime.utcnow().isoformat(),
                "asset_id": "asset_abc123",
                "asset_name": "sample_video.mp4",
                "asset_type": "video",
                "file_size": 104857600,
                "file_path": "/storage/videos/sample_video.mp4",
                "data_duration": "120.5",
                "data_resolution": "1920x1080",
                "meta_project_id": "proj_456",
                "meta_uploaded_by": "user@example.com"
            }
        
        if "workflow.completed" in event_types:
            samples["workflow_completed"] = {
                "id": "evt_789012",
                "type": "workflow.completed",
                "timestamp": datetime.utcnow().isoformat(),
                "workflow_id": "wf_def456",
                "workflow_type": "transcoding",
                "workflow_result": "success",
                "workflow_duration": 300,
                "data_input_asset": "asset_abc123",
                "data_output_assets": '["asset_proxy1", "asset_proxy2"]',
                "meta_triggered_by": "auto"
            }
        
        return samples
    
    async def _search_assets(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Search for assets based on Zapier criteria"""
        # This would integrate with the asset service
        # For now, return mock data
        return {
            "success": True,
            "assets": [
                {
                    "id": "asset_123",
                    "name": "example.mp4",
                    "type": "video",
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        }
    
    async def _list_projects(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """List projects based on Zapier criteria"""
        # This would integrate with the project service
        # For now, return mock data
        return {
            "success": True,
            "projects": [
                {
                    "id": "proj_123",
                    "name": "Example Project",
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        }
    
    async def create_instant_trigger(
        self,
        event_types: List[str],
        target_url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an instant trigger for Zapier"""
        # Register the webhook with Zapier
        trigger_id = f"trigger_{datetime.utcnow().timestamp()}"
        
        # Store trigger configuration
        trigger_config = {
            "id": trigger_id,
            "event_types": event_types,
            "target_url": target_url,
            "options": options or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Zapier instant trigger created",
            trigger_id=trigger_id,
            event_types=event_types
        )
        
        return {
            "success": True,
            "trigger_id": trigger_id,
            "sample_data": self._get_sample_data(event_types)
        }
    
    async def list_triggers(self) -> List[Dict[str, Any]]:
        """List all active Zapier triggers"""
        # This would fetch from database
        # For now, return empty list
        return []
    
    async def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a Zapier trigger"""
        logger.info("Zapier trigger deleted", trigger_id=trigger_id)
        return True