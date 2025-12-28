'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  Skeleton,
  styled,
  alpha,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import StateBadge, { StateMachineState } from './StateBadge';

// ============================================================================
// TYPES
// ============================================================================

export interface TransitionCondition {
  indicator_name: string;
  value: number;
  threshold: number;
  operator: string;
  met: boolean;
}

export interface Transition {
  timestamp: string; // ISO
  strategy_id: string;
  symbol: string;
  from_state: string;
  to_state: string;
  trigger: 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1' | 'MANUAL';
  conditions: Record<string, TransitionCondition>;
}

export interface TransitionLogProps {
  transitions: Transition[];
  maxItems?: number; // domyślnie 50
  onTransitionClick?: (transition: Transition) => void;
  isLoading?: boolean;
}

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const TransitionRow = styled(TableRow, {
  shouldForwardProp: (prop) => prop !== 'backgroundColor' && prop !== 'isExpanded'
})<{ backgroundColor?: string; isExpanded?: boolean }>(({ theme, backgroundColor, isExpanded }) => ({
  cursor: 'pointer',
  transition: 'background-color 0.2s ease',
  backgroundColor: backgroundColor || 'transparent',

  '&:hover': {
    backgroundColor: backgroundColor
      ? alpha(backgroundColor, 0.8)
      : alpha(theme.palette.action.hover, 0.08)
  },

  ...(isExpanded && {
    borderLeft: `3px solid ${theme.palette.primary.main}`
  })
}));

const ExpandButton = styled(IconButton, {
  shouldForwardProp: (prop) => prop !== 'expanded'
})<{ expanded?: boolean }>(({ expanded }) => ({
  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
  transition: 'transform 0.3s ease'
}));

const ConditionBadge = styled(Chip, {
  shouldForwardProp: (prop) => prop !== 'conditionMet'
})<{ conditionMet?: boolean }>(({ theme, conditionMet }) => ({
  margin: theme.spacing(0.5),
  fontSize: '0.75rem',
  height: '24px',
  backgroundColor: conditionMet
    ? alpha(theme.palette.success.main, 0.1)
    : alpha(theme.palette.error.main, 0.1),
  color: conditionMet ? theme.palette.success.main : theme.palette.error.main,
  border: `1px solid ${conditionMet ? theme.palette.success.main : theme.palette.error.main}`
}));

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format timestamp to HH:MM:SS
 */
function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    Logger.error('TransitionLog.formatTime', { message: 'Error formatting time', error });
    return 'Invalid time';
  }
}

/**
 * Format timestamp to full date and time
 */
function formatFullTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('en-GB', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    Logger.error('TransitionLog.formatTimestamp', { message: 'Error formatting timestamp', error });
    return 'Invalid timestamp';
  }
}

/**
 * Get background color based on transition type
 */
function getTransitionBackgroundColor(toState: string, trigger: string): string | undefined {
  // Transitions to POSITION_ACTIVE - green (success - we entered)
  if (toState === 'POSITION_ACTIVE') {
    return alpha('#4caf50', 0.15);
  }

  // Transitions to EXITED with E1 - red (emergency)
  if (toState === 'EXITED' && trigger === 'E1') {
    return alpha('#f44336', 0.15);
  }

  // Transitions to EXITED with ZE1 - blue (normal close)
  if (toState === 'EXITED' && trigger === 'ZE1') {
    return alpha('#2196f3', 0.15);
  }

  return undefined;
}

/**
 * Get trigger badge color
 */
function getTriggerColor(trigger: string): 'primary' | 'secondary' | 'error' | 'warning' | 'success' | 'info' {
  switch (trigger) {
    case 'S1': return 'warning';
    case 'O1': return 'success';
    case 'Z1': return 'info';
    case 'ZE1': return 'primary';
    case 'E1': return 'error';
    case 'MANUAL': return 'secondary';
    default: return 'secondary';
  }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * Skeleton loader for transition rows
 */
const TransitionSkeleton: React.FC = () => (
  <>
    {[...Array(5)].map((_, index) => (
      <TableRow key={index}>
        <TableCell><Skeleton width={20} /></TableCell>
        <TableCell><Skeleton width={70} /></TableCell>
        <TableCell>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Skeleton width={80} height={32} />
            <Skeleton width={20} height={32} />
            <Skeleton width={80} height={32} />
          </Box>
        </TableCell>
        <TableCell><Skeleton width={40} /></TableCell>
        <TableCell><Skeleton width={80} /></TableCell>
      </TableRow>
    ))}
  </>
);

/**
 * Empty state when no transitions
 */
const EmptyState: React.FC = () => (
  <TableRow>
    <TableCell colSpan={5}>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          py: 6
        }}
      >
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No transitions yet
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Transition history will appear here once the state machine starts processing
        </Typography>
      </Box>
    </TableCell>
  </TableRow>
);

/**
 * Expanded row details showing conditions
 */
interface TransitionDetailsProps {
  transition: Transition;
}

const TransitionDetails: React.FC<TransitionDetailsProps> = ({ transition }) => {
  const conditionEntries = Object.entries(transition.conditions);

  return (
    <TableRow>
      <TableCell colSpan={5} sx={{ py: 2, backgroundColor: alpha('#000', 0.02) }}>
        <Box sx={{ px: 2 }}>
          {/* Header Info */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Full Timestamp:</strong> {formatFullTimestamp(transition.timestamp)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <strong>Strategy ID:</strong> {transition.strategy_id}
            </Typography>
          </Box>

          {/* Conditions */}
          <Typography variant="subtitle2" gutterBottom>
            Trigger Conditions:
          </Typography>

          {conditionEntries.length === 0 ? (
            <Typography variant="body2" color="text.disabled" sx={{ fontStyle: 'italic' }}>
              No conditions data available
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
              {conditionEntries.map(([key, condition]) => {
                const icon = condition.met ? (
                  <CheckCircleIcon sx={{ fontSize: 16 }} />
                ) : (
                  <CancelIcon sx={{ fontSize: 16 }} />
                );

                const label = `${condition.indicator_name}: ${condition.value.toFixed(2)} ${condition.operator} ${condition.threshold.toFixed(2)}`;

                return (
                  <ConditionBadge
                    key={key}
                    label={label}
                    icon={icon}
                    conditionMet={condition.met}
                    size="small"
                  />
                );
              })}
            </Box>
          )}
        </Box>
      </TableCell>
    </TableRow>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const TransitionLog: React.FC<TransitionLogProps> = ({
  transitions,
  maxItems = 50,
  onTransitionClick,
  isLoading = false
}) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevTransitionsLength = useRef<number>(transitions.length);

  // Auto-scroll to top when new transition arrives
  useEffect(() => {
    if (transitions.length > prevTransitionsLength.current && containerRef.current) {
      containerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    prevTransitionsLength.current = transitions.length;
  }, [transitions.length]);

  // Limit transitions to maxItems
  const displayTransitions = transitions.slice(0, maxItems);

  const handleRowClick = (transition: Transition, index: number) => {
    // Toggle expansion
    setExpandedIndex(expandedIndex === index ? null : index);

    // Call optional callback
    if (onTransitionClick) {
      onTransitionClick(transition);
    }
  };

  return (
    <Paper
      elevation={2}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          backgroundColor: alpha('#000', 0.02)
        }}
      >
        <Typography variant="h6" component="h2">
          Transition Log
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {isLoading ? 'Loading...' : `Showing ${displayTransitions.length} of ${transitions.length} transitions`}
        </Typography>
      </Box>

      {/* Table */}
      <TableContainer
        ref={containerRef}
        sx={{
          flexGrow: 1,
          overflow: 'auto'
        }}
      >
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: '40px' }}></TableCell>
              <TableCell sx={{ width: '100px' }}>Time</TableCell>
              <TableCell>Transition</TableCell>
              <TableCell sx={{ width: '80px' }}>Trigger</TableCell>
              <TableCell sx={{ width: '100px' }}>Symbol</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TransitionSkeleton />
            ) : displayTransitions.length === 0 ? (
              <EmptyState />
            ) : (
              displayTransitions.map((transition, index) => {
                const isExpanded = expandedIndex === index;
                const backgroundColor = getTransitionBackgroundColor(
                  transition.to_state,
                  transition.trigger
                );

                return (
                  <React.Fragment key={`${transition.timestamp}-${index}`}>
                    <TransitionRow
                      backgroundColor={backgroundColor}
                      isExpanded={isExpanded}
                      onClick={() => handleRowClick(transition, index)}
                    >
                      {/* Expand Button */}
                      <TableCell>
                        <ExpandButton
                          expanded={isExpanded}
                          size="small"
                          aria-label="expand row"
                        >
                          <ExpandMoreIcon fontSize="small" />
                        </ExpandButton>
                      </TableCell>

                      {/* Time */}
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {formatTime(transition.timestamp)}
                        </Typography>
                      </TableCell>

                      {/* Transition (From → To) */}
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <StateBadge
                            state={transition.from_state as StateMachineState}
                            size="small"
                          />
                          <Typography variant="body2" color="text.secondary">
                            →
                          </Typography>
                          <StateBadge
                            state={transition.to_state as StateMachineState}
                            size="small"
                          />
                        </Box>
                      </TableCell>

                      {/* Trigger */}
                      <TableCell>
                        <Chip
                          label={transition.trigger}
                          color={getTriggerColor(transition.trigger)}
                          size="small"
                          sx={{ fontSize: '0.7rem', height: '22px' }}
                        />
                      </TableCell>

                      {/* Symbol */}
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {transition.symbol}
                        </Typography>
                      </TableCell>
                    </TransitionRow>

                    {/* Expanded Details */}
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        sx={{ p: 0, border: 0 }}
                      >
                        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                          <TransitionDetails transition={transition} />
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default TransitionLog;
