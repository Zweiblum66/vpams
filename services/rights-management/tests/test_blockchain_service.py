"""
Tests for Blockchain Service
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..src.models.blockchain_schemas import (
    BlockchainType, BlockchainNetwork, TransactionStatus,
    BlockchainConfigCreate, BlockchainConfigUpdate,
    BlockCreate, TransactionCreate,
    RightsBlockchainRecord as RightsBlockchainRecordSchema,
    SmartContractType, SmartContractCreate,
    ContractInteraction, IPFSUpload
)
from ..src.services.blockchain_service import BlockchainService
from ..src.models.blockchain_models import (
    BlockchainConfig, Block, BlockchainTransaction,
    RightsBlockchainRecord, SmartContract
)


@pytest.fixture
def blockchain_service():
    """Create blockchain service instance"""
    service = BlockchainService()
    return service


@pytest.fixture
async def blockchain_config(db_session: AsyncSession, blockchain_service):
    """Create a test blockchain configuration"""
    config_data = BlockchainConfigCreate(
        blockchain_type=BlockchainType.PRIVATE,
        network=BlockchainNetwork.LOCAL,
        encryption_enabled=True,
        multi_sig_required=False,
        batch_size=100,
        confirmation_blocks=1,
        store_full_data=True
    )
    
    config = await blockchain_service.create_blockchain_config(db_session, config_data)
    return config


class TestBlockchainService:
    """Test blockchain service functionality"""
    
    @pytest.mark.asyncio
    async def test_create_blockchain_config(self, db_session: AsyncSession, blockchain_service):
        """Test creating blockchain configuration"""
        config_data = BlockchainConfigCreate(
            blockchain_type=BlockchainType.ETHEREUM,
            network=BlockchainNetwork.TESTNET,
            node_url="https://ropsten.infura.io/v3/test-key",
            chain_id=3,
            encryption_enabled=True,
            multi_sig_required=True,
            min_signatures=2
        )
        
        result = await blockchain_service.create_blockchain_config(db_session, config_data)
        
        assert result.id is not None
        assert result.blockchain_type == BlockchainType.ETHEREUM
        assert result.network == BlockchainNetwork.TESTNET
        assert result.node_url == config_data.node_url
        assert result.chain_id == 3
        assert result.multi_sig_required is True
        assert result.min_signatures == 2
    
    @pytest.mark.asyncio
    async def test_update_blockchain_config(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test updating blockchain configuration"""
        update_data = BlockchainConfigUpdate(
            batch_size=200,
            confirmation_blocks=3,
            encryption_enabled=False
        )
        
        result = await blockchain_service.update_blockchain_config(
            db_session,
            str(blockchain_config.id),
            update_data
        )
        
        assert result.batch_size == 200
        assert result.confirmation_blocks == 3
        assert result.encryption_enabled is False
    
    @pytest.mark.asyncio
    async def test_create_block(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test creating a block in private blockchain"""
        block_data = BlockCreate(
            data={
                "test": "data",
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata={"created_by": "test"}
        )
        
        result = await blockchain_service.create_block(
            db_session,
            str(blockchain_config.id),
            block_data
        )
        
        assert result.id is not None
        assert result.index == 0  # First block
        assert result.hash is not None
        assert result.previous_hash == "0"
        assert result.data == block_data.data
    
    @pytest.mark.asyncio
    async def test_create_transaction(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test creating a blockchain transaction"""
        transaction_data = TransactionCreate(
            transaction_type="rights_transfer",
            from_address="0x1234567890abcdef",
            to_address="0xfedcba0987654321",
            data={
                "license_id": "test-license-123",
                "transfer_date": datetime.utcnow().isoformat()
            }
        )
        
        result = await blockchain_service.create_transaction(
            db_session,
            str(blockchain_config.id),
            transaction_data,
            "test-user-123"
        )
        
        assert result.transaction_id is not None
        assert result.transaction_type == "rights_transfer"
        assert result.from_address == transaction_data.from_address
        assert result.to_address == transaction_data.to_address
        assert result.status == TransactionStatus.CONFIRMED  # Private blockchain confirms immediately
    
    @pytest.mark.asyncio
    async def test_store_rights_record(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test storing rights record on blockchain"""
        record_data = RightsBlockchainRecordSchema(
            record_type="license_creation",
            entity_id=str(uuid.uuid4()),
            entity_type="license",
            rights_data={
                "license_number": "LIC-2024-001",
                "rights_type": "broadcast",
                "territories": ["US", "CA"]
            },
            parties=[
                {"id": "party1", "role": "licensor", "name": "Content Owner Inc"},
                {"id": "party2", "role": "licensee", "name": "Broadcaster Corp"}
            ],
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        
        result = await blockchain_service.store_rights_record(
            db_session,
            str(blockchain_config.id),
            record_data,
            "test-user-123"
        )
        
        assert result.id is not None
        assert result.entity_id == record_data.entity_id
        assert result.entity_type == record_data.entity_type
        assert result.data_hash is not None
        assert result.transaction_id is not None
    
    @pytest.mark.asyncio
    async def test_verify_rights_record(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test verifying rights record on blockchain"""
        # First store a record
        record_data = RightsBlockchainRecordSchema(
            record_type="license_creation",
            entity_id="test-license-456",
            entity_type="license",
            rights_data={
                "license_number": "LIC-2024-002",
                "status": "active"
            },
            parties=[
                {"id": "party1", "role": "licensor", "name": "Rights Holder"}
            ]
        )
        
        stored_record = await blockchain_service.store_rights_record(
            db_session,
            str(blockchain_config.id),
            record_data,
            "test-user-123"
        )
        
        # Now verify it
        verification = await blockchain_service.verify_rights_record(
            db_session,
            "license",
            "test-license-456"
        )
        
        assert verification.is_valid is True
        assert verification.record_hash == stored_record.data_hash
        assert verification.transaction_id is not None
    
    @pytest.mark.asyncio
    async def test_deploy_smart_contract(self, db_session: AsyncSession, blockchain_service):
        """Test deploying a smart contract"""
        contract_data = SmartContractCreate(
            contract_type=SmartContractType.LICENSE,
            contract_name="RightsLicenseContract",
            description="Smart contract for managing rights licenses",
            abi={
                "functions": [
                    {
                        "name": "createLicense",
                        "inputs": [
                            {"name": "licenseId", "type": "string"},
                            {"name": "expiryDate", "type": "uint256"}
                        ]
                    }
                ]
            },
            bytecode="0x608060405234801561001057600080fd5b50...",  # Simplified
            deploy_immediately=True,
            constructor_params={"owner": "0x1234567890abcdef"}
        )
        
        result = await blockchain_service.deploy_smart_contract(
            db_session,
            contract_data,
            "test-user-123"
        )
        
        assert result.id is not None
        assert result.contract_type == SmartContractType.LICENSE
        assert result.contract_name == "RightsLicenseContract"
        assert result.is_deployed is True
        assert result.contract_address is not None
        assert result.deployment_transaction is not None
    
    @pytest.mark.asyncio
    async def test_interact_with_contract(self, db_session: AsyncSession, blockchain_service):
        """Test interacting with a smart contract"""
        # First deploy a contract
        contract_data = SmartContractCreate(
            contract_type=SmartContractType.LICENSE,
            contract_name="TestContract",
            abi={"functions": [{"name": "getLicense", "inputs": [{"name": "id", "type": "string"}]}]},
            deploy_immediately=True
        )
        
        contract = await blockchain_service.deploy_smart_contract(
            db_session,
            contract_data,
            "test-user-123"
        )
        
        # Now interact with it
        interaction_data = ContractInteraction(
            contract_id=str(contract.id),
            method_name="getLicense",
            parameters={"id": "123"},
            from_address="0x1234567890abcdef"
        )
        
        result = await blockchain_service.interact_with_contract(
            db_session,
            interaction_data,
            "test-user-123"
        )
        
        assert result.success is True
        assert result.transaction_hash is not None
        assert result.return_values is not None
    
    @pytest.mark.asyncio
    async def test_ipfs_upload(self, db_session: AsyncSession, blockchain_service):
        """Test uploading to IPFS"""
        # Initialize IPFS client
        await blockchain_service.initialize()
        
        upload_data = IPFSUpload(
            data={
                "license_id": "test-license-789",
                "metadata": {
                    "title": "Test Content",
                    "rights": ["broadcast", "streaming"]
                }
            },
            pin=True,
            encrypt=True
        )
        
        # This test might fail if IPFS is not running
        try:
            result = await blockchain_service.upload_to_ipfs(db_session, upload_data)
            
            assert result.ipfs_hash is not None
            assert result.size > 0
            assert result.gateway_url is not None
            assert result.pinned is True
            assert result.encrypted is True
            assert result.encryption_key is not None
        except Exception as e:
            # Skip if IPFS is not available
            if "IPFS client not initialized" in str(e):
                pytest.skip("IPFS not available")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_blockchain_stats(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test getting blockchain statistics"""
        # Create some test data
        for i in range(3):
            block_data = BlockCreate(
                data={"block": i, "test": True},
                metadata={"index": i}
            )
            await blockchain_service.create_block(
                db_session,
                str(blockchain_config.id),
                block_data
            )
        
        # Get stats
        stats = await blockchain_service.get_blockchain_stats(db_session)
        
        assert stats.total_blocks >= 3
        assert stats.total_transactions >= 0
        assert isinstance(stats.transactions_by_type, dict)
        assert stats.average_block_time >= 0
    
    @pytest.mark.asyncio
    async def test_hash_chain_verification(self, db_session: AsyncSession, blockchain_service, blockchain_config):
        """Test hash chain verification for linked records"""
        entity_id = "test-entity-chain"
        
        # Create first record
        record1 = RightsBlockchainRecordSchema(
            record_type="creation",
            entity_id=entity_id,
            entity_type="license",
            rights_data={"version": 1},
            parties=[{"id": "p1", "role": "owner"}]
        )
        
        result1 = await blockchain_service.store_rights_record(
            db_session,
            str(blockchain_config.id),
            record1,
            "user1"
        )
        
        # Create second record linked to first
        record2 = RightsBlockchainRecordSchema(
            record_type="update",
            entity_id=entity_id,
            entity_type="license",
            rights_data={"version": 2},
            parties=[{"id": "p1", "role": "owner"}]
        )
        
        result2 = await blockchain_service.store_rights_record(
            db_session,
            str(blockchain_config.id),
            record2,
            "user1"
        )
        
        # Verify the chain
        verification = await blockchain_service.verify_rights_record(
            db_session,
            "license",
            entity_id
        )
        
        assert verification.is_valid is True
        assert result2.previous_hash == result1.data_hash