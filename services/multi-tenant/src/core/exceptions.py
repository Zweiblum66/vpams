"""Custom exceptions for Multi-Tenant Service."""

from typing import Dict, Any, Optional


class MultiTenantException(Exception):
    """Base exception for multi-tenant related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "MULTI_TENANT_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class TenantNotFoundError(MultiTenantException):
    """Tenant not found error."""
    
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant not found: {tenant_id}",
            error_code="TENANT_NOT_FOUND",
            status_code=404,
            details={"tenant_id": tenant_id}
        )


class TenantAlreadyExistsError(MultiTenantException):
    """Tenant already exists error."""
    
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant already exists: {tenant_id}",
            error_code="TENANT_ALREADY_EXISTS",
            status_code=409,
            details={"tenant_id": tenant_id}
        )


class TenantProvisioningError(MultiTenantException):
    """Tenant provisioning error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Tenant provisioning failed: {message}",
            error_code="TENANT_PROVISIONING_ERROR",
            status_code=500,
            details=details
        )


class TenantQuotaExceededError(MultiTenantException):
    """Tenant quota exceeded error."""
    
    def __init__(self, quota_type: str, current: int, limit: int):
        super().__init__(
            message=f"Tenant quota exceeded for {quota_type}: {current} > {limit}",
            error_code="TENANT_QUOTA_EXCEEDED",
            status_code=429,
            details={"quota_type": quota_type, "current": current, "limit": limit}
        )


class TenantIsolationError(MultiTenantException):
    """Tenant isolation violation error."""
    
    def __init__(self, message: str, tenant_id: str, target_tenant: str = None):
        super().__init__(
            message=f"Tenant isolation violation: {message}",
            error_code="TENANT_ISOLATION_ERROR",
            status_code=403,
            details={"tenant_id": tenant_id, "target_tenant": target_tenant}
        )


class DomainNotAvailableError(MultiTenantException):
    """Domain not available error."""
    
    def __init__(self, domain: str, reason: str = "Already in use"):
        super().__init__(
            message=f"Domain not available: {domain}",
            error_code="DOMAIN_NOT_AVAILABLE",
            status_code=409,
            details={"domain": domain, "reason": reason}
        )


class DomainVerificationError(MultiTenantException):
    """Domain verification error."""
    
    def __init__(self, domain: str, reason: str):
        super().__init__(
            message=f"Domain verification failed: {domain}",
            error_code="DOMAIN_VERIFICATION_ERROR",
            status_code=400,
            details={"domain": domain, "reason": reason}
        )


class TenantConfigurationError(MultiTenantException):
    """Tenant configuration error."""
    
    def __init__(self, config_key: str, reason: str):
        super().__init__(
            message=f"Invalid tenant configuration: {config_key}",
            error_code="TENANT_CONFIGURATION_ERROR",
            status_code=400,
            details={"config_key": config_key, "reason": reason}
        )


class TenantResourceLimitError(MultiTenantException):
    """Tenant resource limit error."""
    
    def __init__(self, resource: str, limit: Any, requested: Any):
        super().__init__(
            message=f"Resource limit exceeded for {resource}",
            error_code="TENANT_RESOURCE_LIMIT",
            status_code=429,
            details={"resource": resource, "limit": limit, "requested": requested}
        )


class TenantStateError(MultiTenantException):
    """Invalid tenant state error."""
    
    def __init__(self, tenant_id: str, current_state: str, operation: str):
        super().__init__(
            message=f"Invalid tenant state for operation {operation}",
            error_code="TENANT_STATE_ERROR",
            status_code=409,
            details={
                "tenant_id": tenant_id,
                "current_state": current_state,
                "operation": operation
            }
        )


class TenantDeletionError(MultiTenantException):
    """Tenant deletion error."""
    
    def __init__(self, tenant_id: str, reason: str):
        super().__init__(
            message=f"Cannot delete tenant: {reason}",
            error_code="TENANT_DELETION_ERROR",
            status_code=400,
            details={"tenant_id": tenant_id, "reason": reason}
        )


class TenantMigrationError(MultiTenantException):
    """Tenant migration error."""
    
    def __init__(self, tenant_id: str, source: str, target: str, reason: str):
        super().__init__(
            message=f"Tenant migration failed: {reason}",
            error_code="TENANT_MIGRATION_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "source": source,
                "target": target,
                "reason": reason
            }
        )


class TenantBackupError(MultiTenantException):
    """Tenant backup error."""
    
    def __init__(self, tenant_id: str, operation: str, reason: str):
        super().__init__(
            message=f"Tenant backup {operation} failed: {reason}",
            error_code="TENANT_BACKUP_ERROR",
            status_code=500,
            details={
                "tenant_id": tenant_id,
                "operation": operation,
                "reason": reason
            }
        )


class ConfigurationError(MultiTenantException):
    """Configuration related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class ValidationError(MultiTenantException):
    """Input validation errors."""
    
    def __init__(self, message: str, field: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, **(details or {})}
        )


class ResourceNotFoundError(MultiTenantException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class PermissionDeniedError(MultiTenantException):
    """Permission denied errors."""
    
    def __init__(self, action: str, resource: str = ""):
        super().__init__(
            message=f"Permission denied for action: {action}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"action": action, "resource": resource}
        )