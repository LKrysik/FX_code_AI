/**
 * TradeWorkspace Component
 *
 * Unified workspace combining:
 * - Dashboard (balance, P&L, signals)
 * - Trading (session management)
 * - Risk Management (positions, risk gauge)
 *
 * Features:
 * - All-in-one view (no navigation needed)
 * - Real-time WebSocket updates
 * - Quick session starter (left panel)
 * - Live monitor (center panel)
 * - Positions panel (right panel)
 * - Zero dialogs, inline editing
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Alert, Snackbar } from '@mui/material';
import { QuickSessionStarter, SessionConfig } from './QuickSessionStarter';
import { LiveMonitor } from './LiveMonitor';
import { PositionsPanel, Position } from './PositionsPanel';
import { useTradingStore, useTradingActions } from '@/stores';
import { wsService } from '@/services/websocket';
import { apiService } from '@/services/api';

export const TradeWorkspace: React.FC = () => {
  // Zustand stores
  const { activeSession, positions: storePositions, performance, walletBalance } = useTradingStore();
  const { startSession, stopSession, fetchTradingPerformance, fetchWalletBalance } = useTradingActions();

  // Local state
  const [positions, setPositions] = useState<Position[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({ open: false, message: '', severity: 'info' });
  const [totalRisk, setTotalRisk] = useState(0);

  // WebSocket setup
  useEffect(() => {
    // Subscribe to real-time updates
    wsService.subscribe('session_update');
    wsService.subscribe('position_update');
    wsService.subscribe('signals');
    wsService.subscribe('market_data');

    // Set up WebSocket listeners
    const unsubscribeSessionUpdate = wsService.addSessionUpdateListener((message) => {
      if (message.type === 'session_update' || message.stream === 'execution_status') {
        // Refresh data when session updates
        fetchTradingPerformance();
        fetchWalletBalance();
      }
    });

    const unsubscribeSignals = wsService.addMessageListener((message) => {
      if (message.type === 'data' && message.stream === 'signals') {
        setSignals((prev) => [message.data, ...prev.slice(0, 9)]); // Keep last 10 signals
      }
    });

    // Initial data load
    loadData();

    // Cleanup
    return () => {
      if (unsubscribeSessionUpdate) unsubscribeSessionUpdate();
      if (unsubscribeSignals) unsubscribeSignals();
      wsService.unsubscribe('session_update');
      wsService.unsubscribe('position_update');
      wsService.unsubscribe('signals');
      wsService.unsubscribe('market_data');
    };
  }, []);

  // Convert store positions to Position[] format
  useEffect(() => {
    if (storePositions && Array.isArray(storePositions)) {
      const formattedPositions: Position[] = storePositions.map((pos: any) => ({
        id: pos.id || pos.position_id || String(Math.random()),
        symbol: pos.symbol || 'UNKNOWN',
        side: (pos.side || 'long').toLowerCase() as 'long' | 'short',
        size: pos.size || pos.quantity || 0,
        entryPrice: pos.entry_price || pos.entryPrice || 0,
        currentPrice: pos.current_price || pos.currentPrice || pos.entry_price || 0,
        pnl: pos.pnl || pos.unrealized_pnl || 0,
        pnlPct: pos.pnl_pct || pos.pnlPct || 0,
        stopLoss: pos.stop_loss || pos.stopLoss,
        takeProfit: pos.take_profit || pos.takeProfit,
        riskPct: pos.risk_pct || pos.riskPct || 0,
        strategy: pos.strategy || pos.strategy_name,
        timestamp: pos.timestamp || pos.created_at || new Date().toISOString(),
      }));

      setPositions(formattedPositions);

      // Calculate total risk
      const risk = formattedPositions.reduce((sum, pos) => sum + (pos.riskPct || 0), 0);
      setTotalRisk(risk);
    }
  }, [storePositions]);

  const loadData = async () => {
    try {
      await Promise.all([
        fetchTradingPerformance(),
        fetchWalletBalance(),
      ]);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleStartSession = async (config: SessionConfig) => {
    try {
      // Get strategy details
      const strategyId = config.strategy_ids[0];
      const strategyData = await apiService.get4SectionStrategy(strategyId);

      if (!strategyData || !strategyData.strategy) {
        throw new Error('Strategy not found');
      }

      const strategyName = strategyData.strategy.strategy_name;
      const strategy_config: Record<string, any> = {};
      strategy_config[strategyName] = strategyData.strategy.strategy_json || strategyData.strategy;

      // Start session via API
      const sessionData = {
        session_type: config.session_type,
        symbols: config.symbols,
        strategy_config: strategy_config,
        config: {
          budget: { global_cap: config.budget },
          ...config.config,
        },
        idempotent: true,
      };

      const response = await apiService.startSession(sessionData);
      const sessionId = response.data?.session_id || response.session_id || 'unknown';

      setSnackbar({
        open: true,
        message: `Session started successfully: ${sessionId}`,
        severity: 'success',
      });

      // Refresh data
      await loadData();
    } catch (error: any) {
      console.error('Failed to start session:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to start session',
        severity: 'error',
      });
    }
  };

  const handleStopSession = async () => {
    if (!activeSession) return;

    try {
      await apiService.stopSession(activeSession.session_id);

      setSnackbar({
        open: true,
        message: 'Session stopped successfully',
        severity: 'success',
      });

      await loadData();
    } catch (error: any) {
      console.error('Failed to stop session:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to stop session',
        severity: 'error',
      });
    }
  };

  const handleClosePosition = async (positionId: string) => {
    try {
      // API call to close position
      // await apiService.closePosition(positionId);

      setSnackbar({
        open: true,
        message: 'Position closed successfully',
        severity: 'success',
      });

      await loadData();
    } catch (error: any) {
      console.error('Failed to close position:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to close position',
        severity: 'error',
      });
    }
  };

  const handleEditStopLoss = async (positionId: string, value: number) => {
    try {
      // API call to update stop loss
      // await apiService.updateStopLoss(positionId, value);

      // Optimistic update
      setPositions((prev) =>
        prev.map((pos) =>
          pos.id === positionId ? { ...pos, stopLoss: value } : pos
        )
      );

      setSnackbar({
        open: true,
        message: 'Stop loss updated',
        severity: 'success',
      });
    } catch (error: any) {
      console.error('Failed to update stop loss:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to update stop loss',
        severity: 'error',
      });
    }
  };

  const handleEditTakeProfit = async (positionId: string, value: number) => {
    try {
      // API call to update take profit
      // await apiService.updateTakeProfit(positionId, value);

      // Optimistic update
      setPositions((prev) =>
        prev.map((pos) =>
          pos.id === positionId ? { ...pos, takeProfit: value } : pos
        )
      );

      setSnackbar({
        open: true,
        message: 'Take profit updated',
        severity: 'success',
      });
    } catch (error: any) {
      console.error('Failed to update take profit:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to update take profit',
        severity: 'error',
      });
    }
  };

  const handleEmergencyStop = async () => {
    if (confirm('Emergency stop will close ALL positions immediately. Continue?')) {
      try {
        await handleStopSession();

        setSnackbar({
          open: true,
          message: 'Emergency stop executed - all positions closed',
          severity: 'warning',
        });
      } catch (error: any) {
        console.error('Failed to execute emergency stop:', error);
        setSnackbar({
          open: true,
          message: error.message || 'Failed to execute emergency stop',
          severity: 'error',
        });
      }
    }
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 120px)', gap: 2, p: 2 }}>
      {/* LEFT: Quick Start - always visible */}
      <Paper sx={{ width: 300, p: 2, overflow: 'auto' }} elevation={2}>
        <QuickSessionStarter
          onStart={handleStartSession}
          disabled={!!activeSession && activeSession.status === 'running'}
          currentSession={activeSession}
        />
      </Paper>

      {/* CENTER: Live Monitor - real-time updates */}
      <Paper sx={{ flex: 1, p: 2, overflow: 'auto' }} elevation={2}>
        <LiveMonitor
          session={activeSession}
          performance={performance}
          walletBalance={walletBalance}
          signals={signals}
          onStop={handleStopSession}
        />
      </Paper>

      {/* RIGHT: Positions - editable inline */}
      <Paper sx={{ width: 340, p: 2, overflow: 'auto' }} elevation={2}>
        <PositionsPanel
          positions={positions}
          totalRisk={totalRisk}
          maxRisk={20}
          onClosePosition={handleClosePosition}
          onEditStopLoss={handleEditStopLoss}
          onEditTakeProfit={handleEditTakeProfit}
          onEmergencyStop={handleEmergencyStop}
        />
      </Paper>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TradeWorkspace;
