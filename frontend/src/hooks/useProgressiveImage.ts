import { useState, useEffect } from 'react';

interface ProgressiveImageOptions {
  /** Low quality placeholder image URL */
  placeholder?: string;
  /** Blur radius for placeholder (in pixels) */
  blurRadius?: number;
  /** Transition duration (in ms) */
  transitionDuration?: number;
  /** Whether to use intersection observer */
  lazy?: boolean;
  /** Root margin for intersection observer */
  rootMargin?: string;
  /** Callback when image loads */
  onLoad?: () => void;
  /** Callback when image fails to load */
  onError?: (error: Error) => void;
}

interface ProgressiveImageState {
  /** Current image source */
  currentSrc: string;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Whether the high quality image is loaded */
  isLoaded: boolean;
  /** Blur value for CSS filter */
  blur: number;
  /** Reference to attach to image element */
  ref: React.RefObject<HTMLImageElement>;
}

/**
 * Hook for progressive image loading with lazy loading support
 */
export function useProgressiveImage(
  src: string,
  options: ProgressiveImageOptions = {}
): ProgressiveImageState {
  const {
    placeholder,
    blurRadius = 20,
    transitionDuration = 300,
    lazy = true,
    rootMargin = '50px',
    onLoad,
    onError,
  } = options;

  const [currentSrc, setCurrentSrc] = useState(placeholder || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [blur, setBlur] = useState(placeholder ? blurRadius : 0);
  const [shouldLoad, setShouldLoad] = useState(!lazy);
  
  const imageRef = React.useRef<HTMLImageElement>(null);

  // Intersection observer for lazy loading
  useEffect(() => {
    if (!lazy || !imageRef.current) {
      setShouldLoad(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );

    observer.observe(imageRef.current);

    return () => observer.disconnect();
  }, [lazy, rootMargin]);

  // Load high quality image
  useEffect(() => {
    if (!shouldLoad || !src) return;

    setLoading(true);
    setError(null);

    const img = new Image();
    
    const handleLoad = () => {
      // Start transition
      setCurrentSrc(src);
      
      // Animate blur removal
      let currentBlur = placeholder ? blurRadius : 0;
      const blurStep = currentBlur / (transitionDuration / 16); // 60fps
      
      const animateBlur = () => {
        currentBlur = Math.max(0, currentBlur - blurStep);
        setBlur(currentBlur);
        
        if (currentBlur > 0) {
          requestAnimationFrame(animateBlur);
        } else {
          setIsLoaded(true);
          setLoading(false);
          onLoad?.();
        }
      };
      
      requestAnimationFrame(animateBlur);
    };
    
    const handleError = () => {
      const err = new Error(`Failed to load image: ${src}`);
      setError(err);
      setLoading(false);
      onError?.(err);
    };

    img.addEventListener('load', handleLoad);
    img.addEventListener('error', handleError);
    img.src = src;

    return () => {
      img.removeEventListener('load', handleLoad);
      img.removeEventListener('error', handleError);
    };
  }, [src, shouldLoad, placeholder, blurRadius, transitionDuration, onLoad, onError]);

  return {
    currentSrc,
    loading,
    error,
    isLoaded,
    blur,
    ref: imageRef,
  };
}

/**
 * Hook for loading multiple image sizes (responsive images)
 */
export function useResponsiveImage(
  sources: {
    small?: string;
    medium?: string;
    large?: string;
    original: string;
  },
  breakpoints: {
    small?: number;
    medium?: number;
    large?: number;
  } = {
    small: 640,
    medium: 1024,
    large: 1920,
  }
): string {
  const [selectedSrc, setSelectedSrc] = useState(sources.original);

  useEffect(() => {
    const updateImageSource = () => {
      const width = window.innerWidth;
      
      if (sources.small && width <= breakpoints.small!) {
        setSelectedSrc(sources.small);
      } else if (sources.medium && width <= breakpoints.medium!) {
        setSelectedSrc(sources.medium);
      } else if (sources.large && width <= breakpoints.large!) {
        setSelectedSrc(sources.large);
      } else {
        setSelectedSrc(sources.original);
      }
    };

    updateImageSource();

    window.addEventListener('resize', updateImageSource);
    return () => window.removeEventListener('resize', updateImageSource);
  }, [sources, breakpoints]);

  return selectedSrc;
}

/**
 * Hook for preloading images
 */
export function useImagePreloader(
  urls: string[],
  options: {
    sequential?: boolean;
    onProgress?: (loaded: number, total: number) => void;
    onComplete?: () => void;
  } = {}
): {
  loading: boolean;
  progress: number;
  errors: Record<string, Error>;
} {
  const [loading, setLoading] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const [errors, setErrors] = useState<Record<string, Error>>({});

  useEffect(() => {
    if (urls.length === 0) return;

    setLoading(true);
    setLoadedCount(0);
    setErrors({});

    let mounted = true;
    let loaded = 0;
    const errorMap: Record<string, Error> = {};

    const loadImage = (url: string): Promise<void> => {
      return new Promise((resolve) => {
        const img = new Image();
        
        img.onload = () => {
          if (mounted) {
            loaded++;
            setLoadedCount(loaded);
            options.onProgress?.(loaded, urls.length);
          }
          resolve();
        };
        
        img.onerror = () => {
          if (mounted) {
            errorMap[url] = new Error(`Failed to load: ${url}`);
            loaded++;
            setLoadedCount(loaded);
            options.onProgress?.(loaded, urls.length);
          }
          resolve();
        };
        
        img.src = url;
      });
    };

    const loadAll = async () => {
      if (options.sequential) {
        // Load images one by one
        for (const url of urls) {
          await loadImage(url);
        }
      } else {
        // Load all images in parallel
        await Promise.all(urls.map(loadImage));
      }

      if (mounted) {
        setErrors(errorMap);
        setLoading(false);
        options.onComplete?.();
      }
    };

    loadAll();

    return () => {
      mounted = false;
    };
  }, [urls, options.sequential]);

  return {
    loading,
    progress: urls.length > 0 ? (loadedCount / urls.length) * 100 : 0,
    errors,
  };
}

export default useProgressiveImage;