"""
Azure Blob Storage Driver

This module implements the storage driver for Azure Blob Storage.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, AsyncIterator, Union, BinaryIO, Tuple, Callable
from urllib.parse import urlparse
import hashlib
import base64

try:
    from azure.storage.blob.aio import BlobServiceClient, ContainerClient
    from azure.storage.blob import (
        BlobProperties, BlobSasPermissions, AccessPolicy,
        generate_blob_sas, BlobBlock, BlobType, StandardBlobTier
    )
    from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    BlobServiceClient = None
    ContainerClient = None

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota, UploadProgress,
    StorageTier, StorageType, ObjectNotFoundError,
    StoragePermissionError, InvalidStorageOperationError,
    StorageQuotaExceededError, StorageOperationError
)


logger = logging.getLogger(__name__)


class AzureBlobStorageDriver(StorageDriver):
    """Azure Blob Storage implementation of StorageDriver"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure Blob Storage driver"""
        super().__init__(config)
        
        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure SDK not installed. Install with: pip install azure-storage-blob"
            )
        
        # Azure configuration
        self.account_name = config.get("account_name")
        self.account_key = config.get("account_key")
        self.connection_string = config.get("connection_string")
        self.container_name = config.get("container_name", "mams-storage")
        self.sas_token = config.get("sas_token")
        self.endpoint_suffix = config.get("endpoint_suffix", "core.windows.net")
        
        # Tier mapping
        self.tier_mapping = {
            StorageTier.HOT: StandardBlobTier.HOT,
            StorageTier.WARM: StandardBlobTier.COOL,  # Azure uses "Cool" instead of "Warm"
            StorageTier.COLD: StandardBlobTier.COLD,
            StorageTier.ARCHIVE: StandardBlobTier.ARCHIVE
        }
        
        # Driver configuration
        self.default_tier = StandardBlobTier.HOT
        self.enable_versioning = config.get("enable_versioning", True)
        self.enable_soft_delete = config.get("enable_soft_delete", True)
        self.soft_delete_days = config.get("soft_delete_days", 7)
        
        # Clients
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None
        
        # Multipart upload tracking
        self._multipart_uploads: Dict[str, Dict[str, Any]] = {}
    
    @property
    def storage_type(self) -> StorageType:
        """Return the storage type"""
        return StorageType.OBJECT
    
    async def initialize(self) -> None:
        """Initialize Azure Blob Storage connection"""
        try:
            # Create blob service client
            if self.connection_string:
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.{self.endpoint_suffix}"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key
                )
            elif self.account_name and self.sas_token:
                account_url = f"https://{self.account_name}.blob.{self.endpoint_suffix}"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.sas_token
                )
            else:
                raise InvalidStorageOperationError(
                    "Azure Blob Storage requires either connection_string, "
                    "account_name/account_key, or account_name/sas_token"
                )
            
            # Get container client
            self._container_client = self._blob_service_client.get_container_client(
                self.container_name
            )
            
            # Create container if it doesn't exist
            try:
                await self._container_client.create_container()
                logger.info(f"Created Azure container: {self.container_name}")
            except ResourceExistsError:
                logger.info(f"Azure container already exists: {self.container_name}")
            
            # Verify access
            await self._container_client.get_container_properties()
            
            self._initialized = True
            logger.info("Azure Blob Storage driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage: {e}")
            raise StorageOperationError(f"Azure initialization failed: {e}")
    
    async def close(self) -> None:
        """Close Azure Blob Storage connection"""
        if self._blob_service_client:
            await self._blob_service_client.close()
        self._initialized = False
        logger.info("Azure Blob Storage driver closed")
    
    async def exists(self, key: str) -> bool:
        """Check if an object exists"""
        self._ensure_initialized()
        
        try:
            blob_client = self._container_client.get_blob_client(key)
            await blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
    
    async def get_object(self, key: str) -> bytes:
        """Retrieve an object"""
        self._ensure_initialized()
        
        try:
            blob_client = self._container_client.get_blob_client(key)
            download_stream = await blob_client.download_blob()
            return await download_stream.readall()
        except ResourceNotFoundError:
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
            blob_client = self._container_client.get_blob_client(key)
            download_stream = await blob_client.download_blob()
            
            async for chunk in download_stream.chunks():
                yield chunk
                
        except ResourceNotFoundError:
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
            blob_client = self._container_client.get_blob_client(key)
            
            # Prepare blob metadata
            blob_metadata = metadata or {}
            
            # Upload blob
            if isinstance(data, bytes):
                blob_properties = await blob_client.upload_blob(
                    data,
                    metadata=blob_metadata,
                    content_type=content_type,
                    overwrite=True,
                    standard_blob_tier=self.default_tier
                )
            else:
                blob_properties = await blob_client.upload_blob(
                    data,
                    metadata=blob_metadata,
                    content_type=content_type,
                    overwrite=True,
                    standard_blob_tier=self.default_tier
                )
            
            # Get blob properties for response
            properties = await blob_client.get_blob_properties()
            
            return self._blob_properties_to_storage_object(key, properties)
            
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
            blob_client = self._container_client.get_blob_client(key)
            
            # Collect stream data
            chunks = []
            total_size = 0
            
            async for chunk in stream:
                chunks.append(chunk)
                total_size += len(chunk)
                
                if progress_callback:
                    progress = UploadProgress(
                        bytes_uploaded=total_size,
                        total_bytes=size or total_size,
                        percentage=round((total_size / (size or total_size)) * 100, 2)
                        if size else 0
                    )
                    progress_callback(progress)
            
            # Upload collected data
            data = b''.join(chunks)
            
            return await self.put_object(key, data, metadata, content_type)
            
        except Exception as e:
            logger.error(f"Failed to put object stream {key}: {e}")
            raise StorageOperationError(f"Failed to put object stream: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object"""
        self._ensure_initialized()
        
        try:
            blob_client = self._container_client.get_blob_client(key)
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise StorageOperationError(f"Failed to delete object: {e}")
    
    async def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple objects"""
        results = {}
        
        # Azure doesn't have batch delete, so we delete in parallel
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
            async for blob in self._container_client.list_blobs(
                name_starts_with=prefix,
                results_per_page=max_keys
            ):
                # Skip if delimiter logic applies
                if delimiter and prefix:
                    relative_key = blob.name[len(prefix):]
                    if delimiter in relative_key:
                        continue
                
                obj = self._blob_item_to_storage_object(blob)
                objects.append(obj)
                
                if len(objects) >= max_keys:
                    break
            
            # Azure SDK handles pagination internally
            # For now, we don't return a continuation token
            return objects, None
            
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise StorageOperationError(f"Failed to list objects: {e}")
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata without retrieving content"""
        self._ensure_initialized()
        
        try:
            blob_client = self._container_client.get_blob_client(key)
            properties = await blob_client.get_blob_properties()
            
            return self._blob_properties_to_storage_object(key, properties)
            
        except ResourceNotFoundError:
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
            # Get source blob URL
            source_blob = self._container_client.get_blob_client(source_key)
            source_url = source_blob.url
            
            # Start copy operation
            dest_blob = self._container_client.get_blob_client(dest_key)
            copy_props = await dest_blob.start_copy_from_url(
                source_url,
                metadata=metadata
            )
            
            # Wait for copy to complete
            properties = await dest_blob.get_blob_properties()
            while properties.copy.status == "pending":
                await asyncio.sleep(1)
                properties = await dest_blob.get_blob_properties()
            
            if properties.copy.status != "success":
                raise StorageOperationError(
                    f"Copy failed with status: {properties.copy.status}"
                )
            
            return self._blob_properties_to_storage_object(dest_key, properties)
            
        except ResourceNotFoundError:
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
            blob_client = self._container_client.get_blob_client(key)
            
            # Set permissions based on operation
            if operation == 'get':
                permissions = BlobSasPermissions(read=True)
            elif operation == 'put':
                permissions = BlobSasPermissions(write=True, create=True)
            else:
                raise InvalidStorageOperationError(f"Unsupported operation: {operation}")
            
            # Generate SAS token
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=key,
                account_key=self.account_key,
                permission=permissions,
                expiry=expiry
            )
            
            # Construct URL
            return f"{blob_client.url}?{sas_token}"
            
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
        
        # Azure uses block blobs for multipart uploads
        upload_id = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        self._multipart_uploads[upload_id] = {
            "key": key,
            "metadata": metadata or {},
            "content_type": content_type,
            "blocks": [],
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
        
        try:
            blob_client = self._container_client.get_blob_client(key)
            
            # Generate block ID
            block_id = base64.b64encode(f"{part_number:06d}".encode()).decode()
            
            # Stage block
            await blob_client.stage_block(block_id, data)
            
            # Track block
            upload_info["blocks"].append({
                "block_id": block_id,
                "part_number": part_number,
                "size": len(data)
            })
            
            return {
                "PartNumber": part_number,
                "ETag": hashlib.md5(data).hexdigest(),
                "Size": len(data)
            }
            
        except Exception as e:
            logger.error(f"Failed to upload part {part_number}: {e}")
            raise StorageOperationError(f"Failed to upload part: {e}")
    
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
            blob_client = self._container_client.get_blob_client(key)
            
            # Sort blocks by part number
            blocks = sorted(upload_info["blocks"], key=lambda x: x["part_number"])
            block_list = [b["block_id"] for b in blocks]
            
            # Commit blocks
            await blob_client.commit_block_list(
                block_list,
                metadata=upload_info["metadata"],
                content_type=upload_info["content_type"],
                standard_blob_tier=self.default_tier
            )
            
            # Clean up
            del self._multipart_uploads[upload_id]
            
            # Get final properties
            properties = await blob_client.get_blob_properties()
            return self._blob_properties_to_storage_object(key, properties)
            
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
            # Get account info
            account_info = await self._blob_service_client.get_account_information()
            
            # Calculate usage (this is a simplified approach)
            total_size = 0
            file_count = 0
            
            async for blob in self._container_client.list_blobs():
                total_size += blob.size or 0
                file_count += 1
            
            # Azure doesn't provide quota info directly
            # Return unlimited quota with current usage
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
            blob_client = self._container_client.get_blob_client(key)
            
            # Set blob tier
            await blob_client.set_standard_blob_tier(self.tier_mapping[tier])
            
            # Get updated properties
            properties = await blob_client.get_blob_properties()
            return self._blob_properties_to_storage_object(key, properties)
            
        except ResourceNotFoundError:
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
            blob_client = self._container_client.get_blob_client(key)
            properties = await blob_client.get_blob_properties()
            
            # Check if blob is archived
            if properties.blob_tier != StandardBlobTier.ARCHIVE:
                return {
                    "status": "not_archived",
                    "message": "Object is not in archive tier"
                }
            
            # Map restore tier
            restore_priority = "Standard"
            if tier == "Expedited":
                restore_priority = "High"
            
            # Rehydrate blob
            await blob_client.set_standard_blob_tier(
                StandardBlobTier.HOT,
                rehydrate_priority=restore_priority
            )
            
            return {
                "status": "restoring",
                "message": f"Archive restoration initiated with {restore_priority} priority"
            }
            
        except ResourceNotFoundError:
            raise ObjectNotFoundError(key)
        except Exception as e:
            logger.error(f"Failed to restore {key}: {e}")
            raise StorageOperationError(f"Failed to restore from archive: {e}")
    
    def _blob_properties_to_storage_object(
        self,
        key: str,
        properties: BlobProperties
    ) -> StorageObject:
        """Convert Azure blob properties to StorageObject"""
        # Map Azure tier to our tier
        storage_class = None
        if hasattr(properties, 'blob_tier'):
            for our_tier, azure_tier in self.tier_mapping.items():
                if properties.blob_tier == azure_tier:
                    storage_class = our_tier.value
                    break
        
        return StorageObject(
            key=key,
            size=properties.size or 0,
            last_modified=properties.last_modified or datetime.utcnow(),
            etag=properties.etag.strip('"') if properties.etag else None,
            content_type=properties.content_settings.content_type if properties.content_settings else None,
            metadata=properties.metadata,
            storage_class=storage_class,
            version_id=properties.version_id
        )
    
    def _blob_item_to_storage_object(self, blob_item) -> StorageObject:
        """Convert Azure blob item to StorageObject"""
        return StorageObject(
            key=blob_item.name,
            size=blob_item.size or 0,
            last_modified=blob_item.last_modified or datetime.utcnow(),
            etag=blob_item.etag.strip('"') if blob_item.etag else None,
            content_type=blob_item.content_settings.content_type if blob_item.content_settings else None,
            metadata=blob_item.metadata,
            storage_class=blob_item.blob_tier.value if blob_item.blob_tier else None
        )