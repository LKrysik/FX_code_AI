/**
 * LiveMonitor Component
 *
 * Real-time session monitoring with WebSocket updates.
 * Shows balance, P&L, active session, latest signals.
 *
 * Features:
 * - Real-time balance updates
 * - P&L tracking (today + session)
 * - Active signals display
 * - Session runtime
 * - Quick actions (Stop, Full Dashboard)
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Divider,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Alert,
} from '@mui/material';
import {
  AccountBalanceWallet as WalletIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Stop as StopIcon,
  Assessment as DashboardIcon,
  Bolt as SignalIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

interface LiveMonitorProps {
  session: any;
  performance: any;
  walletBalance: any;
  signals: any[];
  onStop: () => void;
  onViewDashboard?: () => void;
}

export const LiveMonitor: React.FC<LiveMonitorProps> = ({
  session,
  performance,
  walletBalance,
  signals = [],
  onStop,
  onViewDashboard,
}) => {
  const [runtime, setRuntime] = useState('');

  // Update runtime every second
  useEffect(() => {
    if (!session?.start_time) return;

    const updateRuntime = () => {
      try {
        const distance = formatDistanceToNow(new Date(session.start_time), {
          addSuffix: false,
        });
        setRuntime(distance);
      } catch (error) {
        setRuntime('Unknown');
      }
    };

    updateRuntime();
    const interval = setInterval(updateRuntime, 1000);

    return () => clearInterval(interval);
  }, [session?.start_time]);

  const isRunning = session?.status === 'running';
  const todayPnL = performance?.daily_pnl || 0;
  const todayPnLPct = walletBalance?.total
    ? (todayPnL / walletBalance.total) * 100
    : 0;

  const latestSignal = signals && signals.length > 0 ? signals[0] : null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
      {/* Balance Card */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <WalletIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6">Balance</Typography>
          </Box>
          <Typography variant="h4" color="primary.main">
            ${walletBalance?.total?.toFixed(2) || '0.00'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Available: ${walletBalance?.available?.toFixed(2) || '0.00'}
          </Typography>
        </CardContent>
      </Card>

      {/* Today P&L Card */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            {todayPnL >= 0 ? (
              <TrendingUpIcon color="success" sx={{ mr: 1 }} />
            ) : (
              <TrendingDownIcon color="error" sx={{ mr: 1 }} />
            )}
            <Typography variant="h6">Today P&L</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Typography
              variant="h4"
              color={todayPnL >= 0 ? 'success.main' : 'error.main'}
            >
              ${Math.abs(todayPnL).toFixed(2)}
            </Typography>
            <Typography
              variant="h6"
              color={todayPnL >= 0 ? 'success.main' : 'error.main'}
            >
              ({todayPnL >= 0 ? '+' : '-'}{Math.abs(todayPnLPct).toFixed(2)}%)
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Active Session Card */}
      {session ? (
        <Card sx={{ bgcolor: isRunning ? 'success.light' : 'background.paper' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                {isRunning ? (
                  <SuccessIcon color="success" sx={{ mr: 1 }} />
                ) : (
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                )}
                <Typography variant="h6">Active Session</Typography>
              </Box>
              <Chip
                label={session.status?.toUpperCase() || 'UNKNOWN'}
                color={isRunning ? 'success' : 'error'}
                size="small"
              />
            </Box>

            <Typography variant="body2" fontWeight="bold" gutterBottom>
              {session.session_id}
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  Started:
                </Typography>
                <Typography variant="caption" fontWeight="bold">
                  {session.start_time
                    ? new Date(session.start_time).toLocaleTimeString()
                    : 'N/A'}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  Runtime:
                </Typography>
                <Typography variant="caption" fontWeight="bold">
                  {runtime}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  Mode:
                </Typography>
                <Chip
                  label={session.session_type?.toUpperCase() || 'UNKNOWN'}
                  size="small"
                  variant="outlined"
                />
              </Box>
            </Box>

            {isRunning && (
              <Button
                variant="contained"
                color="error"
                startIcon={<StopIcon />}
                onClick={onStop}
                fullWidth
                sx={{ mt: 2 }}
              >
                Stop Session
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">
          No active session. Use Quick Start to begin trading.
        </Alert>
      )}

      <Divider />

      {/* Latest Signal */}
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <SignalIcon color="warning" sx={{ mr: 1 }} />
          <Typography variant="h6">Latest Signal</Typography>
        </Box>

        {latestSignal ? (
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                <Typography variant="body1" fontWeight="bold">
                  {latestSignal.symbol?.replace('_', '/')}
                </Typography>
                <Chip
                  label={latestSignal.signalType?.toUpperCase() || 'SIGNAL'}
                  color={latestSignal.signalType === 'pump' ? 'success' : 'error'}
                  size="small"
                />
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Magnitude:
                  </Typography>
                  <Typography variant="caption" fontWeight="bold">
                    {latestSignal.magnitude?.toFixed(2)}%
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Confidence:
                  </Typography>
                  <Typography variant="caption" fontWeight="bold">
                    {latestSignal.confidence?.toFixed(0)}%
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Time:
                  </Typography>
                  <Typography variant="caption" fontWeight="bold">
                    {latestSignal.timestamp
                      ? new Date(latestSignal.timestamp).toLocaleTimeString()
                      : 'N/A'}
                  </Typography>
                </Box>
              </Box>

              {latestSignal.confidence && latestSignal.confidence < 100 && (
                <LinearProgress
                  variant="determinate"
                  value={latestSignal.confidence}
                  sx={{ mt: 1, height: 6, borderRadius: 3 }}
                  color={latestSignal.confidence > 70 ? 'success' : 'warning'}
                />
              )}
            </CardContent>
          </Card>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No signals yet
          </Typography>
        )}
      </Box>

      {/* Live Stats */}
      <Box>
        <Typography variant="h6" gutterBottom>
          Live Stats
        </Typography>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Signals:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {signals?.length || 0}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Open Orders:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {session?.open_orders || 0}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Avg Win Rate:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {performance?.win_rate?.toFixed(1) || '0.0'}%
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">Sharpe Ratio:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Action Buttons */}
      {onViewDashboard && (
        <Button
          variant="outlined"
          startIcon={<DashboardIcon />}
          onClick={onViewDashboard}
          fullWidth
        >
          Full Dashboard
        </Button>
      )}
    </Box>
  );
};

export default LiveMonitor;
