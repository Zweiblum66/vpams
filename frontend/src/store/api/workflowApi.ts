import { baseApi } from './baseApi';

export interface WorkflowNode {
  node_id: string;
  node_type: string;
  task_type?: string;
  name: string;
  description?: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  color?: string;
  icon?: string;
  parameters: Record<string, any>;
  timeout?: number;
  retry_count: number;
  retry_delay: number;
  continue_on_error: boolean;
  input_ports: string[];
  output_ports: string[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowConnection {
  connection_id: string;
  source_node_id: string;
  target_node_id: string;
  source_port: string;
  target_port: string;
  connection_type: string;
  points: Array<{ x: number; y: number }>;
  color?: string;
  style?: string;
  condition?: string;
  created_at: string;
}

export interface WorkflowDesignerLayout {
  canvas_size: { width: number; height: number };
  zoom_level: number;
  pan_offset: { x: number; y: number };
  grid_size: number;
  snap_to_grid: boolean;
  show_grid: boolean;
  auto_layout: boolean;
  layout_direction: string;
}

export interface WorkflowDesignerState {
  workflow_id: string;
  name: string;
  description?: string;
  version: string;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  layout: WorkflowDesignerLayout;
  variables: Record<string, any>;
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  validation_status?: any;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface NodeLibraryItem {
  node_type: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  color?: string;
  input_ports: Array<Record<string, any>>;
  output_ports: Array<Record<string, any>>;
  parameters: Record<string, any>;
  configuration_schema: Record<string, any>;
  examples: Array<Record<string, any>>;
  documentation?: string;
  version: string;
  dependencies: string[];
  is_deprecated: boolean;
}

export interface WorkflowValidationResult {
  workflow_id: string;
  is_valid: boolean;
  errors: Array<Record<string, any>>;
  warnings: Array<Record<string, any>>;
  suggestions: Array<Record<string, any>>;
  node_validations: Record<string, any>;
  connection_validations: Record<string, any>;
  flow_validation: any;
  validation_time: number;
  validated_at: string;
}

export interface WorkflowTemplate {
  template_id: string;
  name: string;
  description?: string;
  category: string;
  tags: string[];
  workflow_state: WorkflowDesignerState;
  is_public: boolean;
  is_featured: boolean;
  usage_count: number;
  rating: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTestCase {
  test_case_id: string;
  workflow_id: string;
  name: string;
  description?: string;
  test_data: Record<string, any>;
  expected_outputs?: Record<string, any>;
  timeout?: number;
  tags: string[];
  is_active: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTestResult {
  result_id: string;
  test_case_id: string;
  workflow_id: string;
  status: 'passed' | 'failed' | 'error';
  execution_time: number;
  start_time: string;
  end_time: string;
  input_data: Record<string, any>;
  output_data?: Record<string, any>;
  expected_output?: Record<string, any>;
  error_message?: string;
  step_results: Array<{
    node_id: string;
    step_name: string;
    status: 'passed' | 'failed' | 'error';
    execution_time: number;
    input_data: Record<string, any>;
    output_data?: Record<string, any>;
    error_message?: string;
  }>;
  coverage_data?: Record<string, any>;
  created_at: string;
}

export interface WorkflowTestSuiteResult {
  suite_id: string;
  workflow_id: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  total_execution_time: number;
  start_time: string;
  end_time: string;
  test_results: WorkflowTestResult[];
  coverage_summary: WorkflowTestCoverage;
  created_at: string;
}

export interface WorkflowTestDataTemplate {
  template_id: string;
  workflow_id: string;
  name: string;
  description?: string;
  category: string;
  template_data: Record<string, any>;
  schema?: Record<string, any>;
  usage_count: number;
  is_public: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTestCoverage {
  workflow_id: string;
  total_nodes: number;
  tested_nodes: number;
  coverage_percentage: number;
  node_coverage: Record<string, {
    node_id: string;
    is_covered: boolean;
    test_cases: string[];
    execution_count: number;
  }>;
  connection_coverage: Record<string, {
    connection_id: string;
    is_covered: boolean;
    test_cases: string[];
    execution_count: number;
  }>;
  untested_paths: Array<{
    path: string[];
    reason: string;
  }>;
  generated_at: string;
}

// Import approval workflow types
import {
  ApprovalRequest,
  ApprovalDashboardStats,
  ApprovalMetrics,
  CreateApprovalRequestRequest,
  RespondToApprovalRequest,
  ApprovalRequestFilter,
  WorkflowNotification,
} from '../../types/workflow';

export const workflowApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // Node Library
    getAvailableNodes: builder.query<
      { categories: Record<string, NodeLibraryItem[]>; total_nodes: number },
      { category?: string; search?: string }
    >({
      query: ({ category, search }) => ({
        url: '/designer/nodes',
        params: { category, search },
      }),
      providesTags: ['WorkflowNodes'],
    }),

    getNodeDetails: builder.query<NodeLibraryItem, string>({
      query: (nodeType) => `/designer/nodes/${nodeType}`,
      providesTags: ['WorkflowNodes'],
    }),

    // Workflow Designer State
    createDesignerWorkflow: builder.mutation<
      WorkflowDesignerState,
      {
        name: string;
        description?: string;
        category?: string;
        tags?: string[];
        initial_nodes?: any[];
        created_by?: string;
      }
    >({
      query: (data) => ({
        url: '/designer/workflows',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['WorkflowList'],
    }),

    getDesignerWorkflow: builder.query<WorkflowDesignerState, string>({
      query: (workflowId) => `/designer/workflows/${workflowId}`,
      providesTags: (result, error, workflowId) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    updateDesignerState: builder.mutation<
      WorkflowDesignerState,
      { workflowId: string; state: WorkflowDesignerState }
    >({
      query: ({ workflowId, state }) => ({
        url: `/designer/workflows/${workflowId}/state`,
        method: 'PATCH',
        body: state,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    // Node Operations
    addNode: builder.mutation<
      { node_id: string; workflow_id: string; message: string },
      { workflowId: string; node: WorkflowNode }
    >({
      query: ({ workflowId, node }) => ({
        url: `/designer/workflows/${workflowId}/nodes`,
        method: 'POST',
        body: node,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    updateNode: builder.mutation<
      { node_id: string; workflow_id: string; message: string },
      { workflowId: string; nodeId: string; nodeUpdate: Partial<WorkflowNode> }
    >({
      query: ({ workflowId, nodeId, nodeUpdate }) => ({
        url: `/designer/workflows/${workflowId}/nodes/${nodeId}`,
        method: 'PATCH',
        body: nodeUpdate,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    deleteNode: builder.mutation<
      void,
      { workflowId: string; nodeId: string }
    >({
      query: ({ workflowId, nodeId }) => ({
        url: `/designer/workflows/${workflowId}/nodes/${nodeId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    // Connection Operations
    createConnection: builder.mutation<
      { connection_id: string; workflow_id: string; message: string },
      { workflowId: string; connection: WorkflowConnection }
    >({
      query: ({ workflowId, connection }) => ({
        url: `/designer/workflows/${workflowId}/connections`,
        method: 'POST',
        body: connection,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    deleteConnection: builder.mutation<
      void,
      { workflowId: string; connectionId: string }
    >({
      query: ({ workflowId, connectionId }) => ({
        url: `/designer/workflows/${workflowId}/connections/${connectionId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowDesigner', id: workflowId },
      ],
    }),

    // Validation
    validateWorkflow: builder.mutation<WorkflowValidationResult, string>({
      query: (workflowId) => ({
        url: `/designer/workflows/${workflowId}/validate`,
        method: 'POST',
      }),
    }),

    validateWorkflowRealtime: builder.mutation<
      {
        valid: boolean;
        errors: string[];
        warnings: string[];
        suggestions: string[];
        validation_time: number;
      },
      { workflowId: string; state: WorkflowDesignerState }
    >({
      query: ({ workflowId, state }) => ({
        url: `/designer/workflows/${workflowId}/validate/realtime`,
        method: 'POST',
        body: state,
      }),
    }),

    // Export/Import
    exportWorkflow: builder.mutation<
      any,
      {
        workflowId: string;
        format?: string;
        include_metadata?: boolean;
        include_layout?: boolean;
        minify?: boolean;
      }
    >({
      query: ({ workflowId, ...options }) => ({
        url: `/designer/workflows/${workflowId}/export`,
        method: 'POST',
        body: options,
      }),
    }),

    importWorkflow: builder.mutation<
      { workflow_id: string; message: string },
      {
        format: string;
        content: string | Record<string, any>;
        preserve_ids?: boolean;
        merge_with_existing?: boolean;
        validate_on_import?: boolean;
        source?: string;
        imported_by?: string;
      }
    >({
      query: (data) => ({
        url: '/designer/workflows/import',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['WorkflowList'],
    }),

    // Templates
    getDesignerTemplates: builder.query<
      {
        templates: WorkflowTemplate[];
        total: number;
        page: number;
        page_size: number;
      },
      {
        category?: string;
        tag?: string;
        search?: string;
        page?: number;
        page_size?: number;
      }
    >({
      query: (params) => ({
        url: '/designer/templates',
        params,
      }),
      providesTags: ['WorkflowTemplates'],
    }),

    createDesignerTemplate: builder.mutation<
      { template_id: string; message: string },
      WorkflowTemplate
    >({
      query: (template) => ({
        url: '/designer/templates',
        method: 'POST',
        body: template,
      }),
      invalidatesTags: ['WorkflowTemplates'],
    }),

    // Preview and Testing
    previewWorkflow: builder.mutation<
      any,
      {
        workflowId: string;
        sample_data?: Record<string, any>;
        include_steps?: boolean;
        include_outputs?: boolean;
      }
    >({
      query: ({ workflowId, ...options }) => ({
        url: `/designer/workflows/${workflowId}/preview`,
        method: 'POST',
        body: options,
      }),
    }),

    testWorkflow: builder.mutation<
      WorkflowTestResult,
      {
        workflowId: string;
        test_data?: Record<string, any>;
        dry_run?: boolean;
      }
    >({
      query: ({ workflowId, ...options }) => ({
        url: `/designer/workflows/${workflowId}/test`,
        method: 'POST',
        body: options,
      }),
    }),

    // Test Management
    createTestCase: builder.mutation<
      WorkflowTestCase,
      {
        workflowId: string;
        name: string;
        description?: string;
        test_data: Record<string, any>;
        expected_outputs?: Record<string, any>;
        timeout?: number;
        tags?: string[];
      }
    >({
      query: ({ workflowId, ...testCase }) => ({
        url: `/designer/workflows/${workflowId}/test-cases`,
        method: 'POST',
        body: testCase,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestCases', id: workflowId },
      ],
    }),

    getTestCases: builder.query<
      { test_cases: WorkflowTestCase[]; total: number },
      { workflowId: string; page?: number; page_size?: number }
    >({
      query: ({ workflowId, page = 1, page_size = 20 }) => ({
        url: `/designer/workflows/${workflowId}/test-cases`,
        params: { page, page_size },
      }),
      providesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestCases', id: workflowId },
      ],
    }),

    updateTestCase: builder.mutation<
      WorkflowTestCase,
      {
        workflowId: string;
        testCaseId: string;
        updates: Partial<WorkflowTestCase>;
      }
    >({
      query: ({ workflowId, testCaseId, updates }) => ({
        url: `/designer/workflows/${workflowId}/test-cases/${testCaseId}`,
        method: 'PATCH',
        body: updates,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestCases', id: workflowId },
      ],
    }),

    deleteTestCase: builder.mutation<
      void,
      { workflowId: string; testCaseId: string }
    >({
      query: ({ workflowId, testCaseId }) => ({
        url: `/designer/workflows/${workflowId}/test-cases/${testCaseId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestCases', id: workflowId },
      ],
    }),

    runTestCase: builder.mutation<
      WorkflowTestResult,
      { workflowId: string; testCaseId: string; dry_run?: boolean }
    >({
      query: ({ workflowId, testCaseId, dry_run = false }) => ({
        url: `/designer/workflows/${workflowId}/test-cases/${testCaseId}/run`,
        method: 'POST',
        body: { dry_run },
      }),
    }),

    runAllTestCases: builder.mutation<
      WorkflowTestSuiteResult,
      { workflowId: string; dry_run?: boolean; parallel?: boolean }
    >({
      query: ({ workflowId, dry_run = false, parallel = true }) => ({
        url: `/designer/workflows/${workflowId}/test-cases/run-all`,
        method: 'POST',
        body: { dry_run, parallel },
      }),
    }),

    // Test Results
    getTestResults: builder.query<
      { results: WorkflowTestResult[]; total: number },
      {
        workflowId: string;
        testCaseId?: string;
        status?: 'passed' | 'failed' | 'error';
        page?: number;
        page_size?: number;
      }
    >({
      query: ({ workflowId, testCaseId, status, page = 1, page_size = 20 }) => ({
        url: `/designer/workflows/${workflowId}/test-results`,
        params: { test_case_id: testCaseId, status, page, page_size },
      }),
      providesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestResults', id: workflowId },
      ],
    }),

    getTestResult: builder.query<
      WorkflowTestResult,
      { workflowId: string; resultId: string }
    >({
      query: ({ workflowId, resultId }) => 
        `/designer/workflows/${workflowId}/test-results/${resultId}`,
      providesTags: (result, error, { resultId }) => [
        { type: 'WorkflowTestResults', id: resultId },
      ],
    }),

    // Test Data Templates
    getTestDataTemplates: builder.query<
      { templates: WorkflowTestDataTemplate[]; total: number },
      { workflowId: string; category?: string }
    >({
      query: ({ workflowId, category }) => ({
        url: `/designer/workflows/${workflowId}/test-data-templates`,
        params: { category },
      }),
      providesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestDataTemplates', id: workflowId },
      ],
    }),

    createTestDataTemplate: builder.mutation<
      WorkflowTestDataTemplate,
      {
        workflowId: string;
        name: string;
        description?: string;
        category: string;
        template_data: Record<string, any>;
        schema?: Record<string, any>;
      }
    >({
      query: ({ workflowId, ...template }) => ({
        url: `/designer/workflows/${workflowId}/test-data-templates`,
        method: 'POST',
        body: template,
      }),
      invalidatesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestDataTemplates', id: workflowId },
      ],
    }),

    // Test Coverage
    getTestCoverage: builder.query<
      WorkflowTestCoverage,
      { workflowId: string }
    >({
      query: ({ workflowId }) => 
        `/designer/workflows/${workflowId}/test-coverage`,
      providesTags: (result, error, { workflowId }) => [
        { type: 'WorkflowTestCoverage', id: workflowId },
      ],
    }),

    // Workflow Conversion
    convertToExecutable: builder.mutation<
      any,
      {
        workflowId: string;
        validate?: boolean;
        optimize?: boolean;
      }
    >({
      query: ({ workflowId, ...options }) => ({
        url: `/designer/workflows/${workflowId}/convert`,
        method: 'POST',
        body: options,
      }),
    }),

    // Settings
    getDesignerSettings: builder.query<Record<string, any>, void>({
      query: () => '/designer/settings',
      providesTags: ['WorkflowSettings'],
    }),

    updateDesignerSettings: builder.mutation<
      Record<string, any>,
      Record<string, any>
    >({
      query: (settings) => ({
        url: '/designer/settings',
        method: 'PATCH',
        body: settings,
      }),
      invalidatesTags: ['WorkflowSettings'],
    }),

    // Approval Workflow Endpoints
    getApprovalRequests: builder.query<{ data: ApprovalRequest[]; total: number }, {
      page?: number;
      limit?: number;
      filters?: ApprovalRequestFilter;
    }>({
      query: ({ page = 1, limit = 20, filters = {} }) => ({
        url: '/approvals/requests',
        params: { page, limit, ...filters },
      }),
      providesTags: ['ApprovalRequest'],
    }),
    
    getApprovalRequest: builder.query<ApprovalRequest, string>({
      query: (id) => `/approvals/requests/${id}`,
      providesTags: ['ApprovalRequest'],
    }),
    
    createApprovalRequest: builder.mutation<ApprovalRequest, CreateApprovalRequestRequest>({
      query: (request) => ({
        url: '/approvals/requests',
        method: 'POST',
        body: request,
      }),
      invalidatesTags: ['ApprovalRequest', 'ApprovalStats'],
    }),
    
    respondToApprovalRequest: builder.mutation<ApprovalRequest, { id: string } & RespondToApprovalRequest>({
      query: ({ id, ...response }) => ({
        url: `/approvals/requests/${id}/respond`,
        method: 'POST',
        body: response,
      }),
      invalidatesTags: ['ApprovalRequest', 'ApprovalStats'],
    }),
    
    cancelApprovalRequest: builder.mutation<ApprovalRequest, string>({
      query: (id) => ({
        url: `/approvals/requests/${id}/cancel`,
        method: 'POST',
      }),
      invalidatesTags: ['ApprovalRequest', 'ApprovalStats'],
    }),
    
    // My Approvals (for current user)
    getMyApprovalRequests: builder.query<{ data: ApprovalRequest[]; total: number }, {
      page?: number;
      limit?: number;
      status?: string[];
    }>({
      query: ({ page = 1, limit = 20, status }) => ({
        url: '/approvals/my-requests',
        params: { page, limit, status: status?.join(',') },
      }),
      providesTags: ['ApprovalRequest'],
    }),
    
    getMyApprovalsToReview: builder.query<{ data: ApprovalRequest[]; total: number }, {
      page?: number;
      limit?: number;
      priority?: string[];
    }>({
      query: ({ page = 1, limit = 20, priority }) => ({
        url: '/approvals/my-approvals',
        params: { page, limit, priority: priority?.join(',') },
      }),
      providesTags: ['ApprovalRequest'],
    }),
    
    // Dashboard and Statistics
    getApprovalDashboardStats: builder.query<ApprovalDashboardStats, void>({
      query: () => '/approvals/dashboard/stats',
      providesTags: ['ApprovalStats'],
    }),
    
    getApprovalMetrics: builder.query<ApprovalMetrics, {
      period: 'day' | 'week' | 'month' | 'quarter' | 'year';
      start_date?: string;
      end_date?: string;
    }>({
      query: ({ period, start_date, end_date }) => ({
        url: '/approvals/metrics',
        params: { period, start_date, end_date },
      }),
      providesTags: ['ApprovalStats'],
    }),

    // Workflow Notifications
    getWorkflowNotifications: builder.query<{ data: WorkflowNotification[]; total: number }, {
      page?: number;
      limit?: number;
      read?: boolean;
    }>({
      query: ({ page = 1, limit = 20, read }) => ({
        url: '/workflows/notifications',
        params: { page, limit, read },
      }),
      providesTags: ['WorkflowNotification'],
    }),
    
    markNotificationAsRead: builder.mutation<WorkflowNotification, string>({
      query: (id) => ({
        url: `/workflows/notifications/${id}/read`,
        method: 'POST',
      }),
      invalidatesTags: ['WorkflowNotification'],
    }),

    // Escalation Rules
    getEscalationRules: builder.query<{ data: any[]; total: number }, {
      workflow_id?: string;
      step_id?: string;
      page?: number;
      limit?: number;
    }>({
      query: ({ workflow_id, step_id, page = 1, limit = 20 }) => ({
        url: '/workflows/escalation-rules',
        params: { workflow_id, step_id, page, limit },
      }),
      providesTags: ['EscalationRule'],
    }),
    
    createEscalationRule: builder.mutation<any, any>({
      query: (rule) => ({
        url: '/workflows/escalation-rules',
        method: 'POST',
        body: rule,
      }),
      invalidatesTags: ['EscalationRule'],
    }),
    
    updateEscalationRule: builder.mutation<any, { id: string } & any>({
      query: ({ id, ...rule }) => ({
        url: `/workflows/escalation-rules/${id}`,
        method: 'PUT',
        body: rule,
      }),
      invalidatesTags: ['EscalationRule'],
    }),
    
    deleteEscalationRule: builder.mutation<void, string>({
      query: (id) => ({
        url: `/workflows/escalation-rules/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['EscalationRule'],
    }),
    
    testEscalationRule: builder.mutation<any, { id: string; test_scenario: string }>({
      query: ({ id, test_scenario }) => ({
        url: `/workflows/escalation-rules/${id}/test`,
        method: 'POST',
        body: { test_scenario },
      }),
    }),

    // Escalation for Approval Requests
    escalateApprovalRequest: builder.mutation<ApprovalRequest, { 
      id: string; 
      escalate_to: string[]; 
      comment?: string; 
    }>({
      query: ({ id, escalate_to, comment }) => ({
        url: `/approvals/requests/${id}/escalate`,
        method: 'POST',
        body: { escalate_to, comment },
      }),
      invalidatesTags: ['ApprovalRequest', 'ApprovalStats'],
    }),
  }),
});

export const {
  useGetAvailableNodesQuery,
  useGetNodeDetailsQuery,
  useCreateDesignerWorkflowMutation,
  useGetDesignerWorkflowQuery,
  useUpdateDesignerStateMutation,
  useAddNodeMutation,
  useUpdateNodeMutation,
  useDeleteNodeMutation,
  useCreateConnectionMutation,
  useDeleteConnectionMutation,
  useValidateWorkflowMutation,
  useValidateWorkflowRealtimeMutation,
  useExportWorkflowMutation,
  useImportWorkflowMutation,
  useGetDesignerTemplatesQuery,
  useCreateDesignerTemplateMutation,
  usePreviewWorkflowMutation,
  useTestWorkflowMutation,
  useCreateTestCaseMutation,
  useGetTestCasesQuery,
  useUpdateTestCaseMutation,
  useDeleteTestCaseMutation,
  useRunTestCaseMutation,
  useRunAllTestCasesMutation,
  useGetTestResultsQuery,
  useGetTestResultQuery,
  useGetTestDataTemplatesQuery,
  useCreateTestDataTemplateMutation,
  useGetTestCoverageQuery,
  useConvertToExecutableMutation,
  useGetDesignerSettingsQuery,
  useUpdateDesignerSettingsMutation,
  
  // Approval Workflow hooks
  useGetApprovalRequestsQuery,
  useGetApprovalRequestQuery,
  useCreateApprovalRequestMutation,
  useRespondToApprovalRequestMutation,
  useCancelApprovalRequestMutation,
  useGetMyApprovalRequestsQuery,
  useGetMyApprovalsToReviewQuery,
  useGetApprovalDashboardStatsQuery,
  useGetApprovalMetricsQuery,
  useGetWorkflowNotificationsQuery,
  useMarkNotificationAsReadMutation,
  
  // Escalation Rules hooks
  useGetEscalationRulesQuery,
  useCreateEscalationRuleMutation,
  useUpdateEscalationRuleMutation,
  useDeleteEscalationRuleMutation,
  useTestEscalationRuleMutation,
  useEscalateApprovalRequestMutation,
} = workflowApi;