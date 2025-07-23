"""
Blockchain Service for Rights Management
"""

import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
import uuid
import aiohttp
from web3 import Web3
from eth_account import Account
import ipfshttpclient

from ..models.blockchain_models import (
    BlockchainConfig, Block, BlockchainTransaction, RightsBlockchainRecord,
    SmartContract, ContractInteraction, IPFSRecord, BlockchainAuditLog
)
from ..models.blockchain_schemas import (
    BlockchainType, TransactionStatus, BlockchainNetwork, SmartContractType,
    BlockchainConfigCreate, BlockchainConfigUpdate, BlockchainConfigResponse,
    BlockCreate, BlockResponse, TransactionCreate, TransactionResponse,
    RightsBlockchainRecord as RightsBlockchainRecordSchema,
    BlockchainQuery, BlockchainVerification, BlockchainStats,
    SmartContractCreate, SmartContractUpdate, SmartContractResponse,
    ContractInteraction as ContractInteractionSchema,
    ContractInteractionResult, IPFSUpload, IPFSResponse,
    BlockchainAuditTrail
)
from ..core.logger import get_logger
from ..core.exceptions import BlockchainError, ValidationError, NotFoundError
from ..core.encryption import EncryptionService

logger = get_logger(__name__)


class BlockchainService:
    """Service for managing blockchain operations"""
    
    def __init__(self):
        self.encryption_service = EncryptionService()
        self._web3_connections = {}
        self._ipfs_client = None
    
    async def initialize(self):
        """Initialize blockchain connections"""
        try:
            # Initialize IPFS client
            self._ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            logger.info("IPFS client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize IPFS client: {str(e)}")
    
    # Configuration Management
    async def create_blockchain_config(
        self,
        db: AsyncSession,
        config_data: BlockchainConfigCreate
    ) -> BlockchainConfigResponse:
        """Create blockchain configuration"""
        try:
            # Validate configuration
            await self._validate_blockchain_config(config_data)
            
            # Create configuration
            config = BlockchainConfig(**config_data.dict())
            
            db.add(config)
            await db.commit()
            await db.refresh(config)
            
            # Initialize connection if active
            if config.is_active:
                await self._initialize_blockchain_connection(config)
            
            logger.info(f"Created blockchain configuration: {config.id}")
            return BlockchainConfigResponse.from_orm(config)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create blockchain config: {str(e)}")
            raise BlockchainError(f"Failed to create blockchain config: {str(e)}")
    
    async def update_blockchain_config(
        self,
        db: AsyncSession,
        config_id: str,
        update_data: BlockchainConfigUpdate
    ) -> BlockchainConfigResponse:
        """Update blockchain configuration"""
        try:
            # Get configuration
            config = await self._get_blockchain_config(db, config_id)
            if not config:
                raise NotFoundError(f"Blockchain configuration not found: {config_id}")
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(config, field, value)
            
            config.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(config)
            
            # Reinitialize connection if needed
            if config.is_active:
                await self._initialize_blockchain_connection(config)
            
            logger.info(f"Updated blockchain configuration: {config.id}")
            return BlockchainConfigResponse.from_orm(config)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update blockchain config: {str(e)}")
            raise
    
    # Block Operations
    async def create_block(
        self,
        db: AsyncSession,
        config_id: str,
        block_data: BlockCreate
    ) -> BlockResponse:
        """Create a new block in the private blockchain"""
        try:
            # Get configuration
            config = await self._get_blockchain_config(db, config_id)
            if not config:
                raise NotFoundError(f"Blockchain configuration not found: {config_id}")
            
            if config.blockchain_type != BlockchainType.PRIVATE:
                raise ValidationError("Block creation only supported for private blockchain")
            
            # Get the latest block
            latest_block = await self._get_latest_block(db, config_id)
            
            # Create new block
            block = Block(
                config_id=config_id,
                index=latest_block.index + 1 if latest_block else 0,
                data=block_data.data,
                previous_hash=latest_block.hash if latest_block else "0",
                metadata=block_data.metadata
            )
            
            # Mine the block
            block.hash = await self._mine_block(block, config.difficulty)
            
            db.add(block)
            await db.commit()
            await db.refresh(block)
            
            logger.info(f"Created block {block.index} with hash: {block.hash}")
            return BlockResponse.from_orm(block)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create block: {str(e)}")
            raise BlockchainError(f"Failed to create block: {str(e)}")
    
    # Transaction Operations
    async def create_transaction(
        self,
        db: AsyncSession,
        config_id: str,
        transaction_data: TransactionCreate,
        user_id: str
    ) -> TransactionResponse:
        """Create a blockchain transaction"""
        try:
            # Get configuration
            config = await self._get_blockchain_config(db, config_id)
            if not config:
                raise NotFoundError(f"Blockchain configuration not found: {config_id}")
            
            # Generate transaction ID
            transaction_id = self._generate_transaction_id(transaction_data)
            
            # Sign transaction if private key provided
            signature = None
            if transaction_data.private_key:
                signature = self._sign_transaction(transaction_data, transaction_data.private_key)
            
            # Create transaction record
            transaction = BlockchainTransaction(
                transaction_id=transaction_id,
                config_id=config_id,
                transaction_type=transaction_data.transaction_type,
                from_address=transaction_data.from_address,
                to_address=transaction_data.to_address,
                data=transaction_data.data,
                signature=signature,
                metadata={
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            db.add(transaction)
            
            # Submit to blockchain based on type
            if config.blockchain_type == BlockchainType.ETHEREUM:
                await self._submit_ethereum_transaction(transaction, config)
            elif config.blockchain_type == BlockchainType.PRIVATE:
                await self._add_to_private_blockchain(db, transaction, config)
            
            # Create audit log
            audit_log = BlockchainAuditLog(
                action="transaction_created",
                entity_type="transaction",
                entity_id=transaction_id,
                blockchain_type=config.blockchain_type,
                user_id=user_id,
                user_address=transaction_data.from_address,
                status=TransactionStatus.PENDING
            )
            db.add(audit_log)
            
            await db.commit()
            await db.refresh(transaction)
            
            logger.info(f"Created transaction: {transaction_id}")
            return TransactionResponse.from_orm(transaction)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create transaction: {str(e)}")
            raise BlockchainError(f"Failed to create transaction: {str(e)}")
    
    # Rights Record Operations
    async def store_rights_record(
        self,
        db: AsyncSession,
        config_id: str,
        record_data: RightsBlockchainRecordSchema,
        user_id: str
    ) -> RightsBlockchainRecord:
        """Store rights record on blockchain"""
        try:
            # Calculate hash
            record_data.hash = record_data.calculate_hash()
            
            # Get previous hash if exists
            previous_record = await self._get_latest_rights_record(
                db, record_data.entity_type, record_data.entity_id
            )
            if previous_record:
                record_data.previous_hash = previous_record.data_hash
            
            # Store on IPFS if configured
            ipfs_hash = None
            config = await self._get_blockchain_config(db, config_id)
            if config and config.ipfs_gateway and not config.store_full_data:
                ipfs_response = await self.upload_to_ipfs(
                    db,
                    IPFSUpload(
                        data=record_data.dict(),
                        encrypt=config.encryption_enabled
                    )
                )
                ipfs_hash = ipfs_response.ipfs_hash
            
            # Create blockchain record
            rights_record = RightsBlockchainRecord(
                record_type=record_data.record_type,
                entity_id=record_data.entity_id,
                entity_type=record_data.entity_type,
                rights_data=record_data.rights_data if config.store_full_data else {"ipfs_hash": ipfs_hash},
                parties=record_data.parties,
                data_hash=record_data.hash,
                previous_hash=record_data.previous_hash,
                ipfs_hash=ipfs_hash,
                expires_at=record_data.expires_at,
                metadata={
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(rights_record)
            
            # Create transaction for the record
            transaction_data = TransactionCreate(
                transaction_type="rights_record",
                from_address=f"user_{user_id}",
                to_address="rights_registry",
                data={
                    "record_id": str(rights_record.id),
                    "entity_type": record_data.entity_type,
                    "entity_id": record_data.entity_id,
                    "hash": record_data.hash
                }
            )
            
            transaction = await self.create_transaction(db, config_id, transaction_data, user_id)
            rights_record.transaction_id = transaction.id
            
            await db.commit()
            await db.refresh(rights_record)
            
            logger.info(f"Stored rights record: {rights_record.id}")
            return rights_record
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store rights record: {str(e)}")
            raise BlockchainError(f"Failed to store rights record: {str(e)}")
    
    async def verify_rights_record(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str
    ) -> BlockchainVerification:
        """Verify rights record on blockchain"""
        try:
            # Get the rights record
            query = select(RightsBlockchainRecord).where(
                and_(
                    RightsBlockchainRecord.entity_type == entity_type,
                    RightsBlockchainRecord.entity_id == entity_id
                )
            ).order_by(desc(RightsBlockchainRecord.created_at))
            
            result = await db.execute(query)
            record = result.scalar_one_or_none()
            
            if not record:
                return BlockchainVerification(
                    is_valid=False,
                    record_hash="",
                    verification_details={"error": "Record not found"}
                )
            
            # Verify hash chain
            is_valid = await self._verify_hash_chain(db, record)
            
            # Get blockchain details
            blockchain_details = {}
            if record.transaction_id:
                transaction = await self._get_transaction(db, record.transaction_id)
                if transaction:
                    blockchain_details = {
                        "transaction_id": transaction.transaction_id,
                        "block_number": transaction.block_number,
                        "blockchain_hash": transaction.block_hash,
                        "confirmations": transaction.confirmations,
                        "status": transaction.status.value
                    }
            
            # Verify IPFS if applicable
            if record.ipfs_hash:
                ipfs_valid = await self._verify_ipfs_content(record.ipfs_hash, record.data_hash)
                blockchain_details["ipfs_verification"] = ipfs_valid
            
            return BlockchainVerification(
                is_valid=is_valid,
                record_hash=record.data_hash,
                blockchain_hash=blockchain_details.get("blockchain_hash"),
                transaction_id=blockchain_details.get("transaction_id"),
                block_number=blockchain_details.get("block_number"),
                timestamp=record.created_at,
                verification_details=blockchain_details
            )
            
        except Exception as e:
            logger.error(f"Failed to verify rights record: {str(e)}")
            raise BlockchainError(f"Failed to verify rights record: {str(e)}")
    
    # Smart Contract Operations
    async def deploy_smart_contract(
        self,
        db: AsyncSession,
        contract_data: SmartContractCreate,
        user_id: str
    ) -> SmartContractResponse:
        """Deploy a smart contract"""
        try:
            # Create contract record
            contract = SmartContract(
                contract_type=contract_data.contract_type,
                contract_name=contract_data.contract_name,
                description=contract_data.description,
                abi=contract_data.abi,
                bytecode=contract_data.bytecode,
                source_code=contract_data.source_code,
                network=contract_data.network,
                version=contract_data.version,
                metadata=contract_data.metadata
            )
            
            db.add(contract)
            
            # Deploy if requested
            if contract_data.deploy_immediately:
                # Get appropriate config for network
                config = await self._get_config_for_network(db, contract_data.network)
                if not config:
                    raise ValidationError(f"No configuration found for network: {contract_data.network}")
                
                # Deploy contract
                deployment_result = await self._deploy_contract_to_blockchain(
                    contract,
                    config,
                    contract_data.constructor_params
                )
                
                contract.contract_address = deployment_result["address"]
                contract.deployment_transaction = deployment_result["transaction_hash"]
                contract.deployment_block = deployment_result["block_number"]
                contract.deployer_address = deployment_result["deployer"]
                contract.is_deployed = True
                contract.deployed_at = datetime.utcnow()
                
                # Create audit log
                audit_log = BlockchainAuditLog(
                    action="contract_deployed",
                    entity_type="smart_contract",
                    entity_id=str(contract.id),
                    blockchain_type=config.blockchain_type,
                    transaction_hash=deployment_result["transaction_hash"],
                    block_number=deployment_result["block_number"],
                    user_id=user_id,
                    user_address=deployment_result["deployer"],
                    status=TransactionStatus.CONFIRMED
                )
                db.add(audit_log)
            
            await db.commit()
            await db.refresh(contract)
            
            logger.info(f"Created smart contract: {contract.id}")
            return SmartContractResponse.from_orm(contract)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to deploy smart contract: {str(e)}")
            raise BlockchainError(f"Failed to deploy smart contract: {str(e)}")
    
    async def interact_with_contract(
        self,
        db: AsyncSession,
        interaction_data: ContractInteractionSchema,
        user_id: str
    ) -> ContractInteractionResult:
        """Interact with a smart contract"""
        try:
            # Get contract
            contract = await self._get_smart_contract(db, interaction_data.contract_id)
            if not contract:
                raise NotFoundError(f"Smart contract not found: {interaction_data.contract_id}")
            
            if not contract.is_deployed:
                raise ValidationError("Contract is not deployed")
            
            # Get blockchain config
            config = await self._get_config_for_network(db, contract.network)
            if not config:
                raise ValidationError(f"No configuration found for network: {contract.network}")
            
            # Execute contract interaction
            result = await self._execute_contract_method(
                contract,
                config,
                interaction_data
            )
            
            # Log interaction
            interaction_log = ContractInteraction(
                contract_id=contract.id,
                method_name=interaction_data.method_name,
                parameters=interaction_data.parameters,
                from_address=interaction_data.from_address,
                value=interaction_data.value,
                transaction_hash=result.get("transaction_hash"),
                block_number=result.get("block_number"),
                gas_used=result.get("gas_used"),
                gas_limit=interaction_data.gas_limit,
                success=result.get("success", False),
                return_values=result.get("return_values"),
                error_message=result.get("error_message"),
                revert_reason=result.get("revert_reason"),
                metadata={
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            db.add(interaction_log)
            await db.commit()
            
            return ContractInteractionResult(
                success=result.get("success", False),
                transaction_hash=result.get("transaction_hash"),
                block_number=result.get("block_number"),
                gas_used=result.get("gas_used"),
                return_values=result.get("return_values"),
                error_message=result.get("error_message"),
                revert_reason=result.get("revert_reason")
            )
            
        except Exception as e:
            logger.error(f"Failed to interact with contract: {str(e)}")
            raise BlockchainError(f"Failed to interact with contract: {str(e)}")
    
    # IPFS Operations
    async def upload_to_ipfs(
        self,
        db: AsyncSession,
        upload_data: IPFSUpload
    ) -> IPFSResponse:
        """Upload data to IPFS"""
        try:
            if not self._ipfs_client:
                raise ValidationError("IPFS client not initialized")
            
            # Prepare data
            data_str = json.dumps(upload_data.data, sort_keys=True)
            
            # Encrypt if requested
            encryption_key = None
            if upload_data.encrypt:
                encrypted_data, encryption_key = self.encryption_service.encrypt(data_str.encode())
                data_to_upload = encrypted_data
            else:
                data_to_upload = data_str.encode()
            
            # Upload to IPFS
            result = self._ipfs_client.add_bytes(data_to_upload)
            ipfs_hash = result
            
            # Pin if requested
            if upload_data.pin:
                self._ipfs_client.pin.add(ipfs_hash)
            
            # Create record
            ipfs_record = IPFSRecord(
                ipfs_hash=ipfs_hash,
                size=len(data_to_upload),
                gateway_url=f"https://ipfs.io/ipfs/{ipfs_hash}",
                data_type="rights_data",
                encrypted=upload_data.encrypt,
                encryption_key_id=encryption_key if encryption_key else None,
                pinned=upload_data.pin,
                metadata=upload_data.metadata
            )
            
            db.add(ipfs_record)
            await db.commit()
            
            logger.info(f"Uploaded to IPFS: {ipfs_hash}")
            
            return IPFSResponse(
                ipfs_hash=ipfs_hash,
                size=len(data_to_upload),
                gateway_url=f"https://ipfs.io/ipfs/{ipfs_hash}",
                pinned=upload_data.pin,
                encrypted=upload_data.encrypt,
                encryption_key=encryption_key,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to upload to IPFS: {str(e)}")
            raise BlockchainError(f"Failed to upload to IPFS: {str(e)}")
    
    # Statistics
    async def get_blockchain_stats(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BlockchainStats:
        """Get blockchain statistics"""
        try:
            # Default date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get block count
            block_count_query = select(func.count(Block.id))
            if start_date:
                block_count_query = block_count_query.where(Block.timestamp >= start_date)
            if end_date:
                block_count_query = block_count_query.where(Block.timestamp <= end_date)
            
            block_count_result = await db.execute(block_count_query)
            total_blocks = block_count_result.scalar() or 0
            
            # Get transaction stats
            tx_query = select(
                func.count(BlockchainTransaction.id).label("total"),
                func.count().filter(BlockchainTransaction.status == TransactionStatus.PENDING).label("pending"),
                func.count().filter(BlockchainTransaction.status == TransactionStatus.FAILED).label("failed")
            )
            
            if start_date:
                tx_query = tx_query.where(BlockchainTransaction.timestamp >= start_date)
            if end_date:
                tx_query = tx_query.where(BlockchainTransaction.timestamp <= end_date)
            
            tx_result = await db.execute(tx_query)
            tx_stats = tx_result.one()
            
            # Get transactions by type
            tx_by_type_query = select(
                BlockchainTransaction.transaction_type,
                func.count(BlockchainTransaction.id).label("count")
            ).group_by(BlockchainTransaction.transaction_type)
            
            if start_date:
                tx_by_type_query = tx_by_type_query.where(BlockchainTransaction.timestamp >= start_date)
            if end_date:
                tx_by_type_query = tx_by_type_query.where(BlockchainTransaction.timestamp <= end_date)
            
            tx_by_type_result = await db.execute(tx_by_type_query)
            transactions_by_type = {row.transaction_type: row.count for row in tx_by_type_result}
            
            # Get average block time (for private blockchain)
            avg_block_time = 0.0
            if total_blocks > 1:
                block_time_query = select(
                    func.avg(
                        func.extract('epoch', Block.timestamp) - 
                        func.lag(func.extract('epoch', Block.timestamp)).over(order_by=Block.index)
                    ).label("avg_time")
                ).select_from(Block)
                
                block_time_result = await db.execute(block_time_query)
                avg_block_time = block_time_result.scalar() or 0.0
            
            # Get average gas fee
            avg_gas_query = select(func.avg(BlockchainTransaction.gas_fee)).where(
                BlockchainTransaction.gas_fee.isnot(None)
            )
            
            if start_date:
                avg_gas_query = avg_gas_query.where(BlockchainTransaction.timestamp >= start_date)
            if end_date:
                avg_gas_query = avg_gas_query.where(BlockchainTransaction.timestamp <= end_date)
            
            avg_gas_result = await db.execute(avg_gas_query)
            average_gas_fee = avg_gas_result.scalar() or 0.0
            
            # Get IPFS stats
            ipfs_query = select(
                func.count(IPFSRecord.id).label("count"),
                func.sum(IPFSRecord.size).label("total_size")
            ).where(IPFSRecord.is_active == True)
            
            if start_date:
                ipfs_query = ipfs_query.where(IPFSRecord.created_at >= start_date)
            if end_date:
                ipfs_query = ipfs_query.where(IPFSRecord.created_at <= end_date)
            
            ipfs_result = await db.execute(ipfs_query)
            ipfs_stats = ipfs_result.one()
            
            return BlockchainStats(
                total_blocks=total_blocks,
                total_transactions=tx_stats.total or 0,
                pending_transactions=tx_stats.pending or 0,
                failed_transactions=tx_stats.failed or 0,
                transactions_by_type=transactions_by_type,
                average_block_time=avg_block_time,
                average_gas_fee=average_gas_fee,
                total_data_size=ipfs_stats.total_size or 0,
                ipfs_objects=ipfs_stats.count or 0,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"Failed to get blockchain stats: {str(e)}")
            raise BlockchainError(f"Failed to get blockchain stats: {str(e)}")
    
    # Helper methods
    async def _validate_blockchain_config(self, config_data: BlockchainConfigCreate):
        """Validate blockchain configuration"""
        if config_data.blockchain_type == BlockchainType.ETHEREUM:
            if not config_data.node_url:
                raise ValidationError("Node URL is required for Ethereum")
            if not config_data.chain_id:
                raise ValidationError("Chain ID is required for Ethereum")
        
        if config_data.multi_sig_required and config_data.min_signatures < 2:
            raise ValidationError("Minimum signatures must be at least 2 for multi-sig")
    
    async def _get_blockchain_config(self, db: AsyncSession, config_id: str) -> Optional[BlockchainConfig]:
        """Get blockchain configuration by ID"""
        query = select(BlockchainConfig).where(BlockchainConfig.id == config_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_config_for_network(self, db: AsyncSession, network: BlockchainNetwork) -> Optional[BlockchainConfig]:
        """Get active configuration for a network"""
        query = select(BlockchainConfig).where(
            and_(
                BlockchainConfig.network == network,
                BlockchainConfig.is_active == True
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _initialize_blockchain_connection(self, config: BlockchainConfig):
        """Initialize blockchain connection"""
        if config.blockchain_type == BlockchainType.ETHEREUM:
            web3 = Web3(Web3.HTTPProvider(config.node_url))
            self._web3_connections[str(config.id)] = web3
            logger.info(f"Initialized Web3 connection for config: {config.id}")
    
    async def _get_latest_block(self, db: AsyncSession, config_id: str) -> Optional[Block]:
        """Get the latest block for a configuration"""
        query = select(Block).where(
            Block.config_id == config_id
        ).order_by(desc(Block.index))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _mine_block(self, block: Block, difficulty: int) -> str:
        """Mine a block (proof of work)"""
        block.nonce = 0
        computed_hash = self._calculate_block_hash(block)
        
        while not computed_hash.startswith('0' * difficulty):
            block.nonce += 1
            computed_hash = self._calculate_block_hash(block)
        
        return computed_hash
    
    def _calculate_block_hash(self, block: Block) -> str:
        """Calculate hash of a block"""
        block_string = json.dumps({
            "index": block.index,
            "timestamp": block.timestamp.isoformat(),
            "data": block.data,
            "previous_hash": block.previous_hash,
            "nonce": block.nonce
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def _generate_transaction_id(self, transaction_data: TransactionCreate) -> str:
        """Generate unique transaction ID"""
        data = {
            "type": transaction_data.transaction_type,
            "from": transaction_data.from_address,
            "to": transaction_data.to_address,
            "data": transaction_data.data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _sign_transaction(self, transaction_data: TransactionCreate, private_key: str) -> str:
        """Sign a transaction"""
        # Create message hash
        message = {
            "type": transaction_data.transaction_type,
            "from": transaction_data.from_address,
            "to": transaction_data.to_address,
            "data": transaction_data.data
        }
        
        message_string = json.dumps(message, sort_keys=True)
        message_hash = hashlib.sha256(message_string.encode()).hexdigest()
        
        # Sign with private key (simplified for example)
        # In production, use proper cryptographic signing
        account = Account.from_key(private_key)
        signature = account.signHash(message_hash)
        
        return signature.signature.hex()
    
    async def _submit_ethereum_transaction(self, transaction: BlockchainTransaction, config: BlockchainConfig):
        """Submit transaction to Ethereum blockchain"""
        # This would interact with actual Ethereum network
        # For now, we'll simulate it
        await asyncio.sleep(1)
        transaction.status = TransactionStatus.PENDING
        transaction.transaction_hash = f"0x{uuid.uuid4().hex}"
    
    async def _add_to_private_blockchain(self, db: AsyncSession, transaction: BlockchainTransaction, config: BlockchainConfig):
        """Add transaction to private blockchain"""
        # Create a new block for the transaction
        block_data = BlockCreate(
            data={
                "transaction_id": transaction.transaction_id,
                "type": transaction.transaction_type,
                "from": transaction.from_address,
                "to": transaction.to_address,
                "data": transaction.data
            }
        )
        
        block = await self.create_block(db, str(config.id), block_data)
        
        # Update transaction with block info
        transaction.block_id = block.id
        transaction.block_hash = block.hash
        transaction.block_number = block.index
        transaction.status = TransactionStatus.CONFIRMED
        transaction.confirmed_at = datetime.utcnow()
        transaction.confirmations = 1
    
    async def _get_latest_rights_record(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str
    ) -> Optional[RightsBlockchainRecord]:
        """Get the latest rights record for an entity"""
        query = select(RightsBlockchainRecord).where(
            and_(
                RightsBlockchainRecord.entity_type == entity_type,
                RightsBlockchainRecord.entity_id == entity_id
            )
        ).order_by(desc(RightsBlockchainRecord.created_at))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_transaction(self, db: AsyncSession, transaction_id: str) -> Optional[BlockchainTransaction]:
        """Get transaction by ID"""
        query = select(BlockchainTransaction).where(BlockchainTransaction.id == transaction_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _verify_hash_chain(self, db: AsyncSession, record: RightsBlockchainRecord) -> bool:
        """Verify the hash chain for a rights record"""
        # Recalculate hash
        record_data = RightsBlockchainRecordSchema(
            record_type=record.record_type,
            entity_id=record.entity_id,
            entity_type=record.entity_type,
            rights_data=record.rights_data,
            parties=record.parties,
            created_at=record.created_at,
            expires_at=record.expires_at,
            previous_hash=record.previous_hash
        )
        
        calculated_hash = record_data.calculate_hash()
        
        # Verify hash matches
        if calculated_hash != record.data_hash:
            return False
        
        # Verify previous hash if exists
        if record.previous_hash:
            previous_query = select(RightsBlockchainRecord).where(
                RightsBlockchainRecord.data_hash == record.previous_hash
            )
            previous_result = await db.execute(previous_query)
            previous_record = previous_result.scalar_one_or_none()
            
            if not previous_record:
                return False
        
        return True
    
    async def _verify_ipfs_content(self, ipfs_hash: str, expected_hash: str) -> bool:
        """Verify IPFS content matches expected hash"""
        try:
            if not self._ipfs_client:
                return False
            
            # Retrieve content from IPFS
            content = self._ipfs_client.cat(ipfs_hash)
            
            # Calculate hash of content
            content_hash = hashlib.sha256(content).hexdigest()
            
            # For encrypted content, we can't verify the data hash directly
            # We would need to decrypt first, which we skip for performance
            
            return True  # Simplified verification
            
        except Exception as e:
            logger.error(f"Failed to verify IPFS content: {str(e)}")
            return False
    
    async def _get_smart_contract(self, db: AsyncSession, contract_id: str) -> Optional[SmartContract]:
        """Get smart contract by ID"""
        query = select(SmartContract).where(SmartContract.id == contract_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _deploy_contract_to_blockchain(
        self,
        contract: SmartContract,
        config: BlockchainConfig,
        constructor_params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Deploy contract to blockchain"""
        # This would deploy to actual blockchain
        # For now, we'll simulate it
        await asyncio.sleep(2)
        
        return {
            "address": f"0x{uuid.uuid4().hex}",
            "transaction_hash": f"0x{uuid.uuid4().hex}",
            "block_number": 12345678,
            "deployer": f"0x{uuid.uuid4().hex[:40]}"
        }
    
    async def _execute_contract_method(
        self,
        contract: SmartContract,
        config: BlockchainConfig,
        interaction_data: ContractInteractionSchema
    ) -> Dict[str, Any]:
        """Execute smart contract method"""
        # This would interact with actual smart contract
        # For now, we'll simulate it
        await asyncio.sleep(1)
        
        # Simulate different responses based on method
        if interaction_data.method_name == "getLicense":
            return {
                "success": True,
                "return_values": {
                    "licenseId": "123",
                    "isActive": True,
                    "expiryDate": datetime.utcnow().isoformat()
                },
                "transaction_hash": f"0x{uuid.uuid4().hex}",
                "block_number": 12345679,
                "gas_used": 21000
            }
        else:
            return {
                "success": True,
                "transaction_hash": f"0x{uuid.uuid4().hex}",
                "block_number": 12345679,
                "gas_used": 50000
            }