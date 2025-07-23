"""
Tests for Tier Migration functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

from src.services.tier_migration_service import (
    TierMigrationService, MigrationPolicy, MigrationTask,
    MigrationStatus, MigrationStats
)
from src.core.interfaces import StorageTier, StorageObject, ObjectNotFoundError


class MockStorageDriver:
    """Mock storage driver for testing"""
    def __init__(self):
        self.objects = {
            "old_file.txt": StorageObject(
                key="old_file.txt",
                size=1024,
                last_modified=datetime.utcnow() - timedelta(days=45),
                etag="abc123",
                storage_class="hot"
            ),
            "very_old_file.txt": StorageObject(
                key="very_old_file.txt",
                size=2048,
                last_modified=datetime.utcnow() - timedelta(days=100),
                etag="def456",
                storage_class="warm"
            ),
            "new_file.txt": StorageObject(
                key="new_file.txt",
                size=512,
                last_modified=datetime.utcnow() - timedelta(days=5),
                etag="ghi789",
                storage_class="hot"
            )
        }
    
    async def get_object_info(self, key: str) -> StorageObject:
        if key not in self.objects:
            raise ObjectNotFoundError(key)
        return self.objects[key]
    
    async def list_objects(self, **kwargs):
        return list(self.objects.values()), None
    
    async def change_storage_tier(self, key: str, tier: StorageTier) -> StorageObject:
        if key not in self.objects:
            raise ObjectNotFoundError(key)
        obj = self.objects[key]
        obj.storage_class = tier.value.lower()
        return obj
    
    async def copy_object(self, source_key: str, dest_key: str, metadata=None):
        if source_key not in self.objects:
            raise ObjectNotFoundError(source_key)
        obj = self.objects[source_key]
        new_obj = StorageObject(
            key=dest_key,
            size=obj.size,
            last_modified=datetime.utcnow(),
            etag=obj.etag,
            storage_class=obj.storage_class,
            metadata=metadata
        )
        self.objects[dest_key] = new_obj
        return new_obj
    
    async def delete_object(self, key: str) -> bool:
        if key in self.objects:
            del self.objects[key]
            return True
        return False


class MockStorageService:
    """Mock storage service for testing"""
    def __init__(self):
        self._drivers = {
            "local": MockStorageDriver(),
            "s3": MockStorageDriver()
        }
        self._default_driver = "local"
    
    def get_driver(self, driver_name=None):
        return self._drivers.get(driver_name or self._default_driver)
    
    async def copy_object(self, source_key, dest_key, metadata, source_driver, dest_driver):
        source = self.get_driver(source_driver)
        dest = self.get_driver(dest_driver)
        
        obj_info = await source.get_object_info(source_key)
        new_obj = StorageObject(
            key=dest_key,
            size=obj_info.size,
            last_modified=datetime.utcnow(),
            etag=obj_info.etag,
            storage_class=obj_info.storage_class,
            metadata=metadata
        )
        
        if hasattr(dest, 'objects'):
            dest.objects[dest_key] = new_obj
        
        return new_obj


@pytest.fixture
async def migration_service():
    """Create a migration service for testing"""
    storage_service = MockStorageService()
    service = TierMigrationService(storage_service)
    # Don't start background worker in tests
    service._migration_task = None
    yield service
    await service.shutdown()


class TestTierMigrationService:
    """Test cases for tier migration service"""
    
    async def test_migrate_single_object(self, migration_service):
        """Test migrating a single object"""
        task = await migration_service.migrate_object(
            "old_file.txt",
            StorageTier.WARM,
            source_driver="local"
        )
        
        assert task.object_key == "old_file.txt"
        assert task.source_tier == StorageTier.HOT
        assert task.target_tier == StorageTier.WARM
        assert task.status == MigrationStatus.COMPLETED
    
    async def test_migrate_already_in_tier(self, migration_service):
        """Test migrating object already in target tier"""
        # First migrate to warm
        await migration_service.migrate_object(
            "old_file.txt",
            StorageTier.WARM,
            source_driver="local"
        )
        
        # Try to migrate to warm again
        with pytest.raises(Exception) as exc:
            await migration_service.migrate_object(
                "old_file.txt",
                StorageTier.WARM,
                source_driver="local"
            )
        
        assert "already in warm tier" in str(exc.value).lower()
    
    async def test_force_migration(self, migration_service):
        """Test force migration to same tier"""
        # Migrate to same tier with force
        task = await migration_service.migrate_object(
            "new_file.txt",
            StorageTier.HOT,
            source_driver="local",
            force=True
        )
        
        assert task.status == MigrationStatus.COMPLETED
    
    async def test_cross_driver_migration(self, migration_service):
        """Test migration between different drivers"""
        task = await migration_service.migrate_object(
            "old_file.txt",
            StorageTier.COLD,
            source_driver="local",
            target_driver="s3"
        )
        
        assert task.source_driver == "local"
        assert task.target_driver == "s3"
        assert task.status == MigrationStatus.COMPLETED
    
    async def test_batch_migration(self, migration_service):
        """Test batch migration of multiple objects"""
        keys = ["old_file.txt", "very_old_file.txt", "new_file.txt"]
        tasks = await migration_service.migrate_objects_batch(
            keys,
            StorageTier.COLD,
            source_driver="local"
        )
        
        assert len(tasks) == 3
        for task in tasks:
            assert task.target_tier == StorageTier.COLD
    
    async def test_migration_policy_age_based(self, migration_service):
        """Test age-based migration policy"""
        policy = MigrationPolicy(
            name="test_age_policy",
            description="Test age-based migration",
            hot_to_warm_days=30,
            warm_to_cold_days=90
        )
        
        migration_service.add_policy(policy)
        
        # Apply policy (dry run)
        eligible, stats = await migration_service.apply_policy(
            "test_age_policy",
            driver_name="local",
            dry_run=True
        )
        
        # Should find old_file.txt (45 days) for hot->warm
        # and very_old_file.txt (100 days) for warm->cold
        assert len(eligible) >= 1
        assert stats.total_objects >= 3
    
    async def test_migration_policy_size_filter(self, migration_service):
        """Test migration policy with size filters"""
        policy = MigrationPolicy(
            name="test_size_policy",
            description="Test size-based filtering",
            hot_to_warm_days=30,
            min_file_size=1000,  # Only files >= 1KB
            max_file_size=2000   # Only files <= 2KB
        )
        
        migration_service.add_policy(policy)
        
        eligible, stats = await migration_service.apply_policy(
            "test_size_policy",
            driver_name="local",
            dry_run=True
        )
        
        # Should only find old_file.txt (1KB, 45 days old)
        # Not new_file.txt (too small) or very_old_file.txt (wrong tier)
        for key, _, _ in eligible:
            obj = await migration_service.storage_service.get_driver("local").get_object_info(key)
            assert 1000 <= obj.size <= 2000
    
    async def test_migration_policy_patterns(self, migration_service):
        """Test migration policy with pattern filters"""
        policy = MigrationPolicy(
            name="test_pattern_policy",
            description="Test pattern-based filtering",
            hot_to_warm_days=1,  # Very short for testing
            include_patterns=["*.txt"],
            exclude_patterns=["new_*"]
        )
        
        migration_service.add_policy(policy)
        
        eligible, stats = await migration_service.apply_policy(
            "test_pattern_policy",
            driver_name="local",
            dry_run=True
        )
        
        # Should not include new_file.txt due to exclude pattern
        for key, _, _ in eligible:
            assert not key.startswith("new_")
    
    async def test_get_migration_status(self, migration_service):
        """Test getting migration task status"""
        task = await migration_service.migrate_object(
            "old_file.txt",
            StorageTier.WARM,
            source_driver="local"
        )
        
        # Get status
        status = await migration_service.get_migration_status(task.task_id)
        assert status is not None
        assert status.task_id == task.task_id
        assert status.status == MigrationStatus.COMPLETED
        
        # Non-existent task
        status = await migration_service.get_migration_status("invalid_id")
        assert status is None
    
    async def test_migration_stats(self, migration_service):
        """Test getting migration statistics"""
        # Perform some migrations
        await migration_service.migrate_object(
            "old_file.txt",
            StorageTier.WARM,
            source_driver="local"
        )
        
        stats = await migration_service.get_migration_stats("local")
        
        assert stats.total_objects >= 3
        assert stats.total_bytes > 0
        assert "hot" in stats.tier_distribution
        assert stats.migrated_objects >= 1
    
    async def test_policy_management(self, migration_service):
        """Test policy add/remove/list operations"""
        policy1 = MigrationPolicy(
            name="policy1",
            description="Test policy 1"
        )
        policy2 = MigrationPolicy(
            name="policy2",
            description="Test policy 2"
        )
        
        # Add policies
        migration_service.add_policy(policy1)
        migration_service.add_policy(policy2)
        
        # List policies
        policies = migration_service.get_policies()
        assert len(policies) >= 2
        assert "policy1" in policies
        assert "policy2" in policies
        
        # Remove policy
        migration_service.remove_policy("policy1")
        policies = migration_service.get_policies()
        assert "policy1" not in policies
        assert "policy2" in policies
    
    async def test_migration_window(self, migration_service):
        """Test migration window restrictions"""
        # Get current time
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Create policy with window that excludes current time
        if current_hour < 12:
            # Morning - set window to afternoon
            start = "13:00"
            end = "17:00"
        else:
            # Afternoon/evening - set window to morning
            start = "06:00"
            end = "10:00"
        
        policy = MigrationPolicy(
            name="windowed_policy",
            description="Policy with time window",
            hot_to_warm_days=1,
            migration_window_start=start,
            migration_window_end=end
        )
        
        migration_service.add_policy(policy)
        
        # Should not run outside window
        eligible, stats = await migration_service.apply_policy(
            "windowed_policy",
            driver_name="local",
            dry_run=False
        )
        
        # No migrations should occur outside window
        assert stats.migrated_objects == 0