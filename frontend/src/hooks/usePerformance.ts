import { useCallback, useEffect, useRef } from 'react';
import { performanceMonitor } from '../utils/performance';

export interface PerformanceHookOptions {
  trackRender?: boolean;
  trackEffects?: boolean;
  componentName?: string;
  metadata?: Record<string, any>;
}

export const usePerformance = (options: PerformanceHookOptions = {}) => {
  const {
    trackRender = false,
    trackEffects = false,
    componentName = 'UnknownComponent',
    metadata = {}
  } = options;

  const renderStartRef = useRef<number>(0);
  const mountStartRef = useRef<number>(0);
  const effectTimersRef = useRef<Map<string, number>>(new Map());

  // Track component render time
  useEffect(() => {
    if (trackRender) {
      const renderTime = performance.now() - renderStartRef.current;
      performanceMonitor.trackComponentRender(componentName, renderTime);
    }
  });

  // Track component mount time
  useEffect(() => {
    if (trackEffects) {
      const mountTime = performance.now() - mountStartRef.current;
      performanceMonitor.startMeasure(`${componentName}-mount`, {
        ...metadata,
        mountTime
      });
    }

    return () => {
      if (trackEffects) {
        performanceMonitor.endMeasure(`${componentName}-mount`);
      }
    };
  }, [componentName, trackEffects, metadata]);

  // Initialize render tracking
  if (trackRender) {
    renderStartRef.current = performance.now();
  }

  // Initialize mount tracking
  if (trackEffects && mountStartRef.current === 0) {
    mountStartRef.current = performance.now();
  }

  // Performance measurement functions
  const startMeasure = useCallback((name: string, measureMetadata?: Record<string, any>) => {
    const fullName = `${componentName}-${name}`;
    performanceMonitor.startMeasure(fullName, {
      ...metadata,
      ...measureMetadata,
      component: componentName
    });
    return fullName;
  }, [componentName, metadata]);

  const endMeasure = useCallback((name: string) => {
    const fullName = name.startsWith(componentName) ? name : `${componentName}-${name}`;
    return performanceMonitor.endMeasure(fullName);
  }, [componentName]);

  const measureAsync = useCallback(async <T>(
    name: string,
    asyncFunction: () => Promise<T>,
    measureMetadata?: Record<string, any>
  ): Promise<T> => {
    const fullName = `${componentName}-${name}`;
    return performanceMonitor.measureAsync(fullName, asyncFunction, {
      ...metadata,
      ...measureMetadata,
      component: componentName
    });
  }, [componentName, metadata]);

  const measureSync = useCallback(<T>(
    name: string,
    syncFunction: () => T,
    measureMetadata?: Record<string, any>
  ): T => {
    const fullName = `${componentName}-${name}`;
    return performanceMonitor.measureSync(fullName, syncFunction, {
      ...metadata,
      ...measureMetadata,
      component: componentName
    });
  }, [componentName, metadata]);

  // Effect timing
  const startEffect = useCallback((effectName: string) => {
    const startTime = performance.now();
    effectTimersRef.current.set(effectName, startTime);
  }, []);

  const endEffect = useCallback((effectName: string) => {
    const startTime = effectTimersRef.current.get(effectName);
    if (startTime) {
      const duration = performance.now() - startTime;
      performanceMonitor.startMeasure(`${componentName}-effect-${effectName}`, {
        ...metadata,
        effectName,
        duration
      });
      performanceMonitor.endMeasure(`${componentName}-effect-${effectName}`);
      effectTimersRef.current.delete(effectName);
    }
  }, [componentName, metadata]);

  return {
    startMeasure,
    endMeasure,
    measureAsync,
    measureSync,
    startEffect,
    endEffect,
  };
};

// Hook for API performance tracking
export const useApiPerformance = () => {
  const trackApiCall = useCallback((
    method: string,
    url: string,
    startTime: number,
    status: number,
    size?: number
  ) => {
    const duration = performance.now() - startTime;
    performanceMonitor.trackApiCall(method, url, duration, status, size);
  }, []);

  const wrapApiCall = useCallback(async <T>(
    method: string,
    url: string,
    apiCall: () => Promise<T>
  ): Promise<T> => {
    const startTime = performance.now();
    
    try {
      const result = await apiCall();
      trackApiCall(method, url, startTime, 200);
      return result;
    } catch (error: any) {
      const status = error?.response?.status || 500;
      trackApiCall(method, url, startTime, status);
      throw error;
    }
  }, [trackApiCall]);

  return {
    trackApiCall,
    wrapApiCall,
  };
};

// Hook for memory monitoring
export const useMemoryMonitoring = (intervalMs: number = 30000) => {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const startMonitoring = () => {
      performanceMonitor.logMemoryUsage();
      
      intervalRef.current = setInterval(() => {
        performanceMonitor.logMemoryUsage();
      }, intervalMs);
    };

    const stopMonitoring = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    // Start monitoring when component mounts
    startMonitoring();

    // Cleanup on unmount
    return stopMonitoring;
  }, [intervalMs]);

  const getMemoryUsage = useCallback(() => {
    return performanceMonitor.getMemoryUsage();
  }, []);

  return {
    getMemoryUsage,
  };
};

// Hook for Web Vitals tracking
export const useWebVitals = () => {
  useEffect(() => {
    // Dynamically import web-vitals to avoid bundle size impact
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS((metric) => {
        performanceMonitor.trackWebVitals({
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          delta: metric.delta,
          id: metric.id,
          navigationType: metric.navigationType
        });
      });

      getFID((metric) => {
        performanceMonitor.trackWebVitals({
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          delta: metric.delta,
          id: metric.id,
          navigationType: metric.navigationType
        });
      });

      getFCP((metric) => {
        performanceMonitor.trackWebVitals({
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          delta: metric.delta,
          id: metric.id,
          navigationType: metric.navigationType
        });
      });

      getLCP((metric) => {
        performanceMonitor.trackWebVitals({
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          delta: metric.delta,
          id: metric.id,
          navigationType: metric.navigationType
        });
      });

      getTTFB((metric) => {
        performanceMonitor.trackWebVitals({
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          delta: metric.delta,
          id: metric.id,
          navigationType: metric.navigationType
        });
      });
    }).catch((error) => {
      console.debug('Web Vitals not available:', error);
    });
  }, []);
};

// Hook for component-specific performance tracking
export const useComponentPerformance = (componentName: string) => {
  const renderCount = useRef(0);
  const mountTime = useRef(0);
  
  // Track render count
  renderCount.current++;
  
  // Track mount time
  useEffect(() => {
    mountTime.current = performance.now();
    
    return () => {
      const unmountTime = performance.now();
      const totalMountTime = unmountTime - mountTime.current;
      
      performanceMonitor.startMeasure(`${componentName}-lifecycle`, {
        component: componentName,
        renderCount: renderCount.current,
        totalMountTime,
        actionType: 'performance',
        performanceType: 'component_lifecycle'
      });
      performanceMonitor.endMeasure(`${componentName}-lifecycle`);
    };
  }, [componentName]);

  // Track excessive re-renders
  useEffect(() => {
    if (renderCount.current > 10) {
      performanceMonitor.startMeasure(`${componentName}-excessive-renders`, {
        component: componentName,
        renderCount: renderCount.current,
        actionType: 'performance',
        performanceType: 'excessive_renders'
      });
      performanceMonitor.endMeasure(`${componentName}-excessive-renders`);
    }
  }, [componentName]);

  return {
    renderCount: renderCount.current,
  };
};