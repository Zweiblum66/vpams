import { check, sleep, group } from 'k6';
import http from 'k6/http';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics for API stress testing
const apiErrors = new Counter('api_errors');
const apiTimeouts = new Counter('api_timeouts');
const apiRateLimit = new Counter('api_rate_limits');
const endpointDuration = new Trend('endpoint_duration');
const dataIntegrity = new Rate('data_integrity_check');

// Stress test configuration
export const options = {
  scenarios: {
    // Scenario 1: Rate limit testing
    rate_limit_test: {
      executor: 'constant-arrival-rate',
      rate: 1000, // 1000 requests per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 100,
      maxVUs: 200,
      exec: 'rateLimitTest',
    },
    
    // Scenario 2: Connection pool exhaustion
    connection_exhaustion: {
      executor: 'shared-iterations',
      vus: 500, // 500 concurrent connections
      iterations: 5000,
      maxDuration: '10m',
      exec: 'connectionExhaustionTest',
      startTime: '5m',
    },
    
    // Scenario 3: Large payload stress
    large_payload_stress: {
      executor: 'constant-vus',
      vus: 50,
      duration: '10m',
      exec: 'largePayloadTest',
      startTime: '15m',
    },
    
    // Scenario 4: Memory leak detection
    memory_leak_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '30m',
      exec: 'memoryLeakTest',
      startTime: '25m',
    },
    
    // Scenario 5: Cascading failure simulation
    cascading_failure: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '3m', target: 500 }, // Overload
        { duration: '5m', target: 1000 }, // Extreme stress
        { duration: '5m', target: 10 }, // Recovery
      ],
      exec: 'cascadingFailureTest',
      startTime: '55m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(99)<2000'], // Even under stress, 99% should be under 2s
    http_req_failed: ['rate<0.5'], // Allow up to 50% failure rate during stress
    api_errors: ['count<10000'],
    api_timeouts: ['count<5000'],
    api_rate_limits: ['count<10000'],
    data_integrity_check: ['rate>0.95'], // 95% data integrity even under stress
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const STRESS_USER_COUNT = 10000; // Pre-created stress test users

// Get auth token from pool
let tokenPool = [];
function getAuthToken() {
  if (tokenPool.length === 0) {
    // Refill token pool
    for (let i = 0; i < 100; i++) {
      const loginRes = http.post(
        `${BASE_URL}/api/v1/auth/login`,
        JSON.stringify({
          email: `stress-user-${Math.floor(Math.random() * STRESS_USER_COUNT)}@test.local`,
          password: 'StressTest123!',
        }),
        { 
          headers: { 'Content-Type': 'application/json' },
          timeout: '5s',
        }
      );
      
      if (loginRes.status === 200) {
        tokenPool.push(loginRes.json('data.accessToken'));
      }
    }
  }
  
  return tokenPool.pop() || null;
}

// Test 1: Rate limit testing
export function rateLimitTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Hammer a single endpoint
  const res = http.get(`${BASE_URL}/api/v1/assets`, { 
    headers,
    timeout: '2s',
  });
  
  check(res, {
    'not rate limited': (r) => r.status !== 429,
  }) || apiRateLimit.add(1);
  
  if (res.status === 0) {
    apiTimeouts.add(1);
  } else if (res.status >= 500) {
    apiErrors.add(1);
  }
  
  endpointDuration.add(res.timings.duration);
}

// Test 2: Connection pool exhaustion
export function connectionExhaustionTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Hold connections open
  const batch = [];
  for (let i = 0; i < 10; i++) {
    batch.push(
      http.get(`${BASE_URL}/api/v1/assets?page=${i + 1}&limit=100&include=metadata,versions`, {
        headers,
        timeout: '30s',
      })
    );
  }
  
  // Check all responses
  batch.forEach((res) => {
    if (res.status === 0) {
      apiTimeouts.add(1);
    } else if (res.status >= 500) {
      apiErrors.add(1);
    }
  });
}

// Test 3: Large payload stress
export function largePayloadTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Generate large metadata payload
  const largeMetadata = {
    title: randomString(1000),
    description: randomString(10000),
    tags: Array(1000).fill(null).map(() => randomString(20)),
    customFields: {},
  };
  
  // Add 1000 custom fields
  for (let i = 0; i < 1000; i++) {
    largeMetadata.customFields[`field_${i}`] = randomString(100);
  }
  
  const payload = JSON.stringify({
    name: `stress-asset-${Date.now()}.dat`,
    type: 'document',
    metadata: largeMetadata,
  });
  
  const res = http.post(`${BASE_URL}/api/v1/assets`, payload, {
    headers,
    timeout: '30s',
  });
  
  check(res, {
    'large payload accepted': (r) => r.status === 201 || r.status === 413,
  });
  
  if (res.status === 0) {
    apiTimeouts.add(1);
  } else if (res.status >= 500) {
    apiErrors.add(1);
  }
  
  endpointDuration.add(res.timings.duration);
  sleep(1);
}

// Test 4: Memory leak detection
export function memoryLeakTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Create and delete objects repeatedly
  group('memory leak detection', () => {
    // Create asset
    const createRes = http.post(
      `${BASE_URL}/api/v1/assets`,
      JSON.stringify({
        name: `leak-test-${Date.now()}.tmp`,
        type: 'temporary',
        metadata: {
          test: 'memory-leak',
          data: randomString(10000), // 10KB of data
        },
      }),
      { headers, timeout: '10s' }
    );
    
    if (createRes.status === 201) {
      const assetId = createRes.json('data.id');
      
      // Update metadata multiple times
      for (let i = 0; i < 10; i++) {
        http.patch(
          `${BASE_URL}/api/v1/assets/${assetId}/metadata`,
          JSON.stringify({
            additionalData: randomString(5000),
            iteration: i,
          }),
          { headers, timeout: '5s' }
        );
      }
      
      // Delete asset
      const deleteRes = http.del(
        `${BASE_URL}/api/v1/assets/${assetId}`,
        null,
        { headers, timeout: '5s' }
      );
      
      check(deleteRes, {
        'cleanup successful': (r) => r.status === 204,
      });
    }
  });
  
  sleep(0.5);
}

// Test 5: Cascading failure simulation
export function cascadingFailureTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Simulate operations that could cause cascading failures
  const operations = [
    // Heavy search query
    () => {
      const complexQuery = {
        query: randomString(100),
        filters: {
          type: ['video', 'image', 'document'],
          dateRange: { start: '2020-01-01', end: '2024-12-31' },
          metadata: {
            tags: Array(50).fill(null).map(() => randomString(10)),
          },
        },
        aggregations: ['type', 'size', 'creator', 'project'],
        includeRelated: true,
      };
      
      const res = http.post(
        `${BASE_URL}/api/v1/search/advanced`,
        JSON.stringify(complexQuery),
        { headers, timeout: '10s' }
      );
      
      dataIntegrity.add(res.status === 200 && res.json('data') !== null);
      return res;
    },
    
    // Recursive project query
    () => {
      const res = http.get(
        `${BASE_URL}/api/v1/projects/tree?depth=10&include=assets,metadata,permissions`,
        { headers, timeout: '10s' }
      );
      
      dataIntegrity.add(res.status === 200 && res.json('data') !== null);
      return res;
    },
    
    // Bulk operation
    () => {
      const assetIds = Array(100).fill(null).map(() => Math.floor(Math.random() * 100000));
      const res = http.post(
        `${BASE_URL}/api/v1/assets/bulk/export`,
        JSON.stringify({
          assetIds,
          format: 'zip',
          includeMetadata: true,
          includeVersions: true,
        }),
        { headers, timeout: '30s' }
      );
      
      dataIntegrity.add(res.status === 200 || res.status === 202);
      return res;
    },
    
    // Complex aggregation
    () => {
      const res = http.get(
        `${BASE_URL}/api/v1/analytics/usage?` +
        'groupBy=user,project,assetType&' +
        'metrics=count,totalSize,avgSize,downloadCount&' +
        'period=last90days&' +
        'interval=daily',
        { headers, timeout: '15s' }
      );
      
      dataIntegrity.add(res.status === 200 && res.json('data') !== null);
      return res;
    },
  ];
  
  // Execute random operation
  const operation = randomItem(operations);
  const res = operation();
  
  if (res.status === 0) {
    apiTimeouts.add(1);
  } else if (res.status >= 500) {
    apiErrors.add(1);
  }
  
  endpointDuration.add(res.timings.duration);
  
  // Small delay to prevent complete system overload
  sleep(Math.random() * 0.5);
}

// Teardown: Check system recovery
export function teardown(data) {
  console.log('Stress test completed. Checking system recovery...');
  
  // Wait for system to stabilize
  sleep(30);
  
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  
  check(healthRes, {
    'system recovered': (r) => r.status === 200,
    'all services healthy': (r) => {
      const health = r.json();
      return health && Object.values(health).every(service => service.status === 'healthy');
    },
  });
}