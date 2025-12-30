/**
 * State Overview Table Component (SM-01)
 * ========================================
 *
 * Displays all state machine instances with current state and duration.
 * Shows: Strategy x Symbol x STATE x Since
 *
 * Features:
 * - Real-time state updates via WebSocket
 * - Sort by state priority (POSITION_ACTIVE first)
 * - Colored row backgrounds for critical states
 * - Click to view instance details
 * - Auto-updating "since" duration
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 */

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Logger } from '@/services/frontendLogService';
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
  Button,
  CircularProgress,
  Skeleton,
  Chip,
  alpha,
  useTheme,
} from '@mui/material';
import { Visibility as ViewIcon } from '@mui/icons-material';
import StateBadge, { StateMachineState } from './StateBadge';
// BUG-008-3: Import data freshness hook for AC3/AC4 compliance
import { useDataFreshness } from '@/hooks/useDataFreshness';

// ============================================================================
// TYPES
// ============================================================================

export interface StateInstance {
  strategy_id: string;
  symbol: string;
  state: StateMachineState;
  since: string | null; // ISO timestamp
}

export interface StateOverviewTableProps {
  sessionId: string;
  instances: StateInstance[];
  onInstanceClick?: (instance: StateInstance) => void;
  isLoading?: boolean;
  // BUG-008-3: Optional timestamp for data freshness tracking (AC3, AC4)
  lastUpdateTime?: Date | number | string | null;
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * State priority for sorting (lower = higher priority)
 * Story 1A-4: Updated to include all states from centralized vocabulary
 */
const STATE_PRIORITY: Record<StateMachineState, number> = {
  POSITION_ACTIVE: 1,
  S1: 2, // Signal detected - high priority
  SIGNAL_DETECTED: 2, // Legacy, same as S1
  Z1: 3, // Entering position
  ZE1: 4, // Taking profit
  E1: 5, // Stopping loss - urgent but after active position
  O1: 6, // False alarm / cancelled
  ERROR: 7,
  MONITORING: 8,
  EXITED: 9,
  INACTIVE: 10,
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Calculate time elapsed since timestamp
 */
function calculateTimeSince(since: string | null): string {
  if (!since) return 'N/A';

  try {
    const start = new Date(since).getTime();
    const now = Date.now();
    const diffMs = now - start;

    if (diffMs < 0) return '0s';

    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  } catch (error) {
    Logger.error('StateOverviewTable.calculateTimeSince', { message: 'Error calculating time since', error });
    return 'N/A';
  }
}

/**
 * Sort instances by state priority
 */
function sortInstances(instances: StateInstance[]): StateInstance[] {
  return [...instances].sort((a, b) => {
    const priorityDiff = STATE_PRIORITY[a.state] - STATE_PRIORITY[b.state];
    if (priorityDiff !== 0) return priorityDiff;

    // Secondary sort: by strategy_id
    const strategyDiff = a.strategy_id.localeCompare(b.strategy_id);
    if (strategyDiff !== 0) return strategyDiff;

    // Tertiary sort: by symbol
    return a.symbol.localeCompare(b.symbol);
  });
}

/**
 * Get row background color based on state
 */
function getRowBackgroundColor(state: StateMachineState, theme: any): string {
  switch (state) {
    case 'POSITION_ACTIVE':
      return alpha(theme.palette.error.main, 0.08);
    case 'SIGNAL_DETECTED':
      return alpha(theme.palette.warning.main, 0.08);
    default:
      return 'transparent';
  }
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

const LoadingSkeleton: React.FC = () => (
  <TableBody>
    {[1, 2, 3, 4, 5].map((i) => (
      <TableRow key={i}>
        <TableCell><Skeleton variant="text" width="80%" /></TableCell>
        <TableCell><Skeleton variant="text" width="60%" /></TableCell>
        <TableCell><Skeleton variant="rectangular" width={100} height={24} /></TableCell>
        <TableCell><Skeleton variant="text" width="50%" /></TableCell>
        <TableCell><Skeleton variant="rectangular" width={60} height={32} /></TableCell>
      </TableRow>
    ))}
  </TableBody>
);

// ============================================================================
// TIME DISPLAY COMPONENT
// ============================================================================

interface TimeSinceProps {
  since: string | null;
}

const TimeSince: React.FC<TimeSinceProps> = ({ since }) => {
  const [timeDisplay, setTimeDisplay] = useState<string>(calculateTimeSince(since));

  useEffect(() => {
    if (!since) {
      setTimeDisplay('N/A');
      return;
    }

    // Update every second
    const interval = setInterval(() => {
      setTimeDisplay(calculateTimeSince(since));
    }, 1000);

    return () => clearInterval(interval);
  }, [since]);

  return (
    <Typography variant="body2" color="text.secondary">
      {timeDisplay}
    </Typography>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const StateOverviewTable: React.FC<StateOverviewTableProps> = ({
  sessionId,
  instances,
  onInstanceClick,
  isLoading = false,
  lastUpdateTime,
}) => {
  const theme = useTheme();

  // BUG-008-3: Use centralized data freshness hook for AC3/AC4 compliance
  const { formattedAge, isStale, isVeryStale, opacity } = useDataFreshness(lastUpdateTime);

  // Sort instances by priority
  const sortedInstances = useMemo(() => sortInstances(instances), [instances]);

  // ========================================
  // Render
  // ========================================

  return (
    <Box>
      {/* Header with freshness indicator - BUG-008-3 AC3/AC4 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">State Machine Overview</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {lastUpdateTime && (
            <>
              <Typography
                variant="caption"
                color={isStale ? 'warning.main' : 'text.secondary'}
                sx={{ fontWeight: isStale ? 500 : 400 }}
              >
                {formattedAge}
              </Typography>
              {isVeryStale && (
                <Chip
                  label="STALE"
                  size="small"
                  color="warning"
                  variant="outlined"
                  sx={{ height: 20, fontSize: '0.65rem', fontWeight: 'bold' }}
                />
              )}
            </>
          )}
          <Typography variant="caption" color="text.secondary">
            Session: {sessionId}
          </Typography>
        </Box>
      </Box>

      {/* Table with opacity degradation when stale - BUG-008-3 AC4 */}
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ opacity: lastUpdateTime ? opacity : 1, transition: 'opacity 0.3s ease' }}
      >
        <Table size="small" sx={{ minWidth: 650 }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Strategy</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Symbol</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>State</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Since</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }} align="center">Action</TableCell>
            </TableRow>
          </TableHead>

          {/* Loading State */}
          {isLoading && instances.length === 0 && <LoadingSkeleton />}

          {/* Data Rows */}
          {!isLoading && sortedInstances.length > 0 && (
            <TableBody>
              {sortedInstances.map((instance, index) => {
                const rowKey = `${instance.strategy_id}-${instance.symbol}-${index}`;
                const rowBgColor = getRowBackgroundColor(instance.state, theme);

                return (
                  <TableRow
                    key={rowKey}
                    hover
                    sx={{
                      backgroundColor: rowBgColor,
                      '&:hover': {
                        backgroundColor:
                          rowBgColor === 'transparent'
                            ? alpha(theme.palette.action.hover, 0.04)
                            : alpha(rowBgColor, 1.5),
                      },
                      cursor: onInstanceClick ? 'pointer' : 'default',
                    }}
                    onClick={() => onInstanceClick?.(instance)}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {instance.strategy_id}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {instance.symbol}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <StateBadge
                        state={instance.state}
                        since={instance.since ?? undefined}
                        size="small"
                        showDuration={false}
                      />
                    </TableCell>

                    <TableCell>
                      <TimeSince since={instance.since} />
                    </TableCell>

                    <TableCell align="center">
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<ViewIcon />}
                        onClick={(e) => {
                          e.stopPropagation();
                          onInstanceClick?.(instance);
                        }}
                        sx={{ textTransform: 'none' }}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          )}

          {/* Empty State */}
          {!isLoading && sortedInstances.length === 0 && (
            <TableBody>
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No active instances
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    State machines will appear here when strategies are running
                  </Typography>
                </TableCell>
              </TableRow>
            </TableBody>
          )}
        </Table>
      </TableContainer>

      {/* Footer */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Showing {sortedInstances.length} instance{sortedInstances.length !== 1 ? 's' : ''}
        </Typography>
        {isLoading && sortedInstances.length > 0 && (
          <CircularProgress size={16} />
        )}
      </Box>
    </Box>
  );
};

export default StateOverviewTable;
