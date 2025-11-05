'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  SelectChangeEvent,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
  Add as AddIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { apiService } from '@/services/api';

// ============================================
// TypeScript Interfaces
// ============================================

interface PaperTradingSession {
  session_id: string;
  strategy_id: string;
  strategy_name: string;
  symbols: string[];
  direction: 'LONG' | 'SHORT' | 'BOTH';
  leverage: number;
  initial_balance: number;
  current_balance: number;
  status: 'RUNNING' | 'STOPPED' | 'COMPLETED' | 'ERROR';
  created_at: string;
  stopped_at?: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  current_drawdown: number;
  max_drawdown: number;
}

interface Strategy {
  id: string;
  strategy_name: string;
  description?: string;
  direction: 'LONG' | 'SHORT' | 'BOTH';
  enabled: boolean;
}

interface CreateSessionFormData {
  strategy_id: string;
  symbols: string[];
  direction: 'LONG' | 'SHORT' | 'BOTH';
  leverage: number;
  initial_balance: number;
  notes: string;
}

// ============================================
// Main Component
// ============================================

export default function PaperTradingPage() {
  // ============================================
  // State Management
  // ============================================

  const router = useRouter();
  const [sessions, setSessions] = useState<PaperTradingSession[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [symbolsLoading, setSymbolsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState<CreateSessionFormData>({
    strategy_id: '',
    symbols: ['BTC_USDT'],
    direction: 'SHORT',
    leverage: 3,
    initial_balance: 10000,
    notes: '',
  });
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // ============================================
  // Data Fetching
  // ============================================

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/api/paper-trading/sessions');
      if (response.success && response.sessions) {
        setSessions(response.sessions);
      }
    } catch (error: any) {
      console.error('Failed to fetch paper trading sessions:', error);
      setSnackbar({
        open: true,
        message: `Failed to load sessions: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStrategies = useCallback(async () => {
    try {
      const response = await apiService.get('/api/strategies');
      if (response.strategies) {
        setStrategies(response.strategies);
      }
    } catch (error: any) {
      console.error('Failed to fetch strategies:', error);
      setSnackbar({
        open: true,
        message: `Failed to load strategies: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    }
  }, []);

  const loadAvailableSymbols = useCallback(async () => {
    setSymbolsLoading(true);
    try {
      const symbols = await apiService.getSymbols();
      if (symbols && symbols.length > 0) {
        setAvailableSymbols(symbols);
        // Update default symbol in form to first available symbol
        setFormData(prev => ({
          ...prev,
          symbols: [symbols[0]]
        }));
      } else {
        setAvailableSymbols([]);
      }
    } catch (error) {
      console.error('Failed to load available symbols:', error);
      // Fallback to default symbols if API fails
      const fallbackSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT', 'MATIC_USDT', 'AVAX_USDT'];
      setAvailableSymbols(fallbackSymbols);
      setFormData(prev => ({
        ...prev,
        symbols: [fallbackSymbols[0]]
      }));
    } finally {
      setSymbolsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchStrategies();
    loadAvailableSymbols();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, [fetchSessions, fetchStrategies, loadAvailableSymbols]);

  // ============================================
  // Session Management Handlers
  // ============================================

  const handleCreateSession = async () => {
    try {
      if (!formData.strategy_id) {
        setSnackbar({
          open: true,
          message: 'Please select a strategy',
          severity: 'warning',
        });
        return;
      }

      const selectedStrategy = strategies.find(s => s.id === formData.strategy_id);
      if (!selectedStrategy) {
        setSnackbar({
          open: true,
          message: 'Selected strategy not found',
          severity: 'error',
        });
        return;
      }

      setLoading(true);

      const requestBody = {
        strategy_id: formData.strategy_id,
        strategy_name: selectedStrategy.strategy_name,
        symbols: formData.symbols,
        direction: formData.direction,
        leverage: formData.leverage,
        initial_balance: formData.initial_balance,
        notes: formData.notes || '',
      };

      const response = await apiService.post('/api/paper-trading/sessions', requestBody);

      if (response.success && response.session) {
        setSnackbar({
          open: true,
          message: `Paper trading session started: ${response.session.session_id}`,
          severity: 'success',
        });
        setDialogOpen(false);
        // Reset form
        setFormData({
          strategy_id: '',
          symbols: ['BTC_USDT'],
          direction: 'SHORT',
          leverage: 3,
          initial_balance: 10000,
          notes: '',
        });
        // Refresh sessions list
        fetchSessions();
      }
    } catch (error: any) {
      console.error('Failed to create paper trading session:', error);
      setSnackbar({
        open: true,
        message: `Failed to start session: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStopSession = async (sessionId: string) => {
    try {
      setLoading(true);
      const response = await apiService.post(`/api/paper-trading/sessions/${sessionId}/stop`, {});

      if (response.success) {
        setSnackbar({
          open: true,
          message: 'Session stopped successfully',
          severity: 'success',
        });
        fetchSessions();
      }
    } catch (error: any) {
      console.error('Failed to stop session:', error);
      setSnackbar({
        open: true,
        message: `Failed to stop session: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!window.confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      return;
    }

    try {
      setLoading(true);
      await apiService.delete(`/api/paper-trading/sessions/${sessionId}`);

      setSnackbar({
        open: true,
        message: 'Session deleted successfully',
        severity: 'success',
      });
      fetchSessions();
    } catch (error: any) {
      console.error('Failed to delete session:', error);
      setSnackbar({
        open: true,
        message: `Failed to delete session: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewSession = (sessionId: string) => {
    router.push(`/paper-trading/${sessionId}`);
  };

  // ============================================
  // Form Handlers
  // ============================================

  const handleSymbolsChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setFormData({
      ...formData,
      symbols: typeof value === 'string' ? value.split(',') : value,
    });
  };

  // ============================================
  // Helper Functions
  // ============================================

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
    switch (status) {
      case 'RUNNING':
        return 'success';
      case 'STOPPED':
        return 'warning';
      case 'COMPLETED':
        return 'default';
      case 'ERROR':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number): string => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  // ============================================
  // Render
  // ============================================

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          📊 Paper Trading
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchSessions}
            sx={{ mr: 2 }}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogOpen(true)}
            disabled={loading}
          >
            New Session
          </Button>
        </Box>
      </Box>

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Paper Trading</strong> allows you to test strategies with simulated trading (no real money).
          All orders are executed with realistic slippage, funding rates, and liquidation calculations.
        </Typography>
      </Alert>

      {/* Loading Indicator */}
      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Sessions Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Session ID</strong></TableCell>
              <TableCell><strong>Strategy</strong></TableCell>
              <TableCell><strong>Symbols</strong></TableCell>
              <TableCell><strong>Direction</strong></TableCell>
              <TableCell><strong>Leverage</strong></TableCell>
              <TableCell align="right"><strong>Balance</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>Win Rate</strong></TableCell>
              <TableCell align="right"><strong>Drawdown</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                    No paper trading sessions yet. Click "New Session" to start testing a strategy.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              sessions.map((session) => (
                <TableRow key={session.session_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {session.session_id.substring(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>{session.strategy_name}</TableCell>
                  <TableCell>
                    {session.symbols.map(symbol => (
                      <Chip key={symbol} label={symbol} size="small" sx={{ mr: 0.5 }} />
                    ))}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={session.direction}
                      size="small"
                      color={session.direction === 'SHORT' ? 'error' : session.direction === 'LONG' ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell>{session.leverage}x</TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {formatCurrency(session.current_balance)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      / {formatCurrency(session.initial_balance)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{
                        color: session.total_pnl >= 0 ? 'success.main' : 'error.main',
                        fontWeight: 600,
                      }}
                    >
                      {formatCurrency(session.total_pnl)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatPercentage(session.total_pnl_pct)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {session.win_rate.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {session.winning_trades}W / {session.losing_trades}L
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{ color: session.current_drawdown < -10 ? 'error.main' : 'text.primary' }}
                    >
                      {session.current_drawdown.toFixed(2)}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Max: {session.max_drawdown.toFixed(2)}%
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={session.status}
                      color={getStatusColor(session.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="View Details">
                      <IconButton
                        size="small"
                        onClick={() => handleViewSession(session.session_id)}
                        color="primary"
                      >
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {session.status === 'RUNNING' && (
                      <Tooltip title="Stop Session">
                        <IconButton
                          size="small"
                          onClick={() => handleStopSession(session.session_id)}
                          color="warning"
                          disabled={loading}
                        >
                          <StopIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Delete Session">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteSession(session.session_id)}
                        color="error"
                        disabled={loading || session.status === 'RUNNING'}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create Session Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Paper Trading Session</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={3}>
              {/* Strategy Selection */}
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Strategy *</InputLabel>
                  <Select
                    value={formData.strategy_id}
                    onChange={(e) => setFormData({ ...formData, strategy_id: e.target.value })}
                    label="Strategy *"
                  >
                    {strategies.length === 0 ? (
                      <MenuItem value="" disabled>
                        No strategies available. Create a strategy first.
                      </MenuItem>
                    ) : (
                      strategies.map((strategy) => (
                        <MenuItem key={strategy.id} value={strategy.id}>
                          {strategy.strategy_name} ({strategy.direction})
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              </Grid>

              {/* Symbols Selection */}
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Trading Symbols *</InputLabel>
                  <Select
                    multiple
                    value={formData.symbols}
                    onChange={handleSymbolsChange}
                    label="Trading Symbols *"
                    disabled={symbolsLoading}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {symbolsLoading ? (
                      <MenuItem disabled>
                        <Typography variant="body2" color="text.secondary">
                          Loading symbols...
                        </Typography>
                      </MenuItem>
                    ) : availableSymbols.length === 0 ? (
                      <MenuItem disabled>
                        <Typography variant="body2" color="text.secondary">
                          No symbols available. Check backend configuration.
                        </Typography>
                      </MenuItem>
                    ) : (
                      availableSymbols.map((symbol) => (
                        <MenuItem key={symbol} value={symbol}>
                          {symbol}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              </Grid>

              {/* Direction */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Direction *</InputLabel>
                  <Select
                    value={formData.direction}
                    onChange={(e) => setFormData({ ...formData, direction: e.target.value as 'LONG' | 'SHORT' | 'BOTH' })}
                    label="Direction *"
                  >
                    <MenuItem value="LONG">LONG (Buy)</MenuItem>
                    <MenuItem value="SHORT">SHORT (Sell)</MenuItem>
                    <MenuItem value="BOTH">BOTH (Long & Short)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Leverage */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Leverage *</InputLabel>
                  <Select
                    value={formData.leverage}
                    onChange={(e) => setFormData({ ...formData, leverage: Number(e.target.value) })}
                    label="Leverage *"
                  >
                    <MenuItem value={1}>1x - No leverage (Spot)</MenuItem>
                    <MenuItem value={2}>2x - Conservative</MenuItem>
                    <MenuItem value={3}>3x - RECOMMENDED ⭐</MenuItem>
                    <MenuItem value={5}>5x - High risk ⚠️</MenuItem>
                    <MenuItem value={10}>10x - EXTREME RISK 🔴</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Initial Balance */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Initial Balance (USD) *"
                  type="number"
                  value={formData.initial_balance}
                  onChange={(e) => setFormData({ ...formData, initial_balance: Number(e.target.value) })}
                  InputProps={{
                    startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
                  }}
                  helperText="Recommended: $10,000 - $50,000 for testing"
                />
              </Grid>

              {/* Notes */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Notes (Optional)"
                  multiline
                  rows={3}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Add notes about this trading session..."
                />
              </Grid>

              {/* Info Alert */}
              {formData.leverage > 3 && (
                <Grid item xs={12}>
                  <Alert severity="warning">
                    <Typography variant="body2">
                      <strong>High Risk:</strong> {formData.leverage}x leverage means liquidation occurs at{' '}
                      {(100 / formData.leverage).toFixed(1)}% adverse price movement. Consider using 3x or lower
                      for pump & dump strategies with high volatility.
                    </Typography>
                  </Alert>
                </Grid>
              )}
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateSession}
            variant="contained"
            startIcon={<PlayIcon />}
            disabled={loading || !formData.strategy_id || formData.symbols.length === 0}
          >
            Start Session
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
