'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Download as DownloadIcon,
  BarChart as BarChartIcon,
  Timeline as TimelineIcon,
  PieChart as PieChartIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import {
  getSessionStatusColor,
  getSessionStatusIcon,
  getPerformanceStatusColor,
  type SessionStatusType
} from '@/utils/statusUtils';

interface BacktestSession {
  session_id: string;
  status: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  strategy_name: string;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  created_at: string;
}

interface BacktestResult {
  session_id: string;
  summary: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    total_pnl: number;
    max_drawdown: number;
    profit_factor: number;
    avg_trade_duration: number;
  };
  trades: any[];
  performance: any;
}

const commonSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'];

interface DataSource {
  session_id: string;
  symbols: string[];
  created_at: string;
  data_types: string[];
}

export default function BacktestingPage() {
  const [sessions, setSessions] = useState<BacktestSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<BacktestResult | null>(null);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [availableStrategies, setAvailableStrategies] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Backend health check (consistent with Dashboard)
  const checkBackendConnection = useCallback(async () => {
    try {
      await apiService.healthCheck();
    } catch (error) {
      // Silently handle health check failures
      console.warn('Health check failed:', error);
    }
  }, []);

  useVisibilityAwareInterval(checkBackendConnection, 15000);

  // Form state for new backtest
  const [backtestForm, setBacktestForm] = useState({
    symbols: ['BTC_USDT'],
    data_sources: [] as string[], // Selected session IDs
    selected_strategies: [] as string[], // Selected strategy blueprint IDs
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end_date: new Date(),
    config: {
      budget: {
        global_cap: 10000,
        allocations: {}
      },
      timeframe: '1h'
    }
  });

  useEffect(() => {
    loadBacktestSessions();
    loadDataSources();
    loadAvailableStrategies();
  }, []);

  const loadAvailableStrategies = async () => {
    try {
      // Load 5-section strategies from backend API
      const strategies = await apiService.get4SectionStrategies();
      setAvailableStrategies(strategies);
      console.log('Loaded strategies:', strategies);
    } catch (error) {
      console.error('Failed to load available strategies:', error);
      setAvailableStrategies([]);
      setSnackbar({
        open: true,
        message: 'Failed to load available strategies',
        severity: 'error'
      });
    }
  };

  const loadDataSources = async () => {
    try {
      // Load available data sessions from the data directory
      // In a real implementation, this would come from an API endpoint
      // For now, we'll simulate with the existing data structure
      const mockDataSources: DataSource[] = [
        {
          session_id: 'session_20250909_130028_8eb70dba',
          symbols: ['ALU_USDT', 'ADA_USDT', 'BTC_USDT', 'ETH_USDT', 'LTC_USDT'],
          created_at: '2025-09-09T13:00:28Z',
          data_types: ['price', 'orderbook']
        },
        {
          session_id: 'session_20250909_125616_c0b6a833',
          symbols: ['BTC_USDT', 'ETH_USDT'],
          created_at: '2025-09-09T12:56:16Z',
          data_types: ['price', 'orderbook', 'trades']
        }
      ];
      setDataSources(mockDataSources);
    } catch (error) {
      console.error('Failed to load data sources:', error);
      setDataSources([]);
    }
  };

  const loadBacktestSessions = async () => {
    setLoading(true);
    try {
      // Get current session status from backend
      const sessionStatus = await apiService.getExecutionStatus();

      if (sessionStatus && sessionStatus.session_id) {
        // Transform backend session data to frontend format
        const session: BacktestSession = {
          session_id: sessionStatus.session_id,
          status: sessionStatus.status || 'unknown',
          symbols: sessionStatus.symbols || [],
          start_date: sessionStatus.start_time ? new Date(sessionStatus.start_time).toISOString().split('T')[0] : '',
          end_date: new Date().toISOString().split('T')[0], // Current date as end
          strategy_name: 'backtest_strategy', // Default name
          total_trades: sessionStatus.total_trades || 0,
          win_rate: sessionStatus.win_rate || 0,
          total_pnl: sessionStatus.total_pnl || 0,
          max_drawdown: sessionStatus.max_drawdown || 0,
          created_at: sessionStatus.start_time || new Date().toISOString()
        };

        setSessions([session]);
      } else {
        // No active sessions
        setSessions([]);
      }
    } catch (error) {
      console.error('Failed to load backtest sessions:', error);
      setSessions([]);
      setSnackbar({
        open: true,
        message: 'Failed to load backtest sessions',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStartBacktest = () => {
    setDialogOpen(true);
  };

  const handleViewResults = async (session: BacktestSession) => {
    try {
      // Fetch detailed results from backend
      const results = await apiService.getSessionStatus(session.session_id);

      if (results) {
        // Transform backend results to frontend format
        const result: BacktestResult = {
          session_id: session.session_id,
          summary: {
            total_trades: results.total_trades || 0,
            winning_trades: Math.floor((results.total_trades || 0) * (results.win_rate || 0) / 100),
            losing_trades: (results.total_trades || 0) - Math.floor((results.total_trades || 0) * (results.win_rate || 0) / 100),
            win_rate: results.win_rate || 0,
            total_pnl: results.total_pnl || 0,
            max_drawdown: results.max_drawdown || 0,
            profit_factor: (results.total_pnl || 0) > 0 ? 1.5 : 0.8,
            avg_trade_duration: 45 // Default value
          },
          trades: results.trades || [],
          performance: results.metrics || {}
        };

        setSelectedSession(result);
      } else {
        setSnackbar({
          open: true,
          message: 'No results available for this session',
          severity: 'warning'
        });
      }
    } catch (error) {
      console.error('Failed to load backtest results:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load backtest results',
        severity: 'error'
      });
    }
  };

  const handleCreateBacktest = async () => {
    setLoading(true);
    try {
      // Validate strategy selection
      if (backtestForm.selected_strategies.length === 0) {
        setSnackbar({
          open: true,
          message: 'Please select at least one strategy',
          severity: 'error'
        });
        return;
      }

      // Get selected strategy details
      const strategyId = backtestForm.selected_strategies[0];
      const selectedStrategy = availableStrategies.find(s => s.id === strategyId);

      if (!selectedStrategy) {
        setSnackbar({
          open: true,
          message: 'Selected strategy not found',
          severity: 'error'
        });
        return;
      }

      // Start backtest session with selected strategy
      const response = await apiService.startBacktest(backtestForm.symbols, {
        strategy_config: selectedStrategy,
        acceleration_factor: 10,
        budget: backtestForm.config.budget
      });

      if (response.status === 'success' || response.data) {
        setSnackbar({
          open: true,
          message: 'Backtest started successfully',
          severity: 'success'
        });
        setDialogOpen(false);
        // Refresh sessions list
        await loadBacktestSessions();
      } else {
        throw new Error(response.error_message || 'Failed to start backtest');
      }
    } catch (error: any) {
      console.error('Failed to start backtest:', error);
      setSnackbar({
        open: true,
        message: error.message || 'Failed to start backtest',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadResults = (sessionId: string) => {
    // In a real implementation, this would trigger a download
    setSnackbar({
      open: true,
      message: `Downloading results for session ${sessionId}`,
      severity: 'info'
    });
  };


  return (
    <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Backtesting
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadBacktestSessions}
              disabled={loading}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={handleStartBacktest}
            >
              New Backtest
            </Button>
          </Box>
        </Box>

        {/* System Status */}
        <SystemStatusIndicator showDetails={false} />

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <AssessmentIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Total Backtests</Typography>
                </Box>
                <Typography variant="h4" color="primary">
                  {sessions.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6">Completed</Typography>
                </Box>
                <Typography variant="h4" color="success">
                  {sessions.filter(s => s.status === 'completed').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <PlayIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="h6">Running</Typography>
                </Box>
                <Typography variant="h4" color="info">
                  {sessions.filter(s => s.status === 'running').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <TrendingUpIcon color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Avg Win Rate</Typography>
                </Box>
                <Typography variant="h4" color="secondary">
                  {sessions.length > 0
                    ? (sessions.reduce((sum, s) => sum + s.win_rate, 0) / sessions.length).toFixed(1)
                    : '0.0'}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Backtest Sessions Table */}
        <Paper sx={{ mb: 3, overflow: 'hidden' }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">Backtest Sessions</Typography>
          </Box>
          <TableContainer sx={{ maxWidth: '100%', overflow: 'auto' }}>
            <Table sx={{ minWidth: 800 }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ minWidth: 120 }}>Session ID</TableCell>
                  <TableCell sx={{ minWidth: 80 }}>Status</TableCell>
                  <TableCell sx={{ minWidth: 120 }}>Symbols</TableCell>
                  <TableCell sx={{ minWidth: 120 }}>Date Range</TableCell>
                  <TableCell sx={{ minWidth: 100 }}>Strategy</TableCell>
                  <TableCell align="right" sx={{ minWidth: 80 }}>Trades</TableCell>
                  <TableCell align="right" sx={{ minWidth: 80 }}>Win Rate</TableCell>
                  <TableCell align="right" sx={{ minWidth: 100 }}>P&L</TableCell>
                  <TableCell align="right" sx={{ minWidth: 80 }}>Max DD</TableCell>
                  <TableCell sx={{ minWidth: 100 }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.session_id} hover>
                    <TableCell sx={{ maxWidth: 120 }}>
                      <Typography variant="body2" fontWeight="bold" sx={{ wordBreak: 'break-all' }}>
                        {session.session_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(session.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={session.status}
                        color={getSessionStatusColor(session.status as SessionStatusType)}
                        size="small"
                        icon={getSessionStatusIcon(session.status as SessionStatusType)}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', maxWidth: 120 }}>
                        {session.symbols.map(symbol => (
                          <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Typography variant="body2">
                        {session.start_date} to {session.end_date}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={session.strategy_name} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">{session.total_trades}</TableCell>
                    <TableCell align="right">{session.win_rate.toFixed(1)}%</TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        color={getPerformanceStatusColor(session.total_pnl) + '.main'}
                        fontWeight="bold"
                      >
                        ${session.total_pnl.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" color="error.main">
                        {session.max_drawdown.toFixed(1)}%
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="View Results">
                          <IconButton
                            size="small"
                            onClick={() => handleViewResults(session)}
                            disabled={session.status !== 'completed'}
                          >
                            <AssessmentIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Download Results">
                          <IconButton
                            size="small"
                            onClick={() => handleDownloadResults(session.session_id)}
                            disabled={session.status !== 'completed'}
                          >
                            <DownloadIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
                {sessions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={10} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No backtest sessions found. Start your first backtest to see results here.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        {/* Analytics Dashboard */}
        {selectedSession && (
          <Paper sx={{ mb: 3, p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <BarChartIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h5" component="h2">
                Analytics Dashboard: {selectedSession.session_id}
              </Typography>
            </Box>

            {/* Performance Overview Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} md={3}>
                <Card sx={{ bgcolor: selectedSession.summary.total_pnl >= 0 ? 'success.light' : 'error.light' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Total Return</Typography>
                        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                          {selectedSession.summary.total_pnl >= 0 ? '+' : ''}${selectedSession.summary.total_pnl.toFixed(2)}
                        </Typography>
                      </Box>
                      <TrendingUpIcon sx={{ fontSize: 40, opacity: 0.7 }} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Win Rate</Typography>
                        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                          {selectedSession.summary.win_rate.toFixed(1)}%
                        </Typography>
                      </Box>
                      <PieChartIcon sx={{ fontSize: 40, opacity: 0.7, color: 'primary.main' }} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Sharpe Ratio</Typography>
                        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                          {selectedSession.performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <TimelineIcon sx={{ fontSize: 40, opacity: 0.7, color: 'secondary.main' }} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card sx={{ bgcolor: 'warning.light' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Max Drawdown</Typography>
                        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                          {selectedSession.summary.max_drawdown.toFixed(1)}%
                        </Typography>
                      </Box>
                      <BarChartIcon sx={{ fontSize: 40, opacity: 0.7, color: 'warning.main' }} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Trade Analysis */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <AssessmentIcon sx={{ mr: 1 }} />
                    Trade Analysis
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Total Trades</Typography>
                      <Chip label={selectedSession.summary.total_trades} color="primary" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Winning Trades</Typography>
                      <Chip label={selectedSession.summary.winning_trades} color="success" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Losing Trades</Typography>
                      <Chip label={selectedSession.summary.losing_trades} color="error" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Profit Factor</Typography>
                      <Chip label={selectedSession.summary.profit_factor.toFixed(2)} color="info" />
                    </Box>
                  </Box>
                </Paper>
              </Grid>

              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <TimelineIcon sx={{ mr: 1 }} />
                    Risk Metrics
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Sharpe Ratio</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {selectedSession.performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Sortino Ratio</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {selectedSession.performance?.sortino_ratio?.toFixed(2) || 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Calmar Ratio</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {selectedSession.performance?.calmar_ratio?.toFixed(2) || 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body1">Value at Risk (95%)</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {selectedSession.performance?.value_at_risk ? `${(selectedSession.performance.value_at_risk * 100).toFixed(1)}%` : 'N/A'}
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Detailed Results Accordion */}
        {selectedSession && (
          <Accordion expanded={false} sx={{ maxWidth: '100%', overflow: 'hidden' }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6" sx={{ wordBreak: 'break-word' }}>
                Detailed Backtest Results: {selectedSession.session_id}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ maxWidth: '100%', overflow: 'auto' }}>
              <Grid container spacing={2} sx={{ width: '100%' }}>
                <Grid item xs={12} sm={6}>
                  <Paper sx={{ p: 2, width: '100%' }}>
                    <Typography variant="h6" gutterBottom>
                      Performance Summary
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Total Trades</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.summary.total_trades}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Winning Trades</Typography>
                        <Typography variant="body2" fontWeight="bold" color="success.main" sx={{ ml: 1 }}>
                          {selectedSession.summary.winning_trades}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Losing Trades</Typography>
                        <Typography variant="body2" fontWeight="bold" color="error.main" sx={{ ml: 1 }}>
                          {selectedSession.summary.losing_trades}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Win Rate</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.summary.win_rate.toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Total P&L</Typography>
                        <Typography
                          variant="body2"
                          fontWeight="bold"
                          color={getPerformanceStatusColor(selectedSession.summary.total_pnl) + '.main'}
                          sx={{ ml: 1 }}
                        >
                          ${selectedSession.summary.total_pnl.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Max Drawdown</Typography>
                        <Typography variant="body2" fontWeight="bold" color="error.main" sx={{ ml: 1 }}>
                          {selectedSession.summary.max_drawdown.toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Profit Factor</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.summary.profit_factor.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Sharpe Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Sortino Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.sortino_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Calmar Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.calmar_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <Paper sx={{ p: 2, width: '100%' }}>
                    <Typography variant="h6" gutterBottom>
                      Risk Metrics
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Sharpe Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Sortino Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.sortino_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Calmar Ratio</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.calmar_ratio?.toFixed(2) || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Value at Risk (95%)</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.value_at_risk ? `${(selectedSession.performance.value_at_risk * 100).toFixed(1)}%` : 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                        <Typography variant="body2" sx={{ flexShrink: 0 }}>Max Drawdown Duration</Typography>
                        <Typography variant="body2" fontWeight="bold" sx={{ ml: 1 }}>
                          {selectedSession.performance?.max_drawdown_duration || 'N/A'}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        )}

        {/* New Backtest Dialog */}
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>Start New Backtest</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Symbols</InputLabel>
                <Select
                  multiple
                  value={backtestForm.symbols}
                  label="Symbols"
                  onChange={(e) => setBacktestForm(prev => ({
                    ...prev,
                    symbols: typeof e.target.value === 'string' ? [e.target.value] : e.target.value
                  }))}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {commonSymbols.map(symbol => (
                    <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Strategy to Test</InputLabel>
                <Select
                  value={backtestForm.selected_strategies[0] || ''}
                  label="Strategy to Test"
                  onChange={(e) => setBacktestForm(prev => ({
                    ...prev,
                    selected_strategies: e.target.value ? [e.target.value] : []
                  }))}
                  renderValue={(selected) => {
                    const strategy = availableStrategies.find(s => s.id === selected);
                    return strategy ? strategy.strategy_name : 'Select a strategy';
                  }}
                >
                  {availableStrategies.length === 0 ? (
                    <MenuItem disabled>
                      <Typography variant="body2" color="text.secondary">
                        No strategies available. Create a strategy first.
                      </Typography>
                    </MenuItem>
                  ) : (
                    availableStrategies.map(strategy => (
                      <MenuItem key={strategy.id} value={strategy.id}>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {strategy.strategy_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {strategy.direction || 'LONG'} | Created: {strategy.created_at ? new Date(strategy.created_at).toLocaleDateString() : 'Unknown'}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))
                  )}
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Select a 5-section strategy to test against historical data.
                </Typography>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Data Sources (Historical Sessions)</InputLabel>
                <Select
                  multiple
                  value={backtestForm.data_sources}
                  label="Data Sources (Historical Sessions)"
                  onChange={(e) => setBacktestForm(prev => ({
                    ...prev,
                    data_sources: typeof e.target.value === 'string' ? [e.target.value] : e.target.value
                  }))}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => {
                        const source = dataSources.find(ds => ds.session_id === value);
                        return (
                          <Chip
                            key={value}
                            label={source ? `${source.session_id.split('_')[1]} (${source.symbols.length} symbols)` : value}
                            size="small"
                            color="secondary"
                          />
                        );
                      })}
                    </Box>
                  )}
                >
                  {dataSources.map(source => (
                    <MenuItem key={source.session_id} value={source.session_id}>
                      <Box>
                        <Typography variant="body2" fontWeight="bold">
                          {source.session_id.split('_')[1]} - {new Date(source.created_at).toLocaleDateString()}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Symbols: {source.symbols.join(', ')} | Types: {source.data_types.join(', ')}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Select historical data sessions to use for backtesting. Leave empty to use all available data.
                </Typography>
              </FormControl>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Start Date"
                    type="date"
                    value={backtestForm.start_date.toISOString().split('T')[0]}
                    onChange={(e) => setBacktestForm(prev => ({
                      ...prev,
                      start_date: new Date(e.target.value)
                    }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="End Date"
                    type="date"
                    value={backtestForm.end_date.toISOString().split('T')[0]}
                    onChange={(e) => setBacktestForm(prev => ({
                      ...prev,
                      end_date: new Date(e.target.value)
                    }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>

              <TextField
                fullWidth
                label="Global Budget Cap (USD)"
                type="number"
                value={backtestForm.config.budget.global_cap}
                onChange={(e) => setBacktestForm(prev => ({
                  ...prev,
                  config: {
                    ...prev.config,
                    budget: {
                      ...prev.config.budget,
                      global_cap: parseFloat(e.target.value) || 10000
                    }
                  }
                }))}
                helperText="Maximum total budget for backtest"
              />

              <FormControl fullWidth>
                <InputLabel>Timeframe</InputLabel>
                <Select
                  value={backtestForm.config.timeframe}
                  label="Timeframe"
                  onChange={(e) => setBacktestForm(prev => ({
                    ...prev,
                    config: {
                      ...prev.config,
                      timeframe: e.target.value
                    }
                  }))}
                >
                  <MenuItem value="1m">1 Minute</MenuItem>
                  <MenuItem value="5m">5 Minutes</MenuItem>
                  <MenuItem value="15m">15 Minutes</MenuItem>
                  <MenuItem value="1h">1 Hour</MenuItem>
                  <MenuItem value="4h">4 Hours</MenuItem>
                  <MenuItem value="1d">1 Day</MenuItem>
                </Select>
              </FormControl>

              <Alert severity="info">
                <Typography variant="body2">
                  <strong>Backtesting:</strong> Historical data simulation to test strategies
                  <br />
                  Results will be available after completion for detailed analysis
                </Typography>
              </Alert>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateBacktest} variant="contained" color="success">
              Start Backtest
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={4000}
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert
            onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
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
