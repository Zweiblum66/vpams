"""
Pydantic schemas for Integration Service
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class IntegrationType(str, Enum):
    """Supported integration types"""
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    ZAPIER = "zapier"
    CUSTOM = "custom"


class AuthType(str, Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


class EventType(str, Enum):
    """Event types that can trigger integrations"""
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


# Base schemas
class IntegrationBase(BaseModel):
    """Base integration schema"""
    name: str = Field(..., min_length=1, max_length=255)
    type: IntegrationType
    description: Optional[str] = None
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, Any] = Field(default_factory=dict)


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration"""
    pass


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    auth_config: Optional[Dict[str, Any]] = None


class IntegrationResponse(IntegrationBase):
    """Schema for integration responses"""
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    event_count: int = 0
    error_count: int = 0
    
    class Config:
        from_attributes = True


class IntegrationListResponse(BaseModel):
    """Response for listing integrations"""
    integrations: List[IntegrationResponse]
    total: int
    skip: int
    limit: int


class IntegrationTestResponse(BaseModel):
    """Response for integration test"""
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


# Webhook schemas
class WebhookBase(BaseModel):
    """Base webhook schema"""
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    events: List[EventType]
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: int = Field(30, ge=1, le=300)
    retry_count: int = Field(3, ge=0, le=10)
    enabled: bool = True


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook"""
    pass


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    events: Optional[List[EventType]] = None
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    enabled: Optional[bool] = None


class WebhookResponse(WebhookBase):
    """Schema for webhook responses"""
    id: UUID
    integration_id: UUID
    verified: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Response for listing webhooks"""
    webhooks: List[WebhookResponse]
    total: int
    skip: int
    limit: int


class WebhookEventResponse(BaseModel):
    """Response for webhook event history"""
    id: UUID
    event_type: str
    status: str
    attempts: int
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Slack schemas
class SlackIntegrationConfig(BaseModel):
    """Slack-specific configuration"""
    default_channel: Optional[str] = None
    notification_settings: Dict[str, bool] = Field(default_factory=dict)
    mention_users: bool = True
    thread_replies: bool = False
    
    @validator('default_channel')
    def validate_channel(cls, v):
        if v and not (v.startswith('#') or v.startswith('@')):
            v = f'#{v}'
        return v


class SlackOAuthResponse(BaseModel):
    """Response from Slack OAuth flow"""
    ok: bool
    access_token: str
    token_type: str = "bot"
    scope: str
    bot_user_id: str
    app_id: str
    team: Dict[str, str]
    enterprise: Optional[Dict[str, str]] = None
    authed_user: Dict[str, str]


# Teams schemas
class TeamsIntegrationConfig(BaseModel):
    """Teams-specific configuration"""
    default_channel: Optional[str] = None
    notification_settings: Dict[str, bool] = Field(default_factory=dict)
    adaptive_cards: bool = True
    mentions_enabled: bool = True


class TeamsChannelInfo(BaseModel):
    """Teams channel information"""
    id: str
    name: str
    description: Optional[str] = None


# Event schemas
class IntegrationEventData(BaseModel):
    """Data sent with integration events"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationEventResponse(BaseModel):
    """Response from sending an integration event"""
    success: bool
    integration_id: UUID
    event_id: str
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None


# Template schemas
class IntegrationTemplateResponse(BaseModel):
    """Response for integration templates"""
    id: UUID
    name: str
    type: IntegrationType
    description: Optional[str] = None
    config_template: Dict[str, Any]
    required_fields: List[str]
    icon: Optional[str] = None
    category: Optional[str] = None
    is_featured: bool = False
    
    class Config:
        from_attributes = True


# Additional Teams schemas
class TeamsInstallRequest(BaseModel):
    """Request to install Teams app"""
    tenant_id: Optional[str] = None
    client_id: str
    redirect_uri: str
    state: Optional[str] = None
    additional_scopes: Optional[List[str]] = None


class TeamsOAuthCallback(BaseModel):
    """Teams OAuth callback data"""
    code: str
    state: str
    client_id: str
    client_secret: str
    redirect_uri: str
    tenant_id: Optional[str] = None
    team_id: Optional[str] = None
    channel_id: Optional[str] = None
    webhook_url: Optional[str] = None
    integration_name: Optional[str] = None


class TeamsWebhookPayload(BaseModel):
    """Teams incoming webhook payload"""
    type: str
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    from_user: Optional[Dict[str, Any]] = Field(alias="from")
    conversation: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    value: Optional[Dict[str, Any]] = None


class TeamsMessageRequest(BaseModel):
    """Request to send Teams message"""
    team_id: Optional[str] = None
    channel_id: Optional[str] = None
    content: str
    content_type: str = "html"
    attachments: Optional[List[Dict[str, Any]]] = None


class TeamsTeamResponse(BaseModel):
    """Teams team information"""
    id: str
    displayName: str
    description: Optional[str] = None
    webUrl: Optional[str] = None


class TeamsChannelResponse(BaseModel):
    """Teams channel information"""
    id: str
    displayName: str
    description: Optional[str] = None
    membershipType: str = "standard"
    webUrl: Optional[str] = None