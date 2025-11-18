'use client';

/**
 * Unified Trading Dashboard
 * ========================
 *
 * Single-screen interface for ALL trading modes:
 * - Live Trading (real money)
 * - Paper Trading (virtual money)
 * - Backtesting (historical data replay)
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 * Performance Target: 2-second time-to-insight (93% improvement from 30s)
 *
 * Architecture:
 * - Single initial load: GET /api/dashboard/summary
 * - Real-time updates: WebSocket subscriptions
 * - Cache-optimized queries: <100ms response time
 *
 * Layout:
 * ┌─────────────────────────────────────────────────┐
 * │ Mode Switcher: [Live|Paper|Backtest]  Controls │
 * ├──────────────────┬──────────────────────────────┤
 * │ Symbol Watchlist │ Live Indicator Panel         │
 * │ - BTC_USDT       │ - TWPA(300,0): 50250         │
 * │ - ETH_USDT       │ - Velocity(60,0): 0.05       │
 * │ - ADA_USDT       │ - Volume_Surge: 1.2x         │
 * ├──────────────────┴──────────────────────────────┤
 * │ Recent Signals (last 10)                        │
 * │ - [12:34] BTC_USDT LONG (confidence: 0.85)      │
 * └─────────────────────────────────────────────────┘
 */

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  ToggleButton,
  ToggleButtonGroup,
  Alert,
  Snackbar,
  LinearProgress,
  Chip,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import { SymbolWatchlist, type SymbolData } from '@/components/dashboard/SymbolWatchlist';
import { LiveIndicatorPanel } from '@/components/dashboard/LiveIndicatorPanel';
import { CandlestickChart } from '@/components/dashboard/CandlestickChart';
import { MultiSymbolGrid } from '@/components/dashboard/MultiSymbolGrid';
import { SignalDetailPanel, type SignalDetail } from '@/components/dashboard/SignalDetailPanel';
import { SignalHistoryPanel } from '@/components/dashboard/SignalHistoryPanel';
import { TransactionHistoryPanel } from '@/components/dashboard/TransactionHistoryPanel';

// ============================================================================
// Types
// ============================================================================

type TradingMode = 'live' | 'paper' | 'backtest';

interface DashboardSummary {
  session_id: string;
  global_pnl: number;
  total_positions: number;
  total_signals: number;
  symbols: SymbolData[];
  recent_signals: Signal[];
  risk_metrics: RiskMetrics;
  last_updated: string;
}

interface Signal {
  signal_id: string;
  symbol: string;
  signal_type: string;
  side: 'LONG' | 'SHORT';
  confidence: number;
  execution_status: string;
  timestamp: string;
}

interface RiskMetrics {
  budget_utilization_pct: number;
  avg_margin_ratio: number;
  max_drawdown_pct: number;
  active_alerts: string[];
}

// ============================================================================
// Dashboard Content Component (wrapped in Suspense)
// ============================================================================

function DashboardContent() {
  // ========================================
  // State Management
  // ========================================

  // Get mode from URL query parameter (for /trading and /backtesting redirects)
  const searchParams = useSearchParams();
  const urlMode = searchParams?.get('mode') as TradingMode | null;

  const [mode, setMode] = useState<TradingMode>(urlMode || 'paper');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC_USDT');

  // Backtest-specific state
  const [backtestSessionId, setBacktestSessionId] = useState<string>('');
  const [availableSessions, setAvailableSessions] = useState<any[]>([]);

  // View mode: 'single' or 'grid'
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');

  // Sync URL mode parameter with state on browser navigation
  // FIX: Only sync once on mount to avoid infinite loop
  useEffect(() => {
    if (urlMode) {
      setMode(urlMode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run on mount

  // Signal detail panel
  const [signalPanelOpen, setSignalPanelOpen] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState<SignalDetail | null>(null);

  // Tab for Signal History / Transaction History
  const [historyTab, setHistoryTab] = useState<number>(0);

  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // ========================================
  // Data Loading Functions
  // ========================================

  /**
   * Load complete dashboard data in SINGLE request.
   * Performance target: <100ms
   * FIX: Added AbortController for cancellation
   */
  const loadDashboardData = useCallback(async () => {
    if (!sessionId) return;

    const abortController = new AbortController();

    setLoading(true);
    try {
      // OPTIMIZED: Single request for all dashboard data
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/summary?session_id=${sessionId}`,
        { signal: abortController.signal }
      );

      if (!response.ok) {
        throw new Error(`Dashboard API error: ${response.status}`);
      }

      const result = await response.json();

      // Handle envelope response format
      const data = result.data || result;

      setDashboardData(data);
    } catch (error: any) {
      // Don't show error for aborted requests
      if (error.name === 'AbortError') return;

      console.error('Failed to load dashboard data:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load dashboard data',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }

    // Cleanup function to cancel request on unmount/re-render
    return () => abortController.abort();
  }, [sessionId]);

  /**
   * Load available data collection sessions for backtest mode.
   */
  const loadAvailableSessions = useCallback(async () => {
    if (mode !== 'backtest') return;

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/data-collection/sessions`);
      if (!response.ok) throw new Error('Failed to load sessions');

      const result = await response.json();
      const sessions = result.data?.sessions || result.sessions || [];

      setAvailableSessions(sessions);

      // Auto-select first session if available
      if (sessions.length > 0 && !backtestSessionId) {
        setBacktestSessionId(sessions[0].session_id);
      }
    } catch (error) {
      console.error('Failed to load available sessions:', error);
    }
  }, [mode, backtestSessionId]);

  /**
   * Check current execution status.
   * Used to detect running sessions on mount.
   */
  const checkExecutionStatus = useCallback(async () => {
    try {
      const status = await apiService.getExecutionStatus();

      if (status && status.session_id && status.status === 'running') {
        setSessionId(status.session_id);
        setIsSessionRunning(true);

        // Detect mode from session
        const sessionType = status.session_type || 'paper';
        if (sessionType === 'live' || sessionType === 'paper' || sessionType === 'backtest') {
          setMode(sessionType as TradingMode);
        }
      } else {
        setIsSessionRunning(false);
      }
    } catch (error) {
      console.error('Failed to check execution status:', error);
    }
  }, []);

  // ========================================
  // Effects
  // ========================================

  // Initial load: Check for running session
  useEffect(() => {
    checkExecutionStatus();
  }, [checkExecutionStatus]);

  // Load available sessions when switching to backtest mode
  useEffect(() => {
    if (mode === 'backtest') {
      loadAvailableSessions();
    }
  }, [mode, loadAvailableSessions]);

  // Load dashboard data when sessionId changes
  useEffect(() => {
    if (sessionId && isSessionRunning) {
      loadDashboardData();
    }
  }, [sessionId, isSessionRunning, loadDashboardData]);

  // Auto-refresh every 2 seconds when session is running
  useVisibilityAwareInterval(
    () => {
      if (isSessionRunning && sessionId) {
        loadDashboardData();
      }
    },
    2000 // 2-second refresh for real-time feel
  );

  // ========================================
  // Event Handlers
  // ========================================

  const handleModeChange = (_event: React.MouseEvent<HTMLElement>, newMode: TradingMode | null) => {
    if (newMode !== null) {
      setMode(newMode);
    }
  };

  const handleStartSession = async () => {
    // Validate backtest mode requires session selection
    if (mode === 'backtest' && !backtestSessionId) {
      setSnackbar({
        open: true,
        message: 'Please select a data collection session for backtesting',
        severity: 'warning',
      });
      return;
    }

    try {
      const sessionData: any = {
        session_type: mode,
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'], // TODO: Make configurable
        strategy_config: {}, // TODO: Load from strategy selection
        config: {
          budget: {
            global_cap: 1000,
            allocations: {},
          },
        },
        idempotent: true,
      };

      // ✅ FIX: For backtest mode, include the data collection session_id in config
      // Backend expects session_id in config object (not on root level)
      // See: docs/frontend/BACKTEST_SESSION_FIX.md and tests_e2e/integration/test_backtest_session_flow.py
      if (mode === 'backtest') {
        sessionData.config.session_id = backtestSessionId;
      }

      const response = await apiService.startSession(sessionData);

      setSessionId(response.data?.session_id || null);
      setIsSessionRunning(true);

      setSnackbar({
        open: true,
        message: `${mode.toUpperCase()} session started successfully`,
        severity: 'success',
      });
    } catch (error) {
      console.error('Failed to start session:', error);
      setSnackbar({
        open: true,
        message: 'Failed to start session',
        severity: 'error',
      });
    }
  };

  const handleStopSession = async () => {
    if (!sessionId) return;

    try {
      await apiService.stopSession(sessionId);

      setIsSessionRunning(false);
      setDashboardData(null);

      setSnackbar({
        open: true,
        message: 'Session stopped successfully',
        severity: 'success',
      });
    } catch (error) {
      console.error('Failed to stop session:', error);
      setSnackbar({
        open: true,
        message: 'Failed to stop session',
        severity: 'error',
      });
    }
  };

  const handleRefresh = () => {
    loadDashboardData();
  };

  const handleSignalClick = (signal: Signal) => {
    // Convert Signal to SignalDetail (add mock indicator details for now)
    const signalDetail: SignalDetail = {
      ...signal,
      indicators: [
        {
          indicator_id: 'twpa_300_0',
          indicator_name: 'TWPA(300,0)',
          value: 50250,
          threshold_min: 50000,
          met: true,
        },
        {
          indicator_id: 'velocity_60_0',
          indicator_name: 'Velocity(60,0)',
          value: 0.85,
          threshold_min: 0.5,
          met: true,
        },
        {
          indicator_id: 'volume_surge',
          indicator_name: 'Volume_Surge',
          value: 2.3,
          threshold_min: 2.0,
          met: true,
        },
      ],
      execution: {
        status: signal.execution_status,
        order_id: signal.signal_id,
        entry_price: 50250,
        size: 0.1,
        risk_score: 3,
      },
    };

    setSelectedSignal(signalDetail);
    setSignalPanelOpen(true);
  };

  const handleViewModeToggle = () => {
    setViewMode(viewMode === 'single' ? 'grid' : 'single');
  };

  // ========================================
  // Render
  // ========================================

  return (
    <Box>
      {/* Header: Mode Switcher + Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" component="h1">
            {mode === 'live' && '🔴 Live Trading Dashboard'}
            {mode === 'paper' && '📝 Paper Trading Dashboard'}
            {mode === 'backtest' && '⏮️ Backtesting Dashboard'}
          </Typography>

          {/* Mode Switcher */}
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={handleModeChange}
            disabled={isSessionRunning}
            size="small"
          >
            <ToggleButton value="paper">
              Paper Trading
            </ToggleButton>
            <ToggleButton value="live">
              Live Trading
            </ToggleButton>
            <ToggleButton value="backtest">
              Backtesting
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Control Buttons */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          {isSessionRunning && (
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(_, newMode) => newMode && setViewMode(newMode)}
              size="small"
            >
              <ToggleButton value="single">Single View</ToggleButton>
              <ToggleButton value="grid">Grid View</ToggleButton>
            </ToggleButtonGroup>
          )}

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading || !isSessionRunning}
          >
            Refresh
          </Button>

          {isSessionRunning ? (
            <Button
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopSession}
            >
              Stop Session
            </Button>
          ) : (
            <>
              {mode === 'backtest' && (
                <FormControl sx={{ minWidth: 300, mr: 2 }} size="small">
                  <InputLabel>Data Collection Session</InputLabel>
                  <Select
                    value={backtestSessionId}
                    label="Data Collection Session"
                    onChange={(e) => setBacktestSessionId(e.target.value)}
                  >
                    {availableSessions.length === 0 ? (
                      <MenuItem disabled>No sessions available</MenuItem>
                    ) : (
                      availableSessions.map((session) => (
                        <MenuItem key={session.session_id} value={session.session_id}>
                          {session.session_id} ({new Date(session.start_time).toLocaleDateString()})
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              )}
              <Button
                variant="contained"
                color="success"
                startIcon={<PlayIcon />}
                onClick={handleStartSession}
                disabled={mode === 'backtest' && !backtestSessionId}
              >
                Start {mode === 'paper' ? 'Paper' : mode === 'live' ? 'Live' : 'Backtest'} Session
              </Button>
            </>
          )}
        </Box>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Active Session Alert */}
      {isSessionRunning && sessionId && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Active Session:</strong> {sessionId} |
            <strong> Mode:</strong> {mode.toUpperCase()} |
            <strong> Status:</strong> Running
          </Typography>
        </Alert>
      )}

      {/* Main Dashboard Content */}
      {!isSessionRunning ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <SpeedIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h5" color="text.secondary" gutterBottom>
            No Active Session
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Select a trading mode and click &quot;Start Session&quot; to begin monitoring.
          </Typography>
        </Paper>
      ) : dashboardData ? (
        <Grid container spacing={3}>
          {/* Summary Cards */}
          <Grid item xs={12}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Global P&L
                    </Typography>
                    <Typography
                      variant="h4"
                      color={dashboardData.global_pnl >= 0 ? 'success.main' : 'error.main'}
                    >
                      ${dashboardData.global_pnl.toFixed(2)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Active Positions
                    </Typography>
                    <Typography variant="h4" color="primary">
                      {dashboardData.total_positions}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Total Signals
                    </Typography>
                    <Typography variant="h4" color="secondary">
                      {dashboardData.total_signals}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Budget Usage
                    </Typography>
                    <Typography variant="h4" color="info.main">
                      {dashboardData.risk_metrics.budget_utilization_pct.toFixed(1)}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Grid>

          {/* Conditional Rendering: Single View vs Grid View */}
          {viewMode === 'single' ? (
            <>
              {/* Single View: Watchlist + Chart + Indicators */}
              <Grid item xs={12} md={4}>
                <SymbolWatchlist
                  symbols={dashboardData.symbols}
                  loading={loading}
                  onSymbolClick={(symbol) => setSelectedSymbol(symbol)}
                />
              </Grid>

              <Grid item xs={12} md={8}>
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    {selectedSymbol} Chart
                  </Typography>
                  <CandlestickChart
                    symbol={selectedSymbol}
                    sessionId={sessionId}
                    height={400}
                    autoRefresh={true}
                  />
                </Paper>

                <LiveIndicatorPanel
                  sessionId={sessionId}
                  symbol={selectedSymbol}
                  refreshInterval={5000}
                />
              </Grid>
            </>
          ) : (
            /* Grid View: Multi-Symbol Grid */
            <Grid item xs={12}>
              <MultiSymbolGrid
                symbols={dashboardData.symbols}
                sessionId={sessionId}
                gridSize={2}
                onSymbolExpand={(symbol) => {
                  setSelectedSymbol(symbol);
                  setViewMode('single');
                }}
              />
            </Grid>
          )}

          {/* Signal History & Transaction History (Tabbed) */}
          <Grid item xs={12}>
            <Paper sx={{ p: 0 }}>
              <Tabs
                value={historyTab}
                onChange={(_, newValue) => setHistoryTab(newValue)}
                sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
              >
                <Tab label="📊 Signal History" />
                <Tab label="💰 Transaction History" />
              </Tabs>

              <Box sx={{ p: 2 }}>
                <Box sx={{ display: historyTab === 0 ? 'block' : 'none' }}>
                  <SignalHistoryPanel
                    sessionId={sessionId}
                    symbol={viewMode === 'single' ? selectedSymbol : undefined}
                    refreshInterval={5000}
                    isActive={historyTab === 0}
                  />
                </Box>
                <Box sx={{ display: historyTab === 1 ? 'block' : 'none' }}>
                  <TransactionHistoryPanel
                    sessionId={sessionId}
                    refreshInterval={5000}
                    isActive={historyTab === 1}
                  />
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            Loading dashboard data...
          </Typography>
        </Paper>
      )}

      {/* Signal Detail Panel (Slide-out) */}
      <SignalDetailPanel
        open={signalPanelOpen}
        signal={selectedSignal}
        onClose={() => setSignalPanelOpen(false)}
      />

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
}

// ============================================================================
// Main Component with Suspense Boundary
// ============================================================================

export default function UnifiedDashboardPage() {
  return (
    <Suspense fallback={
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    }>
      <DashboardContent />
    </Suspense>
  );
}
