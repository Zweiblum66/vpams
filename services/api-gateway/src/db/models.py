"""
Database models for API Gateway

Includes models for API keys, rate limiting, and gateway-specific data.
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.base import Base


class APIKey(Base):
    """API Key model for application authentication"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Key metadata
    prefix = Column(String(10), nullable=False)  # For easy identification (e.g., "mams_")
    hash = Column(String(255), nullable=False)  # Hashed version of the key
    last_four = Column(String(4), nullable=False)  # Last 4 characters for identification
    
    # Ownership and permissions
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Optional user association
    application_id = Column(UUID(as_uuid=True), nullable=True)  # Optional app association
    scopes = Column(JSON, default=list)  # List of permitted scopes/permissions
    
    # Status and limits
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_override = Column(Integer, nullable=True)  # Custom rate limit for this key
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)  # Additional custom metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    # Relationships
    usage_logs = relationship("APIKeyUsageLog", back_populates="api_key", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_api_key_active', 'is_active', 'key'),
        Index('idx_api_key_user', 'user_id', 'is_active'),
        Index('idx_api_key_app', 'application_id', 'is_active'),
        Index('idx_api_key_expires', 'expires_at', 'is_active'),
    )


class APIKeyUsageLog(Base):
    """Log of API key usage for analytics and security"""
    __tablename__ = "api_key_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Request information
    request_id = Column(String(64), nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=False)
    
    # Client information
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    api_key = relationship("APIKey", back_populates="usage_logs")
    
    # Indexes for analytics
    __table_args__ = (
        Index('idx_usage_key_time', 'api_key_id', 'created_at'),
        Index('idx_usage_time', 'created_at'),
        Index('idx_usage_status', 'status_code', 'created_at'),
    )


class RateLimitOverride(Base):
    """Custom rate limit overrides for specific keys or IPs"""
    __tablename__ = "rate_limit_overrides"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Target of override
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Rate limit settings
    requests_per_minute = Column(Integer, nullable=True)
    requests_per_hour = Column(Integer, nullable=True)
    requests_per_day = Column(Integer, nullable=True)
    burst_size = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    reason = Column(String(255), nullable=True)
    
    # Validity period
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_rate_override_key', 'api_key_id', 'is_active'),
        Index('idx_rate_override_ip', 'ip_address', 'is_active'),
        Index('idx_rate_override_user', 'user_id', 'is_active'),
    )


class ServiceRegistration(Base):
    """Registration of downstream services"""
    __tablename__ = "service_registrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Service endpoints
    base_url = Column(String(500), nullable=False)
    health_check_path = Column(String(255), default="/health")
    
    # Service metadata
    version = Column(String(50), nullable=True)
    api_version = Column(String(10), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_healthy = Column(Boolean, default=True, nullable=False)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    
    # Load balancing configuration
    weight = Column(Integer, default=100)  # For weighted load balancing
    max_connections = Column(Integer, nullable=True)
    timeout_seconds = Column(Integer, default=30)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GatewayAuditLog(Base):
    """Audit log for gateway-level events"""
    __tablename__ = "gateway_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event information
    event_type = Column(String(100), nullable=False)  # e.g., "api_key_created", "rate_limit_exceeded"
    event_category = Column(String(50), nullable=False)  # e.g., "security", "admin", "system"
    severity = Column(String(20), nullable=False)  # e.g., "info", "warning", "critical"
    
    # Actor information
    actor_type = Column(String(50), nullable=False)  # e.g., "user", "api_key", "system"
    actor_id = Column(String(255), nullable=True)
    actor_ip = Column(String(45), nullable=True)
    
    # Event details
    resource_type = Column(String(50), nullable=True)  # e.g., "api_key", "service"
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    
    # Request context
    request_id = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for querying
    __table_args__ = (
        Index('idx_audit_event_time', 'event_type', 'created_at'),
        Index('idx_audit_category_time', 'event_category', 'created_at'),
        Index('idx_audit_actor', 'actor_type', 'actor_id', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id', 'created_at'),
    )