"""
Database models for Partner Service
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, JSON, Text,
    ForeignKey, UniqueConstraint, Index, Float, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from .base import Base


class PartnerTypeEnum(str, enum.Enum):
    """Partner type enum"""
    TECHNOLOGY = "technology"
    INTEGRATION = "integration"
    RESELLER = "reseller"
    SOLUTION = "solution"
    CONSULTING = "consulting"
    TRAINING = "training"
    SUPPORT = "support"


class PartnerStatusEnum(str, enum.Enum):
    """Partner status enum"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class PartnerTierEnum(str, enum.Enum):
    """Partner tier enum"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ApplicationStatusEnum(str, enum.Enum):
    """Application status enum"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Partner(Base):
    """Partner organization model"""
    __tablename__ = "partners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    company_name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    display_name = Column(String(255))
    partner_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Partner Classification
    partner_type = Column(SQLEnum(PartnerTypeEnum), nullable=False)
    partner_tier = Column(SQLEnum(PartnerTierEnum), default=PartnerTierEnum.BRONZE)
    status = Column(SQLEnum(PartnerStatusEnum), default=PartnerStatusEnum.PENDING)
    
    # Contact Information
    primary_contact_name = Column(String(255))
    primary_contact_email = Column(String(255), index=True)
    primary_contact_phone = Column(String(50))
    website = Column(String(500))
    
    # Address Information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    
    # Business Information
    tax_id = Column(String(50))
    business_registration = Column(String(100))
    industry = Column(String(100))
    company_size = Column(String(50))  # startup, small, medium, large, enterprise
    annual_revenue = Column(String(50))  # revenue range
    
    # Partnership Details
    partnership_start_date = Column(DateTime(timezone=True))
    partnership_end_date = Column(DateTime(timezone=True))
    commission_rate = Column(Float, default=0.0)
    discount_rate = Column(Float, default=0.0)
    
    # Settings
    auto_approve_deals = Column(Boolean, default=False)
    marketing_consent = Column(Boolean, default=False)
    data_sharing_consent = Column(Boolean, default=False)
    
    # Metadata
    onboarding_completed = Column(Boolean, default=False)
    certification_status = Column(String(50), default="pending")
    specializations = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity_at = Column(DateTime(timezone=True))
    
    # Relationships
    applications = relationship("PartnerApplication", back_populates="partner", cascade="all, delete-orphan")
    contacts = relationship("PartnerContact", back_populates="partner", cascade="all, delete-orphan")
    resources = relationship("PartnerResource", back_populates="partner", cascade="all, delete-orphan")
    deals = relationship("PartnerDeal", back_populates="partner", cascade="all, delete-orphan")
    activities = relationship("PartnerActivity", back_populates="partner", cascade="all, delete-orphan")
    certifications = relationship("PartnerCertification", back_populates="partner", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_partner_company', 'company_name'),
        Index('idx_partner_type_tier', 'partner_type', 'partner_tier'),
        Index('idx_partner_status', 'status'),
    )


class PartnerApplication(Base):
    """Partner application model"""
    __tablename__ = "partner_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Application Details
    application_type = Column(SQLEnum(PartnerTypeEnum), nullable=False)
    requested_tier = Column(SQLEnum(PartnerTierEnum), default=PartnerTierEnum.BRONZE)
    status = Column(SQLEnum(ApplicationStatusEnum), default=ApplicationStatusEnum.DRAFT)
    
    # Application Data
    business_plan = Column(Text)
    technical_capabilities = Column(JSON, default=dict)
    market_focus = Column(JSON, default=list)
    customer_references = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    
    # Attachments
    documents = Column(JSON, default=list)  # Document URLs/paths
    
    # Review Information
    reviewer_id = Column(String(255))
    review_notes = Column(Text)
    review_date = Column(DateTime(timezone=True))
    approval_date = Column(DateTime(timezone=True))
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    partner = relationship("Partner", back_populates="applications")
    
    __table_args__ = (
        Index('idx_application_status', 'status'),
        Index('idx_application_type', 'application_type'),
        Index('idx_application_submitted', 'submitted_at'),
    )


class PartnerContact(Base):
    """Partner contact persons"""
    __tablename__ = "partner_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Contact Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100))
    department = Column(String(100))
    
    # Contact Details
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    mobile = Column(String(50))
    
    # Contact Type
    contact_type = Column(String(50), default="general")  # primary, technical, sales, billing, support
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Permissions
    portal_access = Column(Boolean, default=False)
    admin_access = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    partner = relationship("Partner", back_populates="contacts")
    
    __table_args__ = (
        Index('idx_contact_email', 'email'),
        Index('idx_contact_type', 'contact_type'),
        UniqueConstraint('partner_id', 'email', name='uq_partner_contact_email'),
    )


class PartnerResource(Base):
    """Partner resources and documentation"""
    __tablename__ = "partner_resources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Resource Information
    title = Column(String(255), nullable=False)
    description = Column(Text)
    resource_type = Column(String(50), nullable=False)  # document, video, training, webinar, tool
    category = Column(String(100))  # marketing, technical, sales, support
    
    # Access Control
    access_level = Column(String(50), default="partner")  # public, partner, tier_specific, private
    required_tier = Column(SQLEnum(PartnerTierEnum))
    
    # Resource Details
    file_url = Column(String(500))
    external_url = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Metadata
    tags = Column(JSON, default=list)
    version = Column(String(20), default="1.0")
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Statistics
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    # Timestamps
    published_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    partner = relationship("Partner", back_populates="resources")
    
    __table_args__ = (
        Index('idx_resource_type', 'resource_type'),
        Index('idx_resource_category', 'category'),
        Index('idx_resource_access', 'access_level'),
    )


class PartnerDeal(Base):
    """Partner deals and opportunities"""
    __tablename__ = "partner_deals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Deal Information
    deal_name = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=False)
    deal_value = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Deal Status
    stage = Column(String(50), default="prospecting")  # prospecting, qualification, proposal, negotiation, closed_won, closed_lost
    probability = Column(Float, default=0.0)  # 0-100
    
    # Timeline
    expected_close_date = Column(DateTime(timezone=True))
    actual_close_date = Column(DateTime(timezone=True))
    
    # Commission
    partner_commission_rate = Column(Float, default=0.0)
    partner_commission_amount = Column(Float, default=0.0)
    commission_paid = Column(Boolean, default=False)
    
    # Deal Details
    description = Column(Text)
    products = Column(JSON, default=list)
    deal_source = Column(String(100))
    
    # Contact Information
    customer_contact_name = Column(String(255))
    customer_contact_email = Column(String(255))
    partner_contact_id = Column(UUID(as_uuid=True), ForeignKey("partner_contacts.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    partner = relationship("Partner", back_populates="deals")
    partner_contact = relationship("PartnerContact")
    
    __table_args__ = (
        Index('idx_deal_stage', 'stage'),
        Index('idx_deal_close_date', 'expected_close_date'),
        Index('idx_deal_value', 'deal_value'),
    )


class PartnerActivity(Base):
    """Partner activity tracking"""
    __tablename__ = "partner_activities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Activity Information
    activity_type = Column(String(50), nullable=False)  # login, download, deal_created, certification_completed
    activity_category = Column(String(50))  # portal, training, sales, support
    
    # Activity Details
    title = Column(String(255))
    description = Column(Text)
    metadata = Column(JSON, default=dict)
    
    # User Information
    user_id = Column(String(255))
    user_email = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    partner = relationship("Partner", back_populates="activities")
    
    __table_args__ = (
        Index('idx_activity_type', 'activity_type'),
        Index('idx_activity_date', 'created_at'),
        Index('idx_activity_user', 'user_id'),
    )


class PartnerCertification(Base):
    """Partner certifications and training"""
    __tablename__ = "partner_certifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    
    # Certification Information
    certification_name = Column(String(255), nullable=False)
    certification_type = Column(String(100))  # technical, sales, support, integration
    certification_level = Column(String(50))  # basic, advanced, expert
    
    # Status
    status = Column(String(50), default="in_progress")  # in_progress, completed, expired, revoked
    
    # Certification Details
    provider = Column(String(255))
    requirements = Column(JSON, default=list)
    completion_criteria = Column(JSON, default=dict)
    
    # Dates
    enrolled_date = Column(DateTime(timezone=True))
    completion_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    
    # Results
    score = Column(Float)
    certificate_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    partner = relationship("Partner", back_populates="certifications")
    
    __table_args__ = (
        Index('idx_cert_type', 'certification_type'),
        Index('idx_cert_status', 'status'),
        Index('idx_cert_expiry', 'expiry_date'),
    )