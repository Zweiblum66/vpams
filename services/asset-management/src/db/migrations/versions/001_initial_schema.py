"""Initial schema for Asset Management Service

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE assetstatus AS ENUM ('uploading', 'processing', 'active', 'archived', 'deleted', 'error')")
    op.execute("CREATE TYPE assettype AS ENUM ('video', 'audio', 'image', 'document', 'subtitle', 'project', 'other')")
    op.execute("CREATE TYPE containertype AS ENUM ('project', 'folder', 'bin', 'shotlist', 'sequence')")
    
    # Create project_containers table
    op.create_table('project_containers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('container_type', postgresql.ENUM('project', 'folder', 'bin', 'shotlist', 'sequence', name='containertype'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('path', sa.String(length=1024), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['project_containers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_container_parent', 'project_containers', ['parent_id'], unique=False)
    op.create_index('idx_container_path', 'project_containers', ['path'], unique=False)
    op.create_index('idx_container_type_owner', 'project_containers', ['container_type', 'owner_id'], unique=False)
    
    # Create assets table
    op.create_table('assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('file_extension', sa.String(length=32), nullable=True),
        sa.Column('asset_type', postgresql.ENUM('video', 'audio', 'image', 'document', 'subtitle', 'project', 'other', name='assettype'), nullable=False),
        sa.Column('status', postgresql.ENUM('uploading', 'processing', 'active', 'archived', 'deleted', 'error', name='assetstatus'), nullable=False),
        sa.Column('technical_metadata', sa.JSON(), nullable=True),
        sa.Column('storage_driver', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('storage_tier', sa.String(length=32), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('file_size >= 0', name='check_file_size_positive'),
        sa.ForeignKeyConstraint(['project_id'], ['project_containers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_asset_created', 'assets', ['created_at'], unique=False)
    op.create_index('idx_asset_name_project', 'assets', ['name', 'project_id'], unique=False)
    op.create_index('idx_asset_owner_project', 'assets', ['owner_id', 'project_id'], unique=False)
    op.create_index('idx_asset_type_status', 'assets', ['asset_type', 'status'], unique=False)
    op.create_index(op.f('ix_assets_file_hash'), 'assets', ['file_hash'], unique=False)
    op.create_index(op.f('ix_assets_name'), 'assets', ['name'], unique=False)
    
    # Create asset_versions table
    op.create_table('asset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_label', sa.String(length=64), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('storage_driver', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('storage_tier', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'version_number', name='uq_asset_version')
    )
    op.create_index('idx_version_current', 'asset_versions', ['asset_id', 'is_current'], unique=False)
    
    # Create asset_relationships table
    op.create_table('asset_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(length=64), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('source_asset_id != target_asset_id', name='check_different_assets'),
        sa.ForeignKeyConstraint(['source_asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_asset_id', 'target_asset_id', 'relationship_type', name='uq_asset_relationship')
    )
    op.create_index('idx_relationship_type', 'asset_relationships', ['relationship_type'], unique=False)
    
    # Create tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_category'), 'tags', ['category'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)
    
    # Create collections table
    op.create_table('collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('cover_asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['cover_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collection_owner', 'collections', ['owner_id'], unique=False)
    
    # Create asset_shares table
    op.create_table('asset_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_type', sa.String(length=32), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_download', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.Column('can_share', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_hash', sa.String(length=128), nullable=True),
        sa.Column('download_limit', sa.Integer(), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=True),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'shared_with_id', 'shared_with_type', name='uq_asset_share')
    )
    op.create_index('idx_share_expires', 'asset_shares', ['expires_at'], unique=False)
    op.create_index('idx_share_target', 'asset_shares', ['shared_with_id', 'shared_with_type'], unique=False)
    
    # Create asset_tags association table
    op.create_table('asset_tags',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('asset_id', 'tag_id', name='uq_asset_tag')
    )
    
    # Create asset_collections association table
    op.create_table('asset_collections',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('asset_id', 'collection_id', name='uq_asset_collection')
    )


def downgrade() -> None:
    # Drop association tables
    op.drop_table('asset_collections')
    op.drop_table('asset_tags')
    
    # Drop main tables
    op.drop_table('asset_shares')
    op.drop_table('collections')
    op.drop_table('tags')
    op.drop_table('asset_relationships')
    op.drop_table('asset_versions')
    op.drop_table('assets')
    op.drop_table('project_containers')
    
    # Drop enums
    op.execute('DROP TYPE containertype')
    op.execute('DROP TYPE assettype')
    op.execute('DROP TYPE assetstatus')