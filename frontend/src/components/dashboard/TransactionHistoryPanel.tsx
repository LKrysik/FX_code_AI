/**
 * Transaction History Panel Component
 * =====================================
 *
 * Displays order/transaction history with filtering by status.
 *
 * Features:
 * - Filter by status (FILLED, CANCELLED, FAILED)
 * - Filter by side (BUY, SELL)
 * - Shows slippage and commission
 * - Summary statistics
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface TransactionItem {
  order_id: string;
  strategy_id: string;
  symbol: string;
  session_id: string;
  side: string;
  order_type: string;
  timestamp: string;
  quantity: number;
  price: number | null;
  filled_quantity: number;
  filled_price: number | null;
  status: string;
  commission: number;
  slippage: number | null;
  metadata: Record<string, any>;
}

export interface TransactionSummary {
  total_filled: number;
  total_cancelled: number;
  total_failed: number;
  total_commission: number;
}

export interface TransactionHistoryPanelProps {
  sessionId: string | null;
  refreshInterval?: number;
  isActive?: boolean; // Whether panel is currently visible (controls auto-refresh)
}

// ============================================================================
// Component
// ============================================================================

export const TransactionHistoryPanel: React.FC<TransactionHistoryPanelProps> = ({
  sessionId,
  refreshInterval = 5000,
  isActive = true,
}) => {
  // ========================================
  // State
  // ========================================

  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [summary, setSummary] = useState<TransactionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sideFilter, setSideFilter] = useState<string>('all');

  // ========================================
  // Data Loading
  // ========================================

  const loadTransactions = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        session_id: sessionId,
        limit: '100',
      });

      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      if (sideFilter !== 'all') {
        params.append('side', sideFilter);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transactions/history?${params}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load transactions: ${response.statusText}`);
      }

      const result = await response.json();
      const data = result.data || result;

      setTransactions(data.transactions || []);
      setSummary(data.summary || null);
    } catch (err: any) {
      console.error('Failed to load transaction history:', err);
      setError(err.message || 'Failed to load transaction history');
    } finally {
      setLoading(false);
    }
  }, [sessionId, statusFilter, sideFilter]);

  // ========================================
  // Effects
  // ========================================

  useEffect(() => {
    if (sessionId) {
      loadTransactions();
    }
  }, [sessionId, statusFilter, sideFilter, loadTransactions]);

  // Auto-refresh (only when panel is active)
  useEffect(() => {
    if (!refreshInterval || !sessionId || !isActive) return;

    const intervalId = setInterval(() => {
      loadTransactions();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [refreshInterval, sessionId, isActive, loadTransactions]);

  // ========================================
  // Helpers
  // ========================================

  const getStatusIcon = (status: string) => {
    if (status === 'FILLED') return <CheckCircleIcon color="success" fontSize="small" />;
    if (status === 'CANCELLED') return <CancelIcon color="warning" fontSize="small" />;
    if (status === 'FAILED' || status === 'REJECTED') return <ErrorIcon color="error" fontSize="small" />;
    return null;
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    if (status === 'FILLED') return 'success';
    if (status === 'CANCELLED') return 'warning';
    if (status === 'FAILED' || status === 'REJECTED') return 'error';
    return 'default';
  };

  const getSideColor = (side: string): 'success' | 'error' | 'default' => {
    if (side === 'BUY') return 'success';
    if (side === 'SELL') return 'error';
    return 'default';
  };

  // ========================================
  // Render
  // ========================================

  if (!sessionId) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Start a session to view transaction history
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">💰 Transaction History</Typography>
        <Button variant="outlined" size="small" onClick={loadTransactions} disabled={loading}>
          Refresh
        </Button>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Filled
                </Typography>
                <Typography variant="h6" color="success.main">
                  {summary.total_filled}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Cancelled
                </Typography>
                <Typography variant="h6" color="warning.main">
                  {summary.total_cancelled}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Failed
                </Typography>
                <Typography variant="h6" color="error.main">
                  {summary.total_failed}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Total Commission
                </Typography>
                <Typography variant="h6">
                  ${summary.total_commission.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <ToggleButtonGroup
          value={statusFilter}
          exclusive
          onChange={(_, val) => val && setStatusFilter(val)}
          size="small"
        >
          <ToggleButton value="all">All</ToggleButton>
          <ToggleButton value="NEW">🆕 New</ToggleButton>
          <ToggleButton value="PARTIALLY_FILLED">⏳ Partial</ToggleButton>
          <ToggleButton value="FILLED">✅ Filled</ToggleButton>
          <ToggleButton value="CANCELLED">⚠️ Cancelled</ToggleButton>
          <ToggleButton value="FAILED">❌ Failed</ToggleButton>
        </ToggleButtonGroup>

        <ToggleButtonGroup
          value={sideFilter}
          exclusive
          onChange={(_, val) => val && setSideFilter(val)}
          size="small"
        >
          <ToggleButton value="all">All Sides</ToggleButton>
          <ToggleButton value="BUY">BUY</ToggleButton>
          <ToggleButton value="SELL">SELL</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && transactions.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Empty State */}
      {!loading && transactions.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          No transactions found matching filters
        </Typography>
      )}

      {/* Transaction Table */}
      {transactions.length > 0 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Quantity</TableCell>
                <TableCell align="right">Price</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Slippage</TableCell>
                <TableCell align="right">Commission</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {transactions.map((tx) => (
                <TableRow key={tx.order_id} hover>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(tx.timestamp).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {tx.symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={tx.side} color={getSideColor(tx.side)} size="small" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{tx.order_type}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {tx.filled_quantity > 0
                        ? `${tx.filled_quantity}/${tx.quantity}`
                        : tx.quantity}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {tx.filled_price
                        ? `$${tx.filled_price.toFixed(2)}`
                        : tx.price
                        ? `$${tx.price.toFixed(2)}`
                        : '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getStatusIcon(tx.status)}
                      <Chip label={tx.status} color={getStatusColor(tx.status)} size="small" />
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={
                        tx.slippage
                          ? tx.slippage > 0
                            ? 'error.main'
                            : 'success.main'
                          : 'text.secondary'
                      }
                    >
                      {tx.slippage ? `$${tx.slippage.toFixed(2)}` : '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">${tx.commission.toFixed(2)}</Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Footer */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Showing {transactions.length} transaction{transactions.length !== 1 ? 's' : ''}
        </Typography>
        {loading && transactions.length > 0 && <CircularProgress size={20} />}
      </Box>
    </Box>
  );
};
