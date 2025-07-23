"""Custom exceptions for GDPR Compliance Service"""

from typing import Optional


class GDPRComplianceError(Exception):
    """Base exception for GDPR compliance service"""
    pass


class DataRequestError(GDPRComplianceError):
    """Error in processing data request"""
    pass


class ConsentError(GDPRComplianceError):
    """Error in consent management"""
    pass


class ExportError(GDPRComplianceError):
    """Error in data export"""
    pass


class DeletionError(GDPRComplianceError):
    """Error in data deletion"""
    pass


class PolicyError(GDPRComplianceError):
    """Error in privacy policy management"""
    pass


class ValidationError(GDPRComplianceError):
    """Validation error"""
    pass


class NotFoundException(GDPRComplianceError):
    """Resource not found"""
    pass


class UnauthorizedError(GDPRComplianceError):
    """Unauthorized access"""
    pass


class ReportGenerationError(GDPRComplianceError):
    """Error generating audit report"""
    pass


class RetentionError(GDPRComplianceError):
    """Error in data retention operations"""
    pass


class DataClassificationError(GDPRComplianceError):
    """Error in data classification operations"""
    pass


class CategoryNotFoundError(NotFoundException):
    """Data category not found"""
    pass


class MappingNotFoundError(NotFoundException):
    """Data mapping not found"""
    pass


class PolicyViolationError(GDPRComplianceError):
    """Policy violation prevents operation"""
    pass


class NotFoundError(NotFoundException):
    """Generic not found error"""
    pass