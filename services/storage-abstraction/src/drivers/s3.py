"""
S3-Compatible Storage Driver

This module implements the storage driver for S3-compatible object storage
including AWS S3, MinIO, and other S3-compatible services.
"""

import asyncio
import io
from typing import (
    Optional, List, Dict, Any, AsyncIterator, BinaryIO,
    Union, Tuple, Callable
)
from datetime import datetime, timedelta
import hashlib
import mimetypes
from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageQuota, UploadProgress,
    StorageTier, ObjectNotFoundError, StorageQuotaExceededError,
    StoragePermissionError, InvalidStorageOperationError,
    StorageAuthenticationError
)


class S3StorageDriver(StorageDriver):
    """S3-compatible storage driver implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint_url = config.get("endpoint_url")
        self.access_key_id = config.get("access_key_id")
        self.secret_access_key = config.get("secret_access_key")
        self.bucket = config.get("bucket", "mams-storage")
        self.region = config.get("region", "us-east-1")
        self.use_ssl = config.get("use_ssl", True)
        self.verify_ssl = config.get("verify_ssl", True)
        self.chunk_size = config.get("chunk_size", 8192)
        self.multipart_threshold = config.get("multipart_threshold", 100 * 1024 * 1024)
        self.multipart_chunk_size = config.get("multipart_chunk_size", 10 * 1024 * 1024)
        self.max_pool_connections = config.get("max_pool_connections", 10)
        
        # S3 client configuration
        self.client_config = Config(
            region_name=self.region,
            signature_version='s3v4',
            max_pool_connections=self.max_pool_connections,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        
        self.session = None
        self._client = None
        self._resource = None
    
    async def initialize(self) -> None:
        """Initialize the storage driver"""
        try:
            # Create session
            self.session = aioboto3.Session()
            
            # Test connection and permissions
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=self.client_config,
                use_ssl=self.use_ssl,
                verify=self.verify_ssl
            ) as s3:
                # Check if bucket exists
                try:
                    await s3.head_bucket(Bucket=self.bucket)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == '404':
                        # Try to create bucket
                        try:
                            if self.region == 'us-east-1':
                                await s3.create_bucket(Bucket=self.bucket)
                            else:
                                await s3.create_bucket(
                                    Bucket=self.bucket,
                                    CreateBucketConfiguration={'LocationConstraint': self.region}
                                )
                        except ClientError as create_error:
                            raise StoragePermissionError(
                                f"Cannot create bucket {self.bucket}: {create_error}"
                            )
                    elif error_code == '403':
                        raise StoragePermissionError(
                            f"Access denied to bucket {self.bucket}"
                        )
                    else:
                        raise
                
                # Test write permissions
                test_key = '.write_test'
                try:
                    await s3.put_object(
                        Bucket=self.bucket,
                        Key=test_key,
                        Body=b'test'
                    )
                    await s3.delete_object(Bucket=self.bucket, Key=test_key)
                except ClientError as e:
                    raise StoragePermissionError(
                        f"No write permission to bucket {self.bucket}: {e}"
                    )
            
            self._initialized = True
            
        except Exception as e:
            raise StorageAuthenticationError(f"Failed to initialize S3 storage: {e}")
    
    async def close(self) -> None:
        """Close connections and cleanup resources"""
        self._initialized = False
        if self._client:
            await self._client.close()
        if self._resource:
            await self._resource.close()
    
    async def _get_client(self):
        """Get S3 client"""
        if not self._initialized:
            raise InvalidStorageOperationError("Storage driver not initialized")
        
        if not self._client:
            self._client = await self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=self.client_config,
                use_ssl=self.use_ssl,
                verify=self.verify_ssl
            ).__aenter__()
        
        return self._client
    
    async def exists(self, key: str) -> bool:
        """Check if an object exists"""
        client = await self._get_client()
        
        try:
            await client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    async def get_object(self, key: str) -> bytes:
        """Retrieve an object"""
        client = await self._get_client()
        
        try:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            async with response['Body'] as stream:
                return await stream.read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ObjectNotFoundError(key)
            elif e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied to {key}")
            raise Exception(f"Failed to get object: {e}")
    
    async def get_object_stream(
        self, 
        key: str, 
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Stream an object in chunks"""
        client = await self._get_client()
        
        try:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            async with response['Body'] as stream:
                async for chunk in stream.iter_chunks(chunk_size):
                    yield chunk
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ObjectNotFoundError(key)
            elif e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied to {key}")
            raise Exception(f"Failed to stream object: {e}")
    
    async def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO],
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> StorageObject:
        """Store an object"""
        client = await self._get_client()
        
        # Prepare data
        if isinstance(data, bytes):
            body = data
            size = len(data)
        else:
            # File-like object
            data.seek(0)
            body = data.read()
            size = len(body)
        
        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = 'application/octet-stream'
        
        # Prepare S3 metadata
        s3_metadata = metadata.copy() if metadata else {}
        
        try:
            # Use multipart upload for large files
            if size > self.multipart_threshold:
                return await self._multipart_upload(
                    key, body, s3_metadata, content_type
                )
            
            # Regular upload
            response = await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=s3_metadata
            )
            
            # Get object info for response
            head_response = await client.head_object(Bucket=self.bucket, Key=key)
            
            return StorageObject(
                key=key,
                size=size,
                last_modified=head_response['LastModified'],
                etag=response['ETag'].strip('"'),
                content_type=content_type,
                metadata=s3_metadata,
                version_id=response.get('VersionId')
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied to {key}")
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
        # For S3, we need to collect the stream or use multipart upload
        # Since we don't know the size, we'll use multipart upload
        
        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = 'application/octet-stream'
        
        # Prepare metadata
        s3_metadata = metadata.copy() if metadata else {}
        
        # Start multipart upload
        upload_id = await self.create_multipart_upload(key, s3_metadata, content_type)
        
        parts = []
        part_number = 1
        bytes_uploaded = 0
        current_part = b''
        start_time = datetime.now()
        
        try:
            async for chunk in stream:
                current_part += chunk
                
                # Upload part when it reaches chunk size
                if len(current_part) >= self.multipart_chunk_size:
                    part_info = await self.upload_part(
                        key, upload_id, part_number, current_part
                    )
                    parts.append(part_info)
                    bytes_uploaded += len(current_part)
                    
                    # Progress callback
                    if progress_callback and size:
                        progress = UploadProgress(
                            bytes_uploaded=bytes_uploaded,
                            total_bytes=size,
                            start_time=start_time,
                            current_time=datetime.now()
                        )
                        await asyncio.to_thread(progress_callback, progress)
                    
                    current_part = b''
                    part_number += 1
            
            # Upload final part if any
            if current_part:
                part_info = await self.upload_part(
                    key, upload_id, part_number, current_part
                )
                parts.append(part_info)
                bytes_uploaded += len(current_part)
            
            # Complete multipart upload
            return await self.complete_multipart_upload(key, upload_id, parts)
            
        except Exception as e:
            # Abort on error
            await self.abort_multipart_upload(key, upload_id)
            raise Exception(f"Failed to store object stream: {e}")
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object"""
        client = await self._get_client()
        
        try:
            # Check if exists first
            exists = await self.exists(key)
            if not exists:
                return False
            
            await client.delete_object(Bucket=self.bucket, Key=key)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied to delete {key}")
            raise Exception(f"Failed to delete object: {e}")
    
    async def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple objects"""
        client = await self._get_client()
        results = {}
        
        # S3 allows batch delete of up to 1000 objects
        batch_size = 1000
        
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i:i + batch_size]
            delete_objects = [{'Key': key} for key in batch_keys]
            
            try:
                response = await client.delete_objects(
                    Bucket=self.bucket,
                    Delete={
                        'Objects': delete_objects,
                        'Quiet': True
                    }
                )
                
                # Mark successful deletes
                for key in batch_keys:
                    results[key] = True
                
                # Mark failed deletes
                for error in response.get('Errors', []):
                    results[error['Key']] = False
                    
            except Exception:
                # Mark all as failed
                for key in batch_keys:
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
        client = await self._get_client()
        
        params = {
            'Bucket': self.bucket,
            'MaxKeys': max_keys
        }
        
        if prefix:
            params['Prefix'] = prefix
        if delimiter:
            params['Delimiter'] = delimiter
        if continuation_token:
            params['ContinuationToken'] = continuation_token
        
        try:
            response = await client.list_objects_v2(**params)
            
            objects = []
            
            # Add regular objects
            for obj in response.get('Contents', []):
                objects.append(StorageObject(
                    key=obj['Key'],
                    size=obj['Size'],
                    last_modified=obj['LastModified'],
                    etag=obj['ETag'].strip('"'),
                    storage_class=obj.get('StorageClass', 'STANDARD')
                ))
            
            # Add common prefixes as directories
            for prefix_info in response.get('CommonPrefixes', []):
                objects.append(StorageObject(
                    key=prefix_info['Prefix'],
                    size=0,
                    last_modified=datetime.now(),
                    content_type='application/x-directory'
                ))
            
            # Get next continuation token
            next_token = response.get('NextContinuationToken')
            
            return objects, next_token
            
        except ClientError as e:
            raise Exception(f"Failed to list objects: {e}")
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata without retrieving content"""
        client = await self._get_client()
        
        try:
            response = await client.head_object(Bucket=self.bucket, Key=key)
            
            return StorageObject(
                key=key,
                size=response['ContentLength'],
                last_modified=response['LastModified'],
                etag=response['ETag'].strip('"'),
                content_type=response.get('ContentType', 'application/octet-stream'),
                metadata=response.get('Metadata', {}),
                storage_class=response.get('StorageClass', 'STANDARD'),
                version_id=response.get('VersionId')
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ObjectNotFoundError(key)
            elif e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied to {key}")
            raise Exception(f"Failed to get object info: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Copy an object within the same storage"""
        client = await self._get_client()
        
        try:
            # Get source object info
            source_info = await self.get_object_info(source_key)
            
            copy_source = {'Bucket': self.bucket, 'Key': source_key}
            
            # Prepare copy parameters
            params = {
                'Bucket': self.bucket,
                'Key': dest_key,
                'CopySource': copy_source,
                'MetadataDirective': 'REPLACE' if metadata else 'COPY'
            }
            
            if metadata:
                params['Metadata'] = metadata
            else:
                params['Metadata'] = source_info.metadata or {}
            
            # Copy object
            response = await client.copy_object(**params)
            
            return await self.get_object_info(dest_key)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ObjectNotFoundError(source_key)
            elif e.response['Error']['Code'] == 'AccessDenied':
                raise StoragePermissionError(f"Access denied")
            raise Exception(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageObject:
        """Move/rename an object"""
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
        client = await self._get_client()
        
        client_method = 'get_object' if operation == 'get' else 'put_object'
        
        request_params = {
            'Bucket': self.bucket,
            'Key': key
        }
        
        if params:
            request_params.update(params)
        
        try:
            url = await client.generate_presigned_url(
                ClientMethod=client_method,
                Params=request_params,
                ExpiresIn=expires_in
            )
            return url
            
        except Exception as e:
            raise Exception(f"Failed to generate presigned URL: {e}")
    
    async def create_multipart_upload(
        self,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Initiate a multipart upload"""
        client = await self._get_client()
        
        params = {
            'Bucket': self.bucket,
            'Key': key
        }
        
        if metadata:
            params['Metadata'] = metadata
        
        if content_type:
            params['ContentType'] = content_type
        
        try:
            response = await client.create_multipart_upload(**params)
            return response['UploadId']
            
        except ClientError as e:
            raise Exception(f"Failed to create multipart upload: {e}")
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> Dict[str, Any]:
        """Upload a part in a multipart upload"""
        client = await self._get_client()
        
        try:
            response = await client.upload_part(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data
            )
            
            return {
                'PartNumber': part_number,
                'ETag': response['ETag']
            }
            
        except ClientError as e:
            raise Exception(f"Failed to upload part: {e}")
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]]
    ) -> StorageObject:
        """Complete a multipart upload"""
        client = await self._get_client()
        
        try:
            response = await client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            return await self.get_object_info(key)
            
        except ClientError as e:
            raise Exception(f"Failed to complete multipart upload: {e}")
    
    async def abort_multipart_upload(
        self,
        key: str,
        upload_id: str
    ) -> None:
        """Abort a multipart upload"""
        client = await self._get_client()
        
        try:
            await client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id
            )
        except ClientError:
            # Ignore errors when aborting
            pass
    
    async def get_quota(self) -> StorageQuota:
        """Get storage quota information"""
        client = await self._get_client()
        
        # S3 doesn't have built-in quotas, so we calculate usage
        total_size = 0
        file_count = 0
        
        try:
            paginator = client.get_paginator('list_objects_v2')
            
            async for page in paginator.paginate(Bucket=self.bucket):
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
                    file_count += 1
            
            # For S3, we don't have a real quota, so return large values
            # In production, this would integrate with account limits
            return StorageQuota(
                total_bytes=1024 * 1024 * 1024 * 1024 * 1024,  # 1PB
                used_bytes=total_size,
                available_bytes=1024 * 1024 * 1024 * 1024 * 1024 - total_size,
                file_count=file_count
            )
            
        except Exception as e:
            raise Exception(f"Failed to get quota: {e}")
    
    async def change_storage_tier(
        self,
        key: str,
        tier: StorageTier
    ) -> StorageObject:
        """Change storage tier of an object"""
        client = await self._get_client()
        
        # Map our tiers to S3 storage classes
        tier_mapping = {
            StorageTier.HOT: 'STANDARD',
            StorageTier.WARM: 'STANDARD_IA',
            StorageTier.COLD: 'GLACIER_IR',
            StorageTier.ARCHIVE: 'DEEP_ARCHIVE'
        }
        
        storage_class = tier_mapping.get(tier)
        if not storage_class:
            raise InvalidStorageOperationError(f"Unsupported tier: {tier}")
        
        try:
            # Copy object to change storage class
            copy_source = {'Bucket': self.bucket, 'Key': key}
            
            await client.copy_object(
                Bucket=self.bucket,
                Key=key,
                CopySource=copy_source,
                StorageClass=storage_class,
                MetadataDirective='COPY'
            )
            
            return await self.get_object_info(key)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ObjectNotFoundError(key)
            raise Exception(f"Failed to change storage tier: {e}")
    
    async def restore_from_archive(
        self,
        key: str,
        days: int = 1,
        tier: str = "Standard"
    ) -> Dict[str, Any]:
        """Restore an archived object"""
        client = await self._get_client()
        
        try:
            # Check if object is in Glacier
            obj_info = await self.get_object_info(key)
            
            if obj_info.storage_class not in ['GLACIER', 'GLACIER_IR', 'DEEP_ARCHIVE']:
                return {
                    'status': 'not_archived',
                    'message': 'Object is not in archive storage'
                }
            
            # Submit restore request
            response = await client.restore_object(
                Bucket=self.bucket,
                Key=key,
                RestoreRequest={
                    'Days': days,
                    'GlacierJobParameters': {
                        'Tier': tier
                    }
                }
            )
            
            return {
                'status': 'restore_initiated',
                'days': days,
                'tier': tier
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'RestoreAlreadyInProgress':
                return {
                    'status': 'restore_in_progress',
                    'message': 'Restore already in progress'
                }
            elif e.response['Error']['Code'] == 'NoSuchKey':
                raise ObjectNotFoundError(key)
            raise Exception(f"Failed to restore from archive: {e}")
    
    async def _multipart_upload(
        self,
        key: str,
        data: bytes,
        metadata: Dict[str, str],
        content_type: str
    ) -> StorageObject:
        """Helper method for multipart upload"""
        upload_id = await self.create_multipart_upload(key, metadata, content_type)
        
        parts = []
        part_number = 1
        
        try:
            # Split data into chunks
            for i in range(0, len(data), self.multipart_chunk_size):
                chunk = data[i:i + self.multipart_chunk_size]
                part_info = await self.upload_part(key, upload_id, part_number, chunk)
                parts.append(part_info)
                part_number += 1
            
            # Complete upload
            return await self.complete_multipart_upload(key, upload_id, parts)
            
        except Exception as e:
            # Abort on error
            await self.abort_multipart_upload(key, upload_id)
            raise