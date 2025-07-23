"""
Test Watch Folder Service

Tests for automatic file ingestion through monitored folders.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.events import FileCreatedEvent, FileMovedEvent, DirCreatedEvent

from src.services.watch_folder_service import (
    WatchFolderService,
    WatchFolderHandler,
    get_watch_folder_service
)
from src.models.schemas import (
    WatchFolderConfig, IngestJobCreate, IngestJob, IngestType,
    IngestStatus, IngestPriority, ValidationRule
)
from src.core.exceptions import WatchFolderError, IngestServiceError
from src.services.ingest_service import IngestService


class TestWatchFolderHandler:
    """Test cases for WatchFolderHandler."""
    
    @pytest.fixture
    def watch_folder_config(self):
        """Create watch folder configuration."""
        return WatchFolderConfig(
            id="test_watch_folder",
            path="/test/watch/folder",
            enabled=True,
            stability_delay=2.0,
            include_patterns=["mp4", "mov", "mxf"],
            exclude_patterns=["temp", "._"],
            recursive=True,
            destination_project_id="project123",
            auto_generate_proxies=True,
            preserve_folder_structure=True,
            priority=IngestPriority.NORMAL,
            tags=["watch_folder", "auto"],
            metadata_template={"source": "watch_folder"}
        )
    
    @pytest.fixture
    def watch_folder_service(self):
        """Create WatchFolderService instance."""
        service = WatchFolderService()
        service.ingest_service = Mock(spec=IngestService)
        return service
    
    @pytest.fixture
    def handler(self, watch_folder_config, watch_folder_service):
        """Create WatchFolderHandler instance."""
        return WatchFolderHandler(watch_folder_config, watch_folder_service)
    
    def test_init(self, handler, watch_folder_config, watch_folder_service):
        """Test handler initialization."""
        assert handler.config == watch_folder_config
        assert handler.watch_service == watch_folder_service
        assert handler.processed_files == set()
        assert handler.file_timestamps == {}
    
    def test_on_created_file(self, handler):
        """Test handling file creation event."""
        # Create file event
        event = FileCreatedEvent("/test/watch/folder/video.mp4")
        event.is_directory = False
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_created(event)
            mock_handle.assert_called_once_with("/test/watch/folder/video.mp4", "created")
    
    def test_on_created_directory(self, handler):
        """Test handling directory creation event (should be ignored)."""
        # Create directory event
        event = DirCreatedEvent("/test/watch/folder/subdir")
        event.is_directory = True
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_created(event)
            mock_handle.assert_not_called()
    
    def test_on_moved_file(self, handler):
        """Test handling file move event."""
        # Create move event
        event = FileMovedEvent("/test/watch/folder/temp.mp4", "/test/watch/folder/video.mp4")
        event.is_directory = False
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_moved(event)
            mock_handle.assert_called_once_with("/test/watch/folder/video.mp4", "moved")
    
    def test_handle_file_event_matching_filter(self, handler):
        """Test handling file event with matching filter."""
        file_path = "/test/watch/folder/video.mp4"
        
        with patch.object(handler, '_matches_filters', return_value=True):
            with patch('asyncio.create_task') as mock_create_task:
                with patch('time.time', return_value=123456.0):
                    handler._handle_file_event(file_path, "created")
                    
                    assert handler.file_timestamps[file_path] == 123456.0
                    mock_create_task.assert_called_once()
    
    def test_handle_file_event_not_matching_filter(self, handler):
        """Test handling file event with non-matching filter."""
        file_path = "/test/watch/folder/document.pdf"
        
        with patch.object(handler, '_matches_filters', return_value=False):
            with patch('asyncio.create_task') as mock_create_task:
                handler._handle_file_event(file_path, "created")
                
                assert file_path not in handler.file_timestamps
                mock_create_task.assert_not_called()
    
    def test_handle_file_event_already_processed(self, handler):
        """Test handling file event for already processed file."""
        file_path = "/test/watch/folder/video.mp4"
        handler.processed_files.add(file_path)
        
        with patch.object(handler, '_matches_filters', return_value=True):
            with patch('asyncio.create_task') as mock_create_task:
                handler._handle_file_event(file_path, "created")
                
                # Should not create new task
                mock_create_task.assert_not_called()
    
    def test_handle_file_event_exception(self, handler):
        """Test handling file event with exception."""
        file_path = "/test/watch/folder/video.mp4"
        
        with patch.object(handler, '_matches_filters', side_effect=Exception("Filter error")):
            # Should not raise exception
            handler._handle_file_event(file_path, "created")
            
            # File should not be in timestamps
            assert file_path not in handler.file_timestamps
    
    def test_matches_filters_include_patterns(self, handler):
        """Test filter matching with include patterns."""
        # Should match
        assert handler._matches_filters("/test/video.mp4") is True
        assert handler._matches_filters("/test/video.MOV") is True
        assert handler._matches_filters("/test/video.mxf") is True
        
        # Should not match
        assert handler._matches_filters("/test/video.pdf") is False
        assert handler._matches_filters("/test/document.txt") is False
    
    def test_matches_filters_exclude_patterns(self, handler):
        """Test filter matching with exclude patterns."""
        # Should be excluded
        assert handler._matches_filters("/test/temp_video.mp4") is False
        assert handler._matches_filters("/test/._video.mp4") is False
        
        # Should not be excluded
        assert handler._matches_filters("/test/video.mp4") is True
    
    def test_matches_filters_no_patterns(self, handler):
        """Test filter matching with no patterns."""
        handler.config.include_patterns = []
        handler.config.exclude_patterns = []
        
        # All files should match
        assert handler._matches_filters("/test/any_file.xyz") is True
    
    async def test_process_file_after_delay_success(self, handler):
        """Test successful file processing after delay."""
        file_path = "/test/watch/folder/video.mp4"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.getmtime', return_value=time.time() - 10):
                    with patch.object(
                        handler.watch_service,
                        '_create_ingest_job_for_file',
                        new_callable=AsyncMock
                    ) as mock_create:
                        await handler._process_file_after_delay(file_path)
                        
                        assert file_path in handler.processed_files
                        mock_create.assert_called_once_with(file_path, handler.config)
    
    async def test_process_file_after_delay_file_disappeared(self, handler):
        """Test processing when file disappears."""
        file_path = "/test/watch/folder/video.mp4"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('os.path.exists', return_value=False):
                with patch.object(
                    handler.watch_service,
                    '_create_ingest_job_for_file',
                    new_callable=AsyncMock
                ) as mock_create:
                    await handler._process_file_after_delay(file_path)
                    
                    # Should not create ingest job
                    mock_create.assert_not_called()
                    assert file_path not in handler.processed_files
    
    async def test_process_file_after_delay_still_changing(self, handler):
        """Test processing when file is still changing."""
        file_path = "/test/watch/folder/video.mp4"
        
        # First call: file still changing, second call: file stable
        mtime_values = [time.time() - 1, time.time() - 10]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.getmtime', side_effect=mtime_values):
                    with patch.object(
                        handler.watch_service,
                        '_create_ingest_job_for_file',
                        new_callable=AsyncMock
                    ) as mock_create:
                        await handler._process_file_after_delay(file_path)
                        
                        assert file_path in handler.processed_files
                        mock_create.assert_called_once_with(file_path, handler.config)
    
    async def test_process_file_after_delay_exception(self, handler):
        """Test processing with exception."""
        file_path = "/test/watch/folder/video.mp4"
        
        with patch('os.path.exists', side_effect=Exception("OS error")):
            # Should handle exception gracefully
            await handler._process_file_after_delay(file_path)
            
            assert file_path not in handler.processed_files


class TestWatchFolderService:
    """Test cases for WatchFolderService."""
    
    @pytest.fixture
    def service(self):
        """Create WatchFolderService instance."""
        return WatchFolderService()
    
    @pytest.fixture
    def mock_ingest_service(self):
        """Create mock IngestService."""
        mock = Mock(spec=IngestService)
        mock.create_job = AsyncMock()
        mock.process_job = AsyncMock()
        return mock
    
    @pytest.fixture
    def watch_folder_config(self):
        """Create watch folder configuration."""
        return WatchFolderConfig(
            id="test_watch_folder",
            path="/tmp/test_watch_folder",
            enabled=True,
            stability_delay=2.0,
            include_patterns=["mp4", "mov"],
            exclude_patterns=["temp"],
            recursive=True,
            destination_project_id="project123",
            auto_generate_proxies=True,
            preserve_folder_structure=True,
            priority=IngestPriority.NORMAL,
            tags=["watch_folder"],
            metadata_template={"source": "watch_folder"}
        )
    
    @pytest.fixture
    def temp_watch_folder(self):
        """Create temporary watch folder for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_init(self, service):
        """Test service initialization."""
        assert service.ingest_service is None
        assert service.watch_folders == {}
        assert service.observers == {}
        assert service.handlers == {}
        assert service._is_monitoring is False
    
    async def test_initialize(self, service, mock_ingest_service):
        """Test service initialization with ingest service."""
        with patch.object(service, '_load_watch_folders', new_callable=AsyncMock):
            with patch.object(service, 'start_monitoring', new_callable=AsyncMock):
                await service.initialize(mock_ingest_service)
                
                assert service.ingest_service == mock_ingest_service
                service._load_watch_folders.assert_called_once()
                service.start_monitoring.assert_called_once()
    
    async def test_create_watch_folder_success(self, service, watch_folder_config, temp_watch_folder):
        """Test successful watch folder creation."""
        watch_folder_config.path = temp_watch_folder
        
        with patch.object(service, '_start_watching_folder', new_callable=AsyncMock):
            result = await service.create_watch_folder(watch_folder_config)
            
            assert result == watch_folder_config
            assert watch_folder_config.id in service.watch_folders
            service._start_watching_folder.assert_called_once_with(watch_folder_config)
    
    async def test_create_watch_folder_path_not_exists(self, service, watch_folder_config):
        """Test watch folder creation with non-existent path."""
        watch_folder_config.path = "/non/existent/path"
        
        with pytest.raises(WatchFolderError, match="does not exist"):
            await service.create_watch_folder(watch_folder_config)
    
    async def test_create_watch_folder_not_directory(self, service, watch_folder_config):
        """Test watch folder creation with file instead of directory."""
        with tempfile.NamedTemporaryFile() as f:
            watch_folder_config.path = f.name
            
            with pytest.raises(WatchFolderError, match="not a directory"):
                await service.create_watch_folder(watch_folder_config)
    
    async def test_create_watch_folder_disabled(self, service, watch_folder_config, temp_watch_folder):
        """Test creating disabled watch folder."""
        watch_folder_config.path = temp_watch_folder
        watch_folder_config.enabled = False
        
        with patch.object(service, '_start_watching_folder', new_callable=AsyncMock):
            result = await service.create_watch_folder(watch_folder_config)
            
            assert result == watch_folder_config
            assert watch_folder_config.id in service.watch_folders
            # Should not start monitoring
            service._start_watching_folder.assert_not_called()
    
    async def test_list_watch_folders(self, service, watch_folder_config):
        """Test listing watch folders."""
        service.watch_folders = {
            "folder1": watch_folder_config,
            "folder2": watch_folder_config
        }
        
        result = await service.list_watch_folders()
        
        assert len(result) == 2
        assert watch_folder_config in result
    
    async def test_get_watch_folder_exists(self, service, watch_folder_config):
        """Test getting existing watch folder."""
        service.watch_folders[watch_folder_config.id] = watch_folder_config
        
        result = await service.get_watch_folder(watch_folder_config.id)
        
        assert result == watch_folder_config
    
    async def test_get_watch_folder_not_exists(self, service):
        """Test getting non-existent watch folder."""
        result = await service.get_watch_folder("non_existent")
        
        assert result is None
    
    async def test_update_watch_folder_success(self, service, watch_folder_config):
        """Test successful watch folder update."""
        folder_id = watch_folder_config.id
        service.watch_folders[folder_id] = watch_folder_config
        
        # Create updated config
        updated_config = watch_folder_config.model_copy()
        updated_config.tags = ["updated", "tags"]
        
        with patch.object(service, '_stop_watching_folder', new_callable=AsyncMock):
            with patch.object(service, '_start_watching_folder', new_callable=AsyncMock):
                result = await service.update_watch_folder(folder_id, updated_config)
                
                assert result == updated_config
                assert service.watch_folders[folder_id].tags == ["updated", "tags"]
                service._stop_watching_folder.assert_called_once_with(folder_id)
                service._start_watching_folder.assert_called_once_with(updated_config)
    
    async def test_update_watch_folder_not_exists(self, service, watch_folder_config):
        """Test updating non-existent watch folder."""
        result = await service.update_watch_folder("non_existent", watch_folder_config)
        
        assert result is None
    
    async def test_update_watch_folder_exception(self, service, watch_folder_config):
        """Test watch folder update with exception."""
        folder_id = watch_folder_config.id
        service.watch_folders[folder_id] = watch_folder_config
        
        # Create updated config
        updated_config = watch_folder_config.model_copy()
        updated_config.tags = ["updated", "tags"]
        
        with patch.object(
            service,
            '_stop_watching_folder',
            side_effect=Exception("Stop error")
        ):
            with pytest.raises(WatchFolderError, match="Failed to update"):
                await service.update_watch_folder(folder_id, updated_config)
            
            # Original config should be restored
            assert service.watch_folders[folder_id] == watch_folder_config
    
    async def test_delete_watch_folder_success(self, service, watch_folder_config):
        """Test successful watch folder deletion."""
        folder_id = watch_folder_config.id
        service.watch_folders[folder_id] = watch_folder_config
        
        with patch.object(service, '_stop_watching_folder', new_callable=AsyncMock):
            result = await service.delete_watch_folder(folder_id)
            
            assert result is True
            assert folder_id not in service.watch_folders
            service._stop_watching_folder.assert_called_once_with(folder_id)
    
    async def test_delete_watch_folder_not_exists(self, service):
        """Test deleting non-existent watch folder."""
        result = await service.delete_watch_folder("non_existent")
        
        assert result is False
    
    async def test_start_monitoring(self, service, watch_folder_config):
        """Test starting monitoring for all watch folders."""
        service.watch_folders = {
            "folder1": watch_folder_config,
            "folder2": watch_folder_config.model_copy(update={"enabled": False})
        }
        
        with patch.object(service, '_start_watching_folder', new_callable=AsyncMock):
            await service.start_monitoring()
            
            assert service._is_monitoring is True
            # Should only start monitoring for enabled folder
            service._start_watching_folder.assert_called_once_with(watch_folder_config)
    
    async def test_start_monitoring_already_started(self, service):
        """Test starting monitoring when already started."""
        service._is_monitoring = True
        
        with patch.object(service, '_start_watching_folder', new_callable=AsyncMock):
            await service.start_monitoring()
            
            # Should not start again
            service._start_watching_folder.assert_not_called()
    
    async def test_stop_monitoring(self, service):
        """Test stopping monitoring for all watch folders."""
        service._is_monitoring = True
        service.observers = {"folder1": Mock(), "folder2": Mock()}
        
        with patch.object(service, '_stop_watching_folder', new_callable=AsyncMock):
            await service.stop_monitoring()
            
            assert service._is_monitoring is False
            assert service._stop_watching_folder.call_count == 2
    
    async def test_start_watching_folder_success(self, service, watch_folder_config):
        """Test successful folder watching start."""
        # Mock Observer
        mock_observer = Mock()
        
        with patch('src.services.watch_folder_service.Observer', return_value=mock_observer):
            await service._start_watching_folder(watch_folder_config)
            
            assert watch_folder_config.id in service.observers
            assert watch_folder_config.id in service.handlers
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()
    
    async def test_start_watching_folder_already_watching(self, service, watch_folder_config):
        """Test starting to watch already watched folder."""
        service.observers[watch_folder_config.id] = Mock()
        
        with patch('src.services.watch_folder_service.Observer') as mock_observer_class:
            await service._start_watching_folder(watch_folder_config)
            
            # Should not create new observer
            mock_observer_class.assert_not_called()
    
    async def test_stop_watching_folder_success(self, service, watch_folder_config):
        """Test successful folder watching stop."""
        folder_id = watch_folder_config.id
        mock_observer = Mock()
        service.observers[folder_id] = mock_observer
        service.handlers[folder_id] = Mock()
        
        await service._stop_watching_folder(folder_id)
        
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5)
        assert folder_id not in service.observers
        assert folder_id not in service.handlers
    
    async def test_create_ingest_job_for_file_success(self, service, mock_ingest_service, watch_folder_config):
        """Test successful ingest job creation."""
        service.ingest_service = mock_ingest_service
        file_path = "/test/video.mp4"
        
        # Mock job creation
        mock_job = IngestJob(
            id="job123",
            source_path=file_path,
            ingest_type=IngestType.WATCH_FOLDER,
            status=IngestStatus.PENDING
        )
        mock_ingest_service.create_job.return_value = mock_job
        
        with patch('asyncio.create_task'):
            await service._create_ingest_job_for_file(file_path, watch_folder_config)
        
        # Verify job creation
        mock_ingest_service.create_job.assert_called_once()
        call_args = mock_ingest_service.create_job.call_args[0][0]
        assert call_args.source_path == file_path
        assert call_args.ingest_type == IngestType.WATCH_FOLDER
        assert call_args.priority == watch_folder_config.priority
    
    async def test_create_ingest_job_for_file_no_service(self, service, watch_folder_config):
        """Test ingest job creation without ingest service."""
        file_path = "/test/video.mp4"
        
        # Should handle gracefully (log error)
        await service._create_ingest_job_for_file(file_path, watch_folder_config)
    
    async def test_get_watch_folder_stats(self, service, watch_folder_config):
        """Test getting watch folder statistics."""
        folder_id = watch_folder_config.id
        service.watch_folders[folder_id] = watch_folder_config
        
        # Create mock handler
        mock_handler = Mock()
        mock_handler.processed_files = {"file1", "file2", "file3"}
        mock_handler.file_timestamps = {"file4": 123456, "file5": 123457}
        service.handlers[folder_id] = mock_handler
        
        # Create mock observer
        service.observers[folder_id] = Mock()
        
        stats = await service.get_watch_folder_stats(folder_id)
        
        assert stats["is_monitoring"] is True
        assert stats["processed_files"] == 3
        assert stats["pending_files"] == 2
    
    async def test_scan_watch_folder_success(self, service, watch_folder_config, temp_watch_folder):
        """Test successful watch folder scan."""
        watch_folder_config.path = temp_watch_folder
        service.watch_folders[watch_folder_config.id] = watch_folder_config
        
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(temp_watch_folder, f"video{i}.mp4")
            with open(file_path, 'w') as f:
                f.write(f"content{i}")
            test_files.append(file_path)
        
        # Create file that should be excluded
        excluded_file = os.path.join(temp_watch_folder, "temp_video.mp4")
        with open(excluded_file, 'w') as f:
            f.write("excluded")
        
        result = await service.scan_watch_folder(watch_folder_config.id)
        
        assert len(result) == 3
        assert all(f in result for f in test_files)
        assert excluded_file not in result
    
    async def test_scan_watch_folder_not_found(self, service):
        """Test scanning non-existent watch folder."""
        with pytest.raises(WatchFolderError, match="not found"):
            await service.scan_watch_folder("non_existent")
    
    async def test_process_existing_files(self, service, mock_ingest_service, watch_folder_config, temp_watch_folder):
        """Test processing existing files in watch folder."""
        service.ingest_service = mock_ingest_service
        watch_folder_config.path = temp_watch_folder
        service.watch_folders[watch_folder_config.id] = watch_folder_config
        
        # Create test file
        test_file = os.path.join(temp_watch_folder, "existing_video.mp4")
        with open(test_file, 'w') as f:
            f.write("existing content")
        
        with patch.object(service, '_create_ingest_job_for_file', new_callable=AsyncMock):
            result = await service.process_existing_files(watch_folder_config.id)
            
            service._create_ingest_job_for_file.assert_called_once_with(
                test_file,
                watch_folder_config
            )
    
    async def test_get_watch_folder_service_singleton(self):
        """Test that get_watch_folder_service returns singleton."""
        service1 = await get_watch_folder_service()
        service2 = await get_watch_folder_service()
        
        assert service1 is service2