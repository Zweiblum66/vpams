"""
Pydantic schemas for Billing Service
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum

from src.db.models import (
    SubscriptionStatus, PaymentStatus, InvoiceStatus,
    PaymentMethodType, BillingInterval, Currency
)


# Base schemas
class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime]


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


# Plan schemas
class PlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    currency: Currency = Currency.USD
    billing_interval: BillingInterval
    trial_days: int = Field(0, ge=0)


class PlanCreate(PlanBase):
    features: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_limit: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    api_calls_limit: Optional[int] = None
    is_visible: bool = True


class PlanUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    user_limit: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    api_calls_limit: Optional[int] = None
    is_visible: Optional[bool] = None


class PlanResponse(PlanBase, TimestampMixin):
    id: UUID
    features: Dict[str, Any]
    metadata: Dict[str, Any]
    user_limit: Optional[int]
    storage_limit_gb: Optional[int]
    api_calls_limit: Optional[int]
    is_active: bool
    is_visible: bool
    stripe_product_id: Optional[str]
    stripe_price_id: Optional[str]
    paypal_plan_id: Optional[str]
    addons: List["PlanAddonResponse"] = []
    
    class Config:
        orm_mode = True


# Plan addon schemas
class PlanAddonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)


class PlanAddonCreate(PlanAddonBase):
    extra_users: int = 0
    extra_storage_gb: int = 0
    extra_api_calls: int = 0
    features: Dict[str, Any] = Field(default_factory=dict)


class PlanAddonResponse(PlanAddonBase, TimestampMixin):
    id: UUID
    plan_id: UUID
    extra_users: int
    extra_storage_gb: int
    extra_api_calls: int
    features: Dict[str, Any]
    is_active: bool
    
    class Config:
        orm_mode = True


# Customer schemas
class CustomerBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company_name: Optional[str] = None


class CustomerCreate(CustomerBase):
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    currency: Currency = Currency.USD
    locale: str = "en-US"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    currency: Optional[Currency] = None
    locale: Optional[str] = None


class CustomerResponse(CustomerBase, TimestampMixin):
    id: UUID
    organization_id: UUID
    company_name: Optional[str]
    billing_address_line1: Optional[str]
    billing_address_line2: Optional[str]
    billing_city: Optional[str]
    billing_state: Optional[str]
    billing_country: Optional[str]
    billing_postal_code: Optional[str]
    tax_id: Optional[str]
    tax_exempt: bool
    currency: Currency
    locale: str
    account_balance: Decimal
    stripe_customer_id: Optional[str]
    paypal_customer_id: Optional[str]
    
    class Config:
        orm_mode = True


# Subscription schemas
class SubscriptionBase(BaseModel):
    plan_id: UUID
    quantity: int = Field(1, ge=1)


class SubscriptionCreate(SubscriptionBase):
    payment_method_id: Optional[str] = None
    enable_trial: bool = True
    addon_ids: List[UUID] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class SubscriptionChangePlan(BaseModel):
    new_plan_id: UUID
    prorate: bool = True


class SubscriptionCancel(BaseModel):
    at_period_end: bool = True
    reason: Optional[str] = None


class SubscriptionResponse(SubscriptionBase, TimestampMixin):
    id: UUID
    customer_id: UUID
    status: SubscriptionStatus
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    ended_at: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]
    tax_percent: Decimal
    discount_percent: Decimal
    current_usage: Dict[str, Any]
    stripe_subscription_id: Optional[str]
    paypal_subscription_id: Optional[str]
    metadata: Dict[str, Any]
    cancel_reason: Optional[str]
    plan: Optional[PlanResponse]
    items: List["SubscriptionItemResponse"] = []
    
    class Config:
        orm_mode = True


class SubscriptionItemResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    type: str
    description: str
    quantity: int
    unit_price: Decimal
    addon_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        orm_mode = True


class SubscriptionUsage(BaseModel):
    subscription_id: UUID
    period_start: datetime
    period_end: datetime
    usage: Dict[str, float]
    limits: Dict[str, Optional[float]]
    overage_charges: Decimal


# Payment method schemas
class PaymentMethodBase(BaseModel):
    type: PaymentMethodType
    set_as_default: bool = False


class PaymentMethodCreate(PaymentMethodBase):
    # Card
    stripe_payment_method_id: Optional[str] = None
    
    # Bank account
    account_number: Optional[str] = None
    routing_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    bank_name: Optional[str] = None
    
    # PayPal
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentMethodResponse(PaymentMethodBase, TimestampMixin):
    id: UUID
    customer_id: UUID
    is_default: bool
    
    # Card details
    last4: Optional[str]
    brand: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    
    # Bank details
    bank_name: Optional[str]
    account_last4: Optional[str]
    routing_number: Optional[str]
    
    # Processor IDs
    stripe_payment_method_id: Optional[str]
    paypal_payment_method_id: Optional[str]
    
    class Config:
        orm_mode = True


# Payment schemas
class PaymentBase(BaseModel):
    amount: Decimal = Field(..., ge=0)
    currency: Currency = Currency.USD
    description: Optional[str] = None


class ChargeCreate(PaymentBase):
    payment_method_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentUpdate(BaseModel):
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentResponse(PaymentBase, TimestampMixin):
    id: UUID
    customer_id: UUID
    invoice_id: Optional[UUID]
    status: PaymentStatus
    payment_method_id: Optional[UUID]
    payment_method_type: Optional[PaymentMethodType]
    stripe_payment_intent_id: Optional[str]
    stripe_charge_id: Optional[str]
    paypal_payment_id: Optional[str]
    failure_code: Optional[str]
    failure_message: Optional[str]
    refunded_amount: int
    refund_reason: Optional[str]
    metadata: Dict[str, Any]
    
    class Config:
        orm_mode = True


# Refund schemas
class RefundCreate(BaseModel):
    amount: Optional[Decimal] = None  # None means full refund
    reason: str


class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    amount: int
    currency: Currency
    status: PaymentStatus
    reason: str
    stripe_refund_id: Optional[str]
    paypal_refund_id: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True


# Invoice schemas
class InvoiceLineItemBase(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal


class InvoiceLineItemCreate(InvoiceLineItemBase):
    type: Optional[str] = "custom"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvoiceLineItemResponse(InvoiceLineItemBase):
    id: UUID
    invoice_id: UUID
    amount: int
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    type: str
    metadata: Dict[str, Any]
    
    class Config:
        orm_mode = True


class InvoiceBase(BaseModel):
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    currency: Optional[Currency] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    line_items: List[InvoiceLineItemCreate]
    tax_rate: Optional[Decimal] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InvoiceSend(BaseModel):
    recipients: Optional[List[EmailStr]] = None
    cc: Optional[List[EmailStr]] = None
    subject: Optional[str] = None
    message: Optional[str] = None


class InvoiceResponse(InvoiceBase, TimestampMixin):
    id: UUID
    customer_id: UUID
    subscription_id: Optional[UUID]
    invoice_number: str
    status: InvoiceStatus
    subtotal: int
    tax: int
    total: int
    amount_paid: int
    amount_due: int
    currency: Currency
    paid_at: Optional[datetime]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    stripe_invoice_id: Optional[str]
    paypal_invoice_id: Optional[str]
    pdf_url: Optional[str]
    metadata: Dict[str, Any]
    line_items: List[InvoiceLineItemResponse] = []
    
    class Config:
        orm_mode = True


# Tax schemas
class TaxCalculationRequest(BaseModel):
    amount: Decimal = Field(..., ge=0)
    currency: Optional[Currency] = None
    billing_address: Optional[Dict[str, str]] = None
    tax_code: Optional[str] = None


class TaxCalculationResponse(BaseModel):
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    tax_rate: Decimal
    tax_breakdown: List[Dict[str, Any]]
    currency: Currency


class TaxRateResponse(BaseModel):
    id: str
    country: str
    state: Optional[str]
    rate: Decimal
    name: str
    inclusive: bool
    active: bool


class TaxSettingsUpdate(BaseModel):
    tax_calculation_enabled: Optional[bool] = None
    tax_inclusive_pricing: Optional[bool] = None
    default_tax_code: Optional[str] = None
    nexus_addresses: Optional[List[Dict[str, str]]] = None


# Analytics schemas
class MRRResponse(BaseModel):
    current_mrr: float
    growth_rate: float
    monthly_data: List[Dict[str, Any]]
    new_mrr: float
    expansion_mrr: float
    contraction_mrr: float
    churned_mrr: float
    net_new_mrr: float


class ChurnResponse(BaseModel):
    customer_churn_rate: float
    revenue_churn_rate: float
    gross_revenue_churn: float
    net_revenue_churn: float
    churned_customers: int
    churn_reasons: Dict[str, int]
    average_customer_lifetime_months: float
    period_months: int


class RevenueResponse(BaseModel):
    total_revenue: float
    recurring_revenue: float
    one_time_revenue: float
    revenue_data: List[Dict[str, Any]]
    revenue_by_plan: Dict[str, float]
    revenue_by_currency: Dict[str, float]
    arpu: float
    ltv: float
    period: Dict[str, Any]


class CustomerMetricsResponse(BaseModel):
    total_customers: int
    active_customers: int
    new_customers_this_month: int
    trial_customers: int
    customer_by_plan: Dict[str, int]
    value_distribution: Dict[str, int]
    geographic_distribution: Dict[str, int]
    average_customers_per_month: float


class GrowthMetricsResponse(BaseModel):
    compound_monthly_growth_rate: float
    net_revenue_retention: float
    expansion_revenue: float
    quick_ratio: float
    monthly_growth_data: List[Dict[str, Any]]
    cohort_retention: Dict[str, List[float]]


# Update forward references
PlanResponse.update_forward_refs()
SubscriptionResponse.update_forward_refs()
InvoiceResponse.update_forward_refs()