'use client';

/**
 * LiquidationAlert Component - TIER 1.4
 * =====================================
 * Real-time liquidation risk monitoring for leveraged positions.
 *
 * Features:
 * - WebSocket-powered real-time updates
 * - Color-coded severity levels (CRITICAL, HIGH, MEDIUM)
 * - Distance to liquidation percentage display
 * - Toast notifications for critical warnings (<10%)
 * - Position details (symbol, side, leverage, prices)
 * - Auto-dismiss for non-critical alerts
 *
 * Warning Levels:
 * - CRITICAL (<10%): Red, immediate action required
 * - HIGH (10-20%): Orange, close monitoring needed
 * - MEDIUM (20-30%): Yellow, elevated risk
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Typography,
  IconButton,
  Collapse,
  Chip,
  Stack,
  Paper,
} from '@mui/material';
import {
  Close as CloseIcon,
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';

interface LiquidationWarning {
  session_id: string;
  symbol: string;
  position_side: 'LONG' | 'SHORT';
  leverage: number;
  entry_price: number;
  current_price: number;
  liquidation_price: number;
  distance_pct: number;
  warning_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LIQUIDATED';
  timestamp: string;
  position_amount: number;
  unrealized_pnl: number;
}

interface LiquidationAlertProps {
  sessionId?: string;  // Optional: filter by session
  enableToastNotifications?: boolean;
  autoHideDelay?: number;  // Auto-hide non-critical alerts after N milliseconds
}

export default function LiquidationAlert({
  sessionId,
  enableToastNotifications = true,
  autoHideDelay = 10000,  // 10 seconds default
}: LiquidationAlertProps) {
  const [warnings, setWarnings] = useState<Map<string, LiquidationWarning>>(new Map());
  const [dismissedWarnings, setDismissedWarnings] = useState<Set<string>>(new Set());
  const { enqueueSnackbar } = useSnackbar();

  // WebSocket connection
  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8080/ws';
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;
    let isConnecting = false;

    const connect = () => {
      if (isConnecting) return;
      isConnecting = true;

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[LiquidationAlert] WebSocket connected');
        isConnecting = false;

        // Subscribe to paper trading events (includes liquidation warnings)
        ws?.send(
          JSON.stringify({
            type: 'subscribe',
            stream: 'paper_trading',
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle liquidation warning events
          if (data.event === 'paper_trading.liquidation_warning') {
            const warning: LiquidationWarning = data;

            // Filter by session if specified
            if (sessionId && warning.session_id !== sessionId) {
              return;
            }

            // Update warnings map
            const key = `${warning.session_id}:${warning.symbol}`;
            setWarnings((prev) => {
              const updated = new Map(prev);
              updated.set(key, warning);
              return updated;
            });

            // Show toast notification for critical warnings
            if (enableToastNotifications && warning.warning_level === 'CRITICAL') {
              enqueueSnackbar(
                `CRITICAL: ${warning.symbol} position is ${warning.distance_pct.toFixed(1)}% from liquidation!`,
                {
                  variant: 'error',
                  autoHideDuration: null,  // Don't auto-hide critical warnings
                  action: (key) => (
                    <IconButton
                      size="small"
                      color="inherit"
                      onClick={() => {
                        // Close snackbar but don't dismiss the main alert
                        (window as any).closeSnackbar?.(key);
                      }}
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  ),
                }
              );
            }

            // Auto-hide non-critical warnings after delay
            if (warning.warning_level !== 'CRITICAL' && autoHideDelay > 0) {
              setTimeout(() => {
                setWarnings((prev) => {
                  const updated = new Map(prev);
                  updated.delete(key);
                  return updated;
                });
              }, autoHideDelay);
            }
          }
        } catch (error) {
          console.error('[LiquidationAlert] Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[LiquidationAlert] WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('[LiquidationAlert] WebSocket disconnected, reconnecting in 5s...');
        isConnecting = false;
        reconnectTimeout = setTimeout(connect, 5000);
      };
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, [sessionId, enableToastNotifications, autoHideDelay, enqueueSnackbar]);

  const handleDismiss = useCallback((key: string) => {
    setDismissedWarnings((prev) => new Set(prev).add(key));
    setWarnings((prev) => {
      const updated = new Map(prev);
      updated.delete(key);
      return updated;
    });
  }, []);

  // Get severity color
  const getSeverityColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
      case 'LIQUIDATED':
        return 'error';
      case 'HIGH':
        return 'warning';
      case 'MEDIUM':
        return 'info';
      default:
        return 'info';
    }
  };

  // Format price
  const formatPrice = (price: number) => {
    return price.toFixed(2);
  };

  // Format P&L
  const formatPnL = (pnl: number) => {
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toFixed(2)}`;
  };

  // Sort warnings by severity (CRITICAL first)
  const sortedWarnings = Array.from(warnings.entries()).sort(([, a], [, b]) => {
    const severityOrder = { CRITICAL: 0, LIQUIDATED: 0, HIGH: 1, MEDIUM: 2 };
    return (
      (severityOrder[a.warning_level] || 99) - (severityOrder[b.warning_level] || 99)
    );
  });

  if (sortedWarnings.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Stack spacing={1}>
        {sortedWarnings.map(([key, warning]) => {
          if (dismissedWarnings.has(key)) {
            return null;
          }

          return (
            <Collapse key={key} in={true}>
              <Alert
                severity={getSeverityColor(warning.warning_level) as any}
                icon={<WarningIcon />}
                action={
                  <IconButton
                    aria-label="close"
                    color="inherit"
                    size="small"
                    onClick={() => handleDismiss(key)}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                }
                sx={{
                  animation: warning.warning_level === 'CRITICAL' ? 'pulse 2s infinite' : 'none',
                  '@keyframes pulse': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.8 },
                  },
                }}
              >
                <AlertTitle>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="h6" component="span">
                      {warning.warning_level} LIQUIDATION RISK
                    </Typography>
                    <Chip
                      label={`${warning.distance_pct.toFixed(1)}% to liquidation`}
                      color={getSeverityColor(warning.warning_level) as any}
                      size="small"
                    />
                  </Stack>
                </AlertTitle>

                <Paper elevation={0} sx={{ p: 1, mt: 1, bgcolor: 'background.default' }}>
                  <Stack spacing={1}>
                    {/* Position Details */}
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Symbol
                        </Typography>
                        <Typography variant="body1" fontWeight="bold">
                          {warning.symbol}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Side
                        </Typography>
                        <Chip
                          label={warning.position_side}
                          color={warning.position_side === 'LONG' ? 'success' : 'error'}
                          size="small"
                          icon={
                            warning.position_side === 'LONG' ? (
                              <TrendingUpIcon />
                            ) : (
                              <TrendingDownIcon />
                            )
                          }
                        />
                      </Box>

                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Leverage
                        </Typography>
                        <Typography variant="body1" fontWeight="bold">
                          {warning.leverage}x
                        </Typography>
                      </Box>
                    </Stack>

                    {/* Price Details */}
                    <Stack direction="row" spacing={2}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Entry Price
                        </Typography>
                        <Typography variant="body2">
                          ${formatPrice(warning.entry_price)}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Current Price
                        </Typography>
                        <Typography variant="body2" fontWeight="bold">
                          ${formatPrice(warning.current_price)}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Liquidation Price
                        </Typography>
                        <Typography variant="body2" color="error">
                          ${formatPrice(warning.liquidation_price)}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Unrealized P&L
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight="bold"
                          color={warning.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
                        >
                          {formatPnL(warning.unrealized_pnl)}
                        </Typography>
                      </Box>
                    </Stack>

                    {/* Action Recommendation */}
                    <Box
                      sx={{
                        p: 1,
                        bgcolor:
                          warning.warning_level === 'CRITICAL'
                            ? 'error.main'
                            : 'warning.main',
                        color: 'white',
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="body2" fontWeight="bold">
                        {warning.warning_level === 'CRITICAL'
                          ? '⚠️ IMMEDIATE ACTION REQUIRED: Close position or add margin to prevent liquidation!'
                          : warning.warning_level === 'HIGH'
                          ? '⚠️ HIGH RISK: Consider reducing position size or setting tighter stop-loss'
                          : '⚠️ ELEVATED RISK: Monitor position closely and prepare exit strategy'}
                      </Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Alert>
            </Collapse>
          );
        })}
      </Stack>
    </Box>
  );
}
