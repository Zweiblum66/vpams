import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend, Counter } from 'k6/metrics';
import exec from 'k6/execution';

// Custom metrics for workflow performance
const workflowStartTime = new Trend('workflow_start_time');
const workflowCompletionTime = new Trend('workflow_completion_time');
const workflowStepDuration = new Trend('workflow_step_duration');
const workflowSuccessRate = new Rate('workflow_success_rate');
const parallelWorkflows = new Counter('parallel_workflows');
const workflowErrors = new Counter('workflow_errors');

// Workflow test scenarios
export const options = {
  scenarios: {
    // Simple linear workflows
    simple_workflows: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1m',
      duration: '15m',
      preAllocatedVUs: 20,
      maxVUs: 50,
      exec: 'simpleWorkflowTest',
    },
    
    // Complex branching workflows
    complex_workflows: {
      executor: 'constant-arrival-rate',
      rate: 5,
      timeUnit: '1m',
      duration: '15m',
      preAllocatedVUs: 15,
      maxVUs: 30,
      exec: 'complexWorkflowTest',
      startTime: '15m',
    },
    
    // Parallel workflow execution
    parallel_workflows: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1m',
      preAllocatedVUs: 30,
      maxVUs: 100,
      stages: [
        { duration: '5m', target: 20 },
        { duration: '10m', target: 50 },
        { duration: '5m', target: 10 },
      ],
      exec: 'parallelWorkflowTest',
      startTime: '30m',
    },
    
    // Long-running workflows
    long_running_workflows: {
      executor: 'per-vu-iterations',
      vus: 10,
      iterations: 5,
      maxDuration: '30m',
      exec: 'longRunningWorkflowTest',
      startTime: '50m',
    },
  },
  
  thresholds: {
    workflow_start_time: ['p(95)<1000'], // 95% of workflows start within 1s
    workflow_completion_time: ['p(95)<60000'], // 95% complete within 60s
    workflow_step_duration: ['p(95)<5000'], // 95% of steps complete within 5s
    workflow_success_rate: ['rate>0.9'], // 90% success rate
    workflow_errors: ['count<100'], // Less than 100 errors total
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Helper function to get auth token
function getAuthToken() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: 'workflow-test@mams.local',
      password: 'WorkflowTest123!',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return loginRes.status === 200 ? loginRes.json('data.accessToken') : null;
}

// Monitor workflow execution
function monitorWorkflow(workflowId, token, maxDuration = 300000) { // 5 min max
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  const startTime = Date.now();
  let status = 'running';
  let lastStep = null;
  
  while (status === 'running' && (Date.now() - startTime) < maxDuration) {
    const res = http.get(`${BASE_URL}/api/v1/workflows/${workflowId}/status`, { headers });
    
    if (res.status === 200) {
      const data = res.json('data');
      status = data.status;
      
      // Track step durations
      if (data.currentStep !== lastStep) {
        if (lastStep) {
          workflowStepDuration.add(Date.now() - startTime);
        }
        lastStep = data.currentStep;
      }
    } else {
      workflowErrors.add(1);
      return false;
    }
    
    sleep(1); // Poll every second
  }
  
  const completionTime = Date.now() - startTime;
  workflowCompletionTime.add(completionTime);
  
  return status === 'completed';
}

// Test 1: Simple linear workflow
export function simpleWorkflowTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Create a simple ingest workflow
  const workflowDef = {
    name: 'Simple Ingest Workflow',
    type: 'ingest',
    steps: [
      {
        id: 'validate',
        type: 'validation',
        config: {
          rules: ['file_type', 'file_size', 'checksum'],
        },
      },
      {
        id: 'extract',
        type: 'metadata_extraction',
        config: {
          extractors: ['exif', 'ffprobe'],
        },
      },
      {
        id: 'thumbnail',
        type: 'thumbnail_generation',
        config: {
          sizes: ['small', 'medium', 'large'],
        },
      },
      {
        id: 'index',
        type: 'search_indexing',
        config: {
          fields: ['title', 'description', 'tags'],
        },
      },
    ],
  };
  
  const startWorkflowTime = Date.now();
  const createRes = http.post(
    `${BASE_URL}/api/v1/workflows/execute`,
    JSON.stringify({
      workflow: workflowDef,
      input: {
        assetId: `test-asset-${Date.now()}`,
        filePath: '/test/sample-video.mp4',
      },
    }),
    { headers }
  );
  
  if (createRes.status === 201 || createRes.status === 200) {
    workflowStartTime.add(Date.now() - startWorkflowTime);
    const workflowId = createRes.json('data.workflowId');
    
    parallelWorkflows.add(1);
    const success = monitorWorkflow(workflowId, token);
    parallelWorkflows.add(-1);
    
    workflowSuccessRate.add(success);
  } else {
    workflowErrors.add(1);
    workflowSuccessRate.add(false);
  }
}

// Test 2: Complex branching workflow
export function complexWorkflowTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Create a complex workflow with conditions and parallel branches
  const workflowDef = {
    name: 'Complex Processing Workflow',
    type: 'processing',
    steps: [
      {
        id: 'analyze',
        type: 'content_analysis',
        config: {
          analyzers: ['format', 'quality', 'content_type'],
        },
      },
      {
        id: 'decision',
        type: 'conditional',
        config: {
          conditions: [
            {
              if: 'output.analyze.content_type == "video"',
              then: ['transcode_video', 'extract_frames'],
            },
            {
              if: 'output.analyze.content_type == "image"',
              then: ['optimize_image', 'create_variants'],
            },
            {
              else: ['process_document'],
            },
          ],
        },
      },
      {
        id: 'transcode_video',
        type: 'video_transcode',
        config: {
          profiles: ['web', 'mobile', 'broadcast'],
          parallel: true,
        },
      },
      {
        id: 'extract_frames',
        type: 'frame_extraction',
        config: {
          interval: 1, // Every 1 second
          format: 'jpeg',
        },
      },
      {
        id: 'optimize_image',
        type: 'image_optimization',
        config: {
          formats: ['webp', 'avif'],
          quality: 85,
        },
      },
      {
        id: 'create_variants',
        type: 'image_resize',
        config: {
          sizes: [
            { width: 150, height: 150, fit: 'cover' },
            { width: 800, height: 600, fit: 'inside' },
            { width: 1920, height: 1080, fit: 'inside' },
          ],
        },
      },
      {
        id: 'process_document',
        type: 'document_processing',
        config: {
          extractText: true,
          generatePreview: true,
        },
      },
      {
        id: 'ai_enrichment',
        type: 'ai_processing',
        config: {
          models: ['auto_tagging', 'scene_detection', 'face_recognition'],
          confidence_threshold: 0.8,
        },
      },
      {
        id: 'quality_check',
        type: 'quality_assurance',
        config: {
          checks: ['completeness', 'accuracy', 'compliance'],
        },
      },
    ],
  };
  
  const startWorkflowTime = Date.now();
  const createRes = http.post(
    `${BASE_URL}/api/v1/workflows/execute`,
    JSON.stringify({
      workflow: workflowDef,
      input: {
        assetId: `complex-asset-${Date.now()}`,
        filePath: '/test/sample-content.mp4',
        metadata: {
          priority: 'high',
          requester: 'test-user',
        },
      },
    }),
    { headers }
  );
  
  if (createRes.status === 201 || createRes.status === 200) {
    workflowStartTime.add(Date.now() - startWorkflowTime);
    const workflowId = createRes.json('data.workflowId');
    
    parallelWorkflows.add(1);
    const success = monitorWorkflow(workflowId, token, 600000); // 10 min max
    parallelWorkflows.add(-1);
    
    workflowSuccessRate.add(success);
  } else {
    workflowErrors.add(1);
    workflowSuccessRate.add(false);
  }
}

// Test 3: Parallel workflow execution
export function parallelWorkflowTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Create multiple workflows that can run in parallel
  const workflows = [
    {
      name: 'Thumbnail Generation',
      type: 'thumbnail',
      priority: 'high',
    },
    {
      name: 'Metadata Extraction',
      type: 'metadata',
      priority: 'medium',
    },
    {
      name: 'Proxy Generation',
      type: 'proxy',
      priority: 'low',
    },
  ];
  
  const workflowIds = [];
  
  // Start all workflows
  workflows.forEach((workflow) => {
    const createRes = http.post(
      `${BASE_URL}/api/v1/workflows/execute`,
      JSON.stringify({
        workflow: {
          name: workflow.name,
          type: workflow.type,
          steps: [
            {
              id: 'process',
              type: workflow.type,
              config: { priority: workflow.priority },
            },
          ],
        },
        input: {
          assetId: `parallel-asset-${Date.now()}-${Math.random()}`,
        },
      }),
      { headers }
    );
    
    if (createRes.status === 201 || createRes.status === 200) {
      workflowIds.push(createRes.json('data.workflowId'));
    }
  });
  
  parallelWorkflows.add(workflowIds.length);
  
  // Monitor all workflows in parallel
  const results = workflowIds.map(id => monitorWorkflow(id, token));
  
  parallelWorkflows.add(-workflowIds.length);
  
  // Check overall success
  const allSuccess = results.every(r => r === true);
  workflowSuccessRate.add(allSuccess);
}

// Test 4: Long-running workflow
export function longRunningWorkflowTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Create a workflow that simulates long-running operations
  const workflowDef = {
    name: 'Long Running Batch Process',
    type: 'batch',
    steps: [
      {
        id: 'prepare',
        type: 'batch_preparation',
        config: {
          batchSize: 1000,
          validateInputs: true,
        },
      },
      {
        id: 'process_batch',
        type: 'batch_processing',
        config: {
          parallel: 10,
          retryOnFailure: true,
          maxRetries: 3,
          operations: [
            'validate',
            'transform',
            'enrich',
            'export',
          ],
        },
      },
      {
        id: 'aggregate_results',
        type: 'result_aggregation',
        config: {
          generateReport: true,
          notifyOnCompletion: true,
        },
      },
      {
        id: 'cleanup',
        type: 'cleanup',
        config: {
          removeTempFiles: true,
          archiveResults: true,
        },
      },
    ],
  };
  
  const startWorkflowTime = Date.now();
  const createRes = http.post(
    `${BASE_URL}/api/v1/workflows/execute`,
    JSON.stringify({
      workflow: workflowDef,
      input: {
        query: 'type:video AND created_at:[NOW-30d TO NOW]',
        operation: 'batch_transcode',
        options: {
          profile: 'archive',
          priority: 'background',
        },
      },
    }),
    { headers }
  );
  
  if (createRes.status === 201 || createRes.status === 200) {
    workflowStartTime.add(Date.now() - startWorkflowTime);
    const workflowId = createRes.json('data.workflowId');
    
    // Monitor long-running workflow with extended timeout
    const success = monitorWorkflow(workflowId, token, 1800000); // 30 min max
    workflowSuccessRate.add(success);
    
    // Check final results
    if (success) {
      const resultsRes = http.get(
        `${BASE_URL}/api/v1/workflows/${workflowId}/results`,
        { headers }
      );
      
      check(resultsRes, {
        'results available': (r) => r.status === 200,
        'all items processed': (r) => {
          const data = r.json('data');
          return data && data.processed === data.total;
        },
      });
    }
  } else {
    workflowErrors.add(1);
    workflowSuccessRate.add(false);
  }
}