"""
FTP/SFTP Storage Driver

This module implements FTP and SFTP storage drivers for the storage abstraction layer.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple, Union
from pathlib import Path, PurePosixPath
import mimetypes
import hashlib
import tempfile
import os
from io import BytesIO

try:
    import paramiko
    from paramiko import SSHClient, AutoAddPolicy, SFTPClient
except ImportError:
    paramiko = None
    SSHClient = None
    SFTPClient = None

try:
    import aioftp
except ImportError:
    aioftp = None

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageTier, PresignedUrl,
    ObjectNotFoundError, StorageQuotaExceededError, StoragePermissionError,
    InvalidStorageOperationError, StorageOperationError
)


logger = logging.getLogger(__name__)


class FTPStorageDriver(StorageDriver):
    """FTP storage driver implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize FTP driver"""
        if aioftp is None:
            raise ImportError("aioftp package is required for FTP storage")
        
        self.config = config
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 21)
        self.username = config.get("username", "anonymous")
        self.password = config.get("password", "")
        self.path_prefix = config.get("path_prefix", "/")
        self.passive = config.get("passive", True)
        self.timeout = config.get("timeout", 30)
        self.encoding = config.get("encoding", "utf-8")
        
        # Connection pool
        self._client: Optional[aioftp.Client] = None
        
        # Ensure path prefix ends with /
        if not self.path_prefix.endswith("/"):
            self.path_prefix += "/"
    
    async def initialize(self) -> None:
        """Initialize the driver"""
        # Test connection
        await self._ensure_connected()
    
    async def close(self) -> None:
        """Close the driver and cleanup resources"""
        if self._client:
            await self._client.quit()
            self._client = None
    
    async def _ensure_connected(self) -> aioftp.Client:
        """Ensure FTP connection is established"""
        if self._client is None:
            self._client = aioftp.Client(
                encoding=self.encoding,
                socket_timeout=self.timeout
            )
            await self._client.connect(self.host, self.port)
            await self._client.login(self.username, self.password)
            
            if self.passive:
                self._client.passive_commands.add("MLSD")
                self._client.passive_commands.add("LIST")
                self._client.passive_commands.add("RETR")
                self._client.passive_commands.add("STOR")
        
        return self._client
    
    def _normalize_path(self, key: str) -> str:
        """Normalize object key to FTP path"""
        if key.startswith("/"):
            key = key[1:]
        
        # Combine with prefix
        full_path = PurePosixPath(self.path_prefix) / key
        return str(full_path)
    
    def _extract_key(self, ftp_path: str) -> str:
        """Extract object key from FTP path"""
        if ftp_path.startswith(self.path_prefix):
            key = ftp_path[len(self.path_prefix):]
            if key.startswith("/"):
                key = key[1:]
            return key
        return ftp_path
    
    async def _parse_list_line(self, line: str) -> Optional[StorageObject]:
        """Parse FTP LIST response line"""
        # This is a simplified parser - real implementation would need to handle
        # various FTP server formats (Unix, Windows, etc.)
        parts = line.split(None, 8)
        if len(parts) < 9:
            return None
        
        # Unix-style listing
        permissions = parts[0]
        size = int(parts[4])
        date_parts = parts[5:8]
        name = parts[8]
        
        # Skip directories (starts with 'd')
        if permissions.startswith('d'):
            return None
        
        # Parse date (simplified)
        try:
            # This is very simplified - real implementation needs better parsing
            modified = datetime.utcnow()  # Placeholder
        except:
            modified = datetime.utcnow()
        
        key = self._extract_key(name)
        
        return StorageObject(
            key=key,
            size=size,
            last_modified=modified,
            etag=hashlib.md5(f"{name}_{size}".encode()).hexdigest(),
            content_type=mimetypes.guess_type(name)[0],
            metadata={
                "permissions": permissions,
                "raw_listing": line
            },
            storage_class="standard"
        )
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata"""
        try:
            client = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Get file info using MLST if available, otherwise use SIZE
            try:
                info = await client.mlst(path)
                size = int(info.get("size", 0))
                
                # Parse modify time if available
                modify = info.get("modify", "")
                if modify:
                    # Parse YYYYMMDDHHMMSS format
                    modified = datetime.strptime(modify, "%Y%m%d%H%M%S")
                else:
                    modified = datetime.utcnow()
                
                return StorageObject(
                    key=key,
                    size=size,
                    last_modified=modified,
                    etag=hashlib.md5(f"{path}_{size}".encode()).hexdigest(),
                    content_type=mimetypes.guess_type(key)[0],
                    metadata={"mlst_info": info},
                    storage_class="standard"
                )
                
            except aioftp.StatusCodeError as e:
                if e.received_codes[-1].startswith("550"):  # File not found
                    raise ObjectNotFoundError(key)
                
                # Fallback to SIZE command
                size = await client.get_size(path)
                if size is None:
                    raise ObjectNotFoundError(key)
                
                return StorageObject(
                    key=key,
                    size=size,
                    last_modified=datetime.utcnow(),
                    etag=hashlib.md5(f"{path}_{size}".encode()).hexdigest(),
                    content_type=mimetypes.guess_type(key)[0],
                    metadata={},
                    storage_class="standard"
                )
        
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get object info for {key}: {e}")
            raise StorageOperationError(f"Failed to get object info: {e}")
    
    async def get_object(self, key: str) -> bytes:
        """Download object content"""
        try:
            client = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Download to memory
            stream = BytesIO()
            
            async with client.download_stream(path) as download_stream:
                async for block in download_stream.iter_by_block():
                    stream.write(block)
            
            return stream.getvalue()
        
        except aioftp.StatusCodeError as e:
            if e.received_codes[-1].startswith("550"):  # File not found
                raise ObjectNotFoundError(key)
            raise StorageOperationError(f"FTP error: {e}")
        except Exception as e:
            logger.error(f"Failed to download object {key}: {e}")
            raise StorageOperationError(f"Failed to download object: {e}")
    
    async def get_object_stream(self, key: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Stream object content"""
        try:
            client = await self._ensure_connected()
            path = self._normalize_path(key)
            chunk_size = kwargs.get('chunk_size', 8192)
            
            async with client.download_stream(path) as download_stream:
                async for block in download_stream.iter_by_block(chunk_size):
                    yield block
        
        except aioftp.StatusCodeError as e:
            if e.received_codes[-1].startswith("550"):  # File not found
                raise ObjectNotFoundError(key)
            raise StorageOperationError(f"FTP error: {e}")
        except Exception as e:
            logger.error(f"Failed to stream object {key}: {e}")
            raise StorageOperationError(f"Failed to stream object: {e}")
    
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Upload object"""
        try:
            client = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Ensure parent directory exists
            parent_dir = str(PurePosixPath(path).parent)
            try:
                await client.make_directory(parent_dir, parents=True)
            except:
                # Directory might already exist
                pass
            
            # Upload from memory
            stream = BytesIO(data)
            
            async with client.upload_stream(path) as upload_stream:
                while True:
                    chunk = stream.read(8192)
                    if not chunk:
                        break
                    await upload_stream.write(chunk)
            
            # Get file info after upload
            return await self.get_object_info(key)
        
        except Exception as e:
            logger.error(f"Failed to upload object {key}: {e}")
            raise StorageOperationError(f"Failed to upload object: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete object"""
        try:
            client = await self._ensure_connected()
            path = self._normalize_path(key)
            
            await client.remove(path)
            return True
        
        except aioftp.StatusCodeError as e:
            if e.received_codes[-1].startswith("550"):  # File not found
                return False
            raise StorageOperationError(f"FTP error: {e}")
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise StorageOperationError(f"Failed to delete object: {e}")
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """List objects"""
        try:
            client = await self._ensure_connected()
            
            # Build search path
            if prefix:
                search_path = self._normalize_path(prefix)
            else:
                search_path = self.path_prefix
            
            objects = []
            
            # List directory
            listing = await client.list(search_path, recursive=delimiter is None)
            
            for item in listing:
                # Skip if continuation token is set and we haven't reached it
                if continuation_token and item[0].path <= continuation_token:
                    continue
                
                # Convert to StorageObject
                if item[1]["type"] == "file":
                    key = self._extract_key(str(item[0]))
                    
                    # Apply prefix filter
                    if prefix and not key.startswith(prefix):
                        continue
                    
                    obj = StorageObject(
                        key=key,
                        size=int(item[1].get("size", 0)),
                        last_modified=datetime.utcnow(),  # FTP doesn't provide this easily
                        etag=hashlib.md5(f"{key}_{item[1].get('size', 0)}".encode()).hexdigest(),
                        content_type=mimetypes.guess_type(key)[0],
                        metadata={"ftp_info": item[1]},
                        storage_class="standard"
                    )
                    objects.append(obj)
                    
                    if len(objects) >= max_keys:
                        break
            
            # Determine next token
            next_token = None
            if len(objects) >= max_keys:
                next_token = objects[-1].key
            
            return objects, next_token
        
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise StorageOperationError(f"Failed to list objects: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Copy object (using download/upload)"""
        try:
            # FTP doesn't support server-side copy, so download and re-upload
            data = await self.get_object(source_key)
            return await self.put_object(dest_key, data, metadata=metadata)
        
        except Exception as e:
            logger.error(f"Failed to copy object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Move object"""
        try:
            client = await self._ensure_connected()
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            # Ensure destination directory exists
            dest_dir = str(PurePosixPath(dest_path).parent)
            try:
                await client.make_directory(dest_dir, parents=True)
            except:
                pass
            
            # Rename file
            await client.rename(source_path, dest_path)
            
            return await self.get_object_info(dest_key)
        
        except Exception as e:
            logger.error(f"Failed to move object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to move object: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if object exists"""
        try:
            await self.get_object_info(key)
            return True
        except ObjectNotFoundError:
            return False
        except Exception:
            return False
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = "get",
        expires_in: int = 3600,
        **kwargs
    ) -> PresignedUrl:
        """Generate presigned URL (not supported for FTP)"""
        raise InvalidStorageOperationError(
            "Presigned URLs are not supported for FTP storage"
        )
    
    async def create_multipart_upload(
        self,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Create multipart upload (not supported)"""
        raise InvalidStorageOperationError(
            "Multipart uploads are not supported for FTP storage"
        )
    
    async def change_storage_tier(self, key: str, tier: StorageTier, **kwargs) -> StorageObject:
        """Change storage tier (not supported)"""
        raise InvalidStorageOperationError(
            "Storage tiers are not supported for FTP storage"
        )
    
    async def restore_object(self, key: str, days: int = 1, tier: str = "Standard", **kwargs) -> bool:
        """Restore object (not applicable)"""
        raise InvalidStorageOperationError(
            "Object restoration is not applicable for FTP storage"
        )
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage (not available for FTP)"""
        return {
            "used_bytes": -1,
            "total_bytes": -1,
            "usage_percentage": -1,
            "message": "Storage usage information not available for FTP"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            client = await self._ensure_connected()
            # Try to get current directory
            await client.get_current_directory()
            
            return {
                "status": "healthy",
                "message": f"FTP connection to {self.host}:{self.port} is active",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"FTP health check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }


class SFTPStorageDriver(StorageDriver):
    """SFTP storage driver implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SFTP driver"""
        if paramiko is None:
            raise ImportError("paramiko package is required for SFTP storage")
        
        self.config = config
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 22)
        self.username = config.get("username")
        self.password = config.get("password")
        self.key_filename = config.get("key_filename")
        self.key_password = config.get("key_password")
        self.path_prefix = config.get("path_prefix", "/")
        self.timeout = config.get("timeout", 30)
        self.auto_add_host_key = config.get("auto_add_host_key", False)
        
        # Connection objects
        self._ssh_client: Optional[SSHClient] = None
        self._sftp_client: Optional[SFTPClient] = None
        self._lock = asyncio.Lock()
        
        # Ensure path prefix ends with /
        if not self.path_prefix.endswith("/"):
            self.path_prefix += "/"
        
        # Validate authentication
        if not self.username:
            raise ValueError("Username is required for SFTP")
        if not self.password and not self.key_filename:
            raise ValueError("Either password or key_filename is required for SFTP")
    
    async def initialize(self) -> None:
        """Initialize the driver"""
        await self._ensure_connected()
    
    async def close(self) -> None:
        """Close the driver and cleanup resources"""
        async with self._lock:
            if self._sftp_client:
                self._sftp_client.close()
                self._sftp_client = None
            if self._ssh_client:
                self._ssh_client.close()
                self._ssh_client = None
    
    async def _ensure_connected(self) -> SFTPClient:
        """Ensure SFTP connection is established"""
        async with self._lock:
            if self._sftp_client is None:
                # Create SSH client
                self._ssh_client = SSHClient()
                
                if self.auto_add_host_key:
                    self._ssh_client.set_missing_host_key_policy(AutoAddPolicy())
                else:
                    self._ssh_client.load_system_host_keys()
                
                # Connect with password or key
                connect_kwargs = {
                    "hostname": self.host,
                    "port": self.port,
                    "username": self.username,
                    "timeout": self.timeout
                }
                
                if self.key_filename:
                    connect_kwargs["key_filename"] = self.key_filename
                    if self.key_password:
                        connect_kwargs["passphrase"] = self.key_password
                else:
                    connect_kwargs["password"] = self.password
                
                # Run connection in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: self._ssh_client.connect(**connect_kwargs)
                )
                
                # Open SFTP session
                self._sftp_client = self._ssh_client.open_sftp()
            
            return self._sftp_client
    
    def _normalize_path(self, key: str) -> str:
        """Normalize object key to SFTP path"""
        if key.startswith("/"):
            key = key[1:]
        
        # Combine with prefix
        full_path = PurePosixPath(self.path_prefix) / key
        return str(full_path)
    
    def _extract_key(self, sftp_path: str) -> str:
        """Extract object key from SFTP path"""
        if sftp_path.startswith(self.path_prefix):
            key = sftp_path[len(self.path_prefix):]
            if key.startswith("/"):
                key = key[1:]
            return key
        return sftp_path
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata"""
        try:
            sftp = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Get file stats
            loop = asyncio.get_event_loop()
            stat = await loop.run_in_executor(None, sftp.stat, path)
            
            return StorageObject(
                key=key,
                size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=hashlib.md5(f"{path}_{stat.st_size}_{stat.st_mtime}".encode()).hexdigest(),
                content_type=mimetypes.guess_type(key)[0],
                metadata={
                    "mode": oct(stat.st_mode),
                    "uid": stat.st_uid,
                    "gid": stat.st_gid,
                    "atime": datetime.fromtimestamp(stat.st_atime).isoformat()
                },
                storage_class="standard"
            )
        
        except FileNotFoundError:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to get object info for {key}: {e}")
            raise StorageOperationError(f"Failed to get object info: {e}")
    
    async def get_object(self, key: str) -> bytes:
        """Download object content"""
        try:
            sftp = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Download file
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, sftp.get, path, tmp_path)
                
                # Read content
                with open(tmp_path, 'rb') as f:
                    return f.read()
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
        
        except FileNotFoundError:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to download object {key}: {e}")
            raise StorageOperationError(f"Failed to download object: {e}")
    
    async def get_object_stream(self, key: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Stream object content"""
        try:
            sftp = await self._ensure_connected()
            path = self._normalize_path(key)
            chunk_size = kwargs.get('chunk_size', 32768)
            
            # Open remote file
            loop = asyncio.get_event_loop()
            
            # Download to temp file first (SFTP doesn't support true streaming)
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Download file
                await loop.run_in_executor(None, sftp.get, path, tmp_path)
                
                # Stream from temp file
                with open(tmp_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
        
        except FileNotFoundError:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to stream object {key}: {e}")
            raise StorageOperationError(f"Failed to stream object: {e}")
    
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Upload object"""
        try:
            sftp = await self._ensure_connected()
            path = self._normalize_path(key)
            
            # Ensure parent directory exists
            parent_dir = str(PurePosixPath(path).parent)
            loop = asyncio.get_event_loop()
            
            # Create parent directories
            try:
                await loop.run_in_executor(None, sftp.makedirs, parent_dir)
            except:
                # Directory might already exist
                pass
            
            # Write to temporary file first
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_path = tmp_file.name
            
            try:
                # Upload file
                await loop.run_in_executor(None, sftp.put, tmp_path, path)
                
                # Get file info after upload
                return await self.get_object_info(key)
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"Failed to upload object {key}: {e}")
            raise StorageOperationError(f"Failed to upload object: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete object"""
        try:
            sftp = await self._ensure_connected()
            path = self._normalize_path(key)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, sftp.remove, path)
            return True
        
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise StorageOperationError(f"Failed to delete object: {e}")
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """List objects"""
        try:
            sftp = await self._ensure_connected()
            
            # Build search path
            if prefix:
                search_path = self._normalize_path(prefix)
            else:
                search_path = self.path_prefix
            
            objects = []
            loop = asyncio.get_event_loop()
            
            # List directory recursively
            async def list_dir(path: str):
                try:
                    attrs_list = await loop.run_in_executor(None, sftp.listdir_attr, path)
                    
                    for attrs in attrs_list:
                        full_path = str(PurePosixPath(path) / attrs.filename)
                        
                        # Skip if continuation token is set and we haven't reached it
                        if continuation_token and full_path <= continuation_token:
                            continue
                        
                        # Process files
                        if not attrs.st_mode & 0o040000:  # Not a directory
                            key = self._extract_key(full_path)
                            
                            # Apply prefix filter
                            if prefix and not key.startswith(prefix):
                                continue
                            
                            obj = StorageObject(
                                key=key,
                                size=attrs.st_size,
                                last_modified=datetime.fromtimestamp(attrs.st_mtime),
                                etag=hashlib.md5(
                                    f"{full_path}_{attrs.st_size}_{attrs.st_mtime}".encode()
                                ).hexdigest(),
                                content_type=mimetypes.guess_type(key)[0],
                                metadata={
                                    "mode": oct(attrs.st_mode),
                                    "uid": attrs.st_uid,
                                    "gid": attrs.st_gid
                                },
                                storage_class="standard"
                            )
                            objects.append(obj)
                            
                            if len(objects) >= max_keys:
                                return
                        
                        # Recurse into directories if no delimiter
                        elif not delimiter and attrs.st_mode & 0o040000:
                            await list_dir(full_path)
                            if len(objects) >= max_keys:
                                return
                except:
                    # Skip directories we can't read
                    pass
            
            await list_dir(search_path)
            
            # Sort objects by key
            objects.sort(key=lambda x: x.key)
            
            # Determine next token
            next_token = None
            if len(objects) >= max_keys:
                next_token = objects[-1].key
            
            return objects[:max_keys], next_token
        
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise StorageOperationError(f"Failed to list objects: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Copy object (using download/upload)"""
        try:
            # SFTP doesn't support server-side copy, so download and re-upload
            data = await self.get_object(source_key)
            return await self.put_object(dest_key, data, metadata=metadata)
        
        except Exception as e:
            logger.error(f"Failed to copy object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Move object"""
        try:
            sftp = await self._ensure_connected()
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            # Ensure destination directory exists
            dest_dir = str(PurePosixPath(dest_path).parent)
            loop = asyncio.get_event_loop()
            
            try:
                await loop.run_in_executor(None, sftp.makedirs, dest_dir)
            except:
                pass
            
            # Rename file
            await loop.run_in_executor(None, sftp.rename, source_path, dest_path)
            
            return await self.get_object_info(dest_key)
        
        except Exception as e:
            logger.error(f"Failed to move object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to move object: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if object exists"""
        try:
            await self.get_object_info(key)
            return True
        except ObjectNotFoundError:
            return False
        except Exception:
            return False
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = "get",
        expires_in: int = 3600,
        **kwargs
    ) -> PresignedUrl:
        """Generate presigned URL (not supported for SFTP)"""
        raise InvalidStorageOperationError(
            "Presigned URLs are not supported for SFTP storage"
        )
    
    async def create_multipart_upload(
        self,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Create multipart upload (not supported)"""
        raise InvalidStorageOperationError(
            "Multipart uploads are not supported for SFTP storage"
        )
    
    async def change_storage_tier(self, key: str, tier: StorageTier, **kwargs) -> StorageObject:
        """Change storage tier (not supported)"""
        raise InvalidStorageOperationError(
            "Storage tiers are not supported for SFTP storage"
        )
    
    async def restore_object(self, key: str, days: int = 1, tier: str = "Standard", **kwargs) -> bool:
        """Restore object (not applicable)"""
        raise InvalidStorageOperationError(
            "Object restoration is not applicable for SFTP storage"
        )
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage"""
        try:
            sftp = await self._ensure_connected()
            loop = asyncio.get_event_loop()
            
            # Try to get disk usage using statvfs
            try:
                vfs = await loop.run_in_executor(None, sftp.statvfs, self.path_prefix)
                
                total = vfs.f_blocks * vfs.f_frsize
                available = vfs.f_bavail * vfs.f_frsize
                used = total - available
                
                return {
                    "used_bytes": used,
                    "total_bytes": total,
                    "available_bytes": available,
                    "usage_percentage": (used / total * 100) if total > 0 else 0
                }
            except:
                # statvfs might not be supported
                return {
                    "used_bytes": -1,
                    "total_bytes": -1,
                    "usage_percentage": -1,
                    "message": "Storage usage information not available"
                }
        
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {
                "used_bytes": -1,
                "total_bytes": -1,
                "usage_percentage": -1,
                "message": f"Failed to get storage usage: {e}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            sftp = await self._ensure_connected()
            loop = asyncio.get_event_loop()
            
            # Try to list current directory
            await loop.run_in_executor(None, sftp.listdir, ".")
            
            return {
                "status": "healthy",
                "message": f"SFTP connection to {self.host}:{self.port} is active",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"SFTP health check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }