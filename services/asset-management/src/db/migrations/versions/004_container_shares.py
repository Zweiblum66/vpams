"""Add container shares table

Revision ID: 004
Revises: 003
Create Date: 2025-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create container shares table"""
    
    # Create container_shares table
    op.create_table(
        'container_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_type', sa.String(32), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_add_assets', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_share', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['container_id'], ['project_containers.id'], ondelete='CASCADE'),
        sa.CheckConstraint("shared_with_type IN ('user', 'group')", name='check_share_type')
    )
    
    # Create indexes
    op.create_index('idx_share_target', 'container_shares', ['shared_with_id', 'shared_with_type'])
    op.create_index('idx_share_expires', 'container_shares', ['expires_at'])
    op.create_index('idx_share_container', 'container_shares', ['container_id'])
    
    # Create unique constraint
    op.create_unique_constraint(
        'uq_container_share', 
        'container_shares', 
        ['container_id', 'shared_with_id', 'shared_with_type']
    )


def downgrade():
    """Drop container shares table"""
    
    # Drop indexes
    op.drop_index('idx_share_container', 'container_shares')
    op.drop_index('idx_share_expires', 'container_shares')
    op.drop_index('idx_share_target', 'container_shares')
    
    # Drop table
    op.drop_table('container_shares')