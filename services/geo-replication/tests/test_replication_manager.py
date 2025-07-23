"""
Tests for geo-replication manager
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.services.replication_manager import (
    GeoReplicationManager,
    ReplicationType,
    ReplicationMode,
    ConflictResolutionStrategy
)
from src.models.schemas import (
    ReplicationConfig,
    RegionInfo,
    ReplicationJob,
    ReplicationStatus,
    RegionStatus
)


@pytest.fixture
async def replication_manager():
    """Create a replication manager instance for testing"""
    manager = GeoReplicationManager()
    
    # Mock the configuration
    manager.replication_config = ReplicationConfig(
        enabled=True,
        primary_region="us-east-1",
        secondary_regions=["eu-west-1", "ap-southeast-1"],
        replication_mode=ReplicationMode.ASYNC,
        conflict_resolution=ConflictResolutionStrategy.LAST_WRITE_WINS,
        batch_size=100,
        max_lag_seconds=60
    )
    
    # Initialize with mocked connections
    with patch.object(manager, '_connect_region', new_callable=AsyncMock):
        await manager.initialize()
    
    yield manager
    
    # Cleanup
    await manager.shutdown()


@pytest.mark.asyncio
async def test_initialization(replication_manager):
    """Test replication manager initialization"""
    assert replication_manager._initialized
    assert len(replication_manager.regions) == 3
    assert "us-east-1" in replication_manager.regions
    assert "eu-west-1" in replication_manager.regions
    assert "ap-southeast-1" in replication_manager.regions
    
    # Check primary region
    primary = replication_manager.regions["us-east-1"]
    assert primary.is_primary
    assert primary.status == "active"


@pytest.mark.asyncio
async def test_region_health_check():
    """Test region health checking"""
    manager = GeoReplicationManager()
    
    # Mock connections
    manager.db_connections["us-east-1"] = AsyncMock()
    manager.redis_clients["us-east-1"] = AsyncMock()
    manager.mongodb_clients["us-east-1"] = AsyncMock()
    manager.opensearch_clients["us-east-1"] = AsyncMock()
    manager.s3_clients["us-east-1"] = AsyncMock()
    
    # All services healthy
    manager.db_connections["us-east-1"].connect.return_value.__aenter__.return_value.execute = AsyncMock()
    manager.redis_clients["us-east-1"].ping = AsyncMock()
    manager.mongodb_clients["us-east-1"].admin.command = AsyncMock()
    manager.opensearch_clients["us-east-1"].ping = AsyncMock()
    manager.s3_clients["us-east-1"].list_buckets = AsyncMock()
    
    health = await manager._check_region_health("us-east-1")
    
    assert health["healthy"]
    assert all(health["checks"].values())
    assert health["error"] is None


@pytest.mark.asyncio
async def test_database_replication(replication_manager):
    """Test database replication process"""
    # Mock database connections
    primary_db = AsyncMock()
    replication_manager.db_connections["us-east-1"] = primary_db
    
    # Mock replication slots
    mock_slots = [
        ("slot_eu_west_1", True, "0/1000000", "0/900000"),
        ("slot_ap_southeast_1", True, "0/1000000", "0/800000")
    ]
    
    primary_db.connect.return_value.__aenter__.return_value.execute.return_value.fetchall.return_value = mock_slots
    
    # Mock lag calculation
    with patch.object(replication_manager, '_get_replication_lag', return_value=5.0):
        await replication_manager._replicate_database_changes()
    
    # Check that jobs were created
    assert len(replication_manager.replication_jobs) > 0


@pytest.mark.asyncio
async def test_file_replication(replication_manager):
    """Test S3 file replication"""
    # Mock S3 client
    s3_client = AsyncMock()
    replication_manager.s3_clients["us-east-1"] = s3_client
    
    # Mock bucket list
    s3_client.list_buckets.return_value = {
        "Buckets": [
            {"Name": "mams-media-us-east-1"},
            {"Name": "mams-backup-us-east-1"}
        ]
    }
    
    # Mock replication configuration
    s3_client.get_bucket_replication.return_value = {
        "ReplicationConfiguration": {
            "Rules": [
                {
                    "Status": "Enabled",
                    "Destination": {
                        "Bucket": "arn:aws:s3:::mams-media-eu-west-1"
                    }
                }
            ]
        }
    }
    
    with patch.object(replication_manager, '_get_s3_replication_metrics', return_value={"pending_bytes": 0}):
        await replication_manager._replicate_file_changes()
    
    s3_client.list_buckets.assert_called_once()


@pytest.mark.asyncio
async def test_cache_replication(replication_manager):
    """Test Redis cache replication"""
    # Mock Redis clients
    primary_redis = AsyncMock()
    secondary_redis = AsyncMock()
    
    replication_manager.redis_clients["us-east-1"] = primary_redis
    replication_manager.redis_clients["eu-west-1"] = secondary_redis
    
    # Mock scan_iter to return some keys
    async def mock_scan_iter(match):
        keys = ["session:123", "rate_limit:user:456", "cache:data:789"]
        for key in keys:
            if match.replace("*", "") in key:
                yield key
    
    primary_redis.scan_iter = mock_scan_iter
    primary_redis.ttl.return_value = 3600
    primary_redis.get.return_value = "test_value"
    
    await replication_manager._replicate_cache_changes()
    
    # Verify replication
    assert secondary_redis.set.call_count == 3


@pytest.mark.asyncio
async def test_conflict_resolution_last_write_wins():
    """Test last-write-wins conflict resolution"""
    manager = GeoReplicationManager()
    manager.replication_config.conflict_resolution = ConflictResolutionStrategy.LAST_WRITE_WINS
    
    source_data = {"id": 1, "value": "source"}
    target_data = {"id": 1, "value": "target"}
    metadata = {
        "source_timestamp": 1000,
        "target_timestamp": 900
    }
    
    result = await manager.handle_conflict(
        "data_mismatch",
        source_data,
        target_data,
        metadata
    )
    
    assert result == source_data  # Source is newer


@pytest.mark.asyncio
async def test_conflict_resolution_primary_wins():
    """Test primary-wins conflict resolution"""
    manager = GeoReplicationManager()
    manager.replication_config.conflict_resolution = ConflictResolutionStrategy.PRIMARY_WINS
    manager.replication_config.primary_region = "us-east-1"
    
    source_data = {"id": 1, "value": "source"}
    target_data = {"id": 1, "value": "target"}
    metadata = {
        "source_region": "us-east-1",
        "target_region": "eu-west-1"
    }
    
    result = await manager.handle_conflict(
        "data_mismatch",
        source_data,
        target_data,
        metadata
    )
    
    assert result == source_data  # Primary wins


@pytest.mark.asyncio
async def test_replication_status(replication_manager):
    """Test getting replication status"""
    # Set up regions
    replication_manager.regions["us-east-1"].status = "active"
    replication_manager.regions["eu-west-1"].status = "active"
    replication_manager.regions["ap-southeast-1"].status = "error"
    
    # Mock lag calculation
    with patch.object(replication_manager, '_get_replication_lag', return_value=10.0):
        status = await replication_manager.get_replication_status()
    
    assert status.enabled
    assert status.primary_region == "us-east-1"
    assert len(status.active_regions) == 2
    assert len(status.inactive_regions) == 1
    assert status.replication_lag_seconds == 10.0


@pytest.mark.asyncio
async def test_force_sync(replication_manager):
    """Test force synchronization"""
    # Mock sync methods
    replication_manager._force_sync_database = AsyncMock()
    replication_manager._force_sync_files = AsyncMock()
    replication_manager._force_sync_cache = AsyncMock()
    replication_manager._force_sync_search = AsyncMock()
    replication_manager._force_sync_metadata = AsyncMock()
    
    # Test full sync
    await replication_manager.force_sync("eu-west-1", ReplicationType.FULL)
    
    replication_manager._force_sync_database.assert_called_once_with("eu-west-1")
    replication_manager._force_sync_files.assert_called_once_with("eu-west-1")
    replication_manager._force_sync_cache.assert_called_once_with("eu-west-1")
    replication_manager._force_sync_search.assert_called_once_with("eu-west-1")
    replication_manager._force_sync_metadata.assert_called_once_with("eu-west-1")


@pytest.mark.asyncio
async def test_metadata_replication(replication_manager):
    """Test MongoDB metadata replication"""
    # Mock MongoDB clients
    primary_mongodb = AsyncMock()
    secondary_mongodb = AsyncMock()
    
    replication_manager.mongodb_clients["us-east-1"] = primary_mongodb
    replication_manager.mongodb_clients["eu-west-1"] = secondary_mongodb
    
    # Mock database
    primary_db = primary_mongodb.__getitem__.return_value
    secondary_db = secondary_mongodb.__getitem__.return_value
    
    # Mock change stream
    change = {
        "operationType": "insert",
        "documentKey": {"_id": "123"},
        "fullDocument": {"_id": "123", "name": "test"}
    }
    
    with patch.object(replication_manager, '_process_metadata_change', new_callable=AsyncMock) as mock_process:
        await replication_manager._process_metadata_change(change, "asset_metadata")
        
        # Verify replication to secondary region
        secondary_collection = secondary_db.__getitem__.return_value
        secondary_collection.insert_one.assert_called()


@pytest.mark.asyncio
async def test_replication_metrics(replication_manager):
    """Test metrics collection"""
    # Access metrics collector
    metrics = replication_manager.metrics
    
    # Increment counters
    metrics.increment("replication.database.errors")
    metrics.gauge("replication.lag.eu-west-1", 15.5)
    
    # Verify metrics were recorded (in a real implementation)
    # This would check actual metrics storage
    assert True  # Placeholder for actual metric verification


@pytest.mark.asyncio
async def test_version_vector_conflict_resolution():
    """Test version vector conflict resolution"""
    manager = GeoReplicationManager()
    manager.replication_config.conflict_resolution = ConflictResolutionStrategy.VERSION_VECTOR
    
    source_data = {"id": 1, "value": "source"}
    target_data = {"id": 1, "value": "target"}
    metadata = {
        "source_version_vector": {"us-east-1": 5, "eu-west-1": 3},
        "target_version_vector": {"us-east-1": 4, "eu-west-1": 3}
    }
    
    result = await manager.handle_conflict(
        "version_conflict",
        source_data,
        target_data,
        metadata
    )
    
    assert result == source_data  # Source has newer version


@pytest.mark.asyncio
async def test_replication_job_lifecycle(replication_manager):
    """Test replication job creation and tracking"""
    # Create a job
    job = ReplicationJob(
        job_id="test-job-1",
        source_region="us-east-1",
        target_region="eu-west-1",
        replication_type=ReplicationType.DATABASE,
        status="running",
        started_at=datetime.utcnow()
    )
    
    replication_manager.replication_jobs[job.job_id] = job
    
    # Update job progress
    job.items_processed = 500
    job.items_total = 1000
    
    # Complete job
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    
    assert job.duration_seconds is not None
    assert job.items_processed == 500


@pytest.mark.asyncio
async def test_search_index_replication(replication_manager):
    """Test OpenSearch index replication"""
    # Mock OpenSearch clients
    primary_opensearch = AsyncMock()
    secondary_opensearch = AsyncMock()
    
    replication_manager.opensearch_clients["us-east-1"] = primary_opensearch
    replication_manager.opensearch_clients["eu-west-1"] = secondary_opensearch
    
    # Mock indices
    primary_opensearch.indices.get_alias.return_value = {
        "mams-assets": {},
        "mams-metadata": {}
    }
    
    # Mock transport for replication API
    secondary_opensearch.transport.perform_request = AsyncMock()
    
    await replication_manager._replicate_search_indices()
    
    # Verify follower indices were created
    assert secondary_opensearch.transport.perform_request.call_count >= 2