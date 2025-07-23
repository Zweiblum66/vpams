"""
Pydantic models for failover service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class RegionStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    STANDBY = "standby"


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class FailoverState(str, Enum):
    NORMAL = "normal"
    FAILING_OVER = "failing_over"
    FAILED_OVER = "failed_over"
    FAILING_BACK = "failing_back"


class FailoverType(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"


class LoadBalancerAlgorithm(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    GEOGRAPHIC = "geographic"
    LATENCY_BASED = "latency_based"


class RegionHealth(BaseModel):
    """Health status of a region"""
    region: str
    status: RegionStatus
    last_check: datetime = Field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    latency_ms: Optional[float] = None
    services: Dict[str, ServiceStatus] = {}
    database_status: Dict[str, bool] = {}
    error_message: Optional[str] = None
    
    @property
    def is_healthy(self) -> bool:
        return self.status in [RegionStatus.ACTIVE, RegionStatus.STANDBY]
    
    @property
    def health_percentage(self) -> float:
        if not self.services:
            return 0.0
        healthy_count = sum(1 for s in self.services.values() if s == ServiceStatus.HEALTHY)
        return (healthy_count / len(self.services)) * 100


class ServiceHealth(BaseModel):
    """Health status of a service"""
    service_name: str
    region: str
    status: ServiceStatus
    response_time_ms: Optional[float] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)
    error_count: int = 0
    metadata: Dict[str, Any] = {}


class FailoverEvent(BaseModel):
    """Failover event record"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: FailoverType
    state: FailoverState
    from_region: str
    to_region: str
    reason: str
    triggered_by: Optional[str] = None  # User ID or "system"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    services_affected: List[str] = []
    data_loss_assessment: Optional[Dict[str, Any]] = None
    rollback_available: bool = True
    metadata: Dict[str, Any] = {}


class FailoverPlan(BaseModel):
    """Failover execution plan"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    source_region: str
    target_region: str
    services: List[str]
    pre_checks: List[str] = []
    steps: List[Dict[str, Any]] = []
    post_checks: List[str] = []
    rollback_steps: List[Dict[str, Any]] = []
    estimated_downtime_minutes: int
    requires_approval: bool = False
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class RegionConfiguration(BaseModel):
    """Region configuration"""
    region: str
    is_primary: bool = False
    endpoints: Dict[str, str] = {}
    capacity: Dict[str, Any] = {}
    features_enabled: List[str] = []
    replication_targets: List[str] = []
    failover_priority: int = 0
    auto_failover_enabled: bool = True
    maintenance_windows: List[Dict[str, Any]] = []


class FailoverMetrics(BaseModel):
    """Failover metrics and statistics"""
    total_failovers: int = 0
    successful_failovers: int = 0
    failed_failovers: int = 0
    average_failover_time_seconds: float = 0.0
    last_failover: Optional[datetime] = None
    mttr_minutes: float = 0.0  # Mean Time To Recovery
    availability_percentage: float = 99.9
    data_loss_incidents: int = 0
    by_region: Dict[str, Dict[str, Any]] = {}
    by_type: Dict[str, int] = {}


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration"""
    algorithm: LoadBalancerAlgorithm
    regions: List[str]
    weights: Optional[Dict[str, float]] = None
    health_check_interval: int = 30
    sticky_sessions: bool = False
    session_duration_seconds: int = 3600
    
    @validator("weights")
    def validate_weights(cls, v, values):
        if v and values.get("algorithm") == LoadBalancerAlgorithm.WEIGHTED:
            total = sum(v.values())
            if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                raise ValueError("Weights must sum to 1.0")
        return v


class HealthCheckConfig(BaseModel):
    """Health check configuration"""
    enabled: bool = True
    interval_seconds: int = 30
    timeout_seconds: int = 10
    retries: int = 3
    success_threshold: int = 2
    failure_threshold: int = 3
    check_types: List[str] = ["http", "tcp", "database"]


class FailoverRequest(BaseModel):
    """Manual failover request"""
    target_region: str
    reason: str
    services: Optional[List[str]] = None  # None means all services
    force: bool = False
    skip_health_check: bool = False
    maintenance_mode: bool = False
    expected_duration_minutes: Optional[int] = None


class FailoverStatus(BaseModel):
    """Current failover status"""
    current_state: FailoverState
    primary_region: str
    active_region: str
    standby_regions: List[str]
    region_health: Dict[str, RegionHealth]
    active_failover: Optional[FailoverEvent] = None
    pending_failbacks: List[FailoverEvent] = []
    last_state_change: datetime = Field(default_factory=datetime.utcnow)
    automated_actions_enabled: bool = True


class DataConsistencyCheck(BaseModel):
    """Data consistency check result"""
    check_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    regions_compared: List[str]
    check_type: str  # "full", "incremental", "sample"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    inconsistencies_found: int = 0
    records_checked: int = 0
    services_checked: Dict[str, bool] = {}
    details: List[Dict[str, Any]] = []
    
    @property
    def consistency_percentage(self) -> float:
        if self.records_checked == 0:
            return 100.0
        return ((self.records_checked - self.inconsistencies_found) / self.records_checked) * 100


class NotificationConfig(BaseModel):
    """Notification configuration"""
    enabled: bool = True
    channels: List[str] = ["email", "slack", "webhook"]
    recipients: Dict[str, List[str]] = {}
    severity_levels: List[str] = ["critical", "warning", "info"]
    rate_limit_per_hour: int = 10
    group_similar_events: bool = True


class RecoveryPointStatus(BaseModel):
    """Recovery point objective status"""
    region: str
    rpo_target_minutes: int
    current_lag_minutes: float
    is_within_rpo: bool
    last_sync_time: datetime
    estimated_data_loss_mb: float = 0.0
    services_status: Dict[str, Dict[str, Any]] = {}


class SystemTopology(BaseModel):
    """System topology information"""
    regions: List[RegionConfiguration]
    active_connections: Dict[str, List[str]] = {}
    replication_flows: List[Dict[str, Any]] = []
    load_distribution: Dict[str, float] = {}
    network_latency: Dict[str, Dict[str, float]] = {}  # Region to region latency
    last_updated: datetime = Field(default_factory=datetime.utcnow)