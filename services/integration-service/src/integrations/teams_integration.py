"""
Microsoft Teams integration implementation
"""

from typing import Dict, Any, Optional, List
import httpx
import json
from datetime import datetime
import uuid

from ..core.integration_framework import (
    BaseIntegration, IntegrationConfig, IntegrationEvent,
    IntegrationResponse, IntegrationType, AuthType, EventType
)
from ..core.integration_framework import IntegrationStatus
import structlog

logger = structlog.get_logger()


class TeamsIntegration(BaseIntegration[Dict[str, Any]]):
    """
    Microsoft Teams integration for sending notifications and messages
    """
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self._token = None
        self._tenant_id = None
        self._team_id = None
        self._channel_id = None
    
    async def connect(self) -> bool:
        """Initialize Teams connection"""
        try:
            # Extract access token and tenant info from auth config
            if self.config.auth_type == AuthType.OAUTH2:
                self._token = self.config.auth_config.get("access_token")
                self._tenant_id = self.config.auth_config.get("tenant_id")
                self._team_id = self.config.custom_config.get("team_id")
                self._channel_id = self.config.custom_config.get("channel_id")
            
            if not self._token:
                logger.error("No access token found in Teams configuration")
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
            logger.error(f"Failed to connect to Teams: {e}")
            self.status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Teams"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = IntegrationStatus.DISCONNECTED
    
    async def send_event(self, event: IntegrationEvent) -> IntegrationResponse:
        """Send an event to Teams"""
        start_time = datetime.utcnow()
        
        try:
            # Determine how to send the event
            if event.type == EventType.CUSTOM and "teams_message" in event.data:
                # Direct message sending
                response = await self._send_custom_message(event.data["teams_message"])
            elif "webhook_url" in self.config.custom_config:
                # Use incoming webhook for notifications
                response = await self._send_webhook_notification(event)
            else:
                # Format event as channel message
                response = await self._send_event_notification(event)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return IntegrationResponse(
                success=response.get("success", False),
                data=response,
                error=response.get("error") if not response.get("success") else None,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to send Teams event: {e}")
            return IntegrationResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def test_connection(self) -> bool:
        """Test Teams connection"""
        try:
            # Use me endpoint to test auth
            response = await self._make_teams_request("GET", "/me")
            return response is not None and "id" in response
        except Exception as e:
            logger.error(f"Teams connection test failed: {e}")
            return False
    
    async def _make_teams_request(
        self,
        method: str,
        endpoint: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to Microsoft Graph API"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
        
        response = await self._make_request(
            method,
            url,
            json=json_body,
            params=params,
            headers=headers
        )
        
        return response.json() if response.content else {}
    
    async def _send_custom_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a custom Teams message"""
        team_id = message_data.get("team_id", self._team_id)
        channel_id = message_data.get("channel_id", self._channel_id)
        
        if not team_id or not channel_id:
            return {"success": False, "error": "Missing team_id or channel_id"}
        
        endpoint = f"/teams/{team_id}/channels/{channel_id}/messages"
        
        # Format message body
        body = {
            "body": {
                "contentType": message_data.get("contentType", "html"),
                "content": message_data.get("content", "")
            }
        }
        
        if "attachments" in message_data:
            body["attachments"] = message_data["attachments"]
        
        try:
            response = await self._make_teams_request("POST", endpoint, json_body=body)
            return {"success": True, "data": response}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_webhook_notification(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Send notification via Teams incoming webhook"""
        webhook_url = self.config.custom_config.get("webhook_url")
        
        if not webhook_url:
            return {"success": False, "error": "No webhook URL configured"}
        
        # Format as adaptive card
        card = self._format_adaptive_card(event)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=card)
                success = response.status_code == 200
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "response": response.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_event_notification(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Send an event as a formatted notification to a channel"""
        if not self._team_id or not self._channel_id:
            # Try webhook instead
            if "webhook_url" in self.config.custom_config:
                return await self._send_webhook_notification(event)
            return {"success": False, "error": "No team or channel configured"}
        
        # Format the event as an adaptive card
        card = self._format_adaptive_card(event)
        
        # Send as channel message
        endpoint = f"/teams/{self._team_id}/channels/{self._channel_id}/messages"
        
        body = {
            "body": {
                "contentType": "html",
                "content": f"<attachment id=\"{uuid.uuid4()}\"></attachment>"
            },
            "attachments": [{
                "id": str(uuid.uuid4()),
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": json.dumps(card)
            }]
        }
        
        try:
            response = await self._make_teams_request("POST", endpoint, json_body=body)
            return {"success": True, "data": response}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_adaptive_card(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Format an event into Teams adaptive card format"""
        # Color scheme based on event type
        color_map = {
            EventType.ASSET_CREATED: "good",
            EventType.ASSET_UPDATED: "accent",
            EventType.ASSET_DELETED: "warning",
            EventType.WORKFLOW_STARTED: "accent",
            EventType.WORKFLOW_COMPLETED: "good",
            EventType.WORKFLOW_FAILED: "attention",
            EventType.USER_CREATED: "accent",
            EventType.PROJECT_CREATED: "good"
        }
        
        # Emoji map
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
        color = color_map.get(event.type, "default")
        
        # Build card
        card = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"{emoji} {event.type.value.replace('.', ' ').title()}",
                            "size": "Large",
                            "weight": "Bolder",
                            "color": color
                        },
                        {
                            "type": "FactSet",
                            "facts": self._build_facts(event)
                        }
                    ],
                    "actions": self._build_actions(event)
                }
            }]
        }
        
        # Add additional sections based on event data
        content_body = card["attachments"][0]["content"]["body"]
        
        # Add description if available
        if "description" in event.data:
            content_body.insert(1, {
                "type": "TextBlock",
                "text": event.data["description"],
                "wrap": True
            })
        
        # Add raw data section for complex events
        if len(event.data) > 5:
            content_body.append({
                "type": "TextBlock",
                "text": "Additional Data:",
                "weight": "Bolder",
                "spacing": "Medium"
            })
            content_body.append({
                "type": "TextBlock",
                "text": json.dumps(event.data, indent=2)[:1000],
                "fontType": "Monospace",
                "wrap": True,
                "size": "Small"
            })
        
        # Add timestamp
        content_body.append({
            "type": "TextBlock",
            "text": f"Event occurred at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "size": "Small",
            "color": "Default",
            "spacing": "Medium"
        })
        
        return card
    
    def _build_facts(self, event: IntegrationEvent) -> List[Dict[str, str]]:
        """Build fact set for adaptive card"""
        facts = [
            {"title": "Event ID", "value": event.id},
            {"title": "Source", "value": event.source}
        ]
        
        # Add specific facts based on event type
        if event.type in [EventType.ASSET_CREATED, EventType.ASSET_UPDATED]:
            if "asset_name" in event.data:
                facts.append({"title": "Asset", "value": event.data["asset_name"]})
            if "asset_type" in event.data:
                facts.append({"title": "Type", "value": event.data["asset_type"]})
            if "file_size" in event.data:
                facts.append({"title": "Size", "value": self._format_file_size(event.data["file_size"])})
        
        elif event.type in [EventType.WORKFLOW_STARTED, EventType.WORKFLOW_COMPLETED, EventType.WORKFLOW_FAILED]:
            if "workflow_type" in event.data:
                facts.append({"title": "Workflow", "value": event.data["workflow_type"]})
            if "duration" in event.data:
                facts.append({"title": "Duration", "value": f"{event.data['duration']}s"})
            if event.type == EventType.WORKFLOW_FAILED and "error" in event.data:
                facts.append({"title": "Error", "value": event.data["error"][:100]})
        
        # Add metadata facts
        for key, value in event.metadata.items():
            if key not in ["timestamp", "event_id"] and len(facts) < 10:
                facts.append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value)[:50]
                })
        
        return facts[:10]  # Limit to 10 facts
    
    def _build_actions(self, event: IntegrationEvent) -> List[Dict[str, Any]]:
        """Build action buttons for adaptive card"""
        actions = []
        
        if "view_url" in event.data:
            actions.append({
                "type": "Action.OpenUrl",
                "title": "View",
                "url": event.data["view_url"]
            })
        
        if "dashboard_url" in event.metadata:
            actions.append({
                "type": "Action.OpenUrl",
                "title": "Dashboard",
                "url": event.metadata["dashboard_url"]
            })
        
        # Add MAMS link if configured
        if "mams_base_url" in self.config.custom_config:
            base_url = self.config.custom_config["mams_base_url"]
            actions.append({
                "type": "Action.OpenUrl",
                "title": "Open in MAMS",
                "url": f"{base_url}/events/{event.id}"
            })
        
        return actions[:3]  # Limit to 3 actions
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    async def send_message(
        self,
        team_id: str,
        channel_id: str,
        content: str,
        content_type: str = "html",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a message to a Teams channel"""
        endpoint = f"/teams/{team_id}/channels/{channel_id}/messages"
        
        body = {
            "body": {
                "contentType": content_type,
                "content": content
            }
        }
        
        if attachments:
            body["attachments"] = attachments
        
        return await self._make_teams_request("POST", endpoint, json_body=body)
    
    async def list_teams(self) -> List[Dict[str, Any]]:
        """List teams the user is a member of"""
        try:
            response = await self._make_teams_request("GET", "/me/joinedTeams")
            return response.get("value", [])
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return []
    
    async def list_channels(self, team_id: str) -> List[Dict[str, Any]]:
        """List channels in a team"""
        try:
            response = await self._make_teams_request("GET", f"/teams/{team_id}/channels")
            return response.get("value", [])
        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []
    
    async def create_channel(
        self,
        team_id: str,
        display_name: str,
        description: Optional[str] = None,
        membership_type: str = "standard"
    ) -> Dict[str, Any]:
        """Create a new channel in a team"""
        body = {
            "displayName": display_name,
            "membershipType": membership_type
        }
        
        if description:
            body["description"] = description
        
        return await self._make_teams_request(
            "POST",
            f"/teams/{team_id}/channels",
            json_body=body
        )
    
    async def upload_file(
        self,
        team_id: str,
        channel_id: str,
        file_name: str,
        file_content: bytes,
        folder_path: str = "General"
    ) -> Dict[str, Any]:
        """Upload a file to a Teams channel"""
        # This would require using OneDrive API endpoints
        # Simplified version - would need proper implementation
        endpoint = f"/teams/{team_id}/channels/{channel_id}/filesFolder/children"
        
        # Note: Actual implementation would need multipart upload
        logger.warning("File upload to Teams not fully implemented")
        return {"success": False, "error": "Not implemented"}