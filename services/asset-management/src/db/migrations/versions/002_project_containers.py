"""Add project containers and editorial workflow tables

Revision ID: 002
Revises: 001
Create Date: 2025-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create project containers and editorial workflow tables"""
    
    # Create container type enum
    op.execute("""
        CREATE TYPE containertype AS ENUM (
            'project', 'folder', 'bin', 'shotlist', 'sequence'
        )
    """)
    
    # Create project_containers table
    op.create_table(
        'project_containers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('container_type', postgresql.ENUM('project', 'folder', 'bin', 'shotlist', 'sequence', name='containertype'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('path', sa.String(1024), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['project_containers.id'], ondelete='CASCADE')
    )
    
    # Create indexes for project_containers
    op.create_index('idx_container_type_owner', 'project_containers', ['container_type', 'owner_id'])
    op.create_index('idx_container_parent', 'project_containers', ['parent_id'])
    op.create_index('idx_container_path', 'project_containers', ['path'])
    
    # Add project_id to assets table
    op.add_column('assets', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_asset_project', 'assets', 'project_containers', ['project_id'], ['id'])
    
    # Create shot_items table for editorial workflow
    op.create_table(
        'shot_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('in_point', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('out_point', sa.BigInteger(), nullable=True),
        sa.Column('duration', sa.BigInteger(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('markers', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('color_label', sa.String(7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['container_id'], ['project_containers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('in_point >= 0', name='check_in_point_positive'),
        sa.CheckConstraint('out_point IS NULL OR out_point > in_point', name='check_out_after_in')
    )
    
    # Create indexes for shot_items
    op.create_index('idx_shot_container', 'shot_items', ['container_id'])
    op.create_index('idx_shot_asset', 'shot_items', ['asset_id'])
    
    # Create sequence_timelines table
    op.create_table(
        'sequence_timelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('track_number', sa.Integer(), nullable=False),
        sa.Column('track_type', sa.String(32), nullable=False),
        sa.Column('track_name', sa.String(128), nullable=True),
        sa.Column('clip_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_time', sa.BigInteger(), nullable=False),
        sa.Column('end_time', sa.BigInteger(), nullable=False),
        sa.Column('source_in', sa.BigInteger(), nullable=True),
        sa.Column('source_out', sa.BigInteger(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('effects', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('transition_in', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('transition_out', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('opacity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sequence_id'], ['project_containers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['clip_id'], ['shot_items.id'], ondelete='CASCADE'),
        sa.CheckConstraint('start_time >= 0', name='check_start_time_positive'),
        sa.CheckConstraint('end_time > start_time', name='check_end_after_start'),
        sa.CheckConstraint('speed > 0', name='check_speed_positive'),
        sa.CheckConstraint('opacity >= 0 AND opacity <= 1', name='check_opacity_range')
    )
    
    # Create indexes for sequence_timelines
    op.create_index('idx_timeline_sequence', 'sequence_timelines', ['sequence_id'])
    op.create_index('idx_timeline_track', 'sequence_timelines', ['sequence_id', 'track_number'])
    op.create_index('idx_timeline_time', 'sequence_timelines', ['sequence_id', 'start_time', 'end_time'])
    
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
        sa.UniqueConstraint('name')
    )
    
    # Create indexes for project_templates
    op.create_index('idx_template_category', 'project_templates', ['category'])
    op.create_index('idx_template_owner', 'project_templates', ['owner_id'])


def downgrade():
    """Drop project containers and editorial workflow tables"""
    
    # Drop project_templates table
    op.drop_index('idx_template_owner', table_name='project_templates')
    op.drop_index('idx_template_category', table_name='project_templates')
    op.drop_table('project_templates')
    
    # Drop sequence_timelines table
    op.drop_index('idx_timeline_time', table_name='sequence_timelines')
    op.drop_index('idx_timeline_track', table_name='sequence_timelines')
    op.drop_index('idx_timeline_sequence', table_name='sequence_timelines')
    op.drop_table('sequence_timelines')
    
    # Drop shot_items table
    op.drop_index('idx_shot_asset', table_name='shot_items')
    op.drop_index('idx_shot_container', table_name='shot_items')
    op.drop_table('shot_items')
    
    # Remove project_id from assets
    op.drop_constraint('fk_asset_project', 'assets', type_='foreignkey')
    op.drop_column('assets', 'project_id')
    
    # Drop project_containers table
    op.drop_index('idx_container_path', table_name='project_containers')
    op.drop_index('idx_container_parent', table_name='project_containers')
    op.drop_index('idx_container_type_owner', table_name='project_containers')
    op.drop_table('project_containers')
    
    # Drop enum
    op.execute("DROP TYPE containertype")