'use client';

/**
 * STATEBADGE INTEGRATION EXAMPLE
 *
 * Pokazuje jak zintegrować StateBadge z real-time WebSocket updates
 * i state management (Zustand/Redux).
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Divider
} from '@mui/material';
import StateBadge from './StateBadge';
import type { StateMachineState } from './StateBadge';

// ============================================================================
// TYPES
// ============================================================================

interface Position {
  id: string;
  symbol: string;
  state: StateMachineState;
  stateChangedAt: string;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

interface SystemStatus {
  overall: StateMachineState;
  since: string;
  activePositions: number;
  signals: number;
}

// ============================================================================
// MOCK DATA (Replace with real API/WebSocket)
// ============================================================================

const MOCK_POSITIONS: Position[] = [
  {
    id: '1',
    symbol: 'BTC/USDT',
    state: 'POSITION_ACTIVE',
    stateChangedAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    entryPrice: 42000,
    currentPrice: 42500,
    pnl: 500,
    pnlPercent: 1.19
  },
  {
    id: '2',
    symbol: 'ETH/USDT',
    state: 'SIGNAL_DETECTED',
    stateChangedAt: new Date(Date.now() - 30 * 1000).toISOString(),
    entryPrice: 0,
    currentPrice: 2200,
    pnl: 0,
    pnlPercent: 0
  },
  {
    id: '3',
    symbol: 'SOL/USDT',
    state: 'MONITORING',
    stateChangedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    entryPrice: 0,
    currentPrice: 98.5,
    pnl: 0,
    pnlPercent: 0
  }
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const StateBadgeIntegration: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    overall: 'MONITORING',
    since: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    activePositions: 1,
    signals: 1
  });

  const [positions, setPositions] = useState<Position[]>(MOCK_POSITIONS);

  // Simulate WebSocket updates
  useEffect(() => {
    // Example: Simulate state changes every 10 seconds
    const interval = setInterval(() => {
      // Randomly update a position state (for demo purposes)
      const randomIndex = Math.floor(Math.random() * positions.length);
      const states: StateMachineState[] = [
        'MONITORING',
        'SIGNAL_DETECTED',
        'POSITION_ACTIVE',
        'EXITED'
      ];
      const randomState = states[Math.floor(Math.random() * states.length)];

      setPositions((prev) =>
        prev.map((pos, idx) =>
          idx === randomIndex
            ? {
                ...pos,
                state: randomState,
                stateChangedAt: new Date().toISOString()
              }
            : pos
        )
      );
    }, 10000);

    return () => clearInterval(interval);
  }, [positions.length]);

  // Calculate system status based on positions
  useEffect(() => {
    const hasSignals = positions.some((p) => p.state === 'SIGNAL_DETECTED');
    const hasActivePositions = positions.some((p) => p.state === 'POSITION_ACTIVE');
    const hasErrors = positions.some((p) => p.state === 'ERROR');

    let overall: StateMachineState = 'MONITORING';
    if (hasErrors) overall = 'ERROR';
    else if (hasActivePositions) overall = 'POSITION_ACTIVE';
    else if (hasSignals) overall = 'SIGNAL_DETECTED';

    setSystemStatus((prev) => ({
      ...prev,
      overall,
      activePositions: positions.filter((p) => p.state === 'POSITION_ACTIVE').length,
      signals: positions.filter((p) => p.state === 'SIGNAL_DETECTED').length
    }));
  }, [positions]);

  return (
    <Box sx={{ p: 3 }}>
      {/* System Status Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant="h5" gutterBottom>
                Trading System Status
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Positions: {systemStatus.activePositions} | Signals: {systemStatus.signals}
              </Typography>
            </Box>
            <StateBadge
              state={systemStatus.overall}
              since={systemStatus.since}
              showDuration
              size="large"
            />
          </Box>
        </CardContent>
      </Card>

      {/* Positions Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {positions.map((position) => (
          <Grid item xs={12} md={4} key={position.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">{position.symbol}</Typography>
                  <StateBadge
                    state={position.state}
                    since={position.stateChangedAt}
                    showDuration
                    size="small"
                  />
                </Box>

                <Divider sx={{ my: 2 }} />

                {position.state === 'POSITION_ACTIVE' && (
                  <>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        Entry:
                      </Typography>
                      <Typography variant="body2">${position.entryPrice.toLocaleString()}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        Current:
                      </Typography>
                      <Typography variant="body2">${position.currentPrice.toLocaleString()}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">
                        P&L:
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          color: position.pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        ${position.pnl.toFixed(2)} ({position.pnlPercent >= 0 ? '+' : ''}
                        {position.pnlPercent.toFixed(2)}%)
                      </Typography>
                    </Box>
                  </>
                )}

                {position.state === 'SIGNAL_DETECTED' && (
                  <Typography variant="body2" color="warning.main">
                    Evaluating entry conditions...
                  </Typography>
                )}

                {position.state === 'MONITORING' && (
                  <Typography variant="body2" color="text.secondary">
                    Scanning for signals...
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Positions Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Position Monitor
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell>State</TableCell>
                <TableCell align="right">Entry Price</TableCell>
                <TableCell align="right">Current Price</TableCell>
                <TableCell align="right">P&L</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((position) => (
                <TableRow key={position.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {position.symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <StateBadge
                      state={position.state}
                      since={position.stateChangedAt}
                      showDuration
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    {position.entryPrice > 0 ? `$${position.entryPrice.toLocaleString()}` : '-'}
                  </TableCell>
                  <TableCell align="right">${position.currentPrice.toLocaleString()}</TableCell>
                  <TableCell align="right">
                    {position.state === 'POSITION_ACTIVE' ? (
                      <Typography
                        variant="body2"
                        sx={{
                          color: position.pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
                      </Typography>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Integration Code Example */}
      <Card sx={{ mt: 3, bgcolor: 'grey.50' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            WebSocket Integration Example
          </Typography>
          <Box component="pre" sx={{ fontSize: '0.85rem', overflow: 'auto' }}>
{`// Example WebSocket integration
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000');

socket.on('state_change', (data) => {
  const { symbol, state, timestamp } = data;

  setPositions((prev) =>
    prev.map((pos) =>
      pos.symbol === symbol
        ? { ...pos, state, stateChangedAt: timestamp }
        : pos
    )
  );
});

socket.on('position_update', (data) => {
  const { symbol, currentPrice, pnl, pnlPercent } = data;

  setPositions((prev) =>
    prev.map((pos) =>
      pos.symbol === symbol
        ? { ...pos, currentPrice, pnl, pnlPercent }
        : pos
    )
  );
});`}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default StateBadgeIntegration;
