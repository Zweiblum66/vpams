-- Rights Management Service Schema
\c mams_rights;

-- License types
CREATE TYPE license_type AS ENUM ('royalty_free', 'rights_managed', 'creative_commons', 'editorial', 'custom');
CREATE TYPE usage_type AS ENUM ('commercial', 'editorial', 'personal', 'educational', 'non_profit');
CREATE TYPE territory_type AS ENUM ('worldwide', 'regional', 'country', 'state', 'custom');

-- Rights holders
CREATE TABLE rights_holders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    holder_type VARCHAR(50) NOT NULL, -- 'individual', 'company', 'agency'
    contact_info JSONB DEFAULT '{}',
    tax_id VARCHAR(100),
    payment_info JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- License agreements
CREATE TABLE license_agreements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    agreement_number VARCHAR(100) UNIQUE,
    rights_holder_id UUID REFERENCES rights_holders(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    license_type license_type NOT NULL,
    agreement_date DATE NOT NULL,
    effective_date DATE NOT NULL,
    expiration_date DATE,
    auto_renew BOOLEAN DEFAULT false,
    terms_document_url VARCHAR(1024),
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Asset licenses (specific rights for assets)
CREATE TABLE asset_licenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    agreement_id UUID REFERENCES license_agreements(id),
    license_type license_type NOT NULL,
    usage_rights usage_type[] DEFAULT '{}',
    territory_type territory_type DEFAULT 'worldwide',
    territories TEXT[], -- Specific countries/regions
    start_date DATE NOT NULL,
    end_date DATE,
    is_exclusive BOOLEAN DEFAULT false,
    max_uses INT,
    price_per_use DECIMAL(10,2),
    total_price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    restrictions JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT no_overlapping_exclusive_licenses EXCLUDE USING gist (
        asset_id WITH =,
        daterange(start_date, end_date, '[]') WITH &&
    ) WHERE (is_exclusive = true)
);

-- Usage tracking
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    license_id UUID REFERENCES asset_licenses(id),
    project_id UUID,
    usage_type usage_type NOT NULL,
    usage_date DATE NOT NULL,
    usage_description TEXT,
    platform VARCHAR(100),
    territory VARCHAR(100),
    reach_estimate BIGINT,
    usage_metadata JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Model releases
CREATE TABLE model_releases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_contact JSONB DEFAULT '{}',
    release_date DATE NOT NULL,
    release_type VARCHAR(50) NOT NULL, -- 'full', 'limited', 'editorial'
    limitations TEXT,
    document_url VARCHAR(1024),
    is_minor BOOLEAN DEFAULT false,
    guardian_info JSONB,
    expiration_date DATE,
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Property releases
CREATE TABLE property_releases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    property_description TEXT NOT NULL,
    property_owner VARCHAR(255),
    location JSONB DEFAULT '{}',
    release_date DATE NOT NULL,
    release_type VARCHAR(50) NOT NULL,
    limitations TEXT,
    document_url VARCHAR(1024),
    expiration_date DATE,
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Copyright information
CREATE TABLE copyrights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    copyright_holder VARCHAR(255) NOT NULL,
    copyright_year INT,
    copyright_notice TEXT,
    registration_number VARCHAR(100),
    registration_date DATE,
    jurisdiction VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Compliance checks
CREATE TABLE compliance_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL,
    check_type VARCHAR(50) NOT NULL, -- 'license', 'release', 'copyright', 'usage'
    check_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    performed_by UUID NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'passed', 'failed', 'warning'
    issues JSONB DEFAULT '[]',
    notes TEXT
);

-- Rights alerts
CREATE TABLE rights_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL, -- 'expiring', 'exceeded', 'missing', 'conflict'
    severity VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical'
    asset_id UUID,
    license_id UUID REFERENCES asset_licenses(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    action_required TEXT,
    due_date DATE,
    is_resolved BOOLEAN DEFAULT false,
    resolved_by UUID,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Revenue sharing
CREATE TABLE revenue_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agreement_id UUID REFERENCES license_agreements(id),
    rights_holder_id UUID REFERENCES rights_holders(id),
    share_percentage DECIMAL(5,2) NOT NULL,
    minimum_guarantee DECIMAL(10,2),
    payment_terms TEXT,
    effective_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Payment records
CREATE TABLE payment_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rights_holder_id UUID REFERENCES rights_holders(id),
    agreement_id UUID REFERENCES license_agreements(id),
    payment_date DATE NOT NULL,
    payment_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50),
    reference_number VARCHAR(100),
    payment_period_start DATE,
    payment_period_end DATE,
    usage_report JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_rights_holders_org ON rights_holders(organization_id);
CREATE INDEX idx_license_agreements_org ON license_agreements(organization_id);
CREATE INDEX idx_license_agreements_holder ON license_agreements(rights_holder_id);
CREATE INDEX idx_license_agreements_expiration ON license_agreements(expiration_date);

CREATE INDEX idx_asset_licenses_asset ON asset_licenses(asset_id);
CREATE INDEX idx_asset_licenses_agreement ON asset_licenses(agreement_id);
CREATE INDEX idx_asset_licenses_dates ON asset_licenses(start_date, end_date);
CREATE INDEX idx_asset_licenses_type ON asset_licenses(license_type);

CREATE INDEX idx_usage_records_asset ON usage_records(asset_id);
CREATE INDEX idx_usage_records_license ON usage_records(license_id);
CREATE INDEX idx_usage_records_date ON usage_records(usage_date);

CREATE INDEX idx_model_releases_asset ON model_releases(asset_id);
CREATE INDEX idx_property_releases_asset ON property_releases(asset_id);
CREATE INDEX idx_copyrights_asset ON copyrights(asset_id);

CREATE INDEX idx_compliance_checks_asset ON compliance_checks(asset_id);
CREATE INDEX idx_compliance_checks_date ON compliance_checks(check_date);
CREATE INDEX idx_compliance_checks_status ON compliance_checks(status);

CREATE INDEX idx_rights_alerts_asset ON rights_alerts(asset_id);
CREATE INDEX idx_rights_alerts_type ON rights_alerts(alert_type);
CREATE INDEX idx_rights_alerts_resolved ON rights_alerts(is_resolved);

-- Triggers
CREATE TRIGGER update_rights_holders_updated_at BEFORE UPDATE ON rights_holders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_license_agreements_updated_at BEFORE UPDATE ON license_agreements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_licenses_updated_at BEFORE UPDATE ON asset_licenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_releases_updated_at BEFORE UPDATE ON model_releases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_releases_updated_at BEFORE UPDATE ON property_releases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_copyrights_updated_at BEFORE UPDATE ON copyrights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_revenue_shares_updated_at BEFORE UPDATE ON revenue_shares
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();