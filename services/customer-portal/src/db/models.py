"""
Database models for Customer Portal
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, DECIMAL, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from src.db.base import Base


class SubscriptionTier(PyEnum):
    """Subscription tier levels"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TicketStatus(PyEnum):
    """Support ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(PyEnum):
    """Support ticket priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvoiceStatus(PyEnum):
    """Invoice status"""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    website = Column(String(255))
    
    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Billing
    tax_id = Column(String(50))
    billing_email = Column(String(255))
    
    # Settings
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="organization", uselist=False)
    users = relationship("OrganizationUser", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")
    support_tickets = relationship("SupportTicket", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")


class Subscription(Base):
    """Subscription model"""
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Plan details
    tier = Column(Enum(SubscriptionTier), nullable=False)
    plan_name = Column(String(100), nullable=False)
    
    # Limits
    user_limit = Column(Integer)
    storage_limit_gb = Column(Integer)
    api_calls_limit = Column(Integer)
    
    # Pricing
    monthly_price = Column(DECIMAL(10, 2), nullable=False)
    annual_price = Column(DECIMAL(10, 2))
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    trial_end_date = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_trial = Column(Boolean, default=False)
    auto_renew = Column(Boolean, default=True)
    
    # Usage
    current_users = Column(Integer, default=0)
    current_storage_gb = Column(Float, default=0)
    current_api_calls = Column(Integer, default=0)
    
    # Metadata
    features = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="subscription")
    addons = relationship("SubscriptionAddon", back_populates="subscription")


class SubscriptionAddon(Base):
    """Subscription add-ons"""
    __tablename__ = "subscription_addons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    monthly_price = Column(DECIMAL(10, 2), nullable=False)
    
    # Limits modification
    extra_users = Column(Integer, default=0)
    extra_storage_gb = Column(Integer, default=0)
    extra_api_calls = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="addons")


class OrganizationUser(Base):
    """Organization users (link to main user table)"""
    __tablename__ = "organization_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to main users table
    
    role = Column(String(50), nullable=False)  # admin, member, billing, readonly
    is_primary = Column(Boolean, default=False)
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id'),
    )


class APIKey(Base):
    """API Keys for organization"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    prefix = Column(String(10), nullable=False)  # Visible prefix
    
    permissions = Column(JSON, default=list)
    rate_limit = Column(Integer, default=1000)
    
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="api_keys")


class SupportTicket(Base):
    """Support tickets"""
    __tablename__ = "support_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    ticket_number = Column(String(20), unique=True, nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(String(50))
    
    created_by = Column(UUID(as_uuid=True), nullable=False)
    assigned_to = Column(UUID(as_uuid=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="support_tickets")
    comments = relationship("TicketComment", back_populates="ticket")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_org_status', 'organization_id', 'status'),
        Index('idx_ticket_number', 'ticket_number'),
    )


class TicketComment(Base):
    """Support ticket comments"""
    __tablename__ = "ticket_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=False)
    
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="comments")


class Invoice(Base):
    """Invoices"""
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    
    # Amounts
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    tax_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Dates
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_date = Column(DateTime(timezone=True))
    
    # Payment
    payment_method = Column(String(50))
    payment_reference = Column(String(100))
    
    # Metadata
    line_items = Column(JSON, default=list)
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="invoices")
    
    # Indexes
    __table_args__ = (
        Index('idx_invoice_org_status', 'organization_id', 'status'),
        Index('idx_invoice_number', 'invoice_number'),
    )


class UsageMetric(Base):
    """Usage metrics tracking"""
    __tablename__ = "usage_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    metric_date = Column(DateTime(timezone=True), nullable=False)
    
    # Usage data
    active_users = Column(Integer, default=0)
    storage_gb = Column(Float, default=0)
    bandwidth_gb = Column(Float, default=0)
    api_calls = Column(Integer, default=0)
    
    # Asset metrics
    assets_uploaded = Column(Integer, default=0)
    assets_downloaded = Column(Integer, default=0)
    assets_total = Column(Integer, default=0)
    
    # Feature usage
    ai_operations = Column(Integer, default=0)
    workflow_executions = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('organization_id', 'metric_date'),
        Index('idx_usage_org_date', 'organization_id', 'metric_date'),
    )