# Frontend Bundle Size Optimization Guide for MAMS

## Overview

This guide provides comprehensive strategies for optimizing the MAMS frontend bundle size, reducing load times, and improving performance. The optimization focuses on code splitting, lazy loading, asset optimization, and bundle analysis.

## Current State Analysis

### Bundle Composition
```
Initial Bundle (before optimization):
├── Main Bundle: ~800KB (uncompressed)
├── Vendor Bundle: ~1.2MB (React, MUI, etc.)
├── CSS Bundle: ~150KB
└── Assets: ~2MB (images, fonts, icons)

Target Bundle (after optimization):
├── Main Bundle: <250KB
├── Vendor Chunks: <300KB each
├── CSS Bundle: <50KB
└── Optimized Assets: <500KB
```

## Optimization Strategies

### 1. Code Splitting

#### Route-Based Splitting
```typescript
// Lazy load pages
const Dashboard = lazy(() => import('../pages/Dashboard'));
const AssetLibrary = lazy(() => import('../pages/AssetLibrary'));
const Timeline = lazy(() => import('../pages/Timeline'));
const Analytics = lazy(() => import('../pages/Analytics'));

// Route configuration
const router = createBrowserRouter([
  {
    path: '/dashboard',
    element: (
      <LazyWrapper>
        <Dashboard />
      </LazyWrapper>
    )
  },
  // ... other routes
]);
```

#### Component-Based Splitting
```typescript
// Heavy components
const VideoPlayer = lazy(() => import('../components/media/VideoPlayer'));
const Timeline = lazy(() => import('../components/timeline/Timeline'));
const WorkflowDesigner = lazy(() => import('../components/workflow/WorkflowDesigner'));

// Library splitting
const loadVideoJS = () => import('video.js');
const loadCharts = () => import('recharts');
const loadPdfViewer = () => import('react-pdf');
```

### 2. Bundle Optimization

#### Vite Configuration
```typescript
// vite.config.optimization.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'redux-vendor': ['@reduxjs/toolkit', 'react-redux'],
          'mui-vendor': ['@mui/material', '@mui/icons-material'],
          'utils-vendor': ['lodash-es', 'date-fns', 'axios'],
          'media-vendor': ['video.js', 'wavesurfer.js'],
          'charts-vendor': ['recharts', 'd3-scale'],
        }
      }
    }
  }
});
```

#### Tree Shaking
```typescript
// Use ES modules for better tree shaking
import { debounce } from 'lodash-es'; // ✅ Good
import _ from 'lodash'; // ❌ Bad - imports entire library

// Import only needed MUI components
import Button from '@mui/material/Button'; // ✅ Good
import { Button } from '@mui/material'; // ⚠️ Okay with babel plugin
```

### 3. Asset Optimization

#### Image Optimization
```bash
# Run asset optimization
npm run optimize-assets

# Generated formats:
# - Original format (optimized)
# - WebP format
# - Responsive sizes (thumbnail, small, medium, large)
# - Progressive JPEG
# - Compressed PNG
```

#### Font Optimization
```css
/* Subset fonts to reduce size */
@font-face {
  font-family: 'Roboto';
  src: url('/assets/fonts/roboto-subset.woff2') format('woff2');
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153;
}

/* Preload critical fonts */
<link rel="preload" href="/assets/fonts/roboto-400.woff2" as="font" type="font/woff2" crossorigin>
```

### 4. Progressive Loading

#### Lazy Loading Implementation
```typescript
// LazyWrapper with Suspense
const LazyWrapper: React.FC = ({ children }) => (
  <ErrorBoundary>
    <Suspense fallback={<SkeletonLoader />}>
      {children}
    </Suspense>
  </ErrorBoundary>
);

// Progressive component loading
const useProgressiveLoading = (components: string[]) => {
  const [currentStep, setCurrentStep] = useState(0);
  
  const loadNextStep = useCallback(() => {
    if (currentStep < components.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  }, [currentStep, components.length]);
  
  return { currentStep, loadNextStep };
};
```

#### Intersection Observer for Preloading
```typescript
// Preload components when links are visible
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const href = entry.target.getAttribute('href');
      if (href) preloadRouteComponents(href);
    }
  });
}, { rootMargin: '50px' });
```

### 5. Bundle Analysis

#### Webpack Bundle Analyzer
```bash
# Analyze bundle composition
npm run build:analyze

# View interactive treemap
open dist/stats.html
```

#### Size Monitoring
```json
// package.json size limits
"size-limit": [
  {
    "name": "Main bundle",
    "path": "dist/assets/index-*.js",
    "limit": "250 KB"
  },
  {
    "name": "Vendor bundle",
    "path": "dist/assets/vendor-*.js",
    "limit": "300 KB"
  }
]
```

## Implementation Steps

### Step 1: Setup Optimization Configuration

1. **Update Vite Config**:
   ```bash
   cp vite.config.optimization.ts vite.config.ts
   ```

2. **Install Dependencies**:
   ```bash
   npm install --save-dev rollup-plugin-visualizer vite-plugin-compression size-limit
   ```

3. **Update Package Scripts**:
   ```json
   {
     "scripts": {
       "build:analyze": "ANALYZE=true npm run build",
       "size-limit": "size-limit"
     }
   }
   ```

### Step 2: Implement Code Splitting

1. **Convert Routes to Lazy Loading**:
   ```typescript
   // Replace direct imports with lazy imports
   const Dashboard = lazy(() => import('../pages/Dashboard'));
   ```

2. **Wrap with LazyWrapper**:
   ```typescript
   <Route path="/dashboard" element={
     <LazyWrapper>
       <Dashboard />
     </LazyWrapper>
   } />
   ```

3. **Split Heavy Components**:
   ```typescript
   // Identify components > 50KB and make them lazy
   const VideoPlayer = lazy(() => import('../components/VideoPlayer'));
   ```

### Step 3: Optimize Assets

1. **Run Asset Optimization**:
   ```bash
   node scripts/optimize-assets.js
   ```

2. **Configure CDN Integration**:
   ```typescript
   // Use optimized assets from CDN
   const assetUrl = cdnService.getOptimizedImageUrl(path, {
     width: 800,
     format: 'webp',
     quality: 85
   });
   ```

### Step 4: Implement Progressive Loading

1. **Add Intersection Observer**:
   ```typescript
   useEffect(() => {
     setupLinkPreloading();
     lazyLoadImages();
   }, []);
   ```

2. **Preload Critical Components**:
   ```typescript
   // On route change
   useEffect(() => {
     preloadRouteComponents(location.pathname);
   }, [location.pathname]);
   ```

### Step 5: Monitor and Optimize

1. **Run Bundle Analysis**:
   ```bash
   npm run build:analyze
   npm run size-limit
   ```

2. **Check Performance**:
   ```bash
   # Lighthouse CI
   lhci autorun --upload.target=temporary-public-storage
   ```

## Performance Targets

### Bundle Size Targets
- **Main Bundle**: <250KB (gzipped)
- **Vendor Chunks**: <300KB each (gzipped)
- **Route Chunks**: <100KB each (gzipped)
- **CSS Bundle**: <50KB (gzipped)
- **Total Initial Load**: <500KB (gzipped)

### Loading Performance Targets
- **First Contentful Paint**: <1.5s
- **Largest Contentful Paint**: <2.5s
- **Time to Interactive**: <3.5s
- **First Input Delay**: <100ms
- **Cumulative Layout Shift**: <0.1

## Monitoring and Alerts

### Real-Time Monitoring
```typescript
// Bundle performance monitoring
const bundleAnalyzer = new BundleAnalyzer();

// Monitor chunk loading
bundleAnalyzer.monitorChunkLoading();

// Generate reports
window.addEventListener('load', () => {
  bundleAnalyzer.generateReport().then(report => {
    console.log('Bundle Report:', report);
    
    // Send to analytics
    gtag('event', 'bundle_analysis', {
      total_size: report.bundleAnalysis.totalSize,
      load_time: report.bundleAnalysis.loadTime
    });
  });
});
```

### CI/CD Integration
```yaml
# .github/workflows/size-check.yml
name: Bundle Size Check

on: [pull_request]

jobs:
  size-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
      - name: Install dependencies
        run: npm ci
      - name: Build project
        run: npm run build
      - name: Check bundle size
        run: npm run size-limit
```

### Performance Budgets
```javascript
// webpack.config.js performance budgets
module.exports = {
  performance: {
    maxAssetSize: 250000, // 250KB
    maxEntrypointSize: 250000,
    hints: 'error'
  }
};
```

## Best Practices

### 1. Component Design
- Keep components under 50KB uncompressed
- Use composition over large monolithic components
- Implement proper error boundaries for lazy components

### 2. Library Management
- Use ES modules for better tree shaking
- Import only needed functionality
- Consider lighter alternatives (e.g., date-fns vs moment.js)

### 3. Asset Management
- Use WebP images with fallbacks
- Implement responsive images
- Lazy load images below the fold
- Optimize SVGs and use icon fonts sparingly

### 4. Caching Strategy
- Implement proper cache headers
- Use service workers for offline caching
- Version assets with hashes
- Cache vendor chunks separately

## Troubleshooting

### Common Issues

1. **Large Vendor Bundles**
   ```bash
   # Analyze vendor dependencies
   npx webpack-bundle-analyzer dist/static/js/*.js
   
   # Split large vendors further
   splitChunks: {
     chunks: 'all',
     cacheGroups: {
       mui: {
         test: /[\\/]node_modules[\\/]@mui[\\/]/,
         name: 'mui',
         chunks: 'all',
       }
     }
   }
   ```

2. **Lazy Loading Errors**
   ```typescript
   // Add retry logic
   const retryImport = (fn: () => Promise<any>, retriesLeft = 3): Promise<any> => {
     return fn().catch((error) => {
       if (retriesLeft === 1) throw error;
       return retryImport(fn, retriesLeft - 1);
     });
   };
   
   const LazyComponent = lazy(() => 
     retryImport(() => import('./Component'))
   );
   ```

3. **CSS Loading Issues**
   ```typescript
   // Ensure CSS is loaded with component
   const LazyComponent = lazy(() => 
     Promise.all([
       import('./Component'),
       import('./Component.css')
     ]).then(([Component]) => Component)
   );
   ```

## Tools and Resources

### Build Tools
- **Vite**: Fast build tool with excellent optimization
- **Rollup**: Advanced bundling with tree shaking
- **SWC**: Fast TypeScript/JavaScript compiler

### Analysis Tools
- **webpack-bundle-analyzer**: Interactive bundle visualization
- **size-limit**: Size tracking and limits
- **bundlephobia**: Analyze npm package impact

### Performance Tools
- **Lighthouse**: Performance auditing
- **WebPageTest**: Real-world performance testing
- **Chrome DevTools**: Network and performance analysis

## Results and Impact

### Expected Improvements
- **50-70% reduction** in initial bundle size
- **40-60% faster** initial page load
- **Improved** Core Web Vitals scores
- **Better** user experience on slow networks
- **Reduced** CDN and hosting costs

### Measurement Strategy
1. **Before/After Metrics**: Compare bundle sizes and load times
2. **User Metrics**: Monitor real user performance data
3. **Business Metrics**: Track conversion rates and engagement
4. **Technical Metrics**: Monitor error rates and load failures

This optimization guide ensures that the MAMS frontend delivers optimal performance while maintaining functionality and user experience.