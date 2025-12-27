/**
 * Transition Timeline Component (SH-04)
 * =====================================
 *
 * Visual timeline showing state machine transitions during a session.
 * Displays transitions as connected nodes on a horizontal/vertical timeline.
 *
 * Features:
 * - Visual timeline with state nodes
 * - Color-coded states (MONITORING=blue, SIGNAL_DETECTED=yellow, POSITION_ACTIVE=green, etc.)
 * - Time labels and duration between transitions
 * - Hover tooltips with transition details
 * - Expandable node details
 * - Zoom/scroll for long sessions
 *
 * Related: docs/UI_BACKLOG.md (SH-04)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tooltip,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Collapse,
  Divider,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
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
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  ViewList as VerticalIcon,
  ViewModule as HorizontalIcon,
  PlayArrow as TransitionIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface StateTransition {
  id: string;
  timestamp: string;
  from_state: string;
  to_state: string;
  trigger: string;
  trigger_values?: Record<string, number | string>;
  duration_in_state_ms?: number;
}

export interface TransitionTimelineProps {
  sessionId: string;
  transitions?: StateTransition[];
  orientation?: 'vertical' | 'horizontal';
  height?: number;
}

// ============================================================================
// State Colors
// ============================================================================

const STATE_COLORS: Record<string, string> = {
  MONITORING: '#2196f3', // Blue
  SIGNAL_DETECTED: '#ff9800', // Orange
  POSITION_ACTIVE: '#4caf50', // Green
  POSITION_CLOSING: '#9c27b0', // Purple
  COOLDOWN: '#607d8b', // Grey
  STOPPED: '#f44336', // Red
  ERROR: '#f44336', // Red
  IDLE: '#9e9e9e', // Grey
};

const STATE_LABELS: Record<string, string> = {
  MONITORING: 'Monitoring',
  SIGNAL_DETECTED: 'S1 Detected',
  POSITION_ACTIVE: 'In Position',
  POSITION_CLOSING: 'Closing',
  COOLDOWN: 'Cooldown',
  STOPPED: 'Stopped',
  ERROR: 'Error',
  IDLE: 'Idle',
};

// ============================================================================
// Component
// ============================================================================

export const TransitionTimeline: React.FC<TransitionTimelineProps> = ({
  sessionId,
  transitions: propTransitions,
  orientation = 'vertical',
  height = 400,
}) => {
  const [transitions, setTransitions] = useState<StateTransition[]>(propTransitions || []);
  const [loading, setLoading] = useState(!propTransitions);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [displayOrientation, setDisplayOrientation] = useState<'vertical' | 'horizontal'>(orientation);
  const [zoomLevel, setZoomLevel] = useState(1);

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
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/transitions`);

        if (!response.ok) {
          throw new Error(`Failed to load transitions: ${response.status}`);
        }

        const result = await response.json();
        const data = result.data?.transitions || result.transitions || [];
        setTransitions(data);

        if (data.length === 0) {
          setError('No transitions recorded for this session');
        }
      } catch (err) {
        Logger.error('TransitionTimeline.loadTransitions', 'Failed to load transitions', { error: err });
        setError('Failed to load transition data');
      } finally {
        setLoading(false);
      }
    };

    loadTransitions();
  }, [sessionId, propTransitions]);

  // ========================================
  // Handlers
  // ========================================

  const toggleNodeExpanded = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 2));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.25, 0.5));
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
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStateColor = (state: string): string => {
    return STATE_COLORS[state] || '#9e9e9e';
  };

  const getStateLabel = (state: string): string => {
    return STATE_LABELS[state] || state;
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 3, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading transitions...
        </Typography>
      </Paper>
    );
  }

  if (error && transitions.length === 0) {
    return (
      <Paper sx={{ p: 3, height }}>
        <Alert severity="info">{error}</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={500}>
          State Transition Timeline
        </Typography>

        <Stack direction="row" spacing={1} alignItems="center">
          <Chip
            label={`${transitions.length} transitions`}
            size="small"
            variant="outlined"
          />

          {/* Zoom Controls */}
          <IconButton size="small" onClick={handleZoomOut} disabled={zoomLevel <= 0.5}>
            <ZoomOutIcon fontSize="small" />
          </IconButton>
          <Typography variant="caption" sx={{ minWidth: 40, textAlign: 'center' }}>
            {Math.round(zoomLevel * 100)}%
          </Typography>
          <IconButton size="small" onClick={handleZoomIn} disabled={zoomLevel >= 2}>
            <ZoomInIcon fontSize="small" />
          </IconButton>

          {/* Orientation Toggle */}
          <ToggleButtonGroup
            value={displayOrientation}
            exclusive
            onChange={(_, value) => value && setDisplayOrientation(value)}
            size="small"
          >
            <ToggleButton value="vertical">
              <VerticalIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="horizontal">
              <HorizontalIcon fontSize="small" />
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Timeline Content */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          transform: `scale(${zoomLevel})`,
          transformOrigin: 'top left',
        }}
      >
        {displayOrientation === 'vertical' ? (
          <Timeline position="alternate">
            {transitions.map((transition, index) => (
              <TimelineItem key={transition.id || index}>
                <TimelineOppositeContent sx={{ m: 'auto 0' }}>
                  <Typography variant="caption" color="text.secondary">
                    {formatTime(transition.timestamp)}
                  </Typography>
                  {transition.duration_in_state_ms && (
                    <Typography variant="caption" display="block" color="text.disabled">
                      ({formatDuration(transition.duration_in_state_ms)})
                    </Typography>
                  )}
                </TimelineOppositeContent>

                <TimelineSeparator>
                  <TimelineConnector sx={{ bgcolor: getStateColor(transition.from_state) }} />
                  <Tooltip
                    title={`${getStateLabel(transition.from_state)} → ${getStateLabel(transition.to_state)}`}
                    arrow
                  >
                    <TimelineDot
                      sx={{
                        bgcolor: getStateColor(transition.to_state),
                        cursor: 'pointer',
                        transition: 'transform 0.2s',
                        '&:hover': { transform: 'scale(1.2)' },
                      }}
                      onClick={() => toggleNodeExpanded(transition.id || String(index))}
                    >
                      <TransitionIcon fontSize="small" />
                    </TimelineDot>
                  </Tooltip>
                  {index < transitions.length - 1 && (
                    <TimelineConnector sx={{ bgcolor: getStateColor(transition.to_state) }} />
                  )}
                </TimelineSeparator>

                <TimelineContent sx={{ py: '12px', px: 2 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: 'background.default',
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography variant="body2" fontWeight={500}>
                      {getStateLabel(transition.to_state)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Trigger: {transition.trigger}
                    </Typography>

                    {/* Expandable Details */}
                    <Collapse in={expandedNodes.has(transition.id || String(index))}>
                      <Box sx={{ mt: 1, pt: 1, borderTop: '1px dashed', borderColor: 'divider' }}>
                        <Typography variant="caption" display="block" color="text.secondary">
                          From: {getStateLabel(transition.from_state)}
                        </Typography>
                        {transition.trigger_values && Object.keys(transition.trigger_values).length > 0 && (
                          <Box sx={{ mt: 0.5 }}>
                            <Typography variant="caption" fontWeight={500}>
                              Trigger Values:
                            </Typography>
                            {Object.entries(transition.trigger_values).map(([key, value]) => (
                              <Typography key={key} variant="caption" display="block" sx={{ pl: 1 }}>
                                {key}: {typeof value === 'number' ? value.toFixed(4) : value}
                              </Typography>
                            ))}
                          </Box>
                        )}
                      </Box>
                    </Collapse>

                    <IconButton
                      size="small"
                      onClick={() => toggleNodeExpanded(transition.id || String(index))}
                      sx={{ mt: 0.5 }}
                    >
                      {expandedNodes.has(transition.id || String(index)) ? (
                        <CollapseIcon fontSize="small" />
                      ) : (
                        <ExpandIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Box>
                </TimelineContent>
              </TimelineItem>
            ))}
          </Timeline>
        ) : (
          /* Horizontal Timeline */
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              overflowX: 'auto',
              pb: 2,
              minHeight: 150,
            }}
          >
            {transitions.map((transition, index) => (
              <React.Fragment key={transition.id || index}>
                {/* Connector Line */}
                {index > 0 && (
                  <Box
                    sx={{
                      width: 60,
                      height: 4,
                      bgcolor: getStateColor(transition.from_state),
                      flexShrink: 0,
                    }}
                  />
                )}

                {/* Node */}
                <Tooltip
                  title={
                    <Box>
                      <Typography variant="body2">
                        {getStateLabel(transition.from_state)} → {getStateLabel(transition.to_state)}
                      </Typography>
                      <Typography variant="caption">
                        Trigger: {transition.trigger}
                      </Typography>
                      <br />
                      <Typography variant="caption">
                        Time: {formatTime(transition.timestamp)}
                      </Typography>
                    </Box>
                  }
                  arrow
                >
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      flexShrink: 0,
                      cursor: 'pointer',
                      '&:hover .node-dot': { transform: 'scale(1.2)' },
                    }}
                    onClick={() => toggleNodeExpanded(transition.id || String(index))}
                  >
                    <Box
                      className="node-dot"
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        bgcolor: getStateColor(transition.to_state),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        transition: 'transform 0.2s',
                        boxShadow: 2,
                      }}
                    >
                      <TransitionIcon fontSize="small" />
                    </Box>
                    <Typography
                      variant="caption"
                      sx={{ mt: 0.5, textAlign: 'center', maxWidth: 80 }}
                    >
                      {getStateLabel(transition.to_state)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatTime(transition.timestamp)}
                    </Typography>
                  </Box>
                </Tooltip>
              </React.Fragment>
            ))}
          </Box>
        )}
      </Box>

      {/* Legend */}
      <Divider sx={{ my: 1 }} />
      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ pt: 1 }}>
        {Object.entries(STATE_COLORS).slice(0, 5).map(([state, color]) => (
          <Chip
            key={state}
            label={getStateLabel(state)}
            size="small"
            sx={{
              bgcolor: color,
              color: 'white',
              fontSize: '0.65rem',
            }}
          />
        ))}
      </Stack>
    </Paper>
  );
};

export default TransitionTimeline;
