export {};

import { getAuthHeaders } from '../config/api';

interface LogEntry {
  level: 'log' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  data?: any[];
  stack?: string;
  location?: {
    file?: string;
    line?: number;
    column?: number;
  };
  userAgent?: string;
  url?: string;
  type?: 'error' | 'message' | 'log';
  tag?: string;
  source?: 'browser' | 'api' | 'database';
  network?: {
    method?: string;
    url?: string;
    status?: number;
    ok?: boolean;
    duration?: number;
  };
}

// Extended Error interface for browser-specific properties
interface BrowserError extends Error {
  fileName?: string;
  lineNumber?: number;
  columnNumber?: number;
}

class Logger {
  private static instance: Logger;
  private originalConsole: {
    log: typeof console.log;
    info: typeof console.info;
    warn: typeof console.warn;
    error: typeof console.error;
  };
  private originalFetch: typeof window.fetch;
  private originalXHR: typeof window.XMLHttpRequest;
  private logQueue: LogEntry[] = [];
  private isProcessing: boolean = false;
  private readonly FLUSH_INTERVAL = 0;

  private constructor() {
    // Store original methods
    this.originalConsole = {
      log: console.log,
      info: console.info,
      warn: console.warn,
      error: console.error
    };
    this.originalFetch = window.fetch;
    this.originalXHR = window.XMLHttpRequest;

    // Initialize the logger
    this.initialize();
  }

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private isEventApiUrl(url: string): boolean {
    try {
      const u = new URL(url, window.location.origin);
      return u.pathname.startsWith('/api/events');
    } catch {
      return false;
    }
  }

  private initialize(): void {
    // Override console methods
    console.log = (...args) => this.handleLog('log', args);
    console.info = (...args) => this.handleLog('info', args);
    console.warn = (...args) => this.handleLog('warn', args);
    console.error = (...args) => this.handleLog('error', args);

    // Set up periodic flushing
    setInterval(() => this.flushLogs(), this.FLUSH_INTERVAL);

    // Handle uncaught errors
    window.addEventListener('error', (event) => {
      this.handleLog('error', [event.message], {
        stack: event.error?.stack,
        location: {
          file: event.filename,
          line: event.lineno,
          column: event.colno
        },
        type: 'error',
        tag: 'window.onerror',
        source: 'browser'
      });
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason;
      this.handleLog('error', [error?.message || String(error)], {
        stack: error?.stack,
        location: error instanceof Error && 'fileName' in error ? {
          file: (error as BrowserError).fileName,
          line: (error as BrowserError).lineNumber,
          column: (error as BrowserError).columnNumber
        } : undefined,
        type: 'error',
        tag: 'unhandledrejection',
        source: 'browser'
      });
    });

    // Patch fetch
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = (init && init.method) || 'GET';
      const url = typeof input === 'string' ? input : (input instanceof URL ? input.toString() : input.url);
      
      if (this.isEventApiUrl(url)) {
        return this.originalFetch.apply(window, [input, init]);
      }

      const start = performance.now();
      try {
        const response = await this.originalFetch.apply(window, [input, init]);
        const duration = performance.now() - start;
        
        this.handleLog(response.ok ? 'info' : 'error', [`${method} ${url}`], {
          type: response.ok ? 'log' : 'error',
          tag: 'network',
          source: 'browser',
          network: {
            method,
            url,
            status: response.status,
            ok: response.ok,
            duration
          }
        });
        
        return response;
      } catch (error) {
        const duration = performance.now() - start;
        this.handleLog('error', [`${method} ${url} failed`], {
          type: 'error',
          tag: 'network',
          source: 'browser',
          network: {
            method,
            url,
            ok: false,
            duration
          }
        });
        throw error;
      }
    };

    // Patch XMLHttpRequest
    const PatchedXHR = function(this: XMLHttpRequest) {
      const xhr = new Logger.instance.originalXHR();
      let method = '';
      let url = '';
      let start = 0;

      const open = xhr.open;
      xhr.open = function(_method: string, _url: string | URL) {
        method = _method;
        url = typeof _url === 'string' ? _url : _url.toString();
        // @ts-ignore
        return open.apply(xhr, arguments);
      };

      const send = xhr.send;
      xhr.send = function() {
        start = performance.now();
        xhr.addEventListener('loadend', () => {
          if (Logger.instance.isEventApiUrl(url)) return;
          const duration = performance.now() - start;
          const ok = xhr.status >= 200 && xhr.status < 400;
          
          Logger.instance.handleLog(ok ? 'info' : 'error', [`${method} ${url}`], {
            type: ok ? 'log' : 'error',
            tag: 'network',
            source: 'browser',
            network: {
              method,
              url,
              status: xhr.status,
              ok,
              duration
            }
          });
        });
        // @ts-ignore
        return send.apply(xhr, arguments);
      };

      return xhr;
    };
    window.XMLHttpRequest = PatchedXHR as any;

    // Log initial page load
    this.handleLog('info', ['Application initialized'], {
      url: window.location.href,
      userAgent: navigator.userAgent,
      type: 'log',
      tag: 'init',
      source: 'browser'
    });
  }

  private handleLog(level: LogEntry['level'], args: any[], additionalInfo: Partial<LogEntry> = {}): void {
    // Call original console method
    this.originalConsole[level].apply(console, args);

    // Create log entry
    const entry: LogEntry = {
      level,
      message: args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
      ).join(' '),
      timestamp: new Date().toISOString(),
      data: args,
      url: window.location.href,
      userAgent: navigator.userAgent,
      type: level === 'error' ? 'error' : 'log',
      tag: additionalInfo.tag || `console.${level}`,
      source: 'browser',
      ...additionalInfo
    };

    // Add to queue
    this.logQueue.push(entry);

    // Immediately flush after each log
    this.flushLogs();
  }

  private async flushLogs(): Promise<void> {
    if (this.isProcessing || this.logQueue.length === 0) return;

    // Prevent sending logs if no valid token is present
    const authHeaders = getAuthHeaders();
    if (!authHeaders['Authorization']) {
      // No token, clear the queue and skip sending
      this.logQueue = [];
      this.isProcessing = false;
      return;
    }

    this.isProcessing = true;
    this.logQueue = [];

    try {
      // await api.post('/api/events', {
      //   source: 'browser',
      //   tag: 'console',
      //   data: logsToSend,
      //   type: 'log'
      // });
      // API call to /api/events intentionally disabled
    } catch (error: any) {
      // console.log('error', {error});
      // If sending fails, put logs back in queue
      // this.logQueue = [...logsToSend, ...this.logQueue];
      // --- RETRY LOGIC COMMENTED OUT BELOW ---
      /*
      // If already on login page, do not retry
      const path = window.location.pathname;
      if (
        (error.message?.includes('401') ||
         error.message?.toLowerCase().includes('token is missing') ||
         error.message?.toLowerCase().includes('unauthorized')) &&
        path === '/signin'
      ) {
        this.originalConsole.warn('Not retrying log send: already on login page.');
        this.retryCount = 0;
        return;
      }
      // Check if it's a rate limit error
      if (error.message?.includes('429') || error.message?.includes('TOO MANY REQUESTS')) {
        // Double the wait time for rate limit errors
        const waitTime = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
        this.originalConsole.warn(`Rate limited. Waiting ${waitTime/1000} seconds before retry.`);
        setTimeout(() => this.flushLogs(), waitTime);
        this.retryCount++;
      } else {
        this.originalConsole.error('Failed to send logs to server:', error);
        // Implement retry logic with exponential backoff
        if (this.retryCount < this.MAX_RETRIES) {
          this.retryCount++;
          const waitTime = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
          setTimeout(() => this.flushLogs(), waitTime);
        } else {
          this.originalConsole.error('Max retries reached for sending logs to server');
          this.retryCount = 0;
        }
      }
      */
      // --- END RETRY LOGIC COMMENTED OUT ---
    } finally {
      this.isProcessing = false;
    }
  }

  public restoreOriginal(): void {
    // Restore original methods
    console.log = this.originalConsole.log;
    console.info = this.originalConsole.info;
    console.warn = this.originalConsole.warn;
    console.error = this.originalConsole.error;
    window.fetch = this.originalFetch;
    window.XMLHttpRequest = this.originalXHR;
  }

  // Method to manually log an error with stack trace
  public logError(error: Error, context?: any): void {
    this.handleLog('error', [error.message, context], {
      stack: error.stack,
      location: 'fileName' in error ? {
        file: (error as BrowserError).fileName,
        line: (error as BrowserError).lineNumber,
        column: (error as BrowserError).columnNumber
      } : undefined,
      type: 'error',
      tag: 'manual.error',
      source: 'browser'
    });
  }

  // Method to manually log a network request
  public logNetwork(method: string, url: string, status: number, duration: number): void {
    const ok = status >= 200 && status < 400;
    this.handleLog(ok ? 'info' : 'error', [`${method} ${url}`], {
      type: ok ? 'log' : 'error',
      tag: 'network',
      source: 'browser',
      network: {
        method,
        url,
        status,
        ok,
        duration
      }
    });
  }
}

// Export singleton instance
export const logger = Logger.getInstance(); 