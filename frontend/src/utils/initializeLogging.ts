import { logger } from './logger';
import { performanceMonitor } from './performance';
import { errorReportingService } from '../services/errorReportingService';

export const initializeLogging = () => {
  // Set up logger configuration based on environment
  const isDevelopment = process.env.NODE_ENV === 'development';
  const isProduction = process.env.NODE_ENV === 'production';

  // Configure logger
  logger.setContext({
    version: process.env.REACT_APP_VERSION || '1.0.0',
    environment: process.env.NODE_ENV || 'development',
    buildTime: process.env.REACT_APP_BUILD_TIME || new Date().toISOString(),
    gitCommit: process.env.REACT_APP_GIT_COMMIT || 'unknown',
  });

  // Enable performance monitoring
  performanceMonitor.setEnabled(true);

  // Configure error reporting service
  errorReportingService.setEnabled(isProduction);
  
  if (process.env.REACT_APP_ERROR_REPORTING_ENDPOINT) {
    errorReportingService.setEndpoint(process.env.REACT_APP_ERROR_REPORTING_ENDPOINT);
  }

  // Log initialization
  logger.info('Logging system initialized', {
    isDevelopment,
    isProduction,
    errorReportingEnabled: isProduction,
    performanceMonitoringEnabled: true,
    actionType: 'initialization',
  });

  // Test error reporting in development
  if (isDevelopment && process.env.REACT_APP_TEST_ERROR_REPORTING === 'true') {
    setTimeout(() => {
      errorReportingService.testErrorReporting()
        .then((success) => {
          logger.info('Error reporting test completed', { success });
        })
        .catch((error) => {
          logger.error('Error reporting test failed', {}, error);
        });
    }, 5000);
  }

  // Set up periodic health checks in production
  if (isProduction) {
    setInterval(() => {
      errorReportingService.healthCheck()
        .then((isHealthy) => {
          if (!isHealthy) {
            logger.warn('Error reporting service health check failed');
          }
        })
        .catch((error) => {
          logger.error('Error reporting service health check error', {}, error);
        });
    }, 5 * 60 * 1000); // Check every 5 minutes
  }

  // Log page load performance
  window.addEventListener('load', () => {
    setTimeout(() => {
      logger.info('Page loaded', {
        loadTime: performance.now(),
        actionType: 'page_load',
      });
    }, 100);
  });

  // Log page visibility changes
  document.addEventListener('visibilitychange', () => {
    logger.info('Page visibility changed', {
      visible: document.visibilityState === 'visible',
      actionType: 'page_visibility',
    });
  });

  // Log network status changes
  window.addEventListener('online', () => {
    logger.info('Network status changed', {
      online: true,
      actionType: 'network_status',
    });
  });

  window.addEventListener('offline', () => {
    logger.warn('Network status changed', {
      online: false,
      actionType: 'network_status',
    });
  });

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    logger.info('Page unloading', {
      actionType: 'page_unload',
    });
    
    // Flush any pending logs
    logger.flush();
  });
};

export default initializeLogging;