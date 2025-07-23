import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { scenario } from 'k6/execution';

// Custom metrics
const activeUsers = new Gauge('active_users');
const sessionDuration = new Trend('session_duration');
const userActions = new Counter('user_actions');
const actionSuccess = new Rate('action_success_rate');
const concurrentOperations = new Gauge('concurrent_operations');

// Realistic user behavior scenarios
export const options = {
  scenarios: {
    // Scenario 1: Morning surge (users logging in and starting work)
    morning_surge: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 500,
      stages: [
        { duration: '5m', target: 100 }, // Ramp up to 100 users/s
        { duration: '10m', target: 200 }, // Peak morning activity
        { duration: '5m', target: 50 }, // Stabilize
      ],
      exec: 'morningUserBehavior',
    },
    
    // Scenario 2: Normal workday activity
    workday_activity: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1s',
      duration: '30m',
      preAllocatedVUs: 100,
      maxVUs: 300,
      exec: 'workdayUserBehavior',
      startTime: '20m',
    },
    
    // Scenario 3: Lunch break dip
    lunch_break: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 100,
      stages: [
        { duration: '5m', target: 20 }, // Users leaving for lunch
        { duration: '20m', target: 10 }, // Low activity
        { duration: '5m', target: 50 }, // Users returning
      ],
      exec: 'limitedUserBehavior',
      startTime: '50m',
    },
    
    // Scenario 4: Afternoon peak
    afternoon_peak: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 400,
      stages: [
        { duration: '5m', target: 150 }, // Ramp up
        { duration: '15m', target: 150 }, // Sustained peak
        { duration: '10m', target: 30 }, // End of day wind down
      ],
      exec: 'intensiveUserBehavior',
      startTime: '80m',
    },
    
    // Scenario 5: Batch operations (scheduled jobs)
    batch_operations: {
      executor: 'per-vu-iterations',
      vus: 10,
      iterations: 5,
      maxDuration: '15m',
      exec: 'batchOperations',
      startTime: '60m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    action_success_rate: ['rate>0.95'],
    http_req_failed: ['rate<0.05'],
    active_users: ['value<1000'],
    concurrent_operations: ['value<500'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Helper function to authenticate
function authenticate() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: `user${Math.floor(Math.random() * 1000)}@mams.local`,
      password: 'TestUser123!',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  if (loginRes.status === 200) {
    return loginRes.json('data.accessToken');
  }
  return null;
}

// Morning user behavior: login, check recent assets, upload files
export function morningUserBehavior() {
  const sessionStart = new Date();
  activeUsers.add(1);
  
  // Authenticate
  const token = authenticate();
  if (!token) {
    activeUsers.add(-1);
    return;
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Check dashboard
  let res = http.get(`${BASE_URL}/api/v1/dashboard`, { headers });
  userActions.add(1);
  actionSuccess.add(res.status === 200);
  sleep(2);
  
  // Check recent assets
  res = http.get(`${BASE_URL}/api/v1/assets?sort=-created_at&limit=20`, { headers });
  userActions.add(1);
  actionSuccess.add(res.status === 200);
  sleep(3);
  
  // Upload a new asset (simulate morning uploads)
  if (Math.random() < 0.3) { // 30% of users upload
    concurrentOperations.add(1);
    res = http.post(
      `${BASE_URL}/api/v1/assets`,
      JSON.stringify({
        name: `morning-upload-${Date.now()}.mp4`,
        type: 'video',
        size: Math.floor(Math.random() * 100) * 1024 * 1024,
      }),
      { headers }
    );
    userActions.add(1);
    actionSuccess.add(res.status === 201);
    concurrentOperations.add(-1);
    sleep(5);
  }
  
  // Browse projects
  res = http.get(`${BASE_URL}/api/v1/projects`, { headers });
  userActions.add(1);
  actionSuccess.add(res.status === 200);
  
  const sessionEnd = new Date();
  sessionDuration.add(sessionEnd - sessionStart);
  activeUsers.add(-1);
  
  sleep(Math.random() * 10 + 5); // Stay logged in for 5-15s
}

// Normal workday behavior: search, view, edit, collaborate
export function workdayUserBehavior() {
  const sessionStart = new Date();
  activeUsers.add(1);
  
  const token = authenticate();
  if (!token) {
    activeUsers.add(-1);
    return;
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Simulate typical work session
  for (let i = 0; i < Math.floor(Math.random() * 10) + 5; i++) {
    const action = Math.random();
    
    if (action < 0.4) {
      // Search for assets (40%)
      const query = ['video', 'image', 'document', 'project'][Math.floor(Math.random() * 4)];
      const res = http.get(`${BASE_URL}/api/v1/search?q=${query}`, { headers });
      userActions.add(1);
      actionSuccess.add(res.status === 200);
      sleep(Math.random() * 3 + 2);
      
    } else if (action < 0.7) {
      // View asset details (30%)
      const assetId = Math.floor(Math.random() * 10000);
      const res = http.get(`${BASE_URL}/api/v1/assets/${assetId}`, { headers });
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 404);
      sleep(Math.random() * 5 + 3);
      
    } else if (action < 0.85) {
      // Edit metadata (15%)
      concurrentOperations.add(1);
      const assetId = Math.floor(Math.random() * 10000);
      const res = http.patch(
        `${BASE_URL}/api/v1/assets/${assetId}/metadata`,
        JSON.stringify({
          tags: ['edited', 'workday', `tag-${Date.now()}`],
        }),
        { headers }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 404);
      concurrentOperations.add(-1);
      sleep(Math.random() * 2 + 1);
      
    } else {
      // Download asset (15%)
      concurrentOperations.add(1);
      const assetId = Math.floor(Math.random() * 10000);
      const res = http.get(`${BASE_URL}/api/v1/assets/${assetId}/download`, { 
        headers,
        responseType: 'none', // Don't store response body
      });
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 404);
      concurrentOperations.add(-1);
      sleep(Math.random() * 10 + 5);
    }
  }
  
  const sessionEnd = new Date();
  sessionDuration.add(sessionEnd - sessionStart);
  activeUsers.add(-1);
}

// Limited user behavior during lunch
export function limitedUserBehavior() {
  const sessionStart = new Date();
  activeUsers.add(1);
  
  const token = authenticate();
  if (!token) {
    activeUsers.add(-1);
    return;
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Quick check-in
  const res = http.get(`${BASE_URL}/api/v1/dashboard`, { headers });
  userActions.add(1);
  actionSuccess.add(res.status === 200);
  sleep(Math.random() * 5 + 2);
  
  // Maybe one quick search
  if (Math.random() < 0.5) {
    const searchRes = http.get(`${BASE_URL}/api/v1/search?q=urgent`, { headers });
    userActions.add(1);
    actionSuccess.add(searchRes.status === 200);
  }
  
  const sessionEnd = new Date();
  sessionDuration.add(sessionEnd - sessionStart);
  activeUsers.add(-1);
}

// Intensive afternoon activity
export function intensiveUserBehavior() {
  const sessionStart = new Date();
  activeUsers.add(1);
  
  const token = authenticate();
  if (!token) {
    activeUsers.add(-1);
    return;
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Intensive operations - finalizing work
  for (let i = 0; i < Math.floor(Math.random() * 15) + 10; i++) {
    const action = Math.random();
    
    if (action < 0.2) {
      // Bulk operations (20%)
      concurrentOperations.add(1);
      const res = http.post(
        `${BASE_URL}/api/v1/assets/bulk`,
        JSON.stringify({
          action: 'update',
          assetIds: Array.from({ length: 10 }, () => Math.floor(Math.random() * 10000)),
          data: { status: 'reviewed' },
        }),
        { headers }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200);
      concurrentOperations.add(-1);
      sleep(Math.random() * 3 + 2);
      
    } else if (action < 0.5) {
      // Export/download multiple assets (30%)
      concurrentOperations.add(1);
      const res = http.post(
        `${BASE_URL}/api/v1/export`,
        JSON.stringify({
          assetIds: Array.from({ length: 5 }, () => Math.floor(Math.random() * 10000)),
          format: 'zip',
        }),
        { headers }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 202);
      concurrentOperations.add(-1);
      sleep(Math.random() * 10 + 5);
      
    } else if (action < 0.7) {
      // Create/update projects (20%)
      const projectRes = http.post(
        `${BASE_URL}/api/v1/projects`,
        JSON.stringify({
          name: `afternoon-project-${Date.now()}`,
          description: 'End of day project creation',
        }),
        { headers }
      );
      userActions.add(1);
      actionSuccess.add(projectRes.status === 201);
      sleep(Math.random() * 2 + 1);
      
    } else {
      // Regular search and view (30%)
      const res = http.get(`${BASE_URL}/api/v1/assets?page=${Math.floor(Math.random() * 10) + 1}`, { headers });
      userActions.add(1);
      actionSuccess.add(res.status === 200);
      sleep(Math.random() * 2 + 1);
    }
  }
  
  const sessionEnd = new Date();
  sessionDuration.add(sessionEnd - sessionStart);
  activeUsers.add(-1);
}

// Batch operations (system/scheduled jobs)
export function batchOperations() {
  const token = authenticate();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  concurrentOperations.add(1);
  
  // Simulate batch processing
  const operations = [
    // Batch metadata update
    () => {
      const res = http.post(
        `${BASE_URL}/api/v1/jobs/metadata-enrichment`,
        JSON.stringify({
          query: 'type:video AND status:pending',
          operation: 'auto-tag',
        }),
        { headers, timeout: '300s' }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 202);
    },
    
    // Batch transcoding
    () => {
      const res = http.post(
        `${BASE_URL}/api/v1/jobs/transcode`,
        JSON.stringify({
          query: 'type:video AND proxy:false',
          profiles: ['web', 'mobile'],
        }),
        { headers, timeout: '300s' }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 202);
    },
    
    // Batch export
    () => {
      const res = http.post(
        `${BASE_URL}/api/v1/jobs/export`,
        JSON.stringify({
          projectId: Math.floor(Math.random() * 100),
          format: 'archive',
          destination: 's3://backups/',
        }),
        { headers, timeout: '300s' }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 202);
    },
    
    // Cleanup old assets
    () => {
      const res = http.post(
        `${BASE_URL}/api/v1/jobs/cleanup`,
        JSON.stringify({
          olderThan: '90d',
          status: 'archived',
          action: 'move-to-cold-storage',
        }),
        { headers, timeout: '300s' }
      );
      userActions.add(1);
      actionSuccess.add(res.status === 200 || res.status === 202);
    },
  ];
  
  // Run random batch operation
  const operation = operations[Math.floor(Math.random() * operations.length)];
  operation();
  
  concurrentOperations.add(-1);
  sleep(60); // Wait before next batch
}