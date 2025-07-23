"""Add user behavior tracking tables

Revision ID: 004_add_user_behavior_tracking
Revises: 003_add_usage_analytics
Create Date: 2025-07-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_user_behavior_tracking'
down_revision: Union[str, None] = '003_add_usage_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user behavior tracking tables."""
    
    # Add user_behavior table
    op.create_table(
        'user_behavior',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('sessions_count', sa.Integer, default=0),
        sa.Column('total_time_minutes', sa.Integer, default=0),
        sa.Column('page_views', sa.Integer, default=0),
        sa.Column('actions_count', sa.Integer, default=0),
        sa.Column('features_used', postgresql.JSONB, nullable=True),
        sa.Column('most_used_feature', sa.String(100), nullable=True),
        sa.Column('assets_viewed', sa.Integer, default=0),
        sa.Column('assets_uploaded', sa.Integer, default=0),
        sa.Column('assets_downloaded', sa.Integer, default=0),
        sa.Column('searches_performed', sa.Integer, default=0),
        sa.Column('workflows_created', sa.Integer, default=0),
        sa.Column('workflows_executed', sa.Integer, default=0),
        sa.Column('bounce_rate', sa.Float, nullable=True),
        sa.Column('avg_session_duration', sa.Float, nullable=True),
        sa.Column('return_visitor', sa.Boolean, default=False),
        sa.Column('user_segment', sa.String(50), nullable=True),
        sa.Column('activity_level', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )
    
    # Create indexes for user_behavior
    op.create_index('idx_user_behavior_user_period', 'user_behavior', ['user_id', 'period_start'])
    op.create_index('idx_user_behavior_segment', 'user_behavior', ['user_segment'])
    op.create_index('idx_user_behavior_period_type', 'user_behavior', ['period_type', 'period_start'])
    op.create_index('idx_user_behavior_activity_level', 'user_behavior', ['activity_level'])
    
    # Add asset_interactions table
    op.create_table(
        'asset_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, default=sa.text('now()'), index=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('asset_type', sa.String(50), nullable=True),
        sa.Column('asset_size_bytes', sa.Integer, nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True)
    )
    
    # Create indexes for asset_interactions
    op.create_index('idx_asset_interactions_asset_timestamp', 'asset_interactions', ['asset_id', 'timestamp'])
    op.create_index('idx_asset_interactions_user_timestamp', 'asset_interactions', ['user_id', 'timestamp'])
    op.create_index('idx_asset_interactions_type_timestamp', 'asset_interactions', ['interaction_type', 'timestamp'])
    op.create_index('idx_asset_interactions_project', 'asset_interactions', ['project_id'])
    
    # Update events table with additional columns for behavior tracking
    op.add_column('events', sa.Column('category', sa.String(100), nullable=True, index=True))
    op.add_column('events', sa.Column('duration_ms', sa.Integer, nullable=True))
    op.add_column('events', sa.Column('request_id', sa.String(255), nullable=True))
    op.add_column('events', sa.Column('trace_id', sa.String(255), nullable=True))
    op.add_column('events', sa.Column('source_service', sa.String(100), nullable=True))
    op.add_column('events', sa.Column('source_component', sa.String(100), nullable=True))
    
    # Create additional indexes for events table
    op.create_index('idx_events_category_timestamp', 'events', ['category', 'timestamp'])
    op.create_index('idx_events_source_service', 'events', ['source_service'])
    op.create_index('idx_events_trace_id', 'events', ['trace_id'])
    
    # Update user_sessions table with additional behavior tracking columns
    op.add_column('user_sessions', sa.Column('device_type', sa.String(50), nullable=True))
    op.add_column('user_sessions', sa.Column('browser', sa.String(100), nullable=True))
    op.add_column('user_sessions', sa.Column('os', sa.String(100), nullable=True))
    op.add_column('user_sessions', sa.Column('actions_count', sa.Integer, default=0))
    op.add_column('user_sessions', sa.Column('assets_viewed', sa.Integer, default=0))
    op.add_column('user_sessions', sa.Column('searches_performed', sa.Integer, default=0))
    op.add_column('user_sessions', sa.Column('country', sa.String(2), nullable=True))
    op.add_column('user_sessions', sa.Column('region', sa.String(100), nullable=True))
    op.add_column('user_sessions', sa.Column('city', sa.String(100), nullable=True))
    
    # Create additional indexes for user_sessions
    op.create_index('idx_user_sessions_device_type', 'user_sessions', ['device_type'])
    op.create_index('idx_user_sessions_country', 'user_sessions', ['country'])
    op.create_index('idx_user_sessions_activity', 'user_sessions', ['last_activity_at'])
    
    # Update search_queries table with additional columns
    op.add_column('search_queries', sa.Column('query_type', sa.String(50), nullable=True))
    op.add_column('search_queries', sa.Column('filters', postgresql.JSONB, nullable=True))
    op.add_column('search_queries', sa.Column('sort_order', sa.String(100), nullable=True))
    op.add_column('search_queries', sa.Column('results_count', sa.Integer, nullable=True))
    op.add_column('search_queries', sa.Column('response_time_ms', sa.Integer, nullable=True))
    op.add_column('search_queries', sa.Column('clicked_results', postgresql.JSONB, nullable=True))
    op.add_column('search_queries', sa.Column('search_context', sa.String(100), nullable=True))
    op.add_column('search_queries', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create additional indexes for search_queries
    op.create_index('idx_search_queries_query_type', 'search_queries', ['query_type'])
    op.create_index('idx_search_queries_context', 'search_queries', ['search_context'])
    op.create_index('idx_search_queries_project', 'search_queries', ['project_id'])
    op.create_index('idx_search_queries_text_timestamp', 'search_queries', ['query_text', 'timestamp'])
    
    # Create a function to update user behavior aggregates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_user_behavior_aggregates()
        RETURNS void AS $$
        BEGIN
            -- This function can be called periodically to update user behavior aggregates
            -- Implementation would go here for aggregating behavior data
            -- For now, this is a placeholder
            NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create a trigger function for real-time behavior updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_session_activity()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update session activity when events are inserted
            IF NEW.session_id IS NOT NULL THEN
                UPDATE user_sessions 
                SET 
                    last_activity_at = NEW.timestamp,
                    actions_count = actions_count + 1
                WHERE session_id = NEW.session_id;
                
                -- Increment specific counters based on event type
                IF NEW.event_type = 'asset_view' THEN
                    UPDATE user_sessions 
                    SET assets_viewed = assets_viewed + 1
                    WHERE session_id = NEW.session_id;
                ELSIF NEW.event_type = 'search_query' THEN
                    UPDATE user_sessions 
                    SET searches_performed = searches_performed + 1
                    WHERE session_id = NEW.session_id;
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for automatic session activity updates
    op.execute("""
        CREATE TRIGGER trigger_update_session_activity
        AFTER INSERT ON events
        FOR EACH ROW
        EXECUTE FUNCTION update_session_activity();
    """)


def downgrade() -> None:
    """Remove user behavior tracking tables."""
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trigger_update_session_activity ON events;")
    op.execute("DROP FUNCTION IF EXISTS update_session_activity();")
    op.execute("DROP FUNCTION IF EXISTS update_user_behavior_aggregates();")
    
    # Drop indexes
    op.drop_index('idx_search_queries_text_timestamp', 'search_queries')
    op.drop_index('idx_search_queries_project', 'search_queries')
    op.drop_index('idx_search_queries_context', 'search_queries')
    op.drop_index('idx_search_queries_query_type', 'search_queries')
    
    op.drop_index('idx_user_sessions_activity', 'user_sessions')
    op.drop_index('idx_user_sessions_country', 'user_sessions')
    op.drop_index('idx_user_sessions_device_type', 'user_sessions')
    
    op.drop_index('idx_events_trace_id', 'events')
    op.drop_index('idx_events_source_service', 'events')
    op.drop_index('idx_events_category_timestamp', 'events')
    
    op.drop_index('idx_asset_interactions_project', 'asset_interactions')
    op.drop_index('idx_asset_interactions_type_timestamp', 'asset_interactions')
    op.drop_index('idx_asset_interactions_user_timestamp', 'asset_interactions')
    op.drop_index('idx_asset_interactions_asset_timestamp', 'asset_interactions')
    
    op.drop_index('idx_user_behavior_activity_level', 'user_behavior')
    op.drop_index('idx_user_behavior_period_type', 'user_behavior')
    op.drop_index('idx_user_behavior_segment', 'user_behavior')
    op.drop_index('idx_user_behavior_user_period', 'user_behavior')
    
    # Drop added columns from existing tables
    op.drop_column('search_queries', 'project_id')
    op.drop_column('search_queries', 'search_context')
    op.drop_column('search_queries', 'clicked_results')
    op.drop_column('search_queries', 'response_time_ms')
    op.drop_column('search_queries', 'results_count')
    op.drop_column('search_queries', 'sort_order')
    op.drop_column('search_queries', 'filters')
    op.drop_column('search_queries', 'query_type')
    
    op.drop_column('user_sessions', 'city')
    op.drop_column('user_sessions', 'region')
    op.drop_column('user_sessions', 'country')
    op.drop_column('user_sessions', 'searches_performed')
    op.drop_column('user_sessions', 'assets_viewed')
    op.drop_column('user_sessions', 'actions_count')
    op.drop_column('user_sessions', 'os')
    op.drop_column('user_sessions', 'browser')
    op.drop_column('user_sessions', 'device_type')
    
    op.drop_column('events', 'source_component')
    op.drop_column('events', 'source_service')
    op.drop_column('events', 'trace_id')
    op.drop_column('events', 'request_id')
    op.drop_column('events', 'duration_ms')
    op.drop_column('events', 'category')
    
    # Drop new tables
    op.drop_table('asset_interactions')
    op.drop_table('user_behavior')