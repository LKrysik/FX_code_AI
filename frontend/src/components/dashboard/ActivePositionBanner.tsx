'use client';

/**
 * ActivePositionBanner Component
 * ==============================
 *
 * HIGH VISIBILITY position alert banner for Dashboard.
 *
 * WHY THIS EXISTS:
 * - Trader MUST see active positions IMMEDIATELY on Dashboard
 * - Position details hidden in tab = trader misses critical P&L changes
 * - This banner appears at TOP of Dashboard when ANY position is open
 *
 * STATE MACHINE CONNECTION:
 * - Position exists after Z1 (Entry Executed)
 * - Position closed after ZE1 (Normal Exit) or E1 (Emergency Exit)
 * - Banner shows CURRENT state: POSITION_ACTIVE
 *
 * TRADER VALUE:
 * - "Am I in a position?" - immediately visible (yes/no)
 * - "What's my P&L?" - large, color-coded number
 * - "How long have I been in?" - time display
 * - "Emergency close?" - one-click button
 * - "Modify SL/TP?" - inline edit (PM-03)
 *
 * Related: docs/UI_BACKLOG.md - PM-01, PM-03 (Position panel + SL/TP modification)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  IconButton,
  Collapse,
  Grid,
  Tooltip,
  LinearProgress,
  Alert,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from '@mui/material';
import {
  TrendingUp as ProfitIcon,
  TrendingDown as LossIcon,
  Close as CloseIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  AccessTime as TimeIcon,
  Warning as WarningIcon,
  OpenInNew as OpenIcon,
  Edit as EditIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

interface Position {
  position_id: string;
  session_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  margin_ratio: number;
  leverage: number;
  stop_loss_price?: number;
  take_profit_price?: number;
  liquidation_price?: number;
  opened_at: string;
  updated_at: string;
}

interface ActivePositionBannerProps {
  sessionId: string | null;
  onNavigateToPositions?: () => void;
  onClosePosition?: (positionId: string) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function ActivePositionBanner({
  sessionId,
  onNavigateToPositions,
  onClosePosition,
}: ActivePositionBannerProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [closingId, setClosingId] = useState<string | null>(null);

  // PM-03: SL/TP Edit State
  const [editingSlTp, setEditingSlTp] = useState<{
    positionId: string;
    symbol: string;
    side: 'LONG' | 'SHORT';
    entryPrice: number;
    currentSl: number | null;
    currentTp: number | null;
  } | null>(null);
  const [slValue, setSlValue] = useState<string>('');
  const [tpValue, setTpValue] = useState<string>('');
  const [savingSlTp, setSavingSlTp] = useState(false);
  const [slTpError, setSlTpError] = useState<string | null>(null);

  // ========================================
  // Data Loading
  // ========================================

  const fetchPositions = useCallback(async () => {
    if (!sessionId) {
      setPositions([]);
      setLoading(false);
      return;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/positions?session_id=${sessionId}&status=OPEN`
      );

      if (!response.ok) {
        throw new Error(`Failed to load positions: ${response.status}`);
      }

      const result = await response.json();
      const data = result.data || result;

      // Handle both array and object with positions property
      const positionList = Array.isArray(data) ? data : (data.positions || []);
      setPositions(positionList);
      setError(null);
    } catch (err) {
      console.error('[ActivePositionBanner] Failed to fetch positions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load positions');
      setPositions([]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Initial load and periodic refresh
  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 2000); // 2s refresh for real-time P&L
    return () => clearInterval(interval);
  }, [fetchPositions]);

  // ========================================
  // Event Handlers
  // ========================================

  const handleClosePosition = async (position: Position) => {
    const positionId = `${position.session_id}:${position.symbol}`;

    if (!confirm(`Close ${position.side} position on ${position.symbol}?`)) {
      return;
    }

    setClosingId(positionId);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/positions/${positionId}/close`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'USER_REQUESTED_FROM_BANNER' }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to close position: ${response.status}`);
      }

      // Callback to parent if provided
      if (onClosePosition) {
        onClosePosition(positionId);
      }

      // Refresh positions
      setTimeout(fetchPositions, 500);
    } catch (err) {
      console.error('[ActivePositionBanner] Failed to close position:', err);
      alert(`Failed to close position: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setClosingId(null);
    }
  };

  // PM-03: Open SL/TP Edit Dialog
  const handleOpenSlTpEdit = (position: Position) => {
    const positionId = `${position.session_id}:${position.symbol}`;
    setEditingSlTp({
      positionId,
      symbol: position.symbol,
      side: position.side,
      entryPrice: position.entry_price,
      currentSl: position.stop_loss_price || null,
      currentTp: position.take_profit_price || null,
    });
    setSlValue(position.stop_loss_price?.toString() || '');
    setTpValue(position.take_profit_price?.toString() || '');
    setSlTpError(null);
  };

  // PM-03: Close SL/TP Edit Dialog
  const handleCloseSlTpEdit = () => {
    setEditingSlTp(null);
    setSlValue('');
    setTpValue('');
    setSlTpError(null);
    setSavingSlTp(false);
  };

  // PM-03: Save SL/TP
  const handleSaveSlTp = async () => {
    if (!editingSlTp) return;

    const sl = slValue ? parseFloat(slValue) : null;
    const tp = tpValue ? parseFloat(tpValue) : null;

    // Client-side validation
    if (sl !== null && isNaN(sl)) {
      setSlTpError('Stop Loss must be a valid number');
      return;
    }
    if (tp !== null && isNaN(tp)) {
      setSlTpError('Take Profit must be a valid number');
      return;
    }

    // Validate SL/TP relative to entry price
    const { side, entryPrice } = editingSlTp;
    if (sl !== null) {
      if (side === 'LONG' && sl >= entryPrice) {
        setSlTpError(`Stop Loss must be below entry price (${formatCurrency(entryPrice)}) for LONG`);
        return;
      }
      if (side === 'SHORT' && sl <= entryPrice) {
        setSlTpError(`Stop Loss must be above entry price (${formatCurrency(entryPrice)}) for SHORT`);
        return;
      }
    }
    if (tp !== null) {
      if (side === 'LONG' && tp <= entryPrice) {
        setSlTpError(`Take Profit must be above entry price (${formatCurrency(entryPrice)}) for LONG`);
        return;
      }
      if (side === 'SHORT' && tp >= entryPrice) {
        setSlTpError(`Take Profit must be below entry price (${formatCurrency(entryPrice)}) for SHORT`);
        return;
      }
    }

    setSavingSlTp(true);
    setSlTpError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/trading/positions/${editingSlTp.positionId}/sl-tp`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            stop_loss: sl,
            take_profit: tp,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to update SL/TP: ${response.status}`);
      }

      // Success - close dialog and refresh positions
      handleCloseSlTpEdit();
      setTimeout(fetchPositions, 500);
    } catch (err) {
      console.error('[ActivePositionBanner] Failed to update SL/TP:', err);
      setSlTpError(err instanceof Error ? err.message : 'Failed to update SL/TP');
    } finally {
      setSavingSlTp(false);
    }
  };

  // ========================================
  // Helpers
  // ========================================

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getTimeSince = (dateString: string): string => {
    const opened = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - opened.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) {
      return `${diffMins}m`;
    }

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;

    if (hours < 24) {
      return `${hours}h ${mins}m`;
    }

    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  };

  const getPnLColor = (pnl: number): string => {
    if (pnl > 0) return 'success.main';
    if (pnl < 0) return 'error.main';
    return 'text.secondary';
  };

  const getMarginColor = (ratio: number): 'success' | 'warning' | 'error' => {
    if (ratio < 15) return 'error';
    if (ratio < 25) return 'warning';
    return 'success';
  };

  // ========================================
  // Render
  // ========================================

  // Don't render if no session or no positions
  if (!sessionId || loading) {
    return null;
  }

  if (positions.length === 0) {
    return null;
  }

  // Calculate totals
  const totalPnL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const avgMarginRatio = positions.reduce((sum, p) => sum + p.margin_ratio, 0) / positions.length;
  const hasLowMargin = positions.some(p => p.margin_ratio < 25);
  const hasRisk = totalPnL < 0 || hasLowMargin;

  return (
    <Paper
      elevation={hasRisk ? 4 : 2}
      sx={{
        mb: 2,
        overflow: 'hidden',
        borderLeft: 4,
        borderColor: hasRisk ? 'error.main' : 'success.main',
        backgroundColor: hasRisk ? 'error.light' : 'success.light',
        '&:hover': {
          boxShadow: 4,
        },
      }}
    >
      {/* Main Banner Row */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Left: Position Count and Status */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            label={`${positions.length} ACTIVE POSITION${positions.length > 1 ? 'S' : ''}`}
            color={hasRisk ? 'error' : 'success'}
            size="medium"
            sx={{ fontWeight: 'bold' }}
          />

          {hasLowMargin && (
            <Tooltip title="Low margin ratio - risk of liquidation!">
              <Chip
                icon={<WarningIcon />}
                label="LOW MARGIN"
                color="error"
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}
        </Box>

        {/* Center: Total P&L (MOST IMPORTANT) */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {totalPnL >= 0 ? <ProfitIcon color="success" /> : <LossIcon color="error" />}
          <Typography
            variant="h5"
            component="span"
            sx={{
              fontWeight: 'bold',
              color: getPnLColor(totalPnL),
            }}
          >
            {formatCurrency(totalPnL)}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: getPnLColor(totalPnL),
              fontWeight: 500,
            }}
          >
            Total P&L
          </Typography>
        </Box>

        {/* Right: Actions */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {onNavigateToPositions && (
            <Button
              size="small"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                onNavigateToPositions();
              }}
              endIcon={<OpenIcon />}
            >
              View Details
            </Button>
          )}

          <IconButton size="small">
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>
      </Box>

      {/* Expanded Details */}
      <Collapse in={expanded}>
        <Box sx={{ px: 2, pb: 2 }}>
          <Grid container spacing={2}>
            {positions.map((position) => {
              const positionId = `${position.session_id}:${position.symbol}`;
              const isClosing = closingId === positionId;

              return (
                <Grid item xs={12} md={positions.length === 1 ? 12 : 6} key={positionId}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      backgroundColor: 'background.paper',
                      borderColor: position.unrealized_pnl >= 0 ? 'success.light' : 'error.light',
                    }}
                  >
                    {/* Position Header */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                          {position.symbol}
                        </Typography>
                        <Chip
                          label={position.side}
                          size="small"
                          color={position.side === 'SHORT' ? 'error' : 'success'}
                        />
                        <Chip
                          label={`${position.leverage}x`}
                          size="small"
                          variant="outlined"
                        />
                      </Box>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Tooltip title={`Opened: ${new Date(position.opened_at).toLocaleString()}`}>
                          <Chip
                            icon={<TimeIcon />}
                            label={getTimeSince(position.opened_at)}
                            size="small"
                            variant="outlined"
                          />
                        </Tooltip>
                      </Box>
                    </Box>

                    {/* Position Details Grid */}
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">
                          Entry Price
                        </Typography>
                        <Typography variant="body1" fontWeight={500}>
                          {formatCurrency(position.entry_price)}
                        </Typography>
                      </Grid>

                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">
                          Current Price
                        </Typography>
                        <Typography variant="body1" fontWeight={500}>
                          {formatCurrency(position.current_price)}
                        </Typography>
                      </Grid>

                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">
                          Unrealized P&L
                        </Typography>
                        <Typography
                          variant="body1"
                          fontWeight="bold"
                          sx={{ color: getPnLColor(position.unrealized_pnl) }}
                        >
                          {formatCurrency(position.unrealized_pnl)}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{ color: getPnLColor(position.unrealized_pnl_pct) }}
                        >
                          {formatPercent(position.unrealized_pnl_pct)}
                        </Typography>
                      </Grid>

                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">
                          Margin Ratio
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography
                            variant="body1"
                            fontWeight={500}
                            color={`${getMarginColor(position.margin_ratio)}.main`}
                          >
                            {position.margin_ratio.toFixed(1)}%
                          </Typography>
                          {position.margin_ratio < 25 && (
                            <WarningIcon fontSize="small" color="warning" />
                          )}
                        </Box>
                      </Grid>
                    </Grid>

                    {/* SL/TP Display with Edit Button (PM-03) */}
                    <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'flex-start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Stop Loss
                        </Typography>
                        <Typography
                          variant="body2"
                          color={position.stop_loss_price ? 'error.main' : 'text.disabled'}
                        >
                          {position.stop_loss_price ? formatCurrency(position.stop_loss_price) : 'Not Set'}
                        </Typography>
                      </Box>

                      <Box sx={{ flex: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Take Profit
                        </Typography>
                        <Typography
                          variant="body2"
                          color={position.take_profit_price ? 'success.main' : 'text.disabled'}
                        >
                          {position.take_profit_price ? formatCurrency(position.take_profit_price) : 'Not Set'}
                        </Typography>
                      </Box>

                      <Box sx={{ flex: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Liquidation
                        </Typography>
                        <Typography variant="body2" color="error.main">
                          {position.liquidation_price ? formatCurrency(position.liquidation_price) : 'N/A'}
                        </Typography>
                      </Box>

                      {/* PM-03: Edit SL/TP Button */}
                      <Tooltip title="Modify Stop Loss / Take Profit">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenSlTpEdit(position);
                          }}
                          sx={{ mt: -0.5 }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>

                    {/* Margin Progress Bar */}
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          Margin Health
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {position.margin_ratio.toFixed(1)}% / 100%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(position.margin_ratio, 100)}
                        color={getMarginColor(position.margin_ratio)}
                        sx={{ height: 6, borderRadius: 3 }}
                      />
                    </Box>

                    {/* Action Button */}
                    <Button
                      fullWidth
                      variant="contained"
                      color="error"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClosePosition(position);
                      }}
                      disabled={isClosing}
                    >
                      {isClosing ? 'Closing...' : 'Close Position 100%'}
                    </Button>
                  </Paper>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      </Collapse>

      {/* PM-03: SL/TP Edit Dialog */}
      <Dialog
        open={editingSlTp !== null}
        onClose={handleCloseSlTpEdit}
        maxWidth="sm"
        fullWidth
        onClick={(e) => e.stopPropagation()}
      >
        <DialogTitle>
          Modify Stop Loss / Take Profit
          {editingSlTp && (
            <Typography variant="body2" color="text.secondary">
              {editingSlTp.symbol} ({editingSlTp.side}) - Entry: {formatCurrency(editingSlTp.entryPrice)}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {slTpError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {slTpError}
            </Alert>
          )}

          {editingSlTp && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {editingSlTp.side === 'LONG'
                  ? 'For LONG positions: Stop Loss must be below entry, Take Profit above entry.'
                  : 'For SHORT positions: Stop Loss must be above entry, Take Profit below entry.'}
              </Typography>

              <TextField
                fullWidth
                label="Stop Loss Price"
                type="number"
                value={slValue}
                onChange={(e) => setSlValue(e.target.value)}
                placeholder={editingSlTp.currentSl ? formatCurrency(editingSlTp.currentSl) : 'Not set'}
                helperText={
                  editingSlTp.side === 'LONG'
                    ? `Must be below ${formatCurrency(editingSlTp.entryPrice)}`
                    : `Must be above ${formatCurrency(editingSlTp.entryPrice)}`
                }
                sx={{ mb: 2 }}
                InputProps={{
                  startAdornment: <Typography sx={{ mr: 1, color: 'error.main' }}>SL:</Typography>,
                }}
              />

              <TextField
                fullWidth
                label="Take Profit Price"
                type="number"
                value={tpValue}
                onChange={(e) => setTpValue(e.target.value)}
                placeholder={editingSlTp.currentTp ? formatCurrency(editingSlTp.currentTp) : 'Not set'}
                helperText={
                  editingSlTp.side === 'LONG'
                    ? `Must be above ${formatCurrency(editingSlTp.entryPrice)}`
                    : `Must be below ${formatCurrency(editingSlTp.entryPrice)}`
                }
                InputProps={{
                  startAdornment: <Typography sx={{ mr: 1, color: 'success.main' }}>TP:</Typography>,
                }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseSlTpEdit} disabled={savingSlTp}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveSlTp}
            disabled={savingSlTp}
            startIcon={savingSlTp ? <CircularProgress size={16} /> : null}
          >
            {savingSlTp ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
