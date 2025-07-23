"""Pydantic schemas for Multi-Tenant Service."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class TenantState(str, Enum):
    """Tenant lifecycle states."""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETING = "deleting"
    DELETED = "deleted"
    FAILED = "failed"


class IsolationMode(str, Enum):
    """Database isolation modes."""
    SCHEMA = "schema"      # Schema-based isolation (same database)
    DATABASE = "database"  # Database-based isolation
    HYBRID = "hybrid"      # Combination approach


class TenantTemplate(str, Enum):
    """Pre-defined tenant templates."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantStatus(str, Enum):
    """Tenant status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class SubscriptionPlan(str, Enum):
    """Subscription plans."""
    FREE = "free"
    STARTER = "starter"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class DomainVerificationMethod(str, Enum):
    """Domain verification methods."""
    DNS = "dns"
    FILE = "file"
    META = "meta"


# Core Models

class TenantQuota(BaseModel):
    """Tenant resource quotas."""
    max_users: int = Field(default=100, ge=-1)  # -1 for unlimited
    max_storage_gb: float = Field(default=1000.0, ge=-1)
    max_assets: int = Field(default=100000, ge=-1)
    max_projects: int = Field(default=1000, ge=-1)
    max_api_calls_per_hour: int = Field(default=10000, ge=-1)
    max_bandwidth_gb_per_month: float = Field(default=10000.0, ge=-1)
    max_compute_hours_per_month: float = Field(default=1000.0, ge=-1)
    custom_limits: Dict[str, Any] = {}


class BrandingConfig(BaseModel):
    """Tenant branding configuration."""
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str = "#1976d2"
    secondary_color: str = "#dc004e"
    font_family: str = "Roboto, sans-serif"
    custom_css: Optional[str] = None


class FeatureFlags(BaseModel):
    """Feature flags configuration."""
    ai_enabled: bool = True
    workflow_automation: bool = True
    advanced_search: bool = True
    custom_metadata: bool = True
    api_access: bool = True
    mobile_app: bool = True
    collaboration: bool = True
    version_control: bool = True
    audit_logging: bool = True
    custom_reports: bool = True


class IntegrationConfig(BaseModel):
    """Integration configuration."""
    slack_enabled: bool = False
    teams_enabled: bool = False
    ldap_enabled: bool = False
    sso_enabled: bool = False
    webhook_enabled: bool = True
    api_rate_limit: int = 1000
    allowed_domains: List[str] = []


class SecurityConfig(BaseModel):
    """Security configuration."""
    password_policy: Dict[str, Any] = {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": True
    }
    session_timeout_minutes: int = 30
    mfa_required: bool = False
    ip_whitelist: List[str] = []
    allowed_countries: List[str] = []
    max_login_attempts: int = 5


class NotificationConfig(BaseModel):
    """Notification configuration."""
    email_enabled: bool = True
    slack_enabled: bool = False
    teams_enabled: bool = False
    webhook_enabled: bool = False
    notification_preferences: Dict[str, List[str]] = {}


class WorkflowConfig(BaseModel):
    """Workflow configuration."""
    auto_tagging: bool = True
    auto_transcription: bool = True
    approval_required: bool = False
    default_workflow: str = "standard"
    custom_workflows: Dict[str, Any] = {}


class TenantConfig(BaseModel):
    """Complete tenant configuration."""
    tenant_id: str
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    workflows: WorkflowConfig = Field(default_factory=WorkflowConfig)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantConfigUpdate(BaseModel):
    """Update tenant configuration request."""
    branding: Optional[BrandingConfig] = None
    features: Optional[FeatureFlags] = None
    integrations: Optional[IntegrationConfig] = None
    security: Optional[SecurityConfig] = None
    notifications: Optional[NotificationConfig] = None
    workflows: Optional[WorkflowConfig] = None


class DomainInfo(BaseModel):
    """Custom domain information."""
    domain: str
    subdomain: Optional[str] = None
    is_verified: bool = False
    verification_token: Optional[str] = None
    ssl_enabled: bool = False
    ssl_certificate_id: Optional[str] = None
    created_at: datetime
    verified_at: Optional[datetime] = None
    dns_records: List[Dict[str, Any]] = []


class DatabaseInfo(BaseModel):
    """Tenant database information."""
    isolation_mode: IsolationMode
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    connection_string: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    created_at: datetime
    size_mb: float = 0.0
    table_count: int = 0


class StorageInfo(BaseModel):
    """Tenant storage information."""
    storage_backend: str
    bucket_name: Optional[str] = None
    prefix: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None
    created_at: datetime
    used_gb: float = 0.0
    file_count: int = 0


class TenantUsage(BaseModel):
    """Current tenant resource usage."""
    tenant_id: str
    storage_used_gb: float = 0.0
    bandwidth_used_gb: float = 0.0
    api_calls_count: int = 0
    active_users: int = 0
    asset_count: int = 0
    project_count: int = 0
    compute_hours: float = 0.0
    last_activity: Optional[datetime] = None
    timestamp: datetime


# Request Models

class TenantCreate(BaseModel):
    """Request to create a new tenant."""
    tenant_id: Optional[str] = None  # Auto-generated if not provided
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    template: Optional[TenantTemplate] = TenantTemplate.STARTER
    region: Optional[str] = None
    custom_domain: Optional[str] = None
    admin_email: str
    admin_name: str
    initial_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    
    @validator('custom_domain')
    def validate_domain(cls, v):
        if v and not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError('Invalid domain format')
        return v


class TenantUpdate(BaseModel):
    """Request to update tenant configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    quota: Optional[TenantQuota] = None
    metadata: Optional[Dict[str, Any]] = None


class DomainAdd(BaseModel):
    """Request to add a custom domain."""
    domain: str
    auto_verify: bool = True
    auto_ssl: bool = True
    
    @validator('domain')
    def validate_domain(cls, v):
        if not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError('Invalid domain format')
        return v.lower()


class DomainVerify(BaseModel):
    """Request to verify a domain."""
    domain: str
    verification_method: str = "dns"  # dns, file, meta
    verification_code: Optional[str] = None


class QuotaUpdate(BaseModel):
    """Request to update tenant quota."""
    quota_type: str
    new_limit: Any
    reason: Optional[str] = None
    effective_date: Optional[datetime] = None


class TenantMigration(BaseModel):
    """Request to migrate tenant."""
    source_region: str
    target_region: str
    migration_type: str = "full"  # full, data_only, config_only
    include_backups: bool = True
    downtime_window: Optional[Dict[str, Any]] = None


# Additional Request Models

class CustomDomainRequest(BaseModel):
    """Request to add custom domain."""
    domain: str
    auto_verify: bool = True
    auto_ssl: bool = True


class TenantContext(BaseModel):
    """Tenant context for request processing."""
    tenant_id: str
    name: str
    subdomain: str
    is_active: bool
    plan: str
    resolved_from: str
    created_at: datetime


class User(BaseModel):
    """User model for authentication."""
    user_id: str
    email: str
    name: str
    tenant_id: str
    roles: List[str] = []
    permissions: List[str] = []
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has permission."""
        return permission in self.permissions


# Response Models

class TenantInfo(BaseModel):
    """Complete tenant information."""
    tenant_id: str
    name: str
    description: Optional[str] = None
    state: TenantState
    template: TenantTemplate
    region: str
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    deletion_requested_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    # Configuration
    config: TenantConfig = Field(default_factory=TenantConfig)
    quota: TenantQuota = Field(default_factory=TenantQuota)
    
    # Infrastructure
    database_info: Optional[DatabaseInfo] = None
    storage_info: Optional[StorageInfo] = None
    domains: List[DomainInfo] = []
    
    # Usage
    current_usage: Optional[TenantUsage] = None
    
    # Additional info
    suspension_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TenantListResponse(BaseModel):
    """List of tenants response."""
    tenants: List[TenantInfo]
    total_count: int
    page: int = 1
    page_size: int = 100
    has_more: bool = False


class TenantProvisioningStatus(BaseModel):
    """Tenant provisioning status."""
    tenant_id: str
    status: str
    progress: float = Field(ge=0.0, le=100.0)
    current_step: str
    steps_completed: List[str] = []
    steps_remaining: List[str] = []
    errors: List[str] = []
    started_at: datetime
    estimated_completion: Optional[datetime] = None


class TenantStatistics(BaseModel):
    """Tenant usage statistics."""
    tenant_id: str
    period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: datetime
    
    # Resource usage
    avg_storage_gb: float
    peak_storage_gb: float
    total_bandwidth_gb: float
    total_api_calls: int
    total_compute_hours: float
    
    # User activity
    active_users: int
    new_users: int
    login_count: int
    
    # Asset activity
    assets_created: int
    assets_deleted: int
    assets_downloaded: int
    
    # Cost metrics
    estimated_cost: Optional[float] = None
    cost_breakdown: Dict[str, float] = {}


class TenantHealth(BaseModel):
    """Tenant health status."""
    tenant_id: str
    overall_status: str  # healthy, degraded, unhealthy
    checks: Dict[str, Dict[str, Any]] = {}
    last_check: datetime
    issues: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class TenantResponse(BaseModel):
    """Tenant response model."""
    tenant_id: str
    name: str
    subdomain: str
    status: TenantStatus
    plan: SubscriptionPlan
    created_at: datetime
    config: Optional[TenantConfig] = None
    domains: List[DomainInfo] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        orm_mode = True


class TenantUsageResponse(BaseModel):
    """Tenant usage response."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    storage_gb: float
    bandwidth_gb: float
    api_calls: int
    active_users: int
    asset_count: int
    cost_estimate: Optional[float] = None


class TenantBackup(BaseModel):
    """Tenant backup information."""
    backup_id: str
    tenant_id: str
    backup_type: str  # full, incremental, config_only
    status: str  # pending, in_progress, completed, failed
    size_gb: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    retention_days: int
    storage_location: str
    metadata: Dict[str, Any] = {}


class BillingInfo(BaseModel):
    """Tenant billing information."""
    tenant_id: str
    billing_period: str
    start_date: datetime
    end_date: datetime
    
    # Usage summary
    usage_summary: Dict[str, Any]
    
    # Cost calculation
    base_cost: float
    usage_cost: float
    discounts: float
    tax: float
    total_cost: float
    
    # Line items
    line_items: List[Dict[str, Any]] = []
    
    # Payment info
    payment_status: str
    invoice_id: Optional[str] = None
    payment_method: Optional[str] = None


# Admin Models

class GlobalStatistics(BaseModel):
    """Global multi-tenant statistics."""
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    
    # Resource usage
    total_storage_gb: float
    total_bandwidth_gb: float
    total_api_calls: int
    
    # System metrics
    avg_provisioning_time: float
    tenant_churn_rate: float
    
    # Regional distribution
    tenants_by_region: Dict[str, int]
    tenants_by_template: Dict[str, int]
    
    # Time series data
    growth_trend: List[Dict[str, Any]] = []
    
    last_updated: datetime


# Error Models

class TenantError(BaseModel):
    """Tenant operation error."""
    error_code: str
    message: str
    tenant_id: Optional[str] = None
    details: Dict[str, Any] = {}
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "TENANT_QUOTA_EXCEEDED",
                "message": "Storage quota exceeded",
                "tenant_id": "tenant123",
                "details": {
                    "quota_type": "storage",
                    "current": 1100,
                    "limit": 1000
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }