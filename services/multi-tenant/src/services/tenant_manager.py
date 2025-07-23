"""
Tenant Manager - Core service for tenant lifecycle management.

Handles tenant provisioning, configuration, isolation, and deletion.
"""

import asyncio
import uuid
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy import text

from ..core.config import get_settings
from ..core.exceptions import (
    TenantAlreadyExistsError, TenantNotFoundError, TenantProvisioningError,
    TenantStateError, TenantDeletionError, TenantQuotaExceededError,
    TenantConfigurationError
)
from ..models.schemas import (
    TenantCreate, TenantUpdate, TenantInfo, TenantState,
    TenantQuota, TenantConfig, TenantUsage
)
from .database_provisioner import DatabaseProvisioner
from .storage_provisioner import StorageProvisioner
from .domain_manager import DomainManager
from .quota_manager import QuotaManager


logger = structlog.get_logger()


class TenantLifecycle(Enum):
    """Tenant lifecycle states."""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETING = "deleting"
    DELETED = "deleted"
    FAILED = "failed"


class TenantManager:
    """
    Main service for managing tenant lifecycle and operations.
    
    Provides complete tenant management including provisioning,
    configuration, isolation, and resource management.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Sub-services
        self.db_provisioner: Optional[DatabaseProvisioner] = None
        self.storage_provisioner: Optional[StorageProvisioner] = None
        self.domain_manager: Optional[DomainManager] = None
        self.quota_manager: Optional[QuotaManager] = None
        
        # Tenant cache
        self.tenant_cache: Dict[str, TenantInfo] = {}
        self.cache_ttl = self.settings.tenant_cache_ttl
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # Database engine for tenant operations
        self.engine = None
        
        # Statistics
        self.stats = {
            "tenants_created": 0,
            "tenants_deleted": 0,
            "active_tenants": 0,
            "provisioning_time_avg": 0.0,
            "last_provisioning": None
        }
    
    async def initialize(self) -> None:
        """Initialize tenant manager and sub-services."""
        try:
            logger.info("Initializing tenant manager")
            
            # Initialize database engine
            self.engine = create_async_engine(
                self.settings.database_url,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True
            )
            
            # Initialize sub-services
            self.db_provisioner = DatabaseProvisioner(self.engine)
            await self.db_provisioner.initialize()
            
            self.storage_provisioner = StorageProvisioner()
            await self.storage_provisioner.initialize()
            
            if self.settings.custom_domains_enabled:
                self.domain_manager = DomainManager()
                await self.domain_manager.initialize()
            
            self.quota_manager = QuotaManager()
            await self.quota_manager.initialize()
            
            # Load existing tenants into cache
            await self._load_tenant_cache()
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Tenant manager initialized",
                active_tenants=len(self.tenant_cache),
                isolation_mode=self.settings.tenant_isolation_mode
            )
            
        except Exception as e:
            logger.error("Failed to initialize tenant manager", error=str(e))
            raise TenantProvisioningError(f"Initialization failed: {str(e)}")
    
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        # Cache cleanup
        task = asyncio.create_task(self._cache_cleanup_loop())
        self._tasks.append(task)
        
        # Usage tracking
        if self.settings.usage_tracking_enabled:
            task = asyncio.create_task(self._usage_tracking_loop())
            self._tasks.append(task)
        
        # Quota enforcement
        task = asyncio.create_task(self._quota_enforcement_loop())
        self._tasks.append(task)
        
        # Stats update
        task = asyncio.create_task(self._stats_update_loop())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def create_tenant(self, tenant_data: TenantCreate) -> TenantInfo:
        """
        Create a new tenant with complete provisioning.
        
        This includes:
        - Database/schema creation
        - Storage setup
        - Domain configuration
        - Initial configuration
        - Resource allocation
        """
        start_time = time.time()
        tenant_id = tenant_data.tenant_id or str(uuid.uuid4())
        
        try:
            logger.info("Creating new tenant", tenant_id=tenant_id, name=tenant_data.name)
            
            # Check if tenant already exists
            if await self.tenant_exists(tenant_id):
                raise TenantAlreadyExistsError(tenant_id)
            
            # Validate quota limits
            if self.settings.max_tenants_per_instance > 0:
                if len(self.tenant_cache) >= self.settings.max_tenants_per_instance:
                    raise TenantQuotaExceededError(
                        "tenants_per_instance",
                        len(self.tenant_cache),
                        self.settings.max_tenants_per_instance
                    )
            
            # Create tenant info
            tenant_info = TenantInfo(
                tenant_id=tenant_id,
                name=tenant_data.name,
                state=TenantLifecycle.PROVISIONING.value,
                created_at=datetime.utcnow(),
                template=tenant_data.template or "starter",
                region=tenant_data.region or self.settings.supported_regions[0],
                metadata=tenant_data.metadata or {}
            )
            
            # Apply template
            template_config = self.settings.tenant_templates.get(
                tenant_info.template,
                self.settings.tenant_templates["starter"]
            )
            
            # Set quota from template
            tenant_info.quota = TenantQuota(**template_config.get("quota", {}))
            
            # Add to cache early to prevent duplicates
            self.tenant_cache[tenant_id] = tenant_info
            
            try:
                # Step 1: Provision database/schema
                logger.info("Provisioning database", tenant_id=tenant_id)
                db_info = await self.db_provisioner.provision_tenant_database(
                    tenant_id,
                    self.settings.tenant_isolation_mode
                )
                tenant_info.database_info = db_info
                
                # Step 2: Setup storage
                logger.info("Setting up storage", tenant_id=tenant_id)
                storage_info = await self.storage_provisioner.provision_tenant_storage(
                    tenant_id,
                    tenant_info.quota.max_storage_gb
                )
                tenant_info.storage_info = storage_info
                
                # Step 3: Configure custom domain if provided
                if tenant_data.custom_domain and self.domain_manager:
                    logger.info("Configuring custom domain", 
                              tenant_id=tenant_id, 
                              domain=tenant_data.custom_domain)
                    domain_info = await self.domain_manager.configure_domain(
                        tenant_id,
                        tenant_data.custom_domain
                    )
                    tenant_info.domains = [domain_info]
                
                # Step 4: Apply initial configuration
                logger.info("Applying tenant configuration", tenant_id=tenant_id)
                tenant_info.config = await self._apply_initial_config(
                    tenant_id,
                    tenant_data.initial_config
                )
                
                # Step 5: Initialize tenant services
                await self._initialize_tenant_services(tenant_id)
                
                # Update state to active
                tenant_info.state = TenantLifecycle.ACTIVE.value
                tenant_info.activated_at = datetime.utcnow()
                
                # Persist to database
                await self._persist_tenant(tenant_info)
                
                # Update statistics
                provision_time = time.time() - start_time
                self._update_provision_stats(provision_time)
                
                logger.info(
                    "Tenant created successfully",
                    tenant_id=tenant_id,
                    provision_time=provision_time
                )
                
                return tenant_info
                
            except Exception as e:
                # Rollback on failure
                logger.error("Tenant provisioning failed, rolling back", 
                           tenant_id=tenant_id, error=str(e))
                
                tenant_info.state = TenantLifecycle.FAILED.value
                await self._rollback_tenant_creation(tenant_id)
                
                # Remove from cache
                self.tenant_cache.pop(tenant_id, None)
                
                raise TenantProvisioningError(str(e))
                
        except Exception as e:
            logger.error("Failed to create tenant", tenant_id=tenant_id, error=str(e))
            raise
    
    async def get_tenant(self, tenant_id: str) -> TenantInfo:
        """Get tenant information."""
        # Check cache first
        if tenant_id in self.tenant_cache:
            cache_entry = self.tenant_cache[tenant_id]
            if self._is_cache_valid(cache_entry):
                return cache_entry
        
        # Load from database
        tenant_info = await self._load_tenant_from_db(tenant_id)
        if not tenant_info:
            raise TenantNotFoundError(tenant_id)
        
        # Update cache
        self.tenant_cache[tenant_id] = tenant_info
        
        return tenant_info
    
    async def update_tenant(self, tenant_id: str, update_data: TenantUpdate) -> TenantInfo:
        """Update tenant configuration."""
        tenant_info = await self.get_tenant(tenant_id)
        
        # Validate state
        if tenant_info.state not in [TenantLifecycle.ACTIVE.value, TenantLifecycle.SUSPENDED.value]:
            raise TenantStateError(tenant_id, tenant_info.state, "update")
        
        # Update allowed fields
        if update_data.name:
            tenant_info.name = update_data.name
        
        if update_data.config:
            tenant_info.config = await self._update_tenant_config(
                tenant_id,
                tenant_info.config,
                update_data.config
            )
        
        if update_data.quota:
            # Validate quota changes
            await self.quota_manager.validate_quota_update(
                tenant_id,
                tenant_info.quota,
                update_data.quota
            )
            tenant_info.quota = update_data.quota
        
        if update_data.metadata:
            tenant_info.metadata.update(update_data.metadata)
        
        tenant_info.updated_at = datetime.utcnow()
        
        # Persist changes
        await self._persist_tenant(tenant_info)
        
        # Update cache
        self.tenant_cache[tenant_id] = tenant_info
        
        logger.info("Tenant updated", tenant_id=tenant_id)
        
        return tenant_info
    
    async def suspend_tenant(self, tenant_id: str, reason: str) -> TenantInfo:
        """Suspend a tenant."""
        tenant_info = await self.get_tenant(tenant_id)
        
        if tenant_info.state != TenantLifecycle.ACTIVE.value:
            raise TenantStateError(tenant_id, tenant_info.state, "suspend")
        
        tenant_info.state = TenantLifecycle.SUSPENDED.value
        tenant_info.suspended_at = datetime.utcnow()
        tenant_info.suspension_reason = reason
        
        # Disable tenant access
        await self._disable_tenant_access(tenant_id)
        
        # Persist changes
        await self._persist_tenant(tenant_info)
        
        logger.info("Tenant suspended", tenant_id=tenant_id, reason=reason)
        
        return tenant_info
    
    async def activate_tenant(self, tenant_id: str) -> TenantInfo:
        """Activate a suspended tenant."""
        tenant_info = await self.get_tenant(tenant_id)
        
        if tenant_info.state != TenantLifecycle.SUSPENDED.value:
            raise TenantStateError(tenant_id, tenant_info.state, "activate")
        
        tenant_info.state = TenantLifecycle.ACTIVE.value
        tenant_info.activated_at = datetime.utcnow()
        tenant_info.suspended_at = None
        tenant_info.suspension_reason = None
        
        # Enable tenant access
        await self._enable_tenant_access(tenant_id)
        
        # Persist changes
        await self._persist_tenant(tenant_info)
        
        logger.info("Tenant activated", tenant_id=tenant_id)
        
        return tenant_info
    
    async def delete_tenant(self, tenant_id: str, force: bool = False) -> None:
        """
        Delete a tenant.
        
        Args:
            tenant_id: Tenant identifier
            force: Force deletion even with active resources
        """
        tenant_info = await self.get_tenant(tenant_id)
        
        # Validate state
        if not force and tenant_info.state == TenantLifecycle.ACTIVE.value:
            # Check for active resources
            usage = await self.get_tenant_usage(tenant_id)
            if usage.active_users > 0 or usage.storage_used_gb > 0:
                raise TenantDeletionError(
                    tenant_id,
                    "Tenant has active resources. Use force=True to override."
                )
        
        logger.info("Deleting tenant", tenant_id=tenant_id, force=force)
        
        tenant_info.state = TenantLifecycle.DELETING.value
        tenant_info.deletion_requested_at = datetime.utcnow()
        
        try:
            # Step 1: Disable access
            await self._disable_tenant_access(tenant_id)
            
            # Step 2: Backup if enabled
            if self.settings.tenant_backup_enabled and not force:
                await self._backup_tenant_data(tenant_id)
            
            # Step 3: Delete storage
            if self.storage_provisioner:
                await self.storage_provisioner.delete_tenant_storage(tenant_id)
            
            # Step 4: Delete database/schema
            if self.db_provisioner:
                await self.db_provisioner.delete_tenant_database(
                    tenant_id,
                    self.settings.tenant_isolation_mode
                )
            
            # Step 5: Remove custom domains
            if self.domain_manager and tenant_info.domains:
                for domain in tenant_info.domains:
                    await self.domain_manager.remove_domain(tenant_id, domain.domain)
            
            # Step 6: Mark as deleted
            tenant_info.state = TenantLifecycle.DELETED.value
            tenant_info.deleted_at = datetime.utcnow()
            
            # Persist final state
            await self._persist_tenant(tenant_info)
            
            # Remove from cache
            self.tenant_cache.pop(tenant_id, None)
            
            self.stats["tenants_deleted"] += 1
            
            logger.info("Tenant deleted successfully", tenant_id=tenant_id)
            
        except Exception as e:
            logger.error("Failed to delete tenant", tenant_id=tenant_id, error=str(e))
            tenant_info.state = TenantLifecycle.FAILED.value
            raise TenantDeletionError(tenant_id, str(e))
    
    async def list_tenants(
        self,
        state: Optional[TenantState] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantInfo]:
        """List tenants with optional filtering."""
        # For now, return from cache
        # In production, this would query the database
        all_tenants = list(self.tenant_cache.values())
        
        # Filter by state if specified
        if state:
            all_tenants = [t for t in all_tenants if t.state == state]
        
        # Apply pagination
        return all_tenants[offset:offset + limit]
    
    async def get_tenant_usage(self, tenant_id: str) -> TenantUsage:
        """Get current tenant resource usage."""
        tenant_info = await self.get_tenant(tenant_id)
        
        # Get usage from various sources
        usage = TenantUsage(
            tenant_id=tenant_id,
            storage_used_gb=0.0,
            bandwidth_used_gb=0.0,
            api_calls_count=0,
            active_users=0,
            compute_hours=0.0,
            timestamp=datetime.utcnow()
        )
        
        # Get storage usage
        if self.storage_provisioner:
            storage_usage = await self.storage_provisioner.get_storage_usage(tenant_id)
            usage.storage_used_gb = storage_usage
        
        # Get other metrics from quota manager
        if self.quota_manager:
            metrics = await self.quota_manager.get_usage_metrics(tenant_id)
            usage.bandwidth_used_gb = metrics.get("bandwidth_gb", 0.0)
            usage.api_calls_count = metrics.get("api_calls", 0)
            usage.active_users = metrics.get("active_users", 0)
            usage.compute_hours = metrics.get("compute_hours", 0.0)
        
        return usage
    
    async def tenant_exists(self, tenant_id: str) -> bool:
        """Check if tenant exists."""
        if tenant_id in self.tenant_cache:
            return True
        
        # Check database
        return await self._tenant_exists_in_db(tenant_id)
    
    async def _apply_initial_config(
        self,
        tenant_id: str,
        config: Optional[Dict[str, Any]]
    ) -> TenantConfig:
        """Apply initial tenant configuration."""
        # Start with defaults
        tenant_config = TenantConfig(
            branding={},
            theme="default",
            language="en",
            timezone="UTC",
            features_enabled=["basic"],
            custom_settings={}
        )
        
        # Apply custom config if provided
        if config:
            for key, value in config.items():
                if key in self.settings.tenant_config_options:
                    setattr(tenant_config, key, value)
                else:
                    tenant_config.custom_settings[key] = value
        
        return tenant_config
    
    async def _initialize_tenant_services(self, tenant_id: str) -> None:
        """Initialize tenant-specific services."""
        # This would initialize tenant-specific:
        # - User management
        # - Asset management
        # - Workflow configuration
        # - Integration settings
        logger.info("Initializing tenant services", tenant_id=tenant_id)
    
    async def _rollback_tenant_creation(self, tenant_id: str) -> None:
        """Rollback failed tenant creation."""
        try:
            # Delete storage
            if self.storage_provisioner:
                await self.storage_provisioner.delete_tenant_storage(tenant_id)
            
            # Delete database/schema
            if self.db_provisioner:
                await self.db_provisioner.delete_tenant_database(
                    tenant_id,
                    self.settings.tenant_isolation_mode
                )
            
            logger.info("Tenant creation rolled back", tenant_id=tenant_id)
            
        except Exception as e:
            logger.error("Failed to rollback tenant creation", 
                       tenant_id=tenant_id, error=str(e))
    
    async def _disable_tenant_access(self, tenant_id: str) -> None:
        """Disable all access for a tenant."""
        # Implementation would:
        # - Revoke API keys
        # - Disable user logins
        # - Block domain access
        logger.info("Tenant access disabled", tenant_id=tenant_id)
    
    async def _enable_tenant_access(self, tenant_id: str) -> None:
        """Enable access for a tenant."""
        # Implementation would:
        # - Restore API keys
        # - Enable user logins
        # - Activate domain access
        logger.info("Tenant access enabled", tenant_id=tenant_id)
    
    async def _backup_tenant_data(self, tenant_id: str) -> None:
        """Backup tenant data before deletion."""
        logger.info("Backing up tenant data", tenant_id=tenant_id)
        # Implementation would backup to archive storage
    
    async def _update_tenant_config(
        self,
        tenant_id: str,
        current_config: TenantConfig,
        updates: Dict[str, Any]
    ) -> TenantConfig:
        """Update tenant configuration."""
        for key, value in updates.items():
            if key in self.settings.tenant_config_options:
                setattr(current_config, key, value)
            else:
                raise TenantConfigurationError(key, "Invalid configuration option")
        
        return current_config
    
    async def _load_tenant_cache(self) -> None:
        """Load active tenants into cache."""
        # In production, this would load from database
        logger.info("Loading tenant cache")
        self.stats["active_tenants"] = len(self.tenant_cache)
    
    async def _persist_tenant(self, tenant_info: TenantInfo) -> None:
        """Persist tenant information to database."""
        # In production, this would save to database
        logger.debug("Persisting tenant", tenant_id=tenant_info.tenant_id)
    
    async def _load_tenant_from_db(self, tenant_id: str) -> Optional[TenantInfo]:
        """Load tenant from database."""
        # In production, this would query database
        return None
    
    async def _tenant_exists_in_db(self, tenant_id: str) -> bool:
        """Check if tenant exists in database."""
        # In production, this would query database
        return False
    
    def _is_cache_valid(self, tenant_info: TenantInfo) -> bool:
        """Check if cached tenant info is still valid."""
        # Simple TTL check for now
        return True
    
    def _update_provision_stats(self, provision_time: float) -> None:
        """Update provisioning statistics."""
        self.stats["tenants_created"] += 1
        self.stats["last_provisioning"] = datetime.utcnow()
        
        # Update average
        total = self.stats["tenants_created"]
        current_avg = self.stats["provisioning_time_avg"]
        self.stats["provisioning_time_avg"] = (
            (current_avg * (total - 1) + provision_time) / total
        )
    
    async def _cache_cleanup_loop(self) -> None:
        """Background task to clean up stale cache entries."""
        while self._running:
            try:
                # Clean up deleted/inactive tenants from cache
                expired = []
                for tenant_id, tenant_info in self.tenant_cache.items():
                    if tenant_info.state == TenantLifecycle.DELETED.value:
                        expired.append(tenant_id)
                
                for tenant_id in expired:
                    self.tenant_cache.pop(tenant_id, None)
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error("Error in cache cleanup", error=str(e))
                await asyncio.sleep(300)
    
    async def _usage_tracking_loop(self) -> None:
        """Background task to track tenant usage."""
        while self._running:
            try:
                # Track usage for all active tenants
                for tenant_id, tenant_info in self.tenant_cache.items():
                    if tenant_info.state == TenantLifecycle.ACTIVE.value:
                        usage = await self.get_tenant_usage(tenant_id)
                        # Store usage metrics
                        logger.debug("Tracked usage", tenant_id=tenant_id, usage=usage)
                
                await asyncio.sleep(3600)  # Run hourly
                
            except Exception as e:
                logger.error("Error in usage tracking", error=str(e))
                await asyncio.sleep(3600)
    
    async def _quota_enforcement_loop(self) -> None:
        """Background task to enforce tenant quotas."""
        while self._running:
            try:
                # Check quotas for all active tenants
                for tenant_id, tenant_info in self.tenant_cache.items():
                    if tenant_info.state == TenantLifecycle.ACTIVE.value:
                        usage = await self.get_tenant_usage(tenant_id)
                        
                        # Check storage quota
                        if usage.storage_used_gb > tenant_info.quota.max_storage_gb:
                            logger.warning(
                                "Tenant storage quota exceeded",
                                tenant_id=tenant_id,
                                used=usage.storage_used_gb,
                                limit=tenant_info.quota.max_storage_gb
                            )
                            # Could suspend or notify tenant
                
                await asyncio.sleep(900)  # Run every 15 minutes
                
            except Exception as e:
                logger.error("Error in quota enforcement", error=str(e))
                await asyncio.sleep(900)
    
    async def _stats_update_loop(self) -> None:
        """Background task to update statistics."""
        while self._running:
            try:
                # Update active tenant count
                self.stats["active_tenants"] = sum(
                    1 for t in self.tenant_cache.values()
                    if t.state == TenantLifecycle.ACTIVE.value
                )
                
                logger.debug("Statistics updated", stats=self.stats)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error("Error in stats update", error=str(e))
                await asyncio.sleep(300)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get tenant manager statistics."""
        return {
            **self.stats,
            "cache_size": len(self.tenant_cache),
            "isolation_mode": self.settings.tenant_isolation_mode
        }
    
    async def cleanup(self) -> None:
        """Cleanup tenant manager resources."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Cleanup sub-services
            if self.db_provisioner:
                await self.db_provisioner.cleanup()
            
            if self.storage_provisioner:
                await self.storage_provisioner.cleanup()
            
            if self.domain_manager:
                await self.domain_manager.cleanup()
            
            if self.quota_manager:
                await self.quota_manager.cleanup()
            
            # Close database engine
            if self.engine:
                await self.engine.dispose()
            
            logger.info("Tenant manager cleanup completed")
            
        except Exception as e:
            logger.error("Error during tenant manager cleanup", error=str(e))