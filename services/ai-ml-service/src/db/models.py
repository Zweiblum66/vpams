"""
Database models for AI/ML Service
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class MLProcessingJob(Base):
    """Model for ML processing jobs."""
    
    __tablename__ = "ml_processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_type = Column(String(50), nullable=False, index=True)  # object_detection, scene_detection, etc.
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    
    # Input parameters
    input_data = Column(JSON, nullable=True)
    processing_parameters = Column(JSON, nullable=True)
    
    # Results
    results = Column(JSON, nullable=True)
    confidence_scores = Column(JSON, nullable=True)
    
    # Metadata
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    results_records = relationship("MLProcessingResult", back_populates="job", cascade="all, delete-orphan")


class MLProcessingResult(Base):
    """Model for detailed ML processing results."""
    
    __tablename__ = "ml_processing_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("ml_processing_jobs.id"), nullable=False)
    
    # Result data
    result_type = Column(String(50), nullable=False)  # detection, classification, transcription, etc.
    result_data = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Bounding box data for detections
    bbox_x = Column(Float, nullable=True)
    bbox_y = Column(Float, nullable=True)
    bbox_width = Column(Float, nullable=True)
    bbox_height = Column(Float, nullable=True)
    
    # Time-based data for video/audio
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("MLProcessingJob", back_populates="results_records")


class MLModelMetrics(Base):
    """Model for ML model performance metrics."""
    
    __tablename__ = "ml_model_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)
    
    # Performance metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    average_processing_time = Column(Float, nullable=True)
    
    # Resource usage
    average_memory_usage = Column(Float, nullable=True)
    average_cpu_usage = Column(Float, nullable=True)
    average_gpu_usage = Column(Float, nullable=True)
    
    # Quality metrics
    average_confidence = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    
    # Time window
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MLCache(Base):
    """Model for ML processing cache."""
    
    __tablename__ = "ml_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    
    # Cache data
    model_name = Column(String(100), nullable=False)
    input_hash = Column(String(64), nullable=False)
    result_data = Column(JSON, nullable=False)
    
    # Metadata
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MLBatchJob(Base):
    """Model for ML batch processing jobs."""
    
    __tablename__ = "ml_batch_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_name = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False)
    
    # Batch configuration
    asset_ids = Column(JSON, nullable=False)  # List of asset IDs to process
    processing_parameters = Column(JSON, nullable=True)
    
    # Status tracking
    status = Column(String(20), nullable=False, default="pending")
    total_items = Column(Integer, nullable=False)
    processed_items = Column(Integer, default=0)
    successful_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    results_summary = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MLModelInfo(Base):
    """Model for ML model information and metadata."""
    
    __tablename__ = "ml_model_info"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, unique=True)
    model_type = Column(String(50), nullable=False)
    
    # Model metadata
    version = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    model_path = Column(String(500), nullable=True)
    
    # Model configuration
    input_format = Column(String(50), nullable=True)
    output_format = Column(String(50), nullable=True)
    supported_formats = Column(JSON, nullable=True)
    
    # Model parameters
    parameters = Column(JSON, nullable=True)
    default_settings = Column(JSON, nullable=True)
    
    # Performance characteristics
    average_processing_time = Column(Float, nullable=True)
    memory_requirements = Column(Integer, nullable=True)  # in MB
    gpu_requirements = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_loaded = Column(Boolean, default=False)
    load_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)