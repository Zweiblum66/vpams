/**
 * Centralized lazy imports for code splitting
 */

import { lazy, LazyExoticComponent, ComponentType } from 'react';

// Lazy load heavy components
export const VideoPlayer = lazy(() => 
  import(/* webpackChunkName: "video-player" */ '../components/media/VideoPlayer')
);

export const AudioPlayer = lazy(() => 
  import(/* webpackChunkName: "audio-player" */ '../components/media/AudioPlayer')
);

export const ImageViewer = lazy(() => 
  import(/* webpackChunkName: "image-viewer" */ '../components/media/ImageViewer')
);

export const Timeline = lazy(() => 
  import(/* webpackChunkName: "timeline" */ '../components/timeline/Timeline')
);

export const SearchAdvanced = lazy(() => 
  import(/* webpackChunkName: "search-advanced" */ '../components/search/SearchAdvanced')
);

export const AssetUploader = lazy(() => 
  import(/* webpackChunkName: "asset-uploader" */ '../components/upload/AssetUploader')
);

export const WorkflowDesigner = lazy(() => 
  import(/* webpackChunkName: "workflow-designer" */ '../components/workflow/WorkflowDesigner')
);

export const Analytics = lazy(() => 
  import(/* webpackChunkName: "analytics" */ '../pages/Analytics')
);

export const AdminPanel = lazy(() => 
  import(/* webpackChunkName: "admin" */ '../pages/admin/AdminPanel')
);

export const UserSettings = lazy(() => 
  import(/* webpackChunkName: "settings" */ '../pages/UserSettings')
);

// Lazy load heavy libraries
export const loadVideoJS = () => 
  import(/* webpackChunkName: "videojs" */ 'video.js');

export const loadWaveSurfer = () => 
  import(/* webpackChunkName: "wavesurfer" */ 'wavesurfer.js');

export const loadCharts = () => 
  import(/* webpackChunkName: "recharts" */ 'recharts');

export const loadPdfViewer = () => 
  import(/* webpackChunkName: "pdf-viewer" */ 'react-pdf');

export const loadMarkdownEditor = () => 
  import(/* webpackChunkName: "md-editor" */ '@uiw/react-md-editor');

export const loadExcelViewer = () => 
  import(/* webpackChunkName: "excel-viewer" */ 'react-excel-renderer');

export const loadColorPicker = () => 
  import(/* webpackChunkName: "color-picker" */ 'react-color');

export const loadDatePicker = () => 
  import(/* webpackChunkName: "date-picker" */ '@mui/x-date-pickers');

// Helper to preload components
export const preloadComponent = (
  component: LazyExoticComponent<ComponentType<any>>
): void => {
  // @ts-ignore - accessing internal _ctor
  const Component = component._ctor || component;
  if (typeof Component === 'function') {
    Component();
  }
};

// Preload critical components based on route
export const preloadRouteComponents = (pathname: string): void => {
  // Preload components likely to be needed based on current route
  switch (true) {
    case pathname.includes('/assets'):
      preloadComponent(VideoPlayer);
      preloadComponent(AudioPlayer);
      preloadComponent(ImageViewer);
      break;
      
    case pathname.includes('/search'):
      preloadComponent(SearchAdvanced);
      break;
      
    case pathname.includes('/timeline'):
    case pathname.includes('/shotlist'):
      preloadComponent(Timeline);
      break;
      
    case pathname.includes('/workflow'):
      preloadComponent(WorkflowDesigner);
      break;
      
    case pathname.includes('/analytics'):
      preloadComponent(Analytics);
      loadCharts(); // Preload chart library
      break;
      
    case pathname.includes('/admin'):
      preloadComponent(AdminPanel);
      break;
      
    case pathname.includes('/settings'):
      preloadComponent(UserSettings);
      break;
  }
};

// Intersection Observer for preloading components when links are visible
export const setupLinkPreloading = (): void => {
  if (!('IntersectionObserver' in window)) return;
  
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const link = entry.target as HTMLAnchorElement;
          const href = link.getAttribute('href');
          if (href) {
            preloadRouteComponents(href);
          }
        }
      });
    },
    { rootMargin: '50px' }
  );
  
  // Observe all internal links
  document.querySelectorAll('a[href^="/"]').forEach((link) => {
    observer.observe(link);
  });
  
  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    observer.disconnect();
  });
};

// Resource hints for critical resources
export const addResourceHints = (): void => {
  const head = document.head;
  
  // Preconnect to CDN
  const preconnectCDN = document.createElement('link');
  preconnectCDN.rel = 'preconnect';
  preconnectCDN.href = 'https://cdn.mams.example.com';
  preconnectCDN.crossOrigin = 'anonymous';
  head.appendChild(preconnectCDN);
  
  // Preconnect to API
  const preconnectAPI = document.createElement('link');
  preconnectAPI.rel = 'preconnect';
  preconnectAPI.href = process.env.VITE_API_URL || 'https://api.mams.example.com';
  head.appendChild(preconnectAPI);
  
  // DNS prefetch for external services
  const dnsPrefetch = [
    'https://fonts.googleapis.com',
    'https://fonts.gstatic.com',
  ];
  
  dnsPrefetch.forEach(url => {
    const link = document.createElement('link');
    link.rel = 'dns-prefetch';
    link.href = url;
    head.appendChild(link);
  });
};

// Progressive image loading
export const loadImage = (src: string, placeholder?: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    
    // Load placeholder immediately if provided
    if (placeholder) {
      resolve(placeholder);
    }
    
    img.onload = () => resolve(src);
    img.onerror = reject;
    img.src = src;
  });
};

// Lazy load images with Intersection Observer
export const lazyLoadImages = (): void => {
  if (!('IntersectionObserver' in window)) return;
  
  const imageObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target as HTMLImageElement;
          const src = img.dataset.src;
          
          if (src) {
            loadImage(src, img.src).then(loadedSrc => {
              img.src = loadedSrc;
              img.classList.add('loaded');
              imageObserver.unobserve(img);
            });
          }
        }
      });
    },
    { rootMargin: '100px' }
  );
  
  // Observe all lazy images
  document.querySelectorAll('img[data-src]').forEach((img) => {
    imageObserver.observe(img);
  });
};