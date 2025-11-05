'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Divider,
  Tab,
  Tabs,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  Stop as StopIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ShowChartIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import LiquidationAlert from '@/components/trading/LiquidationAlert';

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
  notes?: string;
}

interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  current_drawdown: number;
  max_drawdown_duration: number;
  avg_trade_duration: number;
  largest_win: number;
  largest_loss: number;
}

interface Order {
  order_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  position_side: 'LONG' | 'SHORT';
  order_type: 'MARKET' | 'LIMIT';
  quantity: number;
  price: number;
  filled_price: number;
  slippage_pct: number;
  status: 'FILLED' | 'CANCELLED' | 'PENDING';
  timestamp: string;
}

interface Position {
  position_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number;
  quantity: number;
  leverage: number;
  liquidation_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  opened_at: string;
}

// ============================================
// Main Component
// ============================================

export default function PaperTradingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.sessionId as string;

  // ============================================
  // State Management
  // ============================================

  const [session, setSession] = useState<PaperTradingSession | null>(null);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [tabValue, setTabValue] = useState(0);
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

  const fetchSessionDetails = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.get(`/api/paper-trading/sessions/${sessionId}`);
      if (response.success && response.session) {
        setSession(response.session);
      }
    } catch (error: any) {
      console.error('Failed to fetch session details:', error);
      setSnackbar({
        open: true,
        message: `Failed to load session: ${error.message || 'Unknown error'}`,
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const fetchPerformance = useCallback(async () => {
    try {
      const response = await apiService.get(`/api/paper-trading/sessions/${sessionId}/performance`);
      if (response.success && response.performance) {
        setPerformance(response.performance);
      }
    } catch (error: any) {
      console.error('Failed to fetch performance:', error);
    }
  }, [sessionId]);

  const fetchOrders = useCallback(async () => {
    try {
      const response = await apiService.get(`/api/paper-trading/sessions/${sessionId}/orders`);
      if (response.success && response.orders) {
        setOrders(response.orders);
      }
    } catch (error: any) {
      console.error('Failed to fetch orders:', error);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      router.push('/paper-trading');
      return;
    }

    fetchSessionDetails();
    fetchPerformance();
    fetchOrders();

    // Poll for updates every 3 seconds (will be replaced with WebSocket in Task 1.3)
    const interval = setInterval(() => {
      fetchPerformance();
      fetchOrders();
    }, 3000);

    return () => clearInterval(interval);
  }, [sessionId, fetchSessionDetails, fetchPerformance, fetchOrders, router]);

  // ============================================
  // Action Handlers
  // ============================================

  const handleStopSession = async () => {
    try {
      setLoading(true);
      const response = await apiService.post(`/api/paper-trading/sessions/${sessionId}/stop`, {});

      if (response.success) {
        setSnackbar({
          open: true,
          message: 'Session stopped successfully',
          severity: 'success',
        });
        fetchSessionDetails();
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

  const handleRefresh = () => {
    fetchSessionDetails();
    fetchPerformance();
    fetchOrders();
  };

  // ============================================
  // Helper Functions
  // ============================================

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

  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

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

  // ============================================
  // Render Guards
  // ============================================

  if (!session) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="body1" sx={{ mt: 2, textAlign: 'center' }}>
          Loading session details...
        </Typography>
      </Box>
    );
  }

  // ============================================
  // Render
  // ============================================

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton onClick={() => router.push('/paper-trading')} sx={{ mr: 2 }}>
            <ArrowBackIcon />
          </IconButton>
          <Box>
            <Typography variant="h4" component="h1">
              📊 Paper Trading Session
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
              {sessionId}
            </Typography>
          </Box>
        </Box>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            sx={{ mr: 2 }}
            disabled={loading}
          >
            Refresh
          </Button>
          {session.status === 'RUNNING' && (
            <Button
              variant="contained"
              color="warning"
              startIcon={<StopIcon />}
              onClick={handleStopSession}
              disabled={loading}
            >
              Stop Session
            </Button>
          )}
        </Box>
      </Box>

      {/* Liquidation Risk Alerts (TIER 1.4) */}
      {session.leverage > 1 && session.status === 'RUNNING' && (
        <LiquidationAlert
          sessionId={sessionId as string}
          enableToastNotifications={true}
          autoHideDelay={15000}
        />
      )}

      {/* Session Info Card */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Typography variant="caption" color="text.secondary">
              Strategy
            </Typography>
            <Typography variant="h6">{session.strategy_name}</Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="caption" color="text.secondary">
              Symbols
            </Typography>
            <Box>
              {session.symbols.map((symbol) => (
                <Chip key={symbol} label={symbol} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
              ))}
            </Box>
          </Grid>
          <Grid item xs={12} md={2}>
            <Typography variant="caption" color="text.secondary">
              Direction
            </Typography>
            <Box>
              <Chip
                label={session.direction}
                size="small"
                color={
                  session.direction === 'SHORT' ? 'error' : session.direction === 'LONG' ? 'success' : 'default'
                }
              />
            </Box>
          </Grid>
          <Grid item xs={12} md={2}>
            <Typography variant="caption" color="text.secondary">
              Leverage
            </Typography>
            <Typography variant="h6">{session.leverage}x</Typography>
          </Grid>
          <Grid item xs={12} md={2}>
            <Typography variant="caption" color="text.secondary">
              Status
            </Typography>
            <Box>
              <Chip label={session.status} size="small" color={getStatusColor(session.status)} />
            </Box>
          </Grid>
        </Grid>

        {session.notes && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">
              Notes
            </Typography>
            <Typography variant="body2">{session.notes}</Typography>
          </>
        )}
      </Paper>

      {/* Performance Metrics */}
      {performance && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {/* Balance Card */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Current Balance
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                  {formatCurrency(session.current_balance)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Initial: {formatCurrency(session.initial_balance)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* P&L Card */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Total P&L
                </Typography>
                <Typography
                  variant="h5"
                  sx={{
                    fontWeight: 600,
                    mb: 1,
                    color: performance.total_pnl >= 0 ? 'success.main' : 'error.main',
                  }}
                >
                  {formatCurrency(performance.total_pnl)}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {performance.total_pnl >= 0 ? (
                    <TrendingUpIcon fontSize="small" color="success" sx={{ mr: 0.5 }} />
                  ) : (
                    <TrendingDownIcon fontSize="small" color="error" sx={{ mr: 0.5 }} />
                  )}
                  <Typography
                    variant="body2"
                    sx={{ color: performance.total_pnl >= 0 ? 'success.main' : 'error.main' }}
                  >
                    {formatPercentage(performance.total_pnl_pct)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Win Rate Card */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Win Rate
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                  {performance.win_rate.toFixed(1)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {performance.winning_trades}W / {performance.losing_trades}L
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Drawdown Card */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Drawdown
                </Typography>
                <Typography
                  variant="h5"
                  sx={{
                    fontWeight: 600,
                    mb: 1,
                    color: performance.current_drawdown < -10 ? 'error.main' : 'text.primary',
                  }}
                >
                  {performance.current_drawdown.toFixed(2)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Max: {performance.max_drawdown.toFixed(2)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Additional Metrics */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Profit Factor
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {performance.profit_factor.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Sharpe Ratio
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {performance.sharpe_ratio.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Avg Win / Loss
                </Typography>
                <Typography variant="body2" color="success.main">
                  Win: {formatCurrency(performance.avg_win)}
                </Typography>
                <Typography variant="body2" color="error.main">
                  Loss: {formatCurrency(performance.avg_loss)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  Largest Trade
                </Typography>
                <Typography variant="body2" color="success.main">
                  Win: {formatCurrency(performance.largest_win)}
                </Typography>
                <Typography variant="body2" color="error.main">
                  Loss: {formatCurrency(performance.largest_loss)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs for Orders/Positions/Charts */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label={`Orders (${orders.length})`} />
          <Tab label={`Positions (${positions.length})`} />
          <Tab label="Charts" disabled icon={<ShowChartIcon />} />
        </Tabs>

        {/* Orders Tab */}
        {tabValue === 0 && (
          <Box sx={{ p: 2 }}>
            {orders.length === 0 ? (
              <Alert severity="info">
                <Typography variant="body2">
                  No orders yet. Orders will appear here as the strategy executes trades.
                </Typography>
              </Alert>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Time</strong></TableCell>
                      <TableCell><strong>Symbol</strong></TableCell>
                      <TableCell><strong>Side</strong></TableCell>
                      <TableCell><strong>Position</strong></TableCell>
                      <TableCell><strong>Type</strong></TableCell>
                      <TableCell align="right"><strong>Quantity</strong></TableCell>
                      <TableCell align="right"><strong>Price</strong></TableCell>
                      <TableCell align="right"><strong>Filled</strong></TableCell>
                      <TableCell align="right"><strong>Slippage</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orders.map((order) => (
                      <TableRow key={order.order_id} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                            {formatDateTime(order.timestamp)}
                          </Typography>
                        </TableCell>
                        <TableCell>{order.symbol}</TableCell>
                        <TableCell>
                          <Chip
                            label={order.side}
                            size="small"
                            color={order.side === 'BUY' ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={order.position_side}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{order.order_type}</TableCell>
                        <TableCell align="right">{order.quantity.toFixed(6)}</TableCell>
                        <TableCell align="right">{formatCurrency(order.price)}</TableCell>
                        <TableCell align="right">{formatCurrency(order.filled_price)}</TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            sx={{ color: order.slippage_pct > 0.05 ? 'error.main' : 'text.primary' }}
                          >
                            {order.slippage_pct.toFixed(3)}%
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={order.status} size="small" color="success" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}

        {/* Positions Tab */}
        {tabValue === 1 && (
          <Box sx={{ p: 2 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Note:</strong> Position tracking will be implemented in the next phase.
                Currently showing order history only.
              </Typography>
            </Alert>
          </Box>
        )}

        {/* Charts Tab (Placeholder) */}
        {tabValue === 2 && (
          <Box sx={{ p: 2 }}>
            <Alert severity="info">
              <Typography variant="body2">
                <strong>Coming Soon:</strong> Performance charts (Equity Curve, Drawdown, P&L Distribution)
                will be available in Task 1.2 Phase 2.
              </Typography>
            </Alert>
          </Box>
        )}
      </Paper>

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
