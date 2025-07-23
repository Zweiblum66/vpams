"""
Audit Trail Schemas for Rights Management Service
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class AuditAction(str, Enum):
    """Audit action types"""
    # Rights Party Actions
    PARTY_CREATED = "party_created"
    PARTY_UPDATED = "party_updated"
    PARTY_DELETED = "party_deleted"
    PARTY_ACTIVATED = "party_activated"
    PARTY_DEACTIVATED = "party_deactivated"
    
    # License Actions
    LICENSE_CREATED = "license_created"
    LICENSE_UPDATED = "license_updated"
    LICENSE_APPROVED = "license_approved"
    LICENSE_REJECTED = "license_rejected"
    LICENSE_ACTIVATED = "license_activated"
    LICENSE_SUSPENDED = "license_suspended"
    LICENSE_TERMINATED = "license_terminated"
    LICENSE_EXPIRED = "license_expired"
    LICENSE_RENEWED = "license_renewed"
    LICENSE_DOWNLOADED = "license_downloaded"
    LICENSE_VIEWED = "license_viewed"
    
    # Usage Actions
    USAGE_RECORDED = "usage_recorded"
    USAGE_UPDATED = "usage_updated"
    USAGE_DELETED = "usage_deleted"
    USAGE_EXPORTED = "usage_exported"
    
    # Compliance Actions
    COMPLIANCE_CHECK_PERFORMED = "compliance_check_performed"
    COMPLIANCE_ALERT_CREATED = "compliance_alert_created"
    COMPLIANCE_ALERT_RESOLVED = "compliance_alert_resolved"
    COMPLIANCE_ALERT_ACKNOWLEDGED = "compliance_alert_acknowledged"
    
    # Report Actions
    REPORT_GENERATED = "report_generated"
    REPORT_EXPORTED = "report_exported"
    REPORT_SCHEDULED = "report_scheduled"
    
    # Access Control Actions
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    PERMISSION_CHANGED = "permission_changed"
    
    # System Actions
    BULK_OPERATION_PERFORMED = "bulk_operation_performed"
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    SETTINGS_CHANGED = "settings_changed"


class AuditResourceType(str, Enum):
    """Resource types that can be audited"""
    RIGHTS_PARTY = "rights_party"
    LICENSE = "license"
    USAGE_RECORD = "usage_record"
    COMPLIANCE_ALERT = "compliance_alert"
    REPORT = "report"
    SYSTEM = "system"


class AuditTrailBase(BaseModel):
    """Base audit trail model"""
    action: AuditAction
    resource_type: AuditResourceType
    resource_id: str = Field(..., description="ID of the resource being audited")
    
    # User information
    user_id: str = Field(..., description="ID of the user performing the action")
    user_email: str = Field(..., description="Email of the user performing the action")
    user_name: Optional[str] = Field(None, description="Name of the user performing the action")
    user_roles: List[str] = Field(default_factory=list, description="Roles of the user at the time of action")
    
    # Context information
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address of the request")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    session_id: Optional[str] = Field(None, max_length=100, description="Session identifier")
    
    # Change details
    old_values: Optional[Dict[str, Any]] = Field(None, description="Previous values (for updates)")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values (for creates/updates)")
    changes_summary: Optional[str] = Field(None, max_length=1000, description="Human-readable summary of changes")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    # Compliance and security
    compliance_relevant: bool = Field(False, description="Whether this action is compliance-relevant")
    security_relevant: bool = Field(False, description="Whether this action is security-relevant")
    
    # Status
    success: bool = Field(True, description="Whether the action was successful")
    error_message: Optional[str] = Field(None, max_length=1000, description="Error message if action failed")


class AuditTrailCreate(AuditTrailBase):
    """Create audit trail entry"""
    pass


class AuditTrailResponse(AuditTrailBase):
    """Audit trail response"""
    id: str
    timestamp: datetime
    
    # Computed fields
    resource_display_name: Optional[str] = Field(None, description="Human-readable resource name")
    action_display_name: Optional[str] = Field(None, description="Human-readable action name")
    
    class Config:
        from_attributes = True


class AuditTrailFilter(BaseModel):
    """Filter for audit trail queries"""
    # Time range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Resource filters
    resource_type: Optional[AuditResourceType] = None
    resource_id: Optional[str] = None
    resource_ids: Optional[List[str]] = None
    
    # Action filters
    action: Optional[AuditAction] = None
    actions: Optional[List[AuditAction]] = None
    
    # User filters
    user_id: Optional[str] = None
    user_ids: Optional[List[str]] = None
    user_email: Optional[str] = None
    
    # Context filters
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    
    # Status filters
    success: Optional[bool] = None
    compliance_relevant: Optional[bool] = None
    security_relevant: Optional[bool] = None
    
    # Text search
    search_text: Optional[str] = Field(None, description="Search in changes_summary and metadata")
    
    # Tags
    tags: Optional[List[str]] = None
    
    # Sorting
    sort_by: str = Field("timestamp", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class AuditTrailExport(BaseModel):
    """Export audit trail request"""
    filter: AuditTrailFilter
    format: str = Field("csv", pattern="^(csv|json|excel)$", description="Export format")
    include_fields: Optional[List[str]] = Field(None, description="Fields to include in export")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude from export")


class AuditTrailStats(BaseModel):
    """Audit trail statistics"""
    total_entries: int
    entries_by_action: Dict[str, int]
    entries_by_resource_type: Dict[str, int]
    entries_by_user: Dict[str, int]
    entries_by_date: List[Dict[str, Any]]
    
    # Compliance and security
    compliance_relevant_count: int
    security_relevant_count: int
    failed_actions_count: int
    
    # Time range
    start_date: datetime
    end_date: datetime


class AuditRetentionPolicy(BaseModel):
    """Audit retention policy"""
    retention_days: int = Field(2555, ge=90, description="Number of days to retain audit logs (default 7 years)")
    compliance_relevant_retention_days: int = Field(3650, ge=365, description="Retention for compliance-relevant logs (default 10 years)")
    archive_after_days: int = Field(365, ge=30, description="Archive logs after this many days")
    delete_archived_after_days: int = Field(2555, ge=365, description="Delete archived logs after this many days")
    
    # Exclusions
    exclude_actions: List[AuditAction] = Field(default_factory=list, description="Actions to exclude from long-term retention")
    exclude_resource_types: List[AuditResourceType] = Field(default_factory=list, description="Resource types to exclude")


class AuditReport(BaseModel):
    """Audit report configuration"""
    report_type: str = Field(..., description="Type of audit report")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Filters
    filter: AuditTrailFilter
    
    # Grouping and aggregation
    group_by: Optional[List[str]] = Field(None, description="Fields to group by")
    aggregate_fields: Optional[Dict[str, str]] = Field(None, description="Fields to aggregate with functions")
    
    # Output
    format: str = Field("pdf", pattern="^(pdf|html|excel|csv)$")
    include_charts: bool = Field(True, description="Include visual charts in report")
    include_raw_data: bool = Field(False, description="Include raw audit entries")
    
    # Schedule
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled reports")
    recipients: List[str] = Field(default_factory=list, description="Email recipients for scheduled reports")


class AuditComplianceReport(BaseModel):
    """Compliance-focused audit report"""
    compliance_standard: str = Field(..., description="Compliance standard (e.g., GDPR, SOX, HIPAA)")
    period_start: datetime
    period_end: datetime
    
    # Compliance checks
    include_access_logs: bool = True
    include_data_changes: bool = True
    include_permission_changes: bool = True
    include_failed_attempts: bool = True
    
    # Summary statistics
    total_actions: int
    high_risk_actions: int
    unauthorized_attempts: int
    data_exports: int
    
    # Findings
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# Helper models for audit context
class AuditContext(BaseModel):
    """Context information for audit logging"""
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    user_roles: List[str] = Field(default_factory=list)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    @classmethod
    def from_request(cls, request, user: Dict[str, Any]) -> "AuditContext":
        """Create audit context from HTTP request and user"""
        return cls(
            user_id=user.get("user_id", "unknown"),
            user_email=user.get("email", "unknown"),
            user_name=user.get("name"),
            user_roles=user.get("roles", []),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            session_id=request.headers.get("x-session-id")
        )


class AuditDiff(BaseModel):
    """Represents differences between old and new values"""
    field: str
    old_value: Any
    new_value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value
        }


class AuditBatch(BaseModel):
    """Batch of audit entries to create"""
    entries: List[AuditTrailCreate]
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique batch identifier")
    batch_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the entire batch")