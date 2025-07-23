"""
Database models for Asset Management Service

This module defines the SQLAlchemy models for managing media assets,
versions, relationships, and project structures.
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, 
    DateTime, ForeignKey, Text, JSON, Enum, Index, UniqueConstraint,
    CheckConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from .base import Base


class AssetStatus(enum.Enum):
    """Asset status enumeration"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    ERROR = "error"


class AssetType(enum.Enum):
    """Asset type enumeration"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    SUBTITLE = "subtitle"
    PROJECT = "project"
    OTHER = "other"


class ContainerType(enum.Enum):
    """Project container type enumeration"""
    PROJECT = "project"
    FOLDER = "folder"
    BIN = "bin"
    SHOTLIST = "shotlist"
    SEQUENCE = "sequence"


# Association tables for many-to-many relationships
asset_tags = Table(
    'asset_tags',
    Base.metadata,
    Column('asset_id', UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE')),
    UniqueConstraint('asset_id', 'tag_id', name='uq_asset_tag')
)

asset_collections = Table(
    'asset_collections',
    Base.metadata,
    Column('asset_id', UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE')),
    Column('collection_id', UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE')),
    UniqueConstraint('asset_id', 'collection_id', name='uq_asset_collection')
)


class Asset(Base):
    """Main asset model"""
    __tablename__ = 'assets'
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # File information
    file_path = Column(String(1024), nullable=False)  # Storage path
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), index=True)  # SHA-256
    mime_type = Column(String(128))
    file_extension = Column(String(32))
    
    # Asset metadata
    asset_type = Column(Enum(AssetType), nullable=False, index=True)
    status = Column(Enum(AssetStatus), nullable=False, default=AssetStatus.UPLOADING, index=True)
    
    # Media-specific metadata (stored as JSON for flexibility)
    technical_metadata = Column(JSON, default={})
    # For video: duration, resolution, framerate, codec, bitrate, etc.
    # For audio: duration, sample_rate, channels, bitrate, etc.
    # For image: width, height, color_space, dpi, etc.
    
    # Storage information
    storage_driver = Column(String(64), nullable=False)  # Which storage driver
    storage_path = Column(String(1024), nullable=False)  # Full storage path
    storage_tier = Column(String(32), default='hot')  # hot, warm, cold, archive
    
    # Ownership and permissions
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project_containers.id'), index=True)
    is_public = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # Soft delete
    
    # Relationships
    versions = relationship("AssetVersion", back_populates="asset", cascade="all, delete-orphan",
                          order_by="desc(AssetVersion.version_number)")
    tags = relationship("Tag", secondary=asset_tags, back_populates="assets")
    collections = relationship("Collection", secondary=asset_collections, back_populates="assets")
    relationships = relationship("AssetRelationship", 
                               foreign_keys="AssetRelationship.source_asset_id",
                               back_populates="source_asset",
                               cascade="all, delete-orphan")
    related_assets = relationship("AssetRelationship",
                                foreign_keys="AssetRelationship.target_asset_id",
                                back_populates="target_asset")
    project_container = relationship("ProjectContainer", back_populates="assets")
    
    # Indexes
    __table_args__ = (
        Index('idx_asset_type_status', 'asset_type', 'status'),
        Index('idx_asset_owner_project', 'owner_id', 'project_id'),
        Index('idx_asset_created', 'created_at'),
        Index('idx_asset_name_project', 'name', 'project_id'),
        CheckConstraint('file_size >= 0', name='check_file_size_positive'),
    )
    
    def __repr__(self):
        return f"<Asset(id={self.id}, name='{self.name}', type={self.asset_type.value})>"


class AssetVersion(Base):
    """Asset version model for tracking file versions"""
    __tablename__ = 'asset_versions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_label = Column(String(64))  # e.g., "v1.0", "final", "draft"
    
    # Version-specific file information
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False)
    
    # Version metadata
    comment = Column(Text)
    is_current = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Storage information (versions can be in different tiers)
    storage_driver = Column(String(64), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    storage_tier = Column(String(32), default='hot')
    
    # Relationships
    asset = relationship("Asset", back_populates="versions")
    
    __table_args__ = (
        UniqueConstraint('asset_id', 'version_number', name='uq_asset_version'),
        Index('idx_version_current', 'asset_id', 'is_current'),
    )


class AssetRelationship(Base):
    """Relationships between assets (e.g., proxy, derivative, related)"""
    __tablename__ = 'asset_relationships'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    relationship_type = Column(String(64), nullable=False)  # proxy, derivative, related, etc.
    relationship_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source_asset = relationship("Asset", foreign_keys=[source_asset_id], back_populates="relationships")
    target_asset = relationship("Asset", foreign_keys=[target_asset_id], back_populates="related_assets")
    
    __table_args__ = (
        UniqueConstraint('source_asset_id', 'target_asset_id', 'relationship_type', 
                        name='uq_asset_relationship'),
        Index('idx_relationship_type', 'relationship_type'),
        CheckConstraint('source_asset_id != target_asset_id', name='check_different_assets'),
    )


class ProjectContainer(Base):
    """Hierarchical project structure (projects, folders, bins, etc.)"""
    __tablename__ = 'project_containers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    container_type = Column(Enum(ContainerType), nullable=False, index=True)
    
    # Hierarchical structure
    parent_id = Column(UUID(as_uuid=True), ForeignKey('project_containers.id', ondelete='CASCADE'))
    path = Column(String(1024), index=True)  # Full path for quick lookups
    
    # Ownership and permissions
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    
    # Container-specific metadata
    container_metadata = Column(JSON, default={})
    settings = Column(JSON, default={})  # Container-specific settings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # Soft delete
    
    # Relationships
    parent = relationship("ProjectContainer", remote_side=[id], backref=backref("children", cascade="all, delete-orphan"))
    assets = relationship("Asset", back_populates="project_container")
    
    __table_args__ = (
        Index('idx_container_type_owner', 'container_type', 'owner_id'),
        Index('idx_container_parent', 'parent_id'),
        Index('idx_container_path', 'path'),
    )
    
    def __repr__(self):
        return f"<ProjectContainer(id={self.id}, name='{self.name}', type={self.container_type.value})>"


class Tag(Base):
    """Tags for asset categorization"""
    __tablename__ = 'tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False, unique=True, index=True)
    category = Column(String(64), index=True)  # Optional tag categorization
    color = Column(String(7))  # Hex color for UI
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    assets = relationship("Asset", secondary=asset_tags, back_populates="tags")


class Collection(Base):
    """Collections for grouping assets"""
    __tablename__ = 'collections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    
    # Collection metadata
    metadata = Column(JSON, default={})
    cover_asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='SET NULL'))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    assets = relationship("Asset", secondary=asset_collections, back_populates="collections")
    cover_asset = relationship("Asset", foreign_keys=[cover_asset_id])
    
    __table_args__ = (
        Index('idx_collection_owner', 'owner_id'),
    )


class AssetShare(Base):
    """Asset sharing and permissions"""
    __tablename__ = 'asset_shares'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    shared_with_id = Column(UUID(as_uuid=True), nullable=False)  # User or group ID
    shared_with_type = Column(String(32), nullable=False)  # 'user' or 'group'
    
    # Permissions
    can_view = Column(Boolean, default=True, nullable=False)
    can_download = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_share = Column(Boolean, default=False, nullable=False)
    
    # Share settings
    expires_at = Column(DateTime(timezone=True))
    password_hash = Column(String(128))  # Optional password protection
    download_limit = Column(Integer)  # Optional download limit
    download_count = Column(Integer, default=0)
    
    # Metadata
    shared_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        UniqueConstraint('asset_id', 'shared_with_id', 'shared_with_type', name='uq_asset_share'),
        Index('idx_share_target', 'shared_with_id', 'shared_with_type'),
        Index('idx_share_expires', 'expires_at'),
    )


class ShotItem(Base):
    """Shot items for editorial workflow (clips in bins/shotlists)"""
    __tablename__ = 'shot_items'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey('project_containers.id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False)
    
    # Shot metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Timecode information (stored as frames or milliseconds)
    in_point = Column(BigInteger, default=0)  # Start point in source
    out_point = Column(BigInteger)  # End point in source
    duration = Column(BigInteger)  # Calculated duration
    
    # Shot-specific metadata
    metadata = Column(JSON, default={})  # Custom metadata
    markers = Column(JSON, default=[])  # List of markers/comments
    
    # Sorting and organization
    sort_order = Column(Integer, default=0)
    color_label = Column(String(7))  # Hex color for UI
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Relationships
    container = relationship("ProjectContainer", backref="shot_items")
    asset = relationship("Asset", backref="shot_references")
    
    __table_args__ = (
        Index('idx_shot_container', 'container_id'),
        Index('idx_shot_asset', 'asset_id'),
        CheckConstraint('in_point >= 0', name='check_in_point_positive'),
        CheckConstraint('out_point IS NULL OR out_point > in_point', name='check_out_after_in'),
    )


class SequenceTimeline(Base):
    """Timeline for sequences - arranges clips in time"""
    __tablename__ = 'sequence_timelines'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id = Column(UUID(as_uuid=True), ForeignKey('project_containers.id', ondelete='CASCADE'), nullable=False)
    
    # Track information
    track_number = Column(Integer, nullable=False)
    track_type = Column(String(32), nullable=False)  # video, audio, subtitle
    track_name = Column(String(128))
    
    # Clip reference
    clip_id = Column(UUID(as_uuid=True), ForeignKey('shot_items.id', ondelete='CASCADE'), nullable=False)
    
    # Timeline position (in project timebase)
    start_time = Column(BigInteger, nullable=False)  # Timeline start position
    end_time = Column(BigInteger, nullable=False)  # Timeline end position
    
    # Clip adjustments
    source_in = Column(BigInteger)  # Override shot in point
    source_out = Column(BigInteger)  # Override shot out point
    speed = Column(Float, default=1.0)  # Speed adjustment
    
    # Effects and transitions
    effects = Column(JSON, default=[])  # List of applied effects
    transition_in = Column(JSON)  # Incoming transition
    transition_out = Column(JSON)  # Outgoing transition
    
    # Display properties
    is_enabled = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    opacity = Column(Float, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sequence = relationship("ProjectContainer", backref="timeline_items")
    clip = relationship("ShotItem", backref="timeline_references")
    
    __table_args__ = (
        Index('idx_timeline_sequence', 'sequence_id'),
        Index('idx_timeline_track', 'sequence_id', 'track_number'),
        Index('idx_timeline_time', 'sequence_id', 'start_time', 'end_time'),
        CheckConstraint('start_time >= 0', name='check_start_time_positive'),
        CheckConstraint('end_time > start_time', name='check_end_after_start'),
        CheckConstraint('speed > 0', name='check_speed_positive'),
        CheckConstraint('opacity >= 0 AND opacity <= 1', name='check_opacity_range'),
    )


class ProjectTemplate(Base):
    """Templates for project structures"""
    __tablename__ = 'project_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(64))  # Template category
    
    # Template structure (JSON definition of folders/bins)
    structure = Column(JSON, nullable=False)
    
    # Default settings for projects created from this template
    default_settings = Column(JSON, default={})
    
    # Template metadata
    is_system = Column(Boolean, default=False)  # System vs user template
    is_public = Column(Boolean, default=True)  # Available to all users
    owner_id = Column(UUID(as_uuid=True))
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_template_category', 'category'),
        Index('idx_template_owner', 'owner_id'),
    )


class ContainerShare(Base):
    """Container sharing and permissions"""
    __tablename__ = 'container_shares'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey('project_containers.id', ondelete='CASCADE'), nullable=False)
    shared_with_id = Column(UUID(as_uuid=True), nullable=False)  # User or group ID
    shared_with_type = Column(String(32), nullable=False)  # 'user' or 'group'
    
    # Permissions
    can_view = Column(Boolean, default=True, nullable=False)
    can_add_assets = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_share = Column(Boolean, default=False, nullable=False)
    
    # Share settings
    expires_at = Column(DateTime(timezone=True))
    note = Column(Text)  # Optional note about the share
    
    # Metadata
    shared_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    
    # Relationships
    container = relationship("ProjectContainer", backref="shares")
    
    __table_args__ = (
        UniqueConstraint('container_id', 'shared_with_id', 'shared_with_type', name='uq_container_share'),
        Index('idx_share_target', 'shared_with_id', 'shared_with_type'),
        Index('idx_share_expires', 'expires_at'),
        Index('idx_share_container', 'container_id'),
    )