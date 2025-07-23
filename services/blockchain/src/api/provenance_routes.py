"""
API routes for provenance tracking functionality.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.dependencies import get_db, get_current_user
from ..services.provenance_service import ProvenanceService, AssetMetadata, ProvenanceEventData
from ..db.models import User

router = APIRouter(prefix="/api/v1/provenance", tags=["provenance"])

# Pydantic schemas
class AssetMetadataCreate(BaseModel):
    """Schema for creating asset metadata."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., max_length=2000)
    asset_type: str = Field(..., max_length=100)
    file_format: str = Field(..., max_length=50)
    file_size: int = Field(..., gt=0)
    duration: Optional[float] = Field(None, ge=0)
    resolution: Optional[str] = Field(None, max_length=50)
    codec: Optional[str] = Field(None, max_length=50)
    frame_rate: Optional[float] = Field(None, ge=0)
    bitrate: Optional[int] = Field(None, ge=0)
    created_date: Optional[str] = None
    creator: Optional[str] = Field(None, max_length=255)
    camera_model: Optional[str] = Field(None, max_length=100)
    location: Optional[Dict[str, Any]] = None
    technical_metadata: Optional[Dict[str, Any]] = None


class ProvenanceEventCreate(BaseModel):
    """Schema for creating provenance events."""
    event_type: str = Field(..., max_length=50)
    actor: str = Field(..., max_length=255)
    description: str = Field(..., max_length=2000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[str] = Field(None, max_length=255)
    signature: Optional[str] = None


class AssetRegistrationRequest(BaseModel):
    """Request schema for asset registration."""
    asset_id: uuid.UUID
    asset_metadata: AssetMetadataCreate
    creator_address: str = Field(..., max_length=42)
    network: Optional[str] = None


class OwnershipTransferRequest(BaseModel):
    """Request schema for ownership transfer."""
    new_owner_address: str = Field(..., max_length=42)
    transfer_metadata: Dict[str, Any] = Field(default_factory=dict)
    network: Optional[str] = None


class ContentUpdateRequest(BaseModel):
    """Request schema for content updates."""
    new_content_hash: str = Field(..., max_length=64)
    modification_type: str = Field(..., max_length=100)
    modification_metadata: Dict[str, Any] = Field(default_factory=dict)
    network: Optional[str] = None


class VerificationRequest(BaseModel):
    """Request schema for asset verification."""
    verification_type: str = Field(..., max_length=100)
    verified: bool
    evidence: str = Field(..., max_length=5000)
    verifier_address: Optional[str] = Field(None, max_length=42)
    network: Optional[str] = None


class ProvenanceResponse(BaseModel):
    """Standard response schema."""
    success: bool
    data: Dict[str, Any]
    message: str = ""


# Initialize service
provenance_service = ProvenanceService()


@router.post("/assets/register", response_model=ProvenanceResponse)
async def register_asset_provenance(
    request: AssetRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new asset for provenance tracking."""
    try:
        # Convert Pydantic model to AssetMetadata
        asset_metadata = AssetMetadata(
            title=request.asset_metadata.title,
            description=request.asset_metadata.description,
            asset_type=request.asset_metadata.asset_type,
            file_format=request.asset_metadata.file_format,
            file_size=request.asset_metadata.file_size,
            duration=request.asset_metadata.duration,
            resolution=request.asset_metadata.resolution,
            codec=request.asset_metadata.codec,
            frame_rate=request.asset_metadata.frame_rate,
            bitrate=request.asset_metadata.bitrate,
            created_date=request.asset_metadata.created_date,
            creator=request.asset_metadata.creator,
            camera_model=request.asset_metadata.camera_model,
            location=request.asset_metadata.location,
            technical_metadata=request.asset_metadata.technical_metadata
        )
        
        result = await provenance_service.register_asset_provenance(
            asset_id=request.asset_id,
            asset_metadata=asset_metadata,
            creator_address=request.creator_address,
            network=request.network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset successfully registered for provenance tracking"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register asset: {str(e)}"
        )


@router.post("/assets/{blockchain_asset_id}/events", response_model=ProvenanceResponse)
async def add_provenance_event(
    blockchain_asset_id: int,
    event: ProvenanceEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a provenance event to an asset's history."""
    try:
        # Create ProvenanceEventData
        event_data = ProvenanceEventData(
            event_type=event.event_type,
            actor=event.actor,
            timestamp=datetime.utcnow().isoformat(),
            description=event.description,
            metadata=event.metadata,
            location=event.location,
            signature=event.signature
        )
        
        result = await provenance_service.add_provenance_event(
            blockchain_asset_id=blockchain_asset_id,
            event_data=event_data
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Provenance event successfully added"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add provenance event: {str(e)}"
        )


@router.post("/assets/{blockchain_asset_id}/transfer", response_model=ProvenanceResponse)
async def transfer_asset_ownership(
    blockchain_asset_id: int,
    request: OwnershipTransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Transfer ownership of an asset."""
    try:
        result = await provenance_service.transfer_asset_ownership(
            blockchain_asset_id=blockchain_asset_id,
            new_owner_address=request.new_owner_address,
            transfer_metadata=request.transfer_metadata,
            network=request.network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset ownership successfully transferred"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transfer ownership: {str(e)}"
        )


@router.put("/assets/{blockchain_asset_id}/content", response_model=ProvenanceResponse)
async def update_asset_content(
    blockchain_asset_id: int,
    request: ContentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update asset content and record the modification."""
    try:
        result = await provenance_service.update_asset_content(
            blockchain_asset_id=blockchain_asset_id,
            new_content_hash=request.new_content_hash,
            modification_type=request.modification_type,
            modification_metadata=request.modification_metadata,
            network=request.network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset content successfully updated"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update content: {str(e)}"
        )


@router.post("/assets/{blockchain_asset_id}/verify", response_model=ProvenanceResponse)
async def add_verification(
    blockchain_asset_id: int,
    request: VerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add verification to an asset."""
    try:
        result = await provenance_service.add_verification(
            blockchain_asset_id=blockchain_asset_id,
            verification_type=request.verification_type,
            verified=request.verified,
            evidence=request.evidence,
            verifier_address=request.verifier_address,
            network=request.network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Verification successfully added"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add verification: {str(e)}"
        )


@router.get("/assets/{blockchain_asset_id}", response_model=ProvenanceResponse)
async def get_asset_info(
    blockchain_asset_id: int,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive asset information."""
    try:
        result = await provenance_service.get_asset_info(
            blockchain_asset_id=blockchain_asset_id,
            network=network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset information retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {str(e)}"
        )


@router.get("/assets/{blockchain_asset_id}/history", response_model=ProvenanceResponse)
async def get_asset_history(
    blockchain_asset_id: int,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete provenance history for an asset."""
    try:
        result = await provenance_service.get_asset_history(
            blockchain_asset_id=blockchain_asset_id,
            network=network
        )
        
        return ProvenanceResponse(
            success=True,
            data={"history": result, "total_events": len(result)},
            message="Asset history retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset history not found: {str(e)}"
        )


@router.get("/assets/{blockchain_asset_id}/verify/{expected_hash}", response_model=ProvenanceResponse)
async def verify_asset_authenticity(
    blockchain_asset_id: int,
    expected_hash: str,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify the authenticity of an asset."""
    try:
        result = await provenance_service.verify_asset_authenticity(
            blockchain_asset_id=blockchain_asset_id,
            expected_content_hash=expected_hash,
            network=network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset authenticity verification completed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify authenticity: {str(e)}"
        )


@router.get("/assets/{blockchain_asset_id}/lineage", response_model=ProvenanceResponse)
async def trace_asset_lineage(
    blockchain_asset_id: int,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trace the complete lineage of an asset."""
    try:
        result = await provenance_service.trace_asset_lineage(
            blockchain_asset_id=blockchain_asset_id,
            network=network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Asset lineage traced successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trace lineage: {str(e)}"
        )


@router.get("/assets/{blockchain_asset_id}/report", response_model=ProvenanceResponse)
async def create_provenance_report(
    blockchain_asset_id: int,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a comprehensive provenance report for an asset."""
    try:
        result = await provenance_service.create_provenance_report(
            blockchain_asset_id=blockchain_asset_id,
            network=network
        )
        
        return ProvenanceResponse(
            success=True,
            data=result,
            message="Provenance report created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for provenance service."""
    return {
        "status": "healthy",
        "service": "provenance-tracking",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }