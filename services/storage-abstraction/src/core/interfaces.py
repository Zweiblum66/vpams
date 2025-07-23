"""
Storage Abstraction Interfaces

This module defines the abstract base classes and interfaces for the storage system.
All storage drivers must implement these interfaces.
"""

from abc import ABC, abstractmethod
from typing import (
    Optional, List, Dict, Any, AsyncIterator, BinaryIO,
    Union, Tuple, Callable
)
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import asyncio


class StorageType(Enum):
    """Supported storage types"""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    FTP = "ftp"
    SFTP = "sftp"
    NAS = "nas"


class StorageTier(Enum):
    """Storage tiers for lifecycle management"""
    HOT = "hot"          # Frequently accessed data
    WARM = "warm"        # Occasionally accessed data
    COLD = "cold"        # Rarely accessed data
    ARCHIVE = "archive"  # Long-term archival


@dataclass
class StorageObject:
    """Represents an object in storage"""
    key: str                          # Object key/path
    size: int                         # Size in bytes
    last_modified: datetime           # Last modification time
    etag: Optional[str] = None       # Entity tag for versioning
    content_type: Optional[str] = None  # MIME type
    metadata: Optional[Dict[str, str]] = None  # Custom metadata
    storage_class: Optional[str] = None  # Storage class/tier
    version_id: Optional[str] = None  # Version identifier
    
    @property
    def is_directory(self) -> bool:
        """Check if object represents a directory"""
        return self.key.endswith('/') and self.size == 0


@dataclass
class StorageQuota:
    """Storage quota information"""
    total_bytes: int
    used_bytes: int
    available_bytes: int
    file_count: Optional[int] = None
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage"""
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100


@dataclass
class UploadProgress:
    """Upload progress information"""
    bytes_uploaded: int
    total_bytes: int
    start_time: datetime
    current_time: datetime
    
    @property
    def percentage(self) -> float:
        """Calculate upload percentage"""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_uploaded / self.total_bytes) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds"""
        return (self.current_time - self.start_time).total_seconds()
    
    @property
    def speed_bps(self) -> float:
        """Calculate upload speed in bytes per second"""
        if self.elapsed_seconds == 0:
            return 0.0
        return self.bytes_uploaded / self.elapsed_seconds


class StorageDriver(ABC):
    """Abstract base class for storage drivers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize storage driver with configuration
        
        Args:
            config: Driver-specific configuration
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage driver (connect, authenticate, etc.)"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if an object exists
        
        Args:
            key: Object key/path
            
        Returns:
            True if object exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_object(self, key: str) -> bytes:
        """
        Retrieve an object
        
        Args:
            key: Object key/path
            
        Returns:
            Object content as bytes
            
        Raises:
            ObjectNotFoundError: If object doesn't exist
        """
        pass
    
    @abstractmethod
    async def get_object_stream(
        self, 
        key: str, 
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """
        Stream an object in chunks
        
        Args:
            key: Object key/path
            chunk_size: Size of each chunk in bytes
            
        Yields:
            Chunks of object content
            
        Raises:
            ObjectNotFoundError: If object doesn't exist
        """
        pass
    
    @abstractmethod
    async def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> StorageObject:
        """
        Store an object
        
        Args:
            key: Object key/path
            data: Object content (bytes or file-like object)
            metadata: Custom metadata
            content_type: MIME type
            
        Returns:
            StorageObject with details of stored object
        """
        pass
    
    @abstractmethod
    async def put_object_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> StorageObject:
        """
        Store an object from a stream
        
        Args:
            key: Object key/path
            stream: Async iterator yielding chunks
            size: Total size if known
            metadata: Custom metadata
            content_type: MIME type
            progress_callback: Callback for progress updates
            
        Returns:
            StorageObject with details of stored object
        """
        pass
    
    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """
        Delete an object
        
        Args:
            key: Object key/path
            
        Returns:
            True if deleted, False if object didn't exist
        """
        pass
    
    @abstractmethod
    async def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """
        Delete multiple objects
        
        Args:
            keys: List of object keys/paths
            
        Returns:
            Dictionary mapping keys to deletion success
        """
        pass
    
    @abstractmethod
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """
        List objects with optional prefix
        
        Args:
            prefix: Filter objects by prefix
            delimiter: Delimiter for hierarchical listing
            max_keys: Maximum number of objects to return
            continuation_token: Token for pagination
            
        Returns:
            Tuple of (list of objects, continuation token for next page)
        """
        pass
    
    @abstractmethod
    async def get_object_info(self, key: str) -> StorageObject:
        """
        Get object metadata without retrieving content
        
        Args:
            key: Object key/path
            
        Returns:
            StorageObject with metadata
            
        Raises:
            ObjectNotFoundError: If object doesn't exist
        """
        pass
    
    @abstractmethod
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """
        Copy an object within the same storage
        
        Args:
            source_key: Source object key/path
            dest_key: Destination object key/path
            metadata: New metadata (optional)
            
        Returns:
            StorageObject with details of copied object
            
        Raises:
            ObjectNotFoundError: If source doesn't exist
        """
        pass
    
    @abstractmethod
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """
        Move/rename an object
        
        Args:
            source_key: Source object key/path
            dest_key: Destination object key/path
            metadata: New metadata (optional)
            
        Returns:
            StorageObject with details of moved object
            
        Raises:
            ObjectNotFoundError: If source doesn't exist
        """
        pass
    
    @abstractmethod
    async def get_presigned_url(
        self,
        key: str,
        operation: str = 'get',
        expires_in: int = 3600,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a presigned URL for direct access
        
        Args:
            key: Object key/path
            operation: Operation ('get' or 'put')
            expires_in: URL expiration time in seconds
            params: Additional parameters
            
        Returns:
            Presigned URL
        """
        pass
    
    @abstractmethod
    async def create_multipart_upload(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Initiate a multipart upload
        
        Args:
            key: Object key/path
            metadata: Custom metadata
            content_type: MIME type
            
        Returns:
            Upload ID for the multipart upload
        """
        pass
    
    @abstractmethod
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> Dict[str, Any]:
        """
        Upload a part in a multipart upload
        
        Args:
            key: Object key/path
            upload_id: Multipart upload ID
            part_number: Part number (1-based)
            data: Part data
            
        Returns:
            Part information (ETag, etc.)
        """
        pass
    
    @abstractmethod
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> StorageObject:
        """
        Complete a multipart upload
        
        Args:
            key: Object key/path
            upload_id: Multipart upload ID
            parts: List of part information
            
        Returns:
            StorageObject with details of completed upload
        """
        pass
    
    @abstractmethod
    async def abort_multipart_upload(
        self,
        key: str,
        upload_id: str
    ) -> None:
        """
        Abort a multipart upload
        
        Args:
            key: Object key/path
            upload_id: Multipart upload ID
        """
        pass
    
    @abstractmethod
    async def get_quota(self) -> StorageQuota:
        """
        Get storage quota information
        
        Returns:
            StorageQuota with usage information
        """
        pass
    
    # Optional tier management methods
    async def change_storage_tier(
        self,
        key: str,
        tier: StorageTier
    ) -> StorageObject:
        """
        Change storage tier of an object (if supported)
        
        Args:
            key: Object key/path
            tier: Target storage tier
            
        Returns:
            Updated StorageObject
            
        Raises:
            NotImplementedError: If tier management not supported
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support storage tiers")
    
    async def restore_from_archive(
        self,
        key: str,
        days: int = 1,
        tier: str = "Standard"
    ) -> Dict[str, Any]:
        """
        Restore an archived object (if supported)
        
        Args:
            key: Object key/path
            days: Number of days to keep restored
            tier: Restore tier (e.g., "Expedited", "Standard", "Bulk")
            
        Returns:
            Restore request information
            
        Raises:
            NotImplementedError: If archival not supported
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support archive restoration")


class StorageException(Exception):
    """Base exception for storage operations"""
    pass


class ObjectNotFoundError(StorageException):
    """Raised when an object is not found"""
    def __init__(self, key: str):
        super().__init__(f"Object not found: {key}")
        self.key = key


class StorageQuotaExceededError(StorageException):
    """Raised when storage quota is exceeded"""
    def __init__(self, quota: StorageQuota):
        super().__init__(f"Storage quota exceeded: {quota.usage_percentage:.1f}% used")
        self.quota = quota


class StorageAuthenticationError(StorageException):
    """Raised when authentication fails"""
    pass


class StoragePermissionError(StorageException):
    """Raised when permission is denied"""
    pass


class InvalidStorageOperationError(StorageException):
    """Raised when an invalid operation is attempted"""
    pass