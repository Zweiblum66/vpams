import { defineConfig, splitVendorChunkPlugin } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import viteCompression from 'vite-plugin-compression';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    splitVendorChunkPlugin(),
    // Compression plugin for gzip and brotli
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
    // PWA plugin for service worker and offline support
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
      manifest: {
        name: 'MAMS - Media Asset Management',
        short_name: 'MAMS',
        theme_color: '#1976d2',
        icons: [
          {
            src: '/android-chrome-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/android-chrome-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        // Cache strategies for different types of assets
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
          {
            urlPattern: /^https:\/\/api\..*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5, // 5 minutes
              },
              networkTimeoutSeconds: 10,
            },
          },
        ],
      },
    }),
    // Bundle visualizer
    visualizer({
      open: false,
      gzipSize: true,
      brotliSize: true,
      filename: 'dist/bundle-analysis.html',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@store': path.resolve(__dirname, './src/store'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  build: {
    // Output configuration
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    
    // Rollup options for code splitting
    rollupOptions: {
      output: {
        // Manual chunk splitting for optimal caching
        manualChunks: (id) => {
          // React ecosystem
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            
            // Material UI
            if (id.includes('@mui') || id.includes('@emotion')) {
              return 'mui-vendor';
            }
            
            // Redux and data fetching
            if (id.includes('redux') || id.includes('@reduxjs') || id.includes('reselect')) {
              return 'redux-vendor';
            }
            
            // Media libraries
            if (id.includes('video.js') || id.includes('wavesurfer') || id.includes('plyr')) {
              return 'media-vendor';
            }
            
            // Utilities
            if (id.includes('lodash') || id.includes('date-fns') || id.includes('axios')) {
              return 'utils-vendor';
            }
            
            // Charts and visualization
            if (id.includes('recharts') || id.includes('d3')) {
              return 'charts-vendor';
            }
            
            // Forms and validation
            if (id.includes('react-hook-form') || id.includes('yup')) {
              return 'forms-vendor';
            }
            
            // Large libraries
            if (id.includes('monaco-editor')) {
              return 'monaco-vendor';
            }
            
            // Everything else from node_modules
            return 'vendor';
          }
          
          // App code splitting by feature
          if (id.includes('src/pages/admin')) {
            return 'admin';
          }
          
          if (id.includes('src/pages/workflow')) {
            return 'workflow';
          }
          
          if (id.includes('src/components/media')) {
            return 'media-components';
          }
        },
        
        // Asset file naming
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
            return `assets/images/[name]-[hash][extname]`;
          }
          
          if (/woff2?|ttf|otf|eot/i.test(ext)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          
          return `assets/[name]-[hash][extname]`;
        },
        
        // Chunk file naming
        chunkFileNames: 'assets/js/[name]-[hash].js',
        
        // Entry file naming
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },
    
    // Chunk size warnings
    chunkSizeWarningLimit: 1000, // 1MB
    
    // Target modern browsers for smaller bundles
    target: ['es2020', 'edge88', 'firefox78', 'chrome87', 'safari14'],
    
    // Minification options
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
      },
    },
  },
  
  // Development server configuration
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  
  // Optimize deps
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@mui/material',
      '@emotion/react',
      '@emotion/styled',
      '@reduxjs/toolkit',
      'react-redux',
    ],
    exclude: ['@mui/icons-material'], // Large library, better to tree-shake
  },
});