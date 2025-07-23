"""
Database models for Plugin Service
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


class PluginStatusEnum(str, enum.Enum):
    """Plugin status enum"""
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"
    UNINSTALLED = "uninstalled"


class Plugin(Base):
    """Plugin model"""
    __tablename__ = "plugins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    author = Column(String(255), nullable=False)
    author_email = Column(String(255))
    developer_id = Column(UUID(as_uuid=True), ForeignKey("developer_accounts.id"))
    homepage = Column(String(500))
    documentation_url = Column(String(500))
    icon_url = Column(String(500))
    license = Column(String(100), default="Proprietary")
    
    # Status
    status = Column(SQLEnum(PluginStatusEnum), default=PluginStatusEnum.INSTALLED)
    is_active = Column(Boolean, default=True)
    
    # Requirements
    min_mams_version = Column(String(50), default="1.0.0")
    max_mams_version = Column(String(50))
    
    # Metadata
    metadata = Column(JSON, default={})
    config = Column(JSON, default={})
    capabilities = Column(JSON, default=[])
    
    # Marketplace
    download_url = Column(String(500))
    price = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    installed_at = Column(DateTime(timezone=True))
    last_enabled_at = Column(DateTime(timezone=True))
    
    # Relationships
    installations = relationship("PluginInstallation", back_populates="plugin", cascade="all, delete-orphan")
    executions = relationship("PluginExecution", back_populates="plugin", cascade="all, delete-orphan")
    reviews = relationship("PluginReview", back_populates="plugin", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_plugin_status', 'status'),
        Index('idx_plugin_author', 'author'),
    )


class PluginInstallation(Base):
    """Plugin installation tracking"""
    __tablename__ = "plugin_installations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False)
    
    # Installation details
    version = Column(String(50), nullable=False)
    config = Column(JSON, default={})
    enabled = Column(Boolean, default=True)
    
    # Timestamps
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationships
    plugin = relationship("Plugin", back_populates="installations")
    
    __table_args__ = (
        UniqueConstraint('plugin_id', 'tenant_id', name='uq_plugin_tenant'),
        Index('idx_installation_tenant', 'tenant_id'),
    )


class PluginExecution(Base):
    """Plugin execution history"""
    __tablename__ = "plugin_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False)
    
    # Execution details
    hook_name = Column(String(255))
    event_type = Column(String(255))
    context = Column(JSON, default={})
    parameters = Column(JSON, default={})
    
    # Results
    success = Column(Boolean, nullable=False)
    result = Column(JSON)
    error = Column(Text)
    
    # Performance
    execution_time_ms = Column(Integer)
    memory_used_mb = Column(Float)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    plugin = relationship("Plugin", back_populates="executions")
    
    __table_args__ = (
        Index('idx_execution_plugin_tenant', 'plugin_id', 'tenant_id'),
        Index('idx_execution_started', 'started_at'),
    )


class PluginReview(Base):
    """Plugin reviews and ratings"""
    __tablename__ = "plugin_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False)
    user_id = Column(String(255), nullable=False)
    
    # Review
    rating = Column(Float, nullable=False)
    title = Column(String(255))
    comment = Column(Text)
    
    # Metadata
    version_reviewed = Column(String(50))
    verified_purchase = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin", back_populates="reviews")
    
    __table_args__ = (
        UniqueConstraint('plugin_id', 'user_id', name='uq_plugin_user_review'),
        Index('idx_review_rating', 'rating'),
    )


class PluginWebhook(Base):
    """Plugin webhook registrations"""
    __tablename__ = "plugin_webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Webhook details
    event_types = Column(JSON, default=[])
    url = Column(String(500), nullable=False)
    secret = Column(String(255))
    
    # Configuration
    active = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=30)
    
    # Statistics
    total_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    last_call_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_webhook_plugin_tenant', 'plugin_id', 'tenant_id'),
    )


class DeveloperAccount(Base):
    """Developer accounts for plugin creators"""
    __tablename__ = "developer_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False)
    
    # Developer info
    company_name = Column(String(255))
    website = Column(String(500))
    support_email = Column(String(255))
    
    # Verification
    verified = Column(Boolean, default=False)
    verification_date = Column(DateTime(timezone=True))
    
    # Revenue
    revenue_share_percent = Column(Float, default=70.0)
    total_revenue = Column(Float, default=0.0)
    pending_payout = Column(Float, default=0.0)
    
    # API Access
    api_key = Column(String(255), unique=True)
    api_key_created_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    payouts = relationship("Payout", back_populates="developer", cascade="all, delete-orphan")
    payment_methods = relationship("PaymentMethod", back_populates="developer", cascade="all, delete-orphan")
    tax_documents = relationship("TaxDocument", back_populates="developer", cascade="all, delete-orphan")


class PluginCategory(Base):
    """Plugin categories for marketplace"""
    __tablename__ = "plugin_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    parent_id = Column(UUID(as_uuid=True), ForeignKey("plugin_categories.id"))
    
    # Display
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    children = relationship("PluginCategory", backref="parent", remote_side=[id])



class PluginRating(Base):
    """Plugin ratings and reviews"""
    __tablename__ = "plugin_ratings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    
    # Rating
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(255))
    comment = Column(Text)
    
    # Moderation
    is_approved = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    moderator_notes = Column(Text)
    
    # Helpfulness
    helpful_count = Column(Integer, default=0)
    unhelpful_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    
    __table_args__ = (
        UniqueConstraint('plugin_id', 'user_id', name='uq_plugin_user_rating'),
        Index('idx_rating_plugin', 'plugin_id'),
        Index('idx_rating_user', 'user_id'),
    )


class PluginDownload(Base):
    """Plugin download tracking"""
    __tablename__ = "plugin_downloads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255))
    tenant_id = Column(String(255))
    
    # Download details
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    referrer = Column(String(500))
    
    # Download metadata
    download_method = Column(String(50), default="marketplace")  # marketplace, api, direct
    file_size = Column(Integer)
    download_duration = Column(Float)  # seconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    
    __table_args__ = (
        Index('idx_download_plugin', 'plugin_id'),
        Index('idx_download_user', 'user_id'),
        Index('idx_download_created', 'created_at'),
    )


class PluginTag(Base):
    """Plugin tags for categorization and search"""
    __tablename__ = "plugin_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    
    # Display
    color = Column(String(7))  # Hex color code
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PluginTagAssociation(Base):
    """Many-to-many relationship between plugins and tags"""
    __tablename__ = "plugin_tag_associations"
    
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("plugin_tags.id", ondelete="CASCADE"), primary_key=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketplaceFeatured(Base):
    """Featured plugins in marketplace"""
    __tablename__ = "marketplace_featured"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    
    # Featured details
    title = Column(String(255))
    description = Column(Text)
    banner_image_url = Column(String(500))
    
    # Display
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Schedule
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    
    __table_args__ = (
        Index('idx_featured_active', 'is_active'),
        Index('idx_featured_order', 'display_order'),
    )


class PluginSale(Base):
    """Plugin sales transactions"""
    __tablename__ = "plugin_sales"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    
    # Sale details
    sale_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(String(50))
    transaction_id = Column(String(255), unique=True)
    
    # Revenue sharing
    revenue_share_percent = Column(Float, default=70.0)  # Developer gets 70%
    revenue_share_amount = Column(Float, nullable=False)
    platform_fee_percent = Column(Float, default=30.0)  # Platform gets 30%
    platform_fee_amount = Column(Float, nullable=False)
    
    # Transaction status
    status = Column(String(50), default="completed")  # pending, completed, refunded, failed
    refund_amount = Column(Float, default=0.0)
    refund_reason = Column(Text)
    
    # Payment processing
    payment_processor = Column(String(50))  # stripe, paypal, etc.
    payment_processor_fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    
    # Metadata
    customer_country = Column(String(2))  # ISO country code
    customer_ip = Column(String(45))
    user_agent = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    
    __table_args__ = (
        Index('idx_sale_plugin', 'plugin_id'),
        Index('idx_sale_customer', 'customer_id'),
        Index('idx_sale_status', 'status'),
        Index('idx_sale_created', 'created_at'),
        Index('idx_sale_transaction', 'transaction_id'),
    )


class Payout(Base):
    """Developer payouts"""
    __tablename__ = "payouts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    developer_id = Column(UUID(as_uuid=True), ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Payout details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payout_method = Column(String(50), default="paypal")  # paypal, bank_transfer, stripe
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, processing, completed, failed, cancelled
    status_message = Column(Text)
    
    # Payment processor details
    payment_processor = Column(String(50))
    processor_transaction_id = Column(String(255))
    processor_fee = Column(Float, default=0.0)
    
    # Payout period
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    # Processing details
    processed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    
    # Admin notes
    notes = Column(Text)
    admin_user_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    developer = relationship("DeveloperAccount", back_populates="payouts")
    
    __table_args__ = (
        Index('idx_payout_developer', 'developer_id'),
        Index('idx_payout_status', 'status'),
        Index('idx_payout_created', 'created_at'),
        Index('idx_payout_period', 'period_start', 'period_end'),
    )


class RevenueReport(Base):
    """Revenue reports for analytics and compliance"""
    __tablename__ = "revenue_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report details
    report_type = Column(String(50), nullable=False)  # monthly, quarterly, yearly, custom
    report_period_start = Column(DateTime(timezone=True), nullable=False)
    report_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Financial data
    total_sales = Column(Float, default=0.0)
    total_revenue = Column(Float, default=0.0)
    platform_fees = Column(Float, default=0.0)
    developer_revenue = Column(Float, default=0.0)
    processing_fees = Column(Float, default=0.0)
    refunds = Column(Float, default=0.0)
    
    # Transaction counts
    transaction_count = Column(Integer, default=0)
    refund_count = Column(Integer, default=0)
    payout_count = Column(Integer, default=0)
    
    # Report metadata
    report_data = Column(JSON)  # Detailed breakdown
    generated_by = Column(String(255))
    
    # Status
    status = Column(String(50), default="draft")  # draft, published, archived
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_report_type', 'report_type'),
        Index('idx_report_period', 'report_period_start', 'report_period_end'),
        Index('idx_report_status', 'status'),
    )


class PaymentMethod(Base):
    """Developer payment methods"""
    __tablename__ = "payment_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    developer_id = Column(UUID(as_uuid=True), ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Payment method details
    method_type = Column(String(50), nullable=False)  # paypal, bank_transfer, stripe
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Method-specific data (encrypted)
    payment_details = Column(JSON)  # Encrypted payment details
    
    # Verification
    verification_status = Column(String(50), default="unverified")  # unverified, pending, verified, failed
    verification_date = Column(DateTime(timezone=True))
    verification_notes = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    developer = relationship("DeveloperAccount", back_populates="payment_methods")
    
    __table_args__ = (
        Index('idx_payment_developer', 'developer_id'),
        Index('idx_payment_type', 'method_type'),
        Index('idx_payment_primary', 'is_primary'),
    )


class TaxDocument(Base):
    """Tax documents for developers"""
    __tablename__ = "tax_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    developer_id = Column(UUID(as_uuid=True), ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Document details
    document_type = Column(String(50), nullable=False)  # 1099, w9, tax_report
    tax_year = Column(Integer, nullable=False)
    
    # File information
    file_path = Column(String(500))
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Tax information
    total_earnings = Column(Float, default=0.0)
    tax_withheld = Column(Float, default=0.0)
    
    # Status
    status = Column(String(50), default="generated")  # generated, sent, received, processed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    developer = relationship("DeveloperAccount", back_populates="tax_documents")
    
    __table_args__ = (
        Index('idx_tax_developer', 'developer_id'),
        Index('idx_tax_year', 'tax_year'),
        Index('idx_tax_type', 'document_type'),
        UniqueConstraint('developer_id', 'document_type', 'tax_year', name='uq_developer_tax_document'),
    )


class CertificationRequest(Base):
    """Plugin certification requests"""
    __tablename__ = "certification_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    developer_id = Column(UUID(as_uuid=True), ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Request details
    version = Column(String(50), nullable=False)
    certification_level = Column(String(50), default="standard")  # basic, standard, premium
    status = Column(String(50), default="pending")  # pending, in_review, certified, rejected, failed
    
    # Scoring
    overall_score = Column(Float, default=0.0)
    
    # Review information
    reviewer_id = Column(String(255))
    reviewer_notes = Column(Text)
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    developer = relationship("DeveloperAccount")
    tests = relationship("CertificationTest", back_populates="certification", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_cert_plugin', 'plugin_id'),
        Index('idx_cert_developer', 'developer_id'),
        Index('idx_cert_status', 'status'),
        Index('idx_cert_level', 'certification_level'),
        Index('idx_cert_submitted', 'submitted_at'),
    )


class CertificationTest(Base):
    """Individual certification test results"""
    __tablename__ = "certification_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_id = Column(UUID(as_uuid=True), ForeignKey("certification_requests.id", ondelete="CASCADE"), nullable=False)
    
    # Test details
    test_name = Column(String(100), nullable=False)
    test_type = Column(String(50), nullable=False)  # security, quality, performance, functionality, compatibility
    status = Column(String(50), nullable=False)  # pass, warning, error, suggestion
    score = Column(Float, default=0.0)
    
    # Test results
    details = Column(JSON, default={})
    error_message = Column(Text)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    certification = relationship("CertificationRequest", back_populates="tests")
    
    __table_args__ = (
        Index('idx_test_certification', 'certification_id'),
        Index('idx_test_type', 'test_type'),
        Index('idx_test_status', 'status'),
        Index('idx_test_score', 'score'),
    )


class CertificationBadge(Base):
    """Certification badges for plugins"""
    __tablename__ = "certification_badges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    certification_id = Column(UUID(as_uuid=True), ForeignKey("certification_requests.id", ondelete="CASCADE"), nullable=False)
    
    # Badge details
    badge_type = Column(String(50), nullable=False)  # certification, excellence, quality, security
    badge_level = Column(String(50), nullable=False)  # basic, standard, premium
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Badge metadata
    badge_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Validity
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin")
    certification = relationship("CertificationRequest")
    
    __table_args__ = (
        Index('idx_badge_plugin', 'plugin_id'),
        Index('idx_badge_type', 'badge_type'),
        Index('idx_badge_level', 'badge_level'),
        Index('idx_badge_active', 'is_active'),
        UniqueConstraint('plugin_id', 'badge_type', 'badge_level', name='uq_plugin_badge'),
    )