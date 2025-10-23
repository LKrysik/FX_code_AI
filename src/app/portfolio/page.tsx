'use client';

import React, { useState, useEffect } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tabs,
  Tab,
} from '@mui/material';
import {
  AccountBalanceWallet as WalletIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Assessment as AssessmentIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';

interface PortfolioBalance {
  total_usd_estimate: number;
  assets: {
    [key: string]: {
      free: number;
      locked: number;
    };
  };
  source: string;
  timestamp: string;
}

interface Trade {
  trade_id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  total_pnl: number;
  timestamp: string;
  status: string;
}

interface Performance {
  total_pnl: number;
  win_rate: number;
  total_trades: number;
  active_positions: number;
  max_drawdown: number;
}

export default function PortfolioPage() {
  const [balance, setBalance] = useState<PortfolioBalance | null>(null);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  useEffect(() => {
    loadPortfolioData();
  }, []);

  // Auto-refresh every 30 seconds; pause when tab hidden
  useVisibilityAwareInterval(loadPortfolioData, 30000);

  const loadPortfolioData = async () => {
    setLoading(true);
    try {
      const [balanceData, perfData, tradesData] = await Promise.all([
        apiService.getWalletBalance(),
        apiService.getTradingPerformance(),
        apiService.getAllOrders() // This might need to be adjusted based on actual API
      ]);

      setBalance(balanceData);
      setPerformance(perfData);
      setTrades(tradesData?.orders || []);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load portfolio data',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const getTotalValue = () => {
    if (!balance) return 0;
    return Object.entries(balance.assets).reduce((total, [asset, amounts]) => {
      // Simple USD estimation - in real app, you'd use current prices
      const usdValue = asset === 'USDT' ? amounts.free + amounts.locked :
                      asset === 'BTC' ? (amounts.free + amounts.locked) * 50000 :
                      asset === 'ETH' ? (amounts.free + amounts.locked) * 3000 :
                      (amounts.free + amounts.locked) * 1; // Default fallback
      return total + usdValue;
    }, 0);
  };

  const getAssetValue = (asset: string, amount: number) => {
    // Simple USD estimation - in real app, you'd use current prices
    if (asset === 'USDT') return amount;
    if (asset === 'BTC') return amount * 50000;
    if (asset === 'ETH') return amount * 3000;
    return amount; // Default fallback
  };

  const getAssetChange = (asset: string) => {
    // Mock change data - in real app, you'd calculate from historical data
    const changes: {[key: string]: number} = {
      'BTC': 2.5,
      'ETH': -1.2,
      'USDT': 0.0,
      'ADA': 5.8,
      'SOL': -3.1
    };
    return changes[asset] || 0;
  };

  const recentTrades = trades.slice(0, 10);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Portfolio & Performance
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadPortfolioData}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Portfolio Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <WalletIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Portfolio Value</Typography>
              </Box>
              <Typography variant="h4" color="primary" sx={{ mb: 1 }}>
                ${getTotalValue().toFixed(2)}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                {balance?.source && (
                  <Chip
                    label={`Source: ${balance.source}`}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.7rem' }}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AssessmentIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total P&L</Typography>
              </Box>
              <Typography
                variant="h4"
                color={performance?.total_pnl && performance.total_pnl >= 0 ? 'success.main' : 'error.main'}
                sx={{ mb: 1 }}
              >
                ${performance?.total_pnl ? performance.total_pnl.toFixed(2) : '0.00'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {performance?.win_rate ? `${performance.win_rate.toFixed(1)}% Win Rate` : 'No trades yet'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ChartIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Positions</Typography>
              </Box>
              <Typography variant="h4" color="info.main" sx={{ mb: 1 }}>
                {performance?.active_positions || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {performance?.total_trades ? `${performance.total_trades} Total Trades` : 'No trades yet'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="Assets" />
          <Tab label="Recent Trades" />
          <Tab label="Performance" />
        </Tabs>
      </Paper>

      {/* Assets Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper>
              <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="h6">Asset Holdings</Typography>
              </Box>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Asset</TableCell>
                      <TableCell align="right">Free</TableCell>
                      <TableCell align="right">Locked</TableCell>
                      <TableCell align="right">Total</TableCell>
                      <TableCell align="right">Value (USD)</TableCell>
                      <TableCell align="right">24h Change</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {balance && Object.entries(balance.assets).map(([asset, amounts]) => {
                      const total = amounts.free + amounts.locked;
                      const usdValue = getAssetValue(asset, total);
                      const change = getAssetChange(asset);

                      return (
                        <TableRow key={asset} hover>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <Typography variant="body2" fontWeight="bold">
                                {asset}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell align="right">{amounts.free.toFixed(6)}</TableCell>
                          <TableCell align="right">{amounts.locked.toFixed(6)}</TableCell>
                          <TableCell align="right" fontWeight="bold">{total.toFixed(6)}</TableCell>
                          <TableCell align="right">${usdValue.toFixed(2)}</TableCell>
                          <TableCell align="right">
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                              {change >= 0 ? (
                                <TrendingUpIcon sx={{ color: 'success.main', mr: 0.5, fontSize: 16 }} />
                              ) : (
                                <TrendingDownIcon sx={{ color: 'error.main', mr: 0.5, fontSize: 16 }} />
                              )}
                              <Typography
                                variant="body2"
                                color={change >= 0 ? 'success.main' : 'error.main'}
                              >
                                {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                              </Typography>
                            </Box>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {(!balance || Object.keys(balance.assets).length === 0) && (
                      <TableRow>
                        <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                          <Typography variant="body2" color="text.secondary">
                            No assets found
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Portfolio Allocation
              </Typography>
              {balance && Object.entries(balance.assets).map(([asset, amounts]) => {
                const total = amounts.free + amounts.locked;
                const usdValue = getAssetValue(asset, total);
                const percentage = (usdValue / getTotalValue()) * 100;

                return (
                  <Box key={asset} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2">{asset}</Typography>
                      <Typography variant="body2">{percentage.toFixed(1)}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={percentage}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: 'grey.200',
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: asset === 'BTC' ? '#f7931a' :
                                         asset === 'ETH' ? '#627eea' :
                                         asset === 'USDT' ? '#26a69a' : '#1976d2'
                        }
                      }}
                    />
                  </Box>
                );
              })}
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Recent Trades Tab */}
      {activeTab === 1 && (
        <Paper>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">Recent Trades</Typography>
          </Box>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Side</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">P&L</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentTrades.map((trade) => (
                  <TableRow key={trade.trade_id} hover>
                    <TableCell>
                      {new Date(trade.timestamp).toLocaleTimeString()}
                    </TableCell>
                    <TableCell>
                      <Chip label={trade.symbol} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={trade.side}
                        size="small"
                        color={trade.side === 'BUY' ? 'success' : 'error'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">{trade.quantity.toFixed(6)}</TableCell>
                    <TableCell align="right">${trade.price.toFixed(2)}</TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        color={trade.total_pnl >= 0 ? 'success.main' : 'error.main'}
                        fontWeight="bold"
                      >
                        ${trade.total_pnl.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={trade.status}
                        size="small"
                        color={trade.status === 'FILLED' ? 'success' : 'warning'}
                        variant="outlined"
                      />
                    </TableCell>
                  </TableRow>
                ))}
                {recentTrades.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No recent trades
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Performance Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              {performance ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Win Rate</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {performance.win_rate.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Total Trades</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {performance.total_trades}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Active Positions</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {performance.active_positions}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Max Drawdown</Typography>
                    <Typography variant="body2" fontWeight="bold" color="error.main">
                      {(performance.max_drawdown * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No performance data available
                </Typography>
              )}
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Risk Analysis
              </Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Portfolio risk analysis would be displayed here, including:
                  <br />• Value at Risk (VaR)
                  <br />• Sharpe Ratio
                  <br />• Maximum Drawdown
                  <br />• Correlation Matrix
                </Typography>
              </Alert>
            </Paper>
          </Grid>
        </Grid>
      )}

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
