"""
Pydantic schemas for Partner Service
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from ..db.models import PartnerTypeEnum, PartnerStatusEnum, PartnerTierEnum, ApplicationStatusEnum


# Base schemas
class PartnerBase(BaseModel):
    """Base partner schema"""
    company_name: str = Field(..., min_length=2, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    partner_type: PartnerTypeEnum
    website: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)


class PartnerCreate(PartnerBase):
    """Schema for creating a partner"""
    primary_contact_name: str = Field(..., min_length=2, max_length=255)
    primary_contact_email: EmailStr
    primary_contact_phone: Optional[str] = Field(None, max_length=50)
    
    # Address information
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Business information
    tax_id: Optional[str] = Field(None, max_length=50)
    business_registration: Optional[str] = Field(None, max_length=100)
    annual_revenue: Optional[str] = Field(None, max_length=50)


class PartnerUpdate(BaseModel):
    """Schema for updating a partner"""
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[str] = Field(None, max_length=50)
    specializations: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    marketing_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None


class PartnerResponse(PartnerBase):
    """Schema for partner response"""
    id: str
    partner_code: str
    partner_tier: PartnerTierEnum
    status: PartnerStatusEnum
    primary_contact_name: Optional[str]
    primary_contact_email: Optional[str]
    primary_contact_phone: Optional[str]
    
    # Address
    address_line1: Optional[str]
    city: Optional[str]
    state_province: Optional[str]
    country: Optional[str]
    
    # Partnership details
    partnership_start_date: Optional[datetime]
    commission_rate: Optional[float]
    discount_rate: Optional[float]
    
    # Status
    onboarding_completed: bool
    certification_status: str
    specializations: List[str]
    tags: List[str]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Partner Application Schemas
class PartnerApplicationCreate(BaseModel):
    """Schema for creating a partner application"""
    application_type: PartnerTypeEnum
    requested_tier: PartnerTierEnum = PartnerTierEnum.BRONZE
    business_plan: str = Field(..., min_length=100)
    technical_capabilities: Dict[str, Any] = Field(default_factory=dict)
    market_focus: List[str] = Field(default_factory=list)
    customer_references: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)


class PartnerApplicationUpdate(BaseModel):
    """Schema for updating a partner application"""
    business_plan: Optional[str] = Field(None, min_length=100)
    technical_capabilities: Optional[Dict[str, Any]] = None
    market_focus: Optional[List[str]] = None
    customer_references: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    status: Optional[ApplicationStatusEnum] = None


class PartnerApplicationResponse(BaseModel):
    """Schema for partner application response"""
    id: str
    partner_id: str
    application_type: PartnerTypeEnum
    requested_tier: PartnerTierEnum
    status: ApplicationStatusEnum
    business_plan: str
    technical_capabilities: Dict[str, Any]
    market_focus: List[str]
    customer_references: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    documents: List[str]
    
    # Review information
    reviewer_id: Optional[str]
    review_notes: Optional[str]
    review_date: Optional[datetime]
    approval_date: Optional[datetime]
    
    # Timestamps
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Partner Contact Schemas
class PartnerContactCreate(BaseModel):
    """Schema for creating a partner contact"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    mobile: Optional[str] = Field(None, max_length=50)
    contact_type: str = Field("general", max_length=50)
    is_primary: bool = False
    portal_access: bool = False
    admin_access: bool = False


class PartnerContactUpdate(BaseModel):
    """Schema for updating a partner contact"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    mobile: Optional[str] = Field(None, max_length=50)
    contact_type: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    portal_access: Optional[bool] = None
    admin_access: Optional[bool] = None
    is_active: Optional[bool] = None


class PartnerContactResponse(BaseModel):
    """Schema for partner contact response"""
    id: str
    partner_id: str
    first_name: str
    last_name: str
    title: Optional[str]
    department: Optional[str]
    email: str
    phone: Optional[str]
    mobile: Optional[str]
    contact_type: str
    is_primary: bool
    is_active: bool
    portal_access: bool
    admin_access: bool
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Partner Resource Schemas
class PartnerResourceCreate(BaseModel):
    """Schema for creating a partner resource"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    resource_type: str = Field(..., max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    access_level: str = Field("partner", max_length=50)
    required_tier: Optional[PartnerTierEnum] = None
    file_url: Optional[str] = Field(None, max_length=500)
    external_url: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    version: str = Field("1.0", max_length=20)
    is_featured: bool = False
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class PartnerResourceUpdate(BaseModel):
    """Schema for updating a partner resource"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    access_level: Optional[str] = Field(None, max_length=50)
    required_tier: Optional[PartnerTierEnum] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = Field(None, max_length=20)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class PartnerResourceResponse(BaseModel):
    """Schema for partner resource response"""
    id: str
    partner_id: str
    title: str
    description: Optional[str]
    resource_type: str
    category: Optional[str]
    access_level: str
    required_tier: Optional[PartnerTierEnum]
    file_url: Optional[str]
    external_url: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    tags: List[str]
    version: str
    is_featured: bool
    is_active: bool
    download_count: int
    view_count: int
    
    # Timestamps
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Partner Deal Schemas
class PartnerDealCreate(BaseModel):
    """Schema for creating a partner deal"""
    deal_name: str = Field(..., min_length=1, max_length=255)
    customer_name: str = Field(..., min_length=1, max_length=255)
    deal_value: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=3)
    stage: str = Field("prospecting", max_length=50)
    probability: float = Field(0.0, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    description: Optional[str] = None
    products: List[Dict[str, Any]] = Field(default_factory=list)
    deal_source: Optional[str] = Field(None, max_length=100)
    customer_contact_name: Optional[str] = Field(None, max_length=255)
    customer_contact_email: Optional[EmailStr] = None
    partner_contact_id: Optional[str] = None


class PartnerDealUpdate(BaseModel):
    """Schema for updating a partner deal"""
    deal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    deal_value: Optional[float] = Field(None, gt=0)
    stage: Optional[str] = Field(None, max_length=50)
    probability: Optional[float] = Field(None, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    actual_close_date: Optional[datetime] = None
    description: Optional[str] = None
    products: Optional[List[Dict[str, Any]]] = None
    deal_source: Optional[str] = Field(None, max_length=100)
    customer_contact_name: Optional[str] = Field(None, max_length=255)
    customer_contact_email: Optional[EmailStr] = None


class PartnerDealResponse(BaseModel):
    """Schema for partner deal response"""
    id: str
    partner_id: str
    deal_name: str
    customer_name: str
    deal_value: float
    currency: str
    stage: str
    probability: float
    expected_close_date: Optional[datetime]
    actual_close_date: Optional[datetime]
    partner_commission_rate: float
    partner_commission_amount: float
    commission_paid: bool
    description: Optional[str]
    products: List[Dict[str, Any]]
    deal_source: Optional[str]
    customer_contact_name: Optional[str]
    customer_contact_email: Optional[str]
    partner_contact_id: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Partner Activity Schemas
class PartnerActivityResponse(BaseModel):
    """Schema for partner activity response"""
    id: str
    partner_id: str
    activity_type: str
    activity_category: Optional[str]
    title: Optional[str]
    description: Optional[str]
    metadata: Dict[str, Any]
    user_id: Optional[str]
    user_email: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True


# Dashboard and Statistics Schemas
class PartnerDashboardResponse(BaseModel):
    """Schema for partner dashboard response"""
    partner_info: PartnerResponse
    statistics: Dict[str, Any]
    recent_activities: List[PartnerActivityResponse]
    active_deals: List[PartnerDealResponse]
    certifications: List[Dict[str, Any]]
    resources_count: int
    contacts_count: int


class PartnerListResponse(BaseModel):
    """Schema for partner list response"""
    partners: List[PartnerResponse]
    total: int
    page: int
    limit: int


# File upload schemas
class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    file_id: str
    filename: str
    file_url: str
    file_size: int
    mime_type: str
    uploaded_at: datetime