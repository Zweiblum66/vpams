"""Pydantic schemas for GDPR Compliance Service"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator, constr
from datetime import datetime
from enum import Enum
from uuid import UUID


# Enums matching database models
class ConsentType(str, Enum):
    """Types of consent"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    ESSENTIAL = "essential"
    PERFORMANCE = "performance"
    FUNCTIONAL = "functional"
    THIRD_PARTY = "third_party"


class DataRequestType(str, Enum):
    """Types of GDPR data requests"""
    ACCESS = "access"
    PORTABILITY = "portability"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class DataRequestStatus(str, Enum):
    """Status of GDPR data requests"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PrivacyLevel(str, Enum):
    """Privacy levels for data classification"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class ExportFormat(str, Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    PDF = "pdf"
    EXCEL = "excel"


class PolicySeverity(str, Enum):
    """Severity levels for policy violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyStatus(str, Enum):
    """Status of policy definitions"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class EvaluationResult(str, Enum):
    """Results of policy evaluation"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


# Consent Management Schemas
class ConsentBase(BaseModel):
    """Base consent schema"""
    consent_type: ConsentType
    consent_given: bool
    policy_version: str
    consent_text: Optional[str] = None


class ConsentCreate(ConsentBase):
    """Create consent schema"""
    user_id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentUpdate(BaseModel):
    """Update consent schema"""
    consent_given: bool
    withdrawal_reason: Optional[str] = None


class ConsentResponse(ConsentBase):
    """Consent response schema"""
    id: UUID
    user_id: UUID
    consent_date: datetime
    withdrawn: bool
    withdrawal_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserConsentsResponse(BaseModel):
    """All consents for a user"""
    user_id: UUID
    consents: List[ConsentResponse]
    all_required_consents_given: bool
    last_updated: datetime


# Data Request Schemas
class DataRequestBase(BaseModel):
    """Base data request schema"""
    request_type: DataRequestType
    request_reason: Optional[str] = None
    notification_email: EmailStr


class DataRequestCreate(DataRequestBase):
    """Create data request schema"""
    user_id: UUID
    requested_by: str
    export_format: Optional[ExportFormat] = ExportFormat.JSON
    request_data: Optional[Dict[str, Any]] = None


class DataRequestVerify(BaseModel):
    """Verify data request schema"""
    request_id: str
    verification_token: str


class DataRequestCancel(BaseModel):
    """Cancel data request schema"""
    cancellation_reason: Optional[str] = None


class DataRequestResponse(DataRequestBase):
    """Data request response schema"""
    id: UUID
    request_id: str
    user_id: UUID
    status: DataRequestStatus
    requested_at: datetime
    requested_by: str
    processed_at: Optional[datetime] = None
    export_format: Optional[str] = None
    export_size_bytes: Optional[int] = None
    verification_required: bool
    verified: bool
    error_message: Optional[str] = None
    
    @validator("export_size_bytes")
    def format_size(cls, v):
        if v is None:
            return None
        return v  # Can add formatting logic here if needed


class DataRequestProgress(BaseModel):
    """Data request progress schema"""
    request_id: str
    status: DataRequestStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: str
    estimated_completion: Optional[datetime] = None


# Data Export Schemas
class DataExportRequest(BaseModel):
    """Request data export"""
    user_id: UUID
    format: ExportFormat = ExportFormat.JSON
    categories: Optional[List[str]] = None  # Specific categories to export
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_metadata: bool = True
    anonymize_data: bool = False


class DataExportResponse(BaseModel):
    """Data export response"""
    request_id: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    size_bytes: int
    format: ExportFormat
    categories_included: List[str]
    record_count: int


# Data Deletion Schemas
class DataDeletionRequest(BaseModel):
    """Request data deletion"""
    user_id: UUID
    deletion_reason: str
    categories: Optional[List[str]] = None  # Specific categories to delete
    immediate: bool = False  # Skip grace period


class DataDeletionResponse(BaseModel):
    """Data deletion response"""
    request_id: str
    scheduled_deletion_date: datetime
    categories_to_delete: List[str]
    grace_period_days: int
    can_be_cancelled_until: datetime


# Privacy Policy Schemas
class PrivacyPolicyBase(BaseModel):
    """Base privacy policy schema"""
    version: str
    title: str
    content: str
    summary: Optional[str] = None
    language: str = "en"
    effective_date: datetime
    change_summary: Optional[str] = None
    requires_re_consent: bool = False


class PrivacyPolicyCreate(PrivacyPolicyBase):
    """Create privacy policy schema"""
    created_by: str


class PrivacyPolicyResponse(PrivacyPolicyBase):
    """Privacy policy response schema"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PrivacyPolicyAcceptance(BaseModel):
    """Accept privacy policy schema"""
    policy_version: str
    accepted: bool
    user_id: UUID
    ip_address: Optional[str] = None


# Data Category Schemas
class DataCategoryBase(BaseModel):
    """Base data category schema"""
    category_name: str
    description: Optional[str] = None
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    is_sensitive: bool = False
    requires_explicit_consent: bool = False
    legal_basis: Optional[str] = None
    purpose: Optional[str] = None


class DataCategoryCreate(DataCategoryBase):
    """Create data category schema"""
    retention_days: Optional[int] = None
    can_be_anonymized: bool = True
    shared_with_third_parties: bool = False
    third_party_details: Optional[Dict[str, Any]] = None


class DataCategoryResponse(DataCategoryBase):
    """Data category response schema"""
    id: UUID
    retention_days: Optional[int] = None
    can_be_anonymized: bool
    shared_with_third_parties: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Data Mapping Schemas
class DataMappingBase(BaseModel):
    """Base data mapping schema"""
    table_name: str
    column_name: str
    category_id: UUID
    field_description: Optional[str] = None
    contains_pii: bool = True
    encryption_required: bool = False


class DataMappingCreate(DataMappingBase):
    """Create data mapping schema"""
    anonymization_method: Optional[str] = None
    anonymization_params: Optional[Dict[str, Any]] = None
    include_in_export: bool = True
    export_transform: Optional[str] = None


class DataMappingResponse(DataMappingBase):
    """Data mapping response schema"""
    id: UUID
    anonymization_method: Optional[str] = None
    include_in_export: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[DataCategoryResponse] = None


# Audit Log Schemas
class AuditLogEntry(BaseModel):
    """Audit log entry schema"""
    event_type: str
    action: str
    actor_id: Optional[UUID] = None
    actor_type: str
    subject_user_id: Optional[UUID] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogResponse(AuditLogEntry):
    """Audit log response schema"""
    id: UUID
    event_timestamp: datetime
    actor_ip: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None


class AuditLogQuery(BaseModel):
    """Query audit logs"""
    event_type: Optional[str] = None
    actor_id: Optional[UUID] = None
    subject_user_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Anonymization Schemas
class AnonymizationRequest(BaseModel):
    """Request data anonymization"""
    user_id: UUID
    reason: str
    partial: bool = False
    categories: Optional[List[str]] = None


class AnonymizationResponse(BaseModel):
    """Anonymization response schema"""
    id: UUID
    user_id: UUID
    anonymized_at: datetime
    tables_affected: Dict[str, int]
    total_records: int
    anonymization_method: str
    partial_anonymization: bool
    verified: bool


# Compliance Report Schemas
class ComplianceReport(BaseModel):
    """GDPR compliance report"""
    generated_at: datetime
    reporting_period_start: datetime
    reporting_period_end: datetime
    
    # Consent metrics
    total_users_with_consent: int
    consent_by_type: Dict[ConsentType, int]
    consent_withdrawal_count: int
    
    # Request metrics
    total_data_requests: int
    requests_by_type: Dict[DataRequestType, int]
    average_request_completion_time_hours: float
    requests_completed_on_time: int
    requests_overdue: int
    
    # Data metrics
    total_data_categories: int
    sensitive_data_categories: int
    data_retention_compliance_percentage: float
    
    # Audit metrics
    total_audit_events: int
    failed_operations: int
    
    # Risk assessment
    high_risk_operations: List[Dict[str, Any]]
    compliance_score: float = Field(ge=0, le=100)


class ComplianceMetrics(BaseModel):
    """Real-time compliance metrics"""
    last_updated: datetime
    active_data_requests: int
    pending_deletions: int
    users_without_consent: int
    data_categories_without_mapping: int
    overdue_retention_rules: int
    compliance_health: str  # healthy, warning, critical


# Data Retention Schemas
class DataRetentionRuleBase(BaseModel):
    """Base data retention rule schema"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    table_name: Optional[str] = Field(None, max_length=100)
    data_category_id: Optional[UUID] = None
    condition_sql: Optional[str] = None
    retention_days: int = Field(..., ge=1, le=36500)  # Max 100 years
    deletion_method: str = Field(..., regex="^(hard_delete|soft_delete|anonymize)$")
    run_frequency_days: int = Field(1, ge=1, le=365)
    is_active: bool = True


class DataRetentionRuleCreate(DataRetentionRuleBase):
    """Create data retention rule schema"""
    pass


class DataRetentionRuleUpdate(BaseModel):
    """Update data retention rule schema"""
    description: Optional[str] = None
    condition_sql: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1, le=36500)
    deletion_method: Optional[str] = Field(None, regex="^(hard_delete|soft_delete|anonymize)$")
    run_frequency_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None


class DataRetentionRuleResponse(DataRetentionRuleBase):
    """Data retention rule response schema"""
    id: UUID
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_run_deleted_count: Optional[int] = None
    total_deleted_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class RetentionExecutionResult(BaseModel):
    """Result of retention rule execution"""
    rule_id: UUID
    rule_name: str
    execution_time: datetime
    affected_records: int
    deleted_records: int
    anonymized_records: int
    errors: List[str] = []
    dry_run: bool
    success: bool


class RetentionStatistics(BaseModel):
    """Retention policy statistics"""
    total_rules: int
    active_rules: int
    inactive_rules: int
    total_records_processed: int
    overdue_rules: int
    recent_executions: List[Dict[str, Any]] = []


# Health Check Schema
class HealthCheck(BaseModel):
    """Service health check"""
    status: str
    version: str
    database_connected: bool
    mongodb_connected: bool
    redis_connected: bool
    export_storage_available: bool
    email_service_available: bool
    compliance_score: float
    warnings: List[str] = []


# Audit Reporting Schemas
class AuditReportType(str, Enum):
    """Types of audit reports"""
    COMPLIANCE_OVERVIEW = "compliance_overview"
    USER_ACTIVITY = "user_activity"
    DATA_REQUESTS = "data_requests"
    CONSENT_ANALYSIS = "consent_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    INCIDENT_LOG = "incident_log"


class AuditReportFormat(str, Enum):
    """Audit report output formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"


class AuditReportRequest(BaseModel):
    """Request for audit report generation"""
    report_type: AuditReportType
    start_date: datetime
    end_date: datetime
    format: AuditReportFormat = AuditReportFormat.JSON
    filters: Optional[Dict[str, Any]] = None
    include_recommendations: bool = True
    include_trends: bool = False
    email_to: Optional[List[EmailStr]] = None


class AuditReportResponse(BaseModel):
    """Audit report response"""
    report_id: str
    report_type: AuditReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    format: AuditReportFormat
    data: Optional[Dict[str, Any]] = None  # For JSON format
    file_content: Optional[bytes] = None  # For other formats
    file_name: Optional[str] = None
    download_url: Optional[str] = None


class ComplianceScoreCard(BaseModel):
    """Detailed compliance scorecard"""
    overall_score: float = Field(ge=0, le=100)
    category_scores: Dict[str, float]
    grade: str  # A+, A, B+, B, C, D, F
    trend: str  # improving, stable, declining
    last_updated: datetime
    key_findings: List[str] = []
    areas_of_improvement: List[str] = []


class RiskAssessment(BaseModel):
    """Risk assessment details"""
    risk_id: str
    category: str
    severity: str  # critical, high, medium, low
    description: str
    impact: str
    likelihood: str  # certain, likely, possible, unlikely, rare
    mitigation: str
    detected_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class EventFrequency(BaseModel):
    """Event frequency analysis"""
    event_type: str
    count: int
    percentage: float
    trend: str  # increasing, stable, decreasing
    peak_time: Optional[datetime] = None
    average_per_day: float


class ComplianceTrend(BaseModel):
    """Compliance trend over time"""
    period: str  # YYYY-MM
    compliance_score: float
    total_events: int
    failed_events: int
    high_risk_incidents: int
    data_requests_completed: int
    consent_withdrawals: int


class AuditReportSchedule(BaseModel):
    """Scheduled audit report configuration"""
    schedule_id: UUID
    report_type: AuditReportType
    frequency: str  # daily, weekly, monthly, quarterly
    format: AuditReportFormat
    recipients: List[EmailStr]
    filters: Optional[Dict[str, Any]] = None
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


# Data Classification Schemas
class SensitivityLevel(str, Enum):
    """Data sensitivity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataCategoryUpdate(BaseModel):
    """Update data category schema"""
    description: Optional[str] = None
    privacy_level: Optional[PrivacyLevel] = None
    retention_days: Optional[int] = None
    is_sensitive: Optional[bool] = None
    requires_explicit_consent: Optional[bool] = None
    can_be_anonymized: Optional[bool] = None
    legal_basis: Optional[str] = None
    purpose: Optional[str] = None
    shared_with_third_parties: Optional[bool] = None
    third_party_details: Optional[Dict[str, Any]] = None


class DataMappingUpdate(BaseModel):
    """Update data mapping schema"""
    category_id: Optional[UUID] = None
    field_description: Optional[str] = None
    contains_pii: Optional[bool] = None
    encryption_required: Optional[bool] = None
    anonymization_method: Optional[str] = None
    anonymization_params: Optional[Dict[str, Any]] = None
    include_in_export: Optional[bool] = None
    export_transform: Optional[str] = None


class DataClassificationReport(BaseModel):
    """Data classification report"""
    generated_at: datetime
    total_categories: int
    categories_by_privacy_level: Dict[str, int]
    sensitive_data_categories: List[Dict[str, Any]]
    third_party_sharing: List[Dict[str, Any]]
    retention_summary: Dict[str, List[str]]
    unmapped_tables: Set[str]
    compliance_gaps: List[Dict[str, Any]]
    recommendations: List[str] = []


class DataInventory(BaseModel):
    """Complete data inventory"""
    generated_at: datetime
    total_tables: int
    total_columns: int
    pii_columns: int
    encrypted_columns: int
    tables: Dict[str, Dict[str, Any]]
    data_flows: List["DataFlow"] = []
    compliance_status: Optional["ComplianceStatus"] = None


class DataFlow(BaseModel):
    """Data flow information"""
    category: str
    source_tables: List[str]
    destination_tables: Optional[List[str]] = None
    data_type: str
    description: str
    third_party_involved: bool = False
    requires_consent: bool = False


class ComplianceStatus(BaseModel):
    """Overall compliance status"""
    compliant: bool
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    issues: List[Dict[str, Any]] = []


class ClassificationSuggestion(BaseModel):
    """Automatic classification suggestion"""
    table_name: str
    column_name: str
    suggested_category: str
    confidence: float = Field(ge=0, le=1)
    reasoning: List[str]
    contains_pii: bool
    needs_encryption: bool
    suggested_anonymization: str


class DataDiscoveryRequest(BaseModel):
    """Request for data discovery scan"""
    scan_tables: Optional[List[str]] = None  # None = scan all
    auto_classify: bool = True
    suggest_only: bool = False  # If True, only suggest, don't apply
    confidence_threshold: float = Field(0.8, ge=0, le=1)


class DataDiscoveryResult(BaseModel):
    """Result of data discovery scan"""
    scan_id: str
    started_at: datetime
    completed_at: datetime
    tables_scanned: int
    columns_discovered: int
    new_pii_found: int
    suggestions: List[ClassificationSuggestion]
    auto_classified: int
    errors: List[str] = []


# Update forward references
DataInventory.model_rebuild()
DataFlow.model_rebuild()


# Dashboard Schemas

class ComplianceMetric(BaseModel):
    """Individual compliance metric"""
    name: str
    value: float
    unit: str = "count"  # count, percentage, days, etc.
    change_percentage: float = 0  # Change from previous period
    is_critical: bool = False


class ComplianceTrend(BaseModel):
    """Compliance trend data point"""
    date: datetime
    compliance_score: float
    consent_count: int
    request_count: int
    incident_count: int


class RiskIndicator(BaseModel):
    """Risk indicator for compliance"""
    risk_type: str
    severity: str = Field(..., regex="^(low|medium|high)$")
    description: str
    mitigation: str
    affected_items: int = 0
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ComplianceScore(BaseModel):
    """Overall compliance score"""
    score: float = Field(..., ge=0, le=100)
    grade: str = Field(..., regex="^[A-F][+-]?$")
    components: Dict[str, float] = {}
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class TimeSeriesData(BaseModel):
    """Time series data for charts"""
    labels: List[str]
    datasets: List[Dict[str, Any]]


class PieChartData(BaseModel):
    """Pie chart data"""
    labels: List[str]
    values: List[float]
    title: str


class BarChartData(BaseModel):
    """Bar chart data"""
    labels: List[str]
    values: List[float]
    title: str


class DashboardWidget(BaseModel):
    """Dashboard widget configuration"""
    widget_type: str  # gauge, pie_chart, bar_chart, line_chart, stats, heatmap, etc.
    title: str
    data: Dict[str, Any]
    config: Dict[str, Any] = {}
    position: Optional[Dict[str, int]] = None  # x, y, width, height


class ComplianceDashboard(BaseModel):
    """Main compliance dashboard"""
    compliance_score: ComplianceScore
    key_metrics: List[ComplianceMetric]
    trends: List[ComplianceTrend]
    risk_indicators: List[RiskIndicator]
    widgets: List[DashboardWidget]
    last_updated: datetime
    time_range_days: int = 30


class DataClassificationSummary(BaseModel):
    """Data classification summary for dashboard"""
    total_categories: int
    total_mappings: int
    sensitive_data_count: int
    encrypted_fields_count: int
    privacy_level_distribution: PieChartData
    retention_distribution: BarChartData
    pii_distribution: PieChartData
    unmapped_tables: List[str]
    compliance_gaps_count: int


class ConsentMetrics(BaseModel):
    """Consent management metrics"""
    total_active_consents: int
    consents_given: int
    consents_withdrawn: int
    withdrawal_rate: float
    consent_by_type: PieChartData
    consent_trends: TimeSeriesData
    average_consent_duration_days: int


class DataRequestMetrics(BaseModel):
    """Data request handling metrics"""
    total_requests: int
    requests_by_type: BarChartData
    requests_by_status: PieChartData
    average_completion_time_days: float
    compliance_rate: float  # Percentage completed within 30 days
    pending_requests: int
    overdue_requests: int
    request_trends: TimeSeriesData


class RetentionMetrics(BaseModel):
    """Data retention policy metrics"""
    total_retention_rules: int
    active_retention_rules: int
    rules_by_action_type: PieChartData
    data_scheduled_for_deletion: int
    average_retention_period_days: float
    overdue_executions: int
    retention_by_category: BarChartData
    last_execution_date: Optional[datetime]


class AuditMetrics(BaseModel):
    """Audit logging metrics"""
    total_audit_events: int
    events_by_category: PieChartData
    success_rate: float
    failure_rate: float
    top_users_by_activity: BarChartData
    critical_events_count: int
    audit_trends: TimeSeriesData
    storage_usage_mb: float


# Dashboard Request/Response schemas

class DashboardRequest(BaseModel):
    """Request for dashboard data"""
    time_range_days: int = Field(30, ge=1, le=365)
    include_widgets: List[str] = []
    include_trends: bool = True
    include_risks: bool = True


class DashboardExportRequest(BaseModel):
    """Request to export dashboard data"""
    format: ExportFormat = ExportFormat.PDF
    time_range_days: int = Field(30, ge=1, le=365)
    include_charts: bool = True
    include_raw_data: bool = False


class DashboardExportResponse(BaseModel):
    """Response for dashboard export"""
    export_id: str
    file_path: str
    format: ExportFormat
    size_bytes: int
    created_at: datetime
    expires_at: datetime


# Policy Engine Schemas

class RuleOperator(str, Enum):
    """Operators for rule conditions"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX_MATCH = "regex_match"
    IN = "in"
    NOT_IN = "not_in"


class RuleDataType(str, Enum):
    """Data types for rule evaluation"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"
    OBJECT = "object"


class PolicyCondition(BaseModel):
    """Condition for policy rules"""
    field: str = Field(..., description="Field path to evaluate (e.g., 'user.role')")
    operator: RuleOperator
    value: Any = Field(..., description="Value to compare against")
    data_type: RuleDataType = RuleDataType.STRING
    
    # Compound conditions
    and_conditions: Optional[List['PolicyCondition']] = None
    or_conditions: Optional[List['PolicyCondition']] = None
    
    class Config:
        schema_extra = {
            "example": {
                "field": "user.role",
                "operator": "equals",
                "value": "admin",
                "data_type": "string"
            }
        }


class PolicyAction(BaseModel):
    """Action to take when a rule is violated"""
    type: str = Field(..., description="Action type (notification, block, remediate, log, webhook)")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "type": "notification",
                "parameters": {
                    "recipients": ["admin@example.com"],
                    "message": "Policy violation detected"
                }
            }
        }


class PolicyRuleBase(BaseModel):
    """Base schema for policy rules"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    condition: PolicyCondition
    action: Optional[PolicyAction] = None
    order_index: int = Field(0, ge=0)
    is_active: bool = True


class PolicyRuleCreate(PolicyRuleBase):
    """Schema for creating a policy rule"""
    pass


class PolicyRuleUpdate(BaseModel):
    """Schema for updating a policy rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    condition: Optional[PolicyCondition] = None
    action: Optional[PolicyAction] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class PolicyRuleResponse(PolicyRuleBase):
    """Response schema for policy rules"""
    id: UUID
    policy_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    
    class Config:
        orm_mode = True


class PolicyDefinitionBase(BaseModel):
    """Base schema for policy definitions"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    severity: PolicySeverity = PolicySeverity.MEDIUM
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class PolicyDefinitionCreate(PolicyDefinitionBase):
    """Schema for creating a policy"""
    rules: List[PolicyRuleCreate] = Field(..., min_items=1)


class PolicyDefinitionUpdate(BaseModel):
    """Schema for updating a policy"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    severity: Optional[PolicySeverity] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class PolicyDefinitionResponse(PolicyDefinitionBase):
    """Response schema for policy definitions"""
    id: UUID
    status: PolicyStatus
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    updated_by: Optional[str]
    rules: List[PolicyRuleResponse] = []
    
    class Config:
        orm_mode = True


class PolicyEvaluationCreate(BaseModel):
    """Schema for creating a policy evaluation"""
    policy_id: UUID
    entity_type: str
    entity_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation"""
    policy_id: UUID
    policy_name: Optional[str] = None
    result: EvaluationResult
    passed_rules: List[UUID] = []
    failed_rules: List[UUID] = []
    violations: List['PolicyViolationResponse'] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyViolationBase(BaseModel):
    """Base schema for policy violations"""
    entity_type: str
    entity_id: Optional[str] = None
    severity: PolicySeverity
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyViolationUpdate(BaseModel):
    """Schema for updating violation status"""
    status: Optional[str] = Field(None, regex="^(open|acknowledged|resolved|dismissed)$")
    resolution_notes: Optional[str] = None


class PolicyViolationResponse(PolicyViolationBase):
    """Response schema for policy violations"""
    id: UUID
    policy_id: UUID
    rule_id: Optional[UUID]
    status: str
    created_at: datetime
    detected_by: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    resolution_notes: Optional[str]
    
    class Config:
        orm_mode = True


class PolicyAssignmentCreate(BaseModel):
    """Schema for assigning a policy"""
    policy_id: UUID
    entity_type: str
    entity_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PolicyAssignmentResponse(BaseModel):
    """Response schema for policy assignments"""
    id: UUID
    policy_id: UUID
    entity_type: str
    entity_id: str
    parameters: Dict[str, Any]
    priority: int
    assigned_at: datetime
    assigned_by: str
    
    class Config:
        orm_mode = True


class PolicyTemplateBase(BaseModel):
    """Base schema for policy templates"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str
    template_data: Dict[str, Any]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class PolicyTemplateCreate(PolicyTemplateBase):
    """Schema for creating a policy template"""
    pass


class PolicyTemplateResponse(PolicyTemplateBase):
    """Response schema for policy templates"""
    id: UUID
    version: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    
    class Config:
        orm_mode = True


class PolicyScheduleCreate(BaseModel):
    """Schema for creating a policy schedule"""
    policy_id: UUID
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    timezone: str = Field("UTC", description="Timezone for schedule")
    is_active: bool = True
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyScheduleResponse(BaseModel):
    """Response schema for policy schedules"""
    id: UUID
    policy_id: UUID
    entity_type: Optional[str]
    entity_id: Optional[str]
    cron_expression: str
    timezone: str
    is_active: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    execution_count: int
    context: Dict[str, Any]
    created_at: datetime
    created_by: str
    
    class Config:
        orm_mode = True


class PolicyMetrics(BaseModel):
    """Policy engine metrics"""
    total_policies: int
    active_policies: int
    evaluations: Dict[str, Any]
    violations: Dict[str, Any]
    period: Dict[str, datetime]


# Update forward references
PolicyCondition.model_rebuild()
PolicyEvaluationResult.model_rebuild()


# Access Review Schemas

class ReviewStatus(str, Enum):
    """Status of access reviews"""
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class ReviewDecision(str, Enum):
    """Access review decisions"""
    APPROVED = "approved"
    REVOKED = "revoked"
    MODIFIED = "modified"
    PENDING = "pending"
    ESCALATED = "escalated"


class ReviewScheduleFrequency(str, Enum):
    """Frequency for scheduled reviews"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class AccessReviewBase(BaseModel):
    """Base schema for access reviews"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    review_type: str = Field(..., min_length=1, max_length=100)
    target_type: str = Field(..., min_length=1, max_length=100)
    target_criteria: Dict[str, Any] = Field(default_factory=dict)
    scope: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field("medium", regex="^(low|medium|high|critical)$")
    assigned_to: Optional[str] = None
    auto_approve_threshold: Optional[float] = Field(None, ge=0, le=1)
    require_justification: bool = True
    allow_bulk_decisions: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccessReviewCreate(AccessReviewBase):
    """Schema for creating access reviews"""
    review_start_date: Optional[datetime] = None
    review_end_date: Optional[datetime] = None
    review_period_days: int = Field(30, ge=1, le=365)


class AccessReviewUpdate(BaseModel):
    """Schema for updating access reviews"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, regex="^(low|medium|high|critical)$")
    status: Optional[ReviewStatus] = None
    assigned_to: Optional[str] = None
    review_start_date: Optional[datetime] = None
    review_end_date: Optional[datetime] = None
    auto_approve_threshold: Optional[float] = Field(None, ge=0, le=1)
    require_justification: Optional[bool] = None
    allow_bulk_decisions: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class AccessReviewResponse(AccessReviewBase):
    """Response schema for access reviews"""
    id: UUID
    status: ReviewStatus
    review_start_date: Optional[datetime]
    review_end_date: Optional[datetime]
    completed_at: Optional[datetime]
    total_items: int = 0
    reviewed_items: int = 0
    progress_percentage: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class AccessReviewItemBase(BaseModel):
    """Base schema for access review items"""
    subject_type: str = Field(..., min_length=1, max_length=100)
    subject_id: str = Field(..., min_length=1, max_length=255)
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: str = Field(..., min_length=1, max_length=255)
    permission_type: Optional[str] = Field(None, max_length=100)
    current_access_level: Optional[str] = Field(None, max_length=100)
    access_granted_date: Optional[datetime] = None
    last_used_date: Optional[datetime] = None
    business_justification: Optional[str] = None
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccessReviewItemCreate(AccessReviewItemBase):
    """Schema for creating access review items"""
    pass


class AccessReviewItemUpdate(BaseModel):
    """Schema for updating access review items"""
    permission_type: Optional[str] = Field(None, max_length=100)
    current_access_level: Optional[str] = Field(None, max_length=100)
    business_justification: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(pending|approved|revoked|modified)$")
    metadata: Optional[Dict[str, Any]] = None


class AccessReviewItemResponse(AccessReviewItemBase):
    """Response schema for access review items"""
    id: UUID
    review_id: UUID
    status: str
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class AccessReviewDecisionBase(BaseModel):
    """Base schema for access review decisions"""
    decision: ReviewDecision
    justification: Optional[str] = None
    recommended_action: Optional[str] = Field(None, max_length=100)
    new_access_level: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    comments: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccessReviewDecisionCreate(AccessReviewDecisionBase):
    """Schema for creating access review decisions"""
    pass


class AccessReviewDecisionResponse(AccessReviewDecisionBase):
    """Response schema for access review decisions"""
    id: UUID
    item_id: UUID
    reviewer_id: str
    review_date: datetime

    class Config:
        orm_mode = True


class AccessReviewScheduleBase(BaseModel):
    """Base schema for access review schedules"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    review_type: str = Field(..., min_length=1, max_length=100)
    frequency: ReviewScheduleFrequency
    cron_expression: Optional[str] = Field(None, max_length=100)
    target_criteria: Dict[str, Any] = Field(default_factory=dict)
    auto_start: bool = True
    review_duration_days: int = Field(30, ge=1, le=365)
    template_id: Optional[UUID] = None
    notification_settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AccessReviewScheduleCreate(AccessReviewScheduleBase):
    """Schema for creating access review schedules"""
    next_run_date: Optional[datetime] = None


class AccessReviewScheduleResponse(AccessReviewScheduleBase):
    """Response schema for access review schedules"""
    id: UUID
    last_run_date: Optional[datetime]
    next_run_date: Optional[datetime]
    execution_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class AccessReviewTemplateBase(BaseModel):
    """Base schema for access review templates"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    review_type: str = Field(..., min_length=1, max_length=100)
    default_settings: Dict[str, Any] = Field(default_factory=dict)
    question_template: Dict[str, Any] = Field(default_factory=dict)
    approval_workflow: Dict[str, Any] = Field(default_factory=dict)
    notification_template: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    tags: List[str] = Field(default_factory=list)


class AccessReviewTemplateCreate(AccessReviewTemplateBase):
    """Schema for creating access review templates"""
    pass


class AccessReviewTemplateResponse(AccessReviewTemplateBase):
    """Response schema for access review templates"""
    id: UUID
    version: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class AccessReviewCampaignBase(BaseModel):
    """Base schema for access review campaigns"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    review_type: str = Field(..., min_length=1, max_length=100)
    target_criteria: Dict[str, Any] = Field(default_factory=dict)
    start_date: datetime
    end_date: datetime
    auto_generate_reviews: bool = True
    notification_settings: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[UUID] = None


class AccessReviewCampaignCreate(AccessReviewCampaignBase):
    """Schema for creating access review campaigns"""
    pass


class AccessReviewCampaignResponse(AccessReviewCampaignBase):
    """Response schema for access review campaigns"""
    id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class AccessReviewMetrics(BaseModel):
    """Access review metrics schema"""
    total_reviews: int
    active_reviews: int
    completed_reviews: int
    overdue_reviews: int
    average_completion_days: float
    decisions_by_type: Dict[str, int]
    period_start: datetime
    period_end: datetime


class BulkReviewRequest(BaseModel):
    """Schema for bulk review operations"""
    item_ids: List[str] = Field(..., min_items=1)
    justification: str = Field(..., min_length=1)


class BulkReviewResponse(BaseModel):
    """Response schema for bulk operations"""
    processed_items: int
    successful_items: int
    failed_items: int
    decisions: List[AccessReviewDecisionResponse]
    errors: List[str] = Field(default_factory=list)


# Data Lineage Schemas

class NodeType(str, Enum):
    """Types of data lineage nodes"""
    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    VIEW = "view"
    COLUMN = "column"
    FILE = "file"
    API = "api"
    SERVICE = "service"
    REPORT = "report"
    DASHBOARD = "dashboard"


class TransformationType(str, Enum):
    """Types of data transformations"""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    UNION = "union"
    SPLIT = "split"
    MERGE = "merge"
    VALIDATE = "validate"
    CLEANSE = "cleanse"
    ENRICH = "enrich"


class LineageDirection(str, Enum):
    """Direction for lineage traversal"""
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"


class DataLineageNodeBase(BaseModel):
    """Base schema for data lineage nodes"""
    node_type: NodeType
    identifier: str = Field(..., min_length=1, max_length=500)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_name: Optional[str] = Field(None, max_length=100)
    table_name: Optional[str] = Field(None, max_length=100)
    column_name: Optional[str] = Field(None, max_length=100)
    data_type: Optional[str] = Field(None, max_length=100)
    is_sensitive: bool = False
    classification_level: Optional[str] = Field(None, max_length=50)
    business_context: Dict[str, Any] = Field(default_factory=dict)
    technical_metadata: Dict[str, Any] = Field(default_factory=dict)
    compliance_tags: List[str] = Field(default_factory=list)


class DataLineageNodeCreate(DataLineageNodeBase):
    """Schema for creating data lineage nodes"""
    pass


class DataLineageNodeUpdate(BaseModel):
    """Schema for updating data lineage nodes"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    data_type: Optional[str] = Field(None, max_length=100)
    is_sensitive: Optional[bool] = None
    classification_level: Optional[str] = Field(None, max_length=50)
    business_context: Optional[Dict[str, Any]] = None
    technical_metadata: Optional[Dict[str, Any]] = None
    compliance_tags: Optional[List[str]] = None


class DataLineageNodeResponse(DataLineageNodeBase):
    """Response schema for data lineage nodes"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class DataLineageEdgeBase(BaseModel):
    """Base schema for data lineage edges"""
    source_node_id: str
    target_node_id: str
    relationship_type: str = Field(..., min_length=1, max_length=100)
    transformation_logic: Optional[str] = None
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataLineageEdgeCreate(DataLineageEdgeBase):
    """Schema for creating data lineage edges"""
    pass


class DataLineageEdgeResponse(DataLineageEdgeBase):
    """Response schema for data lineage edges"""
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class DataTransformationBase(BaseModel):
    """Base schema for data transformations"""
    transformation_type: TransformationType
    source_nodes: List[str] = Field(default_factory=list)
    target_nodes: List[str] = Field(default_factory=list)
    transformation_logic: Optional[str] = None
    transformation_code: Optional[str] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    data_quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    success: bool = True


class DataTransformationCreate(DataTransformationBase):
    """Schema for creating data transformations"""
    pass


class DataTransformationResponse(DataTransformationBase):
    """Response schema for data transformations"""
    id: UUID
    session_id: Optional[UUID]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        orm_mode = True


class DataFlowSessionBase(BaseModel):
    """Base schema for data flow sessions"""
    session_name: str = Field(..., min_length=1, max_length=255)
    session_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workflow_id: Optional[str] = Field(None, max_length=255)
    pipeline_id: Optional[str] = Field(None, max_length=255)
    expected_end_time: Optional[datetime] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    environment: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)


class DataFlowSessionCreate(DataFlowSessionBase):
    """Schema for creating data flow sessions"""
    start_time: Optional[datetime] = None


class DataFlowSessionResponse(DataFlowSessionBase):
    """Response schema for data flow sessions"""
    id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    success: Optional[bool]
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    created_by: str

    class Config:
        orm_mode = True


class DataLineageGraphResponse(BaseModel):
    """Response schema for data lineage graphs"""
    root_node: DataLineageNodeResponse
    nodes: List[DataLineageNodeResponse]
    edges: List[DataLineageEdgeResponse]
    transformations: List[DataTransformationResponse] = Field(default_factory=list)
    direction: LineageDirection
    max_depth: int
    statistics: Dict[str, Any] = Field(default_factory=dict)


class DataLineageMetricsResponse(BaseModel):
    """Response schema for data lineage metrics"""
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    sensitive_nodes: int
    total_transformations: int
    active_sessions: int
    period_start: datetime
    period_end: datetime


class DataImpactAnalysisRequest(BaseModel):
    """Request schema for data impact analysis"""
    node_ids: List[str] = Field(..., min_items=1)
    change_type: str = Field(..., min_length=1, max_length=100)
    change_description: Optional[str] = None
    analysis_scope: str = Field("downstream", regex="^(upstream|downstream|both)$")
    max_depth: int = Field(5, ge=1, le=10)
    include_sensitive_data: bool = True


class DataImpactAnalysisResponse(BaseModel):
    """Response schema for data impact analysis"""
    id: UUID
    node_ids: List[str]
    change_type: str
    change_description: Optional[str]
    analysis_scope: str
    max_depth: int
    include_sensitive_data: bool
    impacted_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    impacted_transformations: List[Dict[str, Any]] = Field(default_factory=list)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    analysis_duration_ms: Optional[int]
    analysis_quality_score: Optional[float]
    requested_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        orm_mode = True


class DataLineageSnapshotRequest(BaseModel):
    """Request schema for creating lineage snapshots"""
    snapshot_name: str = Field(..., min_length=1, max_length=255)
    snapshot_type: str = Field("full", regex="^(full|incremental|schema_only)$")
    description: Optional[str] = None
    node_filter: Optional[Dict[str, Any]] = None
    include_metadata: bool = True


class DataLineageSnapshotResponse(BaseModel):
    """Response schema for lineage snapshots"""
    id: UUID
    snapshot_name: str
    snapshot_type: str
    description: Optional[str]
    total_nodes: int
    total_edges: int
    sensitive_nodes: int
    snapshot_timestamp: datetime
    created_at: datetime
    created_by: str

    class Config:
        orm_mode = True


class LineageSearchRequest(BaseModel):
    """Request schema for searching lineage"""
    query: str = Field(..., min_length=1)
    node_types: Optional[List[NodeType]] = None
    schema_names: Optional[List[str]] = None
    is_sensitive: Optional[bool] = None
    classification_levels: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class LineageSearchResponse(BaseModel):
    """Response schema for lineage search"""
    query: str
    total_results: int
    nodes: List[DataLineageNodeResponse]
    search_metadata: Dict[str, Any] = Field(default_factory=dict)


# Risk Assessment Schemas

class RiskSeverity(str, Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, Enum):
    """Risk assessment status"""
    IDENTIFIED = "identified"
    ANALYZING = "analyzing"
    ASSESSED = "assessed"
    MITIGATING = "mitigating"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class RiskCategory(str, Enum):
    """Risk categories"""
    DATA_BREACH = "data_breach"
    PRIVACY_VIOLATION = "privacy_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    REPUTATIONAL = "reputational"


class RiskFactorCreate(BaseModel):
    """Create risk factor schema"""
    factor_name: str = Field(..., min_length=1, max_length=255)
    factor_description: Optional[str] = None
    factor_type: Optional[str] = Field(None, max_length=100)
    likelihood_contribution: float = Field(0.0, ge=0.0, le=1.0)
    impact_contribution: float = Field(0.0, ge=0.0, le=1.0)
    weight: float = Field(1.0, ge=0.0, le=5.0)
    evidence: Optional[str] = None
    data_sources: List[str] = Field(default_factory=list)
    confidence_level: float = Field(0.5, ge=0.0, le=1.0)


class RiskFactorUpdate(BaseModel):
    """Update risk factor schema"""
    factor_name: Optional[str] = Field(None, min_length=1, max_length=255)
    factor_description: Optional[str] = None
    factor_type: Optional[str] = Field(None, max_length=100)
    likelihood_contribution: Optional[float] = Field(None, ge=0.0, le=1.0)
    impact_contribution: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight: Optional[float] = Field(None, ge=0.0, le=5.0)
    evidence: Optional[str] = None
    data_sources: Optional[List[str]] = None
    confidence_level: Optional[float] = Field(None, ge=0.0, le=1.0)


class RiskFactorResponse(BaseModel):
    """Response schema for risk factors"""
    id: UUID
    risk_assessment_id: UUID
    factor_name: str
    factor_description: Optional[str]
    factor_type: Optional[str]
    likelihood_contribution: float
    impact_contribution: float
    weight: float
    evidence: Optional[str]
    data_sources: List[str]
    confidence_level: float
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class RiskMitigationPlanCreate(BaseModel):
    """Create risk mitigation plan schema"""
    plan_name: str = Field(..., min_length=1, max_length=255)
    plan_description: Optional[str] = None
    mitigation_type: Optional[str] = Field(None, max_length=100)
    implementation_steps: List[str] = Field(default_factory=list)
    responsible_party: Optional[str] = Field(None, max_length=255)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    expected_risk_reduction: Optional[float] = Field(None, ge=0.0)
    cost: Optional[float] = Field(None, ge=0.0)
    effort_hours: Optional[float] = Field(None, ge=0.0)
    success_criteria: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    required_resources: List[str] = Field(default_factory=list)


class RiskMitigationPlanUpdate(BaseModel):
    """Update risk mitigation plan schema"""
    plan_name: Optional[str] = Field(None, min_length=1, max_length=255)
    plan_description: Optional[str] = None
    mitigation_type: Optional[str] = Field(None, max_length=100)
    implementation_steps: Optional[List[str]] = None
    responsible_party: Optional[str] = Field(None, max_length=255)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    expected_risk_reduction: Optional[float] = Field(None, ge=0.0)
    actual_risk_reduction: Optional[float] = Field(None, ge=0.0)
    cost: Optional[float] = Field(None, ge=0.0)
    effort_hours: Optional[float] = Field(None, ge=0.0)
    status: Optional[str] = Field(None, max_length=100)
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    success_criteria: Optional[str] = None
    dependencies: Optional[List[str]] = None
    required_resources: Optional[List[str]] = None


class RiskMitigationPlanResponse(BaseModel):
    """Response schema for risk mitigation plans"""
    id: UUID
    risk_assessment_id: UUID
    plan_name: str
    plan_description: Optional[str]
    mitigation_type: Optional[str]
    implementation_steps: List[str]
    responsible_party: Optional[str]
    start_date: Optional[datetime]
    target_completion_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    expected_risk_reduction: Optional[float]
    actual_risk_reduction: Optional[float]
    cost: Optional[float]
    effort_hours: Optional[float]
    status: str
    progress_percentage: float
    success_criteria: Optional[str]
    dependencies: List[str]
    required_resources: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class RiskAssessmentCreate(BaseModel):
    """Create risk assessment schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    risk_category: RiskCategory
    risk_source: Optional[str] = Field(None, max_length=255)
    affected_assets: List[str] = Field(default_factory=list)
    affected_data_types: List[str] = Field(default_factory=list)
    potential_impact: Optional[str] = None
    likelihood_score: int = Field(..., ge=1, le=5)
    impact_score: int = Field(..., ge=1, le=5)
    risk_owner: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional[str] = Field(None, max_length=255)
    mitigation_strategy: Optional[str] = None
    mitigation_actions: List[str] = Field(default_factory=list)
    mitigation_deadline: Optional[datetime] = None
    mitigation_cost_estimate: Optional[float] = Field(None, ge=0.0)
    review_frequency_days: int = Field(90, ge=1, le=365)
    regulatory_requirements: List[str] = Field(default_factory=list)
    compliance_controls: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    # Sub-entities
    risk_factors: List[RiskFactorCreate] = Field(default_factory=list)
    mitigation_plans: List[RiskMitigationPlanCreate] = Field(default_factory=list)

    @validator('likelihood_score', 'impact_score')
    def validate_scores(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Scores must be between 1 and 5')
        return v


class RiskAssessmentUpdate(BaseModel):
    """Update risk assessment schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    risk_category: Optional[RiskCategory] = None
    risk_source: Optional[str] = Field(None, max_length=255)
    affected_assets: Optional[List[str]] = None
    affected_data_types: Optional[List[str]] = None
    potential_impact: Optional[str] = None
    likelihood_score: Optional[int] = Field(None, ge=1, le=5)
    impact_score: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[RiskStatus] = None
    risk_owner: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional[str] = Field(None, max_length=255)
    mitigation_strategy: Optional[str] = None
    mitigation_actions: Optional[List[str]] = None
    mitigation_deadline: Optional[datetime] = None
    mitigation_cost_estimate: Optional[float] = Field(None, ge=0.0)
    last_reviewed_at: Optional[datetime] = None
    review_frequency_days: Optional[int] = Field(None, ge=1, le=365)
    regulatory_requirements: Optional[List[str]] = None
    compliance_controls: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    comments: Optional[List[str]] = None


class RiskAssessmentResponse(BaseModel):
    """Response schema for risk assessments"""
    id: UUID
    title: str
    description: Optional[str]
    risk_category: RiskCategory
    risk_source: Optional[str]
    affected_assets: List[str]
    affected_data_types: List[str]
    potential_impact: Optional[str]
    likelihood_score: int
    impact_score: int
    risk_score: float
    severity: RiskSeverity
    status: RiskStatus
    risk_owner: Optional[str]
    assigned_to: Optional[str]
    mitigation_strategy: Optional[str]
    mitigation_actions: List[str]
    mitigation_deadline: Optional[datetime]
    mitigation_cost_estimate: Optional[float]
    last_reviewed_at: Optional[datetime]
    next_review_due: Optional[datetime]
    review_frequency_days: int
    regulatory_requirements: List[str]
    compliance_controls: List[str]
    tags: List[str]
    attachments: List[str]
    comments: List[str]
    identified_at: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    updated_by: Optional[str]
    # Sub-entities
    risk_factors: List[RiskFactorResponse] = Field(default_factory=list)
    mitigation_plans: List[RiskMitigationPlanResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True


class RiskIncidentCreate(BaseModel):
    """Create risk incident schema"""
    incident_title: str = Field(..., min_length=1, max_length=255)
    incident_description: Optional[str] = None
    incident_type: Optional[str] = Field(None, max_length=100)
    related_risk_assessment_id: Optional[UUID] = None
    was_risk_predicted: bool = False
    actual_impact_description: Optional[str] = None
    financial_impact: Optional[float] = Field(None, ge=0.0)
    affected_records_count: Optional[int] = Field(None, ge=0)
    affected_individuals_count: Optional[int] = Field(None, ge=0)
    downtime_hours: Optional[float] = Field(None, ge=0.0)
    incident_detected_at: Optional[datetime] = None
    incident_occurred_at: Optional[datetime] = None
    response_team: List[str] = Field(default_factory=list)
    response_actions: List[str] = Field(default_factory=list)
    regulatory_notification_required: bool = False
    severity: Optional[RiskSeverity] = None


class RiskIncidentUpdate(BaseModel):
    """Update risk incident schema"""
    incident_title: Optional[str] = Field(None, min_length=1, max_length=255)
    incident_description: Optional[str] = None
    incident_type: Optional[str] = Field(None, max_length=100)
    related_risk_assessment_id: Optional[UUID] = None
    was_risk_predicted: Optional[bool] = None
    actual_impact_description: Optional[str] = None
    financial_impact: Optional[float] = Field(None, ge=0.0)
    affected_records_count: Optional[int] = Field(None, ge=0)
    affected_individuals_count: Optional[int] = Field(None, ge=0)
    downtime_hours: Optional[float] = Field(None, ge=0.0)
    incident_detected_at: Optional[datetime] = None
    incident_occurred_at: Optional[datetime] = None
    incident_resolved_at: Optional[datetime] = None
    response_team: Optional[List[str]] = None
    response_actions: Optional[List[str]] = None
    lessons_learned: Optional[str] = None
    regulatory_notification_required: Optional[bool] = None
    regulatory_notifications_sent: Optional[List[str]] = None
    status: Optional[str] = Field(None, max_length=100)
    severity: Optional[RiskSeverity] = None


class RiskIncidentResponse(BaseModel):
    """Response schema for risk incidents"""
    id: UUID
    incident_title: str
    incident_description: Optional[str]
    incident_type: Optional[str]
    related_risk_assessment_id: Optional[UUID]
    was_risk_predicted: bool
    actual_impact_description: Optional[str]
    financial_impact: Optional[float]
    affected_records_count: Optional[int]
    affected_individuals_count: Optional[int]
    downtime_hours: Optional[float]
    incident_detected_at: Optional[datetime]
    incident_occurred_at: Optional[datetime]
    incident_resolved_at: Optional[datetime]
    response_team: List[str]
    response_actions: List[str]
    lessons_learned: Optional[str]
    regulatory_notification_required: bool
    regulatory_notifications_sent: List[str]
    status: str
    severity: Optional[RiskSeverity]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str

    class Config:
        orm_mode = True


class RiskMetricsResponse(BaseModel):
    """Response schema for risk metrics"""
    total_assessments: int
    assessments_by_category: Dict[str, int]
    assessments_by_severity: Dict[str, int]
    assessments_by_status: Dict[str, int]
    average_risk_score: float
    high_risk_count: int
    critical_risk_count: int
    overdue_reviews: int
    active_incidents: int
    mitigation_plans_completed: int
    mitigation_plans_overdue: int
    period_start: Optional[datetime]
    period_end: Optional[datetime]


class RiskDashboardResponse(BaseModel):
    """Response schema for risk dashboard"""
    risk_score_distribution: Dict[str, int]
    category_breakdown: Dict[str, int]
    severity_trends: Dict[str, List[Dict[str, Any]]]
    top_risks: List[RiskAssessmentResponse]
    recent_incidents: List[RiskIncidentResponse]
    mitigation_progress: Dict[str, Any]
    compliance_gaps: List[Dict[str, Any]]
    metrics: RiskMetricsResponse