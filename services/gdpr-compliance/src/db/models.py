"""Database models for GDPR Compliance Service"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Boolean, JSON,
    ForeignKey, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .base import Base


class ConsentType(enum.Enum):
    """Types of consent"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    ESSENTIAL = "essential"
    PERFORMANCE = "performance"
    FUNCTIONAL = "functional"
    THIRD_PARTY = "third_party"


class DataRequestType(enum.Enum):
    """Types of GDPR data requests"""
    ACCESS = "access"  # Right to access
    PORTABILITY = "portability"  # Right to data portability
    RECTIFICATION = "rectification"  # Right to rectification
    ERASURE = "erasure"  # Right to be forgotten
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"  # Right to object


class DataRequestStatus(enum.Enum):
    """Status of GDPR data requests"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PrivacyLevel(enum.Enum):
    """Privacy levels for data classification"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class UserConsent(Base):
    """User consent tracking"""
    __tablename__ = "user_consents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    consent_given = Column(Boolean, nullable=False, default=False)
    consent_date = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)
    
    # Versioning
    policy_version = Column(String(20), nullable=False)
    consent_text = Column(Text)
    
    # Withdrawal
    withdrawn = Column(Boolean, default=False)
    withdrawal_date = Column(DateTime(timezone=True))
    withdrawal_reason = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    data_requests = relationship("DataRequest", back_populates="consent")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_consent_type", "user_id", "consent_type"),
        Index("idx_consent_date", "consent_date"),
        Index("idx_policy_version", "policy_version"),
    )


class DataRequest(Base):
    """GDPR data requests (access, deletion, etc.)"""
    __tablename__ = "data_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    request_type = Column(SQLEnum(DataRequestType), nullable=False)
    status = Column(SQLEnum(DataRequestStatus), nullable=False, default=DataRequestStatus.PENDING)
    
    # Request details
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    requested_by = Column(String(255))  # Could be user or admin
    request_reason = Column(Text)
    request_data = Column(JSONB)  # Additional request parameters
    
    # Processing
    processed_at = Column(DateTime(timezone=True))
    processed_by = Column(String(255))
    processing_notes = Column(Text)
    
    # Results
    result_data = Column(JSONB)  # Result metadata
    export_path = Column(String(512))  # Path to exported data
    export_format = Column(String(20))  # json, csv, pdf, etc.
    export_size_bytes = Column(Integer)
    
    # Verification
    verification_token = Column(String(255))
    verification_expires = Column(DateTime(timezone=True))
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    
    # Notification
    notification_email = Column(String(255))
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    
    # Deletion specific
    deletion_scheduled = Column(DateTime(timezone=True))
    deletion_completed = Column(DateTime(timezone=True))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    consent_id = Column(UUID(as_uuid=True), ForeignKey("user_consents.id"))
    consent = relationship("UserConsent", back_populates="data_requests")
    audit_logs = relationship("GDPRAuditLog", back_populates="data_request")
    
    # Indexes
    __table_args__ = (
        Index("idx_request_user_type", "user_id", "request_type"),
        Index("idx_request_status", "status"),
        Index("idx_requested_at", "requested_at"),
        Index("idx_deletion_scheduled", "deletion_scheduled"),
    )


class DataCategory(Base):
    """Categories of personal data collected"""
    __tablename__ = "data_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    privacy_level = Column(SQLEnum(PrivacyLevel), nullable=False, default=PrivacyLevel.INTERNAL)
    
    # Data handling
    retention_days = Column(Integer)  # Override default retention
    is_sensitive = Column(Boolean, default=False)  # Special category data
    requires_explicit_consent = Column(Boolean, default=False)
    can_be_anonymized = Column(Boolean, default=True)
    
    # Legal basis
    legal_basis = Column(String(100))  # consent, contract, legal obligation, etc.
    purpose = Column(Text)  # Why we collect this data
    
    # Third party sharing
    shared_with_third_parties = Column(Boolean, default=False)
    third_party_details = Column(JSONB)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    data_mappings = relationship("DataMapping", back_populates="category")


class DataMapping(Base):
    """Mapping of data fields to categories for GDPR compliance"""
    __tablename__ = "data_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("data_categories.id"))
    
    # Field details
    field_description = Column(Text)
    contains_pii = Column(Boolean, default=True)
    encryption_required = Column(Boolean, default=False)
    
    # Anonymization
    anonymization_method = Column(String(50))  # hash, mask, remove, etc.
    anonymization_params = Column(JSONB)
    
    # Export/Import
    include_in_export = Column(Boolean, default=True)
    export_transform = Column(String(50))  # Function to apply during export
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    category = relationship("DataCategory", back_populates="data_mappings")
    
    # Indexes
    __table_args__ = (
        Index("idx_table_column", "table_name", "column_name", unique=True),
        Index("idx_category_mapping", "category_id"),
    )


class PrivacyPolicy(Base):
    """Privacy policy versions"""
    __tablename__ = "privacy_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(20), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)  # Plain language summary
    
    # Language support
    language = Column(String(10), default="en")
    
    # Validity
    effective_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Changes
    change_summary = Column(Text)
    requires_re_consent = Column(Boolean, default=False)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_policy_version", "version"),
        Index("idx_policy_active", "is_active"),
        Index("idx_effective_date", "effective_date"),
    )


class DataRetentionRule(Base):
    """Data retention rules for different data types"""
    __tablename__ = "data_retention_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Rule criteria
    table_name = Column(String(100))
    data_category_id = Column(UUID(as_uuid=True), ForeignKey("data_categories.id"))
    condition_sql = Column(Text)  # SQL condition to identify data
    
    # Retention settings
    retention_days = Column(Integer, nullable=False)
    deletion_method = Column(String(50))  # hard_delete, soft_delete, anonymize
    
    # Execution
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    run_frequency_days = Column(Integer, default=1)
    
    # Statistics
    last_run_deleted_count = Column(Integer)
    total_deleted_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_retention_active", "is_active"),
        Index("idx_next_run", "next_run"),
    )


class GDPRAuditLog(Base):
    """Audit log for all GDPR-related activities"""
    __tablename__ = "gdpr_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # consent, request, export, deletion, etc.
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Actor
    actor_id = Column(UUID(as_uuid=True))
    actor_type = Column(String(50))  # user, admin, system
    actor_ip = Column(String(45))
    actor_user_agent = Column(Text)
    
    # Subject
    subject_user_id = Column(UUID(as_uuid=True), index=True)
    data_request_id = Column(UUID(as_uuid=True), ForeignKey("data_requests.id"))
    
    # Event details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    
    # Changes
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Additional context
    metadata = Column(JSONB)
    
    # Relationships
    data_request = relationship("DataRequest", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_timestamp", "event_timestamp"),
    )


class AnonymizationLog(Base):
    """Log of data anonymization activities"""
    __tablename__ = "anonymization_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    anonymized_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # What was anonymized
    tables_affected = Column(JSONB)  # List of tables and record counts
    total_records = Column(Integer)
    
    # Method
    anonymization_method = Column(String(50))
    partial_anonymization = Column(Boolean, default=False)
    
    # Verification
    verified = Column(Boolean, default=False)
    verification_method = Column(String(100))
    verification_timestamp = Column(DateTime(timezone=True))
    
    # Metadata
    requested_by = Column(String(255))
    reason = Column(Text)
    
    # Indexes
    __table_args__ = (
        Index("idx_anon_user", "user_id"),
        Index("idx_anon_timestamp", "anonymized_at"),
    )


# Policy Engine Models

class PolicySeverity(enum.Enum):
    """Severity levels for policy violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyStatus(enum.Enum):
    """Status of policy definitions"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class EvaluationResult(enum.Enum):
    """Results of policy evaluation"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


class PolicyDefinition(Base):
    """Policy definitions for governance rules"""
    __tablename__ = "policy_definitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    
    # Policy details
    severity = Column(SQLEnum(PolicySeverity), default=PolicySeverity.MEDIUM)
    status = Column(SQLEnum(PolicyStatus), default=PolicyStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    
    # Configuration
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255))
    
    # Relationships
    rules = relationship("PolicyRule", back_populates="policy", cascade="all, delete-orphan")
    evaluations = relationship("PolicyEvaluation", back_populates="policy")
    violations = relationship("PolicyViolation", back_populates="policy")
    assignments = relationship("PolicyAssignment", back_populates="policy")
    
    # Indexes
    __table_args__ = (
        Index("idx_policy_category", "category"),
        Index("idx_policy_status", "status"),
        Index("idx_policy_active", "is_active"),
    )


class PolicyRule(Base):
    """Individual rules within a policy"""
    __tablename__ = "policy_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policy_definitions.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Rule definition
    condition = Column(JSONB, nullable=False)  # Condition to evaluate
    action = Column(JSONB)  # Action to take if rule fails
    
    # Execution
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    policy = relationship("PolicyDefinition", back_populates="rules")
    violations = relationship("PolicyViolation", back_populates="rule")
    
    # Indexes
    __table_args__ = (
        Index("idx_rule_policy", "policy_id"),
        Index("idx_rule_order", "policy_id", "order_index"),
    )


class PolicyEvaluation(Base):
    """Record of policy evaluations"""
    __tablename__ = "policy_evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policy_definitions.id"), nullable=False)
    
    # What was evaluated
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255))
    
    # Evaluation details
    result = Column(SQLEnum(EvaluationResult), nullable=False)
    passed_rules = Column(JSONB, default=[])
    failed_rules = Column(JSONB, default=[])
    
    # Context
    context = Column(JSONB, default={})
    evaluation_duration_ms = Column(Integer)
    
    # Timestamps
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluated_by = Column(String(255))
    
    # Relationships
    policy = relationship("PolicyDefinition", back_populates="evaluations")
    
    # Indexes
    __table_args__ = (
        Index("idx_eval_policy", "policy_id"),
        Index("idx_eval_entity", "entity_type", "entity_id"),
        Index("idx_eval_result", "result"),
        Index("idx_eval_timestamp", "evaluated_at"),
    )


class PolicyViolation(Base):
    """Record of policy violations"""
    __tablename__ = "policy_violations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policy_definitions.id"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("policy_rules.id"))
    
    # Violation details
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255))
    severity = Column(SQLEnum(PolicySeverity), nullable=False)
    
    # Description
    description = Column(Text, nullable=False)
    details = Column(JSONB, default={})
    context = Column(JSONB, default={})
    
    # Status
    status = Column(String(50), default="open")  # open, acknowledged, resolved, dismissed
    
    # Resolution
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    detected_by = Column(String(255))
    
    # Relationships
    policy = relationship("PolicyDefinition", back_populates="violations")
    rule = relationship("PolicyRule", back_populates="violations")
    
    # Indexes
    __table_args__ = (
        Index("idx_violation_policy", "policy_id"),
        Index("idx_violation_entity", "entity_type", "entity_id"),
        Index("idx_violation_status", "status"),
        Index("idx_violation_severity", "severity"),
        Index("idx_violation_timestamp", "created_at"),
    )


class PolicyAssignment(Base):
    """Assignment of policies to specific entities"""
    __tablename__ = "policy_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policy_definitions.id"), nullable=False)
    
    # Assignment target
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255), nullable=False)
    
    # Configuration
    parameters = Column(JSONB, default={})
    priority = Column(Integer, default=0)
    
    # Timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String(255), nullable=False)
    
    # Relationships
    policy = relationship("PolicyDefinition", back_populates="assignments")
    
    # Indexes
    __table_args__ = (
        Index("idx_assignment_policy", "policy_id"),
        Index("idx_assignment_entity", "entity_type", "entity_id"),
        Index("idx_assignment_unique", "policy_id", "entity_type", "entity_id", unique=True),
    )


class PolicyTemplate(Base):
    """Reusable policy templates"""
    __tablename__ = "policy_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)
    
    # Template definition
    template_data = Column(JSONB, nullable=False)
    parameters = Column(JSONB, default={})  # Parameter definitions
    
    # Metadata
    version = Column(String(20), default="1.0.0")
    tags = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_template_category", "category"),
        Index("idx_template_name", "name"),
    )


class PolicySchedule(Base):
    """Scheduled policy evaluations"""
    __tablename__ = "policy_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policy_definitions.id"), nullable=False)
    
    # Schedule target
    entity_type = Column(String(100))
    entity_id = Column(String(255))
    
    # Schedule configuration
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True)
    
    # Execution
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    
    # Context
    context = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_schedule_policy", "policy_id"),
        Index("idx_schedule_active", "is_active"),
        Index("idx_schedule_next_run", "next_run"),
    )


# Access Review Models

class ReviewStatus(enum.Enum):
    """Status of access reviews"""
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class ReviewDecision(enum.Enum):
    """Access review decisions"""
    APPROVED = "approved"
    REVOKED = "revoked"
    MODIFIED = "modified"
    PENDING = "pending"
    ESCALATED = "escalated"


class ReviewScheduleFrequency(enum.Enum):
    """Frequency for scheduled reviews"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class AccessReview(Base):
    """Access review definitions for governance"""
    __tablename__ = "access_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Review configuration
    review_type = Column(String(100), nullable=False, index=True)  # user_access, role_access, application_access
    target_type = Column(String(100), nullable=False)  # user, role, application, resource
    target_criteria = Column(JSONB, default={})  # Criteria for selecting targets
    scope = Column(JSONB, default={})  # Review scope definition
    
    # Review details
    priority = Column(String(50), default="medium")  # low, medium, high, critical
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.DRAFT)
    
    # Dates
    review_start_date = Column(DateTime(timezone=True))
    review_end_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Assignment
    assigned_to = Column(String(255))  # User or group responsible
    
    # Review settings
    auto_approve_threshold = Column(Float)  # Percentage threshold for auto-approval
    require_justification = Column(Boolean, default=True)
    allow_bulk_decisions = Column(Boolean, default=False)
    
    # Configuration
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    items = relationship("AccessReviewItem", back_populates="review", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_review_type", "review_type"),
        Index("idx_review_status", "status"),
        Index("idx_review_dates", "review_start_date", "review_end_date"),
        Index("idx_review_assigned", "assigned_to"),
    )


class AccessReviewItem(Base):
    """Individual items within an access review"""
    __tablename__ = "access_review_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("access_reviews.id"), nullable=False)
    
    # Subject (who has access)
    subject_type = Column(String(100), nullable=False)  # user, service_account, group
    subject_id = Column(String(255), nullable=False)
    
    # Resource (what they have access to)
    resource_type = Column(String(100), nullable=False)  # application, database, folder, role
    resource_id = Column(String(255), nullable=False)
    
    # Access details
    permission_type = Column(String(100))  # read, write, admin, custom
    current_access_level = Column(String(100))
    access_granted_date = Column(DateTime(timezone=True))
    last_used_date = Column(DateTime(timezone=True))
    
    # Review status
    status = Column(String(50), default="pending")  # pending, approved, revoked, modified
    business_justification = Column(Text)
    
    # Assignment
    assigned_to = Column(String(255))  # Reviewer assigned to this item
    
    # Review tracking
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(255))
    
    # Configuration
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    review = relationship("AccessReview", back_populates="items")
    decisions = relationship("AccessReviewDecision", back_populates="item", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_item_review", "review_id"),
        Index("idx_item_subject", "subject_type", "subject_id"),
        Index("idx_item_resource", "resource_type", "resource_id"),
        Index("idx_item_status", "status"),
        Index("idx_item_assigned", "assigned_to"),
    )


class AccessReviewDecision(Base):
    """Review decisions for access items"""
    __tablename__ = "access_review_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("access_review_items.id"), nullable=False)
    
    # Decision details
    reviewer_id = Column(String(255), nullable=False)
    decision = Column(SQLEnum(ReviewDecision), nullable=False)
    justification = Column(Text)
    
    # Action details
    recommended_action = Column(String(100))  # maintain_access, revoke_access, modify_access
    new_access_level = Column(String(100))  # For modified access
    
    # Dates
    review_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))  # When to review again
    
    # Additional context
    comments = Column(Text)
    metadata = Column(JSONB, default={})
    
    # Relationships
    item = relationship("AccessReviewItem", back_populates="decisions")
    
    # Indexes
    __table_args__ = (
        Index("idx_decision_item", "item_id"),
        Index("idx_decision_reviewer", "reviewer_id"),
        Index("idx_decision_type", "decision"),
        Index("idx_decision_date", "review_date"),
    )


class AccessReviewSchedule(Base):
    """Scheduled access reviews"""
    __tablename__ = "access_review_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Review configuration
    review_type = Column(String(100), nullable=False)
    frequency = Column(SQLEnum(ReviewScheduleFrequency), nullable=False)
    cron_expression = Column(String(100))  # For custom frequency
    
    # Target configuration
    target_criteria = Column(JSONB, default={})
    
    # Schedule settings
    auto_start = Column(Boolean, default=True)
    review_duration_days = Column(Integer, default=30)
    template_id = Column(UUID(as_uuid=True), ForeignKey("access_review_templates.id"))
    
    # Execution tracking
    last_run_date = Column(DateTime(timezone=True))
    next_run_date = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    
    # Notification settings
    notification_settings = Column(JSONB, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    template = relationship("AccessReviewTemplate", back_populates="schedules")
    
    # Indexes
    __table_args__ = (
        Index("idx_schedule_type", "review_type"),
        Index("idx_schedule_frequency", "frequency"),
        Index("idx_schedule_active", "is_active"),
        Index("idx_schedule_next_run", "next_run_date"),
    )


class AccessReviewTemplate(Base):
    """Templates for access reviews"""
    __tablename__ = "access_review_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    
    # Template configuration
    review_type = Column(String(100), nullable=False)
    default_settings = Column(JSONB, default={})
    
    # Question templates
    question_template = Column(JSONB, default={})
    
    # Workflow configuration
    approval_workflow = Column(JSONB, default={})
    notification_template = Column(JSONB, default={})
    
    # Template metadata
    is_default = Column(Boolean, default=False)
    tags = Column(JSONB, default=[])
    version = Column(String(20), default="1.0.0")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    schedules = relationship("AccessReviewSchedule", back_populates="template")
    campaigns = relationship("AccessReviewCampaign", back_populates="template")
    
    # Indexes
    __table_args__ = (
        Index("idx_template_type", "review_type"),
        Index("idx_template_default", "is_default"),
        Index("idx_template_name", "name"),
    )


class AccessReviewCampaign(Base):
    """Access review campaigns for coordinated reviews"""
    __tablename__ = "access_review_campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Campaign configuration
    review_type = Column(String(100), nullable=False)
    target_criteria = Column(JSONB, default={})
    
    # Campaign dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Configuration
    auto_generate_reviews = Column(Boolean, default=True)
    notification_settings = Column(JSONB, default={})
    template_id = Column(UUID(as_uuid=True), ForeignKey("access_review_templates.id"))
    
    # Status
    status = Column(String(50), default="planned")  # planned, active, completed, cancelled
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    template = relationship("AccessReviewTemplate", back_populates="campaigns")
    
    # Indexes
    __table_args__ = (
        Index("idx_campaign_type", "review_type"),
        Index("idx_campaign_status", "status"),
        Index("idx_campaign_dates", "start_date", "end_date"),
    )


class AccessReviewResponse(Base):
    """Individual responses to access review items"""
    __tablename__ = "access_review_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("access_review_items.id"), nullable=False)
    
    # Response details
    responder_id = Column(String(255), nullable=False)
    response_type = Column(String(50), nullable=False)  # manager, owner, reviewer
    
    # Responses
    answers = Column(JSONB, default={})  # Question-answer pairs
    overall_recommendation = Column(String(100))
    confidence_level = Column(Float)  # 0.0 to 1.0
    
    # Additional context
    comments = Column(Text)
    attachments = Column(JSONB, default=[])
    
    # Response tracking
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    item = relationship("AccessReviewItem")
    
    # Indexes
    __table_args__ = (
        Index("idx_response_item", "item_id"),
        Index("idx_response_responder", "responder_id"),
        Index("idx_response_type", "response_type"),
        Index("idx_response_date", "submitted_at"),
    )


# Data Lineage Models

class NodeType(enum.Enum):
    """Types of data lineage nodes"""
    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    FILE = "file"
    API = "api"
    SERVICE = "service"
    REPORT = "report"
    DASHBOARD = "dashboard"


class TransformationType(enum.Enum):
    """Types of data transformations"""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    UNION = "union"
    SPLIT = "split"
    MERGE = "merge"
    VALIDATE = "validate"
    CLEANSE = "cleanse"
    ENRICH = "enrich"


class DataLineageNode(Base):
    """Nodes in the data lineage graph"""
    __tablename__ = "data_lineage_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Node identification
    node_type = Column(SQLEnum(NodeType), nullable=False, index=True)
    identifier = Column(String(500), nullable=False, index=True)  # Unique identifier within type
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Schema information
    schema_name = Column(String(100), index=True)
    table_name = Column(String(100), index=True)
    column_name = Column(String(100), index=True)
    data_type = Column(String(100))
    
    # Classification and sensitivity
    is_sensitive = Column(Boolean, default=False, index=True)
    classification_level = Column(String(50), index=True)  # public, internal, confidential, restricted
    
    # Business context
    business_context = Column(JSONB, default={})
    technical_metadata = Column(JSONB, default={})
    compliance_tags = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    source_edges = relationship("DataLineageEdge", foreign_keys="DataLineageEdge.source_node_id", back_populates="source_node")
    target_edges = relationship("DataLineageEdge", foreign_keys="DataLineageEdge.target_node_id", back_populates="target_node")
    
    # Indexes
    __table_args__ = (
        Index("idx_lineage_node_type_identifier", "node_type", "identifier"),
        Index("idx_lineage_node_schema_table", "schema_name", "table_name"),
        Index("idx_lineage_node_sensitive", "is_sensitive"),
        Index("idx_lineage_node_classification", "classification_level"),
    )


class DataLineageEdge(Base):
    """Edges (relationships) in the data lineage graph"""
    __tablename__ = "data_lineage_edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationship
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("data_lineage_nodes.id"), nullable=False)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("data_lineage_nodes.id"), nullable=False)
    relationship_type = Column(String(100), nullable=False, index=True)  # derived_from, feeds_into, transforms_to
    
    # Transformation details
    transformation_logic = Column(Text)  # SQL, code, or description of transformation
    confidence_score = Column(Float, default=1.0)  # Confidence in the relationship (0.0-1.0)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Additional metadata
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    source_node = relationship("DataLineageNode", foreign_keys=[source_node_id], back_populates="source_edges")
    target_node = relationship("DataLineageNode", foreign_keys=[target_node_id], back_populates="target_edges")
    
    # Indexes
    __table_args__ = (
        Index("idx_lineage_edge_source", "source_node_id"),
        Index("idx_lineage_edge_target", "target_node_id"),
        Index("idx_lineage_edge_type", "relationship_type"),
        Index("idx_lineage_edge_active", "is_active"),
        Index("idx_lineage_edge_source_target", "source_node_id", "target_node_id"),
    )


class DataTransformation(Base):
    """Record of data transformations"""
    __tablename__ = "data_transformations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("data_flow_sessions.id"), index=True)
    
    # Transformation details
    transformation_type = Column(SQLEnum(TransformationType), nullable=False, index=True)
    source_nodes = Column(JSONB, default=[])  # List of source node IDs
    target_nodes = Column(JSONB, default=[])  # List of target node IDs
    
    # Transformation logic
    transformation_logic = Column(Text)  # SQL, code, or description
    transformation_code = Column(Text)  # Actual code if available
    execution_context = Column(JSONB, default={})  # Runtime context and parameters
    
    # Quality and performance metrics
    data_quality_metrics = Column(JSONB, default={})
    performance_metrics = Column(JSONB, default={})
    
    # Execution results
    success = Column(Boolean, default=True, index=True)
    error_details = Column(JSONB)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255))
    
    # Relationships
    session = relationship("DataFlowSession", back_populates="transformations")
    
    # Indexes
    __table_args__ = (
        Index("idx_transformation_session", "session_id"),
        Index("idx_transformation_type", "transformation_type"),
        Index("idx_transformation_success", "success"),
        Index("idx_transformation_started", "started_at"),
    )


class DataFlowSession(Base):
    """Sessions for tracking data flow operations"""
    __tablename__ = "data_flow_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session details
    session_name = Column(String(255), nullable=False)
    session_type = Column(String(100), nullable=False, index=True)  # etl, migration, backup, analysis
    description = Column(Text)
    
    # External references
    workflow_id = Column(String(255), index=True)  # Reference to external workflow
    pipeline_id = Column(String(255), index=True)  # Reference to external pipeline
    
    # Execution timing
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    expected_end_time = Column(DateTime(timezone=True))
    
    # Configuration and context
    configuration = Column(JSONB, default={})
    environment = Column(String(100), index=True)  # dev, test, prod
    tags = Column(JSONB, default=[])
    
    # Results
    success = Column(Boolean, index=True)
    summary = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    transformations = relationship("DataTransformation", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_flow_session_type", "session_type"),
        Index("idx_flow_session_workflow", "workflow_id"),
        Index("idx_flow_session_pipeline", "pipeline_id"),
        Index("idx_flow_session_environment", "environment"),
        Index("idx_flow_session_success", "success"),
        Index("idx_flow_session_start", "start_time"),
    )


class DataLineageMetadata(Base):
    """Additional metadata for lineage tracking"""
    __tablename__ = "data_lineage_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference
    node_id = Column(UUID(as_uuid=True), ForeignKey("data_lineage_nodes.id"), nullable=False)
    metadata_type = Column(String(100), nullable=False, index=True)  # schema, statistics, quality, usage
    
    # Metadata content
    metadata_key = Column(String(255), nullable=False, index=True)
    metadata_value = Column(JSONB)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_to = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    
    # Source
    source_system = Column(String(100))
    extraction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255))
    
    # Relationships
    node = relationship("DataLineageNode")
    
    # Indexes
    __table_args__ = (
        Index("idx_lineage_metadata_node", "node_id"),
        Index("idx_lineage_metadata_type", "metadata_type"),
        Index("idx_lineage_metadata_key", "metadata_key"),
        Index("idx_lineage_metadata_active", "is_active"),
        Index("idx_lineage_metadata_valid", "valid_from", "valid_to"),
    )


class DataLineageSnapshot(Base):
    """Point-in-time snapshots of data lineage"""
    __tablename__ = "data_lineage_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Snapshot details
    snapshot_name = Column(String(255), nullable=False)
    snapshot_type = Column(String(100), nullable=False, index=True)  # full, incremental, schema_only
    description = Column(Text)
    
    # Snapshot content
    nodes_snapshot = Column(JSONB)  # Serialized nodes
    edges_snapshot = Column(JSONB)  # Serialized edges
    metadata_snapshot = Column(JSONB)  # Additional metadata
    
    # Statistics
    total_nodes = Column(Integer, default=0)
    total_edges = Column(Integer, default=0)
    sensitive_nodes = Column(Integer, default=0)
    
    # Timestamps
    snapshot_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_lineage_snapshot_type", "snapshot_type"),
        Index("idx_lineage_snapshot_timestamp", "snapshot_timestamp"),
    )


class DataImpactAnalysis(Base):
    """Impact analysis results for data changes"""
    __tablename__ = "data_impact_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Analysis request
    node_ids = Column(JSONB, nullable=False)  # List of node IDs being analyzed
    change_type = Column(String(100), nullable=False, index=True)  # schema_change, data_migration, deletion
    change_description = Column(Text)
    
    # Analysis scope
    analysis_scope = Column(String(100), default="downstream")  # upstream, downstream, both
    max_depth = Column(Integer, default=5)
    include_sensitive_data = Column(Boolean, default=True)
    
    # Analysis results
    impacted_nodes = Column(JSONB, default=[])
    impacted_transformations = Column(JSONB, default=[])
    risk_assessment = Column(JSONB, default={})
    recommendations = Column(JSONB, default=[])
    
    # Analysis metadata
    analysis_duration_ms = Column(Integer)
    analysis_quality_score = Column(Float)  # Confidence in analysis results
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255))
    
    # Indexes
    __table_args__ = (
        Index("idx_impact_analysis_change_type", "change_type"),
        Index("idx_impact_analysis_requested", "requested_at"),
        Index("idx_impact_analysis_completed", "completed_at"),
    )


class RiskSeverity(enum.Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(enum.Enum):
    """Risk assessment status"""
    IDENTIFIED = "identified"
    ANALYZING = "analyzing"
    ASSESSED = "assessed"
    MITIGATING = "mitigating"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class RiskCategory(enum.Enum):
    """Risk categories"""
    DATA_BREACH = "data_breach"
    PRIVACY_VIOLATION = "privacy_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    REPUTATIONAL = "reputational"


class RiskAssessment(Base):
    """Risk assessment records"""
    __tablename__ = "risk_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    risk_category = Column(SQLEnum(RiskCategory), nullable=False, index=True)
    
    # Risk details
    risk_source = Column(String(255))  # What is causing the risk
    affected_assets = Column(JSONB, default=[])  # Assets/systems affected
    affected_data_types = Column(JSONB, default=[])  # Types of data at risk
    potential_impact = Column(Text)  # Description of potential impact
    
    # Assessment scores (1-5 scale)
    likelihood_score = Column(Integer, nullable=False)  # 1=Very Low, 5=Very High
    impact_score = Column(Integer, nullable=False)  # 1=Minimal, 5=Catastrophic
    risk_score = Column(Float, nullable=False)  # Calculated risk score
    severity = Column(SQLEnum(RiskSeverity), nullable=False, index=True)
    
    # Status and ownership
    status = Column(SQLEnum(RiskStatus), nullable=False, default=RiskStatus.IDENTIFIED, index=True)
    risk_owner = Column(String(255))  # Person responsible for the risk
    assigned_to = Column(String(255))  # Person assigned to handle the risk
    
    # Mitigation
    mitigation_strategy = Column(Text)
    mitigation_actions = Column(JSONB, default=[])
    mitigation_deadline = Column(DateTime(timezone=True))
    mitigation_cost_estimate = Column(Float)
    
    # Review and compliance
    last_reviewed_at = Column(DateTime(timezone=True))
    next_review_due = Column(DateTime(timezone=True), index=True)
    review_frequency_days = Column(Integer, default=90)
    
    # Compliance mapping
    regulatory_requirements = Column(JSONB, default=[])  # GDPR, CCPA, etc.
    compliance_controls = Column(JSONB, default=[])
    
    # Additional metadata
    tags = Column(JSONB, default=[])
    attachments = Column(JSONB, default=[])
    comments = Column(JSONB, default=[])
    
    # Timestamps
    identified_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255))
    
    # Relationships
    risk_factors = relationship("RiskFactor", back_populates="risk_assessment", cascade="all, delete-orphan")
    mitigation_plans = relationship("RiskMitigationPlan", back_populates="risk_assessment", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_risk_category_severity", "risk_category", "severity"),
        Index("idx_risk_status", "status"),
        Index("idx_risk_score", "risk_score"),
        Index("idx_risk_next_review", "next_review_due"),
        Index("idx_risk_owner", "risk_owner"),
    )


class RiskFactor(Base):
    """Individual risk factors contributing to a risk assessment"""
    __tablename__ = "risk_factors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False)
    
    # Factor details
    factor_name = Column(String(255), nullable=False)
    factor_description = Column(Text)
    factor_type = Column(String(100))  # vulnerability, threat, environmental, etc.
    
    # Scoring
    likelihood_contribution = Column(Float, default=0.0)  # How much this factor affects likelihood
    impact_contribution = Column(Float, default=0.0)  # How much this factor affects impact
    weight = Column(Float, default=1.0)  # Weight of this factor in overall assessment
    
    # Evidence and sources
    evidence = Column(Text)
    data_sources = Column(JSONB, default=[])
    confidence_level = Column(Float, default=0.5)  # Confidence in this factor (0.0-1.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    risk_assessment = relationship("RiskAssessment", back_populates="risk_factors")
    
    # Indexes
    __table_args__ = (
        Index("idx_risk_factor_assessment", "risk_assessment_id"),
        Index("idx_risk_factor_type", "factor_type"),
    )


class RiskMitigationPlan(Base):
    """Risk mitigation plans and actions"""
    __tablename__ = "risk_mitigation_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False)
    
    # Plan details
    plan_name = Column(String(255), nullable=False)
    plan_description = Column(Text)
    mitigation_type = Column(String(100))  # avoid, transfer, mitigate, accept
    
    # Implementation
    implementation_steps = Column(JSONB, default=[])
    responsible_party = Column(String(255))
    start_date = Column(DateTime(timezone=True))
    target_completion_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))
    
    # Effectiveness
    expected_risk_reduction = Column(Float)  # Expected reduction in risk score
    actual_risk_reduction = Column(Float)  # Actual reduction achieved
    cost = Column(Float)
    effort_hours = Column(Float)
    
    # Status tracking
    status = Column(String(100), default="planned")  # planned, in_progress, completed, cancelled
    progress_percentage = Column(Float, default=0.0)
    success_criteria = Column(Text)
    
    # Dependencies and resources
    dependencies = Column(JSONB, default=[])
    required_resources = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    risk_assessment = relationship("RiskAssessment", back_populates="mitigation_plans")
    
    # Indexes
    __table_args__ = (
        Index("idx_mitigation_plan_assessment", "risk_assessment_id"),
        Index("idx_mitigation_plan_status", "status"),
        Index("idx_mitigation_plan_completion", "target_completion_date"),
    )


class RiskIncident(Base):
    """Records of risk incidents that have materialized"""
    __tablename__ = "risk_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Incident details
    incident_title = Column(String(255), nullable=False, index=True)
    incident_description = Column(Text)
    incident_type = Column(String(100), index=True)  # data_breach, system_failure, etc.
    
    # Related risk
    related_risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"))
    was_risk_predicted = Column(Boolean, default=False)
    
    # Impact assessment
    actual_impact_description = Column(Text)
    financial_impact = Column(Float)
    affected_records_count = Column(Integer)
    affected_individuals_count = Column(Integer)
    downtime_hours = Column(Float)
    
    # Timeline
    incident_detected_at = Column(DateTime(timezone=True))
    incident_occurred_at = Column(DateTime(timezone=True))
    incident_resolved_at = Column(DateTime(timezone=True))
    
    # Response
    response_team = Column(JSONB, default=[])
    response_actions = Column(JSONB, default=[])
    lessons_learned = Column(Text)
    
    # Regulatory reporting
    regulatory_notification_required = Column(Boolean, default=False)
    regulatory_notifications_sent = Column(JSONB, default=[])
    
    # Status
    status = Column(String(100), default="open")  # open, investigating, resolved, closed
    severity = Column(SQLEnum(RiskSeverity), index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    related_risk_assessment = relationship("RiskAssessment")
    
    # Indexes
    __table_args__ = (
        Index("idx_incident_type", "incident_type"),
        Index("idx_incident_status", "status"),
        Index("idx_incident_severity", "severity"),
        Index("idx_incident_detected", "incident_detected_at"),
    )