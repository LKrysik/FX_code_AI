'use client';

/**
 * Session History Page (SH-01)
 * ==============================
 *
 * List of all trading sessions with basic metrics.
 * Allows trader to review past sessions and analyze state machine performance.
 *
 * Features:
 * - Session table with date, mode, symbols, P&L, status
 * - Click row to navigate to session details
 * - Filter by status, mode, date range
 * - Sort by date, P&L
 *
 * Related:
 * - docs/UI_BACKLOG.md - SH-01
 * - /api/paper-trading/sessions - Backend endpoint
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
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { Logger } from '@/services/frontendLogService';

// ============================================================================
// TYPES
// ============================================================================

interface SessionSummary {
  session_id: string;
  strategy_id: string;
  strategy_name: string;
  symbols: string; // Comma-separated
  direction: string;
  status: string;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  initial_balance: number;
  current_balance?: number;
  total_pnl?: number;
  total_return_pct?: number;
  total_trades?: number;
  notes?: string;
}

interface SessionListResponse {
  sessions: SessionSummary[];
  count: number;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SessionHistoryPage() {
  const router = useRouter();

  // State
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  // ========================================
  // Data Loading
  // ========================================

  const loadSessions = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const params = new URLSearchParams();

      // Add filters
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (strategyFilter !== 'all') {
        params.append('strategy_id', strategyFilter);
      }

      params.append('limit', '100');

      const response = await fetch(`${apiUrl}/api/paper-trading/sessions?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to load sessions: ${response.status}`);
      }

      const result: SessionListResponse = await response.json();

      setSessions(result.sessions || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      Logger.error('SessionHistoryPage.loadSessions', 'Failed to load sessions', { error: err });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, strategyFilter]);

  // ========================================
  // Event Handlers
  // ========================================

  const handleRowClick = (sessionId: string) => {
    // TODO: Navigate to session detail page (SH-02)
    // For now, navigate to dashboard with session loaded
    router.push(`/session-history/${sessionId}`);
  };

  const handleRefresh = () => {
    loadSessions();
  };

  // SH-09: Export sessions to CSV
  const exportToCSV = () => {
    if (sessions.length === 0) return;

    // CSV header
    const headers = [
      'Session ID',
      'Strategy',
      'Symbols',
      'Direction',
      'Status',
      'Created',
      'Started',
      'Stopped',
      'Initial Balance',
      'Current Balance',
      'Total P&L',
      'Return %',
      'Total Trades',
      'Notes'
    ];

    // Convert sessions to CSV rows
    const rows = sessions.map(session => [
      session.session_id,
      session.strategy_name || session.strategy_id,
      session.symbols,
      session.direction,
      session.status,
      session.created_at,
      session.started_at || '',
      session.stopped_at || '',
      session.initial_balance?.toString() || '',
      session.current_balance?.toString() || '',
      session.total_pnl?.toFixed(2) || '',
      session.total_return_pct?.toFixed(2) || '',
      session.total_trades?.toString() || '',
      session.notes || ''
    ]);

    // Escape CSV values
    const escapeCSV = (value: string): string => {
      if (value.includes(',') || value.includes('"') || value.includes('\n')) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value;
    };

    // Build CSV content
    const csvContent = [
      headers.map(escapeCSV).join(','),
      ...rows.map(row => row.map(escapeCSV).join(','))
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `session-history-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // ========================================
  // Render Helpers
  // ========================================

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'info' | 'default' => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'stopped':
        return 'success';
      case 'running':
      case 'active':
        return 'info';
      case 'error':
      case 'failed':
        return 'error';
      case 'paused':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const formatPnL = (pnl: number | undefined): string => {
    if (pnl === undefined || pnl === null) return 'N/A';
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toFixed(2)}`;
  };

  const formatPnLPercent = (pct: number | undefined): string => {
    if (pct === undefined || pct === null) return 'N/A';
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  // Get unique strategies for filter
  const uniqueStrategies = Array.from(
    new Set(sessions.map(s => s.strategy_id))
  ).filter(Boolean);

  // ========================================
  // Render
  // ========================================

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Session History
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* SH-09: Export button */}
          <Tooltip title="Export to CSV">
            <span>
              <IconButton onClick={exportToCSV} disabled={loading || sessions.length === 0}>
                <DownloadIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Refresh sessions">
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <FilterIcon color="action" />
          <Typography variant="subtitle2" color="text.secondary">
            Filters:
          </Typography>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="stopped">Stopped</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="error">Error</MenuItem>
            </Select>
          </FormControl>

          {uniqueStrategies.length > 0 && (
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Strategy</InputLabel>
              <Select
                value={strategyFilter}
                label="Strategy"
                onChange={(e) => setStrategyFilter(e.target.value)}
              >
                <MenuItem value="all">All Strategies</MenuItem>
                {uniqueStrategies.map((strategyId) => (
                  <MenuItem key={strategyId} value={strategyId}>
                    {strategyId}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {(statusFilter !== 'all' || strategyFilter !== 'all') && (
            <Button
              size="small"
              onClick={() => {
                setStatusFilter('all');
                setStrategyFilter('all');
              }}
            >
              Clear Filters
            </Button>
          )}
        </Stack>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && !sessions.length ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : sessions.length === 0 ? (
        /* Empty State */
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Sessions Found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No trading sessions match your current filters.
            {(statusFilter !== 'all' || strategyFilter !== 'all') &&
              ' Try clearing filters.'}
          </Typography>
        </Paper>
      ) : (
        /* Session Table */
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Strategy</TableCell>
                <TableCell>Symbols</TableCell>
                <TableCell>Direction</TableCell>
                <TableCell align="right">Initial Balance</TableCell>
                <TableCell align="right">P&L</TableCell>
                <TableCell align="right">Return %</TableCell>
                <TableCell align="right">Trades</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sessions.map((session) => (
                <TableRow
                  key={session.session_id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => handleRowClick(session.session_id)}
                >
                  <TableCell>
                    <Typography variant="body2">
                      {formatDate(session.started_at || session.created_at)}
                    </Typography>
                    {session.stopped_at && (
                      <Typography variant="caption" color="text.secondary">
                        Stopped: {formatDate(session.stopped_at)}
                      </Typography>
                    )}
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {session.strategy_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {session.strategy_id}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2">
                      {session.symbols || 'N/A'}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={session.direction}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>

                  <TableCell align="right">
                    <Typography variant="body2">
                      ${session.initial_balance.toFixed(2)}
                    </Typography>
                  </TableCell>

                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={
                        (session.total_pnl ?? 0) >= 0
                          ? 'success.main'
                          : 'error.main'
                      }
                      fontWeight={500}
                    >
                      {formatPnL(session.total_pnl)}
                    </Typography>
                  </TableCell>

                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={
                        (session.total_return_pct ?? 0) >= 0
                          ? 'success.main'
                          : 'error.main'
                      }
                      fontWeight={500}
                    >
                      {formatPnLPercent(session.total_return_pct)}
                    </Typography>
                  </TableCell>

                  <TableCell align="right">
                    <Typography variant="body2">
                      {session.total_trades ?? 'N/A'}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={session.status}
                      color={getStatusColor(session.status)}
                      size="small"
                    />
                  </TableCell>

                  <TableCell align="center">
                    <Tooltip title="View Details">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(session.session_id);
                        }}
                      >
                        <ViewIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Footer Info */}
      {!loading && sessions.length > 0 && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Showing {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
