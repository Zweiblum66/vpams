import { logger } from '../utils/logger';

export interface ErrorReport {
  errorId: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info';
  message: string;
  stack?: string;
  context: Record<string, any>;
  userAgent: string;
  url: string;
  userId?: string;
  sessionId: string;
  browserInfo: {
    name: string;
    version: string;
    platform: string;
    language: string;
    cookieEnabled: boolean;
  };
  screenInfo: {
    width: number;
    height: number;
    colorDepth: number;
    pixelDepth: number;
  };
  memoryInfo?: {
    usedJSHeapSize: number;
    totalJSHeapSize: number;
    jsHeapSizeLimit: number;
  };
  performanceInfo?: {
    timing: PerformanceTiming;
    navigation: PerformanceNavigation;
  };
}

class ErrorReportingService {
  private isEnabled: boolean = true;
  private endpoint: string = '/api/v1/error-reports';
  private maxRetries: number = 3;
  private retryDelay: number = 1000;

  constructor() {
    this.endpoint = process.env.REACT_APP_ERROR_REPORTING_ENDPOINT || this.endpoint;
  }

  private getBrowserInfo() {
    const userAgent = navigator.userAgent;
    let browserName = 'Unknown';
    let browserVersion = 'Unknown';

    // Simple browser detection
    if (userAgent.includes('Chrome')) {
      browserName = 'Chrome';
      const match = userAgent.match(/Chrome\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Firefox')) {
      browserName = 'Firefox';
      const match = userAgent.match(/Firefox\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Safari')) {
      browserName = 'Safari';
      const match = userAgent.match(/Version\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Edge')) {
      browserName = 'Edge';
      const match = userAgent.match(/Edge\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    }

    return {
      name: browserName,
      version: browserVersion,
      platform: navigator.platform,
      language: navigator.language,
      cookieEnabled: navigator.cookieEnabled,
    };
  }

  private getScreenInfo() {
    return {
      width: window.screen.width,
      height: window.screen.height,
      colorDepth: window.screen.colorDepth,
      pixelDepth: window.screen.pixelDepth,
    };
  }

  private getMemoryInfo() {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
      };
    }
    return undefined;
  }

  private getPerformanceInfo() {
    if (performance.timing && performance.navigation) {
      return {
        timing: performance.timing,
        navigation: performance.navigation,
      };
    }
    return undefined;
  }

  private getCurrentUserId(): string | undefined {
    try {
      const userData = localStorage.getItem('user_data');
      if (userData) {
        const user = JSON.parse(userData);
        return user.user_id;
      }
    } catch (error) {
      // Ignore errors when getting user ID
    }
    return undefined;
  }

  private async sendReport(report: ErrorReport): Promise<boolean> {
    if (!this.isEnabled) return false;

    let attempts = 0;
    const maxAttempts = this.maxRetries + 1;

    while (attempts < maxAttempts) {
      try {
        const response = await fetch(this.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(report),
        });

        if (response.ok) {
          logger.debug('Error report sent successfully', {
            errorId: report.errorId,
            attempts: attempts + 1,
          });
          return true;
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      } catch (error) {
        attempts++;
        logger.warn('Failed to send error report', {
          errorId: report.errorId,
          attempt: attempts,
          error: error.message,
        });

        if (attempts < maxAttempts) {
          // Wait before retrying
          await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempts));
        }
      }
    }

    logger.error('Failed to send error report after all attempts', {
      errorId: report.errorId,
      totalAttempts: attempts,
    });

    return false;
  }

  async reportError(
    error: Error,
    context: Record<string, any> = {},
    level: 'error' | 'warning' | 'info' = 'error'
  ): Promise<void> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    
    const report: ErrorReport = {
      errorId,
      timestamp: new Date().toISOString(),
      level,
      message: error.message,
      stack: error.stack,
      context,
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: this.getCurrentUserId(),
      sessionId: logger.getBufferedLogs()[0]?.sessionId || 'unknown',
      browserInfo: this.getBrowserInfo(),
      screenInfo: this.getScreenInfo(),
      memoryInfo: this.getMemoryInfo(),
      performanceInfo: this.getPerformanceInfo(),
    };

    // Log locally first
    logger.error('Error reported to error reporting service', {
      errorId,
      message: error.message,
      context,
      actionType: 'error_reporting',
    }, error);

    // Send to remote endpoint
    await this.sendReport(report);
  }

  async reportWarning(
    message: string,
    context: Record<string, any> = {}
  ): Promise<void> {
    const warningError = new Error(message);
    warningError.name = 'Warning';
    await this.reportError(warningError, context, 'warning');
  }

  async reportInfo(
    message: string,
    context: Record<string, any> = {}
  ): Promise<void> {
    const infoError = new Error(message);
    infoError.name = 'Info';
    await this.reportError(infoError, context, 'info');
  }

  // Configuration methods
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  setEndpoint(endpoint: string): void {
    this.endpoint = endpoint;
  }

  setMaxRetries(maxRetries: number): void {
    this.maxRetries = maxRetries;
  }

  setRetryDelay(delay: number): void {
    this.retryDelay = delay;
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.endpoint}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      return response.ok;
    } catch (error) {
      logger.warn('Error reporting service health check failed', {}, error);
      return false;
    }
  }

  // Test error reporting
  async testErrorReporting(): Promise<boolean> {
    const testError = new Error('Test error from error reporting service');
    testError.name = 'TestError';
    
    try {
      await this.reportError(testError, {
        isTest: true,
        testTimestamp: new Date().toISOString(),
      });
      return true;
    } catch (error) {
      logger.error('Error reporting service test failed', {}, error);
      return false;
    }
  }
}

// Create singleton instance
export const errorReportingService = new ErrorReportingService();

// Export for testing
export { ErrorReportingService };

export default errorReportingService;