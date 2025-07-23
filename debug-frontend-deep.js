const puppeteer = require('puppeteer');
const fs = require('fs').promises;

async function debugFrontend() {
  console.log('Deep Frontend Debugging with Puppeteer\n');
  console.log('=====================================\n');
  
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    
    // Enable request interception to see what's being loaded
    await page.setRequestInterception(true);
    const resources = [];
    
    page.on('request', request => {
      const url = request.url();
      const type = request.resourceType();
      resources.push({ url, type });
      request.continue();
    });
    
    // Capture console messages
    const consoleLogs = [];
    page.on('console', msg => {
      consoleLogs.push({
        type: msg.type(),
        text: msg.text()
      });
    });
    
    // Capture errors
    const pageErrors = [];
    page.on('pageerror', error => {
      pageErrors.push(error.toString());
    });
    
    console.log('1. Loading frontend page...');
    try {
      const response = await page.goto('http://192.168.178.186:3000', { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });
      
      console.log(`   Status: ${response.status()}`);
      console.log(`   Content-Type: ${response.headers()['content-type']}`);
      
    } catch (error) {
      console.log('   ❌ Error loading page:', error.message);
      return;
    }
    
    // Get the raw HTML
    const html = await page.content();
    const htmlPreview = html.substring(0, 500);
    console.log('\n2. HTML Content Preview:');
    console.log('   ' + htmlPreview.replace(/\n/g, '\n   '));
    
    // Check for React indicators
    console.log('\n3. Checking for React/SPA indicators:');
    
    const reactIndicators = await page.evaluate(() => {
      const checks = {
        hasRootDiv: !!document.getElementById('root'),
        hasReactRoot: !!document.querySelector('[data-reactroot]'),
        hasReactInWindow: typeof window.React !== 'undefined',
        hasReactDOM: typeof window.ReactDOM !== 'undefined',
        scriptTags: Array.from(document.querySelectorAll('script')).map(s => s.src || 'inline'),
        linkTags: Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.href),
        metaTags: Array.from(document.querySelectorAll('meta')).map(m => ({
          name: m.name || m.property,
          content: m.content
        }))
      };
      
      // Check for Vite/React build artifacts
      checks.hasViteModule = Array.from(document.querySelectorAll('script')).some(s => 
        s.type === 'module' || s.src.includes('/@vite') || s.src.includes('/assets/')
      );
      
      return checks;
    });
    
    console.log('   Root div (#root):', reactIndicators.hasRootDiv ? '✅' : '❌');
    console.log('   React root element:', reactIndicators.hasReactRoot ? '✅' : '❌');
    console.log('   React in window:', reactIndicators.hasReactInWindow ? '✅' : '❌');
    console.log('   Vite modules:', reactIndicators.hasViteModule ? '✅' : '❌');
    
    console.log('\n4. Script tags found:');
    reactIndicators.scriptTags.forEach(script => {
      console.log('   -', script || '(inline script)');
    });
    
    console.log('\n5. Stylesheets found:');
    reactIndicators.linkTags.forEach(link => {
      console.log('   -', link);
    });
    
    // Analyze loaded resources
    console.log('\n6. Resources loaded:');
    const resourceTypes = {};
    resources.forEach(r => {
      resourceTypes[r.type] = (resourceTypes[r.type] || 0) + 1;
    });
    Object.entries(resourceTypes).forEach(([type, count]) => {
      console.log(`   ${type}: ${count}`);
    });
    
    // Check for specific React app files
    console.log('\n7. Checking for expected React app files:');
    const expectedFiles = [
      '/src/main.tsx',
      '/src/App.tsx',
      '/assets/',
      '/@vite',
      '/node_modules/'
    ];
    
    for (const file of expectedFiles) {
      const found = resources.some(r => r.url.includes(file));
      console.log(`   ${file}: ${found ? '✅' : '❌'}`);
    }
    
    // Console logs
    if (consoleLogs.length > 0) {
      console.log('\n8. Console logs:');
      consoleLogs.forEach(log => {
        console.log(`   [${log.type}] ${log.text}`);
      });
    }
    
    // Page errors
    if (pageErrors.length > 0) {
      console.log('\n9. Page errors:');
      pageErrors.forEach(error => {
        console.log('   ', error);
      });
    }
    
    // Try to check nginx configuration
    console.log('\n10. Checking server configuration:');
    
    // Test common React app paths
    const testPaths = [
      '/index.html',
      '/manifest.json',
      '/favicon.ico',
      '/static/js/bundle.js',
      '/assets/index.js',
      '/@vite/client'
    ];
    
    for (const path of testPaths) {
      try {
        const response = await page.goto(`http://192.168.178.186:3000${path}`, {
          waitUntil: 'domcontentloaded',
          timeout: 5000
        });
        console.log(`   ${path}: ${response.status()}`);
      } catch (e) {
        console.log(`   ${path}: Failed`);
      }
    }
    
    // Go back to main page
    await page.goto('http://192.168.178.186:3000');
    
    // Take screenshots
    console.log('\n11. Taking screenshots...');
    await page.screenshot({ 
      path: './frontend-debug-full.png',
      fullPage: true 
    });
    console.log('   Full page: ./frontend-debug-full.png');
    
    // Check if we can inject React manually
    console.log('\n12. Attempting to find React app entry point...');
    
    const entryPointCheck = await page.evaluate(() => {
      // Look for common entry points
      const possibleEntryPoints = [
        document.querySelector('script[type="module"]'),
        document.querySelector('script[src*="main"]'),
        document.querySelector('script[src*="index"]'),
        document.querySelector('script[src*="app"]')
      ];
      
      return possibleEntryPoints.map(script => {
        if (!script) return null;
        return {
          src: script.src,
          type: script.type,
          content: script.innerHTML.substring(0, 100)
        };
      }).filter(Boolean);
    });
    
    console.log('   Entry points found:', entryPointCheck.length);
    entryPointCheck.forEach(ep => {
      console.log(`   - ${ep.src || 'inline'} (type: ${ep.type})`);
    });
    
    // Generate diagnostic report
    console.log('\n13. Generating diagnostic report...');
    
    const report = {
      timestamp: new Date().toISOString(),
      url: 'http://192.168.178.186:3000',
      reactDetected: reactIndicators.hasRootDiv || reactIndicators.hasViteModule,
      resourcesLoaded: resources.length,
      errors: pageErrors,
      recommendations: []
    };
    
    // Add recommendations
    if (!reactIndicators.hasRootDiv) {
      report.recommendations.push('Missing #root div - React app not mounting');
    }
    if (!reactIndicators.hasViteModule && reactIndicators.scriptTags.length === 0) {
      report.recommendations.push('No module scripts found - Vite build may have failed');
    }
    if (html.includes('nginx')) {
      report.recommendations.push('Nginx default page detected - check nginx configuration');
    }
    if (html.includes('MAMS - Media Asset Management System') && !reactIndicators.hasRootDiv) {
      report.recommendations.push('Static HTML is being served instead of React app');
    }
    
    await fs.writeFile('./frontend-diagnostic-report.json', JSON.stringify(report, null, 2));
    console.log('   Report saved: ./frontend-diagnostic-report.json');
    
    console.log('\n14. Diagnosis Summary:');
    console.log('   ' + (report.reactDetected ? '✅ React app detected' : '❌ React app NOT detected'));
    console.log('\n   Recommendations:');
    report.recommendations.forEach(rec => {
      console.log(`   - ${rec}`);
    });
    
  } catch (error) {
    console.error('Error during debugging:', error);
  } finally {
    await browser.close();
  }
}

// Run the debug
debugFrontend().catch(console.error);