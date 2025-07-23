"""
Tests for Dropbox Storage Driver

This module contains comprehensive tests for the Dropbox storage driver.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import hashlib
from typing import Dict, Any

from src.drivers.dropbox_driver import DropboxStorageDriver
from src.core.interfaces import (
    ObjectNotFoundError, StorageQuotaExceededError, 
    StoragePermissionError, InvalidStorageOperationError,
    StorageOperationError, StorageObject, PresignedUrl
)


class MockDropboxMetadata:
    """Mock Dropbox file metadata"""
    def __init__(self, path: str, size: int = 1024, is_file: bool = True):
        self.path_display = path
        self.path_lower = path.lower()
        self.size = size if is_file else None
        self.server_modified = datetime.utcnow()
        self.client_modified = datetime.utcnow()
        self.content_hash = hashlib.md5(f"{path}_{size}".encode()).hexdigest()
        self.id = f"id_{hashlib.md5(path.encode()).hexdigest()[:8]}"
        self.rev = f"rev_{hashlib.md5(path.encode()).hexdigest()[:8]}"
        if not is_file:
            self.entries = []


class MockDropboxError:
    """Mock Dropbox API error"""
    def __init__(self, error_type: str):
        self.error_type = error_type
    
    def is_path_not_found(self):
        return self.error_type == "path_not_found"
    
    def is_path_malformed(self):
        return self.error_type == "path_malformed"
    
    def is_insufficient_space(self):
        return self.error_type == "insufficient_space"
    
    def is_from_path_not_found(self):
        return self.error_type == "from_path_not_found"
    
    def is_to_path_malformed(self):
        return self.error_type == "to_path_malformed"


@pytest.fixture
def dropbox_config():
    """Dropbox configuration for testing"""
    return {
        "access_token": "test_access_token",
        "app_key": "test_app_key",
        "app_secret": "test_app_secret",
        "refresh_token": "test_refresh_token",
        "path_prefix": "/mams_test",
        "chunk_size": 8 * 1024 * 1024
    }


@pytest.fixture
def mock_dropbox_client():
    """Mock Dropbox client"""
    with patch('src.drivers.dropbox_driver.dropbox') as mock_dropbox:
        client = MagicMock()
        mock_dropbox.Dropbox.return_value = client
        
        # Mock WriteMode and other enums
        mock_dropbox.files.WriteMode.overwrite = "overwrite"
        mock_dropbox.files.UploadSessionCursor = MagicMock
        mock_dropbox.files.CommitInfo = MagicMock
        mock_dropbox.sharing.SharedLinkSettings = MagicMock
        
        yield client, mock_dropbox


@pytest.mark.asyncio
class TestDropboxStorageDriver:
    """Test cases for Dropbox storage driver"""
    
    async def test_initialization(self, dropbox_config, mock_dropbox_client):
        """Test driver initialization"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        
        assert driver.access_token == dropbox_config["access_token"]
        assert driver.path_prefix == "/mams_test"
        assert driver.chunk_size == 8 * 1024 * 1024
        mock_dropbox.Dropbox.assert_called_once_with(dropbox_config["access_token"])
    
    async def test_initialization_missing_token(self, dropbox_config, mock_dropbox_client):
        """Test initialization with missing access token"""
        client, mock_dropbox = mock_dropbox_client
        
        dropbox_config.pop("access_token")
        with pytest.raises(ValueError, match="access_token is required"):
            DropboxStorageDriver(dropbox_config)
    
    async def test_get_object_info_success(self, dropbox_config, mock_dropbox_client):
        """Test successful object info retrieval"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock response
        mock_metadata = MockDropboxMetadata("/mams_test/test.txt", 1024)
        client.files_get_metadata.return_value = mock_metadata
        
        driver = DropboxStorageDriver(dropbox_config)
        obj_info = await driver.get_object_info("test.txt")
        
        assert obj_info.key == "test.txt"
        assert obj_info.size == 1024
        assert obj_info.etag == mock_metadata.content_hash
        assert obj_info.version_id == mock_metadata.rev
        client.files_get_metadata.assert_called_once_with("/mams_test/test.txt")
    
    async def test_get_object_info_not_found(self, dropbox_config, mock_dropbox_client):
        """Test object info retrieval for non-existent object"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock API error
        error = MagicMock()
        error.error = MockDropboxError("path_not_found")
        client.files_get_metadata.side_effect = type('ApiError', (), {'error': error.error})()
        
        driver = DropboxStorageDriver(dropbox_config)
        with pytest.raises(ObjectNotFoundError):
            await driver.get_object_info("nonexistent.txt")
    
    async def test_get_object_success(self, dropbox_config, mock_dropbox_client):
        """Test successful object download"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.content = b"test content"
        client.files_download.return_value = (None, mock_response)
        
        driver = DropboxStorageDriver(dropbox_config)
        content = await driver.get_object("test.txt")
        
        assert content == b"test content"
        client.files_download.assert_called_once_with("/mams_test/test.txt")
    
    async def test_put_object_small_file(self, dropbox_config, mock_dropbox_client):
        """Test uploading a small file"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock response
        mock_metadata = MockDropboxMetadata("/mams_test/test.txt", 100)
        client.files_upload.return_value = mock_metadata
        
        driver = DropboxStorageDriver(dropbox_config)
        data = b"small file content"
        result = await driver.put_object("test.txt", data)
        
        assert result.key == "test.txt"
        assert result.size == 100
        client.files_upload.assert_called_once()
    
    async def test_put_object_large_file(self, dropbox_config, mock_dropbox_client):
        """Test uploading a large file using upload session"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock upload session
        session_result = MagicMock()
        session_result.session_id = "test_session_id"
        client.files_upload_session_start.return_value = session_result
        
        mock_metadata = MockDropboxMetadata("/mams_test/large.txt", 20 * 1024 * 1024)
        client.files_upload_session_finish.return_value = mock_metadata
        
        driver = DropboxStorageDriver(dropbox_config)
        driver.chunk_size = 1024  # Small chunk size for testing
        
        data = b"x" * 2048  # Large enough to trigger chunked upload
        result = await driver.put_object("large.txt", data)
        
        assert result.key == "large.txt"
        client.files_upload_session_start.assert_called_once()
        client.files_upload_session_finish.assert_called_once()
    
    async def test_put_object_quota_exceeded(self, dropbox_config, mock_dropbox_client):
        """Test upload with quota exceeded error"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock API error
        error = MagicMock()
        error.error = MockDropboxError("insufficient_space")
        client.files_upload.side_effect = type('ApiError', (), {'error': error.error})()
        
        driver = DropboxStorageDriver(dropbox_config)
        with pytest.raises(StorageQuotaExceededError):
            await driver.put_object("test.txt", b"content")
    
    async def test_delete_object_success(self, dropbox_config, mock_dropbox_client):
        """Test successful object deletion"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        result = await driver.delete_object("test.txt")
        
        assert result is True
        client.files_delete_v2.assert_called_once_with("/mams_test/test.txt")
    
    async def test_delete_object_not_found(self, dropbox_config, mock_dropbox_client):
        """Test deleting non-existent object"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock API error
        error = MagicMock()
        error.error = MockDropboxError("path_not_found")
        client.files_delete_v2.side_effect = type('ApiError', (), {'error': error.error})()
        
        driver = DropboxStorageDriver(dropbox_config)
        result = await driver.delete_object("nonexistent.txt")
        
        assert result is False
    
    async def test_list_objects_success(self, dropbox_config, mock_dropbox_client):
        """Test listing objects"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock list folder result
        result = MagicMock()
        result.entries = [
            MockDropboxMetadata("/mams_test/file1.txt", 100),
            MockDropboxMetadata("/mams_test/file2.txt", 200),
        ]
        result.has_more = False
        result.cursor = None
        client.files_list_folder.return_value = result
        
        driver = DropboxStorageDriver(dropbox_config)
        objects, next_token = await driver.list_objects()
        
        assert len(objects) == 2
        assert objects[0].key == "file1.txt"
        assert objects[1].key == "file2.txt"
        assert next_token is None
    
    async def test_list_objects_with_continuation(self, dropbox_config, mock_dropbox_client):
        """Test listing objects with continuation token"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock continued listing
        result = MagicMock()
        result.entries = [MockDropboxMetadata("/mams_test/file3.txt", 300)]
        result.has_more = False
        result.cursor = None
        client.files_list_folder_continue.return_value = result
        
        driver = DropboxStorageDriver(dropbox_config)
        objects, next_token = await driver.list_objects(continuation_token="test_cursor")
        
        assert len(objects) == 1
        assert objects[0].key == "file3.txt"
        client.files_list_folder_continue.assert_called_once_with("test_cursor")
    
    async def test_copy_object_success(self, dropbox_config, mock_dropbox_client):
        """Test copying an object"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock response
        response = MagicMock()
        response.metadata = MockDropboxMetadata("/mams_test/dest.txt", 100)
        client.files_copy_v2.return_value = response
        
        driver = DropboxStorageDriver(dropbox_config)
        result = await driver.copy_object("source.txt", "dest.txt")
        
        assert result.key == "dest.txt"
        client.files_copy_v2.assert_called_once_with(
            "/mams_test/source.txt", 
            "/mams_test/dest.txt"
        )
    
    async def test_move_object_success(self, dropbox_config, mock_dropbox_client):
        """Test moving an object"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock response
        response = MagicMock()
        response.metadata = MockDropboxMetadata("/mams_test/dest.txt", 100)
        client.files_move_v2.return_value = response
        
        driver = DropboxStorageDriver(dropbox_config)
        result = await driver.move_object("source.txt", "dest.txt")
        
        assert result.key == "dest.txt"
        client.files_move_v2.assert_called_once_with(
            "/mams_test/source.txt", 
            "/mams_test/dest.txt"
        )
    
    async def test_exists_true(self, dropbox_config, mock_dropbox_client):
        """Test checking if object exists (exists)"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock successful metadata retrieval
        mock_metadata = MockDropboxMetadata("/mams_test/test.txt", 100)
        client.files_get_metadata.return_value = mock_metadata
        
        driver = DropboxStorageDriver(dropbox_config)
        exists = await driver.exists("test.txt")
        
        assert exists is True
    
    async def test_exists_false(self, dropbox_config, mock_dropbox_client):
        """Test checking if object exists (doesn't exist)"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock API error
        error = MagicMock()
        error.error = MockDropboxError("path_not_found")
        client.files_get_metadata.side_effect = type('ApiError', (), {'error': error.error})()
        
        driver = DropboxStorageDriver(dropbox_config)
        exists = await driver.exists("nonexistent.txt")
        
        assert exists is False
    
    async def test_get_presigned_url_existing_link(self, dropbox_config, mock_dropbox_client):
        """Test generating presigned URL with existing shared link"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock existing shared link
        shared_link = MagicMock()
        shared_link.url = "https://www.dropbox.com/s/abcd1234/test.txt?dl=0"
        
        links_result = MagicMock()
        links_result.links = [shared_link]
        client.sharing_list_shared_links.return_value = links_result
        
        driver = DropboxStorageDriver(dropbox_config)
        presigned_url = await driver.get_presigned_url("test.txt")
        
        assert "dl.dropboxusercontent.com" in presigned_url.url
        assert presigned_url.url.endswith("?dl=1")
        assert presigned_url.expires_at > datetime.utcnow()
    
    async def test_get_presigned_url_create_new(self, dropbox_config, mock_dropbox_client):
        """Test generating presigned URL by creating new shared link"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock no existing links
        links_result = MagicMock()
        links_result.links = []
        client.sharing_list_shared_links.return_value = links_result
        
        # Mock creating new link
        new_link = MagicMock()
        new_link.url = "https://www.dropbox.com/s/efgh5678/test.txt?dl=0"
        client.sharing_create_shared_link_with_settings.return_value = new_link
        
        driver = DropboxStorageDriver(dropbox_config)
        presigned_url = await driver.get_presigned_url("test.txt", expires_in=7200)
        
        assert "dl.dropboxusercontent.com" in presigned_url.url
        assert presigned_url.url.endswith("?dl=1")
        client.sharing_create_shared_link_with_settings.assert_called_once()
    
    async def test_get_presigned_url_fallback(self, dropbox_config, mock_dropbox_client):
        """Test presigned URL generation fallback"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock exception when trying to get/create shared link
        client.sharing_list_shared_links.side_effect = Exception("API error")
        
        driver = DropboxStorageDriver(dropbox_config)
        presigned_url = await driver.get_presigned_url("test.txt")
        
        assert "content.dropboxapi.com" in presigned_url.url
        assert "Authorization" in presigned_url.headers
        assert "Dropbox-API-Arg" in presigned_url.headers
    
    async def test_create_multipart_upload(self, dropbox_config, mock_dropbox_client):
        """Test creating multipart upload session"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock session start
        session_result = MagicMock()
        session_result.session_id = "test_session_123"
        client.files_upload_session_start.return_value = session_result
        
        driver = DropboxStorageDriver(dropbox_config)
        upload_id = await driver.create_multipart_upload("test.txt")
        
        assert upload_id.startswith("dropbox_test_session_123_")
        client.files_upload_session_start.assert_called_once_with(b"")
    
    async def test_upload_part(self, dropbox_config, mock_dropbox_client):
        """Test uploading a part in multipart upload"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        upload_id = "dropbox_session123_hash456"
        part_data = b"part content"
        
        result = await driver.upload_part("test.txt", upload_id, 2, part_data)
        
        assert result["PartNumber"] == 2
        assert result["Size"] == len(part_data)
        assert "ETag" in result
        client.files_upload_session_append_v2.assert_called_once()
    
    async def test_complete_multipart_upload(self, dropbox_config, mock_dropbox_client):
        """Test completing multipart upload"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock completion response
        mock_metadata = MockDropboxMetadata("/mams_test/test.txt", 1024)
        client.files_upload_session_finish.return_value = mock_metadata
        
        driver = DropboxStorageDriver(dropbox_config)
        upload_id = "dropbox_session123_hash456"
        parts = [
            {"PartNumber": 1, "Size": 512},
            {"PartNumber": 2, "Size": 512}
        ]
        
        result = await driver.complete_multipart_upload("test.txt", upload_id, parts)
        
        assert result.key == "test.txt"
        assert result.size == 1024
        client.files_upload_session_finish.assert_called_once()
    
    async def test_abort_multipart_upload(self, dropbox_config, mock_dropbox_client):
        """Test aborting multipart upload"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        
        # Should not raise exception (no-op for Dropbox)
        await driver.abort_multipart_upload("test.txt", "dropbox_session123_hash456")
    
    async def test_get_storage_usage(self, dropbox_config, mock_dropbox_client):
        """Test getting storage usage"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock space usage response
        space_usage = MagicMock()
        space_usage.used = 5 * 1024 * 1024 * 1024  # 5GB
        
        allocation = MagicMock()
        individual = MagicMock()
        individual.allocated = 10 * 1024 * 1024 * 1024  # 10GB
        allocation.get_individual.return_value = individual
        space_usage.allocation = allocation
        
        client.users_get_space_usage.return_value = space_usage
        
        driver = DropboxStorageDriver(dropbox_config)
        usage = await driver.get_storage_usage()
        
        assert usage["used_bytes"] == 5 * 1024 * 1024 * 1024
        assert usage["allocated_bytes"] == 10 * 1024 * 1024 * 1024
        assert usage["usage_percentage"] == 50.0
    
    async def test_health_check_healthy(self, dropbox_config, mock_dropbox_client):
        """Test health check when service is healthy"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock successful API call
        client.users_get_current_account.return_value = MagicMock()
        
        driver = DropboxStorageDriver(dropbox_config)
        health = await driver.health_check()
        
        assert health["status"] == "healthy"
        assert "timestamp" in health
    
    async def test_health_check_auth_error(self, dropbox_config, mock_dropbox_client):
        """Test health check with authentication error"""
        client, mock_dropbox = mock_dropbox_client
        
        # Create a proper exception class that inherits from Exception
        class AuthError(Exception):
            pass
        
        # Mock auth error
        client.users_get_current_account.side_effect = AuthError("Invalid token")
        
        # Patch the AuthError in the driver module
        with patch('src.drivers.dropbox_driver.AuthError', AuthError):
            driver = DropboxStorageDriver(dropbox_config)
            health = await driver.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Authentication failed" in health["message"]
    
    async def test_change_storage_tier_not_supported(self, dropbox_config, mock_dropbox_client):
        """Test changing storage tier (not supported)"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        with pytest.raises(InvalidStorageOperationError):
            await driver.change_storage_tier("test.txt", "cold")
    
    async def test_restore_object_not_supported(self, dropbox_config, mock_dropbox_client):
        """Test restoring object (not supported)"""
        client, mock_dropbox = mock_dropbox_client
        
        driver = DropboxStorageDriver(dropbox_config)
        with pytest.raises(InvalidStorageOperationError):
            await driver.restore_object("test.txt")
    
    async def test_get_object_stream(self, dropbox_config, mock_dropbox_client):
        """Test streaming object content"""
        client, mock_dropbox = mock_dropbox_client
        
        # Mock object info
        mock_metadata = MockDropboxMetadata("/mams_test/test.txt", 1024)
        client.files_get_metadata.return_value = mock_metadata
        
        # Mock download
        mock_response = MagicMock()
        mock_response.content = b"x" * 1024
        client.files_download.return_value = (None, mock_response)
        
        driver = DropboxStorageDriver(dropbox_config)
        
        chunks = []
        async for chunk in driver.get_object_stream("test.txt", chunk_size=256):
            chunks.append(chunk)
        
        assert len(chunks) == 4  # 1024 bytes / 256 bytes per chunk
        assert sum(len(chunk) for chunk in chunks) == 1024