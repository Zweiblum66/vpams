"""
Tests for the Scheduler Service
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.scheduler_service import SchedulerService
from src.services.ingest_service import IngestService
from src.models.schemas import (
    ScheduledIngestConfig, IngestJobCreate, IngestType, IngestPriority
)
from src.core.exceptions import SchedulerError


@pytest.fixture
async def mock_ingest_service():
    """Create a mock ingest service"""
    service = Mock(spec=IngestService)
    service.create_job = Mock()
    service.process_job = Mock()
    return service


@pytest.fixture
async def scheduler_service(mock_ingest_service):
    """Create a scheduler service with mock dependencies"""
    service = SchedulerService()
    await service.initialize(mock_ingest_service)
    yield service
    await service.shutdown()


@pytest.fixture
def sample_scheduled_ingest():
    """Create a sample scheduled ingest configuration"""
    return ScheduledIngestConfig(
        name="Daily News Archive Ingest",
        source_path="/watch/news/archive",
        destination_project_id="news-project-123",
        cron_expression="0 2 * * *",  # Every day at 2 AM
        enabled=True,
        metadata_template={
            "category": "news",
            "retention_policy": "30_days"
        },
        tags=["automated", "news", "archive"],
        priority=IngestPriority.NORMAL,
        auto_generate_proxies=True,
        preserve_folder_structure=True
    )


class TestSchedulerService:
    """Test suite for scheduler service"""
    
    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, mock_ingest_service):
        """Test scheduler service initialization"""
        service = SchedulerService()
        assert not service._is_running
        
        await service.initialize(mock_ingest_service)
        assert service._is_running
        assert service.scheduler.running
        
        await service.shutdown()
        assert not service._is_running
    
    @pytest.mark.asyncio
    async def test_create_scheduled_ingest(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test creating a scheduled ingest configuration"""
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        assert config.id is not None
        assert config.name == sample_scheduled_ingest.name
        assert config.cron_expression == sample_scheduled_ingest.cron_expression
        assert config.enabled == True
        
        # Check that it's stored
        stored_config = await scheduler_service.get_scheduled_ingest(config.id)
        assert stored_config is not None
        assert stored_config.name == config.name
    
    @pytest.mark.asyncio
    async def test_create_scheduled_ingest_invalid_cron(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test creating scheduled ingest with invalid cron expression"""
        sample_scheduled_ingest.cron_expression = "invalid cron"
        
        with pytest.raises(SchedulerError, match="Invalid cron expression"):
            await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
    
    @pytest.mark.asyncio
    async def test_list_scheduled_ingests(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test listing scheduled ingests"""
        # Initially empty
        ingests = await scheduler_service.list_scheduled_ingests()
        assert len(ingests) == 0
        
        # Create one
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Should have one
        ingests = await scheduler_service.list_scheduled_ingests()
        assert len(ingests) == 1
        assert ingests[0].id == config.id
    
    @pytest.mark.asyncio
    async def test_update_scheduled_ingest(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test updating a scheduled ingest configuration"""
        # Create
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Update
        config.name = "Updated Name"
        config.cron_expression = "0 3 * * *"  # 3 AM instead of 2 AM
        config.enabled = False
        
        updated_config = await scheduler_service.update_scheduled_ingest(
            config.id, config
        )
        
        assert updated_config is not None
        assert updated_config.name == "Updated Name"
        assert updated_config.cron_expression == "0 3 * * *"
        assert updated_config.enabled == False
    
    @pytest.mark.asyncio
    async def test_delete_scheduled_ingest(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test deleting a scheduled ingest configuration"""
        # Create
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Verify exists
        stored_config = await scheduler_service.get_scheduled_ingest(config.id)
        assert stored_config is not None
        
        # Delete
        success = await scheduler_service.delete_scheduled_ingest(config.id)
        assert success == True
        
        # Verify deleted
        stored_config = await scheduler_service.get_scheduled_ingest(config.id)
        assert stored_config is None
    
    @pytest.mark.asyncio
    async def test_manual_scheduled_ingest_execution(
        self,
        scheduler_service,
        sample_scheduled_ingest,
        mock_ingest_service
    ):
        """Test manually triggering a scheduled ingest"""
        from fastapi import BackgroundTasks
        
        # Create scheduled ingest
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Mock the ingest service calls
        mock_job = Mock()
        mock_job.id = "test-job-123"
        mock_ingest_service.create_job.return_value = mock_job
        mock_ingest_service.process_job.return_value = None
        
        # Trigger manual execution
        background_tasks = BackgroundTasks()
        success = await scheduler_service.run_scheduled_ingest(
            config.id,
            background_tasks
        )
        
        assert success == True
        # Note: In real test, we'd check that background task was added
    
    @pytest.mark.asyncio
    async def test_scheduled_ingest_execution_flow(
        self,
        scheduler_service,
        sample_scheduled_ingest,
        mock_ingest_service
    ):
        """Test the scheduled ingest execution flow"""
        # Mock the ingest service calls
        mock_job = Mock()
        mock_job.id = "test-job-123"
        mock_ingest_service.create_job.return_value = mock_job
        mock_ingest_service.process_job.return_value = None
        
        # Create scheduled ingest
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Execute the scheduled ingest directly
        await scheduler_service._execute_scheduled_ingest(config)
        
        # Verify ingest service was called correctly
        mock_ingest_service.create_job.assert_called_once()
        call_args = mock_ingest_service.create_job.call_args[0][0]
        
        assert isinstance(call_args, IngestJobCreate)
        assert call_args.source_path == sample_scheduled_ingest.source_path
        assert call_args.destination_project_id == sample_scheduled_ingest.destination_project_id
        assert call_args.ingest_type == IngestType.SCHEDULED
        assert call_args.metadata_override == sample_scheduled_ingest.metadata_template
        assert call_args.tags == sample_scheduled_ingest.tags
        assert call_args.priority == sample_scheduled_ingest.priority
        
        mock_ingest_service.process_job.assert_called_once_with(mock_job.id)
    
    @pytest.mark.asyncio
    async def test_scheduler_stats(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test getting scheduler statistics"""
        # Get initial stats
        stats = await scheduler_service.get_scheduler_stats()
        
        assert stats["is_running"] == True
        assert stats["total_scheduled_ingests"] == 0
        assert stats["active_scheduled_ingests"] == 0
        assert stats["scheduled_jobs"] == 0
        
        # Create scheduled ingest
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Get updated stats
        stats = await scheduler_service.get_scheduler_stats()
        
        assert stats["total_scheduled_ingests"] == 1
        assert stats["active_scheduled_ingests"] == 1
        assert stats["scheduled_jobs"] == 1  # One job should be scheduled
    
    @pytest.mark.asyncio
    async def test_cron_job_scheduling(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test that cron jobs are properly scheduled"""
        # Create scheduled ingest
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Check that job is scheduled in APScheduler
        job_id = f"scheduled_ingest_{config.id}"
        scheduled_job = scheduler_service.scheduler.get_job(job_id)
        
        assert scheduled_job is not None
        assert scheduled_job.id == job_id
        assert scheduled_job.name == f"Scheduled Ingest: {config.name}"
        
        # Disable the scheduled ingest
        config.enabled = False
        await scheduler_service.update_scheduled_ingest(config.id, config)
        
        # Job should be removed
        scheduled_job = scheduler_service.scheduler.get_job(job_id)
        assert scheduled_job is None
    
    @pytest.mark.asyncio
    async def test_multiple_scheduled_ingests(
        self,
        scheduler_service,
        sample_scheduled_ingest
    ):
        """Test managing multiple scheduled ingests"""
        # Create multiple scheduled ingests
        configs = []
        for i in range(3):
            config = ScheduledIngestConfig(
                name=f"Scheduled Ingest {i+1}",
                source_path=f"/watch/folder{i+1}",
                destination_project_id=f"project-{i+1}",
                cron_expression=f"0 {i+1} * * *",  # Different hours
                enabled=True
            )
            created_config = await scheduler_service.create_scheduled_ingest(config)
            configs.append(created_config)
        
        # List all
        all_ingests = await scheduler_service.list_scheduled_ingests()
        assert len(all_ingests) == 3
        
        # Check that all jobs are scheduled
        stats = await scheduler_service.get_scheduler_stats()
        assert stats["total_scheduled_ingests"] == 3
        assert stats["active_scheduled_ingests"] == 3
        assert stats["scheduled_jobs"] == 3
    
    @pytest.mark.asyncio
    async def test_scheduler_error_handling(
        self,
        scheduler_service,
        sample_scheduled_ingest,
        mock_ingest_service
    ):
        """Test error handling in scheduled execution"""
        # Mock ingest service to raise error
        mock_ingest_service.create_job.side_effect = Exception("Ingest service error")
        
        config = await scheduler_service.create_scheduled_ingest(sample_scheduled_ingest)
        
        # Execute scheduled ingest - should handle error gracefully
        await scheduler_service._execute_scheduled_ingest(config)
        
        # Last execution time should still be updated even on failure
        updated_config = await scheduler_service.get_scheduled_ingest(config.id)
        assert updated_config.last_execution is not None


class TestSchedulerIntegration:
    """Integration tests for scheduler service"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_scheduled_ingest(
        self,
        mock_ingest_service
    ):
        """Test complete end-to-end scheduled ingest flow"""
        scheduler_service = SchedulerService()
        
        try:
            await scheduler_service.initialize(mock_ingest_service)
            
            # Create a scheduled ingest that runs every 5 seconds (for testing)
            config = ScheduledIngestConfig(
                name="Test Integration",
                source_path="/test/path",
                destination_project_id="test-project",
                cron_expression="*/5 * * * * *",  # Every 5 seconds (for quick testing)
                enabled=True,
                metadata_template={"test": True},
                tags=["integration-test"],
                priority=IngestPriority.HIGH
            )
            
            created_config = await scheduler_service.create_scheduled_ingest(config)
            
            # Mock the ingest service
            mock_job = Mock()
            mock_job.id = "integration-test-job"
            mock_ingest_service.create_job.return_value = mock_job
            mock_ingest_service.process_job.return_value = None
            
            # Wait a bit and check if job gets executed
            # Note: In a real test environment, you might want to use a shorter interval
            # or mock the scheduler to trigger immediately
            
            # For this test, we'll just verify the configuration is correct
            stored_config = await scheduler_service.get_scheduled_ingest(created_config.id)
            assert stored_config is not None
            assert stored_config.name == config.name
            assert stored_config.enabled == True
            
            # Verify job is scheduled
            job_id = f"scheduled_ingest_{created_config.id}"
            scheduled_job = scheduler_service.scheduler.get_job(job_id)
            assert scheduled_job is not None
            
        finally:
            await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_scheduler_service_lifecycle():
    """Test the complete lifecycle of scheduler service"""
    service = SchedulerService()
    
    # Initially not running
    assert not service._is_running
    
    # Initialize
    mock_ingest_service = Mock(spec=IngestService)
    await service.initialize(mock_ingest_service)
    assert service._is_running
    assert service.scheduler.running
    
    # Shutdown
    await service.shutdown()
    assert not service._is_running
    assert not service.scheduler.running