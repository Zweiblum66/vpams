"""
Blockchain Database Models for Rights Management Service
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from .blockchain_schemas import BlockchainType, TransactionStatus, BlockchainNetwork, SmartContractType

Base = declarative_base()


class BlockchainConfig(Base):
    """Blockchain configuration model"""
    __tablename__ = 'blockchain_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blockchain_type = Column(SQLEnum(BlockchainType), nullable=False)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, default=BlockchainNetwork.TESTNET)
    
    # Connection settings
    node_url = Column(String(500))
    api_key = Column(String(255))
    chain_id = Column(Integer)
    contract_address = Column(String(255))
    
    # Security settings
    encryption_enabled = Column(Boolean, default=True, nullable=False)
    multi_sig_required = Column(Boolean, default=False, nullable=False)
    min_signatures = Column(Integer, default=1, nullable=False)
    
    # Performance settings
    batch_size = Column(Integer, default=100, nullable=False)
    confirmation_blocks = Column(Integer, default=6, nullable=False)
    
    # Storage settings
    store_full_data = Column(Boolean, default=False, nullable=False)
    ipfs_gateway = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Relationships
    transactions = relationship("BlockchainTransaction", back_populates="config")
    blocks = relationship("Block", back_populates="config")
    
    # Indexes
    __table_args__ = (
        Index('idx_blockchain_configs_type', 'blockchain_type'),
        Index('idx_blockchain_configs_network', 'network'),
        Index('idx_blockchain_configs_active', 'is_active'),
    )


class Block(Base):
    """Blockchain block model"""
    __tablename__ = 'blockchain_blocks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey('blockchain_configs.id'), nullable=False)
    
    # Block data
    index = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    data = Column(JSONB, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False, unique=True)
    nonce = Column(Integer, default=0, nullable=False)
    
    # Mining info
    miner = Column(String(255))
    difficulty = Column(Integer, default=4, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Relationships
    config = relationship("BlockchainConfig", back_populates="blocks")
    transactions = relationship("BlockchainTransaction", back_populates="block")
    
    # Indexes
    __table_args__ = (
        Index('idx_blockchain_blocks_index', 'index'),
        Index('idx_blockchain_blocks_hash', 'hash'),
        Index('idx_blockchain_blocks_config', 'config_id'),
        Index('idx_blockchain_blocks_timestamp', 'timestamp'),
    )


class BlockchainTransaction(Base):
    """Blockchain transaction model"""
    __tablename__ = 'blockchain_transactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(255), unique=True, nullable=False)
    config_id = Column(UUID(as_uuid=True), ForeignKey('blockchain_configs.id'), nullable=False)
    block_id = Column(UUID(as_uuid=True), ForeignKey('blockchain_blocks.id'))
    
    # Transaction data
    transaction_type = Column(String(50), nullable=False)
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    data = Column(JSONB, nullable=False)
    
    # Transaction details
    signature = Column(Text)
    gas_fee = Column(Float)
    value = Column(Float)
    
    # Status
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    confirmations = Column(Integer, default=0, nullable=False)
    
    # Blockchain info
    block_hash = Column(String(64))
    block_number = Column(Integer)
    transaction_index = Column(Integer)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime(timezone=True))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Relationships
    config = relationship("BlockchainConfig", back_populates="transactions")
    block = relationship("Block", back_populates="transactions")
    rights_records = relationship("RightsBlockchainRecord", back_populates="transaction")
    
    # Indexes
    __table_args__ = (
        Index('idx_blockchain_transactions_id', 'transaction_id'),
        Index('idx_blockchain_transactions_type', 'transaction_type'),
        Index('idx_blockchain_transactions_status', 'status'),
        Index('idx_blockchain_transactions_from', 'from_address'),
        Index('idx_blockchain_transactions_to', 'to_address'),
        Index('idx_blockchain_transactions_timestamp', 'timestamp'),
        Index('idx_blockchain_transactions_block', 'block_id'),
    )


class RightsBlockchainRecord(Base):
    """Rights blockchain record model"""
    __tablename__ = 'rights_blockchain_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('blockchain_transactions.id'))
    
    # Record data
    record_type = Column(String(50), nullable=False)
    entity_id = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False)
    
    # Rights data
    rights_data = Column(JSONB, nullable=False)
    parties = Column(JSONB, nullable=False)
    
    # Hashes
    data_hash = Column(String(64), nullable=False, unique=True)
    previous_hash = Column(String(64))
    
    # IPFS
    ipfs_hash = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))
    
    # Verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True))
    verification_details = Column(JSONB)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Relationships
    transaction = relationship("BlockchainTransaction", back_populates="rights_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_blockchain_records_entity', 'entity_type', 'entity_id'),
        Index('idx_rights_blockchain_records_type', 'record_type'),
        Index('idx_rights_blockchain_records_hash', 'data_hash'),
        Index('idx_rights_blockchain_records_created', 'created_at'),
        Index('idx_rights_blockchain_records_expires', 'expires_at'),
        Index('idx_rights_blockchain_records_verified', 'is_verified'),
    )


class SmartContract(Base):
    """Smart contract model"""
    __tablename__ = 'smart_contracts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_type = Column(SQLEnum(SmartContractType), nullable=False)
    contract_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Contract code
    abi = Column(JSONB, nullable=False)
    bytecode = Column(Text)
    source_code = Column(Text)
    
    # Deployment
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, default=BlockchainNetwork.TESTNET)
    contract_address = Column(String(255))
    deployer_address = Column(String(255))
    deployment_transaction = Column(String(255))
    deployment_block = Column(Integer)
    
    # Status
    is_deployed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Version
    version = Column(String(20), nullable=False, default='1.0.0')
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    deployed_at = Column(DateTime(timezone=True))
    
    # Relationships
    interactions = relationship("ContractInteraction", back_populates="contract")
    
    # Indexes
    __table_args__ = (
        Index('idx_smart_contracts_type', 'contract_type'),
        Index('idx_smart_contracts_name', 'contract_name'),
        Index('idx_smart_contracts_network', 'network'),
        Index('idx_smart_contracts_address', 'contract_address'),
        Index('idx_smart_contracts_deployed', 'is_deployed'),
        Index('idx_smart_contracts_active', 'is_active'),
    )


class ContractInteraction(Base):
    """Smart contract interaction log"""
    __tablename__ = 'contract_interactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey('smart_contracts.id'), nullable=False)
    
    # Interaction details
    method_name = Column(String(255), nullable=False)
    parameters = Column(JSONB)
    from_address = Column(String(255), nullable=False)
    value = Column(Float)
    
    # Transaction info
    transaction_hash = Column(String(255))
    block_number = Column(Integer)
    gas_used = Column(Integer)
    gas_limit = Column(Integer)
    
    # Results
    success = Column(Boolean, nullable=False)
    return_values = Column(JSONB)
    error_message = Column(Text)
    revert_reason = Column(Text)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Relationships
    contract = relationship("SmartContract", back_populates="interactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_contract_interactions_contract', 'contract_id'),
        Index('idx_contract_interactions_method', 'method_name'),
        Index('idx_contract_interactions_from', 'from_address'),
        Index('idx_contract_interactions_success', 'success'),
        Index('idx_contract_interactions_timestamp', 'timestamp'),
    )


class IPFSRecord(Base):
    """IPFS storage record"""
    __tablename__ = 'ipfs_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # IPFS data
    ipfs_hash = Column(String(255), unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    gateway_url = Column(String(500), nullable=False)
    
    # Storage details
    data_type = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(255))
    
    # Security
    encrypted = Column(Boolean, default=True, nullable=False)
    encryption_key_id = Column(String(255))
    
    # Status
    pinned = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    accessed_at = Column(DateTime(timezone=True))
    
    # Indexes
    __table_args__ = (
        Index('idx_ipfs_records_hash', 'ipfs_hash'),
        Index('idx_ipfs_records_entity', 'entity_type', 'entity_id'),
        Index('idx_ipfs_records_type', 'data_type'),
        Index('idx_ipfs_records_created', 'created_at'),
        Index('idx_ipfs_records_active', 'is_active'),
    )


class BlockchainAuditLog(Base):
    """Blockchain operations audit log"""
    __tablename__ = 'blockchain_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Action details
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(255), nullable=False)
    
    # Blockchain details
    blockchain_type = Column(SQLEnum(BlockchainType), nullable=False)
    transaction_hash = Column(String(255))
    block_number = Column(Integer)
    
    # User details
    user_id = Column(String(255), nullable=False)
    user_address = Column(String(255), nullable=False)
    
    # Status
    status = Column(SQLEnum(TransactionStatus), nullable=False)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime(timezone=True))
    
    # Additional data
    metadata = Column(JSONB)
    error_details = Column(JSONB)
    
    # Indexes
    __table_args__ = (
        Index('idx_blockchain_audit_logs_action', 'action'),
        Index('idx_blockchain_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_blockchain_audit_logs_user', 'user_id'),
        Index('idx_blockchain_audit_logs_status', 'status'),
        Index('idx_blockchain_audit_logs_initiated', 'initiated_at'),
    )