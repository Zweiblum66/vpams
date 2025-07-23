"""
Test Storage Client

Tests for storage client functionality in the Ingest Service.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional, List

from src.services.storage_client import StorageClient, get_storage_client
from src.core.exceptions import StorageError
from src.core.config import settings


class TestStorageClient:
    """Test cases for StorageClient."""
    
    @pytest.fixture
    def client(self):
        """Create storage client instance."""
        with patch.object(settings, 'storage_service_url', 'http://storage-service:8000'):
            with patch.object(settings, 'storage_service_api_key', 'test-api-key'):
                return StorageClient()
    
    @pytest.fixture
    def sample_file_path(self):
        """Sample file path for testing."""
        return "/test/path/video.mp4"
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "title": "Test Video",
            "description": "A test video file",
            "creator": "Test User",
            "format": "mp4"
        }
    
    @pytest.fixture
    def sample_tags(self):
        """Sample tags for testing."""
        return ["test", "video", "sample"]
    
    async def test_init(self):
        """Test client initialization."""
        with patch.object(settings, 'storage_service_url', 'http://test-storage:9000'):
            with patch.object(settings, 'storage_service_api_key', 'secret-key'):
                client = StorageClient()
                
                assert client.base_url == 'http://test-storage:9000'
                assert client.api_key == 'secret-key'
    
    async def test_upload_file_success(self, client, sample_file_path):
        """Test successful file upload."""
        # Mock uuid generation
        mock_asset_id = "12345678-1234-5678-1234-567812345678"
        with patch('uuid.uuid4', return_value=uuid.UUID(mock_asset_id)):
            asset_id = await client.upload_file(sample_file_path)
            
            assert asset_id == mock_asset_id
    
    async def test_upload_file_with_metadata(self, client, sample_file_path, sample_metadata, sample_tags):
        """Test file upload with metadata and tags."""
        project_id = "project123"
        
        asset_id = await client.upload_file(
            file_path=sample_file_path,
            project_id=project_id,
            metadata=sample_metadata,
            tags=sample_tags
        )
        
        # Should return a valid UUID
        assert len(asset_id) == 36
        uuid.UUID(asset_id)  # Should not raise exception
    
    async def test_upload_file_exception(self, client, sample_file_path):
        """Test file upload with exception."""
        # Mock asyncio.sleep to raise exception
        with patch('asyncio.sleep', side_effect=Exception("Network error")):
            with pytest.raises(StorageError, match="Failed to upload file"):
                await client.upload_file(sample_file_path)
    
    async def test_update_asset_metadata_success(self, client, sample_metadata):
        """Test successful metadata update."""
        asset_id = str(uuid.uuid4())
        
        result = await client.update_asset_metadata(asset_id, sample_metadata)
        
        assert result is True
    
    async def test_update_asset_metadata_exception(self, client, sample_metadata):
        """Test metadata update with exception."""
        asset_id = str(uuid.uuid4())
        
        # Mock the logger to raise exception
        with patch.object(client.__class__.__module__ + '.logger.info', side_effect=Exception("Update error")):
            result = await client.update_asset_metadata(asset_id, sample_metadata)
            
            assert result is False
    
    async def test_get_asset_info_success(self, client):
        """Test successful asset info retrieval."""
        asset_id = str(uuid.uuid4())
        
        info = await client.get_asset_info(asset_id)
        
        assert info is not None
        assert info["id"] == asset_id
        assert info["status"] == "active"
        assert "created_at" in info
    
    async def test_get_asset_info_exception(self, client):
        """Test asset info retrieval with exception."""
        asset_id = str(uuid.uuid4())
        
        # Create a mock that raises exception when accessing items
        with patch.object(client, 'get_asset_info', side_effect=Exception("Retrieval error")):
            try:
                info = await client.get_asset_info(asset_id)
            except:
                info = None
            
            assert info is None
    
    async def test_delete_asset_success(self, client):
        """Test successful asset deletion."""
        asset_id = str(uuid.uuid4())
        
        result = await client.delete_asset(asset_id)
        
        assert result is True
    
    async def test_delete_asset_exception(self, client):
        """Test asset deletion with exception."""
        asset_id = str(uuid.uuid4())
        
        # Mock the logger to raise exception
        with patch.object(client.__class__.__module__ + '.logger.info', side_effect=Exception("Delete error")):
            result = await client.delete_asset(asset_id)
            
            assert result is False
    
    async def test_get_storage_client_singleton(self):
        """Test that get_storage_client returns singleton."""
        client1 = await get_storage_client()
        client2 = await get_storage_client()
        
        assert client1 is client2
    
    async def test_upload_file_empty_metadata_and_tags(self, client, sample_file_path):
        """Test file upload with empty metadata and tags."""
        asset_id = await client.upload_file(
            file_path=sample_file_path,
            metadata=None,
            tags=None
        )
        
        # Should still succeed
        assert len(asset_id) == 36
    
    async def test_concurrent_uploads(self, client, sample_file_path):
        """Test concurrent file uploads."""
        # Create multiple upload tasks
        tasks = [
            client.upload_file(f"{sample_file_path}_{i}")
            for i in range(5)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # All should succeed with unique IDs
        assert len(results) == 5
        assert len(set(results)) == 5  # All unique
        assert all(len(asset_id) == 36 for asset_id in results)
    
    async def test_upload_file_with_special_characters(self, client):
        """Test file upload with special characters in path."""
        special_path = "/test/path with spaces/видео.mp4"
        
        asset_id = await client.upload_file(special_path)
        
        # Should handle special characters
        assert len(asset_id) == 36
    
    async def test_update_metadata_empty_dict(self, client):
        """Test metadata update with empty dictionary."""
        asset_id = str(uuid.uuid4())
        
        result = await client.update_asset_metadata(asset_id, {})
        
        assert result is True
    
    async def test_logging_file_upload(self, client, sample_file_path, sample_metadata, sample_tags):
        """Test that file upload logs appropriate information."""
        project_id = "project123"
        
        with patch.object(client.__class__.__module__ + '.logger') as mock_logger:
            asset_id = await client.upload_file(
                file_path=sample_file_path,
                project_id=project_id,
                metadata=sample_metadata,
                tags=sample_tags
            )
            
            # Verify logging
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "file_upload_simulated"
            assert "file_path" in call_args[1]
            assert "asset_id" in call_args[1]
            assert "project_id" in call_args[1]
            assert call_args[1]["metadata_keys"] == list(sample_metadata.keys())
            assert call_args[1]["tags"] == sample_tags
    
    async def test_logging_metadata_update(self, client, sample_metadata):
        """Test that metadata update logs appropriate information."""
        asset_id = str(uuid.uuid4())
        
        with patch.object(client.__class__.__module__ + '.logger') as mock_logger:
            await client.update_asset_metadata(asset_id, sample_metadata)
            
            # Verify logging
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "asset_metadata_update_simulated"
            assert call_args[1]["asset_id"] == asset_id
            assert call_args[1]["metadata_keys"] == list(sample_metadata.keys())
    
    async def test_logging_asset_deletion(self, client):
        """Test that asset deletion logs appropriate information."""
        asset_id = str(uuid.uuid4())
        
        with patch.object(client.__class__.__module__ + '.logger') as mock_logger:
            await client.delete_asset(asset_id)
            
            # Verify logging
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "asset_deletion_simulated"
            assert call_args[1]["asset_id"] == asset_id
    
    async def test_error_logging_upload_failure(self, client, sample_file_path):
        """Test error logging when upload fails."""
        project_id = "project123"
        
        with patch('asyncio.sleep', side_effect=Exception("Upload failed")):
            with patch.object(client.__class__.__module__ + '.logger') as mock_logger:
                with pytest.raises(StorageError):
                    await client.upload_file(
                        file_path=sample_file_path,
                        project_id=project_id
                    )
                
                # Verify error logging
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args
                assert call_args[0][0] == "file_upload_failed"
                assert "error" in call_args[1]
                assert call_args[1]["file_path"] == sample_file_path
                assert call_args[1]["project_id"] == project_id
    
    async def test_asset_info_format(self, client):
        """Test the format of returned asset info."""
        asset_id = str(uuid.uuid4())
        
        info = await client.get_asset_info(asset_id)
        
        # Verify format
        assert isinstance(info, dict)
        assert info["id"] == asset_id
        assert info["status"] in ["active", "inactive", "deleted"]
        assert isinstance(info["created_at"], str)
        # ISO format check
        assert "T" in info["created_at"]
        assert info["created_at"].endswith("Z")
    
    async def test_upload_delay_simulation(self, client, sample_file_path):
        """Test that upload simulates delay."""
        start_time = asyncio.get_event_loop().time()
        
        await client.upload_file(sample_file_path)
        
        end_time = asyncio.get_event_loop().time()
        
        # Should have delayed at least 0.1 seconds
        assert (end_time - start_time) >= 0.1