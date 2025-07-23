"""Pydantic schemas for Broadcast Integration Service"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID
import enum

from ..db.models import RundownStatus, StoryStatus, ApprovalStatus, GraphicsType


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common fields"""
    class Config:
        from_attributes = True
        use_enum_values = True


# Rundown schemas
class RundownBase(BaseSchema):
    """Base rundown schema"""
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    show_date: datetime
    duration_seconds: int = Field(default=0, ge=0)
    
    # Optional fields
    mos_ro_id: Optional[str] = None
    newsroom_system: Optional[str] = None
    newsroom_id: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    producer_id: Optional[UUID] = None
    director_id: Optional[UUID] = None
    studio: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class RundownCreate(RundownBase):
    """Schema for creating rundown"""
    pass


class RundownUpdate(BaseSchema):
    """Schema for updating rundown"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    show_date: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    status: Optional[RundownStatus] = None
    locked: Optional[bool] = None
    
    # Optional updates
    mos_ro_id: Optional[str] = None
    newsroom_system: Optional[str] = None
    newsroom_id: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    producer_id: Optional[UUID] = None
    director_id: Optional[UUID] = None
    studio: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class RundownResponse(RundownBase):
    """Rundown response schema"""
    id: UUID
    status: RundownStatus
    locked: bool
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Include story count
    story_count: Optional[int] = None


class RundownWithStories(RundownResponse):
    """Rundown with stories included"""
    stories: List["StoryResponse"]


# Story schemas
class StoryBase(BaseSchema):
    """Base story schema"""
    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    duration_seconds: int = Field(default=0, ge=0)
    position: int = Field(..., ge=0)
    
    # Optional fields
    mos_story_id: Optional[str] = None
    newsroom_id: Optional[str] = None
    script_id: Optional[UUID] = None
    media_assets: List[str] = Field(default_factory=list)
    reporter_id: Optional[UUID] = None
    camera_positions: List[Dict[str, Any]] = Field(default_factory=list)
    backtime: Optional[float] = None
    fronttime: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class StoryCreate(StoryBase):
    """Schema for creating story"""
    rundown_id: UUID


class StoryUpdate(BaseSchema):
    """Schema for updating story"""
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    duration_seconds: Optional[int] = Field(None, ge=0)
    position: Optional[int] = Field(None, ge=0)
    status: Optional[StoryStatus] = None
    
    # Optional updates
    mos_story_id: Optional[str] = None
    newsroom_id: Optional[str] = None
    script_id: Optional[UUID] = None
    media_assets: Optional[List[str]] = None
    reporter_id: Optional[UUID] = None
    camera_positions: Optional[List[Dict[str, Any]]] = None
    backtime: Optional[float] = None
    fronttime: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class StoryResponse(StoryBase):
    """Story response schema"""
    id: UUID
    rundown_id: UUID
    status: StoryStatus
    on_air: bool
    actual_start: Optional[datetime] = None
    actual_duration: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Include related data count
    graphics_count: Optional[int] = None
    approval_count: Optional[int] = None


class StoryReorder(BaseSchema):
    """Schema for reordering stories"""
    story_positions: List[Dict[str, Any]] = Field(
        ...,
        description="List of story IDs and their new positions",
        example=[{"story_id": "uuid", "position": 0}]
    )


# Script schemas
class ScriptBase(BaseSchema):
    """Base script schema"""
    content: str = Field(..., min_length=1)
    language: str = Field(default="en", max_length=10)
    cue_points: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScriptCreate(ScriptBase):
    """Schema for creating script"""
    pass


class ScriptUpdate(BaseSchema):
    """Schema for updating script"""
    content: Optional[str] = Field(None, min_length=1)
    language: Optional[str] = Field(None, max_length=10)
    cue_points: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ScriptResponse(ScriptBase):
    """Script response schema"""
    id: UUID
    version: int
    formatted_content: Optional[str] = None
    word_count: Optional[int] = None
    estimated_duration: Optional[int] = None
    approval_status: ApprovalStatus
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ScriptApproval(BaseSchema):
    """Script approval schema"""
    approval_status: ApprovalStatus
    comments: Optional[str] = None


# Graphics schemas
class GraphicsBase(BaseSchema):
    """Base graphics schema"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    type: GraphicsType
    category: Optional[str] = Field(None, max_length=100)
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class GraphicsCreate(GraphicsBase):
    """Schema for creating graphics"""
    template_id: Optional[UUID] = None


class GraphicsUpdate(BaseSchema):
    """Schema for updating graphics"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[GraphicsType] = None
    category: Optional[str] = Field(None, max_length=100)
    data: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class GraphicsResponse(GraphicsBase):
    """Graphics response schema"""
    id: UUID
    is_template: bool
    template_id: Optional[UUID] = None
    preview_url: Optional[str] = None
    render_url: Optional[str] = None
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Template schemas
class TemplateBase(BaseSchema):
    """Base template schema"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class RundownTemplateCreate(TemplateBase):
    """Schema for creating rundown template"""
    show_type: Optional[str] = Field(None, max_length=100)
    duration_minutes: Optional[int] = Field(None, ge=0)
    structure: Dict[str, Any]
    default_stories: List[Dict[str, Any]] = Field(default_factory=list)
    is_public: bool = Field(default=False)


class RundownTemplateResponse(TemplateBase):
    """Rundown template response schema"""
    id: UUID
    show_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    structure: Dict[str, Any]
    default_stories: List[Dict[str, Any]]
    active: bool
    is_public: bool
    created_by: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class GraphicsTemplateCreate(BaseSchema):
    """Schema for creating graphics template"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    type: GraphicsType
    category: Optional[str] = Field(None, max_length=100)
    schema: Dict[str, Any]
    default_data: Dict[str, Any] = Field(default_factory=dict)
    preview_template: Optional[str] = None
    renderer: str = Field(..., min_length=1, max_length=50)
    renderer_template: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class GraphicsTemplateResponse(BaseSchema):
    """Graphics template response schema"""
    id: UUID
    name: str
    slug: str
    type: GraphicsType
    category: Optional[str] = None
    schema: Dict[str, Any]
    default_data: Dict[str, Any]
    preview_template: Optional[str] = None
    renderer: str
    renderer_template: Optional[str] = None
    active: bool
    version: str
    description: Optional[str] = None
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None


# Approval schemas
class ApprovalRequest(BaseSchema):
    """Approval request schema"""
    approval_type: str = Field(..., min_length=1, max_length=50)
    comments: Optional[str] = None


class ApprovalResponse(BaseSchema):
    """Approval response schema"""
    status: ApprovalStatus
    comments: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)


class StoryApprovalResponse(BaseSchema):
    """Story approval response schema"""
    id: UUID
    story_id: UUID
    approval_type: str
    status: ApprovalStatus
    requested_by: UUID
    requested_at: datetime
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    comments: Optional[str] = None
    conditions: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


# Live production schemas
class LiveStatus(BaseSchema):
    """Live production status"""
    rundown_id: Optional[UUID] = None
    on_air_story_id: Optional[UUID] = None
    next_story_id: Optional[UUID] = None
    countdown_seconds: Optional[int] = None
    is_live: bool = Field(default=False)
    studio_ready: bool = Field(default=False)
    automation_enabled: bool = Field(default=False)


class BreakingNews(BaseSchema):
    """Breaking news insertion"""
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    duration_seconds: int = Field(..., ge=0)
    script_content: Optional[str] = None
    position: Optional[int] = None
    interrupt_current: bool = Field(default=False)


# Automation schemas
class AutomationTrigger(BaseSchema):
    """Automation trigger schema"""
    event_type: str = Field(..., min_length=1, max_length=100)
    event_data: Dict[str, Any]
    scheduled_time: Optional[datetime] = None


class AutomationStatus(BaseSchema):
    """Automation system status"""
    connected: bool
    system_type: str
    capabilities: List[str]
    current_preset: Optional[str] = None
    error_message: Optional[str] = None


# WebSocket messages
class WSMessage(BaseSchema):
    """WebSocket message schema"""
    type: str = Field(..., min_length=1, max_length=50)
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSRundownUpdate(WSMessage):
    """Rundown update WebSocket message"""
    type: str = Field(default="rundown_update")
    rundown_id: UUID
    changes: Dict[str, Any]


class WSStoryUpdate(WSMessage):
    """Story update WebSocket message"""
    type: str = Field(default="story_update")
    story_id: UUID
    rundown_id: UUID
    changes: Dict[str, Any]


# Update forward references
RundownWithStories.model_rebuild()


# Teleprompter schemas
class TeleprompterSettings(BaseSchema):
    """Teleprompter settings schema"""
    speed_wpm: int = Field(default=180, ge=50, le=500)
    font_size: int = Field(default=32, ge=12, le=72)
    font_family: str = Field(default="Arial")
    text_color: str = Field(default="#FFFFFF")
    background_color: str = Field(default="#000000")
    margin_top: int = Field(default=100, ge=0)
    margin_bottom: int = Field(default=100, ge=0)
    show_countdown: bool = Field(default=True)
    show_cues: bool = Field(default=True)


class TeleprompterScript(BaseSchema):
    """Teleprompter script output"""
    script_id: UUID
    content: str
    formatted_content: str
    cue_points: List[Dict[str, Any]]
    estimated_duration: int
    word_count: int
    settings: TeleprompterSettings