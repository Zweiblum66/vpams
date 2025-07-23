"""Encryption utilities for GDPR compliance"""

import os
import base64
from pathlib import Path
from typing import Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import aiofiles
import asyncio


def generate_key(password: str, salt: Optional[bytes] = None) -> bytes:
    """Generate encryption key from password"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def get_fernet(key: Union[str, bytes]) -> Fernet:
    """Get Fernet instance from key"""
    if isinstance(key, str):
        # If key is a password, generate proper key
        if len(key) < 32:
            key = generate_key(key)
        else:
            key = key.encode()
    
    return Fernet(key)


async def encrypt_file(
    file_path: Path,
    key: Union[str, bytes],
    output_path: Optional[Path] = None,
    chunk_size: int = 64 * 1024  # 64KB chunks
) -> Path:
    """Encrypt a file asynchronously"""
    fernet = get_fernet(key)
    
    if output_path is None:
        output_path = file_path.with_suffix(file_path.suffix + ".encrypted")
    
    async with aiofiles.open(file_path, 'rb') as infile:
        async with aiofiles.open(output_path, 'wb') as outfile:
            # Write file header with version
            await outfile.write(b"GDPR_ENC_V1\n")
            
            while True:
                chunk = await infile.read(chunk_size)
                if not chunk:
                    break
                
                encrypted_chunk = fernet.encrypt(chunk)
                # Write chunk size (4 bytes) followed by encrypted chunk
                chunk_size_bytes = len(encrypted_chunk).to_bytes(4, 'big')
                await outfile.write(chunk_size_bytes)
                await outfile.write(encrypted_chunk)
    
    return output_path


async def decrypt_file(
    file_path: Path,
    key: Union[str, bytes],
    output_path: Optional[Path] = None
) -> Path:
    """Decrypt a file asynchronously"""
    fernet = get_fernet(key)
    
    if output_path is None:
        if file_path.suffix == ".encrypted":
            output_path = file_path.with_suffix("")
        else:
            output_path = file_path.with_name(file_path.stem + "_decrypted" + file_path.suffix)
    
    async with aiofiles.open(file_path, 'rb') as infile:
        # Read and verify header
        header = await infile.read(12)
        if header != b"GDPR_ENC_V1\n":
            raise ValueError("Invalid encrypted file format")
        
        async with aiofiles.open(output_path, 'wb') as outfile:
            while True:
                # Read chunk size
                size_bytes = await infile.read(4)
                if not size_bytes:
                    break
                
                chunk_size = int.from_bytes(size_bytes, 'big')
                # Read encrypted chunk
                encrypted_chunk = await infile.read(chunk_size)
                if not encrypted_chunk:
                    break
                
                decrypted_chunk = fernet.decrypt(encrypted_chunk)
                await outfile.write(decrypted_chunk)
    
    return output_path


def encrypt_string(data: str, key: Union[str, bytes]) -> str:
    """Encrypt a string and return base64 encoded result"""
    fernet = get_fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_string(encrypted_data: str, key: Union[str, bytes]) -> str:
    """Decrypt a base64 encoded encrypted string"""
    fernet = get_fernet(key)
    decoded = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted = fernet.decrypt(decoded)
    return decrypted.decode()


def encrypt_dict(data: dict, key: Union[str, bytes], fields: Optional[list] = None) -> dict:
    """Encrypt specific fields in a dictionary"""
    fernet = get_fernet(key)
    encrypted_data = data.copy()
    
    if fields is None:
        # Encrypt all string values
        fields = [k for k, v in data.items() if isinstance(v, str)]
    
    for field in fields:
        if field in encrypted_data and encrypted_data[field] is not None:
            value = str(encrypted_data[field])
            encrypted_value = fernet.encrypt(value.encode())
            encrypted_data[field] = base64.urlsafe_b64encode(encrypted_value).decode()
    
    return encrypted_data


def decrypt_dict(encrypted_data: dict, key: Union[str, bytes], fields: Optional[list] = None) -> dict:
    """Decrypt specific fields in a dictionary"""
    fernet = get_fernet(key)
    decrypted_data = encrypted_data.copy()
    
    if fields is None:
        # Try to decrypt all string values that look like base64
        fields = []
        for k, v in encrypted_data.items():
            if isinstance(v, str) and _is_base64(v):
                fields.append(k)
    
    for field in fields:
        if field in decrypted_data and decrypted_data[field] is not None:
            try:
                decoded = base64.urlsafe_b64decode(decrypted_data[field].encode())
                decrypted_value = fernet.decrypt(decoded)
                decrypted_data[field] = decrypted_value.decode()
            except Exception:
                # If decryption fails, leave the value as is
                pass
    
    return decrypted_data


def _is_base64(s: str) -> bool:
    """Check if a string is likely base64 encoded"""
    try:
        if len(s) % 4 != 0:
            return False
        base64.urlsafe_b64decode(s.encode())
        return True
    except Exception:
        return False


async def secure_delete_file(file_path: Path, passes: int = 3) -> None:
    """Securely delete a file by overwriting with random data"""
    if not file_path.exists():
        return
    
    file_size = file_path.stat().st_size
    
    async with aiofiles.open(file_path, 'r+b') as f:
        for _ in range(passes):
            await f.seek(0)
            # Write random data
            await f.write(os.urandom(file_size))
            await f.flush()
            os.fsync(f.fileno())
    
    # Finally remove the file
    file_path.unlink()


class EncryptedFieldManager:
    """Manager for handling encrypted fields in database models"""
    
    def __init__(self, key: Union[str, bytes]):
        self.fernet = get_fernet(key)
    
    def encrypt_field(self, value: Optional[str]) -> Optional[str]:
        """Encrypt a field value"""
        if value is None:
            return None
        encrypted = self.fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_field(self, encrypted_value: Optional[str]) -> Optional[str]:
        """Decrypt a field value"""
        if encrypted_value is None:
            return None
        try:
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            # Return original value if decryption fails
            return encrypted_value
    
    def encrypt_json(self, data: dict, fields: list) -> dict:
        """Encrypt specific fields in JSON data"""
        return encrypt_dict(data, self.fernet._signing_key, fields)
    
    def decrypt_json(self, data: dict, fields: list) -> dict:
        """Decrypt specific fields in JSON data"""
        return decrypt_dict(data, self.fernet._signing_key, fields)


# Utility functions for key management
def save_key(key: bytes, key_file: Path) -> None:
    """Save encryption key to file (use with caution in production)"""
    key_file.parent.mkdir(parents=True, exist_ok=True)
    with open(key_file, 'wb') as f:
        f.write(key)


def load_key(key_file: Path) -> bytes:
    """Load encryption key from file"""
    with open(key_file, 'rb') as f:
        return f.read()


def rotate_encryption(
    old_key: Union[str, bytes],
    new_key: Union[str, bytes],
    data: dict,
    fields: list
) -> dict:
    """Rotate encryption from old key to new key"""
    # Decrypt with old key
    decrypted = decrypt_dict(data, old_key, fields)
    # Encrypt with new key
    return encrypt_dict(decrypted, new_key, fields)