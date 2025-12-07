'use client';

/**
 * Session Detail Page (SH-02)
 * ===========================
 *
 * Detailed view of a single trading session.
 * Shows state machine transitions, trades, P&L breakdown.
 *
 * Implemented features:
 * - SH-03: Summary stats (S1 count, Z1 count, accuracy) ✅
 * - SH-04: Transition timeline visualization ✅
 * - SH-05: Transition details (expandable with indicator values) ✅
 * - SH-07: Per-trade breakdown table ✅
 * - SH-08: Session replay mode ✅
 *
 * TODO (Future sprint):
 * - SH-06: Chart with S1/Z1/ZE1 markers (use SM-05 component)
 *
 * Related: docs/UI_BACKLOG.md - SH-02 through SH-08
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Breadcrumbs,
  Link,
  Divider,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  CalendarToday as DateIcon,
  TrendingUp as TrendingIcon,
  PlayCircle as ReplayIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { SessionReplayPlayer, ReplayDataPoint } from '@/components/session-history/SessionReplayPlayer';
import { TransitionTimeline } from '@/components/session-history/TransitionTimeline';
import { SessionSummaryStats } from '@/components/session-history/SessionSummaryStats';
import { TradeBreakdownTable } from '@/components/session-history/TradeBreakdownTable';
import { TransitionDetails } from '@/components/session-history/TransitionDetails';
import {
  Timeline as TimelineIcon,
  Analytics as StatsIcon,
  TableChart as TradesIcon,
  ListAlt as DetailsIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

interface SessionDetail {
  session_id: string;
  strategy_id: string;
  strategy_name: string;
  symbols: string;
  direction: string;
  status: string;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  initial_balance: number;
  current_balance?: number;
  total_pnl?: number;
  total_return_pct?: number;
  notes?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.sessionId as string;

  // State
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [currentReplayPoint, setCurrentReplayPoint] = useState<ReplayDataPoint | null>(null);

  // SH-08: Handle replay data point changes
  const handleReplayDataPointChange = useCallback((dataPoint: ReplayDataPoint, index: number) => {
    setCurrentReplayPoint(dataPoint);
  }, []);

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    const loadSessionDetail = async () => {
      if (!sessionId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/paper-trading/sessions/${sessionId}`);

        if (!response.ok) {
          throw new Error(`Failed to load session: ${response.status}`);
        }

        const result = await response.json();
        setSession(result.session || result);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        console.error('Failed to load session detail:', err);
      } finally {
        setLoading(false);
      }
    };

    loadSessionDetail();
  }, [sessionId]);

  // ========================================
  // Render Helpers
  // ========================================

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button
          variant="outlined"
          startIcon={<BackIcon />}
          onClick={() => router.push('/session-history')}
        >
          Back to Session History
        </Button>
      </Box>
    );
  }

  if (!session) {
    return (
      <Box>
        <Alert severity="warning" sx={{ mb: 3 }}>
          Session not found
        </Alert>
        <Button
          variant="outlined"
          startIcon={<BackIcon />}
          onClick={() => router.push('/session-history')}
        >
          Back to Session History
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body1"
          onClick={() => router.push('/session-history')}
          sx={{ cursor: 'pointer' }}
        >
          Session History
        </Link>
        <Typography color="text.primary">{session.session_id}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Session Details
        </Typography>

        <Button
          variant="outlined"
          startIcon={<BackIcon />}
          onClick={() => router.push('/session-history')}
        >
          Back
        </Button>
      </Box>

      {/* Session Info */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Session ID
            </Typography>
            <Typography variant="body1" fontWeight={500}>
              {session.session_id}
            </Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Strategy
            </Typography>
            <Typography variant="body1" fontWeight={500}>
              {session.strategy_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {session.strategy_id}
            </Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Symbols
            </Typography>
            <Typography variant="body1">{session.symbols}</Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Direction
            </Typography>
            <Typography variant="body1">{session.direction}</Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Created
            </Typography>
            <Typography variant="body1">{formatDate(session.created_at)}</Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Status
            </Typography>
            <Typography variant="body1">{session.status}</Typography>
          </Grid>

          {session.started_at && (
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Started
              </Typography>
              <Typography variant="body1">{formatDate(session.started_at)}</Typography>
            </Grid>
          )}

          {session.stopped_at && (
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Stopped
              </Typography>
              <Typography variant="body1">{formatDate(session.stopped_at)}</Typography>
            </Grid>
          )}
        </Grid>
      </Paper>

      {/* Performance Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Initial Balance
              </Typography>
              <Typography variant="h5">${session.initial_balance.toFixed(2)}</Typography>
            </CardContent>
          </Card>
        </Grid>

        {session.current_balance !== undefined && (
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Current Balance
                </Typography>
                <Typography variant="h5">${session.current_balance.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {session.total_pnl !== undefined && (
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Total P&L
                </Typography>
                <Typography
                  variant="h5"
                  color={session.total_pnl >= 0 ? 'success.main' : 'error.main'}
                >
                  {session.total_pnl >= 0 ? '+' : ''}${session.total_pnl.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {session.total_return_pct !== undefined && (
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Return %
                </Typography>
                <Typography
                  variant="h5"
                  color={session.total_return_pct >= 0 ? 'success.main' : 'error.main'}
                >
                  {session.total_return_pct >= 0 ? '+' : ''}
                  {session.total_return_pct.toFixed(2)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Tabs for different views */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Statistics" icon={<StatsIcon />} iconPosition="start" />
          <Tab label="Timeline" icon={<TimelineIcon />} iconPosition="start" />
          <Tab label="Details" icon={<DetailsIcon />} iconPosition="start" />
          <Tab label="Trades" icon={<TradesIcon />} iconPosition="start" />
          <Tab label="Replay Mode" icon={<ReplayIcon />} iconPosition="start" />
        </Tabs>

        {/* Tab 0: SH-03 Summary Stats */}
        {activeTab === 0 && (
          <Box sx={{ p: 3 }}>
            <SessionSummaryStats sessionId={sessionId} />
          </Box>
        )}

        {/* Tab 1: SH-04 Transition Timeline */}
        {activeTab === 1 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Transition Timeline (SH-04)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Visual timeline showing state machine transitions during this session.
              Click on nodes to expand details and see trigger values.
            </Typography>

            {/* Timeline Component */}
            <TransitionTimeline
              sessionId={sessionId}
              height={450}
            />
          </Box>
        )}

        {/* Tab 2: SH-05 Transition Details */}
        {activeTab === 2 && (
          <Box sx={{ p: 3 }}>
            <TransitionDetails sessionId={sessionId} />
          </Box>
        )}

        {/* Tab 3: SH-07 Trade Breakdown */}
        {activeTab === 3 && (
          <Box sx={{ p: 3 }}>
            <TradeBreakdownTable sessionId={sessionId} />
          </Box>
        )}

        {/* Tab 4: SH-08 Replay Mode */}
        {activeTab === 4 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Session Replay (SH-08)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Step through the trading session data point by data point. Use the controls to play,
              pause, or step through the session to analyze how the state machine reacted to market conditions.
            </Typography>

            {/* Replay Player */}
            <SessionReplayPlayer
              sessionId={sessionId}
              symbol={session.symbols.split(',')[0]?.trim() || 'BTC_USDT'}
              onDataPointChange={handleReplayDataPointChange}
            />

            {/* Current Replay Point Details */}
            {currentReplayPoint && (
              <Paper sx={{ p: 2, mt: 2, backgroundColor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Current Data Point
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">
                      Time
                    </Typography>
                    <Typography variant="body2">
                      {new Date(currentReplayPoint.timestamp).toLocaleString()}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">
                      Price
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      ${currentReplayPoint.price.toFixed(2)}
                    </Typography>
                  </Grid>
                  {currentReplayPoint.state && (
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="text.secondary">
                        State
                      </Typography>
                      <Typography variant="body2">
                        {currentReplayPoint.state}
                      </Typography>
                    </Grid>
                  )}
                  {currentReplayPoint.transition && (
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="text.secondary">
                        Transition
                      </Typography>
                      <Typography variant="body2">
                        {currentReplayPoint.transition.trigger}: {currentReplayPoint.transition.from_state} → {currentReplayPoint.transition.to_state}
                      </Typography>
                    </Grid>
                  )}
                </Grid>

                {/* Indicator Values */}
                {currentReplayPoint.indicators && Object.keys(currentReplayPoint.indicators).length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Indicators
                    </Typography>
                    <Grid container spacing={1}>
                      {Object.entries(currentReplayPoint.indicators).map(([key, value]) => (
                        <Grid item xs={6} md={2} key={key}>
                          <Typography variant="caption" color="text.secondary">
                            {key}
                          </Typography>
                          <Typography variant="body2" fontWeight={500}>
                            {typeof value === 'number' ? value.toFixed(4) : value}
                          </Typography>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}
              </Paper>
            )}
          </Box>
        )}
      </Paper>
    </Box>
  );
}
