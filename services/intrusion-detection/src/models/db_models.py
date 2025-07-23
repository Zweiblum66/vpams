"""Database models for Intrusion Detection Service"""

from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, JSON, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base import Base
import uuid


class IntrusionEvent(Base):
    """Intrusion detection event record"""
    __tablename__ = "intrusion_events"
    __table_args__ = (
        Index("idx_intrusion_events_timestamp", "timestamp"),
        Index("idx_intrusion_events_severity", "severity"),
        Index("idx_intrusion_events_source_ip", "source_ip"),
        Index("idx_intrusion_events_event_type", "event_type"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type = Column(String(100), nullable=False)  # port_scan, brute_force, malware, ddos, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    confidence = Column(Float, nullable=False, default=1.0)
    
    # Network information
    source_ip = Column(String(45))  # IPv4/IPv6
    source_port = Column(Integer)
    destination_ip = Column(String(45))
    destination_port = Column(Integer)
    protocol = Column(String(20))  # TCP, UDP, ICMP, etc.
    
    # Event details
    description = Column(Text)
    signature_id = Column(String(50))
    signature_name = Column(String(200))
    raw_data = Column(JSON)
    
    # Detection metadata
    detection_method = Column(String(50))  # signature, anomaly, behavioral
    rule_id = Column(String(100))
    threat_category = Column(String(100))
    
    # Response information
    action_taken = Column(String(50))  # blocked, allowed, monitored
    blocked = Column(Boolean, default=False)
    
    # Relationships
    alert_id = Column(UUID(as_uuid=True), ForeignKey("security_alerts.id"))
    alert = relationship("SecurityAlert", back_populates="events")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SecurityAlert(Base):
    """Security alert aggregating multiple events"""
    __tablename__ = "security_alerts"
    __table_args__ = (
        Index("idx_security_alerts_status", "status"),
        Index("idx_security_alerts_severity", "severity"),
        Index("idx_security_alerts_created_at", "created_at"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False)
    status = Column(String(50), default="open")  # open, investigating, resolved, false_positive
    
    # Alert metadata
    alert_type = Column(String(100), nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    event_count = Column(Integer, default=1)
    
    # Affected resources
    affected_systems = Column(JSON)  # List of affected system IPs/hostnames
    affected_users = Column(JSON)  # List of affected user IDs
    
    # Investigation details
    assigned_to = Column(String(100))
    priority = Column(Integer, default=3)  # 1-5, 1 being highest
    investigation_notes = Column(Text)
    resolution_notes = Column(Text)
    
    # Response actions
    actions_taken = Column(JSON)
    recommendations = Column(JSON)
    
    # Relationships
    events = relationship("IntrusionEvent", back_populates="alert")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))


class NetworkBaseline(Base):
    """Network traffic baseline for anomaly detection"""
    __tablename__ = "network_baselines"
    __table_args__ = (
        Index("idx_network_baselines_metric_hour", "metric_name", "hour_of_day"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False)
    hour_of_day = Column(Integer, nullable=False)  # 0-23
    day_of_week = Column(Integer, nullable=False)  # 0-6
    
    # Statistical values
    mean_value = Column(Float, nullable=False)
    std_deviation = Column(Float, nullable=False)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    percentile_95 = Column(Float, nullable=False)
    
    # Sample information
    sample_count = Column(Integer, nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ThreatIntelligence(Base):
    """Threat intelligence indicators"""
    __tablename__ = "threat_intelligence"
    __table_args__ = (
        Index("idx_threat_intelligence_indicator", "indicator"),
        Index("idx_threat_intelligence_type", "indicator_type"),
        Index("idx_threat_intelligence_active", "is_active"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator = Column(String(500), nullable=False, unique=True)
    indicator_type = Column(String(50), nullable=False)  # ip, domain, hash, url, etc.
    threat_type = Column(String(100))  # malware, phishing, botnet, etc.
    
    # Threat details
    description = Column(Text)
    severity = Column(String(20))
    confidence = Column(Float, default=1.0)
    tags = Column(JSON)
    
    # Source information
    source = Column(String(100), nullable=False)
    source_url = Column(String(500))
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    false_positive = Column(Boolean, default=False)
    
    # Additional metadata
    metadata = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))


class FileIntegrityRecord(Base):
    """File integrity monitoring records"""
    __tablename__ = "file_integrity_records"
    __table_args__ = (
        Index("idx_file_integrity_file_path", "file_path"),
        Index("idx_file_integrity_changed", "changed"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String(1000), nullable=False)
    
    # File attributes
    file_hash = Column(String(128), nullable=False)  # SHA-256
    file_size = Column(Integer)
    permissions = Column(String(10))
    owner = Column(String(100))
    group = Column(String(100))
    
    # Monitoring status
    changed = Column(Boolean, default=False)
    change_type = Column(String(50))  # created, modified, deleted, permissions
    previous_hash = Column(String(128))
    
    # Timestamps
    last_checked = Column(DateTime(timezone=True), nullable=False)
    last_modified = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemActivity(Base):
    """System activity monitoring"""
    __tablename__ = "system_activities"
    __table_args__ = (
        Index("idx_system_activities_timestamp", "timestamp"),
        Index("idx_system_activities_activity_type", "activity_type"),
        Index("idx_system_activities_user", "user"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    activity_type = Column(String(100), nullable=False)  # login, command, process_start, etc.
    
    # Activity details
    user = Column(String(100))
    process_name = Column(String(200))
    command_line = Column(Text)
    source_ip = Column(String(45))
    
    # Risk assessment
    risk_score = Column(Float, default=0.0)
    suspicious = Column(Boolean, default=False)
    
    # Additional data
    metadata = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())