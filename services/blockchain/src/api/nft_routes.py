"""
API routes for NFT functionality.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..db.base import get_db
from ..services.nft_service import NFTService
from ..db.nft_models import (
    NFTCollection, NFTToken, NFTListing, NFTBid, NFTTransfer,
    NFTType, NFTStatus, MarketplaceStatus, BidStatus, AuctionType
)

router = APIRouter()

# Initialize NFT service
nft_service = NFTService()


# Pydantic Models
class NFTCollectionCreate(BaseModel):
    """Schema for creating NFT collection."""
    name: str = Field(..., min_length=1, max_length=255)
    symbol: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = None
    creator_address: str
    banner_image: Optional[str] = None
    featured_image: Optional[str] = None
    logo_image: Optional[str] = None
    max_supply: Optional[int] = Field(default=None, ge=1)
    royalty_percentage: Optional[Decimal] = Field(default=Decimal("5.0"), ge=0, le=25)
    royalty_recipient: Optional[str] = None
    website_url: Optional[str] = None
    discord_url: Optional[str] = None
    twitter_url: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("creator_address", "royalty_recipient")
    def validate_ethereum_address(cls, v):
        if v and (not v.startswith("0x") or len(v) != 42):
            raise ValueError("Invalid Ethereum address format")
        return v.lower() if v else v


class NFTMintRequest(BaseModel):
    """Schema for minting NFT."""
    collection_id: Optional[uuid.UUID] = None
    asset_id: Optional[uuid.UUID] = None
    recipient_address: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    animation_url: Optional[str] = None
    external_url: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    properties: Optional[Dict[str, Any]] = None
    royalty_percentage: Optional[Decimal] = Field(default=Decimal("5.0"), ge=0, le=25)
    royalty_recipient: Optional[str] = None
    unlockable_content: Optional[str] = None
    nft_type: Optional[NFTType] = Field(default=NFTType.SINGLE)
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("recipient_address", "royalty_recipient")
    def validate_ethereum_address(cls, v):
        if v and (not v.startswith("0x") or len(v) != 42):
            raise ValueError("Invalid Ethereum address format")
        return v.lower() if v else v


class NFTListingCreate(BaseModel):
    """Schema for creating NFT listing."""
    nft_token_id: uuid.UUID
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH")
    auction_type: AuctionType = Field(default=AuctionType.FIXED_PRICE)
    reserve_price: Optional[Decimal] = Field(default=None, gt=0)
    duration_hours: Optional[int] = Field(default=168, ge=1, le=8760)  # Max 1 year


class NFTBidCreate(BaseModel):
    """Schema for creating NFT bid."""
    nft_token_id: uuid.UUID
    bid_amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH")
    expires_hours: Optional[int] = Field(default=24, ge=1, le=168)  # Max 1 week


class NFTTransferRequest(BaseModel):
    """Schema for NFT transfer."""
    token_id: int
    from_address: str
    to_address: str
    network: Optional[str] = Field(default=settings.default_network)
    
    @validator("from_address", "to_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


# Collection Management Endpoints
@router.post("/collections", response_model=Dict[str, Any])
async def create_collection(
    collection_data: NFTCollectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new NFT collection."""
    try:
        # Create collection in database
        collection = NFTCollection(
            name=collection_data.name,
            symbol=collection_data.symbol,
            description=collection_data.description,
            creator_address=collection_data.creator_address,
            owner_address=collection_data.creator_address,
            banner_image=collection_data.banner_image,
            featured_image=collection_data.featured_image,
            logo_image=collection_data.logo_image,
            max_supply=collection_data.max_supply,
            royalty_percentage=collection_data.royalty_percentage,
            royalty_recipient=collection_data.royalty_recipient or collection_data.creator_address,
            website_url=collection_data.website_url,
            discord_url=collection_data.discord_url,
            twitter_url=collection_data.twitter_url,
            properties=collection_data.properties,
            network=collection_data.network
        )
        
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        
        return {
            "id": str(collection.id),
            "name": collection.name,
            "symbol": collection.symbol,
            "creator_address": collection.creator_address,
            "network": collection.network,
            "created_at": collection.created_at.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create collection: {str(e)}"
        )


@router.get("/collections/{collection_id}", response_model=Dict[str, Any])
async def get_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get collection details."""
    try:
        collection = await db.get(NFTCollection, collection_id)
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        # Get collection statistics
        nft_count = await db.execute(
            "SELECT COUNT(*) FROM nft_tokens WHERE collection_id = :collection_id",
            {"collection_id": collection_id}
        )
        total_nfts = nft_count.scalar()
        
        return {
            "id": str(collection.id),
            "name": collection.name,
            "symbol": collection.symbol,
            "description": collection.description,
            "creator_address": collection.creator_address,
            "owner_address": collection.owner_address,
            "total_supply": collection.total_supply,
            "max_supply": collection.max_supply,
            "total_nfts": total_nfts,
            "royalty_percentage": str(collection.royalty_percentage),
            "royalty_recipient": collection.royalty_recipient,
            "contract_address": collection.contract_address,
            "network": collection.network,
            "is_verified": collection.is_verified,
            "is_featured": collection.is_featured,
            "banner_image": collection.banner_image,
            "featured_image": collection.featured_image,
            "logo_image": collection.logo_image,
            "website_url": collection.website_url,
            "discord_url": collection.discord_url,
            "twitter_url": collection.twitter_url,
            "properties": collection.properties,
            "created_at": collection.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection: {str(e)}"
        )


# NFT Minting Endpoints
@router.post("/mint", response_model=Dict[str, Any])
async def mint_nft(
    mint_request: NFTMintRequest,
    db: AsyncSession = Depends(get_db)
):
    """Mint a new NFT."""
    try:
        # Prepare NFT properties
        nft_properties = {
            "name": mint_request.name,
            "description": mint_request.description,
            "image_uri": mint_request.image_url,
            "animation_url": mint_request.animation_url,
            "external_url": mint_request.external_url,
            "custom_attributes": mint_request.attributes or [],
            "royalty_percentage": float(mint_request.royalty_percentage),
            "royalty_recipient": mint_request.royalty_recipient or mint_request.recipient_address,
            "network": mint_request.network
        }
        
        # Mint NFT on blockchain
        mint_result = await nft_service.mint_nft(
            mint_request.asset_id or uuid.uuid4(),  # Generate UUID if no asset_id
            mint_request.recipient_address,
            nft_properties,
            mint_request.network
        )
        
        # Create NFT record in database
        nft_token = NFTToken(
            collection_id=mint_request.collection_id,
            asset_id=mint_request.asset_id,
            token_id=str(mint_result["token_id"]),
            name=mint_request.name,
            description=mint_request.description,
            nft_type=mint_request.nft_type,
            status=NFTStatus.MINTED,
            current_owner=mint_request.recipient_address,
            creator_address=mint_request.recipient_address,
            minter_address=mint_request.recipient_address,
            image_url=mint_request.image_url,
            animation_url=mint_request.animation_url,
            external_url=mint_request.external_url,
            token_uri=mint_result["metadata_uri"],
            ipfs_hash=mint_result["ipfs_hash"],
            contract_address=mint_result["contract_address"],
            network=mint_request.network,
            mint_transaction_hash=mint_result["transaction_hash"],
            mint_block_number=mint_result["block_number"],
            minted_at=datetime.now(timezone.utc),
            royalty_percentage=mint_request.royalty_percentage,
            royalty_recipient=mint_request.royalty_recipient or mint_request.recipient_address,
            attributes=mint_request.attributes,
            properties=mint_request.properties,
            unlockable_content=mint_request.unlockable_content
        )
        
        db.add(nft_token)
        await db.commit()
        await db.refresh(nft_token)
        
        return {
            "id": str(nft_token.id),
            "token_id": mint_result["token_id"],
            "transaction_hash": mint_result["transaction_hash"],
            "contract_address": mint_result["contract_address"],
            "owner_address": mint_request.recipient_address,
            "metadata_uri": mint_result["metadata_uri"],
            "network": mint_request.network,
            "status": "minted"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to mint NFT: {str(e)}"
        )


@router.post("/batch-mint", response_model=List[Dict[str, Any]])
async def batch_mint_nfts(
    mint_requests: List[NFTMintRequest],
    db: AsyncSession = Depends(get_db)
):
    """Batch mint multiple NFTs."""
    try:
        # Prepare batch requests for NFT service
        batch_requests = []
        for request in mint_requests:
            nft_properties = {
                "name": request.name,
                "description": request.description,
                "image_uri": request.image_url,
                "animation_url": request.animation_url,
                "external_url": request.external_url,
                "custom_attributes": request.attributes or [],
                "royalty_percentage": float(request.royalty_percentage),
                "royalty_recipient": request.royalty_recipient or request.recipient_address,
                "network": request.network
            }
            
            batch_requests.append({
                "asset_id": request.asset_id or uuid.uuid4(),
                "recipient_address": request.recipient_address,
                "nft_properties": nft_properties,
                "network": request.network
            })
        
        # Batch mint on blockchain
        mint_results = await nft_service.batch_mint_nfts(batch_requests)
        
        # Create database records
        results = []
        for i, mint_result in enumerate(mint_results):
            if "error" in mint_result:
                results.append({
                    "index": i,
                    "status": "failed",
                    "error": mint_result["error"]
                })
                continue
            
            request = mint_requests[i]
            nft_token = NFTToken(
                collection_id=request.collection_id,
                asset_id=request.asset_id,
                token_id=str(mint_result["token_id"]),
                name=request.name,
                description=request.description,
                nft_type=request.nft_type,
                status=NFTStatus.MINTED,
                current_owner=request.recipient_address,
                creator_address=request.recipient_address,
                minter_address=request.recipient_address,
                image_url=request.image_url,
                animation_url=request.animation_url,
                external_url=request.external_url,
                token_uri=mint_result["metadata_uri"],
                ipfs_hash=mint_result["ipfs_hash"],
                contract_address=mint_result["contract_address"],
                network=request.network,
                mint_transaction_hash=mint_result["transaction_hash"],
                mint_block_number=mint_result["block_number"],
                minted_at=datetime.now(timezone.utc),
                royalty_percentage=request.royalty_percentage,
                royalty_recipient=request.royalty_recipient or request.recipient_address,
                attributes=request.attributes,
                properties=request.properties,
                unlockable_content=request.unlockable_content
            )
            
            db.add(nft_token)
            
            results.append({
                "index": i,
                "token_id": mint_result["token_id"],
                "transaction_hash": mint_result["transaction_hash"],
                "status": "minted"
            })
        
        await db.commit()
        return results
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to batch mint NFTs: {str(e)}"
        )


# NFT Information Endpoints
@router.get("/tokens/{nft_id}", response_model=Dict[str, Any])
async def get_nft_token(
    nft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get NFT token details."""
    try:
        nft_token = await db.get(NFTToken, nft_id)
        
        if not nft_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NFT token not found"
            )
        
        # Get on-chain information
        try:
            chain_info = await nft_service.get_nft_info(
                int(nft_token.token_id),
                nft_token.network
            )
        except Exception as e:
            chain_info = {"error": str(e)}
        
        return {
            "id": str(nft_token.id),
            "token_id": nft_token.token_id,
            "name": nft_token.name,
            "description": nft_token.description,
            "image_url": nft_token.image_url,
            "animation_url": nft_token.animation_url,
            "external_url": nft_token.external_url,
            "current_owner": nft_token.current_owner,
            "creator_address": nft_token.creator_address,
            "contract_address": nft_token.contract_address,
            "network": nft_token.network,
            "status": nft_token.status.value,
            "nft_type": nft_token.nft_type.value,
            "royalty_percentage": str(nft_token.royalty_percentage),
            "royalty_recipient": nft_token.royalty_recipient,
            "attributes": nft_token.attributes,
            "properties": nft_token.properties,
            "unlockable_content": nft_token.unlockable_content,
            "token_uri": nft_token.token_uri,
            "ipfs_hash": nft_token.ipfs_hash,
            "minted_at": nft_token.minted_at.isoformat() if nft_token.minted_at else None,
            "created_at": nft_token.created_at.isoformat(),
            "chain_info": chain_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NFT token: {str(e)}"
        )


@router.get("/tokens/{nft_id}/history", response_model=List[Dict[str, Any]])
async def get_nft_history(
    nft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get NFT transaction history."""
    try:
        nft_token = await db.get(NFTToken, nft_id)
        
        if not nft_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NFT token not found"
            )
        
        # Get on-chain history
        try:
            chain_history = await nft_service.get_nft_history(
                int(nft_token.token_id),
                nft_token.network
            )
        except Exception as e:
            chain_history = []
        
        # Get database transfer history
        transfers = await db.execute(
            "SELECT * FROM nft_transfers WHERE nft_token_id = :nft_id ORDER BY block_timestamp DESC",
            {"nft_id": nft_id}
        )
        db_transfers = transfers.fetchall()
        
        # Combine and sort history
        history = []
        
        # Add chain history
        for event in chain_history:
            history.append(event)
        
        # Add database transfers
        for transfer in db_transfers:
            history.append({
                "event_type": transfer.transfer_type,
                "from_address": transfer.from_address,
                "to_address": transfer.to_address,
                "sale_price": str(transfer.sale_price) if transfer.sale_price else None,
                "currency": transfer.currency,
                "transaction_hash": transfer.transaction_hash,
                "block_number": transfer.block_number,
                "timestamp": transfer.block_timestamp.isoformat()
            })
        
        # Sort by timestamp
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NFT history: {str(e)}"
        )


# NFT Transfer Endpoints
@router.post("/transfer", response_model=Dict[str, Any])
async def transfer_nft(
    transfer_request: NFTTransferRequest,
    db: AsyncSession = Depends(get_db)
):
    """Transfer NFT ownership."""
    try:
        # Transfer on blockchain
        transfer_result = await nft_service.transfer_nft(
            transfer_request.token_id,
            transfer_request.from_address,
            transfer_request.to_address,
            transfer_request.network
        )
        
        # Update database
        nft_token = await db.execute(
            "SELECT * FROM nft_tokens WHERE token_id = :token_id AND network = :network",
            {"token_id": str(transfer_request.token_id), "network": transfer_request.network}
        )
        token = nft_token.fetchone()
        
        if token:
            # Update owner
            await db.execute(
                "UPDATE nft_tokens SET current_owner = :new_owner, updated_at = :now WHERE id = :token_id",
                {
                    "new_owner": transfer_request.to_address,
                    "now": datetime.now(timezone.utc),
                    "token_id": token.id
                }
            )
            
            # Record transfer
            transfer = NFTTransfer(
                nft_token_id=token.id,
                from_address=transfer_request.from_address,
                to_address=transfer_request.to_address,
                transfer_type="transfer",
                transaction_hash=transfer_result["transaction_hash"],
                block_number=transfer_result["block_number"],
                block_timestamp=datetime.now(timezone.utc)
            )
            db.add(transfer)
            
            await db.commit()
        
        return {
            "token_id": transfer_request.token_id,
            "from_address": transfer_request.from_address,
            "to_address": transfer_request.to_address,
            "transaction_hash": transfer_result["transaction_hash"],
            "network": transfer_request.network,
            "status": "transferred"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to transfer NFT: {str(e)}"
        )


# Marketplace Endpoints
@router.post("/listings", response_model=Dict[str, Any])
async def create_listing(
    listing_data: NFTListingCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create NFT marketplace listing."""
    try:
        # Get NFT token
        nft_token = await db.get(NFTToken, listing_data.nft_token_id)
        
        if not nft_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NFT token not found"
            )
        
        # List on blockchain (if applicable)
        try:
            listing_result = await nft_service.list_nft_for_sale(
                int(nft_token.token_id),
                listing_data.price,
                listing_data.duration_hours,
                nft_token.network
            )
        except Exception as e:
            listing_result = {"error": str(e)}
        
        # Create database listing
        end_time = datetime.now(timezone.utc) + timedelta(hours=listing_data.duration_hours)
        
        listing = NFTListing(
            nft_token_id=listing_data.nft_token_id,
            seller_address=nft_token.current_owner,
            price=listing_data.price,
            currency=listing_data.currency,
            auction_type=listing_data.auction_type,
            reserve_price=listing_data.reserve_price,
            end_time=end_time,
            listing_transaction_hash=listing_result.get("transaction_hash")
        )
        
        db.add(listing)
        
        # Update NFT status
        nft_token.status = NFTStatus.LISTED
        
        await db.commit()
        await db.refresh(listing)
        
        return {
            "id": str(listing.id),
            "nft_token_id": str(listing.nft_token_id),
            "seller_address": listing.seller_address,
            "price": str(listing.price),
            "currency": listing.currency,
            "auction_type": listing.auction_type.value,
            "end_time": listing.end_time.isoformat(),
            "transaction_hash": listing.listing_transaction_hash,
            "status": "listed"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create listing: {str(e)}"
        )


@router.post("/bids", response_model=Dict[str, Any])
async def place_bid(
    bid_data: NFTBidCreate,
    bidder_address: str = Query(..., description="Bidder's wallet address"),
    db: AsyncSession = Depends(get_db)
):
    """Place bid on NFT."""
    try:
        # Get NFT token
        nft_token = await db.get(NFTToken, bid_data.nft_token_id)
        
        if not nft_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NFT token not found"
            )
        
        # Place bid on blockchain (if applicable)
        try:
            bid_result = await nft_service.place_bid(
                int(nft_token.token_id),
                bidder_address,
                bid_data.bid_amount,
                nft_token.network
            )
        except Exception as e:
            bid_result = {"error": str(e)}
        
        # Create database bid
        expires_at = datetime.now(timezone.utc) + timedelta(hours=bid_data.expires_hours)
        
        bid = NFTBid(
            nft_token_id=bid_data.nft_token_id,
            bidder_address=bidder_address,
            bid_amount=bid_data.bid_amount,
            currency=bid_data.currency,
            expires_at=expires_at,
            bid_transaction_hash=bid_result.get("transaction_hash")
        )
        
        db.add(bid)
        await db.commit()
        await db.refresh(bid)
        
        return {
            "id": str(bid.id),
            "nft_token_id": str(bid.nft_token_id),
            "bidder_address": bid.bidder_address,
            "bid_amount": str(bid.bid_amount),
            "currency": bid.currency,
            "expires_at": bid.expires_at.isoformat(),
            "transaction_hash": bid.bid_transaction_hash,
            "status": "active"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to place bid: {str(e)}"
        )


# Search and Discovery Endpoints
@router.get("/search", response_model=List[Dict[str, Any]])
async def search_nfts(
    query: Optional[str] = Query(None, description="Search query"),
    collection_id: Optional[uuid.UUID] = Query(None, description="Filter by collection"),
    owner_address: Optional[str] = Query(None, description="Filter by owner"),
    min_price: Optional[Decimal] = Query(None, description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price filter"),
    nft_type: Optional[NFTType] = Query(None, description="Filter by NFT type"),
    status: Optional[NFTStatus] = Query(None, description="Filter by status"),
    network: Optional[str] = Query(None, description="Filter by network"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Search NFTs with various filters."""
    try:
        # Build query
        query_conditions = []
        params = {}
        
        if query:
            query_conditions.append("(name ILIKE :query OR description ILIKE :query)")
            params["query"] = f"%{query}%"
        
        if collection_id:
            query_conditions.append("collection_id = :collection_id")
            params["collection_id"] = collection_id
        
        if owner_address:
            query_conditions.append("current_owner = :owner_address")
            params["owner_address"] = owner_address.lower()
        
        if nft_type:
            query_conditions.append("nft_type = :nft_type")
            params["nft_type"] = nft_type.value
        
        if status:
            query_conditions.append("status = :status")
            params["status"] = status.value
        
        if network:
            query_conditions.append("network = :network")
            params["network"] = network
        
        # Add price filters (requires joining with listings)
        if min_price or max_price:
            # This would require a more complex query joining with listings
            pass
        
        # Build WHERE clause
        where_clause = ""
        if query_conditions:
            where_clause = "WHERE " + " AND ".join(query_conditions)
        
        # Execute query
        offset = (page - 1) * limit
        sql = f"""
            SELECT * FROM nft_tokens 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """
        
        params.update({"limit": limit, "offset": offset})
        
        result = await db.execute(sql, params)
        nfts = result.fetchall()
        
        # Format results
        search_results = []
        for nft in nfts:
            search_results.append({
                "id": str(nft.id),
                "token_id": nft.token_id,
                "name": nft.name,
                "description": nft.description,
                "image_url": nft.image_url,
                "current_owner": nft.current_owner,
                "creator_address": nft.creator_address,
                "status": nft.status,
                "nft_type": nft.nft_type,
                "network": nft.network,
                "created_at": nft.created_at.isoformat()
            })
        
        return search_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search NFTs: {str(e)}"
        )


# Analytics Endpoints
@router.get("/collections/{collection_id}/stats", response_model=Dict[str, Any])
async def get_collection_stats(
    collection_id: uuid.UUID,
    period: str = Query("24h", description="Statistics period (24h, 7d, 30d, all)"),
    db: AsyncSession = Depends(get_db)
):
    """Get collection statistics."""
    try:
        collection = await db.get(NFTCollection, collection_id)
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        # Get stats from blockchain service
        stats = await nft_service.get_collection_stats(
            collection.name,
            collection.network
        )
        
        # Add database stats
        # Total NFTs
        nft_count = await db.execute(
            "SELECT COUNT(*) FROM nft_tokens WHERE collection_id = :collection_id",
            {"collection_id": collection_id}
        )
        total_nfts = nft_count.scalar()
        
        # Unique owners
        owner_count = await db.execute(
            "SELECT COUNT(DISTINCT current_owner) FROM nft_tokens WHERE collection_id = :collection_id",
            {"collection_id": collection_id}
        )
        unique_owners = owner_count.scalar()
        
        stats.update({
            "collection_id": str(collection_id),
            "total_nfts": total_nfts,
            "unique_owners": unique_owners,
            "period": period
        })
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection stats: {str(e)}"
        )


# Health Check
@router.get("/health", response_model=Dict[str, Any])
async def nft_health_check():
    """NFT service health check."""
    try:
        # Check NFT service functionality
        network_stats = await nft_service.blockchain_service.get_network_stats()
        ipfs_info = await nft_service.ipfs_service.get_node_info()
        
        return {
            "status": "healthy",
            "service": "nft-service",
            "blockchain_networks": network_stats,
            "ipfs": ipfs_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"NFT service unhealthy: {str(e)}"
        )