'use client';

/**
 * ConditionProgress Integration Component
 * =======================================
 *
 * Wraps ConditionProgress with real API calls to:
 *   GET /api/sessions/{session_id}/conditions?symbol=X
 *
 * Maps backend response format to ConditionProgress component format.
 *
 * Architecture Decision:
 * - Uses new endpoint defined in state_machine_routes.py:280
 * - Backend returns condition groups with current indicator values
 * - Conditions evaluated against cached values from IndicatorEngine
 *
 * BUG-007.1c: Refactored to use shared wsService singleton instead of
 * standalone WebSocket connection (ADR-001 compliance)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Logger } from '@/services/frontendLogService';
import ConditionProgress, { ConditionGroup, Condition } from './ConditionProgress';
import { wsService, WSMessage } from '@/services/websocket';

// ============================================================================
// Props
// ============================================================================

interface ConditionProgressIntegrationProps {
  sessionId: string | null;
  symbol: string;
  refreshInterval?: number; // milliseconds (for polling fallback)
}

// ============================================================================
// API Response Types (from state_machine_routes.py)
// ============================================================================

interface APICondition {
  name: string;
  condition_type: string;
  operator: string;
  threshold: number | [number, number];
  current_value: number | null;
  met: boolean;
  enabled: boolean;
  description: string;
}

interface APIConditionGroup {
  name: string; // "S1 - Signal Detection"
  id: string; // "signal_detection"
  is_relevant: boolean;
  require_all: boolean;
  progress: {
    met: number;
    total: number;
    percentage: number;
  };
  conditions: APICondition[];
}

interface APIInstance {
  strategy_id: string;
  symbol: string;
  state: string;
  groups: APIConditionGroup[];
}

interface ConditionsResponse {
  session_id: string;
  instances: APIInstance[];
}

// Map backend group IDs to UI section names
const GROUP_ID_TO_SECTION: Record<string, 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1'> = {
  signal_detection: 'S1',
  signal_cancellation: 'O1',
  entry_conditions: 'Z1',
  close_order_detection: 'ZE1',
  emergency_exit: 'E1',
};

// ============================================================================
// Integration Component
// ============================================================================

const ConditionProgressIntegration: React.FC<ConditionProgressIntegrationProps> = ({
  sessionId,
  symbol,
  refreshInterval = 5000,
}) => {
  // ========================================
  // State
  // ========================================

  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  // BUG-004-6 FIX: Start with MONITORING as default for active sessions
  // INACTIVE should only be set when we explicitly know the session is inactive
  const [currentState, setCurrentState] = useState<string>(sessionId ? 'MONITORING' : 'INACTIVE');
  const [isLoading, setIsLoading] = useState(!!sessionId); // Loading if we have sessionId
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // Transform API Response to UI Format
  // ========================================

  const transformApiResponse = useCallback((apiGroups: APIConditionGroup[]): ConditionGroup[] => {
    return apiGroups.map((apiGroup): ConditionGroup => {
      const section = GROUP_ID_TO_SECTION[apiGroup.id] || 'S1';

      // Extract label from name (e.g., "S1 - Signal Detection" -> "Signal Detection")
      const labelParts = apiGroup.name.split(' - ');
      const label = labelParts.length > 1 ? labelParts[1] : apiGroup.name;

      // Transform conditions to UI format
      const conditions: Condition[] = apiGroup.conditions
        .filter((c) => c.enabled)
        .map((apiCond): Condition => ({
          indicator_name: apiCond.name || apiCond.condition_type,
          operator: normalizeOperator(apiCond.operator),
          threshold: Array.isArray(apiCond.threshold) ? apiCond.threshold[0] : apiCond.threshold,
          current_value: apiCond.current_value ?? 0,
          met: apiCond.met,
        }));

      // Calculate all_met based on logic
      const enabledConditions = conditions.filter(() => true);
      const all_met = apiGroup.require_all
        ? enabledConditions.every((c) => c.met)
        : enabledConditions.some((c) => c.met);

      return {
        section,
        label,
        logic: apiGroup.require_all ? 'AND' : 'OR',
        conditions,
        all_met,
      };
    });
  }, []);

  /**
   * Normalize operator to UI format
   * Backend uses: "gte", ">=", ">" etc.
   * UI expects: ">", "<", ">=", "<=", "==", "!="
   */
  const normalizeOperator = (op: string): Condition['operator'] => {
    const opMap: Record<string, Condition['operator']> = {
      gte: '>=',
      '>=': '>=',
      lte: '<=',
      '<=': '<=',
      gt: '>',
      '>': '>',
      lt: '<',
      '<': '<',
      eq: '==',
      '==': '==',
      '=': '==',
      neq: '!=',
      '!=': '!=',
    };
    return opMap[op.toLowerCase()] || '>=';
  };

  // ========================================
  // API Fetch
  // ========================================

  const fetchConditionStatus = useCallback(async () => {
    // BUG-004-6 FIX: Don't set INACTIVE when sessionId is missing
    // Just return early - let the component show loading or previous state
    // This prevents the race condition where sessionId arrives after first render
    if (!sessionId) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

      // UWAGA: Używamy endpointu GET /api/sessions/{session_id}/conditions
      // Endpoint zdefiniowany w src/api/state_machine_routes.py:280
      const params = new URLSearchParams();
      if (symbol) {
        params.append('symbol', symbol);
      }

      const url = `${apiUrl}/api/sessions/${sessionId}/conditions${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      // Backend zwraca: { data: { session_id, instances: [...] } } (wrapped w envelope)
      // lub bezpośrednio: { session_id, instances: [...] }
      const data: ConditionsResponse = result.data || result;

      // BUG-004-6 FIX: Case-insensitive symbol matching
      // Symbols may come in different formats: "BTCUSDT", "btcusdt", "BTC_USDT"
      const normalizeSymbol = (s: string) => s?.toUpperCase().replace(/_/g, '');
      const normalizedSymbol = normalizeSymbol(symbol);

      const instance = data.instances?.find(
        (i) => normalizeSymbol(i.symbol) === normalizedSymbol
      );

      if (instance) {
        setGroups(transformApiResponse(instance.groups));
        // BUG-004-6 FIX: Default to MONITORING instead of INACTIVE for active sessions
        setCurrentState(instance.state || 'MONITORING');
      } else if (data.instances?.length > 0) {
        // No exact match - use first instance if available
        const firstInstance = data.instances[0];
        setGroups(transformApiResponse(firstInstance.groups));
        setCurrentState(firstInstance.state || 'MONITORING');
      } else {
        // No instances at all - session may be starting
        setGroups([]);
        // BUG-004-6 FIX: Keep current state, don't force INACTIVE
        // If we had a valid state before, keep it during brief gaps
      }
    } catch (err) {
      Logger.error('ConditionProgress.fetchStatus', { message: 'Failed to fetch condition status', error: err });
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Don't clear existing data on error - show stale data with error indicator
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, symbol, transformApiResponse]);

  // ========================================
  // WebSocket Integration via wsService (BUG-007.1c)
  // ========================================

  useEffect(() => {
    if (!sessionId) return;

    // Subscribe to conditions stream
    wsService.subscribe('conditions', { session_id: sessionId, symbol });

    // Add listener for condition update messages
    const cleanup = wsService.addSessionUpdateListener((message: WSMessage) => {
      // Handle condition update messages
      if (message.type === 'condition_update' && message.session_id === sessionId) {
        if (message.data?.groups) {
          setGroups(transformApiResponse(message.data.groups));
        } else if (message.groups) {
          setGroups(transformApiResponse(message.groups));
        }
        // BUG-004-6 FIX: Use MONITORING as fallback, not INACTIVE
        setCurrentState(message.data?.state || message.state || 'MONITORING');
        setError(null); // Clear error on successful update
      }

      // Handle state machine state changes
      if (message.type === 'state_change' && message.session_id === sessionId) {
        // BUG-004-6 FIX: Use MONITORING as fallback, not INACTIVE
        setCurrentState(message.data?.new_state || message.new_state || 'MONITORING');
      }
    }, 'ConditionProgress');

    // Cleanup on unmount
    return () => {
      cleanup();
      wsService.unsubscribe('conditions');
    };
  }, [sessionId, symbol, transformApiResponse]);

  // ========================================
  // BUG-004-6 FIX: Handle sessionId becoming available
  // ========================================

  useEffect(() => {
    if (sessionId) {
      // sessionId just became available - trigger immediate fetch
      Logger.debug('ConditionProgress.sessionId_available', {
        sessionId,
        symbol,
        previousState: currentState,
      });
      fetchConditionStatus();
    }
    // Only trigger when sessionId changes, not on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // ========================================
  // Initial Load + Polling Fallback
  // ========================================

  useEffect(() => {
    // Skip if sessionId not yet available
    if (!sessionId) {
      return;
    }

    // Initial fetch
    fetchConditionStatus();

    // Polling fallback (in case WebSocket fails)
    const intervalId = setInterval(() => {
      fetchConditionStatus();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [fetchConditionStatus, refreshInterval, sessionId]);

  // ========================================
  // Render
  // ========================================

  return (
    <ConditionProgress groups={groups} currentState={currentState} isLoading={isLoading} />
  );
};

export default ConditionProgressIntegration;
