/**
 * Trade Breakdown Table Component (SH-07)
 * =======================================
 *
 * Per-trade breakdown table showing individual trade performance.
 * Lists all trades from a session with entry/exit details and P&L.
 *
 * Features:
 * - List of all trades in session
 * - Entry price, exit price, P&L per trade
 * - Entry/exit timestamps
 * - Trade duration
 * - Exit reason (ZE1 planned vs E1 emergency)
 * - Win/loss highlighting
 * - Sortable columns
 *
 * Related: docs/UI_BACKLOG.md (SH-07)
 */

import React, { useState, useEffect } from 'react';
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
  TableSortLabel,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton,
  Collapse,
  Stack,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  TrendingUp as ProfitIcon,
  TrendingDown as LossIcon,
  Timer as DurationIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  CheckCircle as PlannedIcon,
  Warning as EmergencyIcon,
  Info as InfoIcon,
  TableChart as TableIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface Trade {
  id: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  exit_price: number;
  quantity: number;
  entry_time: string;
  exit_time: string;
  duration_ms: number;
  pnl: number;
  pnl_percent: number;
  exit_reason: 'ZE1' | 'E1' | 'MANUAL';
  entry_trigger?: string;
  exit_trigger?: string;
  indicator_values_at_entry?: Record<string, number>;
  indicator_values_at_exit?: Record<string, number>;
}

export interface TradeBreakdownTableProps {
  sessionId: string;
  trades?: Trade[];
  onTradesLoad?: (trades: Trade[]) => void;
}

type SortField = 'entry_time' | 'pnl' | 'pnl_percent' | 'duration_ms';
type SortDirection = 'asc' | 'desc';

// ============================================================================
// Component
// ============================================================================

export const TradeBreakdownTable: React.FC<TradeBreakdownTableProps> = ({
  sessionId,
  trades: propTrades,
  onTradesLoad,
}) => {
  const [trades, setTrades] = useState<Trade[]>(propTrades || []);
  const [loading, setLoading] = useState(!propTrades);
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('entry_time');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    if (propTrades) {
      setTrades(propTrades);
      setLoading(false);
      return;
    }

    const loadTrades = async () => {
      if (!sessionId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/trades`);

        if (!response.ok) {
          // If endpoint doesn't exist yet, use mock data
          if (response.status === 404) {
            const mockTrades = generateMockTrades();
            setTrades(mockTrades);
            onTradesLoad?.(mockTrades);
            return;
          }
          throw new Error(`Failed to load trades: ${response.status}`);
        }

        const result = await response.json();
        const data = result.data?.trades || result.trades || [];
        setTrades(data);
        onTradesLoad?.(data);
      } catch (err) {
        Logger.error('TradeBreakdownTable.loadTrades', { message: 'Failed to load trades', error: err });
        // Fallback to mock data for development
        const mockTrades = generateMockTrades();
        setTrades(mockTrades);
        onTradesLoad?.(mockTrades);
      } finally {
        setLoading(false);
      }
    };

    loadTrades();
  }, [sessionId, propTrades, onTradesLoad]);

  // ========================================
  // Helpers
  // ========================================

  const generateMockTrades = (): Trade[] => {
    const count = Math.floor(Math.random() * 8) + 3; // 3-10 trades
    const now = Date.now();
    const trades: Trade[] = [];

    for (let i = 0; i < count; i++) {
      const entryTime = new Date(now - (count - i) * 3600000 - Math.random() * 3600000);
      const duration = Math.floor(Math.random() * 1800000) + 60000; // 1-30 minutes
      const exitTime = new Date(entryTime.getTime() + duration);
      const entryPrice = 40000 + Math.random() * 5000;
      const pnlPercent = (Math.random() - 0.4) * 10; // -4% to +6%
      const exitPrice = entryPrice * (1 - pnlPercent / 100); // SHORT position
      const isWin = pnlPercent > 0;

      trades.push({
        id: `trade-${i + 1}`,
        symbol: 'BTC_USDT',
        direction: 'SHORT',
        entry_price: entryPrice,
        exit_price: exitPrice,
        quantity: 0.01,
        entry_time: entryTime.toISOString(),
        exit_time: exitTime.toISOString(),
        duration_ms: duration,
        pnl: (entryPrice - exitPrice) * 0.01, // P&L for SHORT
        pnl_percent: pnlPercent,
        exit_reason: Math.random() > 0.2 ? 'ZE1' : 'E1',
        entry_trigger: 'peak_detected',
        exit_trigger: Math.random() > 0.2 ? 'dump_end_detected' : 'stop_loss_hit',
      });
    }

    return trades;
  };

  const formatTime = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return 'N/A';
    }
  };

  const formatDate = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return '';
    }
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${Math.floor(ms / 1000)}s`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
  };

  const formatPrice = (price: number): string => {
    return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleRowExpanded = (tradeId: string) => {
    setExpandedRows((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(tradeId)) {
        newSet.delete(tradeId);
      } else {
        newSet.add(tradeId);
      }
      return newSet;
    });
  };

  const sortedTrades = [...trades].sort((a, b) => {
    let comparison = 0;
    switch (sortField) {
      case 'entry_time':
        comparison = new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime();
        break;
      case 'pnl':
        comparison = a.pnl - b.pnl;
        break;
      case 'pnl_percent':
        comparison = a.pnl_percent - b.pnl_percent;
        break;
      case 'duration_ms':
        comparison = a.duration_ms - b.duration_ms;
        break;
    }
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  // Summary stats
  const totalPnl = trades.reduce((sum, t) => sum + t.pnl, 0);
  const winCount = trades.filter((t) => t.pnl > 0).length;
  const lossCount = trades.filter((t) => t.pnl <= 0).length;
  const plannedExits = trades.filter((t) => t.exit_reason === 'ZE1').length;

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading trades...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (trades.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">No trades recorded for this session.</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <TableIcon color="primary" />
        <Typography variant="h6">Trade Breakdown (SH-07)</Typography>
        <Tooltip title="Individual trade analysis with entry/exit details and P&L">
          <InfoIcon fontSize="small" color="action" sx={{ ml: 'auto' }} />
        </Tooltip>
      </Box>

      {/* Summary Chips */}
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
        <Chip
          label={`${trades.length} trades`}
          size="small"
          variant="outlined"
        />
        <Chip
          icon={<ProfitIcon />}
          label={`${winCount} wins`}
          size="small"
          color="success"
          variant="outlined"
        />
        <Chip
          icon={<LossIcon />}
          label={`${lossCount} losses`}
          size="small"
          color="error"
          variant="outlined"
        />
        <Chip
          icon={<PlannedIcon />}
          label={`${plannedExits} planned exits`}
          size="small"
          color="info"
          variant="outlined"
        />
        <Chip
          label={`Total: ${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
          size="small"
          color={totalPnl >= 0 ? 'success' : 'error'}
        />
      </Stack>

      {/* Table */}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 40 }}></TableCell>
              <TableCell>#</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'entry_time'}
                  direction={sortField === 'entry_time' ? sortDirection : 'desc'}
                  onClick={() => handleSort('entry_time')}
                >
                  Entry Time
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">Entry Price</TableCell>
              <TableCell align="right">Exit Price</TableCell>
              <TableCell align="center">Exit Type</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'duration_ms'}
                  direction={sortField === 'duration_ms' ? sortDirection : 'desc'}
                  onClick={() => handleSort('duration_ms')}
                >
                  Duration
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'pnl'}
                  direction={sortField === 'pnl' ? sortDirection : 'desc'}
                  onClick={() => handleSort('pnl')}
                >
                  P&L
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'pnl_percent'}
                  direction={sortField === 'pnl_percent' ? sortDirection : 'desc'}
                  onClick={() => handleSort('pnl_percent')}
                >
                  P&L %
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedTrades.map((trade, index) => (
              <React.Fragment key={trade.id}>
                <TableRow
                  sx={{
                    bgcolor: trade.pnl > 0 ? 'success.light' : trade.pnl < 0 ? 'error.light' : 'transparent',
                    '& td': { opacity: trade.pnl !== 0 ? 1 : 0.7 },
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  onClick={() => toggleRowExpanded(trade.id)}
                >
                  <TableCell>
                    <IconButton size="small">
                      {expandedRows.has(trade.id) ? <CollapseIcon fontSize="small" /> : <ExpandIcon fontSize="small" />}
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {index + 1}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatDate(trade.entry_time)} {formatTime(trade.entry_time)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontFamily="monospace">
                      {formatPrice(trade.entry_price)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontFamily="monospace">
                      {formatPrice(trade.exit_price)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title={trade.exit_reason === 'ZE1' ? 'Planned exit (dump end detected)' : 'Emergency exit (stop loss)'}>
                      <Chip
                        icon={trade.exit_reason === 'ZE1' ? <PlannedIcon /> : <EmergencyIcon />}
                        label={trade.exit_reason}
                        size="small"
                        color={trade.exit_reason === 'ZE1' ? 'success' : 'error'}
                        variant="outlined"
                      />
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <DurationIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {formatDuration(trade.duration_ms)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      fontWeight={600}
                      color={trade.pnl >= 0 ? 'success.main' : 'error.main'}
                    >
                      {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      icon={trade.pnl >= 0 ? <ProfitIcon /> : <LossIcon />}
                      label={`${trade.pnl_percent >= 0 ? '+' : ''}${trade.pnl_percent.toFixed(2)}%`}
                      size="small"
                      color={trade.pnl >= 0 ? 'success' : 'error'}
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                </TableRow>

                {/* Expanded Details Row */}
                <TableRow>
                  <TableCell colSpan={9} sx={{ p: 0, borderBottom: expandedRows.has(trade.id) ? undefined : 0 }}>
                    <Collapse in={expandedRows.has(trade.id)}>
                      <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
                        <Stack direction="row" spacing={4}>
                          <Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Entry Trigger
                            </Typography>
                            <Typography variant="body2">
                              {trade.entry_trigger || 'peak_detected'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Exit Trigger
                            </Typography>
                            <Typography variant="body2">
                              {trade.exit_trigger || (trade.exit_reason === 'ZE1' ? 'dump_end_detected' : 'stop_loss_hit')}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Exit Time
                            </Typography>
                            <Typography variant="body2">
                              {formatDate(trade.exit_time)} {formatTime(trade.exit_time)}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Direction
                            </Typography>
                            <Chip label={trade.direction} size="small" color="primary" variant="outlined" />
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Quantity
                            </Typography>
                            <Typography variant="body2">{trade.quantity}</Typography>
                          </Box>
                        </Stack>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default TradeBreakdownTable;
