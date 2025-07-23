"""
Pydantic schemas for the Ingest Service
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
import uuid


class IngestStatus(str, Enum):
    """Ingest job status"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    EXTRACTING_METADATA = "extracting_metadata"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class IngestType(str, Enum):
    """Type of ingest operation"""
    SINGLE_FILE = "single_file"
    BULK_UPLOAD = "bulk_upload"
    WATCH_FOLDER = "watch_folder"
    HOT_FOLDER = "hot_folder"
    CAMERA_CARD = "camera_card"
    LIVE_STREAM = "live_stream"
    SCHEDULED = "scheduled"


class IngestPriority(str, Enum):
    """Ingest priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class FileType(str, Enum):
    """Supported file types"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class ProxyType(str, Enum):
    """Proxy types"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EDIT = "edit"


class CameraCardType(str, Enum):
    """Supported camera card types"""
    P2 = "p2"
    XDCAM = "xdcam"
    SXS = "sxs"
    CFEXPRESS = "cfexpress"
    SDXC = "sdxc"
    MICROSD = "microsd"


class ValidationRule(BaseModel):
    """File validation rule"""
    rule_type: str  # file_size, format, checksum, virus, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    error_level: str = "error"  # error, warning, info


class ChecksumInfo(BaseModel):
    """File checksum information"""
    algorithm: str
    value: str
    verified: bool = False
    verification_time: Optional[datetime] = None


class FileMetadata(BaseModel):
    """Basic file metadata"""
    filename: str
    file_size: int
    file_type: FileType
    mime_type: Optional[str] = None
    extension: str
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    checksums: List[ChecksumInfo] = Field(default_factory=list)


class TechnicalMetadata(BaseModel):
    """Technical metadata for media files"""
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[str] = None
    frame_rate: Optional[float] = None
    bit_rate: Optional[int] = None
    codec: Optional[str] = None
    color_space: Optional[str] = None
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    audio_bit_depth: Optional[int] = None


class CameraMetadata(BaseModel):
    """Camera-specific metadata"""
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    iso: Optional[int] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    focal_length: Optional[float] = None
    white_balance: Optional[str] = None
    recording_format: Optional[str] = None
    timecode: Optional[str] = None
    reel_name: Optional[str] = None
    clip_name: Optional[str] = None


class SpannedClipInfo(BaseModel):
    """Information about spanned clips"""
    clip_id: str
    span_index: int
    total_spans: int
    is_complete: bool = False
    related_files: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """File validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    virus_scan_result: Optional[str] = None
    checksum_verified: bool = False
    format_supported: bool = True
    size_within_limits: bool = True


class IngestJobCreate(BaseModel):
    """Create ingest job request"""
    source_path: str
    destination_project_id: Optional[str] = None
    ingest_type: IngestType = IngestType.SINGLE_FILE
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_override: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = False
    
    # Camera card specific
    camera_card_type: Optional[CameraCardType] = None
    camera_card_path: Optional[str] = None
    
    # Live ingest specific
    stream_url: Optional[str] = None
    growing_file_timeout: Optional[int] = None
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    repeat_interval: Optional[int] = None  # seconds


class IngestJobUpdate(BaseModel):
    """Update ingest job request"""
    status: Optional[IngestStatus] = None
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    current_operation: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IngestJob(BaseModel):
    """Ingest job response"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    destination_project_id: Optional[str] = None
    ingest_type: IngestType
    status: IngestStatus = IngestStatus.PENDING
    progress_percentage: float = 0.0
    current_operation: str = "Initializing"
    
    # File information
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_size: int = 0
    processed_size: int = 0
    
    # Results
    created_assets: List[str] = Field(default_factory=list)
    validation_results: List[ValidationResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Metadata
    file_metadata: Optional[FileMetadata] = None
    technical_metadata: Optional[TechnicalMetadata] = None
    camera_metadata: Optional[CameraMetadata] = None
    spanned_clip_info: Optional[SpannedClipInfo] = None
    
    # Processing options
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_override: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    priority: int = 5
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # User context
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None


class IngestJobList(BaseModel):
    """List of ingest jobs"""
    jobs: List[IngestJob]
    total: int
    page: int
    per_page: int
    total_pages: int


class IngestStats(BaseModel):
    """Ingest service statistics"""
    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_files_processed: int = 0
    total_size_processed: int = 0
    average_processing_time: float = 0.0
    success_rate: float = 0.0
    
    # Current status
    queue_depth: int = 0
    active_workers: int = 0
    system_load: float = 0.0
    
    # Time-based stats
    jobs_today: int = 0
    jobs_this_week: int = 0
    jobs_this_month: int = 0


class WatchFolderConfig(BaseModel):
    """Watch folder configuration for monitoring and automatic ingestion"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    path: str
    enabled: bool = True
    recursive: bool = True
    destination_project_id: Optional[str] = None
    
    # File filtering
    include_patterns: List[str] = Field(default_factory=list)  # file patterns to include
    exclude_patterns: List[str] = Field(default_factory=list)  # file patterns to exclude
    
    # Processing configuration
    stability_delay: float = Field(default=5.0, ge=1.0, le=60.0)  # seconds to wait for file stability
    
    # Configuration
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_template: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    priority: IngestPriority = IngestPriority.NORMAL
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = True
    
    # Cleanup options
    auto_delete_source: bool = False
    process_existing_files: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HotFolderConfig(BaseModel):
    """Hot folder configuration for immediate processing"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    path: str
    enabled: bool = True
    recursive: bool = True
    destination_project_id: Optional[str] = None
    
    # Processing configuration
    immediate_processing: bool = True
    immediate_processing_delay: float = Field(default=0.5, ge=0.1, le=10.0)  # seconds
    check_file_stability: bool = True
    stability_check_interval: float = Field(default=1.0, ge=0.5, le=5.0)  # seconds
    
    # File handling
    include_patterns: List[str] = Field(default_factory=list)  # file patterns to include
    exclude_patterns: List[str] = Field(default_factory=list)  # file patterns to exclude
    
    # Post-processing actions
    move_after_processing: bool = False
    processed_folder: Optional[str] = None
    delete_after_processing: bool = False
    
    # Configuration
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_template: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    priority: IngestPriority = IngestPriority.HIGH
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledIngestConfig(BaseModel):
    """Scheduled ingest configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source_path: str
    destination_project_id: Optional[str] = None
    cron_expression: str
    enabled: bool = True
    
    # Configuration
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_template: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    priority: IngestPriority = IngestPriority.NORMAL
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = True
    
    # Execution tracking
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestNotification(BaseModel):
    """Ingest notification message"""
    job_id: str
    event_type: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None


class BulkIngestRequest(BaseModel):
    """Bulk ingest request"""
    source_paths: List[str]
    destination_project_id: Optional[str] = None
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    metadata_template: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    auto_generate_proxies: bool = True
    preserve_folder_structure: bool = True
    parallel_processing: bool = True
    max_concurrent: int = Field(default=3, ge=1, le=10)


class CameraCardInfo(BaseModel):
    """Camera card information and contents"""
    
    class ClipInfo(BaseModel):
        """Individual clip information on camera card"""
        clip_name: str
        file_path: str
        file_size: int
        created_at: datetime
        duration: Optional[str] = None
        resolution: Optional[Dict[str, str]] = None
        frame_rate: Optional[str] = None
        codec: Optional[str] = None
        metadata: Dict[str, Any] = Field(default_factory=dict)
        
        # Associated files
        proxy_path: Optional[str] = None
        audio_path: Optional[str] = None
        thumbnail_path: Optional[str] = None
    
    card_path: str
    card_type: CameraCardType
    detected_at: datetime
    clips: List[ClipInfo] = Field(default_factory=list)
    total_files: int = 0
    total_size: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)