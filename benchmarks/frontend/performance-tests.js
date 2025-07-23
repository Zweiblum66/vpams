import puppeteer from 'puppeteer';
import lighthouse from 'lighthouse';
import fs from 'fs/promises';
import path from 'path';

const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const TEST_USER = {
  email: process.env.TEST_EMAIL || 'perf-test@mams.local',
  password: process.env.TEST_PASSWORD || 'PerfTest123!@#',
};

// Custom performance metrics collector
class PerformanceCollector {
  constructor() {
    this.metrics = [];
  }

  async measurePageLoad(page, url, name) {
    const startTime = Date.now();
    
    // Enable performance monitoring
    await page.evaluateOnNewDocument(() => {
      window.__PERF_MARKS__ = {};
      window.__PERF_MEASURES__ = {};
      
      // Override performance.mark
      const originalMark = window.performance.mark.bind(window.performance);
      window.performance.mark = function(name) {
        window.__PERF_MARKS__[name] = performance.now();
        return originalMark(name);
      };
      
      // Override performance.measure
      const originalMeasure = window.performance.measure.bind(window.performance);
      window.performance.measure = function(name, startMark, endMark) {
        const result = originalMeasure(name, startMark, endMark);
        const entries = performance.getEntriesByName(name, 'measure');
        if (entries.length > 0) {
          window.__PERF_MEASURES__[name] = entries[0].duration;
        }
        return result;
      };
    });
    
    // Navigate to page
    await page.goto(url, { waitUntil: 'networkidle0' });
    
    // Wait for custom app ready signal
    await page.waitForFunction(() => window.__APP_READY__ === true, { timeout: 10000 }).catch(() => {});
    
    const loadTime = Date.now() - startTime;
    
    // Collect performance metrics
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      const paint = performance.getEntriesByType('paint');
      const resources = performance.getEntriesByType('resource');
      
      // Calculate resource metrics
      const jsSize = resources
        .filter(r => r.name.endsWith('.js'))
        .reduce((sum, r) => sum + (r.transferSize || 0), 0);
        
      const cssSize = resources
        .filter(r => r.name.endsWith('.css'))
        .reduce((sum, r) => sum + (r.transferSize || 0), 0);
        
      const imageSize = resources
        .filter(r => r.initiatorType === 'img')
        .reduce((sum, r) => sum + (r.transferSize || 0), 0);
      
      return {
        // Navigation timing
        dns: navigation.domainLookupEnd - navigation.domainLookupStart,
        tcp: navigation.connectEnd - navigation.connectStart,
        ttfb: navigation.responseStart - navigation.requestStart,
        download: navigation.responseEnd - navigation.responseStart,
        domInteractive: navigation.domInteractive,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        load: navigation.loadEventEnd - navigation.loadEventStart,
        
        // Paint timing
        firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
        
        // Resource metrics
        resourceCount: resources.length,
        jsSize,
        cssSize,
        imageSize,
        totalSize: jsSize + cssSize + imageSize,
        
        // Custom app metrics
        customMarks: window.__PERF_MARKS__,
        customMeasures: window.__PERF_MEASURES__,
      };
    });
    
    // Get memory usage if available
    const memory = await page.evaluate(() => {
      if (window.performance.memory) {
        return {
          usedJSHeapSize: window.performance.memory.usedJSHeapSize,
          totalJSHeapSize: window.performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: window.performance.memory.jsHeapSizeLimit,
        };
      }
      return null;
    });
    
    this.metrics.push({
      name,
      url,
      timestamp: new Date().toISOString(),
      loadTime,
      ...metrics,
      memory,
    });
    
    return metrics;
  }
}

// Test scenarios
async function runPerformanceTests() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  
  const collector = new PerformanceCollector();
  
  try {
    // Test 1: Initial page load (cold)
    console.log('Testing initial page load (cold)...');
    const page = await browser.newPage();
    await page.setCacheEnabled(false);
    await collector.measurePageLoad(page, BASE_URL, 'Initial Load (Cold)');
    await page.close();
    
    // Test 2: Login flow
    console.log('Testing login flow...');
    const loginPage = await browser.newPage();
    await loginPage.goto(`${BASE_URL}/login`);
    
    // Measure login interaction
    const loginStartTime = Date.now();
    await loginPage.type('input[name="email"]', TEST_USER.email);
    await loginPage.type('input[name="password"]', TEST_USER.password);
    await loginPage.click('button[type="submit"]');
    await loginPage.waitForNavigation({ waitUntil: 'networkidle0' });
    const loginTime = Date.now() - loginStartTime;
    
    collector.metrics.push({
      name: 'Login Flow',
      timestamp: new Date().toISOString(),
      duration: loginTime,
    });
    
    // Get auth token for subsequent tests
    const authToken = await loginPage.evaluate(() => localStorage.getItem('authToken'));
    
    // Test 3: Asset listing page
    console.log('Testing asset listing page...');
    await collector.measurePageLoad(loginPage, `${BASE_URL}/assets`, 'Asset Listing');
    
    // Test 4: Search performance
    console.log('Testing search performance...');
    const searchStartTime = Date.now();
    await loginPage.type('input[name="search"]', 'test video');
    await loginPage.keyboard.press('Enter');
    await loginPage.waitForSelector('[data-testid="search-results"]', { timeout: 5000 });
    const searchTime = Date.now() - searchStartTime;
    
    collector.metrics.push({
      name: 'Search Operation',
      timestamp: new Date().toISOString(),
      duration: searchTime,
    });
    
    // Test 5: Asset detail page
    console.log('Testing asset detail page...');
    const firstAsset = await loginPage.$('[data-testid="asset-item"]:first-child a');
    if (firstAsset) {
      await firstAsset.click();
      await loginPage.waitForNavigation({ waitUntil: 'networkidle0' });
      
      const detailMetrics = await loginPage.evaluate(() => {
        return {
          videoLoadTime: window.__PERF_MEASURES__?.['video-load'] || null,
          metadataLoadTime: window.__PERF_MEASURES__?.['metadata-load'] || null,
          thumbnailLoadTime: window.__PERF_MEASURES__?.['thumbnail-load'] || null,
        };
      });
      
      collector.metrics.push({
        name: 'Asset Detail Page',
        timestamp: new Date().toISOString(),
        ...detailMetrics,
      });
    }
    
    await loginPage.close();
    
    // Test 6: Warm cache performance
    console.log('Testing warm cache performance...');
    const warmPage = await browser.newPage();
    await warmPage.setCacheEnabled(true);
    
    // Set auth token
    await warmPage.evaluateOnNewDocument((token) => {
      localStorage.setItem('authToken', token);
    }, authToken);
    
    await collector.measurePageLoad(warmPage, `${BASE_URL}/assets`, 'Asset Listing (Warm Cache)');
    await warmPage.close();
    
    // Run Lighthouse tests
    console.log('Running Lighthouse tests...');
    const lighthouseResults = await runLighthouseTests(browser);
    
    // Generate report
    const report = {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      baseUrl: BASE_URL,
      metrics: collector.metrics,
      lighthouse: lighthouseResults,
      summary: generateSummary(collector.metrics),
    };
    
    // Save report
    const reportPath = path.join(
      process.cwd(),
      'benchmarks',
      'reports',
      `frontend-performance-${Date.now()}.json`
    );
    
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`Performance report saved to: ${reportPath}`);
    
    return report;
    
  } finally {
    await browser.close();
  }
}

// Run Lighthouse tests
async function runLighthouseTests(browser) {
  const results = {};
  
  const pages = [
    { name: 'home', url: BASE_URL },
    { name: 'login', url: `${BASE_URL}/login` },
    { name: 'assets', url: `${BASE_URL}/assets` },
    { name: 'search', url: `${BASE_URL}/search?q=test` },
  ];
  
  for (const { name, url } of pages) {
    console.log(`Running Lighthouse for ${name} page...`);
    
    const { lhr } = await lighthouse(url, {
      port: new URL(browser.wsEndpoint()).port,
      output: 'json',
      logLevel: 'error',
      configPath: './lighthouse-config.js',
    });
    
    results[name] = {
      scores: {
        performance: lhr.categories.performance.score * 100,
        accessibility: lhr.categories.accessibility?.score * 100,
        bestPractices: lhr.categories['best-practices']?.score * 100,
        seo: lhr.categories.seo?.score * 100,
      },
      metrics: {
        firstContentfulPaint: lhr.audits['first-contentful-paint'].numericValue,
        largestContentfulPaint: lhr.audits['largest-contentful-paint'].numericValue,
        totalBlockingTime: lhr.audits['total-blocking-time'].numericValue,
        cumulativeLayoutShift: lhr.audits['cumulative-layout-shift'].numericValue,
        speedIndex: lhr.audits['speed-index'].numericValue,
      },
    };
  }
  
  return results;
}

// Generate summary statistics
function generateSummary(metrics) {
  const pageLoads = metrics.filter(m => m.loadTime);
  const loadTimes = pageLoads.map(m => m.loadTime);
  
  return {
    pageLoadMetrics: {
      count: loadTimes.length,
      average: loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length,
      min: Math.min(...loadTimes),
      max: Math.max(...loadTimes),
      p50: percentile(loadTimes, 0.5),
      p90: percentile(loadTimes, 0.9),
      p95: percentile(loadTimes, 0.95),
      p99: percentile(loadTimes, 0.99),
    },
    resourceMetrics: {
      averageJsSize: average(pageLoads.map(m => m.jsSize)),
      averageCssSize: average(pageLoads.map(m => m.cssSize)),
      averageImageSize: average(pageLoads.map(m => m.imageSize)),
      averageTotalSize: average(pageLoads.map(m => m.totalSize)),
      averageResourceCount: average(pageLoads.map(m => m.resourceCount)),
    },
  };
}

// Helper functions
function percentile(arr, p) {
  const sorted = arr.slice().sort((a, b) => a - b);
  const index = Math.floor(sorted.length * p);
  return sorted[index];
}

function average(arr) {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

// Run tests if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runPerformanceTests()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error('Performance tests failed:', error);
      process.exit(1);
    });
}

export { runPerformanceTests, PerformanceCollector };