import { logger } from './logger';

export interface PerformanceMetrics {
  name: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface WebVitalsMetrics {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  id: string;
  navigationType: string;
}

class PerformanceMonitor {
  private metrics: Map<string, PerformanceMetrics> = new Map();
  private observers: PerformanceObserver[] = [];
  private isEnabled: boolean = true;

  constructor() {
    this.setupObservers();
    this.trackPageLoad();
  }

  private setupObservers(): void {
    try {
      // Long Task Observer
      if ('PerformanceObserver' in window) {
        const longTaskObserver = new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            if (entry.duration > 50) { // Tasks longer than 50ms
              logger.warn('Long task detected', {
                name: entry.name,
                duration: entry.duration,
                startTime: entry.startTime,
                actionType: 'performance'
              });
            }
          });
        });

        try {
          longTaskObserver.observe({ entryTypes: ['longtask'] });
          this.observers.push(longTaskObserver);
        } catch (e) {
          console.debug('Long task observer not supported');
        }

        // Navigation Observer
        const navigationObserver = new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            const navEntry = entry as PerformanceNavigationTiming;
            this.trackNavigationTiming(navEntry);
          });
        });

        try {
          navigationObserver.observe({ entryTypes: ['navigation'] });
          this.observers.push(navigationObserver);
        } catch (e) {
          console.debug('Navigation observer not supported');
        }

        // Resource Observer
        const resourceObserver = new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            const resourceEntry = entry as PerformanceResourceTiming;
            this.trackResourceTiming(resourceEntry);
          });
        });

        try {
          resourceObserver.observe({ entryTypes: ['resource'] });
          this.observers.push(resourceObserver);
        } catch (e) {
          console.debug('Resource observer not supported');
        }

        // Measure Observer
        const measureObserver = new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            logger.debug('Performance measure', {
              name: entry.name,
              duration: entry.duration,
              startTime: entry.startTime,
              actionType: 'performance'
            });
          });
        });

        try {
          measureObserver.observe({ entryTypes: ['measure'] });
          this.observers.push(measureObserver);
        } catch (e) {
          console.debug('Measure observer not supported');
        }
      }
    } catch (error) {
      logger.error('Failed to setup performance observers', {}, error);
    }
  }

  private trackPageLoad(): void {
    // Track page load performance
    window.addEventListener('load', () => {
      setTimeout(() => {
        if (performance.navigation && performance.timing) {
          const navigation = performance.navigation;
          const timing = performance.timing;
          
          const metrics = {
            navigationStart: timing.navigationStart,
            domContentLoadedEventEnd: timing.domContentLoadedEventEnd,
            loadEventEnd: timing.loadEventEnd,
            domComplete: timing.domComplete,
            redirectTime: timing.redirectEnd - timing.redirectStart,
            dnsTime: timing.domainLookupEnd - timing.domainLookupStart,
            connectTime: timing.connectEnd - timing.connectStart,
            requestTime: timing.responseStart - timing.requestStart,
            responseTime: timing.responseEnd - timing.responseStart,
            domProcessingTime: timing.domComplete - timing.domLoading,
            loadTime: timing.loadEventEnd - timing.navigationStart,
            navigationType: navigation.type,
            redirectCount: navigation.redirectCount
          };

          logger.info('Page load performance', {
            ...metrics,
            actionType: 'performance',
            performanceType: 'page_load'
          });
        }
      }, 0);
    });
  }

  private trackNavigationTiming(entry: PerformanceNavigationTiming): void {
    const metrics = {
      name: entry.name,
      duration: entry.duration,
      redirectTime: entry.redirectEnd - entry.redirectStart,
      dnsTime: entry.domainLookupEnd - entry.domainLookupStart,
      connectTime: entry.connectEnd - entry.connectStart,
      requestTime: entry.responseStart - entry.requestStart,
      responseTime: entry.responseEnd - entry.responseStart,
      domProcessingTime: entry.domComplete - entry.domContentLoadedEventStart,
      loadTime: entry.loadEventEnd - entry.loadEventStart,
      navigationType: entry.type,
      transferSize: entry.transferSize,
      encodedBodySize: entry.encodedBodySize,
      decodedBodySize: entry.decodedBodySize
    };

    logger.info('Navigation timing', {
      ...metrics,
      actionType: 'performance',
      performanceType: 'navigation'
    });
  }

  private trackResourceTiming(entry: PerformanceResourceTiming): void {
    // Only log slow resources or errors
    if (entry.duration > 1000 || entry.transferSize === 0) {
      logger.info('Resource timing', {
        name: entry.name,
        duration: entry.duration,
        transferSize: entry.transferSize,
        encodedBodySize: entry.encodedBodySize,
        decodedBodySize: entry.decodedBodySize,
        initiatorType: entry.initiatorType,
        nextHopProtocol: entry.nextHopProtocol,
        actionType: 'performance',
        performanceType: 'resource'
      });
    }
  }

  // Public API
  startMeasure(name: string, metadata?: Record<string, any>): void {
    if (!this.isEnabled) return;

    const startTime = performance.now();
    this.metrics.set(name, {
      name,
      startTime,
      metadata
    });

    // Use Performance API mark
    try {
      performance.mark(`${name}-start`);
    } catch (error) {
      logger.debug('Performance mark not supported', { name });
    }
  }

  endMeasure(name: string): number | null {
    if (!this.isEnabled) return null;

    const metric = this.metrics.get(name);
    if (!metric) {
      logger.warn('No performance metric found', { name });
      return null;
    }

    const endTime = performance.now();
    const duration = endTime - metric.startTime;

    // Update metric
    metric.endTime = endTime;
    metric.duration = duration;

    // Use Performance API measure
    try {
      performance.mark(`${name}-end`);
      performance.measure(name, `${name}-start`, `${name}-end`);
    } catch (error) {
      logger.debug('Performance measure not supported', { name });
    }

    // Log the measurement
    logger.info('Performance measurement', {
      name,
      duration,
      startTime: metric.startTime,
      endTime,
      metadata: metric.metadata,
      actionType: 'performance',
      performanceType: 'measure'
    });

    // Clean up
    this.metrics.delete(name);

    return duration;
  }

  measureAsync<T>(name: string, asyncFunction: () => Promise<T>, metadata?: Record<string, any>): Promise<T> {
    this.startMeasure(name, metadata);
    
    return asyncFunction()
      .then(result => {
        this.endMeasure(name);
        return result;
      })
      .catch(error => {
        this.endMeasure(name);
        throw error;
      });
  }

  measureSync<T>(name: string, syncFunction: () => T, metadata?: Record<string, any>): T {
    this.startMeasure(name, metadata);
    
    try {
      const result = syncFunction();
      this.endMeasure(name);
      return result;
    } catch (error) {
      this.endMeasure(name);
      throw error;
    }
  }

  // Memory monitoring
  getMemoryUsage(): Record<string, number> | null {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
        usedPercentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100
      };
    }
    return null;
  }

  logMemoryUsage(): void {
    const memoryUsage = this.getMemoryUsage();
    if (memoryUsage) {
      logger.info('Memory usage', {
        ...memoryUsage,
        actionType: 'performance',
        performanceType: 'memory'
      });
    }
  }

  // Component performance tracking
  trackComponentRender(componentName: string, renderTime: number): void {
    if (renderTime > 16) { // Longer than one frame (60fps)
      logger.warn('Slow component render', {
        componentName,
        renderTime,
        actionType: 'performance',
        performanceType: 'component'
      });
    }
  }

  // API call tracking
  trackApiCall(method: string, url: string, duration: number, status: number, size?: number): void {
    const level = status >= 400 ? 'error' : duration > 1000 ? 'warn' : 'info';
    
    logger[level](`API ${method} ${url}`, {
      method,
      url,
      duration,
      status,
      size,
      actionType: 'performance',
      performanceType: 'api'
    });
  }

  // Network monitoring
  getConnectionInfo(): Record<string, any> | null {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      return {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData
      };
    }
    return null;
  }

  // Web Vitals integration
  trackWebVitals(metric: WebVitalsMetrics): void {
    logger.info(`Web Vitals: ${metric.name}`, {
      value: metric.value,
      rating: metric.rating,
      delta: metric.delta,
      id: metric.id,
      navigationType: metric.navigationType,
      actionType: 'performance',
      performanceType: 'web_vitals'
    });
  }

  // Configuration
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  // Cleanup
  disconnect(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.metrics.clear();
  }

  // Get all metrics
  getMetrics(): PerformanceMetrics[] {
    return Array.from(this.metrics.values());
  }

  // Clear metrics
  clearMetrics(): void {
    this.metrics.clear();
  }
}

// Create singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Export for testing
export { PerformanceMonitor };

// Utility functions
export function withPerformanceTracking<T extends (...args: any[]) => any>(
  fn: T,
  name: string,
  metadata?: Record<string, any>
): T {
  return ((...args: Parameters<T>) => {
    return performanceMonitor.measureSync(name, () => fn(...args), metadata);
  }) as T;
}

export function withAsyncPerformanceTracking<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  name: string,
  metadata?: Record<string, any>
): T {
  return ((...args: Parameters<T>) => {
    return performanceMonitor.measureAsync(name, () => fn(...args), metadata);
  }) as T;
}