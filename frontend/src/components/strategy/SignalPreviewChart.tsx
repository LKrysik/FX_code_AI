/**
 * SB-03: Signal Preview Chart Component
 *
 * Shows where S1 signals would trigger on historical chart data
 * based on strategy conditions.
 *
 * Features:
 * - Historical OHLCV chart (mock data)
 * - S1 signal markers showing where pump detection would trigger
 * - Z1 entry and O1 timeout predictions
 * - Visual legend explaining markers
 * - Symbol and timeframe selection
 * - Collapsible panel
 * - Mock data fallback for development
 *
 * Integration:
 * - Strategy Builder page (after QuickBacktestPreview)
 * - Requires strategy configuration to calculate signal positions
 *
 * Location: frontend/src/components/strategy/SignalPreviewChart.tsx
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  IconButton,
  Collapse,
  Chip,
  Stack,
  Divider,
  Alert,
} from '@mui/material';
import {
  ShowChart as ChartIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Info as InfoIcon,
  Circle as CircleIcon,
  Warning as WarningIcon,
  TrendingUp as PumpIcon,
  PlayArrow as EntryIcon,
  Cancel as TimeoutIcon,
} from '@mui/icons-material';
import { Strategy5Section } from '@/types/strategy';

// ============================================================================
// TYPES
// ============================================================================

interface OHLCVData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface SignalMarker {
  time: number;
  price: number;
  type: 'S1' | 'Z1' | 'O1';
  label: string;
}

interface SignalPreviewChartProps {
  strategy: Strategy5Section;
}

// ============================================================================
// MOCK DATA GENERATOR
// ============================================================================

function generateMockOHLCVData(
  symbol: string,
  timeframe: string,
  count: number = 200
): OHLCVData[] {
  const data: OHLCVData[] = [];
  const now = Math.floor(Date.now() / 1000);

  // Timeframe in seconds
  const tfSeconds = timeframe === '1m' ? 60 : timeframe === '5m' ? 300 : timeframe === '15m' ? 900 : 3600;

  // Base price based on symbol
  let basePrice = symbol === 'BTC_USDT' ? 45000 :
    symbol === 'ETH_USDT' ? 2500 :
    symbol === 'SOL_USDT' ? 100 :
    symbol === 'DOGE_USDT' ? 0.08 : 0.000012;

  // Generate candles with occasional pump patterns
  let price = basePrice;
  let inPump = false;
  let pumpDuration = 0;

  for (let i = 0; i < count; i++) {
    const time = now - (count - i) * tfSeconds;

    // Randomly start a pump (5% chance per candle)
    if (!inPump && Math.random() < 0.05) {
      inPump = true;
      pumpDuration = 5 + Math.floor(Math.random() * 10); // 5-15 candles
    }

    // Price movement
    let change: number;
    if (inPump && pumpDuration > 0) {
      // Pump phase - strong upward movement
      change = (0.5 + Math.random() * 1.5) / 100; // 0.5-2% up
      pumpDuration--;
      if (pumpDuration === 0) {
        inPump = false;
      }
    } else {
      // Normal trading - small random movement
      change = (Math.random() - 0.5) * 0.01; // -0.5% to +0.5%
    }

    price = price * (1 + change);

    // Generate OHLCV
    const volatility = inPump ? 0.015 : 0.005;
    const high = price * (1 + Math.random() * volatility);
    const low = price * (1 - Math.random() * volatility);
    const open = low + Math.random() * (high - low);
    const close = low + Math.random() * (high - low);
    const volume = 100000 + Math.random() * (inPump ? 500000 : 200000);

    data.push({
      time,
      open,
      high,
      low,
      close,
      volume,
    });
  }

  return data;
}

function detectSignals(
  data: OHLCVData[],
  strategy: Strategy5Section
): SignalMarker[] {
  const signals: SignalMarker[] = [];
  const lookback = 5; // Candles to look back for pump detection

  // Simple pump detection heuristic based on strategy
  const hasS1Conditions = strategy.s1_signal?.conditions?.length > 0;
  const o1Timeout = strategy.o1_cancel?.timeoutSeconds || 30;

  if (!hasS1Conditions) {
    return signals;
  }

  // Calculate magnitude threshold (mock based on strategy complexity)
  const s1ConditionCount = strategy.s1_signal.conditions.length;
  const magnitudeThreshold = 2 + s1ConditionCount * 0.5; // 2-5% based on conditions

  for (let i = lookback; i < data.length - 5; i++) {
    const candle = data[i];

    // Calculate price change over lookback period
    const prevPrice = data[i - lookback].close;
    const priceChange = ((candle.close - prevPrice) / prevPrice) * 100;

    // Detect pump (S1 signal)
    if (priceChange >= magnitudeThreshold) {
      // Check if we already have a signal nearby (avoid duplicates)
      const recentSignal = signals.find(
        s => Math.abs(s.time - candle.time) < 300 // Within 5 minutes
      );

      if (!recentSignal) {
        signals.push({
          time: candle.time,
          price: candle.high,
          type: 'S1',
          label: `Pump ${priceChange.toFixed(1)}%`,
        });

        // Predict Z1 or O1 based on subsequent candles
        let entryFound = false;
        for (let j = 1; j <= 5 && i + j < data.length; j++) {
          const futureCandle = data[i + j];
          const futureChange = ((futureCandle.close - candle.close) / candle.close) * 100;

          // If price drops (good for SHORT), Z1 triggers
          if (futureChange < -1) {
            signals.push({
              time: futureCandle.time,
              price: futureCandle.low,
              type: 'Z1',
              label: 'Entry',
            });
            entryFound = true;
            break;
          }
        }

        // If no entry within timeout, O1 triggers
        if (!entryFound && i + 5 < data.length) {
          signals.push({
            time: data[i + 5].time,
            price: data[i + 5].close,
            type: 'O1',
            label: 'Timeout',
          });
        }
      }
    }
  }

  return signals;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const SignalPreviewChart: React.FC<SignalPreviewChartProps> = ({
  strategy,
}) => {
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [symbol, setSymbol] = useState('BTC_USDT');
  const [timeframe, setTimeframe] = useState('5m');
  const [ohlcvData, setOhlcvData] = useState<OHLCVData[]>([]);
  const [signals, setSignals] = useState<SignalMarker[]>([]);

  const symbols = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'DOGE_USDT', 'PEPE_USDT'];
  const timeframes = ['1m', '5m', '15m', '1h'];

  const loadData = useCallback(async () => {
    setLoading(true);

    try {
      // Try to fetch from API first
      const response = await fetch(
        `/api/market-data/ohlcv?symbol=${symbol}&timeframe=${timeframe}&limit=200`
      );

      if (response.ok) {
        const apiData = await response.json();
        setOhlcvData(apiData);
        setSignals(detectSignals(apiData, strategy));
      } else {
        // Fallback to mock data
        await new Promise(resolve => setTimeout(resolve, 800));
        const mockData = generateMockOHLCVData(symbol, timeframe, 200);
        setOhlcvData(mockData);
        setSignals(detectSignals(mockData, strategy));
      }
    } catch {
      // Fallback to mock data on error
      await new Promise(resolve => setTimeout(resolve, 800));
      const mockData = generateMockOHLCVData(symbol, timeframe, 200);
      setOhlcvData(mockData);
      setSignals(detectSignals(mockData, strategy));
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, strategy]);

  // Load data when expanded or settings change
  useEffect(() => {
    if (expanded) {
      loadData();
    }
  }, [expanded, loadData]);

  // Signal counts
  const signalCounts = useMemo(() => {
    const counts = { S1: 0, Z1: 0, O1: 0 };
    signals.forEach(s => counts[s.type]++);
    return counts;
  }, [signals]);

  // Mini chart rendering (SVG-based)
  const chartHeight = 200;
  const chartWidth = 800;

  const renderChart = () => {
    if (ohlcvData.length === 0) return null;

    const minPrice = Math.min(...ohlcvData.map(d => d.low));
    const maxPrice = Math.max(...ohlcvData.map(d => d.high));
    const priceRange = maxPrice - minPrice;

    const scaleY = (price: number) =>
      chartHeight - ((price - minPrice) / priceRange) * chartHeight;

    const scaleX = (index: number) =>
      (index / (ohlcvData.length - 1)) * chartWidth;

    // Generate candlestick path
    const candleWidth = Math.max(1, chartWidth / ohlcvData.length - 1);

    return (
      <svg width={chartWidth} height={chartHeight + 40} style={{ background: '#1e1e1e' }}>
        {/* Price grid */}
        {[0.25, 0.5, 0.75].map(ratio => (
          <line
            key={ratio}
            x1={0}
            y1={ratio * chartHeight}
            x2={chartWidth}
            y2={ratio * chartHeight}
            stroke="#333"
            strokeDasharray="4,4"
          />
        ))}

        {/* Candlesticks */}
        {ohlcvData.map((candle, i) => {
          const x = scaleX(i);
          const isGreen = candle.close >= candle.open;
          const color = isGreen ? '#00c853' : '#ff1744';
          const bodyTop = scaleY(Math.max(candle.open, candle.close));
          const bodyBottom = scaleY(Math.min(candle.open, candle.close));
          const bodyHeight = Math.max(1, bodyBottom - bodyTop);

          return (
            <g key={i}>
              {/* Wick */}
              <line
                x1={x}
                y1={scaleY(candle.high)}
                x2={x}
                y2={scaleY(candle.low)}
                stroke={color}
                strokeWidth={1}
              />
              {/* Body */}
              <rect
                x={x - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={color}
              />
            </g>
          );
        })}

        {/* Signal markers */}
        {signals.map((signal, i) => {
          const dataIndex = ohlcvData.findIndex(d => d.time === signal.time);
          if (dataIndex < 0) return null;

          const x = scaleX(dataIndex);
          const y = scaleY(signal.price);

          const color = signal.type === 'S1' ? '#ff9800' :
            signal.type === 'Z1' ? '#4caf50' : '#9e9e9e';

          const markerSize = 8;

          return (
            <g key={`signal-${i}`}>
              {/* Marker circle */}
              <circle
                cx={x}
                cy={y}
                r={markerSize}
                fill={color}
                opacity={0.9}
              />
              {/* Triangle for S1 */}
              {signal.type === 'S1' && (
                <polygon
                  points={`${x},${y - 15} ${x - 5},${y - 8} ${x + 5},${y - 8}`}
                  fill={color}
                />
              )}
              {/* Text label */}
              <text
                x={x}
                y={y - 20}
                textAnchor="middle"
                fill={color}
                fontSize={10}
                fontWeight="bold"
              >
                {signal.type}
              </text>
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(10, ${chartHeight + 10})`}>
          <circle cx={8} cy={12} r={6} fill="#ff9800" />
          <text x={20} y={16} fill="#fff" fontSize={11}>S1 - Pump Detected</text>

          <circle cx={150} cy={12} r={6} fill="#4caf50" />
          <text x={162} y={16} fill="#fff" fontSize={11}>Z1 - Entry</text>

          <circle cx={250} cy={12} r={6} fill="#9e9e9e" />
          <text x={262} y={16} fill="#fff" fontSize={11}>O1 - Timeout</text>
        </g>
      </svg>
    );
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ChartIcon color="primary" />
          <Typography variant="h6">Signal Preview Chart</Typography>
          <Tooltip title="SB-03: Shows where S1 signals would trigger on historical data based on your strategy">
            <IconButton size="small">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {!expanded && signalCounts.S1 > 0 && (
            <Stack direction="row" spacing={0.5}>
              <Chip
                size="small"
                label={`${signalCounts.S1} S1`}
                color="warning"
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${signalCounts.Z1} Z1`}
                color="success"
                variant="outlined"
              />
            </Stack>
          )}
          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded}>
        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Symbol</InputLabel>
            <Select
              value={symbol}
              label="Symbol"
              onChange={(e) => setSymbol(e.target.value)}
            >
              {symbols.map(s => (
                <MenuItem key={s} value={s}>{s}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select
              value={timeframe}
              label="Timeframe"
              onChange={(e) => setTimeframe(e.target.value)}
            >
              {timeframes.map(tf => (
                <MenuItem key={tf} value={tf}>{tf}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            size="small"
            startIcon={loading ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={loadData}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>

        {/* Signal Summary */}
        {signals.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Stack direction="row" spacing={2}>
              <Chip
                icon={<PumpIcon />}
                label={`${signalCounts.S1} S1 Signals (Pump Detected)`}
                color="warning"
                variant="filled"
              />
              <Chip
                icon={<EntryIcon />}
                label={`${signalCounts.Z1} Z1 Entries (Position Opened)`}
                color="success"
                variant="filled"
              />
              <Chip
                icon={<TimeoutIcon />}
                label={`${signalCounts.O1} O1 Timeouts (Entry Cancelled)`}
                color="default"
                variant="filled"
              />
            </Stack>
          </Box>
        )}

        {/* Chart */}
        {loading ? (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <CircularProgress size={40} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Loading historical data for {symbol}...
            </Typography>
          </Box>
        ) : ohlcvData.length > 0 ? (
          <Box sx={{ overflowX: 'auto', borderRadius: 1, border: 1, borderColor: 'divider' }}>
            {renderChart()}
          </Box>
        ) : (
          <Alert severity="info">
            No data available. Configure your strategy with S1 conditions and click Refresh.
          </Alert>
        )}

        {/* Interpretation */}
        {signals.length > 0 && (
          <Alert
            severity={
              signalCounts.Z1 / signalCounts.S1 >= 0.6 ? 'success' :
              signalCounts.Z1 / signalCounts.S1 >= 0.4 ? 'info' : 'warning'
            }
            sx={{ mt: 2 }}
          >
            <Typography variant="body2">
              <strong>Entry Rate: {((signalCounts.Z1 / signalCounts.S1) * 100).toFixed(0)}%</strong>
              {' - '}
              {signalCounts.Z1 / signalCounts.S1 >= 0.6 ? (
                'Good signal-to-entry conversion. Strategy conditions look well-tuned.'
              ) : signalCounts.Z1 / signalCounts.S1 >= 0.4 ? (
                'Moderate entry rate. Consider adjusting Z1 conditions or O1 timeout.'
              ) : (
                'Low entry rate. Many signals timeout before entry. Review conditions.'
              )}
            </Typography>
          </Alert>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Info */}
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          <em>
            This preview uses simplified detection based on price momentum.
            Actual signals depend on your configured indicator variants.
            Mock data - backend integration pending.
          </em>
        </Typography>
      </Collapse>
    </Paper>
  );
};

export default SignalPreviewChart;
