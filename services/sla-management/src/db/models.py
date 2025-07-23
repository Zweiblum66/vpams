"""
Database models for SLA Management Service.
"""
from datetime import datetime, timezone
from typing import Optional
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, Numeric, JSON, Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SLATierEnum(PyEnum):
    """SLA service tiers."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    PREMIUM = "premium"


class SLAStatusEnum(PyEnum):
    """SLA status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class MetricTypeEnum(PyEnum):
    """SLA metric types."""
    PERCENTAGE = "percentage"
    TIME = "time"
    COUNT = "count"
    BOOLEAN = "boolean"


class PenaltyTypeEnum(PyEnum):
    """SLA penalty types."""
    CREDIT = "credit"
    REFUND = "refund"
    TERMINATION_RIGHT = "termination_right"


class NotificationTypeEnum(PyEnum):
    """SLA notification types."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"


class ComplianceStatusEnum(PyEnum):
    """SLA compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    CRITICAL = "critical"


class Customer(Base):
    """Customer model (simplified for SLA service)."""
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(100), nullable=False, unique=True, index=True)
    company_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sla_agreements = relationship("SLAAgreement", back_populates="customer")


class SLAAgreement(Base):
    """SLA agreement records."""
    __tablename__ = "sla_agreements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Customer relationship
    customer_id = Column(String(100), ForeignKey("customers.customer_id"), nullable=False)
    
    # Agreement details
    tier = Column(Enum(SLATierEnum), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default="1.0")
    
    # Agreement lifecycle
    status = Column(Enum(SLAStatusEnum), nullable=False, default=SLAStatusEnum.PENDING, index=True)
    effective_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    auto_renewal = Column(Boolean, nullable=False, default=True)
    billing_cycle = Column(String(20), nullable=False, default="monthly")
    
    # Legal terms
    terms_and_conditions = Column(Text, nullable=False)
    signed_date = Column(DateTime(timezone=True), nullable=True)
    signed_by = Column(String(255), nullable=True)
    
    # Configuration
    custom_terms = Column(JSON, nullable=True)
    escalation_contacts = Column(JSON, nullable=True)  # List of escalation contacts
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="sla_agreements")
    metrics = relationship("SLAMetric", back_populates="agreement", cascade="all, delete-orphan")
    penalties = relationship("SLAPenalty", back_populates="agreement", cascade="all, delete-orphan")
    notifications = relationship("SLANotification", back_populates="agreement", cascade="all, delete-orphan")
    compliance_records = relationship("SLAComplianceRecord", back_populates="agreement")
    
    __table_args__ = (
        Index('idx_sla_agreement_customer', 'customer_id', 'status'),
        Index('idx_sla_agreement_tier', 'tier', 'status'),
        Index('idx_sla_agreement_dates', 'effective_date', 'expiration_date'),
    )


class SLAMetric(Base):
    """SLA metric definitions."""
    __tablename__ = "sla_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(String(100), ForeignKey("sla_agreements.agreement_id"), nullable=False)
    
    # Metric identification
    metric_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Metric configuration
    type = Column(Enum(MetricTypeEnum), nullable=False)
    target_value = Column(Numeric(10, 4), nullable=False)
    measurement_unit = Column(String(50), nullable=False)
    measurement_period = Column(String(50), nullable=False)  # hourly, daily, weekly, monthly
    calculation_method = Column(String(50), nullable=False, default="average")
    
    # Thresholds
    threshold_warning = Column(Numeric(10, 4), nullable=True)
    threshold_critical = Column(Numeric(10, 4), nullable=True)
    
    # Configuration
    data_source = Column(String(100), nullable=True)  # Where to get metric data
    calculation_query = Column(Text, nullable=True)  # SQL query or calculation logic
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agreement = relationship("SLAAgreement", back_populates="metrics")
    measurements = relationship("SLAMetricMeasurement", back_populates="metric")
    
    __table_args__ = (
        UniqueConstraint('agreement_id', 'metric_id', name='uq_sla_metric_agreement'),
        Index('idx_sla_metric_type', 'type', 'enabled'),
        Index('idx_sla_metric_period', 'measurement_period', 'enabled'),
    )


class SLAPenalty(Base):
    """SLA penalty definitions."""
    __tablename__ = "sla_penalties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(String(100), ForeignKey("sla_agreements.agreement_id"), nullable=False)
    
    # Penalty identification
    penalty_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Trigger conditions
    trigger_condition = Column(String(500), nullable=False)  # Expression to evaluate
    related_metric_ids = Column(JSON, nullable=True)  # List of related metric IDs
    
    # Penalty configuration
    penalty_type = Column(Enum(PenaltyTypeEnum), nullable=False)
    penalty_amount = Column(Numeric(10, 4), nullable=False)
    penalty_unit = Column(String(50), nullable=False)  # percentage, fixed_amount, service_credits
    max_penalty_per_period = Column(Numeric(10, 4), nullable=True)
    
    # Escalation
    escalation_rules = Column(JSON, nullable=True)  # List of escalation steps
    auto_apply = Column(Boolean, nullable=False, default=True)
    requires_approval = Column(Boolean, nullable=False, default=False)
    
    # Status
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agreement = relationship("SLAAgreement", back_populates="penalties")
    penalty_applications = relationship("SLAPenaltyApplication", back_populates="penalty")
    
    __table_args__ = (
        UniqueConstraint('agreement_id', 'penalty_id', name='uq_sla_penalty_agreement'),
        Index('idx_sla_penalty_type', 'penalty_type', 'enabled'),
    )


class SLANotification(Base):
    """SLA notification configurations."""
    __tablename__ = "sla_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(String(100), ForeignKey("sla_agreements.agreement_id"), nullable=False)
    
    # Notification identification
    notification_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Trigger configuration
    trigger_condition = Column(String(500), nullable=False)
    related_metric_ids = Column(JSON, nullable=True)
    
    # Notification configuration
    notification_type = Column(Enum(NotificationTypeEnum), nullable=False)
    recipients = Column(JSON, nullable=False)  # List of recipients
    template = Column(String(100), nullable=True)
    message_template = Column(Text, nullable=True)
    
    # Escalation
    escalation_delay = Column(Integer, nullable=True)  # Minutes
    escalation_recipients = Column(JSON, nullable=True)
    max_escalation_level = Column(Integer, nullable=False, default=3)
    
    # Rate limiting
    cooldown_period = Column(Integer, nullable=False, default=60)  # Minutes
    max_notifications_per_hour = Column(Integer, nullable=False, default=10)
    
    # Status
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agreement = relationship("SLAAgreement", back_populates="notifications")
    notification_logs = relationship("SLANotificationLog", back_populates="notification")
    
    __table_args__ = (
        UniqueConstraint('agreement_id', 'notification_id', name='uq_sla_notification_agreement'),
        Index('idx_sla_notification_type', 'notification_type', 'enabled'),
    )


class SLAMetricMeasurement(Base):
    """SLA metric measurements."""
    __tablename__ = "sla_metric_measurements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(UUID(as_uuid=True), ForeignKey("sla_metrics.id"), nullable=False)
    
    # Measurement data
    measured_value = Column(Numeric(15, 6), nullable=False)
    measurement_timestamp = Column(DateTime(timezone=True), nullable=False)
    measurement_period_start = Column(DateTime(timezone=True), nullable=False)
    measurement_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Quality indicators
    data_quality_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    sample_size = Column(Integer, nullable=True)
    confidence_interval = Column(Numeric(5, 2), nullable=True)
    
    # Metadata
    measurement_source = Column(String(100), nullable=True)
    raw_data = Column(JSON, nullable=True)
    calculation_details = Column(JSON, nullable=True)
    
    # Status
    is_validated = Column(Boolean, nullable=False, default=False)
    validation_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    metric = relationship("SLAMetric", back_populates="measurements")
    
    __table_args__ = (
        Index('idx_sla_measurement_metric', 'metric_id', 'measurement_timestamp'),
        Index('idx_sla_measurement_period', 'measurement_period_start', 'measurement_period_end'),
        Index('idx_sla_measurement_timestamp', 'measurement_timestamp'),
    )


class SLAComplianceRecord(Base):
    """SLA compliance tracking records."""
    __tablename__ = "sla_compliance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(String(100), ForeignKey("sla_agreements.agreement_id"), nullable=False)
    
    # Compliance period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly
    
    # Compliance results
    overall_compliance_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    compliant_metrics = Column(Integer, nullable=False, default=0)
    total_metrics = Column(Integer, nullable=False, default=0)
    status = Column(Enum(ComplianceStatusEnum), nullable=False)
    
    # Breach information
    breached_metrics = Column(JSON, nullable=True)  # List of breached metric details
    triggered_penalties = Column(JSON, nullable=True)  # List of triggered penalties
    total_penalty_amount = Column(Numeric(12, 2), nullable=False, default=0)
    penalty_currency = Column(String(3), nullable=False, default="USD")
    
    # Analysis
    trend_indicator = Column(String(20), nullable=True)  # improving, declining, stable
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical
    recommendations = Column(JSON, nullable=True)  # List of recommendations
    
    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agreement = relationship("SLAAgreement", back_populates="compliance_records")
    
    __table_args__ = (
        UniqueConstraint('agreement_id', 'period_start', 'period_type', name='uq_compliance_period'),
        Index('idx_compliance_agreement', 'agreement_id', 'period_start'),
        Index('idx_compliance_status', 'status', 'period_end'),
        Index('idx_compliance_score', 'overall_compliance_score', 'period_end'),
    )


class SLAPenaltyApplication(Base):
    """SLA penalty applications."""
    __tablename__ = "sla_penalty_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    penalty_id = Column(UUID(as_uuid=True), ForeignKey("sla_penalties.id"), nullable=False)
    compliance_record_id = Column(UUID(as_uuid=True), ForeignKey("sla_compliance_records.id"), nullable=False)
    
    # Application details
    application_date = Column(DateTime(timezone=True), nullable=False)
    triggered_by_metric = Column(String(100), nullable=False)
    breach_severity = Column(String(20), nullable=False)  # minor, major, critical
    
    # Penalty calculation
    calculated_amount = Column(Numeric(12, 2), nullable=False)
    actual_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    adjustment_reason = Column(Text, nullable=True)
    
    # Application status
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, applied, disputed
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Dispute handling
    is_disputed = Column(Boolean, nullable=False, default=False)
    dispute_reason = Column(Text, nullable=True)
    dispute_resolution = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    penalty = relationship("SLAPenalty", back_populates="penalty_applications")
    compliance_record = relationship("SLAComplianceRecord")
    
    __table_args__ = (
        Index('idx_penalty_application_date', 'application_date'),
        Index('idx_penalty_application_status', 'status', 'application_date'),
    )


class SLANotificationLog(Base):
    """SLA notification logs."""
    __tablename__ = "sla_notification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("sla_notifications.id"), nullable=False)
    
    # Notification details
    triggered_at = Column(DateTime(timezone=True), nullable=False)
    trigger_condition = Column(String(500), nullable=False)
    trigger_data = Column(JSON, nullable=True)
    
    # Delivery details
    delivery_method = Column(String(50), nullable=False)
    recipients = Column(JSON, nullable=False)
    message_content = Column(Text, nullable=True)
    
    # Delivery status
    delivery_status = Column(String(20), nullable=False)  # sent, delivered, failed, bounced
    delivery_timestamp = Column(DateTime(timezone=True), nullable=True)
    delivery_attempts = Column(Integer, nullable=False, default=1)
    failure_reason = Column(Text, nullable=True)
    
    # Response tracking
    acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Escalation tracking
    escalation_level = Column(Integer, nullable=False, default=0)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    notification = relationship("SLANotification", back_populates="notification_logs")
    
    __table_args__ = (
        Index('idx_notification_log_triggered', 'triggered_at'),
        Index('idx_notification_log_status', 'delivery_status', 'triggered_at'),
        Index('idx_notification_log_escalation', 'escalation_level', 'triggered_at'),
    )