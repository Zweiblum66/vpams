"""Database models for the Reseller Tools Service"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Base


class ResellerStatusEnum(str, enum.Enum):
    """Reseller status options"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ResellerTierEnum(str, enum.Enum):
    """Reseller tier levels"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class CustomerStatusEnum(str, enum.Enum):
    """Customer status options"""
    PROSPECT = "prospect"
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class LeadStatusEnum(str, enum.Enum):
    """Lead status options"""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class CommissionTypeEnum(str, enum.Enum):
    """Commission calculation types"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"


class PaymentStatusEnum(str, enum.Enum):
    """Payment status options"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Reseller(Base):
    """Reseller model for partner management"""
    __tablename__ = "resellers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Reference to User Management Service
    company_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    
    # Address information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Business information
    business_license = Column(String(100))
    tax_id = Column(String(100))
    website = Column(String(255))
    
    # Reseller details
    status = Column(SQLEnum(ResellerStatusEnum), default=ResellerStatusEnum.PENDING)
    tier = Column(SQLEnum(ResellerTierEnum), default=ResellerTierEnum.BRONZE)
    commission_rate = Column(Float, default=0.15)  # 15% default commission
    territory = Column(JSON)  # Geographic territory restrictions
    
    # Financial information
    payment_terms = Column(Integer, default=30)  # Net 30 days
    credit_limit = Column(Float, default=10000.0)
    current_balance = Column(Float, default=0.0)
    
    # Metadata
    notes = Column(Text)
    onboarding_completed = Column(Boolean, default=False)
    contract_signed_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customers = relationship("Customer", back_populates="reseller", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="reseller", cascade="all, delete-orphan")
    pricing_tiers = relationship("PricingTier", back_populates="reseller", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="reseller", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_reseller_status_tier', 'status', 'tier'),
        Index('ix_reseller_email_status', 'email', 'status'),
    )


class Customer(Base):
    """Customer model for reseller's clients"""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Company information
    company_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    
    # Address information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Customer details
    status = Column(SQLEnum(CustomerStatusEnum), default=CustomerStatusEnum.PROSPECT)
    industry = Column(String(100))
    company_size = Column(String(50))  # e.g., "1-10", "11-50", "51-200"
    annual_revenue = Column(String(50))  # Revenue range
    
    # Subscription information
    subscription_tier = Column(String(100))
    monthly_value = Column(Float, default=0.0)
    contract_value = Column(Float, default=0.0)
    contract_length = Column(Integer)  # months
    renewal_date = Column(DateTime(timezone=True))
    
    # Sales information
    lead_source = Column(String(100))
    sales_stage = Column(String(100))
    probability = Column(Float, default=0.0)  # 0-1 scale
    expected_close_date = Column(DateTime(timezone=True))
    
    # Metadata
    notes = Column(Text)
    tags = Column(JSON)  # Flexible tagging system
    custom_fields = Column(JSON)  # Custom fields for reseller use
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reseller = relationship("Reseller", back_populates="customers")
    activities = relationship("CustomerActivity", back_populates="customer", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_customer_reseller_status', 'reseller_id', 'status'),
        Index('ix_customer_company_name', 'company_name'),
    )


class Lead(Base):
    """Lead model for sales pipeline management"""
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Lead information
    company_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    title = Column(String(255))
    
    # Lead details
    status = Column(SQLEnum(LeadStatusEnum), default=LeadStatusEnum.NEW)
    source = Column(String(100))  # Website, referral, event, etc.
    industry = Column(String(100))
    company_size = Column(String(50))
    annual_revenue = Column(String(50))
    
    # Sales information
    estimated_value = Column(Float, default=0.0)
    probability = Column(Float, default=0.0)  # 0-1 scale
    expected_close_date = Column(DateTime(timezone=True))
    last_contact_date = Column(DateTime(timezone=True))
    next_follow_up = Column(DateTime(timezone=True))
    
    # Lead scoring
    score = Column(Integer, default=0)
    temperature = Column(String(20), default="cold")  # cold, warm, hot
    
    # Metadata
    notes = Column(Text)
    tags = Column(JSON)
    requirements = Column(JSON)  # Specific requirements/interests
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reseller = relationship("Reseller", back_populates="leads")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_lead_reseller_status', 'reseller_id', 'status'),
        Index('ix_lead_score_temp', 'score', 'temperature'),
    )


class PricingTier(Base):
    """Pricing tier model for reseller-specific pricing"""
    __tablename__ = "pricing_tiers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Tier information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tier_level = Column(Integer, default=1)  # 1=basic, 2=standard, 3=premium
    
    # Pricing details
    base_price = Column(Float, nullable=False)
    reseller_price = Column(Float, nullable=False)  # Price reseller pays
    suggested_retail_price = Column(Float)
    minimum_retail_price = Column(Float)
    
    # Features and limits
    features = Column(JSON)  # Feature list
    user_limit = Column(Integer)
    storage_limit_gb = Column(Integer)
    bandwidth_limit_gb = Column(Integer)
    
    # Terms
    billing_cycle = Column(String(20), default="monthly")  # monthly, annually
    setup_fee = Column(Float, default=0.0)
    contract_length = Column(Integer)  # months
    
    # Status
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reseller = relationship("Reseller", back_populates="pricing_tiers")
    
    # Indexes
    __table_args__ = (
        Index('ix_pricing_reseller_active', 'reseller_id', 'active'),
    )


class Commission(Base):
    """Commission tracking model"""
    __tablename__ = "commissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    
    # Commission details
    commission_type = Column(SQLEnum(CommissionTypeEnum), default=CommissionTypeEnum.PERCENTAGE)
    order_id = Column(String(255))  # External order reference
    product_name = Column(String(255))
    
    # Financial information
    sale_amount = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)
    commission_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Payment tracking
    payment_status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    payment_date = Column(DateTime(timezone=True))
    payment_reference = Column(String(255))
    
    # Dates
    sale_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reseller = relationship("Reseller", back_populates="commissions")
    customer = relationship("Customer")
    
    # Indexes
    __table_args__ = (
        Index('ix_commission_reseller_status', 'reseller_id', 'payment_status'),
        Index('ix_commission_due_date', 'due_date'),
    )


class CustomerActivity(Base):
    """Customer activity tracking model"""
    __tablename__ = "customer_activities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # User who performed the activity
    
    # Activity details
    activity_type = Column(String(100), nullable=False)  # call, email, meeting, demo, etc.
    subject = Column(String(255))
    description = Column(Text)
    outcome = Column(String(100))
    duration_minutes = Column(Integer)
    
    # Follow-up
    next_action = Column(String(255))
    next_action_date = Column(DateTime(timezone=True))
    
    # Metadata
    attachments = Column(JSON)  # File references
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="activities")
    
    # Indexes
    __table_args__ = (
        Index('ix_activity_customer_type', 'customer_id', 'activity_type'),
        Index('ix_activity_date', 'created_at'),
    )


class LeadActivity(Base):
    """Lead activity tracking model"""
    __tablename__ = "lead_activities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # User who performed the activity
    
    # Activity details
    activity_type = Column(String(100), nullable=False)  # call, email, meeting, demo, etc.
    subject = Column(String(255))
    description = Column(Text)
    outcome = Column(String(100))
    duration_minutes = Column(Integer)
    
    # Follow-up
    next_action = Column(String(255))
    next_action_date = Column(DateTime(timezone=True))
    
    # Metadata
    attachments = Column(JSON)  # File references
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    lead = relationship("Lead", back_populates="activities")
    
    # Indexes
    __table_args__ = (
        Index('ix_lead_activity_lead_type', 'lead_id', 'activity_type'),
        Index('ix_lead_activity_date', 'created_at'),
    )


class ResellerMetrics(Base):
    """Daily metrics for reseller performance tracking"""
    __tablename__ = "reseller_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    metric_date = Column(DateTime(timezone=True), nullable=False)
    
    # Sales metrics
    leads_created = Column(Integer, default=0)
    leads_converted = Column(Integer, default=0)
    customers_acquired = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0.0)
    commission_earned = Column(Float, default=0.0)
    
    # Pipeline metrics
    active_leads = Column(Integer, default=0)
    qualified_leads = Column(Integer, default=0)
    active_customers = Column(Integer, default=0)
    total_pipeline_value = Column(Float, default=0.0)
    
    # Performance metrics
    conversion_rate = Column(Float, default=0.0)
    average_deal_size = Column(Float, default=0.0)
    sales_cycle_days = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reseller = relationship("Reseller")
    
    # Indexes
    __table_args__ = (
        Index('ix_metrics_reseller_date', 'reseller_id', 'metric_date'),
    )


class ResellerNotification(Base):
    """Notification system for resellers"""
    __tablename__ = "reseller_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Notification details
    notification_type = Column(String(100), nullable=False)  # commission, lead, customer, system
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Status
    read = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    action_required = Column(Boolean, default=False)
    action_url = Column(String(500))
    
    # Metadata
    metadata = Column(JSON)  # Additional notification data
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))
    
    # Relationships
    reseller = relationship("Reseller")
    
    # Indexes
    __table_args__ = (
        Index('ix_notification_reseller_read', 'reseller_id', 'read'),
        Index('ix_notification_priority', 'priority'),
    )