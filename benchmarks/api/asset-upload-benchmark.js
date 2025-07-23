import { check, sleep } from 'k6';
import http from 'k6/http';
import { FormData } from 'https://jslib.k6.io/formdata/0.0.2/index.js';
import { SharedArray } from 'k6/data';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const uploadSuccess = new Rate('upload_success_rate');
const uploadDuration = new Trend('upload_duration');
const uploadThroughput = new Trend('upload_throughput_mbps');
const uploadErrors = new Counter('upload_errors');

// Test configuration for file upload benchmarks
export const options = {
  scenarios: {
    // Small file uploads (images)
    small_files: {
      executor: 'constant-arrival-rate',
      rate: 10, // 10 uploads per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 20,
      maxVUs: 50,
      exec: 'uploadSmallFile',
    },
    // Medium file uploads (short videos)
    medium_files: {
      executor: 'constant-arrival-rate',
      rate: 5, // 5 uploads per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 10,
      maxVUs: 30,
      exec: 'uploadMediumFile',
      startTime: '5m',
    },
    // Large file uploads (full videos)
    large_files: {
      executor: 'constant-arrival-rate',
      rate: 2, // 2 uploads per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 5,
      maxVUs: 15,
      exec: 'uploadLargeFile',
      startTime: '10m',
    },
    // Concurrent multi-file uploads
    batch_uploads: {
      executor: 'constant-arrival-rate',
      rate: 3, // 3 batch uploads per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 10,
      maxVUs: 20,
      exec: 'uploadBatch',
      startTime: '15m',
    },
  },
  thresholds: {
    upload_success_rate: ['rate>0.95'], // 95% success rate
    upload_duration: ['p(95)<10000'], // 95% complete within 10s
    upload_throughput_mbps: ['p(50)>80'], // Median throughput > 80 Mbps
    upload_errors: ['count<100'], // Less than 100 errors total
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Generate test files in memory
function generateTestFile(sizeInMB) {
  const sizeInBytes = sizeInMB * 1024 * 1024;
  const content = 'x'.repeat(sizeInBytes);
  return {
    data: content,
    filename: `test-${sizeInMB}mb-${Date.now()}.dat`,
    content_type: 'application/octet-stream',
  };
}

// Authenticate and get token
function getAuthToken() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: 'perf-test@mams.local',
      password: 'PerfTest123!@#',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  if (loginRes.status !== 200) {
    uploadErrors.add(1);
    return null;
  }

  return loginRes.json('data.accessToken');
}

// Upload file helper
function uploadFile(token, file, metadata = {}) {
  const fd = new FormData();
  fd.append('file', http.file(file.data, file.filename, file.content_type));
  fd.append('metadata', JSON.stringify({
    title: `Performance Test - ${file.filename}`,
    description: 'Automated performance test upload',
    tags: ['performance', 'test', 'benchmark'],
    ...metadata,
  }));

  const startTime = new Date();
  
  const uploadRes = http.post(
    `${BASE_URL}/api/v1/assets/upload`,
    fd.body(),
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': `multipart/form-data; boundary=${fd.boundary}`,
      },
      timeout: '300s', // 5 minute timeout for large files
    }
  );

  const endTime = new Date();
  const duration = endTime - startTime;
  const fileSizeMB = file.data.length / (1024 * 1024);
  const throughputMbps = (fileSizeMB * 8) / (duration / 1000); // Megabits per second

  uploadDuration.add(duration);
  uploadThroughput.add(throughputMbps);

  const success = check(uploadRes, {
    'upload successful': (r) => r.status === 201 || r.status === 200,
    'asset id returned': (r) => r.json('data.id') !== undefined,
  });

  uploadSuccess.add(success);
  if (!success) {
    uploadErrors.add(1);
  }

  return uploadRes.json('data.id');
}

// Test scenarios
export function uploadSmallFile() {
  const token = getAuthToken();
  if (!token) return;

  // 1-5 MB files (images)
  const fileSize = Math.floor(Math.random() * 4) + 1;
  const file = generateTestFile(fileSize);
  
  uploadFile(token, file, { type: 'image' });
  
  sleep(1);
}

export function uploadMediumFile() {
  const token = getAuthToken();
  if (!token) return;

  // 10-50 MB files (short videos)
  const fileSize = Math.floor(Math.random() * 40) + 10;
  const file = generateTestFile(fileSize);
  
  uploadFile(token, file, { type: 'video', duration: '00:05:00' });
  
  sleep(2);
}

export function uploadLargeFile() {
  const token = getAuthToken();
  if (!token) return;

  // 100-500 MB files (full videos)
  const fileSize = Math.floor(Math.random() * 400) + 100;
  const file = generateTestFile(fileSize);
  
  uploadFile(token, file, { 
    type: 'video', 
    duration: '00:30:00',
    resolution: '1920x1080',
    codec: 'h264'
  });
  
  sleep(5);
}

export function uploadBatch() {
  const token = getAuthToken();
  if (!token) return;

  // Upload 3-5 files in parallel
  const fileCount = Math.floor(Math.random() * 3) + 3;
  const batch = [];

  for (let i = 0; i < fileCount; i++) {
    const fileSize = Math.floor(Math.random() * 10) + 1; // 1-10 MB
    const file = generateTestFile(fileSize);
    
    batch.push(
      http.asyncRequest('POST', `${BASE_URL}/api/v1/assets/upload`, {
        file: http.file(file.data, file.filename, file.content_type),
        metadata: JSON.stringify({
          title: `Batch upload ${i + 1}`,
          batch_id: `batch-${Date.now()}`,
        }),
      }, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
    );
  }

  // Wait for all uploads to complete
  const responses = http.batch(batch);
  
  responses.forEach((res) => {
    const success = res.status === 201 || res.status === 200;
    uploadSuccess.add(success);
    if (!success) {
      uploadErrors.add(1);
    }
  });

  sleep(3);
}

export function teardown(data) {
  // Report summary statistics
  console.log('Upload benchmark completed');
}