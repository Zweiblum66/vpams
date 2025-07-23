"""
Database models for Integration Service
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, JSON, Text, Integer,
    ForeignKey, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from .base import Base


class IntegrationType(str, Enum):
    """Types of integrations"""
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    ZAPIER = "zapier"
    CUSTOM = "custom"


class Integration(Base):
    """Integration configurations"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(IntegrationType), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    
    # Configuration (encrypted in production)
    config = Column(JSON, nullable=False)
    
    # Authentication
    auth_type = Column(String(50))  # none, api_key, oauth2, etc.
    auth_config = Column(JSON)  # Encrypted auth details
    
    # Owner
    user_id = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Statistics
    event_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Relationships
    webhooks = relationship("Webhook", back_populates="integration", cascade="all, delete-orphan")
    events = relationship("IntegrationEvent", back_populates="integration", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_integration_name_user"),
        Index("idx_integrations_user_id", "user_id"),
        Index("idx_integrations_type", "type"),
        Index("idx_integrations_enabled", "enabled"),
    )


class Webhook(Base):
    """Webhook configurations"""
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(String(255))  # For signature verification
    
    # Events to subscribe to
    events = Column(JSON, nullable=False)  # List of event types
    
    # Configuration
    headers = Column(JSON)  # Custom headers
    timeout = Column(Integer, default=30)
    retry_count = Column(Integer, default=3)
    
    # Status
    enabled = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_triggered_at = Column(DateTime(timezone=True))
    
    # Statistics
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Relationships
    integration = relationship("Integration", back_populates="webhooks")
    
    __table_args__ = (
        Index("idx_webhooks_integration_id", "integration_id"),
        Index("idx_webhooks_enabled", "enabled"),
    )


class IntegrationEvent(Base):
    """Events sent to integrations"""
    __tablename__ = "integration_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=False)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id"))
    
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
    
    # Delivery status
    status = Column(String(50), nullable=False)  # pending, success, failed, retrying
    attempts = Column(Integer, default=0)
    
    # Response
    response_status = Column(Integer)
    response_body = Column(Text)
    response_headers = Column(JSON)
    
    # Error info
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    integration = relationship("Integration", back_populates="events")
    
    __table_args__ = (
        Index("idx_integration_events_integration_id", "integration_id"),
        Index("idx_integration_events_status", "status"),
        Index("idx_integration_events_event_type", "event_type"),
        Index("idx_integration_events_created_at", "created_at"),
    )


class SlackIntegration(Base):
    """Slack-specific integration details"""
    __tablename__ = "slack_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id"), unique=True, nullable=False)
    
    # Slack workspace info
    team_id = Column(String(255), nullable=False)
    team_name = Column(String(255))
    
    # OAuth tokens (encrypted)
    access_token = Column(Text, nullable=False)
    bot_user_id = Column(String(255))
    
    # Configuration
    default_channel = Column(String(255))
    notification_settings = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_slack_integrations_team_id", "team_id"),
    )


class TeamsIntegration(Base):
    """Microsoft Teams-specific integration details"""
    __tablename__ = "teams_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id"), unique=True, nullable=False)
    
    # Teams tenant info
    tenant_id = Column(String(255), nullable=False)
    service_url = Column(Text, nullable=False)
    
    # Bot registration
    bot_id = Column(String(255))
    bot_name = Column(String(255))
    
    # Configuration
    default_channel = Column(String(500))
    notification_settings = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_teams_integrations_tenant_id", "tenant_id"),
    )


class IntegrationTemplate(Base):
    """Pre-configured integration templates"""
    __tablename__ = "integration_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(SQLEnum(IntegrationType), nullable=False)
    description = Column(Text)
    
    # Template configuration
    config_template = Column(JSON, nullable=False)
    required_fields = Column(JSON)  # List of required config fields
    
    # UI hints
    icon = Column(String(255))
    category = Column(String(100))
    
    # Availability
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_integration_templates_type", "type"),
        Index("idx_integration_templates_is_public", "is_public"),
    )