"""
Local Filesystem Storage Driver

This module implements the storage driver for local filesystem storage.
"""

import os
import shutil
import asyncio
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import (
    Optional, List, Dict, Any, AsyncIterator, BinaryIO,
    Union, Tuple, Callable
)
from datetime import datetime
import hashlib
import mimetypes
from urllib.parse import quote, unquote

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota, UploadProgress,
    ObjectNotFoundError, StorageQuotaExceededError,
    StoragePermissionError, InvalidStorageOperationError
)


class LocalStorageDriver(StorageDriver):
    """Local filesystem storage driver implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.root_path = Path(config.get("root", "/var/mams/storage"))
        self.permissions = config.get("permissions", 0o755)
        self.chunk_size = config.get("chunk_size", 8192)
        
    async def initialize(self) -> None:
        """Initialize the storage driver"""
        try:
            # Ensure root directory exists
            await asyncio.to_thread(self.root_path.mkdir, parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.root_path / ".write_test"
            async with aiofiles.open(test_file, 'w') as f:
                await f.write("test")
            await aiofiles.os.remove(test_file)
            
            self._initialized = True
        except PermissionError as e:
            raise StoragePermissionError(f"No write permission to {self.root_path}: {e}")
        except Exception as e:
            raise Exception(f"Failed to initialize local storage: {e}")
    
    async def close(self) -> None:
        """Close connections and cleanup resources"""
        self._initialized = False
    
    def _get_absolute_path(self, key: str) -> Path:
        """Get absolute path for a key"""
        # Remove leading slashes and normalize
        clean_key = key.lstrip('/')
        path = self.root_path / clean_key
        
        # Ensure path is within root directory (prevent directory traversal)
        try:
            path = path.resolve()
            path.relative_to(self.root_path.resolve())
        except ValueError:
            raise InvalidStorageOperationError(f"Invalid key: {key}")
        
        return path
    
    async def exists(self, key: str) -> bool:
        """Check if an object exists"""
        path = self._get_absolute_path(key)
        return await asyncio.to_thread(path.exists)
    
    async def get_object(self, key: str) -> bytes:
        """Retrieve an object"""
        path = self._get_absolute_path(key)
        
        if not await asyncio.to_thread(path.exists):
            raise ObjectNotFoundError(key)
        
        if await asyncio.to_thread(path.is_dir):
            raise InvalidStorageOperationError(f"Key points to directory: {key}")
        
        try:
            async with aiofiles.open(path, 'rb') as f:
                return await f.read()
        except PermissionError:
            raise StoragePermissionError(f"No read permission for {key}")
        except Exception as e:
            raise Exception(f"Failed to read object: {e}")
    
    async def get_object_stream(
        self, 
        key: str, 
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Stream an object in chunks"""
        path = self._get_absolute_path(key)
        
        if not await asyncio.to_thread(path.exists):
            raise ObjectNotFoundError(key)
        
        if await asyncio.to_thread(path.is_dir):
            raise InvalidStorageOperationError(f"Key points to directory: {key}")
        
        try:
            async with aiofiles.open(path, 'rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except PermissionError:
            raise StoragePermissionError(f"No read permission for {key}")
        except Exception as e:
            raise Exception(f"Failed to stream object: {e}")
    
    async def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> StorageObject:
        """Store an object"""
        path = self._get_absolute_path(key)
        
        # Create parent directory if needed
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        
        # Write data
        try:
            if isinstance(data, bytes):
                async with aiofiles.open(path, 'wb') as f:
                    await f.write(data)
                size = len(data)
            else:
                # File-like object
                data.seek(0)
                content = data.read()
                async with aiofiles.open(path, 'wb') as f:
                    await f.write(content)
                size = len(content)
            
            # Set permissions
            await asyncio.to_thread(os.chmod, path, self.permissions)
            
            # Get file stats
            stat = await asyncio.to_thread(path.stat)
            
            # Store metadata as extended attributes if supported
            if metadata:
                await self._set_metadata(path, metadata)
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(str(path))
            
            return StorageObject(
                key=key,
                size=size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=await self._calculate_etag(path),
                content_type=content_type,
                metadata=metadata
            )
        except PermissionError:
            raise StoragePermissionError(f"No write permission for {key}")
        except Exception as e:
            raise Exception(f"Failed to store object: {e}")
    
    async def put_object_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> StorageObject:
        """Store an object from a stream"""
        path = self._get_absolute_path(key)
        
        # Create parent directory if needed
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        
        bytes_written = 0
        start_time = datetime.now()
        
        try:
            async with aiofiles.open(path, 'wb') as f:
                async for chunk in stream:
                    await f.write(chunk)
                    bytes_written += len(chunk)
                    
                    # Report progress if callback provided
                    if progress_callback and size:
                        progress = UploadProgress(
                            bytes_uploaded=bytes_written,
                            total_bytes=size,
                            start_time=start_time,
                            current_time=datetime.now()
                        )
                        await asyncio.to_thread(progress_callback, progress)
            
            # Set permissions
            await asyncio.to_thread(os.chmod, path, self.permissions)
            
            # Get file stats
            stat = await asyncio.to_thread(path.stat)
            
            # Store metadata
            if metadata:
                await self._set_metadata(path, metadata)
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(str(path))
            
            return StorageObject(
                key=key,
                size=bytes_written,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=await self._calculate_etag(path),
                content_type=content_type,
                metadata=metadata
            )
        except PermissionError:
            raise StoragePermissionError(f"No write permission for {key}")
        except Exception as e:
            # Clean up partial file
            if await asyncio.to_thread(path.exists):
                await aiofiles.os.remove(path)
            raise Exception(f"Failed to store object stream: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object"""
        path = self._get_absolute_path(key)
        
        if not await asyncio.to_thread(path.exists):
            return False
        
        try:
            if await asyncio.to_thread(path.is_dir):
                await asyncio.to_thread(shutil.rmtree, path)
            else:
                await aiofiles.os.remove(path)
            return True
        except PermissionError:
            raise StoragePermissionError(f"No delete permission for {key}")
        except Exception as e:
            raise Exception(f"Failed to delete object: {e}")
    
    async def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple objects"""
        results = {}
        for key in keys:
            try:
                results[key] = await self.delete_object(key)
            except Exception:
                results[key] = False
        return results
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """List objects with optional prefix"""
        base_path = self.root_path
        if prefix:
            base_path = self._get_absolute_path(prefix)
        
        objects = []
        dirs_seen = set()
        
        # Handle continuation token (simple implementation using offset)
        offset = 0
        if continuation_token:
            try:
                offset = int(continuation_token)
            except ValueError:
                offset = 0
        
        count = 0
        total_scanned = 0
        
        try:
            # Walk directory tree
            for root, dirs, files in os.walk(base_path):
                root_path = Path(root)
                
                # Calculate relative path
                try:
                    rel_path = root_path.relative_to(self.root_path)
                except ValueError:
                    continue
                
                # Handle delimiter (directory mode)
                if delimiter and prefix:
                    prefix_path = Path(prefix)
                    try:
                        rel_to_prefix = root_path.relative_to(self.root_path / prefix_path)
                        # If this path contains the delimiter, only include the directory
                        parts = str(rel_to_prefix).split(delimiter)
                        if len(parts) > 1:
                            dir_key = str(prefix_path / parts[0]) + delimiter
                            if dir_key not in dirs_seen:
                                dirs_seen.add(dir_key)
                                if total_scanned >= offset:
                                    objects.append(StorageObject(
                                        key=dir_key,
                                        size=0,
                                        last_modified=datetime.fromtimestamp(root_path.stat().st_mtime),
                                        content_type="application/x-directory"
                                    ))
                                    count += 1
                                total_scanned += 1
                            continue
                    except ValueError:
                        pass
                
                # Add files
                for filename in sorted(files):
                    if count >= max_keys:
                        break
                    
                    file_path = root_path / filename
                    key = str(rel_path / filename) if str(rel_path) != "." else filename
                    
                    # Skip if before offset
                    if total_scanned < offset:
                        total_scanned += 1
                        continue
                    
                    # Skip if doesn't match prefix
                    if prefix and not key.startswith(prefix):
                        continue
                    
                    stat = file_path.stat()
                    content_type, _ = mimetypes.guess_type(filename)
                    
                    objects.append(StorageObject(
                        key=key,
                        size=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        etag=await self._calculate_etag(file_path),
                        content_type=content_type
                    ))
                    count += 1
                    total_scanned += 1
                
                if count >= max_keys:
                    break
            
            # Determine if there are more results
            next_token = None
            if count >= max_keys:
                # Check if there are more files
                remaining = False
                for _ in os.walk(base_path):
                    remaining = True
                    break
                if remaining:
                    next_token = str(offset + count)
            
            return objects, next_token
            
        except Exception as e:
            raise Exception(f"Failed to list objects: {e}")
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata without retrieving content"""
        path = self._get_absolute_path(key)
        
        if not await asyncio.to_thread(path.exists):
            raise ObjectNotFoundError(key)
        
        try:
            stat = await asyncio.to_thread(path.stat)
            content_type, _ = mimetypes.guess_type(str(path))
            metadata = await self._get_metadata(path)
            
            return StorageObject(
                key=key,
                size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=await self._calculate_etag(path),
                content_type=content_type,
                metadata=metadata
            )
        except Exception as e:
            raise Exception(f"Failed to get object info: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Copy an object within the same storage"""
        source_path = self._get_absolute_path(source_key)
        dest_path = self._get_absolute_path(dest_key)
        
        if not await asyncio.to_thread(source_path.exists):
            raise ObjectNotFoundError(source_key)
        
        try:
            # Create parent directory if needed
            await asyncio.to_thread(dest_path.parent.mkdir, parents=True, exist_ok=True)
            
            # Copy file
            if await asyncio.to_thread(source_path.is_dir):
                await asyncio.to_thread(shutil.copytree, source_path, dest_path)
            else:
                await asyncio.to_thread(shutil.copy2, source_path, dest_path)
            
            # Update metadata if provided
            if metadata:
                await self._set_metadata(dest_path, metadata)
            else:
                # Copy metadata from source
                source_metadata = await self._get_metadata(source_path)
                if source_metadata:
                    await self._set_metadata(dest_path, source_metadata)
            
            return await self.get_object_info(dest_key)
            
        except PermissionError:
            raise StoragePermissionError(f"No permission to copy {source_key} to {dest_key}")
        except Exception as e:
            raise Exception(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Move/rename an object"""
        source_path = self._get_absolute_path(source_key)
        dest_path = self._get_absolute_path(dest_key)
        
        if not await asyncio.to_thread(source_path.exists):
            raise ObjectNotFoundError(source_key)
        
        try:
            # Create parent directory if needed
            await asyncio.to_thread(dest_path.parent.mkdir, parents=True, exist_ok=True)
            
            # Move file
            await asyncio.to_thread(shutil.move, str(source_path), str(dest_path))
            
            # Update metadata if provided
            if metadata:
                await self._set_metadata(dest_path, metadata)
            
            return await self.get_object_info(dest_key)
            
        except PermissionError:
            raise StoragePermissionError(f"No permission to move {source_key} to {dest_key}")
        except Exception as e:
            raise Exception(f"Failed to move object: {e}")
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = 'get',
        expires_in: int = 3600,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a presigned URL for direct access"""
        # For local storage, return a file:// URL
        path = self._get_absolute_path(key)
        
        if not await asyncio.to_thread(path.exists):
            raise ObjectNotFoundError(key)
        
        # Return file URL (note: this only works for local access)
        return f"file://{path.absolute()}"
    
    async def create_multipart_upload(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Initiate a multipart upload"""
        # For local storage, we'll use a simple implementation
        import uuid
        upload_id = str(uuid.uuid4())
        
        # Create temporary directory for parts
        temp_dir = self.root_path / ".multipart" / upload_id
        await asyncio.to_thread(temp_dir.mkdir, parents=True, exist_ok=True)
        
        # Store metadata for later
        if metadata or content_type:
            meta_file = temp_dir / "metadata.json"
            import json
            meta_data = {
                "key": key,
                "metadata": metadata,
                "content_type": content_type
            }
            async with aiofiles.open(meta_file, 'w') as f:
                await f.write(json.dumps(meta_data))
        
        return upload_id
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> Dict[str, Any]:
        """Upload a part in a multipart upload"""
        temp_dir = self.root_path / ".multipart" / upload_id
        
        if not await asyncio.to_thread(temp_dir.exists):
            raise InvalidStorageOperationError(f"Invalid upload ID: {upload_id}")
        
        # Write part to temporary file
        part_file = temp_dir / f"part_{part_number:05d}"
        async with aiofiles.open(part_file, 'wb') as f:
            await f.write(data)
        
        # Calculate ETag
        etag = hashlib.md5(data).hexdigest()
        
        return {
            "part_number": part_number,
            "etag": etag,
            "size": len(data)
        }
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> StorageObject:
        """Complete a multipart upload"""
        temp_dir = self.root_path / ".multipart" / upload_id
        
        if not await asyncio.to_thread(temp_dir.exists):
            raise InvalidStorageOperationError(f"Invalid upload ID: {upload_id}")
        
        # Sort parts by part number
        parts = sorted(parts, key=lambda x: x["part_number"])
        
        # Combine parts
        path = self._get_absolute_path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        
        async with aiofiles.open(path, 'wb') as out_file:
            for part in parts:
                part_file = temp_dir / f"part_{part['part_number']:05d}"
                if not await asyncio.to_thread(part_file.exists):
                    raise InvalidStorageOperationError(
                        f"Missing part {part['part_number']}"
                    )
                
                async with aiofiles.open(part_file, 'rb') as in_file:
                    data = await in_file.read()
                    await out_file.write(data)
        
        # Load metadata if exists
        metadata = None
        content_type = None
        meta_file = temp_dir / "metadata.json"
        if await asyncio.to_thread(meta_file.exists):
            import json
            async with aiofiles.open(meta_file, 'r') as f:
                meta_data = json.loads(await f.read())
                metadata = meta_data.get("metadata")
                content_type = meta_data.get("content_type")
        
        # Set metadata
        if metadata:
            await self._set_metadata(path, metadata)
        
        # Clean up temporary files
        await asyncio.to_thread(shutil.rmtree, temp_dir)
        
        return await self.get_object_info(key)
    
    async def abort_multipart_upload(
        self,
        key: str,
        upload_id: str
    ) -> None:
        """Abort a multipart upload"""
        temp_dir = self.root_path / ".multipart" / upload_id
        
        if await asyncio.to_thread(temp_dir.exists):
            await asyncio.to_thread(shutil.rmtree, temp_dir)
    
    async def get_quota(self) -> StorageQuota:
        """Get storage quota information"""
        try:
            # Get disk usage statistics
            stat = await asyncio.to_thread(shutil.disk_usage, self.root_path)
            
            # Count files
            file_count = 0
            for _, _, files in os.walk(self.root_path):
                file_count += len(files)
            
            return StorageQuota(
                total_bytes=stat.total,
                used_bytes=stat.used,
                available_bytes=stat.free,
                file_count=file_count
            )
        except Exception as e:
            raise Exception(f"Failed to get quota: {e}")
    
    async def _calculate_etag(self, path: Path) -> str:
        """Calculate ETag for a file"""
        # For small files, use MD5 of content
        # For large files, use modification time and size
        stat = await asyncio.to_thread(path.stat)
        
        if stat.st_size < 10 * 1024 * 1024:  # 10MB
            hasher = hashlib.md5()
            async with aiofiles.open(path, 'rb') as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        else:
            # Use size and mtime for large files
            return f"{stat.st_size}-{int(stat.st_mtime)}"
    
    async def _get_metadata(self, path: Path) -> Optional[Dict[str, str]]:
        """Get metadata for a file (stub implementation)"""
        # In a real implementation, this would use extended attributes
        # or a separate metadata store
        return None
    
    async def _set_metadata(self, path: Path, metadata: Dict[str, str]) -> None:
        """Set metadata for a file (stub implementation)"""
        # In a real implementation, this would use extended attributes
        # or a separate metadata store
        pass