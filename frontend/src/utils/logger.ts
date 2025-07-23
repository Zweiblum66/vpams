export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4,
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  error?: Error;
  userId?: string;
  sessionId?: string;
  url?: string;
  userAgent?: string;
  stackTrace?: string;
}

export interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableRemote: boolean;
  enableStorage: boolean;
  maxStorageEntries: number;
  remoteEndpoint?: string;
  context?: Record<string, any>;
}

class Logger {
  private config: LoggerConfig;
  private sessionId: string;
  private buffer: LogEntry[] = [];
  private maxBufferSize = 100;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = {
      level: LogLevel.INFO,
      enableConsole: true,
      enableRemote: false,
      enableStorage: true,
      maxStorageEntries: 1000,
      ...config,
    };
    
    this.sessionId = this.generateSessionId();
    this.loadStoredLogs();
    this.setupErrorHandlers();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  private setupErrorHandlers(): void {
    // Global error handler for unhandled JavaScript errors
    window.addEventListener('error', (event) => {
      this.error('Unhandled JavaScript error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack,
      });
    });

    // Global handler for unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise,
        stack: event.reason?.stack,
      });
    });

    // Console error override to capture console.error calls
    const originalError = console.error;
    console.error = (...args) => {
      originalError.apply(console, args);
      this.error('Console error', { args });
    };
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.config.level;
  }

  private formatMessage(level: LogLevel, message: string): string {
    const timestamp = new Date().toISOString();
    const levelName = LogLevel[level];
    return `[${timestamp}] [${levelName}] ${message}`;
  }

  private createLogEntry(level: LogLevel, message: string, context?: Record<string, any>, error?: Error): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context: { ...this.config.context, ...context },
      error,
      userId: this.getCurrentUserId(),
      sessionId: this.sessionId,
      url: window.location.href,
      userAgent: navigator.userAgent,
    };

    if (error) {
      entry.stackTrace = error.stack;
    }

    return entry;
  }

  private getCurrentUserId(): string | undefined {
    try {
      const authState = localStorage.getItem('user_data');
      if (authState) {
        const user = JSON.parse(authState);
        return user.user_id;
      }
    } catch (error) {
      // Ignore errors when getting user ID
    }
    return undefined;
  }

  private logToConsole(entry: LogEntry): void {
    if (!this.config.enableConsole) return;

    const formattedMessage = this.formatMessage(entry.level, entry.message);
    const logData = [formattedMessage];

    if (entry.context) {
      logData.push('Context:', entry.context);
    }

    if (entry.error) {
      logData.push('Error:', entry.error);
    }

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(...logData);
        break;
      case LogLevel.INFO:
        console.info(...logData);
        break;
      case LogLevel.WARN:
        console.warn(...logData);
        break;
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        console.error(...logData);
        break;
    }
  }

  private logToStorage(entry: LogEntry): void {
    if (!this.config.enableStorage) return;

    try {
      this.buffer.push(entry);
      
      // Limit buffer size
      if (this.buffer.length > this.maxBufferSize) {
        this.buffer = this.buffer.slice(-this.maxBufferSize);
      }

      // Store in localStorage
      const storedLogs = this.getStoredLogs();
      storedLogs.push(entry);
      
      // Limit stored logs
      if (storedLogs.length > this.config.maxStorageEntries) {
        storedLogs.splice(0, storedLogs.length - this.config.maxStorageEntries);
      }

      localStorage.setItem('mams_logs', JSON.stringify(storedLogs));
    } catch (error) {
      console.error('Failed to store log entry:', error);
    }
  }

  private async logToRemote(entry: LogEntry): Promise<void> {
    if (!this.config.enableRemote || !this.config.remoteEndpoint) return;

    try {
      await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      });
    } catch (error) {
      console.error('Failed to send log to remote endpoint:', error);
    }
  }

  private log(level: LogLevel, message: string, context?: Record<string, any>, error?: Error): void {
    if (!this.shouldLog(level)) return;

    const entry = this.createLogEntry(level, message, context, error);

    this.logToConsole(entry);
    this.logToStorage(entry);
    
    // Send to remote endpoint asynchronously
    if (this.config.enableRemote) {
      this.logToRemote(entry).catch(console.error);
    }
  }

  private loadStoredLogs(): void {
    try {
      const stored = localStorage.getItem('mams_logs');
      if (stored) {
        const logs = JSON.parse(stored);
        this.buffer = logs.slice(-this.maxBufferSize);
      }
    } catch (error) {
      console.error('Failed to load stored logs:', error);
    }
  }

  private getStoredLogs(): LogEntry[] {
    try {
      const stored = localStorage.getItem('mams_logs');
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to get stored logs:', error);
      return [];
    }
  }

  // Public API
  debug(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.DEBUG, message, context);
  }

  info(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.INFO, message, context);
  }

  warn(message: string, context?: Record<string, any>): void {
    this.log(LogLevel.WARN, message, context);
  }

  error(message: string, context?: Record<string, any>, error?: Error): void {
    this.log(LogLevel.ERROR, message, context, error);
  }

  fatal(message: string, context?: Record<string, any>, error?: Error): void {
    this.log(LogLevel.FATAL, message, context, error);
  }

  // Performance logging
  time(label: string): void {
    console.time(label);
  }

  timeEnd(label: string): void {
    console.timeEnd(label);
  }

  // User action logging
  logUserAction(action: string, context?: Record<string, any>): void {
    this.info(`User action: ${action}`, { 
      action, 
      ...context,
      actionType: 'user_action'
    });
  }

  // API call logging
  logApiCall(method: string, url: string, status: number, duration: number, context?: Record<string, any>): void {
    const level = status >= 400 ? LogLevel.ERROR : LogLevel.INFO;
    this.log(level, `API ${method} ${url} - ${status}`, {
      method,
      url,
      status,
      duration,
      ...context,
      actionType: 'api_call'
    });
  }

  // Navigation logging
  logNavigation(from: string, to: string, context?: Record<string, any>): void {
    this.info(`Navigation: ${from} → ${to}`, {
      from,
      to,
      ...context,
      actionType: 'navigation'
    });
  }

  // Configuration
  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  setContext(context: Record<string, any>): void {
    this.config.context = { ...this.config.context, ...context };
  }

  // Utility methods
  getBufferedLogs(): LogEntry[] {
    return [...this.buffer];
  }

  getAllStoredLogs(): LogEntry[] {
    return this.getStoredLogs();
  }

  clearLogs(): void {
    this.buffer = [];
    localStorage.removeItem('mams_logs');
  }

  exportLogs(): string {
    return JSON.stringify(this.getStoredLogs(), null, 2);
  }

  // Batch operations
  flush(): void {
    // Force flush any pending remote logs
    if (this.buffer.length > 0 && this.config.enableRemote) {
      this.buffer.forEach(entry => {
        this.logToRemote(entry).catch(console.error);
      });
    }
  }
}

// Create singleton instance
export const logger = new Logger({
  level: process.env.NODE_ENV === 'development' ? LogLevel.DEBUG : LogLevel.INFO,
  enableConsole: true,
  enableRemote: process.env.NODE_ENV === 'production',
  enableStorage: true,
  remoteEndpoint: process.env.REACT_APP_LOG_ENDPOINT || '/api/v1/logs',
  context: {
    app: 'mams-frontend',
    version: process.env.REACT_APP_VERSION || '1.0.0',
    environment: process.env.NODE_ENV || 'development',
  },
});

// Export types and logger
export { Logger };
export default logger;