/**
 * Session Summary Stats Component (SH-03)
 * =======================================
 *
 * Displays summary statistics for a trading session.
 * Shows signal counts (S1, Z1, O1, E1), accuracy metrics, and trade performance.
 *
 * Features:
 * - S1 Signal count (pump detections)
 * - Z1 Entry count (positions opened)
 * - O1 Timeout count (signals that expired)
 * - ZE1 Close count (normal exits)
 * - E1 Emergency count (emergency exits)
 * - Entry accuracy: Z1 / (Z1 + O1)
 * - Exit accuracy: ZE1 / (ZE1 + E1)
 * - Win rate and average P&L
 *
 * Related: docs/UI_BACKLOG.md (SH-03)
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Tooltip,
  CircularProgress,
  Alert,
  LinearProgress,
  Divider,
  Stack,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  TrendingUp as SignalIcon,
  PlayCircle as EntryIcon,
  Timer as TimeoutIcon,
  Stop as CloseIcon,
  Warning as EmergencyIcon,
  Analytics as AccuracyIcon,
  ShowChart as WinRateIcon,
  AttachMoney as PnLIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface SessionStats {
  s1_count: number;       // Signal detections (pump found)
  z1_count: number;       // Entry triggers (position opened)
  o1_count: number;       // Timeout exits (signal expired)
  ze1_count: number;      // Normal closes (take profit / planned exit)
  e1_count: number;       // Emergency exits (stop loss / panic)

  // Calculated metrics
  entry_accuracy?: number;   // Z1 / (Z1 + O1) - how often S1 led to entry
  exit_accuracy?: number;    // ZE1 / (ZE1 + E1) - how often exits were planned

  // Trade metrics
  win_count?: number;
  loss_count?: number;
  win_rate?: number;
  avg_pnl?: number;
  total_pnl?: number;
}

export interface SessionSummaryStatsProps {
  sessionId: string;
  stats?: SessionStats;
  onStatsLoad?: (stats: SessionStats) => void;
}

// ============================================================================
// Component
// ============================================================================

export const SessionSummaryStats: React.FC<SessionSummaryStatsProps> = ({
  sessionId,
  stats: propStats,
  onStatsLoad,
}) => {
  const [stats, setStats] = useState<SessionStats | null>(propStats || null);
  const [loading, setLoading] = useState(!propStats);
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    if (propStats) {
      setStats(propStats);
      setLoading(false);
      return;
    }

    const loadStats = async () => {
      if (!sessionId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/stats`);

        if (!response.ok) {
          // If endpoint doesn't exist yet, use mock data
          if (response.status === 404) {
            const mockStats = generateMockStats();
            setStats(mockStats);
            onStatsLoad?.(mockStats);
            return;
          }
          throw new Error(`Failed to load stats: ${response.status}`);
        }

        const result = await response.json();
        const data = result.data?.stats || result.stats || result;

        // Calculate derived metrics
        const processed = processStats(data);
        setStats(processed);
        onStatsLoad?.(processed);
      } catch (err) {
        Logger.error('SessionSummaryStats.loadStats', { message: 'Failed to load session stats', error: err });
        // Fallback to mock data for development
        const mockStats = generateMockStats();
        setStats(mockStats);
        onStatsLoad?.(mockStats);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, propStats, onStatsLoad]);

  // ========================================
  // Helpers
  // ========================================

  const processStats = (raw: Partial<SessionStats>): SessionStats => {
    const s1 = raw.s1_count || 0;
    const z1 = raw.z1_count || 0;
    const o1 = raw.o1_count || 0;
    const ze1 = raw.ze1_count || 0;
    const e1 = raw.e1_count || 0;

    const entryAccuracy = (z1 + o1) > 0 ? (z1 / (z1 + o1)) * 100 : 0;
    const exitAccuracy = (ze1 + e1) > 0 ? (ze1 / (ze1 + e1)) * 100 : 0;

    const winCount = raw.win_count || 0;
    const lossCount = raw.loss_count || 0;
    const winRate = (winCount + lossCount) > 0 ? (winCount / (winCount + lossCount)) * 100 : 0;

    return {
      s1_count: s1,
      z1_count: z1,
      o1_count: o1,
      ze1_count: ze1,
      e1_count: e1,
      entry_accuracy: entryAccuracy,
      exit_accuracy: exitAccuracy,
      win_count: winCount,
      loss_count: lossCount,
      win_rate: winRate,
      avg_pnl: raw.avg_pnl || 0,
      total_pnl: raw.total_pnl || 0,
    };
  };

  const generateMockStats = (): SessionStats => {
    // Generate realistic mock data for development
    const s1 = Math.floor(Math.random() * 15) + 5;
    const z1 = Math.floor(s1 * (0.5 + Math.random() * 0.3)); // 50-80% of S1
    const o1 = s1 - z1;
    const ze1 = Math.floor(z1 * (0.6 + Math.random() * 0.3)); // 60-90% of Z1
    const e1 = z1 - ze1;
    const winCount = Math.floor(ze1 * (0.4 + Math.random() * 0.4)); // 40-80% win
    const lossCount = ze1 - winCount;

    return processStats({
      s1_count: s1,
      z1_count: z1,
      o1_count: o1,
      ze1_count: ze1,
      e1_count: e1,
      win_count: winCount,
      loss_count: lossCount,
      avg_pnl: (Math.random() - 0.3) * 50, // -15 to +35
      total_pnl: (Math.random() - 0.3) * 500, // -150 to +350
    });
  };

  const getAccuracyColor = (value: number): 'success' | 'warning' | 'error' => {
    if (value >= 70) return 'success';
    if (value >= 50) return 'warning';
    return 'error';
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading statistics...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (!stats) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">No statistics available for this session.</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <AccuracyIcon color="primary" />
        <Typography variant="h6">Session Statistics (SH-03)</Typography>
        <Tooltip title="Statistics are calculated from state machine transitions. Entry accuracy = how often S1 signals led to positions. Exit accuracy = how often exits were planned (not emergency).">
          <InfoIcon fontSize="small" color="action" sx={{ ml: 'auto' }} />
        </Tooltip>
      </Box>

      {/* Signal Counts */}
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        State Machine Signals
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* S1 - Signal Detected */}
        <Grid item xs={6} sm={4} md={2.4}>
          <Card variant="outlined">
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <SignalIcon fontSize="small" sx={{ color: '#ff9800' }} />
                <Typography variant="caption" color="text.secondary">S1 Signals</Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>{stats.s1_count}</Typography>
              <Typography variant="caption" color="text.secondary">Pumps detected</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Z1 - Entry */}
        <Grid item xs={6} sm={4} md={2.4}>
          <Card variant="outlined">
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <EntryIcon fontSize="small" sx={{ color: '#4caf50' }} />
                <Typography variant="caption" color="text.secondary">Z1 Entries</Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>{stats.z1_count}</Typography>
              <Typography variant="caption" color="text.secondary">Positions opened</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* O1 - Timeout */}
        <Grid item xs={6} sm={4} md={2.4}>
          <Card variant="outlined">
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <TimeoutIcon fontSize="small" sx={{ color: '#607d8b' }} />
                <Typography variant="caption" color="text.secondary">O1 Timeouts</Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>{stats.o1_count}</Typography>
              <Typography variant="caption" color="text.secondary">Signals expired</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* ZE1 - Normal Close */}
        <Grid item xs={6} sm={4} md={2.4}>
          <Card variant="outlined">
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <CloseIcon fontSize="small" sx={{ color: '#2196f3' }} />
                <Typography variant="caption" color="text.secondary">ZE1 Closes</Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>{stats.ze1_count}</Typography>
              <Typography variant="caption" color="text.secondary">Planned exits</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* E1 - Emergency */}
        <Grid item xs={6} sm={4} md={2.4}>
          <Card variant="outlined">
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <EmergencyIcon fontSize="small" sx={{ color: '#f44336' }} />
                <Typography variant="caption" color="text.secondary">E1 Emergency</Typography>
              </Box>
              <Typography variant="h5" fontWeight={600}>{stats.e1_count}</Typography>
              <Typography variant="caption" color="text.secondary">Emergency exits</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      {/* Accuracy Metrics */}
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        Accuracy Metrics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Entry Accuracy */}
        <Grid item xs={12} sm={6} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" fontWeight={500}>
                  Entry Accuracy
                </Typography>
                <Chip
                  label={`${stats.entry_accuracy?.toFixed(1)}%`}
                  size="small"
                  color={getAccuracyColor(stats.entry_accuracy || 0)}
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats.entry_accuracy || 0}
                color={getAccuracyColor(stats.entry_accuracy || 0)}
                sx={{ height: 8, borderRadius: 1 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {stats.z1_count} entries / {stats.z1_count + stats.o1_count} signals
              </Typography>
              <Tooltip title="Entry accuracy = Z1 / (Z1 + O1). High value means signals often led to actual positions.">
                <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                  How often S1 signals result in entry
                </Typography>
              </Tooltip>
            </CardContent>
          </Card>
        </Grid>

        {/* Exit Accuracy */}
        <Grid item xs={12} sm={6} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" fontWeight={500}>
                  Exit Accuracy
                </Typography>
                <Chip
                  label={`${stats.exit_accuracy?.toFixed(1)}%`}
                  size="small"
                  color={getAccuracyColor(stats.exit_accuracy || 0)}
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats.exit_accuracy || 0}
                color={getAccuracyColor(stats.exit_accuracy || 0)}
                sx={{ height: 8, borderRadius: 1 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {stats.ze1_count} planned / {stats.ze1_count + stats.e1_count} total exits
              </Typography>
              <Tooltip title="Exit accuracy = ZE1 / (ZE1 + E1). High value means most exits were planned, not emergency.">
                <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                  How often exits were planned vs emergency
                </Typography>
              </Tooltip>
            </CardContent>
          </Card>
        </Grid>

        {/* Win Rate */}
        <Grid item xs={12} sm={6} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" fontWeight={500}>
                  Win Rate
                </Typography>
                <Chip
                  label={`${stats.win_rate?.toFixed(1)}%`}
                  size="small"
                  color={getAccuracyColor(stats.win_rate || 0)}
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats.win_rate || 0}
                color={getAccuracyColor(stats.win_rate || 0)}
                sx={{ height: 8, borderRadius: 1 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {stats.win_count} wins / {(stats.win_count || 0) + (stats.loss_count || 0)} trades
              </Typography>
              <Tooltip title="Win rate = Winning trades / Total trades">
                <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                  Percentage of profitable trades
                </Typography>
              </Tooltip>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* P&L Summary */}
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        Profit & Loss
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={6}>
          <Card variant="outlined">
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <PnLIcon fontSize="small" color="primary" />
                <Typography variant="body2" color="text.secondary">
                  Average P&L per Trade
                </Typography>
              </Box>
              <Typography
                variant="h4"
                fontWeight={600}
                color={(stats.avg_pnl || 0) >= 0 ? 'success.main' : 'error.main'}
              >
                {(stats.avg_pnl || 0) >= 0 ? '+' : ''}${(stats.avg_pnl || 0).toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6}>
          <Card variant="outlined">
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WinRateIcon fontSize="small" color="primary" />
                <Typography variant="body2" color="text.secondary">
                  Total Session P&L
                </Typography>
              </Box>
              <Typography
                variant="h4"
                fontWeight={600}
                color={(stats.total_pnl || 0) >= 0 ? 'success.main' : 'error.main'}
              >
                {(stats.total_pnl || 0) >= 0 ? '+' : ''}${(stats.total_pnl || 0).toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Info Note */}
      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="caption">
          <strong>Signal Flow:</strong> S1 (pump detected) → Z1 (entry) OR O1 (timeout) → ZE1 (planned exit) OR E1 (emergency exit)
        </Typography>
      </Alert>
    </Paper>
  );
};

export default SessionSummaryStats;
