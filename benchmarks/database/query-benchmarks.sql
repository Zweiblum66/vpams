-- MAMS Database Performance Benchmarks
-- These queries test various database operations and measure performance

-- Setup: Create benchmark schema
CREATE SCHEMA IF NOT EXISTS benchmark;

-- Test 1: Asset Search Performance
-- Measures full-text search with various filters
CREATE OR REPLACE FUNCTION benchmark.test_asset_search(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_times NUMERIC[];
    i INTEGER;
BEGIN
    execution_times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        
        PERFORM a.id, a.name, a.created_at, 
                ts_rank(a.search_vector, plainto_tsquery('english', 'video production')) as rank
        FROM assets a
        JOIN asset_metadata am ON a.id = am.asset_id
        WHERE a.search_vector @@ plainto_tsquery('english', 'video production')
            AND a.status = 'active'
            AND a.created_at >= CURRENT_DATE - INTERVAL '30 days'
            AND am.file_size BETWEEN 1048576 AND 1073741824 -- 1MB to 1GB
        ORDER BY rank DESC, a.created_at DESC
        LIMIT 20;
        
        end_time := clock_timestamp();
        execution_times := array_append(execution_times, 
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;
    
    RETURN QUERY
    SELECT 'Asset Full-Text Search'::TEXT,
           AVG(unnest)::NUMERIC(10,2),
           MIN(unnest)::NUMERIC(10,2),
           MAX(unnest)::NUMERIC(10,2),
           STDDEV(unnest)::NUMERIC(10,2)
    FROM unnest(execution_times);
END;
$$ LANGUAGE plpgsql;

-- Test 2: Complex Join Performance
-- Measures performance of multi-table joins
CREATE OR REPLACE FUNCTION benchmark.test_complex_joins(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_times NUMERIC[];
    i INTEGER;
BEGIN
    execution_times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        
        PERFORM 
            a.id,
            a.name,
            p.name as project_name,
            u.name as owner_name,
            COUNT(DISTINCT av.id) as version_count,
            COUNT(DISTINCT at.tag_id) as tag_count,
            MAX(al.created_at) as last_access
        FROM assets a
        JOIN projects p ON a.project_id = p.id
        JOIN users u ON a.created_by = u.id
        LEFT JOIN asset_versions av ON a.id = av.asset_id
        LEFT JOIN asset_tags at ON a.id = at.asset_id
        LEFT JOIN asset_access_logs al ON a.id = al.asset_id
        WHERE a.created_at >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY a.id, a.name, p.name, u.name
        ORDER BY a.created_at DESC
        LIMIT 50;
        
        end_time := clock_timestamp();
        execution_times := array_append(execution_times, 
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;
    
    RETURN QUERY
    SELECT 'Complex Multi-Table Join'::TEXT,
           AVG(unnest)::NUMERIC(10,2),
           MIN(unnest)::NUMERIC(10,2),
           MAX(unnest)::NUMERIC(10,2),
           STDDEV(unnest)::NUMERIC(10,2)
    FROM unnest(execution_times);
END;
$$ LANGUAGE plpgsql;

-- Test 3: Aggregation Performance
-- Measures performance of aggregation queries
CREATE OR REPLACE FUNCTION benchmark.test_aggregations(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_times NUMERIC[];
    i INTEGER;
BEGIN
    execution_times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        
        PERFORM 
            DATE_TRUNC('day', a.created_at) as upload_date,
            COUNT(*) as asset_count,
            SUM(am.file_size) as total_size,
            AVG(am.file_size) as avg_size,
            COUNT(DISTINCT a.created_by) as unique_uploaders,
            COUNT(DISTINCT a.project_id) as projects_affected
        FROM assets a
        JOIN asset_metadata am ON a.id = am.asset_id
        WHERE a.created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', a.created_at)
        ORDER BY upload_date DESC;
        
        end_time := clock_timestamp();
        execution_times := array_append(execution_times, 
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;
    
    RETURN QUERY
    SELECT 'Daily Asset Aggregations'::TEXT,
           AVG(unnest)::NUMERIC(10,2),
           MIN(unnest)::NUMERIC(10,2),
           MAX(unnest)::NUMERIC(10,2),
           STDDEV(unnest)::NUMERIC(10,2)
    FROM unnest(execution_times);
END;
$$ LANGUAGE plpgsql;

-- Test 4: Recursive Query Performance
-- Measures performance of recursive CTEs (project hierarchy)
CREATE OR REPLACE FUNCTION benchmark.test_recursive_queries(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_times NUMERIC[];
    i INTEGER;
BEGIN
    execution_times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        
        WITH RECURSIVE project_tree AS (
            -- Anchor: top-level projects
            SELECT p.id, p.name, p.parent_id, 0 as depth, 
                   ARRAY[p.id] as path
            FROM projects p
            WHERE p.parent_id IS NULL
            
            UNION ALL
            
            -- Recursive: child projects
            SELECT p.id, p.name, p.parent_id, pt.depth + 1,
                   pt.path || p.id
            FROM projects p
            JOIN project_tree pt ON p.parent_id = pt.id
            WHERE pt.depth < 10 -- Prevent infinite recursion
        )
        PERFORM 
            pt.id,
            pt.name,
            pt.depth,
            COUNT(a.id) as asset_count
        FROM project_tree pt
        LEFT JOIN assets a ON a.project_id = pt.id
        GROUP BY pt.id, pt.name, pt.depth, pt.path
        ORDER BY pt.path;
        
        end_time := clock_timestamp();
        execution_times := array_append(execution_times, 
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;
    
    RETURN QUERY
    SELECT 'Recursive Project Hierarchy'::TEXT,
           AVG(unnest)::NUMERIC(10,2),
           MIN(unnest)::NUMERIC(10,2),
           MAX(unnest)::NUMERIC(10,2),
           STDDEV(unnest)::NUMERIC(10,2)
    FROM unnest(execution_times);
END;
$$ LANGUAGE plpgsql;

-- Test 5: Concurrent Access Performance
-- Simulates multiple users accessing the same resources
CREATE OR REPLACE FUNCTION benchmark.test_concurrent_access(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC
) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_times NUMERIC[];
    i INTEGER;
BEGIN
    execution_times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        
        -- Simulate checking permissions and logging access
        WITH user_permissions AS (
            SELECT DISTINCT p.resource_id
            FROM user_roles ur
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = (SELECT id FROM users ORDER BY RANDOM() LIMIT 1)
                AND p.resource_type = 'asset'
        )
        INSERT INTO asset_access_logs (asset_id, user_id, action, created_at)
        SELECT 
            a.id,
            (SELECT id FROM users ORDER BY RANDOM() LIMIT 1),
            'view',
            NOW()
        FROM assets a
        JOIN user_permissions up ON a.id = up.resource_id::UUID
        WHERE a.status = 'active'
        ORDER BY RANDOM()
        LIMIT 10
        ON CONFLICT DO NOTHING;
        
        end_time := clock_timestamp();
        execution_times := array_append(execution_times, 
            EXTRACT(EPOCH FROM (end_time - start_time)) * 1000);
    END LOOP;
    
    RETURN QUERY
    SELECT 'Concurrent Access Control'::TEXT,
           AVG(unnest)::NUMERIC(10,2),
           MIN(unnest)::NUMERIC(10,2),
           MAX(unnest)::NUMERIC(10,2),
           STDDEV(unnest)::NUMERIC(10,2)
    FROM unnest(execution_times);
END;
$$ LANGUAGE plpgsql;

-- Master benchmark function to run all tests
CREATE OR REPLACE FUNCTION benchmark.run_all_benchmarks(iterations INTEGER DEFAULT 100)
RETURNS TABLE(
    test_name TEXT,
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    std_dev_ms NUMERIC,
    iterations INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.*, iterations
    FROM (
        SELECT * FROM benchmark.test_asset_search(iterations)
        UNION ALL
        SELECT * FROM benchmark.test_complex_joins(iterations)
        UNION ALL
        SELECT * FROM benchmark.test_aggregations(iterations)
        UNION ALL
        SELECT * FROM benchmark.test_recursive_queries(iterations)
        UNION ALL
        SELECT * FROM benchmark.test_concurrent_access(iterations)
    ) t;
END;
$$ LANGUAGE plpgsql;

-- Index performance analysis
CREATE OR REPLACE FUNCTION benchmark.analyze_index_usage()
RETURNS TABLE(
    schema_name TEXT,
    table_name TEXT,
    index_name TEXT,
    index_size TEXT,
    index_scans BIGINT,
    index_reads BIGINT,
    index_efficiency NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        indexname::TEXT,
        pg_size_pretty(pg_relation_size(indexrelid))::TEXT,
        idx_scan,
        idx_tup_read,
        CASE 
            WHEN idx_scan = 0 THEN 0
            ELSE ROUND((idx_tup_read::NUMERIC / idx_scan::NUMERIC), 2)
        END as efficiency
    FROM pg_stat_user_indexes
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'benchmark')
    ORDER BY idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Connection pool performance
CREATE OR REPLACE FUNCTION benchmark.connection_pool_stats()
RETURNS TABLE(
    stat_name TEXT,
    stat_value BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'Active Connections'::TEXT, COUNT(*)::BIGINT
    FROM pg_stat_activity
    WHERE state = 'active'
    UNION ALL
    SELECT 'Idle Connections'::TEXT, COUNT(*)::BIGINT
    FROM pg_stat_activity
    WHERE state = 'idle'
    UNION ALL
    SELECT 'Idle in Transaction'::TEXT, COUNT(*)::BIGINT
    FROM pg_stat_activity
    WHERE state = 'idle in transaction'
    UNION ALL
    SELECT 'Waiting Connections'::TEXT, COUNT(*)::BIGINT
    FROM pg_stat_activity
    WHERE wait_event IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Generate benchmark report
CREATE OR REPLACE FUNCTION benchmark.generate_report()
RETURNS TEXT AS $$
DECLARE
    report TEXT;
    benchmark_results RECORD;
    index_stats RECORD;
    connection_stats RECORD;
BEGIN
    report := E'=== MAMS Database Performance Benchmark Report ===\n';
    report := report || 'Generated: ' || NOW()::TEXT || E'\n\n';
    
    -- Query benchmarks
    report := report || E'Query Performance Benchmarks:\n';
    report := report || E'----------------------------\n';
    
    FOR benchmark_results IN 
        SELECT * FROM benchmark.run_all_benchmarks(100)
    LOOP
        report := report || benchmark_results.test_name || E':\n';
        report := report || '  Average: ' || benchmark_results.avg_time_ms || E' ms\n';
        report := report || '  Min: ' || benchmark_results.min_time_ms || E' ms\n';
        report := report || '  Max: ' || benchmark_results.max_time_ms || E' ms\n';
        report := report || '  Std Dev: ' || benchmark_results.std_dev_ms || E' ms\n\n';
    END LOOP;
    
    -- Index usage
    report := report || E'\nTop 10 Most Used Indexes:\n';
    report := report || E'-------------------------\n';
    
    FOR index_stats IN 
        SELECT * FROM benchmark.analyze_index_usage() LIMIT 10
    LOOP
        report := report || index_stats.index_name || ' (' || index_stats.table_name || E'):\n';
        report := report || '  Size: ' || index_stats.index_size || E'\n';
        report := report || '  Scans: ' || index_stats.index_scans || E'\n';
        report := report || '  Efficiency: ' || index_stats.index_efficiency || E' reads/scan\n\n';
    END LOOP;
    
    -- Connection pool stats
    report := report || E'\nConnection Pool Statistics:\n';
    report := report || E'---------------------------\n';
    
    FOR connection_stats IN 
        SELECT * FROM benchmark.connection_pool_stats()
    LOOP
        report := report || connection_stats.stat_name || ': ' || connection_stats.stat_value || E'\n';
    END LOOP;
    
    RETURN report;
END;
$$ LANGUAGE plpgsql;