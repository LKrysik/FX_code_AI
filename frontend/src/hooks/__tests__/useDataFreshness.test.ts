/**
 * useDataFreshness Hook Tests
 * ===========================
 * BUG-008-3: Tests for data freshness tracking and stale detection.
 */

import { renderHook, act } from '@testing-library/react';
import { useDataFreshness, useMultiStreamFreshness, getOverallFreshness, DataFreshnessResult } from '../useDataFreshness';

describe('useDataFreshness', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Basic functionality', () => {
    test('returns "Just now" for recent updates', () => {
      const now = Date.now();
      const { result } = renderHook(() => useDataFreshness(now));

      expect(result.current.formattedAge).toBe('Just now');
      expect(result.current.ageSeconds).toBeLessThan(5);
      expect(result.current.isStale).toBe(false);
      expect(result.current.isVeryStale).toBe(false);
      expect(result.current.opacity).toBe(1.0);
      expect(result.current.showStaleBadge).toBe(false);
    });

    test('returns formatted seconds for updates < 60s old', () => {
      const thirtySecondsAgo = Date.now() - 30000;
      const { result } = renderHook(() => useDataFreshness(thirtySecondsAgo));

      expect(result.current.formattedAge).toBe('Updated 30s ago');
      expect(result.current.ageSeconds).toBeCloseTo(30, 0);
      expect(result.current.isStale).toBe(false);
      expect(result.current.isVeryStale).toBe(false);
    });

    test('returns formatted minutes for updates >= 60s old', () => {
      const twoMinutesAgo = Date.now() - 120000;
      const { result } = renderHook(() => useDataFreshness(twoMinutesAgo));

      expect(result.current.formattedAge).toBe('Updated 2m ago');
      expect(result.current.ageSeconds).toBeCloseTo(120, 0);
    });
  });

  describe('Stale detection (AC3, AC4)', () => {
    test('marks data as stale when > 60 seconds old', () => {
      const sixtyFiveSecondsAgo = Date.now() - 65000;
      const { result } = renderHook(() => useDataFreshness(sixtyFiveSecondsAgo));

      expect(result.current.isStale).toBe(true);
      expect(result.current.isVeryStale).toBe(false);
      expect(result.current.opacity).toBe(0.7);
      expect(result.current.showStaleBadge).toBe(false);
    });

    test('marks data as very stale when > 120 seconds old', () => {
      const threeMinutesAgo = Date.now() - 180000;
      const { result } = renderHook(() => useDataFreshness(threeMinutesAgo));

      expect(result.current.isStale).toBe(true);
      expect(result.current.isVeryStale).toBe(true);
      expect(result.current.opacity).toBe(0.7);
      expect(result.current.showStaleBadge).toBe(true);
    });
  });

  describe('Input formats', () => {
    test('accepts Date object', () => {
      const date = new Date(Date.now() - 10000);
      const { result } = renderHook(() => useDataFreshness(date));

      expect(result.current.ageSeconds).toBeCloseTo(10, 0);
      expect(result.current.lastUpdateTimestamp).toBe(date.getTime());
    });

    test('accepts ISO string', () => {
      const isoString = new Date(Date.now() - 20000).toISOString();
      const { result } = renderHook(() => useDataFreshness(isoString));

      expect(result.current.ageSeconds).toBeCloseTo(20, 0);
    });

    test('accepts timestamp number', () => {
      const timestamp = Date.now() - 15000;
      const { result } = renderHook(() => useDataFreshness(timestamp));

      expect(result.current.ageSeconds).toBeCloseTo(15, 0);
      expect(result.current.lastUpdateTimestamp).toBe(timestamp);
    });

    test('handles null gracefully', () => {
      const { result } = renderHook(() => useDataFreshness(null));

      expect(result.current.formattedAge).toBe('No data');
      expect(result.current.isStale).toBe(true);
      expect(result.current.isVeryStale).toBe(true);
      expect(result.current.opacity).toBe(0.5);
      expect(result.current.showStaleBadge).toBe(true);
      expect(result.current.lastUpdateTimestamp).toBeNull();
    });

    test('handles undefined gracefully', () => {
      const { result } = renderHook(() => useDataFreshness(undefined));

      expect(result.current.formattedAge).toBe('No data');
      expect(result.current.isStale).toBe(true);
    });
  });

  describe('Auto-refresh', () => {
    test('updates formattedAge over time', () => {
      const initialTime = Date.now();
      jest.setSystemTime(initialTime);

      const lastUpdate = initialTime;
      const { result } = renderHook(() => useDataFreshness(lastUpdate, 1000));

      expect(result.current.formattedAge).toBe('Just now');

      // Advance time by 30 seconds
      act(() => {
        jest.setSystemTime(initialTime + 30000);
        jest.advanceTimersByTime(1000);
      });

      // Allow 2s tolerance for timing variations
      expect(result.current.ageSeconds).toBeGreaterThanOrEqual(29);
      expect(result.current.ageSeconds).toBeLessThanOrEqual(32);
    });
  });
});

describe('useMultiStreamFreshness', () => {
  test('tracks multiple streams independently', () => {
    const now = Date.now();
    const streams = {
      prices: now - 5000,        // 5s ago - fresh
      indicators: now - 70000,  // 70s ago - stale
      stateMachines: now - 150000, // 150s ago - very stale
    };

    const { result } = renderHook(() => useMultiStreamFreshness(streams));

    expect(result.current.prices.isStale).toBe(false);
    expect(result.current.indicators.isStale).toBe(true);
    expect(result.current.indicators.isVeryStale).toBe(false);
    expect(result.current.stateMachines.isVeryStale).toBe(true);
  });

  test('handles empty streams object', () => {
    const { result } = renderHook(() => useMultiStreamFreshness({}));

    expect(Object.keys(result.current)).toHaveLength(0);
  });
});

describe('getOverallFreshness', () => {
  test('returns stalest stream status', () => {
    const streamResults: Record<string, DataFreshnessResult> = {
      prices: {
        formattedAge: 'Updated 5s ago',
        ageSeconds: 5,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 5000,
      },
      indicators: {
        formattedAge: 'Updated 3m ago',
        ageSeconds: 180,
        isStale: true,
        isVeryStale: true,
        opacity: 0.7,
        showStaleBadge: true,
        lastUpdateTimestamp: Date.now() - 180000,
      },
    };

    const overall = getOverallFreshness(streamResults);

    expect(overall.ageSeconds).toBe(180);
    expect(overall.isVeryStale).toBe(true);
    expect(overall.showStaleBadge).toBe(true);
  });

  test('returns default for empty streams', () => {
    const overall = getOverallFreshness({});

    expect(overall.formattedAge).toBe('No data');
    expect(overall.isStale).toBe(true);
  });
});
