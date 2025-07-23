"""Database models for NRCS Integration Service"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint, Index, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime

from .base import Base


class NRCSType(str, enum.Enum):
    """NRCS system types"""
    ENPS = "enps"
    AVID_INEWS = "avid_inews"
    ROSS_INCEPTION = "ross_inception"
    OCTOPUS = "octopus"
    GENERIC = "generic"


class ConnectionStatus(str, enum.Enum):
    """NRCS connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class SyncStatus(str, enum.Enum):
    """Synchronization status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StoryStatus(str, enum.Enum):
    """Story status in NRCS"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AssignmentStatus(str, enum.Enum):
    """Assignment status"""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class NRCSSystem(Base):
    """NRCS system configuration"""
    __tablename__ = "nrcs_systems"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # System info
    system_type = Column(SQLEnum(NRCSType), nullable=False)
    vendor = Column(String(100))
    version = Column(String(50))
    
    # Connection info
    host = Column(String(255))
    port = Column(Integer)
    api_url = Column(String(500))
    websocket_url = Column(String(500))
    
    # Authentication
    username = Column(String(100))
    password = Column(String(255))  # Encrypted
    api_key = Column(String(255))   # Encrypted
    token = Column(Text)            # Encrypted
    
    # Configuration
    config = Column(JSONB, default=dict)
    features = Column(JSONB, default=list)
    
    # Status
    status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.DISCONNECTED)
    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    last_connection = Column(DateTime(timezone=True))
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Stats
    total_stories = Column(Integer, default=0)
    total_rundowns = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    
    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stories = relationship("NRCSStory", back_populates="system")
    rundowns = relationship("NRCSRundown", back_populates="system")
    users = relationship("NRCSUser", back_populates="system")
    assignments = relationship("NRCSAssignment", back_populates="system")
    sync_logs = relationship("SyncLog", back_populates="system")
    
    # Indexes
    __table_args__ = (
        Index('idx_nrcs_system_type', 'system_type'),
        Index('idx_nrcs_system_status', 'status'),
        Index('idx_nrcs_system_active', 'is_active'),
    )


class NRCSStory(Base):
    """NRCS story representation"""
    __tablename__ = "nrcs_stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    
    # Story identification
    story_id = Column(String(255), nullable=False)  # External NRCS story ID
    slug = Column(String(255), nullable=False)
    
    # Content
    headline = Column(String(500), nullable=False)
    summary = Column(Text)
    body = Column(Text)
    
    # Metadata
    author = Column(String(255))
    editor = Column(String(255))
    category = Column(String(100))
    priority = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(StoryStatus), default=StoryStatus.DRAFT)
    is_breaking = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    
    # Timing
    embargo_until = Column(DateTime(timezone=True))
    publish_at = Column(DateTime(timezone=True))
    expire_at = Column(DateTime(timezone=True))
    
    # External references
    external_id = Column(String(255))
    source_system = Column(String(50))
    related_stories = Column(JSONB, default=list)
    
    # Content structure
    sections = Column(JSONB, default=list)
    media_references = Column(JSONB, default=list)
    tags = Column(JSONB, default=list)
    
    # Sync info
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING)
    sync_error = Column(Text)
    
    # Version control
    version = Column(Integer, default=1)
    revision_hash = Column(String(64))
    
    # Workflow
    approval_status = Column(String(50))
    approver = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    # Analytics
    view_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    external_created_at = Column(DateTime(timezone=True))
    external_updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    system = relationship("NRCSSystem", back_populates="stories")
    rundown_items = relationship("RundownItem", back_populates="story")
    assignments = relationship("NRCSAssignment", back_populates="story")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('system_id', 'story_id', name='uq_system_story'),
        Index('idx_story_status', 'status'),
        Index('idx_story_author', 'author'),
        Index('idx_story_created', 'created_at'),
        Index('idx_story_sync', 'sync_status'),
        Index('idx_story_external_id', 'external_id'),
    )


class NRCSRundown(Base):
    """NRCS rundown representation"""
    __tablename__ = "nrcs_rundowns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    
    # Rundown identification
    rundown_id = Column(String(255), nullable=False)  # External NRCS rundown ID
    name = Column(String(500), nullable=False)
    
    # Show information
    show_name = Column(String(255))
    episode_number = Column(String(50))
    air_date = Column(DateTime(timezone=True))
    air_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Status
    status = Column(String(50), default="draft")
    is_live = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    
    # Producer information
    producer = Column(String(255))
    director = Column(String(255))
    
    # Template info
    template_name = Column(String(255))
    template_version = Column(String(50))
    
    # Timing
    estimated_duration = Column(Integer)  # seconds
    actual_duration = Column(Integer)     # seconds
    
    # Sync info
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING)
    sync_error = Column(Text)
    
    # External references
    external_id = Column(String(255))
    parent_rundown_id = Column(String(255))
    
    # Configuration
    auto_timing = Column(Boolean, default=True)
    allow_overrun = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    external_created_at = Column(DateTime(timezone=True))
    external_updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    system = relationship("NRCSSystem", back_populates="rundowns")
    items = relationship("RundownItem", back_populates="rundown", order_by="RundownItem.position")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('system_id', 'rundown_id', name='uq_system_rundown'),
        Index('idx_rundown_status', 'status'),
        Index('idx_rundown_air_date', 'air_date'),
        Index('idx_rundown_show', 'show_name'),
        Index('idx_rundown_sync', 'sync_status'),
    )


class RundownItem(Base):
    """Individual item in a rundown"""
    __tablename__ = "rundown_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rundown_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_rundowns.id"), nullable=False)
    story_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_stories.id"))
    
    # Position and identification
    position = Column(Integer, nullable=False)
    item_id = Column(String(255))  # External item ID
    
    # Item details
    title = Column(String(500))
    item_type = Column(String(50))  # story, commercial, break, etc.
    
    # Timing
    duration_seconds = Column(Integer)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(50), default="ready")
    is_played = Column(Boolean, default=False)
    played_at = Column(DateTime(timezone=True))
    
    # Technical details
    video_format = Column(String(50))
    audio_channels = Column(Integer)
    
    # Graphics and automation
    graphics = Column(JSONB, default=list)
    automation_commands = Column(JSONB, default=list)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rundown = relationship("NRCSRundown", back_populates="items")
    story = relationship("NRCSStory", back_populates="rundown_items")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('rundown_id', 'position', name='uq_rundown_position'),
        Index('idx_item_type', 'item_type'),
        Index('idx_item_status', 'status'),
        Index('idx_item_timing', 'start_time', 'end_time'),
    )


class NRCSUser(Base):
    """NRCS user representation"""
    __tablename__ = "nrcs_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    
    # User identification
    user_id = Column(String(255), nullable=False)  # External NRCS user ID
    username = Column(String(255), nullable=False)
    email = Column(String(255))
    
    # User info
    first_name = Column(String(255))
    last_name = Column(String(255))
    display_name = Column(String(255))
    title = Column(String(255))
    department = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))
    
    # Permissions
    roles = Column(JSONB, default=list)
    permissions = Column(JSONB, default=list)
    groups = Column(JSONB, default=list)
    
    # Sync info
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING)
    
    # Contact info
    phone = Column(String(50))
    extension = Column(String(20))
    location = Column(String(255))
    
    # Preferences
    timezone = Column(String(50))
    language = Column(String(10))
    preferences = Column(JSONB, default=dict)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    external_created_at = Column(DateTime(timezone=True))
    external_updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    system = relationship("NRCSSystem", back_populates="users")
    assignments = relationship("NRCSAssignment", back_populates="assignee")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('system_id', 'user_id', name='uq_system_user'),
        UniqueConstraint('system_id', 'username', name='uq_system_username'),
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_last_activity', 'last_activity'),
    )


class NRCSAssignment(Base):
    """Story/beat assignments"""
    __tablename__ = "nrcs_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    story_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_stories.id"))
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_users.id"), nullable=False)
    
    # Assignment details
    assignment_id = Column(String(255))  # External assignment ID
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Assignment type
    assignment_type = Column(String(50), default="story")  # story, beat, event, etc.
    priority = Column(Integer, default=0)
    
    # Status and timing
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.OPEN)
    due_date = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Location and logistics
    location = Column(String(500))
    contact_info = Column(JSONB, default=dict)
    
    # Beat information
    beat_name = Column(String(255))
    beat_category = Column(String(100))
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    milestone_notes = Column(Text)
    
    # Sync info
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    external_created_at = Column(DateTime(timezone=True))
    
    # Relationships
    system = relationship("NRCSSystem", back_populates="assignments")
    story = relationship("NRCSStory", back_populates="assignments")
    assignee = relationship("NRCSUser", back_populates="assignments")
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_assignment_status', 'status'),
        Index('idx_assignment_due', 'due_date'),
        Index('idx_assignment_type', 'assignment_type'),
        Index('idx_assignment_beat', 'beat_name'),
    )


class WireService(Base):
    """Wire service feed management"""
    __tablename__ = "wire_services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    
    # Wire service info
    service_name = Column(String(255), nullable=False)
    service_code = Column(String(50), nullable=False)
    category = Column(String(100))
    
    # Configuration
    feed_url = Column(String(1000))
    polling_interval = Column(Integer, default=300)  # seconds
    is_active = Column(Boolean, default=True)
    
    # Filtering
    keywords = Column(JSONB, default=list)
    exclude_keywords = Column(JSONB, default=list)
    categories = Column(JSONB, default=list)
    
    # Processing
    auto_ingest = Column(Boolean, default=False)
    auto_publish = Column(Boolean, default=False)
    processing_rules = Column(JSONB, default=dict)
    
    # Stats
    total_stories = Column(Integer, default=0)
    stories_today = Column(Integer, default=0)
    last_story_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    system = relationship("NRCSSystem")
    wire_stories = relationship("WireStory", back_populates="wire_service")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('system_id', 'service_code', name='uq_system_wire_service'),
        Index('idx_wire_service_active', 'is_active'),
        Index('idx_wire_service_category', 'category'),
    )


class WireStory(Base):
    """Wire service stories"""
    __tablename__ = "wire_stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wire_service_id = Column(UUID(as_uuid=True), ForeignKey("wire_services.id"), nullable=False)
    
    # Story identification
    wire_id = Column(String(255), nullable=False)
    headline = Column(String(1000), nullable=False)
    slug = Column(String(255))
    
    # Content
    summary = Column(Text)
    body = Column(Text)
    category = Column(String(100))
    
    # Metadata
    author = Column(String(255))
    source = Column(String(255))
    location = Column(String(255))
    priority = Column(Integer, default=0)
    
    # Processing
    is_processed = Column(Boolean, default=False)
    is_ingested = Column(Boolean, default=False)
    processing_notes = Column(Text)
    
    # References
    story_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_stories.id"))  # If ingested
    
    # Timestamps
    published_at = Column(DateTime(timezone=True))
    ingested_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    wire_service = relationship("WireService", back_populates="wire_stories")
    story = relationship("NRCSStory")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('wire_service_id', 'wire_id', name='uq_wire_story'),
        Index('idx_wire_story_published', 'published_at'),
        Index('idx_wire_story_category', 'category'),
        Index('idx_wire_story_processed', 'is_processed'),
    )


class SyncLog(Base):
    """Synchronization logging"""
    __tablename__ = "sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id = Column(UUID(as_uuid=True), ForeignKey("nrcs_systems.id"), nullable=False)
    
    # Sync operation
    operation_type = Column(String(50), nullable=False)  # story, rundown, user, etc.
    operation_action = Column(String(50), nullable=False)  # create, update, delete, sync
    
    # Target info
    target_type = Column(String(50))
    target_id = Column(String(255))
    
    # Status
    status = Column(SQLEnum(SyncStatus), nullable=False)
    
    # Details
    details = Column(JSONB, default=dict)
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    system = relationship("NRCSSystem", back_populates="sync_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_sync_log_status', 'status'),
        Index('idx_sync_log_operation', 'operation_type', 'operation_action'),
        Index('idx_sync_log_started', 'started_at'),
        Index('idx_sync_log_system', 'system_id', 'started_at'),
    )