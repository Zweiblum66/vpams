"""
Extended database models for NFT functionality.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, Numeric, JSON, Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .models import Base, NetworkType


class NFTType(PyEnum):
    """Types of NFTs."""
    SINGLE = "single"  # 1/1 NFT
    EDITION = "edition"  # Limited edition
    OPEN_EDITION = "open_edition"  # Unlimited minting
    GENERATIVE = "generative"  # Algorithmically generated
    INTERACTIVE = "interactive"  # Interactive/utility NFTs
    MEMBERSHIP = "membership"  # Membership/access NFTs


class NFTStatus(PyEnum):
    """NFT status types."""
    DRAFT = "draft"
    MINTING = "minting"
    MINTED = "minted"
    LISTED = "listed"
    SOLD = "sold"
    TRANSFERRED = "transferred"
    BURNED = "burned"


class MarketplaceStatus(PyEnum):
    """Marketplace listing status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    SOLD = "sold"
    CANCELLED = "cancelled"


class BidStatus(PyEnum):
    """Bid status types."""
    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class AuctionType(PyEnum):
    """Auction types."""
    FIXED_PRICE = "fixed_price"
    ENGLISH_AUCTION = "english_auction"  # Ascending bid
    DUTCH_AUCTION = "dutch_auction"  # Descending price
    RESERVE_AUCTION = "reserve_auction"  # With reserve price


class NFTCollection(Base):
    """NFT collections for organizing related NFTs."""
    __tablename__ = "nft_collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Collection details
    name = Column(String(255), nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    
    # Creator and ownership
    creator_address = Column(String(42), nullable=False, index=True)
    owner_address = Column(String(42), nullable=False, index=True)
    
    # Collection metadata
    banner_image = Column(String(512), nullable=True)
    featured_image = Column(String(512), nullable=True)
    logo_image = Column(String(512), nullable=True)
    
    # Collection properties
    total_supply = Column(Integer, nullable=False, default=0)
    max_supply = Column(Integer, nullable=True)  # None for unlimited
    royalty_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    royalty_recipient = Column(String(42), nullable=True)
    
    # Blockchain information
    contract_address = Column(String(42), nullable=True, index=True)
    network = Column(Enum(NetworkType), nullable=False, default=NetworkType.POLYGON)
    
    # Marketplace settings
    is_verified = Column(Boolean, nullable=False, default=False)
    is_featured = Column(Boolean, nullable=False, default=False)
    explicit_content = Column(Boolean, nullable=False, default=False)
    
    # Social and external links
    website_url = Column(String(512), nullable=True)
    discord_url = Column(String(512), nullable=True)
    twitter_url = Column(String(512), nullable=True)
    instagram_url = Column(String(512), nullable=True)
    
    # Collection metadata
    properties = Column(JSON, nullable=True)  # Custom collection properties
    traits = Column(JSON, nullable=True)  # Available trait types
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    nfts = relationship("NFTToken", back_populates="collection", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('name', 'network', name='uq_collection_name_network'),
        Index('idx_collection_creator_network', 'creator_address', 'network'),
    )


class NFTToken(Base):
    """Individual NFT tokens."""
    __tablename__ = "nft_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("nft_collections.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to media asset
    
    # Token identification
    token_id = Column(String(255), nullable=False, index=True)
    token_uri = Column(String(512), nullable=True)
    
    # Token details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    nft_type = Column(Enum(NFTType), nullable=False, default=NFTType.SINGLE)
    status = Column(Enum(NFTStatus), nullable=False, default=NFTStatus.DRAFT)
    
    # Ownership
    current_owner = Column(String(42), nullable=False, index=True)
    creator_address = Column(String(42), nullable=False, index=True)
    minter_address = Column(String(42), nullable=True, index=True)
    
    # Media and metadata
    image_url = Column(String(512), nullable=True)
    animation_url = Column(String(512), nullable=True)  # For videos/interactive content
    external_url = Column(String(512), nullable=True)
    ipfs_hash = Column(String(255), nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    
    # Blockchain information
    contract_address = Column(String(42), nullable=True, index=True)
    network = Column(Enum(NetworkType), nullable=False, default=NetworkType.POLYGON)
    
    # Minting information
    mint_transaction_hash = Column(String(66), nullable=True, index=True)
    mint_block_number = Column(Integer, nullable=True)
    minted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Royalty information
    royalty_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    royalty_recipient = Column(String(42), nullable=True)
    
    # Attributes and traits
    attributes = Column(JSON, nullable=True)  # Array of trait objects
    rarity_rank = Column(Integer, nullable=True)
    rarity_score = Column(Numeric(10, 4), nullable=True)
    
    # Edition information (for limited editions)
    edition_number = Column(Integer, nullable=True)
    edition_total = Column(Integer, nullable=True)
    
    # Properties
    properties = Column(JSON, nullable=True)  # Custom properties
    unlockable_content = Column(Text, nullable=True)  # Hidden content for owner
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    collection = relationship("NFTCollection", back_populates="nfts")
    listings = relationship("NFTListing", back_populates="nft_token")
    bids = relationship("NFTBid", back_populates="nft_token")
    transfers = relationship("NFTTransfer", back_populates="nft_token")
    
    __table_args__ = (
        UniqueConstraint('token_id', 'contract_address', 'network', name='uq_token_contract_network'),
        Index('idx_nft_owner_network', 'current_owner', 'network'),
        Index('idx_nft_creator_status', 'creator_address', 'status'),
    )


class NFTListing(Base):
    """NFT marketplace listings."""
    __tablename__ = "nft_listings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    
    # Listing details
    seller_address = Column(String(42), nullable=False, index=True)
    price = Column(Numeric(18, 8), nullable=False)  # In ETH/native currency
    currency = Column(String(10), nullable=False, default="ETH")
    
    # Auction details
    auction_type = Column(Enum(AuctionType), nullable=False, default=AuctionType.FIXED_PRICE)
    reserve_price = Column(Numeric(18, 8), nullable=True)  # For reserve auctions
    
    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(Enum(MarketplaceStatus), nullable=False, default=MarketplaceStatus.ACTIVE)
    
    # Blockchain information
    listing_transaction_hash = Column(String(66), nullable=True, index=True)
    sale_transaction_hash = Column(String(66), nullable=True, index=True)
    
    # Statistics
    view_count = Column(Integer, nullable=False, default=0)
    favorite_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    sold_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    nft_token = relationship("NFTToken", back_populates="listings")
    bids = relationship("NFTBid", back_populates="listing")
    
    __table_args__ = (
        Index('idx_listing_seller_status', 'seller_address', 'status'),
        Index('idx_listing_price_time', 'price', 'end_time'),
    )


class NFTBid(Base):
    """NFT marketplace bids."""
    __tablename__ = "nft_bids"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("nft_listings.id"), nullable=True)
    
    # Bid details
    bidder_address = Column(String(42), nullable=False, index=True)
    bid_amount = Column(Numeric(18, 8), nullable=False)
    currency = Column(String(10), nullable=False, default="ETH")
    
    # Timing
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(Enum(BidStatus), nullable=False, default=BidStatus.ACTIVE)
    
    # Blockchain information
    bid_transaction_hash = Column(String(66), nullable=True, index=True)
    acceptance_transaction_hash = Column(String(66), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    nft_token = relationship("NFTToken", back_populates="bids")
    listing = relationship("NFTListing", back_populates="bids")
    
    __table_args__ = (
        Index('idx_bid_bidder_status', 'bidder_address', 'status'),
        Index('idx_bid_amount_time', 'bid_amount', 'created_at'),
    )


class NFTTransfer(Base):
    """NFT transfer history."""
    __tablename__ = "nft_transfers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    
    # Transfer details
    from_address = Column(String(42), nullable=True, index=True)  # Null for minting
    to_address = Column(String(42), nullable=False, index=True)
    transfer_type = Column(String(50), nullable=False, index=True)  # mint, transfer, sale, burn
    
    # Sale information (if applicable)
    sale_price = Column(Numeric(18, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    
    # Blockchain information
    transaction_hash = Column(String(66), nullable=False, unique=True, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    block_timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Gas information
    gas_used = Column(Integer, nullable=True)
    gas_price = Column(Numeric(18, 0), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    nft_token = relationship("NFTToken", back_populates="transfers")
    
    __table_args__ = (
        Index('idx_transfer_from_to', 'from_address', 'to_address'),
        Index('idx_transfer_type_time', 'transfer_type', 'block_timestamp'),
    )


class NFTCollection(Base):
    """Collection analytics and statistics."""
    __tablename__ = "nft_collection_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("nft_collections.id"), nullable=False)
    
    # Statistics period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Volume statistics
    volume_eth = Column(Numeric(18, 8), nullable=False, default=0)
    volume_usd = Column(Numeric(12, 2), nullable=True)
    sales_count = Column(Integer, nullable=False, default=0)
    unique_buyers = Column(Integer, nullable=False, default=0)
    unique_sellers = Column(Integer, nullable=False, default=0)
    
    # Price statistics
    floor_price = Column(Numeric(18, 8), nullable=True)
    average_price = Column(Numeric(18, 8), nullable=True)
    median_price = Column(Numeric(18, 8), nullable=True)
    highest_sale = Column(Numeric(18, 8), nullable=True)
    
    # Listing statistics
    active_listings = Column(Integer, nullable=False, default=0)
    new_listings = Column(Integer, nullable=False, default=0)
    expired_listings = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('collection_id', 'period_start', 'period_type', name='uq_collection_period'),
        Index('idx_stats_period', 'period_type', 'period_start'),
    )


class NFTFavorite(Base):
    """User favorites for NFTs."""
    __tablename__ = "nft_favorites"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    user_address = Column(String(42), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('nft_token_id', 'user_address', name='uq_favorite_user_nft'),
        Index('idx_favorite_user_time', 'user_address', 'created_at'),
    )


class NFTView(Base):
    """NFT view tracking for analytics."""
    __tablename__ = "nft_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    
    # Viewer information
    viewer_address = Column(String(42), nullable=True, index=True)  # Null for anonymous
    viewer_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(512), nullable=True)
    
    # View context
    referrer = Column(String(512), nullable=True)
    page_type = Column(String(50), nullable=False, default="detail")  # detail, gallery, search
    
    # Timestamps
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_view_nft_time', 'nft_token_id', 'viewed_at'),
        Index('idx_view_viewer_time', 'viewer_address', 'viewed_at'),
    )


class NFTReport(Base):
    """NFT content reports."""
    __tablename__ = "nft_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nft_token_id = Column(UUID(as_uuid=True), ForeignKey("nft_tokens.id"), nullable=False)
    
    # Reporter information
    reporter_address = Column(String(42), nullable=False, index=True)
    
    # Report details
    reason = Column(String(100), nullable=False)  # copyright, inappropriate, spam, etc.
    description = Column(Text, nullable=True)
    evidence_urls = Column(JSON, nullable=True)  # URLs to supporting evidence
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, reviewed, resolved, dismissed
    moderator_notes = Column(Text, nullable=True)
    resolved_by = Column(String(42), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_report_status_time', 'status', 'created_at'),
        Index('idx_report_nft_status', 'nft_token_id', 'status'),
    )