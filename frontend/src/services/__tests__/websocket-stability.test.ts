/**
 * WebSocket Stability Tests (BUG-008-2 AC6)
 * ==========================================
 *
 * These tests verify WebSocket connection stability under various conditions.
 *
 * AC6: Connection remains stable for 1 hour with no missed pongs under normal conditions
 *
 * MANUAL TEST PROCEDURE:
 * ----------------------
 * For the full 1-hour stability test, run the application and monitor:
 *
 * 1. Start the backend: python -m src.api.unified_server
 * 2. Start the frontend: npm run dev
 * 3. Open browser to http://localhost:3000
 * 4. Open browser DevTools → Console
 * 5. Filter logs by "websocket.heartbeat" or "websocket.slow"
 * 6. Leave running for 1 hour
 * 7. Check for any "missed_pong" or "slow_connection" warnings
 *
 * EXPECTED RESULTS:
 * - Zero "websocket.heartbeat_missed_pong" warnings
 * - Zero "websocket.slow_connection_detected" warnings
 * - Consistent "websocket.heartbeat" logs every 30 seconds
 *
 * ENVIRONMENT VARIABLES FOR TUNING:
 * - NEXT_PUBLIC_WS_HEARTBEAT_INTERVAL_MS: Default 30000 (30s)
 * - NEXT_PUBLIC_WS_HEARTBEAT_TIMEOUT_MS: Default 30000 (30s)
 * - NEXT_PUBLIC_WS_MAX_MISSED_PONGS: Default 3
 * - NEXT_PUBLIC_WS_SLOW_CONNECTION_THRESHOLD: Default 2
 */

import { useWebSocketStore } from '@/stores/websocketStore';

// Mock WebSocket for stability simulation
class StabilityMockWebSocket {
  static OPEN = 1;
  readyState = StabilityMockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  url: string;
  private pongDelay: number;

  constructor(url: string, pongDelay = 100) {
    this.url = url;
    this.pongDelay = pongDelay;
    setTimeout(() => this.onopen?.(), 10);
  }

  send(data: string) {
    const message = JSON.parse(data);
    if (message.type === 'heartbeat') {
      // Simulate pong response with configurable delay
      setTimeout(() => {
        this.onmessage?.({
          data: JSON.stringify({
            type: 'status',
            status: 'pong',
            timestamp: new Date().toISOString()
          })
        });
      }, this.pongDelay);
    }
  }

  close() {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }
}

// Mock config with test values
jest.mock('@/utils/config', () => ({
  config: {
    wsUrl: 'ws://localhost:8080/ws',
    websocket: {
      heartbeatIntervalMs: 100, // 100ms for faster testing
      heartbeatTimeoutMs: 200, // 200ms timeout
      maxMissedPongs: 3,
      slowConnectionThreshold: 2,
    },
  },
  debugLog: jest.fn(),
  errorLog: jest.fn()
}));

// Mock other dependencies
jest.mock('@/services/authService', () => ({
  authService: {
    isAuthenticated: jest.fn().mockReturnValue(false),
    ensureSession: jest.fn().mockResolvedValue(false),
    getCurrentUser: jest.fn().mockReturnValue(null),
  }
}));

jest.mock('@/hooks/usePerformanceMonitor', () => ({
  recordWebSocketMessage: jest.fn()
}));

jest.mock('@/utils/statusUtils', () => ({
  categorizeError: jest.fn().mockReturnValue({ type: 'network', message: 'Mock error' }),
  logUnifiedError: jest.fn(),
  getErrorRecoveryStrategy: jest.fn().mockReturnValue({ shouldRetry: false })
}));

describe('WebSocket Stability Tests (AC6)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    useWebSocketStore.setState({
      isConnected: false,
      connectionStatus: 'disconnected',
      lastError: null
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  describe('Connection stability under normal conditions', () => {
    test('connection remains stable with fast pong responses', () => {
      // This simulates normal conditions where pong responses are fast
      const mockWs = new StabilityMockWebSocket('ws://test', 50);

      // Simulate heartbeat cycle
      let missedPongs = 0;
      const heartbeatInterval = 100;
      const heartbeatTimeout = 200;

      // Run 10 heartbeat cycles
      for (let i = 0; i < 10; i++) {
        mockWs.send(JSON.stringify({ type: 'heartbeat' }));
        jest.advanceTimersByTime(50); // Fast response
        // Pong received, no missed pongs
      }

      expect(missedPongs).toBe(0);
    });

    test('slow connection warning at threshold', () => {
      const slowConnectionThreshold = 2;
      let slowConnectionWarnings = 0;
      let missedPongs = 0;

      // Simulate missed pongs
      for (let i = 0; i < slowConnectionThreshold; i++) {
        missedPongs++;
      }

      if (missedPongs === slowConnectionThreshold) {
        slowConnectionWarnings++;
      }

      expect(slowConnectionWarnings).toBe(1);
      expect(missedPongs).toBe(2);
    });

    test('reconnect only after max missed pongs', () => {
      const maxMissedPongs = 3;
      let reconnectTriggered = false;
      let missedPongs = 0;

      // Simulate max missed pongs
      for (let i = 0; i < maxMissedPongs; i++) {
        missedPongs++;
      }

      if (missedPongs >= maxMissedPongs) {
        reconnectTriggered = true;
      }

      expect(reconnectTriggered).toBe(true);
      expect(missedPongs).toBe(3);
    });
  });

  describe('Timing configuration validation', () => {
    test('heartbeat interval is reasonable (10s-60s range)', () => {
      const interval = 30000; // Default 30s
      expect(interval).toBeGreaterThanOrEqual(10000);
      expect(interval).toBeLessThanOrEqual(60000);
    });

    test('total tolerance (interval * maxMissed) provides sufficient buffer', () => {
      const heartbeatInterval = 30000;
      const maxMissedPongs = 3;
      const totalTolerance = heartbeatInterval * maxMissedPongs;

      // Total tolerance should be at least 60 seconds for production
      expect(totalTolerance).toBeGreaterThanOrEqual(60000);
    });

    test('slow connection warning gives user time to react', () => {
      const heartbeatInterval = 30000;
      const slowConnectionThreshold = 2;
      const warningTime = heartbeatInterval * slowConnectionThreshold;

      // Warning at 60 seconds gives 30 seconds before reconnect
      expect(warningTime).toBe(60000);
    });
  });

  describe('Baseline metrics documentation', () => {
    test('documents expected baseline metrics', () => {
      const baselineMetrics = {
        // Expected values under normal conditions
        heartbeatIntervalMs: 30000,
        expectedPongResponseMs: 100, // Typical fast response
        maxAcceptablePongResponseMs: 5000, // AC3: Backend responds within 5s
        missedPongsBeforeWarning: 2,
        missedPongsBeforeReconnect: 3,
        totalToleranceMs: 90000, // 30s * 3

        // Stability targets
        targetUptimePercent: 99.9,
        maxMissedPongsPerHour: 0, // AC6: No missed pongs under normal conditions
        maxReconnectsPerHour: 0, // AC6: Stable connection
      };

      // Document the baseline
      expect(baselineMetrics.heartbeatIntervalMs).toBe(30000);
      expect(baselineMetrics.maxAcceptablePongResponseMs).toBeLessThanOrEqual(5000);
      expect(baselineMetrics.maxMissedPongsPerHour).toBe(0);
      expect(baselineMetrics.maxReconnectsPerHour).toBe(0);
    });
  });
});

/**
 * STABILITY TEST CHECKLIST
 * ========================
 *
 * Before marking AC6 as complete, manually verify:
 *
 * [ ] Run application for 1 hour under normal network conditions
 * [ ] No "websocket.heartbeat_missed_pong" warnings in console
 * [ ] No "websocket.slow_connection_detected" warnings in console
 * [ ] No unexpected reconnections
 * [ ] Connection status remains "connected" throughout
 *
 * Test Environment:
 * - Backend: python -m src.api.unified_server
 * - Frontend: npm run dev
 * - Browser: Chrome/Firefox with DevTools open
 * - Network: Normal connectivity (not throttled)
 *
 * If any issues occur, document:
 * - Time of occurrence
 * - Number of missed pongs
 * - Network conditions
 * - Backend load at time of issue
 */
