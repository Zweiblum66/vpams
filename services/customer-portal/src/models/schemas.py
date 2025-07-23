"""
Pydantic schemas for Customer Portal
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.db.models import SubscriptionTier, TicketStatus, TicketPriority, InvoiceStatus


class UserRole(str, Enum):
    """User roles within organization"""
    ADMIN = "admin"
    MEMBER = "member"
    BILLING = "billing"
    READONLY = "readonly"


# Organization Schemas
class OrganizationBase(BaseModel):
    """Base organization schema"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    timezone: str = "UTC"
    language: str = "en"


class OrganizationUpdate(BaseModel):
    """Organization update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema"""
    id: UUID
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# User Schemas
class OrganizationUserResponse(BaseModel):
    """Organization user response"""
    id: UUID
    user_id: UUID
    email: str
    name: str
    role: str
    is_primary: bool
    joined_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        orm_mode = True


class UserInvite(BaseModel):
    """User invitation schema"""
    email: EmailStr
    role: UserRole = UserRole.MEMBER
    send_email: bool = True


# Subscription Schemas
class SubscriptionPlan(BaseModel):
    """Subscription plan details"""
    tier: SubscriptionTier
    name: str
    description: str
    monthly_price: float
    annual_price: float
    user_limit: Optional[int]
    storage_limit_gb: Optional[int]
    api_calls_limit: Optional[int]
    features: List[str]


class SubscriptionResponse(BaseModel):
    """Subscription response schema"""
    id: UUID
    tier: SubscriptionTier
    plan_name: str
    user_limit: Optional[int]
    storage_limit_gb: Optional[int]
    api_calls_limit: Optional[int]
    monthly_price: float
    annual_price: Optional[float]
    start_date: datetime
    end_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    is_active: bool
    is_trial: bool
    auto_renew: bool
    current_users: int
    current_storage_gb: float
    current_api_calls: int
    days_remaining: Optional[int]
    features: List[str]
    addons: List["AddonResponse"]
    
    class Config:
        orm_mode = True


class SubscriptionUpgrade(BaseModel):
    """Subscription upgrade request"""
    tier: SubscriptionTier
    billing_period: str = Field(..., regex="^(monthly|annual)$")


class AddonResponse(BaseModel):
    """Subscription addon response"""
    id: UUID
    name: str
    description: Optional[str]
    monthly_price: float
    extra_users: int
    extra_storage_gb: int
    extra_api_calls: int
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


class UsageResponse(BaseModel):
    """Usage statistics response"""
    period: str
    start_date: datetime
    end_date: datetime
    storage: Dict[str, Any]
    users: Dict[str, Any]
    api_calls: Dict[str, Any]
    bandwidth_gb: float
    assets: Dict[str, Any]


# Support Ticket Schemas
class TicketCreate(BaseModel):
    """Create ticket schema"""
    subject: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: Optional[str] = None


class TicketUpdate(BaseModel):
    """Update ticket schema"""
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None


class TicketResponse(BaseModel):
    """Ticket response schema"""
    id: UUID
    ticket_number: str
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    comment_count: int
    created_by: UUID
    assigned_to: Optional[UUID]
    
    class Config:
        orm_mode = True


class CommentCreate(BaseModel):
    """Create comment schema"""
    comment: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    """Comment response schema"""
    id: UUID
    comment: str
    created_by: UUID
    created_at: datetime
    is_internal: bool
    
    class Config:
        orm_mode = True


# Knowledge Base Schemas
class KnowledgeBaseArticle(BaseModel):
    """Knowledge base article"""
    id: str
    title: str
    summary: str
    category: str
    content: str
    url: str
    views: int
    helpful_count: int
    last_updated: datetime


class KnowledgeSearchResult(BaseModel):
    """Knowledge base search result"""
    id: str
    title: str
    summary: str
    category: str
    url: str
    relevance_score: float


# API Key Schemas
class APIKeyCreate(BaseModel):
    """Create API key schema"""
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = []
    rate_limit: int = Field(1000, ge=1, le=10000)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response schema"""
    id: UUID
    name: str
    key: Optional[str]  # Only returned on creation
    prefix: str
    permissions: List[str]
    rate_limit: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


# Invoice Schemas
class InvoiceResponse(BaseModel):
    """Invoice response schema"""
    id: UUID
    invoice_number: str
    status: InvoiceStatus
    subtotal: float
    tax_amount: float
    total_amount: float
    currency: str
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime]
    payment_method: Optional[str]
    line_items: List[Dict[str, Any]]
    
    class Config:
        orm_mode = True


# Analytics Schemas
class AnalyticsTimeRange(str, Enum):
    """Analytics time range options"""
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class AnalyticsRequest(BaseModel):
    """Analytics request schema"""
    time_range: AnalyticsTimeRange
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: List[str] = []
    
    @validator("end_date")
    def validate_dates(cls, v, values):
        if v and "start_date" in values and values["start_date"]:
            if v < values["start_date"]:
                raise ValueError("End date must be after start date")
        return v


class AnalyticsResponse(BaseModel):
    """Analytics response schema"""
    time_range: str
    start_date: datetime
    end_date: datetime
    metrics: Dict[str, Any]
    charts: Dict[str, List[Any]]
    summary: Dict[str, Any]


# Resource Schemas
class ResourceDownload(BaseModel):
    """Resource download schema"""
    id: str
    name: str
    description: str
    category: str
    file_size: int
    file_type: str
    version: str
    download_url: str
    release_date: datetime
    
    
class TrainingMaterial(BaseModel):
    """Training material schema"""
    id: str
    title: str
    description: str
    type: str  # video, document, webinar
    duration_minutes: Optional[int]
    url: str
    thumbnail_url: Optional[str]
    created_at: datetime


# Forward references
SubscriptionResponse.update_forward_refs()