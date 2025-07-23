"""
Database models for CDN service
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.base import Base


class CDNDistribution(Base):
    """CDN distribution database model"""
    __tablename__ = "cdn_distributions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id = Column(String(255), unique=True, nullable=False, index=True)
    provider_id = Column(String(50), nullable=False, index=True)
    provider_distribution_id = Column(String(255), nullable=True)
    
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="creating")
    enabled = Column(Boolean, default=True)
    
    domain_name = Column(String(255), nullable=True)
    custom_domain = Column(String(255), nullable=True)
    certificate_arn = Column(String(255), nullable=True)
    
    # Configuration
    origins = Column(JSON, nullable=False)
    cache_rules = Column(JSON, nullable=False)
    security_policy = Column(JSON, nullable=False)
    
    # Logging
    logging_enabled = Column(Boolean, default=False)
    logging_bucket = Column(String(255), nullable=True)
    logging_prefix = Column(String(255), nullable=True)
    realtime_logs_enabled = Column(Boolean, default=False)
    realtime_logs_config = Column(String(255), nullable=True)
    
    # Metadata
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    metrics = relationship("CDNMetric", back_populates="distribution", cascade="all, delete-orphan")
    purge_requests = relationship("CDNPurgeRequest", back_populates="distribution", cascade="all, delete-orphan")
    optimizations = relationship("CDNOptimization", back_populates="distribution", cascade="all, delete-orphan")
    alerts = relationship("CDNAlert", back_populates="distribution", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_cdn_distributions_status", "status"),
        Index("idx_cdn_distributions_custom_domain", "custom_domain"),
    )


class CDNMetric(Base):
    """CDN metrics database model"""
    __tablename__ = "cdn_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Request metrics
    requests_total = Column(Integer, default=0)
    requests_cached = Column(Integer, default=0)
    cache_hit_rate = Column(Float, default=0.0)
    
    # Bandwidth metrics
    bandwidth_bytes = Column(BigInteger, default=0)
    bandwidth_cached_bytes = Column(BigInteger, default=0)
    
    # Visitor metrics
    unique_visitors = Column(Integer, default=0)
    unique_countries = Column(Integer, default=0)
    
    # Error metrics
    error_4xx_count = Column(Integer, default=0)
    error_5xx_count = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)
    
    # Performance metrics
    avg_response_time_ms = Column(Float, default=0.0)
    avg_origin_response_time_ms = Column(Float, default=0.0)
    p95_response_time_ms = Column(Float, default=0.0)
    p99_response_time_ms = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    distribution = relationship("CDNDistribution", back_populates="metrics")
    
    __table_args__ = (
        Index("idx_cdn_metrics_distribution_time", "distribution_id", "period_start"),
        Index("idx_cdn_metrics_period", "period_start", "period_end"),
    )


class CDNPurgeRequest(Base):
    """CDN cache purge request database model"""
    __tablename__ = "cdn_purge_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    # Purge configuration
    paths = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    purge_all = Column(Boolean, default=False)
    
    # Status
    status = Column(String(50), nullable=False, default="pending")
    provider_request_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metrics
    objects_purged = Column(Integer, default=0)
    bytes_purged = Column(BigInteger, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # User tracking
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    distribution = relationship("CDNDistribution", back_populates="purge_requests")
    
    __table_args__ = (
        Index("idx_cdn_purge_requests_status", "status"),
        Index("idx_cdn_purge_requests_created", "created_at"),
    )


class CDNOptimization(Base):
    """CDN content optimization configuration"""
    __tablename__ = "cdn_optimizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    optimization_id = Column(String(255), unique=True, nullable=False, index=True)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    optimization_type = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    settings = Column(JSON, nullable=False)
    
    # Metrics
    files_optimized = Column(Integer, default=0)
    bytes_saved = Column(BigInteger, default=0)
    optimization_ratio = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    distribution = relationship("CDNDistribution", back_populates="optimizations")
    
    __table_args__ = (
        Index("idx_cdn_optimizations_type", "optimization_type"),
    )


class CDNAlert(Base):
    """CDN alert configuration"""
    __tablename__ = "cdn_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(String(255), unique=True, nullable=False, index=True)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=False)
    comparison_operator = Column(String(20), nullable=False)
    evaluation_periods = Column(Integer, default=3)
    period_seconds = Column(Integer, default=300)
    
    enabled = Column(Boolean, default=True)
    notification_channels = Column(JSON, default=list)
    
    # Alert state
    current_state = Column(String(20), default="ok")  # ok, alerting, insufficient_data
    last_state_change = Column(DateTime(timezone=True), nullable=True)
    last_notification = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    distribution = relationship("CDNDistribution", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_cdn_alerts_type_state", "alert_type", "current_state"),
        Index("idx_cdn_alerts_enabled", "enabled"),
    )


class CDNAccessLog(Base):
    """CDN access log entries (sampled)"""
    __tablename__ = "cdn_access_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    client_ip = Column(String(45), nullable=False)
    method = Column(String(10), nullable=False)
    uri = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=False)
    bytes_sent = Column(BigInteger, default=0)
    
    referer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    edge_location = Column(String(50), nullable=True)
    cache_status = Column(String(20), nullable=True)
    response_time_ms = Column(Float, nullable=True)
    
    ssl_protocol = Column(String(20), nullable=True)
    ssl_cipher = Column(String(50), nullable=True)
    edge_result_type = Column(String(20), nullable=True)
    
    __table_args__ = (
        Index("idx_cdn_access_logs_timestamp", "timestamp"),
        Index("idx_cdn_access_logs_status", "status_code"),
        Index("idx_cdn_access_logs_cache", "cache_status"),
        # Partition by month for efficient data management
        {"postgresql_partition_by": "RANGE (timestamp)"}
    )


class CDNCostTracking(Base):
    """CDN cost tracking and estimates"""
    __tablename__ = "cdn_cost_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("cdn_distributions.id"), nullable=False)
    
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Usage metrics
    data_transfer_gb = Column(Float, default=0.0)
    requests_millions = Column(Float, default=0.0)
    invalidation_requests = Column(Integer, default=0)
    field_level_encryption_requests = Column(Integer, default=0)
    
    # Cost breakdown
    data_transfer_cost = Column(Float, default=0.0)
    requests_cost = Column(Float, default=0.0)
    invalidation_cost = Column(Float, default=0.0)
    field_level_encryption_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    currency = Column(String(3), default="USD")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_cdn_cost_tracking_period", "distribution_id", "period_start"),
    )


class CDNProviderConfig(Base):
    """CDN provider configuration"""
    __tablename__ = "cdn_provider_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(String(50), unique=True, nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)
    
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    configuration = Column(JSON, nullable=False)
    
    api_endpoint = Column(String(255), nullable=True)
    regions_available = Column(JSON, default=list)
    features_supported = Column(JSON, default=list)
    
    # Credentials (encrypted in production)
    api_credentials = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Add BigInteger type for large numbers
from sqlalchemy import BigInteger


class User(Base):
    """User model stub for foreign key references"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())