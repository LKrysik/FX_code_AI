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
import { IndicatorValuesPanel } from '@/components/dashboard/IndicatorValuesPanel'; // Story 1A-3
import { CandlestickChart } from '@/components/dashboard/CandlestickChart';
import { MultiSymbolGrid } from '@/components/dashboard/MultiSymbolGrid';
import { SignalDetailPanel, type SignalDetail } from '@/components/dashboard/SignalDetailPanel';
import { SignalHistoryPanel } from '@/components/dashboard/SignalHistoryPanel';
import { RecentSignalsPanel } from '@/components/dashboard/RecentSignalsPanel'; // Story 1A-1
import { TransactionHistoryPanel } from '@/components/dashboard/TransactionHistoryPanel';
import { SessionConfigDialog, type SessionConfig } from '@/components/dashboard/SessionConfigDialog';
import EquityCurveChart from '@/components/charts/EquityCurveChart';
import DrawdownChart from '@/components/charts/DrawdownChart';
import PositionMonitor from '@/components/trading/PositionMonitor';
import StateOverviewTableIntegration from '@/components/dashboard/StateOverviewTable.integration';
import ConditionProgressIntegration from '@/components/dashboard/ConditionProgress.integration';
import TransitionLogIntegration from '@/components/dashboard/TransitionLog.integration';
import PumpIndicatorsPanel from '@/components/dashboard/PumpIndicatorsPanel';
import ActivePositionBanner from '@/components/dashboard/ActivePositionBanner';
import StateBadge from '@/components/dashboard/StateBadge'; // Story 1A-2
import StatusHero from '@/components/dashboard/StatusHero'; // Story 1A-5
import { useStateMachineState } from '@/hooks/useStateMachineState'; // Story 1A-2
import { useStatusHeroData } from '@/hooks/useStatusHeroData'; // Story 1A-5
import { Logger } from '@/services/frontendLogService';

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

interface EquityCurveDataPoint {
  timestamp: string;
  current_balance: number;
  total_pnl: number;
  total_return_pct: number;
  max_drawdown?: number;
  current_drawdown?: number;
}

interface EquityCurveResponse {
  session_id: string;
  initial_balance: number;
  equity_curve: EquityCurveDataPoint[];
  last_updated: string;
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
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  // ✅ FIX (BUG-003-2): Auto-select first symbol from session when dashboard data loads
  useEffect(() => {
    if (dashboardData?.symbols && dashboardData.symbols.length > 0) {
      const firstSymbol = dashboardData.symbols[0]?.symbol;
      if (firstSymbol && firstSymbol !== selectedSymbol) {
        Logger.debug('DashboardPage.autoSelectSymbol', 'Auto-selecting first symbol from session', { symbol: firstSymbol });
        setSelectedSymbol(firstSymbol);
      }
    }
  }, [dashboardData?.symbols]);

  // Story 1A-2: State Machine State for Hero Badge
  const { currentState: stateMachineState, since: stateSince } = useStateMachineState();

  // Story 1A-5: StatusHero Data Integration
  const statusHeroData = useStatusHeroData(sessionId, selectedSymbol);

  // FIX ERROR 45: Loading state for session start/stop
  const [sessionActionLoading, setSessionActionLoading] = useState(false);

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

  // Session configuration dialog
  const [configDialogOpen, setConfigDialogOpen] = useState(false);

  // Equity Curve data for performance visualization
  const [equityCurveData, setEquityCurveData] = useState<EquityCurveDataPoint[]>([]);
  const [initialBalance, setInitialBalance] = useState<number>(10000);

  // Trade markers for equity chart
  interface TradeMarker {
    timestamp: string;
    side: 'BUY' | 'SELL';
    symbol: string;
    price: number;
    quantity: number;
    pnl?: number;
  }
  const [tradeMarkers, setTradeMarkers] = useState<TradeMarker[]>([]);

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
   * FIX: Proper AbortController usage with cleanup
   */
  const loadDashboardData = useCallback(async (signal?: AbortSignal, isBackgroundRefresh = false) => {
    Logger.debug('DashboardPage.loadDashboardData', 'Called', { sessionId, isBackgroundRefresh });
    if (!sessionId) {
      Logger.debug('DashboardPage.loadDashboardData', 'SKIPPED - no sessionId');
      return;
    }

    Logger.debug('DashboardPage.loadDashboardData', 'STARTING fetch');
    // ✅ FIX (BUG-003-7): Only show loading on initial load, not on background refreshes
    // This prevents UI flickering during periodic updates
    const shouldShowLoading = !isBackgroundRefresh;
    if (shouldShowLoading) {
      setLoading(true);
    }
    try {
      // OPTIMIZED: Single request for all dashboard data
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/summary?session_id=${sessionId}`,
        { signal }
      );

      Logger.debug('DashboardPage.loadDashboardData', 'Fetch response', { ok: response.ok, status: response.status });

      if (!response.ok) {
        throw new Error(`Dashboard API error: ${response.status}`);
      }

      const result = await response.json();

      // Type-safe null check
      if (!result) {
        throw new Error('Empty response from dashboard API');
      }

      // Handle envelope response format
      const data = result.data || result;

      // ✅ FIX (BUG-003-5): Deduplicate symbols to prevent duplicate LiveIndicatorPanel rendering
      if (data.symbols && Array.isArray(data.symbols)) {
        const seen = new Set<string>();
        data.symbols = data.symbols.filter((s: { symbol: string }) => {
          if (seen.has(s.symbol)) {
            Logger.debug('DashboardPage.loadDashboardData', 'Removed duplicate symbol', { symbol: s.symbol });
            return false;
          }
          seen.add(s.symbol);
          return true;
        });
      }

      Logger.debug('DashboardPage.loadDashboardData', 'SUCCESS', { symbolCount: data.symbols?.length });
      setDashboardData(data);
    } catch (error) {
      // Don't show error for aborted requests
      if (error instanceof Error && error.name === 'AbortError') {
        Logger.debug('DashboardPage.loadDashboardData', 'ABORTED');
        return;
      }

      Logger.error('DashboardPage.loadDashboardData', 'Failed to load dashboard data', { error });

      // Type-safe error message
      const errorMessage = error instanceof Error
        ? error.message
        : 'Unknown error occurred';

      setSnackbar({
        open: true,
        message: `Failed to load dashboard data: ${errorMessage}`,
        severity: 'error',
      });
    } finally {
      // ✅ FIX (BUG-003-7): Only clear loading if we set it (not on background refresh)
      if (!isBackgroundRefresh) {
        Logger.debug('DashboardPage.loadDashboardData', 'FINALLY - setLoading(false)');
        setLoading(false);
      }
    }
  }, [sessionId]);

  /**
   * Load available data collection sessions for backtest mode.
   * FIX ERROR 38: Added AbortController cleanup
   */
  const loadAvailableSessions = useCallback(async (signal?: AbortSignal) => {
    if (mode !== 'backtest') return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/data-collection/sessions`,
        { signal }
      );

      if (!response.ok) throw new Error('Failed to load sessions');

      const result = await response.json();
      const sessions = result.data?.sessions || result.sessions || [];

      setAvailableSessions(sessions);

      // Auto-select first session if available
      if (sessions.length > 0 && !backtestSessionId) {
        setBacktestSessionId(sessions[0].session_id);
      }
    } catch (error) {
      // Don't log aborted requests
      if (error instanceof Error && error.name === 'AbortError') return;

      Logger.error('DashboardPage.loadAvailableSessions', 'Failed to load available sessions', { error });
    }
  }, [mode, backtestSessionId]);

  /**
   * Load equity curve data for EquityCurveChart component.
   * Fetches balance history from paper_trading_performance table.
   */
  const loadEquityCurveData = useCallback(async (signal?: AbortSignal) => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/equity-curve?session_id=${sessionId}`,
        { signal }
      );

      if (!response.ok) return;

      const result = await response.json();
      const data = result.data || result;

      if (data.equity_curve) {
        setEquityCurveData(data.equity_curve);
      }
      if (data.initial_balance) {
        setInitialBalance(data.initial_balance);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      Logger.error('DashboardPage.loadEquityCurveData', 'Failed to load equity curve', { error });
    }
  }, [sessionId]);

  /**
   * Load trade markers for EquityCurveChart.
   * Fetches transaction history to show BUY/SELL markers on chart.
   */
  const loadTradeMarkers = useCallback(async (signal?: AbortSignal) => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transactions/history?session_id=${sessionId}&status=FILLED&limit=50`,
        { signal }
      );

      if (!response.ok) return;

      const result = await response.json();
      const data = result.data || result;

      if (data.transactions) {
        const markers: TradeMarker[] = data.transactions.map((tx: any) => ({
          timestamp: tx.timestamp,
          side: tx.side as 'BUY' | 'SELL',
          symbol: tx.symbol,
          price: tx.filled_price || tx.price,
          quantity: tx.filled_quantity || tx.quantity,
          pnl: tx.realized_pnl,
        }));
        setTradeMarkers(markers);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      Logger.error('DashboardPage.loadTradeMarkers', 'Failed to load trade markers', { error });
    }
  }, [sessionId]);

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
      Logger.error('DashboardPage.checkExecutionStatus', 'Failed to check execution status', { error });
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
  // FIX ERROR 40: Add AbortController and remove loadAvailableSessions from deps
  // Intentionally exclude loadAvailableSessions from deps to prevent unnecessary re-fetches
  useEffect(() => {
    if (mode !== 'backtest') return;

    const abortController = new AbortController();
    loadAvailableSessions(abortController.signal);

    return () => abortController.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]); // Removed loadAvailableSessions to prevent unnecessary re-fetches

  // Load dashboard data when sessionId changes
  // FIX: Added AbortController cleanup to prevent state updates after unmount
  // FIX: Load dashboard data when sessionId exists, regardless of isSessionRunning state
  // FIX: Include loadDashboardData in deps to avoid stale closure (React exhaustive-deps rule)
  useEffect(() => {
    Logger.debug('DashboardPage.useEffect', 'Session data effect triggered', { sessionId });
    if (!sessionId) {
      Logger.debug('DashboardPage.useEffect', 'SKIPPED - no sessionId');
      return;
    }

    Logger.debug('DashboardPage.useEffect', 'CALLING loadDashboardData');
    const abortController = new AbortController();

    loadDashboardData(abortController.signal);
    loadEquityCurveData(abortController.signal);
    loadTradeMarkers(abortController.signal);

    // Cleanup: abort fetch on unmount or when sessionId changes
    return () => {
      Logger.debug('DashboardPage.useEffect', 'CLEANUP - aborting');
      abortController.abort();
    };
  }, [sessionId, loadDashboardData, loadEquityCurveData, loadTradeMarkers]);

  // Auto-refresh every 2 seconds when session is running
  // FIX ERROR 37: Track abort controller for interval fetches to prevent memory leak
  const abortControllerRef = React.useRef<AbortController | null>(null);

  useVisibilityAwareInterval(
    () => {
      Logger.debug('DashboardPage.interval', 'TICK', { isSessionRunning, sessionId });
      if (isSessionRunning && sessionId) {
        // Cancel previous fetch if still in progress
        if (abortControllerRef.current) {
          Logger.debug('DashboardPage.interval', 'ABORTING previous fetch');
          abortControllerRef.current.abort();
        }

        // Create new abort controller for this fetch
        Logger.debug('DashboardPage.interval', 'CALLING loadDashboardData');
        abortControllerRef.current = new AbortController();
        // ✅ FIX (BUG-003-7): Pass isBackgroundRefresh=true to prevent flickering
        loadDashboardData(abortControllerRef.current.signal, true);
      }
    },
    2000 // 2-second refresh for real-time feel
  );

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // ========================================
  // Event Handlers
  // ========================================

  const handleModeChange = (_event: React.MouseEvent<HTMLElement>, newMode: TradingMode | null) => {
    if (newMode !== null) {
      setMode(newMode);
    }
  };

  const handleStartSessionClick = () => {
    // FIX: Prevent double-open by checking if already open
    if (configDialogOpen) return;

    // Open configuration dialog instead of starting directly
    setConfigDialogOpen(true);
  };

  const handleSessionConfigSubmit = async (config: SessionConfig) => {
    Logger.debug('DashboardPage.handleSessionConfigSubmit', 'START', { config });
    // FIX ERROR 45: Add loading state for better UX
    setSessionActionLoading(true);
    setConfigDialogOpen(false);

    try {
      Logger.debug('DashboardPage.handleSessionConfigSubmit', 'Calling apiService.startSession');
      const response = await apiService.startSession(config);
      Logger.debug('DashboardPage.handleSessionConfigSubmit', 'Response received', { response });

      // Type-safe null checks
      if (!response || !response.data) {
        throw new Error('Invalid response from startSession API');
      }

      Logger.debug('DashboardPage.handleSessionConfigSubmit', 'Setting sessionId and isSessionRunning', {
        sessionId: response.data.session_id
      });
      setSessionId(response.data.session_id || null);
      setIsSessionRunning(true);
      Logger.debug('DashboardPage.handleSessionConfigSubmit', 'State set - sessionId and isSessionRunning');

      setSnackbar({
        open: true,
        message: `${mode.toUpperCase()} session started successfully`,
        severity: 'success',
      });
    } catch (error) {
      Logger.error('DashboardPage.handleSessionConfigSubmit', 'Failed to start session', { error });

      // Type-safe error message
      const errorMessage = error instanceof Error
        ? error.message
        : 'Unknown error occurred';

      setSnackbar({
        open: true,
        message: `Failed to start session: ${errorMessage}`,
        severity: 'error',
      });
    } finally {
      Logger.debug('DashboardPage.handleSessionConfigSubmit', 'FINALLY');
      setSessionActionLoading(false);
    }
  };

  const handleStopSession = async () => {
    if (!sessionId) return;

    // FIX ERROR 46: Add loading state and optimistic UI
    setSessionActionLoading(true);

    try {
      await apiService.stopSession(sessionId);

      setIsSessionRunning(false);
      // FIX ERROR 44: Explicitly clear dashboard data to free memory
      setDashboardData(null);

      setSnackbar({
        open: true,
        message: 'Session stopped successfully',
        severity: 'success',
      });
    } catch (error) {
      // Enhanced error logging with full context for debugging
      Logger.error('DashboardPage.handleStopSession', 'Failed to stop session', {
        sessionId: sessionId,
        errorType: error instanceof Error ? error.constructor.name : typeof error,
        errorMessage: error instanceof Error ? error.message : String(error),
      });

      // Type-safe error message
      const errorMessage = error instanceof Error
        ? error.message
        : 'Unknown error occurred';

      setSnackbar({
        open: true,
        message: `Failed to stop session: ${errorMessage}`,
        severity: 'error',
      });
    } finally {
      setSessionActionLoading(false);
    }
  };

  const handleRefresh = () => {
    // Create abort controller for manual refresh (same pattern as useEffect)
    const abortController = new AbortController();
    loadDashboardData(abortController.signal);
  };

  const handleSignalClick = async (signal: Signal) => {
    // Fetch real signal details from API
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${apiUrl}/api/signals/${signal.signal_id}`);

      if (response.ok) {
        const result = await response.json();
        const signalData = result.data || result;

        // Transform API response to SignalDetail format
        const indicators = [];
        if (signalData.signal?.indicator_values) {
          // Convert indicator_values object to array format
          for (const [key, value] of Object.entries(signalData.signal.indicator_values)) {
            indicators.push({
              indicator_id: key,
              indicator_name: key,
              value: typeof value === 'number' ? value : 0,
              threshold_min: undefined,
              met: true,
            });
          }
        }

        const signalDetail: SignalDetail = {
          ...signal,
          indicators,
          execution: {
            status: signalData.order?.status || signal.execution_status,
            order_id: signalData.order?.order_id || signal.signal_id,
            entry_price: signalData.order?.filled_price || signalData.order?.price || 0,
            size: signalData.order?.quantity || 0,
            risk_score: signalData.position?.risk_score || 0,
          },
        };

        setSelectedSignal(signalDetail);
        setSignalPanelOpen(true);
      } else {
        // Fallback: show signal with no indicator details
        Logger.warn('DashboardPage.handleSignalClick', 'Failed to fetch signal details, showing basic info');
        const signalDetail: SignalDetail = {
          ...signal,
          indicators: [],
          execution: {
            status: signal.execution_status,
            order_id: signal.signal_id,
            entry_price: 0,
            size: 0,
            risk_score: 0,
          },
        };
        setSelectedSignal(signalDetail);
        setSignalPanelOpen(true);
      }
    } catch (error) {
      Logger.error('DashboardPage.handleSignalClick', 'Error fetching signal details', { error });
      // Fallback: show signal with no indicator details
      const signalDetail: SignalDetail = {
        ...signal,
        indicators: [],
        execution: {
          status: signal.execution_status,
          order_id: signal.signal_id,
          entry_price: 0,
          size: 0,
          risk_score: 0,
        },
      };
      setSelectedSignal(signalDetail);
      setSignalPanelOpen(true);
    }
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
            disabled={loading || !sessionId}
          >
            Refresh
          </Button>

          {isSessionRunning ? (
            <Button
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopSession}
              disabled={sessionActionLoading}
            >
              {sessionActionLoading ? 'Stopping...' : 'Stop Session'}
            </Button>
          ) : (
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayIcon />}
              onClick={handleStartSessionClick}
              disabled={sessionActionLoading}
            >
              {sessionActionLoading ? 'Starting...' : `Start ${mode === 'paper' ? 'Paper' : mode === 'live' ? 'Live' : 'Backtest'} Session`}
            </Button>
          )}
        </Box>
      </Box>

      {/* Loading Indicator - REMOVED to prevent page jumping during auto-refresh */}

      {/* Story 1A-5: StatusHero Component - PRIMARY HERO ELEMENT */}
      {/* Largest and most prominent element - combines state, P&L, and symbol */}
      {/* Visible immediately without scrolling - 2-second time-to-insight */}
      {isSessionRunning && (
        <Box sx={{ mb: 3 }}>
          <StatusHero
            state={statusHeroData.state}
            symbol={statusHeroData.symbol || selectedSymbol}
            pnl={statusHeroData.pnl}
            pnlPercent={statusHeroData.pnlPercent}
            entryPrice={statusHeroData.entryPrice}
            currentPrice={statusHeroData.currentPrice}
            sessionTime={statusHeroData.sessionTime}
            positionTime={statusHeroData.positionTime}
            signalType={statusHeroData.signalType}
            indicatorHighlights={statusHeroData.indicatorHighlights}
            side={statusHeroData.side}
          />
        </Box>
      )}

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

      {/* State Machine Overview - Full Width */}
      {isSessionRunning && sessionId && (
        <Box sx={{ mb: 3 }}>
          <StateOverviewTableIntegration
            sessionId={sessionId}
            onNavigateToDetail={(instance) => {
              setSelectedSymbol(instance.symbol);
              setViewMode('single');
            }}
          />
        </Box>
      )}

      {/* CRITICAL: Active Position Banner - HIGH VISIBILITY when position open */}
      {/* This banner appears prominently when trader has an active position */}
      {/* Trader MUST see P&L, Entry, Current price IMMEDIATELY without clicking tabs */}
      {isSessionRunning && sessionId && (
        <ActivePositionBanner
          sessionId={sessionId}
          onNavigateToPositions={() => setHistoryTab(2)} // Switch to "Active Positions" tab
          onClosePosition={(positionId) => {
            Logger.debug('DashboardPage.onClosePosition', 'Position closed from banner', { positionId });
            // Position will auto-refresh via banner's internal state
          }}
        />
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

          {/* Equity Curve - Performance Visualization */}
          <Grid item xs={12} md={6}>
            <EquityCurveChart
              data={equityCurveData}
              initialBalance={initialBalance}
              trades={tradeMarkers}
            />
          </Grid>

          {/* Drawdown Analysis Chart */}
          <Grid item xs={12} md={6}>
            <DrawdownChart
              data={equityCurveData.map(d => ({
                timestamp: d.timestamp,
                current_drawdown: d.current_drawdown || 0,
                max_drawdown: d.max_drawdown || 0,
              }))}
            />
          </Grid>

          {/* Conditional Rendering: Single View vs Grid View */}
          {viewMode === 'single' ? (
            <>
              {/* Single View: Signals + Watchlist + Chart + Indicators */}
              <Grid item xs={12} md={4}>
                {/* Story 1A-1: Recent Signals Panel - Prominent Position (AC5) */}
                <Box sx={{ mb: 2 }}>
                  <RecentSignalsPanel
                    sessionId={sessionId}
                    maxSignals={10}
                    onSignalClick={(signalId) => {
                      Logger.debug('DashboardPage.onSignalClick', 'Signal clicked', { signalId });
                      // Could open signal detail panel here
                    }}
                  />
                </Box>

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

                {/* Pump Indicators Panel (PI-01, PI-02, PI-03) - Most prominent position */}
                <Box sx={{ mb: 2 }}>
                  <PumpIndicatorsPanel
                    sessionId={sessionId}
                    symbol={selectedSymbol}
                    refreshInterval={2000}
                  />
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    {/* Story 1A-3: MVP Indicator Values Panel (AC1-5) */}
                    <IndicatorValuesPanel
                      sessionId={sessionId}
                      symbol={selectedSymbol}
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <LiveIndicatorPanel
                      sessionId={sessionId}
                      symbol={selectedSymbol}
                      refreshInterval={5000}
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <ConditionProgressIntegration
                      sessionId={sessionId}
                      symbol={selectedSymbol}
                    />
                  </Grid>
                </Grid>
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

          {/* Signal History, Transaction History, and Positions (Tabbed) */}
          <Grid item xs={12}>
            <Paper sx={{ p: 0 }}>
              <Tabs
                value={historyTab}
                onChange={(_, newValue) => setHistoryTab(newValue)}
                sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
              >
                <Tab label="📊 Signal History" />
                <Tab label="💰 Transaction History" />
                <Tab label="📍 Active Positions" />
                <Tab label="🔄 State Transitions" />
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
                <Box sx={{ display: historyTab === 2 ? 'block' : 'none', height: '500px' }}>
                  <PositionMonitor
                    session_id={sessionId || undefined}
                    className="h-full"
                  />
                </Box>
                <Box sx={{ display: historyTab === 3 ? 'block' : 'none' }}>
                  <TransitionLogIntegration
                    sessionId={sessionId}
                    symbol={viewMode === 'single' ? selectedSymbol : undefined}
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

      {/* Session Configuration Dialog */}
      <SessionConfigDialog
        open={configDialogOpen}
        mode={mode}
        onClose={() => setConfigDialogOpen(false)}
        onSubmit={handleSessionConfigSubmit}
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
