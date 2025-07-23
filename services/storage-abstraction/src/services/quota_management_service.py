"""
Storage Quota Management Service

This module handles storage quota tracking, enforcement, and alerts for users,
groups, and organizations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota,
    StorageQuotaExceededError, InvalidStorageOperationError,
    StorageOperationError
)
from ..core.config import get_settings


logger = logging.getLogger(__name__)


class QuotaType(Enum):
    """Types of quotas"""
    USER = "user"
    GROUP = "group"
    ORGANIZATION = "organization"
    DRIVER = "driver"
    GLOBAL = "global"


class QuotaAction(Enum):
    """Actions to take when quota is exceeded"""
    BLOCK = "block"
    WARN = "warn"
    ALERT = "alert"


@dataclass
class QuotaPolicy:
    """Defines a quota policy"""
    id: str
    name: str
    description: str
    quota_type: QuotaType
    entity_id: str  # User ID, Group ID, etc.
    
    # Quota limits
    max_storage_bytes: Optional[int] = None
    max_file_count: Optional[int] = None
    max_file_size: Optional[int] = None
    
    # Actions
    soft_limit_percentage: float = 0.8  # Warn at 80%
    hard_limit_percentage: float = 1.0  # Block at 100%
    action_on_soft_limit: QuotaAction = QuotaAction.WARN
    action_on_hard_limit: QuotaAction = QuotaAction.BLOCK
    
    # Additional settings
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Driver-specific quotas
    driver_quotas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quota_type": self.quota_type.value,
            "entity_id": self.entity_id,
            "max_storage_bytes": self.max_storage_bytes,
            "max_file_count": self.max_file_count,
            "max_file_size": self.max_file_size,
            "soft_limit_percentage": self.soft_limit_percentage,
            "hard_limit_percentage": self.hard_limit_percentage,
            "action_on_soft_limit": self.action_on_soft_limit.value,
            "action_on_hard_limit": self.action_on_hard_limit.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "driver_quotas": self.driver_quotas
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuotaPolicy':
        """Create from dictionary"""
        data = data.copy()
        data['quota_type'] = QuotaType(data['quota_type'])
        data['action_on_soft_limit'] = QuotaAction(data['action_on_soft_limit'])
        data['action_on_hard_limit'] = QuotaAction(data['action_on_hard_limit'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class QuotaUsage:
    """Current quota usage"""
    policy_id: str
    entity_id: str
    used_storage_bytes: int = 0
    used_file_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Driver-specific usage
    driver_usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "policy_id": self.policy_id,
            "entity_id": self.entity_id,
            "used_storage_bytes": self.used_storage_bytes,
            "used_file_count": self.used_file_count,
            "last_updated": self.last_updated.isoformat(),
            "driver_usage": self.driver_usage
        }


@dataclass
class QuotaAlert:
    """Quota alert/warning"""
    id: str
    policy_id: str
    entity_id: str
    alert_type: QuotaAction
    message: str
    threshold_percentage: float
    current_usage_bytes: int
    max_allowed_bytes: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


class QuotaManagementService:
    """Service for managing storage quotas"""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        self.settings = get_settings()
        
        # Quota storage
        self._policies: Dict[str, QuotaPolicy] = {}
        self._usage: Dict[str, QuotaUsage] = {}
        self._alerts: List[QuotaAlert] = []
        self._quota_cache: Dict[str, Dict[str, Any]] = {}
        
        # Persistence
        self._data_dir = Path(self.settings.temp_directory) / "quotas"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._usage_update_task: Optional[asyncio.Task] = None
        self._alert_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Default quotas
        self._load_default_quotas()
    
    def _load_default_quotas(self) -> None:
        """Load default quota policies from settings"""
        if self.settings.enable_quotas:
            # Global default quota
            global_quota = QuotaPolicy(
                id="global_default",
                name="Global Default Quota",
                description="Default quota for all users",
                quota_type=QuotaType.GLOBAL,
                entity_id="*",
                max_storage_bytes=self.settings.default_user_quota,
                max_file_count=10000,
                max_file_size=self.settings.max_upload_size
            )
            self._policies[global_quota.id] = global_quota
    
    async def initialize(self) -> None:
        """Initialize the quota management service"""
        logger.info("Initializing quota management service")
        
        # Load persisted data
        await self._load_data()
        
        # Start background tasks
        if self.settings.enable_quotas:
            self._usage_update_task = asyncio.create_task(self._usage_update_worker())
            self._alert_check_task = asyncio.create_task(self._alert_check_worker())
    
    async def shutdown(self) -> None:
        """Shutdown the quota management service"""
        logger.info("Shutting down quota management service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in [self._usage_update_task, self._alert_check_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Save data
        await self._save_data()
    
    async def check_quota(
        self,
        entity_id: str,
        entity_type: QuotaType,
        size_to_add: int,
        driver_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if adding size would exceed quota"""
        # Find applicable policies
        policies = self._get_applicable_policies(entity_id, entity_type, driver_name)
        
        if not policies:
            return True, None  # No quota restrictions
        
        # Check each policy
        for policy in policies:
            if not policy.enabled:
                continue
            
            usage = await self.get_usage(policy.id, entity_id)
            
            # Check storage bytes limit
            if policy.max_storage_bytes:
                new_usage = usage.used_storage_bytes + size_to_add
                
                if new_usage > policy.max_storage_bytes * policy.hard_limit_percentage:
                    return False, f"Storage quota exceeded for {policy.name}"
            
            # Check file size limit
            if policy.max_file_size and size_to_add > policy.max_file_size:
                return False, f"File size exceeds maximum allowed size of {policy.max_file_size} bytes"
        
        return True, None
    
    async def update_usage(
        self,
        entity_id: str,
        entity_type: QuotaType,
        size_delta: int,
        file_count_delta: int = 0,
        driver_name: Optional[str] = None
    ) -> None:
        """Update quota usage"""
        policies = self._get_applicable_policies(entity_id, entity_type, driver_name)
        
        for policy in policies:
            usage_key = f"{policy.id}:{entity_id}"
            
            if usage_key not in self._usage:
                self._usage[usage_key] = QuotaUsage(
                    policy_id=policy.id,
                    entity_id=entity_id
                )
            
            usage = self._usage[usage_key]
            usage.used_storage_bytes = max(0, usage.used_storage_bytes + size_delta)
            usage.used_file_count = max(0, usage.used_file_count + file_count_delta)
            usage.last_updated = datetime.utcnow()
            
            # Update driver-specific usage
            if driver_name:
                if driver_name not in usage.driver_usage:
                    usage.driver_usage[driver_name] = {
                        "used_storage_bytes": 0,
                        "used_file_count": 0
                    }
                
                driver_usage = usage.driver_usage[driver_name]
                driver_usage["used_storage_bytes"] = max(
                    0, driver_usage["used_storage_bytes"] + size_delta
                )
                driver_usage["used_file_count"] = max(
                    0, driver_usage["used_file_count"] + file_count_delta
                )
            
            # Check for alerts
            await self._check_quota_alerts(policy, usage)
    
    async def get_usage(
        self,
        policy_id: str,
        entity_id: str
    ) -> QuotaUsage:
        """Get current usage for a policy and entity"""
        usage_key = f"{policy_id}:{entity_id}"
        
        if usage_key not in self._usage:
            # Calculate current usage
            await self._calculate_usage(policy_id, entity_id)
        
        return self._usage.get(usage_key, QuotaUsage(policy_id, entity_id))
    
    async def get_quota_status(
        self,
        entity_id: str,
        entity_type: QuotaType,
        driver_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get quota status for an entity"""
        policies = self._get_applicable_policies(entity_id, entity_type, driver_name)
        
        status = {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "quotas": []
        }
        
        for policy in policies:
            usage = await self.get_usage(policy.id, entity_id)
            
            quota_info = {
                "policy_id": policy.id,
                "policy_name": policy.name,
                "enabled": policy.enabled,
                "limits": {
                    "max_storage_bytes": policy.max_storage_bytes,
                    "max_file_count": policy.max_file_count,
                    "max_file_size": policy.max_file_size
                },
                "usage": {
                    "used_storage_bytes": usage.used_storage_bytes,
                    "used_file_count": usage.used_file_count,
                    "last_updated": usage.last_updated.isoformat()
                },
                "percentages": {}
            }
            
            # Calculate percentages
            if policy.max_storage_bytes:
                quota_info["percentages"]["storage"] = round(
                    (usage.used_storage_bytes / policy.max_storage_bytes) * 100, 2
                )
            
            if policy.max_file_count:
                quota_info["percentages"]["file_count"] = round(
                    (usage.used_file_count / policy.max_file_count) * 100, 2
                )
            
            status["quotas"].append(quota_info)
        
        return status
    
    def create_policy(self, policy: QuotaPolicy) -> None:
        """Create a new quota policy"""
        if policy.id in self._policies:
            raise InvalidStorageOperationError(f"Policy already exists: {policy.id}")
        
        policy.created_at = datetime.utcnow()
        policy.updated_at = datetime.utcnow()
        self._policies[policy.id] = policy
        
        logger.info(f"Created quota policy: {policy.id}")
    
    def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> QuotaPolicy:
        """Update an existing quota policy"""
        if policy_id not in self._policies:
            raise InvalidStorageOperationError(f"Policy not found: {policy_id}")
        
        policy = self._policies[policy_id]
        
        # Update allowed fields
        allowed_fields = [
            "name", "description", "max_storage_bytes", "max_file_count",
            "max_file_size", "soft_limit_percentage", "hard_limit_percentage",
            "action_on_soft_limit", "action_on_hard_limit", "enabled",
            "driver_quotas"
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                if field.startswith("action_on_"):
                    value = QuotaAction(value) if isinstance(value, str) else value
                setattr(policy, field, value)
        
        policy.updated_at = datetime.utcnow()
        
        logger.info(f"Updated quota policy: {policy_id}")
        return policy
    
    def delete_policy(self, policy_id: str) -> None:
        """Delete a quota policy"""
        if policy_id not in self._policies:
            raise InvalidStorageOperationError(f"Policy not found: {policy_id}")
        
        del self._policies[policy_id]
        
        # Remove associated usage data
        usage_keys_to_remove = [
            key for key in self._usage.keys()
            if key.startswith(f"{policy_id}:")
        ]
        for key in usage_keys_to_remove:
            del self._usage[key]
        
        logger.info(f"Deleted quota policy: {policy_id}")
    
    def get_policies(
        self,
        entity_type: Optional[QuotaType] = None,
        entity_id: Optional[str] = None
    ) -> List[QuotaPolicy]:
        """Get quota policies"""
        policies = list(self._policies.values())
        
        if entity_type:
            policies = [p for p in policies if p.quota_type == entity_type]
        
        if entity_id:
            policies = [
                p for p in policies
                if p.entity_id == entity_id or p.entity_id == "*"
            ]
        
        return policies
    
    def get_alerts(
        self,
        entity_id: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[QuotaAlert]:
        """Get quota alerts"""
        alerts = self._alerts
        
        if entity_id:
            alerts = [a for a in alerts if a.entity_id == entity_id]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> None:
        """Acknowledge a quota alert"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                break
    
    def _get_applicable_policies(
        self,
        entity_id: str,
        entity_type: QuotaType,
        driver_name: Optional[str] = None
    ) -> List[QuotaPolicy]:
        """Get policies applicable to an entity"""
        applicable = []
        
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            
            # Check entity type match
            if policy.quota_type == entity_type and policy.entity_id == entity_id:
                applicable.append(policy)
            
            # Check global policies
            elif policy.quota_type == QuotaType.GLOBAL and policy.entity_id == "*":
                applicable.append(policy)
            
            # Check driver-specific quotas
            elif driver_name and driver_name in policy.driver_quotas:
                applicable.append(policy)
        
        return applicable
    
    async def _calculate_usage(
        self,
        policy_id: str,
        entity_id: str
    ) -> None:
        """Calculate current usage for a policy and entity"""
        if policy_id not in self._policies:
            return
        
        policy = self._policies[policy_id]
        usage_key = f"{policy_id}:{entity_id}"
        
        # Initialize usage
        usage = QuotaUsage(
            policy_id=policy_id,
            entity_id=entity_id
        )
        
        # Calculate usage based on entity type
        # This is simplified - in production, you'd query a database
        # to get actual usage by user/group/org
        
        # For now, calculate based on all objects
        for driver_name in self.storage_service._drivers:
            driver = self.storage_service.get_driver(driver_name)
            
            try:
                objects, _ = await driver.list_objects(max_keys=10000)
                
                driver_bytes = sum(obj.size for obj in objects)
                driver_count = len(objects)
                
                usage.used_storage_bytes += driver_bytes
                usage.used_file_count += driver_count
                
                usage.driver_usage[driver_name] = {
                    "used_storage_bytes": driver_bytes,
                    "used_file_count": driver_count
                }
            except Exception as e:
                logger.error(f"Failed to calculate usage for driver {driver_name}: {e}")
        
        self._usage[usage_key] = usage
    
    async def _check_quota_alerts(
        self,
        policy: QuotaPolicy,
        usage: QuotaUsage
    ) -> None:
        """Check if alerts should be triggered"""
        if not policy.max_storage_bytes:
            return
        
        usage_percentage = (usage.used_storage_bytes / policy.max_storage_bytes) * 100
        
        # Check soft limit
        if usage_percentage >= policy.soft_limit_percentage * 100:
            await self._create_alert(
                policy,
                usage.entity_id,
                policy.action_on_soft_limit,
                f"Storage usage at {usage_percentage:.1f}% of quota",
                policy.soft_limit_percentage,
                usage.used_storage_bytes,
                policy.max_storage_bytes
            )
        
        # Check hard limit
        if usage_percentage >= policy.hard_limit_percentage * 100:
            await self._create_alert(
                policy,
                usage.entity_id,
                policy.action_on_hard_limit,
                f"Storage quota exceeded - usage at {usage_percentage:.1f}%",
                policy.hard_limit_percentage,
                usage.used_storage_bytes,
                policy.max_storage_bytes
            )
    
    async def _create_alert(
        self,
        policy: QuotaPolicy,
        entity_id: str,
        alert_type: QuotaAction,
        message: str,
        threshold: float,
        current_usage: int,
        max_allowed: int
    ) -> None:
        """Create a new alert"""
        # Check if similar alert already exists
        for alert in self._alerts:
            if (alert.policy_id == policy.id and
                alert.entity_id == entity_id and
                alert.alert_type == alert_type and
                not alert.acknowledged and
                (datetime.utcnow() - alert.created_at) < timedelta(hours=1)):
                return  # Don't create duplicate alerts
        
        import hashlib
        alert_id = hashlib.md5(
            f"{policy.id}:{entity_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        
        alert = QuotaAlert(
            id=alert_id,
            policy_id=policy.id,
            entity_id=entity_id,
            alert_type=alert_type,
            message=message,
            threshold_percentage=threshold,
            current_usage_bytes=current_usage,
            max_allowed_bytes=max_allowed
        )
        
        self._alerts.append(alert)
        
        # Keep alerts limited
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]
        
        logger.warning(f"Quota alert created: {message}")
    
    async def _usage_update_worker(self) -> None:
        """Background worker to update usage statistics"""
        logger.info("Starting quota usage update worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Update usage every 5 minutes
                await asyncio.sleep(300)
                
                # Recalculate usage for all active policies
                for policy in self._policies.values():
                    if policy.enabled:
                        await self._calculate_usage(policy.id, policy.entity_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Usage update worker error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Usage update worker stopped")
    
    async def _alert_check_worker(self) -> None:
        """Background worker to check for quota alerts"""
        logger.info("Starting quota alert check worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Check alerts every minute
                await asyncio.sleep(60)
                
                # Check all active policies
                for policy in self._policies.values():
                    if policy.enabled and policy.max_storage_bytes:
                        usage = await self.get_usage(policy.id, policy.entity_id)
                        await self._check_quota_alerts(policy, usage)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check worker error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Alert check worker stopped")
    
    async def _save_data(self) -> None:
        """Save quota data to disk"""
        try:
            # Save policies
            policies_data = {
                pid: policy.to_dict()
                for pid, policy in self._policies.items()
            }
            
            policies_file = self._data_dir / "policies.json"
            async with asyncio.Lock():
                with open(policies_file, 'w') as f:
                    json.dump(policies_data, f, indent=2)
            
            # Save usage data
            usage_data = {
                key: usage.to_dict()
                for key, usage in self._usage.items()
            }
            
            usage_file = self._data_dir / "usage.json"
            with open(usage_file, 'w') as f:
                json.dump(usage_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save quota data: {e}")
    
    async def _load_data(self) -> None:
        """Load quota data from disk"""
        try:
            # Load policies
            policies_file = self._data_dir / "policies.json"
            if policies_file.exists():
                with open(policies_file, 'r') as f:
                    policies_data = json.load(f)
                
                for pid, pdata in policies_data.items():
                    self._policies[pid] = QuotaPolicy.from_dict(pdata)
            
            # Load usage data
            usage_file = self._data_dir / "usage.json"
            if usage_file.exists():
                with open(usage_file, 'r') as f:
                    usage_data = json.load(f)
                
                for key, udata in usage_data.items():
                    usage = QuotaUsage(
                        policy_id=udata["policy_id"],
                        entity_id=udata["entity_id"],
                        used_storage_bytes=udata["used_storage_bytes"],
                        used_file_count=udata["used_file_count"],
                        last_updated=datetime.fromisoformat(udata["last_updated"]),
                        driver_usage=udata.get("driver_usage", {})
                    )
                    self._usage[key] = usage
            
        except Exception as e:
            logger.error(f"Failed to load quota data: {e}")


# Global instance
_quota_service: Optional[QuotaManagementService] = None


async def get_quota_service(storage_service) -> QuotaManagementService:
    """Get or create quota service instance"""
    global _quota_service
    
    if _quota_service is None:
        _quota_service = QuotaManagementService(storage_service)
        await _quota_service.initialize()
    
    return _quota_service


async def close_quota_service() -> None:
    """Close quota service"""
    global _quota_service
    
    if _quota_service is not None:
        await _quota_service.shutdown()
        _quota_service = None