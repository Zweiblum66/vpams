"""
SQLAlchemy models for Workflow Engine Service
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, JSON, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base
from ..models.schemas import WorkflowStatus, TaskStatus, TriggerType, TaskType, WorkflowPriority


class WorkflowDefinition(Base):
    """Workflow definition model"""
    __tablename__ = "workflow_definitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    version = Column(String(50), nullable=False, default="1.0.0")
    enabled = Column(Boolean, default=True, index=True)
    priority = Column(SQLEnum(WorkflowPriority), default=WorkflowPriority.NORMAL, index=True)
    
    # JSON fields for complex data
    triggers = Column(JSON, default=list)
    variables = Column(JSON, default=dict)
    input_schema = Column(JSON)
    tasks = Column(JSON, nullable=False, default=list)
    
    # Configuration
    timeout = Column(Integer, default=3600)
    max_retries = Column(Integer, default=3)
    retry_delay = Column(Integer, default=300)
    
    # Designer state (for visual workflow designer)
    designer_state = Column(JSON)
    
    # Metadata
    tags = Column(JSON, default=list)
    category = Column(String(100), index=True)
    created_by = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Soft delete
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    instances = relationship("WorkflowInstance", back_populates="workflow_definition")
    
    __table_args__ = (
        Index('idx_workflow_category_enabled', 'category', 'enabled'),
        Index('idx_workflow_created_by_enabled', 'created_by', 'enabled'),
    )


class WorkflowInstance(Base):
    """Workflow execution instance model"""
    __tablename__ = "workflow_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)
    workflow_definition_id = Column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"))
    workflow_name = Column(String(255), nullable=False)
    workflow_version = Column(String(50), nullable=False)
    
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False, index=True)
    priority = Column(SQLEnum(WorkflowPriority), default=WorkflowPriority.NORMAL, index=True)
    
    # Execution context
    input_data = Column(JSON, default=dict)
    variables = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    
    # Trigger information
    triggered_by = Column(String(255), nullable=False, index=True)
    trigger_type = Column(SQLEnum(TriggerType), nullable=False, index=True)
    trigger_data = Column(JSON, default=dict)
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), index=True)
    started_at = Column(DateTime(timezone=True), index=True)
    completed_at = Column(DateTime(timezone=True), index=True)
    
    # Execution details
    current_task_id = Column(String(255))
    execution_path = Column(JSON, default=list)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workflow_definition = relationship("WorkflowDefinition", back_populates="instances")
    task_instances = relationship("TaskInstance", back_populates="workflow_instance", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_instance_status_priority', 'status', 'priority'),
        Index('idx_instance_workflow_status', 'workflow_id', 'status'),
        Index('idx_instance_triggered_by_status', 'triggered_by', 'status'),
        Index('idx_instance_scheduled_status', 'scheduled_at', 'status'),
        Index('idx_instance_created_status', 'created_at', 'status'),
    )


class TaskInstance(Base):
    """Task execution instance model"""
    __tablename__ = "task_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_instance_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_instance_id = Column(UUID(as_uuid=True), ForeignKey("workflow_instances.id"), nullable=False)
    task_id = Column(String(255), nullable=False, index=True)
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True)
    task_name = Column(String(255), nullable=False)
    
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    
    # Execution details
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Retry information
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True))
    
    # Resource usage
    resource_usage = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workflow_instance = relationship("WorkflowInstance", back_populates="task_instances")
    
    __table_args__ = (
        Index('idx_task_workflow_status', 'workflow_instance_id', 'status'),
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_task_created_status', 'created_at', 'status'),
    )


class WorkflowTrigger(Base):
    """Workflow trigger configuration model"""
    __tablename__ = "workflow_triggers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(255), nullable=False, index=True)
    trigger_type = Column(SQLEnum(TriggerType), nullable=False, index=True)
    enabled = Column(Boolean, default=True, index=True)
    config = Column(JSON, nullable=False, default=dict)
    
    # Last execution info
    last_triggered_at = Column(DateTime(timezone=True))
    last_instance_id = Column(String(255))
    trigger_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_trigger_workflow_enabled', 'workflow_id', 'enabled'),
        Index('idx_trigger_type_enabled', 'trigger_type', 'enabled'),
    )


class WorkflowSchedule(Base):
    """Workflow schedule model for cron-based triggers"""
    __tablename__ = "workflow_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(255), nullable=False, index=True)
    trigger_id = Column(UUID(as_uuid=True), ForeignKey("workflow_triggers.id"))
    
    # Schedule configuration
    cron_expression = Column(String(255))
    timezone = Column(String(50), default="UTC")
    
    # Next execution
    next_run_at = Column(DateTime(timezone=True), index=True)
    
    # Status
    enabled = Column(Boolean, default=True, index=True)
    paused = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_schedule_next_run_enabled', 'next_run_at', 'enabled'),
    )


class WorkflowEvent(Base):
    """Workflow event tracking model"""
    __tablename__ = "workflow_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_instance_id = Column(String(255), nullable=False, index=True)
    task_instance_id = Column(String(255), index=True)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # started, completed, failed, etc.
    event_data = Column(JSON, default=dict)
    
    # User/System info
    triggered_by = Column(String(255))
    
    # Timestamp
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_event_instance_type', 'workflow_instance_id', 'event_type'),
        Index('idx_event_occurred_type', 'occurred_at', 'event_type'),
    )


class WorkflowTemplate(Base):
    """Pre-defined workflow templates"""
    __tablename__ = "workflow_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    
    # Template definition (includes all workflow configuration)
    definition = Column(JSON, nullable=False)
    default_priority = Column(SQLEnum(WorkflowPriority), default=WorkflowPriority.NORMAL)
    
    # Template configuration extracted from definition
    triggers = Column(JSON, default=list)
    variables = Column(JSON, default=dict)
    input_schema = Column(JSON)
    tasks = Column(JSON, default=list)
    timeout = Column(Integer, default=3600)
    max_retries = Column(Integer, default=3)
    retry_delay = Column(Integer, default=300)
    
    # Designer state (for visual workflow designer templates)
    designer_state = Column(JSON)
    
    # Metadata
    tags = Column(JSON, default=list)
    is_public = Column(Boolean, default=True, index=True)
    created_by = Column(String(255))
    
    # Usage stats
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_template_category_public', 'category', 'is_public'),
    )


class ApprovalRequest(Base):
    """Approval request model"""
    __tablename__ = "approval_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_instance_id = Column(String(255), nullable=False, index=True)
    task_instance_id = Column(String(255), nullable=False, index=True)
    
    # Request details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    requestor_id = Column(String(255), nullable=False, index=True)
    requestor_name = Column(String(255), nullable=False)
    requestor_email = Column(String(255))
    
    # Approval configuration (JSON)
    approval_config = Column(JSON, nullable=False)
    
    # Status
    status = Column(String(50), nullable=False, index=True)  # ApprovalStatus enum
    current_level = Column(Integer, default=0)
    
    # Timing
    deadline_at = Column(DateTime(timezone=True), index=True)
    completed_at = Column(DateTime(timezone=True))
    
    # Context and results
    context_data = Column(JSON, default=dict)
    attachments = Column(JSON, default=list)
    final_decision = Column(String(50))  # ApprovalStatus enum
    final_comments = Column(Text)
    
    # Escalation tracking
    escalation_history = Column(JSON, default=list)
    current_escalation_level = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    decisions = relationship("ApprovalDecision", back_populates="approval_request", cascade="all, delete-orphan")
    notifications = relationship("ApprovalNotification", back_populates="approval_request", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_approval_status_requestor', 'status', 'requestor_id'),
        Index('idx_approval_deadline_status', 'deadline_at', 'status'),
        Index('idx_approval_created_status', 'created_at', 'status'),
    )


class ApprovalDecision(Base):
    """Individual approval decision model"""
    __tablename__ = "approval_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(String(255), unique=True, nullable=False, index=True)
    request_id = Column(String(255), ForeignKey("approval_requests.request_id"), nullable=False, index=True)
    approver_id = Column(String(255), nullable=False, index=True)
    approver_name = Column(String(255), nullable=False)
    approver_type = Column(String(50), nullable=False)  # ApproverType enum
    
    # Decision details
    decision = Column(String(50), nullable=False)  # ApprovalStatus enum
    comments = Column(Text)
    conditions_met = Column(JSON, default=list)
    
    # Voting details
    vote_weight = Column(Float, default=1.0)
    
    # Delegation info
    delegated_from = Column(String(255))
    delegation_reason = Column(Text)
    
    # Timing
    assigned_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True), server_default=func.now())
    response_time_hours = Column(Float)
    
    # Form data
    form_data = Column(JSON)
    attachments = Column(JSON, default=list)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="decisions")
    
    __table_args__ = (
        Index('idx_decision_request_approver', 'request_id', 'approver_id'),
        Index('idx_decision_approver_created', 'approver_id', 'created_at'),
    )


class ApprovalNotification(Base):
    """Approval notification model"""
    __tablename__ = "approval_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(String(255), unique=True, nullable=False, index=True)
    request_id = Column(String(255), ForeignKey("approval_requests.request_id"), nullable=False, index=True)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # new_request, reminder, etc.
    recipient_id = Column(String(255), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)
    
    # Content
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Timing
    scheduled_for = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    
    # Status
    is_sent = Column(Boolean, default=False, index=True)
    send_attempts = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Actions
    action_links = Column(JSON, default=list)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="notifications")
    
    __table_args__ = (
        Index('idx_notification_recipient_sent', 'recipient_id', 'is_sent'),
        Index('idx_notification_scheduled_sent', 'scheduled_for', 'is_sent'),
    )