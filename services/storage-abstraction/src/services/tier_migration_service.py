"""
Storage Tier Migration Service

This module handles automatic and manual migration of files between storage tiers
based on age, access patterns, and policies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageTier,
    ObjectNotFoundError, InvalidStorageOperationError,
    StorageOperationError
)
from ..core.config import get_settings


logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MigrationPolicy:
    """Defines rules for automatic tier migration"""
    name: str
    description: str
    enabled: bool = True
    
    # Age-based rules (in days)
    hot_to_warm_days: Optional[int] = None
    warm_to_cold_days: Optional[int] = None
    cold_to_archive_days: Optional[int] = None
    
    # Access-based rules
    access_count_threshold: Optional[int] = None
    last_access_days: Optional[int] = None
    
    # Size-based rules
    min_file_size: Optional[int] = None
    max_file_size: Optional[int] = None
    
    # Pattern-based rules
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    # Time restrictions
    migration_window_start: Optional[str] = None  # HH:MM format
    migration_window_end: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "hot_to_warm_days": self.hot_to_warm_days,
            "warm_to_cold_days": self.warm_to_cold_days,
            "cold_to_archive_days": self.cold_to_archive_days,
            "access_count_threshold": self.access_count_threshold,
            "last_access_days": self.last_access_days,
            "min_file_size": self.min_file_size,
            "max_file_size": self.max_file_size,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "migration_window_start": self.migration_window_start,
            "migration_window_end": self.migration_window_end
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationPolicy':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class MigrationTask:
    """Represents a single migration task"""
    task_id: str
    object_key: str
    source_tier: StorageTier
    target_tier: StorageTier
    source_driver: str
    target_driver: Optional[str] = None
    status: MigrationStatus = MigrationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "object_key": self.object_key,
            "source_tier": self.source_tier.value,
            "target_tier": self.target_tier.value,
            "source_driver": self.source_driver,
            "target_driver": self.target_driver,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


@dataclass
class MigrationStats:
    """Migration statistics"""
    total_objects: int = 0
    total_bytes: int = 0
    migrated_objects: int = 0
    migrated_bytes: int = 0
    failed_objects: int = 0
    avg_migration_time: float = 0.0
    tier_distribution: Dict[str, int] = field(default_factory=dict)


class TierMigrationService:
    """Service for managing storage tier migrations"""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        self.settings = get_settings()
        
        # Migration configuration
        self._policies: Dict[str, MigrationPolicy] = {}
        self._active_tasks: Dict[str, MigrationTask] = {}
        self._migration_history: List[MigrationTask] = []
        self._migration_lock = asyncio.Lock()
        
        # Background task
        self._migration_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Default policies from settings
        self._load_default_policies()
    
    def _load_default_policies(self) -> None:
        """Load default migration policies from settings"""
        if self.settings.enable_storage_tiers:
            # Age-based policy
            age_policy = MigrationPolicy(
                name="age_based_migration",
                description="Migrate files based on age",
                hot_to_warm_days=self.settings.hot_tier_days,
                warm_to_cold_days=self.settings.warm_tier_days,
                cold_to_archive_days=self.settings.cold_tier_days
            )
            self._policies[age_policy.name] = age_policy
            
            # Access-based policy
            access_policy = MigrationPolicy(
                name="access_based_migration",
                description="Migrate files based on access patterns",
                last_access_days=90,
                access_count_threshold=5
            )
            self._policies[access_policy.name] = access_policy
    
    async def initialize(self) -> None:
        """Initialize the tier migration service"""
        logger.info("Initializing tier migration service")
        
        # Start background migration task
        if self.settings.enable_storage_tiers:
            self._migration_task = asyncio.create_task(self._migration_worker())
    
    async def shutdown(self) -> None:
        """Shutdown the tier migration service"""
        logger.info("Shutting down tier migration service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel migration task
        if self._migration_task:
            self._migration_task.cancel()
            try:
                await self._migration_task
            except asyncio.CancelledError:
                pass
    
    async def migrate_object(
        self,
        key: str,
        target_tier: StorageTier,
        source_driver: Optional[str] = None,
        target_driver: Optional[str] = None,
        force: bool = False
    ) -> MigrationTask:
        """Manually migrate a single object to a different tier"""
        async with self._migration_lock:
            try:
                # Get object info
                driver = self.storage_service.get_driver(source_driver)
                obj_info = await driver.get_object_info(key)
                
                # Determine current tier
                current_tier = self._get_tier_from_storage_class(obj_info.storage_class)
                
                # Check if migration is needed
                if current_tier == target_tier and not force:
                    raise InvalidStorageOperationError(
                        f"Object {key} is already in {target_tier.value} tier"
                    )
                
                # Create migration task
                import hashlib
                task_id = hashlib.md5(f"{key}:{datetime.utcnow().isoformat()}".encode()).hexdigest()
                
                task = MigrationTask(
                    task_id=task_id,
                    object_key=key,
                    source_tier=current_tier,
                    target_tier=target_tier,
                    source_driver=source_driver or self.storage_service._default_driver,
                    target_driver=target_driver
                )
                
                self._active_tasks[task_id] = task
                
                # Execute migration
                await self._execute_migration(task)
                
                return task
                
            except Exception as e:
                logger.error(f"Failed to migrate object {key}: {e}")
                raise
    
    async def migrate_objects_batch(
        self,
        keys: List[str],
        target_tier: StorageTier,
        source_driver: Optional[str] = None,
        target_driver: Optional[str] = None
    ) -> List[MigrationTask]:
        """Migrate multiple objects to a different tier"""
        tasks = []
        
        for key in keys:
            try:
                task = await self.migrate_object(
                    key, target_tier, source_driver, target_driver
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to migrate {key}: {e}")
        
        return tasks
    
    async def apply_policy(
        self,
        policy_name: str,
        driver_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Tuple[List[str], MigrationStats]:
        """Apply a migration policy to find and migrate eligible objects"""
        if policy_name not in self._policies:
            raise InvalidStorageOperationError(f"Policy not found: {policy_name}")
        
        policy = self._policies[policy_name]
        if not policy.enabled:
            raise InvalidStorageOperationError(f"Policy is disabled: {policy_name}")
        
        # Check migration window
        if not self._in_migration_window(policy):
            logger.info(f"Outside migration window for policy {policy_name}")
            return [], MigrationStats()
        
        # Find eligible objects
        eligible_objects = await self._find_eligible_objects(policy, driver_name)
        
        stats = MigrationStats(total_objects=len(eligible_objects))
        
        if dry_run:
            return eligible_objects, stats
        
        # Execute migrations
        for obj_key, current_tier, target_tier in eligible_objects:
            try:
                await self.migrate_object(
                    obj_key, target_tier, driver_name
                )
                stats.migrated_objects += 1
            except Exception as e:
                logger.error(f"Failed to migrate {obj_key}: {e}")
                stats.failed_objects += 1
        
        return eligible_objects, stats
    
    async def get_migration_status(self, task_id: str) -> Optional[MigrationTask]:
        """Get status of a migration task"""
        # Check active tasks
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        
        # Check history
        for task in self._migration_history:
            if task.task_id == task_id:
                return task
        
        return None
    
    async def get_migration_stats(
        self,
        driver_name: Optional[str] = None
    ) -> MigrationStats:
        """Get migration statistics"""
        stats = MigrationStats()
        
        # Get all objects
        driver = self.storage_service.get_driver(driver_name)
        objects, _ = await driver.list_objects(max_keys=10000)
        
        stats.total_objects = len(objects)
        
        # Calculate tier distribution
        for obj in objects:
            stats.total_bytes += obj.size
            tier = self._get_tier_from_storage_class(obj.storage_class)
            tier_name = tier.value if tier else "unknown"
            stats.tier_distribution[tier_name] = stats.tier_distribution.get(tier_name, 0) + 1
        
        # Add migration history stats
        for task in self._migration_history:
            if task.status == MigrationStatus.COMPLETED:
                stats.migrated_objects += 1
            elif task.status == MigrationStatus.FAILED:
                stats.failed_objects += 1
        
        return stats
    
    def add_policy(self, policy: MigrationPolicy) -> None:
        """Add a new migration policy"""
        self._policies[policy.name] = policy
    
    def remove_policy(self, policy_name: str) -> None:
        """Remove a migration policy"""
        if policy_name in self._policies:
            del self._policies[policy_name]
    
    def get_policies(self) -> Dict[str, MigrationPolicy]:
        """Get all migration policies"""
        return self._policies.copy()
    
    async def _execute_migration(self, task: MigrationTask) -> None:
        """Execute a single migration task"""
        task.status = MigrationStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        
        try:
            # Get source driver
            source_driver = self.storage_service.get_driver(task.source_driver)
            
            # For same-driver tier changes
            if not task.target_driver or task.target_driver == task.source_driver:
                # Use native tier change if supported
                obj = await source_driver.change_storage_tier(
                    task.object_key,
                    task.target_tier
                )
                
                task.status = MigrationStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                
            else:
                # Cross-driver migration
                target_driver = self.storage_service.get_driver(task.target_driver)
                
                # Copy object
                await self.storage_service.copy_object(
                    task.object_key,
                    task.object_key,
                    None,
                    task.source_driver,
                    task.target_driver
                )
                
                # Change tier on target
                await target_driver.change_storage_tier(
                    task.object_key,
                    task.target_tier
                )
                
                # Delete from source
                await source_driver.delete_object(task.object_key)
                
                task.status = MigrationStatus.COMPLETED
                task.completed_at = datetime.utcnow()
            
            logger.info(
                f"Successfully migrated {task.object_key} from "
                f"{task.source_tier.value} to {task.target_tier.value}"
            )
            
        except Exception as e:
            logger.error(f"Migration failed for {task.object_key}: {e}")
            task.status = MigrationStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            
            # Retry if under limit
            if task.retry_count < task.max_retries:
                task.status = MigrationStatus.PENDING
                logger.info(f"Will retry migration for {task.object_key}")
        
        finally:
            # Move to history
            if task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]
            self._migration_history.append(task)
            
            # Keep history limited
            if len(self._migration_history) > 1000:
                self._migration_history = self._migration_history[-1000:]
    
    async def _find_eligible_objects(
        self,
        policy: MigrationPolicy,
        driver_name: Optional[str] = None
    ) -> List[Tuple[str, StorageTier, StorageTier]]:
        """Find objects eligible for migration based on policy"""
        eligible = []
        driver = self.storage_service.get_driver(driver_name)
        
        # List all objects
        objects, _ = await driver.list_objects(max_keys=10000)
        
        for obj in objects:
            current_tier = self._get_tier_from_storage_class(obj.storage_class)
            target_tier = None
            
            # Check age-based rules
            if policy.hot_to_warm_days and current_tier == StorageTier.HOT:
                age_days = (datetime.utcnow() - obj.last_modified).days
                if age_days >= policy.hot_to_warm_days:
                    target_tier = StorageTier.WARM
            
            elif policy.warm_to_cold_days and current_tier == StorageTier.WARM:
                age_days = (datetime.utcnow() - obj.last_modified).days
                if age_days >= policy.warm_to_cold_days:
                    target_tier = StorageTier.COLD
            
            elif policy.cold_to_archive_days and current_tier == StorageTier.COLD:
                age_days = (datetime.utcnow() - obj.last_modified).days
                if age_days >= policy.cold_to_archive_days:
                    target_tier = StorageTier.ARCHIVE
            
            # Check size-based rules
            if target_tier and policy.min_file_size and obj.size < policy.min_file_size:
                target_tier = None
            
            if target_tier and policy.max_file_size and obj.size > policy.max_file_size:
                target_tier = None
            
            # Check pattern-based rules
            if target_tier and policy.include_patterns:
                import fnmatch
                if not any(fnmatch.fnmatch(obj.key, pattern) for pattern in policy.include_patterns):
                    target_tier = None
            
            if target_tier and policy.exclude_patterns:
                import fnmatch
                if any(fnmatch.fnmatch(obj.key, pattern) for pattern in policy.exclude_patterns):
                    target_tier = None
            
            if target_tier:
                eligible.append((obj.key, current_tier, target_tier))
        
        return eligible
    
    def _get_tier_from_storage_class(self, storage_class: Optional[str]) -> StorageTier:
        """Convert storage class string to StorageTier enum"""
        if not storage_class:
            return StorageTier.HOT
        
        storage_class_lower = storage_class.lower()
        
        # Map common storage class names
        tier_mapping = {
            "hot": StorageTier.HOT,
            "standard": StorageTier.HOT,
            "warm": StorageTier.WARM,
            "nearline": StorageTier.WARM,
            "cool": StorageTier.WARM,
            "cold": StorageTier.COLD,
            "coldline": StorageTier.COLD,
            "archive": StorageTier.ARCHIVE,
            "glacier": StorageTier.ARCHIVE,
            "deep_archive": StorageTier.ARCHIVE
        }
        
        for key, tier in tier_mapping.items():
            if key in storage_class_lower:
                return tier
        
        return StorageTier.HOT
    
    def _in_migration_window(self, policy: MigrationPolicy) -> bool:
        """Check if current time is within migration window"""
        if not policy.migration_window_start or not policy.migration_window_end:
            return True
        
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")
        
        return (policy.migration_window_start <= current_time <= policy.migration_window_end)
    
    async def _migration_worker(self) -> None:
        """Background worker for automatic migrations"""
        logger.info("Starting migration worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Run migrations every hour
                await asyncio.sleep(3600)
                
                # Apply enabled policies
                for policy_name, policy in self._policies.items():
                    if policy.enabled:
                        try:
                            await self.apply_policy(policy_name)
                        except Exception as e:
                            logger.error(f"Failed to apply policy {policy_name}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Migration worker error: {e}")
                await asyncio.sleep(60)  # Wait before retry
        
        logger.info("Migration worker stopped")


# Global instance
_migration_service: Optional[TierMigrationService] = None


async def get_migration_service(storage_service) -> TierMigrationService:
    """Get or create migration service instance"""
    global _migration_service
    
    if _migration_service is None:
        _migration_service = TierMigrationService(storage_service)
        await _migration_service.initialize()
    
    return _migration_service


async def close_migration_service() -> None:
    """Close migration service"""
    global _migration_service
    
    if _migration_service is not None:
        await _migration_service.shutdown()
        _migration_service = None