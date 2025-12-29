/**
 * StateOverviewTable - Integration Example
 * ==========================================
 *
 * Demonstrates integration with:
 * - REST API for initial data
 * - WebSocket for real-time updates
 * - Error handling and retry logic
 * - Navigation to detail views
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Box, Alert, Button, Container, Typography } from '@mui/material';
import StateOverviewTable, { StateInstance } from './StateOverviewTable';

// ============================================================================
// INTEGRATION COMPONENT
// ============================================================================

interface StateOverviewIntegrationProps {
  sessionId: string;
  apiUrl?: string;
  wsUrl?: string;
  onNavigateToDetail?: (instance: StateInstance) => void;
}

const StateOverviewTableIntegration: React.FC<StateOverviewIntegrationProps> = ({
  sessionId,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
  wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8080/ws',
  onNavigateToDetail,
}) => {
  // ========================================
  // State
  // ========================================

  const [instances, setInstances] = useState<StateInstance[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

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
  // WebSocket - Real-time Updates
  // ========================================

  const connectWebSocket = useCallback(() => {
    if (!sessionId || !wsUrl) return;

    try {
      // UWAGA: WebSocket endpoint /ws/state-machines/{sessionId} NIE ISTNIEJE w backendzie
      // Używamy głównego WS endpoint /ws z subscription model
      // TODO: Backend powinien obsługiwać channel 'state_machines' z session_id
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
        setError(null);

        // Subscribe do kanału state_machines
        // UWAGA: Backend musi obsługiwać ten typ wiadomości w websocket_server.py
        socket.send(JSON.stringify({
          type: 'subscribe',
          channel: 'state_machines',
          session_id: sessionId
        }));
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle different message types
          switch (message.type) {
            case 'state_change':
              handleStateChange(message.data);
              break;

            case 'instance_added':
              handleInstanceAdded(message.data);
              break;

            case 'instance_removed':
              handleInstanceRemoved(message.data);
              break;

            case 'full_update':
              setInstances(message.data.instances || []);
              break;

            case 'error':
              console.error('WebSocket error message received:', message.data);
              setError(message.data?.message || 'Unknown server error');
              break;

            default:
              console.warn('Unknown WebSocket message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      socket.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);

        // Attempt reconnect after 5 seconds
        setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...');
          connectWebSocket();
        }, 5000);
      };

      setWs(socket);

      return () => {
        socket.close();
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('WebSocket connection failed');
    }
  }, [sessionId, wsUrl]);

  // ========================================
  // WebSocket Event Handlers
  // ========================================

  const handleStateChange = (data: {
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
  };

  const handleInstanceAdded = (data: StateInstance) => {
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
  };

  const handleInstanceRemoved = (data: {
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
  };

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

  // WebSocket connection
  useEffect(() => {
    if (sessionId) {
      const cleanup = connectWebSocket();
      return cleanup;
    }
  }, [sessionId, connectWebSocket]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [ws]);

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
