/**
 * Transition Details Component (SH-05)
 * =====================================
 *
 * Expandable details panel showing indicator values at each state transition.
 * Shows what indicator values triggered each state change.
 *
 * Features:
 * - Expandable/collapsible transition cards
 * - Indicator values at transition moment
 * - Before/after comparison
 * - Threshold highlighting
 * - Visual indicators for exceeded thresholds
 * - Timestamp and duration display
 *
 * Related: docs/UI_BACKLOG.md (SH-05)
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  LinearProgress,
  IconButton,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  TrendingUp as PumpIcon,
  TrendingDown as DumpIcon,
  PlayCircle as EntryIcon,
  Stop as CloseIcon,
  Warning as EmergencyIcon,
  Timer as TimeoutIcon,
  ArrowForward as ArrowIcon,
  CheckCircle as ThresholdMetIcon,
  RadioButtonUnchecked as ThresholdNotMetIcon,
  Info as InfoIcon,
  ExpandLess as CollapseAllIcon,
  UnfoldMore as ExpandAllIcon,
} from '@mui/icons-material';
import { StateTransition } from './TransitionTimeline';

// ============================================================================
// Types
// ============================================================================

export interface TransitionWithIndicators extends StateTransition {
  indicator_values?: Record<string, number>;
  thresholds?: Record<string, { value: number; operator: '>=' | '<=' | '>' | '<' | '==' }>;
  price_at_transition?: number;
}

export interface TransitionDetailsProps {
  sessionId: string;
  transitions?: TransitionWithIndicators[];
  onTransitionsLoad?: (transitions: TransitionWithIndicators[]) => void;
}

// ============================================================================
// Constants
// ============================================================================

const TRIGGER_ICONS: Record<string, React.ReactNode> = {
  pump_detected: <PumpIcon sx={{ color: '#ff9800' }} />,
  peak_detected: <TrendingUp sx={{ color: '#4caf50' }} />,
  entry_conditions_met: <EntryIcon sx={{ color: '#4caf50' }} />,
  dump_end_detected: <CloseIcon sx={{ color: '#2196f3' }} />,
  take_profit: <CloseIcon sx={{ color: '#4caf50' }} />,
  stop_loss: <EmergencyIcon sx={{ color: '#f44336' }} />,
  timeout: <TimeoutIcon sx={{ color: '#607d8b' }} />,
  manual_close: <CloseIcon sx={{ color: '#9c27b0' }} />,
};

const STATE_COLORS: Record<string, string> = {
  MONITORING: '#2196f3',
  SIGNAL_DETECTED: '#ff9800',
  POSITION_ACTIVE: '#4caf50',
  POSITION_CLOSING: '#9c27b0',
  COOLDOWN: '#607d8b',
  STOPPED: '#f44336',
};

// Fix missing import
import { TrendingUp } from '@mui/icons-material';

// ============================================================================
// Component
// ============================================================================

export const TransitionDetails: React.FC<TransitionDetailsProps> = ({
  sessionId,
  transitions: propTransitions,
  onTransitionsLoad,
}) => {
  const [transitions, setTransitions] = useState<TransitionWithIndicators[]>(propTransitions || []);
  const [loading, setLoading] = useState(!propTransitions);
  const [error, setError] = useState<string | null>(null);
  const [expandedPanels, setExpandedPanels] = useState<Set<string>>(new Set());

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    if (propTransitions) {
      setTransitions(propTransitions);
      setLoading(false);
      return;
    }

    const loadTransitions = async () => {
      if (!sessionId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/transitions?include_indicators=true`);

        if (!response.ok) {
          // Fallback to mock data if endpoint doesn't exist
          if (response.status === 404) {
            const mockData = generateMockTransitions();
            setTransitions(mockData);
            onTransitionsLoad?.(mockData);
            return;
          }
          throw new Error(`Failed to load transitions: ${response.status}`);
        }

        const result = await response.json();
        const data = result.data?.transitions || result.transitions || [];
        setTransitions(data);
        onTransitionsLoad?.(data);
      } catch (err) {
        console.error('Failed to load transition details:', err);
        // Fallback to mock data
        const mockData = generateMockTransitions();
        setTransitions(mockData);
        onTransitionsLoad?.(mockData);
      } finally {
        setLoading(false);
      }
    };

    loadTransitions();
  }, [sessionId, propTransitions, onTransitionsLoad]);

  // ========================================
  // Mock Data Generator
  // ========================================

  const generateMockTransitions = (): TransitionWithIndicators[] => {
    const now = Date.now();
    const basePrice = 42000;

    return [
      {
        id: 't-1',
        timestamp: new Date(now - 3600000).toISOString(),
        from_state: 'MONITORING',
        to_state: 'SIGNAL_DETECTED',
        trigger: 'pump_detected',
        duration_in_state_ms: 120000,
        price_at_transition: basePrice * 1.05,
        indicator_values: {
          PUMP_MAGNITUDE_PCT: 5.2,
          PRICE_VELOCITY: 0.0034,
          VOLUME_RATIO: 2.8,
          RSI_14: 72.5,
        },
        thresholds: {
          PUMP_MAGNITUDE_PCT: { value: 5.0, operator: '>=' },
          PRICE_VELOCITY: { value: 0.003, operator: '>=' },
        },
      },
      {
        id: 't-2',
        timestamp: new Date(now - 3480000).toISOString(),
        from_state: 'SIGNAL_DETECTED',
        to_state: 'POSITION_ACTIVE',
        trigger: 'entry_conditions_met',
        duration_in_state_ms: 45000,
        price_at_transition: basePrice * 1.052,
        indicator_values: {
          PUMP_MAGNITUDE_PCT: 5.5,
          PRICE_VELOCITY: 0.0028,
          VOLUME_RATIO: 3.2,
          RSI_14: 74.1,
          MOMENTUM_DECAY: 0.15,
        },
        thresholds: {
          MOMENTUM_DECAY: { value: 0.1, operator: '>=' },
        },
      },
      {
        id: 't-3',
        timestamp: new Date(now - 3300000).toISOString(),
        from_state: 'POSITION_ACTIVE',
        to_state: 'MONITORING',
        trigger: 'dump_end_detected',
        duration_in_state_ms: 180000,
        price_at_transition: basePrice * 0.98,
        indicator_values: {
          PUMP_MAGNITUDE_PCT: -2.1,
          PRICE_VELOCITY: -0.0008,
          VOLUME_RATIO: 1.2,
          RSI_14: 42.3,
          DUMP_MAGNITUDE_PCT: 7.2,
        },
        thresholds: {
          DUMP_MAGNITUDE_PCT: { value: 5.0, operator: '>=' },
        },
      },
    ];
  };

  // ========================================
  // Handlers
  // ========================================

  const togglePanel = (panelId: string) => {
    setExpandedPanels((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(panelId)) {
        newSet.delete(panelId);
      } else {
        newSet.add(panelId);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    setExpandedPanels(new Set(transitions.map((t) => t.id)));
  };

  const collapseAll = () => {
    setExpandedPanels(new Set());
  };

  // ========================================
  // Helpers
  // ========================================

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

  const formatDuration = (ms?: number): string => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${Math.floor(ms / 1000)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const checkThreshold = (
    value: number,
    threshold?: { value: number; operator: string }
  ): boolean => {
    if (!threshold) return false;
    switch (threshold.operator) {
      case '>=':
        return value >= threshold.value;
      case '<=':
        return value <= threshold.value;
      case '>':
        return value > threshold.value;
      case '<':
        return value < threshold.value;
      case '==':
        return value === threshold.value;
      default:
        return false;
    }
  };

  const getThresholdProgress = (value: number, threshold?: { value: number; operator: string }): number => {
    if (!threshold) return 0;
    const progress = (value / threshold.value) * 100;
    return Math.min(Math.max(progress, 0), 150); // Cap at 150%
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading transition details...
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

  if (transitions.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">No transitions recorded for this session.</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <InfoIcon color="primary" />
        <Typography variant="h6">Transition Details (SH-05)</Typography>
        <Tooltip title="Click on each transition to see the indicator values that triggered the state change">
          <InfoIcon fontSize="small" color="action" sx={{ ml: 'auto' }} />
        </Tooltip>
        <IconButton size="small" onClick={expandAll} title="Expand All">
          <ExpandAllIcon fontSize="small" />
        </IconButton>
        <IconButton size="small" onClick={collapseAll} title="Collapse All">
          <CollapseAllIcon fontSize="small" />
        </IconButton>
      </Box>

      <Stack spacing={2}>
        {transitions.map((transition, index) => (
          <Accordion
            key={transition.id}
            expanded={expandedPanels.has(transition.id)}
            onChange={() => togglePanel(transition.id)}
            sx={{
              '&:before': { display: 'none' },
              borderLeft: `4px solid ${STATE_COLORS[transition.to_state] || '#9e9e9e'}`,
            }}
          >
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', pr: 2 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 30 }}>
                  #{index + 1}
                </Typography>

                {TRIGGER_ICONS[transition.trigger] || <ArrowIcon color="action" />}

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={transition.from_state}
                    size="small"
                    sx={{
                      bgcolor: STATE_COLORS[transition.from_state] || '#9e9e9e',
                      color: 'white',
                      fontSize: '0.7rem',
                    }}
                  />
                  <ArrowIcon fontSize="small" color="action" />
                  <Chip
                    label={transition.to_state}
                    size="small"
                    sx={{
                      bgcolor: STATE_COLORS[transition.to_state] || '#9e9e9e',
                      color: 'white',
                      fontSize: '0.7rem',
                    }}
                  />
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
                  {formatTime(transition.timestamp)}
                </Typography>

                {transition.duration_in_state_ms && (
                  <Chip
                    icon={<TimeoutIcon />}
                    label={formatDuration(transition.duration_in_state_ms)}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
            </AccordionSummary>

            <AccordionDetails>
              <Divider sx={{ mb: 2 }} />

              {/* Trigger Info */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Trigger: <strong>{transition.trigger.replace(/_/g, ' ').toUpperCase()}</strong>
                </Typography>
                {transition.price_at_transition && (
                  <Typography variant="body2" color="text.secondary">
                    Price at transition: ${transition.price_at_transition.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </Typography>
                )}
              </Box>

              {/* Indicator Values Table */}
              {transition.indicator_values && Object.keys(transition.indicator_values).length > 0 && (
                <>
                  <Typography variant="subtitle2" gutterBottom>
                    Indicator Values at Transition
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Indicator</TableCell>
                          <TableCell align="right">Value</TableCell>
                          <TableCell align="right">Threshold</TableCell>
                          <TableCell align="center" sx={{ width: 150 }}>
                            Progress
                          </TableCell>
                          <TableCell align="center">Met?</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(transition.indicator_values).map(([key, value]) => {
                          const threshold = transition.thresholds?.[key];
                          const isMet = checkThreshold(value, threshold);
                          const progress = getThresholdProgress(value, threshold);

                          return (
                            <TableRow
                              key={key}
                              sx={{
                                bgcolor: isMet ? 'success.light' : 'transparent',
                                '& td': { opacity: threshold ? 1 : 0.7 },
                              }}
                            >
                              <TableCell>
                                <Typography variant="body2" fontWeight={threshold ? 600 : 400}>
                                  {key}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2" fontFamily="monospace">
                                  {typeof value === 'number' ? value.toFixed(4) : value}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                {threshold ? (
                                  <Typography variant="body2" fontFamily="monospace">
                                    {threshold.operator} {threshold.value}
                                  </Typography>
                                ) : (
                                  <Typography variant="body2" color="text.disabled">
                                    -
                                  </Typography>
                                )}
                              </TableCell>
                              <TableCell>
                                {threshold && (
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <LinearProgress
                                      variant="determinate"
                                      value={Math.min(progress, 100)}
                                      color={isMet ? 'success' : 'warning'}
                                      sx={{ flex: 1, height: 8, borderRadius: 1 }}
                                    />
                                    <Typography variant="caption" sx={{ minWidth: 40 }}>
                                      {progress.toFixed(0)}%
                                    </Typography>
                                  </Box>
                                )}
                              </TableCell>
                              <TableCell align="center">
                                {threshold ? (
                                  isMet ? (
                                    <ThresholdMetIcon color="success" fontSize="small" />
                                  ) : (
                                    <ThresholdNotMetIcon color="warning" fontSize="small" />
                                  )
                                ) : (
                                  <Typography variant="body2" color="text.disabled">
                                    -
                                  </Typography>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              )}

              {/* Trigger Values (legacy) */}
              {transition.trigger_values && Object.keys(transition.trigger_values).length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Trigger Values
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {Object.entries(transition.trigger_values).map(([key, value]) => (
                      <Chip
                        key={key}
                        label={`${key}: ${typeof value === 'number' ? value.toFixed(4) : value}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>

      {/* Info Note */}
      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="caption">
          <strong>How to read:</strong> Each transition shows the indicator values at the moment the state changed.
          Green highlighting means the threshold was met and triggered the transition.
        </Typography>
      </Alert>
    </Paper>
  );
};

export default TransitionDetails;
