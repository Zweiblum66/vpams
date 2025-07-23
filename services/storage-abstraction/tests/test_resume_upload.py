"""
Tests for Resume Upload functionality
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.services.resume_upload_service import (
    ResumeUploadService, ResumableUpload
)
from src.drivers.local import LocalStorageDriver
from src.core.interfaces import InvalidStorageOperationError


@pytest.fixture
async def resume_service():
    """Create a resume upload service for testing"""
    service = ResumeUploadService()
    service._session_file = Path(tempfile.mkdtemp()) / "test_sessions.json"
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
async def storage_driver():
    """Create a local storage driver for testing"""
    config = {
        "root_path": tempfile.mkdtemp(),
        "create_directories": True
    }
    driver = LocalStorageDriver(config)
    await driver.initialize()
    yield driver
    await driver.close()


class TestResumeUploadService:
    """Test cases for resume upload service"""
    
    async def test_create_resumable_upload(self, resume_service):
        """Test creating a resumable upload session"""
        session = await resume_service.create_resumable_upload(
            key="test/file.bin",
            total_size=1024 * 1024,  # 1MB
            chunk_size=256 * 1024,   # 256KB
            driver_name="local"
        )
        
        assert session.upload_id
        assert session.key == "test/file.bin"
        assert session.total_size == 1024 * 1024
        assert session.chunk_size == 256 * 1024
        assert session.uploaded_size == 0
        assert len(session.chunks_completed) == 0
        assert session.driver_name == "local"
        assert os.path.exists(session.temp_path)
    
    async def test_upload_chunk(self, resume_service):
        """Test uploading chunks"""
        # Create session
        session = await resume_service.create_resumable_upload(
            key="test/file.bin",
            total_size=1024,  # 1KB
            chunk_size=256,   # 256B
            driver_name="local"
        )
        
        # Upload first chunk
        data1 = b"A" * 256
        updated_session = await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=0,
            data=data1
        )
        
        assert 0 in updated_session.chunks_completed
        assert updated_session.uploaded_size == 256
        
        # Upload second chunk
        data2 = b"B" * 256
        updated_session = await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=1,
            data=data2
        )
        
        assert 1 in updated_session.chunks_completed
        assert updated_session.uploaded_size == 512
    
    async def test_duplicate_chunk_upload(self, resume_service):
        """Test uploading the same chunk twice"""
        session = await resume_service.create_resumable_upload(
            key="test/file.bin",
            total_size=1024,
            chunk_size=256,
            driver_name="local"
        )
        
        # Upload chunk
        data = b"A" * 256
        await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=0,
            data=data
        )
        
        # Upload same chunk again
        updated_session = await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=0,
            data=data
        )
        
        # Should not duplicate
        assert updated_session.chunks_completed.count(0) == 1
    
    async def test_complete_upload(self, resume_service, storage_driver):
        """Test completing an upload"""
        # Create session
        session = await resume_service.create_resumable_upload(
            key="test/completed.bin",
            total_size=512,
            chunk_size=256,
            driver_name="local"
        )
        
        # Upload all chunks
        await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=0,
            data=b"A" * 256
        )
        await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=1,
            data=b"B" * 256
        )
        
        # Complete upload
        result = await resume_service.complete_upload(
            session.upload_id,
            storage_driver,
            verify_checksum=False
        )
        
        assert result.key == "test/completed.bin"
        assert result.size == 512
        
        # Session should be cleaned up
        assert await resume_service.get_upload_status(session.upload_id) is None
    
    async def test_incomplete_upload_error(self, resume_service, storage_driver):
        """Test completing upload with missing chunks"""
        session = await resume_service.create_resumable_upload(
            key="test/incomplete.bin",
            total_size=512,
            chunk_size=256,
            driver_name="local"
        )
        
        # Upload only first chunk
        await resume_service.upload_chunk(
            session.upload_id,
            chunk_index=0,
            data=b"A" * 256
        )
        
        # Try to complete - should fail
        with pytest.raises(InvalidStorageOperationError) as exc:
            await resume_service.complete_upload(
                session.upload_id,
                storage_driver
            )
        
        assert "Missing chunks" in str(exc.value)
    
    async def test_abort_upload(self, resume_service):
        """Test aborting an upload"""
        session = await resume_service.create_resumable_upload(
            key="test/aborted.bin",
            total_size=1024,
            chunk_size=256,
            driver_name="local"
        )
        
        # Abort upload
        await resume_service.abort_upload(session.upload_id)
        
        # Session should be gone
        assert await resume_service.get_upload_status(session.upload_id) is None
        
        # Temp files should be cleaned up
        assert not os.path.exists(Path(session.temp_path).parent)
    
    async def test_expired_session(self, resume_service):
        """Test expired session handling"""
        session = await resume_service.create_resumable_upload(
            key="test/expired.bin",
            total_size=1024,
            chunk_size=256,
            driver_name="local",
            ttl_hours=0  # Expires immediately
        )
        
        # Manually expire the session
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        # Try to upload chunk - should fail
        with pytest.raises(InvalidStorageOperationError) as exc:
            await resume_service.upload_chunk(
                session.upload_id,
                chunk_index=0,
                data=b"data"
            )
        
        assert "expired" in str(exc.value).lower()
    
    async def test_list_uploads(self, resume_service):
        """Test listing active uploads"""
        # Create multiple sessions
        session1 = await resume_service.create_resumable_upload(
            key="project1/file1.bin",
            total_size=1024,
            chunk_size=256,
            driver_name="local"
        )
        
        session2 = await resume_service.create_resumable_upload(
            key="project1/file2.bin",
            total_size=2048,
            chunk_size=512,
            driver_name="local"
        )
        
        session3 = await resume_service.create_resumable_upload(
            key="project2/file3.bin",
            total_size=4096,
            chunk_size=1024,
            driver_name="local"
        )
        
        # List all
        all_uploads = await resume_service.list_uploads()
        assert len(all_uploads) == 3
        
        # List with prefix
        project1_uploads = await resume_service.list_uploads(key_prefix="project1/")
        assert len(project1_uploads) == 2
        
        project2_uploads = await resume_service.list_uploads(key_prefix="project2/")
        assert len(project2_uploads) == 1
    
    async def test_session_persistence(self, resume_service):
        """Test session persistence across service restarts"""
        # Create session
        session = await resume_service.create_resumable_upload(
            key="test/persistent.bin",
            total_size=1024,
            chunk_size=256,
            driver_name="local"
        )
        
        upload_id = session.upload_id
        
        # Upload some chunks
        await resume_service.upload_chunk(
            upload_id,
            chunk_index=0,
            data=b"A" * 256
        )
        
        # Save sessions
        await resume_service._save_sessions()
        
        # Create new service instance
        new_service = ResumeUploadService()
        new_service._session_file = resume_service._session_file
        await new_service.initialize()
        
        # Should be able to get session
        loaded_session = await new_service.get_upload_status(upload_id)
        assert loaded_session is not None
        assert loaded_session.key == "test/persistent.bin"
        assert 0 in loaded_session.chunks_completed
        
        await new_service.shutdown()
    
    async def test_progress_callback(self, resume_service):
        """Test progress callback functionality"""
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append({
                "bytes": progress.bytes_uploaded,
                "percentage": progress.percentage,
                "chunks": progress.chunks_completed
            })
        
        session = await resume_service.create_resumable_upload(
            key="test/progress.bin",
            total_size=1000,
            chunk_size=250,
            driver_name="local"
        )
        
        # Upload chunks with progress callback
        for i in range(4):
            await resume_service.upload_chunk(
                session.upload_id,
                chunk_index=i,
                data=b"X" * 250,
                progress_callback=progress_callback
            )
        
        # Check progress updates
        assert len(progress_updates) == 4
        assert progress_updates[0]["percentage"] == 25.0
        assert progress_updates[1]["percentage"] == 50.0
        assert progress_updates[2]["percentage"] == 75.0
        assert progress_updates[3]["percentage"] == 100.0
    
    async def test_concurrent_chunk_uploads(self, resume_service):
        """Test concurrent chunk uploads"""
        session = await resume_service.create_resumable_upload(
            key="test/concurrent.bin",
            total_size=4096,
            chunk_size=1024,
            driver_name="local"
        )
        
        # Upload chunks concurrently
        tasks = []
        for i in range(4):
            task = resume_service.upload_chunk(
                session.upload_id,
                chunk_index=i,
                data=bytes([65 + i]) * 1024  # A, B, C, D
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Check all chunks uploaded
        final_session = await resume_service.get_upload_status(session.upload_id)
        assert len(final_session.chunks_completed) == 4
        assert final_session.uploaded_size == 4096