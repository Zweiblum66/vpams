"""
Database models for failover service
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.base import Base


class FailoverEventDB(Base):
    """Failover event database model"""
    __tablename__ = "failover_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    
    from_region = Column(String(50), nullable=False)
    to_region = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    triggered_by = Column(String(255), nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    success = Column(Boolean, nullable=True)
    services_affected = Column(JSON, default=list)
    data_loss_assessment = Column(JSON, nullable=True)
    
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_failover_events_type", "event_type"),
        Index("idx_failover_events_state", "state"),
        Index("idx_failover_events_started", "started_at"),
    )


class RegionHealthDB(Base):
    """Region health history database model"""
    __tablename__ = "region_health_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    
    health_percentage = Column(Float, default=0.0)
    latency_ms = Column(Float, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    services = Column(JSON, default=dict)
    database_status = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    
    checked_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_region_health_checked", "region", "checked_at"),
    )


class ServiceHealthDB(Base):
    """Service health history database model"""
    __tablename__ = "service_health_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    
    response_time_ms = Column(Float, nullable=True)
    error_count = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)
    
    checked_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_service_health_checked", "service_name", "region", "checked_at"),
        Index("idx_service_health_status", "status"),
    )


class FailoverPlanDB(Base):
    """Failover plan database model"""
    __tablename__ = "failover_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    source_region = Column(String(50), nullable=False)
    target_region = Column(String(50), nullable=False)
    
    services = Column(JSON, default=list)
    pre_checks = Column(JSON, default=list)
    steps = Column(JSON, default=list)
    post_checks = Column(JSON, default=list)
    rollback_steps = Column(JSON, default=list)
    
    estimated_downtime_minutes = Column(Integer, default=15)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class DataConsistencyCheckDB(Base):
    """Data consistency check results database model"""
    __tablename__ = "data_consistency_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id = Column(String(255), unique=True, nullable=False, index=True)
    
    regions_compared = Column(JSON, nullable=False)
    check_type = Column(String(50), nullable=False)
    
    inconsistencies_found = Column(Integer, default=0)
    records_checked = Column(Integer, default=0)
    services_checked = Column(JSON, default=dict)
    details = Column(JSON, default=list)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_consistency_checks_started", "started_at"),
    )


class NotificationHistoryDB(Base):
    """Notification history database model"""
    __tablename__ = "notification_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    notification_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    
    channels = Column(JSON, default=list)
    recipients = Column(JSON, default=dict)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    event_id = Column(String(255), nullable=True)
    metadata = Column(JSON, default=dict)
    
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_notifications_type", "notification_type"),
        Index("idx_notifications_severity", "severity"),
        Index("idx_notifications_sent", "sent_at"),
    )


class FailoverMetricsDB(Base):
    """Aggregated failover metrics database model"""
    __tablename__ = "failover_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    metric_date = Column(DateTime(timezone=True), nullable=False, unique=True)
    
    total_failovers = Column(Integer, default=0)
    successful_failovers = Column(Integer, default=0)
    failed_failovers = Column(Integer, default=0)
    
    average_failover_time_seconds = Column(Float, default=0.0)
    min_failover_time_seconds = Column(Float, nullable=True)
    max_failover_time_seconds = Column(Float, nullable=True)
    
    availability_percentage = Column(Float, default=100.0)
    data_loss_incidents = Column(Integer, default=0)
    
    by_region = Column(JSON, default=dict)
    by_type = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_metrics_date", "metric_date"),
    )


class RegionConfigurationDB(Base):
    """Region configuration database model"""
    __tablename__ = "region_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region = Column(String(50), unique=True, nullable=False, index=True)
    
    is_primary = Column(Boolean, default=False)
    endpoints = Column(JSON, default=dict)
    capacity = Column(JSON, default=dict)
    features_enabled = Column(JSON, default=list)
    replication_targets = Column(JSON, default=list)
    
    failover_priority = Column(Integer, default=0)
    auto_failover_enabled = Column(Boolean, default=True)
    maintenance_windows = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    """User model stub for foreign key references"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())