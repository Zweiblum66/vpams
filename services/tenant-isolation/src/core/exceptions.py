"""Custom exceptions for Tenant Isolation Service."""

from typing import Dict, Any, Optional


class TenantIsolationException(Exception):
    """Base exception for tenant isolation related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "TENANT_ISOLATION_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class IsolationViolationError(TenantIsolationException):
    """Tenant isolation violation error."""
    
    def __init__(self, violation_type: str, tenant_id: str, target_tenant: Optional[str] = None):
        super().__init__(
            message=f"Tenant isolation violation: {violation_type}",
            error_code="ISOLATION_VIOLATION",
            status_code=403,
            details={
                "violation_type": violation_type,
                "tenant_id": tenant_id,
                "target_tenant": target_tenant
            }
        )


class CrossTenantAccessError(TenantIsolationException):
    """Cross-tenant access attempt error."""
    
    def __init__(self, source_tenant: str, target_tenant: str, resource: str):
        super().__init__(
            message=f"Cross-tenant access denied: {source_tenant} -> {target_tenant}",
            error_code="CROSS_TENANT_ACCESS_DENIED",
            status_code=403,
            details={
                "source_tenant": source_tenant,
                "target_tenant": target_tenant,
                "resource": resource
            }
        )


class TenantContextMissingError(TenantIsolationException):
    """Tenant context missing error."""
    
    def __init__(self, operation: str):
        super().__init__(
            message=f"Tenant context required for operation: {operation}",
            error_code="TENANT_CONTEXT_MISSING",
            status_code=400,
            details={"operation": operation}
        )


class DataResidencyViolationError(TenantIsolationException):
    """Data residency violation error."""
    
    def __init__(self, tenant_id: str, required_region: str, actual_region: str):
        super().__init__(
            message=f"Data residency violation for tenant {tenant_id}",
            error_code="DATA_RESIDENCY_VIOLATION",
            status_code=403,
            details={
                "tenant_id": tenant_id,
                "required_region": required_region,
                "actual_region": actual_region
            }
        )


class EncryptionKeyError(TenantIsolationException):
    """Tenant encryption key error."""
    
    def __init__(self, tenant_id: str, operation: str):
        super().__init__(
            message=f"Encryption key error for tenant {tenant_id}: {operation}",
            error_code="ENCRYPTION_KEY_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "operation": operation
            }
        )


class ResourceIsolationError(TenantIsolationException):
    """Resource isolation error."""
    
    def __init__(self, resource_type: str, tenant_id: str, reason: str):
        super().__init__(
            message=f"Resource isolation error for {resource_type}",
            error_code="RESOURCE_ISOLATION_ERROR",
            status_code=500,
            details={
                "resource_type": resource_type,
                "tenant_id": tenant_id,
                "reason": reason
            }
        )


class DatabaseIsolationError(TenantIsolationException):
    """Database isolation error."""
    
    def __init__(self, tenant_id: str, operation: str, reason: str):
        super().__init__(
            message=f"Database isolation error during {operation}",
            error_code="DATABASE_ISOLATION_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "operation": operation,
                "reason": reason
            }
        )


class StorageIsolationError(TenantIsolationException):
    """Storage isolation error."""
    
    def __init__(self, tenant_id: str, path: str, reason: str):
        super().__init__(
            message=f"Storage isolation error: {reason}",
            error_code="STORAGE_ISOLATION_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "path": path,
                "reason": reason
            }
        )


class NetworkIsolationError(TenantIsolationException):
    """Network isolation error."""
    
    def __init__(self, tenant_id: str, network_resource: str, reason: str):
        super().__init__(
            message=f"Network isolation error: {reason}",
            error_code="NETWORK_ISOLATION_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "network_resource": network_resource,
                "reason": reason
            }
        )


class CacheIsolationError(TenantIsolationException):
    """Cache isolation error."""
    
    def __init__(self, tenant_id: str, cache_key: str, reason: str):
        super().__init__(
            message=f"Cache isolation error: {reason}",
            error_code="CACHE_ISOLATION_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "cache_key": cache_key,
                "reason": reason
            }
        )


class AuditLogError(TenantIsolationException):
    """Audit log error."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Audit log error during {operation}: {reason}",
            error_code="AUDIT_LOG_ERROR",
            status_code=500,
            details={
                "operation": operation,
                "reason": reason
            }
        )


class ComplianceViolationError(TenantIsolationException):
    """Compliance violation error."""
    
    def __init__(self, compliance_type: str, violation: str, tenant_id: str):
        super().__init__(
            message=f"Compliance violation ({compliance_type}): {violation}",
            error_code="COMPLIANCE_VIOLATION",
            status_code=403,
            details={
                "compliance_type": compliance_type,
                "violation": violation,
                "tenant_id": tenant_id
            }
        )


class ConfigurationError(TenantIsolationException):
    """Configuration related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class ValidationError(TenantIsolationException):
    """Input validation errors."""
    
    def __init__(self, message: str, field: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, **(details or {})}
        )


class ResourceNotFoundError(TenantIsolationException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class PermissionDeniedError(TenantIsolationException):
    """Permission denied errors."""
    
    def __init__(self, action: str, resource: str = ""):
        super().__init__(
            message=f"Permission denied for action: {action}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"action": action, "resource": resource}
        )