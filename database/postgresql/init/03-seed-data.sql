-- Seed Data for MAMS Development
-- This file contains sample data for testing and development

\c mams_users;

-- Insert default organization
INSERT INTO organizations (id, name, slug, description) VALUES
    ('00000000-0000-0000-0000-000000000001', 'MAMS Demo Organization', 'mams-demo', 'Default organization for development and testing');

-- Insert system permissions
INSERT INTO permissions (name, slug, resource, action, description) VALUES
    -- Asset permissions
    ('View Assets', 'assets.view', 'assets', 'view', 'View and search assets'),
    ('Create Assets', 'assets.create', 'assets', 'create', 'Upload and create new assets'),
    ('Edit Assets', 'assets.edit', 'assets', 'edit', 'Edit asset metadata and properties'),
    ('Delete Assets', 'assets.delete', 'assets', 'delete', 'Delete assets permanently'),
    ('Download Assets', 'assets.download', 'assets', 'download', 'Download original assets'),
    ('Share Assets', 'assets.share', 'assets', 'share', 'Share assets with others'),
    
    -- Project permissions
    ('View Projects', 'projects.view', 'projects', 'view', 'View projects'),
    ('Create Projects', 'projects.create', 'projects', 'create', 'Create new projects'),
    ('Edit Projects', 'projects.edit', 'projects', 'edit', 'Edit project settings'),
    ('Delete Projects', 'projects.delete', 'projects', 'delete', 'Delete projects'),
    
    -- User management permissions
    ('View Users', 'users.view', 'users', 'view', 'View user accounts'),
    ('Create Users', 'users.create', 'users', 'create', 'Create new user accounts'),
    ('Edit Users', 'users.edit', 'users', 'edit', 'Edit user accounts'),
    ('Delete Users', 'users.delete', 'users', 'delete', 'Delete user accounts'),
    
    -- Workflow permissions
    ('View Workflows', 'workflows.view', 'workflows', 'view', 'View workflows'),
    ('Create Workflows', 'workflows.create', 'workflows', 'create', 'Create workflow templates'),
    ('Execute Workflows', 'workflows.execute', 'workflows', 'execute', 'Start workflow instances'),
    ('Approve Tasks', 'workflows.approve', 'workflows', 'approve', 'Approve workflow tasks'),
    
    -- Rights management permissions
    ('View Rights', 'rights.view', 'rights', 'view', 'View rights and licenses'),
    ('Manage Rights', 'rights.manage', 'rights', 'manage', 'Create and edit rights'),
    
    -- System permissions
    ('View Analytics', 'analytics.view', 'analytics', 'view', 'View system analytics'),
    ('Manage Settings', 'settings.manage', 'settings', 'manage', 'Manage system settings'),
    ('View Audit Logs', 'audit.view', 'audit', 'view', 'View audit logs');

-- Insert default roles
INSERT INTO roles (id, organization_id, name, slug, description, is_system) VALUES
    ('00000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000001', 'Administrator', 'admin', 'Full system access', true),
    ('00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000001', 'Editor', 'editor', 'Can edit and manage content', true),
    ('00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000001', 'Viewer', 'viewer', 'Read-only access', true),
    ('00000000-0000-0000-0000-000000000013', '00000000-0000-0000-0000-000000000001', 'Producer', 'producer', 'Project management and approval', true);

-- Assign permissions to roles
-- Admin gets all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000010', id FROM permissions;

-- Editor permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000011', id FROM permissions
WHERE slug IN (
    'assets.view', 'assets.create', 'assets.edit', 'assets.download', 'assets.share',
    'projects.view', 'projects.create', 'projects.edit',
    'workflows.view', 'workflows.execute',
    'rights.view'
);

-- Viewer permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000012', id FROM permissions
WHERE slug IN ('assets.view', 'projects.view', 'workflows.view', 'rights.view');

-- Producer permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000013', id FROM permissions
WHERE slug IN (
    'assets.view', 'assets.download', 'assets.share',
    'projects.view', 'projects.create', 'projects.edit',
    'workflows.view', 'workflows.create', 'workflows.execute', 'workflows.approve',
    'analytics.view'
);

-- Insert demo users (passwords are hashed version of 'password123')
INSERT INTO users (id, organization_id, email, username, password_hash, first_name, last_name, is_verified, email_verified_at) VALUES
    ('00000000-0000-0000-0000-000000000100', '00000000-0000-0000-0000-000000000001', 'admin@mams.demo', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGC5R8sJNhO', 'Admin', 'User', true, CURRENT_TIMESTAMP),
    ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000001', 'editor@mams.demo', 'editor', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGC5R8sJNhO', 'Editor', 'User', true, CURRENT_TIMESTAMP),
    ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000001', 'viewer@mams.demo', 'viewer', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGC5R8sJNhO', 'Viewer', 'User', true, CURRENT_TIMESTAMP),
    ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000001', 'producer@mams.demo', 'producer', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGC5R8sJNhO', 'Producer', 'User', true, CURRENT_TIMESTAMP);

-- Assign roles to users
INSERT INTO user_roles (user_id, role_id, assigned_by) VALUES
    ('00000000-0000-0000-0000-000000000100', '00000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000100'), -- Admin user gets admin role
    ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000100'), -- Editor user gets editor role
    ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000100'), -- Viewer user gets viewer role
    ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000013', '00000000-0000-0000-0000-000000000100'); -- Producer user gets producer role

\c mams_assets;

-- Insert demo projects
INSERT INTO projects (id, organization_id, name, slug, description, created_by) VALUES
    ('00000000-0000-0000-0000-000000000200', '00000000-0000-0000-0000-000000000001', 'Demo Project', 'demo-project', 'Sample project for demonstration', '00000000-0000-0000-0000-000000000100'),
    ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000001', 'Marketing Campaign 2024', 'marketing-2024', 'Marketing materials for 2024', '00000000-0000-0000-0000-000000000103');

-- Insert demo collections
INSERT INTO asset_collections (id, project_id, name, collection_type, description, created_by) VALUES
    ('00000000-0000-0000-0000-000000000300', '00000000-0000-0000-0000-000000000200', 'Raw Footage', 'folder', 'Unedited video files', '00000000-0000-0000-0000-000000000100'),
    ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000200', 'Final Cuts', 'folder', 'Completed video edits', '00000000-0000-0000-0000-000000000100'),
    ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000201', 'Social Media', 'bin', 'Assets for social media posts', '00000000-0000-0000-0000-000000000103');

\c mams_metadata;

-- Insert default metadata schemas
INSERT INTO metadata_schemas (id, organization_id, name, slug, description, applies_to, schema_definition, created_by) VALUES
    ('00000000-0000-0000-0000-000000000400', '00000000-0000-0000-0000-000000000001', 'Basic Video Metadata', 'basic-video', 'Standard metadata for video assets', ARRAY['video'], 
    '{"groups": ["general", "technical", "rights"]}', '00000000-0000-0000-0000-000000000100'),
    ('00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000001', 'Image Metadata', 'image-metadata', 'Standard metadata for images', ARRAY['image'], 
    '{"groups": ["general", "technical", "rights"]}', '00000000-0000-0000-0000-000000000100');

-- Insert schema fields for video metadata
INSERT INTO schema_fields (schema_id, field_name, field_label, field_type, field_group, is_required, display_order) VALUES
    ('00000000-0000-0000-0000-000000000400', 'title', 'Title', 'string', 'general', true, 1),
    ('00000000-0000-0000-0000-000000000400', 'description', 'Description', 'text', 'general', false, 2),
    ('00000000-0000-0000-0000-000000000400', 'keywords', 'Keywords', 'tags', 'general', false, 3),
    ('00000000-0000-0000-0000-000000000400', 'creation_date', 'Creation Date', 'date', 'general', false, 4),
    ('00000000-0000-0000-0000-000000000400', 'location', 'Location', 'string', 'general', false, 5),
    ('00000000-0000-0000-0000-000000000400', 'camera_model', 'Camera Model', 'string', 'technical', false, 10),
    ('00000000-0000-0000-0000-000000000400', 'fps', 'Frame Rate', 'decimal', 'technical', false, 11),
    ('00000000-0000-0000-0000-000000000400', 'resolution', 'Resolution', 'string', 'technical', false, 12),
    ('00000000-0000-0000-0000-000000000400', 'copyright_holder', 'Copyright Holder', 'string', 'rights', false, 20),
    ('00000000-0000-0000-0000-000000000400', 'usage_rights', 'Usage Rights', 'select', 'rights', false, 21);

\c mams_workflow;

-- Insert workflow templates
INSERT INTO workflow_templates (id, organization_id, name, slug, description, category, workflow_definition, created_by) VALUES
    ('00000000-0000-0000-0000-000000000500', '00000000-0000-0000-0000-000000000001', 'Basic Ingest Workflow', 'basic-ingest', 'Standard asset ingestion workflow', 'ingest',
    '{
        "steps": [
            {"id": "upload", "name": "File Upload", "type": "automatic"},
            {"id": "scan", "name": "Virus Scan", "type": "automatic"},
            {"id": "metadata", "name": "Extract Metadata", "type": "automatic"},
            {"id": "proxy", "name": "Generate Proxies", "type": "automatic"},
            {"id": "review", "name": "Quality Review", "type": "manual"},
            {"id": "approve", "name": "Approve for Use", "type": "approval"}
        ]
    }', '00000000-0000-0000-0000-000000000100'),
    
    ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000001', 'Content Approval', 'content-approval', 'Review and approval workflow', 'review',
    '{
        "steps": [
            {"id": "submit", "name": "Submit for Review", "type": "manual"},
            {"id": "legal", "name": "Legal Review", "type": "approval"},
            {"id": "brand", "name": "Brand Review", "type": "approval"},
            {"id": "publish", "name": "Publish Content", "type": "automatic"}
        ]
    }', '00000000-0000-0000-0000-000000000100');

\c mams_rights;

-- Insert sample rights holders
INSERT INTO rights_holders (id, organization_id, name, holder_type, contact_info) VALUES
    ('00000000-0000-0000-0000-000000000600', '00000000-0000-0000-0000-000000000001', 'Stock Media Inc.', 'company', 
    '{"email": "licensing@stockmedia.example", "phone": "+1-555-0100"}'),
    ('00000000-0000-0000-0000-000000000601', '00000000-0000-0000-0000-000000000001', 'John Photographer', 'individual', 
    '{"email": "john@example.com", "phone": "+1-555-0101"}');

\c mams_audit;

-- Insert initial audit log entry
INSERT INTO audit_logs (organization_id, user_id, user_email, action, resource_type, resource_name) VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000100', 'admin@mams.demo', 'create', 'system', 'Database initialized');

-- Insert default retention policies
INSERT INTO retention_policies (organization_id, policy_name, resource_type, retention_days, action_after_retention) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Audit Log Retention', 'audit_logs', 730, 'archive'),
    ('00000000-0000-0000-0000-000000000001', 'Access Log Retention', 'access_logs', 90, 'delete'),
    ('00000000-0000-0000-0000-000000000001', 'Deleted Asset Retention', 'assets', 30, 'delete');