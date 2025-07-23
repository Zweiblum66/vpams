"""Decentralized storage routes"""

import logging
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from ..core.config import settings
from ..db.base import get_db
from ..models.web3_models import Web3User, DecentralizedStorage, StorageType
from ..models.schemas import (
    StorageUploadResponse,
    StorageItemResponse,
    StorageListResponse,
    IPFSPinResponse
)
from ..services.ipfs_service import IPFSService
from ..services.arweave_service import ArweaveService
from ..services.filecoin_service import FilecoinService
from ..services.storage_encryption import StorageEncryptionService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=StorageUploadResponse)
async def upload_to_decentralized_storage(
    file: UploadFile = File(...),
    storage_type: StorageType = Form(StorageType.IPFS),
    encrypt: bool = Form(False),
    is_public: bool = Form(True),
    pin_remote: bool = Form(True),
    asset_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file to decentralized storage"""
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Encrypt if requested
        encryption_key_hash = None
        if encrypt:
            encryption_service = StorageEncryptionService()
            content, encryption_key = await encryption_service.encrypt_content(content)
            encryption_key_hash = await encryption_service.store_encryption_key(
                encryption_key,
                current_user.id
            )
        
        # Upload based on storage type
        if storage_type == StorageType.IPFS:
            ipfs_service = IPFSService()
            await ipfs_service.initialize()
            
            # Upload to IPFS
            file_like = io.BytesIO(content)
            result = await ipfs_service.add_file(
                file_like,
                file.filename,
                pin=True
            )
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload to IPFS"
                )
            
            content_hash = result.cid
            
            # Pin to remote service if requested
            if pin_remote and settings.PINATA_API_KEY:
                await ipfs_service.pin_to_pinata(
                    content_hash,
                    name=file.filename,
                    metadata={
                        "user_id": str(current_user.id),
                        "asset_id": asset_id
                    }
                )
            
            await ipfs_service.cleanup()
            
        elif storage_type == StorageType.ARWEAVE:
            arweave_service = ArweaveService()
            content_hash = await arweave_service.upload_data(
                content,
                content_type=file.content_type,
                tags={
                    "Content-Type": file.content_type,
                    "Filename": file.filename,
                    "User-ID": str(current_user.id)
                }
            )
            
        elif storage_type == StorageType.FILECOIN:
            filecoin_service = FilecoinService()
            content_hash = await filecoin_service.store_file(
                content,
                filename=file.filename
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage type: {storage_type}"
            )
        
        # Store metadata in database
        storage_record = DecentralizedStorage(
            storage_id=f"{storage_type.value}_{content_hash}",
            user_id=current_user.id,
            asset_id=asset_id,
            storage_type=storage_type,
            content_hash=content_hash,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            is_pinned=True,
            is_permanent=storage_type in [StorageType.ARWEAVE, StorageType.FILECOIN],
            is_encrypted=encrypt,
            encryption_key_hash=encryption_key_hash,
            is_public=is_public,
            tags=tags,
            created_at=datetime.utcnow()
        )
        db.add(storage_record)
        await db.commit()
        
        # Build response
        if storage_type == StorageType.IPFS:
            access_url = f"{settings.IPFS_GATEWAY_URL}/{content_hash}"
        elif storage_type == StorageType.ARWEAVE:
            access_url = f"{settings.ARWEAVE_URL}/{content_hash}"
        else:
            access_url = None
        
        return StorageUploadResponse(
            storage_id=storage_record.storage_id,
            content_hash=content_hash,
            storage_type=storage_type.value,
            filename=file.filename,
            file_size=file_size,
            is_encrypted=encrypt,
            is_public=is_public,
            access_url=access_url,
            created_at=storage_record.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading to decentralized storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )

@router.get("/files", response_model=StorageListResponse)
async def list_stored_files(
    storage_type: Optional[StorageType] = Query(None),
    asset_id: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's stored files"""
    try:
        # Build query
        query = select(DecentralizedStorage).where(
            DecentralizedStorage.user_id == current_user.id
        )
        
        if storage_type:
            query = query.where(DecentralizedStorage.storage_type == storage_type)
        
        if asset_id:
            query = query.where(DecentralizedStorage.asset_id == asset_id)
        
        if is_public is not None:
            query = query.where(DecentralizedStorage.is_public == is_public)
        
        # Get total count
        count_query = query.with_only_columns(func.count())
        total = await db.scalar(count_query)
        
        # Get items
        query = query.order_by(DecentralizedStorage.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Build response
        files = []
        for item in items:
            # Build access URL
            if item.storage_type == StorageType.IPFS:
                access_url = f"{settings.IPFS_GATEWAY_URL}/{item.content_hash}"
            elif item.storage_type == StorageType.ARWEAVE:
                access_url = f"{settings.ARWEAVE_URL}/{item.content_hash}"
            else:
                access_url = None
            
            files.append(StorageItemResponse(
                storage_id=item.storage_id,
                content_hash=item.content_hash,
                storage_type=item.storage_type.value,
                filename=item.filename,
                content_type=item.content_type,
                file_size=item.file_size,
                is_encrypted=item.is_encrypted,
                is_public=item.is_public,
                is_pinned=item.is_pinned,
                is_permanent=item.is_permanent,
                access_url=access_url,
                asset_id=item.asset_id,
                tags=item.tags,
                created_at=item.created_at
            ))
        
        return StorageListResponse(
            items=files,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )

@router.get("/files/{storage_id}", response_model=StorageItemResponse)
async def get_file_info(
    storage_id: str,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file information"""
    try:
        # Get file record
        file_record = await db.execute(
            select(DecentralizedStorage).where(
                DecentralizedStorage.storage_id == storage_id,
                DecentralizedStorage.user_id == current_user.id
            )
        )
        file_record = file_record.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Build access URL
        if file_record.storage_type == StorageType.IPFS:
            access_url = f"{settings.IPFS_GATEWAY_URL}/{file_record.content_hash}"
        elif file_record.storage_type == StorageType.ARWEAVE:
            access_url = f"{settings.ARWEAVE_URL}/{file_record.content_hash}"
        else:
            access_url = None
        
        return StorageItemResponse(
            storage_id=file_record.storage_id,
            content_hash=file_record.content_hash,
            storage_type=file_record.storage_type.value,
            filename=file_record.filename,
            content_type=file_record.content_type,
            file_size=file_record.file_size,
            is_encrypted=file_record.is_encrypted,
            is_public=file_record.is_public,
            is_pinned=file_record.is_pinned,
            is_permanent=file_record.is_permanent,
            access_url=access_url,
            asset_id=file_record.asset_id,
            tags=file_record.tags,
            created_at=file_record.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file info"
        )

@router.get("/files/{storage_id}/download")
async def download_file(
    storage_id: str,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a file from decentralized storage"""
    try:
        # Get file record
        file_record = await db.execute(
            select(DecentralizedStorage).where(
                and_(
                    DecentralizedStorage.storage_id == storage_id,
                    or_(
                        DecentralizedStorage.user_id == current_user.id,
                        DecentralizedStorage.is_public == True
                    )
                )
            )
        )
        file_record = file_record.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Download based on storage type
        if file_record.storage_type == StorageType.IPFS:
            ipfs_service = IPFSService()
            await ipfs_service.initialize()
            
            content = await ipfs_service.get_file(file_record.content_hash)
            await ipfs_service.cleanup()
            
        elif file_record.storage_type == StorageType.ARWEAVE:
            arweave_service = ArweaveService()
            content = await arweave_service.get_data(file_record.content_hash)
            
        elif file_record.storage_type == StorageType.FILECOIN:
            filecoin_service = FilecoinService()
            content = await filecoin_service.retrieve_file(file_record.content_hash)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported storage type"
            )
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found"
            )
        
        # Decrypt if needed
        if file_record.is_encrypted:
            encryption_service = StorageEncryptionService()
            encryption_key = await encryption_service.get_encryption_key(
                file_record.encryption_key_hash,
                current_user.id
            )
            content = await encryption_service.decrypt_content(content, encryption_key)
        
        # Update last accessed
        file_record.last_accessed_at = datetime.utcnow()
        await db.commit()
        
        # Return file
        return StreamingResponse(
            io.BytesIO(content),
            media_type=file_record.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_record.filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )

@router.delete("/files/{storage_id}")
async def delete_file(
    storage_id: str,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a file from decentralized storage"""
    try:
        # Get file record
        file_record = await db.execute(
            select(DecentralizedStorage).where(
                DecentralizedStorage.storage_id == storage_id,
                DecentralizedStorage.user_id == current_user.id
            )
        )
        file_record = file_record.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check if permanent storage
        if file_record.is_permanent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete permanent storage (Arweave/Filecoin)"
            )
        
        # Unpin from IPFS if needed
        if file_record.storage_type == StorageType.IPFS and file_record.is_pinned:
            ipfs_service = IPFSService()
            await ipfs_service.initialize()
            
            # Unpin from local node
            await ipfs_service.pin_rm(file_record.content_hash)
            
            # Unpin from Pinata if used
            if settings.PINATA_API_KEY:
                await ipfs_service.unpin_from_pinata(file_record.content_hash)
            
            await ipfs_service.cleanup()
        
        # Delete database record
        await db.delete(file_record)
        await db.commit()
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )

@router.post("/pin", response_model=IPFSPinResponse)
async def pin_content(
    cid: str,
    name: Optional[str] = None,
    remote: bool = True,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Pin IPFS content"""
    try:
        ipfs_service = IPFSService()
        await ipfs_service.initialize()
        
        # Pin locally
        success = await ipfs_service.pin_add(cid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to pin content"
            )
        
        # Pin remotely if requested
        remote_pin_id = None
        if remote and settings.PINATA_API_KEY:
            result = await ipfs_service.pin_to_pinata(
                cid,
                name=name,
                metadata={"user_id": str(current_user.id)}
            )
            if result:
                remote_pin_id = result.get("id")
        
        await ipfs_service.cleanup()
        
        # Store pin record
        storage_record = DecentralizedStorage(
            storage_id=f"ipfs_pin_{cid}",
            user_id=current_user.id,
            storage_type=StorageType.IPFS,
            content_hash=cid,
            filename=name or cid,
            content_type="application/octet-stream",
            file_size=0,  # Unknown for external content
            is_pinned=True,
            pin_service="pinata" if remote_pin_id else "local",
            is_public=True,
            metadata={"remote_pin_id": remote_pin_id} if remote_pin_id else None
        )
        db.add(storage_record)
        await db.commit()
        
        return IPFSPinResponse(
            cid=cid,
            pinned=True,
            remote_pinned=bool(remote_pin_id),
            remote_pin_id=remote_pin_id,
            gateway_url=f"{settings.IPFS_GATEWAY_URL}/{cid}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pinning content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pin content"
        )

# Helper to get current user
async def get_current_user(db: AsyncSession = Depends(get_db)) -> Web3User:
    # This would validate JWT and return user
    # For now, returning a placeholder
    raise NotImplementedError("Authentication required")