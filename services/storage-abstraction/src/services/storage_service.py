"""
Storage Service

This module provides the main storage service that manages different storage
drivers and handles file operations.
"""

import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator, Union, BinaryIO, Tuple, Callable
from datetime import datetime
import logging
from pathlib import Path

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota, UploadProgress,
    StorageTier, StorageType, ObjectNotFoundError,
    InvalidStorageOperationError
)
from ..core.config import get_settings
from ..drivers import (
    LocalStorageDriver, S3StorageDriver, AzureBlobStorageDriver, 
    GCSStorageDriver, DropboxStorageDriver, OneDriveStorageDriver,
    FTPStorageDriver, SFTPStorageDriver
)


logger = logging.getLogger(__name__)


class StorageService:
    """Main storage service that manages multiple storage drivers"""
    
    def __init__(self):
        self.settings = get_settings()
        self._drivers: Dict[str, StorageDriver] = {}
        self._default_driver: Optional[str] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize storage service and configured drivers"""
        if self._initialized:
            return
        
        logger.info("Initializing storage service...")
        
        # Initialize configured drivers
        for driver_name, driver_config in self.settings.storage_drivers.items():
            try:
                driver = await self._create_driver(driver_name, driver_config)
                await driver.initialize()
                self._drivers[driver_name] = driver
                logger.info(f"Initialized storage driver: {driver_name}")
            except Exception as e:
                logger.error(f"Failed to initialize driver {driver_name}: {e}")
                if driver_name == self.settings.default_storage_driver:
                    raise
        
        # Set default driver
        self._default_driver = self.settings.default_storage_driver
        if self._default_driver not in self._drivers:
            if self._drivers:
                self._default_driver = list(self._drivers.keys())[0]
                logger.warning(
                    f"Default driver not available, using {self._default_driver}"
                )
            else:
                raise InvalidStorageOperationError("No storage drivers available")
        
        self._initialized = True
        logger.info(f"Storage service initialized with {len(self._drivers)} drivers")
    
    async def shutdown(self) -> None:
        """Shutdown storage service and close all drivers"""
        logger.info("Shutting down storage service...")
        
        for driver_name, driver in self._drivers.items():
            try:
                await driver.close()
                logger.info(f"Closed storage driver: {driver_name}")
            except Exception as e:
                logger.error(f"Error closing driver {driver_name}: {e}")
        
        self._drivers.clear()
        self._initialized = False
    
    async def _create_driver(
        self, 
        driver_name: str, 
        config: Dict[str, Any]
    ) -> StorageDriver:
        """Create a storage driver instance"""
        driver_type = config.get("type", driver_name)
        
        # Add common settings from global config
        full_config = self.settings.get_storage_driver_config(driver_name)
        
        if driver_type == "local":
            return LocalStorageDriver(full_config)
        elif driver_type == "s3":
            return S3StorageDriver(full_config)
        elif driver_type == "azure" or driver_type == "azure_blob":
            return AzureBlobStorageDriver(full_config)
        elif driver_type == "gcs" or driver_type == "google":
            return GCSStorageDriver(full_config)
        elif driver_type == "dropbox":
            return DropboxStorageDriver(full_config)
        elif driver_type == "onedrive":
            return OneDriveStorageDriver(full_config)
        elif driver_type == "ftp":
            return FTPStorageDriver(full_config)
        elif driver_type == "sftp":
            return SFTPStorageDriver(full_config)
        else:
            raise InvalidStorageOperationError(f"Unknown driver type: {driver_type}")
    
    def get_driver(self, driver_name: Optional[str] = None) -> StorageDriver:
        """Get a storage driver by name"""
        if not self._initialized:
            raise InvalidStorageOperationError("Storage service not initialized")
        
        if driver_name is None:
            driver_name = self._default_driver
        
        if driver_name not in self._drivers:
            raise InvalidStorageOperationError(f"Driver not found: {driver_name}")
        
        return self._drivers[driver_name]
    
    async def exists(
        self, 
        key: str, 
        driver: Optional[str] = None
    ) -> bool:
        """Check if an object exists"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.exists(key)
    
    async def get_object(
        self, 
        key: str, 
        driver: Optional[str] = None
    ) -> bytes:
        """Retrieve an object"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.get_object(key)
    
    async def get_object_stream(
        self, 
        key: str,
        chunk_size: int = 8192,
        driver: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Stream an object in chunks"""
        storage_driver = self.get_driver(driver)
        async for chunk in storage_driver.get_object_stream(key, chunk_size):
            yield chunk
    
    async def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        driver: Optional[str] = None
    ) -> StorageObject:
        """Store an object"""
        storage_driver = self.get_driver(driver)
        
        # Check quotas if enabled
        if self.settings.enable_quotas:
            await self._check_quota(storage_driver, len(data) if isinstance(data, bytes) else 0)
        
        return await storage_driver.put_object(key, data, metadata, content_type)
    
    async def put_object_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None,
        driver: Optional[str] = None
    ) -> StorageObject:
        """Store an object from a stream"""
        storage_driver = self.get_driver(driver)
        
        # Check quotas if size is known
        if self.settings.enable_quotas and size:
            await self._check_quota(storage_driver, size)
        
        return await storage_driver.put_object_stream(
            key, stream, size, metadata, content_type, progress_callback
        )
    
    async def delete_object(
        self, 
        key: str, 
        driver: Optional[str] = None
    ) -> bool:
        """Delete an object"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.delete_object(key)
    
    async def delete_objects(
        self, 
        keys: List[str], 
        driver: Optional[str] = None
    ) -> Dict[str, bool]:
        """Delete multiple objects"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.delete_objects(keys)
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        driver: Optional[str] = None
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """List objects with optional prefix"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.list_objects(
            prefix, delimiter, max_keys, continuation_token
        )
    
    async def get_object_info(
        self, 
        key: str, 
        driver: Optional[str] = None
    ) -> StorageObject:
        """Get object metadata without retrieving content"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.get_object_info(key)
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        source_driver: Optional[str] = None,
        dest_driver: Optional[str] = None
    ) -> StorageObject:
        """Copy an object within or between storage drivers"""
        source_driver_obj = self.get_driver(source_driver)
        dest_driver_obj = self.get_driver(dest_driver)
        
        # If same driver, use native copy
        if source_driver_obj == dest_driver_obj:
            return await source_driver_obj.copy_object(source_key, dest_key, metadata)
        
        # Cross-driver copy: download and upload
        logger.info(f"Cross-driver copy from {source_driver} to {dest_driver}")
        
        # Get source object info
        source_info = await source_driver_obj.get_object_info(source_key)
        
        # Stream copy for efficiency
        stream = source_driver_obj.get_object_stream(source_key)
        
        return await dest_driver_obj.put_object_stream(
            dest_key,
            stream,
            source_info.size,
            metadata or source_info.metadata,
            source_info.content_type
        )
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        source_driver: Optional[str] = None,
        dest_driver: Optional[str] = None
    ) -> StorageObject:
        """Move an object within or between storage drivers"""
        source_driver_obj = self.get_driver(source_driver)
        dest_driver_obj = self.get_driver(dest_driver)
        
        # If same driver, use native move
        if source_driver_obj == dest_driver_obj:
            return await source_driver_obj.move_object(source_key, dest_key, metadata)
        
        # Cross-driver move: copy then delete
        result = await self.copy_object(
            source_key, dest_key, metadata, source_driver, dest_driver
        )
        await source_driver_obj.delete_object(source_key)
        
        return result
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = 'get',
        expires_in: int = 3600,
        params: Optional[Dict[str, Any]] = None,
        driver: Optional[str] = None
    ) -> str:
        """Generate a presigned URL for direct access"""
        storage_driver = self.get_driver(driver)
        
        # Validate expiry time
        if expires_in > self.settings.max_presigned_url_expiry:
            expires_in = self.settings.max_presigned_url_expiry
        
        return await storage_driver.get_presigned_url(
            key, operation, expires_in, params
        )
    
    async def create_multipart_upload(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        driver: Optional[str] = None
    ) -> str:
        """Initiate a multipart upload"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.create_multipart_upload(
            key, metadata, content_type
        )
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes,
        driver: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a part in a multipart upload"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.upload_part(
            key, upload_id, part_number, data
        )
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]],
        driver: Optional[str] = None
    ) -> StorageObject:
        """Complete a multipart upload"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.complete_multipart_upload(
            key, upload_id, parts
        )
    
    async def abort_multipart_upload(
        self,
        key: str,
        upload_id: str,
        driver: Optional[str] = None
    ) -> None:
        """Abort a multipart upload"""
        storage_driver = self.get_driver(driver)
        await storage_driver.abort_multipart_upload(key, upload_id)
    
    async def get_quota(
        self, 
        driver: Optional[str] = None
    ) -> StorageQuota:
        """Get storage quota information"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.get_quota()
    
    async def change_storage_tier(
        self,
        key: str,
        tier: StorageTier,
        driver: Optional[str] = None
    ) -> StorageObject:
        """Change storage tier of an object"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.change_storage_tier(key, tier)
    
    async def restore_from_archive(
        self,
        key: str,
        days: int = 1,
        tier: str = "Standard",
        driver: Optional[str] = None
    ) -> Dict[str, Any]:
        """Restore an archived object"""
        storage_driver = self.get_driver(driver)
        return await storage_driver.restore_from_archive(key, days, tier)
    
    async def migrate_object(
        self,
        key: str,
        from_driver: str,
        to_driver: str,
        delete_source: bool = True
    ) -> StorageObject:
        """Migrate an object between storage drivers"""
        logger.info(f"Migrating {key} from {from_driver} to {to_driver}")
        
        # Copy object
        result = await self.copy_object(
            key, key, None, from_driver, to_driver
        )
        
        # Delete from source if requested
        if delete_source:
            await self.delete_object(key, from_driver)
        
        return result
    
    async def get_driver_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available storage drivers"""
        info = {}
        
        for name, driver in self._drivers.items():
            try:
                quota = await driver.get_quota()
                info[name] = {
                    "type": driver.__class__.__name__,
                    "initialized": driver._initialized,
                    "quota": {
                        "total_bytes": quota.total_bytes,
                        "used_bytes": quota.used_bytes,
                        "available_bytes": quota.available_bytes,
                        "usage_percentage": quota.usage_percentage,
                        "file_count": quota.file_count
                    }
                }
            except Exception as e:
                info[name] = {
                    "type": driver.__class__.__name__,
                    "initialized": driver._initialized,
                    "error": str(e)
                }
        
        return info
    
    async def _check_quota(self, driver: StorageDriver, size: int) -> None:
        """Check if upload would exceed quota"""
        if not self.settings.enable_quotas:
            return
        
        quota = await driver.get_quota()
        
        if quota.used_bytes + size > quota.total_bytes:
            from ..core.interfaces import StorageQuotaExceededError
            raise StorageQuotaExceededError(quota)


# Global storage service instance
_storage_service: Optional[StorageService] = None


async def get_storage_service() -> StorageService:
    """Get or create storage service instance"""
    global _storage_service
    
    if _storage_service is None:
        _storage_service = StorageService()
        await _storage_service.initialize()
    
    return _storage_service


async def close_storage_service() -> None:
    """Close storage service"""
    global _storage_service
    
    if _storage_service is not None:
        await _storage_service.shutdown()
        _storage_service = None