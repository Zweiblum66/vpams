"""
Database models for Blockchain Service.
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

Base = declarative_base()


class NetworkType(PyEnum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    AVALANCHE = "avalanche"
    BSC = "bsc"


class TransactionStatus(PyEnum):
    """Transaction status types."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RightsType(PyEnum):
    """Types of media rights."""
    OWNERSHIP = "ownership"
    LICENSE = "license"
    USAGE = "usage"
    DISTRIBUTION = "distribution"
    DERIVATIVE = "derivative"
    COMMERCIAL = "commercial"
    NON_COMMERCIAL = "non_commercial"


class LicenseStatus(PyEnum):
    """License status types."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class PaymentStatus(PyEnum):
    """Payment status types."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ContractType(PyEnum):
    """Smart contract types."""
    MEDIA_RIGHTS = "media_rights"
    NFT = "nft"
    PAYMENTS = "payments"
    PROVENANCE = "provenance"
    ROYALTY = "royalty"
    MARKETPLACE = "marketplace"
    CUSTOM = "custom"


class BlockchainAsset(Base):
    """Blockchain representation of media assets."""
    __tablename__ = "blockchain_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Reference to main asset
    token_id = Column(String(255), nullable=True, index=True)  # NFT token ID
    contract_address = Column(String(42), nullable=True, index=True)
    network = Column(Enum(NetworkType), nullable=False, default=NetworkType.POLYGON)
    
    # Asset metadata stored on IPFS
    ipfs_hash = Column(String(255), nullable=True, index=True)
    metadata_uri = Column(String(512), nullable=True)
    
    # Ownership information
    owner_address = Column(String(42), nullable=False, index=True)
    creator_address = Column(String(42), nullable=False, index=True)
    
    # Rights information
    rights_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash of rights
    royalty_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    minted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    rights = relationship("MediaRights", back_populates="asset", cascade="all, delete-orphan")
    licenses = relationship("RightsLicense", back_populates="asset", cascade="all, delete-orphan")
    transactions = relationship("BlockchainTransaction", back_populates="asset")
    
    __table_args__ = (
        UniqueConstraint('asset_id', 'network', name='uq_asset_network'),
        Index('idx_asset_network_token', 'asset_id', 'network', 'token_id'),
    )


class MediaRights(Base):
    """Media rights stored on blockchain."""
    __tablename__ = "media_rights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("blockchain_assets.id"), nullable=False)
    
    # Rights details
    rights_type = Column(Enum(RightsType), nullable=False)
    description = Column(Text, nullable=True)
    terms = Column(JSON, nullable=True)  # JSON object with rights terms
    
    # Geographic and temporal restrictions
    territories = Column(JSON, nullable=True)  # List of allowed territories
    languages = Column(JSON, nullable=True)  # List of allowed languages
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Usage restrictions
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, nullable=False, default=0)
    
    # Blockchain data
    rights_hash = Column(String(64), nullable=False, unique=True, index=True)
    transaction_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("BlockchainAsset", back_populates="rights")
    licenses = relationship("RightsLicense", back_populates="rights")


class RightsLicense(Base):
    """Licenses for media rights."""
    __tablename__ = "rights_licenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("blockchain_assets.id"), nullable=False)
    rights_id = Column(UUID(as_uuid=True), ForeignKey("media_rights.id"), nullable=False)
    
    # License details
    license_number = Column(String(255), nullable=False, unique=True, index=True)
    licensee_address = Column(String(42), nullable=False, index=True)
    licensor_address = Column(String(42), nullable=False, index=True)
    
    # License terms
    license_type = Column(Enum(RightsType), nullable=False)
    status = Column(Enum(LicenseStatus), nullable=False, default=LicenseStatus.ACTIVE)
    terms = Column(JSON, nullable=True)
    
    # Duration and usage
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, nullable=False, default=0)
    
    # Financial terms
    license_fee = Column(Numeric(18, 8), nullable=False)  # In wei/smallest unit
    royalty_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    currency = Column(String(10), nullable=False, default="ETH")
    
    # Blockchain data
    license_hash = Column(String(64), nullable=False, unique=True, index=True)
    transaction_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("BlockchainAsset", back_populates="licenses")
    rights = relationship("MediaRights", back_populates="licenses")
    payments = relationship("RoyaltyPayment", back_populates="license")
    
    __table_args__ = (
        Index('idx_license_status_dates', 'status', 'valid_from', 'valid_until'),
        Index('idx_licensee_licensor', 'licensee_address', 'licensor_address'),
    )


class BlockchainTransaction(Base):
    """Blockchain transactions."""
    __tablename__ = "blockchain_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("blockchain_assets.id"), nullable=True)
    
    # Transaction details
    transaction_hash = Column(String(66), nullable=False, unique=True, index=True)
    network = Column(Enum(NetworkType), nullable=False)
    block_number = Column(Integer, nullable=True, index=True)
    block_hash = Column(String(66), nullable=True)
    
    # Transaction data
    from_address = Column(String(42), nullable=False, index=True)
    to_address = Column(String(42), nullable=False, index=True)
    contract_address = Column(String(42), nullable=True, index=True)
    
    # Gas and fees
    gas_used = Column(Integer, nullable=True)
    gas_price = Column(Numeric(18, 0), nullable=True)  # In wei
    transaction_fee = Column(Numeric(18, 8), nullable=True)  # In ETH/native currency
    
    # Transaction status and timing
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    nonce = Column(Integer, nullable=True)
    confirmation_blocks = Column(Integer, nullable=False, default=0)
    
    # Operation details
    operation_type = Column(String(50), nullable=False, index=True)  # mint, transfer, license, etc.
    input_data = Column(Text, nullable=True)
    logs = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("BlockchainAsset", back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transaction_network_status', 'network', 'status'),
        Index('idx_transaction_operation_type', 'operation_type', 'created_at'),
    )


class RoyaltyPayment(Base):
    """Royalty payments for licenses."""
    __tablename__ = "royalty_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey("rights_licenses.id"), nullable=False)
    
    # Payment details
    payment_hash = Column(String(64), nullable=False, unique=True, index=True)
    transaction_hash = Column(String(66), nullable=True, index=True)
    
    # Financial information
    amount = Column(Numeric(18, 8), nullable=False)  # In wei/smallest unit
    currency = Column(String(10), nullable=False, default="ETH")
    usd_amount = Column(Numeric(12, 2), nullable=True)  # Converted amount
    exchange_rate = Column(Numeric(18, 8), nullable=True)
    
    # Payment parties
    payer_address = Column(String(42), nullable=False, index=True)
    recipient_address = Column(String(42), nullable=False, index=True)
    
    # Payment metadata
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    payment_type = Column(String(50), nullable=False)  # royalty, license_fee, etc.
    usage_count = Column(Integer, nullable=False, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    license = relationship("RightsLicense", back_populates="payments")
    
    __table_args__ = (
        Index('idx_payment_status_type', 'status', 'payment_type'),
        Index('idx_payment_addresses', 'payer_address', 'recipient_address'),
    )


class SmartContract(Base):
    """Smart contract deployments."""
    __tablename__ = "smart_contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contract details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contract_type = Column(Enum(ContractType), nullable=False, index=True)
    
    # Deployment information
    address = Column(String(42), nullable=False, index=True)
    network = Column(Enum(NetworkType), nullable=False)
    deployer_address = Column(String(42), nullable=False)
    deployment_hash = Column(String(66), nullable=False, index=True)
    
    # Contract metadata
    abi = Column(JSON, nullable=False)  # Contract ABI
    bytecode = Column(Text, nullable=True)
    source_code = Column(Text, nullable=True)
    compiler_version = Column(String(50), nullable=True)
    
    # Deployment details
    deployment_block = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    constructor_args = Column(JSON, nullable=True)
    
    # Status and verification
    verified = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    
    # Timestamps
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('address', 'network', name='uq_contract_address_network'),
        Index('idx_contract_type_network', 'contract_type', 'network'),
    )


class IPFSHash(Base):
    """IPFS hash storage and metadata."""
    __tablename__ = "ipfs_hashes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to main asset
    
    # IPFS details
    ipfs_hash = Column(String(255), nullable=False, unique=True, index=True)
    content_type = Column(String(100), nullable=False)  # metadata, image, video, etc.
    mime_type = Column(String(100), nullable=True)
    
    # Content information
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA-256 checksum
    
    # IPFS metadata
    pinned = Column(Boolean, nullable=False, default=False)
    pin_service = Column(String(100), nullable=True)  # Pinata, Infura, etc.
    gateway_url = Column(String(512), nullable=True)
    
    # Access control
    public = Column(Boolean, nullable=False, default=True)
    encryption_key = Column(String(255), nullable=True)  # For encrypted content
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_ipfs_content_type', 'content_type', 'created_at'),
        Index('idx_ipfs_pinned_size', 'pinned', 'file_size'),
    )


class RightsAuditLog(Base):
    """Audit log for rights operations."""
    __tablename__ = "rights_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference information
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    rights_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    license_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    transaction_hash = Column(String(66), nullable=True, index=True)
    
    # Operation details
    operation = Column(String(100), nullable=False, index=True)
    operator_address = Column(String(42), nullable=False, index=True)
    target_address = Column(String(42), nullable=True, index=True)
    
    # Change tracking
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Network and status
    network = Column(Enum(NetworkType), nullable=False)
    status = Column(String(50), nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_operation_time', 'operation', 'created_at'),
        Index('idx_audit_operator_network', 'operator_address', 'network'),
    )