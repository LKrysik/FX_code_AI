/**
 * Candlestick Chart Component
 * ===========================
 *
 * Lightweight trading chart using TradingView's lightweight-charts library.
 *
 * Features:
 * - Real-time candlestick display
 * - Volume bars
 * - Signal markers overlay
 * - Responsive sizing
 * - Interactive zoom (mouse wheel)
 * - Pan/scroll (drag to scroll)
 * - Reset zoom button
 *
 * Performance:
 * - Optimized for 1000+ candles
 * - Hardware-accelerated rendering
 * - Incremental updates
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 */

import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, CircularProgress, Alert, IconButton } from '@mui/material';
import { ZoomOutMap as ResetZoomIcon } from '@mui/icons-material';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';

// ============================================================================
// Types
// ============================================================================

export interface CandleData {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface SignalMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown';
  text: string;
}

export interface CandlestickChartProps {
  symbol: string;
  sessionId: string | null;
  height?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

// ============================================================================
// Component
// ============================================================================

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  symbol,
  sessionId,
  height = 400,
  autoRefresh = true,
  refreshInterval = 10000, // 10 seconds
}) => {
  // ========================================
  // State
  // ========================================

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [candleData, setCandleData] = useState<CandleData[]>([]);

  // ========================================
  // Data Loading
  // ========================================

  // AbortController ref for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadChartData = async () => {
    if (!sessionId) return;

    // Abort previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      // Load OHLCV data from backend
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const ohlcvResponse = await fetch(
        `${apiUrl}/api/chart/ohlcv?session_id=${sessionId}&symbol=${symbol}&interval=1m&limit=500`,
        { signal: abortControllerRef.current.signal }
      );

      if (!ohlcvResponse.ok) {
        throw new Error(`Failed to load OHLCV data: ${ohlcvResponse.statusText}`);
      }

      const ohlcvResult = await ohlcvResponse.json();
      const ohlcvData = ohlcvResult.data || ohlcvResult;

      // Validate real data - no fallback to mock
      if (!ohlcvData.candles || ohlcvData.candles.length === 0) {
        console.warn('No OHLCV data available for', symbol);
        setCandleData([]);
        setError('No chart data available. Start data collection to see chart.');
      } else {
        setCandleData(ohlcvData.candles);
        setError(null);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      console.error('Failed to load chart data:', err);
      setCandleData([]);
      setError(`Failed to load chart data: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  // ========================================
  // Chart Initialization
  // ========================================

  // Initialize lightweight-charts instance
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart with zoom/pan enabled
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
        secondsVisible: false,
        // Enable zoom and scroll
        rightOffset: 12,
        barSpacing: 6,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      handleScroll: {
        mouseWheel: true, // Enable zoom with mouse wheel
        pressedMouseMove: true, // Enable pan with drag
        horzTouchDrag: true, // Enable touch drag on mobile
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: {
          time: true,
          price: true,
        },
        axisDoubleClickReset: {
          time: true,
          price: true,
        },
        mouseWheel: true, // Enable zoom with mouse wheel
        pinch: true, // Enable pinch zoom on mobile
      },
    });

    chartRef.current = chart;

    // Add candlestick series (v5 API - use 'as any' for compatibility)
    const candlestickSeries = (chart as any).addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candlestickSeriesRef.current = null;
    };
  }, [height]);

  // ========================================
  // Effects
  // ========================================

  // Initial load
  useEffect(() => {
    if (sessionId) {
      loadChartData();
    }
  }, [sessionId, symbol]);

  // Auto-refresh with cleanup
  useEffect(() => {
    if (!autoRefresh || !sessionId) return;

    const intervalId = setInterval(() => {
      loadChartData();
    }, refreshInterval);

    return () => {
      clearInterval(intervalId);
      // Abort any pending request on cleanup
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [autoRefresh, sessionId, symbol, refreshInterval]);

  // Update chart data when candleData changes
  useEffect(() => {
    if (!candlestickSeriesRef.current || candleData.length === 0) return;

    // Convert to lightweight-charts format
    const chartData: CandlestickData[] = candleData.map((candle) => ({
      time: candle.time as Time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candlestickSeriesRef.current.setData(chartData);

    // Fit content to show all data
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [candleData]);

  // ========================================
  // Handlers
  // ========================================

  const handleResetZoom = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  };

  // ========================================
  // Render
  // ========================================

  return (
    <Box sx={{ position: 'relative', width: '100%', height }}>
      {/* Reset Zoom Button */}
      {candleData.length > 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 100,
          }}
        >
          <IconButton
            onClick={handleResetZoom}
            size="small"
            sx={{
              backgroundColor: 'rgba(30, 30, 30, 0.8)',
              color: '#d1d4dc',
              '&:hover': {
                backgroundColor: 'rgba(30, 30, 30, 0.95)',
              },
            }}
            title="Reset Zoom"
          >
            <ResetZoomIcon fontSize="small" />
          </IconButton>
        </Box>
      )}

      {loading && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 10,
          }}
        >
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!sessionId && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Start a session to view chart
          </Typography>
        </Box>
      )}

      <Box
        ref={chartContainerRef}
        sx={{
          width: '100%',
          height: '100%',
          backgroundColor: '#1e1e1e',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
        }}
      />
    </Box>
  );
};

