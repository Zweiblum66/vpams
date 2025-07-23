"""
Asset service for handling asset operations

This module provides the business logic for asset management.
"""

import os
import hashlib
import mimetypes
from typing import Optional, List, Dict, Any, Tuple, BinaryIO
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from pathlib import Path
import aiofiles
import httpx
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
import structlog

from ..db.models import (
    Asset, AssetVersion, AssetStatus, AssetType, 
    Tag, AssetRelationship, asset_tags
)
from ..models.schemas import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    UploadInitiate, UploadResponse, UploadComplete,
    PaginationParams, PaginatedResponse, AssetSearchParams
)
from ..core.config import get_settings
from ..core.exceptions import (
    AssetNotFoundError, DuplicateAssetError, StorageError,
    ValidationError, QuotaExceededError, PermissionError
)
from ..core.validators import FileValidator, MediaFileValidator

logger = structlog.get_logger()


class AssetService:
    """Service for managing assets"""
    
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()
        self._storage_client = None
        self._upload_sessions = {}  # In-memory upload session tracking
    
    @property
    async def storage_client(self) -> httpx.AsyncClient:
        """Get or create storage service client"""
        if self._storage_client is None:
            self._storage_client = httpx.AsyncClient(
                base_url=self.settings.storage_service_url,
                timeout=self.settings.storage_service_timeout
            )
        return self._storage_client
    
    async def close(self):
        """Close connections"""
        if self._storage_client:
            await self._storage_client.aclose()
    
    def _is_media_file(self, mime_type: str) -> bool:
        """Check if file is a media file (video, audio, or image)"""
        if mime_type:
            return mime_type.startswith(('video/', 'audio/', 'image/'))
        return False
    
    def _determine_asset_type(self, mime_type: str, filename: str) -> AssetType:
        """Determine asset type from MIME type and filename"""
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            if mime_type.startswith('video/'):
                return AssetType.VIDEO
            elif mime_type.startswith('audio/'):
                return AssetType.AUDIO
            elif mime_type.startswith('image/'):
                return AssetType.IMAGE
            elif mime_type in ['text/vtt', 'application/x-subrip']:
                return AssetType.SUBTITLE
            elif mime_type in ['application/pdf', 'text/plain', 'text/html']:
                return AssetType.DOCUMENT
        
        # Check by extension
        ext = Path(filename).suffix.lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return AssetType.VIDEO
        elif ext in ['.mp3', '.wav', '.aac', '.flac', '.ogg']:
            return AssetType.AUDIO
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            return AssetType.IMAGE
        elif ext in ['.vtt', '.srt', '.sub']:
            return AssetType.SUBTITLE
        elif ext in ['.pdf', '.txt', '.doc', '.docx']:
            return AssetType.DOCUMENT
        elif ext in ['.prproj', '.aep', '.fcpx']:
            return AssetType.PROJECT
        
        return AssetType.OTHER
    
    async def initiate_upload(
        self,
        upload_data: UploadInitiate,
        auth_token: str
    ) -> UploadResponse:
        """Initiate file upload"""
        try:
            # Create validator
            validator = FileValidator()
            
            # Pre-validate file parameters
            if upload_data.file_size > validator.rules.max_file_size:
                raise ValidationError(
                    f"File size exceeds maximum allowed size of {validator.rules.max_file_size} bytes"
                )
            
            if upload_data.file_size < validator.rules.min_file_size:
                raise ValidationError(
                    f"File size below minimum allowed size of {validator.rules.min_file_size} bytes"
                )
            
            # Validate filename
            if upload_data.filename:
                path = Path(upload_data.filename)
                extension = path.suffix.lower()
                
                # Check blocked extensions
                if extension in validator.rules.blocked_extensions:
                    raise ValidationError(f"File extension '{extension}' is not allowed")
                
                # Check allowed extensions if specified
                if validator.rules.allowed_extensions and extension not in validator.rules.allowed_extensions:
                    raise ValidationError(f"File extension '{extension}' is not supported")
            
            # Validate MIME type if provided
            if upload_data.mime_type:
                # Simple MIME type validation
                allowed = False
                for allowed_type in validator.rules.allowed_mime_types:
                    if allowed_type.endswith('/*'):
                        prefix = allowed_type[:-2]
                        if upload_data.mime_type.startswith(prefix):
                            allowed = True
                            break
                    elif upload_data.mime_type == allowed_type:
                        allowed = True
                        break
                
                if not allowed:
                    raise ValidationError(f"MIME type '{upload_data.mime_type}' is not allowed")
            
            # Generate upload session ID
            upload_id = str(uuid4())
            
            # Calculate chunks
            chunk_size = self.settings.chunk_size
            total_chunks = (upload_data.file_size + chunk_size - 1) // chunk_size
            
            # Determine storage driver
            storage_driver = self.settings.default_storage_driver
            
            # Create upload session with storage service
            client = await self.storage_client
            
            # For multipart uploads
            if upload_data.file_size > chunk_size:
                response = await client.post(
                    f"/api/v1/storage/upload/initiate",
                    json={
                        "filename": upload_data.filename,
                        "size": upload_data.file_size,
                        "driver": storage_driver
                    },
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                if response.status_code != 200:
                    raise StorageError("Failed to initiate upload with storage service")
                
                storage_data = response.json()
                upload_url = storage_data.get("upload_url")
            else:
                # For small files, use direct upload
                upload_url = f"{self.settings.storage_service_url}/api/v1/storage/upload/direct"
            
            # Store upload session info
            session_info = {
                "upload_id": upload_id,
                "filename": upload_data.filename,
                "file_size": upload_data.file_size,
                "mime_type": upload_data.mime_type,
                "asset_data": upload_data.asset_data,
                "storage_driver": storage_driver,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "uploaded_chunks": set(),
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=24),
                "storage_upload_id": storage_data.get("upload_id") if upload_data.file_size > chunk_size else None
            }
            
            self._upload_sessions[upload_id] = session_info
            
            logger.info(
                "upload_initiated",
                upload_id=upload_id,
                filename=upload_data.filename,
                file_size=upload_data.file_size,
                total_chunks=total_chunks
            )
            
            return UploadResponse(
                upload_id=upload_id,
                upload_url=upload_url,
                chunk_size=chunk_size,
                total_chunks=total_chunks,
                expires_at=session_info["expires_at"]
            )
            
        except Exception as e:
            logger.error("upload_initiation_failed", error=str(e))
            raise
    
    async def complete_upload(
        self,
        complete_data: UploadComplete,
        auth_token: str
    ) -> AssetResponse:
        """Complete file upload and create asset"""
        try:
            # Get upload session
            session = self._upload_sessions.get(complete_data.upload_id)
            if not session:
                raise ValidationError("Invalid or expired upload session")
            
            # Check if session is expired
            if datetime.utcnow() > session["expires_at"]:
                del self._upload_sessions[complete_data.upload_id]
                raise ValidationError("Upload session has expired")
            
            # Complete storage upload if multipart
            if session.get("storage_upload_id"):
                client = await self.storage_client
                response = await client.post(
                    f"/api/v1/storage/upload/complete",
                    json={
                        "upload_id": session["storage_upload_id"],
                        "parts": complete_data.parts
                    },
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                if response.status_code != 200:
                    raise StorageError("Failed to complete upload with storage service")
                
                storage_result = response.json()
                storage_path = storage_result["path"]
                file_hash = storage_result.get("hash") or complete_data.file_hash
            else:
                # For direct uploads, the file should already be uploaded
                storage_path = f"assets/{self.user_id}/{session['filename']}"
                file_hash = complete_data.file_hash
            
            # Validate the uploaded file
            validator = MediaFileValidator() if self._is_media_file(session["mime_type"]) else FileValidator()
            validation_results = await validator.validate_file(
                file_path=storage_path,  # This would need actual file path from storage
                original_filename=session["filename"],
                expected_size=session["file_size"],
                expected_hash=file_hash
            )
            
            if not validation_results["valid"]:
                # Clean up failed upload
                # TODO: Delete file from storage
                raise ValidationError(
                    f"File validation failed: {'; '.join(validation_results['errors'])}"
                )
            
            # Log any warnings
            for warning in validation_results.get("warnings", []):
                logger.warning("file_validation_warning", warning=warning, filename=session["filename"])
            
            # Check for duplicates
            from .duplicate_detection import DuplicateDetectionService
            dup_service = DuplicateDetectionService(self.db)
            
            duplicate_check = await dup_service.check_for_duplicates(
                filename=session["filename"],
                file_size=session["file_size"],
                file_hash=file_hash,
                project_id=session["asset_data"].project_id if session.get("asset_data") else None
            )
            
            if duplicate_check.has_exact_duplicates:
                logger.warning(
                    "exact_duplicate_detected",
                    filename=session["filename"],
                    duplicate_count=len(duplicate_check.exact_duplicates),
                    duplicate_ids=[str(id) for id in duplicate_check.exact_duplicates]
                )
                # Note: We still allow the upload but log the warning
                # In a production system, you might want to reject or handle differently
            
            # Determine asset type
            asset_type = self._determine_asset_type(
                session["mime_type"],
                session["filename"]
            )
            
            # Extract file extension
            file_extension = Path(session["filename"]).suffix.lower()
            
            # Create asset data
            asset_data = session.get("asset_data") or AssetCreate(
                name=session["filename"],
                display_name=session["filename"]
            )
            
            # Create asset record
            asset = Asset(
                name=asset_data.name,
                display_name=asset_data.display_name or asset_data.name,
                description=asset_data.description,
                file_path=storage_path,
                file_size=session["file_size"],
                file_hash=file_hash,
                mime_type=session["mime_type"],
                file_extension=file_extension,
                asset_type=asset_type,
                status=AssetStatus.ACTIVE,
                storage_driver=session["storage_driver"],
                storage_path=storage_path,
                storage_tier="hot",
                owner_id=self.user_id,
                project_id=asset_data.project_id,
                is_public=asset_data.is_public,
                technical_metadata=asset_data.metadata or {}
            )
            
            self.db.add(asset)
            
            # Add tags if provided
            if asset_data.tags:
                await self._add_tags_to_asset(asset, asset_data.tags)
            
            # Create initial version
            version = AssetVersion(
                asset_id=asset.id,
                version_number=1,
                version_label="v1.0",
                file_path=storage_path,
                file_size=session["file_size"],
                file_hash=file_hash,
                comment="Initial upload",
                is_current=True,
                created_by=self.user_id,
                storage_driver=session["storage_driver"],
                storage_path=storage_path,
                storage_tier="hot"
            )
            self.db.add(version)
            
            await self.db.commit()
            await self.db.refresh(asset)
            
            # Clean up upload session
            del self._upload_sessions[complete_data.upload_id]
            
            logger.info(
                "asset_created",
                asset_id=str(asset.id),
                name=asset.name,
                type=asset.asset_type.value,
                size=asset.file_size
            )
            
            # Convert to response model
            return await self._asset_to_response(asset)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("upload_completion_failed", error=str(e))
            raise
    
    async def create_asset_from_existing(
        self,
        asset_data: AssetCreate,
        file_info: Dict[str, Any]
    ) -> AssetResponse:
        """Create asset from existing file in storage"""
        try:
            # Validate required file info
            required_fields = ["path", "size", "driver"]
            for field in required_fields:
                if field not in file_info:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Determine asset type
            mime_type = file_info.get("mime_type")
            asset_type = self._determine_asset_type(mime_type, asset_data.name)
            
            # Extract file extension
            file_extension = Path(asset_data.name).suffix.lower()
            
            # Create asset record
            asset = Asset(
                name=asset_data.name,
                display_name=asset_data.display_name or asset_data.name,
                description=asset_data.description,
                file_path=file_info["path"],
                file_size=file_info["size"],
                file_hash=file_info.get("hash"),
                mime_type=mime_type,
                file_extension=file_extension,
                asset_type=asset_type,
                status=AssetStatus.ACTIVE,
                storage_driver=file_info["driver"],
                storage_path=file_info["path"],
                storage_tier=file_info.get("tier", "hot"),
                owner_id=self.user_id,
                project_id=asset_data.project_id,
                is_public=asset_data.is_public,
                technical_metadata=asset_data.metadata or {}
            )
            
            self.db.add(asset)
            
            # Add tags if provided
            if asset_data.tags:
                await self._add_tags_to_asset(asset, asset_data.tags)
            
            # Create initial version
            version = AssetVersion(
                asset_id=asset.id,
                version_number=1,
                version_label="v1.0",
                file_path=file_info["path"],
                file_size=file_info["size"],
                file_hash=file_info.get("hash"),
                comment="Imported from existing file",
                is_current=True,
                created_by=self.user_id,
                storage_driver=file_info["driver"],
                storage_path=file_info["path"],
                storage_tier=file_info.get("tier", "hot")
            )
            self.db.add(version)
            
            await self.db.commit()
            await self.db.refresh(asset)
            
            logger.info(
                "asset_created_from_existing",
                asset_id=str(asset.id),
                name=asset.name,
                path=file_info["path"]
            )
            
            return await self._asset_to_response(asset)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("asset_creation_failed", error=str(e))
            raise
    
    async def get_asset(self, asset_id: UUID) -> AssetResponse:
        """Get asset by ID"""
        query = (
            select(Asset)
            .options(
                selectinload(Asset.tags),
                selectinload(Asset.versions)
            )
            .where(
                and_(
                    Asset.id == asset_id,
                    Asset.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if not asset.is_public and asset.owner_id != self.user_id:
            # TODO: Check sharing permissions
            raise PermissionError("You don't have permission to access this asset")
        
        return await self._asset_to_response(asset)
    
    async def list_assets(
        self,
        pagination: PaginationParams,
        search_params: Optional[AssetSearchParams] = None
    ) -> PaginatedResponse:
        """List assets with filtering and pagination"""
        # Build base query
        query = select(Asset).where(Asset.deleted_at.is_(None))
        
        # Apply filters
        if search_params:
            if search_params.query:
                query = query.where(
                    or_(
                        Asset.name.ilike(f"%{search_params.query}%"),
                        Asset.display_name.ilike(f"%{search_params.query}%"),
                        Asset.description.ilike(f"%{search_params.query}%")
                    )
                )
            
            if search_params.asset_type:
                query = query.where(Asset.asset_type == search_params.asset_type)
            
            if search_params.status:
                query = query.where(Asset.status == search_params.status)
            
            if search_params.project_id:
                query = query.where(Asset.project_id == search_params.project_id)
            
            if search_params.owner_id:
                query = query.where(Asset.owner_id == search_params.owner_id)
            
            if search_params.mime_type:
                query = query.where(Asset.mime_type == search_params.mime_type)
            
            if search_params.min_size:
                query = query.where(Asset.file_size >= search_params.min_size)
            
            if search_params.max_size:
                query = query.where(Asset.file_size <= search_params.max_size)
            
            if search_params.created_after:
                query = query.where(Asset.created_at >= search_params.created_after)
            
            if search_params.created_before:
                query = query.where(Asset.created_at <= search_params.created_before)
            
            if search_params.storage_tier:
                query = query.where(Asset.storage_tier == search_params.storage_tier)
            
            if search_params.is_public is not None:
                query = query.where(Asset.is_public == search_params.is_public)
            
            # Tag filtering
            if search_params.tags:
                query = query.join(asset_tags).join(Tag).where(
                    Tag.name.in_(search_params.tags)
                ).group_by(Asset.id).having(
                    func.count(Tag.id) == len(search_params.tags)
                )
        
        # Add default visibility filter
        query = query.where(
            or_(
                Asset.owner_id == self.user_id,
                Asset.is_public == True
            )
        )
        
        # Count total items
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)
        query = query.order_by(Asset.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        assets = result.scalars().all()
        
        # Convert to response models
        items = [self._asset_to_list_response(asset) for asset in assets]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    
    async def update_asset(
        self,
        asset_id: UUID,
        update_data: AssetUpdate
    ) -> AssetResponse:
        """Update asset metadata"""
        # Get asset
        asset = await self._get_asset_for_update(asset_id)
        
        # Update fields
        if update_data.display_name is not None:
            asset.display_name = update_data.display_name
        
        if update_data.description is not None:
            asset.description = update_data.description
        
        if update_data.is_public is not None:
            asset.is_public = update_data.is_public
        
        if update_data.project_id is not None:
            asset.project_id = update_data.project_id
        
        if update_data.metadata is not None:
            asset.technical_metadata = {**asset.technical_metadata, **update_data.metadata}
        
        # Update tags
        if update_data.tags is not None:
            # Clear existing tags
            asset.tags = []
            # Add new tags
            await self._add_tags_to_asset(asset, update_data.tags)
        
        asset.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(asset)
        
        logger.info("asset_updated", asset_id=str(asset_id))
        
        return await self._asset_to_response(asset)
    
    async def delete_asset(self, asset_id: UUID, permanent: bool = False) -> bool:
        """Delete asset (soft delete by default)"""
        asset = await self._get_asset_for_update(asset_id)
        
        if permanent:
            # Permanent delete - remove from database
            await self.db.delete(asset)
            
            # TODO: Delete file from storage
            
            logger.info("asset_deleted_permanently", asset_id=str(asset_id))
        else:
            # Soft delete
            asset.deleted_at = datetime.utcnow()
            asset.status = AssetStatus.DELETED
            
            logger.info("asset_soft_deleted", asset_id=str(asset_id))
        
        await self.db.commit()
        
        return True
    
    async def create_asset_version(
        self,
        asset_id: UUID,
        file_info: Dict[str, Any],
        comment: Optional[str] = None,
        version_label: Optional[str] = None
    ) -> AssetVersion:
        """Create a new version of an asset"""
        # Get asset and verify permissions
        asset = await self._get_asset_for_update(asset_id)
        
        # Get current version count
        query = select(func.count()).select_from(AssetVersion).where(
            AssetVersion.asset_id == asset_id
        )
        result = await self.db.execute(query)
        version_count = result.scalar_one()
        
        # Check version limit
        settings = get_settings()
        if version_count >= settings.max_versions_per_asset:
            raise ValidationError(
                f"Maximum number of versions ({settings.max_versions_per_asset}) reached"
            )
        
        # Get next version number
        next_version = version_count + 1
        
        # Set all current versions to not current
        await self.db.execute(
            update(AssetVersion)
            .where(AssetVersion.asset_id == asset_id)
            .values(is_current=False)
        )
        
        # Create new version
        new_version = AssetVersion(
            asset_id=asset_id,
            version_number=next_version,
            version_label=version_label or f"v{next_version}.0",
            file_path=file_info["path"],
            file_size=file_info["size"],
            file_hash=file_info.get("hash"),
            comment=comment or f"Version {next_version} created",
            is_current=True,
            created_by=self.user_id,
            storage_driver=file_info.get("driver", asset.storage_driver),
            storage_path=file_info["path"],
            storage_tier=file_info.get("tier", asset.storage_tier)
        )
        
        self.db.add(new_version)
        
        # Update asset with new file info
        asset.file_path = file_info["path"]
        asset.file_size = file_info["size"]
        asset.file_hash = file_info.get("hash")
        asset.storage_path = file_info["path"]
        asset.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(new_version)
        
        logger.info(
            "asset_version_created",
            asset_id=str(asset_id),
            version_number=next_version,
            user_id=str(self.user_id)
        )
        
        return new_version
    
    async def list_asset_versions(
        self,
        asset_id: UUID,
        include_metadata: bool = False
    ) -> List[AssetVersion]:
        """List all versions of an asset"""
        # Get asset and check permissions
        query = select(Asset).where(
            and_(
                Asset.id == asset_id,
                Asset.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if not asset.is_public and asset.owner_id != self.user_id:
            raise PermissionError("You don't have permission to access this asset")
        
        # Get versions
        query = (
            select(AssetVersion)
            .where(AssetVersion.asset_id == asset_id)
            .order_by(AssetVersion.version_number.desc())
        )
        
        result = await self.db.execute(query)
        versions = result.scalars().all()
        
        return versions
    
    async def get_asset_version(
        self,
        asset_id: UUID,
        version_number: int
    ) -> AssetVersion:
        """Get specific version of an asset"""
        # Get asset and check permissions
        query = select(Asset).where(
            and_(
                Asset.id == asset_id,
                Asset.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if not asset.is_public and asset.owner_id != self.user_id:
            raise PermissionError("You don't have permission to access this asset")
        
        # Get specific version
        query = select(AssetVersion).where(
            and_(
                AssetVersion.asset_id == asset_id,
                AssetVersion.version_number == version_number
            )
        )
        
        result = await self.db.execute(query)
        version = result.scalar_one_or_none()
        
        if not version:
            raise AssetNotFoundError(
                f"Version {version_number} not found for asset {asset_id}"
            )
        
        return version
    
    async def set_current_version(
        self,
        asset_id: UUID,
        version_number: int
    ) -> AssetVersion:
        """Set a specific version as the current version"""
        # Get asset and verify permissions
        asset = await self._get_asset_for_update(asset_id)
        
        # Get the version to make current
        version = await self.get_asset_version(asset_id, version_number)
        
        # Set all versions to not current
        await self.db.execute(
            update(AssetVersion)
            .where(AssetVersion.asset_id == asset_id)
            .values(is_current=False)
        )
        
        # Set selected version as current
        version.is_current = True
        
        # Update asset with version's file info
        asset.file_path = version.file_path
        asset.file_size = version.file_size
        asset.file_hash = version.file_hash
        asset.storage_path = version.storage_path
        asset.storage_tier = version.storage_tier
        asset.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(version)
        
        logger.info(
            "asset_version_set_current",
            asset_id=str(asset_id),
            version_number=version_number,
            user_id=str(self.user_id)
        )
        
        return version
    
    async def delete_asset_version(
        self,
        asset_id: UUID,
        version_number: int
    ) -> bool:
        """Delete a specific version (cannot delete current version)"""
        # Get asset and verify permissions
        asset = await self._get_asset_for_update(asset_id)
        
        # Get the version
        version = await self.get_asset_version(asset_id, version_number)
        
        # Check if it's the current version
        if version.is_current:
            raise ValidationError("Cannot delete the current version")
        
        # Check if it's the only version
        query = select(func.count()).select_from(AssetVersion).where(
            AssetVersion.asset_id == asset_id
        )
        result = await self.db.execute(query)
        version_count = result.scalar_one()
        
        if version_count <= 1:
            raise ValidationError("Cannot delete the only version of an asset")
        
        # Delete the version
        await self.db.delete(version)
        
        # TODO: Delete file from storage if no other assets use it
        
        await self.db.commit()
        
        logger.info(
            "asset_version_deleted",
            asset_id=str(asset_id),
            version_number=version_number,
            user_id=str(self.user_id)
        )
        
        return True
    
    async def bulk_update_assets(
        self,
        asset_ids: List[UUID],
        update_data: AssetUpdate
    ) -> Dict[str, Any]:
        """Update multiple assets at once"""
        results = {
            "successful": [],
            "failed": [],
            "total": len(asset_ids),
            "success_count": 0,
            "failure_count": 0
        }
        
        for asset_id in asset_ids:
            try:
                await self.update_asset(asset_id, update_data)
                results["successful"].append(asset_id)
                results["success_count"] += 1
            except Exception as e:
                results["failed"].append({
                    "asset_id": str(asset_id),
                    "error": str(e)
                })
                results["failure_count"] += 1
                logger.error(
                    "bulk_update_asset_failed",
                    asset_id=str(asset_id),
                    error=str(e)
                )
        
        await self.db.commit()
        
        logger.info(
            "bulk_update_completed",
            total=results["total"],
            success=results["success_count"],
            failed=results["failure_count"],
            user_id=str(self.user_id)
        )
        
        return results
    
    async def bulk_delete_assets(
        self,
        asset_ids: List[UUID],
        permanent: bool = False
    ) -> Dict[str, Any]:
        """Delete multiple assets at once"""
        results = {
            "successful": [],
            "failed": [],
            "total": len(asset_ids),
            "success_count": 0,
            "failure_count": 0
        }
        
        for asset_id in asset_ids:
            try:
                await self.delete_asset(asset_id, permanent)
                results["successful"].append(asset_id)
                results["success_count"] += 1
            except Exception as e:
                results["failed"].append({
                    "asset_id": str(asset_id),
                    "error": str(e)
                })
                results["failure_count"] += 1
                logger.error(
                    "bulk_delete_asset_failed",
                    asset_id=str(asset_id),
                    error=str(e)
                )
        
        logger.info(
            "bulk_delete_completed",
            total=results["total"],
            success=results["success_count"],
            failed=results["failure_count"],
            permanent=permanent,
            user_id=str(self.user_id)
        )
        
        return results
    
    async def bulk_tag_assets(
        self,
        asset_ids: List[UUID],
        tags_to_add: Optional[List[str]] = None,
        tags_to_remove: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add or remove tags from multiple assets"""
        results = {
            "successful": [],
            "failed": [],
            "total": len(asset_ids),
            "success_count": 0,
            "failure_count": 0
        }
        
        # Prepare tag objects
        tags_to_add_objs = []
        if tags_to_add:
            for tag_name in tags_to_add:
                query = select(Tag).where(Tag.name == tag_name)
                result = await self.db.execute(query)
                tag = result.scalar_one_or_none()
                
                if not tag:
                    tag = Tag(name=tag_name)
                    self.db.add(tag)
                
                tags_to_add_objs.append(tag)
        
        # Process each asset
        for asset_id in asset_ids:
            try:
                asset = await self._get_asset_for_update(asset_id)
                
                # Add tags
                if tags_to_add_objs:
                    for tag in tags_to_add_objs:
                        if tag not in asset.tags:
                            asset.tags.append(tag)
                
                # Remove tags
                if tags_to_remove:
                    asset.tags = [
                        tag for tag in asset.tags 
                        if tag.name not in tags_to_remove
                    ]
                
                asset.updated_at = datetime.utcnow()
                
                results["successful"].append(asset_id)
                results["success_count"] += 1
                
            except Exception as e:
                results["failed"].append({
                    "asset_id": str(asset_id),
                    "error": str(e)
                })
                results["failure_count"] += 1
                logger.error(
                    "bulk_tag_asset_failed",
                    asset_id=str(asset_id),
                    error=str(e)
                )
        
        await self.db.commit()
        
        logger.info(
            "bulk_tag_completed",
            total=results["total"],
            success=results["success_count"],
            failed=results["failure_count"],
            tags_added=tags_to_add,
            tags_removed=tags_to_remove,
            user_id=str(self.user_id)
        )
        
        return results
    
    async def bulk_move_assets(
        self,
        asset_ids: List[UUID],
        target_project_id: UUID
    ) -> Dict[str, Any]:
        """Move multiple assets to a different project"""
        results = {
            "successful": [],
            "failed": [],
            "total": len(asset_ids),
            "success_count": 0,
            "failure_count": 0
        }
        
        # Verify target project exists and user has access
        # TODO: Check project permissions
        
        for asset_id in asset_ids:
            try:
                asset = await self._get_asset_for_update(asset_id)
                asset.project_id = target_project_id
                asset.updated_at = datetime.utcnow()
                
                results["successful"].append(asset_id)
                results["success_count"] += 1
                
            except Exception as e:
                results["failed"].append({
                    "asset_id": str(asset_id),
                    "error": str(e)
                })
                results["failure_count"] += 1
                logger.error(
                    "bulk_move_asset_failed",
                    asset_id=str(asset_id),
                    error=str(e)
                )
        
        await self.db.commit()
        
        logger.info(
            "bulk_move_completed",
            total=results["total"],
            success=results["success_count"],
            failed=results["failure_count"],
            target_project_id=str(target_project_id),
            user_id=str(self.user_id)
        )
        
        return results
    
    async def _get_asset_for_update(self, asset_id: UUID) -> Asset:
        """Get asset for update with permission check"""
        query = (
            select(Asset)
            .options(selectinload(Asset.tags))
            .where(
                and_(
                    Asset.id == asset_id,
                    Asset.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if asset.owner_id != self.user_id:
            # TODO: Check if user has edit permissions through sharing
            raise PermissionError("You don't have permission to modify this asset")
        
        return asset
    
    async def _add_tags_to_asset(self, asset: Asset, tag_names: List[str]):
        """Add tags to asset, creating new tags if necessary"""
        for tag_name in tag_names:
            # Check if tag exists
            query = select(Tag).where(Tag.name == tag_name)
            result = await self.db.execute(query)
            tag = result.scalar_one_or_none()
            
            if not tag:
                # Create new tag
                tag = Tag(name=tag_name)
                self.db.add(tag)
            
            asset.tags.append(tag)
    
    async def _asset_to_response(self, asset: Asset) -> AssetResponse:
        """Convert asset model to response schema"""
        # Load relationships if not already loaded
        if not asset.tags:
            await self.db.refresh(asset, ["tags", "versions"])
        
        return AssetResponse(
            id=asset.id,
            name=asset.name,
            display_name=asset.display_name,
            description=asset.description,
            file_path=asset.file_path,
            file_size=asset.file_size,
            file_hash=asset.file_hash,
            mime_type=asset.mime_type,
            file_extension=asset.file_extension,
            asset_type=asset.asset_type,
            status=asset.status,
            storage_driver=asset.storage_driver,
            storage_tier=asset.storage_tier,
            owner_id=asset.owner_id,
            project_id=asset.project_id,
            is_public=asset.is_public,
            technical_metadata=asset.technical_metadata,
            version_count=len(asset.versions) if asset.versions else 1,
            tags=[tag.name for tag in asset.tags],
            created_at=asset.created_at,
            updated_at=asset.updated_at
        )
    
    def _asset_to_list_response(self, asset: Asset) -> AssetListResponse:
        """Convert asset model to list response schema"""
        return AssetListResponse(
            id=asset.id,
            name=asset.name,
            display_name=asset.display_name,
            asset_type=asset.asset_type,
            status=asset.status,
            file_size=asset.file_size,
            mime_type=asset.mime_type,
            owner_id=asset.owner_id,
            created_at=asset.created_at
        )