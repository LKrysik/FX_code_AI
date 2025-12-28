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
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Logger } from '@/services/frontendLogService';
import ConditionProgress, { ConditionGroup, Condition } from './ConditionProgress';

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
  const [currentState, setCurrentState] = useState<string>('INACTIVE');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // Transform API Response to UI Format
  // ========================================

  const transformApiResponse = (apiGroups: APIConditionGroup[]): ConditionGroup[] => {
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
  };

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
    if (!sessionId) {
      setGroups([]);
      setCurrentState('INACTIVE');
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

      // Find instance matching our symbol
      const instance = data.instances?.find((i) => i.symbol === symbol);

      if (instance) {
        setGroups(transformApiResponse(instance.groups));
        setCurrentState(instance.state || 'INACTIVE');
      } else if (data.instances?.length > 0) {
        // No exact match - use first instance if available
        const firstInstance = data.instances[0];
        setGroups(transformApiResponse(firstInstance.groups));
        setCurrentState(firstInstance.state || 'INACTIVE');
      } else {
        // No instances at all
        setGroups([]);
        setCurrentState('INACTIVE');
      }
    } catch (err) {
      Logger.error('ConditionProgress.fetchStatus', { message: 'Failed to fetch condition status', error: err });
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Don't clear existing data on error - show stale data with error indicator
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, symbol]);

  // ========================================
  // WebSocket Integration
  // ========================================

  useEffect(() => {
    if (!sessionId) return;

    // WebSocket URL from environment or default
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8080/ws';
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        Logger.debug('ConditionProgress.wsConnected', { message: 'WebSocket connected' });

        // Subscribe to condition updates for this session
        ws?.send(
          JSON.stringify({
            type: 'subscribe',
            channel: 'conditions',
            session_id: sessionId,
            symbol: symbol,
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle condition update messages
          if (message.type === 'condition_update' && message.session_id === sessionId) {
            setGroups(message.groups || []);
            setCurrentState(message.state || 'INACTIVE');
            setError(null); // Clear error on successful update
          }

          // Handle state machine state changes
          if (message.type === 'state_change' && message.session_id === sessionId) {
            setCurrentState(message.new_state || 'INACTIVE');
          }
        } catch (err) {
          Logger.error('ConditionProgress.wsMessage', { message: 'WebSocket message parse error', error: err });
        }
      };

      ws.onerror = (err) => {
        Logger.error('ConditionProgress.wsError', { message: 'WebSocket error', error: err });
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        Logger.debug('ConditionProgress.wsClosed', { message: 'WebSocket disconnected' });
      };
    } catch (err) {
      Logger.error('ConditionProgress.wsInit', { message: 'WebSocket initialization error', error: err });
      setError('Failed to initialize WebSocket');
    }

    // Cleanup on unmount or sessionId change
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: 'unsubscribe',
            channel: 'conditions',
            session_id: sessionId,
          })
        );
        ws.close();
      }
    };
  }, [sessionId, symbol]);

  // ========================================
  // Initial Load + Polling Fallback
  // ========================================

  useEffect(() => {
    // Initial fetch
    fetchConditionStatus();

    // Polling fallback (in case WebSocket fails)
    const intervalId = setInterval(() => {
      fetchConditionStatus();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [fetchConditionStatus, refreshInterval]);

  // ========================================
  // Render
  // ========================================

  return (
    <ConditionProgress groups={groups} currentState={currentState} isLoading={isLoading} />
  );
};

export default ConditionProgressIntegration;
