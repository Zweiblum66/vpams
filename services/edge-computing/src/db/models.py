"""
Database models for Edge Computing Service
"""

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    Text, JSON, Enum, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base
from ..models.schemas import (
    NodeType, NodeStatus, TaskType, TaskStatus,
    TaskPriority, CacheStatus, AlertType
)


class EdgeNodeModel(Base):
    """Edge node database model"""
    __tablename__ = "edge_nodes"
    
    node_id = Column(String(255), primary_key=True)
    node_type = Column(Enum(NodeType), nullable=False)
    location = Column(String(255), nullable=False)
    status = Column(Enum(NodeStatus), default=NodeStatus.OFFLINE, nullable=False)
    capabilities = Column(JSON, default=list)
    resources = Column(JSON, default=dict)
    performance_metrics = Column(JSON, default=dict)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("ProcessingTaskModel", back_populates="node")
    cache_entries = relationship("CacheEntryModel", back_populates="node")
    metrics = relationship("EdgeMetricsModel", back_populates="node")
    alerts = relationship("EdgeAlertModel", back_populates="node")
    
    # Indexes
    __table_args__ = (
        Index("idx_edge_nodes_status", "status"),
        Index("idx_edge_nodes_location", "location"),
        Index("idx_edge_nodes_last_heartbeat", "last_heartbeat"),
    )


class ProcessingTaskModel(Base):
    """Processing task database model"""
    __tablename__ = "processing_tasks"
    
    task_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.NORMAL, nullable=False)
    asset_id = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=False)
    assigned_node = Column(String(255), ForeignKey("edge_nodes.node_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    progress = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    node = relationship("EdgeNodeModel", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index("idx_processing_tasks_status", "status"),
        Index("idx_processing_tasks_priority", "priority"),
        Index("idx_processing_tasks_assigned_node", "assigned_node"),
        Index("idx_processing_tasks_created_at", "created_at"),
        Index("idx_processing_tasks_asset_id", "asset_id"),
    )


class CacheEntryModel(Base):
    """Cache entry database model"""
    __tablename__ = "cache_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False)
    asset_id = Column(String(255), nullable=False)
    node_id = Column(String(255), ForeignKey("edge_nodes.node_id"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(255), nullable=False)
    status = Column(Enum(CacheStatus), default=CacheStatus.CACHED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    access_count = Column(Integer, default=0)
    ttl_seconds = Column(Integer, nullable=True)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    node = relationship("EdgeNodeModel", back_populates="cache_entries")
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("cache_key", "node_id", name="uq_cache_key_node"),
        Index("idx_cache_entries_node_id", "node_id"),
        Index("idx_cache_entries_asset_id", "asset_id"),
        Index("idx_cache_entries_status", "status"),
        Index("idx_cache_entries_last_accessed", "last_accessed"),
    )


class EdgeMetricsModel(Base):
    """Edge metrics database model"""
    __tablename__ = "edge_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    node_id = Column(String(255), ForeignKey("edge_nodes.node_id"), nullable=False)
    tasks_processed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    avg_processing_time = Column(Float, default=0.0)
    cache_hit_rate = Column(Float, default=0.0)
    bandwidth_usage_mbps = Column(Float, default=0.0)
    storage_usage_gb = Column(Float, default=0.0)
    cpu_utilization = Column(Float, default=0.0)
    memory_utilization = Column(Float, default=0.0)
    gpu_utilization = Column(Float, nullable=True)
    
    # Relationships
    node = relationship("EdgeNodeModel", back_populates="metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_edge_metrics_timestamp", "timestamp"),
        Index("idx_edge_metrics_node_id", "node_id"),
        Index("idx_edge_metrics_node_timestamp", "node_id", "timestamp"),
    )


class EdgeAlertModel(Base):
    """Edge alert database model"""
    __tablename__ = "edge_alerts"
    
    alert_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(String(50), nullable=False)
    node_id = Column(String(255), ForeignKey("edge_nodes.node_id"), nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    node = relationship("EdgeNodeModel", back_populates="alerts")
    
    # Indexes
    __table_args__ = (
        Index("idx_edge_alerts_alert_type", "alert_type"),
        Index("idx_edge_alerts_severity", "severity"),
        Index("idx_edge_alerts_node_id", "node_id"),
        Index("idx_edge_alerts_created_at", "created_at"),
        Index("idx_edge_alerts_resolved", "resolved"),
    )


class TaskAssignmentModel(Base):
    """Task assignment history"""
    __tablename__ = "task_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), ForeignKey("processing_tasks.task_id"), nullable=False)
    node_id = Column(String(255), ForeignKey("edge_nodes.node_id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    success = Column(Boolean, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_task_assignments_task_id", "task_id"),
        Index("idx_task_assignments_node_id", "node_id"),
        Index("idx_task_assignments_assigned_at", "assigned_at"),
    )