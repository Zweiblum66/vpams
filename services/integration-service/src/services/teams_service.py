"""
Microsoft Teams service implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..db.models import Integration, IntegrationType as DBIntegrationType
from ..models.schemas import IntegrationType, AuthType
from ..services.integration_service import IntegrationService
from ..integrations.teams_integration import TeamsIntegration
from ..core.integration_framework import (
    IntegrationConfig, IntegrationEvent, EventType
)
from ..core.auth import encrypt_data, decrypt_data
import structlog

logger = structlog.get_logger()


class TeamsService:
    """Service for managing Teams integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_service = IntegrationService(db)
        self.client_id = None  # Should be loaded from config
        self.client_secret = None  # Should be loaded from config
    
    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tenant_id: str = "common"
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at.isoformat()
            
            return token_data
    
    async def refresh_token(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Dict[str, Any]:
        """Refresh Teams OAuth token"""
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return {"success": False, "error": "Integration not found"}
        
        if integration_data.auth_type != AuthType.OAUTH2:
            return {"success": False, "error": "Integration does not use OAuth2"}
        
        refresh_token = integration_data.auth_config.get("refresh_token")
        if not refresh_token:
            return {"success": False, "error": "No refresh token available"}
        
        tenant_id = integration_data.config.get("tenant_id", "common")
        
        try:
            # Get client credentials from config
            client_id = integration_data.config.get("app_id") or self.client_id
            client_secret = self.client_secret
            
            if not client_id or not client_secret:
                return {"success": False, "error": "Missing client credentials"}
            
            # Refresh the token
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                new_token_data = response.json()
                
                # Update integration with new token
                auth_config = integration_data.auth_config
                auth_config["access_token"] = new_token_data["access_token"]
                if "refresh_token" in new_token_data:
                    auth_config["refresh_token"] = new_token_data["refresh_token"]
                
                expires_in = new_token_data.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                auth_config["expires_at"] = expires_at.isoformat()
                
                # Update in database
                result = await self.db.execute(
                    select(Integration).where(
                        and_(
                            Integration.id == integration_id,
                            Integration.user_id == user_id
                        )
                    )
                )
                integration = result.scalar()
                
                if integration:
                    integration.auth_config = encrypt_data(auth_config)
                    integration.updated_at = datetime.utcnow()
                    await self.db.commit()
                
                return {
                    "success": True,
                    "expires_at": expires_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to refresh Teams token: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_team_info(
        self,
        access_token: str,
        team_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get team information"""
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get team info: {e}")
            return None
    
    async def send_message(
        self,
        integration_id: UUID,
        user_id: str,
        team_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        content: str = "",
        content_type: str = "html",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a message to Teams"""
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return {"success": False, "error": "Integration not found"}
        
        # Use provided IDs or fall back to configured ones
        team_id = team_id or integration_data.config.get("team_id")
        channel_id = channel_id or integration_data.config.get("channel_id")
        
        if not team_id or not channel_id:
            return {"success": False, "error": "Team ID and Channel ID required"}
        
        # Create Teams integration instance
        config = IntegrationConfig(
            name=integration_data.name,
            type=IntegrationType.TEAMS,
            enabled=integration_data.enabled,
            auth_type=integration_data.auth_type,
            auth_config=integration_data.auth_config,
            custom_config=integration_data.config
        )
        
        teams = TeamsIntegration(config)
        await teams.connect()
        
        try:
            result = await teams.send_message(
                team_id=team_id,
                channel_id=channel_id,
                content=content,
                content_type=content_type,
                attachments=attachments
            )
            
            return {
                "success": "id" in result,
                "message_id": result.get("id"),
                "data": result
            }
        except Exception as e:
            logger.error(f"Failed to send Teams message: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await teams.disconnect()
    
    async def send_adaptive_card(
        self,
        integration_id: UUID,
        user_id: str,
        card_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send an adaptive card to Teams"""
        # If webhook URL is provided in card data, use direct webhook
        if "webhook_url" in card_data:
            return await self._send_webhook_card(card_data["webhook_url"], card_data)
        
        # Otherwise, send as message attachment
        team_id = card_data.get("team_id")
        channel_id = card_data.get("channel_id")
        
        attachment = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card_data.get("card", card_data)
        }
        
        return await self.send_message(
            integration_id=integration_id,
            user_id=user_id,
            team_id=team_id,
            channel_id=channel_id,
            content="<attachment></attachment>",
            attachments=[attachment]
        )
    
    async def _send_webhook_card(
        self,
        webhook_url: str,
        card_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send adaptive card via webhook"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=card_data)
                success = response.status_code == 200
                
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "response": response.text
                }
        except Exception as e:
            logger.error(f"Failed to send webhook card: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_teams(
        self,
        integration_id: UUID,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """List teams accessible by the integration"""
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return []
        
        # Create Teams integration instance
        config = IntegrationConfig(
            name=integration_data.name,
            type=IntegrationType.TEAMS,
            enabled=integration_data.enabled,
            auth_type=integration_data.auth_type,
            auth_config=integration_data.auth_config,
            custom_config=integration_data.config
        )
        
        teams = TeamsIntegration(config)
        await teams.connect()
        
        try:
            teams_list = await teams.list_teams()
            return teams_list
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return []
        finally:
            await teams.disconnect()
    
    async def list_channels(
        self,
        integration_id: UUID,
        user_id: str,
        team_id: str
    ) -> List[Dict[str, Any]]:
        """List channels in a team"""
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return []
        
        # Create Teams integration instance
        config = IntegrationConfig(
            name=integration_data.name,
            type=IntegrationType.TEAMS,
            enabled=integration_data.enabled,
            auth_type=integration_data.auth_type,
            auth_config=integration_data.auth_config,
            custom_config=integration_data.config
        )
        
        teams = TeamsIntegration(config)
        await teams.connect()
        
        try:
            channels = await teams.list_channels(team_id)
            return channels
        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []
        finally:
            await teams.disconnect()
    
    async def create_channel(
        self,
        integration_id: UUID,
        user_id: str,
        team_id: str,
        display_name: str,
        description: Optional[str] = None,
        membership_type: str = "standard"
    ) -> Dict[str, Any]:
        """Create a new channel in a team"""
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return {"error": "Integration not found"}
        
        # Create Teams integration instance
        config = IntegrationConfig(
            name=integration_data.name,
            type=IntegrationType.TEAMS,
            enabled=integration_data.enabled,
            auth_type=integration_data.auth_type,
            auth_config=integration_data.auth_config,
            custom_config=integration_data.config
        )
        
        teams = TeamsIntegration(config)
        await teams.connect()
        
        try:
            channel = await teams.create_channel(
                team_id=team_id,
                display_name=display_name,
                description=description,
                membership_type=membership_type
            )
            return channel
        except Exception as e:
            logger.error(f"Failed to create channel: {e}")
            return {"error": str(e)}
        finally:
            await teams.disconnect()
    
    async def test_connection(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Dict[str, Any]:
        """Test Teams integration connection"""
        # Use the integration service test
        result = await self.integration_service.test_integration(
            integration_id, user_id
        )
        
        if result:
            return {
                "success": result.success,
                "message": result.message,
                "details": result.details
            }
        
        return {"success": False, "message": "Integration not found"}
    
    async def handle_incoming_message(
        self,
        webhook_id: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Handle incoming message from Teams"""
        # Log the incoming message
        logger.info(
            "Incoming Teams message",
            webhook_id=webhook_id,
            message_type=payload.get("type"),
            from_user=payload.get("from", {}).get("name")
        )
        
        # TODO: Implement message handling logic
        # - Parse the message
        # - Trigger appropriate workflows
        # - Send response if needed
        
        return {"status": "received", "webhook_id": webhook_id}
    
    async def handle_card_action(
        self,
        webhook_id: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Handle adaptive card action from Teams"""
        # Log the card action
        logger.info(
            "Teams card action",
            webhook_id=webhook_id,
            action=payload.get("value", {}).get("action"),
            from_user=payload.get("from", {}).get("name")
        )
        
        # TODO: Implement card action handling
        # - Parse the action data
        # - Execute the requested action
        # - Return appropriate response
        
        return {
            "type": "message",
            "text": "Action received and processed"
        }
    
    async def send_notification(
        self,
        integration_id: UUID,
        event: IntegrationEvent
    ) -> Dict[str, Any]:
        """Send an event notification to Teams"""
        # Get integration
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar()
        
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Send via integration service
        return await self.integration_service.send_event(
            integration_id=integration_id,
            event_type=event.type,
            event_data=event.data,
            metadata=event.metadata
        )