import React, { lazy, Suspense, ComponentType } from 'react';
import { Box, CircularProgress, Skeleton } from '@mui/material';

/**
 * Options for lazy loading components
 */
export interface LazyLoadOptions {
  /** Custom loading component */
  fallback?: React.ReactNode;
  /** Delay before showing loading indicator (ms) */
  delay?: number;
  /** Whether to retry on failure */
  retry?: boolean;
  /** Number of retry attempts */
  retryAttempts?: number;
  /** Whether to preload the component */
  preload?: boolean;
}

/**
 * Default loading component
 */
export const DefaultLoadingComponent: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '200px',
      width: '100%',
    }}
  >
    <CircularProgress />
  </Box>
);

/**
 * Skeleton loading component for list items
 */
export const SkeletonLoadingComponent: React.FC<{ count?: number }> = ({ count = 3 }) => (
  <Box sx={{ p: 2 }}>
    {Array.from({ length: count }).map((_, index) => (
      <Skeleton
        key={index}
        variant="rectangular"
        height={80}
        sx={{ mb: 2, borderRadius: 1 }}
      />
    ))}
  </Box>
);

/**
 * Create a lazy loaded component with error handling and retry logic
 */
export function createLazyComponent<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  options: LazyLoadOptions = {}
): React.LazyExoticComponent<T> {
  const {
    retry = true,
    retryAttempts = 3,
    preload = false,
  } = options;

  let attempts = 0;

  const lazyComponentWithRetry = () => {
    return importFunc().catch((error) => {
      attempts++;
      if (retry && attempts < retryAttempts) {
        // Retry after a delay
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve(lazyComponentWithRetry());
          }, 1000 * attempts); // Exponential backoff
        });
      }
      throw error;
    });
  };

  const LazyComponent = lazy(lazyComponentWithRetry as () => Promise<{ default: T }>);

  // Preload the component if requested
  if (preload) {
    importFunc();
  }

  return LazyComponent;
}

/**
 * Wrapper component for lazy loaded components with loading state
 */
export const LazyLoadWrapper: React.FC<{
  children: React.ReactNode;
  fallback?: React.ReactNode;
  delay?: number;
}> = ({ children, fallback, delay = 200 }) => {
  const [showLoading, setShowLoading] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setShowLoading(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <Suspense fallback={showLoading ? (fallback || <DefaultLoadingComponent />) : null}>
      {children}
    </Suspense>
  );
};

/**
 * HOC to add lazy loading to any component
 */
export function withLazyLoad<P extends object>(
  Component: ComponentType<P>,
  options: LazyLoadOptions = {}
): React.FC<P> {
  return (props: P) => (
    <LazyLoadWrapper fallback={options.fallback} delay={options.delay}>
      <Component {...props} />
    </LazyLoadWrapper>
  );
}

/**
 * Hook for lazy loading with intersection observer
 */
export function useLazyLoad(
  ref: React.RefObject<HTMLElement>,
  onIntersect: () => void,
  options?: IntersectionObserverInit
) {
  React.useEffect(() => {
    if (!ref.current) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        onIntersect();
        observer.disconnect();
      }
    }, options);

    observer.observe(ref.current);

    return () => observer.disconnect();
  }, [ref, onIntersect, options]);
}

/**
 * Component for lazy loading images
 */
export const LazyImage: React.FC<{
  src: string;
  alt: string;
  placeholder?: string;
  className?: string;
  style?: React.CSSProperties;
  onLoad?: () => void;
  onError?: () => void;
}> = ({ src, alt, placeholder, className, style, onLoad, onError }) => {
  const [imageSrc, setImageSrc] = React.useState(placeholder || '');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const imgRef = React.useRef<HTMLImageElement>(null);

  useLazyLoad(
    imgRef,
    () => {
      const img = new Image();
      img.src = src;
      img.onload = () => {
        setImageSrc(src);
        setLoading(false);
        onLoad?.();
      };
      img.onerror = () => {
        setError(true);
        setLoading(false);
        onError?.();
      };
    },
    { rootMargin: '50px' }
  );

  if (error) {
    return (
      <Box
        className={className}
        style={style}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'grey.200',
          color: 'grey.600',
        }}
      >
        Failed to load image
      </Box>
    );
  }

  return (
    <>
      {loading && placeholder && (
        <Skeleton
          variant="rectangular"
          className={className}
          style={style}
        />
      )}
      <img
        ref={imgRef}
        src={imageSrc}
        alt={alt}
        className={className}
        style={{
          ...style,
          display: loading ? 'none' : 'block',
        }}
      />
    </>
  );
};

/**
 * Preload a component to improve perceived performance
 */
export function preloadComponent(
  importFunc: () => Promise<any>
): void {
  importFunc();
}

/**
 * Batch preload multiple components
 */
export function preloadComponents(
  importFuncs: Array<() => Promise<any>>
): void {
  importFuncs.forEach(preloadComponent);
}

/**
 * Route-based preloading strategy
 */
export const routePreloadMap: Record<string, () => Promise<any>> = {};

export function registerRoutePreload(
  route: string,
  importFunc: () => Promise<any>
): void {
  routePreloadMap[route] = importFunc;
}

export function preloadRoute(route: string): void {
  const importFunc = routePreloadMap[route];
  if (importFunc) {
    preloadComponent(importFunc);
  }
}

/**
 * Hook to preload components based on user interaction
 */
export function usePreloadOnHover(
  importFunc: () => Promise<any>
): {
  onMouseEnter: () => void;
} {
  const preloaded = React.useRef(false);

  const handleMouseEnter = React.useCallback(() => {
    if (!preloaded.current) {
      preloadComponent(importFunc);
      preloaded.current = true;
    }
  }, [importFunc]);

  return { onMouseEnter: handleMouseEnter };
}