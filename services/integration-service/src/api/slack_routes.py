"""
Slack integration routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import RedirectResponse
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import httpx
import hmac
import hashlib
import time
import json
from urllib.parse import urlencode

from ..db.base import get_db
from ..models.schemas import (
    SlackIntegrationConfig, SlackOAuthResponse,
    IntegrationCreate, IntegrationType, AuthType
)
from ..services.slack_service import SlackService
from ..services.integration_service import IntegrationService
from ..core.auth import get_current_user
from ..core.config import settings

router = APIRouter(prefix="/slack", tags=["slack"])


@router.get("/install")
async def slack_install(
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Initiate Slack OAuth installation flow
    
    This generates the Slack installation URL for the app.
    """
    if not settings.SLACK_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Slack integration not configured"
        )
    
    # Build OAuth URL
    params = {
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": "chat:write,channels:read,users:read,files:write,commands",
        "redirect_uri": redirect_uri or f"{settings.API_BASE_URL}/api/v1/slack/oauth/callback"
    }
    
    if state:
        params["state"] = state
    
    oauth_url = f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    
    return {"install_url": oauth_url}


@router.get("/oauth/callback")
async def slack_oauth_callback(
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Slack OAuth callback
    
    This endpoint is called by Slack after the user authorizes the app.
    """
    if not all([settings.SLACK_CLIENT_ID, settings.SLACK_CLIENT_SECRET]):
        raise HTTPException(
            status_code=500,
            detail="Slack integration not configured"
        )
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": settings.SLACK_CLIENT_ID,
                "client_secret": settings.SLACK_CLIENT_SECRET,
                "code": code
            }
        )
        
        data = response.json()
        
        if not data.get("ok"):
            raise HTTPException(
                status_code=400,
                detail=f"Slack OAuth failed: {data.get('error', 'Unknown error')}"
            )
    
    # Parse the response
    oauth_response = SlackOAuthResponse(**data)
    
    # Extract user_id from state if provided
    user_id = None
    if state:
        try:
            state_data = json.loads(state)
            user_id = state_data.get("user_id")
        except:
            pass
    
    if not user_id:
        # For now, we'll need the user to be authenticated
        raise HTTPException(
            status_code=401,
            detail="User authentication required"
        )
    
    # Create integration in database
    service = IntegrationService(db)
    slack_service = SlackService(db)
    
    # Create the integration
    integration_data = IntegrationCreate(
        name=f"Slack - {oauth_response.team['name']}",
        type=IntegrationType.SLACK,
        description=f"Slack workspace: {oauth_response.team['name']}",
        enabled=True,
        config={
            "team_id": oauth_response.team["id"],
            "team_name": oauth_response.team["name"],
            "bot_user_id": oauth_response.bot_user_id,
            "app_id": oauth_response.app_id
        },
        auth_type=AuthType.OAUTH2,
        auth_config={
            "access_token": oauth_response.access_token,
            "token_type": oauth_response.token_type,
            "scope": oauth_response.scope
        }
    )
    
    integration = await service.create_integration(integration_data, user_id=user_id)
    
    # Store Slack-specific data
    await slack_service.create_slack_integration(
        integration_id=integration.id,
        team_id=oauth_response.team["id"],
        team_name=oauth_response.team["name"],
        access_token=oauth_response.access_token,
        bot_user_id=oauth_response.bot_user_id
    )
    
    # Redirect to success page or return success response
    return {
        "success": True,
        "integration_id": str(integration.id),
        "team_name": oauth_response.team["name"]
    }


@router.post("/webhook")
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming Slack webhooks (events, commands, interactions)
    
    This endpoint receives all webhook events from Slack.
    """
    # Verify request signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    if not all([timestamp, signature, settings.SLACK_SIGNING_SECRET]):
        raise HTTPException(status_code=401, detail="Invalid request")
    
    # Check timestamp to prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=401, detail="Request too old")
    
    # Get request body
    body = await request.body()
    
    # Verify signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse body
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = json.loads(body)
    else:
        # URL-encoded (for slash commands)
        from urllib.parse import parse_qs
        parsed = parse_qs(body.decode('utf-8'))
        data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    
    # Handle different types of requests
    if data.get("type") == "url_verification":
        # URL verification challenge
        return {"challenge": data["challenge"]}
    
    # Process the webhook
    service = SlackService(db)
    
    try:
        await service.process_webhook(data)
        return {"ok": True}
    except Exception as e:
        # Log error but return success to avoid Slack retries
        return {"ok": True, "error": str(e)}


@router.post("/{integration_id}/message")
async def send_slack_message(
    integration_id: UUID,
    channel: str,
    text: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to a Slack channel
    
    - **channel**: Channel ID or name (e.g., "#general" or "C1234567890")
    - **text**: Plain text message
    - **blocks**: Rich message blocks (Slack Block Kit format)
    - **thread_ts**: Thread timestamp to reply to
    """
    service = SlackService(db)
    
    try:
        result = await service.send_message(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{integration_id}/channels")
async def list_slack_channels(
    integration_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List available Slack channels
    """
    service = SlackService(db)
    
    try:
        result = await service.list_channels(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            limit=limit,
            cursor=cursor
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{integration_id}/users")
async def list_slack_users(
    integration_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List Slack workspace users
    """
    service = SlackService(db)
    
    try:
        result = await service.list_users(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            limit=limit,
            cursor=cursor
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{integration_id}/file")
async def upload_file_to_slack(
    integration_id: UUID,
    channels: List[str],
    file_url: str,
    filename: str,
    title: Optional[str] = None,
    initial_comment: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file to Slack channels
    
    - **channels**: List of channel IDs to share the file to
    - **file_url**: URL of the file to upload
    - **filename**: Name for the file
    - **title**: Title for the file
    - **initial_comment**: Message to post with the file
    """
    service = SlackService(db)
    
    try:
        result = await service.upload_file(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            channels=channels,
            file_url=file_url,
            filename=filename,
            title=title,
            initial_comment=initial_comment
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{integration_id}/notification")
async def send_notification(
    integration_id: UUID,
    event_type: str,
    event_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a formatted notification based on event type
    
    This endpoint automatically formats the message based on the event type
    and sends it to the configured default channel.
    """
    service = SlackService(db)
    
    try:
        result = await service.send_notification(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            event_type=event_type,
            event_data=event_data
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{integration_id}/config")
async def update_slack_config(
    integration_id: UUID,
    config: SlackIntegrationConfig,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Slack integration configuration
    """
    service = SlackService(db)
    
    try:
        result = await service.update_config(
            integration_id=integration_id,
            user_id=current_user["user_id"],
            config=config
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return {"success": True, "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))