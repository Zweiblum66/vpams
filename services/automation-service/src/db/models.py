"""Database models for Broadcast Automation Service"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime

from .base import Base


class DeviceType(str, enum.Enum):
    """Device type enumeration"""
    SWITCHER = "switcher"
    CAMERA = "camera"
    AUDIO_MIXER = "audio_mixer"
    GRAPHICS = "graphics"
    LIGHTING = "lighting"
    ROUTER = "router"
    RECORDER = "recorder"
    PLAYOUT = "playout"
    OTHER = "other"


class DeviceStatus(str, enum.Enum):
    """Device status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ConnectionType(str, enum.Enum):
    """Connection type enumeration"""
    TCP = "tcp"
    UDP = "udp"
    SERIAL = "serial"
    HTTP = "http"
    WEBSOCKET = "websocket"
    NDI = "ndi"
    EMBER = "ember"
    OTHER = "other"


class MacroStatus(str, enum.Enum):
    """Macro execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class CueStatus(str, enum.Enum):
    """Show cue status"""
    READY = "ready"
    ARMED = "armed"
    ACTIVE = "active"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    ERROR = "error"


class Device(Base):
    """Automation device model"""
    __tablename__ = "automation_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Device info
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100))
    firmware_version = Column(String(50))
    
    # Connection info
    connection_type = Column(SQLEnum(ConnectionType), nullable=False)
    host = Column(String(255))
    port = Column(Integer)
    path = Column(String(500))  # For serial devices or HTTP endpoints
    
    # Authentication
    username = Column(String(100))
    password = Column(String(255))  # Encrypted
    api_key = Column(String(255))   # Encrypted
    
    # Protocol settings
    protocol = Column(String(50))
    protocol_version = Column(String(20))
    protocol_config = Column(JSONB, default=dict)
    
    # Status
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime(timezone=True))
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Capabilities
    capabilities = Column(JSONB, default=list)
    supported_commands = Column(JSONB, default=list)
    
    # Configuration
    config = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    presets = relationship("DevicePreset", back_populates="device")
    commands = relationship("CommandLog", back_populates="device")
    
    # Indexes
    __table_args__ = (
        Index('idx_device_type', 'device_type'),
        Index('idx_device_status', 'status'),
        Index('idx_device_active', 'is_active'),
    )


class DevicePreset(Base):
    """Device preset storage"""
    __tablename__ = "device_presets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("automation_devices.id"), nullable=False)
    
    # Preset info
    preset_number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Preset data
    preset_data = Column(JSONB, nullable=False)
    thumbnail_url = Column(String(500))
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True))
    use_count = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSONB, default=list)
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="presets")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('device_id', 'preset_number', name='uq_device_preset'),
        Index('idx_preset_device', 'device_id'),
        Index('idx_preset_last_used', 'last_used'),
    )


class Macro(Base):
    """Automation macro definition"""
    __tablename__ = "automation_macros"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Macro details
    description = Column(Text)
    category = Column(String(100))
    version = Column(Integer, default=1)
    
    # Macro definition
    triggers = Column(JSONB, default=list)
    actions = Column(JSONB, default=list)
    conditions = Column(JSONB, default=list)
    
    # Execution settings
    timeout_seconds = Column(Integer, default=300)
    allow_concurrent = Column(Boolean, default=False)
    max_retries = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Permissions
    required_role = Column(String(50))
    allowed_users = Column(JSONB, default=list)
    
    # Metadata
    tags = Column(JSONB, default=list)
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    executions = relationship("MacroExecution", back_populates="macro")
    scheduled_executions = relationship("ScheduledExecution", back_populates="macro")
    
    # Indexes
    __table_args__ = (
        Index('idx_macro_category', 'category'),
        Index('idx_macro_active', 'is_active'),
        Index('idx_macro_system', 'is_system'),
    )


class MacroExecution(Base):
    """Macro execution history"""
    __tablename__ = "macro_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    macro_id = Column(UUID(as_uuid=True), ForeignKey("automation_macros.id"), nullable=False)
    
    # Execution info
    execution_id = Column(String(100), unique=True, nullable=False)
    status = Column(SQLEnum(MacroStatus), nullable=False)
    
    # Trigger info
    trigger_type = Column(String(50))
    trigger_source = Column(String(255))
    trigger_data = Column(JSONB, default=dict)
    
    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    
    # Results
    actions_executed = Column(Integer, default=0)
    actions_failed = Column(Integer, default=0)
    error_message = Column(Text)
    execution_log = Column(JSONB, default=list)
    
    # User info
    executed_by = Column(UUID(as_uuid=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    macro = relationship("Macro", back_populates="executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_macro', 'macro_id'),
        Index('idx_execution_status', 'status'),
        Index('idx_execution_started', 'started_at'),
    )


class Show(Base):
    """Show control definition"""
    __tablename__ = "automation_shows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Show info
    description = Column(Text)
    show_type = Column(String(50))
    duration_seconds = Column(Integer)
    
    # Configuration
    default_rehearsal_mode = Column(Boolean, default=False)
    allow_manual_override = Column(Boolean, default=True)
    auto_continue = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    tags = Column(JSONB, default=list)
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    cues = relationship("ShowCue", back_populates="show", order_by="ShowCue.cue_number")
    
    # Indexes
    __table_args__ = (
        Index('idx_show_type', 'show_type'),
        Index('idx_show_active', 'is_active'),
    )


class ShowCue(Base):
    """Individual cue in a show"""
    __tablename__ = "show_cues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    show_id = Column(UUID(as_uuid=True), ForeignKey("automation_shows.id"), nullable=False)
    
    # Cue identification
    cue_number = Column(Float, nullable=False)
    cue_label = Column(String(50))
    name = Column(String(255), nullable=False)
    
    # Cue type and content
    cue_type = Column(String(50), nullable=False)  # macro, wait, note, etc.
    target_id = Column(UUID(as_uuid=True))  # Macro ID or other target
    
    # Timing
    pre_wait = Column(Float, default=0)  # Seconds
    post_wait = Column(Float, default=0)  # Seconds
    auto_follow = Column(Boolean, default=False)
    auto_follow_time = Column(Float)  # Seconds
    
    # Execution settings
    continue_mode = Column(String(20), default="manual")  # manual, auto, timed
    
    # Status
    status = Column(SQLEnum(CueStatus), default=CueStatus.READY)
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    show = relationship("Show", back_populates="cues")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('show_id', 'cue_number', name='uq_show_cue_number'),
        Index('idx_cue_show', 'show_id'),
        Index('idx_cue_type', 'cue_type'),
        Index('idx_cue_status', 'status'),
    )


class CommandLog(Base):
    """Device command history"""
    __tablename__ = "command_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("automation_devices.id"), nullable=False)
    
    # Command info
    command = Column(String(100), nullable=False)
    parameters = Column(JSONB, default=dict)
    
    # Execution info
    status = Column(String(20), nullable=False)  # sent, acknowledged, completed, failed
    sent_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Response
    response_data = Column(JSONB)
    error_message = Column(Text)
    
    # Context
    source = Column(String(50))  # manual, macro, show, schedule
    source_id = Column(UUID(as_uuid=True))
    user_id = Column(UUID(as_uuid=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    device = relationship("Device", back_populates="commands")
    
    # Indexes
    __table_args__ = (
        Index('idx_command_device', 'device_id'),
        Index('idx_command_sent', 'sent_at'),
        Index('idx_command_status', 'status'),
        Index('idx_command_source', 'source', 'source_id'),
    )


class ScheduledExecution(Base):
    """Scheduled macro executions"""
    __tablename__ = "scheduled_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    macro_id = Column(UUID(as_uuid=True), ForeignKey("automation_macros.id"), nullable=False)
    
    # Schedule info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Timing
    schedule_type = Column(String(50), nullable=False)  # once, daily, weekly, cron
    schedule_data = Column(JSONB, nullable=False)
    next_execution = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_execution = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    macro = relationship("Macro", back_populates="scheduled_executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_scheduled_macro', 'macro_id'),
        Index('idx_scheduled_active', 'is_active'),
        Index('idx_scheduled_next', 'next_execution'),
    )


class DeviceGroup(Base):
    """Device grouping for bulk operations"""
    __tablename__ = "device_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Group info
    description = Column(Text)
    group_type = Column(String(50))
    
    # Members
    device_ids = Column(JSONB, default=list)
    
    # Configuration
    sync_commands = Column(Boolean, default=False)
    command_delay_ms = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_group_type', 'group_type'),
    )


class EmergencyOverride(Base):
    """Emergency override log"""
    __tablename__ = "emergency_overrides"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Override info
    override_type = Column(String(50), nullable=False)  # stop_all, manual_control, etc.
    reason = Column(Text, nullable=False)
    
    # User info
    initiated_by = Column(UUID(as_uuid=True), nullable=False)
    authorized_by = Column(UUID(as_uuid=True))
    
    # Timing
    initiated_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True))
    
    # Actions taken
    actions = Column(JSONB, default=list)
    affected_devices = Column(JSONB, default=list)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_override_type', 'override_type'),
        Index('idx_override_time', 'initiated_at'),
    )