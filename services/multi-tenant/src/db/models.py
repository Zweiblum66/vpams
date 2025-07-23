"""
SQLAlchemy models for Multi-Tenant Service.

Defines database schema for tenants, domains, configurations, and usage tracking.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float, JSON, Text,
    ForeignKey, UniqueConstraint, Index, CheckConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import enum

from .base import Base


class SubscriptionPlan(enum.Enum):
    """Tenant subscription plans."""
    FREE = "free"
    STARTER = "starter"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(enum.Enum):
    """Tenant status states."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class DomainVerificationMethod(enum.Enum):
    """Domain verification methods."""
    DNS = "dns"
    FILE = "file"
    META = "meta"


class Tenant(Base):
    """
    Tenant model representing an isolated customer instance.
    """
    __tablename__ = "tenants"
    
    # Primary key
    tenant_id = Column(String(8), primary_key=True, default=lambda: uuid.uuid4().hex[:8])
    
    # Basic information
    name = Column(String(255), nullable=False)
    subdomain = Column(String(63), unique=True, nullable=False, index=True)
    admin_email = Column(String(255), nullable=False)
    
    # Status and lifecycle
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.PENDING, nullable=False)
    plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.STANDARD, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True))
    suspended_at = Column(DateTime(timezone=True))
    suspended_reason = Column(Text)
    deleted_at = Column(DateTime(timezone=True))
    
    # Configuration
    settings = Column(JSONB, default=dict)
    features = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)
    
    # Quotas and limits
    storage_quota_gb = Column(Integer, default=100)
    user_quota = Column(Integer, default=50)
    api_quota_daily = Column(Integer, default=10000)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    domains = relationship("TenantDomain", back_populates="tenant", cascade="all, delete-orphan")
    configs = relationship("TenantConfig", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("TenantUsage", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("TenantApiKey", back_populates="tenant", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_tenant_status", "status"),
        Index("idx_tenant_plan", "plan"),
        Index("idx_tenant_created", "created_at"),
        CheckConstraint("storage_quota_gb >= 0", name="check_storage_quota_positive"),
        CheckConstraint("user_quota >= 0", name="check_user_quota_positive"),
        CheckConstraint("api_quota_daily >= 0", name="check_api_quota_positive"),
    )
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
    
    @hybrid_property
    def is_trial(self) -> bool:
        """Check if tenant is in trial period."""
        return self.trial_ends_at is not None and self.trial_ends_at > datetime.utcnow()
    
    def __repr__(self):
        return f"<Tenant(tenant_id={self.tenant_id}, name={self.name}, subdomain={self.subdomain})>"


class TenantDomain(Base):
    """
    Custom domains configured for tenants.
    """
    __tablename__ = "tenant_domains"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    tenant_id = Column(String(8), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # Domain information
    domain = Column(String(255), unique=True, nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_method = Column(SQLEnum(DomainVerificationMethod), default=DomainVerificationMethod.DNS)
    verification_token = Column(String(64), unique=True)
    verification_attempts = Column(Integer, default=0)
    verified_at = Column(DateTime(timezone=True))
    
    # SSL/TLS
    ssl_enabled = Column(Boolean, default=False)
    ssl_certificate_id = Column(String(36))
    ssl_expires_at = Column(DateTime(timezone=True))
    
    # DNS records
    dns_records = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="domains")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "is_primary", name="uq_one_primary_domain",
                        postgresql_where=Column("is_primary").is_(True)),
        Index("idx_domain_tenant", "tenant_id"),
        Index("idx_domain_verified", "is_verified"),
    )
    
    def __repr__(self):
        return f"<TenantDomain(domain={self.domain}, tenant_id={self.tenant_id}, verified={self.is_verified})>"


class TenantConfig(Base):
    """
    Tenant-specific configuration settings.
    """
    __tablename__ = "tenant_configs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    tenant_id = Column(String(8), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # Configuration categories
    branding = Column(JSONB, default=dict)  # Logo, colors, fonts
    features = Column(JSONB, default=dict)  # Feature flags
    integrations = Column(JSONB, default=dict)  # Third-party integrations
    security = Column(JSONB, default=dict)  # Security settings
    notifications = Column(JSONB, default=dict)  # Notification preferences
    workflows = Column(JSONB, default=dict)  # Workflow configurations
    
    # Versioning
    version = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="configs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "version", name="uq_tenant_config_version"),
        Index("idx_config_tenant", "tenant_id"),
    )
    
    def __repr__(self):
        return f"<TenantConfig(tenant_id={self.tenant_id}, version={self.version})>"


class TenantUsage(Base):
    """
    Tenant resource usage tracking.
    """
    __tablename__ = "tenant_usage"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    tenant_id = Column(String(8), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # Usage metrics
    storage_bytes = Column(BigInteger, default=0)
    bandwidth_bytes = Column(BigInteger, default=0)
    api_calls = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    
    # Resource counts
    total_assets = Column(Integer, default=0)
    total_projects = Column(Integer, default=0)
    total_workflows = Column(Integer, default=0)
    
    # Period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_start", "period_end", name="uq_tenant_usage_period"),
        Index("idx_usage_tenant", "tenant_id"),
        Index("idx_usage_period", "period_start", "period_end"),
        CheckConstraint("period_end > period_start", name="check_valid_period"),
    )
    
    def __repr__(self):
        return f"<TenantUsage(tenant_id={self.tenant_id}, period={self.period_start}-{self.period_end})>"


class TenantApiKey(Base):
    """
    API keys for tenant authentication.
    """
    __tablename__ = "tenant_api_keys"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    tenant_id = Column(String(8), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # API key information
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(8), nullable=False)  # For display (first 8 chars)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Permissions and restrictions
    scopes = Column(JSONB, default=list)  # API scopes/permissions
    ip_whitelist = Column(JSONB, default=list)  # Allowed IP addresses
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("idx_api_key_tenant", "tenant_id"),
        Index("idx_api_key_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<TenantApiKey(name={self.name}, tenant_id={self.tenant_id}, prefix={self.key_prefix})>"


class TenantAuditLog(Base):
    """
    Audit log for tenant-related actions.
    """
    __tablename__ = "tenant_audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    tenant_id = Column(String(8), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # Audit information
    action = Column(String(50), nullable=False)  # e.g., "tenant.created", "domain.added"
    actor_id = Column(String(36))  # User who performed the action
    actor_type = Column(String(20))  # "user", "system", "api"
    
    # Details
    resource_type = Column(String(50))  # e.g., "tenant", "domain", "config"
    resource_id = Column(String(36))
    changes = Column(JSONB, default=dict)  # What changed
    metadata = Column(JSONB, default=dict)  # Additional context
    
    # Request information
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_id = Column(String(36))
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_tenant", "tenant_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_actor", "actor_id"),
    )
    
    def __repr__(self):
        return f"<TenantAuditLog(action={self.action}, tenant_id={self.tenant_id}, created_at={self.created_at})>"


# Import BigInteger for large number storage
from sqlalchemy import BigInteger