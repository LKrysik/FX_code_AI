/**
 * Signal Detail Panel Component
 * ==============================
 *
 * Slide-out panel showing detailed signal information.
 * Non-blocking design - doesn't cover main dashboard.
 *
 * Features:
 * - Slides in from right (400px width)
 * - Shows indicator values, thresholds, execution status
 * - Visual progress bars for indicator strengths
 * - Close on ESC or click outside
 *
 * UX Benefits:
 * - Non-blocking (vs modal that blocks entire screen)
 * - Context preservation (user can see chart while reading)
 * - Industry standard (Slack, Discord, Notion pattern)
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md (Section 3.3)
 */

import React, { useEffect } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
  Chip,
  LinearProgress,
  Button,
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ContentCopy as ContentCopyIcon,
  Share as ShareIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface SignalDetail {
  signal_id: string;
  symbol: string;
  signal_type: string;
  side: 'LONG' | 'SHORT';
  confidence: number;
  timestamp: string;
  execution_status: string;
  indicators: IndicatorDetail[];
  execution?: ExecutionDetail;
  position?: PositionDetail;
}

export interface IndicatorDetail {
  indicator_id: string;
  indicator_name: string;
  value: number;
  threshold_min?: number;
  threshold_max?: number;
  met: boolean; // Whether threshold was met
}

export interface ExecutionDetail {
  status: string;
  order_id?: string;
  entry_price?: number;
  size?: number;
  risk_score?: number;
}

export interface PositionDetail {
  unrealized_pnl: number;
  pnl_pct: number;
  margin_ratio: number;
  liquidation_price?: number;
}

export interface SignalDetailPanelProps {
  open: boolean;
  signal: SignalDetail | null;
  onClose: () => void;
}

// ============================================================================
// Component
// ============================================================================

export const SignalDetailPanel: React.FC<SignalDetailPanelProps> = ({
  open,
  signal,
  onClose,
}) => {
  // ========================================
  // Effects
  // ========================================

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (open) {
      window.addEventListener('keydown', handleEscape);
      return () => window.removeEventListener('keydown', handleEscape);
    }
  }, [open, onClose]);

  // ========================================
  // Render Helpers
  // ========================================

  const renderIndicatorBar = (indicator: IndicatorDetail) => {
    // Calculate percentage for visual bar
    const hasMin = indicator.threshold_min !== undefined;
    const hasMax = indicator.threshold_max !== undefined;

    let percentage = 50; // Default
    if (hasMin && hasMax) {
      const range = indicator.threshold_max! - indicator.threshold_min!;
      percentage = ((indicator.value - indicator.threshold_min!) / range) * 100;
    } else if (hasMax) {
      percentage = (indicator.value / indicator.threshold_max!) * 100;
    }

    percentage = Math.min(Math.max(percentage, 0), 100);

    const color = indicator.met ? 'success' : 'error';

    return (
      <Box key={indicator.indicator_id} sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="body2" fontWeight="medium">
            {indicator.indicator_name}
          </Typography>
          <Typography variant="body2" color={`${color}.main`} fontWeight="bold">
            {indicator.value.toFixed(4)}
          </Typography>
        </Box>

        {(hasMin || hasMax) && (
          <Typography variant="caption" color="text.secondary">
            Threshold: [
            {hasMin ? indicator.threshold_min!.toFixed(2) : '−∞'},
            {hasMax ? indicator.threshold_max!.toFixed(2) : '+∞'}]
            {indicator.met && ' ✓'}
          </Typography>
        )}

        <LinearProgress
          variant="determinate"
          value={percentage}
          color={color}
          sx={{ mt: 0.5, height: 8, borderRadius: 1 }}
        />
      </Box>
    );
  };

  const getSignalTypeIcon = (type: string) => {
    if (type.toLowerCase().includes('entry')) return '🟡';
    if (type.toLowerCase().includes('zone')) return '🟢';
    if (type.toLowerCase().includes('zone_exit')) return '🔵';
    if (type.toLowerCase().includes('exit')) return '🔴';
    return '📊';
  };

  const getExecutionStatusIcon = (status: string) => {
    if (status === 'ORDER_CREATED') return <CheckCircleIcon color="success" />;
    if (status === 'FAILED') return <ErrorIcon color="error" />;
    if (status === 'PENDING') return <WarningIcon color="warning" />;
    return null;
  };

  // ========================================
  // Render
  // ========================================

  if (!signal) return null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: 400,
          p: 3,
        },
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Signal Details</Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Signal Overview */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="h5">{getSignalTypeIcon(signal.signal_type)}</Typography>
          <Box>
            <Typography variant="body1" fontWeight="bold">
              {signal.signal_type}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {signal.symbol} | {signal.side}
            </Typography>
          </Box>
        </Box>

        <Typography variant="caption" color="text.secondary">
          {new Date(signal.timestamp).toLocaleString()}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <Chip
            label={`${signal.side}`}
            color={signal.side === 'LONG' ? 'success' : 'error'}
            size="small"
          />
          <Chip
            label={`Confidence: ${(signal.confidence * 100).toFixed(0)}%`}
            size="small"
            variant="outlined"
          />
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Indicator Values */}
      <Typography variant="subtitle2" gutterBottom>
        📊 INDICATOR VALUES
      </Typography>
      <Box sx={{ mb: 3 }}>
        {signal.indicators.map(renderIndicatorBar)}
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Execution Result */}
      {signal.execution && (
        <>
          <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getExecutionStatusIcon(signal.execution.status)}
            EXECUTION RESULT
          </Typography>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Status:</Typography>
              <Chip label={signal.execution.status} size="small" />
            </Box>

            {signal.execution.order_id && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Order ID:</Typography>
                <Typography variant="body2" fontFamily="monospace">
                  {signal.execution.order_id.substring(0, 12)}...
                </Typography>
              </Box>
            )}

            {signal.execution.entry_price && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Entry Price:</Typography>
                <Typography variant="body2">${signal.execution.entry_price.toFixed(2)}</Typography>
              </Box>
            )}

            {signal.execution.size && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Size:</Typography>
                <Typography variant="body2">{signal.execution.size}</Typography>
              </Box>
            )}

            {signal.execution.risk_score !== undefined && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">Risk Score:</Typography>
                <Chip
                  label={`${signal.execution.risk_score}/10`}
                  size="small"
                  color={signal.execution.risk_score <= 3 ? 'success' : signal.execution.risk_score <= 6 ? 'warning' : 'error'}
                />
              </Box>
            )}
          </Box>

          <Divider sx={{ mb: 2 }} />
        </>
      )}

      {/* Current Position Status */}
      {signal.position && (
        <>
          <Typography variant="subtitle2" gutterBottom>
            📈 CURRENT POSITION STATUS
          </Typography>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Unrealized P&L:</Typography>
              <Typography
                variant="body2"
                fontWeight="bold"
                color={signal.position.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
              >
                ${signal.position.unrealized_pnl.toFixed(2)} ({signal.position.pnl_pct.toFixed(2)}%)
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Margin Ratio:</Typography>
              <Chip
                label={`${signal.position.margin_ratio.toFixed(1)}%`}
                size="small"
                color={signal.position.margin_ratio < 50 ? 'success' : signal.position.margin_ratio < 80 ? 'warning' : 'error'}
              />
            </Box>

            {signal.position.liquidation_price && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">Liquidation Price:</Typography>
                <Typography variant="body2">${signal.position.liquidation_price.toFixed(2)}</Typography>
              </Box>
            )}
          </Box>

          <Divider sx={{ mb: 2 }} />
        </>
      )}

      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button
          variant="outlined"
          startIcon={<ContentCopyIcon />}
          size="small"
          onClick={() => {
            navigator.clipboard.writeText(JSON.stringify(signal, null, 2));
          }}
        >
          Copy Details
        </Button>
        <Button variant="outlined" startIcon={<ShareIcon />} size="small">
          Share
        </Button>
      </Box>
    </Drawer>
  );
};
