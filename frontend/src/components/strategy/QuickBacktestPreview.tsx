/**
 * SB-02: Quick Backtest Preview Component
 *
 * Shows estimated signal counts and performance metrics for a strategy
 * based on historical simulation data.
 *
 * Features:
 * - Signal count estimates: S1, Z1, O1, ZE1, E1
 * - Win rate and P&L projections
 * - Entry/Exit accuracy metrics
 * - Time period selection (24h, 7d, 30d)
 * - Symbol selection for simulation
 * - Visual progress bars and charts
 * - Mock data fallback for development
 *
 * Integration:
 * - Strategy Builder page (below 5-section form)
 * - Requires strategy configuration to calculate estimates
 *
 * Location: frontend/src/components/strategy/QuickBacktestPreview.tsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  LinearProgress,
  Chip,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  IconButton,
  Collapse,
  Divider,
  Alert,
  Stack,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  Info as InfoIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { Strategy5Section } from '@/types/strategy';

// ============================================================================
// TYPES
// ============================================================================

interface BacktestResult {
  // Signal counts
  signalCounts: {
    S1: number;  // Pump detected
    Z1: number;  // Entry executed
    O1: number;  // Timeout/cancel
    ZE1: number; // Planned exit
    E1: number;  // Emergency exit
  };

  // Performance metrics
  performance: {
    winRate: number;        // 0-100
    avgPnLPercent: number;  // Average P&L per trade
    totalPnLPercent: number; // Total cumulative P&L
    maxDrawdownPercent: number;
    sharpeRatio: number;
  };

  // Accuracy metrics
  accuracy: {
    entryAccuracy: number;  // Z1 / (Z1 + O1) - how often S1 leads to entry
    exitAccuracy: number;   // ZE1 / (ZE1 + E1) - how often exits are planned
  };

  // Timing stats
  timing: {
    avgHoldTimeMinutes: number;
    avgTimeBetweenSignalsMinutes: number;
    signalsPerDay: number;
  };

  // Meta
  symbol: string;
  period: string;
  timestamp: string;
}

interface QuickBacktestPreviewProps {
  strategy: Strategy5Section;
  onRunFullBacktest?: () => void;
}

// ============================================================================
// MOCK DATA GENERATOR
// ============================================================================

function generateMockBacktestResult(
  strategy: Strategy5Section,
  symbol: string,
  period: string
): BacktestResult {
  // Base signal frequency based on strategy conditions
  const s1ConditionCount = strategy.s1_signal?.conditions?.length || 0;
  const z1ConditionCount = strategy.z1_entry?.conditions?.length || 0;
  const o1Timeout = strategy.o1_cancel?.timeoutSeconds || 30;

  // More conditions = fewer signals (more selective)
  const selectivityFactor = Math.max(0.3, 1 - (s1ConditionCount + z1ConditionCount) * 0.1);

  // Period multiplier
  const periodMultiplier = period === '24h' ? 1 : period === '7d' ? 7 : 30;

  // Base S1 signals per day (random between 5-15)
  const baseS1PerDay = 5 + Math.random() * 10;
  const s1Count = Math.round(baseS1PerDay * periodMultiplier * selectivityFactor);

  // Z1 = S1 * entry rate (60-80%)
  const entryRate = 0.6 + Math.random() * 0.2;
  const z1Count = Math.round(s1Count * entryRate);

  // O1 = S1 - Z1 (timeouts)
  const o1Count = s1Count - z1Count;

  // Exit split: ZE1 (planned) vs E1 (emergency)
  // Strategy with SL/TP configured = more planned exits
  const hasStopLoss = strategy.z1_entry?.stopLoss?.enabled;
  const hasTakeProfit = strategy.z1_entry?.takeProfit?.enabled;
  const plannedExitRate = hasStopLoss && hasTakeProfit ? 0.75 + Math.random() * 0.15 : 0.5 + Math.random() * 0.2;

  const ze1Count = Math.round(z1Count * plannedExitRate);
  const e1Count = z1Count - ze1Count;

  // Performance based on direction and configuration
  const isShort = strategy.direction === 'SHORT';
  const baseWinRate = isShort ? 55 + Math.random() * 15 : 50 + Math.random() * 15;
  const avgPnL = (baseWinRate - 50) * 0.1 + (Math.random() - 0.5) * 1;
  const totalPnL = avgPnL * z1Count;

  return {
    signalCounts: {
      S1: s1Count,
      Z1: z1Count,
      O1: o1Count,
      ZE1: ze1Count,
      E1: e1Count,
    },
    performance: {
      winRate: baseWinRate,
      avgPnLPercent: avgPnL,
      totalPnLPercent: totalPnL,
      maxDrawdownPercent: 5 + Math.random() * 10,
      sharpeRatio: 0.5 + Math.random() * 1.5,
    },
    accuracy: {
      entryAccuracy: (z1Count / s1Count) * 100,
      exitAccuracy: z1Count > 0 ? (ze1Count / z1Count) * 100 : 0,
    },
    timing: {
      avgHoldTimeMinutes: 15 + Math.random() * 45,
      avgTimeBetweenSignalsMinutes: (24 * 60 * periodMultiplier) / s1Count,
      signalsPerDay: s1Count / periodMultiplier,
    },
    symbol,
    period,
    timestamp: new Date().toISOString(),
  };
}

// ============================================================================
// COMPONENT
// ============================================================================

export const QuickBacktestPreview: React.FC<QuickBacktestPreviewProps> = ({
  strategy,
  onRunFullBacktest,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [symbol, setSymbol] = useState('BTC_USDT');
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('7d');
  const [error, setError] = useState<string | null>(null);

  // Available symbols for simulation
  const symbols = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'DOGE_USDT', 'PEPE_USDT'];

  const runQuickBacktest = useCallback(async () => {
    if (!strategy.name) {
      setError('Please name your strategy before running backtest');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Try to fetch from API first
      const response = await fetch(
        `/api/strategies/quick-backtest?symbol=${symbol}&period=${period}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategy),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        // Fallback to mock data
        await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate loading
        const mockResult = generateMockBacktestResult(strategy, symbol, period);
        setResult(mockResult);
      }
    } catch {
      // Fallback to mock data on error
      await new Promise(resolve => setTimeout(resolve, 1500));
      const mockResult = generateMockBacktestResult(strategy, symbol, period);
      setResult(mockResult);
    } finally {
      setLoading(false);
    }
  }, [strategy, symbol, period]);

  // Auto-run on strategy change (debounced)
  useEffect(() => {
    if (strategy.name && strategy.s1_signal?.conditions?.length > 0) {
      const timer = setTimeout(() => {
        runQuickBacktest();
      }, 500);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy.name, strategy.s1_signal?.conditions?.length]);

  const getPerformanceColor = (value: number, type: 'winRate' | 'pnl' | 'accuracy') => {
    if (type === 'winRate') {
      if (value >= 60) return 'success';
      if (value >= 50) return 'warning';
      return 'error';
    }
    if (type === 'pnl') {
      if (value > 0) return 'success';
      if (value === 0) return 'warning';
      return 'error';
    }
    if (type === 'accuracy') {
      if (value >= 70) return 'success';
      if (value >= 50) return 'warning';
      return 'error';
    }
    return 'default';
  };

  const formatNumber = (num: number, decimals: number = 1) => {
    return num.toFixed(decimals);
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TimelineIcon color="primary" />
          <Typography variant="h6">Quick Backtest Preview</Typography>
          <Tooltip title="SB-02: Shows estimated signal counts and performance based on historical data simulation">
            <IconButton size="small">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded}>
        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Symbol</InputLabel>
            <Select
              value={symbol}
              label="Symbol"
              onChange={(e) => setSymbol(e.target.value)}
            >
              {symbols.map(s => (
                <MenuItem key={s} value={s}>{s}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={period}
              label="Period"
              onChange={(e) => setPeriod(e.target.value as '24h' | '7d' | '30d')}
            >
              <MenuItem value="24h">Last 24h</MenuItem>
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
            </Select>
          </FormControl>

          <Button
            variant="contained"
            size="small"
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <PlayIcon />}
            onClick={runQuickBacktest}
            disabled={loading || !strategy.name}
          >
            {loading ? 'Running...' : 'Run Quick Test'}
          </Button>

          {result && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={runQuickBacktest}
              disabled={loading}
            >
              Refresh
            </Button>
          )}
        </Box>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading && (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <CircularProgress size={40} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Simulating {period} of trading on {symbol}...
            </Typography>
          </Box>
        )}

        {/* Results */}
        {result && !loading && (
          <Box>
            {/* Signal Counts */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Signal Counts ({result.period})
            </Typography>

            <Grid container spacing={1} sx={{ mb: 3 }}>
              {/* S1 */}
              <Grid item xs={6} sm={2.4}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    textAlign: 'center',
                    bgcolor: 'warning.lighter',
                    borderColor: 'warning.light',
                  }}
                >
                  <Typography variant="h4" color="warning.dark" fontWeight="bold">
                    {result.signalCounts.S1}
                  </Typography>
                  <Typography variant="caption" color="warning.dark">
                    S1 Signals
                  </Typography>
                  <Typography variant="caption" display="block" color="text.secondary">
                    Pump detected
                  </Typography>
                </Paper>
              </Grid>

              {/* Z1 */}
              <Grid item xs={6} sm={2.4}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    textAlign: 'center',
                    bgcolor: 'success.lighter',
                    borderColor: 'success.light',
                  }}
                >
                  <Typography variant="h4" color="success.dark" fontWeight="bold">
                    {result.signalCounts.Z1}
                  </Typography>
                  <Typography variant="caption" color="success.dark">
                    Z1 Entries
                  </Typography>
                  <Typography variant="caption" display="block" color="text.secondary">
                    Positions opened
                  </Typography>
                </Paper>
              </Grid>

              {/* O1 */}
              <Grid item xs={6} sm={2.4}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    textAlign: 'center',
                    bgcolor: 'grey.100',
                    borderColor: 'grey.300',
                  }}
                >
                  <Typography variant="h4" color="text.secondary" fontWeight="bold">
                    {result.signalCounts.O1}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    O1 Timeouts
                  </Typography>
                  <Typography variant="caption" display="block" color="text.secondary">
                    Entry cancelled
                  </Typography>
                </Paper>
              </Grid>

              {/* ZE1 */}
              <Grid item xs={6} sm={2.4}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    textAlign: 'center',
                    bgcolor: 'info.lighter',
                    borderColor: 'info.light',
                  }}
                >
                  <Typography variant="h4" color="info.dark" fontWeight="bold">
                    {result.signalCounts.ZE1}
                  </Typography>
                  <Typography variant="caption" color="info.dark">
                    ZE1 Exits
                  </Typography>
                  <Typography variant="caption" display="block" color="text.secondary">
                    Planned close
                  </Typography>
                </Paper>
              </Grid>

              {/* E1 */}
              <Grid item xs={6} sm={2.4}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    textAlign: 'center',
                    bgcolor: 'error.lighter',
                    borderColor: 'error.light',
                  }}
                >
                  <Typography variant="h4" color="error.dark" fontWeight="bold">
                    {result.signalCounts.E1}
                  </Typography>
                  <Typography variant="caption" color="error.dark">
                    E1 Emergency
                  </Typography>
                  <Typography variant="caption" display="block" color="text.secondary">
                    Stop loss hit
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            {/* Performance Metrics */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Performance Estimates
            </Typography>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              {/* Win Rate */}
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Win Rate</Typography>
                    <Chip
                      size="small"
                      label={`${formatNumber(result.performance.winRate)}%`}
                      color={getPerformanceColor(result.performance.winRate, 'winRate') as any}
                    />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={result.performance.winRate}
                    color={getPerformanceColor(result.performance.winRate, 'winRate') as any}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>
              </Grid>

              {/* Entry Accuracy */}
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Entry Accuracy</Typography>
                    <Chip
                      size="small"
                      label={`${formatNumber(result.accuracy.entryAccuracy)}%`}
                      color={getPerformanceColor(result.accuracy.entryAccuracy, 'accuracy') as any}
                    />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={result.accuracy.entryAccuracy}
                    color={getPerformanceColor(result.accuracy.entryAccuracy, 'accuracy') as any}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Z1 / S1 = How often pump signals lead to entry
                  </Typography>
                </Box>
              </Grid>

              {/* Exit Accuracy */}
              <Grid item xs={12} sm={4}>
                <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Exit Accuracy</Typography>
                    <Chip
                      size="small"
                      label={`${formatNumber(result.accuracy.exitAccuracy)}%`}
                      color={getPerformanceColor(result.accuracy.exitAccuracy, 'accuracy') as any}
                    />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={result.accuracy.exitAccuracy}
                    color={getPerformanceColor(result.accuracy.exitAccuracy, 'accuracy') as any}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    ZE1 / (ZE1+E1) = How often exits are planned
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {/* P&L Summary */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} sm={3}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  {result.performance.avgPnLPercent >= 0 ? (
                    <TrendingUpIcon color="success" />
                  ) : (
                    <TrendingDownIcon color="error" />
                  )}
                  <Box>
                    <Typography variant="caption" color="text.secondary">Avg P&L/Trade</Typography>
                    <Typography
                      variant="h6"
                      color={result.performance.avgPnLPercent >= 0 ? 'success.main' : 'error.main'}
                    >
                      {result.performance.avgPnLPercent >= 0 ? '+' : ''}{formatNumber(result.performance.avgPnLPercent)}%
                    </Typography>
                  </Box>
                </Stack>
              </Grid>

              <Grid item xs={6} sm={3}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  {result.performance.totalPnLPercent >= 0 ? (
                    <TrendingUpIcon color="success" />
                  ) : (
                    <TrendingDownIcon color="error" />
                  )}
                  <Box>
                    <Typography variant="caption" color="text.secondary">Total P&L</Typography>
                    <Typography
                      variant="h6"
                      color={result.performance.totalPnLPercent >= 0 ? 'success.main' : 'error.main'}
                    >
                      {result.performance.totalPnLPercent >= 0 ? '+' : ''}{formatNumber(result.performance.totalPnLPercent)}%
                    </Typography>
                  </Box>
                </Stack>
              </Grid>

              <Grid item xs={6} sm={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Max Drawdown</Typography>
                  <Typography variant="h6" color="error.main">
                    -{formatNumber(result.performance.maxDrawdownPercent)}%
                  </Typography>
                </Box>
              </Grid>

              <Grid item xs={6} sm={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Sharpe Ratio</Typography>
                  <Typography variant="h6">
                    {formatNumber(result.performance.sharpeRatio, 2)}
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {/* Timing Stats */}
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
              <Chip
                icon={<TimelineIcon />}
                label={`${formatNumber(result.timing.signalsPerDay, 1)} signals/day`}
                variant="outlined"
                size="small"
              />
              <Chip
                label={`Avg hold: ${formatNumber(result.timing.avgHoldTimeMinutes, 0)} min`}
                variant="outlined"
                size="small"
              />
              <Chip
                label={`${formatNumber(result.timing.avgTimeBetweenSignalsMinutes, 0)} min between signals`}
                variant="outlined"
                size="small"
              />
            </Box>

            {/* Interpretation */}
            <Alert
              severity={
                result.performance.winRate >= 55 && result.accuracy.entryAccuracy >= 60
                  ? 'success'
                  : result.performance.winRate >= 50
                  ? 'info'
                  : 'warning'
              }
              icon={
                result.performance.winRate >= 55 ? (
                  <CheckIcon />
                ) : result.performance.winRate >= 50 ? (
                  <InfoIcon />
                ) : (
                  <WarningIcon />
                )
              }
              sx={{ mb: 2 }}
            >
              <Typography variant="body2">
                {result.performance.winRate >= 55 && result.accuracy.entryAccuracy >= 60 ? (
                  <>
                    <strong>Good potential!</strong> Strategy shows {formatNumber(result.performance.winRate)}% win rate
                    with {formatNumber(result.accuracy.entryAccuracy)}% entry accuracy.
                    Consider running a full backtest for detailed analysis.
                  </>
                ) : result.performance.winRate >= 50 ? (
                  <>
                    <strong>Moderate results.</strong> {formatNumber(result.performance.winRate)}% win rate is near breakeven.
                    Consider adjusting S1/Z1 conditions for better selectivity.
                  </>
                ) : (
                  <>
                    <strong>Below breakeven.</strong> {formatNumber(result.performance.winRate)}% win rate suggests
                    strategy needs refinement. Review entry conditions and timeouts.
                  </>
                )}
              </Typography>
            </Alert>

            {/* Full Backtest Button */}
            {onRunFullBacktest && (
              <Box sx={{ textAlign: 'center' }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayIcon />}
                  onClick={onRunFullBacktest}
                >
                  Run Full Backtest
                </Button>
              </Box>
            )}

            {/* Timestamp */}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'right', mt: 2 }}>
              Simulated at {new Date(result.timestamp).toLocaleTimeString()}
              {' | '}
              <em>Mock data - backend integration pending</em>
            </Typography>
          </Box>
        )}

        {/* Empty State */}
        {!result && !loading && !error && (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <TimelineIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography variant="body1" color="text.secondary">
              Configure your strategy and click "Run Quick Test" to see estimated performance
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Requires at least one S1 condition and a strategy name
            </Typography>
          </Box>
        )}
      </Collapse>
    </Paper>
  );
};

export default QuickBacktestPreview;
