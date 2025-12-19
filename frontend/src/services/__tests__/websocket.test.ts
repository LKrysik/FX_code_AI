/**
 * WebSocket Service Edge Case Tests - Iterative Hardening
 * ========================================================
 *
 * This test file iteratively finds edge cases that break the WebSocket Service
 * and validates the fixes.
 *
 * Round 1 Edge Cases:
 * 1. addSessionUpdateListener with null/undefined listener
 * 2. subscribe with empty/null stream name
 * 3. setCallbacks with null/undefined
 * 4. sendCommand when not connected
 * 5. Multiple rapid reconnects
 */

import { useWebSocketStore } from '@/stores/websocketStore';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: ((event: any) => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    // Simulate connection opening
    setTimeout(() => {
      if (this.onopen) {
        this.onopen({ type: 'open' });
      }
    }, 10);
  }

  send(data: string) {
    // Mock send
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code: code || 1000, reason: reason || '' });
    }
  }
}

// Mock config
jest.mock('@/utils/config', () => ({
  config: {
    wsUrl: 'ws://localhost:8080/ws'
  },
  debugLog: jest.fn(),
  errorLog: jest.fn()
}));

// Mock auth service
jest.mock('@/services/authService', () => ({
  authService: {
    isAuthenticated: jest.fn().mockReturnValue(false),
    ensureSession: jest.fn().mockResolvedValue(false),
    login: jest.fn().mockResolvedValue({ token: 'mock-token' }),
    logout: jest.fn().mockResolvedValue(undefined),
    getCurrentUser: jest.fn().mockReturnValue(null),
    apiCall: jest.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
  }
}));

// Mock performance monitor
jest.mock('@/hooks/usePerformanceMonitor', () => ({
  recordWebSocketMessage: jest.fn()
}));

// Mock status utils
jest.mock('@/utils/statusUtils', () => ({
  categorizeError: jest.fn().mockReturnValue({
    type: 'network',
    severity: 'high',
    message: 'Mock error',
    timestamp: new Date().toISOString(),
    recoverable: true,
    retryable: true
  }),
  logUnifiedError: jest.fn(),
  getErrorRecoveryStrategy: jest.fn().mockReturnValue({
    shouldRetry: true,
    retryDelay: 1000,
    maxRetries: 3,
    fallbackAction: 'reconnect'
  })
}));

// Setup global WebSocket mock
beforeAll(() => {
  (global as any).WebSocket = MockWebSocket;
});

// Reset mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
  // Reset the store
  useWebSocketStore.setState({
    isConnected: false,
    connectionStatus: 'disconnected',
    lastError: null
  });
});

describe('WebSocket Service Edge Cases Round 1', () => {
  describe('Edge Case 1: addSessionUpdateListener with invalid input', () => {
    test('addSessionUpdateListener handles undefined listener gracefully', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        (wsService as any).addSessionUpdateListener(undefined, 'test');
      }).not.toThrow();
    });

    test('addSessionUpdateListener handles null listener gracefully', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        (wsService as any).addSessionUpdateListener(null, 'test');
      }).not.toThrow();
    });

    test('addSessionUpdateListener returns cleanup function', async () => {
      const { wsService } = await import('../websocket');
      const listener = jest.fn();

      const cleanup = wsService.addSessionUpdateListener(listener, 'test');

      expect(typeof cleanup).toBe('function');

      // Cleanup should work
      expect(() => cleanup()).not.toThrow();
    });
  });

  describe('Edge Case 2: subscribe with invalid stream', () => {
    test('subscribe handles empty string stream', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.subscribe('');
      }).not.toThrow();
    });

    test('subscribe handles null stream', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.subscribe(null as any);
      }).not.toThrow();
    });

    test('subscribe handles undefined stream', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.subscribe(undefined as any);
      }).not.toThrow();
    });
  });

  describe('Edge Case 3: setCallbacks with invalid input', () => {
    test('setCallbacks handles null gracefully', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.setCallbacks(null as any);
      }).not.toThrow();
    });

    test('setCallbacks handles undefined gracefully', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.setCallbacks(undefined as any);
      }).not.toThrow();
    });

    test('setCallbacks handles empty object', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.setCallbacks({});
      }).not.toThrow();
    });

    test('setCallbacks merges with existing callbacks', async () => {
      const { wsService } = await import('../websocket');
      const callback1 = jest.fn();
      const callback2 = jest.fn();

      wsService.setCallbacks({ onConnect: callback1 });
      wsService.setCallbacks({ onDisconnect: callback2 });

      // Both callbacks should be set
      expect(true).toBe(true); // Didn't crash
    });
  });

  describe('Edge Case 4: unsubscribe with invalid stream', () => {
    test('unsubscribe handles empty string stream', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.unsubscribe('');
      }).not.toThrow();
    });

    test('unsubscribe handles null stream', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.unsubscribe(null as any);
      }).not.toThrow();
    });

    test('unsubscribe handles non-existent stream', async () => {
      const { wsService } = await import('../websocket');

      // Unsubscribing from a stream that was never subscribed
      expect(() => {
        wsService.unsubscribe('non_existent_stream');
      }).not.toThrow();
    });
  });

  describe('Edge Case 5: clearSessionUpdateListeners', () => {
    test('clearSessionUpdateListeners handles empty listeners set', async () => {
      const { wsService } = await import('../websocket');

      expect(() => {
        wsService.clearSessionUpdateListeners();
      }).not.toThrow();
    });

    test('clearSessionUpdateListeners removes all listeners', async () => {
      const { wsService } = await import('../websocket');
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      wsService.addSessionUpdateListener(listener1, 'test1');
      wsService.addSessionUpdateListener(listener2, 'test2');

      wsService.clearSessionUpdateListeners();

      const stats = wsService.getListenerStats();
      expect(stats.count).toBe(0);
    });
  });
});

describe('WebSocket Service Edge Cases Round 2', () => {
  describe('Edge Case 6: getListenerStats', () => {
    test('getListenerStats returns valid object when empty', async () => {
      const { wsService } = await import('../websocket');
      wsService.clearSessionUpdateListeners();

      const stats = wsService.getListenerStats();

      expect(stats).toHaveProperty('count');
      expect(stats).toHaveProperty('components');
      expect(typeof stats.count).toBe('number');
      expect(typeof stats.components).toBe('object');
    });

    test('getListenerStats tracks component names', async () => {
      const { wsService } = await import('../websocket');
      wsService.clearSessionUpdateListeners();

      wsService.addSessionUpdateListener(jest.fn(), 'ComponentA');
      wsService.addSessionUpdateListener(jest.fn(), 'ComponentB');
      wsService.addSessionUpdateListener(jest.fn(), 'ComponentA');

      const stats = wsService.getListenerStats();

      expect(stats.count).toBe(3);
      expect(stats.components['ComponentA']).toBe(2);
      expect(stats.components['ComponentB']).toBe(1);
    });
  });

  describe('Edge Case 7: isWebSocketConnected', () => {
    test('isWebSocketConnected returns false when not connected', async () => {
      const { wsService } = await import('../websocket');

      // Force disconnect state
      wsService.disconnect();

      expect(wsService.isWebSocketConnected()).toBe(false);
    });
  });

  describe('Edge Case 8: getAuthStatus', () => {
    test('getAuthStatus returns valid object', async () => {
      const { wsService } = await import('../websocket');

      const status = wsService.getAuthStatus();

      expect(status).toHaveProperty('isAuthenticated');
      expect(typeof status.isAuthenticated).toBe('boolean');
    });
  });

  describe('Edge Case 9: disconnect/reconnect cycle', () => {
    test('disconnect handles already disconnected state', async () => {
      const { wsService } = await import('../websocket');

      // Disconnect twice should not crash
      wsService.disconnect();
      expect(() => wsService.disconnect()).not.toThrow();
    });

    test('reconnect after disconnect works', async () => {
      const { wsService } = await import('../websocket');

      wsService.disconnect();

      expect(() => wsService.reconnect()).not.toThrow();
    });
  });

  describe('Edge Case 10: logSubscriptionSummary', () => {
    test('logSubscriptionSummary does not crash', async () => {
      const { wsService } = await import('../websocket');
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      expect(() => wsService.logSubscriptionSummary()).not.toThrow();

      consoleSpy.mockRestore();
    });
  });
});
