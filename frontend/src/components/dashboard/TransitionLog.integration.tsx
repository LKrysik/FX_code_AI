'use client';

/**
 * TransitionLog Integration Component
 * ====================================
 *
 * Wraps TransitionLog with API fetching logic.
 * Fetches transition history from backend API.
 *
 * API Endpoint: GET /api/state-machines/transitions?session_id=X&symbol=Y
 */

import React, { useState, useEffect, useCallback } from 'react';
import TransitionLog, { Transition } from './TransitionLog';
import { Alert } from '@mui/material';

// ============================================================================
// Props
// ============================================================================

interface TransitionLogIntegrationProps {
  sessionId: string | null;
  symbol?: string; // Optional: filter by symbol
  maxItems?: number;
  refreshInterval?: number; // milliseconds
}

// ============================================================================
// API Response Type
// ============================================================================

interface TransitionsResponse {
  success: boolean;
  data: {
    transitions: Transition[];
  };
}

// ============================================================================
// Integration Component
// ============================================================================

const TransitionLogIntegration: React.FC<TransitionLogIntegrationProps> = ({
  sessionId,
  symbol,
  maxItems = 50,
  refreshInterval = 10000, // 10 seconds
}) => {
  // ========================================
  // State
  // ========================================

  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // API Fetch
  // ========================================

  const fetchTransitions = useCallback(async () => {
    if (!sessionId) {
      setTransitions([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const params = new URLSearchParams({
        session_id: sessionId,
        limit: String(maxItems),
      });

      if (symbol) {
        params.append('symbol', symbol);
      }

      // UWAGA: Używamy istniejącego endpointu GET /api/sessions/{session_id}/transitions
      // Endpoint zdefiniowany w src/api/state_machine_routes.py:191
      // UWAGA: Endpoint jest PLACEHOLDER - zwraca pustą listę (wymaga implementacji persistencji EventBus)
      const response = await fetch(
        `${apiUrl}/api/sessions/${sessionId}/transitions`
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      // Backend zwraca: { data: { session_id, transitions: [] } } (wrapped w envelope)
      // lub bezpośrednio: { session_id, transitions: [] }
      const data = result.data || result;
      if (data && Array.isArray(data.transitions)) {
        setTransitions(data.transitions);
      } else {
        // Brak transitions - to normalne dla placeholder endpointu
        setTransitions([]);
      }
    } catch (err) {
      console.error('[TransitionLog] Failed to fetch transitions:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Don't clear existing data on error
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, symbol, maxItems]);

  // ========================================
  // Effects
  // ========================================

  useEffect(() => {
    // Initial fetch
    fetchTransitions();

    // Polling
    const intervalId = setInterval(() => {
      fetchTransitions();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [fetchTransitions, refreshInterval]);

  // ========================================
  // Render
  // ========================================

  return (
    <>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Failed to load transition history: {error}. Showing cached data.
        </Alert>
      )}
      <TransitionLog
        transitions={transitions}
        maxItems={maxItems}
        isLoading={isLoading}
      />
    </>
  );
};

export default TransitionLogIntegration;
