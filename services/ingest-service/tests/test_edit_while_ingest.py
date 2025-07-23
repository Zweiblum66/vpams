"""
Tests for Edit-While-Ingest functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import os
import tempfile

from src.services.edit_while_ingest_service import (
    EditWhileIngestService,
    ActiveIngestSession,
    EditSession
)
from src.models.schemas import IngestJob, IngestStatus
from src.core.exceptions import EditWhileIngestError


@pytest.fixture
def edit_while_ingest_service():
    """Create an EditWhileIngestService instance for testing"""
    return EditWhileIngestService()


@pytest.fixture
def mock_ingest_job():
    """Create a mock IngestJob for testing"""
    return IngestJob(
        id="test-job-123",
        source_path="/source/test_video.mp4",
        destination_project_id="project-456",
        status=IngestStatus.PROCESSING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
async def temp_files():
    """Create temporary files for testing"""
    with tempfile.NamedTemporaryFile(delete=False) as source:
        source.write(b"Test video content" * 1000)
        source_path = source.name
    
    with tempfile.NamedTemporaryFile(delete=False) as dest:
        dest_path = dest.name
    
    yield source_path, dest_path
    
    # Cleanup
    os.unlink(source_path)
    os.unlink(dest_path)


class TestEditWhileIngestService:
    """Test cases for EditWhileIngestService"""
    
    async def test_register_active_ingest(self, edit_while_ingest_service, mock_ingest_job):
        """Test registering a new active ingest"""
        # Register ingest
        session = await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Verify session created
        assert session is not None
        assert session.job_id == mock_ingest_job.id
        assert mock_ingest_job.id in edit_while_ingest_service.active_ingests
        assert mock_ingest_job.id in edit_while_ingest_service.access_locks
    
    async def test_get_partial_file_access(self, edit_while_ingest_service, mock_ingest_job, temp_files):
        """Test getting partial file access"""
        source_path, dest_path = temp_files
        
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path=source_path,
            destination_path=dest_path
        )
        
        # Mock the session's read method
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.read_partial_file = AsyncMock(return_value=b"Test data")
        
        # Get partial data
        data = await edit_while_ingest_service.get_partial_file_access(
            job_id=mock_ingest_job.id,
            byte_range=(0, 100)
        )
        
        assert data == b"Test data"
        session.read_partial_file.assert_called_once_with((0, 100))
    
    async def test_get_partial_file_access_not_found(self, edit_while_ingest_service):
        """Test getting partial file access for non-existent job"""
        data = await edit_while_ingest_service.get_partial_file_access(
            job_id="non-existent-job"
        )
        
        assert data is None
    
    async def test_get_ingest_metadata(self, edit_while_ingest_service, mock_ingest_job):
        """Test getting ingest metadata"""
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Mock metadata
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.get_current_metadata = AsyncMock(return_value={
            "job_id": mock_ingest_job.id,
            "available_bytes": 1024000,
            "segments": []
        })
        
        # Get metadata
        metadata = await edit_while_ingest_service.get_ingest_metadata(mock_ingest_job.id)
        
        assert metadata is not None
        assert metadata["job_id"] == mock_ingest_job.id
        assert metadata["available_bytes"] == 1024000
    
    async def test_request_priority_chunk(self, edit_while_ingest_service, mock_ingest_job):
        """Test requesting priority chunk processing"""
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Mock priority processing
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.prioritize_chunk = AsyncMock(return_value=True)
        
        # Request priority
        success = await edit_while_ingest_service.request_priority_chunk(
            job_id=mock_ingest_job.id,
            byte_offset=1000,
            chunk_size=5000
        )
        
        assert success is True
        session.prioritize_chunk.assert_called_once_with(1000, 5000)
    
    async def test_unregister_active_ingest(self, edit_while_ingest_service, mock_ingest_job):
        """Test unregistering an active ingest"""
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Mock stop monitoring
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.stop_monitoring = AsyncMock()
        
        # Unregister
        await edit_while_ingest_service.unregister_active_ingest(mock_ingest_job.id)
        
        # Verify cleanup
        assert mock_ingest_job.id not in edit_while_ingest_service.active_ingests
        assert mock_ingest_job.id not in edit_while_ingest_service.access_locks
        session.stop_monitoring.assert_called_once()
    
    async def test_get_editable_segments(self, edit_while_ingest_service, mock_ingest_job):
        """Test getting editable segments"""
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Mock segments
        test_segments = [
            {"index": 0, "status": "available"},
            {"index": 1, "status": "available"}
        ]
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.get_available_segments = AsyncMock(return_value=test_segments)
        
        # Get segments
        segments = await edit_while_ingest_service.get_editable_segments(mock_ingest_job.id)
        
        assert len(segments) == 2
        assert segments == test_segments
    
    async def test_create_edit_session(self, edit_while_ingest_service, mock_ingest_job):
        """Test creating an edit session"""
        # Register ingest
        await edit_while_ingest_service.register_active_ingest(
            job=mock_ingest_job,
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4"
        )
        
        # Mock edit session creation
        session = edit_while_ingest_service.active_ingests[mock_ingest_job.id]
        session.create_edit_session = AsyncMock(return_value="edit-session-123")
        
        # Create edit session
        session_id = await edit_while_ingest_service.create_edit_session(
            job_id=mock_ingest_job.id,
            start_time=10.0,
            end_time=30.0
        )
        
        assert session_id == "edit-session-123"
        session.create_edit_session.assert_called_once_with(10.0, 30.0)


class TestActiveIngestSession:
    """Test cases for ActiveIngestSession"""
    
    async def test_read_partial_file(self, temp_files):
        """Test reading partial file data"""
        source_path, dest_path = temp_files
        
        # Create session
        service = EditWhileIngestService()
        session = ActiveIngestSession(
            job_id="test-job",
            source_path=source_path,
            destination_path=dest_path,
            service=service
        )
        
        # Write test data to destination
        with open(dest_path, 'wb') as f:
            f.write(b"Hello World" * 100)
        
        # Read partial data
        data = await session.read_partial_file((0, 10))
        
        assert data == b"Hello Worl"
    
    async def test_get_current_metadata(self):
        """Test getting current metadata"""
        service = EditWhileIngestService()
        session = ActiveIngestSession(
            job_id="test-job",
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4",
            service=service
        )
        
        # Set some test values
        session.available_bytes = 1024000
        session.segments = [{"index": 0}]
        session.proxy_path = "/proxy/test.mp4"
        
        # Get metadata
        metadata = await session.get_current_metadata()
        
        assert metadata["job_id"] == "test-job"
        assert metadata["available_bytes"] == 1024000
        assert len(metadata["segments"]) == 1
        assert metadata["proxy_path"] == "/proxy/test.mp4"
    
    async def test_prioritize_chunk(self):
        """Test prioritizing a chunk"""
        service = EditWhileIngestService()
        session = ActiveIngestSession(
            job_id="test-job",
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4",
            service=service
        )
        
        # Prioritize chunk
        success = await session.prioritize_chunk(1000, 5000)
        
        assert success is True
        assert (1000, 5000) in session.priority_chunks
    
    async def test_get_available_segments(self):
        """Test getting available segments"""
        service = EditWhileIngestService()
        session = ActiveIngestSession(
            job_id="test-job",
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4",
            service=service
        )
        
        # Set test segments
        session.segments = [
            {"index": 0, "status": "available"},
            {"index": 1, "status": "processing"},
            {"index": 2, "status": "available"}
        ]
        
        # Get available segments
        available = await session.get_available_segments()
        
        assert len(available) == 2
        assert available[0]["index"] == 0
        assert available[1]["index"] == 2
    
    async def test_create_edit_session(self):
        """Test creating an edit session"""
        service = EditWhileIngestService()
        session = ActiveIngestSession(
            job_id="test-job",
            source_path="/source/test.mp4",
            destination_path="/dest/test.mp4",
            service=service
        )
        
        # Create edit session
        session_id = await session.create_edit_session(10.0, 30.0)
        
        assert session_id is not None
        assert session_id in session.edit_sessions
        assert session.edit_sessions[session_id]["start_time"] == 10.0
        assert session.edit_sessions[session_id]["end_time"] == 30.0
        assert session.edit_sessions[session_id]["status"] == "active"


class TestEditSession:
    """Test cases for EditSession"""
    
    async def test_add_edit(self):
        """Test adding an edit to a session"""
        session = EditSession(
            session_id="test-session",
            job_id="test-job",
            start_time=10.0,
            end_time=30.0
        )
        
        # Add edit
        await session.add_edit("cut", {
            "in": 15.0,
            "out": 25.0
        })
        
        assert len(session.edits) == 1
        assert session.edits[0]["type"] == "cut"
        assert session.edits[0]["parameters"]["in"] == 15.0
    
    async def test_export_edl(self):
        """Test exporting session as EDL"""
        session = EditSession(
            session_id="test-session",
            job_id="test-job",
            start_time=10.0,
            end_time=30.0
        )
        
        # Add some edits
        await session.add_edit("cut", {
            "in": 15.0,
            "out": 25.0,
            "start": 0.0,
            "end": 10.0
        })
        
        # Export EDL
        edl = await session.export_edl()
        
        assert "TITLE: Edit Session test-session" in edl
        assert "FCM: NON-DROP FRAME" in edl
        assert "001  001      V     C" in edl
    
    def test_format_timecode(self):
        """Test timecode formatting"""
        session = EditSession(
            session_id="test-session",
            job_id="test-job",
            start_time=10.0,
            end_time=30.0
        )
        
        # Test various timecodes
        assert session._format_timecode(0) == "00:00:00:00"
        assert session._format_timecode(3661.5) == "01:01:01:15"  # 1h 1m 1s 15f
        assert session._format_timecode(90.2) == "00:01:30:06"   # 1m 30s 6f


@pytest.mark.asyncio
async def test_monitoring_lifecycle(edit_while_ingest_service, mock_ingest_job, temp_files):
    """Test the complete monitoring lifecycle"""
    source_path, dest_path = temp_files
    
    # Register and start monitoring
    session = await edit_while_ingest_service.register_active_ingest(
        job=mock_ingest_job,
        source_path=source_path,
        destination_path=dest_path
    )
    
    # Let monitoring run briefly
    await asyncio.sleep(0.1)
    
    # Verify monitoring is active
    assert session.is_monitoring is True
    
    # Stop monitoring
    await edit_while_ingest_service.unregister_active_ingest(mock_ingest_job.id)
    
    # Verify cleanup
    assert mock_ingest_job.id not in edit_while_ingest_service.active_ingests