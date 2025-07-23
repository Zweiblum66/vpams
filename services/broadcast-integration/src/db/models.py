"""Database models for Broadcast Integration Service"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class RundownStatus(str, enum.Enum):
    """Rundown status enumeration"""
    DRAFT = "draft"
    READY = "ready"
    ON_AIR = "on_air"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StoryStatus(str, enum.Enum):
    """Story status enumeration"""
    DRAFT = "draft"
    READY = "ready"
    APPROVED = "approved"
    ON_AIR = "on_air"
    COMPLETED = "completed"


class ApprovalStatus(str, enum.Enum):
    """Approval status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class GraphicsType(str, enum.Enum):
    """Graphics type enumeration"""
    LOWER_THIRD = "lower_third"
    TICKER = "ticker"
    FULL_SCREEN = "full_screen"
    BUG = "bug"
    TRANSITION = "transition"
    CUSTOM = "custom"


class Rundown(Base):
    """Broadcast rundown model"""
    __tablename__ = "rundowns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    show_date = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(SQLEnum(RundownStatus), nullable=False, default=RundownStatus.DRAFT)
    locked = Column(Boolean, default=False, nullable=False)
    
    # Newsroom integration
    mos_ro_id = Column(String(255), unique=True)  # MOS Running Order ID
    newsroom_system = Column(String(50))  # ENPS, Avid, Ross, etc.
    newsroom_id = Column(String(255))  # ID in the newsroom system
    
    # Timing
    planned_start = Column(DateTime(timezone=True))
    actual_start = Column(DateTime(timezone=True))
    planned_end = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    
    # Production info
    producer_id = Column(UUID(as_uuid=True))
    director_id = Column(UUID(as_uuid=True))
    studio = Column(String(100))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True))
    
    # Relationships
    stories = relationship("Story", back_populates="rundown", order_by="Story.position", cascade="all, delete-orphan")
    templates = relationship("RundownTemplate", secondary="rundown_template_usage", back_populates="rundowns")


class Story(Base):
    """Story/segment within a rundown"""
    __tablename__ = "stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rundown_id = Column(UUID(as_uuid=True), ForeignKey("rundowns.id"), nullable=False)
    position = Column(Integer, nullable=False)
    
    # Basic info
    slug = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    duration_seconds = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(SQLEnum(StoryStatus), nullable=False, default=StoryStatus.DRAFT)
    on_air = Column(Boolean, default=False, nullable=False)
    
    # Newsroom integration
    mos_story_id = Column(String(255))  # MOS Story ID
    newsroom_id = Column(String(255))  # ID in newsroom system
    
    # Content
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"))
    
    # Media assets
    media_assets = Column(JSONB, default=list)  # List of asset IDs from asset service
    
    # Production info
    reporter_id = Column(UUID(as_uuid=True))
    camera_positions = Column(JSONB, default=list)
    
    # Timing
    backtime = Column(Float)  # Seconds from end of show
    fronttime = Column(Float)  # Seconds from start of show
    actual_start = Column(DateTime(timezone=True))
    actual_duration = Column(Integer)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rundown = relationship("Rundown", back_populates="stories")
    script = relationship("Script", back_populates="stories")
    graphics = relationship("StoryGraphics", back_populates="story", cascade="all, delete-orphan")
    approvals = relationship("StoryApproval", back_populates="story", cascade="all, delete-orphan")


class Script(Base):
    """Teleprompter script for stories"""
    __tablename__ = "scripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, nullable=False, default=1)
    
    # Content
    content = Column(Text, nullable=False)
    formatted_content = Column(Text)  # With prompter formatting
    word_count = Column(Integer)
    estimated_duration = Column(Integer)  # Seconds based on reading speed
    
    # Language
    language = Column(String(10), default="en")
    
    # Cues
    cue_points = Column(JSONB, default=list)  # List of cue points with timings
    
    # Approval
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stories = relationship("Story", back_populates="script")
    versions = relationship("ScriptVersion", back_populates="script", cascade="all, delete-orphan")


class ScriptVersion(Base):
    """Script version history"""
    __tablename__ = "script_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Content snapshot
    content = Column(Text, nullable=False)
    word_count = Column(Integer)
    
    # Change info
    changed_by = Column(UUID(as_uuid=True), nullable=False)
    change_summary = Column(String(500))
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    script = relationship("Script", back_populates="versions")


class Graphics(Base):
    """Graphics and visual elements"""
    __tablename__ = "graphics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Type and category
    type = Column(SQLEnum(GraphicsType), nullable=False)
    category = Column(String(100))
    
    # Template or custom
    is_template = Column(Boolean, default=False, nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("graphics_templates.id"))
    
    # Content
    data = Column(JSONB, nullable=False, default=dict)  # Graphics data/parameters
    preview_url = Column(String(500))
    render_url = Column(String(500))
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    template = relationship("GraphicsTemplate", back_populates="graphics")
    story_graphics = relationship("StoryGraphics", back_populates="graphics")


class GraphicsTemplate(Base):
    """Reusable graphics templates"""
    __tablename__ = "graphics_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Type and category
    type = Column(SQLEnum(GraphicsType), nullable=False)
    category = Column(String(100))
    
    # Template definition
    schema = Column(JSONB, nullable=False)  # JSON schema for data validation
    default_data = Column(JSONB, default=dict)
    preview_template = Column(Text)  # Template for preview generation
    
    # Renderer info
    renderer = Column(String(50), nullable=False)  # vizrt, caspar, etc.
    renderer_template = Column(Text)  # Native template code
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    version = Column(String(20), default="1.0.0")
    
    # Metadata
    description = Column(Text)
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    graphics = relationship("Graphics", back_populates="template")


class StoryGraphics(Base):
    """Graphics assigned to stories"""
    __tablename__ = "story_graphics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    graphics_id = Column(UUID(as_uuid=True), ForeignKey("graphics.id"), nullable=False)
    
    # Timing
    in_point = Column(Float)  # Seconds into story
    out_point = Column(Float)  # Seconds into story
    duration = Column(Float)  # Duration in seconds
    
    # Order
    position = Column(Integer, nullable=False, default=0)
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False)
    triggered = Column(Boolean, default=False, nullable=False)
    triggered_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    story = relationship("Story", back_populates="graphics")
    graphics = relationship("Graphics", back_populates="story_graphics")


class RundownTemplate(Base):
    """Rundown templates for common show formats"""
    __tablename__ = "rundown_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Template type
    show_type = Column(String(100))  # news, magazine, sports, etc.
    duration_minutes = Column(Integer)
    
    # Template structure
    structure = Column(JSONB, nullable=False)  # Template structure definition
    default_stories = Column(JSONB, default=list)  # Default story templates
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    description = Column(Text)
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Ownership
    created_by = Column(UUID(as_uuid=True))
    organization_id = Column(UUID(as_uuid=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rundowns = relationship("Rundown", secondary="rundown_template_usage", back_populates="templates")


class StoryApproval(Base):
    """Story approval workflow"""
    __tablename__ = "story_approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    
    # Approval info
    approval_type = Column(String(50), nullable=False)  # editorial, legal, technical
    status = Column(SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    
    # Approver
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime(timezone=True))
    
    # Feedback
    comments = Column(Text)
    conditions = Column(JSONB, default=list)  # Conditions for approval
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    story = relationship("Story", back_populates="approvals")


class AutomationEvent(Base):
    """Automation system events"""
    __tablename__ = "automation_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rundown_id = Column(UUID(as_uuid=True), ForeignKey("rundowns.id"))
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"))
    
    # Event info
    event_type = Column(String(100), nullable=False)  # camera_switch, audio_route, graphics_trigger, etc.
    event_data = Column(JSONB, nullable=False)
    
    # Timing
    scheduled_time = Column(DateTime(timezone=True))
    executed_time = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(50), default="pending")  # pending, executed, failed, cancelled
    error_message = Column(Text)
    
    # Source
    source = Column(String(50))  # manual, scheduled, triggered
    created_by = Column(UUID(as_uuid=True))
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NewsroomSync(Base):
    """Newsroom synchronization log"""
    __tablename__ = "newsroom_sync"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sync info
    newsroom_system = Column(String(50), nullable=False)
    sync_type = Column(String(50), nullable=False)  # rundown, story, script, etc.
    sync_direction = Column(String(20), nullable=False)  # inbound, outbound
    
    # Object references
    local_id = Column(UUID(as_uuid=True))
    remote_id = Column(String(255))
    object_type = Column(String(50))
    
    # Status
    status = Column(String(50), nullable=False)  # success, failed, partial
    error_message = Column(Text)
    
    # Data
    sync_data = Column(JSONB)
    changes = Column(JSONB)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamp
    synced_at = Column(DateTime(timezone=True), server_default=func.now())


from sqlalchemy import Table

# Association table for rundown templates
rundown_template_usage = Table(
    "rundown_template_usage",
    Base.metadata,
    Column("rundown_id", UUID(as_uuid=True), ForeignKey("rundowns.id"), primary_key=True),
    Column("template_id", UUID(as_uuid=True), ForeignKey("rundown_templates.id"), primary_key=True),
    Column("applied_at", DateTime(timezone=True), server_default=func.now())
)