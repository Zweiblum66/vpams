"""Pydantic schemas for NRCS Integration Service"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID
import enum

from ..db.models import NRCSType, ConnectionStatus, SyncStatus, StoryStatus, AssignmentStatus


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        use_enum_values = True
        arbitrary_types_allowed = True


# NRCS System schemas
class NRCSSystemBase(BaseSchema):
    """Base NRCS system schema"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    system_type: NRCSType
    vendor: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    
    # Connection
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    api_url: Optional[str] = Field(None, max_length=500)
    websocket_url: Optional[str] = Field(None, max_length=500)
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NRCSSystemCreate(NRCSSystemBase):
    """Schema for creating NRCS system"""
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None


class NRCSSystemUpdate(BaseSchema):
    """Schema for updating NRCS system"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vendor: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    
    # Connection
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    api_url: Optional[str] = Field(None, max_length=500)
    websocket_url: Optional[str] = Field(None, max_length=500)
    
    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    
    # Configuration
    config: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class NRCSSystemResponse(NRCSSystemBase):
    """NRCS system response schema"""
    id: UUID
    status: ConnectionStatus
    is_active: bool
    is_primary: bool
    last_connection: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    
    # Stats
    total_stories: int
    total_rundowns: int
    total_users: int
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# Story schemas
class NRCSStoryBase(BaseSchema):
    """Base story schema"""
    story_id: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    headline: str = Field(..., min_length=1, max_length=500)
    summary: Optional[str] = None
    body: Optional[str] = None
    
    # Metadata
    author: Optional[str] = Field(None, max_length=255)
    editor: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    priority: int = Field(default=0, ge=0, le=10)
    
    # Status
    is_breaking: bool = Field(default=False)
    is_featured: bool = Field(default=False)
    
    # Timing
    embargo_until: Optional[datetime] = None
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    
    # References
    external_id: Optional[str] = Field(None, max_length=255)
    source_system: Optional[str] = Field(None, max_length=50)
    related_stories: List[str] = Field(default_factory=list)
    
    # Content structure
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    media_references: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NRCSStoryCreate(NRCSStoryBase):
    """Schema for creating story"""
    system_id: UUID


class NRCSStoryUpdate(BaseSchema):
    """Schema for updating story"""
    headline: Optional[str] = Field(None, min_length=1, max_length=500)
    summary: Optional[str] = None
    body: Optional[str] = None
    
    # Metadata
    author: Optional[str] = Field(None, max_length=255)
    editor: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    priority: Optional[int] = Field(None, ge=0, le=10)
    
    # Status
    status: Optional[StoryStatus] = None
    is_breaking: Optional[bool] = None
    is_featured: Optional[bool] = None
    
    # Timing
    embargo_until: Optional[datetime] = None
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    
    # Content structure
    sections: Optional[List[Dict[str, Any]]] = None
    media_references: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    
    metadata: Optional[Dict[str, Any]] = None


class NRCSStoryResponse(NRCSStoryBase):
    """Story response schema"""
    id: UUID
    system_id: UUID
    status: StoryStatus
    
    # Version control
    version: int
    revision_hash: Optional[str] = None
    
    # Workflow
    approval_status: Optional[str] = None
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Sync info
    last_sync_at: Optional[datetime] = None
    sync_status: SyncStatus
    sync_error: Optional[str] = None
    
    # Analytics
    view_count: int
    share_count: int
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    external_created_at: Optional[datetime] = None
    external_updated_at: Optional[datetime] = None


# Rundown schemas
class NRCSRundownBase(BaseSchema):
    """Base rundown schema"""
    rundown_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=500)
    
    # Show information
    show_name: Optional[str] = Field(None, max_length=255)
    episode_number: Optional[str] = Field(None, max_length=50)
    air_date: Optional[datetime] = None
    air_time: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    
    # Producer information
    producer: Optional[str] = Field(None, max_length=255)
    director: Optional[str] = Field(None, max_length=255)
    
    # Template info
    template_name: Optional[str] = Field(None, max_length=255)
    template_version: Optional[str] = Field(None, max_length=50)
    
    # Configuration
    auto_timing: bool = Field(default=True)
    allow_overrun: bool = Field(default=False)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class NRCSRundownCreate(NRCSRundownBase):
    """Schema for creating rundown"""
    system_id: UUID


class NRCSRundownUpdate(BaseSchema):
    """Schema for updating rundown"""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    
    # Show information
    show_name: Optional[str] = Field(None, max_length=255)
    episode_number: Optional[str] = Field(None, max_length=50)
    air_date: Optional[datetime] = None
    air_time: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    
    # Producer information
    producer: Optional[str] = Field(None, max_length=255)
    director: Optional[str] = Field(None, max_length=255)
    
    # Status
    status: Optional[str] = None
    is_live: Optional[bool] = None
    is_locked: Optional[bool] = None
    
    # Configuration
    auto_timing: Optional[bool] = None
    allow_overrun: Optional[bool] = None
    
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class NRCSRundownResponse(NRCSRundownBase):
    """Rundown response schema"""
    id: UUID
    system_id: UUID
    status: str
    is_live: bool
    is_locked: bool
    
    # Timing
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    
    # External references
    external_id: Optional[str] = None
    parent_rundown_id: Optional[str] = None
    
    # Sync info
    last_sync_at: Optional[datetime] = None
    sync_status: SyncStatus
    sync_error: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    external_created_at: Optional[datetime] = None
    external_updated_at: Optional[datetime] = None
    
    # Stats
    item_count: Optional[int] = None
    total_duration: Optional[int] = None


# Rundown Item schemas
class RundownItemBase(BaseSchema):
    """Base rundown item schema"""
    position: int = Field(..., ge=0)
    item_id: Optional[str] = Field(None, max_length=255)
    
    # Item details
    title: Optional[str] = Field(None, max_length=500)
    item_type: str = Field(default="story", max_length=50)
    
    # Timing
    duration_seconds: Optional[int] = Field(None, ge=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Technical details
    video_format: Optional[str] = Field(None, max_length=50)
    audio_channels: Optional[int] = Field(None, ge=0)
    
    # Graphics and automation
    graphics: List[Dict[str, Any]] = Field(default_factory=list)
    automation_commands: List[Dict[str, Any]] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class RundownItemCreate(RundownItemBase):
    """Schema for creating rundown item"""
    rundown_id: UUID
    story_id: Optional[UUID] = None


class RundownItemUpdate(BaseSchema):
    """Schema for updating rundown item"""
    position: Optional[int] = Field(None, ge=0)
    title: Optional[str] = Field(None, max_length=500)
    item_type: Optional[str] = Field(None, max_length=50)
    
    # Timing
    duration_seconds: Optional[int] = Field(None, ge=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Status
    status: Optional[str] = None
    
    # Technical details
    video_format: Optional[str] = Field(None, max_length=50)
    audio_channels: Optional[int] = Field(None, ge=0)
    
    # Graphics and automation
    graphics: Optional[List[Dict[str, Any]]] = None
    automation_commands: Optional[List[Dict[str, Any]]] = None
    
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class RundownItemResponse(RundownItemBase):
    """Rundown item response schema"""
    id: UUID
    rundown_id: UUID
    story_id: Optional[UUID] = None
    
    # Status
    status: str
    is_played: bool
    played_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# User schemas
class NRCSUserBase(BaseSchema):
    """Base user schema"""
    user_id: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    
    # User info
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    
    # Permissions
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    
    # Contact info
    phone: Optional[str] = Field(None, max_length=50)
    extension: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=255)
    
    # Preferences
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NRCSUserCreate(NRCSUserBase):
    """Schema for creating user"""
    system_id: UUID


class NRCSUserUpdate(BaseSchema):
    """Schema for updating user"""
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    
    # User info
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    
    # Status
    is_active: Optional[bool] = None
    
    # Permissions
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    groups: Optional[List[str]] = None
    
    # Contact info
    phone: Optional[str] = Field(None, max_length=50)
    extension: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=255)
    
    # Preferences
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    preferences: Optional[Dict[str, Any]] = None
    
    metadata: Optional[Dict[str, Any]] = None


class NRCSUserResponse(NRCSUserBase):
    """User response schema"""
    id: UUID
    system_id: UUID
    
    # Status
    is_active: bool
    is_online: bool
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Sync info
    last_sync_at: Optional[datetime] = None
    sync_status: SyncStatus
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    external_created_at: Optional[datetime] = None
    external_updated_at: Optional[datetime] = None


# Assignment schemas
class NRCSAssignmentBase(BaseSchema):
    """Base assignment schema"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    
    # Assignment type
    assignment_type: str = Field(default="story", max_length=50)
    priority: int = Field(default=0, ge=0, le=10)
    
    # Timing
    due_date: Optional[datetime] = None
    
    # Location and logistics
    location: Optional[str] = Field(None, max_length=500)
    contact_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Beat information
    beat_name: Optional[str] = Field(None, max_length=255)
    beat_category: Optional[str] = Field(None, max_length=100)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class NRCSAssignmentCreate(NRCSAssignmentBase):
    """Schema for creating assignment"""
    system_id: UUID
    assignee_id: UUID
    story_id: Optional[UUID] = None


class NRCSAssignmentUpdate(BaseSchema):
    """Schema for updating assignment"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    
    # Assignment type
    assignment_type: Optional[str] = Field(None, max_length=50)
    priority: Optional[int] = Field(None, ge=0, le=10)
    
    # Status and timing
    status: Optional[AssignmentStatus] = None
    due_date: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    milestone_notes: Optional[str] = None
    
    # Location and logistics
    location: Optional[str] = Field(None, max_length=500)
    contact_info: Optional[Dict[str, Any]] = None
    
    # Beat information
    beat_name: Optional[str] = Field(None, max_length=255)
    beat_category: Optional[str] = Field(None, max_length=100)
    
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class NRCSAssignmentResponse(NRCSAssignmentBase):
    """Assignment response schema"""
    id: UUID
    system_id: UUID
    assignee_id: UUID
    story_id: Optional[UUID] = None
    
    # Assignment details
    assignment_id: Optional[str] = None
    
    # Status and timing
    status: AssignmentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: int
    milestone_notes: Optional[str] = None
    
    # Sync info
    last_sync_at: Optional[datetime] = None
    sync_status: SyncStatus
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    external_created_at: Optional[datetime] = None


# Sync operations schemas
class SyncRequest(BaseSchema):
    """Sync operation request"""
    system_id: Optional[UUID] = None
    operation_type: Optional[str] = None  # story, rundown, user, etc.
    target_ids: Optional[List[str]] = None
    force: bool = Field(default=False)


class SyncResponse(BaseSchema):
    """Sync operation response"""
    operation_id: UUID
    status: SyncStatus
    started_at: datetime
    estimated_duration: Optional[int] = None  # seconds
    
    # Progress
    total_items: int
    processed_items: int
    failed_items: int
    
    # Results
    results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# Search schemas
class SearchRequest(BaseSchema):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=1000)
    
    # Filters
    system_id: Optional[UUID] = None
    content_type: Optional[str] = None  # story, rundown, user
    category: Optional[str] = None
    author: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Search options
    fuzzy: bool = Field(default=True)
    include_archived: bool = Field(default=False)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResponse(BaseSchema):
    """Search response schema"""
    total_results: int
    results: List[Dict[str, Any]]
    took_ms: int
    
    # Facets
    facets: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)


# Analytics schemas
class AnalyticsRequest(BaseSchema):
    """Analytics request schema"""
    system_id: Optional[UUID] = None
    metric_type: str  # usage, performance, compliance, etc.
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    granularity: str = Field(default="day")  # hour, day, week, month
    group_by: Optional[List[str]] = None


class AnalyticsResponse(BaseSchema):
    """Analytics response schema"""
    metric_type: str
    period: Dict[str, datetime]
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]


# Status schemas
class SystemStatusResponse(BaseSchema):
    """System status response"""
    system_id: UUID
    name: str
    system_type: NRCSType
    status: ConnectionStatus
    is_active: bool
    last_heartbeat: Optional[datetime] = None
    
    # Connection details
    connection_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Stats
    stats: Dict[str, Any] = Field(default_factory=dict)
    
    # Recent activity
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class ServiceHealthResponse(BaseSchema):
    """Service health response"""
    status: str  # healthy, degraded, unhealthy
    service: str
    version: str
    uptime_seconds: int
    
    # Component health
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # System info
    system_info: Dict[str, Any] = Field(default_factory=dict)