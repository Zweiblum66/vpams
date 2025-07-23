"""
Encryption Service for Blockchain Data
"""

import os
import base64
from typing import Dict, Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

from .logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting blockchain data"""
    
    def __init__(self):
        self._master_key = self._get_or_create_master_key()
        self._fernet = Fernet(self._master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        # In production, this should be stored in a secure key management service
        key_file = os.getenv("ENCRYPTION_KEY_FILE", ".encryption_key")
        
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict access
            logger.info("Generated new encryption master key")
            return key
    
    def encrypt(self, data: bytes) -> Tuple[bytes, str]:
        """
        Encrypt data and return encrypted data with key ID
        
        Returns:
            Tuple of (encrypted_data, key_id)
        """
        try:
            # Generate a unique key for this data
            data_key = Fernet.generate_key()
            fernet = Fernet(data_key)
            
            # Encrypt the data
            encrypted_data = fernet.encrypt(data)
            
            # Encrypt the data key with master key
            encrypted_key = self._fernet.encrypt(data_key)
            
            # Generate key ID
            key_id = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode()
            
            # Store encrypted key (in production, use secure key storage)
            self._store_encrypted_key(key_id, encrypted_key)
            
            return encrypted_data, key_id
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data using key ID"""
        try:
            # Retrieve encrypted key
            encrypted_key = self._retrieve_encrypted_key(key_id)
            if not encrypted_key:
                raise ValueError(f"Key not found: {key_id}")
            
            # Decrypt the data key
            data_key = self._fernet.decrypt(encrypted_key)
            fernet = Fernet(data_key)
            
            # Decrypt the data
            decrypted_data = fernet.decrypt(encrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def encrypt_with_aes_gcm(self, data: bytes, associated_data: bytes = b"") -> Dict[str, str]:
        """
        Encrypt data using AES-GCM for authenticated encryption
        
        Args:
            data: Data to encrypt
            associated_data: Additional data to authenticate but not encrypt
            
        Returns:
            Dictionary with encrypted_data, nonce, and key_id
        """
        try:
            # Generate a 256-bit key
            key = AESGCM.generate_key(bit_length=256)
            aesgcm = AESGCM(key)
            
            # Generate a 96-bit nonce
            nonce = os.urandom(12)
            
            # Encrypt
            ciphertext = aesgcm.encrypt(nonce, data, associated_data)
            
            # Encrypt the key with master key
            encrypted_key = self._fernet.encrypt(key)
            
            # Generate key ID
            key_id = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode()
            
            # Store encrypted key
            self._store_encrypted_key(key_id, encrypted_key)
            
            return {
                "encrypted_data": base64.b64encode(ciphertext).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "key_id": key_id
            }
            
        except Exception as e:
            logger.error(f"AES-GCM encryption failed: {str(e)}")
            raise
    
    def decrypt_with_aes_gcm(
        self,
        encrypted_data: str,
        nonce: str,
        key_id: str,
        associated_data: bytes = b""
    ) -> bytes:
        """Decrypt data encrypted with AES-GCM"""
        try:
            # Retrieve and decrypt the key
            encrypted_key = self._retrieve_encrypted_key(key_id)
            if not encrypted_key:
                raise ValueError(f"Key not found: {key_id}")
            
            key = self._fernet.decrypt(encrypted_key)
            aesgcm = AESGCM(key)
            
            # Decode from base64
            ciphertext = base64.b64decode(encrypted_data)
            nonce_bytes = base64.b64decode(nonce)
            
            # Decrypt
            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext, associated_data)
            
            return plaintext
            
        except Exception as e:
            logger.error(f"AES-GCM decryption failed: {str(e)}")
            raise
    
    def derive_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _store_encrypted_key(self, key_id: str, encrypted_key: bytes):
        """Store encrypted key (in production, use secure key storage like AWS KMS, HashiCorp Vault, etc.)"""
        # For demo purposes, store in memory
        if not hasattr(self, '_key_store'):
            self._key_store = {}
        
        self._key_store[key_id] = encrypted_key
    
    def _retrieve_encrypted_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve encrypted key"""
        if not hasattr(self, '_key_store'):
            return None
        
        return self._key_store.get(key_id)
    
    def generate_hash(self, data: bytes) -> str:
        """Generate SHA-256 hash of data"""
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        return digest.finalize().hex()
    
    def verify_hash(self, data: bytes, expected_hash: str) -> bool:
        """Verify data matches expected hash"""
        actual_hash = self.generate_hash(data)
        return actual_hash == expected_hash