"""
Approval workflow schemas for Workflow Engine Service
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid


class ApprovalStatus(str, Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ApprovalType(str, Enum):
    """Types of approval workflows"""
    SINGLE = "single"  # Single approver
    SEQUENTIAL = "sequential"  # Multiple approvers in sequence
    PARALLEL = "parallel"  # Multiple approvers in parallel
    VOTING = "voting"  # Voting-based approval
    HIERARCHICAL = "hierarchical"  # Based on organizational hierarchy
    CONDITIONAL = "conditional"  # Based on conditions


class EscalationType(str, Enum):
    """Types of escalation"""
    TIME_BASED = "time_based"  # Escalate after timeout
    CONDITION_BASED = "condition_based"  # Escalate based on conditions
    REJECTION_BASED = "rejection_based"  # Escalate on rejection
    MANUAL = "manual"  # Manual escalation


class VotingStrategy(str, Enum):
    """Voting strategies for approval"""
    UNANIMOUS = "unanimous"  # All must approve
    MAJORITY = "majority"  # More than 50% must approve
    WEIGHTED = "weighted"  # Weighted voting
    CUSTOM_THRESHOLD = "custom_threshold"  # Custom percentage threshold


class ApproverType(str, Enum):
    """Types of approvers"""
    USER = "user"
    ROLE = "role"
    GROUP = "group"
    DYNAMIC = "dynamic"  # Determined at runtime
    EXTERNAL = "external"  # External system/service


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ApproverConfig(BaseModel):
    """Configuration for an approver"""
    approver_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approver_type: ApproverType
    identifier: str  # user_id, role_name, group_id, etc.
    name: str
    email: Optional[str] = None
    
    # Approval configuration
    is_required: bool = True
    can_delegate: bool = False
    auto_approve_conditions: Optional[List[Dict[str, Any]]] = None
    
    # Voting configuration (for voting-based approvals)
    vote_weight: float = 1.0
    
    # Time constraints
    response_deadline_hours: Optional[int] = None
    reminder_intervals_hours: Optional[List[int]] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}


class EscalationRule(BaseModel):
    """Escalation rule configuration"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    escalation_type: EscalationType
    
    # Escalation conditions
    trigger_after_hours: Optional[int] = None  # For time-based escalation
    trigger_conditions: Optional[List[Dict[str, Any]]] = None  # For condition-based
    rejection_count: Optional[int] = None  # For rejection-based escalation
    
    # Escalation action
    escalation_action: str = "add_approver"  # add_approver, replace_approver, notify, auto_approve, cancel
    
    # Escalation target
    escalate_to: Optional[ApproverConfig] = None
    
    # Notification settings
    notify_original_approvers: bool = True
    notify_requestor: bool = True
    
    # Escalation message
    escalation_message: Optional[str] = None
    
    # Whether this escalation can be further escalated
    can_re_escalate: bool = False
    max_escalation_levels: int = 3


class ApprovalTaskConfig(BaseModel):
    """Configuration for approval task"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approval_type: ApprovalType
    
    # Basic information
    title: str
    description: str
    context_data: Dict[str, Any] = {}  # Data to show to approvers
    
    # Approvers
    approvers: List[ApproverConfig]
    
    # Approval rules
    voting_strategy: Optional[VotingStrategy] = None  # For voting-based approvals
    approval_threshold: Optional[float] = None  # For custom threshold
    allow_partial_approval: bool = False
    
    # Time constraints
    approval_deadline_hours: Optional[int] = None
    auto_approve_on_timeout: bool = False
    auto_reject_on_timeout: bool = False
    
    # Escalation rules
    escalation_rules: List[EscalationRule] = []
    
    # Notification settings
    send_initial_notification: bool = True
    send_reminder_notifications: bool = True
    reminder_intervals_hours: List[int] = [24, 48]  # Default reminders
    
    # UI customization
    approval_form_schema: Optional[Dict[str, Any]] = None  # JSON schema for custom form
    display_template: Optional[str] = None  # Template for approval UI
    
    # Actions
    on_approve_actions: List[Dict[str, Any]] = []
    on_reject_actions: List[Dict[str, Any]] = []
    on_timeout_actions: List[Dict[str, Any]] = []
    
    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    
    @validator('voting_strategy')
    def validate_voting_strategy(cls, v, values):
        approval_type = values.get('approval_type')
        if v and approval_type not in [ApprovalType.PARALLEL, ApprovalType.VOTING]:
            raise ValueError("Voting strategy only applies to parallel or voting approval types")
        return v


class ApprovalRequest(BaseModel):
    """Approval request model"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_instance_id: str
    task_instance_id: str
    
    # Request details
    title: str
    description: str
    requestor_id: str
    requestor_name: str
    requestor_email: Optional[str] = None
    
    # Approval configuration
    approval_config: ApprovalTaskConfig
    
    # Current status
    status: ApprovalStatus = ApprovalStatus.PENDING
    current_level: int = 0  # For hierarchical/sequential approvals
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Context data for approvers
    context_data: Dict[str, Any] = {}
    attachments: List[Dict[str, Any]] = []  # File references
    
    # Results
    approval_decisions: List["ApprovalDecision"] = []
    final_decision: Optional[ApprovalStatus] = None
    final_comments: Optional[str] = None
    
    # Escalation tracking
    escalation_history: List[Dict[str, Any]] = []
    current_escalation_level: int = 0
    
    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class ApprovalDecision(BaseModel):
    """Individual approval decision"""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    approver_id: str
    approver_name: str
    approver_type: ApproverType
    
    # Decision details
    decision: ApprovalStatus
    comments: Optional[str] = None
    conditions_met: Optional[List[str]] = None  # For conditional approvals
    
    # Voting details (if applicable)
    vote_weight: float = 1.0
    
    # Delegation (if applicable)
    delegated_from: Optional[str] = None
    delegation_reason: Optional[str] = None
    
    # Timing
    assigned_at: datetime
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    response_time_hours: Optional[float] = None
    
    # Form data (if custom form was used)
    form_data: Optional[Dict[str, Any]] = None
    
    # Attachments
    attachments: List[Dict[str, Any]] = []
    
    # Metadata
    metadata: Dict[str, Any] = {}


class ApprovalNotification(BaseModel):
    """Approval notification model"""
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    
    # Notification details
    notification_type: str  # "new_request", "reminder", "escalation", "decision", etc.
    recipient_id: str
    recipient_email: str
    
    # Content
    subject: str
    body: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    
    # Status
    is_sent: bool = False
    send_attempts: int = 0
    last_error: Optional[str] = None
    
    # Actions
    action_links: List[Dict[str, str]] = []  # Links to approval UI
    
    # Metadata
    metadata: Dict[str, Any] = {}


class ApprovalDashboard(BaseModel):
    """Approval dashboard data"""
    user_id: str
    
    # Pending approvals
    pending_approvals: List[ApprovalRequest] = []
    pending_count: int = 0
    
    # Recent decisions
    recent_decisions: List[ApprovalDecision] = []
    
    # Statistics
    total_requests_received: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    average_response_time_hours: float = 0.0
    
    # By status
    requests_by_status: Dict[ApprovalStatus, int] = {}
    
    # By priority
    requests_by_priority: Dict[str, int] = {}
    
    # Delegated approvals
    delegated_to_others: int = 0
    received_delegations: int = 0
    
    # Time-based stats
    requests_this_week: int = 0
    requests_this_month: int = 0
    
    # Upcoming deadlines
    upcoming_deadlines: List[Dict[str, Any]] = []


class ApprovalTemplate(BaseModel):
    """Pre-defined approval workflow template"""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str = "general"
    
    # Template configuration
    approval_type: ApprovalType
    default_approvers: List[ApproverConfig] = []
    default_voting_strategy: Optional[VotingStrategy] = None
    default_escalation_rules: List[EscalationRule] = []
    
    # Default time constraints
    default_deadline_hours: Optional[int] = None
    default_reminder_intervals: List[int] = [24, 48]
    
    # UI configuration
    default_form_schema: Optional[Dict[str, Any]] = None
    default_display_template: Optional[str] = None
    
    # Usage
    is_public: bool = True
    usage_count: int = 0
    
    # Metadata
    tags: List[str] = []
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response schemas

class CreateApprovalRequest(BaseModel):
    """Request to create a new approval"""
    workflow_instance_id: str
    task_instance_id: str
    title: str
    description: str
    approval_config: ApprovalTaskConfig
    context_data: Dict[str, Any] = {}
    attachments: List[Dict[str, Any]] = []
    tags: List[str] = []


class UpdateApprovalDecision(BaseModel):
    """Request to update an approval decision"""
    decision: ApprovalStatus
    comments: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = []


class DelegateApprovalRequest(BaseModel):
    """Request to delegate an approval"""
    delegate_to: ApproverConfig
    delegation_reason: str
    retain_visibility: bool = True


class ApprovalSearchRequest(BaseModel):
    """Request to search approvals"""
    status: Optional[List[ApprovalStatus]] = None
    approver_id: Optional[str] = None
    requestor_id: Optional[str] = None
    workflow_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    deadline_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


class ApprovalResponse(BaseModel):
    """Approval response"""
    request_id: str
    title: str
    description: str
    status: ApprovalStatus
    requestor_name: str
    created_at: datetime
    deadline_at: Optional[datetime]
    approval_progress: float  # 0.0 to 1.0
    pending_approvers: List[str]
    completed_approvers: List[str]
    
    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    """List of approvals response"""
    approvals: List[ApprovalResponse]
    total: int
    page: int
    page_size: int


# Update forward references
ApprovalRequest.model_rebuild()