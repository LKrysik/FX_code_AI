import { useEffect, useRef, useCallback } from 'react';
import { debugLog } from '@/utils/config';

interface PerformanceMetrics {
  apiCalls: number;
  apiErrors: number;
  cacheHits: number;
  cacheMisses: number;
  averageResponseTime: number;
  websocketMessages: number;
  lastUpdated: number;
}

interface PerformanceEntry {
  timestamp: number;
  duration?: number;
  type: 'api' | 'cache' | 'websocket';
  success: boolean;
  details?: any;
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics = {
    apiCalls: 0,
    apiErrors: 0,
    cacheHits: 0,
    cacheMisses: 0,
    averageResponseTime: 0,
    websocketMessages: 0,
    lastUpdated: Date.now()
  };

  private entries: PerformanceEntry[] = [];
  private maxEntries = 100;

  recordApiCall(duration: number, success: boolean): void {
    this.metrics.apiCalls++;
    if (!success) this.metrics.apiErrors++;

    // Update rolling average
    const totalTime = this.metrics.averageResponseTime * (this.metrics.apiCalls - 1) + duration;
    this.metrics.averageResponseTime = totalTime / this.metrics.apiCalls;

    this.addEntry({
      timestamp: Date.now(),
      duration,
      type: 'api',
      success
    });
  }

  recordCacheHit(): void {
    this.metrics.cacheHits++;
    this.addEntry({
      timestamp: Date.now(),
      type: 'cache',
      success: true
    });
  }

  recordCacheMiss(): void {
    this.metrics.cacheMisses++;
    this.addEntry({
      timestamp: Date.now(),
      type: 'cache',
      success: false
    });
  }

  recordWebSocketMessage(): void {
    this.metrics.websocketMessages++;
    this.addEntry({
      timestamp: Date.now(),
      type: 'websocket',
      success: true
    });
  }

  private addEntry(entry: PerformanceEntry): void {
    this.entries.push(entry);
    if (this.entries.length > this.maxEntries) {
      this.entries.shift();
    }
    this.metrics.lastUpdated = Date.now();
  }

  getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  getCacheHitRate(): number {
    const total = this.metrics.cacheHits + this.metrics.cacheMisses;
    return total > 0 ? (this.metrics.cacheHits / total) * 100 : 0;
  }

  getErrorRate(): number {
    return this.metrics.apiCalls > 0 ? (this.metrics.apiErrors / this.metrics.apiCalls) * 100 : 0;
  }

  getRecentEntries(minutes = 5): PerformanceEntry[] {
    const cutoff = Date.now() - (minutes * 60 * 1000);
    return this.entries.filter(entry => entry.timestamp > cutoff);
  }

  reset(): void {
    this.metrics = {
      apiCalls: 0,
      apiErrors: 0,
      cacheHits: 0,
      cacheMisses: 0,
      averageResponseTime: 0,
      websocketMessages: 0,
      lastUpdated: Date.now()
    };
    this.entries = [];
  }
}

// Global performance monitor instance
const performanceMonitor = new PerformanceMonitor();

export function usePerformanceMonitor() {
  const startTimeRef = useRef<number>();

  const startTiming = useCallback(() => {
    startTimeRef.current = performance.now();
  }, []);

  const endTiming = useCallback((type: 'api' | 'cache' | 'websocket', success = true) => {
    if (startTimeRef.current) {
      const duration = performance.now() - startTimeRef.current;
      if (type === 'api') {
        performanceMonitor.recordApiCall(duration, success);
      }
      startTimeRef.current = undefined;
    }
  }, []);

  const recordCacheHit = useCallback(() => {
    performanceMonitor.recordCacheHit();
  }, []);

  const recordCacheMiss = useCallback(() => {
    performanceMonitor.recordCacheMiss();
  }, []);

  const recordWebSocketMessage = useCallback(() => {
    performanceMonitor.recordWebSocketMessage();
  }, []);

  // Log metrics every 30 seconds in development
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const interval = setInterval(() => {
        const metrics = performanceMonitor.getMetrics();
        const hitRate = performanceMonitor.getCacheHitRate();
        const errorRate = performanceMonitor.getErrorRate();

        debugLog('Performance Metrics:', {
          apiCalls: metrics.apiCalls,
          cacheHitRate: `${hitRate.toFixed(1)}%`,
          errorRate: `${errorRate.toFixed(1)}%`,
          avgResponseTime: `${metrics.averageResponseTime.toFixed(0)}ms`,
          websocketMessages: metrics.websocketMessages
        });
      }, 30000);

      return () => clearInterval(interval);
    }
  }, []);

  return {
    startTiming,
    endTiming,
    recordCacheHit,
    recordCacheMiss,
    recordWebSocketMessage,
    getMetrics: () => performanceMonitor.getMetrics(),
    getCacheHitRate: () => performanceMonitor.getCacheHitRate(),
    getErrorRate: () => performanceMonitor.getErrorRate(),
    getRecentEntries: (minutes?: number) => performanceMonitor.getRecentEntries(minutes),
    reset: () => performanceMonitor.reset()
  };
}

// Export global monitor for imperative use
export const getPerformanceMetrics = () => performanceMonitor.getMetrics();
export const getCacheHitRate = () => performanceMonitor.getCacheHitRate();
export const getErrorRate = () => performanceMonitor.getErrorRate();

// Imperative API for non-React code
export const recordApiCall = (duration: number, success: boolean) =>
  performanceMonitor.recordApiCall(duration, success);
export const recordCacheHit = () => performanceMonitor.recordCacheHit();
export const recordCacheMiss = () => performanceMonitor.recordCacheMiss();
export const recordWebSocketMessage = () => performanceMonitor.recordWebSocketMessage();