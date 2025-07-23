"""
Tests for Quota Management functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path
import tempfile
import shutil
import json

from src.services.quota_management_service import (
    QuotaManagementService, QuotaPolicy, QuotaUsage, QuotaAlert,
    QuotaType, QuotaAction
)
from src.core.interfaces import (
    StorageObject, ObjectNotFoundError, StorageQuotaExceededError,
    InvalidStorageOperationError
)


class MockStorageDriver:
    """Mock storage driver for testing"""
    def __init__(self):
        self.objects = {
            "user1/file1.txt": StorageObject(
                key="user1/file1.txt",
                size=1024,
                last_modified=datetime.utcnow(),
                etag="abc123",
                storage_class="hot"
            ),
            "user1/file2.txt": StorageObject(
                key="user1/file2.txt",
                size=2048,
                last_modified=datetime.utcnow(),
                etag="def456",
                storage_class="hot"
            ),
            "user2/bigfile.mp4": StorageObject(
                key="user2/bigfile.mp4",
                size=104857600,  # 100MB
                last_modified=datetime.utcnow(),
                etag="ghi789",
                storage_class="hot"
            )
        }
    
    async def list_objects(self, **kwargs):
        return list(self.objects.values()), None
    
    async def get_object_info(self, key: str) -> StorageObject:
        if key not in self.objects:
            raise ObjectNotFoundError(key)
        return self.objects[key]


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


class MockSettings:
    """Mock settings for testing"""
    def __init__(self):
        self.enable_quotas = True
        self.default_user_quota = 1073741824  # 1GB
        self.max_upload_size = 104857600  # 100MB
        self.temp_directory = tempfile.mkdtemp()


@pytest.fixture
async def quota_service():
    """Create a quota service for testing"""
    storage_service = MockStorageService()
    
    # Create temporary directory for test data
    temp_dir = tempfile.mkdtemp()
    
    service = QuotaManagementService(storage_service)
    service.settings = MockSettings()
    service._data_dir = Path(temp_dir) / "quotas"
    service._data_dir.mkdir(parents=True, exist_ok=True)
    
    # Don't start background workers in tests
    service._usage_update_task = None
    service._alert_check_task = None
    
    yield service
    
    await service.shutdown()
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestQuotaPolicyManagement:
    """Test cases for quota policy management"""
    
    def test_create_policy(self, quota_service):
        """Test creating a new quota policy"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240,  # 10GB
            max_file_count=1000,
            max_file_size=104857600  # 100MB
        )
        
        quota_service.create_policy(policy)
        
        assert "test_policy" in quota_service._policies
        assert quota_service._policies["test_policy"].name == "Test Policy"
    
    def test_create_duplicate_policy(self, quota_service):
        """Test creating a duplicate policy raises error"""
        policy1 = QuotaPolicy(
            id="test_policy",
            name="Test Policy 1",
            description="First policy",
            quota_type=QuotaType.USER,
            entity_id="user123"
        )
        
        policy2 = QuotaPolicy(
            id="test_policy",
            name="Test Policy 2",
            description="Duplicate policy",
            quota_type=QuotaType.USER,
            entity_id="user456"
        )
        
        quota_service.create_policy(policy1)
        
        with pytest.raises(InvalidStorageOperationError):
            quota_service.create_policy(policy2)
    
    def test_update_policy(self, quota_service):
        """Test updating a quota policy"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=5368709120  # 5GB
        )
        
        quota_service.create_policy(policy)
        
        # Update policy
        updates = {
            "max_storage_bytes": 10737418240,  # 10GB
            "description": "Updated test policy",
            "enabled": False
        }
        
        updated_policy = quota_service.update_policy("test_policy", updates)
        
        assert updated_policy.max_storage_bytes == 10737418240
        assert updated_policy.description == "Updated test policy"
        assert updated_policy.enabled is False
    
    def test_update_nonexistent_policy(self, quota_service):
        """Test updating a non-existent policy raises error"""
        with pytest.raises(InvalidStorageOperationError):
            quota_service.update_policy("nonexistent", {"description": "test"})
    
    def test_delete_policy(self, quota_service):
        """Test deleting a quota policy"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123"
        )
        
        quota_service.create_policy(policy)
        assert "test_policy" in quota_service._policies
        
        quota_service.delete_policy("test_policy")
        assert "test_policy" not in quota_service._policies
    
    def test_get_policies_filtered(self, quota_service):
        """Test getting policies with filters"""
        policy1 = QuotaPolicy(
            id="user_policy",
            name="User Policy",
            description="Policy for users",
            quota_type=QuotaType.USER,
            entity_id="user123"
        )
        
        policy2 = QuotaPolicy(
            id="group_policy",
            name="Group Policy",
            description="Policy for groups",
            quota_type=QuotaType.GROUP,
            entity_id="group456"
        )
        
        policy3 = QuotaPolicy(
            id="global_policy",
            name="Global Policy",
            description="Global policy",
            quota_type=QuotaType.GLOBAL,
            entity_id="*"
        )
        
        quota_service.create_policy(policy1)
        quota_service.create_policy(policy2)
        quota_service.create_policy(policy3)
        
        # Filter by entity type
        user_policies = quota_service.get_policies(entity_type=QuotaType.USER)
        assert len(user_policies) == 1
        assert user_policies[0].id == "user_policy"
        
        # Filter by entity ID
        specific_policies = quota_service.get_policies(entity_id="user123")
        assert len(specific_policies) == 2  # user_policy and global_policy


class TestQuotaChecking:
    """Test cases for quota checking functionality"""
    
    async def test_check_quota_within_limits(self, quota_service):
        """Test quota check when within limits"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240,  # 10GB
            max_file_count=1000,
            max_file_size=104857600  # 100MB
        )
        
        quota_service.create_policy(policy)
        
        # Check adding 1MB file
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 1048576
        )
        
        assert allowed is True
        assert reason is None
    
    async def test_check_quota_exceeds_storage_limit(self, quota_service):
        """Test quota check when exceeding storage limit"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=1048576,  # 1MB
            max_file_count=1000,
            max_file_size=104857600  # 100MB
        )
        
        quota_service.create_policy(policy)
        
        # Try to add 2MB file
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 2097152
        )
        
        assert allowed is False
        assert "quota exceeded" in reason.lower()
    
    async def test_check_quota_exceeds_file_size_limit(self, quota_service):
        """Test quota check when exceeding file size limit"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240,  # 10GB
            max_file_count=1000,
            max_file_size=1048576  # 1MB
        )
        
        quota_service.create_policy(policy)
        
        # Try to add 2MB file
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 2097152
        )
        
        assert allowed is False
        assert "file size exceeds" in reason.lower()
    
    async def test_check_quota_no_policies(self, quota_service):
        """Test quota check when no policies exist"""
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 1048576
        )
        
        assert allowed is True
        assert reason is None


class TestUsageTracking:
    """Test cases for usage tracking functionality"""
    
    async def test_update_usage(self, quota_service):
        """Test updating usage statistics"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240  # 10GB
        )
        
        quota_service.create_policy(policy)
        
        # Update usage
        await quota_service.update_usage(
            "user123", QuotaType.USER, 1048576, 1, "local"
        )
        
        usage = await quota_service.get_usage("test_policy", "user123")
        
        assert usage.used_storage_bytes == 1048576
        assert usage.used_file_count == 1
        assert "local" in usage.driver_usage
    
    async def test_update_usage_negative_delta(self, quota_service):
        """Test updating usage with negative delta (file deletion)"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240  # 10GB
        )
        
        quota_service.create_policy(policy)
        
        # Add some usage first
        await quota_service.update_usage(
            "user123", QuotaType.USER, 2097152, 2, "local"
        )
        
        # Remove some usage
        await quota_service.update_usage(
            "user123", QuotaType.USER, -1048576, -1, "local"
        )
        
        usage = await quota_service.get_usage("test_policy", "user123")
        
        assert usage.used_storage_bytes == 1048576
        assert usage.used_file_count == 1
    
    async def test_get_quota_status(self, quota_service):
        """Test getting quota status"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240,  # 10GB
            max_file_count=1000
        )
        
        quota_service.create_policy(policy)
        
        # Add some usage
        await quota_service.update_usage(
            "user123", QuotaType.USER, 1073741824, 100  # 1GB, 100 files
        )
        
        status = await quota_service.get_quota_status(
            "user123", QuotaType.USER
        )
        
        assert status["entity_id"] == "user123"
        assert status["entity_type"] == "user"
        assert len(status["quotas"]) == 1
        
        quota_info = status["quotas"][0]
        assert quota_info["policy_name"] == "Test Policy"
        assert quota_info["usage"]["used_storage_bytes"] == 1073741824
        assert quota_info["usage"]["used_file_count"] == 100
        assert quota_info["percentages"]["storage"] == 10.0  # 1GB/10GB = 10%


class TestQuotaAlerts:
    """Test cases for quota alert functionality"""
    
    def test_get_alerts_unfiltered(self, quota_service):
        """Test getting all alerts"""
        # Create some test alerts
        alert1 = QuotaAlert(
            id="alert1",
            policy_id="policy1",
            entity_id="user123",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,  # 8GB
            max_allowed_bytes=10737418240   # 10GB
        )
        
        alert2 = QuotaAlert(
            id="alert2",
            policy_id="policy1",
            entity_id="user456",
            alert_type=QuotaAction.BLOCK,
            message="Storage quota exceeded",
            threshold_percentage=1.0,
            current_usage_bytes=11811160064,  # 11GB
            max_allowed_bytes=10737418240    # 10GB
        )
        
        quota_service._alerts = [alert1, alert2]
        
        alerts = quota_service.get_alerts()
        assert len(alerts) == 2
    
    def test_get_alerts_filtered_by_entity(self, quota_service):
        """Test getting alerts filtered by entity"""
        alert1 = QuotaAlert(
            id="alert1",
            policy_id="policy1",
            entity_id="user123",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,
            max_allowed_bytes=10737418240
        )
        
        alert2 = QuotaAlert(
            id="alert2",
            policy_id="policy1",
            entity_id="user456",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,
            max_allowed_bytes=10737418240
        )
        
        quota_service._alerts = [alert1, alert2]
        
        user123_alerts = quota_service.get_alerts(entity_id="user123")
        assert len(user123_alerts) == 1
        assert user123_alerts[0].entity_id == "user123"
    
    def test_get_alerts_filtered_by_acknowledgment(self, quota_service):
        """Test getting alerts filtered by acknowledgment status"""
        alert1 = QuotaAlert(
            id="alert1",
            policy_id="policy1",
            entity_id="user123",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,
            max_allowed_bytes=10737418240,
            acknowledged=False
        )
        
        alert2 = QuotaAlert(
            id="alert2",
            policy_id="policy1",
            entity_id="user456",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,
            max_allowed_bytes=10737418240,
            acknowledged=True
        )
        
        quota_service._alerts = [alert1, alert2]
        
        unack_alerts = quota_service.get_alerts(acknowledged=False)
        assert len(unack_alerts) == 1
        assert unack_alerts[0].acknowledged is False
        
        ack_alerts = quota_service.get_alerts(acknowledged=True)
        assert len(ack_alerts) == 1
        assert ack_alerts[0].acknowledged is True
    
    def test_acknowledge_alert(self, quota_service):
        """Test acknowledging an alert"""
        alert = QuotaAlert(
            id="alert1",
            policy_id="policy1",
            entity_id="user123",
            alert_type=QuotaAction.WARN,
            message="Storage usage at 80%",
            threshold_percentage=0.8,
            current_usage_bytes=8589934592,
            max_allowed_bytes=10737418240,
            acknowledged=False
        )
        
        quota_service._alerts = [alert]
        
        # Acknowledge the alert
        quota_service.acknowledge_alert("alert1")
        
        acknowledged_alert = quota_service._alerts[0]
        assert acknowledged_alert.acknowledged is True
        assert acknowledged_alert.acknowledged_at is not None


class TestDataPersistence:
    """Test cases for data persistence functionality"""
    
    async def test_save_and_load_policies(self, quota_service):
        """Test saving and loading policies"""
        policy = QuotaPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test quota policy",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=10737418240
        )
        
        quota_service.create_policy(policy)
        
        # Save data
        await quota_service._save_data()
        
        # Clear policies and reload
        quota_service._policies.clear()
        await quota_service._load_data()
        
        # Check that policy was loaded
        assert "test_policy" in quota_service._policies
        loaded_policy = quota_service._policies["test_policy"]
        assert loaded_policy.name == "Test Policy"
        assert loaded_policy.quota_type == QuotaType.USER
        assert loaded_policy.max_storage_bytes == 10737418240
    
    async def test_save_and_load_usage(self, quota_service):
        """Test saving and loading usage data"""
        usage = QuotaUsage(
            policy_id="test_policy",
            entity_id="user123",
            used_storage_bytes=1073741824,
            used_file_count=100
        )
        
        quota_service._usage["test_policy:user123"] = usage
        
        # Save data
        await quota_service._save_data()
        
        # Clear usage and reload
        quota_service._usage.clear()
        await quota_service._load_data()
        
        # Check that usage was loaded
        assert "test_policy:user123" in quota_service._usage
        loaded_usage = quota_service._usage["test_policy:user123"]
        assert loaded_usage.used_storage_bytes == 1073741824
        assert loaded_usage.used_file_count == 100


class TestQuotaIntegration:
    """Integration tests for quota management"""
    
    async def test_quota_workflow(self, quota_service):
        """Test complete quota management workflow"""
        # 1. Create a quota policy
        policy = QuotaPolicy(
            id="user_quota",
            name="User Quota",
            description="Standard user quota",
            quota_type=QuotaType.USER,
            entity_id="user123",
            max_storage_bytes=1073741824,  # 1GB
            max_file_count=100,
            soft_limit_percentage=0.8,
            hard_limit_percentage=1.0,
            action_on_soft_limit=QuotaAction.WARN,
            action_on_hard_limit=QuotaAction.BLOCK
        )
        
        quota_service.create_policy(policy)
        
        # 2. Check quota before any usage
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 104857600  # 100MB
        )
        assert allowed is True
        
        # 3. Add some usage (700MB - should trigger soft limit)
        await quota_service.update_usage(
            "user123", QuotaType.USER, 734003200, 70  # 700MB, 70 files
        )
        
        # 4. Check quota status
        status = await quota_service.get_quota_status("user123", QuotaType.USER)
        quota_info = status["quotas"][0]
        assert quota_info["percentages"]["storage"] == 70.0
        
        # 5. Try to add more storage (should still be allowed but close to limit)
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 104857600  # 100MB more
        )
        assert allowed is True
        
        # 6. Try to add too much storage (should be blocked)
        allowed, reason = await quota_service.check_quota(
            "user123", QuotaType.USER, 419430400  # 400MB more (would exceed limit)
        )
        assert allowed is False
        assert "quota exceeded" in reason.lower()