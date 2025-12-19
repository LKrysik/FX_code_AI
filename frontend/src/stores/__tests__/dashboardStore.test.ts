/**
 * Dashboard Store Edge Case Tests - Iterative Hardening
 * ======================================================
 *
 * This test file iteratively finds edge cases that break the Dashboard Store
 * and validates the fixes.
 *
 * Round 1 Edge Cases:
 * 1. addSignal with undefined/null signal - could crash
 * 2. addIndicator with partial/null data - findIndex issues
 * 3. updateMarketData with undefined updates - spread issues
 * 4. setMarketData with null/undefined array - iteration crash
 * 5. Concurrent rapid updates - state consistency
 */

import { useDashboardStore } from '../dashboardStore';

// Get a fresh store for each test
const getStore = () => useDashboardStore;

// Reset store state between tests
beforeEach(() => {
  const store = getStore();
  store.setState({
    marketData: [],
    activeSignals: [],
    indicators: [],
    loading: true,
    marketDataLoading: false,
    signalsLoading: false,
    indicatorsLoading: false,
    error: null,
    marketDataError: null,
    signalsError: null,
    indicatorsError: null,
  });
});

describe('DashboardStore Edge Cases Round 1', () => {
  describe('Edge Case 1: addSignal with invalid data', () => {
    test('addSignal handles undefined signal gracefully', () => {
      const store = getStore();
      const initialState = store.getState();

      // Should not throw
      expect(() => {
        initialState.addSignal(undefined as any);
      }).not.toThrow();

      const state = store.getState();
      expect(Array.isArray(state.activeSignals)).toBe(true);
      // After fix: undefined signal is skipped, so array should be empty
      expect(state.activeSignals.length).toBe(0);
    });

    test('addSignal handles null signal gracefully', () => {
      const store = getStore();
      const initialState = store.getState();

      // Should not throw
      expect(() => {
        initialState.addSignal(null as any);
      }).not.toThrow();

      const state = store.getState();
      expect(Array.isArray(state.activeSignals)).toBe(true);
      // After fix: null signal is skipped, so array should be empty
      expect(state.activeSignals.length).toBe(0);
    });

    test('addSignal handles empty object signal', () => {
      const store = getStore();
      store.getState().addSignal({} as any);

      const state = store.getState();
      // Empty object is truthy, so it gets added
      expect(state.activeSignals.length).toBe(1);
    });
  });

  describe('Edge Case 2: addIndicator with partial/invalid data', () => {
    test('addIndicator handles undefined indicator gracefully', () => {
      const store = getStore();

      expect(() => {
        store.getState().addIndicator(undefined as any);
      }).not.toThrow();

      const state = store.getState();
      expect(Array.isArray(state.indicators)).toBe(true);
      // After fix: undefined indicator is skipped
      expect(state.indicators.length).toBe(0);
    });

    test('addIndicator handles indicator without symbol property', () => {
      const store = getStore();
      store.getState().addIndicator({ name: 'test', value: 123 } as any);

      const state = store.getState();
      expect(Array.isArray(state.indicators)).toBe(true);
    });

    test('addIndicator handles indicator without name property', () => {
      const store = getStore();
      store.getState().addIndicator({ symbol: 'BTCUSDT', value: 123 } as any);

      const state = store.getState();
      expect(Array.isArray(state.indicators)).toBe(true);
    });

    test('addIndicator correctly updates existing indicator', () => {
      const store = getStore();

      // Add initial indicator
      store.getState().addIndicator({
        symbol: 'BTCUSDT',
        name: 'RSI',
        value: 50,
        timestamp: '2024-01-01T00:00:00Z'
      });

      expect(store.getState().indicators.length).toBe(1);

      // Update same indicator
      store.getState().addIndicator({
        symbol: 'BTCUSDT',
        name: 'RSI',
        value: 75,
        timestamp: '2024-01-01T00:01:00Z'
      });

      // Should update, not add duplicate
      const state = store.getState();
      expect(state.indicators.length).toBe(1);
      expect(state.indicators[0].value).toBe(75);
    });
  });

  describe('Edge Case 3: updateMarketData with invalid data', () => {
    test('updateMarketData handles undefined updates gracefully', () => {
      const store = getStore();

      // First set some market data
      store.getState().setMarketData([
        { symbol: 'BTCUSDT', price: 50000, priceChange24h: 5, volume24h: 1000000 }
      ]);

      // Try to update with undefined - should not throw
      expect(() => {
        store.getState().updateMarketData('BTCUSDT', undefined as any);
      }).not.toThrow();

      const state = store.getState();
      expect(Array.isArray(state.marketData)).toBe(true);
    });

    test('updateMarketData handles null updates gracefully', () => {
      const store = getStore();

      store.getState().setMarketData([
        { symbol: 'BTCUSDT', price: 50000, priceChange24h: 5, volume24h: 1000000 }
      ]);

      expect(() => {
        store.getState().updateMarketData('BTCUSDT', null as any);
      }).not.toThrow();

      const state = store.getState();
      expect(Array.isArray(state.marketData)).toBe(true);
    });

    test('updateMarketData handles non-existent symbol', () => {
      const store = getStore();

      store.getState().setMarketData([
        { symbol: 'BTCUSDT', price: 50000, priceChange24h: 5, volume24h: 1000000 }
      ]);

      const beforeCount = store.getState().marketData.length;

      // Update non-existent symbol should not crash and should not change data
      store.getState().updateMarketData('NONEXISTENT', { price: 999 });

      const state = store.getState();
      expect(state.marketData.length).toBe(beforeCount);
      expect(state.marketData[0].symbol).toBe('BTCUSDT');
    });
  });

  describe('Edge Case 4: setMarketData with invalid arrays', () => {
    test('setMarketData handles null gracefully', () => {
      const store = getStore();

      expect(() => {
        store.getState().setMarketData(null as any);
      }).not.toThrow();

      const state = store.getState();
      // Should either handle or keep previous valid state
      expect(state.marketData !== undefined).toBe(true);
    });

    test('setMarketData handles undefined gracefully', () => {
      const store = getStore();

      // Should not throw
      expect(() => {
        store.getState().setMarketData(undefined as any);
      }).not.toThrow();

      const state = store.getState();
      // State should still be valid
      expect(state.marketData !== undefined).toBe(true);
    });

    test('setMarketData handles non-array (object) gracefully', () => {
      const store = getStore();

      expect(() => {
        store.getState().setMarketData({ symbol: 'BTCUSDT' } as any);
      }).not.toThrow();
      // Didn't crash
    });
  });

  describe('Edge Case 5: updateIndicator edge cases', () => {
    test('updateIndicator handles empty string symbol', () => {
      const store = getStore();

      store.getState().setIndicators([
        { symbol: 'BTCUSDT', name: 'RSI', value: 50, timestamp: '2024-01-01T00:00:00Z' }
      ]);

      // Empty symbol should not crash
      store.getState().updateIndicator('', 'RSI', { value: 75 });

      // Original indicator should be unchanged
      expect(store.getState().indicators[0].value).toBe(50);
    });

    test('updateIndicator handles null symbol', () => {
      const store = getStore();

      store.getState().setIndicators([
        { symbol: 'BTCUSDT', name: 'RSI', value: 50, timestamp: '2024-01-01T00:00:00Z' }
      ]);

      expect(() => {
        store.getState().updateIndicator(null as any, 'RSI', { value: 75 });
      }).not.toThrow();
      // Didn't crash
    });
  });
});

describe('DashboardStore Edge Cases Round 2', () => {
  describe('Edge Case 6: Signal limit overflow', () => {
    test('addSignal respects 10 signal limit', () => {
      const store = getStore();

      // Add 15 signals
      for (let i = 0; i < 15; i++) {
        store.getState().addSignal({
          id: `signal_${i}`,
          symbol: 'BTCUSDT',
          signalType: 'pump',
          magnitude: i,
          confidence: 50,
          timestamp: new Date().toISOString(),
          strategy: 'test'
        });
      }

      const state = store.getState();
      // Should only have 10 signals (the limit)
      expect(state.activeSignals.length).toBe(10);

      // The latest signal should be first
      expect(state.activeSignals[0].id).toBe('signal_14');
    });
  });

  describe('Edge Case 7: Rapid state updates', () => {
    test('handles rapid sequential updates without corruption', () => {
      const store = getStore();

      // Rapid fire updates
      for (let i = 0; i < 100; i++) {
        store.getState().setMarketData([
          { symbol: `SYMBOL_${i}`, price: i, priceChange24h: i, volume24h: i }
        ]);
      }

      // Final state should be last update
      const state = store.getState();
      expect(state.marketData.length).toBe(1);
      expect(state.marketData[0].symbol).toBe('SYMBOL_99');
    });
  });

  describe('Edge Case 8: setActiveSignals edge cases', () => {
    test('setActiveSignals handles empty array', () => {
      const store = getStore();

      // First add some signals
      store.getState().addSignal({
        id: 'test1',
        symbol: 'BTCUSDT',
        signalType: 'pump',
        magnitude: 10,
        confidence: 50,
        timestamp: new Date().toISOString(),
        strategy: 'test'
      });

      expect(store.getState().activeSignals.length).toBe(1);

      // Clear with empty array
      store.getState().setActiveSignals([]);

      expect(store.getState().activeSignals.length).toBe(0);
    });
  });

  describe('Edge Case 9: Loading state consistency', () => {
    test('loading states are independent', () => {
      const store = getStore();

      // Set different loading states
      store.getState().setMarketData([]);

      const state = store.getState();
      expect(state.marketDataLoading).toBe(false);
      expect(state.signalsLoading).toBe(false);
      expect(state.indicatorsLoading).toBe(false);
    });
  });

  describe('Edge Case 10: reset() clears all state', () => {
    test('reset returns to initial state', () => {
      const store = getStore();

      // Populate state
      store.getState().setMarketData([
        { symbol: 'BTCUSDT', price: 50000, priceChange24h: 5, volume24h: 1000000 }
      ]);
      store.getState().addSignal({
        id: 'test1',
        symbol: 'BTCUSDT',
        signalType: 'pump',
        magnitude: 10,
        confidence: 50,
        timestamp: new Date().toISOString(),
        strategy: 'test'
      });
      store.getState().setError('Test error');

      expect(store.getState().marketData.length).toBe(1);
      expect(store.getState().activeSignals.length).toBe(1);
      expect(store.getState().error).toBe('Test error');

      // Reset
      store.getState().reset();

      // Verify all state is cleared
      const state = store.getState();
      expect(state.marketData.length).toBe(0);
      expect(state.activeSignals.length).toBe(0);
      expect(state.error).toBeNull();
      expect(state.loading).toBe(true); // Initial loading state
    });
  });
});
