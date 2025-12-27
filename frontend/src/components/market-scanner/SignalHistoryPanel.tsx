'use client';

/**
 * Signal History Panel (MS-02)
 * ============================
 *
 * Shows recent signal history for a symbol in the Market Scanner.
 * Displays what state machine signals (S1, Z1, O1, ZE1, E1) have been detected.
 *
 * Features:
 * - Timeline of recent signals
 * - Signal type badges (S1=pump detected, Z1=entry, etc.)
 * - Time since signal
 * - Outcome indicator (if entry led to profit/loss)
 * - Expandable details
 * - Mock data fallback for development
 *
 * Related: docs/UI_BACKLOG.md - MS-02
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Collapse,
  Stack,
  Divider,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
} from '@mui/lab';
import {
  FlashOn as FlashIcon,
  TrendingUp as EntryIcon,
  Timer as TimerIcon,
  ExitToApp as ExitIcon,
  Warning as EmergencyIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  History as HistoryIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

export interface SignalEvent {
  id: string;
  timestamp: string;
  signal_type: 'S1' | 'Z1' | 'O1' | 'ZE1' | 'E1';
  symbol: string;
  price_at_signal: number;
  trigger_values?: Record<string, number>;
  outcome?: 'profit' | 'loss' | 'pending' | 'timeout';
  pnl_pct?: number;
  duration_ms?: number;
  notes?: string;
}

export interface SignalHistoryPanelProps {
  symbol: string;
  maxSignals?: number;
  showOutcomes?: boolean;
}

// ============================================================================
// SIGNAL CONFIG
// ============================================================================

const SIGNAL_CONFIG: Record<string, {
  label: string;
  description: string;
  dotColor: 'warning' | 'success' | 'info' | 'error' | 'grey' | 'primary';
  chipColor: 'warning' | 'success' | 'info' | 'error' | 'default' | 'primary';
  icon: React.ReactNode;
}> = {
  S1: {
    label: 'S1 - Pump Detected',
    description: 'Pump magnitude threshold crossed. Signal detected state.',
    dotColor: 'warning',
    chipColor: 'warning',
    icon: <FlashIcon />,
  },
  Z1: {
    label: 'Z1 - Entry',
    description: 'Entry conditions met. Position opened.',
    dotColor: 'success',
    chipColor: 'success',
    icon: <EntryIcon />,
  },
  O1: {
    label: 'O1 - Timeout',
    description: 'Entry window expired without meeting Z1 conditions.',
    dotColor: 'grey',
    chipColor: 'default',
    icon: <TimerIcon />,
  },
  ZE1: {
    label: 'ZE1 - Planned Exit',
    description: 'Exit conditions met. Position closed normally.',
    dotColor: 'info',
    chipColor: 'info',
    icon: <ExitIcon />,
  },
  E1: {
    label: 'E1 - Emergency Exit',
    description: 'Emergency stop loss triggered. Position closed.',
    dotColor: 'error',
    chipColor: 'error',
    icon: <EmergencyIcon />,
  },
};

// ============================================================================
// MOCK DATA
// ============================================================================

const generateMockSignalHistory = (symbol: string): SignalEvent[] => {
  const now = Date.now();
  const signals: SignalEvent[] = [];

  // Generate a sequence that makes trading sense
  // Typical flow: S1 -> Z1 -> ZE1 or S1 -> O1 or S1 -> Z1 -> E1

  // Signal sequence 1: S1 -> Z1 -> ZE1 (successful trade)
  signals.push({
    id: `${symbol}-sig-1`,
    timestamp: new Date(now - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    signal_type: 'S1',
    symbol,
    price_at_signal: 45230.50,
    trigger_values: { PUMP_MAGNITUDE_PCT: 5.2, PRICE_VELOCITY: 0.8 },
    notes: 'Pump started - magnitude above threshold',
  });

  signals.push({
    id: `${symbol}-sig-2`,
    timestamp: new Date(now - 1.9 * 60 * 60 * 1000).toISOString(),
    signal_type: 'Z1',
    symbol,
    price_at_signal: 45890.00,
    trigger_values: { PEAK_DETECTED: 1.0, VELOCITY_DECLINING: 1.0 },
    outcome: 'profit',
    pnl_pct: 2.3,
    notes: 'Peak detected - SHORT entry',
  });

  signals.push({
    id: `${symbol}-sig-3`,
    timestamp: new Date(now - 1.5 * 60 * 60 * 1000).toISOString(),
    signal_type: 'ZE1',
    symbol,
    price_at_signal: 44830.00,
    trigger_values: { TARGET_REACHED: 1.0 },
    outcome: 'profit',
    pnl_pct: 2.3,
    duration_ms: 24 * 60 * 1000, // 24 minutes
    notes: 'Target reached - profitable exit',
  });

  // Signal sequence 2: S1 -> O1 (timeout)
  signals.push({
    id: `${symbol}-sig-4`,
    timestamp: new Date(now - 45 * 60 * 1000).toISOString(), // 45 min ago
    signal_type: 'S1',
    symbol,
    price_at_signal: 46100.00,
    trigger_values: { PUMP_MAGNITUDE_PCT: 4.8, PRICE_VELOCITY: 0.5 },
    notes: 'Weak pump signal',
  });

  signals.push({
    id: `${symbol}-sig-5`,
    timestamp: new Date(now - 30 * 60 * 1000).toISOString(),
    signal_type: 'O1',
    symbol,
    price_at_signal: 46050.00,
    trigger_values: { ENTRY_WINDOW_EXPIRED: 1.0 },
    outcome: 'timeout',
    notes: 'Entry window expired - no clear peak detected',
  });

  // Signal sequence 3: S1 -> Z1 -> E1 (emergency exit)
  signals.push({
    id: `${symbol}-sig-6`,
    timestamp: new Date(now - 10 * 60 * 1000).toISOString(), // 10 min ago
    signal_type: 'S1',
    symbol,
    price_at_signal: 46500.00,
    trigger_values: { PUMP_MAGNITUDE_PCT: 8.5, PRICE_VELOCITY: 1.2 },
    notes: 'Strong pump detected',
  });

  signals.push({
    id: `${symbol}-sig-7`,
    timestamp: new Date(now - 8 * 60 * 1000).toISOString(),
    signal_type: 'Z1',
    symbol,
    price_at_signal: 47200.00,
    trigger_values: { PEAK_DETECTED: 1.0, VELOCITY_DECLINING: 0.8 },
    outcome: 'pending',
    notes: 'Peak detected - SHORT entry (active)',
  });

  return signals.sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
};

// ============================================================================
// COMPONENT
// ============================================================================

export function SignalHistoryPanel({
  symbol,
  maxSignals = 10,
  showOutcomes = true,
}: SignalHistoryPanelProps) {
  const [signals, setSignals] = useState<SignalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSignals, setExpandedSignals] = useState<Set<string>>(new Set());

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    const loadSignalHistory = async () => {
      if (!symbol) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/market-scanner/${symbol}/signals`);

        if (response.ok) {
          const result = await response.json();
          const signalData = result.signals || [];
          setSignals(signalData.slice(0, maxSignals));
        } else if (response.status === 404) {
          // Endpoint doesn't exist yet, use mock data
          Logger.info('SignalHistoryPanel.loadSignalHistory', 'API endpoint not available, using mock data', { symbol });
          setSignals(generateMockSignalHistory(symbol).slice(0, maxSignals));
        } else {
          throw new Error(`API error: ${response.status}`);
        }
      } catch (err) {
        Logger.error('SignalHistoryPanel.loadSignalHistory', 'Failed to load signal history', { error: err, symbol });
        // Use mock data as fallback
        setSignals(generateMockSignalHistory(symbol).slice(0, maxSignals));
      } finally {
        setLoading(false);
      }
    };

    loadSignalHistory();
  }, [symbol, maxSignals]);

  // ========================================
  // Handlers
  // ========================================

  const toggleExpanded = (signalId: string) => {
    setExpandedSignals(prev => {
      const next = new Set(prev);
      if (next.has(signalId)) {
        next.delete(signalId);
      } else {
        next.add(signalId);
      }
      return next;
    });
  };

  const formatTimeAgo = (timestamp: string): string => {
    const now = Date.now();
    const then = new Date(timestamp).getTime();
    const diffMs = now - then;

    const minutes = Math.floor(diffMs / (1000 * 60));
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const formatDuration = (ms: number): string => {
    const minutes = Math.floor(ms / (1000 * 60));
    const hours = Math.floor(ms / (1000 * 60 * 60));

    if (minutes < 60) return `${minutes}m`;
    return `${hours}h ${minutes % 60}m`;
  };

  const getOutcomeChip = (signal: SignalEvent) => {
    if (!signal.outcome) return null;

    switch (signal.outcome) {
      case 'profit':
        return (
          <Chip
            label={`+${signal.pnl_pct?.toFixed(1)}%`}
            size="small"
            color="success"
            variant="filled"
          />
        );
      case 'loss':
        return (
          <Chip
            label={`${signal.pnl_pct?.toFixed(1)}%`}
            size="small"
            color="error"
            variant="filled"
          />
        );
      case 'pending':
        return (
          <Chip
            label="Active"
            size="small"
            color="info"
            variant="outlined"
          />
        );
      case 'timeout':
        return (
          <Chip
            label="Timeout"
            size="small"
            color="default"
            variant="outlined"
          />
        );
      default:
        return null;
    }
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Box sx={{ py: 2 }}>
        <LinearProgress />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
          Loading signal history...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (signals.length === 0) {
    return (
      <Box sx={{ py: 2, textAlign: 'center' }}>
        <HistoryIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
        <Typography variant="body2" color="text.secondary">
          No signal history for {symbol}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Signals will appear here when the state machine detects pump activity.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HistoryIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" color="text.secondary">
            Signal History
          </Typography>
          <Chip label={signals.length} size="small" />
        </Box>
        <Tooltip title="Signals are generated by the state machine when pump/dump conditions are detected">
          <InfoIcon fontSize="small" color="action" />
        </Tooltip>
      </Box>

      {/* Timeline */}
      <Timeline sx={{ p: 0, m: 0 }}>
        {signals.map((signal, index) => {
          const config = SIGNAL_CONFIG[signal.signal_type];
          const isExpanded = expandedSignals.has(signal.id);
          const isLast = index === signals.length - 1;

          return (
            <TimelineItem key={signal.id} sx={{ minHeight: 'auto' }}>
              <TimelineOppositeContent sx={{ flex: 0.3, py: 1, px: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatTimeAgo(signal.timestamp)}
                </Typography>
              </TimelineOppositeContent>

              <TimelineSeparator>
                <TimelineDot color={config.dotColor} sx={{ my: 0.5 }}>
                  {config.icon}
                </TimelineDot>
                {!isLast && <TimelineConnector />}
              </TimelineSeparator>

              <TimelineContent sx={{ py: 1, px: 1 }}>
                <Paper
                  elevation={isExpanded ? 2 : 0}
                  sx={{
                    p: 1,
                    cursor: 'pointer',
                    bgcolor: isExpanded ? 'background.paper' : 'transparent',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  onClick={() => toggleExpanded(signal.id)}
                >
                  {/* Signal Header */}
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={signal.signal_type}
                        size="small"
                        color={config.chipColor}
                        variant="filled"
                      />
                      {showOutcomes && getOutcomeChip(signal)}
                    </Box>
                    <IconButton size="small">
                      {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                    </IconButton>
                  </Box>

                  {/* Signal Price */}
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Price: ${signal.price_at_signal.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </Typography>

                  {/* Expanded Details */}
                  <Collapse in={isExpanded}>
                    <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid', borderColor: 'divider' }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                        {config.description}
                      </Typography>

                      {signal.notes && (
                        <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic' }}>
                          {signal.notes}
                        </Typography>
                      )}

                      {/* Trigger Values */}
                      {signal.trigger_values && Object.keys(signal.trigger_values).length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            Trigger Values:
                          </Typography>
                          <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mt: 0.5 }}>
                            {Object.entries(signal.trigger_values).map(([key, value]) => (
                              <Chip
                                key={key}
                                label={`${key}: ${typeof value === 'number' ? value.toFixed(2) : value}`}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                          </Stack>
                        </Box>
                      )}

                      {/* Duration if exit signal */}
                      {signal.duration_ms && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                          Trade duration: {formatDuration(signal.duration_ms)}
                        </Typography>
                      )}

                      {/* Timestamp */}
                      <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 1 }}>
                        {new Date(signal.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                  </Collapse>
                </Paper>
              </TimelineContent>
            </TimelineItem>
          );
        })}
      </Timeline>

      {/* Summary */}
      <Divider sx={{ my: 2 }} />
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Showing last {signals.length} signals
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {['S1', 'Z1', 'O1', 'ZE1', 'E1'].map(type => {
            const count = signals.filter(s => s.signal_type === type).length;
            if (count === 0) return null;
            return (
              <Chip
                key={type}
                label={`${type}: ${count}`}
                size="small"
                color={SIGNAL_CONFIG[type].chipColor}
                variant="outlined"
              />
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}

export default SignalHistoryPanel;
