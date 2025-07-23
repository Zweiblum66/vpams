"""Pydantic schemas for Broadcast Automation Service"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, UUID4
import uuid
from enum import Enum

from ..db.models import (
    DeviceType,
    DeviceStatus,
    ConnectionType,
    MacroStatus,
    CueStatus,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v) if v else None,
        }


# Device schemas
class DeviceBase(BaseSchema):
    """Base device schema"""
    name: str = Field(..., description="Device name")
    device_type: DeviceType = Field(..., description="Device type")
    manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    model: Optional[str] = Field(None, description="Device model")
    serial_number: Optional[str] = Field(None, description="Serial number")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    connection_type: ConnectionType = Field(..., description="Connection type")
    host: Optional[str] = Field(None, description="Device host/IP")
    port: Optional[int] = Field(None, description="Device port")
    path: Optional[str] = Field(None, description="Device path (serial/HTTP)")
    protocol: Optional[str] = Field(None, description="Control protocol")
    protocol_version: Optional[str] = Field(None, description="Protocol version")
    protocol_config: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)
    supported_commands: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    """Device creation schema"""
    slug: str = Field(..., description="Unique device slug")
    username: Optional[str] = Field(None, description="Device username")
    password: Optional[str] = Field(None, description="Device password")
    api_key: Optional[str] = Field(None, description="Device API key")
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class DeviceUpdate(BaseSchema):
    """Device update schema"""
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    protocol_config: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    supported_commands: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DeviceResponse(DeviceBase):
    """Device response schema"""
    id: UUID4
    slug: str
    status: DeviceStatus
    is_active: bool
    last_seen: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class DeviceStatus(BaseSchema):
    """Device status schema"""
    id: UUID4
    name: str
    device_type: DeviceType
    status: DeviceStatus
    is_active: bool
    last_seen: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int
    connection_info: Dict[str, Any] = Field(default_factory=dict)


# Device Preset schemas
class DevicePresetBase(BaseSchema):
    """Base device preset schema"""
    preset_number: int = Field(..., ge=0, description="Preset number")
    name: str = Field(..., description="Preset name")
    description: Optional[str] = Field(None, description="Preset description")
    preset_data: Dict[str, Any] = Field(..., description="Preset data")
    thumbnail_url: Optional[str] = Field(None, description="Preset thumbnail")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DevicePresetCreate(DevicePresetBase):
    """Device preset creation schema"""
    device_id: UUID4 = Field(..., description="Device ID")


class DevicePresetUpdate(BaseSchema):
    """Device preset update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    preset_data: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DevicePresetResponse(DevicePresetBase):
    """Device preset response schema"""
    id: UUID4
    device_id: UUID4
    last_used: Optional[datetime] = None
    use_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# Macro schemas
class MacroBase(BaseSchema):
    """Base macro schema"""
    name: str = Field(..., description="Macro name")
    description: Optional[str] = Field(None, description="Macro description")
    category: Optional[str] = Field(None, description="Macro category")
    triggers: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(..., min_items=1)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    timeout_seconds: int = Field(300, ge=1, description="Execution timeout")
    allow_concurrent: bool = Field(False, description="Allow concurrent execution")
    max_retries: int = Field(0, ge=0, description="Maximum retries")
    required_role: Optional[str] = Field(None, description="Required role")
    allowed_users: List[UUID4] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MacroCreate(MacroBase):
    """Macro creation schema"""
    slug: str = Field(..., description="Unique macro slug")
    is_active: bool = Field(True, description="Is macro active")
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class MacroUpdate(BaseSchema):
    """Macro update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    triggers: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    timeout_seconds: Optional[int] = None
    allow_concurrent: Optional[bool] = None
    max_retries: Optional[int] = None
    required_role: Optional[str] = None
    allowed_users: Optional[List[UUID4]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MacroResponse(MacroBase):
    """Macro response schema"""
    id: UUID4
    slug: str
    version: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID4] = None


class MacroExecuteRequest(BaseSchema):
    """Macro execution request schema"""
    trigger_type: str = Field("manual", description="Trigger type")
    trigger_source: Optional[str] = Field(None, description="Trigger source")
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    override_timeout: Optional[int] = Field(None, description="Override timeout")


class MacroExecutionResponse(BaseSchema):
    """Macro execution response schema"""
    id: UUID4
    macro_id: UUID4
    execution_id: str
    status: MacroStatus
    trigger_type: Optional[str] = None
    trigger_source: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    actions_executed: int
    actions_failed: int
    error_message: Optional[str] = None
    execution_log: List[Dict[str, Any]]
    executed_by: Optional[UUID4] = None


# Show Control schemas
class ShowBase(BaseSchema):
    """Base show schema"""
    name: str = Field(..., description="Show name")
    description: Optional[str] = Field(None, description="Show description")
    show_type: Optional[str] = Field(None, description="Show type")
    duration_seconds: Optional[int] = Field(None, description="Show duration")
    default_rehearsal_mode: bool = Field(False, description="Default to rehearsal")
    allow_manual_override: bool = Field(True, description="Allow manual override")
    auto_continue: bool = Field(True, description="Auto-continue cues")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShowCreate(ShowBase):
    """Show creation schema"""
    slug: str = Field(..., description="Unique show slug")
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class ShowUpdate(BaseSchema):
    """Show update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    show_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    default_rehearsal_mode: Optional[bool] = None
    allow_manual_override: Optional[bool] = None
    auto_continue: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_locked: Optional[bool] = None


class ShowResponse(ShowBase):
    """Show response schema"""
    id: UUID4
    slug: str
    is_active: bool
    is_locked: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID4] = None
    cue_count: int = Field(0, description="Number of cues")


# Show Cue schemas
class ShowCueBase(BaseSchema):
    """Base show cue schema"""
    cue_number: float = Field(..., description="Cue number")
    cue_label: Optional[str] = Field(None, description="Cue label")
    name: str = Field(..., description="Cue name")
    cue_type: str = Field(..., description="Cue type")
    target_id: Optional[UUID4] = Field(None, description="Target ID (macro, etc)")
    pre_wait: float = Field(0, ge=0, description="Pre-wait in seconds")
    post_wait: float = Field(0, ge=0, description="Post-wait in seconds")
    auto_follow: bool = Field(False, description="Auto-follow next cue")
    auto_follow_time: Optional[float] = Field(None, description="Auto-follow time")
    continue_mode: str = Field("manual", description="Continue mode")
    notes: Optional[str] = Field(None, description="Cue notes")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShowCueCreate(ShowCueBase):
    """Show cue creation schema"""
    show_id: UUID4 = Field(..., description="Show ID")


class ShowCueUpdate(BaseSchema):
    """Show cue update schema"""
    cue_number: Optional[float] = None
    cue_label: Optional[str] = None
    name: Optional[str] = None
    cue_type: Optional[str] = None
    target_id: Optional[UUID4] = None
    pre_wait: Optional[float] = None
    post_wait: Optional[float] = None
    auto_follow: Optional[bool] = None
    auto_follow_time: Optional[float] = None
    continue_mode: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class ShowCueResponse(ShowCueBase):
    """Show cue response schema"""
    id: UUID4
    show_id: UUID4
    status: CueStatus
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Command schemas
class DeviceCommand(BaseSchema):
    """Device command schema"""
    device_id: UUID4 = Field(..., description="Device ID")
    command: str = Field(..., description="Command name")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(0, description="Command priority")
    timeout: Optional[int] = Field(None, description="Command timeout")


class CommandResponse(BaseSchema):
    """Command response schema"""
    command_id: UUID4
    device_id: UUID4
    command: str
    parameters: Dict[str, Any]
    status: str
    sent_at: datetime
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# Control schemas
class PTZControl(BaseSchema):
    """PTZ control schema"""
    pan: Optional[float] = Field(None, ge=-180, le=180, description="Pan angle")
    tilt: Optional[float] = Field(None, ge=-90, le=90, description="Tilt angle")
    zoom: Optional[float] = Field(None, ge=0, le=100, description="Zoom level")
    speed: float = Field(0.5, ge=0, le=1, description="Movement speed")
    relative: bool = Field(False, description="Relative movement")


class FocusControl(BaseSchema):
    """Focus control schema"""
    focus: Optional[float] = Field(None, ge=0, le=100, description="Focus position")
    auto_focus: Optional[bool] = Field(None, description="Auto-focus enable")
    speed: float = Field(0.5, ge=0, le=1, description="Focus speed")


class IrisControl(BaseSchema):
    """Iris control schema"""
    iris: Optional[float] = Field(None, ge=0, le=100, description="Iris position")
    auto_iris: Optional[bool] = Field(None, description="Auto-iris enable")


class AudioFaderControl(BaseSchema):
    """Audio fader control schema"""
    channel: Union[int, str] = Field(..., description="Channel number or name")
    level: float = Field(..., ge=-100, le=10, description="Fader level in dB")
    duration: int = Field(0, ge=0, description="Fade duration in ms")
    curve: str = Field("linear", description="Fade curve type")


class SwitcherControl(BaseSchema):
    """Switcher control schema"""
    source: Union[int, str] = Field(..., description="Source input")
    bus: str = Field("program", description="Target bus")
    transition_type: str = Field("cut", description="Transition type")
    duration: int = Field(0, ge=0, description="Transition duration in ms")


# Scheduled execution schemas
class ScheduledExecutionBase(BaseSchema):
    """Base scheduled execution schema"""
    name: str = Field(..., description="Schedule name")
    description: Optional[str] = Field(None, description="Schedule description")
    schedule_type: str = Field(..., description="Schedule type")
    schedule_data: Dict[str, Any] = Field(..., description="Schedule configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScheduledExecutionCreate(ScheduledExecutionBase):
    """Scheduled execution creation schema"""
    macro_id: UUID4 = Field(..., description="Macro ID")
    is_active: bool = Field(True, description="Is schedule active")


class ScheduledExecutionUpdate(BaseSchema):
    """Scheduled execution update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ScheduledExecutionResponse(ScheduledExecutionBase):
    """Scheduled execution response schema"""
    id: UUID4
    macro_id: UUID4
    is_active: bool
    next_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    execution_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID4] = None


# Device group schemas
class DeviceGroupBase(BaseSchema):
    """Base device group schema"""
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    group_type: Optional[str] = Field(None, description="Group type")
    device_ids: List[UUID4] = Field(default_factory=list)
    sync_commands: bool = Field(False, description="Sync commands across devices")
    command_delay_ms: int = Field(0, ge=0, description="Delay between commands")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceGroupCreate(DeviceGroupBase):
    """Device group creation schema"""
    slug: str = Field(..., description="Unique group slug")
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class DeviceGroupUpdate(BaseSchema):
    """Device group update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    group_type: Optional[str] = None
    device_ids: Optional[List[UUID4]] = None
    sync_commands: Optional[bool] = None
    command_delay_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class DeviceGroupResponse(DeviceGroupBase):
    """Device group response schema"""
    id: UUID4
    slug: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# Emergency override schemas
class EmergencyOverrideRequest(BaseSchema):
    """Emergency override request schema"""
    override_type: str = Field(..., description="Override type")
    reason: str = Field(..., description="Override reason")
    pin: Optional[str] = Field(None, description="Emergency PIN")


class EmergencyOverrideResponse(BaseSchema):
    """Emergency override response schema"""
    id: UUID4
    override_type: str
    reason: str
    initiated_by: UUID4
    authorized_by: Optional[UUID4] = None
    initiated_at: datetime
    released_at: Optional[datetime] = None
    actions: List[Dict[str, Any]]
    affected_devices: List[UUID4]


# Discovery schemas
class DiscoveryRequest(BaseSchema):
    """Device discovery request schema"""
    protocols: List[str] = Field(default_factory=list, description="Discovery protocols")
    timeout: int = Field(30, ge=1, description="Discovery timeout")
    filters: Dict[str, Any] = Field(default_factory=dict)


class DiscoveredDevice(BaseSchema):
    """Discovered device schema"""
    name: str
    device_type: DeviceType
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    host: str
    port: Optional[int] = None
    protocol: str
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# WebSocket message schemas
class WSMessage(BaseSchema):
    """WebSocket message schema"""
    type: str = Field(..., description="Message type")
    device: Optional[str] = Field(None, description="Device ID or slug")
    command: Optional[str] = Field(None, description="Command name")
    params: Optional[Dict[str, Any]] = Field(None, description="Command parameters")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class WSResponse(BaseSchema):
    """WebSocket response schema"""
    type: str = Field(..., description="Response type")
    request_id: Optional[str] = Field(None, description="Request ID")
    status: str = Field(..., description="Response status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Pagination schemas
class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset"""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper"""
    data: List[Any] = Field(..., description="Response data")
    meta: Dict[str, Any] = Field(..., description="Pagination metadata")
    links: Dict[str, Optional[str]] = Field(..., description="Pagination links")