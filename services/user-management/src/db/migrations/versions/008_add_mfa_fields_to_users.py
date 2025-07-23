"""Add MFA fields to users table

Revision ID: 008
Revises: 007
Create Date: 2025-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """Add MFA fields to users table"""
    # Add mfa_enabled column if it doesn't exist
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add mfa_secret column if it doesn't exist
    op.add_column('users', sa.Column('mfa_secret', sa.String(255), nullable=True))
    
    # Add backup_codes column if it doesn't exist (JSON array)
    op.add_column('users', sa.Column('backup_codes', sa.JSON(), nullable=True))
    
    # Create index on mfa_enabled for performance
    op.create_index('idx_users_mfa_enabled', 'users', ['mfa_enabled'])


def downgrade():
    """Remove MFA fields from users table"""
    # Drop index
    op.drop_index('idx_users_mfa_enabled', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')