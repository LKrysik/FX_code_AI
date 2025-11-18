/**
 * Signal History Panel Component
 * ================================
 *
 * Displays full signal history with filtering and detailed view.
 *
 * Features:
 * - Filter by signal type (S1, Z1, ZE1, E1)
 * - Filter by triggered status
 * - Filter by symbol
 * - Click to view detailed signal information
 * - Shows indicator values and conditions
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  KeyboardArrowDown as ExpandMoreIcon,
  KeyboardArrowUp as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface SignalHistoryItem {
  signal_id: string;
  strategy_id: string;
  symbol: string;
  session_id: string;
  signal_type: string;
  timestamp: string;
  triggered: boolean;
  action: string;
  confidence?: number | null;
  conditions_met: Record<string, any>;
  indicator_values: Record<string, any>;
  metadata: Record<string, any>;
}

export interface SignalHistoryPanelProps {
  sessionId: string | null;
  symbol?: string; // Optional symbol filter
  refreshInterval?: number; // Auto-refresh interval in ms
  isActive?: boolean; // Whether panel is currently visible (controls auto-refresh)
}

// ============================================================================
// Component
// ============================================================================

export const SignalHistoryPanel: React.FC<SignalHistoryPanelProps> = ({
  sessionId,
  symbol: symbolFilter,
  refreshInterval = 5000,
  isActive = true,
}) => {
  // ========================================
  // State
  // ========================================

  const [signals, setSignals] = useState<SignalHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('all');
  const [triggeredFilter, setTriggeredFilter] = useState<string>('all');

  // Expanded rows for detailed view
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // ========================================
  // Data Loading
  // ========================================

  const loadSignals = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      // Build query parameters
      const params = new URLSearchParams({
        session_id: sessionId,
        limit: '100',
      });

      if (symbolFilter) {
        params.append('symbol', symbolFilter);
      }

      if (signalTypeFilter !== 'all') {
        params.append('signal_type', signalTypeFilter);
      }

      if (triggeredFilter !== 'all') {
        params.append('triggered', triggeredFilter);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/signals/history?${params}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load signals: ${response.statusText}`);
      }

      const result = await response.json();
      const data = result.data || result;

      setSignals(data.signals || []);
    } catch (err: any) {
      console.error('Failed to load signal history:', err);
      setError(err.message || 'Failed to load signal history');
    } finally {
      setLoading(false);
    }
  }, [sessionId, symbolFilter, signalTypeFilter, triggeredFilter]);

  // ========================================
  // Effects
  // ========================================

  // Initial load
  useEffect(() => {
    if (sessionId) {
      loadSignals();
    }
  }, [sessionId, signalTypeFilter, triggeredFilter, loadSignals]);

  // Auto-refresh (only when panel is active)
  useEffect(() => {
    if (!refreshInterval || !sessionId || !isActive) return;

    const intervalId = setInterval(() => {
      loadSignals();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [refreshInterval, sessionId, isActive, loadSignals]);

  // ========================================
  // Handlers
  // ========================================

  const toggleRowExpansion = (signalId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(signalId)) {
      newExpanded.delete(signalId);
    } else {
      newExpanded.add(signalId);
    }
    setExpandedRows(newExpanded);
  };

  const getSignalTypeColor = (type: string): 'warning' | 'success' | 'info' | 'error' | 'default' => {
    switch (type) {
      case 'S1':
        return 'warning'; // Entry - Yellow
      case 'Z1':
        return 'success'; // Zone - Green
      case 'ZE1':
        return 'info'; // Zone Exit - Blue
      case 'E1':
        return 'error'; // Exit - Red
      default:
        return 'default';
    }
  };

  const getActionColor = (action: string): 'success' | 'error' | 'default' => {
    if (action === 'BUY') return 'success';
    if (action === 'SELL') return 'error';
    return 'default';
  };

  // ========================================
  // Render
  // ========================================

  if (!sessionId) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Start a session to view signal history
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">📊 Signal History</Typography>
        <Button variant="outlined" size="small" onClick={loadSignals} disabled={loading}>
          Refresh
        </Button>
      </Box>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Signal Type</InputLabel>
          <Select
            value={signalTypeFilter}
            label="Signal Type"
            onChange={(e) => setSignalTypeFilter(e.target.value)}
          >
            <MenuItem value="all">All Types</MenuItem>
            <MenuItem value="S1">S1 - Entry</MenuItem>
            <MenuItem value="Z1">Z1 - Zone</MenuItem>
            <MenuItem value="ZE1">ZE1 - Zone Exit</MenuItem>
            <MenuItem value="E1">E1 - Exit</MenuItem>
            <MenuItem value="O1">O1 - Override</MenuItem>
            <MenuItem value="EMERGENCY">EMERGENCY</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Triggered</InputLabel>
          <Select
            value={triggeredFilter}
            label="Triggered"
            onChange={(e) => setTriggeredFilter(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="true">✅ Triggered</MenuItem>
            <MenuItem value="false">❌ Not Triggered</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && signals.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Empty State */}
      {!loading && signals.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          No signals found matching filters
        </Typography>
      )}

      {/* Signal Table */}
      {signals.length > 0 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width={50}></TableCell>
                <TableCell>Timestamp</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Triggered</TableCell>
                <TableCell>Strategy</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {signals.map((signal) => (
                <React.Fragment key={signal.signal_id}>
                  {/* Main Row */}
                  <TableRow
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => toggleRowExpansion(signal.signal_id)}
                  >
                    <TableCell>
                      <IconButton size="small">
                        {expandedRows.has(signal.signal_id) ? (
                          <ExpandLessIcon />
                        ) : (
                          <ExpandMoreIcon />
                        )}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {new Date(signal.timestamp).toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {signal.symbol}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={signal.signal_type}
                        color={getSignalTypeColor(signal.signal_type)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={signal.action}
                        color={getActionColor(signal.action)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {signal.confidence != null
                          ? `${(signal.confidence * 100).toFixed(0)}%`
                          : 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {signal.triggered ? (
                        <CheckCircleIcon color="success" fontSize="small" />
                      ) : (
                        <CancelIcon color="error" fontSize="small" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {signal.strategy_id}
                      </Typography>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Row - Details */}
                  <TableRow>
                    <TableCell colSpan={7} sx={{ p: 0, borderBottom: 'none' }}>
                      <Collapse in={expandedRows.has(signal.signal_id)} timeout="auto" unmountOnExit>
                        <Box sx={{ p: 2, backgroundColor: 'background.default' }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Indicator Values
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <pre
                              style={{
                                fontSize: '12px',
                                overflow: 'auto',
                                backgroundColor: '#f5f5f5',
                                padding: '8px',
                                borderRadius: '4px',
                              }}
                            >
                              {JSON.stringify(signal.indicator_values, null, 2)}
                            </pre>
                          </Box>

                          <Typography variant="subtitle2" gutterBottom>
                            Conditions Met
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <pre
                              style={{
                                fontSize: '12px',
                                overflow: 'auto',
                                backgroundColor: '#f5f5f5',
                                padding: '8px',
                                borderRadius: '4px',
                              }}
                            >
                              {JSON.stringify(signal.conditions_met, null, 2)}
                            </pre>
                          </Box>

                          {signal.metadata && Object.keys(signal.metadata).length > 0 && (
                            <>
                              <Typography variant="subtitle2" gutterBottom>
                                Metadata
                              </Typography>
                              <Box>
                                <pre
                                  style={{
                                    fontSize: '12px',
                                    overflow: 'auto',
                                    backgroundColor: '#f5f5f5',
                                    padding: '8px',
                                    borderRadius: '4px',
                                  }}
                                >
                                  {JSON.stringify(signal.metadata, null, 2)}
                                </pre>
                              </Box>
                            </>
                          )}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Footer */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Showing {signals.length} signal{signals.length !== 1 ? 's' : ''}
        </Typography>
        {loading && signals.length > 0 && (
          <CircularProgress size={20} />
        )}
      </Box>
    </Box>
  );
};
