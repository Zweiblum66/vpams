"""
API routes for Blockchain Service.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..db.base import get_db
from ..services.blockchain_service import BlockchainService
from ..services.ipfs_service import IPFSService
from ..db.models import (
    BlockchainAsset, MediaRights, RightsLicense, BlockchainTransaction,
    RoyaltyPayment, NetworkType, RightsType, LicenseStatus
)

router = APIRouter()

# Initialize services
blockchain_service = BlockchainService()
ipfs_service = IPFSService()


# Pydantic Models
class AssetRightsCreate(BaseModel):
    """Schema for creating asset rights."""
    asset_id: uuid.UUID
    owner_address: str
    creator_address: str
    rights_type: RightsType
    title: str
    description: Optional[str] = None
    terms: Optional[Dict[str, Any]] = None
    territories: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    royalty_percentage: Optional[Decimal] = Field(default=Decimal("5.0"), ge=0, le=100)
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("owner_address", "creator_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class LicenseCreate(BaseModel):
    """Schema for creating a license."""
    asset_id: uuid.UUID
    licensee_address: str
    rights_type: RightsType
    license_fee: Decimal = Field(ge=0)
    valid_from: datetime
    valid_until: datetime
    max_uses: Optional[int] = Field(default=None, ge=1)
    terms: Optional[Dict[str, Any]] = None
    royalty_percentage: Optional[Decimal] = Field(default=Decimal("5.0"), ge=0, le=100)
    currency: str = Field(default="ETH")
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("licensee_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class RightsTransfer(BaseModel):
    """Schema for transferring rights."""
    asset_id: uuid.UUID
    from_address: str
    to_address: str
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("from_address", "to_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class RoyaltyPaymentCreate(BaseModel):
    """Schema for creating royalty payment."""
    license_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    recipient_address: str
    usage_count: int = Field(default=1, ge=1)
    payment_type: str = Field(default="royalty")
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("recipient_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


# Asset Rights Endpoints
@router.post("/assets/rights", response_model=Dict[str, Any])
async def create_asset_rights(
    rights_data: AssetRightsCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create blockchain rights for a media asset."""
    try:
        # Prepare metadata for IPFS
        asset_metadata = {
            "id": str(rights_data.asset_id),
            "title": rights_data.title,
            "description": rights_data.description,
            "creator": rights_data.creator_address,
            "created_date": datetime.now(timezone.utc).isoformat()
        }
        
        rights_metadata = {
            "type": rights_data.rights_type.value,
            "owner": rights_data.owner_address,
            "license_terms": rights_data.terms or {},
            "territories": rights_data.territories or [],
            "languages": rights_data.languages or [],
            "valid_from": rights_data.valid_from.isoformat() if rights_data.valid_from else None,
            "valid_until": rights_data.valid_until.isoformat() if rights_data.valid_until else None,
            "royalty_percentage": float(rights_data.royalty_percentage),
            "network": rights_data.network
        }
        
        # Upload metadata to IPFS
        ipfs_result = await ipfs_service.upload_asset_metadata(
            asset_metadata,
            rights_metadata,
            rights_data.asset_id
        )
        
        # Prepare blockchain data
        blockchain_data = {
            "asset_id": rights_data.asset_id,
            "creator": rights_data.creator_address,
            "title": rights_data.title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rights_type": rights_data.rights_type.value,
            "terms": rights_data.terms or {},
            "ipfs_hash": ipfs_result["ipfs_hash"]
        }
        
        # Mint rights NFT on blockchain
        blockchain_result = await blockchain_service.mint_rights_nft(
            rights_data.asset_id,
            rights_data.owner_address,
            blockchain_data,
            rights_data.network
        )
        
        # Create database record
        blockchain_asset = BlockchainAsset(
            asset_id=rights_data.asset_id,
            token_id=str(blockchain_result["token_id"]),
            contract_address=blockchain_result["contract_address"],
            network=NetworkType(rights_data.network),
            ipfs_hash=ipfs_result["ipfs_hash"],
            metadata_uri=ipfs_result["gateway_url"],
            owner_address=rights_data.owner_address,
            creator_address=rights_data.creator_address,
            rights_hash=blockchain_result["rights_hash"],
            royalty_percentage=rights_data.royalty_percentage,
            minted_at=datetime.now(timezone.utc)
        )
        
        db.add(blockchain_asset)
        await db.commit()
        await db.refresh(blockchain_asset)
        
        return {
            "id": str(blockchain_asset.id),
            "asset_id": str(rights_data.asset_id),
            "token_id": blockchain_result["token_id"],
            "transaction_hash": blockchain_result["transaction_hash"],
            "rights_hash": blockchain_result["rights_hash"],
            "ipfs_hash": ipfs_result["ipfs_hash"],
            "metadata_uri": ipfs_result["gateway_url"],
            "network": rights_data.network,
            "status": "success"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create asset rights: {str(e)}"
        )


@router.get("/assets/{asset_id}/rights", response_model=Dict[str, Any])
async def get_asset_rights(
    asset_id: uuid.UUID,
    network: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get blockchain rights information for an asset."""
    try:
        # Query database
        query = db.query(BlockchainAsset).filter(BlockchainAsset.asset_id == asset_id)
        if network:
            query = query.filter(BlockchainAsset.network == NetworkType(network))
        
        blockchain_asset = await query.first()
        
        if not blockchain_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset rights not found"
            )
        
        # Verify ownership on blockchain
        verification = await blockchain_service.verify_rights_ownership(
            asset_id,
            blockchain_asset.owner_address,
            blockchain_asset.network.value
        )
        
        return {
            "id": str(blockchain_asset.id),
            "asset_id": str(asset_id),
            "token_id": blockchain_asset.token_id,
            "contract_address": blockchain_asset.contract_address,
            "network": blockchain_asset.network.value,
            "owner_address": blockchain_asset.owner_address,
            "creator_address": blockchain_asset.creator_address,
            "rights_hash": blockchain_asset.rights_hash,
            "royalty_percentage": str(blockchain_asset.royalty_percentage),
            "ipfs_hash": blockchain_asset.ipfs_hash,
            "metadata_uri": blockchain_asset.metadata_uri,
            "minted_at": blockchain_asset.minted_at.isoformat() if blockchain_asset.minted_at else None,
            "verification": verification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset rights: {str(e)}"
        )


@router.post("/assets/rights/transfer", response_model=Dict[str, Any])
async def transfer_asset_rights(
    transfer_data: RightsTransfer,
    db: AsyncSession = Depends(get_db)
):
    """Transfer asset rights ownership."""
    try:
        # Transfer on blockchain
        blockchain_result = await blockchain_service.transfer_rights(
            transfer_data.asset_id,
            transfer_data.from_address,
            transfer_data.to_address,
            transfer_data.network
        )
        
        # Update database
        blockchain_asset = await db.query(BlockchainAsset).filter(
            BlockchainAsset.asset_id == transfer_data.asset_id,
            BlockchainAsset.network == NetworkType(transfer_data.network)
        ).first()
        
        if blockchain_asset:
            blockchain_asset.owner_address = transfer_data.to_address
            blockchain_asset.updated_at = datetime.now(timezone.utc)
            await db.commit()
        
        return {
            "asset_id": str(transfer_data.asset_id),
            "transaction_hash": blockchain_result["transaction_hash"],
            "from_address": transfer_data.from_address,
            "to_address": transfer_data.to_address,
            "network": transfer_data.network,
            "status": "success"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to transfer asset rights: {str(e)}"
        )


# License Management Endpoints
@router.post("/licenses", response_model=Dict[str, Any])
async def create_license(
    license_data: LicenseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a license for media rights."""
    try:
        # Prepare license terms
        license_terms = {
            "rights_type": license_data.rights_type.value,
            "valid_from": license_data.valid_from.isoformat(),
            "valid_until": license_data.valid_until.isoformat(),
            "max_uses": license_data.max_uses,
            "terms": license_data.terms or {},
            "royalty_percentage": float(license_data.royalty_percentage),
            "currency": license_data.currency
        }
        
        # Create license on blockchain
        blockchain_result = await blockchain_service.create_license(
            license_data.asset_id,
            license_data.licensee_address,
            license_terms,
            license_data.license_fee,
            license_data.network
        )
        
        # Create database record
        rights_license = RightsLicense(
            asset_id=license_data.asset_id,  # This will need to be mapped to blockchain_asset.id
            licensee_address=license_data.licensee_address,
            licensor_address=blockchain_result.get("licensor", ""),  # From blockchain result
            license_number=f"LIC-{uuid.uuid4().hex[:8].upper()}",
            license_type=license_data.rights_type,
            status=LicenseStatus.ACTIVE,
            terms=license_data.terms,
            valid_from=license_data.valid_from,
            valid_until=license_data.valid_until,
            max_uses=license_data.max_uses,
            license_fee=license_data.license_fee,
            royalty_percentage=license_data.royalty_percentage,
            currency=license_data.currency,
            license_hash=blockchain_result["license_hash"],
            transaction_hash=blockchain_result["transaction_hash"],
            block_number=blockchain_result["block_number"]
        )
        
        db.add(rights_license)
        await db.commit()
        await db.refresh(rights_license)
        
        return {
            "id": str(rights_license.id),
            "license_number": rights_license.license_number,
            "asset_id": str(license_data.asset_id),
            "licensee_address": license_data.licensee_address,
            "license_fee": str(license_data.license_fee),
            "transaction_hash": blockchain_result["transaction_hash"],
            "license_hash": blockchain_result["license_hash"],
            "network": license_data.network,
            "status": "active"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create license: {str(e)}"
        )


@router.get("/licenses/{license_id}", response_model=Dict[str, Any])
async def get_license(
    license_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get license information."""
    try:
        rights_license = await db.query(RightsLicense).filter(
            RightsLicense.id == license_id
        ).first()
        
        if not rights_license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        return {
            "id": str(rights_license.id),
            "license_number": rights_license.license_number,
            "asset_id": str(rights_license.asset_id),
            "licensee_address": rights_license.licensee_address,
            "licensor_address": rights_license.licensor_address,
            "license_type": rights_license.license_type.value,
            "status": rights_license.status.value,
            "valid_from": rights_license.valid_from.isoformat(),
            "valid_until": rights_license.valid_until.isoformat(),
            "max_uses": rights_license.max_uses,
            "current_uses": rights_license.current_uses,
            "license_fee": str(rights_license.license_fee),
            "royalty_percentage": str(rights_license.royalty_percentage),
            "currency": rights_license.currency,
            "transaction_hash": rights_license.transaction_hash,
            "license_hash": rights_license.license_hash,
            "terms": rights_license.terms,
            "created_at": rights_license.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get license: {str(e)}"
        )


# Royalty Payment Endpoints
@router.post("/royalties/payment", response_model=Dict[str, Any])
async def create_royalty_payment(
    payment_data: RoyaltyPaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a royalty payment."""
    try:
        # Send payment on blockchain
        blockchain_result = await blockchain_service.send_royalty_payment(
            payment_data.recipient_address,
            payment_data.amount,
            payment_data.license_id,
            payment_data.network
        )
        
        # Create database record
        royalty_payment = RoyaltyPayment(
            license_id=payment_data.license_id,
            payment_hash=blockchain_result["transaction_hash"][:64],  # Use tx hash as payment hash
            transaction_hash=blockchain_result["transaction_hash"],
            amount=payment_data.amount,
            currency="ETH",  # From blockchain result
            payer_address=blockchain_result.get("payer", ""),
            recipient_address=payment_data.recipient_address,
            payment_type=payment_data.payment_type,
            usage_count=payment_data.usage_count,
            confirmed_at=datetime.now(timezone.utc)
        )
        
        db.add(royalty_payment)
        await db.commit()
        await db.refresh(royalty_payment)
        
        return {
            "id": str(royalty_payment.id),
            "license_id": str(payment_data.license_id),
            "amount": str(payment_data.amount),
            "recipient_address": payment_data.recipient_address,
            "transaction_hash": blockchain_result["transaction_hash"],
            "network": payment_data.network,
            "status": "completed"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create royalty payment: {str(e)}"
        )


@router.get("/royalties/calculate", response_model=Dict[str, Any])
async def calculate_royalty(
    license_fee: Decimal,
    royalty_percentage: Decimal,
    usage_count: int = 1
):
    """Calculate royalty payment amount."""
    try:
        calculation = await blockchain_service.calculate_royalty_payment(
            license_fee,
            royalty_percentage,
            usage_count
        )
        
        return calculation
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to calculate royalty: {str(e)}"
        )


# Transaction Status Endpoints
@router.get("/transactions/{transaction_hash}", response_model=Dict[str, Any])
async def get_transaction_status(
    transaction_hash: str,
    network: Optional[str] = None
):
    """Get blockchain transaction status."""
    try:
        status_info = await blockchain_service.get_transaction_status(
            transaction_hash,
            network
        )
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction status: {str(e)}"
        )


# Utility Endpoints
@router.get("/networks/stats", response_model=Dict[str, Any])
async def get_network_stats():
    """Get statistics for all blockchain networks."""
    try:
        stats = await blockchain_service.get_network_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get network stats: {str(e)}"
        )


@router.get("/addresses/{address}/balance", response_model=Dict[str, Any])
async def get_address_balance(
    address: str,
    network: Optional[str] = None
):
    """Get balance for an address."""
    try:
        balance = await blockchain_service.get_balance(address, network)
        return balance
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get address balance: {str(e)}"
        )


# IPFS Endpoints
@router.post("/ipfs/upload", response_model=Dict[str, Any])
async def upload_to_ipfs(
    file: UploadFile = File(...),
    content_type: str = Form("file"),
    asset_id: Optional[str] = Form(None),
    pin: bool = Form(True)
):
    """Upload file to IPFS."""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Upload to IPFS
            result = await ipfs_service.upload_file(
                tmp_file_path,
                uuid.UUID(asset_id) if asset_id else None,
                content_type,
                pin
            )
            
            return result
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload to IPFS: {str(e)}"
        )


@router.get("/ipfs/{ipfs_hash}", response_model=Dict[str, Any])
async def get_ipfs_info(ipfs_hash: str):
    """Get IPFS file information."""
    try:
        info = await ipfs_service.get_file_info(ipfs_hash)
        return info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to get IPFS info: {str(e)}"
        )


@router.get("/ipfs/node/info", response_model=Dict[str, Any])
async def get_ipfs_node_info():
    """Get IPFS node information."""
    try:
        info = await ipfs_service.get_node_info()
        return info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get IPFS node info: {str(e)}"
        )


# Verification Endpoints
@router.post("/verify/ownership", response_model=Dict[str, Any])
async def verify_ownership(
    asset_id: uuid.UUID,
    owner_address: str,
    network: Optional[str] = None
):
    """Verify asset rights ownership."""
    try:
        verification = await blockchain_service.verify_rights_ownership(
            asset_id,
            owner_address,
            network
        )
        
        return verification
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to verify ownership: {str(e)}"
        )


@router.post("/verify/batch-ownership", response_model=List[Dict[str, Any]])
async def batch_verify_ownership(
    ownership_requests: List[Dict[str, Any]]
):
    """Batch verify multiple ownership claims."""
    try:
        results = await blockchain_service.batch_verify_ownership(ownership_requests)
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to batch verify ownership: {str(e)}"
        )


# Health Check
@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint."""
    try:
        # Check blockchain connections
        network_stats = await blockchain_service.get_network_stats()
        
        # Check IPFS connection
        ipfs_info = await ipfs_service.get_node_info()
        
        return {
            "status": "healthy",
            "service": "blockchain-service",
            "version": settings.service_version,
            "networks": network_stats,
            "ipfs": ipfs_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )