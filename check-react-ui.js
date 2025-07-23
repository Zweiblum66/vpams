const puppeteer = require('puppeteer');

(async () => {
  console.log('Checking React UI...\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  
  try {
    // Navigate to the frontend
    await page.goto('http://192.168.178.186:3000', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    // Wait for React to render
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Get page title
    const title = await page.title();
    console.log(`Page Title: ${title}`);
    
    // Check for main UI elements
    const elements = await page.evaluate(() => {
      const checks = {
        hasHeader: !!document.querySelector('header'),
        hasNav: !!document.querySelector('nav'),
        hasMain: !!document.querySelector('main'),
        hasMuiElements: !!document.querySelector('[class*="MuiAppBar"]'),
        hasLoginForm: !!document.querySelector('form'),
        hasAssetList: !!document.querySelector('[class*="asset"]'),
        rootContent: document.getElementById('root')?.children.length > 0
      };
      
      // Get visible text
      const visibleText = document.body.innerText || '';
      
      return {
        checks,
        visibleText: visibleText.substring(0, 500)
      };
    });
    
    console.log('\nUI Elements:');
    Object.entries(elements.checks).forEach(([key, value]) => {
      console.log(`  ${key}: ${value ? '✅' : '❌'}`);
    });
    
    console.log('\nVisible Text Preview:');
    console.log(elements.visibleText);
    
    // Take screenshots
    await page.screenshot({ path: 'react-app-full.png', fullPage: true });
    console.log('\nScreenshot saved: react-app-full.png');
    
    // Check for any errors
    const errors = await page.evaluate(() => {
      return window.__REACT_ERROR__ || null;
    });
    
    if (errors) {
      console.log('\n⚠️ React Errors:', errors);
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();