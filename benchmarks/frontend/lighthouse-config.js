// Lighthouse configuration for frontend performance benchmarks
module.exports = {
  extends: 'lighthouse:default',
  settings: {
    // Simulate mobile device
    formFactor: 'mobile',
    throttling: {
      rttMs: 150,
      throughputKbps: 1638.4,
      cpuSlowdownMultiplier: 4,
    },
    screenEmulation: {
      mobile: true,
      width: 360,
      height: 640,
      deviceScaleFactor: 2,
      disabled: false,
    },
    emulatedUserAgent: 'Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4695.0 Mobile Safari/537.36',
  },
  
  // Audit configurations
  passes: [{
    passName: 'defaultPass',
    gatherers: [
      'accessibility',
      'anchor-elements',
      'apple-touch-icon',
      'cache-headers',
      'css-usage',
      'dobetterweb/doctype',
      'dobetterweb/domstats',
      'dobetterweb/js-libraries',
      'dobetterweb/optimized-images',
      'dobetterweb/password-inputs-with-prevented-paste',
      'dobetterweb/response-compression',
      'dobetterweb/tags-blocking-first-paint',
      'font-display',
      'full-page-screenshot',
      'http-redirect',
      'html-without-javascript',
      'image-elements',
      'installable-manifest',
      'js-usage',
      'link-elements',
      'main-document-content',
      'meta-description',
      'meta-robots',
      'metrics',
      'offline',
      'performance-budget',
      'resource-summary',
      'screenshot-thumbnails',
      'script-elements',
      'seo/font-size',
      'seo/tap-targets',
      'service-worker',
      'trace-elements',
      'viewport',
      'web-app-manifest',
    ],
  }],
  
  audits: [
    // Performance
    'first-contentful-paint',
    'largest-contentful-paint',
    'first-meaningful-paint',
    'speed-index',
    'total-blocking-time',
    'max-potential-fid',
    'cumulative-layout-shift',
    'server-response-time',
    'interactive',
    'user-timings',
    'critical-request-chains',
    'redirects',
    'mainthread-work-breakdown',
    'bootup-time',
    'uses-rel-preload',
    'uses-rel-preconnect',
    'font-display',
    'third-party-summary',
    'third-party-facades',
    'lcp-lazy-loaded',
    'uses-passive-event-listeners',
    'no-document-write',
    'long-tasks',
    'non-composited-animations',
    'unsized-images',
    'valid-source-maps',
    'preload-lcp-image',
    
    // Best practices
    'errors-in-console',
    'no-vulnerable-libraries',
    'js-libraries',
    'notification-on-start',
    'geolocation-on-start',
    'inspector-issues',
    'no-unload-listeners',
    
    // Accessibility
    'accessibility/aria-*',
    'accessibility/color-contrast',
    'accessibility/definition-list',
    'accessibility/dlitem',
    'accessibility/document-title',
    'accessibility/duplicate-id-*',
    'accessibility/empty-heading',
    'accessibility/form-field-multiple-labels',
    'accessibility/frame-title',
    'accessibility/heading-order',
    'accessibility/html-has-lang',
    'accessibility/html-lang-valid',
    'accessibility/image-alt',
    'accessibility/input-image-alt',
    'accessibility/label',
    'accessibility/link-name',
    'accessibility/list',
    'accessibility/listitem',
    'accessibility/meta-refresh',
    'accessibility/meta-viewport',
    'accessibility/object-alt',
    'accessibility/tabindex',
    'accessibility/td-headers-attr',
    'accessibility/th-has-data-cells',
    'accessibility/valid-lang',
    'accessibility/video-caption',
    
    // SEO
    'seo/meta-description',
    'seo/font-size',
    'seo/link-text',
    'seo/is-crawlable',
    'seo/robots-txt',
    'seo/tap-targets',
    'seo/hreflang',
    'seo/canonical',
    'seo/structured-data',
  ],
  
  // Custom categories with weights
  categories: {
    performance: {
      title: 'Performance',
      description: 'MAMS frontend performance metrics',
      auditRefs: [
        {id: 'first-contentful-paint', weight: 10, group: 'metrics'},
        {id: 'largest-contentful-paint', weight: 25, group: 'metrics'},
        {id: 'first-meaningful-paint', weight: 0, group: 'metrics'},
        {id: 'speed-index', weight: 10, group: 'metrics'},
        {id: 'total-blocking-time', weight: 30, group: 'metrics'},
        {id: 'max-potential-fid', weight: 0, group: 'metrics'},
        {id: 'cumulative-layout-shift', weight: 25, group: 'metrics'},
        {id: 'interactive', weight: 0, group: 'metrics'},
        
        // Additional performance audits
        {id: 'server-response-time', weight: 0},
        {id: 'redirects', weight: 0},
        {id: 'mainthread-work-breakdown', weight: 0},
        {id: 'bootup-time', weight: 0},
        {id: 'uses-rel-preload', weight: 0},
        {id: 'uses-rel-preconnect', weight: 0},
        {id: 'font-display', weight: 0},
        {id: 'third-party-summary', weight: 0},
      ],
    },
    
    // Custom MAMS-specific category
    'mams-performance': {
      title: 'MAMS Specific Performance',
      description: 'Performance metrics specific to media asset management',
      auditRefs: [
        {id: 'user-timings', weight: 0},
        {id: 'critical-request-chains', weight: 0},
        {id: 'long-tasks', weight: 0},
        {id: 'unsized-images', weight: 0},
        {id: 'preload-lcp-image', weight: 0},
      ],
    },
  },
  
  // Performance budgets
  budgets: [
    {
      path: '/*',
      resourceSizes: [
        {
          resourceType: 'script',
          budget: 300, // 300KB for scripts
        },
        {
          resourceType: 'stylesheet',
          budget: 150, // 150KB for styles
        },
        {
          resourceType: 'image',
          budget: 500, // 500KB for images
        },
        {
          resourceType: 'font',
          budget: 100, // 100KB for fonts
        },
        {
          resourceType: 'total',
          budget: 1500, // 1.5MB total
        },
      ],
      resourceCounts: [
        {
          resourceType: 'script',
          budget: 10,
        },
        {
          resourceType: 'stylesheet',
          budget: 5,
        },
        {
          resourceType: 'font',
          budget: 5,
        },
        {
          resourceType: 'third-party',
          budget: 10,
        },
      ],
      timings: [
        {
          metric: 'interactive',
          budget: 3000, // 3s
        },
        {
          metric: 'first-contentful-paint',
          budget: 1500, // 1.5s
        },
        {
          metric: 'max-potential-fid',
          budget: 100, // 100ms
        },
      ],
    },
  ],
};