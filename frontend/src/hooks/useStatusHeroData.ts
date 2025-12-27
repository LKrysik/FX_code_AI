/**
 * useStatusHeroData Hook
 * ======================
 * Story 1A-5: StatusHero Component (AC2-4)
 *
 * Combines state machine state, P&L data, and position info
 * for the StatusHero component.
 *
 * Data Sources:
 * - State machine state from useStateMachineState hook
 * - Position data from API
 * - Session data from API
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useStateMachineState } from './useStateMachineState';
import { apiService } from '@/services/api';
import type { StateMachineState } from '@/components/dashboard/StateBadge';
import type { StatusHeroProps } from '@/components/dashboard/StatusHero';

export interface StatusHeroData {
  state: StateMachineState;
  symbol: string | null;
  pnl: number | undefined;
  pnlPercent: number | undefined;
  entryPrice: number | undefined;
  currentPrice: number | undefined;
  sessionTime: number;
  positionTime: number;
  signalType: 'pump' | 'dump' | undefined;
  indicatorHighlights: { name: string; value: string }[];
  side: 'LONG' | 'SHORT' | undefined;
  isLoading: boolean;
  error: string | null;
}

export interface UseStatusHeroDataReturn extends StatusHeroData {
  refresh: () => Promise<void>;
}

/**
 * Hook to get all data needed for StatusHero component
 *
 * @param sessionId - Current session ID
 * @param symbol - Symbol to track (optional, defaults to active symbol)
 * @returns StatusHeroData with all metrics
 *
 * @example
 * ```tsx
 * const heroData = useStatusHeroData(sessionId, 'BTCUSDT');
 *
 * return <StatusHero {...heroData} />;
 * ```
 */
export function useStatusHeroData(
  sessionId: string | null,
  symbol?: string
): UseStatusHeroDataReturn {
  const { currentState, since: stateSince, symbol: stateSymbol } = useStateMachineState();

  const [data, setData] = useState<StatusHeroData>({
    state: 'MONITORING',
    symbol: null,
    pnl: undefined,
    pnlPercent: undefined,
    entryPrice: undefined,
    currentPrice: undefined,
    sessionTime: 0,
    positionTime: 0,
    signalType: undefined,
    indicatorHighlights: [],
    side: undefined,
    isLoading: true,
    error: null,
  });

  const sessionStartRef = useRef<number | null>(null);
  const positionStartRef = useRef<number | null>(null);

  /**
   * Fetch position data when in position state
   */
  const fetchPositionData = useCallback(async () => {
    if (!sessionId) return;

    const isInPosition = currentState === 'POSITION_ACTIVE' || currentState === 'ZE1' || currentState === 'E1';

    if (!isInPosition) {
      // Clear position data when not in position
      setData((prev) => ({
        ...prev,
        pnl: undefined,
        pnlPercent: undefined,
        entryPrice: undefined,
        currentPrice: undefined,
        positionTime: 0,
        side: undefined,
      }));
      positionStartRef.current = null;
      return;
    }

    try {
      const response = await apiService.getPositions(sessionId);

      if (response && Array.isArray(response) && response.length > 0) {
        // Get the first active position (or filter by symbol if provided)
        const position = symbol
          ? response.find((p: any) => p.symbol === symbol || p.symbol?.includes(symbol))
          : response[0];

        if (position) {
          // Set position start time if not set
          if (!positionStartRef.current && position.opened_at) {
            positionStartRef.current = new Date(position.opened_at).getTime();
          }

          setData((prev) => ({
            ...prev,
            symbol: position.symbol || prev.symbol,
            pnl: position.unrealized_pnl || 0,
            pnlPercent: position.unrealized_pnl_pct || 0,
            entryPrice: position.entry_price,
            currentPrice: position.current_price,
            side: position.side,
            isLoading: false,
            error: null,
          }));
        }
      }
    } catch (err: any) {
      console.warn('[useStatusHeroData] Failed to fetch position data:', err?.message);
    }
  }, [sessionId, currentState, symbol]);

  /**
   * Fetch session info for session timer
   */
  const fetchSessionInfo = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await apiService.getExecutionStatus();

      if (response && response.started_at) {
        sessionStartRef.current = new Date(response.started_at).getTime();
      }

      // Extract signal type if available
      if (response && response.signal_type) {
        setData((prev) => ({
          ...prev,
          signalType: response.signal_type === 'pump_detection' ? 'pump' : 'dump',
        }));
      }

      // Extract indicator highlights if available
      if (response && response.indicators && Array.isArray(response.indicators)) {
        const highlights = response.indicators.slice(0, 3).map((ind: any) => ({
          name: ind.name || 'Unknown',
          value: typeof ind.value === 'number' ? ind.value.toFixed(2) : String(ind.value),
        }));
        setData((prev) => ({
          ...prev,
          indicatorHighlights: highlights,
        }));
      }
    } catch (err: any) {
      console.warn('[useStatusHeroData] Failed to fetch session info:', err?.message);
    }
  }, [sessionId]);

  /**
   * Update timers every second
   */
  useEffect(() => {
    const updateTimers = () => {
      const now = Date.now();

      // Update session time
      if (sessionStartRef.current) {
        const sessionTime = Math.floor((now - sessionStartRef.current) / 1000);
        setData((prev) => ({
          ...prev,
          sessionTime: sessionTime > 0 ? sessionTime : 0,
        }));
      }

      // Update position time
      if (positionStartRef.current) {
        const positionTime = Math.floor((now - positionStartRef.current) / 1000);
        setData((prev) => ({
          ...prev,
          positionTime: positionTime > 0 ? positionTime : 0,
        }));
      }
    };

    const interval = setInterval(updateTimers, 1000);
    updateTimers(); // Initial update

    return () => clearInterval(interval);
  }, []);

  /**
   * Sync state from useStateMachineState hook
   */
  useEffect(() => {
    setData((prev) => ({
      ...prev,
      state: currentState,
      symbol: stateSymbol || symbol || prev.symbol,
    }));
  }, [currentState, stateSymbol, symbol]);

  /**
   * Fetch data on session/state change
   */
  useEffect(() => {
    if (sessionId) {
      fetchSessionInfo();
      fetchPositionData();

      // Poll position data every 2 seconds when in position
      const isInPosition = currentState === 'POSITION_ACTIVE' || currentState === 'ZE1' || currentState === 'E1';
      if (isInPosition) {
        const pollInterval = setInterval(fetchPositionData, 2000);
        return () => clearInterval(pollInterval);
      }
    } else {
      // Reset data when no session
      setData({
        state: 'MONITORING',
        symbol: null,
        pnl: undefined,
        pnlPercent: undefined,
        entryPrice: undefined,
        currentPrice: undefined,
        sessionTime: 0,
        positionTime: 0,
        signalType: undefined,
        indicatorHighlights: [],
        side: undefined,
        isLoading: false,
        error: null,
      });
      sessionStartRef.current = null;
      positionStartRef.current = null;
    }
  }, [sessionId, currentState, fetchSessionInfo, fetchPositionData]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async () => {
    await Promise.all([fetchSessionInfo(), fetchPositionData()]);
  }, [fetchSessionInfo, fetchPositionData]);

  return {
    ...data,
    refresh,
  };
}

export default useStatusHeroData;
