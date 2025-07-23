"""Add blockchain storage tables

Revision ID: 003
Revises: 002
Create Date: 2025-07-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create blockchain type enum
    op.execute("""
        CREATE TYPE blockchaintype AS ENUM (
            'ethereum', 'hyperledger', 'ipfs', 'private'
        );
    """)
    
    # Create transaction status enum
    op.execute("""
        CREATE TYPE transactionstatus AS ENUM (
            'pending', 'confirmed', 'failed', 'rejected'
        );
    """)
    
    # Create blockchain network enum
    op.execute("""
        CREATE TYPE blockchainnetwork AS ENUM (
            'mainnet', 'testnet', 'private', 'local'
        );
    """)
    
    # Create smart contract type enum
    op.execute("""
        CREATE TYPE smartcontracttype AS ENUM (
            'license', 'royalty', 'usage_tracking', 'rights_transfer', 'escrow'
        );
    """)
    
    # Create blockchain_configs table
    op.create_table('blockchain_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blockchain_type', sa.Enum('ethereum', 'hyperledger', 'ipfs', 'private', 
                                            name='blockchaintype', native_enum=False), nullable=False),
        sa.Column('network', sa.Enum('mainnet', 'testnet', 'private', 'local',
                                    name='blockchainnetwork', native_enum=False), nullable=False),
        sa.Column('node_url', sa.String(length=500), nullable=True),
        sa.Column('api_key', sa.String(length=255), nullable=True),
        sa.Column('chain_id', sa.Integer(), nullable=True),
        sa.Column('contract_address', sa.String(length=255), nullable=True),
        sa.Column('encryption_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('multi_sig_required', sa.Boolean(), nullable=False, default=False),
        sa.Column('min_signatures', sa.Integer(), nullable=False, default=1),
        sa.Column('batch_size', sa.Integer(), nullable=False, default=100),
        sa.Column('confirmation_blocks', sa.Integer(), nullable=False, default=6),
        sa.Column('store_full_data', sa.Boolean(), nullable=False, default=False),
        sa.Column('ipfs_gateway', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for blockchain_configs
    op.create_index('idx_blockchain_configs_type', 'blockchain_configs', ['blockchain_type'])
    op.create_index('idx_blockchain_configs_network', 'blockchain_configs', ['network'])
    op.create_index('idx_blockchain_configs_active', 'blockchain_configs', ['is_active'])
    
    # Create blockchain_blocks table
    op.create_table('blockchain_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('index', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('nonce', sa.Integer(), nullable=False, default=0),
        sa.Column('miner', sa.String(length=255), nullable=True),
        sa.Column('difficulty', sa.Integer(), nullable=False, default=4),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['config_id'], ['blockchain_configs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hash')
    )
    
    # Create indexes for blockchain_blocks
    op.create_index('idx_blockchain_blocks_index', 'blockchain_blocks', ['index'])
    op.create_index('idx_blockchain_blocks_hash', 'blockchain_blocks', ['hash'])
    op.create_index('idx_blockchain_blocks_config', 'blockchain_blocks', ['config_id'])
    op.create_index('idx_blockchain_blocks_timestamp', 'blockchain_blocks', ['timestamp'])
    
    # Create blockchain_transactions table
    op.create_table('blockchain_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('block_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('from_address', sa.String(length=255), nullable=False),
        sa.Column('to_address', sa.String(length=255), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('gas_fee', sa.Float(), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'failed', 'rejected',
                                   name='transactionstatus', native_enum=False), nullable=False),
        sa.Column('confirmations', sa.Integer(), nullable=False, default=0),
        sa.Column('block_hash', sa.String(length=64), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('transaction_index', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['block_id'], ['blockchain_blocks.id'], ),
        sa.ForeignKeyConstraint(['config_id'], ['blockchain_configs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    
    # Create indexes for blockchain_transactions
    op.create_index('idx_blockchain_transactions_id', 'blockchain_transactions', ['transaction_id'])
    op.create_index('idx_blockchain_transactions_type', 'blockchain_transactions', ['transaction_type'])
    op.create_index('idx_blockchain_transactions_status', 'blockchain_transactions', ['status'])
    op.create_index('idx_blockchain_transactions_from', 'blockchain_transactions', ['from_address'])
    op.create_index('idx_blockchain_transactions_to', 'blockchain_transactions', ['to_address'])
    op.create_index('idx_blockchain_transactions_timestamp', 'blockchain_transactions', ['timestamp'])
    op.create_index('idx_blockchain_transactions_block', 'blockchain_transactions', ['block_id'])
    
    # Create rights_blockchain_records table
    op.create_table('rights_blockchain_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('record_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('rights_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('parties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('data_hash', sa.String(length=64), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=True),
        sa.Column('ipfs_hash', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['transaction_id'], ['blockchain_transactions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data_hash')
    )
    
    # Create indexes for rights_blockchain_records
    op.create_index('idx_rights_blockchain_records_entity', 'rights_blockchain_records', ['entity_type', 'entity_id'])
    op.create_index('idx_rights_blockchain_records_type', 'rights_blockchain_records', ['record_type'])
    op.create_index('idx_rights_blockchain_records_hash', 'rights_blockchain_records', ['data_hash'])
    op.create_index('idx_rights_blockchain_records_created', 'rights_blockchain_records', ['created_at'])
    op.create_index('idx_rights_blockchain_records_expires', 'rights_blockchain_records', ['expires_at'])
    op.create_index('idx_rights_blockchain_records_verified', 'rights_blockchain_records', ['is_verified'])
    
    # Create smart_contracts table
    op.create_table('smart_contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_type', sa.Enum('license', 'royalty', 'usage_tracking', 'rights_transfer', 'escrow',
                                         name='smartcontracttype', native_enum=False), nullable=False),
        sa.Column('contract_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('abi', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('bytecode', sa.Text(), nullable=True),
        sa.Column('source_code', sa.Text(), nullable=True),
        sa.Column('network', sa.Enum('mainnet', 'testnet', 'private', 'local',
                                    name='blockchainnetwork', native_enum=False), nullable=False),
        sa.Column('contract_address', sa.String(length=255), nullable=True),
        sa.Column('deployer_address', sa.String(length=255), nullable=True),
        sa.Column('deployment_transaction', sa.String(length=255), nullable=True),
        sa.Column('deployment_block', sa.Integer(), nullable=True),
        sa.Column('is_deployed', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('version', sa.String(length=20), nullable=False, default='1.0.0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for smart_contracts
    op.create_index('idx_smart_contracts_type', 'smart_contracts', ['contract_type'])
    op.create_index('idx_smart_contracts_name', 'smart_contracts', ['contract_name'])
    op.create_index('idx_smart_contracts_network', 'smart_contracts', ['network'])
    op.create_index('idx_smart_contracts_address', 'smart_contracts', ['contract_address'])
    op.create_index('idx_smart_contracts_deployed', 'smart_contracts', ['is_deployed'])
    op.create_index('idx_smart_contracts_active', 'smart_contracts', ['is_active'])
    
    # Create contract_interactions table
    op.create_table('contract_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('method_name', sa.String(length=255), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('from_address', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('transaction_hash', sa.String(length=255), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('gas_used', sa.Integer(), nullable=True),
        sa.Column('gas_limit', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('return_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('revert_reason', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['smart_contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for contract_interactions
    op.create_index('idx_contract_interactions_contract', 'contract_interactions', ['contract_id'])
    op.create_index('idx_contract_interactions_method', 'contract_interactions', ['method_name'])
    op.create_index('idx_contract_interactions_from', 'contract_interactions', ['from_address'])
    op.create_index('idx_contract_interactions_success', 'contract_interactions', ['success'])
    op.create_index('idx_contract_interactions_timestamp', 'contract_interactions', ['timestamp'])
    
    # Create ipfs_records table
    op.create_table('ipfs_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ipfs_hash', sa.String(length=255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('gateway_url', sa.String(length=500), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.String(length=255), nullable=True),
        sa.Column('encrypted', sa.Boolean(), nullable=False, default=True),
        sa.Column('encryption_key_id', sa.String(length=255), nullable=True),
        sa.Column('pinned', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ipfs_hash')
    )
    
    # Create indexes for ipfs_records
    op.create_index('idx_ipfs_records_hash', 'ipfs_records', ['ipfs_hash'])
    op.create_index('idx_ipfs_records_entity', 'ipfs_records', ['entity_type', 'entity_id'])
    op.create_index('idx_ipfs_records_type', 'ipfs_records', ['data_type'])
    op.create_index('idx_ipfs_records_created', 'ipfs_records', ['created_at'])
    op.create_index('idx_ipfs_records_active', 'ipfs_records', ['is_active'])
    
    # Create blockchain_audit_logs table
    op.create_table('blockchain_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=255), nullable=False),
        sa.Column('blockchain_type', sa.Enum('ethereum', 'hyperledger', 'ipfs', 'private',
                                           name='blockchaintype', native_enum=False), nullable=False),
        sa.Column('transaction_hash', sa.String(length=255), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('user_address', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'failed', 'rejected',
                                   name='transactionstatus', native_enum=False), nullable=False),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for blockchain_audit_logs
    op.create_index('idx_blockchain_audit_logs_action', 'blockchain_audit_logs', ['action'])
    op.create_index('idx_blockchain_audit_logs_entity', 'blockchain_audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_blockchain_audit_logs_user', 'blockchain_audit_logs', ['user_id'])
    op.create_index('idx_blockchain_audit_logs_status', 'blockchain_audit_logs', ['status'])
    op.create_index('idx_blockchain_audit_logs_initiated', 'blockchain_audit_logs', ['initiated_at'])


def downgrade():
    # Drop tables
    op.drop_table('blockchain_audit_logs')
    op.drop_table('ipfs_records')
    op.drop_table('contract_interactions')
    op.drop_table('smart_contracts')
    op.drop_table('rights_blockchain_records')
    op.drop_table('blockchain_transactions')
    op.drop_table('blockchain_blocks')
    op.drop_table('blockchain_configs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS blockchaintype')
    op.execute('DROP TYPE IF EXISTS transactionstatus')
    op.execute('DROP TYPE IF EXISTS blockchainnetwork')
    op.execute('DROP TYPE IF EXISTS smartcontracttype')