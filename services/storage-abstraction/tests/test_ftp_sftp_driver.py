"""
Tests for FTP/SFTP Storage Drivers

This module contains comprehensive tests for the FTP and SFTP storage drivers.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from datetime import datetime
import hashlib
from typing import Dict, Any
from io import BytesIO
import tempfile
import os

from src.drivers.ftp_sftp import FTPStorageDriver, SFTPStorageDriver
from src.core.interfaces import (
    ObjectNotFoundError, StorageQuotaExceededError, 
    StoragePermissionError, InvalidStorageOperationError,
    StorageOperationError, StorageObject
)


# Mock FTP response
class MockFTPInfo:
    def __init__(self, type_="file", size=1024, modify="20240115120000"):
        self.data = {
            "type": type_,
            "size": str(size),
            "modify": modify
        }
    
    def get(self, key, default=None):
        return self.data.get(key, default)


# Mock SFTP file attributes
class MockSFTPAttrs:
    def __init__(self, filename, is_dir=False, size=1024, mtime=None):
        self.filename = filename
        self.st_size = size
        self.st_mtime = mtime or datetime.utcnow().timestamp()
        self.st_mode = 0o040755 if is_dir else 0o100644  # Directory or file mode
        self.st_uid = 1000
        self.st_gid = 1000
        self.st_atime = self.st_mtime


@pytest.fixture
def ftp_config():
    """FTP configuration for testing"""
    return {
        "host": "ftp.example.com",
        "port": 21,
        "username": "testuser",
        "password": "testpass",
        "path_prefix": "/mams",
        "passive": True,
        "timeout": 30
    }


@pytest.fixture
def sftp_config():
    """SFTP configuration for testing"""
    return {
        "host": "sftp.example.com",
        "port": 22,
        "username": "testuser",
        "password": "testpass",
        "path_prefix": "/mams",
        "timeout": 30,
        "auto_add_host_key": True
    }


@pytest.mark.asyncio
class TestFTPStorageDriver:
    """Test cases for FTP storage driver"""
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_initialization(self, mock_aioftp, ftp_config):
        """Test driver initialization"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        driver = FTPStorageDriver(ftp_config)
        await driver.initialize()
        
        assert driver.host == "ftp.example.com"
        assert driver.port == 21
        assert driver.username == "testuser"
        assert driver.path_prefix == "/mams/"
        
        # Verify connection was established
        mock_client.connect.assert_called_once_with("ftp.example.com", 21)
        mock_client.login.assert_called_once_with("testuser", "testpass")
    
    async def test_initialization_no_aioftp(self, ftp_config):
        """Test initialization without aioftp package"""
        with patch('src.drivers.ftp_sftp.aioftp', None):
            with pytest.raises(ImportError, match="aioftp package is required"):
                FTPStorageDriver(ftp_config)
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_get_object_info_success(self, mock_aioftp, ftp_config):
        """Test successful object info retrieval"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock MLST response
        mock_client.mlst.return_value = MockFTPInfo("file", 2048, "20240115120000")
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        obj_info = await driver.get_object_info("test.txt")
        
        assert obj_info.key == "test.txt"
        assert obj_info.size == 2048
        assert obj_info.metadata["mlst_info"]["type"] == "file"
        
        mock_client.mlst.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_get_object_info_not_found(self, mock_aioftp, ftp_config):
        """Test object info retrieval for non-existent object"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock 550 error (file not found)
        error = MagicMock()
        error.received_codes = ["550 File not found"]
        mock_client.mlst.side_effect = mock_aioftp.StatusCodeError(
            expected_codes="250",
            received_codes=error.received_codes,
            info="File not found"
        )
        mock_aioftp.StatusCodeError = type(error)
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        with pytest.raises(ObjectNotFoundError):
            await driver.get_object_info("nonexistent.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_get_object_success(self, mock_aioftp, ftp_config):
        """Test successful object download"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock download stream
        content = b"test file content"
        
        class MockDownloadStream:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
            
            async def iter_by_block(self):
                yield content
        
        mock_client.download_stream.return_value = MockDownloadStream()
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        result = await driver.get_object("test.txt")
        
        assert result == content
        mock_client.download_stream.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_put_object_success(self, mock_aioftp, ftp_config):
        """Test successful object upload"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock upload stream
        class MockUploadStream:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
            
            async def write(self, data):
                pass
        
        mock_client.upload_stream.return_value = MockUploadStream()
        mock_client.mlst.return_value = MockFTPInfo("file", 100, "20240115120000")
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        data = b"test content"
        result = await driver.put_object("test.txt", data)
        
        assert result.key == "test.txt"
        assert result.size == 100
        
        mock_client.make_directory.assert_called()
        mock_client.upload_stream.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_delete_object_success(self, mock_aioftp, ftp_config):
        """Test successful object deletion"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        result = await driver.delete_object("test.txt")
        
        assert result is True
        mock_client.remove.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_delete_object_not_found(self, mock_aioftp, ftp_config):
        """Test deleting non-existent object"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock 550 error
        error = MagicMock()
        error.received_codes = ["550 File not found"]
        mock_client.remove.side_effect = mock_aioftp.StatusCodeError(
            expected_codes="250",
            received_codes=error.received_codes,
            info="File not found"
        )
        mock_aioftp.StatusCodeError = type(error)
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        result = await driver.delete_object("nonexistent.txt")
        
        assert result is False
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_list_objects_success(self, mock_aioftp, ftp_config):
        """Test listing objects"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        # Mock list response
        from pathlib import PurePosixPath
        mock_listing = [
            (PurePosixPath("/mams/file1.txt"), {"type": "file", "size": "100"}),
            (PurePosixPath("/mams/file2.txt"), {"type": "file", "size": "200"}),
            (PurePosixPath("/mams/folder"), {"type": "dir"})
        ]
        mock_client.list.return_value = mock_listing
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        objects, next_token = await driver.list_objects()
        
        assert len(objects) == 2  # Only files, not directories
        assert objects[0].key == "file1.txt"
        assert objects[0].size == 100
        assert objects[1].key == "file2.txt"
        assert objects[1].size == 200
        assert next_token is None
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_exists_true(self, mock_aioftp, ftp_config):
        """Test checking if object exists (exists)"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        mock_client.mlst.return_value = MockFTPInfo("file", 100)
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        exists = await driver.exists("test.txt")
        
        assert exists is True
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_get_presigned_url_not_supported(self, mock_aioftp, ftp_config):
        """Test presigned URL generation (not supported)"""
        driver = FTPStorageDriver(ftp_config)
        
        with pytest.raises(InvalidStorageOperationError):
            await driver.get_presigned_url("test.txt")
    
    @patch('src.drivers.ftp_sftp.aioftp')
    async def test_health_check_healthy(self, mock_aioftp, ftp_config):
        """Test health check when service is healthy"""
        mock_client = AsyncMock()
        mock_aioftp.Client.return_value = mock_client
        
        mock_client.get_current_directory.return_value = "/mams"
        
        driver = FTPStorageDriver(ftp_config)
        driver._client = mock_client
        
        health = await driver.health_check()
        
        assert health["status"] == "healthy"
        assert "ftp.example.com:21" in health["message"]


@pytest.mark.asyncio
class TestSFTPStorageDriver:
    """Test cases for SFTP storage driver"""
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_initialization(self, mock_paramiko, sftp_config):
        """Test driver initialization"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        driver = SFTPStorageDriver(sftp_config)
        await driver.initialize()
        
        assert driver.host == "sftp.example.com"
        assert driver.port == 22
        assert driver.username == "testuser"
        assert driver.path_prefix == "/mams/"
        
        # Verify connection was established
        mock_ssh.connect.assert_called_once()
        mock_ssh.open_sftp.assert_called_once()
    
    async def test_initialization_no_paramiko(self, sftp_config):
        """Test initialization without paramiko package"""
        with patch('src.drivers.ftp_sftp.paramiko', None):
            with pytest.raises(ImportError, match="paramiko package is required"):
                SFTPStorageDriver(sftp_config)
    
    async def test_initialization_missing_auth(self, sftp_config):
        """Test initialization with missing authentication"""
        sftp_config.pop("password")
        
        with pytest.raises(ValueError, match="Either password or key_filename is required"):
            SFTPStorageDriver(sftp_config)
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_get_object_info_success(self, mock_paramiko, sftp_config):
        """Test successful object info retrieval"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock stat response
        mock_stat = MockSFTPAttrs("test.txt", is_dir=False, size=2048)
        mock_sftp.stat.return_value = mock_stat
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        obj_info = await driver.get_object_info("test.txt")
        
        assert obj_info.key == "test.txt"
        assert obj_info.size == 2048
        assert "mode" in obj_info.metadata
        
        mock_sftp.stat.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_get_object_info_not_found(self, mock_paramiko, sftp_config):
        """Test object info retrieval for non-existent object"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock FileNotFoundError
        mock_sftp.stat.side_effect = FileNotFoundError()
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        with pytest.raises(ObjectNotFoundError):
            await driver.get_object_info("nonexistent.txt")
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_get_object_success(self, mock_paramiko, sftp_config):
        """Test successful object download"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock get operation
        content = b"test file content"
        
        def mock_get(remote_path, local_path):
            with open(local_path, 'wb') as f:
                f.write(content)
        
        mock_sftp.get.side_effect = mock_get
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        result = await driver.get_object("test.txt")
        
        assert result == content
        mock_sftp.get.assert_called_once()
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_put_object_success(self, mock_paramiko, sftp_config):
        """Test successful object upload"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock stat for get_object_info
        mock_stat = MockSFTPAttrs("test.txt", is_dir=False, size=100)
        mock_sftp.stat.return_value = mock_stat
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        data = b"test content"
        result = await driver.put_object("test.txt", data)
        
        assert result.key == "test.txt"
        assert result.size == 100
        
        mock_sftp.makedirs.assert_called()
        mock_sftp.put.assert_called_once()
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_delete_object_success(self, mock_paramiko, sftp_config):
        """Test successful object deletion"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        result = await driver.delete_object("test.txt")
        
        assert result is True
        mock_sftp.remove.assert_called_once_with("/mams/test.txt")
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_delete_object_not_found(self, mock_paramiko, sftp_config):
        """Test deleting non-existent object"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock FileNotFoundError
        mock_sftp.remove.side_effect = FileNotFoundError()
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        result = await driver.delete_object("nonexistent.txt")
        
        assert result is False
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_list_objects_success(self, mock_paramiko, sftp_config):
        """Test listing objects"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock listdir_attr response
        mock_attrs = [
            MockSFTPAttrs("file1.txt", is_dir=False, size=100),
            MockSFTPAttrs("file2.txt", is_dir=False, size=200),
            MockSFTPAttrs("folder", is_dir=True)
        ]
        mock_sftp.listdir_attr.return_value = mock_attrs
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        objects, next_token = await driver.list_objects()
        
        assert len(objects) == 2  # Only files, not directories
        assert objects[0].key == "file1.txt"
        assert objects[0].size == 100
        assert objects[1].key == "file2.txt"
        assert objects[1].size == 200
        assert next_token is None
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_move_object_success(self, mock_paramiko, sftp_config):
        """Test moving an object"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock stat for get_object_info
        mock_stat = MockSFTPAttrs("dest.txt", is_dir=False, size=100)
        mock_sftp.stat.return_value = mock_stat
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        result = await driver.move_object("source.txt", "dest.txt")
        
        assert result.key == "dest.txt"
        mock_sftp.rename.assert_called_once_with("/mams/source.txt", "/mams/dest.txt")
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_exists_true(self, mock_paramiko, sftp_config):
        """Test checking if object exists (exists)"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock stat
        mock_stat = MockSFTPAttrs("test.txt", is_dir=False, size=100)
        mock_sftp.stat.return_value = mock_stat
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        exists = await driver.exists("test.txt")
        
        assert exists is True
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_get_storage_usage(self, mock_paramiko, sftp_config):
        """Test getting storage usage"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        # Mock statvfs response
        mock_vfs = MagicMock()
        mock_vfs.f_blocks = 1000000
        mock_vfs.f_frsize = 4096
        mock_vfs.f_bavail = 500000
        mock_sftp.statvfs.return_value = mock_vfs
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        usage = await driver.get_storage_usage()
        
        assert usage["total_bytes"] == 1000000 * 4096
        assert usage["available_bytes"] == 500000 * 4096
        assert usage["usage_percentage"] == 50.0
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_health_check_healthy(self, mock_paramiko, sftp_config):
        """Test health check when service is healthy"""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        mock_sftp.listdir.return_value = ["file1.txt", "file2.txt"]
        
        driver = SFTPStorageDriver(sftp_config)
        driver._ssh_client = mock_ssh
        driver._sftp_client = mock_sftp
        
        health = await driver.health_check()
        
        assert health["status"] == "healthy"
        assert "sftp.example.com:22" in health["message"]
    
    @patch('src.drivers.ftp_sftp.paramiko')
    async def test_key_based_auth(self, mock_paramiko, sftp_config):
        """Test SFTP with key-based authentication"""
        # Configure for key auth
        sftp_config.pop("password")
        sftp_config["key_filename"] = "/path/to/key"
        sftp_config["key_password"] = "keypass"
        
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp
        
        driver = SFTPStorageDriver(sftp_config)
        await driver.initialize()
        
        # Verify connect was called with key parameters
        connect_call = mock_ssh.connect.call_args
        assert connect_call[1]["key_filename"] == "/path/to/key"
        assert connect_call[1]["passphrase"] == "keypass"
        assert "password" not in connect_call[1]