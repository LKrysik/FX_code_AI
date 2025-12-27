/**
 * Candlestick Chart Component
 * ===========================
 *
 * Lightweight trading chart using TradingView's lightweight-charts library.
 *
 * Features:
 * - Real-time candlestick display
 * - Volume bars
 * - State machine transition markers (SM-05):
 *   • S1 (Signal Detection): Orange triangle UP - pump detected
 *   • Z1/O1 (Entry): Green circle - position entry
 *   • ZE1 (Close): Blue square - take profit/normal close
 *   • E1 (Emergency): Red X - emergency exit
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
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md, docs/UI_BACKLOG.md (SM-05)
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Logger } from '@/services/frontendLogService';
import { Box, Typography, CircularProgress, Alert, IconButton, Tooltip, Chip, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { ZoomOutMap as ResetZoomIcon, Info as InfoIcon } from '@mui/icons-material';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time, CandlestickSeries } from 'lightweight-charts';
import {
  ChartDrawingTools,
  FibonacciOverlay,
  RectangleOverlay,
  Drawing,
  DrawingMode,
  FibonacciDrawing,
  RectangleDrawing,
} from './ChartDrawingTools';

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

export interface StateTransition {
  timestamp: string; // ISO format
  strategy_id: string;
  symbol: string;
  from_state: string;
  to_state: string;
  trigger: 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1' | 'MANUAL';
  conditions?: Record<string, any>;
}

/**
 * Position data for Entry/SL/TP price lines (CH-03)
 */
export interface PositionLines {
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  side?: 'LONG' | 'SHORT';
}

// D-03: Timeframe type
export type Timeframe = '1m' | '5m' | '15m' | '1h';

export interface CandlestickChartProps {
  symbol: string;
  sessionId: string | null;
  height?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
  positionLines?: PositionLines; // CH-03: Entry/SL/TP horizontal lines
  showTimeframeToggle?: boolean; // D-03: Show timeframe toggle
  showDrawingTools?: boolean; // D-01/D-02: Show drawing tools
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
  positionLines, // CH-03: Entry/SL/TP lines
  showTimeframeToggle = true, // D-03: Show timeframe toggle by default
  showDrawingTools = true, // D-01/D-02: Show drawing tools by default
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
  const [stateTransitions, setStateTransitions] = useState<StateTransition[]>([]);
  // D-03: Timeframe state
  const [timeframe, setTimeframe] = useState<Timeframe>('1m');

  // D-01/D-02: Drawing tools state
  const [drawingMode, setDrawingMode] = useState<DrawingMode>('none');
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [activeDrawing, setActiveDrawing] = useState<Partial<Drawing> | null>(null);
  const [chartDimensions, setChartDimensions] = useState({ width: 0, height: 0 });
  const [isDrawing, setIsDrawing] = useState(false);
  const drawingStartRef = useRef<{ price: number; time: number } | null>(null);

  // Price lines refs (CH-03)
  const entryLineRef = useRef<any>(null);
  const slLineRef = useRef<any>(null);
  const tpLineRef = useRef<any>(null);

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
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

      // Load OHLCV data and state transitions in parallel
      const [ohlcvResponse, transitionsResponse] = await Promise.all([
        fetch(
          `${apiUrl}/api/chart/ohlcv?session_id=${sessionId}&symbol=${symbol}&interval=1m&limit=500`,
          { signal: abortControllerRef.current.signal }
        ),
        fetch(
          `${apiUrl}/api/sessions/${sessionId}/transitions`,
          { signal: abortControllerRef.current.signal }
        )
      ]);

      if (!ohlcvResponse.ok) {
        throw new Error(`Failed to load OHLCV data: ${ohlcvResponse.statusText}`);
      }

      const ohlcvResult = await ohlcvResponse.json();
      const ohlcvData = ohlcvResult.data || ohlcvResult;

      // Validate real data - no fallback to mock
      if (!ohlcvData.candles || ohlcvData.candles.length === 0) {
        Logger.warn('CandlestickChart.loadData', 'No OHLCV data available', { symbol });
        setCandleData([]);
        setError('No chart data available. Start data collection to see chart.');
      } else {
        setCandleData(ohlcvData.candles);
        setError(null);
      }

      // Load state transitions (optional - don't fail if endpoint is down)
      if (transitionsResponse.ok) {
        const transitionsResult = await transitionsResponse.json();
        const transitionsData = transitionsResult.data || transitionsResult;

        if (transitionsData.transitions && Array.isArray(transitionsData.transitions)) {
          // Filter transitions for current symbol only
          const symbolTransitions = transitionsData.transitions.filter(
            (t: StateTransition) => t.symbol === symbol
          );
          setStateTransitions(symbolTransitions);
        }
      } else {
        Logger.warn('CandlestickChart.loadTransitions', 'State transitions endpoint not available (expected for MVP)');
        setStateTransitions([]);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      Logger.error('CandlestickChart.loadData', 'Failed to load chart data', { error: err });
      setCandleData([]);
      setError(`Failed to load chart data: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  // ========================================
  // Helper Functions
  // ========================================

  /**
   * Convert state transitions to lightweight-charts markers
   */
  const convertTransitionsToMarkers = (transitions: StateTransition[]) => {
    return transitions.map((transition) => {
      const timestamp = new Date(transition.timestamp).getTime() / 1000; // Convert to Unix seconds

      // Map trigger types to marker styles based on SM-05 requirements
      switch (transition.trigger) {
        case 'S1': // Signal Detection - Orange triangle UP
          return {
            time: timestamp as Time,
            position: 'belowBar' as const,
            color: '#ff9800', // Orange
            shape: 'arrowUp' as const,
            text: 'S1',
          };
        case 'Z1': // Entry Conditions - Green circle (Z1 is entry evaluation)
        case 'O1': // O1 is actual entry/order placement
          return {
            time: timestamp as Time,
            position: 'belowBar' as const,
            color: '#4caf50', // Green
            shape: 'circle' as const,
            text: transition.trigger,
          };
        case 'ZE1': // Close Order Detection - Blue square
          return {
            time: timestamp as Time,
            position: 'aboveBar' as const,
            color: '#2196f3', // Blue
            shape: 'square' as const,
            text: 'ZE1',
          };
        case 'E1': // Emergency Exit - Red X (arrowDown as X)
          return {
            time: timestamp as Time,
            position: 'aboveBar' as const,
            color: '#f44336', // Red
            shape: 'arrowDown' as const,
            text: 'E1',
          };
        default:
          return {
            time: timestamp as Time,
            position: 'belowBar' as const,
            color: '#9e9e9e', // Gray
            shape: 'circle' as const,
            text: transition.trigger,
          };
      }
    });
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

    // Add candlestick series (v5 API - use chart.addSeries with CandlestickSeries type)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
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
  // Intentionally exclude loadChartData from deps - runs when sessionId or symbol changes
  useEffect(() => {
    if (sessionId) {
      loadChartData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, symbol]);

  // Auto-refresh with cleanup
  // Intentionally exclude loadChartData from deps - runs when autoRefresh, sessionId, symbol, or refreshInterval changes
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Update markers when state transitions change
  useEffect(() => {
    if (!candlestickSeriesRef.current) return;

    const markers = convertTransitionsToMarkers(stateTransitions);

    // TypeScript doesn't recognize setMarkers in v5, but it exists at runtime
    // Using 'as any' to bypass type checking
    // Safety check: verify setMarkers method exists before calling
    const series = candlestickSeriesRef.current as any;
    if (typeof series.setMarkers === 'function') {
      series.setMarkers(markers);
      Logger.debug('CandlestickChart.applyMarkers', `Applied ${markers.length} state machine markers to chart`);
    } else {
      Logger.warn('CandlestickChart.applyMarkers', 'setMarkers not available on series - markers not applied');
    }
  }, [stateTransitions]);

  // CH-03: Update Entry/SL/TP price lines when positionLines change
  useEffect(() => {
    if (!candlestickSeriesRef.current) return;

    const series = candlestickSeriesRef.current as any;

    // Remove existing price lines
    if (entryLineRef.current) {
      try { series.removePriceLine(entryLineRef.current); } catch {}
      entryLineRef.current = null;
    }
    if (slLineRef.current) {
      try { series.removePriceLine(slLineRef.current); } catch {}
      slLineRef.current = null;
    }
    if (tpLineRef.current) {
      try { series.removePriceLine(tpLineRef.current); } catch {}
      tpLineRef.current = null;
    }

    // Add new price lines if position data provided
    if (positionLines) {
      const isShort = positionLines.side === 'SHORT';

      // Entry Price Line - Yellow/Gold dashed
      if (positionLines.entryPrice) {
        entryLineRef.current = series.createPriceLine({
          price: positionLines.entryPrice,
          color: '#ffc107', // Yellow/Gold
          lineWidth: 2,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: `Entry ${positionLines.entryPrice.toFixed(2)}`,
        });
      }

      // Stop Loss Line - Red solid
      if (positionLines.stopLoss) {
        slLineRef.current = series.createPriceLine({
          price: positionLines.stopLoss,
          color: '#f44336', // Red
          lineWidth: 2,
          lineStyle: 0, // Solid
          axisLabelVisible: true,
          title: `SL ${positionLines.stopLoss.toFixed(2)}`,
        });
      }

      // Take Profit Line - Green solid
      if (positionLines.takeProfit) {
        tpLineRef.current = series.createPriceLine({
          price: positionLines.takeProfit,
          color: '#4caf50', // Green
          lineWidth: 2,
          lineStyle: 0, // Solid
          axisLabelVisible: true,
          title: `TP ${positionLines.takeProfit.toFixed(2)}`,
        });
      }

      Logger.debug('CandlestickChart.priceLines', 'CH-03: Price lines updated', { entryPrice: positionLines.entryPrice, stopLoss: positionLines.stopLoss, takeProfit: positionLines.takeProfit });
    }
  }, [positionLines]);

  // ========================================
  // Handlers
  // ========================================

  const handleResetZoom = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  };

  // ========================================
  // D-01/D-02: Drawing Functions
  // ========================================

  // Convert Y position to price
  const yToPrice = useCallback((y: number): number => {
    if (!candlestickSeriesRef.current || !chartRef.current) return 0;
    const coordinate = candlestickSeriesRef.current.coordinateToPrice(y);
    return coordinate || 0;
  }, []);

  // Convert X position to time
  const xToTime = useCallback((x: number): number => {
    if (!chartRef.current) return 0;
    const timeScale = chartRef.current.timeScale();
    const time = timeScale.coordinateToTime(x);
    return typeof time === 'number' ? time : 0;
  }, []);

  // Convert price to Y position
  const priceToY = useCallback((price: number): number => {
    if (!candlestickSeriesRef.current) return 0;
    const coordinate = candlestickSeriesRef.current.priceToCoordinate(price);
    return coordinate || 0;
  }, []);

  // Convert time to X position
  const timeToX = useCallback((time: number): number => {
    if (!chartRef.current) return 0;
    const timeScale = chartRef.current.timeScale();
    const coordinate = timeScale.timeToCoordinate(time as Time);
    return coordinate || 0;
  }, []);

  // Handle drawing mode change
  const handleDrawingModeChange = useCallback((mode: DrawingMode) => {
    setDrawingMode(mode);
    setActiveDrawing(null);
    setIsDrawing(false);
    drawingStartRef.current = null;
  }, []);

  // Handle mouse down for drawing
  const handleChartMouseDown = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (drawingMode === 'none') return;

    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const price = yToPrice(y);
    const time = xToTime(x);

    if (price && time) {
      setIsDrawing(true);
      drawingStartRef.current = { price, time };
      setActiveDrawing({
        id: `drawing-${Date.now()}`,
        type: drawingMode === 'fibonacci' ? 'fibonacci' : 'rectangle',
        startPrice: price,
        startTime: time,
        endPrice: price,
        endTime: time,
        visible: true,
      });
    }
  }, [drawingMode, yToPrice, xToTime]);

  // Handle mouse move for drawing
  const handleChartMouseMove = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !activeDrawing || drawingMode === 'none') return;

    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const price = yToPrice(y);
    const time = xToTime(x);

    if (price && time) {
      setActiveDrawing((prev) => ({
        ...prev,
        endPrice: price,
        endTime: time,
      }));
    }
  }, [isDrawing, activeDrawing, drawingMode, yToPrice, xToTime]);

  // Handle mouse up for drawing
  const handleChartMouseUp = useCallback(() => {
    if (!isDrawing || !activeDrawing || !drawingStartRef.current) return;

    const start = drawingStartRef.current;
    const end = { price: activeDrawing.endPrice || start.price, time: activeDrawing.endTime || start.time };

    // Only save if there's a meaningful movement
    const priceChange = Math.abs((end.price - start.price) / start.price);
    const timeChange = Math.abs(end.time - start.time);

    if (priceChange > 0.001 || timeChange > 60) {
      const newDrawing: Drawing = drawingMode === 'fibonacci'
        ? {
            id: activeDrawing.id || `fib-${Date.now()}`,
            type: 'fibonacci',
            startPrice: start.price,
            endPrice: end.price,
            startTime: start.time,
            endTime: end.time,
            levels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1],
            color: '#ffd700',
            visible: true,
          }
        : {
            id: activeDrawing.id || `rect-${Date.now()}`,
            type: 'rectangle',
            startPrice: start.price,
            endPrice: end.price,
            startTime: start.time,
            endTime: end.time,
            color: '#2196f3',
            fillOpacity: 0.15,
            visible: true,
            label: 'Zone',
          };

      setDrawings((prev) => [...prev, newDrawing]);
      Logger.debug('CandlestickChart.drawingSaved', 'Drawing saved', { drawing: newDrawing });
    }

    // Reset drawing state
    setIsDrawing(false);
    setActiveDrawing(null);
    drawingStartRef.current = null;
    setDrawingMode('none');
  }, [isDrawing, activeDrawing, drawingMode]);

  // Update chart dimensions when chart changes
  useEffect(() => {
    if (chartContainerRef.current) {
      setChartDimensions({
        width: chartContainerRef.current.clientWidth,
        height: chartContainerRef.current.clientHeight,
      });
    }
  }, [height, candleData]);

  // ========================================
  // Render
  // ========================================

  return (
    <Box sx={{ position: 'relative', width: '100%', height }}>
      {/* D-03: Timeframe Toggle */}
      {showTimeframeToggle && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 100,
          }}
        >
          <ToggleButtonGroup
            value={timeframe}
            exclusive
            onChange={(_, newTimeframe) => {
              if (newTimeframe !== null) {
                setTimeframe(newTimeframe);
              }
            }}
            size="small"
            sx={{
              backgroundColor: 'rgba(30, 30, 30, 0.85)',
              '& .MuiToggleButton-root': {
                color: '#9ca3af',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                px: 1.5,
                py: 0.5,
                fontSize: '0.75rem',
                fontWeight: 500,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(59, 130, 246, 0.3)',
                  color: '#60a5fa',
                  '&:hover': {
                    backgroundColor: 'rgba(59, 130, 246, 0.4)',
                  },
                },
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                },
              },
            }}
          >
            <ToggleButton value="1m">1m</ToggleButton>
            <ToggleButton value="5m">5m</ToggleButton>
            <ToggleButton value="15m">15m</ToggleButton>
            <ToggleButton value="1h">1h</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}

      {/* D-01/D-02: Drawing Tools */}
      {showDrawingTools && candleData.length > 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            left: showTimeframeToggle ? 180 : 8,
            zIndex: 100,
          }}
        >
          <ChartDrawingTools
            symbol={symbol}
            onDrawingModeChange={handleDrawingModeChange}
            drawings={drawings}
            onDrawingsChange={setDrawings}
            activeDrawing={activeDrawing}
            onActiveDrawingChange={setActiveDrawing}
          />
        </Box>
      )}

      {/* Chart Controls */}
      {candleData.length > 0 && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 100,
            display: 'flex',
            gap: 1,
          }}
        >
          {/* State Machine Markers Legend */}
          {stateTransitions.length > 0 && (
            <Tooltip
              title={
                <Box sx={{ p: 1 }}>
                  <Typography variant="body2" fontWeight="bold" gutterBottom>
                    State Machine Markers:
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Typography variant="caption">🔺 S1 - Signal Detection (pump detected)</Typography>
                    <Typography variant="caption">🟢 Z1/O1 - Entry (position opened)</Typography>
                    <Typography variant="caption">🟦 ZE1 - Close (take profit/normal exit)</Typography>
                    <Typography variant="caption">🔻 E1 - Emergency Exit</Typography>
                  </Box>
                </Box>
              }
              arrow
            >
              <Chip
                icon={<InfoIcon fontSize="small" />}
                label={`${stateTransitions.length} markers`}
                size="small"
                sx={{
                  backgroundColor: 'rgba(30, 30, 30, 0.8)',
                  color: '#d1d4dc',
                  '&:hover': {
                    backgroundColor: 'rgba(30, 30, 30, 0.95)',
                  },
                }}
              />
            </Tooltip>
          )}

          {/* Reset Zoom Button */}
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

      {/* Chart Container with Drawing Event Handlers */}
      <Box
        ref={chartContainerRef}
        onMouseDown={handleChartMouseDown}
        onMouseMove={handleChartMouseMove}
        onMouseUp={handleChartMouseUp}
        onMouseLeave={handleChartMouseUp}
        sx={{
          width: '100%',
          height: '100%',
          backgroundColor: '#1e1e1e',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          cursor: drawingMode !== 'none' ? 'crosshair' : 'default',
        }}
      />

      {/* D-01/D-02: Drawing Overlays */}
      {drawings.map((drawing) =>
        drawing.type === 'fibonacci' ? (
          <FibonacciOverlay
            key={drawing.id}
            drawing={drawing as FibonacciDrawing}
            chartWidth={chartDimensions.width}
            chartHeight={chartDimensions.height}
            priceToY={priceToY}
            timeToX={timeToX}
          />
        ) : (
          <RectangleOverlay
            key={drawing.id}
            drawing={drawing as RectangleDrawing}
            chartWidth={chartDimensions.width}
            chartHeight={chartDimensions.height}
            priceToY={priceToY}
            timeToX={timeToX}
          />
        )
      )}

      {/* Active Drawing Preview */}
      {activeDrawing && activeDrawing.startPrice && activeDrawing.endPrice && (
        drawingMode === 'fibonacci' ? (
          <FibonacciOverlay
            drawing={{
              id: 'active',
              type: 'fibonacci',
              startPrice: activeDrawing.startPrice,
              endPrice: activeDrawing.endPrice,
              startTime: activeDrawing.startTime || 0,
              endTime: activeDrawing.endTime || 0,
              levels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1],
              color: '#ffd700',
              visible: true,
            }}
            chartWidth={chartDimensions.width}
            chartHeight={chartDimensions.height}
            priceToY={priceToY}
            timeToX={timeToX}
          />
        ) : (
          <RectangleOverlay
            drawing={{
              id: 'active',
              type: 'rectangle',
              startPrice: activeDrawing.startPrice,
              endPrice: activeDrawing.endPrice,
              startTime: activeDrawing.startTime || 0,
              endTime: activeDrawing.endTime || 0,
              color: '#2196f3',
              fillOpacity: 0.15,
              visible: true,
            }}
            chartWidth={chartDimensions.width}
            chartHeight={chartDimensions.height}
            priceToY={priceToY}
            timeToX={timeToX}
          />
        )
      )}
    </Box>
  );
};

