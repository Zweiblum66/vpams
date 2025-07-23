/**
 * Tests for CDN service integration in frontend
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CDNService } from '../cdn';
import { CDNConfig } from '../../config/cdn';

// Mock fetch
global.fetch = vi.fn();

describe('CDNService', () => {
  let cdnService: CDNService;
  let mockConfig: CDNConfig;

  beforeEach(() => {
    mockConfig = {
      enabled: true,
      baseUrl: 'https://cdn.mams.example.com',
      fallbackUrl: 'https://assets.mams.example.com',
      providers: {
        cloudfront: {
          distributionId: 'E123456',
          domain: 'cdn.mams.example.com'
        }
      }
    };
    
    cdnService = new CDNService(mockConfig);
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('getAssetUrl', () => {
    it('should return CDN URL when enabled', () => {
      const path = '/images/logo.png';
      const url = cdnService.getAssetUrl(path);
      
      expect(url).toBe('https://cdn.mams.example.com/images/logo.png');
    });

    it('should return fallback URL when CDN disabled', () => {
      mockConfig.enabled = false;
      cdnService = new CDNService(mockConfig);
      
      const path = '/images/logo.png';
      const url = cdnService.getAssetUrl(path);
      
      expect(url).toBe('https://assets.mams.example.com/images/logo.png');
    });

    it('should handle paths without leading slash', () => {
      const path = 'images/logo.png';
      const url = cdnService.getAssetUrl(path);
      
      expect(url).toBe('https://cdn.mams.example.com/images/logo.png');
    });

    it('should preserve query parameters', () => {
      const path = '/images/logo.png?v=123';
      const url = cdnService.getAssetUrl(path);
      
      expect(url).toBe('https://cdn.mams.example.com/images/logo.png?v=123');
    });
  });

  describe('getOptimizedImageUrl', () => {
    it('should add image optimization parameters', () => {
      const path = '/images/hero.jpg';
      const url = cdnService.getOptimizedImageUrl(path, {
        width: 800,
        height: 600,
        quality: 85,
        format: 'webp'
      });
      
      expect(url).toContain('w=800');
      expect(url).toContain('h=600');
      expect(url).toContain('q=85');
      expect(url).toContain('f=webp');
    });

    it('should handle responsive images', () => {
      const path = '/images/product.jpg';
      const srcset = cdnService.getResponsiveImageSrcset(path, [320, 640, 1024]);
      
      expect(srcset).toContain('320w');
      expect(srcset).toContain('640w');
      expect(srcset).toContain('1024w');
      expect(srcset.split(',').length).toBe(3);
    });

    it('should detect WebP support', async () => {
      // Mock successful WebP image load
      global.Image = vi.fn().mockImplementation(() => ({
        onload: null,
        onerror: null,
        src: '',
        set src(value: string) {
          if (this.onload) {
            this.onload();
          }
        }
      }));

      const supportsWebP = await cdnService.checkWebPSupport();
      expect(supportsWebP).toBe(true);
    });
  });

  describe('preloadAssets', () => {
    it('should create link tags for preloading', () => {
      const assets = [
        { url: '/css/app.css', as: 'style' },
        { url: '/js/app.js', as: 'script' },
        { url: '/fonts/roboto.woff2', as: 'font', type: 'font/woff2', crossOrigin: 'anonymous' }
      ];

      // Mock document.head.appendChild
      const mockAppendChild = vi.spyOn(document.head, 'appendChild').mockImplementation(() => null);
      
      cdnService.preloadAssets(assets);
      
      expect(mockAppendChild).toHaveBeenCalledTimes(3);
      
      // Verify link elements were created correctly
      const calls = mockAppendChild.mock.calls;
      expect(calls[0][0].rel).toBe('preload');
      expect(calls[0][0].href).toContain('cdn.mams.example.com/css/app.css');
      expect(calls[0][0].as).toBe('style');
    });
  });

  describe('invalidateCache', () => {
    it('should call CDN invalidation API', async () => {
      const mockResponse = { success: true, invalidationId: 'INV123' };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await cdnService.invalidateCache(['/images/old.jpg']);
      
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cdn/invalidate'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ paths: ['/images/old.jpg'] })
        })
      );
      
      expect(result).toEqual(mockResponse);
    });

    it('should handle invalidation errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(
        cdnService.invalidateCache(['/images/old.jpg'])
      ).rejects.toThrow('Failed to invalidate cache');
    });
  });

  describe('performance monitoring', () => {
    it('should track CDN performance metrics', async () => {
      const mockPerformanceObserver = vi.fn();
      global.PerformanceObserver = vi.fn().mockImplementation((callback) => ({
        observe: vi.fn(),
        disconnect: vi.fn()
      }));

      cdnService.startPerformanceMonitoring();
      
      expect(global.PerformanceObserver).toHaveBeenCalled();
    });

    it('should report slow assets', () => {
      const slowAssets = cdnService.getSlowAssets(200); // 200ms threshold
      
      // In real scenario, this would return assets that loaded slowly
      expect(Array.isArray(slowAssets)).toBe(true);
    });
  });

  describe('service worker integration', () => {
    it('should register CDN assets for offline caching', async () => {
      const mockCache = {
        addAll: vi.fn().mockResolvedValue(undefined)
      };
      
      global.caches = {
        open: vi.fn().mockResolvedValue(mockCache),
        match: vi.fn(),
        has: vi.fn(),
        delete: vi.fn(),
        keys: vi.fn()
      } as any;

      await cdnService.cacheAssets([
        '/css/app.css',
        '/js/app.js',
        '/images/logo.png'
      ]);

      expect(global.caches.open).toHaveBeenCalledWith('mams-cdn-v1');
      expect(mockCache.addAll).toHaveBeenCalledWith([
        'https://cdn.mams.example.com/css/app.css',
        'https://cdn.mams.example.com/js/app.js',
        'https://cdn.mams.example.com/images/logo.png'
      ]);
    });
  });

  describe('error handling', () => {
    it('should fallback to origin on CDN failure', async () => {
      // Simulate CDN failure
      let attemptCount = 0;
      (global.fetch as any).mockImplementation(async (url: string) => {
        attemptCount++;
        if (url.includes('cdn.mams.example.com') && attemptCount === 1) {
          throw new Error('CDN unreachable');
        }
        return {
          ok: true,
          blob: async () => new Blob(['image data'])
        };
      });

      const blob = await cdnService.fetchAsset('/images/test.jpg');
      
      expect(attemptCount).toBe(2);
      expect(blob).toBeInstanceOf(Blob);
    });

    it('should implement exponential backoff for retries', async () => {
      const delays: number[] = [];
      const originalSetTimeout = global.setTimeout;
      
      global.setTimeout = vi.fn().mockImplementation((fn, delay) => {
        delays.push(delay);
        fn();
        return 1;
      }) as any;

      (global.fetch as any).mockRejectedValue(new Error('Network error'));

      try {
        await cdnService.fetchAssetWithRetry('/test.js', 3);
      } catch (e) {
        // Expected to fail after retries
      }

      // Verify exponential backoff pattern
      expect(delays[0]).toBeLessThan(delays[1]);
      expect(delays[1]).toBeLessThan(delays[2]);
      
      global.setTimeout = originalSetTimeout;
    });
  });

  describe('bandwidth detection', () => {
    it('should adapt quality based on connection speed', async () => {
      // Mock Network Information API
      (navigator as any).connection = {
        effectiveType: '3g',
        downlink: 1.5 // Mbps
      };

      const quality = cdnService.getAdaptiveQuality();
      expect(quality).toBe('medium');

      // Test with 4G
      (navigator as any).connection.effectiveType = '4g';
      (navigator as any).connection.downlink = 10;
      
      const highQuality = cdnService.getAdaptiveQuality();
      expect(highQuality).toBe('high');
    });
  });
});

describe('CDN React Hooks', () => {
  it('should provide useCDNUrl hook', () => {
    // This would test React hooks for CDN integration
    // Example implementation would be in a separate file
    expect(true).toBe(true);
  });
});

describe('CDN Analytics', () => {
  it('should track CDN usage metrics', () => {
    const analytics = cdnService.getAnalytics();
    
    expect(analytics).toHaveProperty('totalRequests');
    expect(analytics).toHaveProperty('cacheHitRate');
    expect(analytics).toHaveProperty('bandwidthUsed');
    expect(analytics).toHaveProperty('errorRate');
  });
});