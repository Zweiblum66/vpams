from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum
from ..db.base import Base

class ChainType(str, Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    AVALANCHE = "avalanche"
    BSC = "bsc"
    FANTOM = "fantom"
    GNOSIS = "gnosis"

class WalletType(str, Enum):
    METAMASK = "metamask"
    WALLETCONNECT = "walletconnect"
    COINBASE = "coinbase"
    LEDGER = "ledger"
    TREZOR = "trezor"
    GNOSIS_SAFE = "gnosis_safe"
    ARGENT = "argent"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"
    REPLACED = "replaced"

class StorageType(str, Enum):
    IPFS = "ipfs"
    ARWEAVE = "arweave"
    FILECOIN = "filecoin"
    STORJ = "storj"
    SIA = "sia"

class TokenStandard(str, Enum):
    ERC20 = "erc20"
    ERC721 = "erc721"
    ERC1155 = "erc1155"
    ERC4626 = "erc4626"  # Tokenized Vaults
    ERC2981 = "erc2981"  # NFT Royalty Standard

class Web3User(Base):
    __tablename__ = "web3_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, index=True, nullable=False)  # MAMS user ID
    primary_address = Column(String(42), index=True, nullable=True)  # Primary wallet address
    ens_name = Column(String(255), nullable=True)
    
    # Authentication
    nonce = Column(String(255), nullable=True)  # For SIWE
    siwe_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Profile
    web3_username = Column(String(255), nullable=True)
    avatar_ipfs_hash = Column(String(255), nullable=True)
    bio = Column(String(1000), nullable=True)
    
    # Settings
    preferred_chain = Column(SQLEnum(ChainType), default=ChainType.ETHEREUM)
    gas_price_preference = Column(String(20), default="standard")  # low, standard, fast
    enable_notifications = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    wallets = relationship("Web3Wallet", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Web3Transaction", back_populates="user")
    stored_files = relationship("DecentralizedStorage", back_populates="user")
    nfts = relationship("NFTAsset", back_populates="owner")
    dao_memberships = relationship("DAOMembership", back_populates="user")

class Web3Wallet(Base):
    __tablename__ = "web3_wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("web3_users.id"), nullable=False)
    
    address = Column(String(42), unique=True, index=True, nullable=False)
    wallet_type = Column(SQLEnum(WalletType), nullable=False)
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Wallet info
    label = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # ENS
    ens_name = Column(String(255), nullable=True)
    reverse_ens_set = Column(Boolean, default=False)
    
    # Security
    is_multisig = Column(Boolean, default=False)
    multisig_threshold = Column(Integer, nullable=True)
    multisig_owners = Column(JSON, nullable=True)  # List of owner addresses
    
    # Activity
    first_transaction_at = Column(DateTime(timezone=True), nullable=True)
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    transaction_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("Web3User", back_populates="wallets")
    balances = relationship("TokenBalance", back_populates="wallet", cascade="all, delete-orphan")

class Web3Transaction(Base):
    __tablename__ = "web3_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_hash = Column(String(66), unique=True, index=True, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("web3_users.id"), nullable=False)
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Transaction details
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42), nullable=True)  # Null for contract creation
    value = Column(String(78), nullable=False)  # Wei amount as string
    gas_price = Column(String(78), nullable=False)
    gas_limit = Column(Integer, nullable=False)
    gas_used = Column(Integer, nullable=True)
    
    # Contract interaction
    is_contract_interaction = Column(Boolean, default=False)
    contract_address = Column(String(42), nullable=True)
    method_name = Column(String(255), nullable=True)
    input_data = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    block_number = Column(Integer, nullable=True)
    block_timestamp = Column(DateTime(timezone=True), nullable=True)
    confirmations = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(String, nullable=True)
    revert_reason = Column(String, nullable=True)
    
    # Metadata
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)  # transfer, swap, mint, etc.
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("Web3User", back_populates="transactions")

class DecentralizedStorage(Base):
    __tablename__ = "decentralized_storage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_id = Column(String(255), unique=True, index=True, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("web3_users.id"), nullable=False)
    asset_id = Column(String(255), index=True, nullable=True)  # MAMS asset ID
    
    # Storage details
    storage_type = Column(SQLEnum(StorageType), nullable=False)
    content_hash = Column(String(255), index=True, nullable=False)  # IPFS CID, Arweave ID, etc.
    
    # File info
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    
    # Pinning/Permanence
    is_pinned = Column(Boolean, default=True)
    pin_service = Column(String(50), nullable=True)  # pinata, infura, etc.
    is_permanent = Column(Boolean, default=False)  # True for Arweave, Filecoin deals
    
    # Encryption
    is_encrypted = Column(Boolean, default=False)
    encryption_key_hash = Column(String(255), nullable=True)
    
    # Access control
    is_public = Column(Boolean, default=True)
    access_list = Column(JSON, nullable=True)  # List of addresses with access
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Cost tracking
    storage_cost = Column(String(78), nullable=True)  # Wei/AR/FIL amount
    payment_tx_hash = Column(String(66), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("Web3User", back_populates="stored_files")

class SmartContract(Base):
    __tablename__ = "smart_contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_address = Column(String(42), unique=True, index=True, nullable=False)
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Contract info
    name = Column(String(255), nullable=False)
    symbol = Column(String(50), nullable=True)  # For tokens
    contract_type = Column(String(50), nullable=False)  # token, nft, dao, defi, etc.
    token_standard = Column(SQLEnum(TokenStandard), nullable=True)
    
    # Deployment
    deployer_address = Column(String(42), nullable=False)
    deployment_tx_hash = Column(String(66), nullable=False)
    deployment_block = Column(Integer, nullable=False)
    deployment_timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    source_code = Column(String, nullable=True)
    abi = Column(JSON, nullable=False)
    
    # Metadata
    description = Column(String(1000), nullable=True)
    website = Column(String(255), nullable=True)
    social_links = Column(JSON, nullable=True)
    logo_uri = Column(String(500), nullable=True)
    
    # Proxy info
    is_proxy = Column(Boolean, default=False)
    implementation_address = Column(String(42), nullable=True)
    
    # Usage stats
    interaction_count = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    total_value_locked = Column(String(78), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class NFTAsset(Base):
    __tablename__ = "nft_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # NFT identification
    contract_address = Column(String(42), nullable=False)
    token_id = Column(String(78), nullable=False)  # Support for large token IDs
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("web3_users.id"), nullable=False)
    owner_address = Column(String(42), nullable=False)
    
    # Metadata
    name = Column(String(255), nullable=True)
    description = Column(String(2000), nullable=True)
    image_uri = Column(String(500), nullable=True)
    metadata_uri = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    # MAMS integration
    mams_asset_id = Column(String(255), nullable=True)  # Link to MAMS asset
    metadata_ipfs_hash = Column(String(255), nullable=True)
    
    # Properties
    attributes = Column(JSON, nullable=True)
    token_standard = Column(SQLEnum(TokenStandard), default=TokenStandard.ERC721)
    
    # Royalties (ERC2981)
    royalty_recipient = Column(String(42), nullable=True)
    royalty_percentage = Column(Float, nullable=True)
    
    # Timestamps
    minted_at = Column(DateTime(timezone=True), nullable=True)
    acquired_at = Column(DateTime(timezone=True), nullable=False)
    last_transfer_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner = relationship("Web3User", back_populates="nfts")

class TokenBalance(Base):
    __tablename__ = "token_balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("web3_wallets.id"), nullable=False)
    
    # Token identification
    contract_address = Column(String(42), nullable=True)  # Null for native token
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Token info
    symbol = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    decimals = Column(Integer, nullable=False)
    
    # Balance
    balance = Column(String(78), nullable=False)  # Raw balance as string
    balance_decimal = Column(Float, nullable=False)  # Human-readable balance
    
    # Value
    usd_price = Column(Float, nullable=True)
    usd_value = Column(Float, nullable=True)
    
    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    wallet = relationship("Web3Wallet", back_populates="balances")

class DAOMembership(Base):
    __tablename__ = "dao_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("web3_users.id"), nullable=False)
    
    # DAO identification
    dao_address = Column(String(42), nullable=False)
    dao_name = Column(String(255), nullable=False)
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Membership details
    member_address = Column(String(42), nullable=False)
    voting_power = Column(String(78), nullable=False)
    delegated_to = Column(String(42), nullable=True)
    
    # Participation
    proposals_created = Column(Integer, default=0)
    votes_cast = Column(Integer, default=0)
    participation_rate = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("Web3User", back_populates="dao_memberships")

class GasPrice(Base):
    __tablename__ = "gas_prices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_type = Column(SQLEnum(ChainType), nullable=False)
    
    # Gas prices in Gwei
    low = Column(Float, nullable=False)
    standard = Column(Float, nullable=False)
    fast = Column(Float, nullable=False)
    instant = Column(Float, nullable=True)
    
    # Base fee (EIP-1559)
    base_fee = Column(Float, nullable=True)
    priority_fee_low = Column(Float, nullable=True)
    priority_fee_standard = Column(Float, nullable=True)
    priority_fee_fast = Column(Float, nullable=True)
    
    # Block info
    block_number = Column(Integer, nullable=False)
    block_time = Column(Float, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index for efficient queries
    __table_args__ = (
        Column('chain_timestamp_idx', chain_type, timestamp),
    )