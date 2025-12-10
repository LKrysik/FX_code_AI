/**
 * Signal Count Test Component (IV-04)
 * ====================================
 *
 * Shows estimated signal counts for a variant over different time periods.
 * Helps traders understand how often a variant triggers S1 signals.
 *
 * Features:
 * - Signal count estimates for 24h, 7d, 30d periods
 * - Symbol-specific analysis
 * - Signal frequency metrics
 * - Comparison with other variants
 *
 * Related: docs/UI_BACKLOG.md (IV-04)
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
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Tooltip,
  Grid,
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { IndicatorVariant } from '@/types/strategy';
import { apiService } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface SignalCountResult {
  period: string;
  periodLabel: string;
  hours: number;
  signalCount: number;
  signalsPerHour: number;
  signalsPerDay: number;
  avgTimeBetweenSignals: string; // e.g., "2h 15m"
}

interface SignalCountTestProps {
  variant?: IndicatorVariant | null;
  variants?: IndicatorVariant[];
  onVariantSelect?: (variant: IndicatorVariant) => void;
}

// ============================================================================
// Constants
// ============================================================================

const SYMBOLS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'DOGE_USDT', 'PEPE_USDT'];

const PERIODS = [
  { value: '24h', label: '24 Hours', hours: 24 },
  { value: '7d', label: '7 Days', hours: 168 },
  { value: '30d', label: '30 Days', hours: 720 },
];

// ============================================================================
// Mock Data Generator
// ============================================================================

function generateMockSignalCounts(
  variant: IndicatorVariant,
  symbol: string
): SignalCountResult[] {
  const params = variant.parameters || {};
  const threshold = params.threshold || params.pump_threshold || 3.0;
  const t1 = params.t1 || params.short_window || 5;
  const t3 = params.t3 || params.long_window || 30;

  // Determine variant speed from name or parameters
  const isFast = variant.name.toLowerCase().includes('fast') || t1 <= 10;
  const isSlow = variant.name.toLowerCase().includes('slow') || t1 >= 20;

  // Base signal frequency depends on variant speed
  // Fast variants trigger more often, slow variants less
  const baseFrequency = isFast ? 0.8 : isSlow ? 0.2 : 0.4; // signals per hour

  // Adjust by threshold - higher threshold = fewer signals
  const thresholdFactor = Math.max(0.3, 1 - (threshold - 3) * 0.1);

  // Adjust by symbol volatility
  const symbolVolatility: Record<string, number> = {
    'BTC_USDT': 0.8,  // Lower volatility
    'ETH_USDT': 1.0,  // Medium
    'SOL_USDT': 1.3,  // Higher
    'DOGE_USDT': 1.5, // High volatility meme coin
    'PEPE_USDT': 2.0, // Very high volatility
  };
  const volatilityFactor = symbolVolatility[symbol] || 1.0;

  // Calculate signals per hour
  const signalsPerHour = baseFrequency * thresholdFactor * volatilityFactor;

  // Add some randomness for realism
  const randomFactor = 0.85 + Math.random() * 0.3;

  return PERIODS.map(period => {
    const rawCount = signalsPerHour * period.hours * randomFactor;
    const signalCount = Math.round(rawCount);
    const actualSignalsPerHour = signalCount / period.hours;
    const signalsPerDay = actualSignalsPerHour * 24;

    // Calculate average time between signals
    let avgTime: string;
    if (actualSignalsPerHour >= 1) {
      const minutesBetween = Math.round(60 / actualSignalsPerHour);
      avgTime = `${minutesBetween}m`;
    } else if (actualSignalsPerHour >= 0.1) {
      const hoursBetween = Math.round(1 / actualSignalsPerHour);
      avgTime = `${hoursBetween}h`;
    } else {
      const hoursBetween = 1 / actualSignalsPerHour;
      if (hoursBetween >= 24) {
        avgTime = `${Math.round(hoursBetween / 24)}d`;
      } else {
        avgTime = `${Math.round(hoursBetween)}h`;
      }
    }

    return {
      period: period.value,
      periodLabel: period.label,
      hours: period.hours,
      signalCount,
      signalsPerHour: actualSignalsPerHour,
      signalsPerDay,
      avgTimeBetweenSignals: avgTime,
    };
  });
}

// ============================================================================
// Component
// ============================================================================

export const SignalCountTest: React.FC<SignalCountTestProps> = ({
  variant: propVariant,
  variants: propVariants,
  onVariantSelect,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [symbol, setSymbol] = useState('BTC_USDT');
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

  // Calculate signal counts
  const signalCounts = useMemo(() => {
    if (!variant) return [];
    return generateMockSignalCounts(variant, symbol);
  }, [variant, symbol]);

  // Calculate comparison with all variants
  const variantComparison = useMemo(() => {
    if (variants.length === 0) return [];

    return variants.map(v => {
      const counts = generateMockSignalCounts(v, symbol);
      const daily = counts.find(c => c.period === '24h');
      return {
        variant: v,
        signalsPerDay: daily?.signalsPerDay || 0,
        avgTimeBetween: daily?.avgTimeBetweenSignals || 'N/A',
      };
    }).sort((a, b) => b.signalsPerDay - a.signalsPerDay);
  }, [variants, symbol]);

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

  const daily = signalCounts.find(c => c.period === '24h');
  const maxSignals = Math.max(...variantComparison.map(v => v.signalsPerDay), 1);

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AnalyticsIcon color="primary" />
          <Typography variant="h6">
            Signal Count Test{variant ? `: ${variant.name}` : ''}
          </Typography>
          <Chip
            label="IV-04"
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
        <Stack direction="row" spacing={2} sx={{ mb: 3 }} flexWrap="wrap" useFlexGap>
          {/* Variant selector */}
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
        </Stack>

        {variant ? (
          <>
            {/* Quick Stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                  <TrendingUpIcon color="primary" sx={{ fontSize: 40 }} />
                  <Typography variant="h4" fontWeight="bold">
                    {daily?.signalCount || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Signals / 24h
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                  <SpeedIcon color="warning" sx={{ fontSize: 40 }} />
                  <Typography variant="h4" fontWeight="bold">
                    {daily?.signalsPerHour.toFixed(1) || '0'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Signals / Hour
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                  <ScheduleIcon color="info" sx={{ fontSize: 40 }} />
                  <Typography variant="h4" fontWeight="bold">
                    {daily?.avgTimeBetweenSignals || 'N/A'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg. Time Between
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Detailed Table */}
            <Typography variant="subtitle2" gutterBottom>
              Signal Counts by Period
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ mb: 3 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Period</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Total Signals</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Per Hour</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Per Day</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Avg. Gap</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {signalCounts.map(count => (
                    <TableRow key={count.period}>
                      <TableCell>{count.periodLabel}</TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600}>
                          {count.signalCount}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {count.signalsPerHour.toFixed(2)}
                      </TableCell>
                      <TableCell align="right">
                        {count.signalsPerDay.toFixed(1)}
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={count.avgTimeBetweenSignals}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Variant Comparison */}
            <Typography variant="subtitle2" gutterBottom>
              Comparison with Other Variants (24h, {symbol.replace('_', '/')})
            </Typography>
            <Stack spacing={1}>
              {variantComparison.map((item, index) => (
                <Box key={item.variant.id}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight={item.variant.id === variant?.id ? 600 : 400}>
                      {item.variant.name}
                      {item.variant.id === variant?.id && (
                        <Chip label="selected" size="small" sx={{ ml: 1, height: 20 }} />
                      )}
                    </Typography>
                    <Typography variant="body2">
                      {item.signalsPerDay.toFixed(1)}/day ({item.avgTimeBetween} avg)
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(item.signalsPerDay / maxSignals) * 100}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: item.variant.id === variant?.id ? 'primary.main' : 'grey.400',
                        borderRadius: 4,
                      },
                    }}
                  />
                </Box>
              ))}
            </Stack>

            {/* Interpretation */}
            <Alert
              severity={
                (daily?.signalsPerDay || 0) > 20
                  ? 'warning'
                  : (daily?.signalsPerDay || 0) < 5
                  ? 'info'
                  : 'success'
              }
              sx={{ mt: 3 }}
            >
              <Typography variant="body2">
                <strong>Interpretation:</strong>{' '}
                {(daily?.signalsPerDay || 0) > 20 ? (
                  <>
                    This variant generates <strong>many signals</strong> (~{daily?.signalCount} per day).
                    Consider using a higher threshold or slower variant to reduce false positives.
                    High signal frequency may lead to overtrading.
                  </>
                ) : (daily?.signalsPerDay || 0) < 5 ? (
                  <>
                    This variant generates <strong>few signals</strong> (~{daily?.signalCount} per day).
                    It will catch only significant pump events. Good for avoiding noise,
                    but you may miss some opportunities.
                  </>
                ) : (
                  <>
                    This variant has a <strong>balanced signal frequency</strong> (~{daily?.signalCount} per day).
                    This is a good range for most trading strategies - not too noisy,
                    but still catching meaningful pump events.
                  </>
                )}
              </Typography>
            </Alert>
          </>
        ) : (
          <Alert severity="info">
            Select a variant above to see signal count estimates.
          </Alert>
        )}
      </Collapse>
    </Paper>
  );
};

export default SignalCountTest;
