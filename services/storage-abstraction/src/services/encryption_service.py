"""
File Encryption Service

This module handles encryption and decryption of files at rest using various
encryption algorithms and key management strategies.
"""

import asyncio
import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from io import BytesIO
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

from ..core.interfaces import (
    StorageObject, ObjectNotFoundError, InvalidStorageOperationError,
    StorageOperationError
)
from ..core.config import get_settings


logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256_CBC = "aes_256_cbc"
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    CHACHA20_POLY1305 = "chacha20_poly1305"


class KeyDerivationMethod(Enum):
    """Key derivation methods"""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"


@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata"""
    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    salt: Optional[bytes] = None
    iv: Optional[bytes] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    rotation_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "key_data": base64.b64encode(self.key_data).decode(),
            "salt": base64.b64encode(self.salt).decode() if self.salt else None,
            "iv": base64.b64encode(self.iv).decode() if self.iv else None,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "rotation_required": self.rotation_required,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptionKey':
        """Create from dictionary"""
        return cls(
            key_id=data["key_id"],
            algorithm=EncryptionAlgorithm(data["algorithm"]),
            key_data=base64.b64decode(data["key_data"]),
            salt=base64.b64decode(data["salt"]) if data.get("salt") else None,
            iv=base64.b64decode(data["iv"]) if data.get("iv") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            rotation_required=data.get("rotation_required", False),
            metadata=data.get("metadata", {})
        )


@dataclass
class EncryptionMetadata:
    """Metadata for encrypted files"""
    key_id: str
    algorithm: EncryptionAlgorithm
    iv: Optional[bytes] = None
    salt: Optional[bytes] = None
    file_hash: Optional[str] = None
    original_size: Optional[int] = None
    encrypted_at: datetime = field(default_factory=datetime.utcnow)
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "iv": base64.b64encode(self.iv).decode() if self.iv else None,
            "salt": base64.b64encode(self.salt).decode() if self.salt else None,
            "file_hash": self.file_hash,
            "original_size": self.original_size,
            "encrypted_at": self.encrypted_at.isoformat(),
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptionMetadata':
        """Create from dictionary"""
        return cls(
            key_id=data["key_id"],
            algorithm=EncryptionAlgorithm(data["algorithm"]),
            iv=base64.b64decode(data["iv"]) if data.get("iv") else None,
            salt=base64.b64decode(data["salt"]) if data.get("salt") else None,
            file_hash=data.get("file_hash"),
            original_size=data.get("original_size"),
            encrypted_at=datetime.fromisoformat(data["encrypted_at"]),
            checksum=data.get("checksum")
        )


class EncryptionService:
    """Service for handling file encryption at rest"""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        self.settings = get_settings()
        
        # Encryption configuration
        self._keys: Dict[str, EncryptionKey] = {}
        self._default_algorithm = EncryptionAlgorithm.AES_256_GCM
        self._chunk_size = 8192  # 8KB chunks for streaming
        
        # Key management
        self._master_key: Optional[bytes] = None
        self._key_rotation_days = 90
        
        # Data persistence
        self._data_dir = Path(self.settings.temp_directory) / "encryption"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._key_rotation_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Load configuration
        self._load_master_key()
        self._load_default_keys()
    
    def _load_master_key(self) -> None:
        """Load or generate master key"""
        master_key_file = self._data_dir / "master.key"
        
        if master_key_file.exists():
            with open(master_key_file, 'rb') as f:
                self._master_key = f.read()
        else:
            # Generate new master key
            self._master_key = secrets.token_bytes(32)
            with open(master_key_file, 'wb') as f:
                f.write(self._master_key)
            
            # Secure the file
            os.chmod(master_key_file, 0o600)
    
    def _load_default_keys(self) -> None:
        """Load default encryption keys"""
        if self.settings.enable_encryption:
            # Create default AES-256-GCM key
            default_key = self._generate_key(
                "default_aes_256_gcm",
                EncryptionAlgorithm.AES_256_GCM
            )
            self._keys[default_key.key_id] = default_key
            
            # Create Fernet key for backwards compatibility
            fernet_key = self._generate_key(
                "default_fernet",
                EncryptionAlgorithm.FERNET
            )
            self._keys[fernet_key.key_id] = fernet_key
    
    async def initialize(self) -> None:
        """Initialize the encryption service"""
        logger.info("Initializing encryption service")
        
        # Load persisted keys
        await self._load_keys()
        
        # Start background tasks
        if self.settings.enable_encryption:
            self._key_rotation_task = asyncio.create_task(self._key_rotation_worker())
    
    async def shutdown(self) -> None:
        """Shutdown the encryption service"""
        logger.info("Shutting down encryption service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel background tasks
        if self._key_rotation_task:
            self._key_rotation_task.cancel()
            try:
                await self._key_rotation_task
            except asyncio.CancelledError:
                pass
        
        # Save keys
        await self._save_keys()
    
    def _generate_key(
        self,
        key_id: str,
        algorithm: EncryptionAlgorithm,
        password: Optional[str] = None
    ) -> EncryptionKey:
        """Generate a new encryption key"""
        if algorithm == EncryptionAlgorithm.AES_256_CBC:
            key_data = secrets.token_bytes(32)  # 256 bits
            iv = secrets.token_bytes(16)  # 128 bits
            return EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data,
                iv=iv
            )
        
        elif algorithm == EncryptionAlgorithm.AES_256_GCM:
            key_data = secrets.token_bytes(32)  # 256 bits
            return EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data
            )
        
        elif algorithm == EncryptionAlgorithm.FERNET:
            key_data = Fernet.generate_key()
            return EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data
            )
        
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            key_data = secrets.token_bytes(32)  # 256 bits
            return EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data
            )
        
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    async def encrypt_file(
        self,
        file_data: bytes,
        key_id: Optional[str] = None,
        algorithm: Optional[EncryptionAlgorithm] = None
    ) -> Tuple[bytes, EncryptionMetadata]:
        """Encrypt file data"""
        # Select key and algorithm
        if key_id and key_id in self._keys:
            key = self._keys[key_id]
        else:
            # Use default key
            algorithm = algorithm or self._default_algorithm
            key = self._get_default_key(algorithm)
        
        # Calculate original file hash
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Encrypt based on algorithm
        if key.algorithm == EncryptionAlgorithm.AES_256_CBC:
            encrypted_data, iv = self._encrypt_aes_cbc(file_data, key)
            metadata = EncryptionMetadata(
                key_id=key.key_id,
                algorithm=key.algorithm,
                iv=iv,
                file_hash=file_hash,
                original_size=len(file_data)
            )
        
        elif key.algorithm == EncryptionAlgorithm.AES_256_GCM:
            encrypted_data, iv, tag = self._encrypt_aes_gcm(file_data, key)
            metadata = EncryptionMetadata(
                key_id=key.key_id,
                algorithm=key.algorithm,
                iv=iv,
                file_hash=file_hash,
                original_size=len(file_data),
                checksum=base64.b64encode(tag).decode()
            )
        
        elif key.algorithm == EncryptionAlgorithm.FERNET:
            encrypted_data = self._encrypt_fernet(file_data, key)
            metadata = EncryptionMetadata(
                key_id=key.key_id,
                algorithm=key.algorithm,
                file_hash=file_hash,
                original_size=len(file_data)
            )
        
        elif key.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            encrypted_data, nonce, tag = self._encrypt_chacha20(file_data, key)
            metadata = EncryptionMetadata(
                key_id=key.key_id,
                algorithm=key.algorithm,
                iv=nonce,
                file_hash=file_hash,
                original_size=len(file_data),
                checksum=base64.b64encode(tag).decode()
            )
        
        else:
            raise ValueError(f"Unsupported algorithm: {key.algorithm}")
        
        # Update key usage
        key.last_used = datetime.utcnow()
        
        return encrypted_data, metadata
    
    async def decrypt_file(
        self,
        encrypted_data: bytes,
        metadata: EncryptionMetadata
    ) -> bytes:
        """Decrypt file data"""
        # Get encryption key
        if metadata.key_id not in self._keys:
            raise InvalidStorageOperationError(f"Encryption key not found: {metadata.key_id}")
        
        key = self._keys[metadata.key_id]
        
        # Decrypt based on algorithm
        if metadata.algorithm == EncryptionAlgorithm.AES_256_CBC:
            decrypted_data = self._decrypt_aes_cbc(encrypted_data, key, metadata.iv)
        
        elif metadata.algorithm == EncryptionAlgorithm.AES_256_GCM:
            tag = base64.b64decode(metadata.checksum) if metadata.checksum else None
            decrypted_data = self._decrypt_aes_gcm(encrypted_data, key, metadata.iv, tag)
        
        elif metadata.algorithm == EncryptionAlgorithm.FERNET:
            decrypted_data = self._decrypt_fernet(encrypted_data, key)
        
        elif metadata.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            tag = base64.b64decode(metadata.checksum) if metadata.checksum else None
            decrypted_data = self._decrypt_chacha20(encrypted_data, key, metadata.iv, tag)
        
        else:
            raise ValueError(f"Unsupported algorithm: {metadata.algorithm}")
        
        # Verify file integrity if hash is available
        if metadata.file_hash:
            actual_hash = hashlib.sha256(decrypted_data).hexdigest()
            if actual_hash != metadata.file_hash:
                raise StorageOperationError("File integrity check failed - hash mismatch")
        
        # Update key usage
        key.last_used = datetime.utcnow()
        
        return decrypted_data
    
    async def encrypt_stream(
        self,
        input_stream: BinaryIO,
        output_stream: BinaryIO,
        key_id: Optional[str] = None,
        algorithm: Optional[EncryptionAlgorithm] = None
    ) -> EncryptionMetadata:
        """Encrypt a file stream"""
        # Select key and algorithm
        if key_id and key_id in self._keys:
            key = self._keys[key_id]
        else:
            algorithm = algorithm or self._default_algorithm
            key = self._get_default_key(algorithm)
        
        # Initialize hash calculator
        hasher = hashlib.sha256()
        original_size = 0
        
        # Encrypt based on algorithm (streaming where possible)
        if key.algorithm == EncryptionAlgorithm.FERNET:
            # Fernet doesn't support streaming, read all data
            data = input_stream.read()
            original_size = len(data)
            hasher.update(data)
            
            encrypted_data = self._encrypt_fernet(data, key)
            output_stream.write(encrypted_data)
            
            metadata = EncryptionMetadata(
                key_id=key.key_id,
                algorithm=key.algorithm,
                file_hash=hasher.hexdigest(),
                original_size=original_size
            )
        
        else:
            # For AES algorithms, implement streaming encryption
            if key.algorithm == EncryptionAlgorithm.AES_256_GCM:
                iv = secrets.token_bytes(12)  # 96 bits for GCM
                cipher = Cipher(
                    algorithms.AES(key.key_data),
                    modes.GCM(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                
                # Write IV first
                output_stream.write(iv)
                
                # Encrypt in chunks
                while True:
                    chunk = input_stream.read(self._chunk_size)
                    if not chunk:
                        break
                    
                    hasher.update(chunk)
                    original_size += len(chunk)
                    encrypted_chunk = encryptor.update(chunk)
                    output_stream.write(encrypted_chunk)
                
                # Finalize and get tag
                encryptor.finalize()
                tag = encryptor.tag
                output_stream.write(tag)
                
                metadata = EncryptionMetadata(
                    key_id=key.key_id,
                    algorithm=key.algorithm,
                    iv=iv,
                    file_hash=hasher.hexdigest(),
                    original_size=original_size,
                    checksum=base64.b64encode(tag).decode()
                )
            
            else:
                # Fallback to reading all data for other algorithms
                data = input_stream.read()
                original_size = len(data)
                hasher.update(data)
                
                encrypted_data, metadata = await self.encrypt_file(data, key.key_id)
                output_stream.write(encrypted_data)
        
        # Update key usage
        key.last_used = datetime.utcnow()
        
        return metadata
    
    def _encrypt_aes_cbc(self, data: bytes, key: EncryptionKey) -> Tuple[bytes, bytes]:
        """Encrypt using AES-256-CBC"""
        iv = secrets.token_bytes(16)
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # PKCS7 padding
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padded_data = data + bytes([padding_length] * padding_length)
        
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return encrypted_data, iv
    
    def _decrypt_aes_cbc(self, data: bytes, key: EncryptionKey, iv: bytes) -> bytes:
        """Decrypt using AES-256-CBC"""
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(data) + decryptor.finalize()
        
        # Remove PKCS7 padding
        padding_length = decrypted_padded[-1]
        return decrypted_padded[:-padding_length]
    
    def _encrypt_aes_gcm(self, data: bytes, key: EncryptionKey) -> Tuple[bytes, bytes, bytes]:
        """Encrypt using AES-256-GCM"""
        iv = secrets.token_bytes(12)  # 96 bits for GCM
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        return encrypted_data, iv, encryptor.tag
    
    def _decrypt_aes_gcm(self, data: bytes, key: EncryptionKey, iv: bytes, tag: bytes) -> bytes:
        """Decrypt using AES-256-GCM"""
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        return decryptor.update(data) + decryptor.finalize()
    
    def _encrypt_fernet(self, data: bytes, key: EncryptionKey) -> bytes:
        """Encrypt using Fernet"""
        f = Fernet(key.key_data)
        return f.encrypt(data)
    
    def _decrypt_fernet(self, data: bytes, key: EncryptionKey) -> bytes:
        """Decrypt using Fernet"""
        f = Fernet(key.key_data)
        return f.decrypt(data)
    
    def _encrypt_chacha20(self, data: bytes, key: EncryptionKey) -> Tuple[bytes, bytes, bytes]:
        """Encrypt using ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        aead = ChaCha20Poly1305(key.key_data)
        nonce = secrets.token_bytes(12)
        encrypted_data = aead.encrypt(nonce, data, None)
        
        # Split encrypted data and tag
        ciphertext = encrypted_data[:-16]
        tag = encrypted_data[-16:]
        
        return ciphertext, nonce, tag
    
    def _decrypt_chacha20(self, data: bytes, key: EncryptionKey, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt using ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        aead = ChaCha20Poly1305(key.key_data)
        encrypted_data = data + tag
        return aead.decrypt(nonce, encrypted_data, None)
    
    def _get_default_key(self, algorithm: EncryptionAlgorithm) -> EncryptionKey:
        """Get default key for algorithm"""
        for key in self._keys.values():
            if key.algorithm == algorithm:
                return key
        
        # Generate new key if none exists
        key_id = f"default_{algorithm.value}"
        new_key = self._generate_key(key_id, algorithm)
        self._keys[key_id] = new_key
        return new_key
    
    def create_key(
        self,
        key_id: str,
        algorithm: EncryptionAlgorithm,
        password: Optional[str] = None
    ) -> EncryptionKey:
        """Create a new encryption key"""
        if key_id in self._keys:
            raise InvalidStorageOperationError(f"Key already exists: {key_id}")
        
        key = self._generate_key(key_id, algorithm, password)
        self._keys[key_id] = key
        
        logger.info(f"Created encryption key: {key_id}")
        return key
    
    def rotate_key(self, key_id: str) -> EncryptionKey:
        """Rotate an encryption key"""
        if key_id not in self._keys:
            raise InvalidStorageOperationError(f"Key not found: {key_id}")
        
        old_key = self._keys[key_id]
        new_key = self._generate_key(f"{key_id}_rotated_{int(datetime.utcnow().timestamp())}", old_key.algorithm)
        
        # Mark old key for rotation
        old_key.rotation_required = True
        
        # Add new key
        self._keys[new_key.key_id] = new_key
        
        logger.info(f"Rotated encryption key: {key_id} -> {new_key.key_id}")
        return new_key
    
    def get_keys(self) -> List[EncryptionKey]:
        """Get all encryption keys"""
        return list(self._keys.values())
    
    def delete_key(self, key_id: str) -> None:
        """Delete an encryption key"""
        if key_id not in self._keys:
            raise InvalidStorageOperationError(f"Key not found: {key_id}")
        
        del self._keys[key_id]
        logger.info(f"Deleted encryption key: {key_id}")
    
    async def _key_rotation_worker(self) -> None:
        """Background worker for automatic key rotation"""
        logger.info("Starting key rotation worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Check for keys that need rotation every day
                await asyncio.sleep(86400)
                
                cutoff_date = datetime.utcnow() - timedelta(days=self._key_rotation_days)
                
                for key in list(self._keys.values()):
                    if key.created_at < cutoff_date and not key.rotation_required:
                        try:
                            self.rotate_key(key.key_id)
                        except Exception as e:
                            logger.error(f"Failed to rotate key {key.key_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Key rotation worker error: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retry
        
        logger.info("Key rotation worker stopped")
    
    async def _save_keys(self) -> None:
        """Save encryption keys to disk"""
        try:
            keys_data = {
                key_id: key.to_dict()
                for key_id, key in self._keys.items()
            }
            
            keys_file = self._data_dir / "keys.json"
            with open(keys_file, 'w') as f:
                json.dump(keys_data, f, indent=2)
            
            # Secure the file
            os.chmod(keys_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save encryption keys: {e}")
    
    async def _load_keys(self) -> None:
        """Load encryption keys from disk"""
        try:
            keys_file = self._data_dir / "keys.json"
            if keys_file.exists():
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
                
                for key_id, key_data in keys_data.items():
                    self._keys[key_id] = EncryptionKey.from_dict(key_data)
            
        except Exception as e:
            logger.error(f"Failed to load encryption keys: {e}")


# Global instance
_encryption_service: Optional[EncryptionService] = None


async def get_encryption_service(storage_service) -> EncryptionService:
    """Get or create encryption service instance"""
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService(storage_service)
        await _encryption_service.initialize()
    
    return _encryption_service


async def close_encryption_service() -> None:
    """Close encryption service"""
    global _encryption_service
    
    if _encryption_service is not None:
        await _encryption_service.shutdown()
        _encryption_service = None