/**
 * Variant Chart Preview Component (IV-01)
 * ========================================
 *
 * Shows how an indicator variant reacts to historical pump events.
 * Displays price chart overlaid with indicator values and detected pumps.
 *
 * Features:
 * - SVG-based candlestick chart with OHLCV data
 * - Indicator values plotted as overlay/subplot
 * - Pump events highlighted with markers
 * - Signal triggers shown when threshold is crossed
 * - Variant parameter influence visualization
 *
 * Related: docs/UI_BACKLOG.md (IV-01)
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Collapse,
  Chip,
  Stack,
  Alert,
  Tooltip,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  ShowChart as ChartIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { IndicatorVariant } from '@/types/strategy';
import { apiService } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface OHLCVData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface IndicatorDataPoint {
  timestamp: number;
  value: number;
  isTrigger: boolean; // When value crosses threshold
}

interface PumpEvent {
  startTime: number;
  peakTime: number;
  endTime?: number;
  startPrice: number;
  peakPrice: number;
  magnitude: number; // percentage
}

interface VariantChartPreviewProps {
  variant?: IndicatorVariant | null;
  variants?: IndicatorVariant[];
  onPumpDetected?: (pump: PumpEvent) => void;
  onVariantSelect?: (variant: IndicatorVariant) => void;
}

// ============================================================================
// Constants
// ============================================================================

const CHART_WIDTH = 800;
const CHART_HEIGHT = 400;
const PRICE_HEIGHT = 250;
const INDICATOR_HEIGHT = 100;
const PADDING = { top: 20, right: 60, bottom: 50, left: 60 };

const SYMBOLS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'DOGE_USDT', 'PEPE_USDT'];
const TIMEFRAMES = [
  { value: '1m', label: '1 minute', minutes: 1 },
  { value: '5m', label: '5 minutes', minutes: 5 },
  { value: '15m', label: '15 minutes', minutes: 15 },
  { value: '1h', label: '1 hour', minutes: 60 },
];

// Base prices for mock data
const BASE_PRICES: Record<string, number> = {
  'BTC_USDT': 42000,
  'ETH_USDT': 2200,
  'SOL_USDT': 95,
  'DOGE_USDT': 0.08,
  'PEPE_USDT': 0.0000012,
};

// ============================================================================
// Mock Data Generators
// ============================================================================

function generateMockOHLCVData(
  symbol: string,
  timeframe: string,
  count: number = 200
): OHLCVData[] {
  const basePrice = BASE_PRICES[symbol] || 100;
  const now = Date.now();
  const intervalMs = TIMEFRAMES.find(tf => tf.value === timeframe)?.minutes || 1;
  const data: OHLCVData[] = [];

  let price = basePrice;
  const volatility = 0.002; // 0.2% base volatility

  // Generate pump events at specific intervals
  const pumpIndices = [30, 80, 130, 170];

  for (let i = 0; i < count; i++) {
    const timestamp = now - (count - i) * intervalMs * 60 * 1000;

    // Check if this is a pump zone
    const isPumpStart = pumpIndices.includes(i);
    const isPumpPeak = pumpIndices.map(p => p + 5).includes(i);
    const isInPump = pumpIndices.some(p => i >= p && i <= p + 10);

    let change = (Math.random() - 0.5) * 2 * volatility * price;

    if (isPumpStart) {
      // Start of pump - sudden rise
      change = price * (0.03 + Math.random() * 0.02); // 3-5% rise
    } else if (isPumpPeak) {
      // Peak of pump - start declining
      change = price * (-0.01 - Math.random() * 0.01); // 1-2% drop
    } else if (isInPump) {
      // During pump - continue trend with volatility
      const pumpIndex = pumpIndices.find(p => i >= p && i <= p + 10)!;
      const pumpPhase = i - pumpIndex;
      if (pumpPhase < 5) {
        change = price * (0.005 + Math.random() * 0.01); // Rising
      } else {
        change = price * (-0.005 - Math.random() * 0.01); // Declining
      }
    }

    const open = price;
    price += change;
    const close = price;

    const high = Math.max(open, close) * (1 + Math.random() * volatility);
    const low = Math.min(open, close) * (1 - Math.random() * volatility);
    const volume = 1000000 * (0.5 + Math.random()) * (isInPump ? 3 : 1);

    data.push({
      timestamp,
      open,
      high,
      low,
      close,
      volume,
    });
  }

  return data;
}

function calculateIndicatorValues(
  ohlcvData: OHLCVData[],
  variant: IndicatorVariant
): IndicatorDataPoint[] {
  const params = variant.parameters || {};

  // Extract variant parameters
  const t1 = params.t1 || params.short_window || 5;
  const t3 = params.t3 || params.long_window || 30;
  const threshold = params.threshold || params.pump_threshold || 3.0;

  // Determine indicator behavior based on variant type
  const isFast = variant.name.toLowerCase().includes('fast');
  const isSlow = variant.name.toLowerCase().includes('slow');

  // Sensitivity factor based on speed
  const sensitivity = isFast ? 1.5 : isSlow ? 0.7 : 1.0;

  const indicatorData: IndicatorDataPoint[] = [];

  for (let i = 0; i < ohlcvData.length; i++) {
    // Calculate magnitude based on lookback window
    const lookbackStart = Math.max(0, i - t3);
    const recentStart = Math.max(0, i - t1);

    // Get price at lookback start
    const basePrice = ohlcvData[lookbackStart].close;
    const currentPrice = ohlcvData[i].close;

    // Calculate magnitude percentage
    let magnitude = ((currentPrice - basePrice) / basePrice) * 100;

    // Apply sensitivity based on variant speed
    magnitude *= sensitivity;

    // Add some noise to make it more realistic
    magnitude += (Math.random() - 0.5) * 0.2;

    // For velocity variants, calculate rate of change
    if (variant.baseType === 'PRICE_VELOCITY' || variant.name.toLowerCase().includes('velocity')) {
      const recentPrice = ohlcvData[recentStart].close;
      const velocity = ((currentPrice - recentPrice) / recentPrice) * 100;
      magnitude = velocity * sensitivity * 2;
    }

    // Clamp value to reasonable range
    magnitude = Math.max(-10, Math.min(15, magnitude));

    indicatorData.push({
      timestamp: ohlcvData[i].timestamp,
      value: magnitude,
      isTrigger: Math.abs(magnitude) >= threshold,
    });
  }

  return indicatorData;
}

function detectPumps(
  ohlcvData: OHLCVData[],
  indicatorData: IndicatorDataPoint[],
  threshold: number
): PumpEvent[] {
  const pumps: PumpEvent[] = [];
  let inPump = false;
  let currentPump: Partial<PumpEvent> | null = null;

  for (let i = 0; i < indicatorData.length; i++) {
    const ind = indicatorData[i];
    const candle = ohlcvData[i];

    if (!inPump && ind.value >= threshold) {
      // Start of pump
      inPump = true;
      currentPump = {
        startTime: ind.timestamp,
        startPrice: candle.open,
        peakPrice: candle.high,
        peakTime: ind.timestamp,
        magnitude: ind.value,
      };
    } else if (inPump && currentPump) {
      // Update peak if higher
      if (candle.high > currentPump.peakPrice!) {
        currentPump.peakPrice = candle.high;
        currentPump.peakTime = ind.timestamp;
        currentPump.magnitude = Math.max(currentPump.magnitude!, ind.value);
      }

      // End of pump when value drops below threshold
      if (ind.value < threshold * 0.5) {
        currentPump.endTime = ind.timestamp;
        pumps.push(currentPump as PumpEvent);
        inPump = false;
        currentPump = null;
      }
    }
  }

  // Close any open pump
  if (inPump && currentPump) {
    currentPump.endTime = ohlcvData[ohlcvData.length - 1].timestamp;
    pumps.push(currentPump as PumpEvent);
  }

  return pumps;
}

// ============================================================================
// Component
// ============================================================================

export const VariantChartPreview: React.FC<VariantChartPreviewProps> = ({
  variant: propVariant,
  variants: propVariants,
  onPumpDetected,
  onVariantSelect,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [symbol, setSymbol] = useState('BTC_USDT');
  const [timeframe, setTimeframe] = useState('5m');
  const [loading, setLoading] = useState(false);
  const [variants, setVariants] = useState<IndicatorVariant[]>(propVariants || []);
  const [selectedVariantId, setSelectedVariantId] = useState<string>('');
  const [loadingVariants, setLoadingVariants] = useState(!propVariants);

  // Load variants if not provided
  useEffect(() => {
    if (propVariants) {
      setVariants(propVariants);
      if (propVariants.length > 0 && !selectedVariantId) {
        setSelectedVariantId(propVariants[0].id);
      }
      return;
    }

    const loadVariants = async () => {
      setLoadingVariants(true);
      try {
        const data = await apiService.getVariants();
        const transformedVariants: IndicatorVariant[] = data.map((v: any) => ({
          id: v.variant_id ?? v.id,
          name: v.name,
          baseType: v.base_indicator_type || v.baseType,
          type: v.variant_type || v.type || 'general',
          description: v.description,
          parameters: v.parameters || {},
          isActive: true,
        }));
        setVariants(transformedVariants);
        if (transformedVariants.length > 0 && !selectedVariantId) {
          setSelectedVariantId(transformedVariants[0].id);
        }
      } catch (err) {
        console.error('Failed to load variants:', err);
        // Use mock variants for development
        const mockVariants: IndicatorVariant[] = [
          {
            id: 'mock-pump-fast',
            name: 'PumpFast',
            baseType: 'PUMP_MAGNITUDE_PCT',
            type: 'general',
            description: 'Fast pump detection with t1=5s, t3=30s',
            parameters: { t1: 5, t3: 30, threshold: 3.0 },
            isActive: true,
          },
          {
            id: 'mock-pump-medium',
            name: 'PumpMedium',
            baseType: 'PUMP_MAGNITUDE_PCT',
            type: 'general',
            description: 'Medium pump detection with t1=15s, t3=60s',
            parameters: { t1: 15, t3: 60, threshold: 5.0 },
            isActive: true,
          },
          {
            id: 'mock-pump-slow',
            name: 'PumpSlow',
            baseType: 'PUMP_MAGNITUDE_PCT',
            type: 'general',
            description: 'Slow pump detection with t1=30s, t3=120s',
            parameters: { t1: 30, t3: 120, threshold: 7.0 },
            isActive: true,
          },
          {
            id: 'mock-velocity-fast',
            name: 'VelocityFast',
            baseType: 'PRICE_VELOCITY',
            type: 'general',
            description: 'Fast velocity detection',
            parameters: { window: 5, threshold: 2.0 },
            isActive: true,
          },
        ];
        setVariants(mockVariants);
        setSelectedVariantId(mockVariants[0].id);
      } finally {
        setLoadingVariants(false);
      }
    };

    loadVariants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propVariants]);

  // Use propVariant if provided, otherwise use selected from dropdown
  const variant = propVariant || variants.find(v => v.id === selectedVariantId) || null;

  const handleVariantChange = (variantId: string) => {
    setSelectedVariantId(variantId);
    const selected = variants.find(v => v.id === variantId);
    if (selected && onVariantSelect) {
      onVariantSelect(selected);
    }
  };

  // Generate data
  const { ohlcvData, indicatorData, pumps, threshold } = useMemo(() => {
    if (!variant) {
      return { ohlcvData: [], indicatorData: [], pumps: [], threshold: 3 };
    }

    const threshold = variant.parameters?.threshold ||
                     variant.parameters?.pump_threshold ||
                     3.0;
    const ohlcv = generateMockOHLCVData(symbol, timeframe, 200);
    const indicator = calculateIndicatorValues(ohlcv, variant);
    const detectedPumps = detectPumps(ohlcv, indicator, threshold);

    return {
      ohlcvData: ohlcv,
      indicatorData: indicator,
      pumps: detectedPumps,
      threshold,
    };
  }, [variant, symbol, timeframe]);

  // Notify about detected pumps
  useEffect(() => {
    if (pumps.length > 0 && onPumpDetected) {
      pumps.forEach(pump => onPumpDetected(pump));
    }
  }, [pumps, onPumpDetected]);

  // ========================================
  // Chart Calculations
  // ========================================

  const chartMetrics = useMemo(() => {
    if (ohlcvData.length === 0) return null;

    const prices = ohlcvData.flatMap(d => [d.high, d.low]);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;

    const indicatorValues = indicatorData.map(d => d.value);
    const minIndicator = Math.min(...indicatorValues, 0);
    const maxIndicator = Math.max(...indicatorValues, threshold);
    const indicatorRange = maxIndicator - minIndicator || 1;

    const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
    const candleWidth = Math.max(2, innerWidth / ohlcvData.length - 1);

    return {
      minPrice,
      maxPrice,
      priceRange,
      minIndicator,
      maxIndicator,
      indicatorRange,
      innerWidth,
      candleWidth,
    };
  }, [ohlcvData, indicatorData, threshold]);

  // ========================================
  // Coordinate Helpers
  // ========================================

  const getX = (index: number): number => {
    if (!chartMetrics) return 0;
    return PADDING.left + (index / (ohlcvData.length - 1)) * chartMetrics.innerWidth;
  };

  const getPriceY = (price: number): number => {
    if (!chartMetrics) return 0;
    return PADDING.top + (1 - (price - chartMetrics.minPrice) / chartMetrics.priceRange) * PRICE_HEIGHT;
  };

  const getIndicatorY = (value: number): number => {
    if (!chartMetrics) return 0;
    const baseY = PADDING.top + PRICE_HEIGHT + 20;
    return baseY + (1 - (value - chartMetrics.minIndicator) / chartMetrics.indicatorRange) * INDICATOR_HEIGHT;
  };

  // ========================================
  // Render
  // ========================================

  if (loadingVariants) {
    return (
      <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading variants...
        </Typography>
      </Paper>
    );
  }

  if (variants.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">
          No variants available. Create variants in the Variant Manager tab first.
        </Alert>
      </Paper>
    );
  }

  const triggerCount = indicatorData.filter(d => d.isTrigger).length;
  const pumpAccuracy = pumps.length > 0
    ? Math.round((pumps.filter(p => p.magnitude >= threshold).length / pumps.length) * 100)
    : 0;

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ChartIcon color="primary" />
          <Typography variant="h6">
            Variant Preview{variant ? `: ${variant.name}` : ''}
          </Typography>
          <Chip
            label="IV-01"
            size="small"
            color="primary"
            variant="outlined"
          />
        </Box>
        <IconButton onClick={() => setExpanded(!expanded)} size="small">
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        {/* Controls */}
        <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
          {/* Variant selector - only show if not passed as prop */}
          {!propVariant && (
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Variant</InputLabel>
              <Select
                value={selectedVariantId}
                onChange={(e) => handleVariantChange(e.target.value)}
                label="Variant"
              >
                {variants.map(v => (
                  <MenuItem key={v.id} value={v.id}>{v.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Symbol</InputLabel>
            <Select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              label="Symbol"
            >
              {SYMBOLS.map(s => (
                <MenuItem key={s} value={s}>{s.replace('_', '/')}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              label="Timeframe"
            >
              {TIMEFRAMES.map(tf => (
                <MenuItem key={tf.value} value={tf.value}>{tf.label}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Chip
            icon={<TimelineIcon />}
            label={`Threshold: ${threshold}%`}
            color="warning"
            variant="outlined"
          />
        </Stack>

        {/* Stats */}
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <Chip
            icon={<TrendingUpIcon />}
            label={`${pumps.length} pumps detected`}
            color={pumps.length > 0 ? 'success' : 'default'}
            size="small"
          />
          <Chip
            icon={<WarningIcon />}
            label={`${triggerCount} trigger points`}
            color={triggerCount > 0 ? 'warning' : 'default'}
            size="small"
          />
          <Tooltip title="How many detected pumps exceeded the threshold">
            <Chip
              label={`${pumpAccuracy}% accuracy`}
              color={pumpAccuracy >= 80 ? 'success' : pumpAccuracy >= 50 ? 'warning' : 'error'}
              size="small"
            />
          </Tooltip>
        </Stack>

        {/* Chart */}
        {!variant ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Select a variant above to preview how it reacts to historical pump events.
          </Alert>
        ) : loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : chartMetrics ? (
          <Box sx={{ overflowX: 'auto' }}>
            <svg
              width={CHART_WIDTH}
              height={CHART_HEIGHT}
              style={{ display: 'block', margin: '0 auto' }}
            >
              {/* Background */}
              <rect
                x={PADDING.left}
                y={PADDING.top}
                width={chartMetrics.innerWidth}
                height={PRICE_HEIGHT}
                fill="#1a1a2e"
              />
              <rect
                x={PADDING.left}
                y={PADDING.top + PRICE_HEIGHT + 20}
                width={chartMetrics.innerWidth}
                height={INDICATOR_HEIGHT}
                fill="#1a1a2e"
              />

              {/* Price Grid Lines */}
              {[0.25, 0.5, 0.75].map((fraction, i) => {
                const price = chartMetrics.minPrice + chartMetrics.priceRange * fraction;
                const y = getPriceY(price);
                return (
                  <g key={`price-grid-${i}`}>
                    <line
                      x1={PADDING.left}
                      y1={y}
                      x2={PADDING.left + chartMetrics.innerWidth}
                      y2={y}
                      stroke="#333"
                      strokeDasharray="4,4"
                    />
                    <text
                      x={PADDING.left + chartMetrics.innerWidth + 5}
                      y={y + 4}
                      fill="#888"
                      fontSize="10"
                    >
                      {price.toFixed(price < 1 ? 8 : 2)}
                    </text>
                  </g>
                );
              })}

              {/* Threshold Line in Indicator Area */}
              <line
                x1={PADDING.left}
                y1={getIndicatorY(threshold)}
                x2={PADDING.left + chartMetrics.innerWidth}
                y2={getIndicatorY(threshold)}
                stroke="#ff9800"
                strokeWidth="2"
                strokeDasharray="8,4"
              />
              <text
                x={PADDING.left + chartMetrics.innerWidth + 5}
                y={getIndicatorY(threshold) + 4}
                fill="#ff9800"
                fontSize="10"
                fontWeight="bold"
              >
                {threshold}%
              </text>

              {/* Zero Line in Indicator Area */}
              <line
                x1={PADDING.left}
                y1={getIndicatorY(0)}
                x2={PADDING.left + chartMetrics.innerWidth}
                y2={getIndicatorY(0)}
                stroke="#666"
                strokeWidth="1"
              />

              {/* Pump Event Highlights */}
              {pumps.map((pump, i) => {
                const startIndex = ohlcvData.findIndex(d => d.timestamp >= pump.startTime);
                const pumpEndTime = pump.endTime;
                const endIndex = pumpEndTime !== undefined
                  ? ohlcvData.findIndex(d => d.timestamp >= pumpEndTime)
                  : ohlcvData.length - 1;

                if (startIndex === -1) return null;

                const x1 = getX(startIndex);
                const x2 = getX(Math.min(endIndex, ohlcvData.length - 1));

                return (
                  <g key={`pump-${i}`}>
                    <rect
                      x={x1}
                      y={PADDING.top}
                      width={Math.max(x2 - x1, 10)}
                      height={PRICE_HEIGHT}
                      fill="rgba(255, 152, 0, 0.15)"
                    />
                    <rect
                      x={x1}
                      y={PADDING.top + PRICE_HEIGHT + 20}
                      width={Math.max(x2 - x1, 10)}
                      height={INDICATOR_HEIGHT}
                      fill="rgba(255, 152, 0, 0.15)"
                    />
                  </g>
                );
              })}

              {/* Candlesticks */}
              {ohlcvData.map((candle, i) => {
                const x = getX(i);
                const isGreen = candle.close >= candle.open;
                const color = isGreen ? '#26a69a' : '#ef5350';

                return (
                  <g key={`candle-${i}`}>
                    {/* Wick */}
                    <line
                      x1={x}
                      y1={getPriceY(candle.high)}
                      x2={x}
                      y2={getPriceY(candle.low)}
                      stroke={color}
                      strokeWidth="1"
                    />
                    {/* Body */}
                    <rect
                      x={x - chartMetrics.candleWidth / 2}
                      y={getPriceY(Math.max(candle.open, candle.close))}
                      width={chartMetrics.candleWidth}
                      height={Math.max(1, Math.abs(getPriceY(candle.open) - getPriceY(candle.close)))}
                      fill={color}
                    />
                  </g>
                );
              })}

              {/* Indicator Line */}
              <path
                d={indicatorData.map((point, i) => {
                  const x = getX(i);
                  const y = getIndicatorY(point.value);
                  return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                }).join(' ')}
                fill="none"
                stroke="#2196f3"
                strokeWidth="2"
              />

              {/* Indicator Area Fill */}
              <path
                d={[
                  `M ${getX(0)} ${getIndicatorY(0)}`,
                  ...indicatorData.map((point, i) => {
                    const x = getX(i);
                    const y = getIndicatorY(point.value);
                    return `L ${x} ${y}`;
                  }),
                  `L ${getX(indicatorData.length - 1)} ${getIndicatorY(0)}`,
                  'Z',
                ].join(' ')}
                fill="rgba(33, 150, 243, 0.2)"
              />

              {/* Trigger Points */}
              {indicatorData.map((point, i) => {
                if (!point.isTrigger) return null;
                const x = getX(i);
                const y = getIndicatorY(point.value);
                return (
                  <circle
                    key={`trigger-${i}`}
                    cx={x}
                    cy={y}
                    r="4"
                    fill="#ff5722"
                    stroke="#fff"
                    strokeWidth="1"
                  />
                );
              })}

              {/* Labels */}
              <text
                x={PADDING.left}
                y={PADDING.top - 5}
                fill="#888"
                fontSize="12"
              >
                Price ({symbol.replace('_', '/')})
              </text>
              <text
                x={PADDING.left}
                y={PADDING.top + PRICE_HEIGHT + 15}
                fill="#2196f3"
                fontSize="12"
              >
                {variant.baseType || 'Indicator'} Value (%)
              </text>

              {/* Axis Labels */}
              <text
                x={PADDING.left - 5}
                y={CHART_HEIGHT - 5}
                fill="#888"
                fontSize="10"
                textAnchor="end"
              >
                200 bars
              </text>
            </svg>
          </Box>
        ) : (
          <Alert severity="warning">No data available</Alert>
        )}

        {variant && (
          <>
        <Divider sx={{ my: 2 }} />

        {/* Interpretation */}
        <Alert
          severity={pumps.length >= 3 ? 'success' : pumps.length >= 1 ? 'info' : 'warning'}
          sx={{ mt: 2 }}
        >
          <Typography variant="body2">
            <strong>Interpretation:</strong>{' '}
            {variant.name.toLowerCase().includes('fast') ? (
              <>
                This <strong>Fast</strong> variant reacts quickly to price movements.
                It detected {pumps.length} pump events with {triggerCount} total trigger points.
                Fast variants are ideal for catching early pump signals but may produce more false positives.
              </>
            ) : variant.name.toLowerCase().includes('slow') ? (
              <>
                This <strong>Slow</strong> variant filters out noise and only triggers on significant moves.
                It detected {pumps.length} pump events with {triggerCount} total trigger points.
                Slow variants are more reliable but may miss the initial phase of pumps.
              </>
            ) : (
              <>
                This <strong>Medium</strong> variant provides balanced sensitivity.
                It detected {pumps.length} pump events with {triggerCount} total trigger points.
                Good for general use with reasonable accuracy and timing.
              </>
            )}
          </Typography>
        </Alert>

        {/* Pump Summary */}
        {pumps.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Detected Pumps
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {pumps.slice(0, 5).map((pump, i) => (
                <Chip
                  key={i}
                  label={`+${pump.magnitude.toFixed(1)}%`}
                  color={pump.magnitude >= threshold ? 'success' : 'default'}
                  size="small"
                  variant={pump.magnitude >= threshold ? 'filled' : 'outlined'}
                />
              ))}
              {pumps.length > 5 && (
                <Chip
                  label={`+${pumps.length - 5} more`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Stack>
          </Box>
        )}
          </>
        )}
      </Collapse>
    </Paper>
  );
};

export default VariantChartPreview;
