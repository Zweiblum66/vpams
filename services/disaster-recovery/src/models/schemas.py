"""
Pydantic schemas for Disaster Recovery Service API
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class DisasterType(str, Enum):
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_FAILURE = "software_failure"
    NETWORK_OUTAGE = "network_outage"
    DATA_CORRUPTION = "data_corruption"
    CYBER_ATTACK = "cyber_attack"
    NATURAL_DISASTER = "natural_disaster"
    POWER_OUTAGE = "power_outage"
    HUMAN_ERROR = "human_error"
    PROVIDER_OUTAGE = "provider_outage"
    COMPLETE_DATACENTER_LOSS = "complete_datacenter_loss"


class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"
    CONTINUOUS = "continuous"


class FailoverMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"


class RecoveryTier(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Backup Strategy Schemas
class BackupStrategyBase(BaseModel):
    service_name: str = Field(..., description="Name of the service to backup")
    backup_type: BackupType = Field(..., description="Type of backup")
    frequency: str = Field(..., description="Cron expression for backup schedule")
    retention_days: int = Field(..., ge=1, description="Days to retain backups")
    storage_locations: List[str] = Field(..., description="Storage locations for backups")
    encryption_enabled: bool = Field(True, description="Enable encryption")
    compression_enabled: bool = Field(True, description="Enable compression")
    verification_enabled: bool = Field(True, description="Verify backup integrity")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BackupStrategyCreate(BackupStrategyBase):
    pass


class BackupStrategyResponse(BackupStrategyBase):
    id: str
    plan_id: str
    created_at: datetime
    is_active: bool


# Failover Procedure Schemas
class FailoverStep(BaseModel):
    name: str = Field(..., description="Step name")
    type: str = Field(..., description="Step type")
    description: str = Field(..., description="Step description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Step parameters")


class FailoverProcedureBase(BaseModel):
    service_name: str = Field(..., description="Service name")
    failover_mode: FailoverMode = Field(..., description="Failover mode")
    primary_region: str = Field(..., description="Primary region")
    failover_regions: List[str] = Field(..., description="Failover regions in priority order")
    health_check_url: str = Field(..., description="Health check endpoint")
    failover_steps: List[FailoverStep] = Field(..., description="Failover steps")
    rollback_steps: Optional[List[FailoverStep]] = Field(None, description="Rollback steps")
    validation_steps: Optional[List[FailoverStep]] = Field(None, description="Validation steps")
    notification_channels: Optional[List[str]] = Field(None, description="Notification channels")
    auto_failover_threshold: int = Field(3, ge=1, description="Failed health checks before auto-failover")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class FailoverProcedureCreate(FailoverProcedureBase):
    pass


class FailoverProcedureResponse(FailoverProcedureBase):
    id: str
    plan_id: str
    created_at: datetime
    is_active: bool


# Disaster Recovery Plan Schemas
class DisasterRecoveryPlanBase(BaseModel):
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    recovery_tiers: Dict[str, RecoveryTier] = Field(..., description="Service recovery tiers")
    contact_list: List[Dict[str, str]] = Field(..., description="Emergency contacts")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DisasterRecoveryPlanCreate(DisasterRecoveryPlanBase):
    backup_strategies: List[BackupStrategyCreate] = Field(..., description="Backup strategies")
    failover_procedures: List[FailoverProcedureCreate] = Field(..., description="Failover procedures")


class DisasterRecoveryPlanResponse(DisasterRecoveryPlanBase):
    id: str
    created_at: datetime
    is_active: bool


class DisasterRecoveryPlanDetail(DisasterRecoveryPlanResponse):
    backup_strategies: List[BackupStrategyResponse]
    failover_procedures: List[FailoverProcedureResponse]
    recovery_metrics: Optional[Dict[str, Any]]
    updated_at: datetime


# Backup Operation Schemas
class BackupExecuteRequest(BaseModel):
    plan_id: str = Field(..., description="Disaster recovery plan ID")
    service_name: str = Field(..., description="Service to backup")
    backup_type: Optional[BackupType] = Field(None, description="Override backup type")


class BackupJobResponse(BaseModel):
    id: str
    plan_id: str
    service_name: str
    backup_type: BackupType
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    storage_location: Optional[str]
    size_bytes: Optional[int]
    metadata: Optional[Dict[str, Any]]


class BackupStatusResponse(BaseModel):
    plan_id: str
    service_name: Optional[str]
    last_backup_time: Optional[datetime]
    next_backup_time: Optional[datetime]
    backup_success_rate: float
    compliance_rate: float
    recent_backups: List[Dict[str, Any]]


class BackupRestoreRequest(BaseModel):
    backup_id: str = Field(..., description="Backup ID to restore")
    target_environment: str = Field(..., description="Target environment")
    validation_required: bool = Field(True, description="Require validation after restore")


class RestoreJobResponse(BaseModel):
    id: str
    backup_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    validation_results: Optional[Dict[str, Any]]


# Failover Operation Schemas
class FailoverExecuteRequest(BaseModel):
    plan_id: str = Field(..., description="Disaster recovery plan ID")
    service_name: str = Field(..., description="Service to failover")
    disaster_type: DisasterType = Field(..., description="Type of disaster")
    target_region: Optional[str] = Field(None, description="Target failover region")


class FailoverEventResponse(BaseModel):
    id: str
    plan_id: str
    service_name: str
    disaster_type: DisasterType
    failover_mode: FailoverMode
    source_region: str
    target_region: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    steps_completed: List[str]


class RollbackResponse(BaseModel):
    failover_id: str
    status: str
    rollback_steps_completed: List[str]
    original_state_restored: bool


# Recovery Test Schemas
class RecoveryTestScenario(BaseModel):
    disaster_type: DisasterType
    affected_regions: List[str]
    data_loss_scenario: Optional[bool] = False
    service_degradation: Optional[Dict[str, float]] = None
    duration_minutes: Optional[int] = None


class RecoveryTestRequest(BaseModel):
    plan_id: str = Field(..., description="Disaster recovery plan ID")
    test_type: str = Field(..., description="Test type: tabletop, backup_restore, failover, full_simulation")
    services: List[str] = Field(..., description="Services to test")
    scenario: RecoveryTestScenario = Field(..., description="Test scenario")


class RecoveryTestResponse(BaseModel):
    id: str
    plan_id: str
    test_type: str
    services_tested: List[str]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    success_rate: Optional[float]
    issues_found: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    report_url: Optional[str]


class RecoveryTestSummary(BaseModel):
    id: str
    test_type: str
    services_tested: List[str]
    status: str
    start_time: datetime
    success_rate: Optional[float]
    issues_count: int


# Business Continuity Schemas
class CriticalFunction(BaseModel):
    name: str
    description: str
    rto_hours: int
    dependencies: List[str]
    responsible_team: str


class CommunicationPlan(BaseModel):
    internal_channels: List[str]
    external_channels: List[str]
    escalation_matrix: Dict[str, List[str]]
    update_frequency_minutes: int


class EmergencyProcedure(BaseModel):
    name: str
    trigger_conditions: List[str]
    steps: List[str]
    responsible_role: str


class BusinessContinuityPlanCreate(BaseModel):
    dr_plan_id: str = Field(..., description="Associated DR plan ID")
    critical_functions: List[CriticalFunction] = Field(..., description="Critical business functions")
    communication_plan: CommunicationPlan = Field(..., description="Communication procedures")
    emergency_procedures: List[EmergencyProcedure] = Field(..., description="Emergency procedures")
    resource_requirements: Dict[str, Any] = Field(..., description="Required resources")


class BusinessContinuityPlanResponse(BaseModel):
    id: str
    dr_plan_id: str
    critical_functions: List[CriticalFunction]
    activation_criteria: Dict[str, Any]
    created_at: datetime
    is_active: bool


# Dashboard and Monitoring Schemas
class ServiceHealthInfo(BaseModel):
    service_name: str
    status: str
    last_check_time: Optional[datetime]
    metrics: Optional[Dict[str, float]]
    issues: List[str]


class RecoveryDashboardResponse(BaseModel):
    plan_id: str
    plan_name: str
    service_health: Dict[str, str]
    backup_status: Dict[str, Any]
    recovery_metrics: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    readiness_score: float
    compliance_status: Dict[str, float]


class ServiceHealthResponse(BaseModel):
    service_name: str
    status: str
    last_check_time: Optional[datetime]
    metrics: Dict[str, Any]
    issues: List[Dict[str, Any]]


# Recovery Runbook Schemas
class RecoveryStep(BaseModel):
    order: int
    phase: str
    action: str
    responsible: str
    duration_minutes: int
    critical: bool
    service: Optional[str] = None


class RecoveryRunbookRequest(BaseModel):
    plan_id: str = Field(..., description="Disaster recovery plan ID")
    disaster_type: DisasterType = Field(..., description="Type of disaster")
    affected_services: List[str] = Field(..., description="Affected services")


class RecoveryRunbookResponse(BaseModel):
    id: str
    plan_id: str
    disaster_type: DisasterType
    affected_services: List[str]
    steps: List[RecoveryStep]
    estimated_recovery_time_hours: float
    printable_url: Optional[str]
    generated_at: datetime


class RecoveryRunbookSummary(BaseModel):
    id: str
    disaster_type: DisasterType
    affected_services: List[str]
    estimated_recovery_time_hours: float
    generated_at: datetime


# Disaster Event Schemas
class DisasterEventReport(BaseModel):
    plan_id: str = Field(..., description="Disaster recovery plan ID")
    disaster_type: DisasterType = Field(..., description="Type of disaster")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    affected_services: List[str] = Field(..., description="Affected services")
    impact_description: str = Field(..., description="Description of impact")


class DisasterEventResponse(BaseModel):
    id: str
    plan_id: str
    disaster_type: DisasterType
    severity: str
    affected_services: List[str]
    status: str
    start_time: datetime
    detection_time: datetime


class DisasterEventSummary(BaseModel):
    id: str
    disaster_type: DisasterType
    severity: str
    affected_services: List[str]
    status: str
    start_time: datetime
    time_to_detection: Optional[int]  # seconds
    time_to_response: Optional[int]  # seconds


# Recovery Metrics Schemas
class ComplianceTrend(BaseModel):
    date: datetime
    rto_compliance: float
    rpo_compliance: float
    backup_compliance: float


class RecoveryMetricsResponse(BaseModel):
    plan_id: str
    service_name: Optional[str]
    time_range_days: int
    rto_compliance: float
    rpo_compliance: float
    backup_success_rate: float
    test_success_rate: float
    mean_time_to_recovery: Optional[float]  # minutes
    service_availability: float  # percentage
    compliance_trends: List[ComplianceTrend]


# Validation
class ContactInfo(BaseModel):
    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    phone: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove common formatting characters
        cleaned = v.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        if len(cleaned) < 10:
            raise ValueError('Phone number too short')
        return v