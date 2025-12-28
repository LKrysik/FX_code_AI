/**
 * TradingChart Component - Agent 6
 * =================================
 * Real-time candlestick chart with signal markers using TradingView Lightweight Charts.
 *
 * Features:
 * - Real-time candlestick chart (OHLCV data)
 * - Signal markers overlay (S1 🟡, Z1 🟢, ZE1 🔵, E1 🔴)
 * - Historical data from QuestDB via REST API
 * - WebSocket updates for new candles
 * - Volume overlay
 * - Symbol selector
 * - Timeframe selector (1m, 5m, 15m, 1h)
 * - Auto-scroll to latest data
 * - Zoom/pan controls
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time, CandlestickSeriesPartialOptions, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { Logger } from '@/services/frontendLogService';

// ========================================
// TypeScript Types
// ========================================

interface TradingChartProps {
  session_id?: string;
  initialSymbol?: string;
  className?: string;
}

interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Signal {
  timestamp: string;
  signal_type: 'S1' | 'Z1' | 'ZE1' | 'E1';
  symbol: string;
  price: number;
  confidence: number;
}

// ========================================
// Component
// ========================================

export default function TradingChart({
  session_id,
  initialSymbol = 'BTC_USDT',
  className = ''
}: TradingChartProps) {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState('5m');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ohlcvData, setOhlcvData] = useState<OHLCVData[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const { lastMessage, isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      // Listen for market data updates
      if (message.type === 'data' && message.stream === 'market_data') {
        handleMarketDataUpdate(message.data);
      }
      // Listen for signal events
      else if (message.type === 'signal_generated' || message.stream === 'signal_generated') {
        handleSignalUpdate(message.data);
      }
    }
  });

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333333',
      },
      grid: {
        vertLines: { color: '#e1e1e1' },
        horzLines: { color: '#e1e1e1' },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series (v5 API uses chart.addSeries with CandlestickSeries type)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series (histogram) - v5 API uses chart.addSeries with HistogramSeries type
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume', // Separate scale for volume
    });

    // Set scale margins for volume series (v5 API - configure via priceScale)
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8, // 80% for price, 20% for volume
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

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
    };
  }, []);

  // Fetch historical data
  useEffect(() => {
    fetchHistoricalData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe, session_id]);

  // Fetch historical OHLCV data
  const fetchHistoricalData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Convert timeframe to minutes
      const timeframeMinutes = parseTimeframe(timeframe);

      // Fetch from backend API (adjust endpoint as needed)
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const params = new URLSearchParams({
        symbol,
        timeframe: timeframe,
        limit: '500',
      });

      if (session_id) {
        params.append('session_id', session_id);
      }

      const response = await fetch(`${API_BASE_URL}/api/market-data/ohlcv?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch OHLCV data: ${response.statusText}`);
      }

      const data = await response.json();
      const ohlcvArray: OHLCVData[] = data.data || data.ohlcv || [];

      setOhlcvData(ohlcvArray);
      updateChart(ohlcvArray);
    } catch (err: any) {
      Logger.error('TradingChart.fetchHistoricalData', { message: 'Failed to fetch historical data', error: err });
      setError(err.message || 'Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };

  // Update chart with OHLCV data
  const updateChart = (data: OHLCVData[]) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    // Convert to lightweight-charts format
    const candleData: CandlestickData[] = data.map(d => ({
      time: (new Date(d.timestamp).getTime() / 1000) as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    const volumeData = data.map(d => ({
      time: (new Date(d.timestamp).getTime() / 1000) as Time,
      value: d.volume,
      color: d.close >= d.open ? '#26a69a' : '#ef5350',
    }));

    candlestickSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);

    // Add signal markers
    if (signals.length > 0) {
      const markers = signals.map(signal => ({
        time: (new Date(signal.timestamp).getTime() / 1000) as Time,
        position: getSignalPosition(signal.signal_type),
        color: getSignalColor(signal.signal_type),
        shape: getSignalShape(signal.signal_type),
        text: signal.signal_type,
      }));

      (candlestickSeriesRef.current as any).setMarkers(markers as any);
    }

    // Auto-scroll to latest
    if (chartRef.current) {
      chartRef.current.timeScale().scrollToRealTime();
    }
  };

  // Handle market data update from WebSocket
  const handleMarketDataUpdate = (data: any) => {
    if (data.symbol !== symbol) return;

    // Update last candle or add new candle
    // This is a simplified approach - in production, you'd aggregate ticks into candles
    const newPrice = data.price;
    const timestamp = data.timestamp || new Date().toISOString();

    // For now, just update the chart by adding a new tick
    // In a real implementation, you'd aggregate ticks into OHLCV candles based on timeframe
    if (candlestickSeriesRef.current) {
      const time = (new Date(timestamp).getTime() / 1000) as Time;

      // Update last candle (simplified - assumes same timeframe bucket)
      candlestickSeriesRef.current.update({
        time,
        open: newPrice,
        high: newPrice,
        low: newPrice,
        close: newPrice,
      });
    }
  };

  // Handle signal update from WebSocket
  const handleSignalUpdate = (data: any) => {
    if (data.symbol !== symbol) return;

    const signal: Signal = {
      timestamp: data.timestamp || new Date().toISOString(),
      signal_type: data.signal_type,
      symbol: data.symbol,
      price: data.price || 0,
      confidence: data.confidence || 0,
    };

    setSignals(prev => [...prev, signal]);

    // Add marker to chart
    if (candlestickSeriesRef.current) {
      const time = (new Date(signal.timestamp).getTime() / 1000) as Time;
      const marker = {
        time,
        position: getSignalPosition(signal.signal_type),
        color: getSignalColor(signal.signal_type),
        shape: getSignalShape(signal.signal_type),
        text: signal.signal_type,
      };

      // Add marker (note: setMarkers replaces all markers, so we need to add to existing)
      const existingMarkers = (candlestickSeriesRef.current as any).markers?.() || [];
      (candlestickSeriesRef.current as any).setMarkers([...existingMarkers, marker] as any);
    }
  };

  // Parse timeframe string to minutes
  const parseTimeframe = (tf: string): number => {
    const match = tf.match(/^(\d+)([mhd])$/);
    if (!match) return 5;

    const value = parseInt(match[1]);
    const unit = match[2];

    switch (unit) {
      case 'm': return value;
      case 'h': return value * 60;
      case 'd': return value * 60 * 24;
      default: return 5;
    }
  };

  // Get signal marker position
  const getSignalPosition = (signalType: string): 'aboveBar' | 'belowBar' => {
    return ['S1', 'Z1'].includes(signalType) ? 'belowBar' : 'aboveBar';
  };

  // Get signal marker color
  const getSignalColor = (signalType: string): string => {
    switch (signalType) {
      case 'S1': return '#fbbf24'; // Yellow
      case 'Z1': return '#10b981'; // Green
      case 'ZE1': return '#3b82f6'; // Blue
      case 'E1': return '#ef4444'; // Red
      default: return '#6b7280'; // Gray
    }
  };

  // Get signal marker shape
  const getSignalShape = (signalType: string): 'arrowUp' | 'arrowDown' | 'circle' => {
    if (['S1', 'Z1'].includes(signalType)) return 'arrowUp';
    if (['ZE1', 'E1'].includes(signalType)) return 'arrowDown';
    return 'circle';
  };

  // Available symbols
  const availableSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'];

  // Available timeframes
  const timeframes = [
    { value: '1m', label: '1 Minute' },
    { value: '5m', label: '5 Minutes' },
    { value: '15m', label: '15 Minutes' },
    { value: '1h', label: '1 Hour' },
    { value: '4h', label: '4 Hours' },
    { value: '1d', label: '1 Day' },
  ];

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <button
            onClick={fetchHistoricalData}
            className="mt-2 px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header Controls */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold text-gray-900">Trading Chart</h3>

          {/* Symbol Selector */}
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {availableSymbols.map(sym => (
              <option key={sym} value={sym}>{sym}</option>
            ))}
          </select>

          {/* Timeframe Selector */}
          <div className="flex space-x-1">
            {timeframes.map(tf => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  timeframe === tf.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {tf.label.split(' ')[0]}
              </button>
            ))}
          </div>

          {!isConnected && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-gray-400 rounded-full">
              Disconnected
            </span>
          )}
        </div>

        {/* Refresh Button */}
        <button
          onClick={fetchHistoricalData}
          disabled={loading}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded disabled:opacity-50"
          title="Refresh chart"
        >
          <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Chart Container */}
      <div className="flex-1 bg-white p-4">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">Loading chart...</p>
            </div>
          </div>
        )}
        <div ref={chartContainerRef} className={loading ? 'hidden' : ''} />
      </div>

      {/* Signal Legend */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="flex items-center justify-between text-xs">
          <div className="flex space-x-4">
            <span className="flex items-center">
              <span className="w-3 h-3 rounded-full bg-yellow-400 mr-1"></span>
              S1 (Entry Signal)
            </span>
            <span className="flex items-center">
              <span className="w-3 h-3 rounded-full bg-green-500 mr-1"></span>
              Z1 (Position Opened)
            </span>
            <span className="flex items-center">
              <span className="w-3 h-3 rounded-full bg-blue-500 mr-1"></span>
              ZE1 (Partial Exit)
            </span>
            <span className="flex items-center">
              <span className="w-3 h-3 rounded-full bg-red-500 mr-1"></span>
              E1 (Full Exit)
            </span>
          </div>
          <span className="text-gray-400">
            Signals: {signals.length} | Last update: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
}
