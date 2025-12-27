/**
 * RecentSignalsPanel Component
 * ============================
 * Story 1A-1: Signal Display on Dashboard
 *
 * Displays recent trading signals prominently on the dashboard.
 * Uses WebSocket real-time updates via dashboardStore.
 *
 * AC1: When signal_generated event arrives via WebSocket, signal appears within 500ms
 * AC3: New signals appear at top of list (most recent first)
 * AC4: Maximum 10 signals displayed
 * AC5: Signal display uses prominent styling
 */

'use client';

import React, { useEffect } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Box,
  Paper,
  Typography,
  Button,
  Skeleton,
} from '@mui/material';
import {
  Notifications as SignalIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { SignalCard } from './SignalCard';
import { useActiveSignals, useDashboardActions } from '@/stores/dashboardStore';
import { wsService } from '@/services/websocket';
import { useDashboardStore } from '@/stores/dashboardStore';

export interface RecentSignalsPanelProps {
  /** Session ID for filtering signals */
  sessionId?: string | null;
  /** Maximum signals to display (default: 10) */
  maxSignals?: number;
  /** Callback when signal is clicked */
  onSignalClick?: (signalId: string) => void;
  /** Show refresh button */
  showRefresh?: boolean;
}

/**
 * RecentSignalsPanel - Prominent display of recent trading signals
 */
export const RecentSignalsPanel: React.FC<RecentSignalsPanelProps> = ({
  sessionId,
  maxSignals = 10,
  onSignalClick,
  showRefresh = true,
}) => {
  const activeSignals = useActiveSignals();
  const { fetchActiveSignals } = useDashboardActions();

  // Story 1A-1 Task 1: Connect WebSocket signals to dashboardStore
  useEffect(() => {
    // Set up WebSocket callback to add signals to store
    const handleSignalReceived = (message: any) => {
      if (!message?.data) return;

      const signalData = message.data;
      Logger.debug('RecentSignalsPanel.signalReceived', 'Signal received via WebSocket', { signalData });

      // Transform WebSocket signal to ActiveSignal format
      const signal = {
        id: signalData.signal_id || `signal_${Date.now()}`,
        symbol: signalData.symbol || 'UNKNOWN',
        signalType: signalData.signal_type === 'S1' || signalData.side === 'LONG' ? 'pump' : 'dump' as 'pump' | 'dump',
        magnitude: signalData.magnitude || signalData.pump_magnitude || 0,
        confidence: signalData.confidence || 50,
        timestamp: signalData.timestamp || new Date().toISOString(),
        strategy: signalData.strategy_id || signalData.strategy || 'default',
      };

      // Filter by session if provided
      if (sessionId && signalData.session_id && signalData.session_id !== sessionId) {
        return;
      }

      // Add to store (AC1: within 500ms)
      useDashboardStore.getState().addSignal(signal);
    };

    // Register callback
    wsService.setCallbacks({
      onSignals: handleSignalReceived,
    });

    Logger.debug('RecentSignalsPanel.init', 'WebSocket signal callback registered');

    // Cleanup on unmount (don't remove callback - other components may need it)
    return () => {
      Logger.debug('RecentSignalsPanel.unmount', 'RecentSignalsPanel unmounted');
    };
  }, [sessionId]);

  // Limit signals to maxSignals (AC4)
  const displayedSignals = activeSignals.slice(0, maxSignals);

  const handleRefresh = () => {
    fetchActiveSignals();
  };

  return (
    <Paper
      sx={{
        p: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SignalIcon color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Recent Signals
          </Typography>
          {displayedSignals.length > 0 && (
            <Typography
              variant="caption"
              sx={{
                px: 1,
                py: 0.25,
                borderRadius: 2,
                backgroundColor: 'primary.light',
                color: 'primary.contrastText',
                fontWeight: 600,
              }}
            >
              {displayedSignals.length}
            </Typography>
          )}
        </Box>

        {showRefresh && (
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        )}
      </Box>

      {/* Signal List */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          pr: 0.5, // Space for scrollbar
        }}
      >
        {displayedSignals.length === 0 ? (
          // Empty State
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              py: 4,
              color: 'text.secondary',
            }}
          >
            <SignalIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
            <Typography variant="body1" gutterBottom>
              No signals yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Signals will appear here when detected
            </Typography>
          </Box>
        ) : (
          // Signal Cards (AC3: newest first - already sorted by store)
          displayedSignals.map((signal) => (
            <SignalCard
              key={signal.id}
              id={signal.id}
              symbol={signal.symbol}
              signalType={signal.signalType}
              magnitude={signal.magnitude}
              confidence={signal.confidence}
              timestamp={signal.timestamp}
              strategy={signal.strategy}
              onClick={onSignalClick ? () => onSignalClick(signal.id) : undefined}
            />
          ))
        )}
      </Box>

      {/* Footer */}
      {displayedSignals.length > 0 && (
        <Box
          sx={{
            mt: 1,
            pt: 1,
            borderTop: 1,
            borderColor: 'divider',
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Showing {displayedSignals.length} of {activeSignals.length} signals (max {maxSignals})
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default RecentSignalsPanel;
