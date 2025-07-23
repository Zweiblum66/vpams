"""
Knowledge Base Models for Archive-Based Recognition

These models store the persistent knowledge base for recognition systems.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, JSON, Text, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class KnowledgeEntity(Base):
    """Base model for knowledge entities (people, logos, objects, etc.)."""
    
    __tablename__ = "knowledge_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)  # person, logo, object, speaker, etc.
    entity_id = Column(String(100), nullable=False, index=True)  # unique identifier (e.g., person_john_doe)
    entity_name = Column(String(255), nullable=False)  # display name
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    categories = Column(ARRAY(String), nullable=True)
    
    # Status and confidence
    is_active = Column(Boolean, default=True)
    confidence_threshold = Column(Float, default=0.7)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_matched = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    features = relationship("EntityFeature", back_populates="entity", cascade="all, delete-orphan")
    detections = relationship("EntityDetection", back_populates="entity")
    
    def __repr__(self):
        return f"<KnowledgeEntity(type={self.entity_type}, id={self.entity_id}, name={self.entity_name})>"


class EntityFeature(Base):
    """Features/embeddings for knowledge entities."""
    
    __tablename__ = "entity_features"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False)
    
    # Feature information
    feature_type = Column(String(50), nullable=False)  # face_embedding, logo_embedding, voice_print, etc.
    feature_version = Column(String(20), nullable=False)  # model version used
    feature_vector = Column(LargeBinary, nullable=False)  # serialized numpy array
    feature_metadata = Column(JSON, nullable=True)
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    
    # Source information
    source_asset_id = Column(UUID(as_uuid=True), nullable=True)
    source_bbox = Column(JSON, nullable=True)  # bounding box if applicable
    source_timestamp = Column(Float, nullable=True)  # timestamp in media if applicable
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entity = relationship("KnowledgeEntity", back_populates="features")


class EntityDetection(Base):
    """Detections/matches of knowledge entities in assets."""
    
    __tablename__ = "entity_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False)
    
    # Asset information
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)  # image, video, audio
    
    # Detection details
    detection_type = Column(String(50), nullable=False)  # face, logo, voice, object, etc.
    confidence = Column(Float, nullable=False)
    
    # Spatial information (for images/video)
    bbox_x = Column(Float, nullable=True)
    bbox_y = Column(Float, nullable=True)
    bbox_width = Column(Float, nullable=True)
    bbox_height = Column(Float, nullable=True)
    
    # Temporal information (for video/audio)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    
    # Additional metadata
    detection_metadata = Column(JSON, nullable=True)
    
    # Processing information
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    processing_job_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)  # human verification
    verification_user_id = Column(UUID(as_uuid=True), nullable=True)
    verification_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entity = relationship("KnowledgeEntity", back_populates="detections")


class AnalysisIndex(Base):
    """Index of analyzed assets for retroactive analysis."""
    
    __tablename__ = "analysis_index"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Asset information
    asset_type = Column(String(50), nullable=False)  # image, video, audio
    asset_path = Column(String(1024), nullable=True)
    asset_size = Column(Integer, nullable=True)
    asset_duration = Column(Float, nullable=True)  # for video/audio
    
    # Analysis status
    faces_analyzed = Column(Boolean, default=False)
    objects_analyzed = Column(Boolean, default=False)
    logos_analyzed = Column(Boolean, default=False)
    speakers_analyzed = Column(Boolean, default=False)
    scenes_analyzed = Column(Boolean, default=False)
    
    # Analysis timestamps
    faces_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    objects_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    logos_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    speakers_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    scenes_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extracted features (for fast matching)
    face_features = Column(JSON, nullable=True)  # list of face embeddings
    logo_features = Column(JSON, nullable=True)  # list of logo embeddings
    voice_features = Column(JSON, nullable=True)  # voice print data
    object_features = Column(JSON, nullable=True)  # detected objects
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_analyzed = Column(DateTime(timezone=True), nullable=True)


class RetroactiveAnalysisJob(Base):
    """Jobs for retroactive analysis when new entities are added."""
    
    __tablename__ = "retroactive_analysis_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False)
    
    # Job configuration
    job_type = Column(String(50), nullable=False)  # face_match, logo_match, voice_match, etc.
    analysis_scope = Column(String(50), nullable=False)  # all, date_range, asset_list
    
    # Scope parameters
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    asset_ids = Column(ARRAY(UUID), nullable=True)
    
    # Progress tracking
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    total_assets = Column(Integer, default=0)
    processed_assets = Column(Integer, default=0)
    matched_assets = Column(Integer, default=0)
    
    # Results
    matches_found = Column(Integer, default=0)
    processing_errors = Column(Integer, default=0)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entity = relationship("KnowledgeEntity")


class EntityRelationship(Base):
    """Relationships between knowledge entities."""
    
    __tablename__ = "entity_relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationship
    entity_a_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False)
    entity_b_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # colleague, family, brand_ambassador, etc.
    
    # Relationship metadata
    strength = Column(Float, nullable=True)  # 0.0 to 1.0
    confidence = Column(Float, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entity_a = relationship("KnowledgeEntity", foreign_keys=[entity_a_id])
    entity_b = relationship("KnowledgeEntity", foreign_keys=[entity_b_id])


class EntityAnnotation(Base):
    """Human annotations and corrections for entities."""
    
    __tablename__ = "entity_annotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Target
    entity_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_entities.id"), nullable=True)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("entity_detections.id"), nullable=True)
    
    # Annotation
    annotation_type = Column(String(50), nullable=False)  # correction, verification, false_positive, etc.
    annotation_data = Column(JSON, nullable=False)
    
    # User information
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    entity = relationship("KnowledgeEntity")
    detection = relationship("EntityDetection")