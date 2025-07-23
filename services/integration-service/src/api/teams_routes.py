"""
Microsoft Teams integration API routes
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import structlog

from ..db.base import get_db
from ..core.auth import get_current_user
from ..models.schemas import (
    IntegrationCreate, IntegrationResponse, IntegrationType, AuthType,
    TeamsInstallRequest, TeamsOAuthCallback, TeamsWebhookPayload,
    TeamsMessageRequest, TeamsChannelResponse, TeamsTeamResponse
)
from ..services.integration_service import IntegrationService
from ..services.teams_service import TeamsService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/integrations/teams", tags=["teams"])


@router.post("/install", response_model=Dict[str, str])
async def install_teams_app(
    request: TeamsInstallRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate Teams OAuth URL for app installation
    """
    # Teams OAuth endpoints
    tenant = request.tenant_id or "common"
    client_id = request.client_id
    redirect_uri = request.redirect_uri
    
    # Scopes required for Teams integration
    scopes = [
        "ChannelMessage.Send",
        "Channel.ReadBasic.All",
        "Team.ReadBasic.All",
        "User.Read"
    ]
    
    if request.additional_scopes:
        scopes.extend(request.additional_scopes)
    
    # Build authorization URL
    auth_url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        f"client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&response_mode=query"
        f"&scope={' '.join(scopes)}"
        f"&state={request.state or current_user['user_id']}"
    )
    
    return {
        "auth_url": auth_url,
        "state": request.state or current_user["user_id"]
    }


@router.post("/oauth/callback", response_model=IntegrationResponse)
async def teams_oauth_callback(
    callback: TeamsOAuthCallback,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Handle Teams OAuth callback and create integration
    """
    teams_service = TeamsService(db)
    
    try:
        # Exchange code for access token
        token_data = await teams_service.exchange_code_for_token(
            code=callback.code,
            client_id=callback.client_id,
            client_secret=callback.client_secret,
            redirect_uri=callback.redirect_uri,
            tenant_id=callback.tenant_id
        )
        
        if not token_data.get("access_token"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token from Teams"
            )
        
        # Get team and channel information
        team_info = None
        if callback.team_id:
            team_info = await teams_service.get_team_info(
                token_data["access_token"],
                callback.team_id
            )
        
        # Create integration
        integration_data = IntegrationCreate(
            name=callback.integration_name or f"Teams - {team_info.get('displayName', 'Workspace') if team_info else 'Workspace'}",
            type=IntegrationType.TEAMS,
            description=f"Microsoft Teams integration{' for team: ' + team_info.get('displayName') if team_info else ''}",
            enabled=True,
            config={
                "tenant_id": callback.tenant_id or token_data.get("tenant_id", "common"),
                "team_id": callback.team_id,
                "channel_id": callback.channel_id,
                "webhook_url": callback.webhook_url,
                "app_id": callback.client_id
            },
            auth_type=AuthType.OAUTH2,
            auth_config={
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": token_data.get("expires_at"),
                "tenant_id": callback.tenant_id or token_data.get("tenant_id"),
                "scope": token_data.get("scope")
            }
        )
        
        integration_service = IntegrationService(db)
        integration = await integration_service.create_integration(
            integration_data,
            current_user["user_id"]
        )
        
        logger.info(
            "Teams integration created",
            integration_id=integration.id,
            user_id=current_user["user_id"],
            team_id=callback.team_id
        )
        
        return integration
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during Teams OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Teams: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Teams OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/webhook/{webhook_id}")
async def handle_teams_webhook(
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming webhooks from Teams
    """
    teams_service = TeamsService(db)
    
    # Get raw body for signature verification
    body = await request.body()
    headers = dict(request.headers)
    
    try:
        # Parse webhook payload
        import json
        payload = json.loads(body)
        
        # Handle different webhook types
        webhook_type = payload.get("type")
        
        if webhook_type == "message":
            # Handle incoming message
            result = await teams_service.handle_incoming_message(
                webhook_id=webhook_id,
                payload=payload,
                headers=headers
            )
        elif webhook_type == "invoke":
            # Handle adaptive card actions
            result = await teams_service.handle_card_action(
                webhook_id=webhook_id,
                payload=payload,
                headers=headers
            )
        else:
            # Log unknown webhook type
            logger.warning(f"Unknown Teams webhook type: {webhook_type}")
            result = {"status": "ignored", "type": webhook_type}
        
        return Response(
            content=json.dumps(result),
            media_type="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Teams webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/{integration_id}/message", response_model=Dict[str, Any])
async def send_teams_message(
    integration_id: UUID,
    message: TeamsMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send a message to Teams
    """
    teams_service = TeamsService(db)
    
    result = await teams_service.send_message(
        integration_id=integration_id,
        user_id=current_user["user_id"],
        team_id=message.team_id,
        channel_id=message.channel_id,
        content=message.content,
        content_type=message.content_type,
        attachments=message.attachments
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send message")
        )
    
    return result


@router.post("/{integration_id}/adaptive-card", response_model=Dict[str, Any])
async def send_adaptive_card(
    integration_id: UUID,
    card_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send an adaptive card to Teams
    """
    teams_service = TeamsService(db)
    
    result = await teams_service.send_adaptive_card(
        integration_id=integration_id,
        user_id=current_user["user_id"],
        card_data=card_data
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send adaptive card")
        )
    
    return result


@router.get("/{integration_id}/teams", response_model=List[TeamsTeamResponse])
async def list_teams(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List Teams the integration has access to
    """
    teams_service = TeamsService(db)
    
    teams = await teams_service.list_teams(
        integration_id=integration_id,
        user_id=current_user["user_id"]
    )
    
    return teams


@router.get("/{integration_id}/teams/{team_id}/channels", response_model=List[TeamsChannelResponse])
async def list_channels(
    integration_id: UUID,
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List channels in a Team
    """
    teams_service = TeamsService(db)
    
    channels = await teams_service.list_channels(
        integration_id=integration_id,
        user_id=current_user["user_id"],
        team_id=team_id
    )
    
    return channels


@router.post("/{integration_id}/teams/{team_id}/channels", response_model=TeamsChannelResponse)
async def create_channel(
    integration_id: UUID,
    team_id: str,
    channel_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new channel in a Team
    """
    teams_service = TeamsService(db)
    
    channel = await teams_service.create_channel(
        integration_id=integration_id,
        user_id=current_user["user_id"],
        team_id=team_id,
        display_name=channel_data["displayName"],
        description=channel_data.get("description"),
        membership_type=channel_data.get("membershipType", "standard")
    )
    
    return channel


@router.post("/{integration_id}/test", response_model=Dict[str, Any])
async def test_teams_connection(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Test Teams integration connection
    """
    teams_service = TeamsService(db)
    
    result = await teams_service.test_connection(
        integration_id=integration_id,
        user_id=current_user["user_id"]
    )
    
    return result


@router.post("/{integration_id}/refresh-token", response_model=Dict[str, Any])
async def refresh_teams_token(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Refresh Teams OAuth token
    """
    teams_service = TeamsService(db)
    
    result = await teams_service.refresh_token(
        integration_id=integration_id,
        user_id=current_user["user_id"]
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to refresh token")
        )
    
    return result