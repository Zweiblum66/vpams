-- Workflow Engine Service Schema
\c mams_workflow;

-- Workflow status enum
CREATE TYPE workflow_status AS ENUM ('draft', 'active', 'paused', 'completed', 'failed', 'cancelled');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'skipped', 'cancelled');
CREATE TYPE task_type AS ENUM ('manual', 'automatic', 'approval', 'conditional', 'parallel', 'webhook');

-- Workflow templates
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    is_system BOOLEAN DEFAULT false,
    workflow_definition JSONB NOT NULL,
    triggers JSONB DEFAULT '[]',
    variables JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, slug)
);

-- Active workflow instances
CREATE TABLE workflow_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES workflow_templates(id),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    status workflow_status DEFAULT 'active',
    context JSONB DEFAULT '{}', -- Runtime variables and state
    current_step VARCHAR(255),
    started_by UUID NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    execution_time_seconds INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow steps/tasks
CREATE TABLE workflow_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID REFERENCES workflow_instances(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL, -- ID from template
    task_name VARCHAR(255) NOT NULL,
    task_type task_type NOT NULL,
    status task_status DEFAULT 'pending',
    assigned_to UUID,
    assigned_group UUID,
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_details JSONB,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    timeout_seconds INT,
    dependencies TEXT[], -- Task IDs that must complete first
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task assignments and history
CREATE TABLE task_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES workflow_tasks(id) ON DELETE CASCADE,
    assigned_to UUID,
    assigned_by UUID,
    assignment_note TEXT,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    unassigned_at TIMESTAMP WITH TIME ZONE
);

-- Approval tasks
CREATE TABLE approval_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES workflow_tasks(id) ON DELETE CASCADE,
    approval_type VARCHAR(50) DEFAULT 'single', -- 'single', 'all', 'majority', 'custom'
    required_approvers UUID[],
    minimum_approvals INT DEFAULT 1,
    approval_deadline TIMESTAMP WITH TIME ZONE,
    escalation_user UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Approval responses
CREATE TABLE approval_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    approval_task_id UUID REFERENCES approval_tasks(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL,
    decision VARCHAR(20) NOT NULL, -- 'approved', 'rejected', 'needs_info'
    comments TEXT,
    responded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow triggers
CREATE TABLE workflow_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES workflow_templates(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) NOT NULL, -- 'asset_upload', 'metadata_change', 'schedule', 'webhook'
    trigger_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Automation rules
CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL, -- 'condition', 'action', 'notification'
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    priority INT DEFAULT 0,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task comments
CREATE TABLE task_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES workflow_tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    comment_text TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    is_internal BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow notifications
CREATE TABLE workflow_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID REFERENCES workflow_instances(id) ON DELETE CASCADE,
    task_id UUID REFERENCES workflow_tasks(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    subject VARCHAR(255),
    message TEXT,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow metrics
CREATE TABLE workflow_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES workflow_templates(id) ON DELETE CASCADE,
    instance_id UUID REFERENCES workflow_instances(id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC,
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_workflow_templates_org ON workflow_templates(organization_id);
CREATE INDEX idx_workflow_instances_template ON workflow_instances(template_id);
CREATE INDEX idx_workflow_instances_status ON workflow_instances(status);
CREATE INDEX idx_workflow_instances_started_by ON workflow_instances(started_by);

CREATE INDEX idx_workflow_tasks_instance ON workflow_tasks(instance_id);
CREATE INDEX idx_workflow_tasks_status ON workflow_tasks(status);
CREATE INDEX idx_workflow_tasks_assigned ON workflow_tasks(assigned_to);
CREATE INDEX idx_workflow_tasks_due ON workflow_tasks(due_date);

CREATE INDEX idx_task_assignments_task ON task_assignments(task_id);
CREATE INDEX idx_approval_tasks_task ON approval_tasks(task_id);
CREATE INDEX idx_approval_responses_approval ON approval_responses(approval_task_id);

CREATE INDEX idx_workflow_triggers_template ON workflow_triggers(template_id);
CREATE INDEX idx_automation_rules_org ON automation_rules(organization_id);
CREATE INDEX idx_task_comments_task ON task_comments(task_id);
CREATE INDEX idx_workflow_notifications_recipient ON workflow_notifications(recipient_id);
CREATE INDEX idx_workflow_notifications_read ON workflow_notifications(is_read);

-- Triggers
CREATE TRIGGER update_workflow_templates_updated_at BEFORE UPDATE ON workflow_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_instances_updated_at BEFORE UPDATE ON workflow_instances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_tasks_updated_at BEFORE UPDATE ON workflow_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_triggers_updated_at BEFORE UPDATE ON workflow_triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_automation_rules_updated_at BEFORE UPDATE ON automation_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_comments_updated_at BEFORE UPDATE ON task_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();