import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { debugLog, errorLog } from '@/utils/config';
import { recordCacheHit, recordCacheMiss } from './usePerformanceMonitor';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
  isStale: boolean;
}

interface CacheOptions {
  ttl?: number; // Default 5 minutes
  staleWhileRevalidate?: boolean; // Default true
  backgroundRefresh?: boolean; // Default true
  retryCount?: number; // Default 3
  retryDelay?: number; // Default 1000ms
}

interface CacheState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  isStale: boolean;
  lastUpdated: number | null;
  retryCount: number;
}

const DEFAULT_OPTIONS: Required<CacheOptions> = {
  ttl: 5 * 60 * 1000, // 5 minutes
  staleWhileRevalidate: true,
  backgroundRefresh: true,
  retryCount: 3,
  retryDelay: 1000,
};

class SmartCache {
  private cache = new Map<string, CacheEntry<any>>();
  private accessOrder = new Set<string>();
  private refreshTimeouts = new Map<string, NodeJS.Timeout>();
  private maxSize: number;

  constructor(maxSize = 100) {
    this.maxSize = maxSize;
    // Adaptive sizing based on memory pressure
    this.detectMemoryPressure();
  }

  private detectMemoryPressure(): void {
    if (typeof performance !== 'undefined' && (performance as any).memory) {
      const memory = (performance as any).memory;
      const usedPercent = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
      if (usedPercent > 0.8) {
        this.maxSize = Math.max(20, Math.floor(this.maxSize * 0.5));
      }
    }
  }

  get<T>(key: string): CacheEntry<T> | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const now = Date.now();
    const isExpired = now - entry.timestamp > entry.ttl;

    if (isExpired) {
      this.cache.delete(key);
      this.accessOrder.delete(key);
      return null;
    }

    // Move to end (most recently used)
    this.accessOrder.delete(key);
    this.accessOrder.add(key);

    // Mark as stale if it's been more than half the TTL
    entry.isStale = now - entry.timestamp > entry.ttl / 2;

    return entry;
  }

  set<T>(key: string, data: T, ttl: number): void {
    // LRU eviction
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const lruKey = this.accessOrder.values().next().value;
      if (lruKey) {
        this.cache.delete(lruKey);
        this.accessOrder.delete(lruKey);
        debugLog(`Cache LRU eviction: ${lruKey}`);
      }
    }

    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
      isStale: false,
    };

    this.cache.set(key, entry);
    // Move to end (most recently used)
    this.accessOrder.delete(key);
    this.accessOrder.add(key);

    debugLog(`Cache set: ${key}, TTL: ${ttl}ms, Size: ${this.cache.size}/${this.maxSize}`);
  }

  invalidate(key: string): void {
    this.cache.delete(key);
    this.accessOrder.delete(key);
    const timeout = this.refreshTimeouts.get(key);
    if (timeout) {
      clearTimeout(timeout);
      this.refreshTimeouts.delete(key);
    }
    debugLog(`Cache invalidated: ${key}`);
  }

  invalidatePattern(pattern: string): void {
    for (const key of Array.from(this.cache.keys())) {
      if (key.includes(pattern)) {
        this.invalidate(key);
      }
    }
    debugLog(`Cache pattern invalidated: ${pattern}`);
  }

  clear(): void {
    this.cache.clear();
    this.accessOrder.clear();
    for (const timeout of Array.from(this.refreshTimeouts.values())) {
      clearTimeout(timeout);
    }
    this.refreshTimeouts.clear();
    debugLog('Cache cleared');
  }

  getStats(): { size: number; maxSize: number; hitRate?: number } {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
    };
  }

  scheduleRefresh<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number,
    onSuccess: (data: T) => void,
    onError: (error: Error) => void
  ): void {
    const timeout = this.refreshTimeouts.get(key);
    if (timeout) return; // Already scheduled

    const refreshTime = ttl / 2; // Refresh when half stale
    const timeoutId = setTimeout(async () => {
      try {
        debugLog(`Background refresh: ${key}`);
        const data = await fetcher();
        this.set(key, data, ttl);
        onSuccess(data);
      } catch (error) {
        errorLog(`Background refresh failed: ${key}`, error as Error);
        onError(error as Error);
      } finally {
        this.refreshTimeouts.delete(key);
      }
    }, refreshTime);

    this.refreshTimeouts.set(key, timeoutId);
  }
}

// Global cache instance
const cache = new SmartCache();

export function useSmartCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: CacheOptions = {}
): CacheState<T> & {
  refetch: () => Promise<void>;
  invalidate: () => void;
} {
  // Memoize options to avoid recreating callbacks/effects every render
  const opts = useMemo(() => ({
    ...DEFAULT_OPTIONS,
    ...options,
  }), [
    options.ttl,
    options.staleWhileRevalidate,
    options.backgroundRefresh,
    options.retryCount,
    options.retryDelay,
  ]);
  const [state, setState] = useState<CacheState<T>>({
    data: null,
    loading: false,
    error: null,
    isStale: false,
    lastUpdated: null,
    retryCount: 0,
  });

  const retryTimeoutRef = useRef<NodeJS.Timeout>();
  const abortControllerRef = useRef<AbortController>();

  const executeFetch = useCallback(async (useCache = true, isRetry = false): Promise<void> => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setState(prev => ({
      ...prev,
      loading: true,
      error: isRetry ? null : prev.error,
    }));

    try {
      // Check cache first
      if (useCache) {
        const cached = cache.get<T>(key);
        if (cached && !cached.isStale) {
          recordCacheHit(); // Record cache hit
          setState(prev => ({
            ...prev,
            data: cached.data,
            loading: false,
            error: null,
            isStale: false,
            lastUpdated: cached.timestamp,
          }));

          // Schedule background refresh if enabled
          if (opts.backgroundRefresh && !cached.isStale) {
            cache.scheduleRefresh(
              key,
              fetcher,
              opts.ttl,
              (data) => {
                setState(prev => ({
                  ...prev,
                  data,
                  isStale: false,
                  lastUpdated: Date.now(),
                }));
              },
              (error) => {
                setState(prev => ({
                  ...prev,
                  error,
                  isStale: true,
                }));
              }
            );
          }

          return;
        } else if (!cached) {
          recordCacheMiss(); // Record cache miss
        }

        // Use stale data while revalidating
        if (cached && cached.isStale && opts.staleWhileRevalidate) {
          setState(prev => ({
            ...prev,
            data: cached.data,
            isStale: true,
            lastUpdated: cached.timestamp,
          }));
        }
      }

      // Fetch fresh data
      debugLog(`Fetching: ${key}`);
      const data = await fetcher();

      // Cache the result
      cache.set(key, data, opts.ttl);

      setState(prev => ({
        ...prev,
        data,
        loading: false,
        error: null,
        isStale: false,
        lastUpdated: Date.now(),
        retryCount: 0,
      }));

    } catch (error) {
      const err = error as Error;

      // Don't treat abort errors as real errors
      if (err.name === 'AbortError') return;

      errorLog(`Fetch failed: ${key}`, err);

      setState(prev => {
        const newRetryCount = isRetry ? 0 : prev.retryCount + 1;

        // Retry logic
        if (!isRetry && newRetryCount < opts.retryCount) {
          retryTimeoutRef.current = setTimeout(() => {
            executeFetch(false, true);
          }, opts.retryDelay * Math.pow(2, newRetryCount)); // Exponential backoff
        }

        return {
          ...prev,
          loading: false,
          error: err,
          retryCount: newRetryCount,
        };
      });
    }
  }, [
    key,
    fetcher,
    opts.ttl,
    opts.staleWhileRevalidate,
    opts.backgroundRefresh,
    opts.retryCount,
    opts.retryDelay,
  ]);

  const refetch = useCallback(async () => {
    cache.invalidate(key);
    await executeFetch(false);
  }, [key, executeFetch]);

  const invalidate = useCallback(() => {
    cache.invalidate(key);
  }, [key]);

  // Initial fetch
  useEffect(() => {
    executeFetch();
  }, [executeFetch]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    ...state,
    refetch,
    invalidate,
  };
}

// Utility functions for cache management
export const invalidateCache = (key: string) => cache.invalidate(key);
export const invalidateCachePattern = (pattern: string) => cache.invalidatePattern(pattern);
export const clearAllCache = () => cache.clear();
export const getCacheStats = () => cache.getStats();

// React hook for imperative cache operations
export function useCacheManager() {
  return {
    invalidate: invalidateCache,
    invalidatePattern: invalidateCachePattern,
    clear: clearAllCache,
  };
}
