"""Pydantic schemas for Intrusion Detection Service."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import ipaddress


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Types of security events."""
    SIGNATURE_MATCH = "signature_match"
    ANOMALY = "anomaly"
    THREAT_INTELLIGENCE = "threat_intelligence"
    HOST_BASED = "host_based"
    NETWORK_INTRUSION = "network_intrusion"
    CORRELATED_ATTACK = "correlated_attack"
    POLICY_VIOLATION = "policy_violation"


class EventStatus(str, Enum):
    """Security event status."""
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Protocol(str, Enum):
    """Network protocols."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    HTTP = "http"
    HTTPS = "https"
    DNS = "dns"
    SSH = "ssh"
    FTP = "ftp"
    SMTP = "smtp"


# Request/Response Models

class NetworkPacket(BaseModel):
    """Network packet data model."""
    id: str
    timestamp: datetime
    source_ip: str
    dest_ip: str
    source_port: Optional[int] = None
    dest_port: Optional[int] = None
    protocol: Protocol
    payload_size: int
    flags: Optional[List[str]] = []
    payload_hash: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    @validator('source_ip', 'dest_ip')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')


class SecurityEvent(BaseModel):
    """Security event data model."""
    id: str
    timestamp: datetime
    event_type: EventType
    threat_level: ThreatLevel
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    source_port: Optional[int] = None
    target_port: Optional[int] = None
    protocol: Optional[Protocol] = None
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    signatures_matched: List[str] = []
    anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}
    status: EventStatus = EventStatus.ACTIVE
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AnomalyResult(BaseModel):
    """Anomaly detection result."""
    is_anomaly: bool
    score: float = Field(ge=0.0, le=1.0)
    anomaly_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    features_analyzed: List[str] = []
    threshold_used: float
    metadata: Dict[str, Any] = {}


class SignatureMatch(BaseModel):
    """Signature detection match."""
    signature_id: str
    name: str
    description: str
    severity: ThreatLevel
    confidence: float = Field(ge=0.0, le=1.0)
    rule_content: str
    matched_content: str
    offset: Optional[int] = None
    metadata: Dict[str, Any] = {}


class ThreatIntelMatch(BaseModel):
    """Threat intelligence match."""
    source: str
    indicator_type: str  # ip, domain, hash, etc.
    indicator_value: str
    threat_level: ThreatLevel
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class HostEvent(BaseModel):
    """Host-based security event."""
    id: str
    timestamp: datetime
    hostname: str
    event_type: str  # file_change, process_start, login_attempt, etc.
    severity: ThreatLevel
    description: str
    file_path: Optional[str] = None
    process_name: Optional[str] = None
    user: Optional[str] = None
    command_line: Optional[str] = None
    metadata: Dict[str, Any] = {}


# API Request Models

class EventQuery(BaseModel):
    """Query parameters for security events."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    threat_level: Optional[ThreatLevel] = None
    event_type: Optional[EventType] = None
    source_ip: Optional[str] = None
    status: Optional[EventStatus] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="timestamp")
    order_direction: str = Field(default="desc", regex="^(asc|desc)$")


class PacketAnalysisRequest(BaseModel):
    """Request for packet analysis."""
    packet_data: str  # Base64 encoded packet data
    interface: Optional[str] = None
    analyze_payload: bool = True
    check_signatures: bool = True
    check_anomalies: bool = True
    check_threat_intel: bool = True


class NetworkScanRequest(BaseModel):
    """Request for network scan."""
    target_network: str  # CIDR notation
    scan_type: str = Field(default="ping", regex="^(ping|port|full)$")
    timeout: int = Field(default=30, ge=1, le=300)
    max_concurrent: int = Field(default=10, ge=1, le=100)


class AlertConfigUpdate(BaseModel):
    """Alert configuration update."""
    enabled: bool
    webhook_url: Optional[str] = None
    email_recipients: List[str] = []
    severity_threshold: ThreatLevel = ThreatLevel.MEDIUM
    rate_limit_minutes: int = Field(default=5, ge=1, le=60)
    include_metadata: bool = True


class RuleUpdate(BaseModel):
    """Detection rule update."""
    rule_id: str
    enabled: bool
    content: Optional[str] = None
    severity: Optional[ThreatLevel] = None
    description: Optional[str] = None
    tags: List[str] = []


# Response Models

class EventResponse(BaseModel):
    """Security event response."""
    event: SecurityEvent
    related_events: List[str] = []
    threat_intel_context: List[ThreatIntelMatch] = []
    recommended_actions: List[str] = []


class EventListResponse(BaseModel):
    """List of security events response."""
    events: List[SecurityEvent]
    total_count: int
    page_info: Dict[str, Any]


class AnalysisResponse(BaseModel):
    """Packet/network analysis response."""
    analysis_id: str
    timestamp: datetime
    results: List[SecurityEvent]
    summary: Dict[str, Any]
    processing_time_ms: float


class StatisticsResponse(BaseModel):
    """IDS statistics response."""
    events_processed_24h: int
    threats_detected_24h: int
    top_threat_sources: List[Dict[str, Any]]
    threat_level_distribution: Dict[ThreatLevel, int]
    detection_accuracy: float
    false_positive_rate: float
    system_performance: Dict[str, Any]
    last_updated: datetime


class SystemStatusResponse(BaseModel):
    """System status response."""
    status: str
    uptime_seconds: int
    components_status: Dict[str, Any]
    resource_usage: Dict[str, Any]
    active_monitors: int
    queue_sizes: Dict[str, int]


class ConfigurationResponse(BaseModel):
    """IDS configuration response."""
    detection_enabled: bool
    monitoring_interfaces: List[str]
    signature_files: List[str]
    threat_intel_sources: List[str]
    alert_configuration: Dict[str, Any]
    performance_settings: Dict[str, Any]


# Error Models

class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {
                        "field": "source_ip",
                        "issue": "Invalid IP address format"
                    }
                }
            }
        }