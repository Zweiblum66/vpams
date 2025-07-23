"""
Assets database models for migrations
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, BigInteger, Numeric, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from .base import AssetsBase, TimestampMixin, UUIDMixin, assets_metadata
import enum

# Export metadata for alembic
metadata = assets_metadata

class AssetType(enum.Enum):
    video = "video"
    audio = "audio"
    image = "image"
    document = "document"
    subtitle = "subtitle"
    other = "other"

class AssetStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    active = "active"
    archived = "archived"
    deleted = "deleted"
    failed = "failed"

class StorageTier(enum.Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"
    archive = "archive"

class Project(AssetsBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'projects'
    
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)

class AssetCollection(AssetsBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'asset_collections'
    
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'))
    parent_id = Column(UUID(as_uuid=True), ForeignKey('asset_collections.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    collection_type = Column(String(50), nullable=False)
    description = Column(Text)
    metadata = Column(JSONB, default={})
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)

class Asset(AssetsBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'assets'
    
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='SET NULL'))
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    asset_type = Column(Enum(AssetType), nullable=False)
    status = Column(Enum(AssetStatus), default=AssetStatus.pending)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False)
    mime_type = Column(String(255), nullable=False)
    file_extension = Column(String(50))
    
    # Media specific fields
    duration_seconds = Column(Numeric(10, 3))
    width = Column(Integer)
    height = Column(Integer)
    frame_rate = Column(Numeric(7, 3))
    bit_rate = Column(Integer)
    codec = Column(String(50))
    
    # Storage information
    storage_path = Column(String(1024), nullable=False)
    storage_tier = Column(Enum(StorageTier), default=StorageTier.hot)
    storage_backend = Column(String(50), nullable=False)
    
    # Metadata
    technical_metadata = Column(JSONB, default={})
    business_metadata = Column(JSONB, default={})
    custom_metadata = Column(JSONB, default={})
    tags = Column(ARRAY(Text))
    
    # Timestamps and tracking
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    archive_date = Column(DateTime(timezone=True))
    deletion_date = Column(DateTime(timezone=True))

class AssetVersion(AssetsBase, UUIDMixin):
    __tablename__ = 'asset_versions'
    
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    version_number = Column(Integer, nullable=False)
    name = Column(String(255))
    description = Column(Text)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    changes = Column(JSONB, default={})
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AssetRelationship(AssetsBase, UUIDMixin):
    __tablename__ = 'asset_relationships'
    
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    relationship_type = Column(String(50), nullable=False)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AssetCollectionItem(AssetsBase):
    __tablename__ = 'asset_collection_items'
    
    collection_id = Column(UUID(as_uuid=True), ForeignKey('asset_collections.id', ondelete='CASCADE'), primary_key=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), primary_key=True)
    sort_order = Column(Integer, default=0)
    added_by = Column(UUID(as_uuid=True), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class Proxy(AssetsBase, UUIDMixin):
    __tablename__ = 'proxies'
    
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    proxy_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    storage_path = Column(String(1024), nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    duration_seconds = Column(Numeric(10, 3))
    format = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Thumbnail(AssetsBase, UUIDMixin):
    __tablename__ = 'thumbnails'
    
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    timecode = Column(Numeric(10, 3), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AssetComment(AssetsBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'asset_comments'
    
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    parent_id = Column(UUID(as_uuid=True), ForeignKey('asset_comments.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), nullable=False)
    comment_text = Column(Text, nullable=False)
    timecode = Column(Numeric(10, 3))
    drawing_data = Column(JSONB)
    is_resolved = Column(Boolean, default=False)

class AssetLock(AssetsBase):
    __tablename__ = 'asset_locks'
    
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), primary_key=True)
    locked_by = Column(UUID(as_uuid=True), nullable=False)
    locked_at = Column(DateTime(timezone=True), server_default=func.now())
    lock_reason = Column(Text)
    expires_at = Column(DateTime(timezone=True))

class ShotItem(AssetsBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'shot_items'
    
    collection_id = Column(UUID(as_uuid=True), ForeignKey('asset_collections.id', ondelete='CASCADE'))
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'))
    name = Column(String(255))
    in_point = Column(Numeric(10, 3), nullable=False)
    out_point = Column(Numeric(10, 3), nullable=False)
    duration = Column(Numeric(10, 3))  # Generated column
    metadata = Column(JSONB, default={})
    sort_order = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), nullable=False)