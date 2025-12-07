'use client';

/**
 * SessionMatrix Component (TS-02)
 * ================================
 *
 * Visual matrix showing Strategy x Symbol = Instance Count
 * Helps trader understand the session configuration at a glance.
 *
 * Features:
 * - Grid view of strategies vs symbols
 * - Shows which combinations are selected (checkmark/X)
 * - Total instance count
 * - Color-coded cells for quick scanning
 *
 * Related: docs/UI_BACKLOG.md - TS-02
 */

import React, { useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  Tooltip,
  alpha,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  GridOn as GridOnIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface SessionMatrixProps {
  strategies: string[];
  symbols: string[];
  selectedStrategies: string[];
  selectedSymbols: string[];
  mode?: 'compact' | 'full';
  showTotals?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export const SessionMatrix: React.FC<SessionMatrixProps> = ({
  strategies,
  symbols,
  selectedStrategies,
  selectedSymbols,
  mode = 'compact',
  showTotals = true,
}) => {
  // Calculate instance count
  const instanceCount = useMemo(() => {
    return selectedStrategies.length * selectedSymbols.length;
  }, [selectedStrategies, selectedSymbols]);

  // Check if a cell is active (both strategy and symbol selected)
  const isCellActive = (strategy: string, symbol: string): boolean => {
    return selectedStrategies.includes(strategy) && selectedSymbols.includes(symbol);
  };

  // Calculate totals per row (strategy)
  const strategyTotals = useMemo(() => {
    return strategies.reduce((acc, strategy) => {
      const count = selectedStrategies.includes(strategy) ? selectedSymbols.length : 0;
      acc[strategy] = count;
      return acc;
    }, {} as Record<string, number>);
  }, [strategies, selectedStrategies, selectedSymbols]);

  // Calculate totals per column (symbol)
  const symbolTotals = useMemo(() => {
    return symbols.reduce((acc, symbol) => {
      const count = selectedSymbols.includes(symbol) ? selectedStrategies.length : 0;
      acc[symbol] = count;
      return acc;
    }, {} as Record<string, number>);
  }, [symbols, selectedSymbols, selectedStrategies]);

  // Color based on instance count
  const getInstanceCountColor = (count: number) => {
    if (count === 0) return 'default';
    if (count <= 3) return 'success';
    if (count <= 6) return 'warning';
    return 'error'; // Many instances = higher risk
  };

  if (strategies.length === 0 || symbols.length === 0) {
    return (
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
          <GridOnIcon />
          <Typography variant="body2">
            Select strategies and symbols to see the session matrix
          </Typography>
        </Box>
      </Paper>
    );
  }

  // Compact mode: just show summary
  if (mode === 'compact') {
    return (
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <GridOnIcon color="primary" />
            <Typography variant="subtitle2">
              Session Matrix
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title={`${selectedStrategies.length} strategies selected`}>
              <Chip
                size="small"
                label={`${selectedStrategies.length} strategies`}
                variant="outlined"
              />
            </Tooltip>
            <Typography variant="body2" color="text.secondary">×</Typography>
            <Tooltip title={`${selectedSymbols.length} symbols selected`}>
              <Chip
                size="small"
                label={`${selectedSymbols.length} symbols`}
                variant="outlined"
              />
            </Tooltip>
            <Typography variant="body2" color="text.secondary">=</Typography>
            <Tooltip title={`Total trading instances that will be created`}>
              <Chip
                size="small"
                label={`${instanceCount} instances`}
                color={getInstanceCountColor(instanceCount)}
              />
            </Tooltip>
          </Box>
        </Box>
      </Paper>
    );
  }

  // Full mode: show complete matrix
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <GridOnIcon color="primary" />
          <Typography variant="subtitle1" fontWeight="bold">
            Session Matrix
          </Typography>
        </Box>
        <Chip
          label={`${instanceCount} total instances`}
          color={getInstanceCountColor(instanceCount)}
        />
      </Box>

      <Box sx={{ overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: 'bold',
                  bgcolor: 'grey.100',
                  position: 'sticky',
                  left: 0,
                  zIndex: 1,
                }}
              >
                Strategy \ Symbol
              </TableCell>
              {symbols.map((symbol) => (
                <TableCell
                  key={symbol}
                  align="center"
                  sx={{
                    fontWeight: 'bold',
                    bgcolor: selectedSymbols.includes(symbol)
                      ? alpha('#4caf50', 0.1)
                      : 'grey.100',
                    whiteSpace: 'nowrap',
                    fontSize: '0.75rem',
                  }}
                >
                  <Tooltip title={symbol}>
                    <span>{symbol.replace('_USDT', '').slice(0, 6)}</span>
                  </Tooltip>
                </TableCell>
              ))}
              {showTotals && (
                <TableCell
                  align="center"
                  sx={{
                    fontWeight: 'bold',
                    bgcolor: 'grey.200',
                  }}
                >
                  Total
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {strategies.map((strategy) => {
              const isStrategySelected = selectedStrategies.includes(strategy);
              return (
                <TableRow key={strategy}>
                  <TableCell
                    sx={{
                      fontWeight: 'medium',
                      bgcolor: isStrategySelected
                        ? alpha('#2196f3', 0.1)
                        : 'grey.50',
                      position: 'sticky',
                      left: 0,
                      zIndex: 1,
                      whiteSpace: 'nowrap',
                      fontSize: '0.8rem',
                    }}
                  >
                    <Tooltip title={strategy}>
                      <span>{strategy.length > 20 ? `${strategy.slice(0, 20)}...` : strategy}</span>
                    </Tooltip>
                  </TableCell>
                  {symbols.map((symbol) => {
                    const active = isCellActive(strategy, symbol);
                    return (
                      <TableCell
                        key={`${strategy}-${symbol}`}
                        align="center"
                        sx={{
                          bgcolor: active
                            ? alpha('#4caf50', 0.2)
                            : 'transparent',
                          p: 0.5,
                        }}
                      >
                        {active ? (
                          <CheckCircleIcon
                            fontSize="small"
                            sx={{ color: 'success.main' }}
                          />
                        ) : (
                          <CancelIcon
                            fontSize="small"
                            sx={{ color: 'grey.300' }}
                          />
                        )}
                      </TableCell>
                    );
                  })}
                  {showTotals && (
                    <TableCell
                      align="center"
                      sx={{
                        bgcolor: 'grey.100',
                        fontWeight: 'bold',
                      }}
                    >
                      <Chip
                        size="small"
                        label={strategyTotals[strategy]}
                        color={strategyTotals[strategy] > 0 ? 'primary' : 'default'}
                        variant={strategyTotals[strategy] > 0 ? 'filled' : 'outlined'}
                        sx={{ minWidth: 40 }}
                      />
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
            {showTotals && (
              <TableRow>
                <TableCell
                  sx={{
                    fontWeight: 'bold',
                    bgcolor: 'grey.200',
                    position: 'sticky',
                    left: 0,
                    zIndex: 1,
                  }}
                >
                  Total
                </TableCell>
                {symbols.map((symbol) => (
                  <TableCell
                    key={`total-${symbol}`}
                    align="center"
                    sx={{ bgcolor: 'grey.100' }}
                  >
                    <Chip
                      size="small"
                      label={symbolTotals[symbol]}
                      color={symbolTotals[symbol] > 0 ? 'secondary' : 'default'}
                      variant={symbolTotals[symbol] > 0 ? 'filled' : 'outlined'}
                      sx={{ minWidth: 40 }}
                    />
                  </TableCell>
                ))}
                <TableCell
                  align="center"
                  sx={{
                    bgcolor: 'grey.300',
                    fontWeight: 'bold',
                  }}
                >
                  <Chip
                    label={instanceCount}
                    color={getInstanceCountColor(instanceCount)}
                    sx={{ minWidth: 50, fontWeight: 'bold' }}
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>

      {/* Warning for high instance count */}
      {instanceCount > 6 && (
        <Box
          sx={{
            mt: 2,
            p: 1.5,
            bgcolor: alpha('#ff9800', 0.1),
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'warning.light',
          }}
        >
          <Typography variant="caption" color="warning.dark">
            <strong>Warning:</strong> {instanceCount} instances means {instanceCount} parallel
            state machines. Consider reducing symbols or strategies for easier monitoring.
          </Typography>
        </Box>
      )}

      {/* Instance explanation */}
      <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Each instance = 1 state machine tracking pump/dump for that strategy-symbol pair
        </Typography>
      </Box>
    </Paper>
  );
};

export default SessionMatrix;
