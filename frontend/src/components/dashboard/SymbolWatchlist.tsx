/**
 * Symbol Watchlist Component
 * ==========================
 *
 * Real-time symbol monitoring with:
 * - Live price updates
 * - 24h price change percentage
 * - Active position indicators
 * - P&L per symbol
 *
 * Performance:
 * - Optimized for <50ms refresh
 * - Reads from watchlist_cache table
 * - Updates via WebSocket (future: topic-based subscriptions)
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 */

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Skeleton,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface SymbolData {
  symbol: string;
  price: number;
  change_pct: number;
  volume_24h: number;
  position?: {
    side: 'LONG' | 'SHORT';
    pnl: number;
    margin_ratio: number;
  };
}

export interface SymbolWatchlistProps {
  symbols: SymbolData[];
  loading?: boolean;
  onSymbolClick?: (symbol: string) => void;
}

// ============================================================================
// Component
// ============================================================================

export const SymbolWatchlist: React.FC<SymbolWatchlistProps> = ({
  symbols,
  loading = false,
  onSymbolClick,
}) => {
  // ========================================
  // Render Helpers
  // ========================================

  const renderSymbolCard = (symbolData: SymbolData) => {
    const isPriceUp = symbolData.change_pct >= 0;
    const hasPosition = Boolean(symbolData.position);

    return (
      <Box
        key={symbolData.symbol}
        onClick={() => onSymbolClick?.(symbolData.symbol)}
        sx={{
          p: 1.5,
          mb: 1,
          border: 1,
          borderColor: hasPosition ? 'primary.main' : 'divider',
          borderRadius: 1,
          cursor: onSymbolClick ? 'pointer' : 'default',
          transition: 'all 0.2s',
          '&:hover': onSymbolClick
            ? {
                borderColor: 'primary.light',
                backgroundColor: 'action.hover',
              }
            : {},
        }}
      >
        {/* Symbol Name + Price */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="body1" fontWeight="bold">
              {symbolData.symbol}
            </Typography>

            {isPriceUp ? (
              <TrendingUpIcon fontSize="small" color="success" />
            ) : (
              <TrendingDownIcon fontSize="small" color="error" />
            )}
          </Box>

          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="body1" fontWeight="medium">
              ${symbolData.price.toFixed(2)}
            </Typography>
            <Typography
              variant="caption"
              color={isPriceUp ? 'success.main' : 'error.main'}
              fontWeight="medium"
            >
              {isPriceUp ? '+' : ''}
              {symbolData.change_pct.toFixed(2)}%
            </Typography>
          </Box>
        </Box>

        {/* Volume */}
        <Typography variant="caption" color="text.secondary" display="block" mb={1}>
          24h Volume: ${(symbolData.volume_24h / 1000000).toFixed(2)}M
        </Typography>

        {/* Position Chips */}
        {symbolData.position && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={symbolData.position.side}
              color={symbolData.position.side === 'LONG' ? 'success' : 'error'}
              size="small"
            />
            <Chip
              label={`P&L: $${symbolData.position.pnl.toFixed(2)}`}
              size="small"
              variant="outlined"
              color={symbolData.position.pnl >= 0 ? 'success' : 'error'}
            />
            <Chip
              label={`Margin: ${symbolData.position.margin_ratio.toFixed(1)}%`}
              size="small"
              variant="outlined"
            />
          </Box>
        )}
      </Box>
    );
  };

  const renderLoadingSkeleton = () => (
    <>
      {[1, 2, 3].map((i) => (
        <Box key={i} sx={{ p: 1.5, mb: 1 }}>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={20} />
          <Skeleton variant="rectangular" width="100%" height={40} sx={{ mt: 1 }} />
        </Box>
      ))}
    </>
  );

  // ========================================
  // Render
  // ========================================

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Typography variant="h6" gutterBottom>
        Symbol Watchlist
      </Typography>

      {loading ? (
        renderLoadingSkeleton()
      ) : symbols.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No symbols in watchlist
        </Typography>
      ) : (
        <Box sx={{ maxHeight: '600px', overflowY: 'auto' }}>
          {symbols.map(renderSymbolCard)}
        </Box>
      )}
    </Paper>
  );
};
