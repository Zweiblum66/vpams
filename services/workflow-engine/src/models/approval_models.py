"""
Database models for approval workflows
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Boolean, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from typing import Dict, Any
import json

from ..db.base import Base
from .approval_schemas import ApprovalStatus, ApprovalTaskConfig


class ApprovalTask(Base):
    """Approval task database model"""
    __tablename__ = "approval_tasks"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Workflow context
    workflow_instance_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    task_instance_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Status
    status = Column(String(50), default=ApprovalStatus.PENDING.value, nullable=False, index=True)
    
    # Configuration (stored as JSON)
    config_json = Column(JSON, nullable=False)
    
    # Context data
    context_data = Column(JSON, default={})
    attachments = Column(JSON, default=[])
    tags = Column(JSON, default=[])
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Created by
    created_by = Column(String(255), index=True)
    
    # Relationships
    decisions = relationship("ApprovalDecision", back_populates="approval_task", cascade="all, delete-orphan")
    history = relationship("ApprovalHistory", back_populates="approval_task", cascade="all, delete-orphan")
    reminders = relationship("ApprovalReminder", back_populates="approval_task", cascade="all, delete-orphan")
    
    def get_config(self) -> ApprovalTaskConfig:
        """Get approval configuration"""
        return ApprovalTaskConfig(**self.config_json)
    
    def set_config(self, config: ApprovalTaskConfig) -> None:
        """Set approval configuration"""
        self.config_json = config.dict()


class ApprovalDecision(Base):
    """Individual approval decision"""
    __tablename__ = "approval_decisions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    approval_task_id = Column(UUID(as_uuid=True), ForeignKey("approval_tasks.id"), nullable=False, index=True)
    
    # Approver info
    approver_id = Column(String(255), nullable=False, index=True)
    approver_name = Column(String(255))
    approver_email = Column(String(255))
    
    # Decision
    decision = Column(String(50), nullable=False)  # approved, rejected, delegated
    comments = Column(Text)
    
    # Delegation info
    delegated_to = Column(String(255))
    delegation_reason = Column(Text)
    
    # Voting info
    vote_weight = Column(Float, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Relationship
    approval_task = relationship("ApprovalTask", back_populates="decisions")


class ApprovalHistory(Base):
    """Approval history tracking"""
    __tablename__ = "approval_history"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    approval_task_id = Column(UUID(as_uuid=True), ForeignKey("approval_tasks.id"), nullable=False, index=True)
    
    # Action info
    action = Column(String(100), nullable=False)  # created, assigned, approved, rejected, escalated, etc.
    performed_by = Column(String(255), nullable=False)
    
    # Details
    details = Column(JSON, default={})
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    approval_task = relationship("ApprovalTask", back_populates="history")


class ApprovalReminder(Base):
    """Approval reminder tracking"""
    __tablename__ = "approval_reminders"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    approval_task_id = Column(UUID(as_uuid=True), ForeignKey("approval_tasks.id"), nullable=False, index=True)
    
    # Reminder info
    approver_id = Column(String(255), nullable=False, index=True)
    reminder_number = Column(Integer, default=1)
    
    # Timing
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True))
    
    # Status
    is_sent = Column(Boolean, default=False)
    send_attempts = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Notification details
    notification_channel = Column(String(50))  # email, slack, teams, etc.
    notification_id = Column(String(255))  # External notification ID
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Relationship
    approval_task = relationship("ApprovalTask", back_populates="reminders")


class ApprovalTemplate(Base):
    """Pre-defined approval workflow templates"""
    __tablename__ = "approval_templates"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template info
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(100), default="general", index=True)
    
    # Configuration (stored as JSON)
    config_json = Column(JSON, nullable=False)
    
    # UI configuration
    form_schema = Column(JSON)
    display_template = Column(Text)
    
    # Usage
    is_public = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON, default=[])
    created_by = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def get_config(self) -> Dict[str, Any]:
        """Get template configuration"""
        return self.config_json
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set template configuration"""
        self.config_json = config


class ApprovalDelegation(Base):
    """Approval delegation tracking"""
    __tablename__ = "approval_delegations"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Delegation info
    delegator_id = Column(String(255), nullable=False, index=True)
    delegate_id = Column(String(255), nullable=False, index=True)
    
    # Scope
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Filters
    approval_types = Column(JSON)  # List of approval types to delegate
    departments = Column(JSON)  # List of departments
    max_amount = Column(Float)  # Maximum amount for expense approvals
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Reason
    reason = Column(Text)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApprovalMetrics(Base):
    """Approval metrics and analytics"""
    __tablename__ = "approval_metrics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric scope
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)  # daily, weekly, monthly
    department = Column(String(100), index=True)
    user_id = Column(String(255), index=True)
    
    # Counts
    total_requests = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    cancelled_count = Column(Integer, default=0)
    escalated_count = Column(Integer, default=0)
    
    # Timing metrics
    avg_response_time_hours = Column(Float)
    min_response_time_hours = Column(Float)
    max_response_time_hours = Column(Float)
    
    # SLA metrics
    sla_met_count = Column(Integer, default=0)
    sla_missed_count = Column(Integer, default=0)
    
    # Additional metrics
    delegation_count = Column(Integer, default=0)
    auto_approval_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)