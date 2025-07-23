"""
Integration Service Pydantic Schemas
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class ExportFormat(str, Enum):
    """Export format options"""
    AAF = "aaf"
    XML = "xml"
    EDL = "edl"
    CMX = "cmx"
    OTIO = "otio"
    OMF = "omf"


class ExportStatus(str, Enum):
    """Export status options"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    """Job status options"""
    QUEUED = "queued"
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TimelineExportRequest(BaseModel):
    """Request to export a timeline"""
    timeline_id: str = Field(..., description="Timeline ID to export")
    format: ExportFormat = Field(..., description="Export format")
    include_media: bool = Field(default=True, description="Include media references")
    include_effects: bool = Field(default=True, description="Include effects")
    include_audio: bool = Field(default=True, description="Include audio tracks")
    start_time: Optional[int] = Field(None, description="Start time in frames")
    end_time: Optional[int] = Field(None, description="End time in frames")
    tracks: Optional[List[str]] = Field(None, description="Specific tracks to export")
    frame_rate: Optional[float] = Field(None, description="Override frame rate")
    resolution: Optional[str] = Field(None, description="Override resolution")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ExportResult(BaseModel):
    """Export result response"""
    export_id: str = Field(..., description="Export ID")
    timeline_id: str = Field(..., description="Timeline ID")
    format: str = Field(..., description="Export format")
    file_path: str = Field(..., description="Export file path")
    status: ExportStatus = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation time")
    completed_at: Optional[datetime] = Field(None, description="Export completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Export metadata")


class NLEExportRequest(BaseModel):
    """Request to export for specific NLE"""
    timeline_id: str = Field(..., description="Timeline ID to export")
    nle_type: str = Field(..., description="NLE type (avid, premiere, resolve, fcpx)")
    format: ExportFormat = Field(..., description="Export format")
    include_media: bool = Field(default=True, description="Include media references")
    include_effects: bool = Field(default=True, description="Include effects")
    include_audio: bool = Field(default=True, description="Include audio tracks")
    project_name: Optional[str] = Field(None, description="Project name")
    export_settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Export settings")


class NLEExportResponse(BaseModel):
    """Response for NLE export request"""
    job_id: str = Field(..., description="Export job ID")
    status: JobStatus = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class ExportJobStatus(BaseModel):
    """Export job status"""
    job_id: str = Field(..., description="Job ID")
    timeline_id: str = Field(..., description="Timeline ID")
    format: str = Field(..., description="Export format")
    status: JobStatus = Field(..., description="Job status")
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[ExportResult] = Field(None, description="Export result if completed")


class User(BaseModel):
    """User model for authentication"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")


class ValidationResult(BaseModel):
    """Export file validation result"""
    is_valid: bool = Field(..., description="Whether the file is valid")
    format: str = Field(..., description="Detected format")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")


class NLEPlugin(BaseModel):
    """NLE Plugin information"""
    nle_name: str = Field(..., description="NLE name")
    plugin_name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    status: str = Field(..., description="Plugin status")
    supported_formats: List[str] = Field(..., description="Supported export formats")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Plugin capabilities")


class ExportTemplate(BaseModel):
    """Export template for reusable settings"""
    template_id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    format: ExportFormat = Field(..., description="Export format")
    settings: Dict[str, Any] = Field(..., description="Export settings")
    created_by: str = Field(..., description="User who created the template")
    created_at: datetime = Field(..., description="Creation time")
    is_public: bool = Field(default=False, description="Whether template is public")


class ExportPreset(BaseModel):
    """Export preset for quick export"""
    preset_id: str = Field(..., description="Preset ID")
    name: str = Field(..., description="Preset name")
    nle_type: str = Field(..., description="Target NLE type")
    format: ExportFormat = Field(..., description="Export format")
    settings: Dict[str, Any] = Field(..., description="Preset settings")
    is_default: bool = Field(default=False, description="Whether this is the default preset")


class MediaReference(BaseModel):
    """Media reference for export"""
    asset_id: str = Field(..., description="Asset ID")
    file_path: str = Field(..., description="File path")
    file_name: str = Field(..., description="File name")
    file_size: int = Field(..., description="File size in bytes")
    duration: Optional[int] = Field(None, description="Duration in frames")
    format: str = Field(..., description="Media format")
    checksum: Optional[str] = Field(None, description="File checksum")


class ExportManifest(BaseModel):
    """Export manifest containing all export information"""
    export_id: str = Field(..., description="Export ID")
    timeline_id: str = Field(..., description="Timeline ID")
    format: str = Field(..., description="Export format")
    created_at: datetime = Field(..., description="Creation time")
    timeline_info: Dict[str, Any] = Field(..., description="Timeline information")
    media_references: List[MediaReference] = Field(..., description="Media references")
    export_settings: Dict[str, Any] = Field(..., description="Export settings")
    nle_info: Optional[Dict[str, Any]] = Field(None, description="NLE-specific information")


class ExportStatistics(BaseModel):
    """Export statistics"""
    total_exports: int = Field(..., description="Total number of exports")
    successful_exports: int = Field(..., description="Number of successful exports")
    failed_exports: int = Field(..., description="Number of failed exports")
    formats_breakdown: Dict[str, int] = Field(..., description="Breakdown by format")
    average_duration: float = Field(..., description="Average export duration in seconds")
    total_duration: float = Field(..., description="Total export duration in seconds")


class ExportHistory(BaseModel):
    """Export history entry"""
    export_id: str = Field(..., description="Export ID")
    timeline_id: str = Field(..., description="Timeline ID")
    timeline_name: str = Field(..., description="Timeline name")
    format: str = Field(..., description="Export format")
    status: ExportStatus = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Creation time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration: Optional[float] = Field(None, description="Export duration in seconds")
    file_size: Optional[int] = Field(None, description="Export file size in bytes")
    created_by: str = Field(..., description="User who created the export")


class ExportQueueInfo(BaseModel):
    """Export queue information"""
    queue_length: int = Field(..., description="Number of jobs in queue")
    processing_jobs: int = Field(..., description="Number of jobs currently processing")
    estimated_wait_time: int = Field(..., description="Estimated wait time in seconds")
    queue_status: str = Field(..., description="Queue status")


class ExportCapabilities(BaseModel):
    """Export capabilities for a format"""
    format: str = Field(..., description="Export format")
    supports_video: bool = Field(..., description="Supports video tracks")
    supports_audio: bool = Field(..., description="Supports audio tracks")
    supports_effects: bool = Field(..., description="Supports effects")
    supports_transitions: bool = Field(..., description="Supports transitions")
    supports_metadata: bool = Field(..., description="Supports metadata")
    max_video_tracks: Optional[int] = Field(None, description="Maximum video tracks")
    max_audio_tracks: Optional[int] = Field(None, description="Maximum audio tracks")
    supported_codecs: List[str] = Field(default_factory=list, description="Supported codecs")
    supported_resolutions: List[str] = Field(default_factory=list, description="Supported resolutions")
    supported_frame_rates: List[float] = Field(default_factory=list, description="Supported frame rates")


class ExportNotification(BaseModel):
    """Export notification"""
    notification_id: str = Field(..., description="Notification ID")
    export_id: str = Field(..., description="Export ID")
    user_id: str = Field(..., description="User ID")
    type: str = Field(..., description="Notification type")
    message: str = Field(..., description="Notification message")
    created_at: datetime = Field(..., description="Creation time")
    read: bool = Field(default=False, description="Whether notification has been read")


class ExportSettings(BaseModel):
    """Export settings"""
    format: ExportFormat = Field(..., description="Export format")
    quality: str = Field(default="high", description="Export quality")
    include_media: bool = Field(default=True, description="Include media references")
    include_effects: bool = Field(default=True, description="Include effects")
    include_audio: bool = Field(default=True, description="Include audio tracks")
    frame_rate: Optional[float] = Field(None, description="Frame rate override")
    resolution: Optional[str] = Field(None, description="Resolution override")
    compression: Optional[str] = Field(None, description="Compression settings")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom settings")


# Marketplace Schemas
class BaseResponse(BaseModel):
    """Base response model"""
    pass


class SingleResponse(BaseResponse):
    """Single item response"""
    data: Dict[str, Any]


class ListResponse(BaseResponse):
    """List response with metadata"""
    data: List[Dict[str, Any]]
    meta: Dict[str, Any] = Field(default_factory=dict)
    links: Optional[Dict[str, str]] = None


# API Listing Responses
class APIListingResponse(SingleResponse):
    """API Listing single response"""
    pass


class APIListingListResponse(ListResponse):
    """API Listing list response"""
    pass


# Marketplace Responses
class MarketplaceStatsResponse(SingleResponse):
    """Marketplace statistics response"""
    pass


# Integration Responses  
class IntegrationResponse(SingleResponse):
    """Integration single response"""
    pass


class IntegrationListResponse(ListResponse):
    """Integration list response"""
    pass


# Webhook Responses
class WebhookResponse(SingleResponse):
    """Webhook single response"""
    pass


class WebhookListResponse(ListResponse):
    """Webhook list response"""
    pass


# GraphQL Responses
class GraphQLSchemaResponse(SingleResponse):
    """GraphQL schema response"""
    pass


# gRPC Responses
class GRPCServiceResponse(SingleResponse):
    """gRPC service response"""
    pass


# Test Response
class TestResultResponse(SingleResponse):
    """Test result response"""
    pass


# Error Response
class ErrorResponse(BaseModel):
    """Error response model"""
    error: Dict[str, Any] = Field(
        ...,
        example={
            "code": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": {},
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )