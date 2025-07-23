"""
Test Live Ingest Service

Tests for handling real-time media streams and growing files.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.services.live_ingest_service import (
    LiveIngestService,
    LiveStreamMonitor,
    GrowingFileMonitor,
    get_live_ingest_service
)
from src.models.schemas import (
    IngestJob, IngestJobCreate, IngestType, IngestStatus, 
    IngestPriority, FileMetadata
)
from src.core.exceptions import LiveIngestError, ValidationError


class TestLiveIngestService:
    """Test cases for LiveIngestService."""
    
    @pytest.fixture
    def service(self):
        """Create LiveIngestService instance."""
        return LiveIngestService()
    
    @pytest.fixture
    def valid_stream_url(self):
        """Valid stream URL for testing."""
        return "rtmp://example.com/live/stream"
    
    @pytest.fixture
    def invalid_stream_url(self):
        """Invalid stream URL for testing."""
        return "invalid://stream"
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    async def test_init(self, service):
        """Test service initialization."""
        assert service.active_streams == {}
        assert service.growing_files == {}
        assert service.monitoring_tasks == set()
        assert service.stream_check_interval == 5.0
        assert service.file_stability_timeout == 30.0
        assert service.max_stream_retry_attempts == 3
    
    async def test_start_live_stream_ingest_success(self, service, valid_stream_url):
        """Test successful live stream ingest start."""
        project_id = "project123"
        metadata = {"title": "Live Stream Test"}
        tags = ["live", "test"]
        
        job = await service.start_live_stream_ingest(
            stream_url=valid_stream_url,
            destination_project_id=project_id,
            metadata_override=metadata,
            tags=tags
        )
        
        assert job is not None
        assert job.source_path == valid_stream_url
        assert job.ingest_type == IngestType.LIVE_STREAM
        assert job.status == IngestStatus.PROCESSING
        assert job.current_operation == "Connecting to stream"
        assert job.metadata_override == metadata
        assert job.tags == tags
        assert job.priority == IngestPriority.HIGH
        assert job.auto_generate_proxies is True
        
        # Verify monitor was created
        assert job.id in service.active_streams
        assert len(service.monitoring_tasks) == 1
    
    async def test_start_live_stream_ingest_invalid_url(self, service, invalid_stream_url):
        """Test live stream ingest with invalid URL."""
        with pytest.raises(LiveIngestError, match="Invalid stream URL"):
            await service.start_live_stream_ingest(stream_url=invalid_stream_url)
    
    async def test_start_live_stream_ingest_exception(self, service, valid_stream_url):
        """Test live stream ingest with exception."""
        with patch.object(service, '_validate_stream_url', side_effect=Exception("Test error")):
            with pytest.raises(LiveIngestError, match="Failed to start live stream ingest"):
                await service.start_live_stream_ingest(stream_url=valid_stream_url)
    
    async def test_start_growing_file_ingest_success(self, service, temp_file):
        """Test successful growing file ingest start."""
        project_id = "project123"
        metadata = {"title": "Growing File Test"}
        tags = ["growing", "test"]
        timeout = 600
        
        job = await service.start_growing_file_ingest(
            file_path=temp_file,
            destination_project_id=project_id,
            growing_file_timeout=timeout,
            metadata_override=metadata,
            tags=tags
        )
        
        assert job is not None
        assert job.source_path == temp_file
        assert job.ingest_type == IngestType.LIVE_STREAM
        assert job.status == IngestStatus.PROCESSING
        assert job.current_operation == "Monitoring growing file"
        assert job.metadata_override == metadata
        assert job.tags == tags
        assert job.priority == IngestPriority.HIGH
        assert job.auto_generate_proxies is True
        
        # Verify monitor was created
        assert job.id in service.growing_files
        assert len(service.monitoring_tasks) == 1
    
    async def test_start_growing_file_ingest_file_not_found(self, service):
        """Test growing file ingest with non-existent file."""
        non_existent_file = "/path/to/nonexistent/file.mp4"
        
        with pytest.raises(LiveIngestError, match="File not found"):
            await service.start_growing_file_ingest(file_path=non_existent_file)
    
    async def test_start_growing_file_ingest_exception(self, service, temp_file):
        """Test growing file ingest with exception."""
        with patch('os.path.exists', side_effect=Exception("Test error")):
            with pytest.raises(LiveIngestError, match="Failed to start growing file ingest"):
                await service.start_growing_file_ingest(file_path=temp_file)
    
    async def test_stop_live_ingest_stream(self, service, valid_stream_url):
        """Test stopping a live stream ingest."""
        # Start ingest
        job = await service.start_live_stream_ingest(stream_url=valid_stream_url)
        job_id = job.id
        
        # Mock the stream monitor's stop_monitoring method
        stream_monitor = service.active_streams[job_id]
        stream_monitor.stop_monitoring = AsyncMock()
        
        # Stop ingest
        result = await service.stop_live_ingest(job_id)
        
        assert result is True
        assert job_id not in service.active_streams
        stream_monitor.stop_monitoring.assert_called_once()
    
    async def test_stop_live_ingest_file(self, service, temp_file):
        """Test stopping a growing file ingest."""
        # Start ingest
        job = await service.start_growing_file_ingest(file_path=temp_file)
        job_id = job.id
        
        # Mock the file monitor's stop_monitoring method
        file_monitor = service.growing_files[job_id]
        file_monitor.stop_monitoring = AsyncMock()
        
        # Stop ingest
        result = await service.stop_live_ingest(job_id)
        
        assert result is True
        assert job_id not in service.growing_files
        file_monitor.stop_monitoring.assert_called_once()
    
    async def test_stop_live_ingest_not_found(self, service):
        """Test stopping a non-existent ingest."""
        result = await service.stop_live_ingest("non_existent_job")
        assert result is False
    
    async def test_stop_live_ingest_exception(self, service, valid_stream_url):
        """Test stopping ingest with exception."""
        # Start ingest
        job = await service.start_live_stream_ingest(stream_url=valid_stream_url)
        job_id = job.id
        
        # Mock to raise exception
        stream_monitor = service.active_streams[job_id]
        stream_monitor.stop_monitoring = AsyncMock(side_effect=Exception("Stop error"))
        
        # Should handle exception and return False
        result = await service.stop_live_ingest(job_id)
        assert result is False
    
    async def test_get_live_ingest_status_stream(self, service, valid_stream_url):
        """Test getting live stream ingest status."""
        # Start ingest
        job = await service.start_live_stream_ingest(stream_url=valid_stream_url)
        job_id = job.id
        
        # Mock get_status method
        expected_status = {"job_id": job_id, "type": "live_stream"}
        stream_monitor = service.active_streams[job_id]
        stream_monitor.get_status = AsyncMock(return_value=expected_status)
        
        # Get status
        status = await service.get_live_ingest_status(job_id)
        
        assert status == expected_status
        stream_monitor.get_status.assert_called_once()
    
    async def test_get_live_ingest_status_file(self, service, temp_file):
        """Test getting growing file ingest status."""
        # Start ingest
        job = await service.start_growing_file_ingest(file_path=temp_file)
        job_id = job.id
        
        # Mock get_status method
        expected_status = {"job_id": job_id, "type": "growing_file"}
        file_monitor = service.growing_files[job_id]
        file_monitor.get_status = AsyncMock(return_value=expected_status)
        
        # Get status
        status = await service.get_live_ingest_status(job_id)
        
        assert status == expected_status
        file_monitor.get_status.assert_called_once()
    
    async def test_get_live_ingest_status_not_found(self, service):
        """Test getting status of non-existent ingest."""
        status = await service.get_live_ingest_status("non_existent_job")
        assert status is None
    
    async def test_get_live_ingest_status_exception(self, service, valid_stream_url):
        """Test getting status with exception."""
        # Start ingest
        job = await service.start_live_stream_ingest(stream_url=valid_stream_url)
        job_id = job.id
        
        # Mock to raise exception
        stream_monitor = service.active_streams[job_id]
        stream_monitor.get_status = AsyncMock(side_effect=Exception("Status error"))
        
        # Should handle exception and return None
        status = await service.get_live_ingest_status(job_id)
        assert status is None
    
    async def test_list_active_live_ingests(self, service, valid_stream_url, temp_file):
        """Test listing all active live ingests."""
        # Start multiple ingests
        stream_job = await service.start_live_stream_ingest(stream_url=valid_stream_url)
        file_job = await service.start_growing_file_ingest(file_path=temp_file)
        
        # Mock get_status methods
        stream_status = {"job_id": stream_job.id, "type": "live_stream"}
        file_status = {"job_id": file_job.id, "type": "growing_file"}
        
        service.active_streams[stream_job.id].get_status = AsyncMock(return_value=stream_status)
        service.growing_files[file_job.id].get_status = AsyncMock(return_value=file_status)
        
        # List active ingests
        active_ingests = await service.list_active_live_ingests()
        
        assert len(active_ingests) == 2
        assert stream_status in active_ingests
        assert file_status in active_ingests
    
    async def test_list_active_live_ingests_exception(self, service):
        """Test listing active ingests with exception."""
        with patch.object(service, 'active_streams', side_effect=Exception("List error")):
            active_ingests = await service.list_active_live_ingests()
            assert active_ingests == []
    
    def test_validate_stream_url_valid(self, service):
        """Test stream URL validation with valid URLs."""
        valid_urls = [
            "rtmp://example.com/live/stream",
            "rtsp://192.168.1.100:554/stream",
            "http://example.com/live.m3u8",
            "https://example.com/live.m3u8",
            "srt://example.com:9000",
            "udp://224.0.0.1:1234",
            "tcp://example.com:8080"
        ]
        
        for url in valid_urls:
            assert service._validate_stream_url(url) is True
    
    def test_validate_stream_url_invalid(self, service):
        """Test stream URL validation with invalid URLs."""
        invalid_urls = [
            "invalid://stream",
            "ftp://example.com/file",
            "rtmp://",  # No hostname
            "://example.com",  # No scheme
            "",
            "not_a_url"
        ]
        
        for url in invalid_urls:
            assert service._validate_stream_url(url) is False
    
    async def test_cleanup_completed_tasks(self, service):
        """Test cleanup of completed monitoring tasks."""
        # Create some mock tasks
        completed_task = AsyncMock()
        completed_task.done.return_value = True
        
        active_task = AsyncMock()
        active_task.done.return_value = False
        
        service.monitoring_tasks = {completed_task, active_task}
        
        # Run cleanup
        await service.cleanup_completed_tasks()
        
        # Verify only active task remains
        assert len(service.monitoring_tasks) == 1
        assert active_task in service.monitoring_tasks
        assert completed_task not in service.monitoring_tasks
    
    async def test_get_live_ingest_service_singleton(self):
        """Test that get_live_ingest_service returns singleton."""
        service1 = await get_live_ingest_service()
        service2 = await get_live_ingest_service()
        
        assert service1 is service2


class TestLiveStreamMonitor:
    """Test cases for LiveStreamMonitor."""
    
    @pytest.fixture
    def service(self):
        """Create LiveIngestService instance."""
        return LiveIngestService()
    
    @pytest.fixture
    def monitor(self, service):
        """Create LiveStreamMonitor instance."""
        return LiveStreamMonitor(
            job_id="test_job_123",
            stream_url="rtmp://example.com/live/stream",
            destination_project_id="project123",
            service=service
        )
    
    async def test_init(self, monitor):
        """Test monitor initialization."""
        assert monitor.job_id == "test_job_123"
        assert monitor.stream_url == "rtmp://example.com/live/stream"
        assert monitor.destination_project_id == "project123"
        assert monitor.is_monitoring is False
        assert monitor.start_time is None
        assert monitor.retry_count == 0
        assert monitor.captured_segments == []
        assert monitor.total_duration == 0.0
    
    async def test_start_monitoring_success(self, monitor):
        """Test successful stream monitoring."""
        # Mock to stop after one iteration
        monitor._capture_stream_segment = AsyncMock()
        monitor.is_monitoring = False  # Will be set to True, then checked in loop
        
        # Create a task that stops monitoring after a short delay
        async def stop_after_delay():
            await asyncio.sleep(0.1)
            monitor.is_monitoring = False
        
        # Start monitoring
        monitor.is_monitoring = True
        monitoring_task = asyncio.create_task(monitor.start_monitoring())
        stop_task = asyncio.create_task(stop_after_delay())
        
        await asyncio.gather(monitoring_task, stop_task)
        
        assert monitor.start_time is not None
        assert monitor.last_update is not None
        monitor._capture_stream_segment.assert_called()
    
    async def test_start_monitoring_with_retry(self, monitor):
        """Test stream monitoring with retries."""
        # Mock capture to fail first, then succeed
        monitor._capture_stream_segment = AsyncMock(
            side_effect=[Exception("Network error"), None, None]
        )
        
        # Run monitoring for a short time
        monitor.is_monitoring = True
        
        async def stop_after_delay():
            await asyncio.sleep(0.2)
            monitor.is_monitoring = False
        
        monitoring_task = asyncio.create_task(monitor.start_monitoring())
        stop_task = asyncio.create_task(stop_after_delay())
        
        await asyncio.gather(monitoring_task, stop_task)
        
        assert monitor.retry_count == 0  # Reset after success
    
    async def test_start_monitoring_max_retries(self, monitor):
        """Test stream monitoring stops after max retries."""
        # Mock capture to always fail
        monitor._capture_stream_segment = AsyncMock(
            side_effect=Exception("Persistent error")
        )
        
        # Run monitoring
        await monitor.start_monitoring()
        
        assert monitor.retry_count >= monitor.service.max_stream_retry_attempts
        assert monitor.is_monitoring is False
    
    async def test_capture_stream_segment(self, monitor):
        """Test stream segment capture."""
        initial_segment_count = len(monitor.captured_segments)
        initial_duration = monitor.total_duration
        
        await monitor._capture_stream_segment()
        
        assert len(monitor.captured_segments) == initial_segment_count + 1
        assert monitor.total_duration > initial_duration
        assert monitor.last_update is not None
        
        # Check segment info
        segment = monitor.captured_segments[-1]
        assert "timestamp" in segment
        assert "duration" in segment
        assert "size" in segment
    
    async def test_stop_monitoring(self, monitor):
        """Test stopping stream monitoring."""
        monitor.is_monitoring = True
        
        await monitor.stop_monitoring()
        
        assert monitor.is_monitoring is False
    
    async def test_get_status(self, monitor):
        """Test getting monitor status."""
        # Set some test data
        monitor.is_monitoring = True
        monitor.start_time = datetime.utcnow()
        monitor.last_update = datetime.utcnow()
        monitor.retry_count = 2
        monitor.captured_segments = [{"test": "segment"}]
        monitor.total_duration = 120.5
        
        status = await monitor.get_status()
        
        assert status["job_id"] == monitor.job_id
        assert status["type"] == "live_stream"
        assert status["stream_url"] == monitor.stream_url
        assert status["is_monitoring"] == monitor.is_monitoring
        assert status["start_time"] == monitor.start_time
        assert status["last_update"] == monitor.last_update
        assert status["retry_count"] == monitor.retry_count
        assert status["segments_captured"] == 1
        assert status["total_duration"] == monitor.total_duration
        assert status["destination_project_id"] == monitor.destination_project_id


class TestGrowingFileMonitor:
    """Test cases for GrowingFileMonitor."""
    
    @pytest.fixture
    def service(self):
        """Create LiveIngestService instance."""
        return LiveIngestService()
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"initial content")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def monitor(self, service, temp_file):
        """Create GrowingFileMonitor instance."""
        return GrowingFileMonitor(
            job_id="test_job_456",
            file_path=temp_file,
            destination_project_id="project123",
            timeout=60,
            service=service
        )
    
    async def test_init(self, monitor, temp_file):
        """Test monitor initialization."""
        assert monitor.job_id == "test_job_456"
        assert monitor.file_path == temp_file
        assert monitor.destination_project_id == "project123"
        assert monitor.timeout == 60
        assert monitor.is_monitoring is False
        assert monitor.start_time is None
        assert monitor.last_size == 0
        assert monitor.last_modified is None
        assert monitor.stable_since is None
        assert monitor.stability_confirmed is False
    
    async def test_start_monitoring_stable_file(self, monitor, temp_file):
        """Test monitoring a file that becomes stable."""
        # Mock check_file_stability to confirm stability quickly
        original_check = monitor._check_file_stability
        call_count = 0
        
        async def mock_check():
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                monitor.stability_confirmed = True
            else:
                await original_check()
        
        monitor._check_file_stability = mock_check
        monitor._trigger_final_ingest = AsyncMock()
        
        # Start monitoring
        await monitor.start_monitoring()
        
        assert monitor.start_time is not None
        assert monitor.stability_confirmed is True
        monitor._trigger_final_ingest.assert_called_once()
    
    async def test_start_monitoring_timeout(self, monitor, temp_file):
        """Test monitoring timeout."""
        # Set very short timeout
        monitor.timeout = 0.1
        monitor._trigger_final_ingest = AsyncMock()
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Should trigger ingest even on timeout
        monitor._trigger_final_ingest.assert_called_once()
    
    async def test_start_monitoring_exception(self, monitor):
        """Test monitoring with exception."""
        monitor._check_file_stability = AsyncMock(side_effect=Exception("Check error"))
        
        # Should handle exception gracefully
        await monitor.start_monitoring()
        
        assert monitor.is_monitoring is False
    
    async def test_check_file_stability_file_disappeared(self, monitor, temp_file):
        """Test stability check when file disappears."""
        # Remove the file
        os.unlink(temp_file)
        
        # Should handle gracefully
        await monitor._check_file_stability()
        
        # No crash, just logged warning
    
    async def test_check_file_stability_size_change(self, monitor, temp_file):
        """Test stability check when file size changes."""
        # Initial check
        await monitor._check_file_stability()
        initial_size = monitor.last_size
        
        # Modify file
        with open(temp_file, 'ab') as f:
            f.write(b"more content")
        
        # Check again
        await monitor._check_file_stability()
        
        assert monitor.last_size > initial_size
        assert monitor.stable_since is not None
        assert monitor.stability_confirmed is False
    
    async def test_check_file_stability_no_change(self, monitor, temp_file):
        """Test stability check when file doesn't change."""
        # Set initial state
        monitor.stable_since = datetime.utcnow() - timedelta(seconds=35)
        
        # Check stability
        await monitor._check_file_stability()
        
        # Should confirm stability after timeout
        assert monitor.stability_confirmed is True
    
    async def test_check_file_stability_exception(self, monitor, temp_file):
        """Test stability check with exception."""
        with patch('os.path.exists', side_effect=Exception("OS error")):
            # Should handle exception gracefully
            await monitor._check_file_stability()
    
    async def test_trigger_final_ingest(self, monitor):
        """Test triggering final ingest."""
        monitor.last_size = 1024
        
        # Should not raise exception
        await monitor._trigger_final_ingest()
    
    async def test_trigger_final_ingest_exception(self, monitor):
        """Test triggering final ingest with exception."""
        with patch.object(monitor.__class__.__module__ + '.logger.info', side_effect=Exception("Log error")):
            # Should handle exception gracefully
            await monitor._trigger_final_ingest()
    
    async def test_stop_monitoring(self, monitor):
        """Test stopping file monitoring."""
        monitor.is_monitoring = True
        
        await monitor.stop_monitoring()
        
        assert monitor.is_monitoring is False
    
    async def test_get_status(self, monitor):
        """Test getting monitor status."""
        # Set some test data
        monitor.is_monitoring = True
        monitor.start_time = datetime.utcnow()
        monitor.last_size = 2048
        monitor.last_modified = datetime.utcnow()
        monitor.stable_since = datetime.utcnow()
        monitor.stability_confirmed = True
        
        status = await monitor.get_status()
        
        assert status["job_id"] == monitor.job_id
        assert status["type"] == "growing_file"
        assert status["file_path"] == monitor.file_path
        assert status["is_monitoring"] == monitor.is_monitoring
        assert status["start_time"] == monitor.start_time
        assert status["current_size"] == monitor.last_size
        assert status["last_modified"] == monitor.last_modified
        assert status["stable_since"] == monitor.stable_since
        assert status["stability_confirmed"] == monitor.stability_confirmed
        assert status["destination_project_id"] == monitor.destination_project_id