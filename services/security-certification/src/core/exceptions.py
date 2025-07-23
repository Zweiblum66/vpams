"""
Custom exceptions for Security Certification Service.
"""


class SecurityCertificationError(Exception):
    """Base exception for security certification service."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "SECURITY_CERT_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class SecurityScanError(SecurityCertificationError):
    """Exception raised during security scanning."""
    
    def __init__(self, message: str, scan_id: str = None, target: str = None):
        self.scan_id = scan_id
        self.target = target
        details = {}
        if scan_id:
            details["scan_id"] = scan_id
        if target:
            details["target"] = target
        super().__init__(message, "SECURITY_SCAN_ERROR", details)


class ComplianceCheckError(SecurityCertificationError):
    """Exception raised during compliance checking."""
    
    def __init__(self, message: str, standard: str = None, control_id: str = None):
        self.standard = standard
        self.control_id = control_id
        details = {}
        if standard:
            details["standard"] = standard
        if control_id:
            details["control_id"] = control_id
        super().__init__(message, "COMPLIANCE_CHECK_ERROR", details)


class CertificationReportError(SecurityCertificationError):
    """Exception raised during report generation."""
    
    def __init__(self, message: str, report_type: str = None, audit_id: str = None):
        self.report_type = report_type
        self.audit_id = audit_id
        details = {}
        if report_type:
            details["report_type"] = report_type
        if audit_id:
            details["audit_id"] = audit_id
        super().__init__(message, "CERTIFICATION_REPORT_ERROR", details)


class VulnerabilityAssessmentError(SecurityCertificationError):
    """Exception raised during vulnerability assessment."""
    
    def __init__(self, message: str, target: str = None, scan_type: str = None):
        self.target = target
        self.scan_type = scan_type
        details = {}
        if target:
            details["target"] = target
        if scan_type:
            details["scan_type"] = scan_type
        super().__init__(message, "VULNERABILITY_ASSESSMENT_ERROR", details)


class SecurityMetricsError(SecurityCertificationError):
    """Exception raised during security metrics calculation."""
    
    def __init__(self, message: str, metric_type: str = None):
        self.metric_type = metric_type
        details = {}
        if metric_type:
            details["metric_type"] = metric_type
        super().__init__(message, "SECURITY_METRICS_ERROR", details)


class AuditConfigurationError(SecurityCertificationError):
    """Exception raised due to audit configuration issues."""
    
    def __init__(self, message: str, config_field: str = None):
        self.config_field = config_field
        details = {}
        if config_field:
            details["config_field"] = config_field
        super().__init__(message, "AUDIT_CONFIGURATION_ERROR", details)


class SecurityToolError(SecurityCertificationError):
    """Exception raised when external security tools fail."""
    
    def __init__(self, message: str, tool_name: str = None, exit_code: int = None):
        self.tool_name = tool_name
        self.exit_code = exit_code
        details = {}
        if tool_name:
            details["tool_name"] = tool_name
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(message, "SECURITY_TOOL_ERROR", details)


class DatabaseError(SecurityCertificationError):
    """Exception raised during database operations."""
    
    def __init__(self, message: str, operation: str = None, table: str = None):
        self.operation = operation
        self.table = table
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        super().__init__(message, "DATABASE_ERROR", details)


class AuthenticationError(SecurityCertificationError):
    """Exception raised during authentication."""
    
    def __init__(self, message: str, user_id: str = None):
        self.user_id = user_id
        details = {}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(SecurityCertificationError):
    """Exception raised during authorization."""
    
    def __init__(self, message: str, user_id: str = None, required_permission: str = None):
        self.user_id = user_id
        self.required_permission = required_permission
        details = {}
        if user_id:
            details["user_id"] = user_id
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class RateLimitError(SecurityCertificationError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str, limit: int = None, window: int = None):
        self.limit = limit
        self.window = window
        details = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class ValidationError(SecurityCertificationError):
    """Exception raised during input validation."""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        super().__init__(message, "VALIDATION_ERROR", details)


class ExternalServiceError(SecurityCertificationError):
    """Exception raised when external services fail."""
    
    def __init__(self, message: str, service: str = None, status_code: int = None):
        self.service = service
        self.status_code = status_code
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)