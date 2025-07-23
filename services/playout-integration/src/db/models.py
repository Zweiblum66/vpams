"""Database models for Playout Integration Service"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class PlayoutSystemType(str, enum.Enum):
    """Playout system types enumeration"""
    GRASS_VALLEY = "grass_valley"
    HARMONIC = "harmonic"
    IMAGINE = "imagine"
    EVERTZ = "evertz"
    PEBBLE_BEACH = "pebble_beach"
    PLAYBOX = "playbox"
    AVECO = "aveco"
    GENERIC = "generic"


class PlayoutProtocol(str, enum.Enum):
    """Playout control protocols"""
    VDCP = "vdcp"
    MOS = "mos"
    BXF = "bxf"
    REST_API = "rest_api"
    PROPRIETARY = "proprietary"
    FTP = "ftp"
    SFTP = "sftp"


class ScheduleStatus(str, enum.Enum):
    """Schedule status enumeration"""
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ContentStatus(str, enum.Enum):
    """Content delivery status"""
    PENDING = "pending"
    QUEUED = "queued"
    TRANSFERRING = "transferring"
    TRANSFERRED = "transferred"
    VALIDATED = "validated"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class TransferStatus(str, enum.Enum):
    """Transfer status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class DeviceStatus(str, enum.Enum):
    """Device status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class PlayoutSystem(Base):
    """Playout system configuration"""
    __tablename__ = "playout_systems"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # System info
    system_type = Column(SQLEnum(PlayoutSystemType), nullable=False)
    vendor = Column(String(100))
    model = Column(String(100))
    version = Column(String(50))
    
    # Connection info
    protocol = Column(SQLEnum(PlayoutProtocol), nullable=False)
    host = Column(String(255))
    port = Column(Integer)
    api_url = Column(String(500))
    api_key = Column(String(255))
    username = Column(String(100))
    password = Column(String(255))  # Encrypted
    
    # Configuration
    config = Column(JSONB, default=dict)
    channels = Column(JSONB, default=list)  # List of channel configurations
    capabilities = Column(JSONB, default=list)  # List of supported features
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schedules = relationship("PlayoutSchedule", back_populates="playout_system")
    devices = relationship("PlayoutDevice", back_populates="playout_system")
    transfers = relationship("ContentTransfer", back_populates="playout_system")


class PlayoutDevice(Base):
    """Physical playout device/server"""
    __tablename__ = "playout_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    
    # Device info
    name = Column(String(255), nullable=False)
    device_id = Column(String(100), nullable=False)  # Vendor-specific ID
    device_type = Column(String(50))  # server, controller, router, etc.
    
    # Channel assignment
    channel = Column(Integer)
    channel_name = Column(String(100))
    
    # Status
    status = Column(SQLEnum(DeviceStatus), nullable=False, default=DeviceStatus.UNKNOWN)
    is_active = Column(Boolean, default=True, nullable=False)
    is_backup = Column(Boolean, default=False, nullable=False)
    
    # Capabilities
    storage_path = Column(String(500))
    storage_total_gb = Column(Float)
    storage_used_gb = Column(Float)
    supported_formats = Column(JSONB, default=list)
    
    # Connection
    ip_address = Column(String(45))
    control_port = Column(Integer)
    
    # Monitoring
    last_status_check = Column(DateTime(timezone=True))
    last_error = Column(Text)
    uptime_seconds = Column(Integer)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    playout_system = relationship("PlayoutSystem", back_populates="devices")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('playout_system_id', 'device_id', name='uq_device_system'),
        Index('idx_device_status', 'status'),
        Index('idx_device_channel', 'channel'),
    )


class PlayoutSchedule(Base):
    """Playout schedule"""
    __tablename__ = "playout_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    
    # Schedule info
    name = Column(String(255), nullable=False)
    schedule_date = Column(DateTime(timezone=True), nullable=False)
    channel = Column(Integer)
    channel_name = Column(String(100))
    
    # Status
    status = Column(SQLEnum(ScheduleStatus), nullable=False, default=ScheduleStatus.DRAFT)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    # Validation
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_errors = Column(JSONB, default=list)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(UUID(as_uuid=True))
    
    # Publishing
    published_at = Column(DateTime(timezone=True))
    published_by = Column(UUID(as_uuid=True))
    
    # Execution
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Import info
    imported_from = Column(String(100))  # traffic, manual, api
    import_file = Column(String(500))
    import_data = Column(JSONB)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    playout_system = relationship("PlayoutSystem", back_populates="schedules")
    schedule_items = relationship("ScheduleItem", back_populates="schedule", order_by="ScheduleItem.position")
    
    # Indexes
    __table_args__ = (
        Index('idx_schedule_date', 'schedule_date'),
        Index('idx_schedule_status', 'status'),
        Index('idx_schedule_channel', 'channel'),
    )


class ScheduleItem(Base):
    """Individual item in a playout schedule"""
    __tablename__ = "schedule_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("playout_schedules.id"), nullable=False)
    
    # Position and timing
    position = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in frames or milliseconds
    
    # Content reference
    content_id = Column(String(255), nullable=False)  # MAMS asset ID
    house_id = Column(String(100))  # House number for playout system
    title = Column(String(255))
    
    # Technical details
    som = Column(String(20))  # Start of media timecode
    eom = Column(String(20))  # End of media timecode
    duration_tc = Column(String(20))  # Duration as timecode
    
    # Item type
    item_type = Column(String(50), default="content")  # content, live, graphic, black, etc.
    is_filler = Column(Boolean, default=False, nullable=False)
    
    # Secondary events
    secondary_events = Column(JSONB, default=list)  # Graphics, bugs, etc.
    
    # Status
    content_status = Column(SQLEnum(ContentStatus), default=ContentStatus.PENDING)
    played_at = Column(DateTime(timezone=True))
    actual_duration = Column(Integer)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schedule = relationship("PlayoutSchedule", back_populates="schedule_items")
    
    # Indexes
    __table_args__ = (
        Index('idx_item_position', 'schedule_id', 'position'),
        Index('idx_item_time', 'scheduled_time'),
        Index('idx_item_content', 'content_id'),
        Index('idx_item_status', 'content_status'),
    )


class ContentTransfer(Base):
    """Content transfer to playout system"""
    __tablename__ = "content_transfers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    
    # Content info
    content_id = Column(String(255), nullable=False)
    source_path = Column(String(500), nullable=False)
    destination_path = Column(String(500))
    file_size = Column(Integer)
    
    # Transfer details
    status = Column(SQLEnum(TransferStatus), nullable=False, default=TransferStatus.PENDING)
    priority = Column(Integer, default=5)  # 1-10, higher is more urgent
    
    # Progress
    bytes_transferred = Column(Integer, default=0)
    transfer_rate = Column(Float)  # MB/s
    percent_complete = Column(Float, default=0.0)
    
    # Timing
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True))
    
    # Error handling
    error_message = Column(Text)
    error_code = Column(String(50))
    
    # Validation
    needs_validation = Column(Boolean, default=True, nullable=False)
    validation_status = Column(String(50))
    validation_result = Column(JSONB)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    playout_system = relationship("PlayoutSystem", back_populates="transfers")
    
    # Indexes
    __table_args__ = (
        Index('idx_transfer_status', 'status'),
        Index('idx_transfer_priority', 'priority'),
        Index('idx_transfer_content', 'content_id'),
        Index('idx_transfer_queued', 'queued_at'),
    )


class AsRunLog(Base):
    """As-run log entries"""
    __tablename__ = "asrun_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    
    # Event info
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(50), nullable=False)  # play, stop, error, etc.
    channel = Column(Integer)
    
    # Content info
    content_id = Column(String(255))
    house_id = Column(String(100))
    title = Column(String(255))
    
    # Timing
    scheduled_time = Column(DateTime(timezone=True))
    actual_time = Column(DateTime(timezone=True), nullable=False)
    scheduled_duration = Column(Integer)
    actual_duration = Column(Integer)
    
    # Status
    status = Column(String(50))  # aired, skipped, error, etc.
    error_message = Column(Text)
    
    # Reconciliation
    schedule_item_id = Column(UUID(as_uuid=True))
    discrepancy_type = Column(String(50))  # early, late, wrong_content, missing, etc.
    discrepancy_seconds = Column(Integer)
    
    # Raw data
    raw_log_entry = Column(Text)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_asrun_time', 'event_time'),
        Index('idx_asrun_type', 'event_type'),
        Index('idx_asrun_channel', 'channel'),
        Index('idx_asrun_content', 'content_id'),
        Index('idx_asrun_discrepancy', 'discrepancy_type'),
    )


class PlayoutMetric(Base):
    """Playout system metrics"""
    __tablename__ = "playout_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("playout_devices.id"))
    
    # Metric info
    metric_type = Column(String(50), nullable=False)  # cpu, memory, storage, transfer, etc.
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))
    
    # Context
    channel = Column(Integer)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_metric_time', 'recorded_at'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_system', 'playout_system_id', 'recorded_at'),
    )


class PlayoutAlert(Base):
    """Playout system alerts"""
    __tablename__ = "playout_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playout_system_id = Column(UUID(as_uuid=True), ForeignKey("playout_systems.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("playout_devices.id"))
    
    # Alert info
    alert_type = Column(String(50), nullable=False)  # error, warning, info
    alert_category = Column(String(50), nullable=False)  # device, transfer, schedule, etc.
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    
    # Details
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(UUID(as_uuid=True))
    acknowledged_at = Column(DateTime(timezone=True))
    
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(UUID(as_uuid=True))
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    
    # Context
    channel = Column(Integer)
    content_id = Column(String(255))
    schedule_id = Column(UUID(as_uuid=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_type', 'alert_type'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_status', 'is_resolved'),
        Index('idx_alert_created', 'created_at'),
    )