-- Migration: Add performance optimization indexes
-- Description: Adds indexes to improve query performance across MAMS services

BEGIN;

-- ============================================================================
-- Asset Management Service Indexes
-- ============================================================================

-- Index for status + owner + date queries (common in dashboards)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_status_owner_created 
ON assets(status, owner_id, created_at);

-- Index for duplicate detection queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_file_hash_deleted 
ON assets(file_hash, deleted_at);

-- Index for project/type filtering with dates
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_project_type_created 
ON assets(project_id, asset_type, created_at);

-- Index for metadata queries (partial index for active assets)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_metadata_status 
ON assets(id, status) 
WHERE deleted_at IS NULL;

-- Index for efficient sorting of shots in containers
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shot_container_sort 
ON shot_items(container_id, sort_order);

-- Index for asset search by name (using trigram for similarity search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_name_trgm 
ON assets USING gin(name gin_trgm_ops);

-- Index for asset tags many-to-many relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_tags_asset_id 
ON asset_tags(asset_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_tags_tag_id 
ON asset_tags(tag_id);

-- Composite index for tag filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_tags_composite 
ON asset_tags(asset_id, tag_id);

-- ============================================================================
-- User Management Service Indexes
-- ============================================================================

-- Index for user search across multiple fields
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_search 
ON users(email, username, first_name, last_name);

-- Index for common filter combinations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_active_verified 
ON users(is_active, is_verified);

-- Partial index for active user login queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email_active 
ON users(email, is_active) 
WHERE is_active = true;

-- Index for user-role relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_active 
ON user_roles(user_id, role_id) 
WHERE deleted_at IS NULL;

-- Index for permission lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_permission_name_resource 
ON permissions(name, resource_type);

-- Index for role-permission relationship
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_permission_composite 
ON role_permissions(role_id, permission_id);

-- ============================================================================
-- Project Container Indexes
-- ============================================================================

-- Index for project hierarchy queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_container_parent 
ON project_containers(parent_id, container_type);

-- Index for owner queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_container_owner_type 
ON project_containers(owner_id, container_type);

-- Index for public containers
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_container_public 
ON project_containers(is_public) 
WHERE is_public = true;

-- ============================================================================
-- Search Service Indexes (for PostgreSQL metadata)
-- ============================================================================

-- Index for search history
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_user_created 
ON search_history(user_id, created_at DESC);

-- Index for saved searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_saved_search_user_name 
ON saved_searches(user_id, name);

-- ============================================================================
-- Workflow Engine Indexes
-- ============================================================================

-- Index for workflow execution queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_exec_status_created 
ON workflow_executions(status, created_at DESC);

-- Index for workflow execution by trigger
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_exec_trigger 
ON workflow_executions(trigger_type, trigger_id);

-- Index for workflow step execution
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_step_exec_workflow 
ON workflow_step_executions(workflow_execution_id, started_at);

-- ============================================================================
-- Rights Management Indexes
-- ============================================================================

-- Index for license lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_license_asset_active 
ON licenses(asset_id, is_active) 
WHERE is_active = true;

-- Index for license expiration queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_license_expiry 
ON licenses(valid_until) 
WHERE is_active = true;

-- Index for usage restrictions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_restriction_asset 
ON usage_restrictions(asset_id, restriction_type);

-- ============================================================================
-- General Performance Indexes
-- ============================================================================

-- Index for audit log queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_entity_created 
ON audit_logs(entity_type, entity_id, created_at DESC);

-- Index for notification queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_user_read 
ON notifications(user_id, is_read, created_at DESC);

-- ============================================================================
-- Function-based Indexes
-- ============================================================================

-- Index for case-insensitive email search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email_lower 
ON users(LOWER(email));

-- Index for full name search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_fullname 
ON users((first_name || ' ' || last_name));

-- ============================================================================
-- Analyze tables to update statistics
-- ============================================================================

-- Analyze all modified tables to ensure query planner has updated statistics
ANALYZE assets;
ANALYZE users;
ANALYZE project_containers;
ANALYZE workflow_executions;
ANALYZE licenses;

-- ============================================================================
-- Create index usage monitoring function
-- ============================================================================

CREATE OR REPLACE FUNCTION monitor_index_usage()
RETURNS TABLE(
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    index_size TEXT,
    times_used BIGINT,
    efficiency_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.schemaname::TEXT,
        s.tablename::TEXT,
        s.indexname::TEXT,
        pg_size_pretty(pg_relation_size(s.indexrelid))::TEXT as index_size,
        s.idx_scan as times_used,
        CASE 
            WHEN s.idx_scan > 0 THEN 
                ROUND((s.idx_tup_read::NUMERIC / s.idx_scan::NUMERIC), 2)
            ELSE 0
        END as efficiency_ratio
    FROM pg_stat_user_indexes s
    WHERE s.schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY s.idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Create slow query logging
-- ============================================================================

-- Enable pg_stat_statements extension for query performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure pg_stat_statements
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Note: Database restart required for shared_preload_libraries change

COMMIT;

-- ============================================================================
-- Maintenance Commands (run periodically)
-- ============================================================================

-- VACUUM ANALYZE assets;
-- VACUUM ANALYZE users;
-- VACUUM ANALYZE project_containers;
-- REINDEX CONCURRENTLY TABLE assets;
-- REINDEX CONCURRENTLY TABLE users;