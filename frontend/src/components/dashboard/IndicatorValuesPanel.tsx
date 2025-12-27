/**
 * Indicator Values Panel Component
 * =================================
 * Story 1A-3: Indicator Values Panel
 *
 * Displays real-time indicator values on the dashboard.
 *
 * Features:
 * - AC1: Displays MVP indicators (TWPA, pump_magnitude_pct, volume_surge_ratio, etc.)
 * - AC2: Real-time updates via WebSocket
 * - AC3: Shows name, current value, unit/format for each indicator
 * - AC4: Visible during active sessions
 * - AC5: Appropriate formatting (%, ratio, price)
 *
 * Related: [Source: _bmad-output/prd.md#FR20]
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Box,
  Paper,
  Typography,
  Skeleton,
  Chip,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  ShowChart as ShowChartIcon,
} from '@mui/icons-material';
import { wsService, WSMessage } from '@/services/websocket';
import { useIndicators } from '@/stores/dashboardStore';

// ============================================================================
// Types
// ============================================================================

export type IndicatorUnit = 'percent' | 'ratio' | 'price' | 'rate';

export interface MVPIndicatorConfig {
  key: string;
  label: string;
  unit: IndicatorUnit;
  description?: string;
}

export interface IndicatorValuesProps {
  sessionId: string | null;
  symbol: string;
}

interface IndicatorDisplayValue {
  key: string;
  label: string;
  value: number | null;
  formattedValue: string;
  unit: IndicatorUnit;
  trend?: 'up' | 'down' | 'flat';
  lastUpdate?: string;
}

// ============================================================================
// MVP Indicators Configuration (from PRD FR20)
// ============================================================================

export const MVP_INDICATORS: MVPIndicatorConfig[] = [
  {
    key: 'twpa',
    label: 'TWPA',
    unit: 'price',
    description: 'Time-Weighted Price Average',
  },
  {
    key: 'pump_magnitude_pct',
    label: 'Pump Magnitude',
    unit: 'percent',
    description: 'Percentage pump magnitude',
  },
  {
    key: 'volume_surge_ratio',
    label: 'Volume Surge',
    unit: 'ratio',
    description: 'Volume surge multiplier',
  },
  {
    key: 'price_velocity',
    label: 'Price Velocity',
    unit: 'rate',
    description: 'Price change rate per second',
  },
  {
    key: 'spread_pct',
    label: 'Spread',
    unit: 'percent',
    description: 'Bid-ask spread percentage',
  },
  {
    key: 'unrealized_pnl_pct',
    label: 'Unrealized P&L',
    unit: 'percent',
    description: 'Unrealized profit/loss percentage',
  },
];

// ============================================================================
// Formatting Functions
// ============================================================================

/**
 * Format indicator value based on its unit type.
 * AC5: Values are formatted appropriately (%, ratio, price)
 */
export function formatIndicatorValue(
  value: number | null | undefined,
  unit: IndicatorUnit
): string {
  // Handle null, undefined, NaN
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }

  const sign = value > 0 ? '+' : '';

  switch (unit) {
    case 'percent':
      // Format: +7.25% or -3.12%
      return `${sign}${(value * 100).toFixed(2)}%`;

    case 'ratio':
      // Format: 3.50x
      return `${value.toFixed(2)}x`;

    case 'price':
      // Format: $45,230.50
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    case 'rate':
      // Format: +0.12%/s
      return `${sign}${(value * 100).toFixed(2)}%/s`;

    default:
      return value.toFixed(4);
  }
}

/**
 * Determine trend direction from current and previous values.
 */
function determineTrend(
  current: number | null,
  previous: number | null
): 'up' | 'down' | 'flat' {
  if (current === null || previous === null) return 'flat';
  if (current > previous) return 'up';
  if (current < previous) return 'down';
  return 'flat';
}

// ============================================================================
// Component
// ============================================================================

// Stale data threshold in milliseconds (30 seconds)
const STALE_THRESHOLD_MS = 30000;

export const IndicatorValuesPanel: React.FC<IndicatorValuesProps> = ({
  sessionId,
  symbol,
}) => {
  // ========================================
  // State
  // ========================================

  const [indicatorValues, setIndicatorValues] = useState<Map<string, IndicatorDisplayValue>>(
    new Map()
  );
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const previousValuesRef = useRef<Map<string, number>>(new Map());

  // Get indicators from store
  const storeIndicators = useIndicators();

  // ========================================
  // Initialize indicator display values
  // ========================================

  useEffect(() => {
    // Initialize all MVP indicators with placeholder values
    const initialValues = new Map<string, IndicatorDisplayValue>();
    MVP_INDICATORS.forEach((config) => {
      initialValues.set(config.key, {
        key: config.key,
        label: config.label,
        value: null,
        formattedValue: '--',
        unit: config.unit,
        trend: 'flat',
      });
    });
    setIndicatorValues(initialValues);
    setLoading(false);
  }, []);

  // ========================================
  // WebSocket subscription for real-time updates (AC2)
  // ========================================

  const handleIndicatorMessage = useCallback(
    (message: WSMessage) => {
      try {
        if (!message || !message.data) return;

        // Handle both direct data and nested data structures
        const data = message.data || message;

        // Filter by symbol if specified
        if (data.symbol && data.symbol !== symbol) return;

        // ✅ FIX (BUG-003-4): Handle individual indicator updates from backend
        // Backend sends: { symbol, indicator, indicator_type, value, timestamp }
        // We need to extract indicator_type as the key and value as the value
        if (data.indicator_type && data.value !== undefined) {
          const indicatorType = data.indicator_type.toLowerCase();
          const config = MVP_INDICATORS.find((i) => i.key === indicatorType);

          if (config) {
            const numValue = typeof data.value === 'number' ? data.value : null;
            const now = new Date().toISOString();

            setIndicatorValues((prev) => {
              const updated = new Map(prev);
              const previousValue = previousValuesRef.current.get(config.key) ?? null;
              const trend = determineTrend(numValue, previousValue);

              if (numValue !== null) {
                previousValuesRef.current.set(config.key, numValue);
              }

              updated.set(config.key, {
                key: config.key,
                label: config.label,
                value: numValue,
                formattedValue: formatIndicatorValue(numValue, config.unit),
                unit: config.unit,
                trend,
                lastUpdate: now,
              });

              return updated;
            });

            setLastUpdate(new Date().toISOString());
          }
          return;
        }

        // Handle aggregated format: { indicators: { twpa: value, ... } }
        const indicatorData = data.indicators || data;

        // Validate indicatorData is an object we can iterate
        if (!indicatorData || typeof indicatorData !== 'object' || Array.isArray(indicatorData)) {
          Logger.warn('IndicatorValuesPanel.handleMessage', 'Invalid indicator data format', { indicatorData });
          return;
        }

        setIndicatorValues((prev) => {
          const updated = new Map(prev);
          const now = new Date().toISOString();

          // Update each indicator value
          Object.entries(indicatorData).forEach(([key, value]) => {
            const config = MVP_INDICATORS.find((i) => i.key === key || i.key === key.toLowerCase());
            if (!config) return;

            const numValue = typeof value === 'number' ? value : null;
            const previousValue = previousValuesRef.current.get(config.key) ?? null;
            const trend = determineTrend(numValue, previousValue);

            // Store current value for next trend calculation
            if (numValue !== null) {
              previousValuesRef.current.set(config.key, numValue);
            }

            updated.set(config.key, {
              key: config.key,
              label: config.label,
              value: numValue,
              formattedValue: formatIndicatorValue(numValue, config.unit),
              unit: config.unit,
              trend,
              lastUpdate: now,
            });
          });

          return updated;
        });

        setLastUpdate(new Date().toISOString());
      } catch (error) {
        Logger.error('IndicatorValuesPanel.handleMessage', 'Error processing indicator message', { error });
      }
    },
    [symbol]
  );

  useEffect(() => {
    if (!sessionId) return;

    // Set up WebSocket callback for indicators
    wsService.setCallbacks({
      onIndicators: handleIndicatorMessage,
    });

    // Subscribe to indicators stream
    wsService.subscribe('indicators', { symbol, session_id: sessionId });

    return () => {
      // Cleanup: unsubscribe on unmount
      wsService.unsubscribe('indicators');
    };
  }, [sessionId, symbol, handleIndicatorMessage]);

  // ========================================
  // Sync with store indicators
  // ========================================

  useEffect(() => {
    if (!storeIndicators || storeIndicators.length === 0) return;

    // Filter indicators for current symbol
    const symbolIndicators = storeIndicators.filter((ind) => ind.symbol === symbol);

    setIndicatorValues((prev) => {
      const updated = new Map(prev);
      const now = new Date().toISOString();

      symbolIndicators.forEach((ind) => {
        const config = MVP_INDICATORS.find((i) => i.key === ind.name);
        if (!config) return;

        const numValue = ind.value;
        const previousValue = previousValuesRef.current.get(ind.name) ?? null;
        const trend = determineTrend(numValue, previousValue);

        if (numValue !== null) {
          previousValuesRef.current.set(ind.name, numValue);
        }

        updated.set(ind.name, {
          key: config.key,
          label: config.label,
          value: numValue,
          formattedValue: formatIndicatorValue(numValue, config.unit),
          unit: config.unit,
          trend,
          lastUpdate: ind.timestamp || now,
        });
      });

      return updated;
    });
  }, [storeIndicators, symbol]);

  // ========================================
  // Render Helpers
  // ========================================

  const getTrendIcon = (trend: 'up' | 'down' | 'flat' | undefined) => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon fontSize="small" sx={{ color: 'success.main' }} />;
      case 'down':
        return <TrendingDownIcon fontSize="small" sx={{ color: 'error.main' }} />;
      default:
        return <TrendingFlatIcon fontSize="small" sx={{ color: 'text.secondary' }} />;
    }
  };

  const getValueColor = (indicator: IndicatorDisplayValue): string => {
    if (indicator.value === null) return 'text.secondary';

    // Special coloring for P&L
    if (indicator.key === 'unrealized_pnl_pct') {
      return indicator.value >= 0 ? 'success.main' : 'error.main';
    }

    // Default based on trend
    switch (indicator.trend) {
      case 'up':
        return 'success.main';
      case 'down':
        return 'error.main';
      default:
        return 'text.primary';
    }
  };

  /**
   * Check if indicator data is stale (older than threshold)
   * Task 2.4: Handle stale data gracefully
   */
  const isDataStale = (lastUpdateTime: string | undefined): boolean => {
    if (!lastUpdateTime) return true;
    const updateTime = new Date(lastUpdateTime).getTime();
    const now = Date.now();
    return now - updateTime > STALE_THRESHOLD_MS;
  };

  const isAnyDataStale = lastUpdate ? isDataStale(lastUpdate) : true;

  const renderIndicatorRow = (indicator: IndicatorDisplayValue) => {
    const config = MVP_INDICATORS.find((c) => c.key === indicator.key);

    return (
      <Box
        key={indicator.key}
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          py: 1,
          px: 1.5,
          '&:hover': {
            backgroundColor: 'action.hover',
            borderRadius: 1,
          },
        }}
      >
        {/* Label + Description */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title={config?.description || ''} arrow placement="left">
            <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
              {indicator.label}
            </Typography>
          </Tooltip>
        </Box>

        {/* Value + Trend */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {indicator.value !== null && getTrendIcon(indicator.trend)}
          <Typography
            variant="body1"
            fontWeight="medium"
            sx={{ color: getValueColor(indicator), fontFamily: 'monospace' }}
          >
            {indicator.formattedValue}
          </Typography>
        </Box>
      </Box>
    );
  };

  const renderLoadingSkeleton = () => (
    <>
      {MVP_INDICATORS.map((config) => (
        <Box
          key={config.key}
          sx={{ display: 'flex', justifyContent: 'space-between', py: 1, px: 1.5 }}
        >
          <Skeleton variant="text" width={100} />
          <Skeleton variant="text" width={80} />
        </Box>
      ))}
    </>
  );

  // ========================================
  // Render
  // ========================================

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ShowChartIcon color="primary" />
          <Typography variant="h6">Indicator Values</Typography>
        </Box>
        <Chip label={symbol} size="small" color="primary" variant="outlined" />
      </Box>

      <Divider sx={{ mb: 1 }} />

      {/* Content */}
      {!sessionId ? (
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No active session
          </Typography>
        </Box>
      ) : loading ? (
        renderLoadingSkeleton()
      ) : (
        <Box>
          {Array.from(indicatorValues.values()).map(renderIndicatorRow)}
        </Box>
      )}

      {/* Footer: Last Update + Stale Indicator */}
      {sessionId && (
        <Box sx={{ mt: 2, pt: 1, borderTop: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            {lastUpdate
              ? `Last update: ${new Date(lastUpdate).toLocaleTimeString()}`
              : 'Waiting for data...'}
          </Typography>
          {isAnyDataStale && lastUpdate && (
            <Chip
              label="STALE"
              size="small"
              color="warning"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.65rem' }}
            />
          )}
        </Box>
      )}
    </Paper>
  );
};

export default IndicatorValuesPanel;
