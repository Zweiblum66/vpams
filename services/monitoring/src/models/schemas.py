"""
Pydantic schemas for Monitoring Service
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ServiceStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertCondition(str, Enum):
    """Alert rule conditions"""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"


class ServiceHealth(BaseModel):
    """Service health information"""
    name: str
    status: ServiceStatus
    version: Optional[str] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)


class SystemStatus(BaseModel):
    """Overall system status"""
    status: ServiceStatus
    timestamp: datetime
    services: List[Dict[str, Any]]
    healthy_services: int
    total_services: int
    alerts: List[Dict[str, Any]] = []


class MetricsSummary(BaseModel):
    """Summary of key metrics"""
    period: str
    timestamp: datetime
    total_users: int
    active_users: int
    total_assets: int
    storage_used_gb: float
    api_requests_count: int
    avg_response_time_ms: float
    error_rate: float
    active_workflows: int
    processing_queue_size: int


class ServiceMetrics(BaseModel):
    """Detailed metrics for a service"""
    service_name: str
    period: str
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_mb: float
    request_count: int
    error_count: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    active_connections: int
    health_score: float = Field(ge=0, le=1)


class AlertRule(BaseModel):
    """Alert rule configuration"""
    id: Optional[str] = None
    name: str
    description: str
    metric: str
    condition: AlertCondition
    threshold: float
    duration_seconds: int = Field(
        default=300,
        description="How long condition must be true before alert triggers"
    )
    severity: AlertSeverity
    service: str = Field(default="all", description="Service name or 'all'")
    enabled: bool = True
    notification_channels: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AlertStatus(BaseModel):
    """Active alert status"""
    id: str
    rule_name: str
    severity: AlertSeverity
    service: str
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    value: float
    threshold: float
    status: str = Field(default="active", description="active, acknowledged, resolved")
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class MetricDataPoint(BaseModel):
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = {}


class MetricTimeSeries(BaseModel):
    """Time series data for a metric"""
    metric_name: str
    labels: Dict[str, str]
    data_points: List[MetricDataPoint]
    unit: Optional[str] = None
    description: Optional[str] = None


class DashboardConfig(BaseModel):
    """Dashboard configuration"""
    id: Optional[str] = None
    name: str
    description: str
    type: str = Field(default="grafana", description="grafana, custom")
    config: Dict[str, Any]
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationChannel(BaseModel):
    """Notification channel configuration"""
    id: Optional[str] = None
    name: str
    type: str = Field(description="email, slack, webhook, pagerduty")
    config: Dict[str, Any]
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HealthCheckConfig(BaseModel):
    """Health check configuration"""
    service_name: str
    endpoint: str
    interval_seconds: int = 60
    timeout_seconds: int = 10
    success_threshold: int = 1
    failure_threshold: int = 3
    enabled: bool = True


class MetricsExportRequest(BaseModel):
    """Request to export metrics"""
    metrics: List[str]
    start_time: datetime
    end_time: datetime
    format: str = Field(default="csv", description="csv, json, prometheus")
    resolution: Optional[str] = Field(
        default="1m",
        description="Data resolution: 1m, 5m, 1h, 1d"
    )
    filters: Dict[str, str] = {}