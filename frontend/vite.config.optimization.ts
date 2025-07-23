/**
 * Vite configuration for bundle size optimization
 */

import { defineConfig, splitVendorChunkPlugin } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import viteCompression from 'vite-plugin-compression';
import { VitePWA } from 'vite-plugin-pwa';
import legacy from '@vitejs/plugin-legacy';

export default defineConfig({
  plugins: [
    react(),
    
    // Split vendor chunks for better caching
    splitVendorChunkPlugin(),
    
    // Bundle analyzer
    visualizer({
      open: process.env.ANALYZE === 'true',
      filename: 'dist/stats.html',
      gzipSize: true,
      brotliSize: true,
    }),
    
    // Compression
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240, // Only compress files > 10KB
      deleteOriginFile: false,
    }),
    
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240,
      deleteOriginFile: false,
    }),
    
    // PWA support for offline functionality
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'MAMS - Media Asset Management',
        short_name: 'MAMS',
        theme_color: '#1976d2',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/cdn\.mams\.example\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'cdn-cache',
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    }),
    
    // Legacy browser support (optional, adds ~30KB)
    legacy({
      targets: ['defaults', 'not IE 11'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime'],
      renderLegacyChunks: false, // Only create system chunks if needed
      polyfills: false // Use polyfill.io instead
    })
  ],
  
  build: {
    // Enable minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
        passes: 2,
      },
      mangle: {
        safari10: true,
      },
      format: {
        comments: false,
      },
    },
    
    // Output configuration
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false, // Disable in production
    
    // Chunk size warnings
    chunkSizeWarningLimit: 500, // KB
    
    // Rollup options
    rollupOptions: {
      output: {
        // Manual chunk splitting for optimal caching
        manualChunks: {
          // React ecosystem
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          
          // Redux ecosystem
          'redux-vendor': ['@reduxjs/toolkit', 'react-redux'],
          
          // UI libraries
          'mui-vendor': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          
          // Utilities
          'utils-vendor': ['lodash-es', 'date-fns', 'axios'],
          
          // Media libraries (lazy loaded)
          'media-vendor': ['video.js', 'wavesurfer.js'],
          
          // Charts (lazy loaded)
          'charts-vendor': ['recharts', 'd3-scale', 'd3-shape'],
        },
        
        // Asset file naming
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
            return `assets/images/[name]-[hash][extname]`;
          } else if (/woff2?|ttf|eot/i.test(ext)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
        
        // Chunk file naming
        chunkFileNames: 'assets/js/[name]-[hash].js',
        
        // Entry file naming
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
      
      // External dependencies (if using CDN)
      external: process.env.USE_CDN === 'true' ? [
        'react',
        'react-dom',
      ] : [],
    },
    
    // Enable CSS code splitting
    cssCodeSplit: true,
    
    // Asset inlining threshold
    assetsInlineLimit: 4096, // 4KB
  },
  
  // Optimize deps
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@reduxjs/toolkit',
      'react-redux',
      '@mui/material',
    ],
    exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/core'], // Heavy deps to exclude
  },
  
  // CSS optimization
  css: {
    modules: {
      localsConvention: 'camelCase',
      generateScopedName: '[hash:base64:5]', // Shorter class names
    },
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`,
      },
    },
  },
  
  resolve: {
    alias: {
      '@': '/src',
      // Use smaller lodash imports
      'lodash': 'lodash-es',
    },
  },
  
  // Development server configuration
  server: {
    port: 3000,
    open: true,
    cors: true,
    // Enable compression in dev too
    middlewareMode: false,
  },
  
  // Preview server configuration
  preview: {
    port: 3001,
    open: true,
    cors: true,
  },
});