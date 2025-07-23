"""
Storage API Routes

This module defines all API endpoints for the storage abstraction service.
"""

import os
import io
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    UploadFile, File, Query, Body, BackgroundTasks
)
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from ..core.config import get_settings
from ..core.interfaces import (
    StorageObject, StorageQuota, StorageTier,
    ObjectNotFoundError, StorageQuotaExceededError,
    StoragePermissionError, InvalidStorageOperationError
)
from ..services import get_storage_service, StorageService
from ..services.resume_upload_service import (
    get_resume_service, ResumableUpload, UploadProgress
)
from ..services.tier_migration_service import (
    get_migration_service, MigrationPolicy, MigrationTask, MigrationStats
)
from ..services.quota_management_service import (
    get_quota_service, QuotaType, QuotaAction, QuotaPolicy as ServiceQuotaPolicy,
    QuotaUsage, QuotaAlert
)
from ..services.encryption_service import (
    get_encryption_service, EncryptionAlgorithm, EncryptionKey as ServiceEncryptionKey,
    EncryptionMetadata
)
from ..services.analytics_service import (
    get_analytics_service, ReportType, TimeRange, AnalyticsReport as ServiceAnalyticsReport,
    UsageStats, PerformanceStats
)


logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


# Request/Response Models
class StorageObjectResponse(BaseModel):
    """Storage object response model"""
    key: str
    size: int
    last_modified: datetime
    etag: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    storage_class: Optional[str] = None
    version_id: Optional[str] = None
    
    class Config:
        orm_mode = True


class ListObjectsResponse(BaseModel):
    """List objects response model"""
    objects: List[StorageObjectResponse]
    continuation_token: Optional[str] = None
    total: int


class StorageQuotaResponse(BaseModel):
    """Storage quota response model"""
    total_bytes: int
    used_bytes: int
    available_bytes: int
    usage_percentage: float
    file_count: Optional[int] = None


class PresignedUrlResponse(BaseModel):
    """Presigned URL response model"""
    url: str
    expires_at: datetime


class MultipartUploadResponse(BaseModel):
    """Multipart upload response model"""
    upload_id: str
    key: str


class UploadPartResponse(BaseModel):
    """Upload part response model"""
    part_number: int
    etag: str
    size: int


class CompleteMultipartRequest(BaseModel):
    """Complete multipart upload request"""
    parts: List[Dict[str, Any]]


class CopyObjectRequest(BaseModel):
    """Copy object request model"""
    source_key: str
    dest_key: str
    source_driver: Optional[str] = None
    dest_driver: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class MoveObjectRequest(BaseModel):
    """Move object request model"""
    source_key: str
    dest_key: str
    source_driver: Optional[str] = None
    dest_driver: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class ChangeTierRequest(BaseModel):
    """Change storage tier request"""
    tier: str = Field(..., regex="^(hot|warm|cold|archive)$")


class RestoreRequest(BaseModel):
    """Restore from archive request"""
    days: int = Field(1, ge=1, le=30)
    tier: str = Field("Standard", regex="^(Expedited|Standard|Bulk)$")


class ResumableUploadRequest(BaseModel):
    """Create resumable upload request"""
    total_size: int = Field(..., gt=0, description="Total file size in bytes")
    chunk_size: int = Field(5242880, ge=1048576, le=104857600, description="Chunk size (1MB-100MB)")
    metadata: Optional[Dict[str, str]] = None
    content_type: Optional[str] = None
    ttl_hours: int = Field(24, ge=1, le=168, description="Session TTL in hours (1-168)")


class ResumableUploadResponse(BaseModel):
    """Resumable upload response"""
    upload_id: str
    key: str
    total_size: int
    uploaded_size: int
    chunk_size: int
    chunks_completed: List[int]
    expires_at: datetime
    
    
class UploadChunkResponse(BaseModel):
    """Upload chunk response"""
    chunk_index: int
    uploaded_size: int
    total_size: int
    percentage: float


class MigrationRequest(BaseModel):
    """Migration request model"""
    target_tier: str = Field(..., regex="^(hot|warm|cold|archive)$")
    source_driver: Optional[str] = None
    target_driver: Optional[str] = None
    force: bool = False


class BatchMigrationRequest(BaseModel):
    """Batch migration request model"""
    keys: List[str]
    target_tier: str = Field(..., regex="^(hot|warm|cold|archive)$")
    source_driver: Optional[str] = None
    target_driver: Optional[str] = None


class MigrationPolicyRequest(BaseModel):
    """Migration policy request model"""
    name: str
    description: str
    enabled: bool = True
    hot_to_warm_days: Optional[int] = None
    warm_to_cold_days: Optional[int] = None
    cold_to_archive_days: Optional[int] = None
    access_count_threshold: Optional[int] = None
    last_access_days: Optional[int] = None
    min_file_size: Optional[int] = None
    max_file_size: Optional[int] = None
    include_patterns: List[str] = []
    exclude_patterns: List[str] = []
    migration_window_start: Optional[str] = None
    migration_window_end: Optional[str] = None


class MigrationTaskResponse(BaseModel):
    """Migration task response model"""
    task_id: str
    object_key: str
    source_tier: str
    target_tier: str
    source_driver: str
    target_driver: Optional[str]
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class MigrationStatsResponse(BaseModel):
    """Migration statistics response"""
    total_objects: int
    total_bytes: int
    migrated_objects: int
    migrated_bytes: int
    failed_objects: int
    avg_migration_time: float
    tier_distribution: Dict[str, int]


# Quota Management Models
class QuotaPolicyRequest(BaseModel):
    """Create/update quota policy request"""
    name: str
    description: str
    quota_type: str = Field(..., regex="^(user|group|organization|driver|global)$")
    entity_id: str
    max_storage_bytes: Optional[int] = None
    max_file_count: Optional[int] = None
    max_file_size: Optional[int] = None
    soft_limit_percentage: float = Field(0.8, ge=0.0, le=1.0)
    hard_limit_percentage: float = Field(1.0, ge=0.0, le=1.0)
    action_on_soft_limit: str = Field("warn", regex="^(block|warn|alert)$")
    action_on_hard_limit: str = Field("block", regex="^(block|warn|alert)$")
    enabled: bool = True
    driver_quotas: Optional[Dict[str, Dict[str, Any]]] = None


class QuotaPolicyResponse(BaseModel):
    """Quota policy response"""
    id: str
    name: str
    description: str
    quota_type: str
    entity_id: str
    max_storage_bytes: Optional[int]
    max_file_count: Optional[int]
    max_file_size: Optional[int]
    soft_limit_percentage: float
    hard_limit_percentage: float
    action_on_soft_limit: str
    action_on_hard_limit: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    driver_quotas: Dict[str, Dict[str, Any]]


class QuotaStatusResponse(BaseModel):
    """Quota status response"""
    entity_id: str
    entity_type: str
    quotas: List[Dict[str, Any]]


class QuotaAlertResponse(BaseModel):
    """Quota alert response"""
    id: str
    policy_id: str
    entity_id: str
    alert_type: str
    message: str
    threshold_percentage: float
    current_usage_bytes: int
    max_allowed_bytes: int
    created_at: datetime
    acknowledged: bool
    acknowledged_at: Optional[datetime]


# Encryption Models
class EncryptionKeyRequest(BaseModel):
    """Create encryption key request"""
    key_id: str
    algorithm: str = Field(..., regex="^(aes_256_cbc|aes_256_gcm|fernet|chacha20_poly1305)$")
    password: Optional[str] = None


class EncryptionKeyResponse(BaseModel):
    """Encryption key response"""
    key_id: str
    algorithm: str
    created_at: datetime
    last_used: datetime
    rotation_required: bool
    metadata: Dict[str, Any]


class EncryptFileRequest(BaseModel):
    """Encrypt file request"""
    key_id: Optional[str] = None
    algorithm: Optional[str] = Field(None, regex="^(aes_256_cbc|aes_256_gcm|fernet|chacha20_poly1305)$")


class EncryptionMetadataResponse(BaseModel):
    """Encryption metadata response"""
    key_id: str
    algorithm: str
    iv: Optional[str] = None
    salt: Optional[str] = None
    file_hash: Optional[str] = None
    original_size: Optional[int] = None
    encrypted_at: datetime
    checksum: Optional[str] = None


# Analytics Models
class GenerateReportRequest(BaseModel):
    """Generate analytics report request"""
    report_type: str = Field(..., regex="^(storage_usage|performance|tier_distribution|access_patterns|quota_usage|driver_health|cost_analysis)$")
    time_range: str = Field(..., regex="^(hour|day|week|month|quarter|year)$")
    filters: Optional[Dict[str, Any]] = None


class AnalyticsReportResponse(BaseModel):
    """Analytics report response"""
    report_id: str
    report_type: str
    time_range: str
    start_time: datetime
    end_time: datetime
    generated_at: datetime
    data: Dict[str, Any]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""
    total_objects: int
    total_bytes: int
    total_files: int
    avg_file_size: float
    median_file_size: float
    largest_file_size: int
    smallest_file_size: int
    by_driver: Dict[str, Dict[str, Any]]
    by_tier: Dict[str, Dict[str, Any]]
    by_file_type: Dict[str, Dict[str, Any]]
    growth_rate: float


class PerformanceStatsResponse(BaseModel):
    """Performance statistics response"""
    avg_upload_speed: float
    avg_download_speed: float
    avg_response_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    p95_response_time: float
    p99_response_time: float
    by_operation: Dict[str, Dict[str, Any]]
    by_driver: Dict[str, Dict[str, Any]]


# Endpoints
@router.get("/drivers")
async def list_storage_drivers(
    storage_service: StorageService = Depends(get_storage_service)
) -> Dict[str, Any]:
    """List available storage drivers and their status"""
    return await storage_service.get_driver_info()


@router.head("/{key:path}")
async def check_object_exists(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Check if an object exists"""
    try:
        exists = await storage_service.exists(key, driver)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object not found: {key}"
            )
        return {"exists": True}
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )


@router.get("/{key:path}/info", response_model=StorageObjectResponse)
async def get_object_info(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get object metadata without downloading content"""
    try:
        obj = await storage_service.get_object_info(key, driver)
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )


@router.get("/{key:path}")
async def download_object(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    stream: bool = Query(True, description="Stream the response"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Download an object"""
    try:
        # Get object info first
        obj_info = await storage_service.get_object_info(key, driver)
        
        if stream:
            # Stream response
            async def stream_generator():
                async for chunk in storage_service.get_object_stream(key, driver=driver):
                    yield chunk
            
            return StreamingResponse(
                stream_generator(),
                media_type=obj_info.content_type or 'application/octet-stream',
                headers={
                    "Content-Length": str(obj_info.size),
                    "ETag": obj_info.etag or "",
                    "Last-Modified": obj_info.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
                }
            )
        else:
            # Return full content
            content = await storage_service.get_object(key, driver)
            return StreamingResponse(
                io.BytesIO(content),
                media_type=obj_info.content_type or 'application/octet-stream',
                headers={
                    "Content-Length": str(len(content)),
                    "ETag": obj_info.etag or "",
                    "Last-Modified": obj_info.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
                }
            )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )
    except StoragePermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/{key:path}", response_model=StorageObjectResponse)
async def upload_object(
    key: str,
    file: UploadFile = File(...),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    metadata: Optional[str] = Query(None, description="JSON metadata"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Upload an object"""
    try:
        # Parse metadata if provided
        file_metadata = None
        if metadata:
            import json
            try:
                file_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid metadata JSON"
                )
        
        # Check file size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
            )
        
        # Upload file
        obj = await storage_service.put_object(
            key=key,
            data=file.file,
            metadata=file_metadata,
            content_type=file.content_type,
            driver=driver
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
        
    except StorageQuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=str(e)
        )
    except StoragePermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload failed for {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed"
        )


@router.delete("/{key:path}")
async def delete_object(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete an object"""
    try:
        deleted = await storage_service.delete_object(key, driver)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object not found: {key}"
            )
        return {"message": f"Object {key} deleted successfully"}
    except StoragePermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/delete-batch")
async def delete_objects_batch(
    keys: List[str] = Body(..., description="List of object keys to delete"),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete multiple objects"""
    try:
        results = await storage_service.delete_objects(keys, driver)
        
        success_count = sum(1 for v in results.values() if v)
        failed_keys = [k for k, v in results.items() if not v]
        
        return {
            "total": len(keys),
            "deleted": success_count,
            "failed": len(failed_keys),
            "failed_keys": failed_keys,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch delete failed"
        )


@router.get("/", response_model=ListObjectsResponse)
async def list_objects(
    prefix: Optional[str] = Query(None, description="Filter by prefix"),
    delimiter: Optional[str] = Query(None, description="Delimiter for hierarchical listing"),
    max_keys: int = Query(1000, ge=1, le=5000, description="Maximum objects to return"),
    continuation_token: Optional[str] = Query(None, description="Pagination token"),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """List objects with optional filtering"""
    try:
        objects, next_token = await storage_service.list_objects(
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
            continuation_token=continuation_token,
            driver=driver
        )
        
        return ListObjectsResponse(
            objects=[
                StorageObjectResponse(
                    key=obj.key,
                    size=obj.size,
                    last_modified=obj.last_modified,
                    etag=obj.etag,
                    content_type=obj.content_type,
                    metadata=obj.metadata,
                    storage_class=obj.storage_class
                )
                for obj in objects
            ],
            continuation_token=next_token,
            total=len(objects)
        )
    except Exception as e:
        logger.error(f"List objects failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list objects"
        )


@router.post("/copy")
async def copy_object(
    request: CopyObjectRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Copy an object"""
    try:
        obj = await storage_service.copy_object(
            source_key=request.source_key,
            dest_key=request.dest_key,
            metadata=request.metadata,
            source_driver=request.source_driver,
            dest_driver=request.dest_driver
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source object not found: {request.source_key}"
        )
    except StoragePermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/move")
async def move_object(
    request: MoveObjectRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Move an object"""
    try:
        obj = await storage_service.move_object(
            source_key=request.source_key,
            dest_key=request.dest_key,
            metadata=request.metadata,
            source_driver=request.source_driver,
            dest_driver=request.dest_driver
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source object not found: {request.source_key}"
        )
    except StoragePermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/{key:path}/presigned-url", response_model=PresignedUrlResponse)
async def create_presigned_url(
    key: str,
    operation: str = Query("get", regex="^(get|put)$", description="Operation type"),
    expires_in: int = Query(3600, ge=60, le=604800, description="URL expiry in seconds"),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Generate a presigned URL for direct access"""
    try:
        url = await storage_service.get_presigned_url(
            key=key,
            operation=operation,
            expires_in=expires_in,
            driver=driver
        )
        
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        return PresignedUrlResponse(
            url=url,
            expires_at=expires_at
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )


@router.post("/multipart/{key:path}/start", response_model=MultipartUploadResponse)
async def start_multipart_upload(
    key: str,
    content_type: Optional[str] = Query(None, description="Content type"),
    metadata: Optional[str] = Query(None, description="JSON metadata"),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Start a multipart upload"""
    try:
        # Parse metadata if provided
        file_metadata = None
        if metadata:
            import json
            try:
                file_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid metadata JSON"
                )
        
        upload_id = await storage_service.create_multipart_upload(
            key=key,
            metadata=file_metadata,
            content_type=content_type,
            driver=driver
        )
        
        return MultipartUploadResponse(
            upload_id=upload_id,
            key=key
        )
    except Exception as e:
        logger.error(f"Failed to start multipart upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start multipart upload"
        )


@router.put("/multipart/{key:path}/{upload_id}/part/{part_number}", response_model=UploadPartResponse)
async def upload_part(
    key: str,
    upload_id: str,
    part_number: int = Field(..., ge=1, le=10000),
    file: UploadFile = File(...),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Upload a part in a multipart upload"""
    try:
        content = await file.read()
        
        part_info = await storage_service.upload_part(
            key=key,
            upload_id=upload_id,
            part_number=part_number,
            data=content,
            driver=driver
        )
        
        return UploadPartResponse(
            part_number=part_info["PartNumber"],
            etag=part_info["ETag"],
            size=len(content)
        )
    except Exception as e:
        logger.error(f"Failed to upload part: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload part"
        )


@router.post("/multipart/{key:path}/{upload_id}/complete", response_model=StorageObjectResponse)
async def complete_multipart_upload(
    key: str,
    upload_id: str,
    request: CompleteMultipartRequest,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Complete a multipart upload"""
    try:
        obj = await storage_service.complete_multipart_upload(
            key=key,
            upload_id=upload_id,
            parts=request.parts,
            driver=driver
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except Exception as e:
        logger.error(f"Failed to complete multipart upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete multipart upload"
        )


@router.delete("/multipart/{key:path}/{upload_id}")
async def abort_multipart_upload(
    key: str,
    upload_id: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Abort a multipart upload"""
    try:
        await storage_service.abort_multipart_upload(
            key=key,
            upload_id=upload_id,
            driver=driver
        )
        
        return {"message": "Multipart upload aborted successfully"}
    except Exception as e:
        logger.error(f"Failed to abort multipart upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort multipart upload"
        )


@router.get("/quota", response_model=StorageQuotaResponse)
async def get_storage_quota(
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get storage quota information"""
    try:
        quota = await storage_service.get_quota(driver)
        
        return StorageQuotaResponse(
            total_bytes=quota.total_bytes,
            used_bytes=quota.used_bytes,
            available_bytes=quota.available_bytes,
            usage_percentage=quota.usage_percentage,
            file_count=quota.file_count
        )
    except Exception as e:
        logger.error(f"Failed to get quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage quota"
        )


@router.post("/{key:path}/tier")
async def change_storage_tier(
    key: str,
    request: ChangeTierRequest,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Change storage tier of an object"""
    try:
        tier_map = {
            "hot": StorageTier.HOT,
            "warm": StorageTier.WARM,
            "cold": StorageTier.COLD,
            "archive": StorageTier.ARCHIVE
        }
        
        tier = tier_map[request.tier]
        
        obj = await storage_service.change_storage_tier(
            key=key,
            tier=tier,
            driver=driver
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Storage tier management not supported by this driver"
        )


@router.post("/{key:path}/restore")
async def restore_from_archive(
    key: str,
    request: RestoreRequest,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Restore an archived object"""
    try:
        result = await storage_service.restore_from_archive(
            key=key,
            days=request.days,
            tier=request.tier,
            driver=driver
        )
        
        return result
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Archive restoration not supported by this driver"
        )


# Resume Upload Endpoints
@router.post("/resume/{key:path}/start", response_model=ResumableUploadResponse)
async def start_resumable_upload(
    key: str,
    request: ResumableUploadRequest,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service),
    resume_service = Depends(get_resume_service)
):
    """Start a resumable upload session"""
    try:
        # Verify driver exists
        storage_driver = storage_service.get_driver(driver)
        
        # Create resumable upload session
        session = await resume_service.create_resumable_upload(
            key=key,
            total_size=request.total_size,
            chunk_size=request.chunk_size,
            driver_name=driver or storage_service._default_driver,
            metadata=request.metadata,
            content_type=request.content_type,
            ttl_hours=request.ttl_hours
        )
        
        return ResumableUploadResponse(
            upload_id=session.upload_id,
            key=session.key,
            total_size=session.total_size,
            uploaded_size=session.uploaded_size,
            chunk_size=session.chunk_size,
            chunks_completed=session.chunks_completed,
            expires_at=session.expires_at
        )
    except Exception as e:
        logger.error(f"Failed to start resumable upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start resumable upload"
        )


@router.put("/resume/{upload_id}/chunk/{chunk_index}", response_model=UploadChunkResponse)
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Field(..., ge=0),
    file: UploadFile = File(...),
    resume_service = Depends(get_resume_service)
):
    """Upload a chunk for a resumable upload"""
    try:
        # Read chunk data
        chunk_data = await file.read()
        
        # Upload chunk
        session = await resume_service.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            data=chunk_data
        )
        
        percentage = round((session.uploaded_size / session.total_size) * 100, 2)
        
        return UploadChunkResponse(
            chunk_index=chunk_index,
            uploaded_size=session.uploaded_size,
            total_size=session.total_size,
            percentage=percentage
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to upload chunk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload chunk"
        )


@router.post("/resume/{upload_id}/complete", response_model=StorageObjectResponse)
async def complete_resumable_upload(
    upload_id: str,
    verify_checksum: bool = Query(True, description="Verify file checksum"),
    storage_service: StorageService = Depends(get_storage_service),
    resume_service = Depends(get_resume_service)
):
    """Complete a resumable upload"""
    try:
        # Get session to determine driver
        session = await resume_service.get_upload_status(upload_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session not found: {upload_id}"
            )
        
        # Get storage driver
        storage_driver = storage_service.get_driver(session.driver_name)
        
        # Complete upload
        obj = await resume_service.complete_upload(
            upload_id=upload_id,
            storage_driver=storage_driver,
            verify_checksum=verify_checksum
        )
        
        return StorageObjectResponse(
            key=obj.key,
            size=obj.size,
            last_modified=obj.last_modified,
            etag=obj.etag,
            content_type=obj.content_type,
            metadata=obj.metadata,
            storage_class=obj.storage_class,
            version_id=obj.version_id
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to complete resumable upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete resumable upload"
        )


@router.delete("/resume/{upload_id}")
async def abort_resumable_upload(
    upload_id: str,
    resume_service = Depends(get_resume_service)
):
    """Abort a resumable upload"""
    try:
        await resume_service.abort_upload(upload_id)
        return {"message": f"Upload {upload_id} aborted successfully"}
    except Exception as e:
        logger.error(f"Failed to abort resumable upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort resumable upload"
        )


@router.get("/resume/{upload_id}/status", response_model=ResumableUploadResponse)
async def get_upload_status(
    upload_id: str,
    resume_service = Depends(get_resume_service)
):
    """Get the status of a resumable upload"""
    session = await resume_service.get_upload_status(upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session not found: {upload_id}"
        )
    
    return ResumableUploadResponse(
        upload_id=session.upload_id,
        key=session.key,
        total_size=session.total_size,
        uploaded_size=session.uploaded_size,
        chunk_size=session.chunk_size,
        chunks_completed=session.chunks_completed,
        expires_at=session.expires_at
    )


@router.get("/resume", response_model=List[ResumableUploadResponse])
async def list_resumable_uploads(
    key_prefix: Optional[str] = Query(None, description="Filter by key prefix"),
    resume_service = Depends(get_resume_service)
):
    """List active resumable upload sessions"""
    sessions = await resume_service.list_uploads(key_prefix)
    
    return [
        ResumableUploadResponse(
            upload_id=session.upload_id,
            key=session.key,
            total_size=session.total_size,
            uploaded_size=session.uploaded_size,
            chunk_size=session.chunk_size,
            chunks_completed=session.chunks_completed,
            expires_at=session.expires_at
        )
        for session in sessions
    ]


# Tier Migration Endpoints
@router.post("/{key:path}/migrate", response_model=MigrationTaskResponse)
async def migrate_object(
    key: str,
    request: MigrationRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Migrate an object to a different storage tier"""
    try:
        migration_service = await get_migration_service(storage_service)
        
        # Map tier string to enum
        tier_map = {
            "hot": StorageTier.HOT,
            "warm": StorageTier.WARM,
            "cold": StorageTier.COLD,
            "archive": StorageTier.ARCHIVE
        }
        target_tier = tier_map[request.target_tier]
        
        task = await migration_service.migrate_object(
            key=key,
            target_tier=target_tier,
            source_driver=request.source_driver,
            target_driver=request.target_driver,
            force=request.force
        )
        
        return MigrationTaskResponse(
            task_id=task.task_id,
            object_key=task.object_key,
            source_tier=task.source_tier.value,
            target_tier=task.target_tier.value,
            source_driver=task.source_driver,
            target_driver=task.target_driver,
            status=task.status.value,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object not found: {key}"
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to migrate object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to migrate object"
        )


@router.post("/migrate/batch", response_model=List[MigrationTaskResponse])
async def migrate_objects_batch(
    request: BatchMigrationRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Migrate multiple objects to a different storage tier"""
    try:
        migration_service = await get_migration_service(storage_service)
        
        # Map tier string to enum
        tier_map = {
            "hot": StorageTier.HOT,
            "warm": StorageTier.WARM,
            "cold": StorageTier.COLD,
            "archive": StorageTier.ARCHIVE
        }
        target_tier = tier_map[request.target_tier]
        
        tasks = await migration_service.migrate_objects_batch(
            keys=request.keys,
            target_tier=target_tier,
            source_driver=request.source_driver,
            target_driver=request.target_driver
        )
        
        return [
            MigrationTaskResponse(
                task_id=task.task_id,
                object_key=task.object_key,
                source_tier=task.source_tier.value,
                target_tier=task.target_tier.value,
                source_driver=task.source_driver,
                target_driver=task.target_driver,
                status=task.status.value,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error_message=task.error_message
            )
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"Failed to migrate objects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to migrate objects"
        )


@router.get("/migrate/task/{task_id}", response_model=MigrationTaskResponse)
async def get_migration_status(
    task_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get status of a migration task"""
    migration_service = await get_migration_service(storage_service)
    task = await migration_service.get_migration_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Migration task not found: {task_id}"
        )
    
    return MigrationTaskResponse(
        task_id=task.task_id,
        object_key=task.object_key,
        source_tier=task.source_tier.value,
        target_tier=task.target_tier.value,
        source_driver=task.source_driver,
        target_driver=task.target_driver,
        status=task.status.value,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message
    )


@router.get("/migrate/stats", response_model=MigrationStatsResponse)
async def get_migration_stats(
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get migration statistics"""
    try:
        migration_service = await get_migration_service(storage_service)
        stats = await migration_service.get_migration_stats(driver)
        
        return MigrationStatsResponse(
            total_objects=stats.total_objects,
            total_bytes=stats.total_bytes,
            migrated_objects=stats.migrated_objects,
            migrated_bytes=stats.migrated_bytes,
            failed_objects=stats.failed_objects,
            avg_migration_time=stats.avg_migration_time,
            tier_distribution=stats.tier_distribution
        )
    except Exception as e:
        logger.error(f"Failed to get migration stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get migration statistics"
        )


@router.post("/migrate/policy", status_code=status.HTTP_201_CREATED)
async def create_migration_policy(
    request: MigrationPolicyRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Create a new migration policy"""
    try:
        migration_service = await get_migration_service(storage_service)
        
        from ..services.tier_migration_service import MigrationPolicy as ServiceMigrationPolicy
        
        policy = ServiceMigrationPolicy(
            name=request.name,
            description=request.description,
            enabled=request.enabled,
            hot_to_warm_days=request.hot_to_warm_days,
            warm_to_cold_days=request.warm_to_cold_days,
            cold_to_archive_days=request.cold_to_archive_days,
            access_count_threshold=request.access_count_threshold,
            last_access_days=request.last_access_days,
            min_file_size=request.min_file_size,
            max_file_size=request.max_file_size,
            include_patterns=request.include_patterns,
            exclude_patterns=request.exclude_patterns,
            migration_window_start=request.migration_window_start,
            migration_window_end=request.migration_window_end
        )
        
        migration_service.add_policy(policy)
        
        return {"message": f"Policy {request.name} created successfully"}
    except Exception as e:
        logger.error(f"Failed to create policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create migration policy"
        )


@router.get("/migrate/policies")
async def list_migration_policies(
    storage_service: StorageService = Depends(get_storage_service)
):
    """List all migration policies"""
    migration_service = await get_migration_service(storage_service)
    policies = migration_service.get_policies()
    
    return {
        name: policy.to_dict()
        for name, policy in policies.items()
    }


@router.post("/migrate/policy/{policy_name}/apply")
async def apply_migration_policy(
    policy_name: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    dry_run: bool = Query(False, description="Perform dry run without migrations"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Apply a migration policy"""
    try:
        migration_service = await get_migration_service(storage_service)
        
        eligible_objects, stats = await migration_service.apply_policy(
            policy_name=policy_name,
            driver_name=driver,
            dry_run=dry_run
        )
        
        return {
            "policy": policy_name,
            "dry_run": dry_run,
            "eligible_objects": len(eligible_objects),
            "stats": {
                "total_objects": stats.total_objects,
                "migrated_objects": stats.migrated_objects,
                "failed_objects": stats.failed_objects
            },
            "objects": eligible_objects[:100] if dry_run else []
        }
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to apply policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply migration policy"
        )


# Quota Management Endpoints
@router.post("/quota/policies", response_model=QuotaPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_quota_policy(
    request: QuotaPolicyRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Create a new quota policy"""
    try:
        quota_service = await get_quota_service(storage_service)
        
        import uuid
        policy_id = str(uuid.uuid4())
        
        # Map string enums to service enums
        quota_type = QuotaType(request.quota_type)
        action_on_soft_limit = QuotaAction(request.action_on_soft_limit)
        action_on_hard_limit = QuotaAction(request.action_on_hard_limit)
        
        policy = ServiceQuotaPolicy(
            id=policy_id,
            name=request.name,
            description=request.description,
            quota_type=quota_type,
            entity_id=request.entity_id,
            max_storage_bytes=request.max_storage_bytes,
            max_file_count=request.max_file_count,
            max_file_size=request.max_file_size,
            soft_limit_percentage=request.soft_limit_percentage,
            hard_limit_percentage=request.hard_limit_percentage,
            action_on_soft_limit=action_on_soft_limit,
            action_on_hard_limit=action_on_hard_limit,
            enabled=request.enabled,
            driver_quotas=request.driver_quotas or {}
        )
        
        quota_service.create_policy(policy)
        
        return QuotaPolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            quota_type=policy.quota_type.value,
            entity_id=policy.entity_id,
            max_storage_bytes=policy.max_storage_bytes,
            max_file_count=policy.max_file_count,
            max_file_size=policy.max_file_size,
            soft_limit_percentage=policy.soft_limit_percentage,
            hard_limit_percentage=policy.hard_limit_percentage,
            action_on_soft_limit=policy.action_on_soft_limit.value,
            action_on_hard_limit=policy.action_on_hard_limit.value,
            enabled=policy.enabled,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            driver_quotas=policy.driver_quotas
        )
    except Exception as e:
        logger.error(f"Failed to create quota policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quota policy"
        )


@router.get("/quota/policies", response_model=List[QuotaPolicyResponse])
async def list_quota_policies(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """List quota policies"""
    try:
        quota_service = await get_quota_service(storage_service)
        
        entity_type_enum = None
        if entity_type:
            entity_type_enum = QuotaType(entity_type)
        
        policies = quota_service.get_policies(entity_type_enum, entity_id)
        
        return [
            QuotaPolicyResponse(
                id=policy.id,
                name=policy.name,
                description=policy.description,
                quota_type=policy.quota_type.value,
                entity_id=policy.entity_id,
                max_storage_bytes=policy.max_storage_bytes,
                max_file_count=policy.max_file_count,
                max_file_size=policy.max_file_size,
                soft_limit_percentage=policy.soft_limit_percentage,
                hard_limit_percentage=policy.hard_limit_percentage,
                action_on_soft_limit=policy.action_on_soft_limit.value,
                action_on_hard_limit=policy.action_on_hard_limit.value,
                enabled=policy.enabled,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
                driver_quotas=policy.driver_quotas
            )
            for policy in policies
        ]
    except Exception as e:
        logger.error(f"Failed to list quota policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list quota policies"
        )


@router.get("/quota/policies/{policy_id}", response_model=QuotaPolicyResponse)
async def get_quota_policy(
    policy_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get a specific quota policy"""
    try:
        quota_service = await get_quota_service(storage_service)
        policies = quota_service.get_policies()
        
        if policy_id not in [p.id for p in policies]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quota policy not found: {policy_id}"
            )
        
        policy = next(p for p in policies if p.id == policy_id)
        
        return QuotaPolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            quota_type=policy.quota_type.value,
            entity_id=policy.entity_id,
            max_storage_bytes=policy.max_storage_bytes,
            max_file_count=policy.max_file_count,
            max_file_size=policy.max_file_size,
            soft_limit_percentage=policy.soft_limit_percentage,
            hard_limit_percentage=policy.hard_limit_percentage,
            action_on_soft_limit=policy.action_on_soft_limit.value,
            action_on_hard_limit=policy.action_on_hard_limit.value,
            enabled=policy.enabled,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            driver_quotas=policy.driver_quotas
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quota policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quota policy"
        )


@router.put("/quota/policies/{policy_id}", response_model=QuotaPolicyResponse)
async def update_quota_policy(
    policy_id: str,
    updates: Dict[str, Any] = Body(...),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Update a quota policy"""
    try:
        quota_service = await get_quota_service(storage_service)
        
        # Convert enum strings to enums if provided
        if "action_on_soft_limit" in updates:
            updates["action_on_soft_limit"] = QuotaAction(updates["action_on_soft_limit"])
        if "action_on_hard_limit" in updates:
            updates["action_on_hard_limit"] = QuotaAction(updates["action_on_hard_limit"])
        
        policy = quota_service.update_policy(policy_id, updates)
        
        return QuotaPolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            quota_type=policy.quota_type.value,
            entity_id=policy.entity_id,
            max_storage_bytes=policy.max_storage_bytes,
            max_file_count=policy.max_file_count,
            max_file_size=policy.max_file_size,
            soft_limit_percentage=policy.soft_limit_percentage,
            hard_limit_percentage=policy.hard_limit_percentage,
            action_on_soft_limit=policy.action_on_soft_limit.value,
            action_on_hard_limit=policy.action_on_hard_limit.value,
            enabled=policy.enabled,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
            driver_quotas=policy.driver_quotas
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update quota policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update quota policy"
        )


@router.delete("/quota/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quota_policy(
    policy_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete a quota policy"""
    try:
        quota_service = await get_quota_service(storage_service)
        quota_service.delete_policy(policy_id)
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete quota policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete quota policy"
        )


@router.get("/quota/status/{entity_type}/{entity_id}", response_model=QuotaStatusResponse)
async def get_quota_status(
    entity_type: str,
    entity_id: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get quota status for an entity"""
    try:
        quota_service = await get_quota_service(storage_service)
        
        entity_type_enum = QuotaType(entity_type)
        status = await quota_service.get_quota_status(entity_id, entity_type_enum, driver)
        
        return QuotaStatusResponse(
            entity_id=status["entity_id"],
            entity_type=status["entity_type"],
            quotas=status["quotas"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {entity_type}"
        )
    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quota status"
        )


@router.get("/quota/alerts", response_model=List[QuotaAlertResponse])
async def list_quota_alerts(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """List quota alerts"""
    try:
        quota_service = await get_quota_service(storage_service)
        alerts = quota_service.get_alerts(entity_id, acknowledged)
        
        return [
            QuotaAlertResponse(
                id=alert.id,
                policy_id=alert.policy_id,
                entity_id=alert.entity_id,
                alert_type=alert.alert_type.value,
                message=alert.message,
                threshold_percentage=alert.threshold_percentage,
                current_usage_bytes=alert.current_usage_bytes,
                max_allowed_bytes=alert.max_allowed_bytes,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged,
                acknowledged_at=alert.acknowledged_at
            )
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Failed to list quota alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list quota alerts"
        )


@router.post("/quota/alerts/{alert_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge_quota_alert(
    alert_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Acknowledge a quota alert"""
    try:
        quota_service = await get_quota_service(storage_service)
        quota_service.acknowledge_alert(alert_id)
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert"
        )


@router.post("/quota/check")
async def check_quota(
    entity_id: str = Body(..., embed=True),
    entity_type: str = Body(..., embed=True),
    size_to_add: int = Body(..., embed=True),
    driver_name: Optional[str] = Body(None, embed=True),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Check if adding storage would exceed quota"""
    try:
        quota_service = await get_quota_service(storage_service)
        
        entity_type_enum = QuotaType(entity_type)
        allowed, reason = await quota_service.check_quota(
            entity_id, entity_type_enum, size_to_add, driver_name
        )
        
        return {
            "allowed": allowed,
            "reason": reason,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "size_to_add": size_to_add
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {entity_type}"
        )
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check quota"
        )


# Encryption Endpoints
@router.post("/encryption/keys", response_model=EncryptionKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_encryption_key(
    request: EncryptionKeyRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Create a new encryption key"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        
        algorithm = EncryptionAlgorithm(request.algorithm)
        key = encryption_service.create_key(
            request.key_id,
            algorithm,
            request.password
        )
        
        return EncryptionKeyResponse(
            key_id=key.key_id,
            algorithm=key.algorithm.value,
            created_at=key.created_at,
            last_used=key.last_used,
            rotation_required=key.rotation_required,
            metadata=key.metadata
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create encryption key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create encryption key"
        )


@router.get("/encryption/keys", response_model=List[EncryptionKeyResponse])
async def list_encryption_keys(
    storage_service: StorageService = Depends(get_storage_service)
):
    """List all encryption keys"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        keys = encryption_service.get_keys()
        
        return [
            EncryptionKeyResponse(
                key_id=key.key_id,
                algorithm=key.algorithm.value,
                created_at=key.created_at,
                last_used=key.last_used,
                rotation_required=key.rotation_required,
                metadata=key.metadata
            )
            for key in keys
        ]
    except Exception as e:
        logger.error(f"Failed to list encryption keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list encryption keys"
        )


@router.post("/encryption/keys/{key_id}/rotate", response_model=EncryptionKeyResponse)
async def rotate_encryption_key(
    key_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Rotate an encryption key"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        new_key = encryption_service.rotate_key(key_id)
        
        return EncryptionKeyResponse(
            key_id=new_key.key_id,
            algorithm=new_key.algorithm.value,
            created_at=new_key.created_at,
            last_used=new_key.last_used,
            rotation_required=new_key.rotation_required,
            metadata=new_key.metadata
        )
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to rotate encryption key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate encryption key"
        )


@router.delete("/encryption/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_encryption_key(
    key_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete an encryption key"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        encryption_service.delete_key(key_id)
    except InvalidStorageOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete encryption key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete encryption key"
        )


@router.post("/{key:path}/encrypt", response_model=EncryptionMetadataResponse)
async def encrypt_file(
    key: str,
    file: UploadFile = File(...),
    request: EncryptFileRequest = Body(...),
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Encrypt and upload a file"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        
        # Read file data
        file_data = await file.read()
        
        # Encrypt the file
        algorithm = EncryptionAlgorithm(request.algorithm) if request.algorithm else None
        encrypted_data, metadata = await encryption_service.encrypt_file(
            file_data,
            request.key_id,
            algorithm
        )
        
        # Store the encrypted file
        await storage_service.put_object(
            key=f"{key}.encrypted",
            data=encrypted_data,
            content_type="application/octet-stream",
            metadata={
                "original_filename": file.filename,
                "encryption_metadata": metadata.to_dict()
            },
            driver=driver
        )
        
        return EncryptionMetadataResponse(
            key_id=metadata.key_id,
            algorithm=metadata.algorithm.value,
            iv=base64.b64encode(metadata.iv).decode() if metadata.iv else None,
            salt=base64.b64encode(metadata.salt).decode() if metadata.salt else None,
            file_hash=metadata.file_hash,
            original_size=metadata.original_size,
            encrypted_at=metadata.encrypted_at,
            checksum=metadata.checksum
        )
    except Exception as e:
        logger.error(f"Failed to encrypt file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt file"
        )


@router.get("/{key:path}/decrypt")
async def decrypt_file(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Decrypt and download a file"""
    try:
        encryption_service = await get_encryption_service(storage_service)
        
        # Get encrypted file
        encrypted_key = f"{key}.encrypted"
        obj_info = await storage_service.get_object_info(encrypted_key, driver)
        
        # Extract encryption metadata
        if not obj_info.metadata or "encryption_metadata" not in obj_info.metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not encrypted or metadata is missing"
            )
        
        metadata_dict = obj_info.metadata["encryption_metadata"]
        if isinstance(metadata_dict, str):
            import json
            metadata_dict = json.loads(metadata_dict)
        
        metadata = EncryptionMetadata.from_dict(metadata_dict)
        
        # Get encrypted data
        encrypted_data = await storage_service.get_object(encrypted_key, driver)
        
        # Decrypt the file
        decrypted_data = await encryption_service.decrypt_file(encrypted_data, metadata)
        
        # Return decrypted file
        original_filename = obj_info.metadata.get("original_filename", key)
        
        return StreamingResponse(
            io.BytesIO(decrypted_data),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=\"{original_filename}\"",
                "Content-Length": str(len(decrypted_data))
            }
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encrypted file not found: {key}"
        )
    except Exception as e:
        logger.error(f"Failed to decrypt file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt file"
        )


@router.get("/{key:path}/encryption-info", response_model=EncryptionMetadataResponse)
async def get_encryption_info(
    key: str,
    driver: Optional[str] = Query(None, description="Storage driver name"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get encryption information for a file"""
    try:
        # Get encrypted file metadata
        encrypted_key = f"{key}.encrypted"
        obj_info = await storage_service.get_object_info(encrypted_key, driver)
        
        # Extract encryption metadata
        if not obj_info.metadata or "encryption_metadata" not in obj_info.metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not encrypted or metadata is missing"
            )
        
        metadata_dict = obj_info.metadata["encryption_metadata"]
        if isinstance(metadata_dict, str):
            import json
            metadata_dict = json.loads(metadata_dict)
        
        metadata = EncryptionMetadata.from_dict(metadata_dict)
        
        return EncryptionMetadataResponse(
            key_id=metadata.key_id,
            algorithm=metadata.algorithm.value,
            iv=base64.b64encode(metadata.iv).decode() if metadata.iv else None,
            salt=base64.b64encode(metadata.salt).decode() if metadata.salt else None,
            file_hash=metadata.file_hash,
            original_size=metadata.original_size,
            encrypted_at=metadata.encrypted_at,
            checksum=metadata.checksum
        )
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encrypted file not found: {key}"
        )
    except Exception as e:
        logger.error(f"Failed to get encryption info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get encryption information"
        )


# Analytics Endpoints
@router.get("/analytics/usage", response_model=UsageStatsResponse)
async def get_usage_statistics(
    driver: Optional[str] = Query(None, description="Filter by storage driver"),
    time_range: Optional[str] = Query("month", regex="^(hour|day|week|month|quarter|year)$"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get storage usage statistics"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        
        time_range_enum = TimeRange(time_range) if time_range else None
        stats = await analytics_service.get_usage_stats(
            driver_name=driver,
            time_range=time_range_enum
        )
        
        return UsageStatsResponse(
            total_objects=stats.total_objects,
            total_bytes=stats.total_bytes,
            total_files=stats.total_files,
            avg_file_size=stats.avg_file_size,
            median_file_size=stats.median_file_size,
            largest_file_size=stats.largest_file_size,
            smallest_file_size=stats.smallest_file_size,
            by_driver=stats.by_driver,
            by_tier=stats.by_tier,
            by_file_type=stats.by_file_type,
            growth_rate=stats.growth_rate
        )
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )


@router.get("/analytics/performance", response_model=PerformanceStatsResponse)
async def get_performance_statistics(
    driver: Optional[str] = Query(None, description="Filter by storage driver"),
    time_range: Optional[str] = Query("day", regex="^(hour|day|week|month|quarter|year)$"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get storage performance statistics"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        
        time_range_enum = TimeRange(time_range) if time_range else None
        stats = await analytics_service.get_performance_stats(
            driver_name=driver,
            time_range=time_range_enum
        )
        
        return PerformanceStatsResponse(
            avg_upload_speed=stats.avg_upload_speed,
            avg_download_speed=stats.avg_download_speed,
            avg_response_time=stats.avg_response_time,
            total_requests=stats.total_requests,
            successful_requests=stats.successful_requests,
            failed_requests=stats.failed_requests,
            success_rate=stats.success_rate,
            p95_response_time=stats.p95_response_time,
            p99_response_time=stats.p99_response_time,
            by_operation=stats.by_operation,
            by_driver=stats.by_driver
        )
    except Exception as e:
        logger.error(f"Failed to get performance statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance statistics"
        )


@router.post("/analytics/reports", response_model=AnalyticsReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_analytics_report(
    request: GenerateReportRequest,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Generate an analytics report"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        
        report_type = ReportType(request.report_type)
        time_range = TimeRange(request.time_range)
        
        report = await analytics_service.generate_report(
            report_type=report_type,
            time_range=time_range,
            filters=request.filters
        )
        
        return AnalyticsReportResponse(
            report_id=report.report_id,
            report_type=report.report_type.value,
            time_range=report.time_range.value,
            start_time=report.start_time,
            end_time=report.end_time,
            generated_at=report.generated_at,
            data=report.data,
            summary=report.summary,
            metadata=report.metadata
        )
    except Exception as e:
        logger.error(f"Failed to generate analytics report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics report"
        )


@router.get("/analytics/reports", response_model=List[AnalyticsReportResponse])
async def list_analytics_reports(
    report_type: Optional[str] = Query(None, regex="^(storage_usage|performance|tier_distribution|access_patterns|quota_usage|driver_health|cost_analysis)$"),
    limit: int = Query(50, ge=1, le=100),
    storage_service: StorageService = Depends(get_storage_service)
):
    """List generated analytics reports"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        
        report_type_enum = ReportType(report_type) if report_type else None
        reports = analytics_service.list_reports(
            report_type=report_type_enum,
            limit=limit
        )
        
        return [
            AnalyticsReportResponse(
                report_id=report.report_id,
                report_type=report.report_type.value,
                time_range=report.time_range.value,
                start_time=report.start_time,
                end_time=report.end_time,
                generated_at=report.generated_at,
                data=report.data,
                summary=report.summary,
                metadata=report.metadata
            )
            for report in reports
        ]
    except Exception as e:
        logger.error(f"Failed to list analytics reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list analytics reports"
        )


@router.get("/analytics/reports/{report_id}", response_model=AnalyticsReportResponse)
async def get_analytics_report(
    report_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Get a specific analytics report"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        report = analytics_service.get_report(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analytics report not found: {report_id}"
            )
        
        return AnalyticsReportResponse(
            report_id=report.report_id,
            report_type=report.report_type.value,
            time_range=report.time_range.value,
            start_time=report.start_time,
            end_time=report.end_time,
            generated_at=report.generated_at,
            data=report.data,
            summary=report.summary,
            metadata=report.metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics report"
        )


@router.delete("/analytics/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analytics_report(
    report_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete an analytics report"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        success = analytics_service.delete_report(report_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analytics report not found: {report_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analytics report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete analytics report"
        )


@router.post("/analytics/metrics")
async def record_metric(
    driver_name: str = Body(..., embed=True),
    metric_type: str = Body(..., embed=True),
    value: float = Body(..., embed=True),
    unit: str = Body("", embed=True),
    metadata: Optional[Dict[str, Any]] = Body(None, embed=True),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Record a custom metric"""
    try:
        analytics_service = await get_analytics_service(storage_service)
        
        analytics_service.record_metric(
            driver_name=driver_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            metadata=metadata
        )
        
        return {"message": "Metric recorded successfully"}
    except Exception as e:
        logger.error(f"Failed to record metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record metric"
        )