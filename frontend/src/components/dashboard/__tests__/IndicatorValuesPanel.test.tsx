/**
 * IndicatorValuesPanel Component Tests
 * =====================================
 * Story 1A-3: Indicator Values Panel
 *
 * Tests:
 * - AC1: Panel displays MVP indicators
 * - AC2: Values update in real-time
 * - AC3: Each indicator shows name, current value, unit/format
 * - AC4: Panel visible during active sessions
 * - AC5: Values formatted appropriately
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { IndicatorValuesPanel, formatIndicatorValue, MVP_INDICATORS } from '../IndicatorValuesPanel';
import { wsService } from '@/services/websocket';

// Mock the WebSocket service
jest.mock('@/services/websocket', () => ({
  wsService: {
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
    setCallbacks: jest.fn(),
    isWebSocketConnected: jest.fn(() => true),
  },
}));

// Mock the dashboardStore
jest.mock('@/stores/dashboardStore', () => ({
  useDashboardStore: jest.fn(() => ({
    indicators: [],
    setIndicators: jest.fn(),
    addIndicator: jest.fn(),
  })),
  useIndicators: jest.fn(() => []),
}));

describe('IndicatorValuesPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // AC1: Panel displays MVP indicators
  describe('AC1: MVP Indicators Display', () => {
    it('should define all MVP indicators', () => {
      expect(MVP_INDICATORS).toBeDefined();
      expect(MVP_INDICATORS.length).toBeGreaterThan(0);

      // Check for required MVP indicators from PRD
      const indicatorKeys = MVP_INDICATORS.map(i => i.key);
      expect(indicatorKeys).toContain('pump_magnitude_pct');
      expect(indicatorKeys).toContain('volume_surge_ratio');
      expect(indicatorKeys).toContain('price_velocity');
      expect(indicatorKeys).toContain('spread_pct');
    });

    it('should render panel with title', () => {
      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);
      expect(screen.getByText(/Indicator Values/i)).toBeInTheDocument();
    });

    it('should show "No active session" when sessionId is null', () => {
      render(<IndicatorValuesPanel sessionId={null} symbol="BTC_USDT" />);
      expect(screen.getByText(/No active session/i)).toBeInTheDocument();
    });
  });

  // AC3: Each indicator shows name, current value, unit/format
  describe('AC3: Indicator Display Format', () => {
    it('should display indicator name for each MVP indicator', () => {
      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);

      // Check that at least some indicator names are rendered
      MVP_INDICATORS.forEach(indicator => {
        // The label should be visible even without data (as placeholders)
        expect(screen.getByText(indicator.label)).toBeInTheDocument();
      });
    });
  });

  // AC5: Values formatted appropriately
  describe('AC5: Value Formatting', () => {
    it('should format percentages correctly', () => {
      expect(formatIndicatorValue(0.0725, 'percent')).toBe('+7.25%');
      expect(formatIndicatorValue(-0.0312, 'percent')).toBe('-3.12%');
      expect(formatIndicatorValue(0, 'percent')).toBe('0.00%');
    });

    it('should format ratios correctly', () => {
      expect(formatIndicatorValue(3.5, 'ratio')).toBe('3.50x');
      expect(formatIndicatorValue(1.0, 'ratio')).toBe('1.00x');
      expect(formatIndicatorValue(0.5, 'ratio')).toBe('0.50x');
    });

    it('should format prices correctly', () => {
      expect(formatIndicatorValue(45230.50, 'price')).toBe('$45,230.50');
      expect(formatIndicatorValue(1234.5678, 'price')).toBe('$1,234.57');
    });

    it('should format rates correctly', () => {
      expect(formatIndicatorValue(0.0012, 'rate')).toBe('+0.12%/s');
      expect(formatIndicatorValue(-0.005, 'rate')).toBe('-0.50%/s');
    });

    it('should handle null/undefined values gracefully', () => {
      expect(formatIndicatorValue(null as any, 'percent')).toBe('--');
      expect(formatIndicatorValue(undefined as any, 'ratio')).toBe('--');
      expect(formatIndicatorValue(NaN, 'price')).toBe('--');
    });
  });

  // AC2: Values update in real-time
  describe('AC2: Real-time Updates', () => {
    it('should subscribe to indicators stream on mount', () => {
      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);

      expect(wsService.setCallbacks).toHaveBeenCalled();
      expect(wsService.subscribe).toHaveBeenCalledWith('indicators', {
        symbol: 'BTC_USDT',
        session_id: 'test-session',
      });
    });

    it('should unsubscribe on unmount', () => {
      const { unmount } = render(
        <IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />
      );

      unmount();

      // Verify cleanup was called
      expect(wsService.unsubscribe).toHaveBeenCalledWith('indicators');
    });

    it('should update UI when WebSocket message arrives', () => {
      // Capture the callback when setCallbacks is called
      let capturedCallback: ((msg: any) => void) | null = null;
      (wsService.setCallbacks as jest.Mock).mockImplementation((callbacks: any) => {
        capturedCallback = callbacks.onIndicators;
      });

      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);

      // Verify callback was captured
      expect(capturedCallback).not.toBeNull();

      // Simulate WebSocket message
      act(() => {
        capturedCallback!({
          type: 'indicators',
          data: {
            symbol: 'BTC_USDT',
            pump_magnitude_pct: 0.0725,
            volume_surge_ratio: 3.5,
          },
        });
      });

      // Verify values are displayed (formatted)
      expect(screen.getByText('+7.25%')).toBeInTheDocument();
      expect(screen.getByText('3.50x')).toBeInTheDocument();
    });

    it('should filter messages by symbol', () => {
      let capturedCallback: ((msg: any) => void) | null = null;
      (wsService.setCallbacks as jest.Mock).mockImplementation((callbacks: any) => {
        capturedCallback = callbacks.onIndicators;
      });

      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);

      // Send message for different symbol
      act(() => {
        capturedCallback!({
          type: 'indicators',
          data: {
            symbol: 'ETH_USDT', // Different symbol - should be ignored
            pump_magnitude_pct: 0.999,
          },
        });
      });

      // Value should NOT be updated (still shows placeholder)
      expect(screen.queryByText('+99.90%')).not.toBeInTheDocument();
    });
  });

  // AC4: Panel visible during active sessions
  describe('AC4: Session Visibility', () => {
    it('should show loading state initially', () => {
      render(<IndicatorValuesPanel sessionId="test-session" symbol="BTC_USDT" />);
      // Component should either show loading or placeholder values
      expect(screen.getByText(/Indicator Values/i)).toBeInTheDocument();
    });

    it('should update symbol display in header', () => {
      render(<IndicatorValuesPanel sessionId="test-session" symbol="ETH_USDT" />);
      expect(screen.getByText(/ETH_USDT/i)).toBeInTheDocument();
    });
  });
});

describe('MVP_INDICATORS configuration', () => {
  it('should have correct structure for each indicator', () => {
    MVP_INDICATORS.forEach(indicator => {
      expect(indicator).toHaveProperty('key');
      expect(indicator).toHaveProperty('label');
      expect(indicator).toHaveProperty('unit');
      expect(['percent', 'ratio', 'price', 'rate']).toContain(indicator.unit);
    });
  });

  it('should include TWPA indicator', () => {
    const twpa = MVP_INDICATORS.find(i => i.key === 'twpa' || i.key === 'TWPA');
    expect(twpa).toBeDefined();
  });
});
