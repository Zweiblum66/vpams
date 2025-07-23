"""Pydantic schemas for the Reseller Tools Service"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import enum

from ..db.models import (
    ResellerStatusEnum, ResellerTierEnum, CustomerStatusEnum,
    LeadStatusEnum, CommissionTypeEnum, PaymentStatusEnum
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        use_enum_values = True


# Reseller schemas
class ResellerBase(BaseSchema):
    """Base reseller schema"""
    company_name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Business information
    business_license: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    
    # Reseller details
    tier: ResellerTierEnum = ResellerTierEnum.BRONZE
    territory: Optional[Dict[str, Any]] = None
    payment_terms: int = Field(default=30, ge=1, le=365)
    credit_limit: float = Field(default=10000.0, ge=0)
    notes: Optional[str] = None


class ResellerCreate(ResellerBase):
    """Schema for creating a reseller"""
    user_id: UUID
    commission_rate: Optional[float] = Field(default=0.15, ge=0, le=1)


class ResellerUpdate(BaseSchema):
    """Schema for updating a reseller"""
    company_name: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Business information
    business_license: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    
    # Reseller details
    status: Optional[ResellerStatusEnum] = None
    tier: Optional[ResellerTierEnum] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=1)
    territory: Optional[Dict[str, Any]] = None
    payment_terms: Optional[int] = Field(None, ge=1, le=365)
    credit_limit: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class ResellerResponse(ResellerBase):
    """Schema for reseller responses"""
    id: UUID
    user_id: UUID
    status: ResellerStatusEnum
    commission_rate: float
    current_balance: float
    onboarding_completed: bool
    contract_signed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Customer schemas
class CustomerBase(BaseSchema):
    """Base customer schema"""
    company_name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Customer details
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[str] = Field(None, max_length=50)
    
    # Subscription information
    subscription_tier: Optional[str] = Field(None, max_length=100)
    monthly_value: Optional[float] = Field(default=0.0, ge=0)
    contract_value: Optional[float] = Field(default=0.0, ge=0)
    contract_length: Optional[int] = Field(None, ge=1)
    renewal_date: Optional[datetime] = None
    
    # Sales information
    lead_source: Optional[str] = Field(None, max_length=100)
    sales_stage: Optional[str] = Field(None, max_length=100)
    probability: Optional[float] = Field(default=0.0, ge=0, le=1)
    expected_close_date: Optional[datetime] = None
    
    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""
    reseller_id: UUID
    status: CustomerStatusEnum = CustomerStatusEnum.PROSPECT


class CustomerUpdate(BaseSchema):
    """Schema for updating a customer"""
    company_name: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Customer details
    status: Optional[CustomerStatusEnum] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[str] = Field(None, max_length=50)
    
    # Subscription information
    subscription_tier: Optional[str] = Field(None, max_length=100)
    monthly_value: Optional[float] = Field(None, ge=0)
    contract_value: Optional[float] = Field(None, ge=0)
    contract_length: Optional[int] = Field(None, ge=1)
    renewal_date: Optional[datetime] = None
    
    # Sales information
    lead_source: Optional[str] = Field(None, max_length=100)
    sales_stage: Optional[str] = Field(None, max_length=100)
    probability: Optional[float] = Field(None, ge=0, le=1)
    expected_close_date: Optional[datetime] = None
    
    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CustomerResponse(CustomerBase):
    """Schema for customer responses"""
    id: UUID
    reseller_id: UUID
    status: CustomerStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None


# Lead schemas
class LeadBase(BaseSchema):
    """Base lead schema"""
    company_name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    
    # Lead details
    source: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[str] = Field(None, max_length=50)
    
    # Sales information
    estimated_value: Optional[float] = Field(default=0.0, ge=0)
    probability: Optional[float] = Field(default=0.0, ge=0, le=1)
    expected_close_date: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    
    # Lead scoring
    temperature: Optional[str] = Field(default="cold", max_length=20)
    
    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    requirements: Optional[Dict[str, Any]] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    reseller_id: UUID
    status: LeadStatusEnum = LeadStatusEnum.NEW


class LeadUpdate(BaseSchema):
    """Schema for updating a lead"""
    company_name: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    
    # Lead details
    status: Optional[LeadStatusEnum] = None
    source: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[str] = Field(None, max_length=50)
    
    # Sales information
    estimated_value: Optional[float] = Field(None, ge=0)
    probability: Optional[float] = Field(None, ge=0, le=1)
    expected_close_date: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    
    # Lead scoring
    score: Optional[int] = Field(None, ge=0, le=100)
    temperature: Optional[str] = Field(None, max_length=20)
    
    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    requirements: Optional[Dict[str, Any]] = None


class LeadResponse(LeadBase):
    """Schema for lead responses"""
    id: UUID
    reseller_id: UUID
    status: LeadStatusEnum
    score: int
    last_contact_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Pricing schemas
class PricingTierBase(BaseSchema):
    """Base pricing tier schema"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    tier_level: int = Field(default=1, ge=1, le=10)
    
    # Pricing details
    base_price: float = Field(..., gt=0)
    reseller_price: float = Field(..., gt=0)
    suggested_retail_price: Optional[float] = Field(None, gt=0)
    minimum_retail_price: Optional[float] = Field(None, gt=0)
    
    # Features and limits
    features: Optional[List[str]] = None
    user_limit: Optional[int] = Field(None, ge=1)
    storage_limit_gb: Optional[int] = Field(None, ge=1)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    
    # Terms
    billing_cycle: str = Field(default="monthly", max_length=20)
    setup_fee: Optional[float] = Field(default=0.0, ge=0)
    contract_length: Optional[int] = Field(None, ge=1)


class PricingTierCreate(PricingTierBase):
    """Schema for creating a pricing tier"""
    reseller_id: UUID


class PricingTierUpdate(BaseSchema):
    """Schema for updating a pricing tier"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tier_level: Optional[int] = Field(None, ge=1, le=10)
    
    # Pricing details
    base_price: Optional[float] = Field(None, gt=0)
    reseller_price: Optional[float] = Field(None, gt=0)
    suggested_retail_price: Optional[float] = Field(None, gt=0)
    minimum_retail_price: Optional[float] = Field(None, gt=0)
    
    # Features and limits
    features: Optional[List[str]] = None
    user_limit: Optional[int] = Field(None, ge=1)
    storage_limit_gb: Optional[int] = Field(None, ge=1)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    
    # Terms
    billing_cycle: Optional[str] = Field(None, max_length=20)
    setup_fee: Optional[float] = Field(None, ge=0)
    contract_length: Optional[int] = Field(None, ge=1)
    active: Optional[bool] = None


class PricingTierResponse(PricingTierBase):
    """Schema for pricing tier responses"""
    id: UUID
    reseller_id: UUID
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Commission schemas
class CommissionBase(BaseSchema):
    """Base commission schema"""
    commission_type: CommissionTypeEnum = CommissionTypeEnum.PERCENTAGE
    order_id: Optional[str] = Field(None, max_length=255)
    product_name: Optional[str] = Field(None, max_length=255)
    
    # Financial information
    sale_amount: float = Field(..., gt=0)
    commission_rate: float = Field(..., ge=0, le=1)
    commission_amount: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    
    # Dates
    sale_date: datetime
    due_date: Optional[datetime] = None


class CommissionCreate(CommissionBase):
    """Schema for creating a commission"""
    reseller_id: UUID
    customer_id: Optional[UUID] = None


class CommissionUpdate(BaseSchema):
    """Schema for updating a commission"""
    commission_type: Optional[CommissionTypeEnum] = None
    order_id: Optional[str] = Field(None, max_length=255)
    product_name: Optional[str] = Field(None, max_length=255)
    
    # Financial information
    sale_amount: Optional[float] = Field(None, gt=0)
    commission_rate: Optional[float] = Field(None, ge=0, le=1)
    commission_amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    
    # Payment tracking
    payment_status: Optional[PaymentStatusEnum] = None
    payment_date: Optional[datetime] = None
    payment_reference: Optional[str] = Field(None, max_length=255)
    
    # Dates
    sale_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class CommissionResponse(CommissionBase):
    """Schema for commission responses"""
    id: UUID
    reseller_id: UUID
    customer_id: Optional[UUID] = None
    payment_status: PaymentStatusEnum
    payment_date: Optional[datetime] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Activity schemas
class ActivityBase(BaseSchema):
    """Base activity schema"""
    activity_type: str = Field(..., max_length=100)
    subject: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    outcome: Optional[str] = Field(None, max_length=100)
    duration_minutes: Optional[int] = Field(None, ge=0)
    
    # Follow-up
    next_action: Optional[str] = Field(None, max_length=255)
    next_action_date: Optional[datetime] = None
    
    # Metadata
    attachments: Optional[List[str]] = None


class CustomerActivityCreate(ActivityBase):
    """Schema for creating customer activity"""
    customer_id: UUID
    user_id: UUID


class LeadActivityCreate(ActivityBase):
    """Schema for creating lead activity"""
    lead_id: UUID
    user_id: UUID


class ActivityResponse(ActivityBase):
    """Schema for activity responses"""
    id: UUID
    user_id: UUID
    created_at: datetime


# Analytics schemas
class ResellerMetricsResponse(BaseSchema):
    """Schema for reseller metrics"""
    id: UUID
    reseller_id: UUID
    metric_date: datetime
    
    # Sales metrics
    leads_created: int
    leads_converted: int
    customers_acquired: int
    revenue_generated: float
    commission_earned: float
    
    # Pipeline metrics
    active_leads: int
    qualified_leads: int
    active_customers: int
    total_pipeline_value: float
    
    # Performance metrics
    conversion_rate: float
    average_deal_size: float
    sales_cycle_days: float
    
    created_at: datetime


class DashboardSummary(BaseSchema):
    """Schema for dashboard summary"""
    total_leads: int
    qualified_leads: int
    active_customers: int
    total_revenue: float
    pending_commissions: float
    conversion_rate: float
    average_deal_size: float
    pipeline_value: float


# Notification schemas
class NotificationBase(BaseSchema):
    """Base notification schema"""
    notification_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=255)
    message: str
    priority: str = Field(default="normal", max_length=20)
    action_required: bool = False
    action_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    reseller_id: UUID


class NotificationResponse(NotificationBase):
    """Schema for notification responses"""
    id: UUID
    reseller_id: UUID
    read: bool
    acknowledged: bool
    created_at: datetime
    read_at: Optional[datetime] = None


# Pagination schemas
class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: Optional[str] = Field(default="desc", regex="^(asc|desc)$")


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool