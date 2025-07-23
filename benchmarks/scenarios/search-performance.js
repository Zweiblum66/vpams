import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

// Custom metrics for search performance
const searchResponseTime = new Trend('search_response_time');
const searchResultAccuracy = new Rate('search_result_accuracy');
const searchResultCount = new Gauge('search_result_count');
const facetGenerationTime = new Trend('facet_generation_time');
const suggestionResponseTime = new Trend('suggestion_response_time');
const searchErrors = new Counter('search_errors');
const emptyResults = new Counter('empty_search_results');

// Search performance test scenarios
export const options = {
  scenarios: {
    // Basic text search
    text_search: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 20,
      maxVUs: 50,
      exec: 'textSearchTest',
    },
    
    // Complex filtered search
    filtered_search: {
      executor: 'constant-arrival-rate',
      rate: 30,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 20,
      maxVUs: 40,
      exec: 'filteredSearchTest',
      startTime: '10m',
    },
    
    // Faceted search with aggregations
    faceted_search: {
      executor: 'constant-arrival-rate',
      rate: 20,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 15,
      maxVUs: 30,
      exec: 'facetedSearchTest',
      startTime: '20m',
    },
    
    // Auto-complete suggestions
    autocomplete_search: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 30,
      maxVUs: 60,
      exec: 'autocompleteTest',
      startTime: '30m',
    },
    
    // Advanced search with AI
    semantic_search: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 10,
      maxVUs: 20,
      exec: 'semanticSearchTest',
      startTime: '40m',
    },
  },
  
  thresholds: {
    search_response_time: ['p(95)<1000', 'p(99)<2000'], // 95% under 1s, 99% under 2s
    search_result_accuracy: ['rate>0.8'], // 80% accuracy
    facet_generation_time: ['p(95)<500'], // Facets generated within 500ms
    suggestion_response_time: ['p(95)<100'], // Suggestions within 100ms
    search_errors: ['count<100'], // Less than 100 errors
    empty_search_results: ['rate<0.1'], // Less than 10% empty results
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Search terms and filters for realistic testing
const SEARCH_TERMS = [
  'video', 'image', 'document', 'presentation', 'audio',
  'project', 'campaign', 'commercial', 'interview', 'tutorial',
  '4K', 'HD', 'raw', 'edited', 'final',
  'red', 'blue', 'green', 'nature', 'urban',
  'January', 'February', 'Q1', '2024', 'annual',
];

const FILE_TYPES = ['video/mp4', 'video/mov', 'image/jpeg', 'image/png', 'application/pdf'];
const TAGS = ['approved', 'review', 'draft', 'final', 'archived', 'featured', 'urgent'];
const PROJECTS = ['Project Alpha', 'Project Beta', 'Campaign 2024', 'Product Launch', 'Training Videos'];

// Helper function to get auth token
function getAuthToken() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: 'search-test@mams.local',
      password: 'SearchTest123!',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return loginRes.status === 200 ? loginRes.json('data.accessToken') : null;
}

// Test 1: Basic text search
export function textSearchTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Random search term
  const searchTerm = SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)];
  
  const startTime = Date.now();
  const res = http.get(
    `${BASE_URL}/api/v1/search?q=${encodeURIComponent(searchTerm)}&limit=20`,
    { headers }
  );
  const responseTime = Date.now() - startTime;
  
  searchResponseTime.add(responseTime);
  
  if (res.status === 200) {
    const data = res.json('data');
    const resultCount = data.results ? data.results.length : 0;
    searchResultCount.add(resultCount);
    
    // Check if results are relevant
    const relevant = data.results && data.results.some(r => 
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.tags?.some(t => t.toLowerCase().includes(searchTerm.toLowerCase()))
    );
    
    searchResultAccuracy.add(relevant || resultCount === 0);
    
    if (resultCount === 0) {
      emptyResults.add(1);
    }
  } else {
    searchErrors.add(1);
    searchResultAccuracy.add(false);
  }
  
  sleep(Math.random() * 2 + 1);
}

// Test 2: Filtered search
export function filteredSearchTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Build complex filter
  const filters = {
    type: FILE_TYPES[Math.floor(Math.random() * FILE_TYPES.length)],
    tags: [TAGS[Math.floor(Math.random() * TAGS.length)]],
    dateRange: {
      start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(), // 90 days ago
      end: new Date().toISOString(),
    },
    sizeRange: {
      min: 1024 * 1024, // 1MB
      max: 1024 * 1024 * 1024, // 1GB
    },
  };
  
  const startTime = Date.now();
  const res = http.post(
    `${BASE_URL}/api/v1/search/filtered`,
    JSON.stringify({
      query: SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)],
      filters: filters,
      sort: { field: 'created_at', order: 'desc' },
      limit: 50,
    }),
    { headers }
  );
  const responseTime = Date.now() - startTime;
  
  searchResponseTime.add(responseTime);
  
  check(res, {
    'filtered search successful': (r) => r.status === 200,
    'filters applied': (r) => {
      if (r.status !== 200) return false;
      const data = r.json('data');
      // Check if results match filters
      return data.results && data.results.every(result => {
        return result.type === filters.type || 
               result.tags?.some(t => filters.tags.includes(t));
      });
    },
  });
  
  if (res.status !== 200) {
    searchErrors.add(1);
  }
  
  sleep(Math.random() * 2 + 1);
}

// Test 3: Faceted search with aggregations
export function facetedSearchTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  const facetStartTime = Date.now();
  const res = http.post(
    `${BASE_URL}/api/v1/search/faceted`,
    JSON.stringify({
      query: '*', // All documents
      facets: {
        type: { field: 'type' },
        tags: { field: 'tags', size: 20 },
        projects: { field: 'project_id', size: 10 },
        dateHistogram: {
          field: 'created_at',
          interval: 'month',
          min_doc_count: 1,
        },
        sizeRange: {
          field: 'size',
          ranges: [
            { to: 1024 * 1024 }, // < 1MB
            { from: 1024 * 1024, to: 100 * 1024 * 1024 }, // 1MB - 100MB
            { from: 100 * 1024 * 1024, to: 1024 * 1024 * 1024 }, // 100MB - 1GB
            { from: 1024 * 1024 * 1024 }, // > 1GB
          ],
        },
      },
      limit: 0, // Only want facets, no results
    }),
    { headers }
  );
  const facetTime = Date.now() - facetStartTime;
  
  facetGenerationTime.add(facetTime);
  
  check(res, {
    'facets returned': (r) => r.status === 200 && r.json('data.facets') !== null,
    'all facet types present': (r) => {
      if (r.status !== 200) return false;
      const facets = r.json('data.facets');
      return facets && 
             facets.type && 
             facets.tags && 
             facets.projects && 
             facets.dateHistogram &&
             facets.sizeRange;
    },
  });
  
  if (res.status !== 200) {
    searchErrors.add(1);
  }
  
  sleep(Math.random() * 3 + 2);
}

// Test 4: Auto-complete suggestions
export function autocompleteTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Simulate typing with partial terms
  const fullTerm = SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)];
  const partialTerm = fullTerm.substring(0, Math.floor(Math.random() * fullTerm.length) + 1);
  
  const startTime = Date.now();
  const res = http.get(
    `${BASE_URL}/api/v1/search/suggest?q=${encodeURIComponent(partialTerm)}&size=10`,
    { headers }
  );
  const responseTime = Date.now() - startTime;
  
  suggestionResponseTime.add(responseTime);
  
  check(res, {
    'suggestions returned quickly': (r) => r.status === 200 && responseTime < 100,
    'relevant suggestions': (r) => {
      if (r.status !== 200) return false;
      const suggestions = r.json('data.suggestions');
      return suggestions && suggestions.length > 0 && 
             suggestions.some(s => s.toLowerCase().includes(partialTerm.toLowerCase()));
    },
  });
  
  if (res.status !== 200) {
    searchErrors.add(1);
  }
  
  sleep(Math.random() * 0.5); // Simulate fast typing
}

// Test 5: Semantic/AI-powered search
export function semanticSearchTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Natural language queries
  const semanticQueries = [
    'Find all videos from last month about product launches',
    'Show me high resolution nature images',
    'Get interview footage with good audio quality',
    'Find presentations about quarterly results',
    'Search for approved marketing materials',
    'Locate raw footage that needs editing',
    'Find all assets related to the summer campaign',
  ];
  
  const query = semanticQueries[Math.floor(Math.random() * semanticQueries.length)];
  
  const startTime = Date.now();
  const res = http.post(
    `${BASE_URL}/api/v1/search/semantic`,
    JSON.stringify({
      query: query,
      useAI: true,
      includeRelated: true,
      limit: 30,
    }),
    { headers }
  );
  const responseTime = Date.now() - startTime;
  
  searchResponseTime.add(responseTime);
  
  if (res.status === 200) {
    const data = res.json('data');
    searchResultCount.add(data.results ? data.results.length : 0);
    
    // Check if AI interpretation is included
    check(res, {
      'AI interpretation provided': (r) => r.json('data.interpretation') !== null,
      'confidence scores included': (r) => {
        const results = r.json('data.results');
        return results && results.every(r => r.relevance_score !== undefined);
      },
    });
    
    // Semantic search should generally return relevant results
    searchResultAccuracy.add(data.results && data.results.length > 0);
  } else {
    searchErrors.add(1);
    searchResultAccuracy.add(false);
  }
  
  sleep(Math.random() * 3 + 2);
}

// Teardown: Generate search performance summary
export function teardown(data) {
  console.log('Search Performance Test Summary:');
  console.log('================================');
  console.log(`Total search errors: ${searchErrors.value || 0}`);
  console.log(`Empty result rate: ${(emptyResults.value || 0) / (data.iterations || 1) * 100}%`);
}