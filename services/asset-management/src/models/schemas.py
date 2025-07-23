"""
Pydantic schemas for Asset Management Service

This module defines request/response schemas for the API.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
import mimetypes

from ..db.models import AssetStatus, AssetType, ContainerType


# Base schemas
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# Asset schemas
class AssetBase(BaseModel):
    """Base asset schema"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    asset_type: AssetType
    project_id: Optional[UUID] = None
    is_public: bool = False
    technical_metadata: Optional[Dict[str, Any]] = None


class AssetCreate(BaseModel):
    """Schema for creating an asset"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    is_public: bool = False
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator("display_name", mode="before")
    def set_display_name(cls, v, values):
        """Set display_name to name if not provided"""
        if v is None and "name" in values.data:
            return values.data["name"]
        return v


class AssetUpdate(BaseModel):
    """Schema for updating an asset"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    project_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetResponse(AssetBase):
    """Asset response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    file_path: str
    file_size: int
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    file_extension: Optional[str] = None
    status: AssetStatus
    storage_driver: str
    storage_tier: str
    owner_id: UUID
    version_count: int = 0
    tags: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class AssetListResponse(BaseModel):
    """Asset list response with metadata"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    display_name: str
    asset_type: AssetType
    status: AssetStatus
    file_size: int
    mime_type: Optional[str] = None
    owner_id: UUID
    created_at: datetime


# Asset version schemas
class AssetVersionCreate(BaseModel):
    """Schema for creating an asset version"""
    version_label: Optional[str] = Field(None, max_length=64)
    comment: Optional[str] = None


class AssetVersionResponse(BaseModel):
    """Asset version response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    asset_id: UUID
    version_number: int
    version_label: Optional[str] = None
    file_size: int
    file_hash: str
    comment: Optional[str] = None
    is_current: bool
    created_by: UUID
    created_at: datetime
    storage_tier: str


# Upload schemas
class UploadInitiate(BaseModel):
    """Schema for initiating file upload"""
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    mime_type: Optional[str] = None
    asset_data: Optional[AssetCreate] = None
    
    @field_validator("mime_type")
    def validate_mime_type(cls, v, values):
        """Validate or guess MIME type"""
        if v is None and "filename" in values.data:
            mime_type, _ = mimetypes.guess_type(values.data["filename"])
            return mime_type
        return v


class UploadResponse(BaseModel):
    """Upload initiation response"""
    upload_id: str
    upload_url: Optional[str] = None
    chunk_size: int
    total_chunks: int
    expires_at: datetime


class UploadComplete(BaseModel):
    """Schema for completing upload"""
    upload_id: str
    file_hash: Optional[str] = None
    parts: Optional[List[Dict[str, Any]]] = None


# Project container schemas
class ProjectContainerBase(BaseModel):
    """Base project container schema"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    container_type: ContainerType
    parent_id: Optional[UUID] = None
    is_public: bool = False
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectContainerCreate(ProjectContainerBase):
    """Schema for creating a project container"""
    pass


class ProjectContainerUpdate(BaseModel):
    """Schema for updating a project container"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectContainerResponse(ProjectContainerBase):
    """Project container response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    path: str
    owner_id: UUID
    asset_count: int = 0
    child_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectContainerTree(ProjectContainerResponse):
    """Project container with children"""
    children: List["ProjectContainerTree"] = []


# Tag schemas
class TagCreate(BaseModel):
    """Schema for creating a tag"""
    name: str = Field(..., min_length=1, max_length=64)
    category: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class TagResponse(BaseModel):
    """Tag response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    category: Optional[str] = None
    color: Optional[str] = None
    asset_count: int = 0
    created_at: datetime


# Collection schemas
class CollectionCreate(BaseModel):
    """Schema for creating a collection"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: bool = False
    metadata: Optional[Dict[str, Any]] = None
    asset_ids: Optional[List[UUID]] = None


class CollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    cover_asset_id: Optional[UUID] = None


class CollectionResponse(BaseModel):
    """Collection response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    description: Optional[str] = None
    owner_id: UUID
    is_public: bool
    metadata: Optional[Dict[str, Any]] = None
    cover_asset_id: Optional[UUID] = None
    asset_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


# Asset version schemas
class AssetVersionCreate(BaseModel):
    """Schema for creating asset version"""
    file_path: str
    file_size: int = Field(..., gt=0)
    file_hash: Optional[str] = None
    comment: Optional[str] = None
    version_label: Optional[str] = Field(None, max_length=64)


class AssetVersionResponse(BaseModel):
    """Asset version response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    asset_id: UUID
    version_number: int
    version_label: Optional[str] = None
    file_path: str
    file_size: int
    file_hash: Optional[str] = None
    comment: Optional[str] = None
    is_current: bool
    created_by: UUID
    created_at: datetime
    storage_driver: str
    storage_path: str
    storage_tier: Optional[str] = None


class VersionUploadInitiate(BaseModel):
    """Schema for initiating version upload"""
    asset_id: UUID
    filename: str
    file_size: int = Field(..., gt=0)
    mime_type: Optional[str] = None
    comment: Optional[str] = None
    version_label: Optional[str] = None


# Asset relationship schemas
class AssetRelationshipCreate(BaseModel):
    """Schema for creating asset relationship"""
    target_asset_id: UUID
    relationship_type: str = Field(..., min_length=1, max_length=64)
    metadata: Optional[Dict[str, Any]] = None


class AssetRelationshipResponse(BaseModel):
    """Asset relationship response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# Bulk operation schemas
class BulkAssetUpdate(BaseModel):
    """Schema for bulk asset updates"""
    asset_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    update_data: AssetUpdate


class BulkAssetDelete(BaseModel):
    """Schema for bulk asset deletion"""
    asset_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    permanent: bool = False


class BulkAssetTag(BaseModel):
    """Schema for bulk tagging operations"""
    asset_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    tags_to_add: Optional[List[str]] = None
    tags_to_remove: Optional[List[str]] = None


class BulkAssetMove(BaseModel):
    """Schema for bulk move operations"""
    asset_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    target_project_id: UUID


class BulkOperationResult(BaseModel):
    """Result of bulk operation"""
    successful: List[UUID] = []
    failed: List[Dict[str, Any]] = []  # {asset_id: str, error: str}
    total: int
    success_count: int
    failure_count: int


# Duplicate detection schemas
class DuplicateDetectionResult(BaseModel):
    """Result of duplicate detection"""
    has_exact_duplicates: bool = False
    has_similar_duplicates: bool = False
    exact_duplicates: List[UUID] = []
    similar_duplicates: List[UUID] = []
    duplicate_count: int = 0


class DuplicateGroup(BaseModel):
    """Group of duplicate assets"""
    file_hash: str
    duplicate_count: int
    total_size: int
    wasted_space: int
    assets: List[Dict[str, Any]]


class DuplicateStatistics(BaseModel):
    """Statistics about duplicates"""
    total_assets: int
    total_duplicate_assets: int
    unique_duplicate_groups: int
    total_wasted_space_bytes: int
    total_wasted_space_gb: float
    duplicate_percentage: float
    largest_duplicate_group: int
    project_id: Optional[UUID] = None


# Project container schemas
class ProjectContainerBase(BaseModel):
    """Base project container schema"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    container_type: ContainerType
    parent_id: Optional[UUID] = None
    is_public: bool = False
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectContainerCreate(BaseModel):
    """Schema for creating a project container"""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = None
    description: Optional[str] = None
    container_type: ContainerType
    parent_id: Optional[UUID] = None
    is_public: bool = False
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    
    @field_validator("display_name", mode="before")
    def set_display_name(cls, v, values):
        """Set display_name to name if not provided"""
        if v is None and "name" in values.data:
            return values.data["name"]
        return v


class ProjectContainerUpdate(BaseModel):
    """Schema for updating a project container"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectContainerResponse(ProjectContainerBase):
    """Project container response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    path: Optional[str] = None
    owner_id: UUID
    asset_count: int = 0
    child_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectContainerTree(ProjectContainerResponse):
    """Project container with children (tree structure)"""
    children: List['ProjectContainerTree'] = []


# Shot item schemas (editorial workflow)
class ShotItemBase(BaseModel):
    """Base shot item schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    in_point: int = Field(0, ge=0)
    out_point: Optional[int] = Field(None, gt=0)
    metadata: Optional[Dict[str, Any]] = None
    markers: Optional[List[Dict[str, Any]]] = None
    color_label: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class ShotItemCreate(BaseModel):
    """Schema for creating a shot item"""
    container_id: UUID
    asset_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    in_point: int = Field(0, ge=0)
    out_point: Optional[int] = Field(None, gt=0)
    metadata: Optional[Dict[str, Any]] = None
    markers: Optional[List[Dict[str, Any]]] = None
    sort_order: Optional[int] = 0
    color_label: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class ShotItemUpdate(BaseModel):
    """Schema for updating a shot item"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    in_point: Optional[int] = Field(None, ge=0)
    out_point: Optional[int] = Field(None, gt=0)
    metadata: Optional[Dict[str, Any]] = None
    markers: Optional[List[Dict[str, Any]]] = None
    sort_order: Optional[int] = None
    color_label: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class ShotItemResponse(ShotItemBase):
    """Shot item response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    container_id: UUID
    asset_id: UUID
    duration: Optional[int] = None
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: UUID
    
    # Include basic asset info
    asset_name: Optional[str] = None
    asset_type: Optional[AssetType] = None
    asset_thumbnail: Optional[str] = None


# Timeline schemas (for sequences)
class TimelineItemBase(BaseModel):
    """Base timeline item schema"""
    track_number: int = Field(..., ge=0)
    track_type: str = Field(..., pattern="^(video|audio|subtitle)$")
    track_name: Optional[str] = None
    start_time: int = Field(..., ge=0)
    end_time: int = Field(..., gt=0)
    source_in: Optional[int] = Field(None, ge=0)
    source_out: Optional[int] = Field(None, gt=0)
    speed: float = Field(1.0, gt=0)
    is_enabled: bool = True
    is_locked: bool = False
    opacity: float = Field(1.0, ge=0, le=1)
    effects: Optional[List[Dict[str, Any]]] = []
    transition_in: Optional[Dict[str, Any]] = None
    transition_out: Optional[Dict[str, Any]] = None


class TimelineItemCreate(TimelineItemBase):
    """Schema for creating a timeline item"""
    sequence_id: UUID
    clip_id: UUID


class TimelineItemUpdate(BaseModel):
    """Schema for updating a timeline item"""
    track_number: Optional[int] = Field(None, ge=0)
    track_name: Optional[str] = None
    start_time: Optional[int] = Field(None, ge=0)
    end_time: Optional[int] = Field(None, gt=0)
    source_in: Optional[int] = Field(None, ge=0)
    source_out: Optional[int] = Field(None, gt=0)
    speed: Optional[float] = Field(None, gt=0)
    is_enabled: Optional[bool] = None
    is_locked: Optional[bool] = None
    opacity: Optional[float] = Field(None, ge=0, le=1)
    effects: Optional[List[Dict[str, Any]]] = None
    transition_in: Optional[Dict[str, Any]] = None
    transition_out: Optional[Dict[str, Any]] = None


class TimelineItemResponse(TimelineItemBase):
    """Timeline item response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sequence_id: UUID
    clip_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Include clip info
    clip_name: Optional[str] = None
    clip_asset_id: Optional[UUID] = None


# Project template schemas
class ProjectTemplateBase(BaseModel):
    """Base project template schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    structure: Dict[str, Any]
    default_settings: Optional[Dict[str, Any]] = {}


class ProjectTemplateCreate(ProjectTemplateBase):
    """Schema for creating a project template"""
    is_public: bool = True


class ProjectTemplateUpdate(BaseModel):
    """Schema for updating a project template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None
    default_settings: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class ProjectTemplateResponse(ProjectTemplateBase):
    """Project template response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_system: bool
    is_public: bool
    owner_id: Optional[UUID] = None
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# Container permissions/sharing schemas
class ContainerShareCreate(BaseModel):
    """Schema for sharing a container"""
    container_id: UUID
    shared_with_id: UUID
    shared_with_type: str = Field(..., pattern="^(user|group)$")
    can_view: bool = True
    can_add_assets: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_share: bool = False
    expires_at: Optional[datetime] = None
    note: Optional[str] = None


class ContainerShareUpdate(BaseModel):
    """Schema for updating container share"""
    can_view: Optional[bool] = None
    can_add_assets: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_share: Optional[bool] = None
    expires_at: Optional[datetime] = None
    note: Optional[str] = None


class ContainerShareResponse(BaseModel):
    """Container share response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    container_id: UUID
    container_name: Optional[str] = None
    shared_with_id: UUID
    shared_with_type: str
    can_view: bool
    can_add_assets: bool
    can_edit: bool
    can_delete: bool
    can_share: bool
    expires_at: Optional[datetime] = None
    note: Optional[str] = None
    shared_by: UUID
    created_at: datetime
    last_accessed_at: Optional[datetime] = None


# Sharing schemas
class AssetShareCreate(BaseModel):
    """Schema for creating asset share"""
    shared_with_id: UUID
    shared_with_type: str = Field(..., pattern="^(user|group)$")
    can_view: bool = True
    can_download: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_share: bool = False
    expires_at: Optional[datetime] = None
    password: Optional[str] = None
    download_limit: Optional[int] = Field(None, gt=0)


class AssetShareUpdate(BaseModel):
    """Schema for updating asset share"""
    can_view: Optional[bool] = None
    can_download: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_share: Optional[bool] = None
    expires_at: Optional[datetime] = None
    download_limit: Optional[int] = Field(None, gt=0)


class AssetShareResponse(BaseModel):
    """Asset share response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    asset_id: UUID
    shared_with_id: UUID
    shared_with_type: str
    can_view: bool
    can_download: bool
    can_edit: bool
    can_delete: bool
    can_share: bool
    expires_at: Optional[datetime] = None
    has_password: bool = False
    download_limit: Optional[int] = None
    download_count: int = 0
    shared_by: UUID
    created_at: datetime
    last_accessed_at: Optional[datetime] = None


# Search schemas
class AssetSearchParams(BaseModel):
    """Asset search parameters"""
    query: Optional[str] = None
    asset_type: Optional[AssetType] = None
    status: Optional[AssetStatus] = None
    project_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    mime_type: Optional[str] = None
    min_size: Optional[int] = Field(None, gt=0)
    max_size: Optional[int] = Field(None, gt=0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    storage_tier: Optional[str] = None
    is_public: Optional[bool] = None


# Bulk operation schemas
class BulkAssetUpdate(BaseModel):
    """Schema for bulk asset updates"""
    asset_ids: List[UUID]
    update_data: AssetUpdate


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    total: int
    successful: int
    failed: int
    errors: Optional[List[Dict[str, Any]]] = None


# Timeline Versioning Schemas
class TimelineVersionCreate(BaseModel):
    """Schema for creating a timeline version"""
    name: Optional[str] = Field(None, description="Version name")
    description: Optional[str] = Field("", description="Version description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_auto_save: bool = Field(False, description="Whether this is an auto-save")


class TimelineVersionUpdate(BaseModel):
    """Schema for updating version metadata"""
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TimelineVersionRestore(BaseModel):
    """Schema for restoring a timeline version"""
    save_current: bool = Field(True, description="Save current state before restoring")
    preserve_ids: bool = Field(False, description="Preserve timeline item IDs")


class TimelineVersionCompare(BaseModel):
    """Schema for comparing two versions"""
    version1_id: str = Field(..., description="First version ID or 'current'")
    version2_id: str = Field(..., description="Second version ID or 'current'")


class TimelineVersionResponse(BaseModel):
    """Response schema for timeline version"""
    id: str
    sequence_id: str
    version_number: int
    name: str
    description: str
    created_by: str
    created_at: datetime
    is_auto_save: bool
    parent_version_id: Optional[str]
    timeline_item_count: int
    metadata: Dict[str, Any]

    class Config:
        orm_mode = True


# Comment Schemas
class CommentCreate(BaseModel):
    """Schema for creating a comment"""
    resource_type: Literal["asset", "container"] = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    parent_comment_id: Optional[str] = Field(None, description="ID of parent comment for replies")
    content: str = Field(..., min_length=1, max_length=5000, description="Comment content")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: str = Field(..., min_length=1, max_length=5000, description="Updated content")
    metadata: Optional[Dict[str, Any]] = None


class CommentResponse(BaseModel):
    """Response schema for a comment"""
    id: str
    resource_type: str
    resource_id: str
    parent_comment_id: Optional[str]
    user: Optional[Dict[str, Any]]  # User info dict
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    is_edited: bool
    is_deleted: bool = False
    mentions: List[str]
    attachments: List[Dict[str, Any]]
    reactions: Dict[str, List[str]]  # emoji -> list of user IDs
    reply_count: int
    metadata: Dict[str, Any]

    class Config:
        orm_mode = True


class CommentThreadResponse(BaseModel):
    """Response schema for a comment thread with nested replies"""
    id: str
    resource_type: str
    resource_id: str
    parent_comment_id: Optional[str]
    user: Optional[Dict[str, Any]]
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    is_edited: bool
    is_deleted: bool
    mentions: List[str]
    attachments: List[Dict[str, Any]]
    reactions: Dict[str, List[str]]
    replies: List['CommentThreadResponse'] = []
    reply_count: int
    metadata: Dict[str, Any]

    class Config:
        orm_mode = True


# Update forward references
CommentThreadResponse.model_rebuild()


# Activity Tracking Schemas
class ActivityFilterParams(BaseModel):
    """Parameters for filtering activities"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    activity_types: Optional[List[str]] = None
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    include_all_users: bool = Field(False, description="Admin only: include activities from all users")


class ActivityLogResponse(BaseModel):
    """Response schema for activity log entry"""
    id: str
    user: Dict[str, Any]  # User info
    activity_type: str
    resource_type: str
    resource_id: Optional[str]
    resource_name: Optional[str]
    description: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True


class ActivitySummaryResponse(BaseModel):
    """Response schema for activity summary"""
    total_activities: int
    activities_by_type: Dict[str, int]
    activities_by_resource: Dict[str, int]
    most_active_hours: List[Dict[str, Any]]
    recent_resources: List[Dict[str, Any]]

    class Config:
        orm_mode = True


# Notification Schemas
class NotificationCreate(BaseModel):
    """Schema for creating a test notification"""
    type: str = Field(..., description="Notification type")
    title: Optional[str] = Field(None, description="Notification title")
    message: str = Field(..., description="Notification message")
    priority: Literal["low", "normal", "high", "urgent"] = Field("normal")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NotificationUpdate(BaseModel):
    """Schema for updating notification"""
    is_read: Optional[bool] = None
    is_archived: Optional[bool] = None


class NotificationResponse(BaseModel):
    """Response schema for notification"""
    id: str
    type: str
    title: str
    message: str
    icon: str
    priority: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    action_url: Optional[str]
    is_read: bool
    metadata: Dict[str, Any]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        orm_mode = True


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    email_frequency: Literal["immediate", "daily", "weekly"] = "immediate"
    notification_types: Dict[str, bool] = Field(default_factory=lambda: {
        "asset_updates": True,
        "project_updates": True,
        "comments": True,
        "system_alerts": True,
        "workflow_updates": True
    })
    quiet_hours: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False,
        "start_time": "22:00",
        "end_time": "08:00",
        "timezone": "UTC"
    })

    class Config:
        orm_mode = True