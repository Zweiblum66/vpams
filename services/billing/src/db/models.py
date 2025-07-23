"""
Database models for Billing Service
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, DECIMAL, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from src.db.base import Base


class SubscriptionStatus(PyEnum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    PAUSED = "paused"


class PaymentStatus(PyEnum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class InvoiceStatus(PyEnum):
    """Invoice status"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class PaymentMethodType(PyEnum):
    """Payment method types"""
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    PAYPAL = "paypal"
    WIRE_TRANSFER = "wire_transfer"
    CREDIT = "credit"


class BillingInterval(PyEnum):
    """Billing intervals"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class Currency(PyEnum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class Plan(Base):
    """Subscription plans"""
    __tablename__ = "plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Pricing
    base_price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(Enum(Currency), default=Currency.USD)
    billing_interval = Column(Enum(BillingInterval), nullable=False)
    trial_days = Column(Integer, default=0)
    
    # Features and limits
    features = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Usage limits
    user_limit = Column(Integer)
    storage_limit_gb = Column(Integer)
    api_calls_limit = Column(Integer)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    
    # Stripe/PayPal IDs
    stripe_product_id = Column(String(255))
    stripe_price_id = Column(String(255))
    paypal_plan_id = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    addons = relationship("PlanAddon", back_populates="plan")


class PlanAddon(Base):
    """Plan add-ons"""
    __tablename__ = "plan_addons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Pricing
    price = Column(DECIMAL(10, 2), nullable=False)
    
    # What it provides
    extra_users = Column(Integer, default=0)
    extra_storage_gb = Column(Integer, default=0)
    extra_api_calls = Column(Integer, default=0)
    features = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    plan = relationship("Plan", back_populates="addons")


class Customer(Base):
    """Billing customers (maps to organizations)"""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    
    # Billing info
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    company_name = Column(String(255))
    
    # Address
    billing_address_line1 = Column(String(255))
    billing_address_line2 = Column(String(255))
    billing_city = Column(String(100))
    billing_state = Column(String(100))
    billing_country = Column(String(2))
    billing_postal_code = Column(String(20))
    
    # Tax
    tax_id = Column(String(50))
    tax_exempt = Column(Boolean, default=False)
    tax_ids = Column(JSON, default=list)  # Multiple tax IDs
    
    # Payment processor IDs
    stripe_customer_id = Column(String(255), unique=True)
    paypal_customer_id = Column(String(255), unique=True)
    
    # Settings
    currency = Column(Enum(Currency), default=Currency.USD)
    locale = Column(String(10), default="en-US")
    
    # Credit balance
    account_balance = Column(DECIMAL(10, 2), default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="customer")
    payment_methods = relationship("PaymentMethod", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")


class Subscription(Base):
    """Customer subscriptions"""
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    
    # Status
    status = Column(Enum(SubscriptionStatus), nullable=False)
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    canceled_at = Column(DateTime(timezone=True))
    
    # Billing
    quantity = Column(Integer, default=1)
    tax_percent = Column(DECIMAL(5, 2), default=0)
    discount_percent = Column(DECIMAL(5, 2), default=0)
    
    # Usage tracking
    current_usage = Column(JSON, default=dict)
    
    # Payment processor IDs
    stripe_subscription_id = Column(String(255), unique=True)
    paypal_subscription_id = Column(String(255), unique=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    cancel_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    items = relationship("SubscriptionItem", back_populates="subscription")
    invoices = relationship("Invoice", back_populates="subscription")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_customer_status', 'customer_id', 'status'),
        Index('idx_subscription_dates', 'current_period_end', 'status'),
    )


class SubscriptionItem(Base):
    """Subscription line items (for add-ons)"""
    __tablename__ = "subscription_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    type = Column(String(50), nullable=False)  # 'addon', 'usage', 'discount'
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    
    # For add-ons
    addon_id = Column(UUID(as_uuid=True), ForeignKey("plan_addons.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="items")


class PaymentMethod(Base):
    """Customer payment methods"""
    __tablename__ = "payment_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    
    type = Column(Enum(PaymentMethodType), nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Card details (tokenized)
    last4 = Column(String(4))
    brand = Column(String(20))
    exp_month = Column(Integer)
    exp_year = Column(Integer)
    
    # Bank account details (tokenized)
    bank_name = Column(String(100))
    account_last4 = Column(String(4))
    routing_number = Column(String(20))
    
    # Payment processor IDs
    stripe_payment_method_id = Column(String(255), unique=True)
    paypal_payment_method_id = Column(String(255), unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="payment_methods")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('(type = \'card\' AND last4 IS NOT NULL) OR type != \'card\''),
        CheckConstraint('(type = \'bank_account\' AND account_last4 IS NOT NULL) OR type != \'bank_account\''),
    )


class Invoice(Base):
    """Customer invoices"""
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False)
    
    # Amounts (in cents)
    subtotal = Column(Integer, nullable=False)
    tax = Column(Integer, default=0)
    total = Column(Integer, nullable=False)
    amount_paid = Column(Integer, default=0)
    amount_due = Column(Integer, nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    
    # Dates
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True))
    
    # Billing period
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    # Payment processor IDs
    stripe_invoice_id = Column(String(255), unique=True)
    paypal_invoice_id = Column(String(255), unique=True)
    
    # PDF
    pdf_url = Column(String(500))
    
    # Metadata
    metadata = Column(JSON, default=dict)
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")
    
    # Indexes
    __table_args__ = (
        Index('idx_invoice_customer_status', 'customer_id', 'status'),
        Index('idx_invoice_number', 'invoice_number'),
        Index('idx_invoice_dates', 'due_date', 'status'),
    )


class InvoiceLineItem(Base):
    """Invoice line items"""
    __tablename__ = "invoice_line_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    
    description = Column(String(500), nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit_price = Column(Integer, nullable=False)  # In cents
    amount = Column(Integer, nullable=False)  # In cents
    
    # Period for subscription items
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    # Type
    type = Column(String(50))  # 'subscription', 'addon', 'usage', 'credit', 'tax'
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")


class Payment(Base):
    """Payment transactions"""
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(Enum(Currency), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False)
    
    # Payment method used
    payment_method_id = Column(UUID(as_uuid=True), ForeignKey("payment_methods.id"))
    payment_method_type = Column(Enum(PaymentMethodType))
    
    # Payment processor info
    stripe_payment_intent_id = Column(String(255), unique=True)
    stripe_charge_id = Column(String(255), unique=True)
    paypal_payment_id = Column(String(255), unique=True)
    
    # Failure info
    failure_code = Column(String(50))
    failure_message = Column(Text)
    
    # Refund info
    refunded_amount = Column(Integer, default=0)
    refund_reason = Column(Text)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    description = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment")
    
    # Indexes
    __table_args__ = (
        Index('idx_payment_customer_status', 'customer_id', 'status'),
        Index('idx_payment_created', 'created_at', 'status'),
    )


class Refund(Base):
    """Payment refunds"""
    __tablename__ = "refunds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(Enum(Currency), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False)
    reason = Column(String(255))
    
    # Payment processor info
    stripe_refund_id = Column(String(255), unique=True)
    paypal_refund_id = Column(String(255), unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    payment = relationship("Payment", back_populates="refunds")


class Coupon(Base):
    """Discount coupons"""
    __tablename__ = "coupons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    
    # Discount
    percent_off = Column(DECIMAL(5, 2))
    amount_off = Column(Integer)  # In cents
    currency = Column(Enum(Currency))
    
    # Validity
    valid_from = Column(DateTime(timezone=True))
    valid_until = Column(DateTime(timezone=True))
    max_redemptions = Column(Integer)
    times_redeemed = Column(Integer, default=0)
    
    # Restrictions
    applicable_plans = Column(JSON, default=list)  # List of plan IDs
    minimum_amount = Column(Integer)  # Minimum order amount in cents
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint('(percent_off IS NOT NULL AND amount_off IS NULL) OR (percent_off IS NULL AND amount_off IS NOT NULL)'),
    )


class UsageRecord(Base):
    """Usage-based billing records"""
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    metric = Column(String(50), nullable=False)  # 'storage_gb', 'api_calls', etc.
    quantity = Column(DECIMAL(20, 4), nullable=False)
    unit_price = Column(DECIMAL(10, 4))  # Price per unit if applicable
    
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Billing
    is_billed = Column(Boolean, default=False)
    invoice_line_item_id = Column(UUID(as_uuid=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_subscription_metric', 'subscription_id', 'metric', 'timestamp'),
        Index('idx_usage_billing', 'is_billed', 'timestamp'),
    )