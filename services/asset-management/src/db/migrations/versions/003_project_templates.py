"""Add project templates table

Revision ID: 003
Revises: 002
Create Date: 2025-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Create project templates table"""
    
    # Create project_templates table
    op.create_table(
        'project_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(64), nullable=True),
        sa.Column('structure', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('default_settings', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_template_name')
    )
    
    # Create indexes
    op.create_index('idx_template_category', 'project_templates', ['category'])
    op.create_index('idx_template_owner', 'project_templates', ['owner_id'])
    op.create_index('idx_template_system', 'project_templates', ['is_system'])


def downgrade():
    """Drop project templates table"""
    
    # Drop indexes
    op.drop_index('idx_template_system', 'project_templates')
    op.drop_index('idx_template_owner', 'project_templates')
    op.drop_index('idx_template_category', 'project_templates')
    
    # Drop table
    op.drop_table('project_templates')