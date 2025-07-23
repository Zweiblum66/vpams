"""
Test Real-time Proxy Generation Service

Tests for creating proxies during media ingest.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable

from src.services.realtime_proxy_service import (
    RealtimeProxyService,
    ProxyGenerationSession,
    ProxyQuality,
    ProxyProfile,
    get_realtime_proxy_service
)
from src.models.schemas import IngestJob, IngestStatus, ProxyType
from src.core.exceptions import ProxyGenerationError


class TestRealtimeProxyService:
    """Test cases for RealtimeProxyService."""
    
    @pytest.fixture
    def service(self):
        """Create RealtimeProxyService instance."""
        return RealtimeProxyService()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        return AsyncMock()
    
    async def test_init(self, service):
        """Test service initialization."""
        assert service.active_generations == {}
        assert len(service.proxy_profiles) == 4
        assert service.chunk_duration == 10
        assert service.buffer_chunks == 3
        assert service.max_parallel_chunks == 4
        assert service.output_format == "mp4"
    
    def test_initialize_profiles(self, service):
        """Test proxy profile initialization."""
        profiles = service._initialize_profiles()
        
        # Verify all qualities have profiles
        assert ProxyQuality.LOW in profiles
        assert ProxyQuality.MEDIUM in profiles
        assert ProxyQuality.HIGH in profiles
        assert ProxyQuality.EDIT in profiles
        
        # Verify LOW profile
        low_profile = profiles[ProxyQuality.LOW]
        assert low_profile.video_codec == "libx264"
        assert low_profile.video_bitrate == "500k"
        assert low_profile.resolution == "640x360"
        assert low_profile.preset == "ultrafast"
        
        # Verify EDIT profile
        edit_profile = profiles[ProxyQuality.EDIT]
        assert edit_profile.video_codec == "prores"
        assert edit_profile.video_bitrate == "40000k"
        assert edit_profile.resolution is None  # Keep original
    
    async def test_start_realtime_proxy_success(self, service, temp_dir, mock_progress_callback):
        """Test successful real-time proxy start."""
        job_id = "test_job_123"
        source_path = "/test/video.mp4"
        
        with patch('asyncio.create_task'):
            session = await service.start_realtime_proxy(
                job_id=job_id,
                source_path=source_path,
                destination_dir=temp_dir,
                quality=ProxyQuality.MEDIUM,
                progress_callback=mock_progress_callback
            )
            
            assert session is not None
            assert session.job_id == job_id
            assert session.source_path == source_path
            assert session.destination_dir == temp_dir
            assert session.profile == service.proxy_profiles[ProxyQuality.MEDIUM]
            assert session.progress_callback == mock_progress_callback
            
            # Verify session is tracked
            assert job_id in service.active_generations
            assert service.active_generations[job_id] == session
    
    async def test_start_realtime_proxy_exception(self, service, temp_dir):
        """Test real-time proxy start with exception."""
        job_id = "test_job_123"
        source_path = "/test/video.mp4"
        
        with patch.object(
            ProxyGenerationSession,
            '__init__',
            side_effect=Exception("Init error")
        ):
            with pytest.raises(ProxyGenerationError, match="Failed to start real-time proxy"):
                await service.start_realtime_proxy(
                    job_id=job_id,
                    source_path=source_path,
                    destination_dir=temp_dir
                )
    
    async def test_stop_realtime_proxy_success(self, service, temp_dir):
        """Test successful real-time proxy stop."""
        job_id = "test_job_123"
        
        # Start proxy first
        with patch('asyncio.create_task'):
            session = await service.start_realtime_proxy(
                job_id=job_id,
                source_path="/test/video.mp4",
                destination_dir=temp_dir
            )
        
        # Mock stop_generation
        session.stop_generation = AsyncMock()
        
        # Stop proxy
        await service.stop_realtime_proxy(job_id)
        
        # Verify
        session.stop_generation.assert_called_once()
        assert job_id not in service.active_generations
    
    async def test_stop_realtime_proxy_not_found(self, service):
        """Test stopping non-existent proxy."""
        # Should not raise exception
        await service.stop_realtime_proxy("non_existent_job")
    
    async def test_stop_realtime_proxy_exception(self, service, temp_dir):
        """Test stopping proxy with exception."""
        job_id = "test_job_123"
        
        # Start proxy first
        with patch('asyncio.create_task'):
            session = await service.start_realtime_proxy(
                job_id=job_id,
                source_path="/test/video.mp4",
                destination_dir=temp_dir
            )
        
        # Mock stop_generation to raise exception
        session.stop_generation = AsyncMock(side_effect=Exception("Stop error"))
        
        # Should handle exception gracefully
        await service.stop_realtime_proxy(job_id)
    
    async def test_get_proxy_status_exists(self, service, temp_dir):
        """Test getting proxy status for existing session."""
        job_id = "test_job_123"
        
        # Start proxy first
        with patch('asyncio.create_task'):
            session = await service.start_realtime_proxy(
                job_id=job_id,
                source_path="/test/video.mp4",
                destination_dir=temp_dir
            )
        
        # Mock get_status
        expected_status = {"job_id": job_id, "is_active": True}
        session.get_status = AsyncMock(return_value=expected_status)
        
        # Get status
        status = await service.get_proxy_status(job_id)
        
        assert status == expected_status
        session.get_status.assert_called_once()
    
    async def test_get_proxy_status_not_found(self, service):
        """Test getting proxy status for non-existent session."""
        status = await service.get_proxy_status("non_existent_job")
        assert status is None
    
    async def test_generate_proxy_chunk_success(self, service):
        """Test successful proxy chunk generation."""
        input_path = "/test/video.mp4"
        output_path = "/test/chunk_001.mp4"
        profile = service.proxy_profiles[ProxyQuality.MEDIUM]
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await service.generate_proxy_chunk(
                input_path=input_path,
                output_path=output_path,
                start_time=10.0,
                duration=5.0,
                profile=profile
            )
            
            assert result is True
    
    async def test_generate_proxy_chunk_failure(self, service):
        """Test proxy chunk generation failure."""
        input_path = "/test/video.mp4"
        output_path = "/test/chunk_001.mp4"
        profile = service.proxy_profiles[ProxyQuality.MEDIUM]
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await service.generate_proxy_chunk(
                input_path=input_path,
                output_path=output_path,
                start_time=10.0,
                duration=5.0,
                profile=profile
            )
            
            assert result is False
    
    async def test_generate_proxy_chunk_exception(self, service):
        """Test proxy chunk generation with exception."""
        input_path = "/test/video.mp4"
        output_path = "/test/chunk_001.mp4"
        profile = service.proxy_profiles[ProxyQuality.MEDIUM]
        
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Subprocess error")):
            result = await service.generate_proxy_chunk(
                input_path=input_path,
                output_path=output_path,
                start_time=10.0,
                duration=5.0,
                profile=profile
            )
            
            assert result is False
    
    async def test_concatenate_chunks_success(self, service, temp_dir):
        """Test successful chunk concatenation."""
        # Create temporary chunk files
        chunk_paths = []
        for i in range(3):
            chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp4")
            with open(chunk_path, 'w') as f:
                f.write(f"chunk {i}")
            chunk_paths.append(chunk_path)
        
        output_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('aiofiles.open', new_callable=AsyncMock):
                result = await service.concatenate_chunks(chunk_paths, output_path)
                
                assert result is True
    
    async def test_concatenate_chunks_failure(self, service, temp_dir):
        """Test chunk concatenation failure."""
        chunk_paths = ["/test/chunk_001.mp4", "/test/chunk_002.mp4"]
        output_path = "/test/output.mp4"
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Concat error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('aiofiles.open', new_callable=AsyncMock):
                with patch('pathlib.Path.unlink'):  # Mock file cleanup
                    result = await service.concatenate_chunks(chunk_paths, output_path)
                    
                    assert result is False
    
    async def test_get_realtime_proxy_service_singleton(self):
        """Test that get_realtime_proxy_service returns singleton."""
        service1 = await get_realtime_proxy_service()
        service2 = await get_realtime_proxy_service()
        
        assert service1 is service2


class TestProxyGenerationSession:
    """Test cases for ProxyGenerationSession."""
    
    @pytest.fixture
    def service(self):
        """Create RealtimeProxyService instance."""
        return RealtimeProxyService()
    
    @pytest.fixture
    def profile(self, service):
        """Get proxy profile for testing."""
        return service.proxy_profiles[ProxyQuality.MEDIUM]
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def session(self, service, profile, temp_dir):
        """Create ProxyGenerationSession instance."""
        return ProxyGenerationSession(
            job_id="test_job_123",
            source_path="/test/video.mp4",
            destination_dir=temp_dir,
            profile=profile,
            service=service,
            progress_callback=None
        )
    
    async def test_init(self, session, temp_dir):
        """Test session initialization."""
        assert session.job_id == "test_job_123"
        assert session.source_path == "/test/video.mp4"
        assert session.destination_dir == temp_dir
        assert session.is_active is False
        assert session.start_time is None
        assert session.chunks_generated == 0
        assert session.total_duration == 0
        assert session.current_position == 0
        assert session.chunk_paths == []
        assert session.errors == []
        
        # Check paths
        assert session.chunks_dir.exists()
        assert session.proxy_path.name == "medium_proxy.mp4"
    
    async def test_start_generation_success(self, session):
        """Test successful generation start."""
        with patch.object(session, '_process_chunks', new_callable=AsyncMock):
            with patch.object(session, '_monitor_source', new_callable=AsyncMock):
                with patch('asyncio.create_task') as mock_create_task:
                    await session.start_generation()
                    
                    assert session.is_active is True
                    assert session.start_time is not None
                    assert len(session.processing_tasks) == session.service.max_parallel_chunks
                    # Monitor task + chunk processing tasks
                    assert mock_create_task.call_count == session.service.max_parallel_chunks + 1
    
    async def test_start_generation_exception(self, session):
        """Test generation start with exception."""
        with patch('asyncio.create_task', side_effect=Exception("Task error")):
            with pytest.raises(Exception):
                await session.start_generation()
            
            assert session.is_active is False
    
    async def test_stop_generation_success(self, session):
        """Test successful generation stop."""
        # Start first
        session.is_active = True
        session.processing_tasks = [AsyncMock() for _ in range(3)]
        session.chunk_paths = ["/test/chunk_001.mp4", "/test/chunk_002.mp4"]
        
        with patch.object(session, '_finalize_proxy', new_callable=AsyncMock):
            await session.stop_generation()
            
            assert session.is_active is False
            session._finalize_proxy.assert_called_once()
            
            # Verify all tasks were cancelled
            for task in session.processing_tasks:
                task.cancel.assert_called_once()
    
    async def test_get_status(self, session):
        """Test getting session status."""
        # Set test data
        session.is_active = True
        session.start_time = datetime.utcnow()
        session.chunks_generated = 5
        session.current_position = 50.0
        session.total_duration = 120.0
        session.errors = ["Error 1", "Error 2"]
        
        # Create proxy file
        session.proxy_path.touch()
        
        status = await session.get_status()
        
        assert status['job_id'] == session.job_id
        assert status['profile'] == session.profile.name
        assert status['quality'] == session.profile.quality.value
        assert status['is_active'] == session.is_active
        assert status['chunks_generated'] == 5
        assert status['current_position'] == 50.0
        assert status['total_duration'] == 120.0
        assert status['proxy_path'] == str(session.proxy_path)
        assert len(status['errors']) == 2
    
    async def test_monitor_source_success(self, session):
        """Test source file monitoring."""
        session.is_active = True
        
        # Mock file duration checks
        duration_values = [30.0, 60.0, 90.0]
        
        with patch.object(session, '_get_file_duration', side_effect=duration_values):
            # Run monitor for limited iterations
            async def limited_monitor():
                original_active = session.is_active
                call_count = 0
                
                async def mock_sleep(duration):
                    nonlocal call_count
                    call_count += 1
                    if call_count >= 3:
                        session.is_active = False
                    await asyncio.sleep(0.01)  # Short sleep for testing
                
                with patch('asyncio.sleep', mock_sleep):
                    await session._monitor_source()
            
            await limited_monitor()
            
            # Verify chunks were queued
            assert session.total_duration == 90.0
            assert session.chunk_queue.qsize() > 0
    
    async def test_process_chunks_success(self, session):
        """Test successful chunk processing."""
        session.is_active = True
        
        # Add test chunk to queue
        chunk_info = {
            'index': 0,
            'start_time': 0.0,
            'duration': 10.0
        }
        await session.chunk_queue.put(chunk_info)
        
        # Mock generate_proxy_chunk
        session.service.generate_proxy_chunk = AsyncMock(return_value=True)
        
        # Run process_chunks for one iteration
        session.is_active = False  # Will stop after processing one chunk
        
        with patch('asyncio.wait_for', return_value=chunk_info):
            await session._process_chunks()
        
        assert session.chunks_generated == 1
        assert len(session.chunk_paths) == 1
    
    async def test_process_chunks_failure(self, session):
        """Test chunk processing with failure."""
        session.is_active = True
        
        # Add test chunk to queue
        chunk_info = {
            'index': 0,
            'start_time': 0.0,
            'duration': 10.0
        }
        await session.chunk_queue.put(chunk_info)
        
        # Mock generate_proxy_chunk to fail
        session.service.generate_proxy_chunk = AsyncMock(return_value=False)
        
        # Run process_chunks for one iteration
        session.is_active = False  # Will stop after processing one chunk
        
        with patch('asyncio.wait_for', return_value=chunk_info):
            await session._process_chunks()
        
        assert session.chunks_generated == 0
        assert len(session.errors) == 1
        assert "Failed to generate chunk 0" in session.errors[0]
    
    async def test_update_proxy_success(self, session):
        """Test successful proxy update."""
        # Add chunk paths
        session.chunk_paths = ["/test/chunk_001.mp4", "/test/chunk_002.mp4", "/test/chunk_003.mp4"]
        
        # Mock concatenate_chunks
        session.service.concatenate_chunks = AsyncMock(return_value=True)
        
        # Create temp proxy file
        temp_proxy = session.proxy_path.with_suffix('.tmp')
        temp_proxy.touch()
        
        await session._update_proxy()
        
        session.service.concatenate_chunks.assert_called_once()
        # Note: File operations might fail in test environment
    
    async def test_finalize_proxy_success(self, session, temp_dir):
        """Test successful proxy finalization."""
        # Create chunk files
        chunk_paths = []
        for i in range(3):
            chunk_path = Path(temp_dir) / f"chunk_{i:03d}.mp4"
            chunk_path.touch()
            chunk_paths.append(str(chunk_path))
        
        session.chunk_paths = chunk_paths
        session.chunks_generated = 3
        
        with patch.object(session, '_update_proxy', new_callable=AsyncMock):
            await session._finalize_proxy()
            
            session._update_proxy.assert_called_once()
            
            # Verify chunks were cleaned up
            for chunk_path in chunk_paths:
                assert not Path(chunk_path).exists()
    
    async def test_get_file_duration_success(self, session):
        """Test successful file duration retrieval."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"120.5\n", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            duration = await session._get_file_duration("/test/video.mp4")
            
            assert duration == 120.5
    
    async def test_get_file_duration_failure(self, session):
        """Test file duration retrieval failure."""
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            duration = await session._get_file_duration("/test/video.mp4")
            
            assert duration == 0.0
    
    async def test_get_file_duration_exception(self, session):
        """Test file duration retrieval with exception."""
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("FFprobe error")):
            duration = await session._get_file_duration("/test/video.mp4")
            
            assert duration == 0.0
    
    async def test_progress_callback_integration(self, session):
        """Test progress callback integration."""
        # Add progress callback
        progress_callback = AsyncMock()
        session.progress_callback = progress_callback
        
        # Add test chunk to queue
        chunk_info = {
            'index': 0,
            'start_time': 0.0,
            'duration': 10.0
        }
        
        # Mock successful chunk generation
        session.service.generate_proxy_chunk = AsyncMock(return_value=True)
        
        # Process chunk with progress callback
        session.is_active = True
        
        with patch('asyncio.wait_for', return_value=chunk_info):
            # Run one iteration
            session.is_active = False
            await session._process_chunks()
        
        # Verify callback was called
        progress_callback.assert_called_once()
        call_args = progress_callback.call_args[0][0]
        assert call_args['job_id'] == session.job_id
        assert call_args['chunks_generated'] == 1
        assert call_args['current_position'] == 10.0