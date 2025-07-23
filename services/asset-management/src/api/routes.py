"""
API routes for Asset Management Service

This module defines all REST API endpoints for asset operations.
"""

from typing import Optional, List, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .dependencies import get_db, get_read_db, get_write_db, get_current_user_id, PaginationParams
from ..services.asset_service import AssetService
from ..models.schemas import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    UploadInitiate, UploadResponse, UploadComplete,
    PaginatedResponse, AssetSearchParams,
    AssetVersionResponse, VersionUploadInitiate,
    BulkAssetUpdate, BulkAssetDelete, BulkAssetTag, BulkAssetMove,
    BulkOperationResult, DuplicateDetectionResult, DuplicateStatistics
)
from ..core.exceptions import (
    AssetNotFoundError, DuplicateAssetError, StorageError,
    ValidationError, QuotaExceededError, PermissionError
)

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("/upload/initiate", response_model=UploadResponse, status_code=status.HTTP_200_OK)
async def initiate_upload(
    upload_data: UploadInitiate,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id),
    authorization: Annotated[str, Header()] = None
):
    """
    Initiate file upload
    
    This endpoint starts the upload process and returns upload details including:
    - Upload ID for tracking
    - Upload URL for sending file data
    - Chunk size for multipart uploads
    - Total number of chunks
    - Expiration time
    """
    try:
        service = AssetService(db, current_user_id)
        result = await service.initiate_upload(upload_data, authorization.split()[1])
        await service.close()
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("upload_initiation_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate upload")


@router.post("/upload/complete", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def complete_upload(
    complete_data: UploadComplete,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id),
    authorization: Annotated[str, Header()] = None
):
    """
    Complete file upload and create asset
    
    This endpoint finalizes the upload process and creates the asset record.
    For multipart uploads, provide the list of uploaded parts.
    """
    try:
        service = AssetService(db, current_user_id)
        result = await service.complete_upload(complete_data, authorization.split()[1])
        await service.close()
        
        logger.info(
            "asset_created_via_upload",
            asset_id=str(result.id),
            user_id=str(current_user_id),
            upload_id=complete_data.upload_id
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        logger.error("upload_completion_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete upload")


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create asset from existing file
    
    This endpoint creates an asset record for a file that already exists in storage.
    Use this for importing existing files or creating assets from processed files.
    """
    try:
        # This would typically include file_info from storage service
        # For now, we'll raise not implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Direct asset creation not yet implemented. Use upload endpoints."
        )
        
    except Exception as e:
        logger.error("asset_creation_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create asset")


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get asset by ID
    
    Returns detailed information about a specific asset including:
    - Basic metadata
    - Technical metadata
    - Storage information
    - Tags and relationships
    - Version information
    """
    try:
        service = AssetService(db, current_user_id)
        return await service.get_asset(asset_id)
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("asset_retrieval_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve asset")


@router.get("/", response_model=PaginatedResponse)
async def list_assets(
    # Pagination
    pagination: PaginationParams = Depends(),
    # Search/filter parameters
    query: Optional[str] = Query(None, description="Search in name, display_name, description"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    owner_id: Optional[UUID] = Query(None, description="Filter by owner"),
    mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
    min_size: Optional[int] = Query(None, description="Minimum file size in bytes"),
    max_size: Optional[int] = Query(None, description="Maximum file size in bytes"),
    storage_tier: Optional[str] = Query(None, description="Filter by storage tier"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (all must match)"),
    # Dependencies
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List assets with filtering and pagination
    
    Returns a paginated list of assets that the user has access to.
    Supports various filters and search capabilities.
    """
    try:
        # Build search params
        search_params = None
        if any([query, asset_type, status, project_id, owner_id, mime_type, 
                min_size, max_size, storage_tier, is_public is not None, tags]):
            search_params = AssetSearchParams(
                query=query,
                asset_type=asset_type,
                status=status,
                project_id=project_id,
                owner_id=owner_id,
                mime_type=mime_type,
                min_size=min_size,
                max_size=max_size,
                storage_tier=storage_tier,
                is_public=is_public,
                tags=tags
            )
        
        service = AssetService(db, current_user_id)
        return await service.list_assets(pagination, search_params)
        
    except Exception as e:
        logger.error("asset_listing_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list assets")


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    update_data: AssetUpdate,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update asset metadata
    
    Updates modifiable fields of an asset. Only the asset owner can update.
    """
    try:
        service = AssetService(db, current_user_id)
        return await service.update_asset(asset_id, update_data)
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("asset_update_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update asset")


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    permanent: bool = Query(False, description="Permanently delete (cannot be undone)"),
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete asset
    
    By default performs a soft delete (marks as deleted but keeps data).
    Use permanent=true for hard delete (removes all data).
    """
    try:
        service = AssetService(db, current_user_id)
        await service.delete_asset(asset_id, permanent)
        
        logger.info(
            "asset_deleted",
            asset_id=str(asset_id),
            user_id=str(current_user_id),
            permanent=permanent
        )
        
        return None
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("asset_deletion_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete asset")


# Bulk operation endpoints
@router.post("/bulk/update", response_model=BulkOperationResult)
async def bulk_update_assets(
    bulk_data: BulkAssetUpdate,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update multiple assets at once
    
    Apply the same updates to multiple assets in a single operation.
    """
    try:
        service = AssetService(db, current_user_id)
        results = await service.bulk_update_assets(
            bulk_data.asset_ids,
            bulk_data.update_data
        )
        
        return BulkOperationResult(
            successful=results["successful"],
            failed=results["failed"],
            total=results["total"],
            success_count=results["success_count"],
            failure_count=results["failure_count"]
        )
        
    except Exception as e:
        logger.error("bulk_update_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bulk update failed")


@router.post("/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete_assets(
    bulk_data: BulkAssetDelete,
    db: AsyncSession = Depends(get_write_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete multiple assets at once
    
    Perform bulk deletion of assets. Can be soft or permanent delete.
    """
    try:
        service = AssetService(db, current_user_id)
        results = await service.bulk_delete_assets(
            bulk_data.asset_ids,
            bulk_data.permanent
        )
        
        return BulkOperationResult(
            successful=results["successful"],
            failed=results["failed"],
            total=results["total"],
            success_count=results["success_count"],
            failure_count=results["failure_count"]
        )
        
    except Exception as e:
        logger.error("bulk_delete_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bulk delete failed")


@router.post("/bulk/tag", response_model=BulkOperationResult)
async def bulk_tag_assets(
    bulk_data: BulkAssetTag,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Add or remove tags from multiple assets
    
    Bulk operation to manage tags on multiple assets.
    """
    try:
        if not bulk_data.tags_to_add and not bulk_data.tags_to_remove:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify tags to add or remove"
            )
        
        service = AssetService(db, current_user_id)
        results = await service.bulk_tag_assets(
            bulk_data.asset_ids,
            bulk_data.tags_to_add,
            bulk_data.tags_to_remove
        )
        
        return BulkOperationResult(
            successful=results["successful"],
            failed=results["failed"],
            total=results["total"],
            success_count=results["success_count"],
            failure_count=results["failure_count"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("bulk_tag_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bulk tag operation failed")


@router.post("/bulk/move", response_model=BulkOperationResult)
async def bulk_move_assets(
    bulk_data: BulkAssetMove,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Move multiple assets to a different project
    
    Bulk operation to move assets between projects.
    """
    try:
        service = AssetService(db, current_user_id)
        results = await service.bulk_move_assets(
            bulk_data.asset_ids,
            bulk_data.target_project_id
        )
        
        return BulkOperationResult(
            successful=results["successful"],
            failed=results["failed"],
            total=results["total"],
            success_count=results["success_count"],
            failure_count=results["failure_count"]
        )
        
    except Exception as e:
        logger.error("bulk_move_failed", error=str(e), user_id=str(current_user_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bulk move failed")


# Version management endpoints
@router.post("/{asset_id}/versions/upload/initiate", response_model=UploadResponse)
async def initiate_version_upload(
    asset_id: UUID,
    upload_data: VersionUploadInitiate,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id),
    authorization: Annotated[str, Header()] = None
):
    """
    Initiate upload for a new version of an asset
    
    This starts the upload process for a new version of an existing asset.
    """
    try:
        # Convert to regular upload initiate
        initiate_data = UploadInitiate(
            filename=upload_data.filename,
            file_size=upload_data.file_size,
            mime_type=upload_data.mime_type,
            asset_data=AssetCreate(
                name=upload_data.filename,
                display_name=upload_data.filename
            )
        )
        
        service = AssetService(db, current_user_id)
        result = await service.initiate_upload(initiate_data, authorization.split()[1])
        await service.close()
        
        # Store asset_id and version info in session for completion
        # In production, this would be stored in Redis or similar
        result.metadata = {
            "asset_id": str(asset_id),
            "comment": upload_data.comment,
            "version_label": upload_data.version_label
        }
        
        return result
        
    except Exception as e:
        logger.error("version_upload_initiation_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate version upload")


@router.get("/{asset_id}/versions", response_model=List[AssetVersionResponse])
async def list_asset_versions(
    asset_id: UUID,
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List all versions of an asset
    
    Returns version history sorted by version number (newest first).
    """
    try:
        service = AssetService(db, current_user_id)
        versions = await service.list_asset_versions(asset_id)
        
        return [
            AssetVersionResponse(
                id=v.id,
                asset_id=v.asset_id,
                version_number=v.version_number,
                version_label=v.version_label,
                file_path=v.file_path,
                file_size=v.file_size,
                file_hash=v.file_hash,
                comment=v.comment,
                is_current=v.is_current,
                created_by=v.created_by,
                created_at=v.created_at,
                storage_driver=v.storage_driver,
                storage_path=v.storage_path,
                storage_tier=v.storage_tier
            )
            for v in versions
        ]
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("version_listing_failed", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list versions")


@router.get("/{asset_id}/versions/{version_number}", response_model=AssetVersionResponse)
async def get_asset_version(
    asset_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get specific version of an asset
    
    Returns detailed information about a specific version.
    """
    try:
        service = AssetService(db, current_user_id)
        version = await service.get_asset_version(asset_id, version_number)
        
        return AssetVersionResponse(
            id=version.id,
            asset_id=version.asset_id,
            version_number=version.version_number,
            version_label=version.version_label,
            file_path=version.file_path,
            file_size=version.file_size,
            file_hash=version.file_hash,
            comment=version.comment,
            is_current=version.is_current,
            created_by=version.created_by,
            created_at=version.created_at,
            storage_driver=version.storage_driver,
            storage_path=version.storage_path,
            storage_tier=version.storage_tier
        )
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("version_retrieval_failed", error=str(e), asset_id=str(asset_id), version=version_number)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve version")


@router.post("/{asset_id}/versions/{version_number}/set-current", response_model=AssetVersionResponse)
async def set_current_version(
    asset_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Set a specific version as the current version
    
    This will update the asset to use the specified version's file.
    """
    try:
        service = AssetService(db, current_user_id)
        version = await service.set_current_version(asset_id, version_number)
        
        return AssetVersionResponse(
            id=version.id,
            asset_id=version.asset_id,
            version_number=version.version_number,
            version_label=version.version_label,
            file_path=version.file_path,
            file_size=version.file_size,
            file_hash=version.file_hash,
            comment=version.comment,
            is_current=version.is_current,
            created_by=version.created_by,
            created_at=version.created_at,
            storage_driver=version.storage_driver,
            storage_path=version.storage_path,
            storage_tier=version.storage_tier
        )
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error("version_set_current_failed", error=str(e), asset_id=str(asset_id), version=version_number)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set current version")


@router.delete("/{asset_id}/versions/{version_number}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_version(
    asset_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a specific version
    
    Cannot delete the current version or the only version of an asset.
    """
    try:
        service = AssetService(db, current_user_id)
        await service.delete_asset_version(asset_id, version_number)
        
        logger.info(
            "asset_version_deleted",
            asset_id=str(asset_id),
            version_number=version_number,
            user_id=str(current_user_id)
        )
        
        return None
        
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("version_deletion_failed", error=str(e), asset_id=str(asset_id), version=version_number)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete version")


# Validation endpoints
@router.post("/validate/filename")
async def validate_filename(
    filename: str = Query(..., description="Filename to validate"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Validate a filename before upload
    
    Checks filename against validation rules including:
    - Allowed/blocked extensions
    - Security patterns
    - Naming conventions
    """
    try:
        from ..core.validators import FileValidator
        
        validator = FileValidator()
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "file_info": {}
        }
        
        validator._validate_filename(filename, results)
        
        return {
            "filename": filename,
            "valid": results["valid"],
            "errors": results["errors"],
            "warnings": results["warnings"],
            "extension": results["file_info"].get("extension"),
            "allowed": results["valid"]
        }
        
    except Exception as e:
        logger.error("filename_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Validation failed")


@router.post("/validate/upload")
async def validate_upload_params(
    filename: str = Query(..., description="Filename"),
    file_size: int = Query(..., gt=0, description="File size in bytes"),
    mime_type: Optional[str] = Query(None, description="MIME type"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Pre-validate upload parameters
    
    Validates upload parameters before initiating upload:
    - File size limits
    - File type restrictions
    - Extension validation
    """
    try:
        from ..core.validators import FileValidator, MediaFileValidator
        
        # Choose appropriate validator
        is_media = mime_type and mime_type.startswith(('video/', 'audio/', 'image/'))
        validator = MediaFileValidator() if is_media else FileValidator()
        
        errors = []
        warnings = []
        
        # Validate file size
        if file_size > validator.rules.max_file_size:
            errors.append(f"File size exceeds maximum allowed size of {validator.rules.max_file_size} bytes")
        elif file_size < validator.rules.min_file_size:
            errors.append(f"File size below minimum allowed size of {validator.rules.min_file_size} bytes")
        
        # Validate filename
        results = {"valid": True, "errors": [], "warnings": [], "file_info": {}}
        validator._validate_filename(filename, results)
        errors.extend(results["errors"])
        warnings.extend(results["warnings"])
        
        # Validate MIME type
        if mime_type:
            validator._validate_mime_type(mime_type, results)
            errors.extend(results["errors"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "file_info": {
                "filename": filename,
                "size": file_size,
                "mime_type": mime_type,
                "extension": results["file_info"].get("extension")
            }
        }
        
    except Exception as e:
        logger.error("upload_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Validation failed")


# Duplicate detection endpoints
@router.post("/duplicates/check")
async def check_for_duplicates(
    filename: str = Query(..., description="Filename to check"),
    file_size: int = Query(..., gt=0, description="File size in bytes"),
    file_hash: Optional[str] = Query(None, description="SHA-256 hash"),
    project_id: Optional[UUID] = Query(None, description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Check if a file would be a duplicate before uploading
    
    Returns information about exact and similar duplicates found.
    """
    try:
        from ..services.duplicate_detection import DuplicateDetectionService
        
        dup_service = DuplicateDetectionService(db)
        result = await dup_service.check_for_duplicates(
            filename=filename,
            file_size=file_size,
            file_hash=file_hash,
            project_id=project_id
        )
        
        # Convert Asset objects to IDs for response
        return {
            "has_exact_duplicates": result.has_exact_duplicates,
            "has_similar_duplicates": result.has_similar_duplicates,
            "exact_duplicates": [str(asset.id) for asset in result.exact_duplicates],
            "similar_duplicates": [str(asset.id) for asset in result.similar_duplicates],
            "duplicate_count": result.duplicate_count
        }
        
    except Exception as e:
        logger.error("duplicate_check_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Duplicate check failed")


@router.get("/duplicates/statistics", response_model=DuplicateStatistics)
async def get_duplicate_statistics(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get statistics about duplicate assets
    
    Returns comprehensive statistics including:
    - Total duplicate count
    - Wasted storage space
    - Duplicate percentage
    """
    try:
        from ..services.duplicate_detection import DuplicateDetectionService
        
        dup_service = DuplicateDetectionService(db)
        stats = await dup_service.get_duplicate_statistics(project_id)
        
        return DuplicateStatistics(**stats)
        
    except Exception as e:
        logger.error("duplicate_statistics_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get statistics")


@router.get("/duplicates/groups")
async def find_duplicate_groups(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    min_group_size: int = Query(2, ge=2, description="Minimum duplicates in group"),
    db: AsyncSession = Depends(get_read_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Find all groups of duplicate assets
    
    Returns groups of assets that share the same file hash,
    sorted by wasted space.
    """
    try:
        from ..services.duplicate_detection import DuplicateDetectionService
        
        dup_service = DuplicateDetectionService(db)
        groups = await dup_service.find_all_duplicate_groups(project_id, min_group_size)
        
        return {
            "groups": groups,
            "total_groups": len(groups),
            "total_wasted_space": sum(g["wasted_space"] for g in groups)
        }
        
    except Exception as e:
        logger.error("duplicate_groups_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to find groups")


@router.post("/duplicates/{file_hash}/suggest-removal")
async def suggest_duplicate_removal(
    file_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Suggest which duplicate to keep and which to remove
    
    Uses intelligent criteria to determine the best asset to keep.
    """
    try:
        from ..services.duplicate_detection import DuplicateDetectionService
        
        dup_service = DuplicateDetectionService(db)
        keep, remove = await dup_service.suggest_duplicates_for_removal(file_hash)
        
        if not keep:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No duplicates found")
        
        return {
            "keep": {
                "id": str(keep.id),
                "name": keep.name,
                "created_at": keep.created_at,
                "reason": "Original/Most metadata"
            },
            "remove": [
                {
                    "id": str(asset.id),
                    "name": asset.name,
                    "created_at": asset.created_at,
                    "size": asset.file_size
                }
                for asset in remove
            ],
            "space_to_recover": sum(asset.file_size for asset in remove)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("duplicate_suggestion_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to suggest removal")


# Virus scanner status endpoint
@router.get("/virus-scanner/status", tags=["admin"])
async def get_virus_scanner_status(
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get virus scanner status
    
    Returns the status of all configured virus scanners.
    Admin endpoint for monitoring scanner health.
    """
    try:
        from ..services.virus_scanner import get_virus_scanner
        
        scanner = get_virus_scanner()
        status = await scanner.get_scanner_status()
        
        return status
        
    except Exception as e:
        logger.error("virus_scanner_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scanner status"
        )


# Health check endpoint
@router.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Service health check"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        return {
            "status": "healthy",
            "service": "asset-management",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )