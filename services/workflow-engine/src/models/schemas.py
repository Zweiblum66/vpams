"""
Pydantic schemas for Workflow Engine Service
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TriggerType(str, Enum):
    """Workflow trigger types"""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"
    API = "api"
    CONDITION = "condition"


class TaskType(str, Enum):
    """Workflow task types"""
    # Media Processing
    TRANSCODE = "transcode"
    GENERATE_PROXY = "generate_proxy"
    EXTRACT_METADATA = "extract_metadata"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    
    # File Operations
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    DELETE_FILE = "delete_file"
    ARCHIVE_FILE = "archive_file"
    
    # Asset Operations
    CREATE_ASSET = "create_asset"
    UPDATE_ASSET = "update_asset"
    TAG_ASSET = "tag_asset"
    PUBLISH_ASSET = "publish_asset"
    
    # Notification
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    WEBHOOK_CALL = "webhook_call"
    
    # Control Flow
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    WAIT = "wait"
    
    # Integration
    API_CALL = "api_call"
    SCRIPT_EXECUTION = "script_execution"
    APPROVAL = "approval"
    
    # AI/ML
    AUTO_TAG = "auto_tag"
    TRANSCRIBE = "transcribe"
    DETECT_OBJECTS = "detect_objects"
    ANALYZE_CONTENT = "analyze_content"


class ConditionOperator(str, Enum):
    """Condition operators for workflow logic"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class WorkflowPriority(str, Enum):
    """Workflow execution priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# Task Configuration Schemas

class TaskConfig(BaseModel):
    """Base task configuration"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    name: str
    description: Optional[str] = None
    timeout: Optional[int] = Field(default=300, description="Task timeout in seconds")
    retry_count: int = Field(default=3, ge=0)
    retry_delay: int = Field(default=60, ge=0)
    continue_on_error: bool = False
    parameters: Dict[str, Any] = {}


class ConditionConfig(BaseModel):
    """Condition configuration for conditional tasks"""
    field: str
    operator: ConditionOperator
    value: Any
    logical_operator: Optional[str] = Field(default="and", pattern="^(and|or)$")


class ConditionalTask(TaskConfig):
    """Conditional task configuration"""
    conditions: List[ConditionConfig]
    then_tasks: List["TaskConfig"]
    else_tasks: Optional[List["TaskConfig"]] = []


class ParallelTask(TaskConfig):
    """Parallel task configuration"""
    tasks: List[TaskConfig]
    wait_for_all: bool = True
    max_concurrent: Optional[int] = None


class LoopTask(TaskConfig):
    """Loop task configuration"""
    items_source: str  # Variable name or expression
    item_variable: str = "item"
    tasks: List[TaskConfig]
    max_iterations: Optional[int] = None
    parallel_execution: bool = False


# Workflow Definition Schemas

class WorkflowTrigger(BaseModel):
    """Workflow trigger configuration"""
    trigger_type: TriggerType
    enabled: bool = True
    config: Dict[str, Any] = {}
    
    @validator('config')
    def validate_config(cls, v, values):
        trigger_type = values.get('trigger_type')
        if trigger_type == TriggerType.SCHEDULE:
            if 'cron' not in v and 'interval' not in v:
                raise ValueError("Schedule trigger requires 'cron' or 'interval' in config")
        elif trigger_type == TriggerType.EVENT:
            if 'event_type' not in v:
                raise ValueError("Event trigger requires 'event_type' in config")
        elif trigger_type == TriggerType.FILE_WATCH:
            if 'path' not in v:
                raise ValueError("File watch trigger requires 'path' in config")
        return v


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    enabled: bool = True
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    
    # Triggers
    triggers: List[WorkflowTrigger] = []
    
    # Variables
    variables: Dict[str, Any] = {}
    input_schema: Optional[Dict[str, Any]] = None
    
    # Tasks
    tasks: List[TaskConfig] = []
    
    # Configuration
    timeout: Optional[int] = Field(default=3600, description="Workflow timeout in seconds")
    max_retries: int = Field(default=3, ge=0)
    retry_delay: int = Field(default=300, ge=0)
    
    # Metadata
    tags: List[str] = []
    category: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Workflow Execution Schemas

class WorkflowInstance(BaseModel):
    """Workflow execution instance"""
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    workflow_name: str
    workflow_version: str
    
    status: WorkflowStatus = WorkflowStatus.PENDING
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    
    # Execution context
    input_data: Dict[str, Any] = {}
    variables: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    
    # Trigger information
    triggered_by: str  # user_id, system, trigger_id
    trigger_type: TriggerType
    trigger_data: Dict[str, Any] = {}
    
    # Timing
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Execution details
    current_task_id: Optional[str] = None
    execution_path: List[str] = []  # Task IDs in execution order
    retry_count: int = 0
    error_message: Optional[str] = None
    
    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class TaskInstance(BaseModel):
    """Task execution instance"""
    task_instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_instance_id: str
    task_id: str
    task_type: TaskType
    task_name: str
    
    status: TaskStatus = TaskStatus.PENDING
    
    # Execution details
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    error_message: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Retry information
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    
    # Resource usage
    resource_usage: Dict[str, Any] = {}


# API Request/Response Schemas

class WorkflowCreateRequest(BaseModel):
    """Request to create a new workflow"""
    name: str
    description: Optional[str] = None
    enabled: bool = True
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    triggers: List[WorkflowTrigger] = []
    variables: Dict[str, Any] = {}
    tasks: List[TaskConfig] = []
    tags: List[str] = []
    category: Optional[str] = None


class WorkflowUpdateRequest(BaseModel):
    """Request to update a workflow"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[WorkflowPriority] = None
    triggers: Optional[List[WorkflowTrigger]] = None
    variables: Optional[Dict[str, Any]] = None
    tasks: Optional[List[TaskConfig]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    version: Optional[str] = None


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    workflow_id: str
    input_data: Dict[str, Any] = {}
    priority: Optional[WorkflowPriority] = None
    scheduled_at: Optional[datetime] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    """Workflow response"""
    workflow_id: str
    name: str
    description: Optional[str]
    version: str
    enabled: bool
    priority: WorkflowPriority
    triggers: List[WorkflowTrigger]
    variables: Dict[str, Any]
    task_count: int
    tags: List[str]
    category: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowInstanceResponse(BaseModel):
    """Workflow instance response"""
    instance_id: str
    workflow_id: str
    workflow_name: str
    workflow_version: str
    status: WorkflowStatus
    priority: WorkflowPriority
    triggered_by: str
    trigger_type: TriggerType
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    current_task: Optional[str]
    progress: float  # 0.0 to 1.0
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """List of workflows response"""
    workflows: List[WorkflowResponse]
    total: int
    page: int
    page_size: int


class WorkflowInstanceListResponse(BaseModel):
    """List of workflow instances response"""
    instances: List[WorkflowInstanceResponse]
    total: int
    page: int
    page_size: int


class WorkflowStats(BaseModel):
    """Workflow statistics"""
    total_workflows: int
    active_workflows: int
    total_executions: int
    running_executions: int
    completed_executions: int
    failed_executions: int
    average_duration_seconds: float
    success_rate: float
    
    # By status
    executions_by_status: Dict[WorkflowStatus, int]
    
    # By priority
    executions_by_priority: Dict[WorkflowPriority, int]
    
    # By trigger type
    executions_by_trigger: Dict[TriggerType, int]
    
    # Time-based stats
    executions_today: int
    executions_this_week: int
    executions_this_month: int
    
    # Performance
    average_task_duration: float
    most_used_workflows: List[Dict[str, Any]]
    most_failed_workflows: List[Dict[str, Any]]


# Visual Workflow Designer Schemas

class NodeType(str, Enum):
    """Node types for visual workflow designer"""
    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    WEBHOOK = "webhook"
    TIMER = "timer"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class ConnectionType(str, Enum):
    """Connection types for visual workflow designer"""
    SUCCESS = "success"
    FAILURE = "failure"
    CONDITIONAL = "conditional"
    ALWAYS = "always"
    LOOP = "loop"
    PARALLEL = "parallel"


class ValidationResult(BaseModel):
    """Validation result for workflow designer"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    validation_time: float
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowDesignerNode(BaseModel):
    """Visual workflow designer node"""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType
    task_type: Optional[TaskType] = None
    name: str
    description: Optional[str] = None
    
    # Visual properties
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    size: Dict[str, float] = Field(default_factory=lambda: {"width": 200, "height": 60})
    color: Optional[str] = None
    icon: Optional[str] = None
    
    # Configuration
    parameters: Dict[str, Any] = {}
    timeout: Optional[int] = Field(default=300, description="Node timeout in seconds")
    retry_count: int = Field(default=3, ge=0)
    retry_delay: int = Field(default=60, ge=0)
    continue_on_error: bool = False
    
    # Connections
    input_ports: List[str] = []
    output_ports: List[str] = []
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerConnection(BaseModel):
    """Visual workflow designer connection"""
    connection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str
    target_node_id: str
    source_port: str = "output"
    target_port: str = "input"
    connection_type: ConnectionType = ConnectionType.SUCCESS
    
    # Visual properties
    points: List[Dict[str, float]] = []  # Bezier curve points
    color: Optional[str] = None
    style: Optional[str] = None  # "solid", "dashed", "dotted"
    
    # Conditional logic
    condition: Optional[str] = None  # Expression for conditional connections
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerLayout(BaseModel):
    """Visual workflow designer layout"""
    canvas_size: Dict[str, float] = Field(default_factory=lambda: {"width": 2000, "height": 1500})
    zoom_level: float = Field(default=1.0, ge=0.1, le=5.0)
    pan_offset: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    grid_size: int = Field(default=20, ge=10, le=100)
    snap_to_grid: bool = True
    show_grid: bool = True
    auto_layout: bool = False
    layout_direction: str = Field(default="horizontal", pattern="^(horizontal|vertical)$")


class WorkflowDesignerState(BaseModel):
    """Complete visual workflow designer state"""
    workflow_id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    
    # Visual elements
    nodes: List[WorkflowDesignerNode] = []
    connections: List[WorkflowDesignerConnection] = []
    layout: WorkflowDesignerLayout = Field(default_factory=WorkflowDesignerLayout)
    
    # Workflow properties
    variables: Dict[str, Any] = {}
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    
    # Validation
    validation_status: Optional[ValidationResult] = None
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerValidation(BaseModel):
    """Workflow designer validation result"""
    workflow_id: str
    is_valid: bool
    errors: List[Dict[str, Any]] = []  # Error details with node/connection references
    warnings: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []
    
    # Validation details
    node_validations: Dict[str, ValidationResult] = {}
    connection_validations: Dict[str, ValidationResult] = {}
    flow_validation: ValidationResult
    
    # Performance metrics
    validation_time: float
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerExport(BaseModel):
    """Workflow designer export format"""
    format: str = "json"  # json, yaml, xml, executable
    version: str = "1.0.0"
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Content
    workflow: WorkflowDesignerState
    metadata: Dict[str, Any] = {}
    
    # Export options
    include_layout: bool = True
    include_metadata: bool = True
    minified: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerImport(BaseModel):
    """Workflow designer import format"""
    format: str = "json"
    content: Union[str, Dict[str, Any]]
    
    # Import options
    preserve_ids: bool = False
    merge_with_existing: bool = False
    validate_on_import: bool = True
    
    # Metadata
    source: Optional[str] = None
    imported_by: Optional[str] = None


class WorkflowDesignerTemplate(BaseModel):
    """Workflow designer template"""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    category: str = "general"
    tags: List[str] = []
    
    # Template content
    workflow_state: WorkflowDesignerState
    
    # Template properties
    is_public: bool = True
    is_featured: bool = False
    usage_count: int = 0
    rating: float = 0.0
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowDesignerPreview(BaseModel):
    """Workflow designer preview result"""
    workflow_id: str
    preview_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Preview content
    execution_plan: List[Dict[str, Any]] = []
    estimated_duration: float = 0.0
    required_resources: Dict[str, Any] = {}
    
    # Sample data results
    sample_outputs: Dict[str, Any] = {}
    execution_steps: List[Dict[str, Any]] = []
    
    # Preview metadata
    preview_time: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NodeLibraryItem(BaseModel):
    """Node library item for workflow designer"""
    node_type: str
    name: str
    description: str
    category: str
    
    # Visual properties
    icon: Optional[str] = None
    color: Optional[str] = None
    
    # Port configuration
    input_ports: List[Dict[str, Any]] = []
    output_ports: List[Dict[str, Any]] = []
    
    # Parameter schema
    parameters: Dict[str, Any] = {}
    configuration_schema: Dict[str, Any] = {}
    
    # Documentation
    examples: List[Dict[str, Any]] = []
    documentation: Optional[str] = None
    
    # Metadata
    version: str = "1.0.0"
    dependencies: List[str] = []
    is_deprecated: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Update forward references
ConditionalTask.model_rebuild()
ParallelTask.model_rebuild()
LoopTask.model_rebuild()