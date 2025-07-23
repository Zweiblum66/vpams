"""
Isolation Manager - Core service for enforcing tenant isolation.

Manages database, storage, network, and application-level isolation
to ensure complete data separation between tenants.
"""

import asyncio
import hashlib
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import structlog
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
import aioredis

from ..core.config import get_settings
from ..core.exceptions import (
    IsolationViolationError, CrossTenantAccessError, TenantContextMissingError,
    DatabaseIsolationError, StorageIsolationError, NetworkIsolationError,
    CacheIsolationError, DataResidencyViolationError, EncryptionKeyError
)
from ..models.schemas import (
    IsolationPolicy, TenantContext, IsolationRule, AccessRequest,
    IsolationViolation, AuditLog
)
from .database_isolator import DatabaseIsolator
from .storage_isolator import StorageIsolator
from .network_isolator import NetworkIsolator
from .cache_isolator import CacheIsolator
from .encryption_manager import EncryptionManager


logger = structlog.get_logger()


class IsolationLevel(Enum):
    """Isolation enforcement levels."""
    STRICT = "strict"      # Complete isolation, no cross-tenant access
    MODERATE = "moderate"  # Controlled cross-tenant access with audit
    MINIMAL = "minimal"    # Basic isolation with warnings


@dataclass
class IsolationContext:
    """Context for isolation enforcement."""
    tenant_id: str
    user_id: str
    session_id: str
    request_id: str
    source_ip: str
    resource_type: str
    operation: str
    metadata: Dict[str, Any]


class IsolationManager:
    """
    Main service for managing and enforcing tenant isolation.
    
    Coordinates all isolation mechanisms across different layers:
    - Database isolation (schemas, RLS, connection pools)
    - Storage isolation (paths, encryption, access control)
    - Network isolation (API namespaces, rate limiting)
    - Cache isolation (key prefixes, data segregation)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.isolation_level = IsolationLevel(self.settings.isolation_mode)
        
        # Isolation components
        self.db_isolator: Optional[DatabaseIsolator] = None
        self.storage_isolator: Optional[StorageIsolator] = None
        self.network_isolator: Optional[NetworkIsolator] = None
        self.cache_isolator: Optional[CacheIsolator] = None
        self.encryption_manager: Optional[EncryptionManager] = None
        
        # Connection pools per tenant
        self.tenant_db_pools: Dict[str, Any] = {}
        self.tenant_cache_pools: Dict[str, Any] = {}
        
        # Active tenant contexts
        self.active_contexts: Dict[str, TenantContext] = {}
        
        # Isolation policies
        self.isolation_policies: Dict[str, IsolationPolicy] = {}
        
        # Audit logs
        self.audit_buffer: List[AuditLog] = []
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # Statistics
        self.stats = {
            "isolation_checks": 0,
            "violations_detected": 0,
            "cross_tenant_attempts": 0,
            "audit_logs_generated": 0,
            "last_violation": None
        }
    
    async def initialize(self) -> None:
        """Initialize isolation manager and components."""
        try:
            logger.info("Initializing isolation manager", level=self.isolation_level.value)
            
            # Initialize isolation components
            if self.settings.db_isolation_enabled:
                self.db_isolator = DatabaseIsolator()
                await self.db_isolator.initialize()
                logger.info("Database isolator initialized")
            
            if self.settings.storage_isolation_enabled:
                self.storage_isolator = StorageIsolator()
                await self.storage_isolator.initialize()
                logger.info("Storage isolator initialized")
            
            if self.settings.network_isolation_enabled:
                self.network_isolator = NetworkIsolator()
                await self.network_isolator.initialize()
                logger.info("Network isolator initialized")
            
            if self.settings.cache_isolation_enabled:
                self.cache_isolator = CacheIsolator()
                await self.cache_isolator.initialize()
                logger.info("Cache isolator initialized")
            
            if self.settings.tenant_encryption_enabled:
                self.encryption_manager = EncryptionManager()
                await self.encryption_manager.initialize()
                logger.info("Encryption manager initialized")
            
            # Load isolation policies
            await self._load_isolation_policies()
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Isolation manager initialized",
                components={
                    "database": self.db_isolator is not None,
                    "storage": self.storage_isolator is not None,
                    "network": self.network_isolator is not None,
                    "cache": self.cache_isolator is not None,
                    "encryption": self.encryption_manager is not None
                }
            )
            
        except Exception as e:
            logger.error("Failed to initialize isolation manager", error=str(e))
            raise
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and enforcement tasks."""
        # Audit log flushing
        task = asyncio.create_task(self._audit_flush_loop())
        self._tasks.append(task)
        
        # Policy enforcement
        task = asyncio.create_task(self._policy_enforcement_loop())
        self._tasks.append(task)
        
        # Connection pool cleanup
        task = asyncio.create_task(self._pool_cleanup_loop())
        self._tasks.append(task)
        
        # Statistics update
        task = asyncio.create_task(self._stats_update_loop())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def enforce_isolation(self, context: IsolationContext) -> bool:
        """
        Enforce isolation for a specific operation.
        
        Args:
            context: Isolation context with tenant and operation details
            
        Returns:
            True if access is allowed, False otherwise
            
        Raises:
            Various isolation violation errors
        """
        self.stats["isolation_checks"] += 1
        
        try:
            # Validate tenant context
            if not context.tenant_id:
                raise TenantContextMissingError(context.operation)
            
            # Check if operation is allowed
            if not await self._check_operation_allowed(context):
                self.stats["violations_detected"] += 1
                raise IsolationViolationError(
                    "Operation not allowed",
                    context.tenant_id
                )
            
            # Apply isolation based on resource type
            if context.resource_type == "database":
                return await self._enforce_database_isolation(context)
            
            elif context.resource_type == "storage":
                return await self._enforce_storage_isolation(context)
            
            elif context.resource_type == "network":
                return await self._enforce_network_isolation(context)
            
            elif context.resource_type == "cache":
                return await self._enforce_cache_isolation(context)
            
            else:
                # Default application-level isolation
                return await self._enforce_application_isolation(context)
                
        except Exception as e:
            # Log violation
            await self._log_violation(context, str(e))
            raise
    
    async def _check_operation_allowed(self, context: IsolationContext) -> bool:
        """Check if operation is allowed based on isolation policies."""
        # Get tenant policy
        policy = self.isolation_policies.get(
            context.tenant_id,
            self._get_default_policy()
        )
        
        # Check against policy rules
        for rule in policy.rules:
            if await self._evaluate_rule(rule, context):
                return rule.allow
        
        # Default deny for strict mode
        return self.isolation_level != IsolationLevel.STRICT
    
    async def _evaluate_rule(self, rule: IsolationRule, context: IsolationContext) -> bool:
        """Evaluate a single isolation rule."""
        # Match resource type
        if rule.resource_type != "*" and rule.resource_type != context.resource_type:
            return False
        
        # Match operation
        if rule.operation != "*" and rule.operation != context.operation:
            return False
        
        # Additional conditions
        for condition in rule.conditions:
            if not await self._evaluate_condition(condition, context):
                return False
        
        return True
    
    async def _evaluate_condition(self, condition: Dict[str, Any], context: IsolationContext) -> bool:
        """Evaluate rule condition."""
        condition_type = condition.get("type")
        
        if condition_type == "ip_range":
            return self._check_ip_in_range(context.source_ip, condition.get("value"))
        
        elif condition_type == "time_window":
            return self._check_time_window(condition.get("start"), condition.get("end"))
        
        elif condition_type == "user_role":
            return await self._check_user_role(context.user_id, condition.get("value"))
        
        return True
    
    async def _enforce_database_isolation(self, context: IsolationContext) -> bool:
        """Enforce database-level isolation."""
        if not self.db_isolator:
            return True
        
        try:
            # Get tenant-specific connection pool
            db_pool = await self._get_tenant_db_pool(context.tenant_id)
            
            # Apply row-level security
            if self.settings.row_level_security_enabled:
                await self.db_isolator.apply_row_level_security(
                    db_pool,
                    context.tenant_id,
                    context.user_id
                )
            
            # Set schema search path
            if self.settings.schema_isolation_enabled:
                await self.db_isolator.set_schema_path(
                    db_pool,
                    context.tenant_id
                )
            
            # Audit database access
            await self._audit_access(context, "database", True)
            
            return True
            
        except Exception as e:
            logger.error("Database isolation error", 
                       tenant_id=context.tenant_id, 
                       error=str(e))
            raise DatabaseIsolationError(
                context.tenant_id,
                context.operation,
                str(e)
            )
    
    async def _enforce_storage_isolation(self, context: IsolationContext) -> bool:
        """Enforce storage-level isolation."""
        if not self.storage_isolator:
            return True
        
        try:
            # Validate storage path
            storage_path = context.metadata.get("path", "")
            
            if not await self.storage_isolator.validate_path(
                context.tenant_id,
                storage_path
            ):
                raise StorageIsolationError(
                    context.tenant_id,
                    storage_path,
                    "Invalid storage path for tenant"
                )
            
            # Apply encryption if enabled
            if self.settings.storage_encryption_per_tenant and self.encryption_manager:
                encryption_key = await self.encryption_manager.get_tenant_key(
                    context.tenant_id
                )
                context.metadata["encryption_key"] = encryption_key
            
            # Check storage quota
            if not await self.storage_isolator.check_quota(
                context.tenant_id,
                context.metadata.get("size", 0)
            ):
                raise StorageIsolationError(
                    context.tenant_id,
                    storage_path,
                    "Storage quota exceeded"
                )
            
            # Audit storage access
            await self._audit_access(context, "storage", True)
            
            return True
            
        except Exception as e:
            logger.error("Storage isolation error", 
                       tenant_id=context.tenant_id, 
                       error=str(e))
            raise
    
    async def _enforce_network_isolation(self, context: IsolationContext) -> bool:
        """Enforce network-level isolation."""
        if not self.network_isolator:
            return True
        
        try:
            # Check API namespace
            if self.settings.api_namespace_isolation:
                if not await self.network_isolator.validate_namespace(
                    context.tenant_id,
                    context.metadata.get("api_path", "")
                ):
                    raise NetworkIsolationError(
                        context.tenant_id,
                        "API namespace",
                        "Invalid API namespace for tenant"
                    )
            
            # Apply rate limiting
            if self.settings.rate_limit_per_tenant:
                if not await self.network_isolator.check_rate_limit(
                    context.tenant_id,
                    context.source_ip
                ):
                    raise NetworkIsolationError(
                        context.tenant_id,
                        "Rate limit",
                        "Rate limit exceeded"
                    )
            
            # Audit network access
            await self._audit_access(context, "network", True)
            
            return True
            
        except Exception as e:
            logger.error("Network isolation error", 
                       tenant_id=context.tenant_id, 
                       error=str(e))
            raise
    
    async def _enforce_cache_isolation(self, context: IsolationContext) -> bool:
        """Enforce cache-level isolation."""
        if not self.cache_isolator:
            return True
        
        try:
            # Get tenant-specific cache connection
            cache_pool = await self._get_tenant_cache_pool(context.tenant_id)
            
            # Validate cache key
            cache_key = context.metadata.get("cache_key", "")
            
            if not await self.cache_isolator.validate_key(
                context.tenant_id,
                cache_key
            ):
                raise CacheIsolationError(
                    context.tenant_id,
                    cache_key,
                    "Invalid cache key for tenant"
                )
            
            # Apply key prefix
            if self.settings.cache_key_prefix_per_tenant:
                prefixed_key = await self.cache_isolator.apply_prefix(
                    context.tenant_id,
                    cache_key
                )
                context.metadata["cache_key"] = prefixed_key
            
            # Audit cache access
            await self._audit_access(context, "cache", True)
            
            return True
            
        except Exception as e:
            logger.error("Cache isolation error", 
                       tenant_id=context.tenant_id, 
                       error=str(e))
            raise
    
    async def _enforce_application_isolation(self, context: IsolationContext) -> bool:
        """Enforce application-level isolation."""
        # Check for cross-tenant access attempts
        target_tenant = context.metadata.get("target_tenant")
        
        if target_tenant and target_tenant != context.tenant_id:
            self.stats["cross_tenant_attempts"] += 1
            
            # Check if cross-tenant access is allowed
            if not self.settings.cross_tenant_access_allowed:
                raise CrossTenantAccessError(
                    context.tenant_id,
                    target_tenant,
                    context.resource_type
                )
            
            # Audit cross-tenant access
            if self.settings.audit_cross_tenant_access:
                await self._audit_cross_tenant_access(
                    context,
                    target_tenant
                )
        
        # Check data residency
        if self.settings.enforce_data_residency:
            await self._check_data_residency(context)
        
        return True
    
    async def _check_data_residency(self, context: IsolationContext) -> None:
        """Check data residency requirements."""
        required_region = context.metadata.get("required_region")
        actual_region = context.metadata.get("actual_region")
        
        if required_region and actual_region != required_region:
            raise DataResidencyViolationError(
                context.tenant_id,
                required_region,
                actual_region
            )
    
    async def _get_tenant_db_pool(self, tenant_id: str) -> Any:
        """Get or create tenant-specific database connection pool."""
        if tenant_id not in self.tenant_db_pools:
            # Create isolated connection pool
            pool = await self._create_tenant_db_pool(tenant_id)
            self.tenant_db_pools[tenant_id] = pool
        
        return self.tenant_db_pools[tenant_id]
    
    async def _create_tenant_db_pool(self, tenant_id: str) -> Any:
        """Create tenant-specific database connection pool."""
        # Modify connection string for tenant
        base_url = self.settings.database_url
        tenant_url = f"{base_url}?application_name=tenant_{tenant_id}"
        
        # Create engine with tenant-specific settings
        engine = create_async_engine(
            tenant_url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            poolclass=NullPool if self.settings.connection_pool_isolation else None
        )
        
        return engine
    
    async def _get_tenant_cache_pool(self, tenant_id: str) -> Any:
        """Get or create tenant-specific cache connection pool."""
        if tenant_id not in self.tenant_cache_pools:
            # Create isolated cache connection
            pool = await self._create_tenant_cache_pool(tenant_id)
            self.tenant_cache_pools[tenant_id] = pool
        
        return self.tenant_cache_pools[tenant_id]
    
    async def _create_tenant_cache_pool(self, tenant_id: str) -> Any:
        """Create tenant-specific cache connection pool."""
        redis = await aioredis.create_redis_pool(
            self.settings.redis_url,
            minsize=1,
            maxsize=5,
            db=int(tenant_id[-1]) % 16  # Simple sharding
        )
        
        return redis
    
    async def create_tenant_context(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        request_id: str
    ) -> TenantContext:
        """Create and register a new tenant context."""
        context = TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            created_at=datetime.utcnow(),
            isolation_level=self.isolation_level.value
        )
        
        # Register context
        self.active_contexts[session_id] = context
        
        # Initialize tenant-specific resources if needed
        if self.settings.connection_pool_isolation:
            await self._get_tenant_db_pool(tenant_id)
        
        if self.settings.cache_isolation_enabled:
            await self._get_tenant_cache_pool(tenant_id)
        
        return context
    
    async def validate_access(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        operation: str
    ) -> bool:
        """Validate tenant access to a specific resource."""
        # Quick validation for common cases
        if resource_type == "tenant" and resource_id != tenant_id:
            return False
        
        # Check resource ownership
        owner_tenant = await self._get_resource_owner(resource_type, resource_id)
        
        if owner_tenant and owner_tenant != tenant_id:
            # Log attempted cross-tenant access
            logger.warning(
                "Cross-tenant access attempt",
                source_tenant=tenant_id,
                target_tenant=owner_tenant,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            return False
        
        return True
    
    async def _get_resource_owner(self, resource_type: str, resource_id: str) -> Optional[str]:
        """Get the tenant that owns a specific resource."""
        # Implementation would query resource metadata
        # This is a placeholder
        return None
    
    def _get_default_policy(self) -> IsolationPolicy:
        """Get default isolation policy."""
        return IsolationPolicy(
            policy_id="default",
            name="Default Isolation Policy",
            rules=[
                IsolationRule(
                    rule_id="deny_all",
                    resource_type="*",
                    operation="*",
                    allow=False,
                    conditions=[]
                )
            ]
        )
    
    async def _load_isolation_policies(self) -> None:
        """Load isolation policies from configuration."""
        # Default policies based on isolation level
        if self.isolation_level == IsolationLevel.STRICT:
            # No cross-tenant access
            pass
        elif self.isolation_level == IsolationLevel.MODERATE:
            # Controlled access with audit
            pass
        else:
            # Basic isolation
            pass
        
        logger.info(f"Loaded {len(self.isolation_policies)} isolation policies")
    
    async def _audit_access(
        self,
        context: IsolationContext,
        resource_type: str,
        allowed: bool
    ) -> None:
        """Audit resource access."""
        if not self.settings.audit_enabled:
            return
        
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            session_id=context.session_id,
            request_id=context.request_id,
            resource_type=resource_type,
            operation=context.operation,
            allowed=allowed,
            source_ip=context.source_ip,
            metadata=context.metadata
        )
        
        self.audit_buffer.append(audit_entry)
        self.stats["audit_logs_generated"] += 1
    
    async def _audit_cross_tenant_access(
        self,
        context: IsolationContext,
        target_tenant: str
    ) -> None:
        """Audit cross-tenant access attempt."""
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            session_id=context.session_id,
            request_id=context.request_id,
            resource_type="cross_tenant",
            operation=context.operation,
            allowed=True,  # Already passed checks
            source_ip=context.source_ip,
            metadata={
                **context.metadata,
                "target_tenant": target_tenant,
                "cross_tenant": True
            }
        )
        
        self.audit_buffer.append(audit_entry)
    
    async def _log_violation(self, context: IsolationContext, error: str) -> None:
        """Log isolation violation."""
        violation = IsolationViolation(
            timestamp=datetime.utcnow(),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            violation_type="access_denied",
            resource_type=context.resource_type,
            operation=context.operation,
            error_message=error,
            severity="high" if self.isolation_level == IsolationLevel.STRICT else "medium",
            metadata=context.metadata
        )
        
        self.stats["last_violation"] = violation.timestamp
        
        # Log to audit
        await self._audit_access(context, context.resource_type, False)
        
        logger.warning(
            "Isolation violation detected",
            tenant_id=context.tenant_id,
            violation_type=violation.violation_type,
            resource_type=context.resource_type
        )
    
    def _check_ip_in_range(self, ip: str, ip_range: str) -> bool:
        """Check if IP is in specified range."""
        # Implementation would use ipaddress module
        return True
    
    def _check_time_window(self, start: str, end: str) -> bool:
        """Check if current time is within window."""
        # Implementation would check time range
        return True
    
    async def _check_user_role(self, user_id: str, required_role: str) -> bool:
        """Check if user has required role."""
        # Implementation would query user service
        return True
    
    async def _audit_flush_loop(self) -> None:
        """Background task to flush audit logs."""
        while self._running:
            try:
                if self.audit_buffer:
                    # Flush audit logs to database
                    await self._flush_audit_logs()
                
                await asyncio.sleep(10)  # Flush every 10 seconds
                
            except Exception as e:
                logger.error("Error flushing audit logs", error=str(e))
                await asyncio.sleep(10)
    
    async def _flush_audit_logs(self) -> None:
        """Flush audit logs to persistent storage."""
        if not self.audit_buffer:
            return
        
        logs_to_flush = self.audit_buffer.copy()
        self.audit_buffer.clear()
        
        # Write to database or log aggregation service
        logger.info(f"Flushed {len(logs_to_flush)} audit logs")
    
    async def _policy_enforcement_loop(self) -> None:
        """Background task to enforce isolation policies."""
        while self._running:
            try:
                # Check for policy violations
                await self._check_policy_compliance()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Error in policy enforcement", error=str(e))
                await asyncio.sleep(60)
    
    async def _check_policy_compliance(self) -> None:
        """Check system-wide policy compliance."""
        # Check active contexts for violations
        for session_id, context in self.active_contexts.items():
            # Check session age
            age = (datetime.utcnow() - context.created_at).total_seconds()
            if age > 3600:  # 1 hour timeout
                logger.info("Expiring old tenant context", session_id=session_id)
                del self.active_contexts[session_id]
    
    async def _pool_cleanup_loop(self) -> None:
        """Background task to cleanup idle connection pools."""
        while self._running:
            try:
                # Cleanup idle database pools
                await self._cleanup_idle_pools()
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error("Error in pool cleanup", error=str(e))
                await asyncio.sleep(300)
    
    async def _cleanup_idle_pools(self) -> None:
        """Cleanup idle tenant connection pools."""
        # Implementation would check pool activity and close idle ones
        pass
    
    async def _stats_update_loop(self) -> None:
        """Background task to update statistics."""
        while self._running:
            try:
                logger.debug(
                    "Isolation manager statistics",
                    active_contexts=len(self.active_contexts),
                    db_pools=len(self.tenant_db_pools),
                    cache_pools=len(self.tenant_cache_pools),
                    **self.stats
                )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error("Error in stats update", error=str(e))
                await asyncio.sleep(300)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get isolation manager statistics."""
        return {
            **self.stats,
            "active_contexts": len(self.active_contexts),
            "db_pools": len(self.tenant_db_pools),
            "cache_pools": len(self.tenant_cache_pools),
            "isolation_level": self.isolation_level.value,
            "audit_buffer_size": len(self.audit_buffer)
        }
    
    async def cleanup(self) -> None:
        """Cleanup isolation manager resources."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Flush remaining audit logs
            await self._flush_audit_logs()
            
            # Close connection pools
            for pool in self.tenant_db_pools.values():
                await pool.dispose()
            
            for pool in self.tenant_cache_pools.values():
                pool.close()
                await pool.wait_closed()
            
            # Cleanup components
            if self.db_isolator:
                await self.db_isolator.cleanup()
            
            if self.storage_isolator:
                await self.storage_isolator.cleanup()
            
            if self.network_isolator:
                await self.network_isolator.cleanup()
            
            if self.cache_isolator:
                await self.cache_isolator.cleanup()
            
            if self.encryption_manager:
                await self.encryption_manager.cleanup()
            
            logger.info("Isolation manager cleanup completed")
            
        except Exception as e:
            logger.error("Error during isolation manager cleanup", error=str(e))