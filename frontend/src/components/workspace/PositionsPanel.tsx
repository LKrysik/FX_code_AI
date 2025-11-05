/**
 * PositionsPanel Component
 *
 * Real-time positions display with inline editing.
 * No dialogs - click to edit stop loss / take profit.
 *
 * Features:
 * - Live P&L updates
 * - Inline edit SL/TP (InlineEdit component)
 * - Risk gauge (portfolio exposure)
 * - Emergency stop button
 * - Position details
 */

'use client';

import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  LinearProgress,
  Divider,
  IconButton,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  ShowChart as ChartIcon,
  Warning as WarningIcon,
  Emergency as EmergencyIcon,
} from '@mui/icons-material';
import { InlineEdit } from '@/components/common/InlineEdit';

export interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPct: number;
  stopLoss?: number;
  takeProfit?: number;
  riskPct: number;
  strategy?: string;
  timestamp: string;
}

interface PositionsPanelProps {
  positions: Position[];
  totalRisk: number;
  maxRisk?: number;
  onClosePosition: (id: string) => Promise<void>;
  onEditStopLoss: (id: string, value: number) => Promise<void>;
  onEditTakeProfit: (id: string, value: number) => Promise<void>;
  onEmergencyStop?: () => Promise<void>;
  onViewChart?: (symbol: string) => void;
}

export const PositionsPanel: React.FC<PositionsPanelProps> = ({
  positions = [],
  totalRisk = 0,
  maxRisk = 20,
  onClosePosition,
  onEditStopLoss,
  onEditTakeProfit,
  onEmergencyStop,
  onViewChart,
}) => {
  const riskLevel = (totalRisk / maxRisk) * 100;
  const isHighRisk = riskLevel >= 75;
  const isCriticalRisk = riskLevel >= 90;

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
      <Typography variant="h6">Positions & Risk</Typography>

      {/* Risk Gauge */}
      <Card
        sx={{
          bgcolor: isCriticalRisk
            ? 'error.light'
            : isHighRisk
            ? 'warning.light'
            : 'background.paper',
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <WarningIcon color={isCriticalRisk ? 'error' : isHighRisk ? 'warning' : 'action'} sx={{ mr: 1 }} />
            <Typography variant="h6">Portfolio Risk</Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1 }}>
            <Typography variant="h4" color={isCriticalRisk ? 'error.main' : isHighRisk ? 'warning.main' : 'primary.main'}>
              {totalRisk.toFixed(1)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              of {maxRisk}% limit
            </Typography>
          </Box>

          <LinearProgress
            variant="determinate"
            value={riskLevel}
            color={isCriticalRisk ? 'error' : isHighRisk ? 'warning' : 'success'}
            sx={{ height: 8, borderRadius: 4 }}
          />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Status:
            </Typography>
            <Chip
              label={isCriticalRisk ? 'CRITICAL' : isHighRisk ? 'HIGH' : 'HEALTHY'}
              color={isCriticalRisk ? 'error' : isHighRisk ? 'warning' : 'success'}
              size="small"
            />
          </Box>
        </CardContent>
      </Card>

      {/* Total P&L Summary */}
      {positions.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Total Open P&L:
            </Typography>
            <Typography
              variant="h5"
              color={totalPnL >= 0 ? 'success.main' : 'error.main'}
              fontWeight="bold"
            >
              {totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)}
            </Typography>
          </CardContent>
        </Card>
      )}

      <Divider />

      {/* Positions List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {positions.length === 0 ? (
          <Alert severity="info">
            No open positions
          </Alert>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {positions.map((position) => (
              <Card key={position.id}>
                <CardContent>
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                    <Box>
                      <Typography variant="h6" fontWeight="bold">
                        {position.symbol.replace('_', '/')}
                      </Typography>
                      <Chip
                        label={position.side.toUpperCase()}
                        color={position.side === 'long' ? 'success' : 'error'}
                        size="small"
                        sx={{ mt: 0.5 }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {onViewChart && (
                        <Tooltip title="View Chart">
                          <IconButton size="small" onClick={() => onViewChart(position.symbol)}>
                            <ChartIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Close Position">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => onClosePosition(position.id)}
                        >
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>

                  {/* Entry & Current Price */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">
                        Entry:
                      </Typography>
                      <Typography variant="caption" fontWeight="bold">
                        ${position.entryPrice.toFixed(4)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">
                        Current:
                      </Typography>
                      <Typography variant="caption" fontWeight="bold">
                        ${position.currentPrice.toFixed(4)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">
                        Size:
                      </Typography>
                      <Typography variant="caption" fontWeight="bold">
                        {position.size.toLocaleString()}
                      </Typography>
                    </Box>
                  </Box>

                  {/* P&L */}
                  <Box
                    sx={{
                      p: 1,
                      bgcolor: position.pnl >= 0 ? 'success.light' : 'error.light',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <Typography
                      variant="body2"
                      color={position.pnl >= 0 ? 'success.main' : 'error.main'}
                      fontWeight="bold"
                      textAlign="center"
                    >
                      {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)} ({position.pnl >= 0 ? '+' : ''}{position.pnlPct.toFixed(2)}%)
                    </Typography>
                  </Box>

                  {/* Inline Edit SL/TP */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        Stop Loss:
                      </Typography>
                      {position.stopLoss !== undefined ? (
                        <InlineEdit
                          value={position.stopLoss}
                          onSave={(newValue) => onEditStopLoss(position.id, newValue as number)}
                          format="currency"
                          min={0}
                          max={position.side === 'long' ? position.entryPrice * 0.95 : position.entryPrice * 1.05}
                          size="small"
                          color="error"
                        />
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => onEditStopLoss(position.id, position.entryPrice * 0.95)}
                        >
                          Set SL
                        </Button>
                      )}
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        Take Profit:
                      </Typography>
                      {position.takeProfit !== undefined ? (
                        <InlineEdit
                          value={position.takeProfit}
                          onSave={(newValue) => onEditTakeProfit(position.id, newValue as number)}
                          format="currency"
                          min={position.side === 'long' ? position.entryPrice * 1.01 : 0}
                          max={position.side === 'long' ? position.entryPrice * 2 : position.entryPrice * 0.99}
                          size="small"
                          color="success"
                        />
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => onEditTakeProfit(position.id, position.entryPrice * 1.10)}
                        >
                          Set TP
                        </Button>
                      )}
                    </Box>
                  </Box>

                  {/* Strategy & Risk */}
                  {position.strategy && (
                    <Box sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" color="text.secondary">
                          Strategy:
                        </Typography>
                        <Chip label={position.strategy} size="small" variant="outlined" />
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Box>

      {/* Emergency Stop Button */}
      {onEmergencyStop && positions.length > 0 && (
        <>
          <Divider />
          <Button
            variant="contained"
            color="error"
            startIcon={<EmergencyIcon />}
            onClick={onEmergencyStop}
            fullWidth
            size="large"
          >
            EMERGENCY STOP ALL
          </Button>
          <Typography variant="caption" color="text.secondary" textAlign="center">
            Closes all positions immediately
          </Typography>
        </>
      )}
    </Box>
  );
};

export default PositionsPanel;
