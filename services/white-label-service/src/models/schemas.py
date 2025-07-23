"""
Pydantic schemas for White-Label Service
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum


class ThemeType(str, Enum):
    """Theme type enumeration"""
    BASIC = "basic"
    ADVANCED = "advanced"
    CUSTOM = "custom"
    PREMIUM = "premium"


class BrandingStatus(str, Enum):
    """Branding status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class DomainStatus(str, Enum):
    """Domain status enumeration"""
    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class SSLStatus(str, Enum):
    """SSL certificate status enumeration"""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"


class MobileAppType(str, Enum):
    """Mobile app type enumeration"""
    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"


# Theme Schemas
class ThemeCreate(BaseModel):
    """Schema for creating a theme"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    theme_type: ThemeType = ThemeType.BASIC
    
    # Colors
    primary_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    accent_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    background_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    text_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    link_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    
    # Typography
    primary_font: Optional[str] = Field(None, max_length=255)
    secondary_font: Optional[str] = Field(None, max_length=255)
    font_sizes: Optional[Dict[str, str]] = None
    font_weights: Optional[Dict[str, Union[str, int]]] = None
    
    # Layout
    border_radius: Optional[str] = Field(None, max_length=20)
    spacing_unit: Optional[str] = Field(None, max_length=20)
    grid_columns: Optional[int] = Field(12, ge=1, le=24)
    breakpoints: Optional[Dict[str, str]] = None
    
    # Component Styles
    button_styles: Optional[Dict[str, Any]] = None
    card_styles: Optional[Dict[str, Any]] = None
    navigation_styles: Optional[Dict[str, Any]] = None
    form_styles: Optional[Dict[str, Any]] = None
    
    # Advanced
    custom_css: Optional[str] = Field(None, max_length=100000)
    css_variables: Optional[Dict[str, str]] = None
    component_overrides: Optional[Dict[str, Any]] = None
    
    # Assets
    logo_url: Optional[HttpUrl] = None
    favicon_url: Optional[HttpUrl] = None
    background_image_url: Optional[HttpUrl] = None
    custom_images: Optional[List[str]] = None
    
    # Dark Mode
    supports_dark_mode: bool = False
    dark_mode_colors: Optional[Dict[str, str]] = None
    
    # Animation
    animation_settings: Optional[Dict[str, Any]] = None
    transition_settings: Optional[Dict[str, Any]] = None


class ThemeUpdate(BaseModel):
    """Schema for updating a theme"""
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    
    # Colors
    primary_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    accent_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    background_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    text_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    link_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    
    # Typography
    primary_font: Optional[str] = Field(None, max_length=255)
    secondary_font: Optional[str] = Field(None, max_length=255)
    font_sizes: Optional[Dict[str, str]] = None
    font_weights: Optional[Dict[str, Union[str, int]]] = None
    
    # Layout
    border_radius: Optional[str] = Field(None, max_length=20)
    spacing_unit: Optional[str] = Field(None, max_length=20)
    grid_columns: Optional[int] = Field(None, ge=1, le=24)
    breakpoints: Optional[Dict[str, str]] = None
    
    # Component Styles
    button_styles: Optional[Dict[str, Any]] = None
    card_styles: Optional[Dict[str, Any]] = None
    navigation_styles: Optional[Dict[str, Any]] = None
    form_styles: Optional[Dict[str, Any]] = None
    
    # Advanced
    custom_css: Optional[str] = Field(None, max_length=100000)
    css_variables: Optional[Dict[str, str]] = None
    component_overrides: Optional[Dict[str, Any]] = None
    
    # Assets
    logo_url: Optional[HttpUrl] = None
    favicon_url: Optional[HttpUrl] = None
    background_image_url: Optional[HttpUrl] = None
    custom_images: Optional[List[str]] = None
    
    # Dark Mode
    supports_dark_mode: Optional[bool] = None
    dark_mode_colors: Optional[Dict[str, str]] = None
    
    # Animation
    animation_settings: Optional[Dict[str, Any]] = None
    transition_settings: Optional[Dict[str, Any]] = None
    
    # Status
    is_active: Optional[bool] = None


class ThemeResponse(BaseModel):
    """Schema for theme response"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    theme_type: ThemeType
    version: str
    tenant_id: str
    is_default: bool
    is_active: bool
    
    # Colors
    primary_color: Optional[str]
    secondary_color: Optional[str]
    accent_color: Optional[str]
    background_color: Optional[str]
    text_color: Optional[str]
    link_color: Optional[str]
    
    # Typography
    primary_font: Optional[str]
    secondary_font: Optional[str]
    font_sizes: Optional[Dict[str, str]]
    font_weights: Optional[Dict[str, Union[str, int]]]
    
    # Layout
    border_radius: Optional[str]
    spacing_unit: Optional[str]
    grid_columns: Optional[int]
    breakpoints: Optional[Dict[str, str]]
    
    # Component Styles
    button_styles: Optional[Dict[str, Any]]
    card_styles: Optional[Dict[str, Any]]
    navigation_styles: Optional[Dict[str, Any]]
    form_styles: Optional[Dict[str, Any]]
    
    # Advanced
    custom_css: Optional[str]
    css_variables: Optional[Dict[str, str]]
    component_overrides: Optional[Dict[str, Any]]
    
    # Assets
    logo_url: Optional[str]
    favicon_url: Optional[str]
    background_image_url: Optional[str]
    custom_images: Optional[List[str]]
    
    # Dark Mode
    supports_dark_mode: bool
    dark_mode_colors: Optional[Dict[str, str]]
    
    # Animation
    animation_settings: Optional[Dict[str, Any]]
    transition_settings: Optional[Dict[str, Any]]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Branding Schemas
class AddressSchema(BaseModel):
    """Address schema"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None


class BrandingCreate(BaseModel):
    """Schema for creating branding configuration"""
    company_name: str = Field(..., min_length=1, max_length=255)
    company_tagline: Optional[str] = Field(None, max_length=500)
    company_description: Optional[str] = None
    company_website: Optional[HttpUrl] = None
    
    # Contact
    contact_email: Optional[str] = Field(None, max_length=255)
    support_email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    address: Optional[AddressSchema] = None
    
    # Legal
    terms_of_service_url: Optional[HttpUrl] = None
    privacy_policy_url: Optional[HttpUrl] = None
    copyright_text: Optional[str] = Field(None, max_length=500)
    legal_entity_name: Optional[str] = Field(None, max_length=255)
    
    # Social Media
    social_media_links: Optional[Dict[str, str]] = None
    
    # Platform
    platform_name: Optional[str] = Field(None, max_length=255)
    welcome_message: Optional[str] = None
    login_message: Optional[str] = None
    footer_text: Optional[str] = None
    
    # Features
    feature_visibility: Optional[Dict[str, bool]] = None
    navigation_menu: Optional[List[Dict[str, Any]]] = None
    
    # Email
    from_email: Optional[str] = Field(None, max_length=255)
    from_name: Optional[str] = Field(None, max_length=255)
    reply_to_email: Optional[str] = Field(None, max_length=255)
    email_signature: Optional[str] = None
    
    # API
    api_documentation_title: Optional[str] = Field(None, max_length=255)
    api_description: Optional[str] = None
    api_contact_info: Optional[Dict[str, str]] = None
    
    # Theme
    theme_id: Optional[str] = None


class BrandingUpdate(BaseModel):
    """Schema for updating branding configuration"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_tagline: Optional[str] = Field(None, max_length=500)
    company_description: Optional[str] = None
    company_website: Optional[HttpUrl] = None
    
    # Contact
    contact_email: Optional[str] = Field(None, max_length=255)
    support_email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    address: Optional[AddressSchema] = None
    
    # Legal
    terms_of_service_url: Optional[HttpUrl] = None
    privacy_policy_url: Optional[HttpUrl] = None
    copyright_text: Optional[str] = Field(None, max_length=500)
    legal_entity_name: Optional[str] = Field(None, max_length=255)
    
    # Social Media
    social_media_links: Optional[Dict[str, str]] = None
    
    # Platform
    platform_name: Optional[str] = Field(None, max_length=255)
    welcome_message: Optional[str] = None
    login_message: Optional[str] = None
    footer_text: Optional[str] = None
    
    # Features
    feature_visibility: Optional[Dict[str, bool]] = None
    navigation_menu: Optional[List[Dict[str, Any]]] = None
    
    # Email
    from_email: Optional[str] = Field(None, max_length=255)
    from_name: Optional[str] = Field(None, max_length=255)
    reply_to_email: Optional[str] = Field(None, max_length=255)
    email_signature: Optional[str] = None
    
    # API
    api_documentation_title: Optional[str] = Field(None, max_length=255)
    api_description: Optional[str] = None
    api_contact_info: Optional[Dict[str, str]] = None
    
    # Theme
    theme_id: Optional[str] = None
    
    # Status
    status: Optional[BrandingStatus] = None


class BrandingResponse(BaseModel):
    """Schema for branding response"""
    id: str
    tenant_id: str
    theme_id: Optional[str]
    status: BrandingStatus
    
    # Company
    company_name: str
    company_tagline: Optional[str]
    company_description: Optional[str]
    company_website: Optional[str]
    
    # Contact
    contact_email: Optional[str]
    support_email: Optional[str]
    phone_number: Optional[str]
    address: Optional[Dict[str, str]]
    
    # Legal
    terms_of_service_url: Optional[str]
    privacy_policy_url: Optional[str]
    copyright_text: Optional[str]
    legal_entity_name: Optional[str]
    
    # Social Media
    social_media_links: Optional[Dict[str, str]]
    
    # Platform
    platform_name: Optional[str]
    welcome_message: Optional[str]
    login_message: Optional[str]
    footer_text: Optional[str]
    
    # Features
    feature_visibility: Optional[Dict[str, bool]]
    navigation_menu: Optional[List[Dict[str, Any]]]
    
    # Email
    from_email: Optional[str]
    from_name: Optional[str]
    reply_to_email: Optional[str]
    email_signature: Optional[str]
    
    # API
    api_documentation_title: Optional[str]
    api_description: Optional[str]
    api_contact_info: Optional[Dict[str, str]]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    activated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Domain Schemas
class DomainCreate(BaseModel):
    """Schema for creating a custom domain"""
    domain: str = Field(..., min_length=3, max_length=255)
    subdomain: Optional[str] = Field(None, max_length=255)
    is_primary: bool = False
    ssl_enabled: bool = True
    redirect_http_to_https: bool = True
    redirect_www: str = Field("auto", regex=r'^(auto|www|non-www)$')


class DomainUpdate(BaseModel):
    """Schema for updating a custom domain"""
    is_primary: Optional[bool] = None
    ssl_enabled: Optional[bool] = None
    redirect_http_to_https: Optional[bool] = None
    redirect_www: Optional[str] = Field(None, regex=r'^(auto|www|non-www)$')


class DomainResponse(BaseModel):
    """Schema for domain response"""
    id: str
    branding_id: str
    domain: str
    subdomain: Optional[str]
    is_primary: bool
    status: DomainStatus
    ssl_enabled: bool
    ssl_status: SSLStatus
    ssl_expires_at: Optional[datetime]
    dns_verified: bool
    dns_verified_at: Optional[datetime]
    dns_records: Optional[List[Dict[str, str]]]
    verification_token: Optional[str]
    verification_method: Optional[str]
    last_error: Optional[str]
    created_at: datetime
    verified_at: Optional[datetime]
    activated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Email Template Schemas
class EmailTemplateCreate(BaseModel):
    """Schema for creating an email template"""
    template_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=500)
    html_content: str = Field(..., min_length=1)
    text_content: Optional[str] = None
    variables: Optional[List[str]] = None
    required_variables: Optional[List[str]] = None
    use_global_styles: bool = True
    custom_styles: Optional[str] = None
    locale: str = Field("en", max_length=10)
    test_data: Optional[Dict[str, Any]] = None


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    html_content: Optional[str] = Field(None, min_length=1)
    text_content: Optional[str] = None
    variables: Optional[List[str]] = None
    required_variables: Optional[List[str]] = None
    use_global_styles: Optional[bool] = None
    custom_styles: Optional[str] = None
    is_active: Optional[bool] = None
    test_data: Optional[Dict[str, Any]] = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response"""
    id: str
    branding_id: str
    template_key: str
    name: str
    description: Optional[str]
    version: str
    subject: str
    html_content: str
    text_content: Optional[str]
    variables: Optional[List[str]]
    required_variables: Optional[List[str]]
    use_global_styles: bool
    custom_styles: Optional[str]
    is_active: bool
    is_default: bool
    locale: str
    test_data: Optional[Dict[str, Any]]
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Mobile App Schemas
class MobileAppCreate(BaseModel):
    """Schema for creating a mobile app configuration"""
    app_name: str = Field(..., min_length=1, max_length=255)
    app_description: Optional[str] = None
    bundle_id: str = Field(..., min_length=1, max_length=255)
    app_type: MobileAppType
    app_store_name: Optional[str] = Field(None, max_length=255)
    app_store_description: Optional[str] = None
    app_store_keywords: Optional[List[str]] = None
    app_store_category: Optional[str] = Field(None, max_length=100)
    
    # Assets
    app_icon_url: Optional[HttpUrl] = None
    splash_screen_url: Optional[HttpUrl] = None
    app_store_icon_url: Optional[HttpUrl] = None
    screenshots: Optional[List[str]] = None
    
    # Configuration
    color_scheme: Optional[Dict[str, str]] = None
    font_configuration: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, bool]] = None
    
    # Notifications
    notification_settings: Optional[Dict[str, Any]] = None
    
    # Deep Linking
    url_scheme: Optional[str] = Field(None, max_length=255)
    universal_links: Optional[List[str]] = None
    
    # Build
    build_settings: Optional[Dict[str, Any]] = None


class MobileAppUpdate(BaseModel):
    """Schema for updating a mobile app configuration"""
    app_name: Optional[str] = Field(None, min_length=1, max_length=255)
    app_description: Optional[str] = None
    app_store_name: Optional[str] = Field(None, max_length=255)
    app_store_description: Optional[str] = None
    app_store_keywords: Optional[List[str]] = None
    app_store_category: Optional[str] = Field(None, max_length=100)
    
    # Assets
    app_icon_url: Optional[HttpUrl] = None
    splash_screen_url: Optional[HttpUrl] = None
    app_store_icon_url: Optional[HttpUrl] = None
    screenshots: Optional[List[str]] = None
    
    # Configuration
    color_scheme: Optional[Dict[str, str]] = None
    font_configuration: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, bool]] = None
    
    # Notifications
    notification_settings: Optional[Dict[str, Any]] = None
    
    # Deep Linking
    url_scheme: Optional[str] = Field(None, max_length=255)
    universal_links: Optional[List[str]] = None
    
    # Build
    build_settings: Optional[Dict[str, Any]] = None
    
    # Publishing
    is_published: Optional[bool] = None
    app_store_url: Optional[HttpUrl] = None
    google_play_url: Optional[HttpUrl] = None


class MobileAppResponse(BaseModel):
    """Schema for mobile app response"""
    id: str
    branding_id: str
    app_name: str
    app_description: Optional[str]
    bundle_id: str
    app_type: MobileAppType
    version: str
    app_store_name: Optional[str]
    app_store_description: Optional[str]
    app_store_keywords: Optional[List[str]]
    app_store_category: Optional[str]
    
    # Assets
    app_icon_url: Optional[str]
    splash_screen_url: Optional[str]
    app_store_icon_url: Optional[str]
    screenshots: Optional[List[str]]
    
    # Configuration
    color_scheme: Optional[Dict[str, str]]
    font_configuration: Optional[Dict[str, Any]]
    feature_flags: Optional[Dict[str, bool]]
    
    # Notifications
    notification_settings: Optional[Dict[str, Any]]
    
    # Deep Linking
    url_scheme: Optional[str]
    universal_links: Optional[List[str]]
    
    # Build
    build_settings: Optional[Dict[str, Any]]
    
    # Publishing
    is_published: bool
    app_store_url: Optional[str]
    google_play_url: Optional[str]
    last_build_at: Optional[datetime]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Asset Schemas
class AssetUploadResponse(BaseModel):
    """Schema for asset upload response"""
    id: str
    asset_type: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    cdn_url: Optional[str]
    created_at: datetime


# Analytics Schemas
class AnalyticsResponse(BaseModel):
    """Schema for analytics response"""
    total_themes: int
    active_themes: int
    total_domains: int
    verified_domains: int
    total_email_templates: int
    active_email_templates: int
    total_mobile_apps: int
    published_mobile_apps: int
    
    # Usage by period
    theme_usage: Dict[str, int]
    domain_usage: Dict[str, int]
    email_template_usage: Dict[str, int]
    mobile_app_usage: Dict[str, int]
    
    # Top resources
    popular_themes: List[Dict[str, Any]]
    popular_domains: List[Dict[str, Any]]
    popular_email_templates: List[Dict[str, Any]]