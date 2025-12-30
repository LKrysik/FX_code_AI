/**
 * useDataFreshness Hook
 * =====================
 * BUG-008-3: Track data freshness and provide stale data indicators.
 *
 * Provides:
 * - Formatted "Updated X seconds ago" string
 * - Stale detection (>60s = stale, >120s = very stale)
 * - Visual degradation flags (opacity, badge)
 * - Auto-refresh every second for live updates
 *
 * Usage:
 * ```tsx
 * const { formattedAge, isStale, isVeryStale, ageSeconds } = useDataFreshness(lastUpdateTime);
 *
 * return (
 *   <Panel className={isStale ? 'data-stale' : ''}>
 *     <Header>Data Panel <span>{formattedAge}</span></Header>
 *     {isVeryStale && <StaleBadge />}
 *   </Panel>
 * );
 * ```
 */

import { useState, useEffect, useMemo, useCallback } from 'react';

// Thresholds for stale data detection
const STALE_THRESHOLD_SECONDS = 60;      // Data older than 60s is considered stale
const VERY_STALE_THRESHOLD_SECONDS = 120; // Data older than 120s is considered very stale

export interface DataFreshnessResult {
  /** Formatted string like "Updated 5s ago", "Updated 2m ago" */
  formattedAge: string;
  /** Age in seconds since last update */
  ageSeconds: number;
  /** True if data is >60s old */
  isStale: boolean;
  /** True if data is >120s old */
  isVeryStale: boolean;
  /** CSS opacity value (1.0 for fresh, 0.7 for stale) */
  opacity: number;
  /** Whether to show the STALE badge */
  showStaleBadge: boolean;
  /** Timestamp of last update (for debugging) */
  lastUpdateTimestamp: number | null;
}

/**
 * Format age in human-readable format
 */
function formatAge(ageSeconds: number): string {
  if (ageSeconds < 0) return 'Just now';
  if (ageSeconds < 5) return 'Just now';
  if (ageSeconds < 60) return `Updated ${Math.floor(ageSeconds)}s ago`;
  if (ageSeconds < 3600) return `Updated ${Math.floor(ageSeconds / 60)}m ago`;
  if (ageSeconds < 86400) return `Updated ${Math.floor(ageSeconds / 3600)}h ago`;
  return `Updated ${Math.floor(ageSeconds / 86400)}d ago`;
}

/**
 * Hook to track data freshness with auto-refresh
 *
 * @param lastUpdateTime - Timestamp of last data update (Date, number, or ISO string)
 * @param refreshIntervalMs - How often to recalculate (default: 1000ms)
 * @returns DataFreshnessResult with freshness info and visual flags
 */
export function useDataFreshness(
  lastUpdateTime: Date | number | string | null | undefined,
  refreshIntervalMs: number = 1000
): DataFreshnessResult {
  const [now, setNow] = useState<number>(Date.now());

  // Parse the last update time to a timestamp
  const lastUpdateTimestamp = useMemo((): number | null => {
    if (lastUpdateTime === null || lastUpdateTime === undefined) return null;

    if (typeof lastUpdateTime === 'number') {
      return lastUpdateTime;
    }

    if (lastUpdateTime instanceof Date) {
      return lastUpdateTime.getTime();
    }

    if (typeof lastUpdateTime === 'string') {
      const parsed = Date.parse(lastUpdateTime);
      return isNaN(parsed) ? null : parsed;
    }

    return null;
  }, [lastUpdateTime]);

  // Auto-refresh every second
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, refreshIntervalMs);

    return () => clearInterval(interval);
  }, [refreshIntervalMs]);

  // Calculate freshness metrics
  const result = useMemo((): DataFreshnessResult => {
    if (lastUpdateTimestamp === null) {
      return {
        formattedAge: 'No data',
        ageSeconds: Infinity,
        isStale: true,
        isVeryStale: true,
        opacity: 0.5,
        showStaleBadge: true,
        lastUpdateTimestamp: null,
      };
    }

    const ageMs = now - lastUpdateTimestamp;
    const ageSeconds = Math.max(0, ageMs / 1000);
    const isStale = ageSeconds > STALE_THRESHOLD_SECONDS;
    const isVeryStale = ageSeconds > VERY_STALE_THRESHOLD_SECONDS;

    return {
      formattedAge: formatAge(ageSeconds),
      ageSeconds,
      isStale,
      isVeryStale,
      opacity: isStale ? 0.7 : 1.0,
      showStaleBadge: isVeryStale,
      lastUpdateTimestamp,
    };
  }, [now, lastUpdateTimestamp]);

  return result;
}

/**
 * Hook to track multiple data streams' freshness
 *
 * @param streams - Object mapping stream names to their last update times
 * @returns Object mapping stream names to their freshness results
 */
export function useMultiStreamFreshness(
  streams: Record<string, Date | number | string | null | undefined>
): Record<string, DataFreshnessResult> {
  const [now, setNow] = useState<number>(Date.now());

  // Auto-refresh every second
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Calculate freshness for all streams
  const results = useMemo(() => {
    const output: Record<string, DataFreshnessResult> = {};

    for (const [streamName, lastUpdateTime] of Object.entries(streams)) {
      let lastUpdateTimestamp: number | null = null;

      if (lastUpdateTime !== null && lastUpdateTime !== undefined) {
        if (typeof lastUpdateTime === 'number') {
          lastUpdateTimestamp = lastUpdateTime;
        } else if (lastUpdateTime instanceof Date) {
          lastUpdateTimestamp = lastUpdateTime.getTime();
        } else if (typeof lastUpdateTime === 'string') {
          const parsed = Date.parse(lastUpdateTime);
          lastUpdateTimestamp = isNaN(parsed) ? null : parsed;
        }
      }

      if (lastUpdateTimestamp === null) {
        output[streamName] = {
          formattedAge: 'No data',
          ageSeconds: Infinity,
          isStale: true,
          isVeryStale: true,
          opacity: 0.5,
          showStaleBadge: true,
          lastUpdateTimestamp: null,
        };
        continue;
      }

      const ageMs = now - lastUpdateTimestamp;
      const ageSeconds = Math.max(0, ageMs / 1000);
      const isStale = ageSeconds > STALE_THRESHOLD_SECONDS;
      const isVeryStale = ageSeconds > VERY_STALE_THRESHOLD_SECONDS;

      output[streamName] = {
        formattedAge: formatAge(ageSeconds),
        ageSeconds,
        isStale,
        isVeryStale,
        opacity: isStale ? 0.7 : 1.0,
        showStaleBadge: isVeryStale,
        lastUpdateTimestamp,
      };
    }

    return output;
  }, [now, streams]);

  return results;
}

/**
 * Get the overall freshness status from multiple streams
 * Returns the stalest stream's status
 */
export function getOverallFreshness(
  streamResults: Record<string, DataFreshnessResult>
): DataFreshnessResult {
  const results = Object.values(streamResults);

  if (results.length === 0) {
    return {
      formattedAge: 'No data',
      ageSeconds: Infinity,
      isStale: true,
      isVeryStale: true,
      opacity: 0.5,
      showStaleBadge: true,
      lastUpdateTimestamp: null,
    };
  }

  // Find the stalest stream
  const stalest = results.reduce((prev, curr) =>
    curr.ageSeconds > prev.ageSeconds ? curr : prev
  );

  return stalest;
}

export default useDataFreshness;
