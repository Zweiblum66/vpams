import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const assetUploadDuration = new Trend('asset_upload_duration');
const searchDuration = new Trend('search_duration');
const apiResponseTime = new Trend('api_response_time');

// Test configuration
export const options = {
  scenarios: {
    // Smoke test
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '1m',
    },
    // Load test
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5m', target: 100 },  // Ramp up to 100 users
        { duration: '10m', target: 100 }, // Stay at 100 users
        { duration: '5m', target: 200 },  // Ramp up to 200 users
        { duration: '10m', target: 200 }, // Stay at 200 users
        { duration: '5m', target: 0 },    // Ramp down to 0 users
      ],
      gracefulRampDown: '30s',
      startTime: '1m', // Start after smoke test
    },
    // Stress test
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 300 },
        { duration: '5m', target: 300 },
        { duration: '2m', target: 400 },
        { duration: '5m', target: 400 },
        { duration: '10m', target: 0 },
      ],
      startTime: '36m', // Start after load test
    },
    // Spike test
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '10s', target: 1000 }, // Spike to 1000 users
        { duration: '3m', target: 1000 },
        { duration: '10s', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '10s', target: 0 },
      ],
      startTime: '66m', // Start after stress test
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% of requests must complete below 500ms
    errors: ['rate<0.1'], // Error rate must be below 10%
    login_duration: ['p(95)<300'],
    asset_upload_duration: ['p(95)<5000'],
    search_duration: ['p(95)<1000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TEST_USER = {
  email: __ENV.TEST_EMAIL || 'perf-test@mams.local',
  password: __ENV.TEST_PASSWORD || 'PerfTest123!@#',
};

// Helper functions
function authenticateUser() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify(TEST_USER),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'login' },
    }
  );

  loginDuration.add(loginRes.timings.duration);
  
  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('data.accessToken') !== '',
  }) || errorRate.add(1);

  return loginRes.json('data.accessToken');
}

// Test scenarios
export function setup() {
  // Create test data
  console.log('Setting up test data...');
  
  // You could create test users, assets, etc. here
  return {
    baseUrl: BASE_URL,
  };
}

export default function (data) {
  // Authenticate once per VU
  const token = authenticateUser();
  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Test 1: Get user profile
  const profileRes = http.get(`${BASE_URL}/api/v1/users/me`, {
    headers: authHeaders,
    tags: { name: 'get_profile' },
  });
  
  apiResponseTime.add(profileRes.timings.duration);
  
  check(profileRes, {
    'profile retrieved': (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(1);

  // Test 2: List assets
  const assetsRes = http.get(`${BASE_URL}/api/v1/assets?page=1&limit=20`, {
    headers: authHeaders,
    tags: { name: 'list_assets' },
  });
  
  apiResponseTime.add(assetsRes.timings.duration);
  
  check(assetsRes, {
    'assets listed': (r) => r.status === 200,
    'has pagination': (r) => r.json('meta.page') !== undefined,
  }) || errorRate.add(1);

  sleep(1);

  // Test 3: Search assets
  const searchQuery = 'test';
  const searchStart = new Date();
  const searchRes = http.get(
    `${BASE_URL}/api/v1/search?q=${searchQuery}&type=all`,
    {
      headers: authHeaders,
      tags: { name: 'search' },
    }
  );
  
  searchDuration.add(searchRes.timings.duration);
  apiResponseTime.add(searchRes.timings.duration);
  
  check(searchRes, {
    'search successful': (r) => r.status === 200,
    'search results returned': (r) => r.json('data') !== null,
  }) || errorRate.add(1);

  sleep(2);

  // Test 4: Get asset details (if any assets exist)
  const assets = assetsRes.json('data');
  if (assets && assets.length > 0) {
    const assetId = assets[0].id;
    const assetRes = http.get(`${BASE_URL}/api/v1/assets/${assetId}`, {
      headers: authHeaders,
      tags: { name: 'get_asset' },
    });
    
    apiResponseTime.add(assetRes.timings.duration);
    
    check(assetRes, {
      'asset retrieved': (r) => r.status === 200,
    }) || errorRate.add(1);
  }

  sleep(2);

  // Test 5: Workflow operations
  const workflowsRes = http.get(`${BASE_URL}/api/v1/workflows`, {
    headers: authHeaders,
    tags: { name: 'list_workflows' },
  });
  
  apiResponseTime.add(workflowsRes.timings.duration);
  
  check(workflowsRes, {
    'workflows listed': (r) => r.status === 200,
  }) || errorRate.add(1);

  // Random sleep between requests
  sleep(Math.random() * 3 + 1);
}

export function teardown(data) {
  // Clean up test data
  console.log('Cleaning up test data...');
}