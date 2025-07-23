from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .web3_models import ChainType, WalletType, TransactionStatus, StorageType, TokenStandard

# Authentication schemas
class Web3AuthRequest(BaseModel):
    address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    chain_type: ChainType = ChainType.ETHEREUM

class Web3AuthChallenge(BaseModel):
    nonce: str
    message: str
    domain: str
    uri: str
    chain_id: int
    issued_at: datetime
    expiration_time: datetime
    statement: str

class Web3AuthVerify(BaseModel):
    address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    signature: str
    message: str
    chain_type: ChainType = ChainType.ETHEREUM

class Web3AuthResponse(BaseModel):
    user_id: str
    address: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Wallet schemas
class WalletBase(BaseModel):
    address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    wallet_type: WalletType
    chain_type: ChainType
    label: Optional[str] = None
    is_primary: bool = False

class WalletCreate(WalletBase):
    pass

class WalletUpdate(BaseModel):
    label: Optional[str] = None
    is_primary: Optional[bool] = None

class WalletResponse(WalletBase):
    id: uuid.UUID
    is_verified: bool
    ens_name: Optional[str] = None
    transaction_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class WalletBalance(BaseModel):
    symbol: str
    name: str
    balance: str
    balance_decimal: float
    decimals: int
    usd_price: Optional[float] = None
    usd_value: Optional[float] = None
    contract_address: Optional[str] = None
    logo_uri: Optional[str] = None

class WalletBalances(BaseModel):
    wallet_address: str
    chain_type: ChainType
    native_balance: WalletBalance
    token_balances: List[WalletBalance]
    total_usd_value: float
    last_updated: datetime

# Transaction schemas
class TransactionCreate(BaseModel):
    to_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    value: str  # Wei amount
    chain_type: ChainType
    gas_price: Optional[str] = None
    gas_limit: Optional[int] = None
    data: Optional[str] = None
    description: Optional[str] = None

class TransactionEstimate(BaseModel):
    gas_limit: int
    gas_price: str
    max_fee_per_gas: Optional[str] = None
    max_priority_fee_per_gas: Optional[str] = None
    estimated_fee_wei: str
    estimated_fee_eth: float
    estimated_fee_usd: Optional[float] = None

class TransactionResponse(BaseModel):
    id: uuid.UUID
    transaction_hash: str
    chain_type: ChainType
    from_address: str
    to_address: Optional[str] = None
    value: str
    status: TransactionStatus
    block_number: Optional[int] = None
    confirmations: int
    gas_used: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Storage schemas
class StorageUploadRequest(BaseModel):
    filename: str
    content_type: str
    file_size: int
    storage_type: StorageType = StorageType.IPFS
    is_encrypted: bool = False
    is_public: bool = True
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    pin_remote: bool = True

class StorageUploadResponse(BaseModel):
    storage_id: str
    content_hash: str
    storage_type: StorageType
    gateway_url: str
    is_pinned: bool
    estimated_cost: Optional[str] = None

class StorageRetrieveRequest(BaseModel):
    content_hash: str
    storage_type: StorageType = StorageType.IPFS

class StorageListResponse(BaseModel):
    files: List[Dict[str, Any]]
    total: int
    page: int
    limit: int

# Smart Contract schemas
class ContractDeployRequest(BaseModel):
    name: str
    contract_type: str
    source_code: str
    constructor_args: Optional[List[Any]] = None
    chain_type: ChainType
    verify_contract: bool = True

class ContractInteractRequest(BaseModel):
    contract_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    method_name: str
    args: List[Any] = []
    value: str = "0"
    chain_type: ChainType

class ContractCallRequest(BaseModel):
    contract_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    method_name: str
    args: List[Any] = []
    chain_type: ChainType

class ContractResponse(BaseModel):
    contract_address: str
    chain_type: ChainType
    name: str
    contract_type: str
    is_verified: bool
    deployment_tx_hash: str
    abi: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True

# NFT schemas
class NFTMintRequest(BaseModel):
    name: str
    description: str
    image_uri: str
    metadata: Dict[str, Any]
    recipient_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    royalty_percentage: float = 2.5
    chain_type: ChainType

class NFTTransferRequest(BaseModel):
    contract_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    token_id: str
    to_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    chain_type: ChainType

class NFTResponse(BaseModel):
    id: uuid.UUID
    contract_address: str
    token_id: str
    chain_type: ChainType
    owner_address: str
    name: Optional[str] = None
    description: Optional[str] = None
    image_uri: Optional[str] = None
    metadata_uri: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True

# DAO schemas
class DAOProposalCreate(BaseModel):
    dao_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    title: str
    description: str
    actions: List[Dict[str, Any]]  # Contract calls to execute
    chain_type: ChainType

class DAOVoteRequest(BaseModel):
    dao_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    proposal_id: int
    support: bool  # True = For, False = Against
    reason: Optional[str] = None
    chain_type: ChainType

class DAOMembershipResponse(BaseModel):
    dao_address: str
    dao_name: str
    chain_type: ChainType
    voting_power: str
    delegated_to: Optional[str] = None
    proposals_created: int
    votes_cast: int
    participation_rate: float
    
    class Config:
        from_attributes = True

# DeFi schemas
class SwapRequest(BaseModel):
    token_in: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    token_out: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    amount_in: str
    min_amount_out: str
    recipient: Optional[str] = None
    deadline: Optional[int] = None
    chain_type: ChainType

class SwapQuote(BaseModel):
    token_in: str
    token_out: str
    amount_in: str
    amount_out: str
    price_impact: float
    route: List[str]
    gas_estimate: int
    deadline: int

class LendingPosition(BaseModel):
    protocol: str
    asset: str
    amount: str
    apy: float
    is_collateral: bool
    health_factor: Optional[float] = None

# ENS schemas
class ENSResolveRequest(BaseModel):
    name: str
    chain_type: ChainType = ChainType.ETHEREUM

class ENSResolveResponse(BaseModel):
    name: str
    address: Optional[str] = None
    content_hash: Optional[str] = None
    text_records: Optional[Dict[str, str]] = None

class ENSRegisterRequest(BaseModel):
    name: str
    owner_address: str = Field(..., regex="^0x[a-fA-F0-9]{40}$")
    duration_years: int = 1
    resolver_address: Optional[str] = None

# Gas schemas
class GasPriceResponse(BaseModel):
    chain_type: ChainType
    low: float
    standard: float
    fast: float
    instant: Optional[float] = None
    base_fee: Optional[float] = None
    block_number: int
    timestamp: datetime

# Analytics schemas
class Web3Analytics(BaseModel):
    total_users: int
    total_wallets: int
    total_transactions: int
    total_storage_size: int
    active_users_24h: int
    transactions_24h: int
    storage_uploaded_24h: int
    popular_chains: List[Dict[str, Any]]
    gas_spent_usd: float

class ChainStats(BaseModel):
    chain_type: ChainType
    transaction_count: int
    unique_users: int
    total_value_transferred: str
    average_gas_price: float
    popular_contracts: List[Dict[str, Any]]

# SIWE (Sign-In with Ethereum) schemas
class SIWEMessage(BaseModel):
    domain: str
    address: str
    statement: str
    uri: str
    version: str
    chain_id: int
    nonce: str
    issued_at: str
    expiration_time: Optional[str] = None
    not_before: Optional[str] = None
    request_id: Optional[str] = None
    resources: Optional[List[str]] = None

class SIWEVerifyRequest(SIWEMessage):
    signature: str

# Web3 User schemas
class Web3UserCreate(BaseModel):
    user_id: str
    primary_address: str
    ens_name: Optional[str] = None
    web3_username: Optional[str] = None
    bio: Optional[str] = None

class Web3UserResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    primary_address: Optional[str]
    ens_name: Optional[str]
    web3_username: Optional[str]
    bio: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# DID schemas
class DIDDocument(BaseModel):
    context: List[str] = Field(default=["https://www.w3.org/ns/did/v1"], alias="@context")
    id: str
    verificationMethod: List[Dict[str, Any]]
    authentication: List[str]
    service: Optional[List[Dict[str, Any]]] = None

class DIDCreateRequest(BaseModel):
    method: str  # ethr, web, key
    address: Optional[str] = None
    domain: Optional[str] = None
    public_key: str
    services: Optional[List[Dict[str, Any]]] = None

class DIDUpdateRequest(BaseModel):
    did: str
    add_service: Optional[Dict[str, Any]] = None
    remove_service_id: Optional[str] = None
    add_verification_method: Optional[Dict[str, Any]] = None

class DIDResolutionResponse(BaseModel):
    did_document: DIDDocument
    did_document_metadata: Dict[str, Any]
    did_resolution_metadata: Dict[str, Any]

# Verifiable Credentials schemas
class VerifiableCredential(BaseModel):
    context: List[str] = Field(default=["https://www.w3.org/2018/credentials/v1"], alias="@context")
    id: str
    type: List[str]
    issuer: str
    issuanceDate: str
    credentialSubject: Dict[str, Any]
    expirationDate: Optional[str] = None
    proof: Optional[Dict[str, Any]] = None

class VerifiablePresentation(BaseModel):
    context: List[str] = Field(default=["https://www.w3.org/2018/credentials/v1"], alias="@context")
    type: List[str] = ["VerifiablePresentation"]
    holder: str
    verifiableCredential: List[VerifiableCredential]
    proof: Dict[str, Any]

# Storage schemas additions
class StorageItemResponse(BaseModel):
    storage_id: str
    content_hash: str
    storage_type: str
    filename: str
    content_type: str
    file_size: int
    is_encrypted: bool
    is_public: bool
    is_pinned: bool
    is_permanent: bool
    access_url: Optional[str]
    asset_id: Optional[str]
    tags: Optional[Dict[str, Any]]
    created_at: datetime

class StorageListResponse(BaseModel):
    items: List[StorageItemResponse]
    total: int
    limit: int
    offset: int

class IPFSPinResponse(BaseModel):
    cid: str
    pinned: bool
    remote_pinned: bool
    remote_pin_id: Optional[str]
    gateway_url: str

# Wallet schemas additions
class WalletInfo(BaseModel):
    id: str
    address: str
    wallet_type: str
    chain_type: str
    label: Optional[str]
    is_primary: bool
    is_verified: bool
    ens_name: Optional[str]
    native_balance: str
    created_at: datetime

class TokenBalanceResponse(BaseModel):
    contract_address: Optional[str]
    symbol: str
    name: str
    decimals: int
    balance: str
    balance_decimal: float
    usd_price: Optional[float]
    usd_value: Optional[float]

class TransactionRequest(BaseModel):
    to: str
    value: str
    data: Optional[str] = None
    gas_limit: Optional[int] = None
    gas_price: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    transaction_hash: str
    chain_type: str
    from_address: str
    to_address: Optional[str]
    value: str
    gas_price: str
    gas_used: Optional[int]
    status: str
    block_number: Optional[int]
    created_at: datetime
    confirmed_at: Optional[datetime]
    description: Optional[str]
    category: Optional[str]

class GasPriceResponse(BaseModel):
    chain: str
    currency: str
    slow: int
    standard: int
    fast: int
    instant: int
    block_time: float

# Health check
class HealthResponse(BaseModel):
    status: str
    service: str = "web3-integration"
    version: str = "1.0.0"
    blockchain_connections: Dict[str, bool]
    ipfs_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)