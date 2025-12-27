/**
 * Frontend Error Logging Service
 *
 * Captures browser console errors, unhandled exceptions, and promise rejections,
 * then sends them to the backend for centralized logging.
 *
 * Features:
 * - Captures console.error calls
 * - Captures window.onerror (uncaught exceptions)
 * - Captures unhandledrejection (unhandled promise rejections)
 * - Batches logs to reduce network requests
 * - Includes user context and browser info
 */

import { config } from '@/utils/config';

interface FrontendLogEntry {
  level: 'error' | 'warn' | 'info';
  message: string;
  stack?: string;
  source?: string;
  lineno?: number;
  colno?: number;
  timestamp: string;
  url: string;
  userAgent: string;
  sessionId?: string;
}

class FrontendLogService {
  private static instance: FrontendLogService;
  private logBuffer: FrontendLogEntry[] = [];
  private flushInterval: NodeJS.Timeout | null = null;
  private isInitialized = false;
  private originalConsoleError: typeof console.error | null = null;
  private sessionId: string;

  // Configuration
  private readonly FLUSH_INTERVAL_MS = 5000; // Flush every 5 seconds
  private readonly MAX_BUFFER_SIZE = 20; // Flush when buffer reaches 20 entries
  private readonly ENDPOINT = '/api/frontend-logs';

  private constructor() {
    this.sessionId = this.generateSessionId();
  }

  static getInstance(): FrontendLogService {
    if (!FrontendLogService.instance) {
      FrontendLogService.instance = new FrontendLogService();
    }
    return FrontendLogService.instance;
  }

  /**
   * Initialize error capturing. Call once on app startup.
   */
  init(): void {
    if (this.isInitialized || typeof window === 'undefined') {
      return;
    }

    this.isInitialized = true;

    // Capture console.error
    this.originalConsoleError = console.error.bind(console);
    console.error = (...args: any[]) => {
      this.captureConsoleError(args);
      this.originalConsoleError!(...args);
    };

    // Capture uncaught exceptions
    window.onerror = (message, source, lineno, colno, error) => {
      this.captureWindowError(message, source, lineno, colno, error);
      return false; // Allow default handling
    };

    // Capture unhandled promise rejections
    window.onunhandledrejection = (event: PromiseRejectionEvent) => {
      this.captureUnhandledRejection(event);
    };

    // Start flush interval
    this.flushInterval = setInterval(() => {
      this.flush();
    }, this.FLUSH_INTERVAL_MS);

    // Flush on page unload
    window.addEventListener('beforeunload', () => {
      this.flush(true);
    });

    console.log('[FrontendLogService] Initialized - errors will be sent to backend');
  }

  /**
   * Cleanup and restore original console.error
   */
  destroy(): void {
    if (!this.isInitialized) {
      return;
    }

    if (this.flushInterval) {
      clearInterval(this.flushInterval);
      this.flushInterval = null;
    }

    if (this.originalConsoleError) {
      console.error = this.originalConsoleError;
      this.originalConsoleError = null;
    }

    window.onerror = null;
    window.onunhandledrejection = null;

    this.flush(true);
    this.isInitialized = false;
  }

  private generateSessionId(): string {
    return `fe_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  }

  private captureConsoleError(args: any[]): void {
    const message = args
      .map(arg => {
        if (arg instanceof Error) {
          return `${arg.message}\n${arg.stack}`;
        }
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg, null, 2);
          } catch {
            return String(arg);
          }
        }
        return String(arg);
      })
      .join(' ');

    const errorArg = args.find(arg => arg instanceof Error);

    this.addLog({
      level: 'error',
      message,
      stack: errorArg?.stack,
      source: 'console.error',
    });
  }

  private captureWindowError(
    message: string | Event,
    source?: string,
    lineno?: number,
    colno?: number,
    error?: Error
  ): void {
    this.addLog({
      level: 'error',
      message: typeof message === 'string' ? message : 'Unknown error',
      stack: error?.stack,
      source: source || 'window.onerror',
      lineno,
      colno,
    });
  }

  private captureUnhandledRejection(event: PromiseRejectionEvent): void {
    let message = 'Unhandled Promise Rejection';
    let stack: string | undefined;

    if (event.reason instanceof Error) {
      message = event.reason.message;
      stack = event.reason.stack;
    } else if (typeof event.reason === 'string') {
      message = event.reason;
    } else if (event.reason) {
      try {
        message = JSON.stringify(event.reason);
      } catch {
        message = String(event.reason);
      }
    }

    this.addLog({
      level: 'error',
      message,
      stack,
      source: 'unhandledrejection',
    });
  }

  private addLog(partial: Omit<FrontendLogEntry, 'timestamp' | 'url' | 'userAgent' | 'sessionId'>): void {
    const entry: FrontendLogEntry = {
      ...partial,
      timestamp: new Date().toISOString(),
      url: typeof window !== 'undefined' ? window.location.href : 'unknown',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
      sessionId: this.sessionId,
    };

    this.logBuffer.push(entry);

    // Flush immediately if buffer is full
    if (this.logBuffer.length >= this.MAX_BUFFER_SIZE) {
      this.flush();
    }
  }

  /**
   * Manually log an error (useful for ErrorBoundary integration)
   */
  logError(message: string, error?: Error, context?: Record<string, any>): void {
    this.addLog({
      level: 'error',
      message: context ? `${message} | Context: ${JSON.stringify(context)}` : message,
      stack: error?.stack,
      source: 'manual',
    });
  }

  /**
   * Flush logs to backend
   */
  private async flush(sync = false): Promise<void> {
    if (this.logBuffer.length === 0) {
      return;
    }

    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];

    const payload = {
      logs: logsToSend,
      metadata: {
        sessionId: this.sessionId,
        appVersion: config.appVersion,
        timestamp: new Date().toISOString(),
      },
    };

    try {
      if (sync && navigator.sendBeacon) {
        // Use sendBeacon for page unload (more reliable)
        navigator.sendBeacon(
          `${config.apiUrl}${this.ENDPOINT}`,
          JSON.stringify(payload)
        );
      } else {
        // Use fetch for normal operation
        await fetch(`${config.apiUrl}${this.ENDPOINT}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          credentials: 'include',
          // Don't wait too long
          signal: AbortSignal.timeout(5000),
        });
      }
    } catch (error) {
      // Log to console but don't re-capture (would cause infinite loop)
      if (this.originalConsoleError) {
        this.originalConsoleError('[FrontendLogService] Failed to send logs:', error);
      }
      // Put logs back in buffer for retry
      this.logBuffer.unshift(...logsToSend);
    }
  }
}

export const frontendLogService = FrontendLogService.getInstance();
