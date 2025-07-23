"""Database models for MOS Integration Service"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Boolean, JSON,
    ForeignKey, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class MOSConnection(Base):
    """MOS connection tracking"""
    __tablename__ = "mos_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nrcs_id = Column(String(255), nullable=False, index=True)
    nrcs_description = Column(String(512))
    connection_status = Column(String(50), nullable=False, default="disconnected")
    last_heartbeat = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Configuration
    supported_profiles = Column(JSONB)
    capabilities = Column(JSONB)
    
    # Relationships
    objects = relationship("MOSObject", back_populates="connection")
    running_orders = relationship("MOSRunningOrder", back_populates="connection")
    messages = relationship("MOSMessage", back_populates="connection")


class MOSObject(Base):
    """MOS media objects"""
    __tablename__ = "mos_objects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obj_id = Column(String(255), nullable=False, unique=True, index=True)
    obj_slug = Column(String(255), nullable=False, index=True)
    obj_type = Column(String(50), nullable=False)
    obj_group = Column(String(100))
    
    # Object metadata
    obj_abstract = Column(Text)
    obj_tb = Column(Integer)  # Time base
    obj_rev = Column(Integer, default=1)  # Revision number
    obj_dur = Column(Integer)  # Duration in time base units
    status = Column(String(50), default="NEW")
    obj_air = Column(String(50))  # Air status
    
    # File paths
    obj_paths = Column(JSONB)  # Array of file paths
    
    # Creator information
    created_by = Column(String(255))
    changed_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Description and metadata
    description = Column(Text)
    external_metadata = Column(JSONB)
    
    # Foreign keys
    connection_id = Column(UUID(as_uuid=True), ForeignKey("mos_connections.id"))
    
    # Relationships
    connection = relationship("MOSConnection", back_populates="objects")
    story_items = relationship("MOSStoryItem", back_populates="mos_object")
    
    # Indexes
    __table_args__ = (
        Index("idx_mos_object_slug", "obj_slug"),
        Index("idx_mos_object_type", "obj_type"),
        Index("idx_mos_object_status", "status"),
        Index("idx_mos_object_created", "created_at"),
    )


class MOSRunningOrder(Base):
    """MOS running orders (playlists)"""
    __tablename__ = "mos_running_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ro_id = Column(String(255), nullable=False, unique=True, index=True)
    ro_slug = Column(String(255), nullable=False)
    ro_edition_id = Column(String(255))
    
    # Running order metadata
    ro_title = Column(String(512))
    ro_start_time = Column(DateTime(timezone=True))
    ro_end_time = Column(DateTime(timezone=True))
    ro_duration = Column(Integer)  # Duration in seconds
    
    # Status and control
    status = Column(String(50), default="READY")
    air_status = Column(String(50))
    ready_to_air = Column(Boolean, default=False)
    
    # Creator information
    created_by = Column(String(255))
    changed_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    external_metadata = Column(JSONB)
    
    # Foreign keys
    connection_id = Column(UUID(as_uuid=True), ForeignKey("mos_connections.id"))
    
    # Relationships
    connection = relationship("MOSConnection", back_populates="running_orders")
    stories = relationship("MOSStory", back_populates="running_order", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_ro_slug", "ro_slug"),
        Index("idx_ro_status", "status"),
        Index("idx_ro_start_time", "ro_start_time"),
    )


class MOSStory(Base):
    """MOS stories within running orders"""
    __tablename__ = "mos_stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(String(255), nullable=False, index=True)
    story_slug = Column(String(255), nullable=False)
    story_number = Column(Integer)  # Position in running order
    
    # Story metadata
    story_title = Column(String(512))
    story_abstract = Column(Text)
    story_body = Column(Text)
    
    # Timing
    story_duration = Column(Integer)  # Duration in seconds
    story_approx_dur = Column(Integer)  # Approximate duration
    
    # Status
    status = Column(String(50), default="READY")
    
    # Creator information
    created_by = Column(String(255))
    changed_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    external_metadata = Column(JSONB)
    
    # Foreign keys
    running_order_id = Column(UUID(as_uuid=True), ForeignKey("mos_running_orders.id"))
    
    # Relationships
    running_order = relationship("MOSRunningOrder", back_populates="stories")
    items = relationship("MOSStoryItem", back_populates="story", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_story_number", "story_number"),
        Index("idx_story_status", "status"),
    )


class MOSStoryItem(Base):
    """Items within MOS stories (references to MOS objects)"""
    __tablename__ = "mos_story_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(String(255), nullable=False, index=True)
    item_slug = Column(String(255))
    item_channel = Column(String(50))
    item_number = Column(Integer)  # Position in story
    
    # Item metadata
    item_type = Column(String(50))
    item_abstract = Column(Text)
    
    # Timing
    item_duration = Column(Integer)  # Duration in seconds
    item_in_point = Column(Integer)  # In point in time base units
    item_out_point = Column(Integer)  # Out point in time base units
    
    # Status
    status = Column(String(50), default="READY")
    
    # Creator information
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    external_metadata = Column(JSONB)
    
    # Foreign keys
    story_id = Column(UUID(as_uuid=True), ForeignKey("mos_stories.id"))
    mos_object_id = Column(UUID(as_uuid=True), ForeignKey("mos_objects.id"), nullable=True)
    
    # Relationships
    story = relationship("MOSStory", back_populates="items")
    mos_object = relationship("MOSObject", back_populates="story_items")
    
    # Indexes
    __table_args__ = (
        Index("idx_item_number", "item_number"),
        Index("idx_item_type", "item_type"),
    )


class MOSMessage(Base):
    """MOS message log for auditing and debugging"""
    __tablename__ = "mos_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(255), index=True)
    message_type = Column(String(100), nullable=False, index=True)
    direction = Column(String(20), nullable=False)  # 'inbound' or 'outbound'
    
    # Message content
    raw_message = Column(Text)
    parsed_message = Column(JSONB)
    
    # Processing information
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text)
    response_message_id = Column(String(255))
    
    # Timing
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    response_sent_at = Column(DateTime(timezone=True))
    
    # Foreign keys
    connection_id = Column(UUID(as_uuid=True), ForeignKey("mos_connections.id"))
    
    # Relationships
    connection = relationship("MOSConnection", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index("idx_message_type", "message_type"),
        Index("idx_message_direction", "direction"),
        Index("idx_message_status", "processing_status"),
        Index("idx_message_received", "received_at"),
    )


class MOSHeartbeat(Base):
    """MOS heartbeat tracking"""
    __tablename__ = "mos_heartbeats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nrcs_id = Column(String(255), nullable=False, index=True)
    heartbeat_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="OK")
    
    # System information
    system_info = Column(JSONB)
    
    # Indexes
    __table_args__ = (
        Index("idx_heartbeat_nrcs", "nrcs_id"),
        Index("idx_heartbeat_time", "heartbeat_time"),
    )