"""
Test Hot Folder Service

Tests for immediate file ingestion through hot folders.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.events import FileCreatedEvent, FileMovedEvent, DirCreatedEvent

from src.services.hot_folder_service import (
    HotFolderService,
    HotFolderHandler,
    get_hot_folder_service
)
from src.models.schemas import (
    HotFolderConfig, IngestJobCreate, IngestJob, IngestType,
    IngestStatus, IngestPriority, ValidationRule
)
from src.core.exceptions import HotFolderError, IngestServiceError
from src.services.ingest_service import IngestService


class TestHotFolderHandler:
    """Test cases for HotFolderHandler."""
    
    @pytest.fixture
    def hot_folder_config(self):
        """Create hot folder configuration."""
        return HotFolderConfig(
            id="test_hot_folder",
            path="/test/hot/folder",
            enabled=True,
            immediate_processing=True,
            immediate_processing_delay=0.5,
            check_file_stability=True,
            stability_check_interval=1.0,
            include_patterns=["mp4", "mov", "mxf"],
            exclude_patterns=["temp", "._"],
            recursive=True,
            destination_project_id="project123",
            auto_generate_proxies=True,
            preserve_folder_structure=False,
            move_after_processing=True,
            processed_folder="/test/processed",
            delete_after_processing=False,
            tags=["hot_folder", "urgent"],
            metadata_template={"source": "hot_folder"}
        )
    
    @pytest.fixture
    def hot_folder_service(self):
        """Create HotFolderService instance."""
        service = HotFolderService()
        service.ingest_service = Mock(spec=IngestService)
        return service
    
    @pytest.fixture
    def handler(self, hot_folder_config, hot_folder_service):
        """Create HotFolderHandler instance."""
        return HotFolderHandler(hot_folder_config, hot_folder_service)
    
    def test_init(self, handler, hot_folder_config, hot_folder_service):
        """Test handler initialization."""
        assert handler.config == hot_folder_config
        assert handler.hot_folder_service == hot_folder_service
        assert handler.processing_files == set()
        assert handler.file_locks == {}
    
    def test_on_created_file(self, handler):
        """Test handling file creation event."""
        # Create file event
        event = FileCreatedEvent("/test/hot/folder/video.mp4")
        event.is_directory = False
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_created(event)
            mock_handle.assert_called_once_with("/test/hot/folder/video.mp4", "created")
    
    def test_on_created_directory(self, handler):
        """Test handling directory creation event (should be ignored)."""
        # Create directory event
        event = DirCreatedEvent("/test/hot/folder/subdir")
        event.is_directory = True
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_created(event)
            mock_handle.assert_not_called()
    
    def test_on_moved_file(self, handler):
        """Test handling file move event."""
        # Create move event
        event = FileMovedEvent("/test/hot/folder/temp.mp4", "/test/hot/folder/video.mp4")
        event.is_directory = False
        
        with patch.object(handler, '_handle_file_event') as mock_handle:
            handler.on_moved(event)
            mock_handle.assert_called_once_with("/test/hot/folder/video.mp4", "moved")
    
    def test_handle_file_event_matching_filter(self, handler):
        """Test handling file event with matching filter."""
        file_path = "/test/hot/folder/video.mp4"
        
        with patch.object(handler, '_matches_filters', return_value=True):
            with patch('asyncio.create_task') as mock_create_task:
                handler._handle_file_event(file_path, "created")
                
                assert file_path in handler.processing_files
                mock_create_task.assert_called_once()
    
    def test_handle_file_event_not_matching_filter(self, handler):
        """Test handling file event with non-matching filter."""
        file_path = "/test/hot/folder/document.pdf"
        
        with patch.object(handler, '_matches_filters', return_value=False):
            with patch('asyncio.create_task') as mock_create_task:
                handler._handle_file_event(file_path, "created")
                
                assert file_path not in handler.processing_files
                mock_create_task.assert_not_called()
    
    def test_handle_file_event_already_processing(self, handler):
        """Test handling file event for already processing file."""
        file_path = "/test/hot/folder/video.mp4"
        handler.processing_files.add(file_path)
        
        with patch.object(handler, '_matches_filters', return_value=True):
            with patch('asyncio.create_task') as mock_create_task:
                handler._handle_file_event(file_path, "created")
                
                # Should not create new task
                mock_create_task.assert_not_called()
    
    def test_handle_file_event_exception(self, handler):
        """Test handling file event with exception."""
        file_path = "/test/hot/folder/video.mp4"
        
        with patch.object(handler, '_matches_filters', side_effect=Exception("Filter error")):
            # Should not raise exception
            handler._handle_file_event(file_path, "created")
            
            # File should not be in processing set
            assert file_path not in handler.processing_files
    
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
    
    async def test_process_file_immediately_success(self, handler):
        """Test immediate file processing success."""
        file_path = "/test/hot/folder/video.mp4"
        
        with patch('os.path.exists', return_value=True):
            with patch.object(handler, '_is_file_stable', return_value=True):
                with patch.object(
                    handler.hot_folder_service,
                    '_create_immediate_ingest_job',
                    new_callable=AsyncMock
                ) as mock_create:
                    await handler._process_file_immediately(file_path)
                    
                    mock_create.assert_called_once_with(file_path, handler.config)
                    assert file_path not in handler.processing_files
    
    async def test_process_file_immediately_file_disappeared(self, handler):
        """Test processing when file disappears."""
        file_path = "/test/hot/folder/video.mp4"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('os.path.exists', return_value=False):
                with patch.object(
                    handler.hot_folder_service,
                    '_create_immediate_ingest_job',
                    new_callable=AsyncMock
                ) as mock_create:
                    await handler._process_file_immediately(file_path)
                    
                    # Should not create ingest job
                    mock_create.assert_not_called()
    
    async def test_process_file_immediately_not_stable(self, handler):
        """Test processing when file is not stable."""
        file_path = "/test/hot/folder/video.mp4"
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('os.path.exists', return_value=True):
                with patch.object(handler, '_is_file_stable', return_value=False):
                    with patch.object(
                        handler.hot_folder_service,
                        '_create_immediate_ingest_job',
                        new_callable=AsyncMock
                    ) as mock_create:
                        await handler._process_file_immediately(file_path)
                        
                        # Should not create ingest job
                        mock_create.assert_not_called()
    
    async def test_process_file_immediately_exception(self, handler):
        """Test processing with exception."""
        file_path = "/test/hot/folder/video.mp4"
        handler.processing_files.add(file_path)
        
        with patch('os.path.exists', side_effect=Exception("OS error")):
            await handler._process_file_immediately(file_path)
            
            # Should clean up processing set
            assert file_path not in handler.processing_files
    
    async def test_is_file_stable_true(self, handler):
        """Test file stability check when stable."""
        file_path = "/test/video.mp4"
        
        # Mock consistent file stats
        mock_stat = MagicMock()
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 123456789.0
        
        with patch('os.stat', return_value=mock_stat):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await handler._is_file_stable(file_path)
                assert result is True
    
    async def test_is_file_stable_false(self, handler):
        """Test file stability check when not stable."""
        file_path = "/test/video.mp4"
        
        # Mock changing file stats
        mock_stat1 = MagicMock()
        mock_stat1.st_size = 1024
        mock_stat1.st_mtime = 123456789.0
        
        mock_stat2 = MagicMock()
        mock_stat2.st_size = 2048  # Size changed
        mock_stat2.st_mtime = 123456790.0
        
        with patch('os.stat', side_effect=[mock_stat1, mock_stat2]):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await handler._is_file_stable(file_path)
                assert result is False
    
    async def test_is_file_stable_os_error(self, handler):
        """Test file stability check with OS error."""
        file_path = "/test/video.mp4"
        
        with patch('os.stat', side_effect=OSError("File not found")):
            result = await handler._is_file_stable(file_path)
            assert result is False


class TestHotFolderService:
    """Test cases for HotFolderService."""
    
    @pytest.fixture
    def service(self):
        """Create HotFolderService instance."""
        return HotFolderService()
    
    @pytest.fixture
    def mock_ingest_service(self):
        """Create mock IngestService."""
        mock = Mock(spec=IngestService)
        mock.create_job = AsyncMock()
        mock.process_job = AsyncMock()
        return mock
    
    @pytest.fixture
    def hot_folder_config(self):
        """Create hot folder configuration."""
        return HotFolderConfig(
            id="test_hot_folder",
            path="/tmp/test_hot_folder",
            enabled=True,
            immediate_processing=True,
            immediate_processing_delay=0.5,
            check_file_stability=True,
            stability_check_interval=1.0,
            include_patterns=["mp4", "mov"],
            exclude_patterns=["temp"],
            recursive=True,
            destination_project_id="project123",
            auto_generate_proxies=True,
            preserve_folder_structure=False,
            move_after_processing=False,
            delete_after_processing=False,
            tags=["hot_folder"],
            metadata_template={"source": "hot_folder"}
        )
    
    @pytest.fixture
    def temp_hot_folder(self):
        """Create temporary hot folder for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_init(self, service):
        """Test service initialization."""
        assert service.ingest_service is None
        assert service.hot_folders == {}
        assert service.observers == {}
        assert service.handlers == {}
        assert service._is_monitoring is False
        assert service._processing_stats["total_processed"] == 0
        assert service._processing_stats["total_failed"] == 0
    
    async def test_initialize(self, service, mock_ingest_service):
        """Test service initialization with ingest service."""
        with patch.object(service, '_load_hot_folders', new_callable=AsyncMock):
            with patch.object(service, 'start_monitoring', new_callable=AsyncMock):
                await service.initialize(mock_ingest_service)
                
                assert service.ingest_service == mock_ingest_service
                service._load_hot_folders.assert_called_once()
                service.start_monitoring.assert_called_once()
    
    async def test_create_hot_folder_success(self, service, hot_folder_config, temp_hot_folder):
        """Test successful hot folder creation."""
        hot_folder_config.path = temp_hot_folder
        
        with patch.object(service, '_start_monitoring_folder', new_callable=AsyncMock):
            result = await service.create_hot_folder(hot_folder_config)
            
            assert result == hot_folder_config
            assert hot_folder_config.id in service.hot_folders
            service._start_monitoring_folder.assert_called_once_with(hot_folder_config)
    
    async def test_create_hot_folder_path_not_exists(self, service, hot_folder_config):
        """Test hot folder creation with non-existent path."""
        hot_folder_config.path = "/non/existent/path"
        
        with pytest.raises(HotFolderError, match="does not exist"):
            await service.create_hot_folder(hot_folder_config)
    
    async def test_create_hot_folder_not_directory(self, service, hot_folder_config):
        """Test hot folder creation with file instead of directory."""
        with tempfile.NamedTemporaryFile() as f:
            hot_folder_config.path = f.name
            
            with pytest.raises(HotFolderError, match="not a directory"):
                await service.create_hot_folder(hot_folder_config)
    
    async def test_create_hot_folder_no_permissions(self, service, hot_folder_config):
        """Test hot folder creation without permissions."""
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isdir', return_value=True):
                with patch('os.access', return_value=False):
                    with pytest.raises(HotFolderError, match="Insufficient permissions"):
                        await service.create_hot_folder(hot_folder_config)
    
    async def test_create_hot_folder_disabled(self, service, hot_folder_config, temp_hot_folder):
        """Test creating disabled hot folder."""
        hot_folder_config.path = temp_hot_folder
        hot_folder_config.enabled = False
        
        with patch.object(service, '_start_monitoring_folder', new_callable=AsyncMock):
            result = await service.create_hot_folder(hot_folder_config)
            
            assert result == hot_folder_config
            assert hot_folder_config.id in service.hot_folders
            # Should not start monitoring
            service._start_monitoring_folder.assert_not_called()
    
    async def test_list_hot_folders(self, service, hot_folder_config):
        """Test listing hot folders."""
        service.hot_folders = {
            "folder1": hot_folder_config,
            "folder2": hot_folder_config
        }
        
        result = await service.list_hot_folders()
        
        assert len(result) == 2
        assert hot_folder_config in result
    
    async def test_get_hot_folder_exists(self, service, hot_folder_config):
        """Test getting existing hot folder."""
        service.hot_folders[hot_folder_config.id] = hot_folder_config
        
        result = await service.get_hot_folder(hot_folder_config.id)
        
        assert result == hot_folder_config
    
    async def test_get_hot_folder_not_exists(self, service):
        """Test getting non-existent hot folder."""
        result = await service.get_hot_folder("non_existent")
        
        assert result is None
    
    async def test_update_hot_folder_success(self, service, hot_folder_config):
        """Test successful hot folder update."""
        folder_id = hot_folder_config.id
        service.hot_folders[folder_id] = hot_folder_config
        
        # Create updated config
        updated_config = hot_folder_config.model_copy()
        updated_config.tags = ["updated", "tags"]
        
        with patch.object(service, '_stop_monitoring_folder', new_callable=AsyncMock):
            with patch.object(service, '_start_monitoring_folder', new_callable=AsyncMock):
                result = await service.update_hot_folder(folder_id, updated_config)
                
                assert result == updated_config
                assert service.hot_folders[folder_id].tags == ["updated", "tags"]
                service._stop_monitoring_folder.assert_called_once_with(folder_id)
                service._start_monitoring_folder.assert_called_once_with(updated_config)
    
    async def test_update_hot_folder_not_exists(self, service, hot_folder_config):
        """Test updating non-existent hot folder."""
        result = await service.update_hot_folder("non_existent", hot_folder_config)
        
        assert result is None
    
    async def test_update_hot_folder_exception(self, service, hot_folder_config):
        """Test hot folder update with exception."""
        folder_id = hot_folder_config.id
        service.hot_folders[folder_id] = hot_folder_config
        
        # Create updated config
        updated_config = hot_folder_config.model_copy()
        updated_config.tags = ["updated", "tags"]
        
        with patch.object(
            service,
            '_stop_monitoring_folder',
            side_effect=Exception("Stop error")
        ):
            with pytest.raises(HotFolderError, match="Failed to update"):
                await service.update_hot_folder(folder_id, updated_config)
            
            # Original config should be restored
            assert service.hot_folders[folder_id] == hot_folder_config
    
    async def test_delete_hot_folder_success(self, service, hot_folder_config):
        """Test successful hot folder deletion."""
        folder_id = hot_folder_config.id
        service.hot_folders[folder_id] = hot_folder_config
        
        with patch.object(service, '_stop_monitoring_folder', new_callable=AsyncMock):
            result = await service.delete_hot_folder(folder_id)
            
            assert result is True
            assert folder_id not in service.hot_folders
            service._stop_monitoring_folder.assert_called_once_with(folder_id)
    
    async def test_delete_hot_folder_not_exists(self, service):
        """Test deleting non-existent hot folder."""
        result = await service.delete_hot_folder("non_existent")
        
        assert result is False
    
    async def test_start_monitoring(self, service, hot_folder_config):
        """Test starting monitoring for all hot folders."""
        service.hot_folders = {
            "folder1": hot_folder_config,
            "folder2": hot_folder_config.model_copy(update={"enabled": False})
        }
        
        with patch.object(service, '_start_monitoring_folder', new_callable=AsyncMock):
            await service.start_monitoring()
            
            assert service._is_monitoring is True
            # Should only start monitoring for enabled folder
            service._start_monitoring_folder.assert_called_once_with(hot_folder_config)
    
    async def test_start_monitoring_already_started(self, service):
        """Test starting monitoring when already started."""
        service._is_monitoring = True
        
        with patch.object(service, '_start_monitoring_folder', new_callable=AsyncMock):
            await service.start_monitoring()
            
            # Should not start again
            service._start_monitoring_folder.assert_not_called()
    
    async def test_stop_monitoring(self, service):
        """Test stopping monitoring for all hot folders."""
        service._is_monitoring = True
        service.observers = {"folder1": Mock(), "folder2": Mock()}
        
        with patch.object(service, '_stop_monitoring_folder', new_callable=AsyncMock):
            await service.stop_monitoring()
            
            assert service._is_monitoring is False
            assert service._stop_monitoring_folder.call_count == 2
    
    async def test_create_immediate_ingest_job_success(self, service, mock_ingest_service, hot_folder_config):
        """Test successful immediate ingest job creation."""
        service.ingest_service = mock_ingest_service
        file_path = "/test/video.mp4"
        
        # Mock job creation
        mock_job = IngestJob(
            id="job123",
            source_path=file_path,
            ingest_type=IngestType.HOT_FOLDER,
            status=IngestStatus.PENDING
        )
        mock_ingest_service.create_job.return_value = mock_job
        
        await service._create_immediate_ingest_job(file_path, hot_folder_config)
        
        # Verify job creation
        mock_ingest_service.create_job.assert_called_once()
        call_args = mock_ingest_service.create_job.call_args[0][0]
        assert call_args.source_path == file_path
        assert call_args.priority == IngestPriority.URGENT
        assert call_args.ingest_type == IngestType.HOT_FOLDER
        
        # Verify immediate processing
        mock_ingest_service.process_job.assert_called_once_with("job123")
    
    async def test_create_immediate_ingest_job_no_service(self, service, hot_folder_config):
        """Test ingest job creation without ingest service."""
        file_path = "/test/video.mp4"
        
        # Should handle gracefully (log error)
        await service._create_immediate_ingest_job(file_path, hot_folder_config)
        
        # Verify stats updated
        assert service._processing_stats["total_failed"] == 1
    
    async def test_move_processed_file_success(self, service, hot_folder_config, temp_hot_folder):
        """Test successful file move after processing."""
        # Create source file
        source_file = os.path.join(temp_hot_folder, "video.mp4")
        with open(source_file, 'w') as f:
            f.write("test content")
        
        # Set processed folder
        processed_folder = os.path.join(temp_hot_folder, "processed")
        hot_folder_config.processed_folder = processed_folder
        
        await service._move_processed_file(source_file, hot_folder_config)
        
        # Verify file moved
        assert not os.path.exists(source_file)
        assert os.path.exists(os.path.join(processed_folder, "video.mp4"))
    
    async def test_move_processed_file_name_conflict(self, service, hot_folder_config, temp_hot_folder):
        """Test file move with naming conflict."""
        # Create source and existing file
        source_file = os.path.join(temp_hot_folder, "video.mp4")
        processed_folder = os.path.join(temp_hot_folder, "processed")
        os.makedirs(processed_folder, exist_ok=True)
        
        # Create existing file
        existing_file = os.path.join(processed_folder, "video.mp4")
        with open(existing_file, 'w') as f:
            f.write("existing")
        
        # Create source file
        with open(source_file, 'w') as f:
            f.write("new content")
        
        hot_folder_config.processed_folder = processed_folder
        
        await service._move_processed_file(source_file, hot_folder_config)
        
        # Verify file moved with new name
        assert not os.path.exists(source_file)
        assert os.path.exists(os.path.join(processed_folder, "video_1.mp4"))
    
    async def test_delete_processed_file_success(self, service, hot_folder_config, temp_hot_folder):
        """Test successful file deletion after processing."""
        # Create file
        test_file = os.path.join(temp_hot_folder, "video.mp4")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        await service._delete_processed_file(test_file, hot_folder_config)
        
        # Verify file deleted
        assert not os.path.exists(test_file)
    
    def test_update_processing_stats_success(self, service):
        """Test updating processing stats on success."""
        initial_processed = service._processing_stats["total_processed"]
        
        service._update_processing_stats(1.5, success=True)
        
        assert service._processing_stats["total_processed"] == initial_processed + 1
        assert service._processing_stats["average_processing_time"] == 1.5
    
    def test_update_processing_stats_failure(self, service):
        """Test updating processing stats on failure."""
        initial_failed = service._processing_stats["total_failed"]
        
        service._update_processing_stats(2.0, success=False)
        
        assert service._processing_stats["total_failed"] == initial_failed + 1
        assert service._processing_stats["average_processing_time"] == 2.0
    
    async def test_get_hot_folder_stats(self, service, hot_folder_config):
        """Test getting hot folder statistics."""
        folder_id = hot_folder_config.id
        service.hot_folders[folder_id] = hot_folder_config
        
        # Create mock handler
        mock_handler = Mock()
        mock_handler.processing_files = {"file1", "file2"}
        mock_handler.file_locks = {"file1": Mock()}
        service.handlers[folder_id] = mock_handler
        
        # Create mock observer
        service.observers[folder_id] = Mock()
        
        stats = await service.get_hot_folder_stats(folder_id)
        
        assert stats["is_monitoring"] is True
        assert stats["currently_processing"] == 2
        assert stats["active_locks"] == 1
        assert stats["immediate_processing"] == hot_folder_config.immediate_processing
        assert stats["configuration"]["path"] == hot_folder_config.path
    
    async def test_get_service_stats(self, service, hot_folder_config):
        """Test getting service statistics."""
        service.hot_folders = {
            "folder1": hot_folder_config,
            "folder2": hot_folder_config.model_copy(update={"enabled": False})
        }
        service._is_monitoring = True
        service._processing_stats = {
            "total_processed": 10,
            "total_failed": 2,
            "average_processing_time": 1.5
        }
        
        stats = await service.get_service_stats()
        
        assert stats["total_hot_folders"] == 2
        assert stats["active_hot_folders"] == 1
        assert stats["monitoring_status"] is True
        assert stats["processing_stats"]["total_processed"] == 10
    
    async def test_trigger_folder_scan_success(self, service, mock_ingest_service, hot_folder_config, temp_hot_folder):
        """Test manual folder scan."""
        service.ingest_service = mock_ingest_service
        hot_folder_config.path = temp_hot_folder
        service.hot_folders[hot_folder_config.id] = hot_folder_config
        
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(temp_hot_folder, f"video{i}.mp4")
            with open(file_path, 'w') as f:
                f.write(f"content{i}")
            test_files.append(file_path)
        
        # Create file that should be excluded
        excluded_file = os.path.join(temp_hot_folder, "temp_video.mp4")
        with open(excluded_file, 'w') as f:
            f.write("excluded")
        
        with patch.object(service, '_create_immediate_ingest_job', new_callable=AsyncMock):
            result = await service.trigger_folder_scan(hot_folder_config.id)
            
            assert len(result) == 3
            assert all(f in result for f in test_files)
            assert excluded_file not in result
            assert service._create_immediate_ingest_job.call_count == 3
    
    async def test_trigger_folder_scan_not_found(self, service):
        """Test manual scan of non-existent folder."""
        with pytest.raises(HotFolderError, match="not found"):
            await service.trigger_folder_scan("non_existent")
    
    async def test_get_hot_folder_service_singleton(self):
        """Test that get_hot_folder_service returns singleton."""
        service1 = await get_hot_folder_service()
        service2 = await get_hot_folder_service()
        
        assert service1 is service2