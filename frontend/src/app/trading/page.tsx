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
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { SystemStatusIndicator, StatusChip } from '@/components/common/SystemStatusIndicator';
import { getSessionStatusColor, getSessionStatusIcon } from '@/utils/statusUtils';

interface Session {
  session_id: string;
  session_type: string;
  status: string;
  symbols: string[];
  start_time?: string;
  end_time?: string;
  total_signals?: number;
  total_trades?: number;
  win_rate?: number;
  total_pnl?: number;
  active_strategies?: string[];
}

interface Strategy {
  strategy_name: string;
  enabled: boolean;
  current_state: string;
  symbol?: string;
}

const sessionTypes = ['live', 'paper'];
const commonSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'];

export default function TradingPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Backend health check - only as backup (WebSocket provides real-time status)
  const checkBackendConnection = useCallback(async () => {
    try {
      await apiService.healthCheck();
    } catch (error) {
      // Silently handle health check failures
      console.warn('Health check failed:', error);
    }
  }, []);

  // Reduced polling frequency - only backup every 5 minutes when WebSocket unavailable
  useVisibilityAwareInterval(checkBackendConnection, 300000); // 5 minutes

  // Form state for new session
  const [sessionForm, setSessionForm] = useState({
    session_type: 'paper',
    symbols: ['BTC_USDT'],
    strategy_config: {
      pump_dump_detector: {
        scan_interval: 60,
        min_pump_magnitude: 5.0,
        min_volume_surge: 2.0
      }
    },
    config: {
      budget: {
        global_cap: 1000,
        allocations: {}
      }
    }
  });

  // ✅ FIX: Define data loading functions BEFORE using them in useEffect/useVisibilityAwareInterval
  // This prevents "Cannot access before initialization" TDZ error
  const loadSessions = useCallback(async (): Promise<Session[]> => {
    try {
      // Get current session status
      const statusResponse = await apiService.getExecutionStatus();
      if (statusResponse && statusResponse.session_id) {
        return [{
          session_id: statusResponse.session_id,
          session_type: statusResponse.session_type || 'unknown',
          status: statusResponse.status || 'unknown',
          symbols: statusResponse.symbols || [],
          start_time: statusResponse.start_time,
          total_signals: statusResponse.total_signals,
          total_trades: statusResponse.total_trades,
          win_rate: statusResponse.win_rate,
          total_pnl: statusResponse.total_pnl,
          active_strategies: statusResponse.active_strategies || []
        }];
      }
      return [];
    } catch (error) {
      return [];
    }
  }, []);

  const loadStrategies = useCallback(async (): Promise<Strategy[]> => {
    try {
      const response = await apiService.getStrategyStatus();
      return response || [];
    } catch (error) {
      return [];
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sessionsData, strategiesData] = await Promise.all([
        loadSessions(),
        loadStrategies()
      ]);

      setSessions(sessionsData);
      setStrategies(strategiesData);

      // Find active session
      const active = sessionsData.find(s => s.status === 'running' || s.status === 'active');
      setActiveSession(active || null);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load trading data',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  }, [loadSessions, loadStrategies]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresh every 30 seconds; pause when tab hidden
  useVisibilityAwareInterval(loadData, 30000);

  const handleStartSession = () => {
    setDialogOpen(true);
  };

  const handleStopSession = async () => {
    if (!activeSession) return;

    try {
      await apiService.stopSession(activeSession.session_id);
      setSnackbar({
        open: true,
        message: 'Session stopped successfully',
        severity: 'success'
      });
      loadData();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to stop session',
        severity: 'error'
      });
    }
  };

  const handleCreateSession = async () => {
    try {
      const sessionData = {
        session_type: sessionForm.session_type,
        symbols: sessionForm.symbols,
        strategy_config: sessionForm.strategy_config,
        config: sessionForm.config,
        idempotent: true
      };

      const response = await apiService.startSession(sessionData);
      setSnackbar({
        open: true,
        message: `Session started: ${response.data?.session_id}`,
        severity: 'success'
      });
      setDialogOpen(false);
      loadData();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to start session',
        severity: 'error'
      });
    }
  };

  // Status utilities are now imported from SystemStatusIndicator

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Live Trading
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
            disabled={loading}
          >
            Refresh
          </Button>
          {activeSession ? (
            <Button
              variant="contained"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopSession}
            >
              Stop Session
            </Button>
          ) : (
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayIcon />}
              onClick={handleStartSession}
            >
              Start New Session
            </Button>
          )}
        </Box>
      </Box>

      {/* System Status */}
      <SystemStatusIndicator showDetails={false} />

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Active Session Status */}
      {activeSession && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Active Session:</strong> {activeSession.session_id} |
            <strong> Type:</strong> {activeSession.session_type} |
            <strong> Symbols:</strong> {activeSession.symbols.join(', ')} |
            <strong> Status:</strong> {activeSession.status}
          </Typography>
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <PlayIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Sessions</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {sessions.filter(s => s.status === 'running' || s.status === 'active').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AssessmentIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Signals</Typography>
              </Box>
              <Typography variant="h4" color="secondary">
                {activeSession?.total_signals || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUpIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Win Rate</Typography>
              </Box>
              <Typography variant="h4" color="success">
                {activeSession?.win_rate ? `${activeSession.win_rate.toFixed(1)}%` : '0%'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUpIcon color={activeSession?.total_pnl && activeSession.total_pnl >= 0 ? 'success' : 'error'} sx={{ mr: 1 }} />
                <Typography variant="h6">Total P&L</Typography>
              </Box>
              <Typography variant="h4" color={activeSession?.total_pnl && activeSession.total_pnl >= 0 ? 'success' : 'error'}>
                ${activeSession?.total_pnl ? activeSession.total_pnl.toFixed(2) : '0.00'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Session Details Accordion */}
      {activeSession && (
        <Accordion expanded={true} sx={{ mb: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Session Details: {activeSession.session_id}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Session Type</Typography>
                <Chip label={activeSession.session_type} color="primary" size="small" />
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Status</Typography>
                <Chip
                  label={activeSession.status}
                  color={getSessionStatusColor(activeSession.status as any)}
                  size="small"
                  icon={getSessionStatusIcon(activeSession.status as any)}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Symbols</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {activeSession.symbols.map(symbol => (
                    <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                  ))}
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Active Strategies</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {activeSession.active_strategies?.map(strategy => (
                    <Chip key={strategy} label={strategy} size="small" color="secondary" variant="outlined" />
                  )) || <Typography variant="caption" color="text.secondary">None</Typography>}
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Start Time</Typography>
                <Typography variant="body1">
                  {activeSession.start_time ? new Date(activeSession.start_time).toLocaleString() : 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Total Trades</Typography>
                <Typography variant="body1">{activeSession.total_trades || 0}</Typography>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Strategies Table */}
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">Available Strategies</Typography>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Strategy Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>State</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow key={strategy.strategy_name} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {strategy.strategy_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={strategy.enabled ? 'Enabled' : 'Disabled'}
                      color={strategy.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={strategy.current_state}
                      color={strategy.current_state === 'INACTIVE' ? 'default' : 'primary'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {strategy.symbol || <Typography variant="caption" color="text.secondary">None</Typography>}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={!strategy.enabled}
                    >
                      Configure
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {strategies.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No strategies available. Create strategies in the Strategy Builder first.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Start Session Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Start New Trading Session</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Session Type</InputLabel>
              <Select
                value={sessionForm.session_type}
                label="Session Type"
                onChange={(e) => setSessionForm(prev => ({ ...prev, session_type: e.target.value }))}
              >
                <MenuItem value="paper">Paper Trading (Virtual)</MenuItem>
                <MenuItem value="live">Live Trading (Real Money)</MenuItem>
                <MenuItem value="backtest">Backtesting (Historical)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Symbols</InputLabel>
              <Select
                multiple
                value={sessionForm.symbols}
                label="Symbols"
                onChange={(e) => setSessionForm(prev => ({
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

            <TextField
              fullWidth
              label="Global Budget Cap (USD)"
              type="number"
              value={sessionForm.config.budget.global_cap}
              onChange={(e) => setSessionForm(prev => ({
                ...prev,
                config: {
                  ...prev.config,
                  budget: {
                    ...prev.config.budget,
                    global_cap: parseFloat(e.target.value) || 1000
                  }
                }
              }))}
              helperText="Maximum total budget for this session"
            />

            <Alert severity="info">
              <Typography variant="body2">
                <strong>Paper Trading:</strong> Virtual money, no real trades - perfect for testing strategies
                <br />
                <strong>Live Trading:</strong> Real money trades on exchange - use with caution
                <br />
                For historical backtesting, use the dedicated Backtesting tab
              </Typography>
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateSession} variant="contained" color="success">
            Start Session
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
