"""
Test Main Ingest Service

Tests for the core ingest service that handles file ingestion processing.
"""

import pytest
import asyncio
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import uuid

from src.services.ingest_service import IngestService, get_ingest_service
from src.models.schemas import (
    IngestJob, IngestJobCreate, IngestJobUpdate, IngestJobList,
    IngestStats, IngestStatus, BulkIngestRequest, FileMetadata,
    TechnicalMetadata, CameraMetadata, ValidationResult
)
from src.core.exceptions import (
    IngestServiceError, FileNotFoundError, ValidationError,
    UnsupportedFormatError, FileSizeError
)


class MockValidationResult:
    """Mock validation result."""
    def __init__(self, is_valid=True, errors=None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.file_path = ""
    
    def __str__(self):
        return self.file_path


class TestIngestService:
    """Test cases for IngestService."""
    
    @pytest.fixture
    def validation_service(self):
        """Create mock validation service."""
        service = Mock()
        service.validate_file = AsyncMock()
        return service
    
    @pytest.fixture
    def metadata_service(self):
        """Create mock metadata service."""
        service = Mock()
        service.extract_file_metadata = AsyncMock()
        service.extract_technical_metadata = AsyncMock()
        service.extract_camera_metadata = AsyncMock()
        return service
    
    @pytest.fixture
    def storage_client(self):
        """Create mock storage client."""
        client = Mock()
        client.upload_file = AsyncMock()
        return client
    
    @pytest.fixture
    def queue_service(self):
        """Create mock queue service."""
        service = Mock()
        service.publish_ingest_job = AsyncMock()
        service.publish_proxy_request = AsyncMock()
        return service
    
    @pytest.fixture
    def service(self, validation_service, metadata_service, storage_client, queue_service):
        """Create ingest service instance with mocked dependencies."""
        service = IngestService()
        service.validation_service = validation_service
        service.metadata_service = metadata_service
        service.storage_client = storage_client
        service.queue_service = queue_service
        return service
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        file_path = tmp_path / "test_file.mp4"
        file_path.write_bytes(b"test video content" * 1000)
        return str(file_path)
    
    @pytest.fixture
    def temp_directory(self, tmp_path):
        """Create a temporary directory with test files."""
        test_dir = tmp_path / "test_ingest"
        test_dir.mkdir()
        
        # Create some test files
        (test_dir / "video1.mp4").write_bytes(b"video content 1" * 100)
        (test_dir / "video2.mp4").write_bytes(b"video content 2" * 100)
        (test_dir / "document.pdf").write_bytes(b"pdf content" * 50)
        
        # Create subdirectory
        sub_dir = test_dir / "subfolder"
        sub_dir.mkdir()
        (sub_dir / "video3.mp4").write_bytes(b"video content 3" * 100)
        
        return str(test_dir)
    
    async def test_create_job_single_file(self, service, temp_file, queue_service):
        """Test creating an ingest job for a single file."""
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123",
            tags=["test", "video"],
            priority=5
        )
        
        job = await service.create_job(job_request)
        
        # Assertions
        assert job.source_path == temp_file
        assert job.destination_project_id == "project123"
        assert job.tags == ["test", "video"]
        assert job.priority == 5
        assert job.total_files == 1
        assert job.total_size > 0
        assert job.status == IngestStatus.PENDING
        assert job.id in service._jobs
        
        # Verify job was queued
        queue_service.publish_ingest_job.assert_called_once_with(job)
    
    async def test_create_job_directory(self, service, temp_directory, queue_service):
        """Test creating an ingest job for a directory."""
        job_request = IngestJobCreate(
            source_path=temp_directory,
            destination_project_id="project123",
            preserve_folder_structure=True
        )
        
        job = await service.create_job(job_request)
        
        # Assertions
        assert job.source_path == temp_directory
        assert job.total_files == 4  # 3 videos + 1 pdf
        assert job.total_size > 0
        assert job.preserve_folder_structure is True
    
    async def test_create_job_nonexistent_path(self, service):
        """Test creating job with non-existent path."""
        job_request = IngestJobCreate(
            source_path="/nonexistent/path",
            destination_project_id="project123"
        )
        
        with pytest.raises(IngestServiceError, match="Failed to create ingest job"):
            await service.create_job(job_request)
    
    async def test_process_job_single_file_success(self, service, temp_file, validation_service, 
                                                   metadata_service, storage_client):
        """Test successful processing of single file job."""
        # Create job first
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123",
            auto_generate_proxies=True
        )
        job = await service.create_job(job_request)
        
        # Setup mocks
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        
        file_metadata = FileMetadata(
            file_name="test_file.mp4",
            file_size=1000,
            file_type="video",
            mime_type="video/mp4"
        )
        metadata_service.extract_file_metadata.return_value = file_metadata
        
        technical_metadata = TechnicalMetadata(
            video_codec="h264",
            resolution="1920x1080",
            frame_rate=30.0,
            duration=120.0
        )
        metadata_service.extract_technical_metadata.return_value = technical_metadata
        
        camera_metadata = CameraMetadata(
            camera_model="Sony FX6",
            lens="24-70mm",
            iso=800
        )
        metadata_service.extract_camera_metadata.return_value = camera_metadata
        
        storage_client.upload_file.return_value = "asset123"
        
        # Process job
        await service.process_job(job.id)
        
        # Assertions
        assert job.status == IngestStatus.COMPLETED
        assert job.processed_files == 1
        assert job.created_assets == ["asset123"]
        assert job.file_metadata == file_metadata
        assert job.technical_metadata == technical_metadata
        assert job.camera_metadata == camera_metadata
        assert job.progress_percentage == 100.0
        
        # Verify proxy generation was requested
        service.queue_service.publish_proxy_request.assert_called_once()
    
    async def test_process_job_validation_failure(self, service, temp_file, validation_service):
        """Test job processing with validation failure."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Setup validation to fail
        validation_service.validate_file.return_value = MockValidationResult(
            is_valid=False,
            errors=["Invalid format", "File corrupted"]
        )
        
        # Process job
        await service.process_job(job.id)
        
        # Assertions
        assert job.status == IngestStatus.FAILED
        assert len(job.errors) > 0
        assert "File validation failed" in job.errors[0]
    
    async def test_process_job_directory(self, service, temp_directory, validation_service,
                                       storage_client):
        """Test processing directory job."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_directory,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Setup mocks - all files valid
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        
        # Mock storage uploads
        storage_client.upload_file.side_effect = ["asset1", "asset2", "asset3", "asset4"]
        
        # Process job
        await service.process_job(job.id)
        
        # Assertions
        assert job.status == IngestStatus.COMPLETED
        assert job.processed_files == 4
        assert len(job.created_assets) == 4
        assert storage_client.upload_file.call_count == 4
    
    async def test_process_job_partial_failure(self, service, temp_directory, validation_service,
                                             storage_client):
        """Test processing with some files failing."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_directory,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Setup mocks - some files invalid
        validation_results = [
            MockValidationResult(is_valid=True),
            MockValidationResult(is_valid=False, errors=["Invalid format"]),
            MockValidationResult(is_valid=True),
            MockValidationResult(is_valid=True)
        ]
        validation_service.validate_file.side_effect = validation_results
        
        # Storage uploads for valid files
        storage_client.upload_file.side_effect = ["asset1", "asset2", "asset3"]
        
        # Process job
        await service.process_job(job.id)
        
        # Should complete with warnings
        assert job.status == IngestStatus.COMPLETED
        assert len(job.warnings) > 0
        assert job.processed_files < job.total_files
    
    async def test_get_job(self, service, temp_file):
        """Test getting a job by ID."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123"
        )
        created_job = await service.create_job(job_request)
        
        # Get job
        retrieved_job = await service.get_job(created_job.id)
        
        assert retrieved_job == created_job
        assert retrieved_job.id == created_job.id
        
        # Test non-existent job
        assert await service.get_job("nonexistent") is None
    
    async def test_list_jobs_pagination(self, service, temp_file):
        """Test listing jobs with pagination."""
        # Create multiple jobs
        for i in range(25):
            job_request = IngestJobCreate(
                source_path=temp_file,
                destination_project_id=f"project{i}"
            )
            await service.create_job(job_request)
        
        # Test first page
        result = await service.list_jobs(page=1, per_page=10)
        assert len(result.jobs) == 10
        assert result.total == 25
        assert result.total_pages == 3
        assert result.page == 1
        
        # Test second page
        result = await service.list_jobs(page=2, per_page=10)
        assert len(result.jobs) == 10
        assert result.page == 2
        
        # Test last page
        result = await service.list_jobs(page=3, per_page=10)
        assert len(result.jobs) == 5
    
    async def test_list_jobs_filter_by_status(self, service, temp_file, validation_service):
        """Test listing jobs filtered by status."""
        # Create jobs with different statuses
        jobs = []
        for i in range(3):
            job_request = IngestJobCreate(
                source_path=temp_file,
                destination_project_id=f"project{i}"
            )
            job = await service.create_job(job_request)
            jobs.append(job)
        
        # Mark some as completed
        jobs[0].status = IngestStatus.COMPLETED
        jobs[1].status = IngestStatus.FAILED
        
        # Test filtering
        result = await service.list_jobs(status=IngestStatus.COMPLETED)
        assert len(result.jobs) == 1
        assert result.jobs[0].status == IngestStatus.COMPLETED
        
        result = await service.list_jobs(status=IngestStatus.FAILED)
        assert len(result.jobs) == 1
        assert result.jobs[0].status == IngestStatus.FAILED
        
        result = await service.list_jobs(status=IngestStatus.PENDING)
        assert len(result.jobs) == 1
    
    async def test_update_job(self, service, temp_file):
        """Test updating a job."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Update job
        update_data = IngestJobUpdate(
            status=IngestStatus.PROCESSING,
            progress_percentage=50.0,
            current_operation="Processing files",
            metadata={"custom": "value"}
        )
        
        updated_job = await service.update_job(job.id, update_data)
        
        # Assertions
        assert updated_job.status == IngestStatus.PROCESSING
        assert updated_job.progress_percentage == 50.0
        assert updated_job.current_operation == "Processing files"
        assert updated_job.metadata_override["custom"] == "value"
        assert updated_job.updated_at > job.created_at
    
    async def test_cancel_job(self, service, temp_file):
        """Test cancelling a job."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Cancel job
        result = await service.cancel_job(job.id)
        assert result is True
        assert job.status == IngestStatus.CANCELLED
        assert job.completed_at is not None
        
        # Try to cancel already cancelled job
        result = await service.cancel_job(job.id)
        assert result is False
        
        # Try to cancel non-existent job
        result = await service.cancel_job("nonexistent")
        assert result is False
    
    async def test_create_bulk_jobs(self, service, temp_file, temp_directory):
        """Test creating multiple jobs in bulk."""
        bulk_request = BulkIngestRequest(
            source_paths=[temp_file, temp_directory],
            destination_project_id="project123",
            tags=["bulk", "test"],
            auto_generate_proxies=True
        )
        
        jobs = await service.create_bulk_jobs(bulk_request)
        
        # Assertions
        assert len(jobs) == 2
        assert all(job.destination_project_id == "project123" for job in jobs)
        assert all(job.tags == ["bulk", "test"] for job in jobs)
        assert all(job.auto_generate_proxies for job in jobs)
    
    async def test_get_stats(self, service, temp_file):
        """Test getting service statistics."""
        # Create some jobs
        for i in range(5):
            job_request = IngestJobCreate(
                source_path=temp_file,
                destination_project_id=f"project{i}"
            )
            job = await service.create_job(job_request)
            
            # Simulate different statuses
            if i < 2:
                job.status = IngestStatus.COMPLETED
                job.started_at = datetime.utcnow()
                job.completed_at = datetime.utcnow()
            elif i == 2:
                job.status = IngestStatus.FAILED
            elif i == 3:
                job.status = IngestStatus.PROCESSING
                service._active_jobs += 1
        
        stats = await service.get_stats()
        
        # Assertions
        assert stats.total_jobs == 5
        assert stats.completed_jobs == 2
        assert stats.failed_jobs == 1
        assert stats.active_jobs == 1
        assert stats.success_rate == 0.4  # 2/5
        assert stats.average_processing_time >= 0
    
    async def test_metadata_extraction_failure_non_critical(self, service, temp_file,
                                                           validation_service, metadata_service,
                                                           storage_client):
        """Test that metadata extraction failure doesn't fail the job."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Setup mocks
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        metadata_service.extract_file_metadata.side_effect = Exception("Metadata error")
        storage_client.upload_file.return_value = "asset123"
        
        # Process job
        await service.process_job(job.id)
        
        # Job should complete with warnings
        assert job.status == IngestStatus.COMPLETED
        assert len(job.warnings) > 0
        assert "Metadata extraction failed" in job.warnings[0]
        assert job.created_assets == ["asset123"]
    
    async def test_proxy_generation_failure_non_critical(self, service, temp_file,
                                                       validation_service, storage_client,
                                                       queue_service):
        """Test that proxy generation failure doesn't fail the job."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_file,
            destination_project_id="project123",
            auto_generate_proxies=True
        )
        job = await service.create_job(job_request)
        
        # Setup mocks
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        storage_client.upload_file.return_value = "asset123"
        queue_service.publish_proxy_request.side_effect = Exception("Queue error")
        
        # Process job
        await service.process_job(job.id)
        
        # Job should complete with warnings
        assert job.status == IngestStatus.COMPLETED
        assert len(job.warnings) > 0
        assert "Failed to request proxy generation" in job.warnings[0]
    
    async def test_concurrent_job_processing(self, service, temp_file, validation_service,
                                           storage_client):
        """Test processing multiple jobs concurrently."""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job_request = IngestJobCreate(
                source_path=temp_file,
                destination_project_id=f"project{i}"
            )
            job = await service.create_job(job_request)
            jobs.append(job)
        
        # Setup mocks
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        storage_client.upload_file.side_effect = ["asset1", "asset2", "asset3"]
        
        # Process jobs concurrently
        tasks = [service.process_job(job.id) for job in jobs]
        await asyncio.gather(*tasks)
        
        # All jobs should complete
        for job in jobs:
            assert job.status == IngestStatus.COMPLETED
            assert job.processed_files == 1
    
    async def test_directory_stats_calculation(self, service, temp_directory):
        """Test calculation of directory statistics."""
        total_files, total_size = await service._calculate_directory_stats(temp_directory)
        
        assert total_files == 4  # 3 videos + 1 pdf
        assert total_size > 0
    
    async def test_get_ingest_service_singleton(self):
        """Test that get_ingest_service returns singleton."""
        service1 = await get_ingest_service()
        service2 = await get_ingest_service()
        
        assert service1 is service2
    
    async def test_job_progress_tracking(self, service, temp_directory, validation_service,
                                       storage_client):
        """Test progress tracking during job processing."""
        # Create job
        job_request = IngestJobCreate(
            source_path=temp_directory,
            destination_project_id="project123"
        )
        job = await service.create_job(job_request)
        
        # Track progress updates
        progress_values = []
        original_progress_setter = job.__class__.progress_percentage.fset
        
        def track_progress(self, value):
            progress_values.append(value)
            original_progress_setter(self, value)
        
        type(job).progress_percentage = property(
            fget=job.__class__.progress_percentage.fget,
            fset=track_progress
        )
        
        # Setup mocks
        validation_service.validate_file.return_value = MockValidationResult(is_valid=True)
        storage_client.upload_file.return_value = "asset"
        
        # Process job
        await service.process_job(job.id)
        
        # Progress should increase
        assert len(progress_values) > 0
        assert progress_values[-1] == 100.0
        assert all(progress_values[i] <= progress_values[i+1] 
                  for i in range(len(progress_values)-1))