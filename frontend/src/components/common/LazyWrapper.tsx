/**
 * Wrapper component for lazy-loaded components with loading states
 */

import React, { Suspense, ReactNode, Component, ErrorInfo } from 'react';
import { Box, CircularProgress, Alert, Skeleton } from '@mui/material';

interface LazyWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
  error?: ReactNode;
  minHeight?: number | string;
  skeleton?: 'text' | 'rectangular' | 'circular' | 'custom';
  skeletonCount?: number;
  retry?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  retryCount: number;
}

// Error boundary for lazy components
class LazyErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode; retry?: boolean },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, retryCount: 0 };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error, retryCount: 0 };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Lazy component failed to load:', error, errorInfo);
    
    // Report to monitoring service
    if (window.gtag) {
      window.gtag('event', 'exception', {
        description: `Lazy load error: ${error.message}`,
        fatal: false,
      });
    }
  }

  handleRetry = () => {
    this.setState(state => ({
      hasError: false,
      error: undefined,
      retryCount: state.retryCount + 1
    }));
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Alert 
          severity="warning" 
          action={
            this.props.retry && this.state.retryCount < 3 ? (
              <button onClick={this.handleRetry}>
                Retry ({3 - this.state.retryCount} left)
              </button>
            ) : undefined
          }
        >
          Failed to load component. {this.state.error?.message}
        </Alert>
      );
    }

    return this.props.children;
  }
}

// Skeleton loaders for different component types
const SkeletonLoader: React.FC<{
  variant: 'text' | 'rectangular' | 'circular' | 'custom';
  count: number;
  height?: number | string;
}> = ({ variant, count, height = 40 }) => {
  const skeletons = [];
  
  for (let i = 0; i < count; i++) {
    switch (variant) {
      case 'text':
        skeletons.push(
          <Skeleton key={i} variant="text" height={height} sx={{ mb: 1 }} />
        );
        break;
        
      case 'rectangular':
        skeletons.push(
          <Skeleton key={i} variant="rectangular" height={height} sx={{ mb: 1 }} />
        );
        break;
        
      case 'circular':
        skeletons.push(
          <Skeleton key={i} variant="circular" width={height} height={height} sx={{ mb: 1 }} />
        );
        break;
        
      case 'custom':
        // Custom skeleton for complex layouts
        skeletons.push(
          <Box key={i} sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="60%" />
                <Skeleton variant="text" width="40%" />
              </Box>
            </Box>
            <Skeleton variant="rectangular" height={200} />
          </Box>
        );
        break;
    }
  }
  
  return <>{skeletons}</>;
};

// Main wrapper component
export const LazyWrapper: React.FC<LazyWrapperProps> = ({
  children,
  fallback,
  error,
  minHeight = 100,
  skeleton = 'rectangular',
  skeletonCount = 1,
  retry = true,
}) => {
  const defaultFallback = fallback || (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight,
        p: 2,
      }}
    >
      <SkeletonLoader 
        variant={skeleton} 
        count={skeletonCount} 
        height={typeof minHeight === 'number' ? minHeight / skeletonCount : '100px'} 
      />
    </Box>
  );

  return (
    <LazyErrorBoundary fallback={error} retry={retry}>
      <Suspense fallback={defaultFallback}>
        {children}
      </Suspense>
    </LazyErrorBoundary>
  );
};

// Specialized wrappers for common use cases
export const LazyVideoPlayer: React.FC<{ children: ReactNode }> = ({ children }) => (
  <LazyWrapper
    skeleton="rectangular"
    minHeight={400}
    skeletonCount={1}
  >
    {children}
  </LazyWrapper>
);

export const LazyTimeline: React.FC<{ children: ReactNode }> = ({ children }) => (
  <LazyWrapper
    skeleton="custom"
    minHeight={300}
    skeletonCount={3}
  >
    {children}
  </LazyWrapper>
);

export const LazyDashboard: React.FC<{ children: ReactNode }> = ({ children }) => (
  <LazyWrapper
    skeleton="rectangular"
    minHeight={200}
    skeletonCount={4}
  >
    {children}
  </LazyWrapper>
);

export const LazyForm: React.FC<{ children: ReactNode }> = ({ children }) => (
  <LazyWrapper
    skeleton="text"
    minHeight={300}
    skeletonCount={6}
  >
    {children}
  </LazyWrapper>
);

// Hook for progressive loading
export const useProgressiveLoading = (steps: string[]) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [loadedSteps, setLoadedSteps] = React.useState<Set<number>>(new Set([0]));

  const loadNextStep = React.useCallback(() => {
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      setLoadedSteps(prev => new Set([...prev, nextStep]));
    }
  }, [currentStep, steps.length]);

  const isStepLoaded = React.useCallback((step: number) => {
    return loadedSteps.has(step);
  }, [loadedSteps]);

  return {
    currentStep,
    loadNextStep,
    isStepLoaded,
    isComplete: currentStep === steps.length - 1,
    progress: ((currentStep + 1) / steps.length) * 100,
  };
};

// Performance monitoring for lazy components
export const withLoadingMetrics = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName: string
) => {
  return React.forwardRef<any, P>((props, ref) => {
    React.useEffect(() => {
      const startTime = performance.now();
      
      return () => {
        const loadTime = performance.now() - startTime;
        
        // Report loading time
        if ('performance' in window && 'measure' in window.performance) {
          performance.mark(`${componentName}-load-end`);
          performance.measure(
            `${componentName}-load-time`,
            `${componentName}-load-start`,
            `${componentName}-load-end`
          );
        }
        
        // Send to analytics
        if (window.gtag) {
          window.gtag('event', 'timing_complete', {
            name: `${componentName}_load`,
            value: Math.round(loadTime),
          });
        }
        
        console.debug(`${componentName} loaded in ${loadTime.toFixed(2)}ms`);
      };
    }, []);
    
    // Mark start time
    React.useLayoutEffect(() => {
      if ('performance' in window) {
        performance.mark(`${componentName}-load-start`);
      }
    }, []);

    return <WrappedComponent {...props} ref={ref} />;
  });
};

export default LazyWrapper;