"""Pydantic schemas for Zero Trust Service."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import ipaddress


class TrustLevel(str, Enum):
    """Trust levels for zero-trust evaluation."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    """Risk levels for security assessment."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustDecision(str, Enum):
    """Trust-based access decisions."""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    STEP_UP_AUTH = "step_up_auth"
    MONITOR = "monitor"


class DeviceType(str, Enum):
    """Device types for classification."""
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    MOBILE = "mobile"
    TABLET = "tablet"
    SERVER = "server"
    IOT = "iot"
    UNKNOWN = "unknown"


class AuthenticationMethod(str, Enum):
    """Authentication methods."""
    PASSWORD = "password"
    TOTP = "totp"
    SMS = "sms"
    PUSH = "push"
    BIOMETRIC = "biometric"
    HARDWARE_KEY = "hardware_key"
    CERTIFICATE = "certificate"


# Core Data Models

class DeviceInfo(BaseModel):
    """Device information for trust evaluation."""
    device_id: str
    device_type: DeviceType
    device_name: Optional[str] = None
    operating_system: Optional[str] = None
    browser: Optional[str] = None
    user_agent: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    is_managed: bool = False
    compliance_status: Optional[str] = None
    last_seen: Optional[datetime] = None
    fingerprint: Optional[str] = None
    metadata: Dict[str, Any] = {}


class GeographicInfo(BaseModel):
    """Geographic information."""
    country_code: str
    country_name: str
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_anonymous_proxy: bool = False
    is_satellite_provider: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


class NetworkInfo(BaseModel):
    """Network context information."""
    network_type: str
    isp: Optional[str] = None
    organization: Optional[str] = None
    asn: Optional[int] = None
    threat_level: str = "unknown"
    is_tor: bool = False
    is_vpn: bool = False
    reputation_score: float = Field(default=0.5, ge=0.0, le=1.0)


class SessionContext(BaseModel):
    """Session context for trust evaluation."""
    user_id: str
    session_id: str
    device_info: Optional[DeviceInfo] = None
    source_ip: str
    user_agent: Optional[str] = None
    timestamp: datetime
    resource: str
    action: str
    geographic_info: Optional[Dict[str, Any]] = None
    network_info: Optional[Dict[str, Any]] = None
    session_history: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    
    @validator('source_ip')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')


class TrustFactor(BaseModel):
    """Individual trust factor assessment."""
    factor_name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    details: Dict[str, Any] = {}
    last_updated: datetime


class BehaviorPattern(BaseModel):
    """User behavior pattern data."""
    user_id: str
    pattern_type: str
    typical_hours: List[int] = []
    typical_locations: List[str] = []
    typical_devices: List[str] = []
    typical_resources: List[str] = []
    access_frequency: Dict[str, int] = {}
    last_updated: datetime
    confidence: float = Field(ge=0.0, le=1.0)


class RiskFactor(BaseModel):
    """Individual risk factor assessment."""
    factor_name: str
    risk_score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    description: str
    evidence: List[str] = []
    mitigation: Optional[str] = None
    detected_at: datetime


# Request Models

class TrustRequest(BaseModel):
    """Trust evaluation request."""
    user_id: str
    session_id: str
    resource: str
    action: str
    source_ip: str
    device_info: Optional[DeviceInfo] = None
    user_agent: Optional[str] = None
    additional_context: Dict[str, Any] = {}
    requested_trust_level: Optional[TrustLevel] = None
    
    @validator('source_ip')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')


class DeviceRegistrationRequest(BaseModel):
    """Device registration request."""
    user_id: str
    device_info: DeviceInfo
    registration_method: str
    verification_code: Optional[str] = None
    attestation_data: Optional[Dict[str, Any]] = None


class SessionVerificationRequest(BaseModel):
    """Session verification request."""
    session_id: str
    verification_method: AuthenticationMethod
    verification_data: Dict[str, Any]
    challenge_response: Optional[str] = None


class PolicyEvaluationRequest(BaseModel):
    """Policy evaluation request."""
    user_id: str
    resource: str
    action: str
    context: Dict[str, Any]
    policies: Optional[List[str]] = None  # Specific policies to evaluate


class RiskAssessmentRequest(BaseModel):
    """Risk assessment request."""
    user_id: str
    session_context: SessionContext
    assessment_type: str = "comprehensive"
    factors_to_assess: List[str] = []


# Response Models

class TrustResult(BaseModel):
    """Trust evaluation result."""
    user_id: str
    session_id: str
    trust_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    decision: TrustDecision
    trust_level: TrustLevel
    risk_level: RiskLevel
    factors: Dict[str, Any] = {}
    recommendations: List[str] = []
    required_actions: List[str] = []
    expires_at: datetime
    metadata: Dict[str, Any] = {}


class AccessDecision(BaseModel):
    """Access control decision."""
    decision: TrustDecision
    reason: str
    trust_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    required_actions: List[str] = []
    alternative_actions: List[str] = []
    valid_until: Optional[datetime] = None


class DeviceTrustResult(BaseModel):
    """Device trust evaluation result."""
    device_id: str
    trust_score: float = Field(ge=0.0, le=1.0)
    trust_level: TrustLevel
    factors: Dict[str, Any] = {}
    recommendations: List[str] = []
    is_registered: bool
    is_compliant: bool
    last_verified: Optional[datetime] = None


class BehaviorAnalysisResult(BaseModel):
    """Behavior analysis result."""
    user_id: str
    trust_score: float = Field(ge=0.0, le=1.0)
    anomalies: List[Dict[str, Any]] = []
    factors: Dict[str, Any] = {}
    baseline_deviation: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class RiskAssessmentResult(BaseModel):
    """Risk assessment result."""
    user_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    risk_factors: Dict[str, Any] = {}
    threat_indicators: List[str] = []
    mitigation_recommendations: List[str] = []
    assessment_timestamp: datetime


class PolicyEvaluationResult(BaseModel):
    """Policy evaluation result."""
    policies_evaluated: List[str]
    violations: List[Dict[str, Any]] = []
    permissions: List[str] = []
    restrictions: List[str] = []
    recommendations: List[str] = []
    evaluation_timestamp: datetime


class ThreatIntelligenceResult(BaseModel):
    """Threat intelligence result."""
    indicators: List[Dict[str, Any]] = []
    threat_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = []
    last_updated: datetime


# Configuration Models

class TrustPolicy(BaseModel):
    """Trust policy configuration."""
    policy_id: str
    name: str
    description: str
    enabled: bool = True
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    priority: int = 0
    metadata: Dict[str, Any] = {}


class ZeroTrustConfig(BaseModel):
    """Zero trust configuration."""
    trust_threshold: float = Field(ge=0.0, le=1.0)
    risk_threshold: float = Field(ge=0.0, le=1.0)
    verification_interval: int  # seconds
    mfa_requirements: Dict[str, Any] = {}
    geo_restrictions: Dict[str, Any] = {}
    time_restrictions: Dict[str, Any] = {}
    device_policies: Dict[str, Any] = {}
    network_policies: Dict[str, Any] = {}


# Statistics and Monitoring Models

class TrustStatistics(BaseModel):
    """Trust engine statistics."""
    total_evaluations: int
    successful_authentications: int
    failed_authentications: int
    challenges_issued: int
    anomalies_detected: int
    average_trust_score: float = Field(ge=0.0, le=1.0)
    average_risk_score: float = Field(ge=0.0, le=1.0)
    active_sessions: int
    registered_devices: int
    policy_violations: int
    last_updated: datetime


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    user_id: str
    device_id: Optional[str] = None
    source_ip: str
    trust_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    status: str
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class AuditEvent(BaseModel):
    """Audit event for compliance tracking."""
    event_id: str
    user_id: str
    session_id: Optional[str] = None
    event_type: str
    resource: str
    action: str
    result: str
    trust_score: Optional[float] = None
    risk_score: Optional[float] = None
    source_ip: str
    device_id: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = {}


# Error Models

class ZeroTrustError(BaseModel):
    """Zero trust error response."""
    error_code: str
    message: str
    details: Dict[str, Any] = {}
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "INSUFFICIENT_TRUST",
                "message": "Trust level too low for requested access",
                "details": {
                    "current_trust": 0.6,
                    "required_trust": 0.8,
                    "recommendations": ["Complete MFA verification"]
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }