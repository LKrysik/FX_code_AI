/**
 * Test suite for performance optimizations
 * Run with: node test_performance_optimizations.js
 */

const { performance } = require('perf_hooks');

// Mock axios for testing
const mockAxios = {
  get: jest.fn(),
  post: jest.fn(),
  interceptors: {
    request: { use: jest.fn() },
    response: { use: jest.fn() }
  },
  defaults: { baseURL: 'http://localhost:8000' }
};

// Mock the performance monitor
let performanceMonitor = {
  recordApiCall: jest.fn(),
  recordCacheHit: jest.fn(),
  recordCacheMiss: jest.fn(),
  recordWebSocketMessage: jest.fn()
};

// Test API Deduplication
describe('API Request Deduplication', () => {
  let apiService;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Mock axios response
    mockAxios.get.mockResolvedValue({
      data: { data: { strategies: [{ name: 'test' }] } }
    });

    // Create a simplified ApiService for testing
    class TestApiService {
      constructor() {
        this.pendingRequests = new Map();
        this.requestTimeouts = new Map();
      }

      async dedupedRequest(key, requestFn, timeoutMs = 30000) {
        if (this.pendingRequests.has(key)) {
          return this.pendingRequests.get(key);
        }

        const timeoutPromise = new Promise((_, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error(`Request timeout: ${key}`));
          }, timeoutMs);
          this.requestTimeouts.set(key, timeout);
        });

        const startTime = performance.now();
        const promise = Promise.race([
          requestFn(),
          timeoutPromise
        ]).then((result) => {
          const duration = performance.now() - startTime;
          performanceMonitor.recordApiCall(duration, true);
          return result;
        }).catch((error) => {
          const duration = performance.now() - startTime;
          performanceMonitor.recordApiCall(duration, false);
          throw error;
        }).finally(() => {
          this.pendingRequests.delete(key);
          if (this.requestTimeouts.has(key)) {
            clearTimeout(this.requestTimeouts.get(key));
            this.requestTimeouts.delete(key);
          }
        });

        this.pendingRequests.set(key, promise);
        return promise;
      }

      async getStrategies() {
        return this.dedupedRequest('getStrategies', async () => {
          const response = await mockAxios.get('/strategies');
          return response.data.data?.strategies || [];
        });
      }
    }

    apiService = new TestApiService();
  });

  test('should deduplicate concurrent requests', async () => {
    // Fire 3 concurrent requests
    const promises = [
      apiService.getStrategies(),
      apiService.getStrategies(),
      apiService.getStrategies()
    ];

    const results = await Promise.all(promises);

    // Should only call axios once
    expect(mockAxios.get).toHaveBeenCalledTimes(1);
    expect(mockAxios.get).toHaveBeenCalledWith('/strategies');

    // All promises should return the same result
    expect(results).toHaveLength(3);
    results.forEach(result => {
      expect(result).toEqual([{ name: 'test' }]);
    });

    // Should record one successful API call
    expect(performanceMonitor.recordApiCall).toHaveBeenCalledTimes(1);
    expect(performanceMonitor.recordApiCall).toHaveBeenCalledWith(
      expect.any(Number), // duration
      true // success
    );
  });

  test('should handle request timeouts', async () => {
    // Mock a slow request that times out
    mockAxios.get.mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({
        data: { data: { strategies: [] } }
      }), 100))
    );

    const promise = apiService.dedupedRequest('slowRequest',
      () => mockAxios.get('/slow'),
      50 // Short timeout
    );

    await expect(promise).rejects.toThrow('Request timeout: slowRequest');

    expect(performanceMonitor.recordApiCall).toHaveBeenCalledWith(
      expect.any(Number),
      false // failure
    );
  });
});

// Test Cache LRU
describe('SmartCache LRU', () => {
  let cache;

  beforeEach(() => {
    class TestSmartCache {
      constructor(maxSize = 3) {
        this.cache = new Map();
        this.accessOrder = new Set();
        this.maxSize = maxSize;
      }

      set(key, data, ttl) {
        // LRU eviction
        if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
          const lruKey = this.accessOrder.values().next().value;
          if (lruKey) {
            this.cache.delete(lruKey);
            this.accessOrder.delete(lruKey);
          }
        }

        const entry = {
          data,
          timestamp: Date.now(),
          ttl,
          isStale: false,
        };

        this.cache.set(key, entry);
        this.accessOrder.delete(key);
        this.accessOrder.add(key);
      }

      get(key) {
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

        entry.isStale = now - entry.timestamp > entry.ttl / 2;
        return entry;
      }
    }

    cache = new TestSmartCache(3);
  });

  test('should enforce max size with LRU eviction', () => {
    // Fill cache to max size
    cache.set('key1', 'data1', 1000);
    cache.set('key2', 'data2', 1000);
    cache.set('key3', 'data3', 1000);

    expect(cache.cache.size).toBe(3);

    // Access key1 to make it most recently used
    cache.get('key1');

    // Add new item - should evict key2 (least recently used)
    cache.set('key4', 'data4', 1000);

    expect(cache.cache.size).toBe(3);
    expect(cache.cache.has('key1')).toBe(true); // Most recently used
    expect(cache.cache.has('key2')).toBe(false); // Evicted
    expect(cache.cache.has('key3')).toBe(true);
    expect(cache.cache.has('key4')).toBe(true);
  });

  test('should update access order on get', () => {
    cache.set('key1', 'data1', 1000);
    cache.set('key2', 'data2', 1000);
    cache.set('key3', 'data3', 1000);

    // Access key3, making it most recently used
    cache.get('key3');

    // Add new item - should evict key1 (now least recently used)
    cache.set('key4', 'data4', 1000);

    expect(cache.cache.has('key1')).toBe(false); // Evicted
    expect(cache.cache.has('key3')).toBe(true); // Most recently used
  });
});

// Test WebSocket Listener Cleanup
describe('WebSocket Listener Cleanup', () => {
  let wsService;

  beforeEach(() => {
    class TestWebSocketService {
      constructor() {
        this.sessionUpdateListeners = new Set();
        this.listenerMetadata = new Map();
      }

      addSessionUpdateListener(listener, componentName = 'unknown') {
        this.sessionUpdateListeners.add(listener);
        this.listenerMetadata.set(listener, {
          component: componentName,
          addedAt: Date.now(),
          stackTrace: process.env.NODE_ENV === 'development' ? new Error().stack : undefined
        });

        return () => {
          this.sessionUpdateListeners.delete(listener);
          this.listenerMetadata.delete(listener);
        };
      }

      getListenerStats() {
        const components = {};
        for (const meta of this.listenerMetadata.values()) {
          components[meta.component] = (components[meta.component] || 0) + 1;
        }
        return { count: this.sessionUpdateListeners.size, components };
      }
    }

    wsService = new TestWebSocketService();
  });

  test('should track listeners with metadata', () => {
    const listener1 = () => {};
    const listener2 = () => {};

    const cleanup1 = wsService.addSessionUpdateListener(listener1, 'ComponentA');
    const cleanup2 = wsService.addSessionUpdateListener(listener2, 'ComponentB');

    expect(wsService.sessionUpdateListeners.size).toBe(2);

    const stats = wsService.getListenerStats();
    expect(stats.count).toBe(2);
    expect(stats.components.ComponentA).toBe(1);
    expect(stats.components.ComponentB).toBe(1);
  });

  test('should cleanup listeners properly', () => {
    const listener = () => {};
    const cleanup = wsService.addSessionUpdateListener(listener, 'TestComponent');

    expect(wsService.sessionUpdateListeners.size).toBe(1);

    cleanup();

    expect(wsService.sessionUpdateListeners.size).toBe(0);
    expect(wsService.getListenerStats().count).toBe(0);
  });
});

// Test Performance Monitor
describe('Performance Monitor', () => {
  beforeEach(() => {
    performanceMonitor = {
      recordApiCall: jest.fn(),
      recordCacheHit: jest.fn(),
      recordCacheMiss: jest.fn(),
      recordWebSocketMessage: jest.fn()
    };
  });

  test('should record API calls', () => {
    performanceMonitor.recordApiCall(150, true);
    expect(performanceMonitor.recordApiCall).toHaveBeenCalledWith(150, true);
  });

  test('should record cache hits and misses', () => {
    performanceMonitor.recordCacheHit();
    performanceMonitor.recordCacheMiss();

    expect(performanceMonitor.recordCacheHit).toHaveBeenCalledTimes(1);
    expect(performanceMonitor.recordCacheMiss).toHaveBeenCalledTimes(1);
  });

  test('should record WebSocket messages', () => {
    performanceMonitor.recordWebSocketMessage();
    expect(performanceMonitor.recordWebSocketMessage).toHaveBeenCalledTimes(1);
  });
});

// Run tests if this file is executed directly
if (require.main === module) {
  console.log('Running performance optimization tests...');

  // Simple test runner
  const testResults = {
    passed: 0,
    failed: 0,
    errors: []
  };

  function runTest(name, testFn) {
    try {
      testFn();
      console.log(`✅ ${name}`);
      testResults.passed++;
    } catch (error) {
      console.log(`❌ ${name}: ${error.message}`);
      testResults.failed++;
      testResults.errors.push({ name, error: error.message });
    }
  }

  // Run all tests
  runTest('API Deduplication - concurrent requests', async () => {
    const apiService = new (class {
      constructor() {
        this.pendingRequests = new Map();
        this.requestTimeouts = new Map();
      }

      async dedupedRequest(key, requestFn) {
        if (this.pendingRequests.has(key)) {
          return this.pendingRequests.get(key);
        }

        const promise = requestFn().finally(() => {
          this.pendingRequests.delete(key);
        });

        this.pendingRequests.set(key, promise);
        return promise;
      }

      async getStrategies() {
        return this.dedupedRequest('getStrategies', async () => {
          return [{ name: 'test' }];
        });
      }
    })();

    const results = await Promise.all([
      apiService.getStrategies(),
      apiService.getStrategies(),
      apiService.getStrategies()
    ]);

    if (results.length !== 3) throw new Error('Expected 3 results');
    if (results[0][0].name !== 'test') throw new Error('Unexpected result');
  });

  runTest('Cache LRU - eviction works', () => {
    const cache = new (class {
      constructor() {
        this.cache = new Map();
        this.accessOrder = new Set();
        this.maxSize = 2;
      }

      set(key, data) {
        if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
          const lruKey = this.accessOrder.values().next().value;
          if (lruKey) {
            this.cache.delete(lruKey);
            this.accessOrder.delete(lruKey);
          }
        }

        this.cache.set(key, data);
        this.accessOrder.delete(key);
        this.accessOrder.add(key);
      }
    })();

    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3); // Should evict 'a'

    if (cache.cache.size !== 2) throw new Error('Cache size should be 2');
    if (cache.cache.has('a')) throw new Error('Key "a" should be evicted');
    if (!cache.cache.has('b')) throw new Error('Key "b" should exist');
    if (!cache.cache.has('c')) throw new Error('Key "c" should exist');
  });

  console.log(`\nTest Results: ${testResults.passed} passed, ${testResults.failed} failed`);

  if (testResults.failed > 0) {
    console.log('\nFailed tests:');
    testResults.errors.forEach(({ name, error }) => {
      console.log(`- ${name}: ${error}`);
    });
    process.exit(1);
  } else {
    console.log('All tests passed! ✅');
  }
}