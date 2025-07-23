"""
Database models for Monitoring Service
"""

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON,
    ForeignKey, Index, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class AlertRule(Base):
    """Alert rule definitions"""
    __tablename__ = "alert_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    metric = Column(String(255), nullable=False)
    condition = Column(String(50), nullable=False)  # greater_than, less_than, equals
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=300)
    severity = Column(String(50), nullable=False)  # critical, warning, info
    service = Column(String(100), default="all")
    enabled = Column(Boolean, default=True)
    notification_channels = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_alert_rules_service", "service"),
        Index("idx_alert_rules_enabled", "enabled"),
    )


class Alert(Base):
    """Active and historical alerts"""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False)
    severity = Column(String(50), nullable=False)
    service = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    status = Column(String(50), default="active")  # active, acknowledged, resolved
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime(timezone=True))
    metadata = Column(JSON, default=dict)
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_alerts_status", "status"),
        Index("idx_alerts_service", "service"),
        Index("idx_alerts_triggered_at", "triggered_at"),
    )


class HealthCheck(Base):
    """Service health check results"""
    __tablename__ = "health_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # healthy, degraded, unhealthy
    response_time_ms = Column(Float)
    error_message = Column(Text)
    version = Column(String(50))
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSON, default=dict)
    
    __table_args__ = (
        Index("idx_health_checks_service", "service_name"),
        Index("idx_health_checks_checked_at", "checked_at"),
    )


class MetricSnapshot(Base):
    """Periodic snapshots of key metrics"""
    __tablename__ = "metric_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    metric_name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    service = Column(String(100))
    
    __table_args__ = (
        Index("idx_metric_snapshots_timestamp", "timestamp"),
        Index("idx_metric_snapshots_metric_name", "metric_name"),
        Index("idx_metric_snapshots_service", "service"),
    )


class ServiceMetrics(Base):
    """Aggregated service metrics"""
    __tablename__ = "service_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    cpu_usage_percent = Column(Float)
    memory_usage_mb = Column(Float)
    request_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_response_time_ms = Column(Float)
    p95_response_time_ms = Column(Float)
    p99_response_time_ms = Column(Float)
    active_connections = Column(Integer, default=0)
    health_score = Column(Float)
    metadata = Column(JSON, default=dict)
    
    __table_args__ = (
        Index("idx_service_metrics_service_timestamp", "service_name", "timestamp"),
    )


class Dashboard(Base):
    """Custom dashboard configurations"""
    __tablename__ = "dashboards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default="grafana")
    config = Column(JSON, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("name", name="uq_dashboard_name"),
    )


class NotificationChannel(Base):
    """Notification channel configurations"""
    __tablename__ = "notification_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # email, slack, webhook, pagerduty
    config = Column(JSON, nullable=False)  # Encrypted in production
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("name", name="uq_notification_channel_name"),
        Index("idx_notification_channels_type", "type"),
    )


class AuditLog(Base):
    """Audit log for monitoring system changes"""
    __tablename__ = "monitoring_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    changes = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    __table_args__ = (
        Index("idx_monitoring_audit_logs_timestamp", "timestamp"),
        Index("idx_monitoring_audit_logs_user_id", "user_id"),
        Index("idx_monitoring_audit_logs_resource", "resource_type", "resource_id"),
    )