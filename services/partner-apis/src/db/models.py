"""Database models for the Partner APIs Service"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, JSON, Index, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Base


class APIKeyStatusEnum(str, enum.Enum):
    """API key status options"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class PartnerTierEnum(str, enum.Enum):
    """Partner tier levels"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class APIVersionEnum(str, enum.Enum):
    """API version options"""
    V1 = "v1"
    V2 = "v2"


class WebhookStatusEnum(str, enum.Enum):
    """Webhook status options"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    SUSPENDED = "suspended"


class EventTypeEnum(str, enum.Enum):
    """Event type options for webhooks"""
    ASSET_CREATED = "asset.created"
    ASSET_UPDATED = "asset.updated"
    ASSET_DELETED = "asset.deleted"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    USER_CREATED = "user.created"
    INGEST_STARTED = "ingest.started"
    INGEST_COMPLETED = "ingest.completed"
    METADATA_EXTRACTED = "metadata.extracted"


class HTTPMethodEnum(str, enum.Enum):
    """HTTP method options"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class APIKey(Base):
    """API key model for partner authentication"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Reference to Partner Service
    
    # Key details
    key_id = Column(String(50), unique=True, nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Configuration
    status = Column(SQLEnum(APIKeyStatusEnum), default=APIKeyStatusEnum.ACTIVE)
    tier = Column(SQLEnum(PartnerTierEnum), default=PartnerTierEnum.BASIC)
    allowed_api_versions = Column(JSON, default=["v1"])  # List of allowed API versions
    allowed_features = Column(JSON, default=["assets"])  # List of allowed features
    allowed_ips = Column(JSON)  # IP whitelist (optional)
    allowed_domains = Column(JSON)  # Domain whitelist (optional)
    
    # Rate limiting
    rate_limit = Column(String(50), default="1000/hour")  # e.g., "1000/hour", "100/minute"
    burst_limit = Column(Integer, default=100)
    current_usage = Column(Integer, default=0)
    last_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Scopes and permissions
    scopes = Column(JSON, default=["read"])  # read, write, admin
    permissions = Column(JSON, default={})  # Detailed permissions per resource
    
    # Lifecycle
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    usage_logs = relationship("APIUsageLog", back_populates="api_key", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="api_key", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_api_key_partner_status', 'partner_id', 'status'),
        Index('ix_api_key_tier_status', 'tier', 'status'),
    )


class APIUsageLog(Base):
    """API usage logging model"""
    __tablename__ = "api_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Request details
    endpoint = Column(String(500), nullable=False)
    method = Column(SQLEnum(HTTPMethodEnum), nullable=False)
    api_version = Column(SQLEnum(APIVersionEnum), nullable=False)
    
    # Response details
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    response_size_bytes = Column(BigInteger)
    
    # Request metadata
    user_agent = Column(String(500))
    ip_address = Column(String(45))  # IPv6 compatible
    request_id = Column(String(100))
    
    # Additional data
    request_data = Column(JSON)  # Query params, headers, etc.
    error_message = Column(Text)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")
    
    # Indexes
    __table_args__ = (
        Index('ix_usage_log_api_key_timestamp', 'api_key_id', 'timestamp'),
        Index('ix_usage_log_endpoint_timestamp', 'endpoint', 'timestamp'),
        Index('ix_usage_log_status_timestamp', 'status_code', 'timestamp'),
    )


class Webhook(Base):
    """Webhook configuration model"""
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Webhook details
    name = Column(String(255), nullable=False)
    url = Column(String(2000), nullable=False)
    description = Column(Text)
    
    # Configuration
    status = Column(SQLEnum(WebhookStatusEnum), default=WebhookStatusEnum.ACTIVE)
    events = Column(JSON, nullable=False)  # List of event types to listen for
    secret = Column(String(255))  # Secret for signature verification
    
    # Delivery settings
    timeout_seconds = Column(Integer, default=30)
    retry_attempts = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    
    # Headers and authentication
    headers = Column(JSON, default={})  # Custom headers to send
    auth_type = Column(String(50))  # bearer, basic, api_key, custom
    auth_config = Column(JSON, default={})  # Auth configuration
    
    # Statistics
    total_deliveries = Column(BigInteger, default=0)
    successful_deliveries = Column(BigInteger, default=0)
    failed_deliveries = Column(BigInteger, default=0)
    last_delivery_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    last_failure_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_key = relationship("APIKey", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_webhook_api_key_status', 'api_key_id', 'status'),
        Index('ix_webhook_events', 'events'),
    )


class WebhookDelivery(Base):
    """Webhook delivery attempt model"""
    __tablename__ = "webhook_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False)
    
    # Event details
    event_type = Column(SQLEnum(EventTypeEnum), nullable=False)
    event_id = Column(String(100), nullable=False)
    
    # Delivery details
    attempt_number = Column(Integer, default=1)
    status_code = Column(Integer)
    response_body = Column(Text)
    response_headers = Column(JSON)
    error_message = Column(Text)
    
    # Request details
    request_url = Column(String(2000), nullable=False)
    request_headers = Column(JSON)
    request_body = Column(Text)
    request_signature = Column(String(255))
    
    # Timing
    duration_ms = Column(Integer)
    delivered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Success indicator
    success = Column(Boolean, default=False)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
    
    # Indexes
    __table_args__ = (
        Index('ix_delivery_webhook_delivered_at', 'webhook_id', 'delivered_at'),
        Index('ix_delivery_event_type_delivered_at', 'event_type', 'delivered_at'),
        Index('ix_delivery_success_delivered_at', 'success', 'delivered_at'),
    )


class APIQuota(Base):
    """API quota and billing model"""
    __tablename__ = "api_quotas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Quota period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Usage counters
    requests_made = Column(BigInteger, default=0)
    requests_limit = Column(BigInteger, nullable=False)
    bandwidth_used_bytes = Column(BigInteger, default=0)
    bandwidth_limit_bytes = Column(BigInteger)
    
    # Feature usage
    assets_accessed = Column(Integer, default=0)
    workflows_triggered = Column(Integer, default=0)
    webhooks_delivered = Column(Integer, default=0)
    
    # Costs (in cents)
    cost_requests = Column(Integer, default=0)
    cost_bandwidth = Column(Integer, default=0)
    cost_storage = Column(Integer, default=0)
    cost_total = Column(Integer, default=0)
    
    # Status
    over_limit = Column(Boolean, default=False)
    suspended = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_key = relationship("APIKey")
    
    # Indexes
    __table_args__ = (
        Index('ix_quota_api_key_period', 'api_key_id', 'period_start', 'period_end'),
        Index('ix_quota_over_limit', 'over_limit'),
    )


class APIEndpoint(Base):
    """API endpoint documentation and configuration model"""
    __tablename__ = "api_endpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Endpoint details
    path = Column(String(500), nullable=False)
    method = Column(SQLEnum(HTTPMethodEnum), nullable=False)
    api_version = Column(SQLEnum(APIVersionEnum), nullable=False)
    
    # Documentation
    name = Column(String(255), nullable=False)
    description = Column(Text)
    summary = Column(String(500))
    
    # Configuration
    requires_auth = Column(Boolean, default=True)
    required_scopes = Column(JSON, default=["read"])
    required_features = Column(JSON, default=[])
    rate_limit_override = Column(String(50))  # Override default rate limit
    
    # Versioning
    deprecated = Column(Boolean, default=False)
    deprecation_date = Column(DateTime(timezone=True))
    replacement_endpoint = Column(String(500))
    
    # Analytics
    total_calls = Column(BigInteger, default=0)
    avg_response_time_ms = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('ix_endpoint_path_method_version', 'path', 'method', 'api_version'),
        Index('ix_endpoint_deprecated', 'deprecated'),
    )


class APIAnalytics(Base):
    """Aggregated API analytics model"""
    __tablename__ = "api_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time dimension
    date = Column(DateTime(timezone=True), nullable=False)
    hour = Column(Integer)  # 0-23 for hourly aggregation
    
    # Dimensions
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    partner_id = Column(UUID(as_uuid=True))
    endpoint = Column(String(500))
    method = Column(SQLEnum(HTTPMethodEnum))
    api_version = Column(SQLEnum(APIVersionEnum))
    status_code = Column(Integer)
    
    # Metrics
    request_count = Column(BigInteger, default=0)
    total_response_time_ms = Column(BigInteger, default=0)
    avg_response_time_ms = Column(Float, default=0.0)
    min_response_time_ms = Column(Integer, default=0)
    max_response_time_ms = Column(Integer, default=0)
    total_response_size_bytes = Column(BigInteger, default=0)
    error_count = Column(Integer, default=0)
    
    # Relationships
    api_key = relationship("APIKey")
    
    # Indexes
    __table_args__ = (
        Index('ix_analytics_date_hour', 'date', 'hour'),
        Index('ix_analytics_api_key_date', 'api_key_id', 'date'),
        Index('ix_analytics_endpoint_date', 'endpoint', 'date'),
    )


class RateLimitBucket(Base):
    """Rate limiting bucket model"""
    __tablename__ = "rate_limit_buckets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Bucket configuration
    bucket_type = Column(String(50), nullable=False)  # hourly, daily, monthly
    window_size_seconds = Column(Integer, nullable=False)
    max_requests = Column(Integer, nullable=False)
    
    # Current state
    current_requests = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_key = relationship("APIKey")
    
    # Indexes
    __table_args__ = (
        Index('ix_rate_limit_api_key_type', 'api_key_id', 'bucket_type'),
        Index('ix_rate_limit_window_start', 'window_start'),
    )


class PartnerAPIConfiguration(Base):
    """Partner-specific API configuration model"""
    __tablename__ = "partner_api_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    
    # API access configuration
    enabled_api_versions = Column(JSON, default=["v1"])
    enabled_features = Column(JSON, default=["assets"])
    custom_rate_limits = Column(JSON, default={})  # Per-endpoint rate limits
    
    # Webhook configuration
    max_webhooks = Column(Integer, default=5)
    allowed_webhook_events = Column(JSON, default=["asset.created", "asset.updated"])
    webhook_timeout_override = Column(Integer)
    
    # Custom branding
    api_docs_branding = Column(JSON, default={})  # Custom branding for API docs
    custom_domain = Column(String(255))  # Custom API domain
    
    # Feature flags
    enable_sandbox = Column(Boolean, default=True)
    enable_webhooks = Column(Boolean, default=True)
    enable_analytics = Column(Boolean, default=True)
    enable_rate_limiting = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('ix_partner_config_partner_id', 'partner_id'),
    )