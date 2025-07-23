"""
Storage Service for proxy file management
"""

import os
import asyncio
from typing import BinaryIO, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import aiofiles
import aioboto3
from botocore.exceptions import ClientError

from ..core.config import settings
from ..core.exceptions import StorageError
from ..core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing proxy file storage"""
    
    def __init__(self):
        self.backend = settings.storage_backend
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        self.local_path = Path(settings.local_storage_path)
        
        # Create local storage directory if needed
        if self.backend == "local":
            self.local_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize storage backend"""
        try:
            if self.backend == "s3":
                # Create S3 session
                session = aioboto3.Session()
                self.s3_client = await session.client(
                    's3',
                    endpoint_url=settings.s3_endpoint,
                    aws_access_key_id=settings.s3_access_key,
                    aws_secret_access_key=settings.s3_secret_key,
                    region_name=settings.s3_region
                ).__aenter__()
                
                # Ensure bucket exists
                await self._ensure_bucket_exists()
                
            logger.info(
                "storage_initialized",
                backend=self.backend,
                bucket=self.bucket_name if self.backend == "s3" else None,
                local_path=str(self.local_path) if self.backend == "local" else None
            )
            
        except Exception as e:
            logger.error("storage_initialization_failed", error=str(e))
            raise StorageError(f"Failed to initialize storage: {str(e)}")
    
    async def close(self):
        """Close storage connections"""
        try:
            if self.s3_client:
                await self.s3_client.__aexit__(None, None, None)
                self.s3_client = None
            
            logger.info("storage_closed")
            
        except Exception as e:
            logger.error("storage_close_failed", error=str(e))
    
    async def _ensure_bucket_exists(self):
        """Ensure S3 bucket exists"""
        try:
            await self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Create bucket
                await self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': settings.s3_region}
                    if settings.s3_region != 'us-east-1' else None
                )
                logger.info("bucket_created", bucket=self.bucket_name)
            else:
                raise
    
    async def store_file(
        self,
        file_path: str,
        storage_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Store file in storage backend"""
        try:
            if self.backend == "s3":
                return await self._store_file_s3(file_path, storage_key, metadata)
            else:
                return await self._store_file_local(file_path, storage_key, metadata)
                
        except Exception as e:
            logger.error(
                "file_storage_failed",
                error=str(e),
                file_path=file_path,
                storage_key=storage_key
            )
            raise StorageError(f"Failed to store file: {str(e)}")
    
    async def _store_file_s3(
        self,
        file_path: str,
        storage_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Store file in S3"""
        try:
            # Prepare metadata
            s3_metadata = metadata or {}
            s3_metadata['original-filename'] = os.path.basename(file_path)
            
            # Upload file
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
                
                await self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Body=file_data,
                    Metadata=s3_metadata
                )
            
            # Generate URL
            url = f"{settings.s3_endpoint}/{self.bucket_name}/{storage_key}"
            
            logger.info(
                "file_stored_s3",
                storage_key=storage_key,
                size=os.path.getsize(file_path),
                url=url
            )
            
            return url
            
        except Exception as e:
            raise StorageError(f"S3 storage failed: {str(e)}")
    
    async def _store_file_local(
        self,
        file_path: str,
        storage_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Store file in local filesystem"""
        try:
            # Create directory structure
            dest_path = self.local_path / storage_key
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            async with aiofiles.open(file_path, 'rb') as src:
                async with aiofiles.open(dest_path, 'wb') as dst:
                    while chunk := await src.read(8192):
                        await dst.write(chunk)
            
            # Store metadata if provided
            if metadata:
                metadata_path = dest_path.with_suffix('.metadata.json')
                async with aiofiles.open(metadata_path, 'w') as f:
                    import json
                    await f.write(json.dumps(metadata, indent=2))
            
            logger.info(
                "file_stored_local",
                storage_key=storage_key,
                size=os.path.getsize(file_path),
                path=str(dest_path)
            )
            
            return str(dest_path)
            
        except Exception as e:
            raise StorageError(f"Local storage failed: {str(e)}")
    
    async def retrieve_file(
        self,
        storage_key: str,
        output_path: str
    ) -> str:
        """Retrieve file from storage"""
        try:
            if self.backend == "s3":
                return await self._retrieve_file_s3(storage_key, output_path)
            else:
                return await self._retrieve_file_local(storage_key, output_path)
                
        except Exception as e:
            logger.error(
                "file_retrieval_failed",
                error=str(e),
                storage_key=storage_key
            )
            raise StorageError(f"Failed to retrieve file: {str(e)}")
    
    async def _retrieve_file_s3(
        self,
        storage_key: str,
        output_path: str
    ) -> str:
        """Retrieve file from S3"""
        try:
            # Download file
            response = await self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            
            # Write to output path
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            async with aiofiles.open(output_path, 'wb') as f:
                async for chunk in response['Body'].iter_chunks(chunk_size=8192):
                    await f.write(chunk)
            
            logger.info(
                "file_retrieved_s3",
                storage_key=storage_key,
                output_path=output_path
            )
            
            return output_path
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise StorageError(f"File not found: {storage_key}")
            raise StorageError(f"S3 retrieval failed: {str(e)}")
    
    async def _retrieve_file_local(
        self,
        storage_key: str,
        output_path: str
    ) -> str:
        """Retrieve file from local storage"""
        try:
            src_path = self.local_path / storage_key
            
            if not src_path.exists():
                raise StorageError(f"File not found: {storage_key}")
            
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Copy file
            async with aiofiles.open(src_path, 'rb') as src:
                async with aiofiles.open(output_path, 'wb') as dst:
                    while chunk := await src.read(8192):
                        await dst.write(chunk)
            
            logger.info(
                "file_retrieved_local",
                storage_key=storage_key,
                output_path=output_path
            )
            
            return output_path
            
        except Exception as e:
            raise StorageError(f"Local retrieval failed: {str(e)}")
    
    async def delete_file(self, storage_key: str):
        """Delete file from storage"""
        try:
            if self.backend == "s3":
                await self._delete_file_s3(storage_key)
            else:
                await self._delete_file_local(storage_key)
                
        except Exception as e:
            logger.error(
                "file_deletion_failed",
                error=str(e),
                storage_key=storage_key
            )
            raise StorageError(f"Failed to delete file: {str(e)}")
    
    async def _delete_file_s3(self, storage_key: str):
        """Delete file from S3"""
        try:
            await self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            
            logger.info("file_deleted_s3", storage_key=storage_key)
            
        except Exception as e:
            raise StorageError(f"S3 deletion failed: {str(e)}")
    
    async def _delete_file_local(self, storage_key: str):
        """Delete file from local storage"""
        try:
            file_path = self.local_path / storage_key
            
            if file_path.exists():
                file_path.unlink()
                
                # Also delete metadata if exists
                metadata_path = file_path.with_suffix('.metadata.json')
                if metadata_path.exists():
                    metadata_path.unlink()
            
            logger.info("file_deleted_local", storage_key=storage_key)
            
        except Exception as e:
            raise StorageError(f"Local deletion failed: {str(e)}")
    
    async def file_exists(self, storage_key: str) -> bool:
        """Check if file exists in storage"""
        try:
            if self.backend == "s3":
                return await self._file_exists_s3(storage_key)
            else:
                return await self._file_exists_local(storage_key)
                
        except Exception as e:
            logger.error(
                "file_exists_check_failed",
                error=str(e),
                storage_key=storage_key
            )
            return False
    
    async def _file_exists_s3(self, storage_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            await self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    async def _file_exists_local(self, storage_key: str) -> bool:
        """Check if file exists in local storage"""
        file_path = self.local_path / storage_key
        return file_path.exists()
    
    async def get_file_info(self, storage_key: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            if self.backend == "s3":
                return await self._get_file_info_s3(storage_key)
            else:
                return await self._get_file_info_local(storage_key)
                
        except Exception as e:
            logger.error(
                "get_file_info_failed",
                error=str(e),
                storage_key=storage_key
            )
            raise StorageError(f"Failed to get file info: {str(e)}")
    
    async def _get_file_info_s3(self, storage_key: str) -> Dict[str, Any]:
        """Get file info from S3"""
        try:
            response = await self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            
            return {
                "storage_key": storage_key,
                "size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat(),
                "metadata": response.get('Metadata', {}),
                "content_type": response.get('ContentType', 'application/octet-stream')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise StorageError(f"File not found: {storage_key}")
            raise
    
    async def _get_file_info_local(self, storage_key: str) -> Dict[str, Any]:
        """Get file info from local storage"""
        file_path = self.local_path / storage_key
        
        if not file_path.exists():
            raise StorageError(f"File not found: {storage_key}")
        
        stat = file_path.stat()
        
        # Load metadata if exists
        metadata = {}
        metadata_path = file_path.with_suffix('.metadata.json')
        if metadata_path.exists():
            async with aiofiles.open(metadata_path, 'r') as f:
                import json
                metadata = json.loads(await f.read())
        
        return {
            "storage_key": storage_key,
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "metadata": metadata,
            "content_type": "application/octet-stream"
        }
    
    def generate_storage_key(
        self,
        asset_id: str,
        proxy_type: str,
        quality: str,
        extension: str
    ) -> str:
        """Generate storage key for proxy file"""
        # Format: proxies/{asset_id}/{proxy_type}/{quality}.{extension}
        return f"proxies/{asset_id}/{proxy_type}/{quality}.{extension}"


# Singleton instance
_storage_service: Optional[StorageService] = None


async def get_storage_service() -> StorageService:
    """Get storage service instance"""
    global _storage_service
    
    if _storage_service is None:
        _storage_service = StorageService()
        await _storage_service.initialize()
    
    return _storage_service