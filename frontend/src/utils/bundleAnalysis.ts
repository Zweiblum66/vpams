/**
 * Bundle analysis and optimization utilities
 */

interface BundleInfo {
  name: string;
  size: number;
  gzipSize?: number;
  brotliSize?: number;
  type: 'js' | 'css' | 'asset';
  chunks: string[];
}

interface PerformanceMetrics {
  loadTime: number;
  parseTime: number;
  renderTime: number;
  interactiveTime: number;
}

class BundleAnalyzer {
  private bundles: Map<string, BundleInfo> = new Map();
  private metrics: Map<string, PerformanceMetrics> = new Map();

  /**
   * Analyze current bundle performance
   */
  analyzeCurrentBundle(): Promise<{
    totalSize: number;
    loadTime: number;
    suggestions: string[];
  }> {
    return new Promise((resolve) => {
      // Get performance navigation timing
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      
      // Get resource timing for all scripts and styles
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      let totalSize = 0;
      const suggestions: string[] = [];
      
      // Analyze JavaScript bundles
      const jsResources = resources.filter(r => 
        r.name.includes('.js') && 
        (r.name.includes('/assets/') || r.name.includes('chunk'))
      );
      
      jsResources.forEach(resource => {
        const size = resource.transferSize || 0;
        totalSize += size;
        
        // Check for large bundles
        if (size > 500 * 1024) { // 500KB
          suggestions.push(`Large bundle detected: ${resource.name} (${(size / 1024).toFixed(1)}KB)`);
        }
        
        // Check for slow loading
        if (resource.duration > 1000) { // 1 second
          suggestions.push(`Slow loading bundle: ${resource.name} (${resource.duration.toFixed(0)}ms)`);
        }
      });
      
      // Analyze CSS bundles
      const cssResources = resources.filter(r => r.name.includes('.css'));
      cssResources.forEach(resource => {
        totalSize += resource.transferSize || 0;
      });
      
      // Check for render-blocking resources
      const renderBlockingJS = jsResources.filter(r => 
        !r.name.includes('chunk') && r.responseEnd < navigation.loadEventStart
      );
      
      if (renderBlockingJS.length > 3) {
        suggestions.push(`Too many render-blocking scripts: ${renderBlockingJS.length}`);
      }
      
      // Check for unused CSS
      if (this.hasUnusedCSS()) {
        suggestions.push('Unused CSS detected - consider code splitting');
      }
      
      // Check for duplicate dependencies
      const duplicates = this.findDuplicateDependencies(jsResources);
      if (duplicates.length > 0) {
        suggestions.push(`Duplicate dependencies found: ${duplicates.join(', ')}`);
      }
      
      resolve({
        totalSize,
        loadTime: navigation.loadEventEnd - navigation.fetchStart,
        suggestions
      });
    });
  }

  /**
   * Detect unused CSS using browser APIs
   */
  private hasUnusedCSS(): boolean {
    try {
      // Check if CSS coverage API is available (dev tools)
      if ('CSS' in window && 'coverage' in (window as any)) {
        return true; // Would need actual coverage data
      }
      
      // Heuristic: check for large CSS files vs DOM complexity
      const stylesheets = Array.from(document.styleSheets);
      const totalRules = stylesheets.reduce((count, sheet) => {
        try {
          return count + (sheet.cssRules?.length || 0);
        } catch (e) {
          return count; // Cross-origin stylesheet
        }
      }, 0);
      
      const domElements = document.querySelectorAll('*').length;
      
      // If we have more than 5 CSS rules per DOM element, likely unused CSS
      return totalRules / domElements > 5;
    } catch (e) {
      return false;
    }
  }

  /**
   * Find potential duplicate dependencies in bundles
   */
  private findDuplicateDependencies(resources: PerformanceResourceTiming[]): string[] {
    const dependencies = new Set<string>();
    const duplicates: string[] = [];
    
    resources.forEach(resource => {
      const url = new URL(resource.name);
      const filename = url.pathname.split('/').pop() || '';
      
      // Extract potential library names from filename
      const matches = filename.match(/^([a-zA-Z-]+)/);
      if (matches) {
        const libName = matches[1];
        if (dependencies.has(libName)) {
          duplicates.push(libName);
        } else {
          dependencies.add(libName);
        }
      }
    });
    
    return Array.from(new Set(duplicates));
  }

  /**
   * Monitor chunk loading performance
   */
  monitorChunkLoading(): void {
    // Override dynamic import to track loading
    const originalImport = window.import || ((path: string) => import(path));
    
    (window as any).import = async (path: string) => {
      const startTime = performance.now();
      
      try {
        const result = await originalImport(path);
        const loadTime = performance.now() - startTime;
        
        // Track chunk loading metrics
        this.metrics.set(path, {
          loadTime,
          parseTime: 0,
          renderTime: 0,
          interactiveTime: 0
        });
        
        // Report slow chunks
        if (loadTime > 2000) {
          console.warn(`Slow chunk loading: ${path} took ${loadTime.toFixed(0)}ms`);
          
          // Report to analytics
          if (window.gtag) {
            window.gtag('event', 'slow_chunk_load', {
              chunk_name: path,
              load_time: Math.round(loadTime),
            });
          }
        }
        
        return result;
      } catch (error) {
        console.error(`Failed to load chunk: ${path}`, error);
        
        // Report chunk loading errors
        if (window.gtag) {
          window.gtag('event', 'chunk_load_error', {
            chunk_name: path,
            error_message: String(error),
          });
        }
        
        throw error;
      }
    };
  }

  /**
   * Get bundle size recommendations
   */
  getBundleSizeRecommendations(): {
    current: number;
    recommended: number;
    suggestions: string[];
  } {
    const currentSize = this.calculateCurrentBundleSize();
    const recommendations: string[] = [];
    
    // Target bundle sizes (in KB)
    const targets = {
      initial: 250,  // Main bundle
      chunk: 100,    // Route chunks
      vendor: 300,   // Vendor bundle
    };
    
    if (currentSize.main > targets.initial) {
      recommendations.push(
        `Main bundle too large: ${(currentSize.main / 1024).toFixed(1)}KB > ${targets.initial}KB target`
      );
      recommendations.push('Consider code splitting and lazy loading');
    }
    
    if (currentSize.vendor > targets.vendor) {
      recommendations.push(
        `Vendor bundle too large: ${(currentSize.vendor / 1024).toFixed(1)}KB > ${targets.vendor}KB target`
      );
      recommendations.push('Consider splitting vendor chunks further');
    }
    
    const avgChunkSize = currentSize.chunks.length > 0 
      ? currentSize.chunks.reduce((a, b) => a + b, 0) / currentSize.chunks.length 
      : 0;
      
    if (avgChunkSize > targets.chunk * 1024) {
      recommendations.push(
        `Average chunk size too large: ${(avgChunkSize / 1024).toFixed(1)}KB > ${targets.chunk}KB target`
      );
    }
    
    return {
      current: currentSize.total,
      recommended: targets.initial + targets.vendor + (targets.chunk * 5), // Estimated
      suggestions: recommendations
    };
  }

  /**
   * Calculate current bundle sizes
   */
  private calculateCurrentBundleSize(): {
    main: number;
    vendor: number;
    chunks: number[];
    total: number;
  } {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    
    let main = 0;
    let vendor = 0;
    const chunks: number[] = [];
    
    resources.forEach(resource => {
      if (!resource.name.includes('.js')) return;
      
      const size = resource.transferSize || 0;
      const url = new URL(resource.name);
      const filename = url.pathname.split('/').pop() || '';
      
      if (filename.includes('main') || filename.includes('index')) {
        main += size;
      } else if (filename.includes('vendor') || filename.includes('chunk')) {
        if (filename.includes('vendor')) {
          vendor += size;
        } else {
          chunks.push(size);
        }
      }
    });
    
    return {
      main,
      vendor,
      chunks,
      total: main + vendor + chunks.reduce((a, b) => a + b, 0)
    };
  }

  /**
   * Generate performance report
   */
  generateReport(): Promise<{
    bundleAnalysis: any;
    performance: any;
    recommendations: string[];
  }> {
    return this.analyzeCurrentBundle().then(bundleAnalysis => {
      const performance = this.getPerformanceMetrics();
      const sizeRecommendations = this.getBundleSizeRecommendations();
      
      const allRecommendations = [
        ...bundleAnalysis.suggestions,
        ...sizeRecommendations.suggestions
      ];
      
      return {
        bundleAnalysis,
        performance,
        recommendations: allRecommendations
      };
    });
  }

  /**
   * Get Core Web Vitals and other performance metrics
   */
  private getPerformanceMetrics(): any {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    
    return {
      // Navigation timing
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
      loadComplete: navigation.loadEventEnd - navigation.fetchStart,
      firstByte: navigation.responseStart - navigation.fetchStart,
      
      // Resource counts
      jsResources: performance.getEntriesByType('resource').filter(r => r.name.includes('.js')).length,
      cssResources: performance.getEntriesByType('resource').filter(r => r.name.includes('.css')).length,
      
      // Memory usage (if available)
      memory: (performance as any).memory ? {
        used: (performance as any).memory.usedJSHeapSize,
        total: (performance as any).memory.totalJSHeapSize,
        limit: (performance as any).memory.jsHeapSizeLimit
      } : null
    };
  }
}

// Singleton instance
export const bundleAnalyzer = new BundleAnalyzer();

// Auto-start monitoring in development
if (process.env.NODE_ENV === 'development') {
  bundleAnalyzer.monitorChunkLoading();
  
  // Generate report after page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      bundleAnalyzer.generateReport().then(report => {
        console.group('📊 Bundle Analysis Report');
        console.log('Bundle Analysis:', report.bundleAnalysis);
        console.log('Performance Metrics:', report.performance);
        console.log('Recommendations:', report.recommendations);
        console.groupEnd();
        
        // Save to localStorage for dev tools
        localStorage.setItem('mams-bundle-report', JSON.stringify(report, null, 2));
      });
    }, 2000);
  });
}

// Export utilities
export const getBundleReport = () => bundleAnalyzer.generateReport();
export const getBundleSize = () => bundleAnalyzer.getBundleSizeRecommendations();
export const startMonitoring = () => bundleAnalyzer.monitorChunkLoading();