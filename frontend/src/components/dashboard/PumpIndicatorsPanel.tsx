'use client';

/**
 * PumpIndicatorsPanel Component (PI-01, PI-02, PI-03)
 * ====================================================
 *
 * Dedicated panel for displaying pump/dump detection indicators.
 *
 * Features:
 * - PI-01: PUMP_MAGNITUDE and PRICE_VELOCITY as large, prominent numbers
 * - PI-02: Velocity trend arrows showing acceleration/deceleration
 * - PI-03: Mini time-series chart showing indicator history
 *
 * Architecture:
 * - Fetches from GET /api/indicators/current (filtered by indicator type)
 * - WebSocket subscription for real-time updates
 * - Stores last N values for trend calculation and mini-chart
 *
 * Related: docs/UI_BACKLOG.md - PI-01, PI-02, PI-03
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Box,
  Paper,
  Typography,
  Skeleton,
  Tooltip,
  Chip,
  alpha,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  ShowChart as ShowChartIcon,
  Speed as SpeedIcon,
  LocalFireDepartment as FireIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface PumpIndicatorValue {
  indicator_type: string;
  value: number;
  timestamp: string;
  threshold?: number;
}

export interface PumpIndicatorsPanelProps {
  sessionId: string | null;
  symbol: string;
  refreshInterval?: number; // milliseconds
}

interface HistoricalValue {
  timestamp: number;
  value: number;
}

// ============================================================================
// Constants
// ============================================================================

const HISTORY_SIZE = 60; // Keep last 60 values for trend and chart
const TREND_WINDOW = 5; // Use last 5 values for trend calculation

// Color thresholds for pump magnitude
const PUMP_THRESHOLDS = {
  LOW: 2, // 2% - mild movement
  MEDIUM: 5, // 5% - significant movement
  HIGH: 10, // 10% - major pump
  EXTREME: 20, // 20% - extreme pump
};

// Color thresholds for velocity (% per second)
const VELOCITY_THRESHOLDS = {
  LOW: 0.05,
  MEDIUM: 0.1,
  HIGH: 0.2,
  EXTREME: 0.5,
};

// ============================================================================
// Helper Functions
// ============================================================================

function getColorForMagnitude(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= PUMP_THRESHOLDS.EXTREME) return '#d32f2f'; // Deep red
  if (absValue >= PUMP_THRESHOLDS.HIGH) return '#f44336'; // Red
  if (absValue >= PUMP_THRESHOLDS.MEDIUM) return '#ff9800'; // Orange
  if (absValue >= PUMP_THRESHOLDS.LOW) return '#ffeb3b'; // Yellow
  return '#4caf50'; // Green (normal)
}

function getColorForVelocity(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= VELOCITY_THRESHOLDS.EXTREME) return '#d32f2f';
  if (absValue >= VELOCITY_THRESHOLDS.HIGH) return '#f44336';
  if (absValue >= VELOCITY_THRESHOLDS.MEDIUM) return '#ff9800';
  if (absValue >= VELOCITY_THRESHOLDS.LOW) return '#ffeb3b';
  return '#4caf50';
}

function formatValue(value: number, decimals: number = 2): string {
  if (Math.abs(value) >= 100) {
    return value.toFixed(1);
  }
  if (Math.abs(value) >= 10) {
    return value.toFixed(decimals);
  }
  return value.toFixed(decimals + 1);
}

function calculateTrend(history: HistoricalValue[]): 'up' | 'down' | 'flat' {
  if (history.length < 2) return 'flat';

  const recent = history.slice(-TREND_WINDOW);
  if (recent.length < 2) return 'flat';

  // Calculate simple linear regression slope
  const n = recent.length;
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += recent[i].value;
    sumXY += i * recent[i].value;
    sumX2 += i * i;
  }

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);

  // Threshold for considering trend significant
  if (slope > 0.01) return 'up';
  if (slope < -0.01) return 'down';
  return 'flat';
}

// ============================================================================
// Mini Sparkline Component (PI-03)
// ============================================================================

interface SparklineProps {
  data: HistoricalValue[];
  width?: number;
  height?: number;
  color: string;
  showArea?: boolean;
}

const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 40,
  color,
  showArea = true,
}) => {
  if (data.length < 2) {
    return (
      <Box
        sx={{
          width,
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: alpha('#ffffff', 0.05),
          borderRadius: 1,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Collecting data...
        </Typography>
      </Box>
    );
  }

  const values = data.map((d) => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;

  // Normalize values to SVG coordinates
  const padding = 4;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * chartWidth;
    const y = padding + chartHeight - ((d.value - minValue) / range) * chartHeight;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${padding + chartWidth},${padding + chartHeight} L ${padding},${padding + chartHeight} Z`;

  return (
    <svg width={width} height={height}>
      {showArea && (
        <path d={areaD} fill={alpha(color, 0.2)} stroke="none" />
      )}
      <path d={pathD} fill="none" stroke={color} strokeWidth={2} />
      {/* Current value dot */}
      {data.length > 0 && (
        <circle
          cx={padding + chartWidth}
          cy={
            padding +
            chartHeight -
            ((data[data.length - 1].value - minValue) / range) * chartHeight
          }
          r={3}
          fill={color}
        />
      )}
    </svg>
  );
};

// ============================================================================
// Trend Arrow Component (PI-02)
// ============================================================================

interface TrendArrowProps {
  trend: 'up' | 'down' | 'flat';
  color: string;
}

const TrendArrow: React.FC<TrendArrowProps> = ({ trend, color }) => {
  const iconProps = {
    sx: {
      fontSize: 28,
      color,
      animation: trend !== 'flat' ? 'pulse 1.5s ease-in-out infinite' : 'none',
      '@keyframes pulse': {
        '0%, 100%': { opacity: 1 },
        '50%': { opacity: 0.5 },
      },
    },
  };

  switch (trend) {
    case 'up':
      return (
        <Tooltip title="Accelerating (pump intensifying)">
          <TrendingUpIcon {...iconProps} />
        </Tooltip>
      );
    case 'down':
      return (
        <Tooltip title="Decelerating (pump weakening)">
          <TrendingDownIcon {...iconProps} />
        </Tooltip>
      );
    default:
      return (
        <Tooltip title="Stable">
          <TrendingFlatIcon {...iconProps} />
        </Tooltip>
      );
  }
};

// ============================================================================
// Single Indicator Card Component (PI-01)
// ============================================================================

interface IndicatorCardProps {
  title: string;
  value: number | null;
  unit: string;
  icon: React.ReactNode;
  color: string;
  history: HistoricalValue[];
  threshold?: number;
  isLoading?: boolean;
}

const IndicatorCard: React.FC<IndicatorCardProps> = ({
  title,
  value,
  unit,
  icon,
  color,
  history,
  threshold,
  isLoading,
}) => {
  const trend = calculateTrend(history);
  const isAboveThreshold = threshold !== undefined && value !== null && Math.abs(value) >= threshold;

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: alpha(color, 0.1),
        border: '2px solid',
        borderColor: isAboveThreshold ? color : alpha(color, 0.3),
        borderRadius: 2,
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 0.3s ease',
        ...(isAboveThreshold && {
          boxShadow: `0 0 20px ${alpha(color, 0.4)}`,
          animation: 'glow 2s ease-in-out infinite',
          '@keyframes glow': {
            '0%, 100%': { boxShadow: `0 0 10px ${alpha(color, 0.3)}` },
            '50%': { boxShadow: `0 0 25px ${alpha(color, 0.5)}` },
          },
        }),
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Box sx={{ color }}>{icon}</Box>
        <Typography variant="subtitle2" fontWeight="bold" sx={{ color }}>
          {title}
        </Typography>
        {isAboveThreshold && (
          <Chip
            label="ACTIVE"
            size="small"
            sx={{
              bgcolor: alpha(color, 0.2),
              color,
              fontWeight: 'bold',
              fontSize: '0.65rem',
              height: 20,
            }}
          />
        )}
      </Box>

      {/* Main Value (PI-01: Large prominent number) */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        {isLoading ? (
          <Skeleton variant="text" width={100} height={60} />
        ) : (
          <Typography
            variant="h3"
            fontWeight="bold"
            sx={{
              color,
              fontFamily: 'monospace',
              lineHeight: 1,
              textShadow: isAboveThreshold ? `0 0 10px ${color}` : 'none',
            }}
          >
            {value !== null ? formatValue(value) : '--'}
          </Typography>
        )}
        <Typography
          variant="h6"
          sx={{ color: alpha(color, 0.7), ml: -1 }}
        >
          {unit}
        </Typography>

        {/* Trend Arrow (PI-02) */}
        {!isLoading && value !== null && (
          <TrendArrow trend={trend} color={color} />
        )}
      </Box>

      {/* Threshold progress bar */}
      {threshold !== undefined && value !== null && (
        <Box sx={{ mb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Threshold: {threshold}{unit}
            </Typography>
            <Typography variant="caption" sx={{ color }}>
              {((Math.abs(value) / threshold) * 100).toFixed(0)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.min((Math.abs(value) / threshold) * 100, 100)}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: alpha(color, 0.1),
              '& .MuiLinearProgress-bar': {
                bgcolor: color,
                borderRadius: 3,
              },
            }}
          />
        </Box>
      )}

      {/* Mini sparkline chart (PI-03) */}
      <Box sx={{ mt: 1 }}>
        <Sparkline data={history} color={color} width={160} height={35} />
      </Box>
    </Paper>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const PumpIndicatorsPanel: React.FC<PumpIndicatorsPanelProps> = ({
  sessionId,
  symbol,
  refreshInterval = 2000, // 2 seconds for real-time feel
}) => {
  // ========================================
  // State
  // ========================================

  const [pumpMagnitude, setPumpMagnitude] = useState<number | null>(null);
  const [priceVelocity, setPriceVelocity] = useState<number | null>(null);
  const [magnitudeHistory, setMagnitudeHistory] = useState<HistoricalValue[]>([]);
  const [velocityHistory, setVelocityHistory] = useState<HistoricalValue[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs for history management (avoid stale closures)
  const magnitudeHistoryRef = useRef<HistoricalValue[]>([]);
  const velocityHistoryRef = useRef<HistoricalValue[]>([]);

  // ========================================
  // API Fetch
  // ========================================

  const fetchIndicators = useCallback(async () => {
    if (!sessionId) {
      setPumpMagnitude(null);
      setPriceVelocity(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/indicators/current?session_id=${sessionId}&symbol=${symbol}`
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      const data = result.data || result;
      const indicators = data.indicators || [];

      const now = Date.now();

      // Extract PUMP_MAGNITUDE_PCT
      const magnitudeIndicator = indicators.find(
        (ind: any) =>
          ind.indicator_name?.toLowerCase().includes('pump_magnitude') ||
          ind.indicator_id?.toLowerCase().includes('pump_magnitude')
      );
      if (magnitudeIndicator) {
        const value = magnitudeIndicator.value;
        setPumpMagnitude(value);

        // Update history
        magnitudeHistoryRef.current = [
          ...magnitudeHistoryRef.current.slice(-HISTORY_SIZE + 1),
          { timestamp: now, value },
        ];
        setMagnitudeHistory([...magnitudeHistoryRef.current]);
      }

      // Extract PRICE_VELOCITY
      const velocityIndicator = indicators.find(
        (ind: any) =>
          ind.indicator_name?.toLowerCase().includes('velocity') ||
          ind.indicator_id?.toLowerCase().includes('velocity')
      );
      if (velocityIndicator) {
        const value = velocityIndicator.value;
        setPriceVelocity(value);

        // Update history
        velocityHistoryRef.current = [
          ...velocityHistoryRef.current.slice(-HISTORY_SIZE + 1),
          { timestamp: now, value },
        ];
        setVelocityHistory([...velocityHistoryRef.current]);
      }
    } catch (err) {
      Logger.error('PumpIndicatorsPanel.fetch', { message: 'Fetch error', error: err });
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, symbol]);

  // ========================================
  // WebSocket Integration
  // ========================================

  useEffect(() => {
    if (!sessionId) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8080/ws';
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        Logger.debug('PumpIndicatorsPanel.wsConnected', { sessionId, symbol });
        ws?.send(
          JSON.stringify({
            type: 'subscribe',
            channel: 'indicators',
            session_id: sessionId,
            symbol: symbol,
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (
            message.type === 'indicator_update' &&
            message.session_id === sessionId &&
            message.symbol === symbol
          ) {
            const now = Date.now();

            // Update pump magnitude
            if (message.indicator_type?.toLowerCase().includes('pump_magnitude')) {
              setPumpMagnitude(message.value);
              magnitudeHistoryRef.current = [
                ...magnitudeHistoryRef.current.slice(-HISTORY_SIZE + 1),
                { timestamp: now, value: message.value },
              ];
              setMagnitudeHistory([...magnitudeHistoryRef.current]);
            }

            // Update velocity
            if (message.indicator_type?.toLowerCase().includes('velocity')) {
              setPriceVelocity(message.value);
              velocityHistoryRef.current = [
                ...velocityHistoryRef.current.slice(-HISTORY_SIZE + 1),
                { timestamp: now, value: message.value },
              ];
              setVelocityHistory([...velocityHistoryRef.current]);
            }
          }
        } catch (err) {
          Logger.error('PumpIndicatorsPanel.wsMessage', { message: 'WS message parse error', error: err });
        }
      };

      ws.onerror = (err) => {
        Logger.error('PumpIndicatorsPanel.wsError', { message: 'WebSocket error', error: err });
      };
    } catch (err) {
      Logger.error('PumpIndicatorsPanel.wsInit', { message: 'WebSocket init error', error: err });
    }

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: 'unsubscribe',
            channel: 'indicators',
            session_id: sessionId,
          })
        );
        ws.close();
      }
    };
  }, [sessionId, symbol]);

  // ========================================
  // Polling Fallback
  // ========================================

  useEffect(() => {
    fetchIndicators();

    const intervalId = setInterval(() => {
      fetchIndicators();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [fetchIndicators, refreshInterval]);

  // ========================================
  // Render
  // ========================================

  const magnitudeColor = pumpMagnitude !== null ? getColorForMagnitude(pumpMagnitude) : '#9e9e9e';
  const velocityColor = priceVelocity !== null ? getColorForVelocity(priceVelocity) : '#9e9e9e';

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <FireIcon sx={{ color: '#ff5722' }} />
        <Typography variant="h6" fontWeight="bold">
          Pump Indicators
        </Typography>
        <Chip
          label={symbol}
          size="small"
          variant="outlined"
          sx={{ ml: 'auto' }}
        />
      </Box>

      {!sessionId ? (
        <Typography variant="body2" color="text.secondary">
          No active session
        </Typography>
      ) : error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* PUMP_MAGNITUDE Card */}
          <IndicatorCard
            title="PUMP MAGNITUDE"
            value={pumpMagnitude}
            unit="%"
            icon={<ShowChartIcon />}
            color={magnitudeColor}
            history={magnitudeHistory}
            threshold={PUMP_THRESHOLDS.MEDIUM}
            isLoading={isLoading && pumpMagnitude === null}
          />

          {/* PRICE_VELOCITY Card */}
          <IndicatorCard
            title="PRICE VELOCITY"
            value={priceVelocity}
            unit="%/s"
            icon={<SpeedIcon />}
            color={velocityColor}
            history={velocityHistory}
            threshold={VELOCITY_THRESHOLDS.MEDIUM}
            isLoading={isLoading && priceVelocity === null}
          />
        </Box>
      )}
    </Paper>
  );
};

export default PumpIndicatorsPanel;
