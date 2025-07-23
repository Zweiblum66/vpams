"""
Dropbox Storage Driver

This module implements the Dropbox storage driver for the storage abstraction layer.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from pathlib import Path
import mimetypes
import hashlib
import io

try:
    import dropbox
    from dropbox.exceptions import AuthError, ApiError
    from dropbox.files import WriteMode, SearchMatchType
except ImportError:
    dropbox = None
    AuthError = Exception
    ApiError = Exception
    WriteMode = None
    SearchMatchType = None

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageTier, PresignedUrl,
    ObjectNotFoundError, StorageQuotaExceededError, StoragePermissionError,
    InvalidStorageOperationError, StorageOperationError
)


logger = logging.getLogger(__name__)


class DropboxStorageDriver(StorageDriver):
    """Dropbox storage driver implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Dropbox driver"""
        if dropbox is None:
            raise ImportError("dropbox package is required for Dropbox storage")
        
        self.config = config
        self.access_token = config.get("access_token")
        self.app_key = config.get("app_key")
        self.app_secret = config.get("app_secret")
        self.refresh_token = config.get("refresh_token")
        
        if not self.access_token:
            raise ValueError("Dropbox access_token is required")
        
        # Initialize Dropbox client
        self.client = dropbox.Dropbox(self.access_token)
        
        # Configuration
        self.chunk_size = config.get("chunk_size", 8 * 1024 * 1024)  # 8MB
        self.upload_session_timeout = config.get("upload_session_timeout", 3600)
        self.max_file_size = config.get("max_file_size", 150 * 1024 * 1024 * 1024)  # 150GB
        
        # Path prefix for all operations
        self.path_prefix = config.get("path_prefix", "/mams")
        if not self.path_prefix.startswith("/"):
            self.path_prefix = "/" + self.path_prefix
    
    def _normalize_path(self, key: str) -> str:
        """Normalize object key to Dropbox path"""
        if not key.startswith("/"):
            key = "/" + key
        
        # Combine with prefix
        full_path = self.path_prefix + key
        
        # Normalize path
        return str(Path(full_path).as_posix())
    
    def _extract_key(self, dropbox_path: str) -> str:
        """Extract object key from Dropbox path"""
        if dropbox_path.startswith(self.path_prefix):
            key = dropbox_path[len(self.path_prefix):]
            if key.startswith("/"):
                key = key[1:]
            return key
        return dropbox_path
    
    def _metadata_to_storage_object(self, metadata) -> StorageObject:
        """Convert Dropbox metadata to StorageObject"""
        key = self._extract_key(metadata.path_display or metadata.path_lower)
        
        # Handle file metadata
        if hasattr(metadata, 'size'):
            size = metadata.size
            last_modified = metadata.server_modified or metadata.client_modified
            content_hash = getattr(metadata, 'content_hash', None)
        else:
            # Folder metadata
            size = 0
            last_modified = datetime.utcnow()
            content_hash = None
        
        return StorageObject(
            key=key,
            size=size,
            last_modified=last_modified,
            etag=content_hash,
            content_type=mimetypes.guess_type(key)[0],
            metadata={
                "dropbox_path": metadata.path_display or metadata.path_lower,
                "dropbox_id": getattr(metadata, 'id', None),
                "is_folder": hasattr(metadata, 'entries')
            },
            storage_class="standard",  # Dropbox doesn't have storage classes
            version_id=getattr(metadata, 'rev', None)
        )
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata"""
        try:
            path = self._normalize_path(key)
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self.client.files_get_metadata, path
            )
            return self._metadata_to_storage_object(metadata)
        
        except ApiError as e:
            if e.error.is_path_not_found():
                raise ObjectNotFoundError(key)
            elif e.error.is_path_malformed():
                raise InvalidStorageOperationError(f"Invalid path: {key}")
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
        except Exception as e:
            logger.error(f"Failed to get object info for {key}: {e}")
            raise StorageOperationError(f"Failed to get object info: {e}")
    
    async def get_object(self, key: str) -> bytes:
        """Download object content"""
        try:
            path = self._normalize_path(key)
            _, response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.files_download, path
            )
            return response.content
        
        except ApiError as e:
            if e.error.is_path_not_found():
                raise ObjectNotFoundError(key)
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
        except Exception as e:
            logger.error(f"Failed to download object {key}: {e}")
            raise StorageOperationError(f"Failed to download object: {e}")
    
    async def get_object_stream(self, key: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Stream object content"""
        try:
            # Dropbox doesn't support range requests directly, so we download in chunks
            path = self._normalize_path(key)
            
            # Get file info first to determine size
            obj_info = await self.get_object_info(key)
            file_size = obj_info.size
            
            # Download in chunks
            chunk_size = kwargs.get('chunk_size', self.chunk_size)
            offset = 0
            
            while offset < file_size:
                # Calculate end offset for this chunk
                end_offset = min(offset + chunk_size - 1, file_size - 1)
                
                # Download chunk (Dropbox doesn't support range requests well)
                # For now, download the whole file and yield chunks
                if offset == 0:
                    data = await self.get_object(key)
                    
                    # Yield in chunks
                    for i in range(0, len(data), chunk_size):
                        yield data[i:i + chunk_size]
                    break
                
                offset = end_offset + 1
        
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
            path = self._normalize_path(key)
            
            # Determine upload method based on file size
            if len(data) <= self.chunk_size:
                # Simple upload for small files
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.client.files_upload(
                        data, 
                        path, 
                        mode=WriteMode.overwrite,
                        autorename=False
                    )
                )
            else:
                # Use upload session for large files
                response = await self._upload_large_file(path, data)
            
            return self._metadata_to_storage_object(response)
        
        except ApiError as e:
            if e.error.is_insufficient_space():
                raise StorageQuotaExceededError("Dropbox storage quota exceeded")
            elif e.error.is_path_malformed():
                raise InvalidStorageOperationError(f"Invalid path: {key}")
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
        except Exception as e:
            logger.error(f"Failed to upload object {key}: {e}")
            raise StorageOperationError(f"Failed to upload object: {e}")
    
    async def _upload_large_file(self, path: str, data: bytes):
        """Upload large file using upload session"""
        def _upload_session():
            # Start upload session
            session_start_result = self.client.files_upload_session_start(
                data[:self.chunk_size]
            )
            session_id = session_start_result.session_id
            
            # Upload remaining chunks
            offset = self.chunk_size
            while offset < len(data):
                chunk_size = min(self.chunk_size, len(data) - offset)
                chunk = data[offset:offset + chunk_size]
                
                if offset + chunk_size < len(data):
                    # Append chunk
                    self.client.files_upload_session_append_v2(
                        chunk,
                        dropbox.files.UploadSessionCursor(session_id, offset)
                    )
                else:
                    # Finish upload
                    return self.client.files_upload_session_finish(
                        chunk,
                        dropbox.files.UploadSessionCursor(session_id, offset),
                        dropbox.files.CommitInfo(path, mode=WriteMode.overwrite)
                    )
                
                offset += chunk_size
        
        return await asyncio.get_event_loop().run_in_executor(None, _upload_session)
    
    async def delete_object(self, key: str) -> bool:
        """Delete object"""
        try:
            path = self._normalize_path(key)
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.files_delete_v2, path
            )
            return True
        
        except ApiError as e:
            if e.error.is_path_not_found():
                return False
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
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
            # Build search path
            search_path = self.path_prefix
            if prefix:
                search_path = self._normalize_path(prefix)
            
            objects = []
            has_more = True
            cursor = continuation_token
            
            while has_more and len(objects) < max_keys:
                if cursor:
                    # Continue listing
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.client.files_list_folder_continue, cursor
                    )
                else:
                    # Start listing
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.client.files_list_folder(
                            search_path, 
                            recursive=delimiter is None,
                            limit=min(max_keys - len(objects), 2000)
                        )
                    )
                
                # Process entries
                for entry in result.entries:
                    if hasattr(entry, 'size'):  # File entry
                        obj = self._metadata_to_storage_object(entry)
                        
                        # Apply prefix filter if specified
                        if not prefix or obj.key.startswith(prefix):
                            objects.append(obj)
                        
                        if len(objects) >= max_keys:
                            break
                
                # Check if there are more results
                has_more = result.has_more
                cursor = result.cursor if has_more else None
            
            next_token = cursor if has_more and len(objects) >= max_keys else None
            return objects, next_token
        
        except ApiError as e:
            if e.error.is_path_not_found():
                return [], None
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
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
        """Copy object"""
        try:
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.files_copy_v2, source_path, dest_path
            )
            
            return self._metadata_to_storage_object(response.metadata)
        
        except ApiError as e:
            if e.error.is_from_path_not_found():
                raise ObjectNotFoundError(source_key)
            elif e.error.is_to_path_malformed():
                raise InvalidStorageOperationError(f"Invalid destination path: {dest_key}")
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
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
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.files_move_v2, source_path, dest_path
            )
            
            return self._metadata_to_storage_object(response.metadata)
        
        except ApiError as e:
            if e.error.is_from_path_not_found():
                raise ObjectNotFoundError(source_key)
            elif e.error.is_to_path_malformed():
                raise InvalidStorageOperationError(f"Invalid destination path: {dest_key}")
            else:
                raise StorageOperationError(f"Dropbox API error: {e}")
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
        """Generate presigned URL (Dropbox shared link)"""
        try:
            path = self._normalize_path(key)
            
            if operation == "get":
                # Create a shared link
                try:
                    # Try to get existing shared link first
                    links = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.client.sharing_list_shared_links(path=path)
                    )
                    
                    if links.links:
                        # Use existing link
                        shared_link = links.links[0]
                    else:
                        # Create new shared link
                        shared_link = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self.client.sharing_create_shared_link_with_settings(
                                path,
                                dropbox.sharing.SharedLinkSettings(
                                    expires=datetime.utcnow() + timedelta(seconds=expires_in)
                                )
                            )
                        )
                    
                    # Convert to direct download link
                    url = shared_link.url.replace('dropbox.com', 'dl.dropboxusercontent.com')
                    if url.endswith('?dl=0'):
                        url = url.replace('?dl=0', '?dl=1')
                    
                    return PresignedUrl(
                        url=url,
                        expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
                    )
                
                except Exception as e:
                    # Fallback: return API download URL (requires auth)
                    return PresignedUrl(
                        url=f"https://content.dropboxapi.com/2/files/download",
                        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                        headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "Dropbox-API-Arg": f'{{"path": "{path}"}}'
                        }
                    )
            else:
                raise InvalidStorageOperationError(
                    f"Presigned URLs for operation '{operation}' not supported by Dropbox"
                )
        
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageOperationError(f"Failed to generate presigned URL: {e}")
    
    async def create_multipart_upload(
        self,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Create multipart upload session"""
        try:
            path = self._normalize_path(key)
            
            # Start upload session
            session_start_result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.files_upload_session_start(b"")
            )
            
            # Store session info
            session_id = session_start_result.session_id
            
            # Return session ID as upload ID
            return f"dropbox_{session_id}_{hashlib.md5(path.encode()).hexdigest()}"
        
        except Exception as e:
            logger.error(f"Failed to create multipart upload for {key}: {e}")
            raise StorageOperationError(f"Failed to create multipart upload: {e}")
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes,
        **kwargs
    ) -> Dict[str, Any]:
        """Upload part for multipart upload"""
        try:
            # Extract session ID from upload ID
            if not upload_id.startswith("dropbox_"):
                raise InvalidStorageOperationError("Invalid upload ID format")
            
            session_id = upload_id.split("_")[1]
            
            # Calculate offset (parts are 1-indexed)
            offset = (part_number - 1) * len(data)
            
            # Upload part
            if part_number == 1:
                # First part - start session if not already started
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.files_upload_session_append_v2(
                        data,
                        dropbox.files.UploadSessionCursor(session_id, 0)
                    )
                )
            else:
                # Subsequent parts
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.files_upload_session_append_v2(
                        data,
                        dropbox.files.UploadSessionCursor(session_id, offset)
                    )
                )
            
            # Return part info
            etag = hashlib.md5(data).hexdigest()
            return {
                "PartNumber": part_number,
                "ETag": etag,
                "Size": len(data)
            }
        
        except Exception as e:
            logger.error(f"Failed to upload part {part_number} for {key}: {e}")
            raise StorageOperationError(f"Failed to upload part: {e}")
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]],
        **kwargs
    ) -> StorageObject:
        """Complete multipart upload"""
        try:
            # Extract session ID from upload ID
            if not upload_id.startswith("dropbox_"):
                raise InvalidStorageOperationError("Invalid upload ID format")
            
            session_id = upload_id.split("_")[1]
            path = self._normalize_path(key)
            
            # Calculate total offset
            total_size = sum(part.get("Size", 0) for part in parts)
            
            # Complete upload
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.files_upload_session_finish(
                    b"",  # No data for finish call
                    dropbox.files.UploadSessionCursor(session_id, total_size),
                    dropbox.files.CommitInfo(path, mode=WriteMode.overwrite)
                )
            )
            
            return self._metadata_to_storage_object(response)
        
        except Exception as e:
            logger.error(f"Failed to complete multipart upload for {key}: {e}")
            raise StorageOperationError(f"Failed to complete multipart upload: {e}")
    
    async def abort_multipart_upload(self, key: str, upload_id: str, **kwargs) -> None:
        """Abort multipart upload"""
        # Dropbox upload sessions automatically expire, so no explicit abort needed
        logger.info(f"Dropbox upload session {upload_id} will expire automatically")
    
    async def change_storage_tier(self, key: str, tier: StorageTier, **kwargs) -> StorageObject:
        """Change storage tier (not supported by Dropbox)"""
        raise InvalidStorageOperationError("Storage tier changes not supported by Dropbox")
    
    async def restore_object(self, key: str, days: int = 1, tier: str = "Standard", **kwargs) -> bool:
        """Restore object (not applicable for Dropbox)"""
        raise InvalidStorageOperationError("Object restoration not applicable for Dropbox")
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage information"""
        try:
            space_usage = await asyncio.get_event_loop().run_in_executor(
                None, self.client.users_get_space_usage
            )
            
            return {
                "used_bytes": space_usage.used,
                "allocated_bytes": space_usage.allocation.get_individual().allocated,
                "usage_percentage": (space_usage.used / space_usage.allocation.get_individual().allocated) * 100
                if space_usage.allocation.get_individual().allocated > 0 else 0
            }
        
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            raise StorageOperationError(f"Failed to get storage usage: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Test API access
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.users_get_current_account
            )
            
            return {
                "status": "healthy",
                "message": "Dropbox API accessible",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except AuthError:
            return {
                "status": "unhealthy",
                "message": "Authentication failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }