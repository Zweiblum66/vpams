"""
Google Cloud Storage Driver

This module implements the storage driver for Google Cloud Storage (GCS).
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, AsyncIterator, Union, BinaryIO, Tuple, Callable
from urllib.parse import urlparse, quote
import hashlib
import base64
import aiofiles

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, Conflict
    from google.auth import default
    from google.oauth2 import service_account
    from google.api_core import retry
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota, UploadProgress,
    StorageTier, StorageType, ObjectNotFoundError,
    StoragePermissionError, InvalidStorageOperationError,
    StorageQuotaExceededError, StorageOperationError
)


logger = logging.getLogger(__name__)


class GCSStorageDriver(StorageDriver):
    """Google Cloud Storage implementation of StorageDriver"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Google Cloud Storage driver"""
        super().__init__(config)
        
        if not GCS_AVAILABLE:
            raise ImportError(
                "Google Cloud SDK not installed. Install with: pip install google-cloud-storage"
            )
        
        # GCS configuration
        self.project_id = config.get("project_id")
        self.bucket_name = config.get("bucket_name", "mams-storage")
        self.credentials_path = config.get("credentials_path")
        self.credentials_json = config.get("credentials_json")
        self.location = config.get("location", "US")
        self.storage_class = config.get("storage_class", "STANDARD")
        
        # Tier mapping
        self.tier_mapping = {
            StorageTier.HOT: "STANDARD",
            StorageTier.WARM: "NEARLINE",
            StorageTier.COLD: "COLDLINE",
            StorageTier.ARCHIVE: "ARCHIVE"
        }
        
        # Driver configuration
        self.enable_versioning = config.get("enable_versioning", True)
        self.enable_lifecycle = config.get("enable_lifecycle", True)
        self.public_access = config.get("public_access", False)
        
        # Clients
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
        
        # Multipart upload tracking
        self._multipart_uploads: Dict[str, Dict[str, Any]] = {}
    
    @property
    def storage_type(self) -> StorageType:
        """Return the storage type"""
        return StorageType.OBJECT
    
    async def initialize(self) -> None:
        """Initialize Google Cloud Storage connection"""
        try:
            # Create credentials
            if self.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
            elif self.credentials_json:
                credentials_dict = json.loads(self.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict
                )
            else:
                # Use default credentials (from environment)
                credentials, project = default()
                if not self.project_id:
                    self.project_id = project
            
            # Create storage client
            self._client = storage.Client(
                project=self.project_id,
                credentials=credentials if 'credentials' in locals() else None
            )
            
            # Get or create bucket
            try:
                self._bucket = self._client.get_bucket(self.bucket_name)
                logger.info(f"Using existing GCS bucket: {self.bucket_name}")
            except NotFound:
                self._bucket = self._client.create_bucket(
                    self.bucket_name,
                    location=self.location
                )
                logger.info(f"Created GCS bucket: {self.bucket_name}")
            
            # Configure bucket
            await self._configure_bucket()
            
            self._initialized = True
            logger.info("Google Cloud Storage driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage: {e}")
            raise StorageOperationError(f"GCS initialization failed: {e}")
    
    async def _configure_bucket(self) -> None:
        """Configure bucket settings"""
        try:
            # Enable versioning if requested
            if self.enable_versioning:
                self._bucket.versioning_enabled = True
            
            # Set default storage class
            self._bucket.storage_class = self.storage_class
            
            # Configure lifecycle rules if enabled
            if self.enable_lifecycle:
                # Example lifecycle rules
                self._bucket.lifecycle_rules = [
                    {
                        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
                        "condition": {"age": 30}
                    },
                    {
                        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
                        "condition": {"age": 90}
                    },
                    {
                        "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
                        "condition": {"age": 365}
                    }
                ]
            
            # Update bucket configuration
            self._bucket.patch()
            
        except Exception as e:
            logger.warning(f"Failed to configure bucket: {e}")
    
    async def close(self) -> None:
        """Close Google Cloud Storage connection"""
        # GCS client doesn't need explicit closing
        self._initialized = False
        logger.info("Google Cloud Storage driver closed")
    
    async def exists(self, key: str) -> bool:
        """Check if an object exists"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            return await asyncio.get_event_loop().run_in_executor(
                None, blob.exists
            )
        except Exception as e:
            logger.error(f"Failed to check existence of {key}: {e}")
            return False
    
    async def get_object(self, key: str) -> bytes:
        """Retrieve an object"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Download blob content
            content = await asyncio.get_event_loop().run_in_executor(
                None, blob.download_as_bytes
            )
            
            return content
            
        except NotFound:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to get object {key}: {e}")
            raise StorageOperationError(f"Failed to get object: {e}")
    
    async def get_object_stream(
        self,
        key: str,
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Stream an object in chunks"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Check if blob exists
            if not await asyncio.get_event_loop().run_in_executor(None, blob.exists):
                raise ObjectNotFoundError(key)
            
            # Download to temporary file and stream
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Download blob to temp file
                await asyncio.get_event_loop().run_in_executor(
                    None, blob.download_to_filename, tmp_path
                )
                
                # Stream from temp file
                async with aiofiles.open(tmp_path, 'rb') as f:
                    while chunk := await f.read(chunk_size):
                        yield chunk
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
                
        except NotFound:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to stream object {key}: {e}")
            raise StorageOperationError(f"Failed to stream object: {e}")
    
    async def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> StorageObject:
        """Store an object"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Set content type
            if content_type:
                blob.content_type = content_type
            
            # Upload data
            if isinstance(data, bytes):
                await asyncio.get_event_loop().run_in_executor(
                    None, blob.upload_from_string, data
                )
            else:
                # For file-like objects, save to temp file first
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(data.read())
                    tmp_path = tmp_file.name
                
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, blob.upload_from_filename, tmp_path
                    )
                finally:
                    os.unlink(tmp_path)
            
            # Reload blob to get updated properties
            await asyncio.get_event_loop().run_in_executor(None, blob.reload)
            
            return self._blob_to_storage_object(blob)
            
        except Exception as e:
            logger.error(f"Failed to put object {key}: {e}")
            raise StorageOperationError(f"Failed to put object: {e}")
    
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
        self._ensure_initialized()
        
        try:
            # Collect stream data to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            total_size = 0
            
            try:
                async with aiofiles.open(tmp_path, 'wb') as f:
                    async for chunk in stream:
                        await f.write(chunk)
                        total_size += len(chunk)
                        
                        if progress_callback:
                            progress = UploadProgress(
                                bytes_uploaded=total_size,
                                total_bytes=size or total_size,
                                percentage=round((total_size / (size or total_size)) * 100, 2)
                                if size else 0
                            )
                            progress_callback(progress)
                
                # Upload from temp file
                blob = self._bucket.blob(key)
                
                if metadata:
                    blob.metadata = metadata
                if content_type:
                    blob.content_type = content_type
                
                await asyncio.get_event_loop().run_in_executor(
                    None, blob.upload_from_filename, tmp_path
                )
                
                # Reload and return
                await asyncio.get_event_loop().run_in_executor(None, blob.reload)
                return self._blob_to_storage_object(blob)
                
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            logger.error(f"Failed to put object stream {key}: {e}")
            raise StorageOperationError(f"Failed to put object stream: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Check if exists before deleting
            if not await asyncio.get_event_loop().run_in_executor(None, blob.exists):
                return False
            
            await asyncio.get_event_loop().run_in_executor(None, blob.delete)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            return False
    
    async def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple objects"""
        results = {}
        
        # GCS doesn't have batch delete, so we delete in parallel
        tasks = []
        for key in keys:
            task = self.delete_object(key)
            tasks.append((key, task))
        
        for key, task in tasks:
            try:
                results[key] = await task
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
        self._ensure_initialized()
        
        try:
            objects = []
            
            # List blobs
            blobs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self._bucket.list_blobs(
                    prefix=prefix,
                    delimiter=delimiter,
                    max_results=max_keys,
                    page_token=continuation_token
                ))
            )
            
            for blob in blobs:
                obj = self._blob_to_storage_object(blob)
                objects.append(obj)
            
            # GCS returns page token if there are more results
            # For simplicity, we're not implementing pagination here
            return objects, None
            
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise StorageOperationError(f"Failed to list objects: {e}")
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata without retrieving content"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Reload blob to get metadata
            await asyncio.get_event_loop().run_in_executor(None, blob.reload)
            
            return self._blob_to_storage_object(blob)
            
        except NotFound:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to get object info {key}: {e}")
            raise StorageOperationError(f"Failed to get object info: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Copy an object within the same storage"""
        self._ensure_initialized()
        
        try:
            source_blob = self._bucket.blob(source_key)
            dest_blob = self._bucket.blob(dest_key)
            
            # Copy blob
            await asyncio.get_event_loop().run_in_executor(
                None, source_blob.copy_to, dest_blob
            )
            
            # Update metadata if provided
            if metadata:
                dest_blob.metadata = metadata
                await asyncio.get_event_loop().run_in_executor(
                    None, dest_blob.patch
                )
            
            # Reload and return
            await asyncio.get_event_loop().run_in_executor(None, dest_blob.reload)
            return self._blob_to_storage_object(dest_blob)
            
        except NotFound:
            raise ObjectNotFoundError(source_key)
        except Exception as e:
            logger.error(f"Failed to copy object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Move an object within the same storage"""
        # Copy then delete
        result = await self.copy_object(source_key, dest_key, metadata)
        await self.delete_object(source_key)
        return result
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = 'get',
        expires_in: int = 3600,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a presigned URL for direct access"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Set expiration
            expiration = timedelta(seconds=expires_in)
            
            # Generate signed URL
            if operation == 'get':
                url = await asyncio.get_event_loop().run_in_executor(
                    None,
                    blob.generate_signed_url,
                    expiration,
                    "GET"
                )
            elif operation == 'put':
                url = await asyncio.get_event_loop().run_in_executor(
                    None,
                    blob.generate_signed_url,
                    expiration,
                    "PUT"
                )
            else:
                raise InvalidStorageOperationError(f"Unsupported operation: {operation}")
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageOperationError(f"Failed to generate presigned URL: {e}")
    
    async def create_multipart_upload(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Initiate a multipart upload"""
        self._ensure_initialized()
        
        # GCS uses resumable uploads instead of multipart
        # We'll simulate multipart with resumable upload
        upload_id = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        self._multipart_uploads[upload_id] = {
            "key": key,
            "metadata": metadata or {},
            "content_type": content_type,
            "parts": {},
            "created_at": datetime.utcnow()
        }
        
        return upload_id
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> Dict[str, Any]:
        """Upload a part in a multipart upload"""
        self._ensure_initialized()
        
        if upload_id not in self._multipart_uploads:
            raise InvalidStorageOperationError(f"Invalid upload ID: {upload_id}")
        
        upload_info = self._multipart_uploads[upload_id]
        if upload_info["key"] != key:
            raise InvalidStorageOperationError("Key mismatch for upload ID")
        
        # Store part data
        upload_info["parts"][part_number] = data
        
        return {
            "PartNumber": part_number,
            "ETag": hashlib.md5(data).hexdigest(),
            "Size": len(data)
        }
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> StorageObject:
        """Complete a multipart upload"""
        self._ensure_initialized()
        
        if upload_id not in self._multipart_uploads:
            raise InvalidStorageOperationError(f"Invalid upload ID: {upload_id}")
        
        upload_info = self._multipart_uploads[upload_id]
        if upload_info["key"] != key:
            raise InvalidStorageOperationError("Key mismatch for upload ID")
        
        try:
            # Combine all parts
            all_parts = upload_info["parts"]
            sorted_parts = sorted(all_parts.items())
            combined_data = b''.join(data for _, data in sorted_parts)
            
            # Upload combined data
            result = await self.put_object(
                key,
                combined_data,
                upload_info["metadata"],
                upload_info["content_type"]
            )
            
            # Clean up
            del self._multipart_uploads[upload_id]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to complete multipart upload: {e}")
            raise StorageOperationError(f"Failed to complete multipart upload: {e}")
    
    async def abort_multipart_upload(
        self,
        key: str,
        upload_id: str
    ) -> None:
        """Abort a multipart upload"""
        self._ensure_initialized()
        
        if upload_id in self._multipart_uploads:
            del self._multipart_uploads[upload_id]
    
    async def get_quota(self) -> StorageQuota:
        """Get storage quota information"""
        self._ensure_initialized()
        
        try:
            # Calculate usage
            total_size = 0
            file_count = 0
            
            blobs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self._bucket.list_blobs())
            )
            
            for blob in blobs:
                total_size += blob.size or 0
                file_count += 1
            
            # GCS doesn't have quotas, return unlimited
            return StorageQuota(
                total_bytes=0,  # 0 means unlimited
                used_bytes=total_size,
                available_bytes=0,
                usage_percentage=0.0,
                file_count=file_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get quota: {e}")
            raise StorageOperationError(f"Failed to get quota: {e}")
    
    async def change_storage_tier(
        self,
        key: str,
        tier: StorageTier
    ) -> StorageObject:
        """Change storage tier of an object"""
        self._ensure_initialized()
        
        if tier not in self.tier_mapping:
            raise InvalidStorageOperationError(f"Unsupported tier: {tier}")
        
        try:
            blob = self._bucket.blob(key)
            
            # Reload to ensure we have latest metadata
            await asyncio.get_event_loop().run_in_executor(None, blob.reload)
            
            # Update storage class
            blob.storage_class = self.tier_mapping[tier]
            await asyncio.get_event_loop().run_in_executor(None, blob.patch)
            
            # Reload and return
            await asyncio.get_event_loop().run_in_executor(None, blob.reload)
            return self._blob_to_storage_object(blob)
            
        except NotFound:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to change tier for {key}: {e}")
            raise StorageOperationError(f"Failed to change storage tier: {e}")
    
    async def restore_from_archive(
        self,
        key: str,
        days: int = 1,
        tier: str = "Standard"
    ) -> Dict[str, Any]:
        """Restore an archived object"""
        self._ensure_initialized()
        
        try:
            blob = self._bucket.blob(key)
            
            # Reload to get current storage class
            await asyncio.get_event_loop().run_in_executor(None, blob.reload)
            
            # Check if blob is archived
            if blob.storage_class != "ARCHIVE":
                return {
                    "status": "not_archived",
                    "message": "Object is not in archive tier"
                }
            
            # Change to STANDARD class to restore
            blob.storage_class = "STANDARD"
            await asyncio.get_event_loop().run_in_executor(None, blob.patch)
            
            return {
                "status": "restored",
                "message": "Object restored from archive to standard storage"
            }
            
        except NotFound:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to restore {key}: {e}")
            raise StorageOperationError(f"Failed to restore from archive: {e}")
    
    def _blob_to_storage_object(self, blob: storage.Blob) -> StorageObject:
        """Convert GCS blob to StorageObject"""
        # Map GCS storage class to our tier
        storage_class = None
        if blob.storage_class:
            for our_tier, gcs_class in self.tier_mapping.items():
                if blob.storage_class == gcs_class:
                    storage_class = our_tier.value
                    break
        
        return StorageObject(
            key=blob.name,
            size=blob.size or 0,
            last_modified=blob.updated or datetime.utcnow(),
            etag=blob.etag,
            content_type=blob.content_type,
            metadata=blob.metadata,
            storage_class=storage_class,
            version_id=str(blob.generation) if blob.generation else None
        )