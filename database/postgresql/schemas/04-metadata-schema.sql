-- Metadata Service Schema
\c mams_metadata;

-- Metadata schema types
CREATE TYPE field_type AS ENUM (
    'string', 'text', 'integer', 'decimal', 'boolean', 
    'date', 'datetime', 'time', 'duration',
    'select', 'multiselect', 'tags',
    'url', 'email', 'phone',
    'json', 'array', 'reference'
);

-- Metadata schemas (templates)
CREATE TABLE metadata_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    is_system BOOLEAN DEFAULT false,
    applies_to VARCHAR(50)[], -- ['video', 'audio', 'image', etc.]
    schema_definition JSONB NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, slug)
);

-- Schema fields definition
CREATE TABLE schema_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schema_id UUID REFERENCES metadata_schemas(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL,
    field_label VARCHAR(255) NOT NULL,
    field_type field_type NOT NULL,
    field_group VARCHAR(255),
    description TEXT,
    is_required BOOLEAN DEFAULT false,
    is_searchable BOOLEAN DEFAULT true,
    is_sortable BOOLEAN DEFAULT true,
    is_filterable BOOLEAN DEFAULT true,
    display_order INT DEFAULT 0,
    validation_rules JSONB DEFAULT '{}',
    default_value JSONB,
    options JSONB, -- For select/multiselect fields
    ui_config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_id, field_name)
);

-- Asset metadata values
CREATE TABLE asset_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    schema_id UUID REFERENCES metadata_schemas(id) ON DELETE CASCADE,
    field_values JSONB NOT NULL DEFAULT '{}',
    version INT DEFAULT 1,
    is_current BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_id, schema_id) WHERE is_current = true
);

-- Metadata history
CREATE TABLE metadata_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metadata_id UUID REFERENCES asset_metadata(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL,
    schema_id UUID NOT NULL,
    field_values JSONB NOT NULL,
    version INT NOT NULL,
    change_summary TEXT,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Controlled vocabularies
CREATE TABLE vocabularies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    is_hierarchical BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, slug)
);

-- Vocabulary terms
CREATE TABLE vocabulary_terms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_id UUID REFERENCES vocabularies(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES vocabulary_terms(id) ON DELETE CASCADE,
    term VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    synonyms TEXT[],
    metadata JSONB DEFAULT '{}',
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vocabulary_id, slug)
);

-- Metadata mappings (for import/export)
CREATE TABLE metadata_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_format VARCHAR(50) NOT NULL, -- 'exif', 'xmp', 'iptc', 'custom'
    target_schema_id UUID REFERENCES metadata_schemas(id) ON DELETE CASCADE,
    mapping_rules JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Metadata extraction jobs
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- 'technical', 'embedded', 'ai', 'manual'
    status VARCHAR(50) DEFAULT 'pending',
    extractor_name VARCHAR(255),
    extracted_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Metadata presets (saved field values)
CREATE TABLE metadata_presets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    schema_id UUID REFERENCES metadata_schemas(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    preset_values JSONB NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated metadata
CREATE TABLE ai_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(50),
    metadata_type VARCHAR(50) NOT NULL, -- 'tags', 'transcription', 'description', 'objects'
    confidence_score NUMERIC(3,2),
    extracted_data JSONB NOT NULL,
    processing_time_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_metadata_schemas_org ON metadata_schemas(organization_id);
CREATE INDEX idx_metadata_schemas_applies ON metadata_schemas USING GIN(applies_to);
CREATE INDEX idx_schema_fields_schema ON schema_fields(schema_id);
CREATE INDEX idx_schema_fields_type ON schema_fields(field_type);

CREATE INDEX idx_asset_metadata_asset ON asset_metadata(asset_id);
CREATE INDEX idx_asset_metadata_schema ON asset_metadata(schema_id);
CREATE INDEX idx_asset_metadata_values ON asset_metadata USING GIN(field_values);
CREATE INDEX idx_metadata_history_asset ON metadata_history(asset_id);
CREATE INDEX idx_metadata_history_metadata ON metadata_history(metadata_id);

CREATE INDEX idx_vocabularies_org ON vocabularies(organization_id);
CREATE INDEX idx_vocabulary_terms_vocab ON vocabulary_terms(vocabulary_id);
CREATE INDEX idx_vocabulary_terms_parent ON vocabulary_terms(parent_id);
CREATE INDEX idx_vocabulary_terms_synonyms ON vocabulary_terms USING GIN(synonyms);

CREATE INDEX idx_extraction_jobs_asset ON extraction_jobs(asset_id);
CREATE INDEX idx_extraction_jobs_status ON extraction_jobs(status);
CREATE INDEX idx_ai_metadata_asset ON ai_metadata(asset_id);
CREATE INDEX idx_ai_metadata_type ON ai_metadata(metadata_type);

-- Full-text search on vocabulary terms
CREATE INDEX idx_vocabulary_terms_search ON vocabulary_terms USING GIN(
    to_tsvector('english', 
        COALESCE(term, '') || ' ' || 
        COALESCE(description, '') || ' ' ||
        COALESCE(array_to_string(synonyms, ' '), '')
    )
);

-- Triggers
CREATE TRIGGER update_metadata_schemas_updated_at BEFORE UPDATE ON metadata_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schema_fields_updated_at BEFORE UPDATE ON schema_fields
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_metadata_updated_at BEFORE UPDATE ON asset_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabularies_updated_at BEFORE UPDATE ON vocabularies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_terms_updated_at BEFORE UPDATE ON vocabulary_terms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metadata_mappings_updated_at BEFORE UPDATE ON metadata_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metadata_presets_updated_at BEFORE UPDATE ON metadata_presets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();