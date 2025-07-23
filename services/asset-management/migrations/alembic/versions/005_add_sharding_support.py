"""Add sharding support

Revision ID: 005_add_sharding_support
Revises: 004_add_container_shares
Create Date: 2025-07-19

This migration adds support for database sharding by creating shard metadata
tables and updating existing tables with shard-aware indexes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '005_add_sharding_support'
down_revision = '004_add_container_shares'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add sharding support tables and indexes"""
    
    # Create shard metadata table
    op.create_table(
        'shard_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('shard_id', sa.String(64), nullable=False, unique=True),
        sa.Column('shard_type', sa.String(32), nullable=False),  # primary, replica
        sa.Column('database_url', sa.Text(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, default=1.0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_read_only', sa.Boolean(), nullable=False, default=False),
        sa.Column('regions', postgresql.ARRAY(sa.String()), default=[]),
        sa.Column('min_range', sa.String(255)),
        sa.Column('max_range', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )
    
    # Create shard key mapping table for tracking which entities are on which shards
    op.create_table(
        'shard_key_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('entity_type', sa.String(64), nullable=False),  # asset, project, etc.
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shard_id', sa.String(64), nullable=False),
        sa.Column('shard_key', sa.String(64), nullable=False),  # project_id, owner_id, etc.
        sa.Column('shard_key_value', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('idx_shard_mapping_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_shard_mapping_shard', 'shard_id'),
        sa.Index('idx_shard_mapping_key', 'shard_key', 'shard_key_value'),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_entity_shard')
    )
    
    # Create shard migration history table
    op.create_table(
        'shard_migrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_shard_id', sa.String(64), nullable=False),
        sa.Column('to_shard_id', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),  # pending, in_progress, completed, failed
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('idx_migration_status', 'status'),
        sa.Index('idx_migration_entity', 'entity_type', 'entity_id')
    )
    
    # Create shard statistics table for monitoring
    op.create_table(
        'shard_statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('shard_id', sa.String(64), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_count', sa.BigInteger(), nullable=False, default=0),
        sa.Column('total_size_bytes', sa.BigInteger(), nullable=False, default=0),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('idx_shard_stats', 'shard_id', 'entity_type'),
        sa.UniqueConstraint('shard_id', 'entity_type', name='uq_shard_entity_stats')
    )
    
    # Add shard-aware indexes to existing tables
    
    # Assets table - add composite indexes for shard keys
    op.create_index('idx_asset_project_created', 'assets', ['project_id', 'created_at'])
    op.create_index('idx_asset_owner_created', 'assets', ['owner_id', 'created_at'])
    op.create_index('idx_asset_project_type', 'assets', ['project_id', 'asset_type'])
    
    # Add shard_id column to assets for tracking (optional, for optimization)
    op.add_column('assets', sa.Column('shard_id', sa.String(64)))
    op.create_index('idx_asset_shard', 'assets', ['shard_id'])
    
    # Project containers - add shard-aware indexes
    op.create_index('idx_container_owner_type', 'project_containers', ['owner_id', 'container_type'])
    op.add_column('project_containers', sa.Column('shard_id', sa.String(64)))
    op.create_index('idx_container_shard', 'project_containers', ['shard_id'])
    
    # Asset versions - ensure they follow the same shard as their parent asset
    op.add_column('asset_versions', sa.Column('shard_id', sa.String(64)))
    op.create_index('idx_version_shard', 'asset_versions', ['shard_id'])
    
    # Create stored procedures for cross-shard queries
    op.execute("""
        CREATE OR REPLACE FUNCTION get_asset_count_by_shard()
        RETURNS TABLE(shard_id VARCHAR, asset_count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT a.shard_id, COUNT(*)::BIGINT
            FROM assets a
            WHERE a.shard_id IS NOT NULL
            GROUP BY a.shard_id;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION migrate_entity_to_shard(
            p_entity_type VARCHAR,
            p_entity_id UUID,
            p_target_shard VARCHAR
        ) RETURNS BOOLEAN AS $$
        DECLARE
            v_migration_id UUID;
        BEGIN
            -- Record migration intent
            INSERT INTO shard_migrations (
                entity_type, entity_id, from_shard_id, to_shard_id, status, started_at
            )
            SELECT 
                p_entity_type, 
                p_entity_id,
                COALESCE(
                    CASE p_entity_type
                        WHEN 'asset' THEN (SELECT shard_id FROM assets WHERE id = p_entity_id)
                        WHEN 'project' THEN (SELECT shard_id FROM project_containers WHERE id = p_entity_id)
                    END,
                    'unknown'
                ),
                p_target_shard,
                'pending',
                NOW()
            RETURNING id INTO v_migration_id;
            
            -- Update shard_id on the entity
            CASE p_entity_type
                WHEN 'asset' THEN
                    UPDATE assets SET shard_id = p_target_shard WHERE id = p_entity_id;
                WHEN 'project' THEN
                    UPDATE project_containers SET shard_id = p_target_shard WHERE id = p_entity_id;
            END CASE;
            
            -- Update migration status
            UPDATE shard_migrations 
            SET status = 'completed', completed_at = NOW()
            WHERE id = v_migration_id;
            
            RETURN TRUE;
        EXCEPTION
            WHEN OTHERS THEN
                UPDATE shard_migrations 
                SET status = 'failed', error_message = SQLERRM
                WHERE id = v_migration_id;
                RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create triggers to maintain shard statistics
    op.execute("""
        CREATE OR REPLACE FUNCTION update_shard_statistics()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO shard_statistics (shard_id, entity_type, entity_count, total_size_bytes)
                VALUES (NEW.shard_id, TG_TABLE_NAME, 1, COALESCE(NEW.file_size, 0))
                ON CONFLICT (shard_id, entity_type)
                DO UPDATE SET 
                    entity_count = shard_statistics.entity_count + 1,
                    total_size_bytes = shard_statistics.total_size_bytes + COALESCE(NEW.file_size, 0),
                    last_updated = NOW();
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE shard_statistics
                SET entity_count = GREATEST(0, entity_count - 1),
                    total_size_bytes = GREATEST(0, total_size_bytes - COALESCE(OLD.file_size, 0)),
                    last_updated = NOW()
                WHERE shard_id = OLD.shard_id AND entity_type = TG_TABLE_NAME;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER update_asset_shard_stats
        AFTER INSERT OR DELETE ON assets
        FOR EACH ROW
        WHEN (NEW.shard_id IS NOT NULL OR OLD.shard_id IS NOT NULL)
        EXECUTE FUNCTION update_shard_statistics();
    """)


def downgrade() -> None:
    """Remove sharding support"""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_asset_shard_stats ON assets;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_shard_statistics();")
    op.execute("DROP FUNCTION IF EXISTS migrate_entity_to_shard(VARCHAR, UUID, VARCHAR);")
    op.execute("DROP FUNCTION IF EXISTS get_asset_count_by_shard();")
    
    # Drop columns
    op.drop_column('asset_versions', 'shard_id')
    op.drop_column('project_containers', 'shard_id')
    op.drop_column('assets', 'shard_id')
    
    # Drop indexes
    op.drop_index('idx_version_shard', 'asset_versions')
    op.drop_index('idx_container_shard', 'project_containers')
    op.drop_index('idx_asset_shard', 'assets')
    op.drop_index('idx_container_owner_type', 'project_containers')
    op.drop_index('idx_asset_project_type', 'assets')
    op.drop_index('idx_asset_owner_created', 'assets')
    op.drop_index('idx_asset_project_created', 'assets')
    
    # Drop tables
    op.drop_table('shard_statistics')
    op.drop_table('shard_migrations')
    op.drop_table('shard_key_mappings')
    op.drop_table('shard_metadata')