"""add auth_provider to users

Revision ID: 006
Revises: 005
Create Date: 2024-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    """Add auth_provider column to users table"""
    # Add auth_provider column
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), nullable=False, server_default='local'))
    
    # Allow null password_hash for LDAP users
    op.alter_column('users', 'password_hash', nullable=True)
    
    # Add index for auth_provider
    op.create_index('idx_users_auth_provider', 'users', ['auth_provider'])
    
    # Add constraint to ensure password_hash is not null for local users
    op.execute("""
        ALTER TABLE users 
        ADD CONSTRAINT check_password_hash_for_local_users 
        CHECK (
            (auth_provider = 'local' AND password_hash IS NOT NULL) OR 
            (auth_provider != 'local')
        )
    """)

def downgrade():
    """Remove auth_provider column from users table"""
    # Remove constraint
    op.drop_constraint('check_password_hash_for_local_users', 'users')
    
    # Remove index
    op.drop_index('idx_users_auth_provider', 'users')
    
    # Make password_hash required again
    op.alter_column('users', 'password_hash', nullable=False)
    
    # Remove auth_provider column
    op.drop_column('users', 'auth_provider')