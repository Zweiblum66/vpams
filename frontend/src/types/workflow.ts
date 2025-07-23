// Workflow and approval types
export interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string;
  category: WorkflowCategory;
  trigger_type: WorkflowTriggerType;
  trigger_conditions: WorkflowTriggerCondition[];
  steps: WorkflowStep[];
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
  version: number;
}

export type WorkflowCategory = 'approval' | 'automation' | 'notification' | 'content_processing' | 'metadata' | 'custom';
export type WorkflowTriggerType = 'manual' | 'asset_upload' | 'asset_update' | 'project_create' | 'timeline_create' | 'scheduled' | 'external_webhook';

export interface WorkflowTriggerCondition {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater_than' | 'less_than' | 'in' | 'not_in';
  value: any;
  nested_path?: string;
}

export interface WorkflowStep {
  id: string;
  name: string;
  type: WorkflowStepType;
  order: number;
  config: WorkflowStepConfig;
  conditions?: WorkflowStepCondition[];
  timeout_minutes?: number;
  retry_count?: number;
  is_required: boolean;
  depends_on?: string[];
}

export type WorkflowStepType = 'approval' | 'notification' | 'automation' | 'wait' | 'condition' | 'parallel' | 'webhook' | 'script';

export interface WorkflowStepConfig {
  // Approval step config
  approval_type?: 'single' | 'multiple' | 'sequential' | 'parallel';
  approvers?: WorkflowApprover[];
  min_approvals?: number;
  allow_self_approval?: boolean;
  escalation_rules?: EscalationRule[];
  
  // Notification step config
  notification_type?: 'email' | 'sms' | 'push' | 'slack' | 'teams';
  recipients?: string[];
  template?: string;
  message?: string;
  
  // Automation step config
  action_type?: 'move_asset' | 'update_metadata' | 'transcode' | 'archive' | 'publish' | 'custom';
  action_config?: Record<string, any>;
  
  // Wait step config
  wait_duration?: number;
  wait_unit?: 'minutes' | 'hours' | 'days';
  
  // Condition step config
  condition_logic?: 'and' | 'or';
  condition_checks?: WorkflowConditionCheck[];
  
  // Webhook step config
  webhook_url?: string;
  webhook_method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  webhook_headers?: Record<string, string>;
  webhook_body?: string;
  
  // Script step config
  script_language?: 'javascript' | 'python' | 'shell';
  script_code?: string;
  script_timeout?: number;
}

export interface WorkflowApprover {
  type: 'user' | 'group' | 'role';
  id: string;
  name: string;
  is_required: boolean;
  order?: number;
}

export interface EscalationRule {
  id?: string;
  name?: string;
  description?: string;
  after_minutes: number;
  escalate_to: WorkflowApprover[];
  notification_template?: string;
  auto_approve?: boolean;
  priority?: ApprovalPriority;
  is_active?: boolean;
  max_escalations?: number;
  escalation_interval?: number;
  trigger?: {
    type: EscalationTrigger;
    after_minutes: number;
    conditions: any[];
  };
  actions?: EscalationAction[];
  notifications?: EscalationNotification[];
}

export type EscalationTrigger = 'timeout' | 'overdue' | 'no_response' | 'rejected' | 'manual';

export interface EscalationAction {
  type: 'escalate' | 'notify' | 'approve' | 'cancel' | 'reassign';
  target_type?: 'user' | 'group' | 'role';
  target_id?: string;
  target_name?: string;
  parameters?: Record<string, any>;
}

export interface EscalationNotification {
  type: 'email' | 'sms' | 'push' | 'webhook';
  template?: string;
  recipients?: string[];
  delay_minutes?: number;
}

export interface WorkflowStepCondition {
  field: string;
  operator: string;
  value: any;
  logic?: 'and' | 'or';
}

export interface WorkflowConditionCheck {
  field: string;
  operator: string;
  value: any;
  nested_path?: string;
}

// Workflow execution types
export interface WorkflowExecution {
  id: string;
  workflow_template_id: string;
  workflow_template: WorkflowTemplate;
  trigger_data: Record<string, any>;
  context: WorkflowContext;
  status: WorkflowExecutionStatus;
  current_step_id?: string;
  started_at: string;
  completed_at?: string;
  cancelled_at?: string;
  error_message?: string;
  steps: WorkflowStepExecution[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type WorkflowExecutionStatus = 'pending' | 'running' | 'waiting' | 'completed' | 'failed' | 'cancelled' | 'paused';

export interface WorkflowContext {
  asset_id?: string;
  project_id?: string;
  timeline_id?: string;
  user_id?: string;
  trigger_user_id?: string;
  metadata?: Record<string, any>;
  variables?: Record<string, any>;
}

export interface WorkflowStepExecution {
  id: string;
  step_id: string;
  step: WorkflowStep;
  status: WorkflowStepExecutionStatus;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  output_data?: Record<string, any>;
  assigned_to?: string[];
  responses?: WorkflowStepResponse[];
  retry_count: number;
  is_escalated?: boolean;
  escalated_at?: string;
}

export type WorkflowStepExecutionStatus = 'pending' | 'running' | 'waiting_approval' | 'approved' | 'rejected' | 'completed' | 'failed' | 'skipped' | 'escalated';

export interface WorkflowStepResponse {
  id: string;
  user_id: string;
  user: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
  response_type: 'approve' | 'reject' | 'comment' | 'escalate';
  comment?: string;
  created_at: string;
  metadata?: Record<string, any>;
}

// Approval specific types
export interface ApprovalRequest {
  id: string;
  title: string;
  description?: string;
  priority: ApprovalPriority;
  type: ApprovalType;
  status: ApprovalStatus;
  workflow_execution_id: string;
  workflow_step_execution_id: string;
  requester_id: string;
  requester: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
  approvers: ApprovalRequestApprover[];
  responses: ApprovalResponse[];
  context: ApprovalContext;
  due_date?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  resolved_by?: string;
}

export type ApprovalPriority = 'low' | 'medium' | 'high' | 'urgent';
export type ApprovalType = 'asset_approval' | 'project_approval' | 'timeline_approval' | 'metadata_approval' | 'custom';
export type ApprovalStatus = 'pending' | 'in_review' | 'approved' | 'rejected' | 'cancelled' | 'escalated';

export interface ApprovalRequestApprover {
  user_id: string;
  user: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
  is_required: boolean;
  order?: number;
  status: 'pending' | 'approved' | 'rejected' | 'skipped';
  responded_at?: string;
}

export interface ApprovalResponse {
  id: string;
  approval_request_id: string;
  user_id: string;
  user: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
  response: 'approve' | 'reject' | 'request_changes';
  comment?: string;
  attachments?: string[];
  created_at: string;
  metadata?: Record<string, any>;
}

export interface ApprovalContext {
  asset_id?: string;
  asset?: {
    id: string;
    name: string;
    asset_type: string;
    thumbnail_path?: string;
  };
  project_id?: string;
  project?: {
    id: string;
    name: string;
  };
  timeline_id?: string;
  timeline?: {
    id: string;
    name: string;
  };
  changes?: ApprovalChange[];
  metadata?: Record<string, any>;
}

export interface ApprovalChange {
  field: string;
  old_value: any;
  new_value: any;
  change_type: 'create' | 'update' | 'delete';
}

// Dashboard and reporting types
export interface ApprovalDashboardStats {
  total_pending: number;
  total_approved: number;
  total_rejected: number;
  total_overdue: number;
  my_pending: number;
  my_approved: number;
  my_rejected: number;
  avg_approval_time: number;
  approval_rate: number;
  escalation_rate: number;
}

export interface ApprovalMetrics {
  period: 'day' | 'week' | 'month' | 'quarter' | 'year';
  start_date: string;
  end_date: string;
  metrics: {
    total_requests: number;
    approved_requests: number;
    rejected_requests: number;
    pending_requests: number;
    escalated_requests: number;
    avg_approval_time_hours: number;
    approval_rate_percentage: number;
    by_priority: Record<ApprovalPriority, number>;
    by_type: Record<ApprovalType, number>;
    by_approver: Array<{
      user_id: string;
      user_name: string;
      total_requests: number;
      approved: number;
      rejected: number;
      avg_response_time_hours: number;
    }>;
    by_day: Array<{
      date: string;
      total: number;
      approved: number;
      rejected: number;
    }>;
  };
}

// Request types
export interface CreateWorkflowTemplateRequest {
  name: string;
  description?: string;
  category: WorkflowCategory;
  trigger_type: WorkflowTriggerType;
  trigger_conditions: WorkflowTriggerCondition[];
  steps: Omit<WorkflowStep, 'id'>[];
}

export interface UpdateWorkflowTemplateRequest {
  name?: string;
  description?: string;
  category?: WorkflowCategory;
  trigger_type?: WorkflowTriggerType;
  trigger_conditions?: WorkflowTriggerCondition[];
  steps?: Omit<WorkflowStep, 'id'>[];
  is_active?: boolean;
}

export interface ExecuteWorkflowRequest {
  workflow_template_id: string;
  trigger_data: Record<string, any>;
  context: WorkflowContext;
}

export interface CreateApprovalRequestRequest {
  title: string;
  description?: string;
  priority: ApprovalPriority;
  type: ApprovalType;
  approvers: string[];
  context: ApprovalContext;
  due_date?: string;
}

export interface RespondToApprovalRequest {
  response: 'approve' | 'reject' | 'request_changes';
  comment?: string;
  attachments?: string[];
}

// Filter and query types
export interface WorkflowExecutionFilter {
  status?: WorkflowExecutionStatus[];
  workflow_template_id?: string;
  created_by?: string;
  date_range?: {
    start_date: string;
    end_date: string;
  };
  context_asset_id?: string;
  context_project_id?: string;
}

export interface ApprovalRequestFilter {
  status?: ApprovalStatus[];
  priority?: ApprovalPriority[];
  type?: ApprovalType[];
  requester_id?: string;
  approver_id?: string;
  date_range?: {
    start_date: string;
    end_date: string;
  };
  overdue?: boolean;
}

export interface WorkflowTemplateFilter {
  category?: WorkflowCategory[];
  trigger_type?: WorkflowTriggerType[];
  is_active?: boolean;
  created_by?: string;
}

// Notification types
export interface WorkflowNotification {
  id: string;
  type: 'workflow_started' | 'workflow_completed' | 'workflow_failed' | 'approval_requested' | 'approval_approved' | 'approval_rejected' | 'approval_escalated';
  title: string;
  message: string;
  workflow_execution_id?: string;
  approval_request_id?: string;
  recipient_id: string;
  read: boolean;
  created_at: string;
  metadata?: Record<string, any>;
}