-- Asset Management Service Schema
\c mams_assets;

-- Asset types enum
CREATE TYPE asset_type AS ENUM ('video', 'audio', 'image', 'document', 'subtitle', 'other');
CREATE TYPE asset_status AS ENUM ('pending', 'processing', 'active', 'archived', 'deleted', 'failed');
CREATE TYPE storage_tier AS ENUM ('hot', 'warm', 'cold', 'archive');

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, slug)
);

-- Asset collections (folders, bins, sequences)
CREATE TABLE asset_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES asset_collections(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    collection_type VARCHAR(50) NOT NULL, -- 'folder', 'bin', 'sequence', 'shotlist'
    description TEXT,
    metadata JSONB DEFAULT '{}',
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Main assets table
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    asset_type asset_type NOT NULL,
    status asset_status DEFAULT 'pending',
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL, -- SHA-256 hash
    mime_type VARCHAR(255) NOT NULL,
    file_extension VARCHAR(50),
    
    -- Media specific fields
    duration_seconds NUMERIC(10,3),
    width INT,
    height INT,
    frame_rate NUMERIC(7,3),
    bit_rate INT,
    codec VARCHAR(50),
    
    -- Storage information
    storage_path VARCHAR(1024) NOT NULL,
    storage_tier storage_tier DEFAULT 'hot',
    storage_backend VARCHAR(50) NOT NULL, -- 's3', 'azure', 'gcs', 'local'
    
    -- Metadata
    technical_metadata JSONB DEFAULT '{}',
    business_metadata JSONB DEFAULT '{}',
    custom_metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Timestamps and tracking
    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    archive_date TIMESTAMP WITH TIME ZONE,
    deletion_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Asset versions table
CREATE TABLE asset_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    name VARCHAR(255),
    description TEXT,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    changes JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_id, version_number)
);

-- Asset relationships
CREATE TABLE asset_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    target_asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- 'proxy', 'thumbnail', 'subtitle', 'alternate', 'derived'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_asset_id, target_asset_id, relationship_type)
);

-- Asset collection items (many-to-many)
CREATE TABLE asset_collection_items (
    collection_id UUID REFERENCES asset_collections(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    sort_order INT DEFAULT 0,
    added_by UUID NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, asset_id)
);

-- Proxies table
CREATE TABLE proxies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    proxy_type VARCHAR(50) NOT NULL, -- 'low', 'medium', 'high', 'thumbnail', 'waveform'
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    width INT,
    height INT,
    duration_seconds NUMERIC(10,3),
    format VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Thumbnails table
CREATE TABLE thumbnails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    timecode NUMERIC(10,3) NOT NULL, -- Seconds from start
    storage_path VARCHAR(1024) NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE asset_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES asset_comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    comment_text TEXT NOT NULL,
    timecode NUMERIC(10,3), -- For time-based comments
    drawing_data JSONB, -- For visual annotations
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Asset locks (for exclusive editing)
CREATE TABLE asset_locks (
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    locked_by UUID NOT NULL,
    locked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lock_reason TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (asset_id)
);

-- Shot items for editorial workflows
CREATE TABLE shot_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES asset_collections(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    name VARCHAR(255),
    in_point NUMERIC(10,3) NOT NULL,
    out_point NUMERIC(10,3) NOT NULL,
    duration NUMERIC(10,3) GENERATED ALWAYS AS (out_point - in_point) STORED,
    metadata JSONB DEFAULT '{}',
    sort_order INT DEFAULT 0,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_assets_organization ON assets(organization_id);
CREATE INDEX idx_assets_project ON assets(project_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_hash ON assets(file_hash);
CREATE INDEX idx_assets_uploaded_by ON assets(uploaded_by);
CREATE INDEX idx_assets_uploaded_at ON assets(uploaded_at);
CREATE INDEX idx_assets_tags ON assets USING GIN(tags);
CREATE INDEX idx_assets_technical_metadata ON assets USING GIN(technical_metadata);
CREATE INDEX idx_assets_business_metadata ON assets USING GIN(business_metadata);

CREATE INDEX idx_collections_project ON asset_collections(project_id);
CREATE INDEX idx_collections_parent ON asset_collections(parent_id);
CREATE INDEX idx_collections_type ON asset_collections(collection_type);

CREATE INDEX idx_versions_asset ON asset_versions(asset_id);
CREATE INDEX idx_relationships_source ON asset_relationships(source_asset_id);
CREATE INDEX idx_relationships_target ON asset_relationships(target_asset_id);
CREATE INDEX idx_proxies_asset ON proxies(asset_id);
CREATE INDEX idx_thumbnails_asset ON thumbnails(asset_id);
CREATE INDEX idx_comments_asset ON asset_comments(asset_id);
CREATE INDEX idx_shot_items_collection ON shot_items(collection_id);
CREATE INDEX idx_shot_items_asset ON shot_items(asset_id);

-- Full-text search
CREATE INDEX idx_assets_search ON assets USING GIN(
    to_tsvector('english', 
        COALESCE(name, '') || ' ' || 
        COALESCE(display_name, '') || ' ' || 
        COALESCE(description, '')
    )
);

-- Triggers
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_collections_updated_at BEFORE UPDATE ON asset_collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_comments_updated_at BEFORE UPDATE ON asset_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shot_items_updated_at BEFORE UPDATE ON shot_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();