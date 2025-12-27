/**
 * useStateMachineState Hook
 * =========================
 * Story 1A-2: State Machine State Badge (AC4: Real-time updates)
 *
 * Custom hook to track the current state machine state with real-time
 * WebSocket updates. Provides the current state for display in StateBadge.
 *
 * State Machine States:
 * - MONITORING: Watching for signals (idle state)
 * - S1: Signal detected (pump/dump found)
 * - O1: Cancellation (false alarm)
 * - Z1: Entry confirmation
 * - POSITION_ACTIVE: In position
 * - ZE1: Exit with profit
 * - E1: Emergency exit
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { wsService } from '@/services/websocket';
import { apiService } from '@/services/api';
import type { StateMachineState } from '@/components/dashboard/StateBadge';

export interface StateMachineStateData {
  state: StateMachineState;
  since: string | null;
  symbol: string | null;
  sessionId: string | null;
}

export interface UseStateMachineStateReturn {
  currentState: StateMachineState;
  since: string | null;
  symbol: string | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Maps backend state names to frontend StateMachineState type
 */
function normalizeState(backendState: string | null | undefined): StateMachineState {
  if (!backendState) return 'MONITORING';

  const stateUpper = backendState.toUpperCase();

  // Direct mappings
  const stateMap: Record<string, StateMachineState> = {
    'MONITORING': 'MONITORING',
    'S1': 'S1',
    'O1': 'O1',
    'Z1': 'Z1',
    'POSITION_ACTIVE': 'POSITION_ACTIVE',
    'ZE1': 'ZE1',
    'E1': 'E1',
    // Legacy mappings
    'INACTIVE': 'INACTIVE',
    'SIGNAL_DETECTED': 'S1', // Map legacy to new
    'EXITED': 'EXITED',
    'ERROR': 'ERROR',
    // Additional backend variations
    'IDLE': 'MONITORING',
    'WATCHING': 'MONITORING',
    'IN_POSITION': 'POSITION_ACTIVE',
    'ACTIVE': 'POSITION_ACTIVE',
  };

  return stateMap[stateUpper] || 'MONITORING';
}

/**
 * Hook to track state machine state with real-time updates
 *
 * @example
 * ```tsx
 * const { currentState, since, isLoading } = useStateMachineState();
 *
 * return <StateBadge state={currentState} since={since} size="hero" />;
 * ```
 */
export function useStateMachineState(): UseStateMachineStateReturn {
  const [stateData, setStateData] = useState<StateMachineStateData>({
    state: 'MONITORING',
    since: null,
    symbol: null,
    sessionId: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void) | null>(null);

  /**
   * Fetch initial state from API
   */
  const fetchInitialState = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiService.getExecutionStatus();

      if (response && response.state_machine_state) {
        setStateData({
          state: normalizeState(response.state_machine_state),
          since: response.state_changed_at || new Date().toISOString(),
          symbol: response.symbol || null,
          sessionId: response.session_id || null,
        });
      } else if (response && response.data) {
        // Handle nested response structure
        const data = response.data;
        setStateData({
          state: normalizeState(data.state_machine_state || data.state),
          since: data.state_changed_at || data.timestamp || new Date().toISOString(),
          symbol: data.symbol || null,
          sessionId: data.session_id || null,
        });
      }
    } catch (err: any) {
      console.warn('[useStateMachineState] Failed to fetch initial state:', err?.message);
      // Don't set error - just use default state
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Handle WebSocket message for state updates
   */
  const handleWebSocketMessage = useCallback((message: any) => {
    // Handle different message formats
    const msgType = message.type || message.event;
    const data = message.data || message;

    // Filter for state-related messages
    const stateMessageTypes = [
      'session_update',
      'state_change',
      'state_update',
      'execution_status',
      'state_machine_update',
    ];

    if (!stateMessageTypes.includes(msgType)) {
      return;
    }

    // Extract state from message
    const newState = data.state_machine_state || data.state || data.current_state;

    if (newState) {
      console.log('[useStateMachineState] State update received:', {
        type: msgType,
        state: newState,
        symbol: data.symbol,
      });

      setStateData({
        state: normalizeState(newState),
        since: data.state_changed_at || data.timestamp || new Date().toISOString(),
        symbol: data.symbol || stateData.symbol,
        sessionId: data.session_id || stateData.sessionId,
      });
    }
  }, [stateData.symbol, stateData.sessionId]);

  /**
   * Subscribe to WebSocket updates
   */
  useEffect(() => {
    // Fetch initial state
    fetchInitialState();

    // Subscribe to WebSocket session updates
    if (wsService && typeof wsService.addSessionUpdateListener === 'function') {
      cleanupRef.current = wsService.addSessionUpdateListener(handleWebSocketMessage, 'StateMachineState');
      console.log('[useStateMachineState] Subscribed to WebSocket updates');
    }

    return () => {
      // Cleanup listener on unmount
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
        console.log('[useStateMachineState] Unsubscribed from WebSocket updates');
      }
    };
  }, [fetchInitialState, handleWebSocketMessage]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async () => {
    await fetchInitialState();
  }, [fetchInitialState]);

  return {
    currentState: stateData.state,
    since: stateData.since,
    symbol: stateData.symbol,
    isLoading,
    error,
    refresh,
  };
}

export default useStateMachineState;
