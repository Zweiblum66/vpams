"""
Database models for White-Label Service
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


class ThemeTypeEnum(str, enum.Enum):
    """Theme type enum"""
    BASIC = "basic"
    ADVANCED = "advanced" 
    CUSTOM = "custom"
    PREMIUM = "premium"


class BrandingStatusEnum(str, enum.Enum):
    """Branding status enum"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class DomainStatusEnum(str, enum.Enum):
    """Domain status enum"""
    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class SSLStatusEnum(str, enum.Enum):
    """SSL certificate status enum"""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"


class MobileAppTypeEnum(str, enum.Enum):
    """Mobile app type enum"""
    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"


class WhiteLabelTheme(Base):
    """White-label theme model"""
    __tablename__ = "whitelabel_themes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255))
    description = Column(Text)
    theme_type = Column(SQLEnum(ThemeTypeEnum), default=ThemeTypeEnum.BASIC)
    version = Column(String(50), default="1.0.0")
    
    # Tenant Association
    tenant_id = Column(String(255), nullable=False, index=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Visual Styling
    primary_color = Column(String(7))  # Hex color
    secondary_color = Column(String(7))
    accent_color = Column(String(7))
    background_color = Column(String(7))
    text_color = Column(String(7))
    link_color = Column(String(7))
    
    # Typography
    primary_font = Column(String(255))
    secondary_font = Column(String(255))
    font_sizes = Column(JSON, default=dict)  # h1, h2, body, etc.
    font_weights = Column(JSON, default=dict)
    
    # Layout & Spacing
    border_radius = Column(String(20))  # e.g., "4px", "0.5rem"
    spacing_unit = Column(String(20))  # e.g., "8px", "0.5rem"
    grid_columns = Column(Integer, default=12)
    breakpoints = Column(JSON, default=dict)  # responsive breakpoints
    
    # Component Styling
    button_styles = Column(JSON, default=dict)
    card_styles = Column(JSON, default=dict)
    navigation_styles = Column(JSON, default=dict)
    form_styles = Column(JSON, default=dict)
    
    # Advanced Customization
    custom_css = Column(Text)  # Custom CSS rules
    css_variables = Column(JSON, default=dict)  # CSS custom properties
    component_overrides = Column(JSON, default=dict)  # Component-specific overrides
    
    # Assets
    logo_url = Column(String(500))
    favicon_url = Column(String(500))
    background_image_url = Column(String(500))
    custom_images = Column(JSON, default=list)  # Additional custom images
    
    # Dark Mode Support
    supports_dark_mode = Column(Boolean, default=False)
    dark_mode_colors = Column(JSON, default=dict)
    
    # Animation & Effects
    animation_settings = Column(JSON, default=dict)
    transition_settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    branding_configs = relationship("WhiteLabelBranding", back_populates="theme", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_theme_tenant', 'tenant_id'),
        Index('idx_theme_active', 'is_active'),
        Index('idx_theme_default', 'tenant_id', 'is_default'),
        UniqueConstraint('tenant_id', 'name', name='uq_theme_tenant_name'),
    )


class WhiteLabelBranding(Base):
    """White-label branding configuration"""
    __tablename__ = "whitelabel_branding"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant Association
    tenant_id = Column(String(255), nullable=False, unique=True, index=True)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("whitelabel_themes.id"))
    status = Column(SQLEnum(BrandingStatusEnum), default=BrandingStatusEnum.DRAFT)
    
    # Company Information
    company_name = Column(String(255), nullable=False)
    company_tagline = Column(String(500))
    company_description = Column(Text)
    company_website = Column(String(500))
    
    # Contact Information
    contact_email = Column(String(255))
    support_email = Column(String(255))
    phone_number = Column(String(50))
    address = Column(JSON, default=dict)  # Street, city, state, country, zip
    
    # Legal Information
    terms_of_service_url = Column(String(500))
    privacy_policy_url = Column(String(500))
    copyright_text = Column(String(500))
    legal_entity_name = Column(String(255))
    
    # Social Media Links
    social_media_links = Column(JSON, default=dict)  # Facebook, Twitter, LinkedIn, etc.
    
    # Platform Configuration
    platform_name = Column(String(255))  # Custom name for the platform
    welcome_message = Column(Text)
    login_message = Column(Text)
    footer_text = Column(Text)
    
    # Feature Visibility
    feature_visibility = Column(JSON, default=dict)  # Which features to show/hide
    navigation_menu = Column(JSON, default=list)  # Custom navigation structure
    
    # Email Configuration
    from_email = Column(String(255))
    from_name = Column(String(255))
    reply_to_email = Column(String(255))
    email_signature = Column(Text)
    
    # API Branding
    api_documentation_title = Column(String(255))
    api_description = Column(Text)
    api_contact_info = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    activated_at = Column(DateTime(timezone=True))
    
    # Relationships
    theme = relationship("WhiteLabelTheme", back_populates="branding_configs")
    custom_domains = relationship("WhiteLabelDomain", back_populates="branding", cascade="all, delete-orphan")
    email_templates = relationship("WhiteLabelEmailTemplate", back_populates="branding", cascade="all, delete-orphan")
    mobile_apps = relationship("WhiteLabelMobileApp", back_populates="branding", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_branding_tenant', 'tenant_id'),
        Index('idx_branding_status', 'status'),
    )


class WhiteLabelDomain(Base):
    """Custom domain configuration"""
    __tablename__ = "whitelabel_domains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branding_id = Column(UUID(as_uuid=True), ForeignKey("whitelabel_branding.id"), nullable=False)
    
    # Domain Information
    domain = Column(String(255), nullable=False, unique=True, index=True)
    subdomain = Column(String(255))  # Optional subdomain
    is_primary = Column(Boolean, default=False)
    status = Column(SQLEnum(DomainStatusEnum), default=DomainStatusEnum.PENDING)
    
    # SSL Configuration
    ssl_enabled = Column(Boolean, default=True)
    ssl_status = Column(SQLEnum(SSLStatusEnum), default=SSLStatusEnum.PENDING)
    ssl_certificate_id = Column(String(255))
    ssl_expires_at = Column(DateTime(timezone=True))
    
    # DNS Configuration
    dns_records = Column(JSON, default=list)  # Required DNS records
    dns_verified = Column(Boolean, default=False)
    dns_verified_at = Column(DateTime(timezone=True))
    
    # Redirect Configuration
    redirect_http_to_https = Column(Boolean, default=True)
    redirect_www = Column(String(20), default="auto")  # auto, www, non-www
    
    # Verification
    verification_token = Column(String(255))
    verification_method = Column(String(50))  # dns, file, email
    verification_attempts = Column(Integer, default=0)
    last_verification_attempt = Column(DateTime(timezone=True))
    
    # Error Information
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True))
    activated_at = Column(DateTime(timezone=True))
    
    # Relationships
    branding = relationship("WhiteLabelBranding", back_populates="custom_domains")
    
    __table_args__ = (
        Index('idx_domain_branding', 'branding_id'),
        Index('idx_domain_status', 'status'),
        Index('idx_domain_primary', 'branding_id', 'is_primary'),
    )


class WhiteLabelEmailTemplate(Base):
    """Custom email template configuration"""
    __tablename__ = "whitelabel_email_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branding_id = Column(UUID(as_uuid=True), ForeignKey("whitelabel_branding.id"), nullable=False)
    
    # Template Information
    template_key = Column(String(100), nullable=False)  # welcome, reset_password, etc.
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(20), default="1.0")
    
    # Email Content
    subject = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text)
    
    # Template Variables
    variables = Column(JSON, default=list)  # Available template variables
    required_variables = Column(JSON, default=list)  # Required variables
    
    # Styling
    use_global_styles = Column(Boolean, default=True)
    custom_styles = Column(Text)  # Additional CSS
    
    # Configuration
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    locale = Column(String(10), default="en")
    
    # Testing
    test_data = Column(JSON, default=dict)  # Sample data for preview
    last_tested_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    branding = relationship("WhiteLabelBranding", back_populates="email_templates")
    
    __table_args__ = (
        Index('idx_email_template_branding', 'branding_id'),
        Index('idx_email_template_key', 'template_key'),
        Index('idx_email_template_active', 'is_active'),
        UniqueConstraint('branding_id', 'template_key', 'locale', name='uq_email_template'),
    )


class WhiteLabelMobileApp(Base):
    """Mobile app white-label configuration"""
    __tablename__ = "whitelabel_mobile_apps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branding_id = Column(UUID(as_uuid=True), ForeignKey("whitelabel_branding.id"), nullable=False)
    
    # App Information
    app_name = Column(String(255), nullable=False)
    app_description = Column(Text)
    bundle_id = Column(String(255), nullable=False)  # com.company.app
    app_type = Column(SQLEnum(MobileAppTypeEnum), nullable=False)
    version = Column(String(50), default="1.0.0")
    
    # App Store Information
    app_store_name = Column(String(255))
    app_store_description = Column(Text)
    app_store_keywords = Column(JSON, default=list)
    app_store_category = Column(String(100))
    
    # Visual Assets
    app_icon_url = Column(String(500))
    splash_screen_url = Column(String(500))
    app_store_icon_url = Column(String(500))
    screenshots = Column(JSON, default=list)
    
    # App Configuration
    color_scheme = Column(JSON, default=dict)  # Primary, secondary, accent colors
    font_configuration = Column(JSON, default=dict)
    feature_flags = Column(JSON, default=dict)  # Which features to enable
    
    # Push Notifications
    notification_settings = Column(JSON, default=dict)
    push_certificate_id = Column(String(255))
    
    # Deep Linking
    url_scheme = Column(String(255))  # myapp://
    universal_links = Column(JSON, default=list)
    
    # Build Configuration
    build_settings = Column(JSON, default=dict)
    provisioning_profile_id = Column(String(255))
    signing_certificate_id = Column(String(255))
    
    # Release Information
    is_published = Column(Boolean, default=False)
    app_store_url = Column(String(500))
    google_play_url = Column(String(500))
    last_build_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    branding = relationship("WhiteLabelBranding", back_populates="mobile_apps")
    
    __table_args__ = (
        Index('idx_mobile_app_branding', 'branding_id'),
        Index('idx_mobile_app_type', 'app_type'),
        Index('idx_mobile_app_published', 'is_published'),
        UniqueConstraint('branding_id', 'bundle_id', name='uq_mobile_app_bundle'),
    )


class WhiteLabelAnalytics(Base):
    """Analytics for white-label usage"""
    __tablename__ = "whitelabel_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference Information
    tenant_id = Column(String(255), nullable=False, index=True)
    branding_id = Column(UUID(as_uuid=True), ForeignKey("whitelabel_branding.id"))
    resource_type = Column(String(50), nullable=False)  # theme, domain, email, mobile_app
    resource_id = Column(String(255), nullable=False)
    
    # Event Information
    event_type = Column(String(50), nullable=False)  # view, download, apply, activate
    event_data = Column(JSON, default=dict)
    
    # User Information
    user_id = Column(String(255))
    session_id = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Geographic Information
    country = Column(String(100))
    city = Column(String(100))
    timezone = Column(String(50))
    
    # Performance Metrics
    response_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_analytics_tenant', 'tenant_id'),
        Index('idx_analytics_resource', 'resource_type', 'resource_id'),
        Index('idx_analytics_event', 'event_type'),
        Index('idx_analytics_date', 'created_at'),
    )


class WhiteLabelAsset(Base):
    """White-label asset storage"""
    __tablename__ = "whitelabel_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Asset Information
    tenant_id = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)  # logo, favicon, image, css, font
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    
    # File Information
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    file_hash = Column(String(64))  # SHA-256 hash
    
    # Image Metadata (for images)
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String(20))
    color_space = Column(String(50))
    
    # Usage Information
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # CDN Information
    cdn_url = Column(String(500))
    cdn_uploaded = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_asset_tenant', 'tenant_id'),
        Index('idx_asset_type', 'asset_type'),
        Index('idx_asset_active', 'is_active'),
        Index('idx_asset_hash', 'file_hash'),
    )