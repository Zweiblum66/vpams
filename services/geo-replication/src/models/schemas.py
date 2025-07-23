"""
Pydantic models for geo-replication service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class ReplicationMode(str, Enum):
    ASYNC = "async"
    SYNC = "sync"
    SEMI_SYNC = "semi_sync"


class ReplicationType(str, Enum):
    DATABASE = "database"
    FILES = "files"
    CACHE = "cache"
    SEARCH = "search"
    METADATA = "metadata"
    FULL = "full"


class ConflictResolutionStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    PRIMARY_WINS = "primary_wins"
    MANUAL = "manual"
    VERSION_VECTOR = "version_vector"


class RegionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"
    MAINTENANCE = "maintenance"


class RegionInfo(BaseModel):
    """Information about a specific region"""
    region_id: str
    is_primary: bool = False
    endpoint_urls: Dict[str, str]
    status: RegionStatus = RegionStatus.ACTIVE
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    available_storage_gb: Optional[float] = None
    
    class Config:
        use_enum_values = True


class ReplicationConfig(BaseModel):
    """Configuration for geo-replication"""
    enabled: bool = True
    primary_region: str
    secondary_regions: List[str] = []
    replication_mode: ReplicationMode = ReplicationMode.ASYNC
    conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    batch_size: int = Field(default=1000, ge=1, le=10000)
    max_lag_seconds: int = Field(default=300, ge=0)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=60)
    
    @validator("secondary_regions")
    def validate_secondary_regions(cls, v, values):
        if "primary_region" in values and values["primary_region"] in v:
            raise ValueError("Primary region cannot be in secondary regions")
        return v


class ReplicationJob(BaseModel):
    """Represents a replication job"""
    job_id: str
    source_region: str
    target_region: str
    replication_type: ReplicationType
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_processed: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    class Config:
        use_enum_values = True


class ReplicationMetrics(BaseModel):
    """Metrics for replication monitoring"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    region_id: str
    replication_type: ReplicationType
    items_pending: int = 0
    items_processed: int = 0
    items_failed: int = 0
    bytes_transferred: int = 0
    lag_seconds: float = 0.0
    error_rate: float = 0.0
    throughput_mbps: float = 0.0
    
    class Config:
        use_enum_values = True


class ReplicationStatus(BaseModel):
    """Overall replication status"""
    enabled: bool
    primary_region: str
    active_regions: List[str] = []
    inactive_regions: List[str] = []
    replication_lag_seconds: float = 0.0
    last_sync_time: Optional[datetime] = None
    pending_jobs: int = 0
    failed_jobs: int = 0
    health_status: str = "healthy"


class ReplicationEvent(BaseModel):
    """Event for replication tracking"""
    event_id: str
    event_type: str
    source_region: str
    target_regions: List[str] = []
    resource_type: str
    resource_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = {}
    version: int = 1


class ConflictResolution(BaseModel):
    """Conflict resolution record"""
    conflict_id: str
    conflict_type: str
    source_region: str
    target_region: str
    resource_type: str
    resource_id: str
    source_data: Dict[str, Any]
    target_data: Dict[str, Any]
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_method: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_data: Optional[Dict[str, Any]] = None


class RegionFailover(BaseModel):
    """Region failover configuration"""
    region_id: str
    failover_priority: int = Field(ge=1, le=100)
    automatic_failover: bool = True
    health_check_interval_seconds: int = Field(default=30, ge=10, le=300)
    unhealthy_threshold: int = Field(default=3, ge=1, le=10)
    healthy_threshold: int = Field(default=2, ge=1, le=10)


class DataSyncRequest(BaseModel):
    """Request for manual data synchronization"""
    source_region: str
    target_regions: List[str]
    sync_type: ReplicationType = ReplicationType.FULL
    resource_filters: Optional[Dict[str, Any]] = None
    force: bool = False
    validate_before_sync: bool = True


class DataSyncResponse(BaseModel):
    """Response for data synchronization request"""
    sync_id: str
    status: str = "initiated"
    source_region: str
    target_regions: List[str]
    sync_type: ReplicationType
    started_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion_time: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class ReplicationTopology(BaseModel):
    """Replication topology configuration"""
    topology_type: str = "hub_spoke"  # hub_spoke, mesh, chain
    primary_region: str
    regions: List[RegionInfo]
    replication_paths: List[Dict[str, str]]  # source -> target mappings
    bandwidth_limits: Optional[Dict[str, int]] = None  # MB/s limits per path


class CrossRegionLatency(BaseModel):
    """Cross-region latency measurements"""
    source_region: str
    target_region: str
    latency_ms: float
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    packet_loss_percentage: float = 0.0
    bandwidth_mbps: Optional[float] = None


class ReplicationAlert(BaseModel):
    """Alert for replication issues"""
    alert_id: str
    alert_type: str  # lag_exceeded, failure_rate_high, region_down
    severity: str  # critical, warning, info
    region_id: str
    message: str
    details: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class VersionVector(BaseModel):
    """Version vector for conflict resolution"""
    vectors: Dict[str, int] = {}  # region_id -> version
    
    def increment(self, region_id: str):
        """Increment version for a region"""
        self.vectors[region_id] = self.vectors.get(region_id, 0) + 1
    
    def merge(self, other: "VersionVector"):
        """Merge with another version vector"""
        for region_id, version in other.vectors.items():
            self.vectors[region_id] = max(
                self.vectors.get(region_id, 0),
                version
            )
    
    def compare(self, other: "VersionVector") -> str:
        """Compare with another version vector"""
        self_newer = False
        other_newer = False
        
        for region_id, version in self.vectors.items():
            other_version = other.vectors.get(region_id, 0)
            if version > other_version:
                self_newer = True
            elif version < other_version:
                other_newer = True
        
        for region_id, version in other.vectors.items():
            if region_id not in self.vectors and version > 0:
                other_newer = True
        
        if self_newer and not other_newer:
            return "newer"
        elif other_newer and not self_newer:
            return "older"
        elif self_newer and other_newer:
            return "concurrent"
        else:
            return "equal"