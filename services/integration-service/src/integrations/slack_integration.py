"""
Slack integration implementation
"""

from typing import Dict, Any, Optional, List
import httpx
import json
from datetime import datetime

from ..core.integration_framework import (
    BaseIntegration, IntegrationConfig, IntegrationEvent,
    IntegrationResponse, IntegrationType, AuthType
)
import structlog

logger = structlog.get_logger()


class SlackIntegration(BaseIntegration[Dict[str, Any]]):
    """
    Slack integration for sending notifications and messages
    """
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = "https://slack.com/api"
        self._token = None
    
    async def connect(self) -> bool:
        """Initialize Slack connection"""
        try:
            # Extract access token from auth config
            if self.config.auth_type == AuthType.OAUTH2:
                self._token = self.config.auth_config.get("access_token")
            elif self.config.auth_type == AuthType.BEARER_TOKEN:
                self._token = self.config.auth_config.get("token")
            
            if not self._token:
                logger.error("No access token found in Slack configuration")
                self.status = IntegrationStatus.ERROR
                return False
            
            # Test the connection
            if await self.test_connection():
                self.status = IntegrationStatus.CONNECTED
                return True
            else:
                self.status = IntegrationStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Slack: {e}")
            self.status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Slack"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = IntegrationStatus.DISCONNECTED
    
    async def send_event(self, event: IntegrationEvent) -> IntegrationResponse:
        """Send an event to Slack"""
        start_time = datetime.utcnow()
        
        try:
            # Determine how to send the event
            if event.type == EventType.CUSTOM and "slack_message" in event.data:
                # Direct message sending
                response = await self._send_custom_message(event.data["slack_message"])
            else:
                # Format event as notification
                response = await self._send_event_notification(event)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return IntegrationResponse(
                success=response.get("ok", False),
                data=response,
                error=response.get("error") if not response.get("ok") else None,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to send Slack event: {e}")
            return IntegrationResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def test_connection(self) -> bool:
        """Test Slack connection"""
        try:
            # Use auth.test endpoint
            response = await self._make_slack_request("auth.test")
            return response.get("ok", False)
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
    
    async def _make_slack_request(
        self,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to Slack API"""
        url = f"{self.base_url}/{method}"
        
        headers = {
            "Authorization": f"Bearer {self._token}"
        }
        
        if json_body:
            headers["Content-Type"] = "application/json"
            response = await self._make_request(
                "POST",
                url,
                json=json_body,
                headers=headers
            )
        else:
            response = await self._make_request(
                "POST",
                url,
                data=data,
                headers=headers
            )
        
        return response.json()
    
    async def _send_custom_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a custom Slack message"""
        return await self._make_slack_request("chat.postMessage", json_body=message_data)
    
    async def _send_event_notification(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Send an event as a formatted notification"""
        # Get default channel from config
        channel = self.config.custom_config.get("default_channel", "#general")
        
        # Format the event into Slack blocks
        blocks = self._format_event_blocks(event)
        
        # Send message
        message_data = {
            "channel": channel,
            "blocks": blocks,
            "text": f"MAMS Event: {event.type.value}"  # Fallback text
        }
        
        return await self._make_slack_request("chat.postMessage", json_body=message_data)
    
    def _format_event_blocks(self, event: IntegrationEvent) -> List[Dict[str, Any]]:
        """Format an event into Slack block kit format"""
        blocks = []
        
        # Header
        emoji_map = {
            EventType.ASSET_CREATED: "🎬",
            EventType.ASSET_UPDATED: "📝",
            EventType.ASSET_DELETED: "🗑️",
            EventType.WORKFLOW_STARTED: "▶️",
            EventType.WORKFLOW_COMPLETED: "✅",
            EventType.WORKFLOW_FAILED: "❌",
            EventType.USER_CREATED: "👤",
            EventType.PROJECT_CREATED: "📁"
        }
        
        emoji = emoji_map.get(event.type, "📢")
        header_text = f"{emoji} {event.type.value.replace('.', ' ').title()}"
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        })
        
        # Event details
        fields = []
        
        # Add common fields
        fields.append({
            "type": "mrkdwn",
            "text": f"*Event ID:* {event.id}"
        })
        
        fields.append({
            "type": "mrkdwn",
            "text": f"*Source:* {event.source}"
        })
        
        # Add specific fields based on event type
        if event.type in [EventType.ASSET_CREATED, EventType.ASSET_UPDATED]:
            if "asset_name" in event.data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Asset:* {event.data['asset_name']}"
                })
            if "asset_type" in event.data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Type:* {event.data['asset_type']}"
                })
        
        elif event.type in [EventType.WORKFLOW_STARTED, EventType.WORKFLOW_COMPLETED, EventType.WORKFLOW_FAILED]:
            if "workflow_type" in event.data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Workflow:* {event.data['workflow_type']}"
                })
            if event.type == EventType.WORKFLOW_FAILED and "error" in event.data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Error:* {event.data['error']}"
                })
        
        # Add metadata fields
        for key, value in event.metadata.items():
            if key not in ["timestamp", "event_id"]:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key.replace('_', ' ').title()}:* {value}"
                })
        
        if fields:
            blocks.append({
                "type": "section",
                "fields": fields[:10]  # Slack limits to 10 fields
            })
        
        # Add raw data if complex
        if len(event.data) > 5:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Additional Data:*\n```{json.dumps(event.data, indent=2)[:2000]}```"
                }
            })
        
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Event occurred at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        # Add action buttons if URLs are provided
        actions = []
        if "view_url" in event.data:
            actions.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View"
                },
                "url": event.data["view_url"]
            })
        
        if "dashboard_url" in event.metadata:
            actions.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Dashboard"
                },
                "url": event.metadata["dashboard_url"]
            })
        
        if actions:
            blocks.append({
                "type": "actions",
                "elements": actions
            })
        
        return blocks
    
    async def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel"""
        message_data = {
            "channel": channel
        }
        
        if text:
            message_data["text"] = text
        
        if blocks:
            message_data["blocks"] = blocks
        
        if thread_ts:
            message_data["thread_ts"] = thread_ts
        
        return await self._make_slack_request("chat.postMessage", json_body=message_data)
    
    async def list_channels(self, limit: int = 100, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List available Slack channels"""
        params = {
            "limit": limit,
            "exclude_archived": True,
            "types": "public_channel,private_channel"
        }
        
        if cursor:
            params["cursor"] = cursor
        
        return await self._make_slack_request("conversations.list", data=params)
    
    async def upload_file(
        self,
        channels: List[str],
        file_content: bytes,
        filename: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file to Slack channels"""
        # Note: File upload requires multipart form data
        # This is a simplified version - actual implementation would need proper file handling
        data = {
            "channels": ",".join(channels),
            "filename": filename,
            "title": title or filename
        }
        
        if initial_comment:
            data["initial_comment"] = initial_comment
        
        # This would need to be implemented with proper multipart/form-data
        return await self._make_slack_request("files.upload", data=data)