"""
Tests for OneDrive Storage Driver

This module contains comprehensive tests for the OneDrive storage driver.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import hashlib
import json
from typing import Dict, Any
import httpx

from src.drivers.onedrive import OneDriveStorageDriver
from src.core.interfaces import (
    ObjectNotFoundError, StorageQuotaExceededError, 
    StoragePermissionError, InvalidStorageOperationError,
    StorageOperationError, StorageObject, PresignedUrl
)


class MockResponse:
    """Mock httpx response"""
    def __init__(self, status_code: int, json_data: Dict[str, Any] = None, 
                 text: str = "", headers: Dict[str, str] = None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}
        self.content = text.encode() if text else b""
    
    def json(self):
        return self._json_data


def create_mock_item(name: str, is_folder: bool = False, size: int = 1024) -> Dict[str, Any]:
    """Create a mock OneDrive item"""
    item = {
        "id": f"id_{hashlib.md5(name.encode()).hexdigest()[:8]}",
        "name": name,
        "size": size if not is_folder else 0,
        "createdDateTime": "2024-01-15T10:30:00Z",
        "lastModifiedDateTime": "2024-01-15T12:00:00Z",
        "eTag": f"etag_{hashlib.md5(name.encode()).hexdigest()[:8]}",
        "webUrl": f"https://onedrive.live.com/item/{name}",
        "parentReference": {
            "path": "/drive/root:/MAMS"
        }
    }
    
    if is_folder:
        item["folder"] = {"childCount": 5}
    else:
        item["file"] = {
            "mimeType": "application/octet-stream",
            "hashes": {
                "sha1Hash": hashlib.sha1(name.encode()).hexdigest(),
                "quickXorHash": "mockQuickXorHash"
            }
        }
    
    return item


@pytest.fixture
def onedrive_config():
    """OneDrive configuration for testing"""
    return {
        "access_token": "test_access_token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "refresh_token": "test_refresh_token",
        "tenant_id": "test_tenant_id",
        "drive_type": "me",
        "path_prefix": "/MAMS",
        "chunk_size": 5 * 1024 * 1024  # 5MB
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient"""
    client = AsyncMock()
    return client


@pytest.mark.asyncio
class TestOneDriveStorageDriver:
    """Test cases for OneDrive storage driver"""
    
    async def test_initialization(self, onedrive_config):
        """Test driver initialization"""
        driver = OneDriveStorageDriver(onedrive_config)
        
        assert driver.access_token == onedrive_config["access_token"]
        assert driver.client_id == onedrive_config["client_id"]
        assert driver.path_prefix == "/MAMS"
        assert driver.chunk_size == 5 * 1024 * 1024
    
    async def test_initialization_missing_credentials(self, onedrive_config):
        """Test initialization with missing credentials"""
        onedrive_config.pop("access_token")
        onedrive_config.pop("client_id")
        
        with pytest.raises(ValueError, match="Either access_token or client_id/client_secret required"):
            OneDriveStorageDriver(onedrive_config)
    
    async def test_get_object_info_success(self, onedrive_config, mock_httpx_client):
        """Test successful object info retrieval"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        mock_item = create_mock_item("test.txt", is_folder=False, size=2048)
        mock_httpx_client.get.return_value = MockResponse(200, mock_item)
        
        obj_info = await driver.get_object_info("test.txt")
        
        assert obj_info.key == "test.txt"
        assert obj_info.size == 2048
        assert obj_info.etag == mock_item["eTag"]
        assert obj_info.metadata["id"] == mock_item["id"]
        
        # Verify API call
        expected_url = "https://graph.microsoft.com/v1.0/me/drive/root:/MAMS/test.txt"
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        assert expected_url in str(call_args)
    
    async def test_get_object_info_not_found(self, onedrive_config, mock_httpx_client):
        """Test object info retrieval for non-existent object"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock 404 response
        mock_httpx_client.get.return_value = MockResponse(404)
        
        with pytest.raises(ObjectNotFoundError):
            await driver.get_object_info("nonexistent.txt")
    
    async def test_get_object_success(self, onedrive_config, mock_httpx_client):
        """Test successful object download"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        content = b"test file content"
        mock_httpx_client.get.return_value = MockResponse(200, text=content.decode())
        
        result = await driver.get_object("test.txt")
        
        assert result == content
        
        # Verify API call includes /content
        call_args = mock_httpx_client.get.call_args
        assert "/content" in str(call_args)
    
    async def test_put_object_small_file(self, onedrive_config, mock_httpx_client):
        """Test uploading a small file"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        mock_item = create_mock_item("test.txt", size=100)
        mock_httpx_client.put.return_value = MockResponse(201, mock_item)
        
        data = b"small file content"
        result = await driver.put_object("test.txt", data)
        
        assert result.key == "test.txt"
        assert result.size == 100
        
        # Verify simple upload was used (PUT)
        mock_httpx_client.put.assert_called_once()
    
    async def test_put_object_large_file(self, onedrive_config, mock_httpx_client):
        """Test uploading a large file using upload session"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        driver.chunk_size = 1024  # Small chunk size for testing
        
        # Mock upload session creation
        session_response = {
            "uploadUrl": "https://sn3302.up.1drv.com/upload/session/123",
            "expirationDateTime": "2024-01-16T00:00:00Z"
        }
        mock_httpx_client.post.return_value = MockResponse(200, session_response)
        
        # Mock chunk upload responses
        mock_item = create_mock_item("large.txt", size=5 * 1024)
        mock_httpx_client.put.return_value = MockResponse(201, mock_item)
        
        data = b"x" * 5 * 1024  # 5KB
        result = await driver.put_object("large.txt", data)
        
        assert result.key == "large.txt"
        
        # Verify upload session was created
        mock_httpx_client.post.assert_called_once()
        # Verify chunks were uploaded
        assert mock_httpx_client.put.call_count > 1
    
    async def test_put_object_quota_exceeded(self, onedrive_config, mock_httpx_client):
        """Test upload with quota exceeded error"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock 507 response (Insufficient Storage)
        mock_httpx_client.put.return_value = MockResponse(507)
        
        with pytest.raises(StorageQuotaExceededError):
            await driver.put_object("test.txt", b"content")
    
    async def test_delete_object_success(self, onedrive_config, mock_httpx_client):
        """Test successful object deletion"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock successful deletion
        mock_httpx_client.delete.return_value = MockResponse(204)
        
        result = await driver.delete_object("test.txt")
        
        assert result is True
        mock_httpx_client.delete.assert_called_once()
    
    async def test_delete_object_not_found(self, onedrive_config, mock_httpx_client):
        """Test deleting non-existent object"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock 404 response
        mock_httpx_client.delete.return_value = MockResponse(404)
        
        result = await driver.delete_object("nonexistent.txt")
        
        assert result is False
    
    async def test_list_objects_success(self, onedrive_config, mock_httpx_client):
        """Test listing objects"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        list_response = {
            "value": [
                create_mock_item("file1.txt", size=100),
                create_mock_item("file2.txt", size=200),
                create_mock_item("folder1", is_folder=True)
            ],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/drive/root/children?$skiptoken=abc123"
        }
        mock_httpx_client.get.return_value = MockResponse(200, list_response)
        
        objects, next_token = await driver.list_objects()
        
        assert len(objects) == 3
        assert objects[0].key == "file1.txt"
        assert objects[1].key == "file2.txt"
        assert objects[2].metadata["is_folder"] is True
        assert next_token == "abc123"
    
    async def test_list_objects_with_prefix(self, onedrive_config, mock_httpx_client):
        """Test listing objects with prefix"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        list_response = {"value": [], "@odata.nextLink": None}
        mock_httpx_client.get.return_value = MockResponse(200, list_response)
        
        await driver.list_objects(prefix="documents")
        
        # Verify prefix is included in path
        call_args = mock_httpx_client.get.call_args
        assert "/documents" in str(call_args)
    
    async def test_copy_object_success(self, onedrive_config, mock_httpx_client):
        """Test copying an object"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock copy response (async operation)
        mock_httpx_client.post.return_value = MockResponse(
            202, 
            headers={"Location": "https://api.onedrive.com/monitor/123"}
        )
        
        # Mock monitor response
        monitor_response = {"status": "completed"}
        mock_httpx_client.get.side_effect = [
            MockResponse(200, monitor_response),
            MockResponse(200, create_mock_item("dest.txt"))
        ]
        
        result = await driver.copy_object("source.txt", "dest.txt")
        
        assert result.key == "dest.txt"
        
        # Verify copy endpoint was called
        post_calls = mock_httpx_client.post.call_args_list
        assert any("/copy" in str(call) for call in post_calls)
    
    async def test_move_object_success(self, onedrive_config, mock_httpx_client):
        """Test moving an object"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock response
        mock_item = create_mock_item("dest.txt")
        mock_httpx_client.patch.return_value = MockResponse(200, mock_item)
        
        result = await driver.move_object("source.txt", "dest.txt")
        
        assert result.key == "dest.txt"
        mock_httpx_client.patch.assert_called_once()
    
    async def test_exists_true(self, onedrive_config, mock_httpx_client):
        """Test checking if object exists (exists)"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock successful response
        mock_httpx_client.get.return_value = MockResponse(200, create_mock_item("test.txt"))
        
        exists = await driver.exists("test.txt")
        
        assert exists is True
    
    async def test_exists_false(self, onedrive_config, mock_httpx_client):
        """Test checking if object exists (doesn't exist)"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock 404 response
        mock_httpx_client.get.return_value = MockResponse(404)
        
        exists = await driver.exists("nonexistent.txt")
        
        assert exists is False
    
    async def test_get_presigned_url_success(self, onedrive_config, mock_httpx_client):
        """Test generating presigned URL"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock create link response
        link_response = {
            "link": {
                "webUrl": "https://1drv.ms/u/s!Abc123def",
                "type": "view",
                "scope": "anonymous"
            }
        }
        mock_httpx_client.post.return_value = MockResponse(201, link_response)
        
        presigned_url = await driver.get_presigned_url("test.txt", expires_in=7200)
        
        assert presigned_url.url == "https://1drv.ms/u/s!Abc123def"
        assert presigned_url.expires_at > datetime.utcnow()
        
        # Verify createLink endpoint was called
        call_args = mock_httpx_client.post.call_args
        assert "/createLink" in str(call_args)
    
    async def test_get_presigned_url_fallback(self, onedrive_config, mock_httpx_client):
        """Test presigned URL generation fallback"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock failed create link
        mock_httpx_client.post.return_value = MockResponse(400)
        
        presigned_url = await driver.get_presigned_url("test.txt")
        
        assert "/content" in presigned_url.url
        assert "Authorization" in presigned_url.headers
    
    async def test_create_multipart_upload(self, onedrive_config, mock_httpx_client):
        """Test creating multipart upload session"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock session creation
        session_response = {
            "uploadUrl": "https://sn3302.up.1drv.com/upload/session/456",
            "expirationDateTime": "2024-01-16T00:00:00Z"
        }
        mock_httpx_client.post.return_value = MockResponse(200, session_response)
        
        upload_id = await driver.create_multipart_upload("test.txt")
        
        assert upload_id == "https://sn3302.up.1drv.com/upload/session/456"
        
        # Verify createUploadSession was called
        call_args = mock_httpx_client.post.call_args
        assert "/createUploadSession" in str(call_args)
    
    async def test_upload_part(self, onedrive_config, mock_httpx_client):
        """Test uploading a part in multipart upload"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock successful part upload
        mock_httpx_client.put.return_value = MockResponse(202)
        
        upload_id = "https://sn3302.up.1drv.com/upload/session/456"
        part_data = b"part content"
        
        result = await driver.upload_part("test.txt", upload_id, 2, part_data)
        
        assert result["PartNumber"] == 2
        assert result["Size"] == len(part_data)
        assert "ETag" in result
        
        # Verify Content-Range header
        call_args = mock_httpx_client.put.call_args
        headers = call_args[1].get("headers", {})
        assert "Content-Range" in headers
    
    async def test_complete_multipart_upload(self, onedrive_config, mock_httpx_client):
        """Test completing multipart upload"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock get object info response
        mock_item = create_mock_item("test.txt", size=10240)
        mock_httpx_client.get.return_value = MockResponse(200, mock_item)
        
        upload_id = "https://sn3302.up.1drv.com/upload/session/456"
        parts = [
            {"PartNumber": 1, "Size": 5120},
            {"PartNumber": 2, "Size": 5120}
        ]
        
        result = await driver.complete_multipart_upload("test.txt", upload_id, parts)
        
        assert result.key == "test.txt"
        assert result.size == 10240
    
    async def test_abort_multipart_upload(self, onedrive_config, mock_httpx_client):
        """Test aborting multipart upload"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        upload_id = "https://sn3302.up.1drv.com/upload/session/456"
        
        # Should not raise exception
        await driver.abort_multipart_upload("test.txt", upload_id)
        
        # Verify DELETE was called on upload URL
        mock_httpx_client.delete.assert_called_once_with(upload_id)
    
    async def test_get_storage_usage(self, onedrive_config, mock_httpx_client):
        """Test getting storage usage"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock drive response with quota
        drive_response = {
            "quota": {
                "total": 5 * 1024 * 1024 * 1024,  # 5GB
                "used": 2 * 1024 * 1024 * 1024,   # 2GB
                "remaining": 3 * 1024 * 1024 * 1024,  # 3GB
                "deleted": 100 * 1024 * 1024,     # 100MB
                "state": "normal"
            }
        }
        mock_httpx_client.get.return_value = MockResponse(200, drive_response)
        
        usage = await driver.get_storage_usage()
        
        assert usage["used_bytes"] == 2 * 1024 * 1024 * 1024
        assert usage["total_bytes"] == 5 * 1024 * 1024 * 1024
        assert usage["usage_percentage"] == 40.0
        assert usage["state"] == "normal"
    
    async def test_health_check_healthy(self, onedrive_config, mock_httpx_client):
        """Test health check when service is healthy"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock successful response
        mock_httpx_client.get.return_value = MockResponse(200, {"id": "drive123"})
        
        health = await driver.health_check()
        
        assert health["status"] == "healthy"
        assert "timestamp" in health
    
    async def test_health_check_unhealthy(self, onedrive_config, mock_httpx_client):
        """Test health check when service is unhealthy"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock error response
        mock_httpx_client.get.side_effect = Exception("Connection error")
        
        health = await driver.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Connection error" in health["message"]
    
    async def test_change_storage_tier_not_supported(self, onedrive_config):
        """Test changing storage tier (not supported)"""
        driver = OneDriveStorageDriver(onedrive_config)
        
        with pytest.raises(InvalidStorageOperationError):
            await driver.change_storage_tier("test.txt", "cold")
    
    async def test_restore_object_not_supported(self, onedrive_config):
        """Test restoring object (not supported)"""
        driver = OneDriveStorageDriver(onedrive_config)
        
        with pytest.raises(InvalidStorageOperationError):
            await driver.restore_object("test.txt")
    
    async def test_token_refresh(self, onedrive_config, mock_httpx_client):
        """Test automatic token refresh"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        driver._token_expires_at = datetime.utcnow() - timedelta(minutes=1)  # Expired
        
        # Mock token refresh response
        token_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token"
        }
        mock_httpx_client.post.return_value = MockResponse(200, token_response)
        
        # Mock regular API call
        mock_httpx_client.get.return_value = MockResponse(200, create_mock_item("test.txt"))
        
        # This should trigger token refresh
        await driver.get_object_info("test.txt")
        
        assert driver.access_token == "new_access_token"
        assert driver.refresh_token == "new_refresh_token"
        
        # Verify token endpoint was called
        post_calls = mock_httpx_client.post.call_args_list
        assert any("oauth2/v2.0/token" in str(call) for call in post_calls)
    
    async def test_get_object_stream(self, onedrive_config, mock_httpx_client):
        """Test streaming object content"""
        driver = OneDriveStorageDriver(onedrive_config)
        driver.client = mock_httpx_client
        
        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            class MockStream:
                def __init__(self):
                    self.status_code = 200
                
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, *args):
                    pass
                
                async def aiter_bytes(self, chunk_size):
                    data = b"x" * 1024
                    for i in range(0, len(data), chunk_size):
                        yield data[i:i + chunk_size]
            
            return MockStream()
        
        mock_httpx_client.stream = mock_stream
        
        chunks = []
        async for chunk in driver.get_object_stream("test.txt", chunk_size=256):
            chunks.append(chunk)
        
        assert len(chunks) == 4  # 1024 bytes / 256 bytes per chunk
        assert sum(len(chunk) for chunk in chunks) == 1024