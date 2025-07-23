-- Monitoring & Audit Service Schema
\c mams_audit;

-- Audit event types
CREATE TYPE audit_action AS ENUM (
    'create', 'read', 'update', 'delete', 
    'upload', 'download', 'share', 'publish',
    'login', 'logout', 'permission_change',
    'approve', 'reject', 'archive', 'restore'
);

-- Main audit log table (partitioned by month)
CREATE TABLE audit_logs (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    user_email VARCHAR(255),
    user_ip INET,
    user_agent TEXT,
    action audit_action NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    resource_name VARCHAR(255),
    changes JSONB,
    metadata JSONB DEFAULT '{}',
    session_id UUID,
    request_id UUID,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create partitions for the next 12 months
DO $$
DECLARE
    start_date date := date_trunc('month', CURRENT_DATE);
    partition_date date;
    partition_name text;
BEGIN
    FOR i IN 0..11 LOOP
        partition_date := start_date + (i || ' months')::interval;
        partition_name := 'audit_logs_' || to_char(partition_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_logs
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            partition_date,
            partition_date + interval '1 month'
        );
    END LOOP;
END $$;

-- Access logs
CREATE TABLE access_logs (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    access_type VARCHAR(50) NOT NULL, -- 'view', 'download', 'stream', 'preview'
    ip_address INET,
    country_code VARCHAR(2),
    user_agent TEXT,
    referrer TEXT,
    response_time_ms INT,
    bytes_transferred BIGINT,
    status_code INT,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- System events
CREATE TABLE system_events (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'debug', 'info', 'warning', 'error', 'critical'
    service_name VARCHAR(50) NOT NULL,
    host_name VARCHAR(255),
    message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Performance metrics
CREATE TABLE performance_metrics (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    service_name VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(20),
    tags JSONB DEFAULT '{}',
    PRIMARY KEY (service_name, metric_name, timestamp)
);

-- Storage analytics
CREATE TABLE storage_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    organization_id UUID NOT NULL,
    storage_tier VARCHAR(20) NOT NULL,
    total_bytes BIGINT NOT NULL,
    file_count INT NOT NULL,
    bytes_added BIGINT DEFAULT 0,
    bytes_removed BIGINT DEFAULT 0,
    average_file_size BIGINT,
    largest_file_size BIGINT,
    storage_cost DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, organization_id, storage_tier)
);

-- Usage analytics
CREATE TABLE usage_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    organization_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'uploads', 'downloads', 'api_calls', 'storage', 'bandwidth'
    metric_value BIGINT NOT NULL,
    unique_users INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, organization_id, metric_type)
);

-- Search analytics
CREATE TABLE search_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID,
    organization_id UUID NOT NULL,
    search_query TEXT NOT NULL,
    search_type VARCHAR(50), -- 'text', 'metadata', 'visual', 'combined'
    filters_used JSONB DEFAULT '{}',
    result_count INT,
    clicked_results JSONB DEFAULT '[]',
    search_duration_ms INT,
    session_id UUID
);

-- API usage tracking
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    api_key_id UUID,
    user_id UUID,
    organization_id UUID NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INT,
    response_time_ms INT,
    request_size_bytes INT,
    response_size_bytes INT,
    ip_address INET,
    error_message TEXT
);

-- Compliance reports
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- 'gdpr', 'audit', 'access', 'retention'
    report_period_start DATE NOT NULL,
    report_period_end DATE NOT NULL,
    generated_by UUID NOT NULL,
    report_data JSONB NOT NULL,
    file_path VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Retention policies
CREATE TABLE retention_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    retention_days INT NOT NULL,
    action_after_retention VARCHAR(50) NOT NULL, -- 'delete', 'archive', 'anonymize'
    conditions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Data exports (for GDPR compliance)
CREATE TABLE data_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    requested_by UUID NOT NULL,
    export_type VARCHAR(50) NOT NULL, -- 'personal_data', 'audit_logs', 'full_export'
    status VARCHAR(20) DEFAULT 'pending',
    file_path VARCHAR(1024),
    file_size_bytes BIGINT,
    expires_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);

CREATE INDEX idx_access_logs_user ON access_logs(user_id);
CREATE INDEX idx_access_logs_resource ON access_logs(resource_type, resource_id);
CREATE INDEX idx_access_logs_timestamp ON access_logs(timestamp);

CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_severity ON system_events(severity);
CREATE INDEX idx_system_events_service ON system_events(service_name);

CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX idx_storage_analytics_org ON storage_analytics(organization_id);
CREATE INDEX idx_storage_analytics_date ON storage_analytics(date);

CREATE INDEX idx_usage_analytics_org ON usage_analytics(organization_id);
CREATE INDEX idx_usage_analytics_date ON usage_analytics(date);
CREATE INDEX idx_usage_analytics_type ON usage_analytics(metric_type);

CREATE INDEX idx_search_analytics_org ON search_analytics(organization_id);
CREATE INDEX idx_search_analytics_user ON search_analytics(user_id);
CREATE INDEX idx_search_analytics_query ON search_analytics USING GIN(to_tsvector('english', search_query));

CREATE INDEX idx_api_usage_org ON api_usage(organization_id);
CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);

-- Create a function to automatically create monthly partitions
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    table_name text;
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    -- Get the date for next month
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    
    -- Create partitions for tables that need them
    FOR table_name IN SELECT unnest(ARRAY['audit_logs', 'access_logs', 'system_events']) LOOP
        partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, table_name, start_date, end_date
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly partition creation (requires pg_cron extension)
-- SELECT cron.schedule('create-partitions', '0 0 1 * *', 'SELECT create_monthly_partitions();');

-- Triggers
CREATE TRIGGER update_retention_policies_updated_at BEFORE UPDATE ON retention_policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();