"""
Tests for Encryption functionality
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import hashlib
import secrets
import base64

from src.services.encryption_service import (
    EncryptionService, EncryptionKey, EncryptionMetadata,
    EncryptionAlgorithm, KeyDerivationMethod
)
from src.core.interfaces import (
    InvalidStorageOperationError, StorageOperationError
)


class MockStorageService:
    """Mock storage service for testing"""
    def __init__(self):
        self._drivers = {"local": Mock()}
        self._default_driver = "local"
    
    def get_driver(self, driver_name=None):
        return self._drivers.get(driver_name or self._default_driver)


class MockSettings:
    """Mock settings for testing"""
    def __init__(self):
        self.enable_encryption = True
        self.temp_directory = tempfile.mkdtemp()


@pytest.fixture
async def encryption_service():
    """Create an encryption service for testing"""
    storage_service = MockStorageService()
    
    # Create temporary directory for test data
    temp_dir = tempfile.mkdtemp()
    
    service = EncryptionService(storage_service)
    service.settings = MockSettings()
    service._data_dir = Path(temp_dir) / "encryption"
    service._data_dir.mkdir(parents=True, exist_ok=True)
    
    # Don't start background workers in tests
    service._key_rotation_task = None
    
    yield service
    
    await service.shutdown()
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestEncryptionKeyManagement:
    """Test cases for encryption key management"""
    
    def test_generate_aes_256_gcm_key(self, encryption_service):
        """Test generating AES-256-GCM key"""
        key = encryption_service._generate_key(
            "test_aes_gcm",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        assert key.key_id == "test_aes_gcm"
        assert key.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert len(key.key_data) == 32  # 256 bits
        assert key.iv is None  # GCM generates IV per encryption
    
    def test_generate_aes_256_cbc_key(self, encryption_service):
        """Test generating AES-256-CBC key"""
        key = encryption_service._generate_key(
            "test_aes_cbc",
            EncryptionAlgorithm.AES_256_CBC
        )
        
        assert key.key_id == "test_aes_cbc"
        assert key.algorithm == EncryptionAlgorithm.AES_256_CBC
        assert len(key.key_data) == 32  # 256 bits
        assert len(key.iv) == 16  # 128 bits
    
    def test_generate_fernet_key(self, encryption_service):
        """Test generating Fernet key"""
        key = encryption_service._generate_key(
            "test_fernet",
            EncryptionAlgorithm.FERNET
        )
        
        assert key.key_id == "test_fernet"
        assert key.algorithm == EncryptionAlgorithm.FERNET
        assert len(key.key_data) == 44  # Fernet key length
    
    def test_generate_chacha20_key(self, encryption_service):
        """Test generating ChaCha20-Poly1305 key"""
        key = encryption_service._generate_key(
            "test_chacha20",
            EncryptionAlgorithm.CHACHA20_POLY1305
        )
        
        assert key.key_id == "test_chacha20"
        assert key.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305
        assert len(key.key_data) == 32  # 256 bits
    
    def test_create_key(self, encryption_service):
        """Test creating and storing a key"""
        key = encryption_service.create_key(
            "test_key",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        assert "test_key" in encryption_service._keys
        assert encryption_service._keys["test_key"] == key
    
    def test_create_duplicate_key_fails(self, encryption_service):
        """Test creating duplicate key raises error"""
        encryption_service.create_key(
            "test_key",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        with pytest.raises(InvalidStorageOperationError):
            encryption_service.create_key(
                "test_key",
                EncryptionAlgorithm.FERNET
            )
    
    def test_rotate_key(self, encryption_service):
        """Test key rotation"""
        original_key = encryption_service.create_key(
            "test_key",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        new_key = encryption_service.rotate_key("test_key")
        
        assert original_key.rotation_required is True
        assert new_key.key_id != "test_key"
        assert new_key.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert new_key.key_id in encryption_service._keys
    
    def test_delete_key(self, encryption_service):
        """Test deleting a key"""
        encryption_service.create_key(
            "test_key",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        assert "test_key" in encryption_service._keys
        
        encryption_service.delete_key("test_key")
        
        assert "test_key" not in encryption_service._keys
    
    def test_get_keys(self, encryption_service):
        """Test getting all keys"""
        key1 = encryption_service.create_key(
            "key1",
            EncryptionAlgorithm.AES_256_GCM
        )
        key2 = encryption_service.create_key(
            "key2",
            EncryptionAlgorithm.FERNET
        )
        
        keys = encryption_service.get_keys()
        
        # Should include default keys plus our test keys
        assert len(keys) >= 2
        assert key1 in keys
        assert key2 in keys


class TestFileEncryption:
    """Test cases for file encryption and decryption"""
    
    async def test_encrypt_decrypt_aes_gcm(self, encryption_service):
        """Test AES-GCM encryption and decryption"""
        test_data = b"This is test data for encryption!"
        
        # Create test key
        key = encryption_service.create_key(
            "test_aes_gcm",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        assert encrypted_data != test_data
        assert metadata.key_id == key.key_id
        assert metadata.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert metadata.original_size == len(test_data)
        assert metadata.file_hash == hashlib.sha256(test_data).hexdigest()
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_encrypt_decrypt_aes_cbc(self, encryption_service):
        """Test AES-CBC encryption and decryption"""
        test_data = b"This is test data for encryption!"
        
        # Create test key
        key = encryption_service.create_key(
            "test_aes_cbc",
            EncryptionAlgorithm.AES_256_CBC
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        assert encrypted_data != test_data
        assert metadata.key_id == key.key_id
        assert metadata.algorithm == EncryptionAlgorithm.AES_256_CBC
        assert metadata.iv is not None
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_encrypt_decrypt_fernet(self, encryption_service):
        """Test Fernet encryption and decryption"""
        test_data = b"This is test data for encryption!"
        
        # Create test key
        key = encryption_service.create_key(
            "test_fernet",
            EncryptionAlgorithm.FERNET
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        assert encrypted_data != test_data
        assert metadata.key_id == key.key_id
        assert metadata.algorithm == EncryptionAlgorithm.FERNET
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_encrypt_decrypt_chacha20(self, encryption_service):
        """Test ChaCha20-Poly1305 encryption and decryption"""
        test_data = b"This is test data for encryption!"
        
        # Create test key
        key = encryption_service.create_key(
            "test_chacha20",
            EncryptionAlgorithm.CHACHA20_POLY1305
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        assert encrypted_data != test_data
        assert metadata.key_id == key.key_id
        assert metadata.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305
        assert metadata.checksum is not None
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_encrypt_with_default_algorithm(self, encryption_service):
        """Test encryption with default algorithm"""
        test_data = b"This is test data for encryption!"
        
        # Encrypt without specifying key or algorithm
        encrypted_data, metadata = await encryption_service.encrypt_file(test_data)
        
        assert encrypted_data != test_data
        assert metadata.algorithm == encryption_service._default_algorithm
    
    async def test_encrypt_large_file(self, encryption_service):
        """Test encryption of large file"""
        # Create 1MB test data
        test_data = secrets.token_bytes(1024 * 1024)
        
        key = encryption_service.create_key(
            "test_large",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        assert len(encrypted_data) > len(test_data)  # Encrypted data should be larger
        assert metadata.original_size == len(test_data)
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_decrypt_with_wrong_key_fails(self, encryption_service):
        """Test decryption with wrong key fails"""
        test_data = b"This is test data for encryption!"
        
        # Create two different keys
        key1 = encryption_service.create_key(
            "key1",
            EncryptionAlgorithm.AES_256_GCM
        )
        key2 = encryption_service.create_key(
            "key2",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt with key1
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key1.key_id
        )
        
        # Try to decrypt with key2's metadata
        metadata.key_id = key2.key_id
        
        with pytest.raises(Exception):  # Should fail with cryptographic error
            await encryption_service.decrypt_file(encrypted_data, metadata)
    
    async def test_file_integrity_check(self, encryption_service):
        """Test file integrity verification"""
        test_data = b"This is test data for encryption!"
        
        key = encryption_service.create_key(
            "test_integrity",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        # Tamper with encrypted data
        tampered_data = encrypted_data[:-1] + b"X"
        
        # Decryption should fail due to integrity check
        with pytest.raises(Exception):
            await encryption_service.decrypt_file(tampered_data, metadata)


class TestStreamEncryption:
    """Test cases for stream encryption"""
    
    async def test_encrypt_stream_fernet(self, encryption_service):
        """Test stream encryption with Fernet"""
        import io
        
        test_data = b"This is test data for stream encryption!"
        input_stream = io.BytesIO(test_data)
        output_stream = io.BytesIO()
        
        key = encryption_service.create_key(
            "test_stream_fernet",
            EncryptionAlgorithm.FERNET
        )
        
        # Encrypt stream
        metadata = await encryption_service.encrypt_stream(
            input_stream,
            output_stream,
            key.key_id
        )
        
        assert metadata.key_id == key.key_id
        assert metadata.original_size == len(test_data)
        
        # Get encrypted data
        encrypted_data = output_stream.getvalue()
        assert encrypted_data != test_data
        
        # Decrypt
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            metadata
        )
        
        assert decrypted_data == test_data
    
    async def test_encrypt_stream_aes_gcm(self, encryption_service):
        """Test stream encryption with AES-GCM"""
        import io
        
        test_data = b"This is test data for stream encryption!" * 100  # Larger data
        input_stream = io.BytesIO(test_data)
        output_stream = io.BytesIO()
        
        key = encryption_service.create_key(
            "test_stream_aes",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt stream
        metadata = await encryption_service.encrypt_stream(
            input_stream,
            output_stream,
            key.key_id
        )
        
        assert metadata.key_id == key.key_id
        assert metadata.original_size == len(test_data)
        assert metadata.iv is not None
        
        # Get encrypted data (includes IV and tag)
        encrypted_data = output_stream.getvalue()
        assert len(encrypted_data) > len(test_data)


class TestEncryptionMetadata:
    """Test cases for encryption metadata"""
    
    def test_metadata_serialization(self):
        """Test metadata to/from dict conversion"""
        import base64
        
        iv = secrets.token_bytes(12)
        salt = secrets.token_bytes(16)
        
        metadata = EncryptionMetadata(
            key_id="test_key",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            iv=iv,
            salt=salt,
            file_hash="abcdef123456",
            original_size=1024,
            checksum="tag123"
        )
        
        # Convert to dict
        data = metadata.to_dict()
        
        assert data["key_id"] == "test_key"
        assert data["algorithm"] == "aes_256_gcm"
        assert data["iv"] == base64.b64encode(iv).decode()
        assert data["salt"] == base64.b64encode(salt).decode()
        assert data["file_hash"] == "abcdef123456"
        assert data["original_size"] == 1024
        
        # Convert back from dict
        restored_metadata = EncryptionMetadata.from_dict(data)
        
        assert restored_metadata.key_id == metadata.key_id
        assert restored_metadata.algorithm == metadata.algorithm
        assert restored_metadata.iv == metadata.iv
        assert restored_metadata.salt == metadata.salt
        assert restored_metadata.file_hash == metadata.file_hash
        assert restored_metadata.original_size == metadata.original_size


class TestKeyPersistence:
    """Test cases for key persistence"""
    
    async def test_save_and_load_keys(self, encryption_service):
        """Test saving and loading keys"""
        # Create test keys
        key1 = encryption_service.create_key(
            "persistent_key1",
            EncryptionAlgorithm.AES_256_GCM
        )
        key2 = encryption_service.create_key(
            "persistent_key2",
            EncryptionAlgorithm.FERNET
        )
        
        # Save keys
        await encryption_service._save_keys()
        
        # Clear keys and reload
        encryption_service._keys.clear()
        await encryption_service._load_keys()
        
        # Check that keys were restored
        assert "persistent_key1" in encryption_service._keys
        assert "persistent_key2" in encryption_service._keys
        
        restored_key1 = encryption_service._keys["persistent_key1"]
        assert restored_key1.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert restored_key1.key_data == key1.key_data
        
        restored_key2 = encryption_service._keys["persistent_key2"]
        assert restored_key2.algorithm == EncryptionAlgorithm.FERNET
        assert restored_key2.key_data == key2.key_data


class TestEncryptionIntegration:
    """Integration tests for encryption functionality"""
    
    async def test_full_encryption_workflow(self, encryption_service):
        """Test complete encryption workflow"""
        # 1. Create encryption key
        key = encryption_service.create_key(
            "workflow_test",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # 2. Prepare test data
        test_data = b"This is sensitive data that needs encryption!"
        original_hash = hashlib.sha256(test_data).hexdigest()
        
        # 3. Encrypt the data
        encrypted_data, metadata = await encryption_service.encrypt_file(
            test_data,
            key.key_id
        )
        
        # 4. Verify encryption metadata
        assert metadata.key_id == key.key_id
        assert metadata.file_hash == original_hash
        assert metadata.original_size == len(test_data)
        assert encrypted_data != test_data
        
        # 5. Save metadata (simulate storage)
        metadata_dict = metadata.to_dict()
        restored_metadata = EncryptionMetadata.from_dict(metadata_dict)
        
        # 6. Decrypt the data
        decrypted_data = await encryption_service.decrypt_file(
            encrypted_data,
            restored_metadata
        )
        
        # 7. Verify decryption
        assert decrypted_data == test_data
        assert hashlib.sha256(decrypted_data).hexdigest() == original_hash
        
        # 8. Verify key usage was updated
        assert key.last_used > key.created_at
    
    async def test_encryption_with_key_rotation(self, encryption_service):
        """Test encryption workflow with key rotation"""
        # Create initial key
        original_key = encryption_service.create_key(
            "rotation_test",
            EncryptionAlgorithm.AES_256_GCM
        )
        
        # Encrypt data with original key
        test_data = b"Data encrypted with original key"
        encrypted_data1, metadata1 = await encryption_service.encrypt_file(
            test_data,
            original_key.key_id
        )
        
        # Rotate the key
        new_key = encryption_service.rotate_key(original_key.key_id)
        
        # Encrypt new data with rotated key
        test_data2 = b"Data encrypted with rotated key"
        encrypted_data2, metadata2 = await encryption_service.encrypt_file(
            test_data2,
            new_key.key_id
        )
        
        # Both decryptions should work
        decrypted_data1 = await encryption_service.decrypt_file(
            encrypted_data1,
            metadata1
        )
        decrypted_data2 = await encryption_service.decrypt_file(
            encrypted_data2,
            metadata2
        )
        
        assert decrypted_data1 == test_data
        assert decrypted_data2 == test_data2
        
        # Original key should be marked for rotation
        assert original_key.rotation_required is True