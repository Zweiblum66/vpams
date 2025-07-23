"""Custom exceptions for Security Audit Service"""


class SecurityAuditException(Exception):
    """Base exception for security audit service"""
    pass


class AuditNotFoundError(SecurityAuditException):
    """Raised when audit is not found"""
    pass


class AuditInProgressError(SecurityAuditException):
    """Raised when trying to modify an audit that's in progress"""
    pass


class ScannerNotAvailableError(SecurityAuditException):
    """Raised when a scanner is not available"""
    pass


class InvalidScanConfigurationError(SecurityAuditException):
    """Raised when scan configuration is invalid"""
    pass


class ReportGenerationError(SecurityAuditException):
    """Raised when report generation fails"""
    pass


class ComplianceCheckError(SecurityAuditException):
    """Raised when compliance check fails"""
    pass