"""
Tests for Azure Blob Storage Driver
"""

import pytest
import asyncio
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.drivers.azure_blob import AzureBlobStorageDriver
from src.core.interfaces import (
    StorageObject, StorageTier, ObjectNotFoundError,
    InvalidStorageOperationError, StorageOperationError
)


class MockBlobProperties:
    """Mock Azure blob properties"""
    def __init__(self, **kwargs):
        self.size = kwargs.get('size', 1024)
        self.last_modified = kwargs.get('last_modified', datetime.utcnow())
        self.etag = kwargs.get('etag', '"abc123"')
        self.blob_tier = kwargs.get('blob_tier', 'Hot')
        self.metadata = kwargs.get('metadata', {})
        self.version_id = kwargs.get('version_id', None)
        self.content_settings = Mock(content_type="application/octet-stream")
        self.copy = Mock(status="success")


class MockBlobClient:
    """Mock Azure blob client"""
    def __init__(self, exists=True):
        self.exists = exists
        self.url = "https://test.blob.core.windows.net/container/key"
        
    async def get_blob_properties(self):
        if not self.exists:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
        return MockBlobProperties()
    
    async def download_blob(self):
        if not self.exists:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
        
        class MockDownloadStream:
            async def readall(self):
                return b"test content"
            
            async def chunks(self):
                yield b"test "
                yield b"content"
        
        return MockDownloadStream()
    
    async def upload_blob(self, data, **kwargs):
        return {"etag": "abc123"}
    
    async def delete_blob(self):
        if not self.exists:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
    
    async def start_copy_from_url(self, source_url, **kwargs):
        return {"copy_id": "123"}
    
    async def set_standard_blob_tier(self, tier, **kwargs):
        pass
    
    async def stage_block(self, block_id, data):
        pass
    
    async def commit_block_list(self, block_list, **kwargs):
        pass


class MockContainerClient:
    """Mock Azure container client"""
    def __init__(self):
        self.blobs = {}
    
    def get_blob_client(self, key):
        return MockBlobClient(exists=key in ["existing_key", "test/file.txt"])
    
    async def create_container(self):
        pass
    
    async def get_container_properties(self):
        return {"name": "test-container"}
    
    async def list_blobs(self, **kwargs):
        mock_blob = Mock()
        mock_blob.name = "test/file.txt"
        mock_blob.size = 1024
        mock_blob.last_modified = datetime.utcnow()
        mock_blob.etag = '"abc123"'
        mock_blob.metadata = {}
        mock_blob.blob_tier = Mock(value="Hot")
        mock_blob.content_settings = Mock(content_type="text/plain")
        
        for blob in [mock_blob]:
            yield blob


class MockBlobServiceClient:
    """Mock Azure blob service client"""
    def __init__(self):
        self.container_client = MockContainerClient()
    
    def get_container_client(self, container_name):
        return self.container_client
    
    async def get_account_information(self):
        return {"sku_name": "Standard_LRS"}
    
    async def close(self):
        pass


@pytest.fixture
def azure_config():
    """Azure storage configuration"""
    return {
        "account_name": "testaccount",
        "account_key": "dGVzdGtleQ==",
        "container_name": "test-container",
        "enable_versioning": True,
        "enable_soft_delete": True
    }


@pytest.fixture
async def azure_driver(azure_config):
    """Create Azure driver with mocked client"""
    with patch('src.drivers.azure_blob.BlobServiceClient') as mock_client_class:
        mock_client_class.from_connection_string.return_value = MockBlobServiceClient()
        
        driver = AzureBlobStorageDriver(azure_config)
        driver._blob_service_client = MockBlobServiceClient()
        driver._container_client = MockContainerClient()
        driver._initialized = True
        
        yield driver
        
        await driver.close()


class TestAzureBlobStorageDriver:
    """Test cases for Azure Blob Storage driver"""
    
    async def test_initialization_with_connection_string(self):
        """Test driver initialization with connection string"""
        config = {
            "connection_string": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net"
        }
        
        with patch('src.drivers.azure_blob.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = MockBlobServiceClient()
            
            driver = AzureBlobStorageDriver(config)
            await driver.initialize()
            
            assert driver._initialized
            mock_client_class.from_connection_string.assert_called_once()
    
    async def test_initialization_with_account_key(self):
        """Test driver initialization with account name and key"""
        config = {
            "account_name": "testaccount",
            "account_key": "testkey",
            "container_name": "test-container"
        }
        
        with patch('src.drivers.azure_blob.BlobServiceClient') as mock_client_class:
            mock_client_class.return_value = MockBlobServiceClient()
            
            driver = AzureBlobStorageDriver(config)
            await driver.initialize()
            
            assert driver._initialized
    
    async def test_initialization_failure(self):
        """Test initialization failure with missing credentials"""
        config = {"container_name": "test-container"}
        
        driver = AzureBlobStorageDriver(config)
        
        with pytest.raises(InvalidStorageOperationError):
            await driver.initialize()
    
    async def test_exists(self, azure_driver):
        """Test checking if object exists"""
        assert await azure_driver.exists("existing_key") is True
        assert await azure_driver.exists("non_existing_key") is False
    
    async def test_get_object(self, azure_driver):
        """Test retrieving an object"""
        content = await azure_driver.get_object("existing_key")
        assert content == b"test content"
        
        with pytest.raises(ObjectNotFoundError):
            await azure_driver.get_object("non_existing_key")
    
    async def test_get_object_stream(self, azure_driver):
        """Test streaming an object"""
        chunks = []
        async for chunk in azure_driver.get_object_stream("existing_key"):
            chunks.append(chunk)
        
        assert chunks == [b"test ", b"content"]
        
        with pytest.raises(ObjectNotFoundError):
            async for chunk in azure_driver.get_object_stream("non_existing_key"):
                pass
    
    async def test_put_object(self, azure_driver):
        """Test storing an object"""
        result = await azure_driver.put_object(
            "new_key",
            b"test data",
            metadata={"user": "test"},
            content_type="text/plain"
        )
        
        assert isinstance(result, StorageObject)
        assert result.key == "new_key"
        assert result.size == 1024
    
    async def test_delete_object(self, azure_driver):
        """Test deleting an object"""
        assert await azure_driver.delete_object("existing_key") is True
        assert await azure_driver.delete_object("non_existing_key") is False
    
    async def test_delete_objects(self, azure_driver):
        """Test deleting multiple objects"""
        results = await azure_driver.delete_objects([
            "existing_key",
            "non_existing_key"
        ])
        
        assert results["existing_key"] is True
        assert results["non_existing_key"] is False
    
    async def test_list_objects(self, azure_driver):
        """Test listing objects"""
        objects, token = await azure_driver.list_objects(prefix="test/")
        
        assert len(objects) == 1
        assert objects[0].key == "test/file.txt"
        assert objects[0].size == 1024
        assert token is None
    
    async def test_get_object_info(self, azure_driver):
        """Test getting object metadata"""
        info = await azure_driver.get_object_info("existing_key")
        
        assert isinstance(info, StorageObject)
        assert info.key == "existing_key"
        assert info.size == 1024
        
        with pytest.raises(ObjectNotFoundError):
            await azure_driver.get_object_info("non_existing_key")
    
    async def test_copy_object(self, azure_driver):
        """Test copying an object"""
        result = await azure_driver.copy_object(
            "existing_key",
            "copied_key",
            metadata={"copied": "true"}
        )
        
        assert isinstance(result, StorageObject)
        assert result.key == "copied_key"
    
    async def test_move_object(self, azure_driver):
        """Test moving an object"""
        result = await azure_driver.move_object(
            "existing_key",
            "moved_key"
        )
        
        assert isinstance(result, StorageObject)
        assert result.key == "moved_key"
    
    async def test_get_presigned_url(self, azure_driver):
        """Test generating presigned URL"""
        with patch('src.drivers.azure_blob.generate_blob_sas') as mock_sas:
            mock_sas.return_value = "sas_token"
            
            url = await azure_driver.get_presigned_url(
                "test_key",
                operation="get",
                expires_in=3600
            )
            
            assert "test_key" in url
            assert "sas_token" in url
    
    async def test_multipart_upload(self, azure_driver):
        """Test multipart upload workflow"""
        # Start multipart upload
        upload_id = await azure_driver.create_multipart_upload(
            "multipart_key",
            metadata={"type": "multipart"}
        )
        
        assert upload_id
        
        # Upload parts
        part1 = await azure_driver.upload_part(
            "multipart_key",
            upload_id,
            1,
            b"part1_data"
        )
        
        assert part1["PartNumber"] == 1
        assert "ETag" in part1
        
        # Complete upload
        result = await azure_driver.complete_multipart_upload(
            "multipart_key",
            upload_id,
            [part1]
        )
        
        assert isinstance(result, StorageObject)
        assert result.key == "multipart_key"
    
    async def test_abort_multipart_upload(self, azure_driver):
        """Test aborting multipart upload"""
        upload_id = await azure_driver.create_multipart_upload("abort_key")
        
        await azure_driver.abort_multipart_upload("abort_key", upload_id)
        
        # Upload should be removed from tracking
        assert upload_id not in azure_driver._multipart_uploads
    
    async def test_get_quota(self, azure_driver):
        """Test getting storage quota"""
        quota = await azure_driver.get_quota()
        
        assert quota.total_bytes == 0  # Unlimited
        assert quota.used_bytes >= 0
        assert quota.file_count >= 0
    
    async def test_change_storage_tier(self, azure_driver):
        """Test changing storage tier"""
        result = await azure_driver.change_storage_tier(
            "existing_key",
            StorageTier.COLD
        )
        
        assert isinstance(result, StorageObject)
        assert result.key == "existing_key"
    
    async def test_restore_from_archive(self, azure_driver):
        """Test restoring from archive"""
        # Mock archived blob
        with patch.object(azure_driver._container_client, 'get_blob_client') as mock_get:
            mock_blob = MockBlobClient()
            mock_props = MockBlobProperties()
            mock_props.blob_tier = "Archive"
            mock_blob.get_blob_properties = AsyncMock(return_value=mock_props)
            mock_blob.set_standard_blob_tier = AsyncMock()
            mock_get.return_value = mock_blob
            
            result = await azure_driver.restore_from_archive(
                "archived_key",
                days=1,
                tier="Expedited"
            )
            
            assert result["status"] == "restoring"
            assert "High priority" in result["message"]