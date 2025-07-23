"""
Slack integration service
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import Integration, SlackIntegration, IntegrationEvent
from ..models.schemas import SlackIntegrationConfig
from ..core.integration_framework import IntegrationEvent as FrameworkEvent, EventType
import structlog

logger = structlog.get_logger()


class SlackService:
    """Service for managing Slack integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_slack_integration(
        self,
        integration_id: UUID,
        team_id: str,
        team_name: str,
        access_token: str,
        bot_user_id: str
    ) -> SlackIntegration:
        """Create Slack-specific integration data"""
        slack_integration = SlackIntegration(
            integration_id=integration_id,
            team_id=team_id,
            team_name=team_name,
            access_token=access_token,
            bot_user_id=bot_user_id
        )
        
        self.db.add(slack_integration)
        await self.db.commit()
        await self.db.refresh(slack_integration)
        
        return slack_integration
    
    async def get_slack_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get Slack integration details"""
        query = (
            select(Integration, SlackIntegration)
            .join(SlackIntegration, Integration.id == SlackIntegration.integration_id)
            .where(
                Integration.id == integration_id,
                Integration.user_id == user_id
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        integration, slack = row
        return {
            "integration": integration,
            "slack": slack
        }
    
    async def send_message(
        self,
        integration_id: UUID,
        user_id: str,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Send a message to a Slack channel"""
        # Get integration
        integration_data = await self.get_slack_integration(integration_id, user_id)
        if not integration_data:
            return None
        
        slack = integration_data["slack"]
        
        # Prepare message payload
        payload = {
            "channel": channel,
            "token": slack.access_token
        }
        
        if text:
            payload["text"] = text
        
        if blocks:
            payload["blocks"] = blocks
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Send message via Slack API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack.access_token}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            data = response.json()
            
            # Log the event
            event = IntegrationEvent(
                integration_id=integration_id,
                event_type="slack.message.sent",
                event_data={"channel": channel, "text": text},
                status="success" if data.get("ok") else "failed",
                response_status=response.status_code,
                response_body=json.dumps(data),
                sent_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            self.db.add(event)
            await self.db.commit()
            
            if not data.get("ok"):
                raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
            
            return data
    
    async def list_channels(
        self,
        integration_id: UUID,
        user_id: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """List available Slack channels"""
        # Get integration
        integration_data = await self.get_slack_integration(integration_id, user_id)
        if not integration_data:
            return None
        
        slack = integration_data["slack"]
        
        # Prepare request
        params = {
            "limit": limit,
            "exclude_archived": True,
            "types": "public_channel,private_channel"
        }
        
        if cursor:
            params["cursor"] = cursor
        
        # Get channels via Slack API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/conversations.list",
                headers={
                    "Authorization": f"Bearer {slack.access_token}"
                },
                params=params
            )
            
            data = response.json()
            
            if not data.get("ok"):
                raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
            
            return {
                "channels": data.get("channels", []),
                "cursor": data.get("response_metadata", {}).get("next_cursor"),
                "has_more": bool(data.get("response_metadata", {}).get("next_cursor"))
            }
    
    async def list_users(
        self,
        integration_id: UUID,
        user_id: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """List Slack workspace users"""
        # Get integration
        integration_data = await self.get_slack_integration(integration_id, user_id)
        if not integration_data:
            return None
        
        slack = integration_data["slack"]
        
        # Prepare request
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        # Get users via Slack API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/users.list",
                headers={
                    "Authorization": f"Bearer {slack.access_token}"
                },
                params=params
            )
            
            data = response.json()
            
            if not data.get("ok"):
                raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
            
            return {
                "users": data.get("members", []),
                "cursor": data.get("response_metadata", {}).get("next_cursor"),
                "has_more": bool(data.get("response_metadata", {}).get("next_cursor"))
            }
    
    async def upload_file(
        self,
        integration_id: UUID,
        user_id: str,
        channels: List[str],
        file_url: str,
        filename: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Upload a file to Slack channels"""
        # Get integration
        integration_data = await self.get_slack_integration(integration_id, user_id)
        if not integration_data:
            return None
        
        slack = integration_data["slack"]
        
        # Download file content
        async with httpx.AsyncClient() as client:
            file_response = await client.get(file_url)
            file_content = file_response.content
        
        # Upload to Slack
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/files.upload",
                headers={
                    "Authorization": f"Bearer {slack.access_token}"
                },
                data={
                    "channels": ",".join(channels),
                    "filename": filename,
                    "title": title or filename,
                    "initial_comment": initial_comment
                },
                files={"file": (filename, file_content)}
            )
            
            data = response.json()
            
            if not data.get("ok"):
                raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
            
            return data
    
    async def send_notification(
        self,
        integration_id: UUID,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send a formatted notification based on event type"""
        # Get integration
        integration_data = await self.get_slack_integration(integration_id, user_id)
        if not integration_data:
            return None
        
        integration = integration_data["integration"]
        slack = integration_data["slack"]
        
        # Get default channel from config
        config = integration.config or {}
        default_channel = slack.default_channel or config.get("default_channel", "#general")
        
        # Format message based on event type
        blocks = self._format_event_notification(event_type, event_data)
        
        # Send message
        return await self.send_message(
            integration_id=integration_id,
            user_id=user_id,
            channel=default_channel,
            blocks=blocks
        )
    
    def _format_event_notification(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format event data into Slack blocks"""
        blocks = []
        
        # Header block
        header_text = {
            "asset.created": "🎬 New Asset Created",
            "asset.updated": "📝 Asset Updated",
            "asset.deleted": "🗑️ Asset Deleted",
            "workflow.started": "▶️ Workflow Started",
            "workflow.completed": "✅ Workflow Completed",
            "workflow.failed": "❌ Workflow Failed",
        }.get(event_type, f"📢 {event_type}")
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        })
        
        # Event details
        if event_type.startswith("asset."):
            blocks.extend(self._format_asset_event(event_type, event_data))
        elif event_type.startswith("workflow."):
            blocks.extend(self._format_workflow_event(event_type, event_data))
        else:
            # Generic event formatting
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Event:* {event_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            })
            
            # Add event data as JSON
            if event_data:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{json.dumps(event_data, indent=2)}```"
                    }
                })
        
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Sent from MAMS at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return blocks
    
    def _format_asset_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format asset-related events"""
        blocks = []
        
        # Asset info section
        fields = []
        
        if "asset_id" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Asset ID:* {event_data['asset_id']}"
            })
        
        if "asset_name" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Name:* {event_data['asset_name']}"
            })
        
        if "asset_type" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Type:* {event_data['asset_type']}"
            })
        
        if "size_bytes" in event_data:
            size_mb = event_data['size_bytes'] / (1024 * 1024)
            fields.append({
                "type": "mrkdwn",
                "text": f"*Size:* {size_mb:.1f} MB"
            })
        
        if "created_by" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*User:* {event_data['created_by']}"
            })
        
        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })
        
        # Add action buttons for asset events
        if event_type != "asset.deleted":
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Asset"
                        },
                        "url": f"{event_data.get('asset_url', '#')}"
                    }
                ]
            })
        
        return blocks
    
    def _format_workflow_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format workflow-related events"""
        blocks = []
        
        # Workflow info section
        fields = []
        
        if "workflow_id" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Workflow ID:* {event_data['workflow_id']}"
            })
        
        if "workflow_type" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Type:* {event_data['workflow_type']}"
            })
        
        if "asset_id" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Asset:* {event_data['asset_id']}"
            })
        
        if "duration_seconds" in event_data:
            duration = event_data['duration_seconds']
            fields.append({
                "type": "mrkdwn",
                "text": f"*Duration:* {duration // 60}m {duration % 60}s"
            })
        
        if event_type == "workflow.failed" and "error" in event_data:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Error:* {event_data['error']}"
            })
        
        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })
        
        return blocks
    
    async def process_webhook(self, data: Dict[str, Any]):
        """Process incoming Slack webhook data"""
        # Handle different webhook types
        webhook_type = data.get("type")
        
        if webhook_type == "event_callback":
            # Event subscription
            event = data.get("event", {})
            await self._process_event(data.get("team_id"), event)
        
        elif webhook_type == "slash_command":
            # Slash command
            await self._process_command(data)
        
        elif webhook_type == "interactive_message" or webhook_type == "block_actions":
            # Interactive component
            await self._process_interaction(data)
        
        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")
    
    async def _process_event(self, team_id: str, event: Dict[str, Any]):
        """Process Slack event"""
        event_type = event.get("type")
        
        # Log the event
        logger.info(f"Slack event received: {event_type}", team_id=team_id, event=event)
        
        # Handle specific event types
        if event_type == "app_mention":
            # Bot was mentioned
            pass
        elif event_type == "message":
            # Message in a channel where bot is present
            pass
        # Add more event handlers as needed
    
    async def _process_command(self, data: Dict[str, Any]):
        """Process Slack slash command"""
        command = data.get("command")
        text = data.get("text", "")
        
        logger.info(f"Slack command received: {command}", text=text)
        
        # Handle specific commands
        # Example: /mams search <query>
        # Add command handlers as needed
    
    async def _process_interaction(self, data: Dict[str, Any]):
        """Process Slack interactive component"""
        actions = data.get("actions", [])
        
        for action in actions:
            action_id = action.get("action_id")
            logger.info(f"Slack interaction: {action_id}")
            
            # Handle specific actions
            # Add interaction handlers as needed
    
    async def update_config(
        self,
        integration_id: UUID,
        user_id: str,
        config: SlackIntegrationConfig
    ) -> bool:
        """Update Slack integration configuration"""
        # Get integration
        query = (
            select(Integration, SlackIntegration)
            .join(SlackIntegration, Integration.id == SlackIntegration.integration_id)
            .where(
                Integration.id == integration_id,
                Integration.user_id == user_id
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return False
        
        integration, slack = row
        
        # Update configuration
        slack.default_channel = config.default_channel
        slack.notification_settings = config.notification_settings.dict()
        
        # Update integration config
        integration.config = {
            **integration.config,
            **config.dict()
        }
        
        await self.db.commit()
        return True