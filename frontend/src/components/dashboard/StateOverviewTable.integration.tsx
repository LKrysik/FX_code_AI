/**
 * StateOverviewTable - Integration Example
 * ==========================================
 *
 * Demonstrates integration with:
 * - REST API for initial data
 * - WebSocket for real-time updates via wsService singleton (BUG-007 fix)
 * - Error handling and retry logic
 * - Navigation to detail views
 *
 * BUG-007.1: Refactored to use shared wsService singleton instead of
 * standalone WebSocket connection (ADR-001 compliance)
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Box, Alert, Button, Container, Typography } from '@mui/material';
import StateOverviewTable, { StateInstance } from './StateOverviewTable';
import { wsService, WSMessage } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';

// ============================================================================
// INTEGRATION COMPONENT
// ============================================================================

interface StateOverviewIntegrationProps {
  sessionId: string;
  apiUrl?: string;
  onNavigateToDetail?: (instance: StateInstance) => void;
}

const StateOverviewTableIntegration: React.FC<StateOverviewIntegrationProps> = ({
  sessionId,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
  onNavigateToDetail,
}) => {
  // ========================================
  // State
  // ========================================

  const [instances, setInstances] = useState<StateInstance[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // BUG-007.1: Use shared WebSocket connection status from store
  const wsConnected = useWebSocketStore((state) => state.isConnected);

  // ========================================
  // REST API - Initial Load
  // ========================================

  const fetchInstances = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      // UWAGA: Używamy istniejącego endpointu GET /api/sessions/{session_id}/state
      // Endpoint zdefiniowany w src/api/state_machine_routes.py:84
      // Decyzja architektoniczna: Jeden endpoint zwraca zarówno stan sesji jak i instancje strategii
      const response = await fetch(
        `${apiUrl}/api/sessions/${sessionId}/state`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const data = result.data || result;

      setInstances(data.instances || []);
    } catch (err: any) {
      console.error('Failed to fetch state machines:', err);
      setError(err.message || 'Failed to load state machines');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, apiUrl]);

  // ========================================
  // WebSocket Event Handlers
  // ========================================

  const handleStateChange = useCallback((data: {
    strategy_id: string;
    symbol: string;
    state: string;
    since: string;
  }) => {
    setInstances((prev) =>
      prev.map((instance) =>
        instance.strategy_id === data.strategy_id &&
        instance.symbol === data.symbol
          ? {
              ...instance,
              state: data.state as any,
              since: data.since,
            }
          : instance
      )
    );
  }, []);

  const handleInstanceAdded = useCallback((data: StateInstance) => {
    setInstances((prev) => {
      // Check if already exists
      const exists = prev.some(
        (i) =>
          i.strategy_id === data.strategy_id && i.symbol === data.symbol
      );

      if (exists) {
        return prev.map((i) =>
          i.strategy_id === data.strategy_id && i.symbol === data.symbol
            ? data
            : i
        );
      }

      return [...prev, data];
    });
  }, []);

  const handleInstanceRemoved = useCallback((data: {
    strategy_id: string;
    symbol: string;
  }) => {
    setInstances((prev) =>
      prev.filter(
        (i) =>
          !(
            i.strategy_id === data.strategy_id && i.symbol === data.symbol
          )
      )
    );
  }, []);

  // ========================================
  // Click Handler
  // ========================================

  const handleInstanceClick = (instance: StateInstance) => {
    console.log('Instance clicked:', instance);

    if (onNavigateToDetail) {
      onNavigateToDetail(instance);
    } else {
      // Default behavior: log to console
      console.log('Navigate to detail view for:', instance);
    }
  };

  // ========================================
  // Effects
  // ========================================

  // Initial data load
  useEffect(() => {
    if (sessionId) {
      fetchInstances();
    }
  }, [sessionId, fetchInstances]);

  // BUG-007.1: WebSocket subscription via wsService singleton
  useEffect(() => {
    if (!sessionId) return;

    // Subscribe to state_machines stream
    wsService.subscribe('state_machines', { session_id: sessionId });

    // Add listener for state machine updates
    const cleanup = wsService.addSessionUpdateListener((message: WSMessage) => {
      // Only process state_machines stream messages
      if (message.stream !== 'state_machines' &&
          !['state_change', 'instance_added', 'instance_removed', 'full_update'].includes(message.type)) {
        return;
      }

      switch (message.type) {
        case 'state_change':
          if (message.data) {
            handleStateChange(message.data);
          }
          break;

        case 'instance_added':
          if (message.data) {
            handleInstanceAdded(message.data);
          }
          break;

        case 'instance_removed':
          if (message.data) {
            handleInstanceRemoved(message.data);
          }
          break;

        case 'full_update':
          if (message.data?.instances) {
            setInstances(message.data.instances);
          }
          break;

        case 'error':
          console.error('WebSocket error message received:', message.data);
          setError(message.data?.message || 'Unknown server error');
          break;
      }
    }, 'StateOverviewTable');

    // Cleanup on unmount
    return () => {
      cleanup();
      wsService.unsubscribe('state_machines');
    };
  }, [sessionId, handleStateChange, handleInstanceAdded, handleInstanceRemoved]);

  // ========================================
  // Render
  // ========================================

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Connection Status */}
      {wsConnected && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Connected to real-time updates
        </Alert>
      )}

      {!wsConnected && !isLoading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Real-time updates disconnected. Attempting to reconnect...
        </Alert>
      )}

      {/* Error Display */}
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={fetchInstances}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {/* Main Table */}
      <StateOverviewTable
        sessionId={sessionId}
        instances={instances}
        onInstanceClick={handleInstanceClick}
        isLoading={isLoading}
      />

      {/* Debug Info (Development Only) */}
      {process.env.NODE_ENV === 'development' && (
        <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
          <Typography variant="caption" component="div">
            <strong>Debug Info:</strong>
          </Typography>
          <Typography variant="caption" component="div">
            Session ID: {sessionId}
          </Typography>
          <Typography variant="caption" component="div">
            WebSocket: {wsConnected ? 'Connected' : 'Disconnected'}
          </Typography>
          <Typography variant="caption" component="div">
            Instances: {instances.length}
          </Typography>
          <Typography variant="caption" component="div">
            API URL: {apiUrl}
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default StateOverviewTableIntegration;
