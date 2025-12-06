/**
 * StateOverviewTable - Example Usage
 * ====================================
 *
 * Demonstrates how to use the StateOverviewTable component
 * with sample data and event handlers.
 */

'use client';

import React, { useState } from 'react';
import { Box, Container, Typography, Paper } from '@mui/material';
import StateOverviewTable, { StateInstance } from './StateOverviewTable';

// ============================================================================
// MOCK DATA
// ============================================================================

const mockInstances: StateInstance[] = [
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'BTCUSDT',
    state: 'POSITION_ACTIVE',
    since: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
  },
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'ETHUSDT',
    state: 'SIGNAL_DETECTED',
    since: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
  },
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'SOLUSDT',
    state: 'MONITORING',
    since: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
  },
  {
    strategy_id: 'trend_follow_v2',
    symbol: 'BTCUSDT',
    state: 'MONITORING',
    since: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
  },
  {
    strategy_id: 'trend_follow_v2',
    symbol: 'ADAUSDT',
    state: 'EXITED',
    since: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
  },
  {
    strategy_id: 'scalping_v1',
    symbol: 'DOGEUSDT',
    state: 'INACTIVE',
    since: null, // No timestamp
  },
];

// ============================================================================
// EXAMPLE COMPONENT
// ============================================================================

const StateOverviewTableExample: React.FC = () => {
  const [sessionId] = useState('session-' + Date.now());
  const [instances, setInstances] = useState<StateInstance[]>(mockInstances);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<StateInstance | null>(null);

  // ========================================
  // Handlers
  // ========================================

  const handleInstanceClick = (instance: StateInstance) => {
    console.log('Instance clicked:', instance);
    setSelectedInstance(instance);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setInstances(mockInstances);
      setIsLoading(false);
    }, 1000);
  };

  // ========================================
  // Render
  // ========================================

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        StateOverviewTable - Example
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        This example shows the StateOverviewTable component with mock data.
        Click on a row or the "View" button to select an instance.
      </Typography>

      {/* Main Table */}
      <StateOverviewTable
        sessionId={sessionId}
        instances={instances}
        onInstanceClick={handleInstanceClick}
        isLoading={isLoading}
      />

      {/* Selected Instance Details */}
      {selectedInstance && (
        <Paper sx={{ mt: 3, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Selected Instance
          </Typography>
          <Box sx={{ fontFamily: 'monospace', fontSize: '14px' }}>
            <pre>{JSON.stringify(selectedInstance, null, 2)}</pre>
          </Box>
        </Paper>
      )}

      {/* Actions */}
      <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
        <button onClick={handleRefresh} disabled={isLoading}>
          {isLoading ? 'Loading...' : 'Refresh Data'}
        </button>
        <button onClick={() => setInstances([])}>
          Clear Instances (Empty State)
        </button>
        <button onClick={() => setInstances(mockInstances)}>
          Reset to Mock Data
        </button>
      </Box>
    </Container>
  );
};

export default StateOverviewTableExample;
