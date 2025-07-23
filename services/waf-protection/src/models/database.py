"""
Database models for WAF Protection Service
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class CustomRule(Base):
    """Custom WAF rule model"""
    __tablename__ = "custom_rules"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    priority = Column(Integer, default=100, nullable=False, index=True)
    threat_level = Column(String(20), nullable=False, index=True)
    score = Column(Integer, default=50, nullable=False)
    
    # Rule configuration
    conditions = Column(JSON, nullable=False)  # Serialized conditions
    rate_limit_window = Column(Integer, nullable=True)
    rate_limit_threshold = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Statistics
    match_count = Column(Integer, default=0, nullable=False)
    block_count = Column(Integer, default=0, nullable=False)
    last_matched = Column(DateTime(timezone=True), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_custom_rules_enabled_priority', 'enabled', 'priority'),
        Index('idx_custom_rules_threat_level', 'threat_level'),
        Index('idx_custom_rules_action', 'action'),
    )


class BlockedRequest(Base):
    """Blocked request log model"""
    __tablename__ = "blocked_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request information
    ip = Column(String(45), nullable=False, index=True)  # IPv6 max length
    method = Column(String(10), nullable=False)
    url = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    headers = Column(JSON, nullable=True)
    body_hash = Column(String(64), nullable=True)  # SHA256 hash of body for privacy
    
    # Block information
    rule_triggered = Column(String(255), nullable=False, index=True)
    threat_level = Column(String(20), nullable=False, index=True)
    block_reason = Column(Text, nullable=False)
    score = Column(Integer, nullable=False, index=True)
    
    # Metadata
    country_code = Column(String(2), nullable=True, index=True)
    country_name = Column(String(100), nullable=True)
    is_bot = Column(Boolean, nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_blocked_requests_ip_timestamp', 'ip', 'timestamp'),
        Index('idx_blocked_requests_rule_timestamp', 'rule_triggered', 'timestamp'),
        Index('idx_blocked_requests_threat_timestamp', 'threat_level', 'timestamp'),
        Index('idx_blocked_requests_country_timestamp', 'country_code', 'timestamp'),
    )


class WAFMetrics(Base):
    """WAF metrics and statistics model"""
    __tablename__ = "waf_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric information
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)
    
    # Context
    ip = Column(String(45), nullable=True, index=True)
    rule_id = Column(String(255), nullable=True, index=True)
    country_code = Column(String(2), nullable=True, index=True)
    threat_level = Column(String(20), nullable=True, index=True)
    
    # Additional data
    metadata = Column(JSON, nullable=True)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    time_period = Column(String(20), nullable=True, index=True)  # minute, hour, day
    
    # Indexes
    __table_args__ = (
        Index('idx_waf_metrics_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_waf_metrics_ip_timestamp', 'ip', 'timestamp'),
        Index('idx_waf_metrics_rule_timestamp', 'rule_id', 'timestamp'),
        Index('idx_waf_metrics_period_timestamp', 'time_period', 'timestamp'),
    )


class IPWhitelist(Base):
    """IP whitelist model"""
    __tablename__ = "ip_whitelist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_range = Column(String(50), nullable=False, unique=True, index=True)  # IP or CIDR
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # Usage statistics
    hit_count = Column(Integer, default=0, nullable=False)
    last_hit = Column(DateTime(timezone=True), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Optional expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)


class IPBlacklist(Base):
    """IP blacklist model"""
    __tablename__ = "ip_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_range = Column(String(50), nullable=False, unique=True, index=True)  # IP or CIDR
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # Block information
    reason = Column(String(255), nullable=True)
    threat_level = Column(String(20), nullable=False, default="medium", index=True)
    
    # Usage statistics
    hit_count = Column(Integer, default=0, nullable=False)
    last_hit = Column(DateTime(timezone=True), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Optional expiration
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)


class WAFConfig(Base):
    """WAF configuration model"""
    __tablename__ = "waf_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    config_type = Column(String(50), nullable=False, default="general")  # general, rule, threshold, etc.
    is_sensitive = Column(Boolean, default=False, nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)
    
    # Version tracking
    version = Column(Integer, default=1, nullable=False)


class AlertRule(Base):
    """Alert rule model"""
    __tablename__ = "alert_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # Alert conditions
    condition_metric = Column(String(100), nullable=False)  # blocked_requests, threat_score, etc.
    condition_operator = Column(String(20), nullable=False)  # gt, lt, eq, etc.
    condition_value = Column(Float, nullable=False)
    condition_window = Column(Integer, nullable=False, default=300)  # seconds
    
    # Alert actions
    webhook_url = Column(String(1024), nullable=True)
    email_recipients = Column(JSON, nullable=True)  # List of email addresses
    severity = Column(String(20), nullable=False, default="medium")
    
    # Rate limiting for alerts
    cooldown_seconds = Column(Integer, default=300, nullable=False)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SuspiciousActivity(Base):
    """Suspicious activity tracking model"""
    __tablename__ = "suspicious_activity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Activity information
    ip = Column(String(45), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)  # repeated_blocks, scanning, etc.
    severity = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Pattern information
    pattern_data = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    
    # Context
    user_agent = Column(Text, nullable=True)
    country_code = Column(String(2), nullable=True, index=True)
    first_seen = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    
    # Status
    status = Column(String(20), nullable=False, default="active", index=True)  # active, resolved, ignored
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Auto-escalation
    auto_blocked = Column(Boolean, default=False, nullable=False)
    escalation_level = Column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_suspicious_activity_ip_type', 'ip', 'activity_type'),
        Index('idx_suspicious_activity_severity_status', 'severity', 'status'),
        Index('idx_suspicious_activity_last_seen', 'last_seen'),
    )