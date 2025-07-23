"""Pydantic schemas for Playout Integration Service"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID
import enum

from ..db.models import (
    PlayoutSystemType, PlayoutProtocol, ScheduleStatus,
    ContentStatus, TransferStatus, DeviceStatus
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common fields"""
    class Config:
        from_attributes = True
        use_enum_values = True


# Playout System schemas
class PlayoutSystemBase(BaseSchema):
    """Base playout system schema"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    system_type: PlayoutSystemType
    vendor: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    
    # Connection
    protocol: PlayoutProtocol
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    api_url: Optional[str] = Field(None, max_length=500)
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    channels: List[Dict[str, Any]] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlayoutSystemCreate(PlayoutSystemBase):
    """Schema for creating playout system"""
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class PlayoutSystemUpdate(BaseSchema):
    """Schema for updating playout system"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vendor: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    
    # Connection
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    api_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Configuration
    config: Optional[Dict[str, Any]] = None
    channels: Optional[List[Dict[str, Any]]] = None
    capabilities: Optional[List[str]] = None
    
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class PlayoutSystemResponse(PlayoutSystemBase):
    """Playout system response schema"""
    id: UUID
    is_active: bool
    is_primary: bool
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Stats
    device_count: Optional[int] = None
    active_schedules: Optional[int] = None


# Device schemas
class DeviceBase(BaseSchema):
    """Base device schema"""
    name: str = Field(..., min_length=1, max_length=255)
    device_id: str = Field(..., min_length=1, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    
    # Channel
    channel: Optional[int] = Field(None, ge=1)
    channel_name: Optional[str] = Field(None, max_length=100)
    
    # Capabilities
    storage_path: Optional[str] = Field(None, max_length=500)
    supported_formats: List[str] = Field(default_factory=list)
    
    # Connection
    ip_address: Optional[str] = Field(None, max_length=45)
    control_port: Optional[int] = Field(None, ge=1, le=65535)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    """Schema for creating device"""
    playout_system_id: UUID
    is_backup: bool = Field(default=False)


class DeviceUpdate(BaseSchema):
    """Schema for updating device"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    device_type: Optional[str] = Field(None, max_length=50)
    
    # Channel
    channel: Optional[int] = Field(None, ge=1)
    channel_name: Optional[str] = Field(None, max_length=100)
    
    # Status
    is_active: Optional[bool] = None
    is_backup: Optional[bool] = None
    
    # Capabilities
    storage_path: Optional[str] = Field(None, max_length=500)
    supported_formats: Optional[List[str]] = None
    
    # Connection
    ip_address: Optional[str] = Field(None, max_length=45)
    control_port: Optional[int] = Field(None, ge=1, le=65535)
    
    metadata: Optional[Dict[str, Any]] = None


class DeviceResponse(DeviceBase):
    """Device response schema"""
    id: UUID
    playout_system_id: UUID
    status: DeviceStatus
    is_active: bool
    is_backup: bool
    
    # Storage
    storage_total_gb: Optional[float] = None
    storage_used_gb: Optional[float] = None
    
    # Monitoring
    last_status_check: Optional[datetime] = None
    last_error: Optional[str] = None
    uptime_seconds: Optional[int] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# Schedule schemas
class ScheduleBase(BaseSchema):
    """Base schedule schema"""
    name: str = Field(..., min_length=1, max_length=255)
    schedule_date: datetime
    channel: Optional[int] = Field(None, ge=1)
    channel_name: Optional[str] = Field(None, max_length=100)
    
    # Import info
    imported_from: Optional[str] = Field(None, max_length=100)
    import_file: Optional[str] = Field(None, max_length=500)
    import_data: Optional[Dict[str, Any]] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ScheduleCreate(ScheduleBase):
    """Schema for creating schedule"""
    playout_system_id: UUID


class ScheduleUpdate(BaseSchema):
    """Schema for updating schedule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    channel: Optional[int] = Field(None, ge=1)
    channel_name: Optional[str] = Field(None, max_length=100)
    
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ScheduleResponse(ScheduleBase):
    """Schedule response schema"""
    id: UUID
    playout_system_id: UUID
    status: ScheduleStatus
    is_locked: bool
    
    # Validation
    is_validated: bool
    validation_errors: List[Dict[str, Any]]
    validated_at: Optional[datetime] = None
    validated_by: Optional[UUID] = None
    
    # Publishing
    published_at: Optional[datetime] = None
    published_by: Optional[UUID] = None
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Stats
    item_count: Optional[int] = None
    total_duration: Optional[int] = None


# Schedule Item schemas
class ScheduleItemBase(BaseSchema):
    """Base schedule item schema"""
    position: int = Field(..., ge=0)
    scheduled_time: datetime
    duration: int = Field(..., gt=0)
    
    # Content
    content_id: str = Field(..., min_length=1, max_length=255)
    house_id: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    
    # Technical
    som: Optional[str] = Field(None, max_length=20)
    eom: Optional[str] = Field(None, max_length=20)
    duration_tc: Optional[str] = Field(None, max_length=20)
    
    # Type
    item_type: str = Field(default="content", max_length=50)
    is_filler: bool = Field(default=False)
    
    # Secondary events
    secondary_events: List[Dict[str, Any]] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScheduleItemCreate(ScheduleItemBase):
    """Schema for creating schedule item"""
    schedule_id: UUID


class ScheduleItemUpdate(BaseSchema):
    """Schema for updating schedule item"""
    position: Optional[int] = Field(None, ge=0)
    scheduled_time: Optional[datetime] = None
    duration: Optional[int] = Field(None, gt=0)
    
    # Content
    house_id: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    
    # Technical
    som: Optional[str] = Field(None, max_length=20)
    eom: Optional[str] = Field(None, max_length=20)
    duration_tc: Optional[str] = Field(None, max_length=20)
    
    # Type
    is_filler: Optional[bool] = None
    
    # Secondary events
    secondary_events: Optional[List[Dict[str, Any]]] = None
    
    metadata: Optional[Dict[str, Any]] = None


class ScheduleItemResponse(ScheduleItemBase):
    """Schedule item response schema"""
    id: UUID
    schedule_id: UUID
    content_status: ContentStatus
    
    # Execution
    played_at: Optional[datetime] = None
    actual_duration: Optional[int] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# Transfer schemas
class TransferBase(BaseSchema):
    """Base transfer schema"""
    content_id: str = Field(..., min_length=1, max_length=255)
    source_path: str = Field(..., min_length=1, max_length=500)
    priority: int = Field(default=5, ge=1, le=10)
    
    needs_validation: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransferCreate(TransferBase):
    """Schema for creating transfer"""
    playout_system_id: UUID
    destination_path: Optional[str] = Field(None, max_length=500)


class TransferUpdate(BaseSchema):
    """Schema for updating transfer"""
    priority: Optional[int] = Field(None, ge=1, le=10)
    needs_validation: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TransferResponse(TransferBase):
    """Transfer response schema"""
    id: UUID
    playout_system_id: UUID
    destination_path: Optional[str] = None
    file_size: Optional[int] = None
    
    # Status
    status: TransferStatus
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Progress
    bytes_transferred: int
    transfer_rate: Optional[float] = None
    percent_complete: float
    
    # Timing
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int
    next_retry_at: Optional[datetime] = None
    
    # Validation
    validation_status: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# As-Run schemas
class AsRunEntry(BaseSchema):
    """As-run log entry schema"""
    event_time: datetime
    event_type: str = Field(..., min_length=1, max_length=50)
    channel: Optional[int] = Field(None, ge=1)
    
    # Content
    content_id: Optional[str] = Field(None, max_length=255)
    house_id: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    
    # Timing
    scheduled_time: Optional[datetime] = None
    actual_time: datetime
    scheduled_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    
    # Status
    status: Optional[str] = Field(None, max_length=50)
    error_message: Optional[str] = None
    
    # Reconciliation
    schedule_item_id: Optional[UUID] = None
    discrepancy_type: Optional[str] = Field(None, max_length=50)
    discrepancy_seconds: Optional[int] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AsRunResponse(AsRunEntry):
    """As-run response schema"""
    id: UUID
    playout_system_id: UUID
    created_at: datetime


# Control commands
class DeviceCommand(BaseSchema):
    """Device control command"""
    command: str = Field(..., min_length=1, max_length=50)
    channel: Optional[int] = Field(None, ge=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class LoadCommand(DeviceCommand):
    """Load content command"""
    command: str = Field(default="load")
    content_id: str = Field(..., min_length=1)
    in_point: Optional[str] = None
    out_point: Optional[str] = None
    preroll: Optional[int] = Field(None, ge=0)


class PlayCommand(DeviceCommand):
    """Play command"""
    command: str = Field(default="play")
    speed: Optional[float] = Field(None, ge=0.0, le=2.0)


# Status responses
class SystemStatus(BaseSchema):
    """System status response"""
    id: UUID
    name: str
    system_type: PlayoutSystemType
    status: str
    is_active: bool
    last_heartbeat: Optional[datetime] = None
    
    devices: List[Dict[str, Any]]
    active_transfers: int
    pending_transfers: int
    active_schedules: int


class TransferProgress(BaseSchema):
    """Transfer progress response"""
    transfer_id: UUID
    content_id: str
    status: TransferStatus
    percent_complete: float
    bytes_transferred: int
    file_size: Optional[int] = None
    transfer_rate: Optional[float] = None
    eta_seconds: Optional[int] = None


class ScheduleValidation(BaseSchema):
    """Schedule validation result"""
    schedule_id: UUID
    is_valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    gaps: List[Dict[str, Any]]
    overlaps: List[Dict[str, Any]]


# Import/Export schemas
class BXFImport(BaseSchema):
    """BXF import request"""
    playout_system_id: UUID
    channel: Optional[int] = None
    bxf_data: str
    validate_only: bool = Field(default=False)


class ScheduleExport(BaseSchema):
    """Schedule export request"""
    format: str = Field(..., pattern="^(bxf|json|csv|xml)$")
    include_metadata: bool = Field(default=True)
    
    
# Alert schemas
class AlertCreate(BaseSchema):
    """Schema for creating alert"""
    playout_system_id: UUID
    device_id: Optional[UUID] = None
    
    alert_type: str = Field(..., max_length=50)
    alert_category: str = Field(..., max_length=50)
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    
    channel: Optional[int] = None
    content_id: Optional[str] = None
    schedule_id: Optional[UUID] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseSchema):
    """Alert response schema"""
    id: UUID
    playout_system_id: UUID
    device_id: Optional[UUID] = None
    
    alert_type: str
    alert_category: str
    severity: str
    
    title: str
    message: str
    
    is_acknowledged: bool
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    
    is_resolved: bool
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    channel: Optional[int] = None
    content_id: Optional[str] = None
    schedule_id: Optional[UUID] = None
    
    metadata: Dict[str, Any]
    
    created_at: datetime
    updated_at: Optional[datetime] = None