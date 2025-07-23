"""
Blockchain Schemas for Rights Management Service
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import hashlib
import json


class BlockchainType(str, Enum):
    """Supported blockchain types"""
    ETHEREUM = "ethereum"
    HYPERLEDGER = "hyperledger"
    IPFS = "ipfs"
    PRIVATE = "private"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"


class BlockchainNetwork(str, Enum):
    """Blockchain networks"""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    PRIVATE = "private"
    LOCAL = "local"


class SmartContractType(str, Enum):
    """Smart contract types"""
    LICENSE = "license"
    ROYALTY = "royalty"
    USAGE_TRACKING = "usage_tracking"
    RIGHTS_TRANSFER = "rights_transfer"
    ESCROW = "escrow"


class BlockBase(BaseModel):
    """Base block model"""
    index: int = Field(..., description="Block index in the chain")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Block data")
    previous_hash: str = Field(..., description="Hash of the previous block")
    nonce: int = Field(0, description="Proof of work nonce")
    hash: Optional[str] = Field(None, description="Block hash")


class BlockCreate(BaseModel):
    """Create block request"""
    data: Dict[str, Any] = Field(..., description="Block data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BlockResponse(BlockBase):
    """Block response"""
    miner: Optional[str] = Field(None, description="Address of the miner")
    difficulty: int = Field(4, description="Mining difficulty")
    
    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    """Base transaction model"""
    transaction_type: str = Field(..., description="Type of transaction")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    data: Dict[str, Any] = Field(..., description="Transaction data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: Optional[str] = Field(None, description="Transaction signature")


class TransactionCreate(TransactionBase):
    """Create transaction request"""
    private_key: Optional[str] = Field(None, description="Private key for signing")


class TransactionResponse(TransactionBase):
    """Transaction response"""
    transaction_id: str
    block_hash: Optional[str] = None
    block_index: Optional[int] = None
    status: TransactionStatus = TransactionStatus.PENDING
    gas_fee: Optional[float] = None
    confirmations: int = 0
    
    class Config:
        from_attributes = True


class BlockchainConfigBase(BaseModel):
    """Base blockchain configuration"""
    blockchain_type: BlockchainType = Field(..., description="Type of blockchain")
    network: BlockchainNetwork = Field(BlockchainNetwork.TESTNET)
    node_url: Optional[str] = Field(None, description="Blockchain node URL")
    api_key: Optional[str] = Field(None, description="API key for blockchain service")
    
    # Network-specific settings
    chain_id: Optional[int] = Field(None, description="Chain ID for Ethereum")
    contract_address: Optional[str] = Field(None, description="Smart contract address")
    
    # Security
    encryption_enabled: bool = Field(True, description="Enable data encryption")
    multi_sig_required: bool = Field(False, description="Require multi-signature")
    min_signatures: int = Field(1, description="Minimum signatures required")
    
    # Performance
    batch_size: int = Field(100, description="Batch size for transactions")
    confirmation_blocks: int = Field(6, description="Blocks to wait for confirmation")
    
    # Storage
    store_full_data: bool = Field(False, description="Store full data on-chain")
    ipfs_gateway: Optional[str] = Field(None, description="IPFS gateway URL")


class BlockchainConfigCreate(BlockchainConfigBase):
    """Create blockchain configuration"""
    pass


class BlockchainConfigUpdate(BaseModel):
    """Update blockchain configuration"""
    node_url: Optional[str] = None
    api_key: Optional[str] = None
    encryption_enabled: Optional[bool] = None
    multi_sig_required: Optional[bool] = None
    min_signatures: Optional[int] = None
    batch_size: Optional[int] = None
    confirmation_blocks: Optional[int] = None


class BlockchainConfigResponse(BlockchainConfigBase):
    """Blockchain configuration response"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True


class RightsBlockchainRecord(BaseModel):
    """Rights record for blockchain storage"""
    record_type: str = Field(..., description="Type of rights record")
    entity_id: str = Field(..., description="ID of the entity (license, usage, etc.)")
    entity_type: str = Field(..., description="Type of entity")
    
    # Rights data
    rights_data: Dict[str, Any] = Field(..., description="Rights information")
    
    # Parties involved
    parties: List[Dict[str, str]] = Field(..., description="Parties involved")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Verification
    hash: Optional[str] = Field(None, description="Data hash")
    previous_hash: Optional[str] = Field(None, description="Previous record hash")
    
    def calculate_hash(self) -> str:
        """Calculate hash of the record"""
        data = {
            "record_type": self.record_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "rights_data": self.rights_data,
            "parties": self.parties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "previous_hash": self.previous_hash
        }
        
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()


class BlockchainQuery(BaseModel):
    """Query blockchain records"""
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    record_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    party_id: Optional[str] = None
    include_expired: bool = False
    
    # Pagination
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class BlockchainVerification(BaseModel):
    """Blockchain verification result"""
    is_valid: bool
    record_hash: str
    blockchain_hash: Optional[str] = None
    transaction_id: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: Optional[datetime] = None
    verification_details: Dict[str, Any] = Field(default_factory=dict)


class BlockchainStats(BaseModel):
    """Blockchain statistics"""
    total_blocks: int
    total_transactions: int
    pending_transactions: int
    failed_transactions: int
    
    # By type
    transactions_by_type: Dict[str, int]
    
    # Performance
    average_block_time: float
    average_gas_fee: float
    
    # Storage
    total_data_size: int
    ipfs_objects: int
    
    # Time range
    start_date: datetime
    end_date: datetime


class SmartContractBase(BaseModel):
    """Base smart contract model"""
    contract_type: SmartContractType
    contract_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Contract details
    abi: Dict[str, Any] = Field(..., description="Contract ABI")
    bytecode: Optional[str] = Field(None, description="Contract bytecode")
    source_code: Optional[str] = Field(None, description="Contract source code")
    
    # Deployment
    network: BlockchainNetwork = BlockchainNetwork.TESTNET
    deployer_address: Optional[str] = None
    
    # Metadata
    version: str = Field("1.0.0", description="Contract version")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SmartContractCreate(SmartContractBase):
    """Create smart contract"""
    deploy_immediately: bool = Field(False, description="Deploy on creation")
    constructor_params: Optional[Dict[str, Any]] = None


class SmartContractUpdate(BaseModel):
    """Update smart contract"""
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SmartContractResponse(SmartContractBase):
    """Smart contract response"""
    id: str
    contract_address: Optional[str] = None
    deployment_transaction: Optional[str] = None
    deployment_block: Optional[int] = None
    is_deployed: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContractInteraction(BaseModel):
    """Smart contract interaction"""
    contract_id: str = Field(..., description="Contract ID")
    method_name: str = Field(..., description="Method to call")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Transaction details
    from_address: str = Field(..., description="Caller address")
    value: Optional[float] = Field(None, description="ETH value to send")
    gas_limit: Optional[int] = Field(None, description="Gas limit")
    
    # Options
    wait_for_confirmation: bool = Field(True)
    return_transaction_hash: bool = Field(False)


class ContractInteractionResult(BaseModel):
    """Contract interaction result"""
    success: bool
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    
    # Return values
    return_values: Optional[Dict[str, Any]] = None
    
    # Errors
    error_message: Optional[str] = None
    revert_reason: Optional[str] = None


class IPFSUpload(BaseModel):
    """IPFS upload request"""
    data: Dict[str, Any] = Field(..., description="Data to upload")
    metadata: Optional[Dict[str, Any]] = None
    pin: bool = Field(True, description="Pin to IPFS")
    encrypt: bool = Field(True, description="Encrypt before upload")


class IPFSResponse(BaseModel):
    """IPFS upload response"""
    ipfs_hash: str = Field(..., description="IPFS content hash")
    size: int = Field(..., description="Size in bytes")
    gateway_url: str = Field(..., description="Gateway URL")
    pinned: bool
    encrypted: bool
    encryption_key: Optional[str] = None
    timestamp: datetime


class BlockchainAuditTrail(BaseModel):
    """Blockchain audit trail entry"""
    action: str = Field(..., description="Action performed")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    
    # Blockchain details
    blockchain_type: BlockchainType
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    
    # User details
    user_id: str
    user_address: str
    
    # Status
    status: TransactionStatus
    
    # Timestamps
    initiated_at: datetime
    confirmed_at: Optional[datetime] = None
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None