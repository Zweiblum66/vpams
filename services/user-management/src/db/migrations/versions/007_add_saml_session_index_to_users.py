"""add saml_session_index to users

Revision ID: 007
Revises: 006
Create Date: 2024-01-16 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    """Add saml_session_index column to users table"""
    # Add saml_session_index column
    op.add_column('users', sa.Column('saml_session_index', sa.String(length=255), nullable=True))
    
    # Add index for saml_session_index
    op.create_index('idx_users_saml_session_index', 'users', ['saml_session_index'])

def downgrade():
    """Remove saml_session_index column from users table"""
    # Remove index
    op.drop_index('idx_users_saml_session_index', 'users')
    
    # Remove saml_session_index column
    op.drop_column('users', 'saml_session_index')