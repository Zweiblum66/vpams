"""
Database models for geo-replication service
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, UniqueConstraint, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class ReplicationStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConflictStatus(enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    ESCALATED = "escalated"


class RegionStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"
    MAINTENANCE = "maintenance"


class ReplicationRegion(Base):
    """Region configuration for replication"""
    __tablename__ = "replication_regions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(String(50), unique=True, nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    status = Column(SQLEnum(RegionStatus), default=RegionStatus.ACTIVE, nullable=False)
    
    # Endpoints
    database_endpoint = Column(String(500), nullable=False)
    redis_endpoint = Column(String(500), nullable=False)
    mongodb_endpoint = Column(String(500), nullable=False)
    opensearch_endpoint = Column(String(500), nullable=False)
    s3_endpoint = Column(String(500), nullable=False)
    
    # Health metrics
    last_health_check = Column(DateTime(timezone=True), server_default=func.now())
    health_check_passed = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    
    # Configuration
    failover_priority = Column(Integer, default=100)
    automatic_failover = Column(Boolean, default=True)
    bandwidth_limit_mbps = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    jobs_as_source = relationship("ReplicationJob", foreign_keys="ReplicationJob.source_region_id", back_populates="source_region")
    jobs_as_target = relationship("ReplicationJob", foreign_keys="ReplicationJob.target_region_id", back_populates="target_region")
    metrics = relationship("ReplicationMetric", back_populates="region", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_region_status", "status"),
        Index("idx_region_primary", "is_primary"),
    )


class ReplicationJob(Base):
    """Replication job tracking"""
    __tablename__ = "replication_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Region information
    source_region_id = Column(UUID(as_uuid=True), ForeignKey("replication_regions.id"), nullable=False)
    target_region_id = Column(UUID(as_uuid=True), ForeignKey("replication_regions.id"), nullable=False)
    
    # Job details
    replication_type = Column(String(50), nullable=False)  # database, files, cache, search, metadata
    resource_type = Column(String(100), nullable=True)
    resource_ids = Column(JSON, nullable=True)  # List of resource IDs being replicated
    
    # Status
    status = Column(SQLEnum(ReplicationStatus), default=ReplicationStatus.PENDING, nullable=False)
    progress_percentage = Column(Float, default=0.0)
    
    # Metrics
    items_total = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    bytes_transferred = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Configuration
    priority = Column(Integer, default=50)  # 0-100, higher = more priority
    batch_size = Column(Integer, default=1000)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    source_region = relationship("ReplicationRegion", foreign_keys=[source_region_id], back_populates="jobs_as_source")
    target_region = relationship("ReplicationRegion", foreign_keys=[target_region_id], back_populates="jobs_as_target")
    
    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_type", "replication_type"),
        Index("idx_job_created", "created_at"),
        Index("idx_job_source_target", "source_region_id", "target_region_id"),
    )


class ReplicationMetric(Base):
    """Metrics for replication monitoring"""
    __tablename__ = "replication_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Region and type
    region_id = Column(UUID(as_uuid=True), ForeignKey("replication_regions.id"), nullable=False)
    replication_type = Column(String(50), nullable=False)
    
    # Metrics
    items_pending = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    bytes_transferred = Column(Integer, default=0)
    
    # Performance
    lag_seconds = Column(Float, default=0.0)
    throughput_mbps = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    
    # Time window
    metric_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    region = relationship("ReplicationRegion", back_populates="metrics")
    
    __table_args__ = (
        Index("idx_metric_region_type", "region_id", "replication_type"),
        Index("idx_metric_timestamp", "metric_timestamp"),
        Index("idx_metric_window", "window_start", "window_end"),
    )


class ReplicationConflict(Base):
    """Conflicts detected during replication"""
    __tablename__ = "replication_conflicts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conflict_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Conflict details
    conflict_type = Column(String(100), nullable=False)  # data_mismatch, version_conflict, constraint_violation
    source_region = Column(String(50), nullable=False)
    target_region = Column(String(50), nullable=False)
    
    # Resource information
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(500), nullable=False)
    resource_path = Column(String(1000), nullable=True)
    
    # Conflict data
    source_data = Column(JSON, nullable=True)
    target_data = Column(JSON, nullable=True)
    diff_data = Column(JSON, nullable=True)
    
    # Version information
    source_version = Column(String(100), nullable=True)
    target_version = Column(String(100), nullable=True)
    version_vector = Column(JSON, nullable=True)
    
    # Resolution
    status = Column(SQLEnum(ConflictStatus), default=ConflictStatus.PENDING, nullable=False)
    resolution_method = Column(String(100), nullable=True)
    resolution_data = Column(JSON, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_conflict_status", "status"),
        Index("idx_conflict_type", "conflict_type"),
        Index("idx_conflict_resource", "resource_type", "resource_id"),
        Index("idx_conflict_detected", "detected_at"),
    )


class ReplicationEvent(Base):
    """Events in the replication system"""
    __tablename__ = "replication_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Event information
    event_type = Column(String(100), nullable=False)  # sync_started, sync_completed, conflict_detected, failover
    severity = Column(String(50), default="info")  # info, warning, error, critical
    
    # Source and targets
    source_region = Column(String(50), nullable=False)
    target_regions = Column(JSON, default=list)
    
    # Resource information
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(500), nullable=True)
    
    # Event data
    data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    
    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_event_type", "event_type"),
        Index("idx_event_timestamp", "timestamp"),
        Index("idx_event_processed", "processed"),
        Index("idx_event_severity", "severity"),
    )


class ReplicationCheckpoint(Base):
    """Checkpoints for resumable replication"""
    __tablename__ = "replication_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Checkpoint identification
    source_region = Column(String(50), nullable=False)
    target_region = Column(String(50), nullable=False)
    replication_type = Column(String(50), nullable=False)
    
    # Checkpoint data
    checkpoint_data = Column(JSON, nullable=False)
    last_processed_id = Column(String(500), nullable=True)
    last_processed_timestamp = Column(DateTime(timezone=True), nullable=True)
    items_processed = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("source_region", "target_region", "replication_type", name="uq_checkpoint"),
        Index("idx_checkpoint_regions", "source_region", "target_region"),
    )


class ReplicationSchedule(Base):
    """Scheduled replication tasks"""
    __tablename__ = "replication_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Schedule identification
    schedule_name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    source_region = Column(String(50), nullable=False)
    target_regions = Column(JSON, default=list)
    replication_type = Column(String(50), nullable=False)
    
    # Schedule
    cron_expression = Column(String(100), nullable=True)  # For cron-based scheduling
    interval_seconds = Column(Integer, nullable=True)  # For interval-based scheduling
    
    # Status
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    
    # Options
    options = Column(JSON, default=dict)  # Additional configuration options
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_schedule_enabled", "enabled"),
        Index("idx_schedule_next_run", "next_run"),
    )