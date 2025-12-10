/**
 * SignalLog Component - Agent 6
 * ===============================
 * Displays trading signals with execution results and indicator values.
 *
 * Features:
 * - Real-time updates via WebSocket (signal_generated events)
 * - Fetch historical signals via REST API (if endpoint exists)
 * - Signal type badges: S1 (Entry), Z1 (Position Opened), ZE1 (Partial Exit), E1 (Full Exit)
 * - Confidence gauge (0-100%)
 * - Indicator values collapsible (TWPA, Velocity, Volume_Surge)
 * - Execution result: Order ID if order created, "Rejected" if risk check failed
 * - Filters: Signal Type, Symbol, Confidence range
 * - Auto-scroll to new signals
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';

// ========================================
// TypeScript Types
// ========================================

interface SignalLogProps {
  session_id?: string;
  className?: string;
}

interface Signal {
  signal_id: string;
  session_id: string;
  timestamp: string;
  signal_type: 'S1' | 'Z1' | 'ZE1' | 'E1';
  symbol: string;
  side: 'LONG' | 'SHORT';
  confidence: number;
  indicator_values?: {
    twpa?: number;
    velocity?: number;
    volume_surge?: number;
    [key: string]: any;
  };
  execution_result?: {
    status: 'ORDER_CREATED' | 'REJECTED' | 'PENDING';
    order_id?: string;
    rejection_reason?: string;
  };
}

type SignalType = 'all' | 'S1' | 'Z1' | 'ZE1' | 'E1';

// ========================================
// Component
// ========================================

export default function SignalLog({
  session_id,
  className = ''
}: SignalLogProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [filteredSignals, setFilteredSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSignals, setExpandedSignals] = useState<Set<string>>(new Set());

  // Filters
  const [signalTypeFilter, setSignalTypeFilter] = useState<SignalType>('all');
  const [symbolFilter, setSymbolFilter] = useState<string>('all');
  const [confidenceMin, setConfidenceMin] = useState<number>(0);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);

  const signalsEndRef = useRef<HTMLDivElement>(null);

  const { lastMessage, isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      // Listen for signal events from live_trading stream
      if (message.type === 'data' && message.stream === 'live_trading') {
        const data = message.data;
        if (data.signal_type) {
          handleSignalUpdate(data);
        }
      }
      // Also listen for direct signal_generated events
      else if (message.type === 'signal_generated' || message.stream === 'signal_generated') {
        handleSignalUpdate(message.data);
      }
    }
  });

  // Apply filters
  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signals, signalTypeFilter, symbolFilter, confidenceMin]);

  // Handle signal update from WebSocket
  const handleSignalUpdate = (data: any) => {
    const signal: Signal = {
      signal_id: data.signal_id || `signal_${Date.now()}`,
      session_id: data.session_id || session_id || 'unknown',
      timestamp: data.timestamp || new Date().toISOString(),
      signal_type: data.signal_type,
      symbol: data.symbol,
      side: data.side || 'LONG',
      confidence: data.confidence || 0,
      indicator_values: data.indicator_values || {},
      execution_result: data.execution_result,
    };

    // Filter by session if provided
    if (session_id && signal.session_id !== session_id) {
      return;
    }

    setSignals(prev => {
      // Check if signal already exists
      const exists = prev.find(s => s.signal_id === signal.signal_id);
      if (exists) {
        // Update existing signal
        return prev.map(s => s.signal_id === signal.signal_id ? signal : s);
      } else {
        // Add new signal (prepend to show newest first)
        return [signal, ...prev];
      }
    });

    // Update available symbols
    setAvailableSymbols(prev => {
      if (!prev.includes(signal.symbol)) {
        return [...prev, signal.symbol];
      }
      return prev;
    });

    // Auto-scroll to new signal
    setTimeout(() => {
      signalsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  // Apply filters to signals
  const applyFilters = () => {
    let filtered = [...signals];

    // Signal type filter
    if (signalTypeFilter !== 'all') {
      filtered = filtered.filter(s => s.signal_type === signalTypeFilter);
    }

    // Symbol filter
    if (symbolFilter !== 'all') {
      filtered = filtered.filter(s => s.symbol === symbolFilter);
    }

    // Confidence filter
    if (confidenceMin > 0) {
      filtered = filtered.filter(s => s.confidence >= confidenceMin);
    }

    // Sort by timestamp descending (newest first)
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    setFilteredSignals(filtered);
  };

  // Toggle indicator details
  const toggleExpanded = (signal_id: string) => {
    setExpandedSignals(prev => {
      const newSet = new Set(prev);
      if (newSet.has(signal_id)) {
        newSet.delete(signal_id);
      } else {
        newSet.add(signal_id);
      }
      return newSet;
    });
  };

  // Get signal type color
  const getSignalTypeColor = (signalType: string) => {
    switch (signalType) {
      case 'S1':
        return 'text-yellow-700 bg-yellow-100 border-yellow-300';
      case 'Z1':
        return 'text-green-700 bg-green-100 border-green-300';
      case 'ZE1':
        return 'text-blue-700 bg-blue-100 border-blue-300';
      case 'E1':
        return 'text-red-700 bg-red-100 border-red-300';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-300';
    }
  };

  // Get signal type label
  const getSignalTypeLabel = (signalType: string) => {
    switch (signalType) {
      case 'S1': return 'Entry Signal';
      case 'Z1': return 'Position Opened';
      case 'ZE1': return 'Partial Exit';
      case 'E1': return 'Full Exit';
      default: return signalType;
    }
  };

  // Get confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold text-gray-900">Signal Log</h3>
          <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-200 rounded-full">
            {filteredSignals.length}
          </span>
          {!isConnected && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-gray-400 rounded-full">
              Disconnected
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4 p-3 border-b border-gray-200 bg-gray-50">
        {/* Signal Type Filter */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Type:</label>
          <select
            value={signalTypeFilter}
            onChange={(e) => setSignalTypeFilter(e.target.value as SignalType)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="S1">S1 (Entry)</option>
            <option value="Z1">Z1 (Opened)</option>
            <option value="ZE1">ZE1 (Partial Exit)</option>
            <option value="E1">E1 (Full Exit)</option>
          </select>
        </div>

        {/* Symbol Filter */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Symbol:</label>
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            {availableSymbols.map(sym => (
              <option key={sym} value={sym}>{sym}</option>
            ))}
          </select>
        </div>

        {/* Confidence Filter */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Min Confidence:</label>
          <input
            type="number"
            min="0"
            max="100"
            step="10"
            value={confidenceMin}
            onChange={(e) => setConfidenceMin(parseInt(e.target.value) || 0)}
            className="w-20 px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-xs text-gray-500">%</span>
        </div>

        {/* Reset Filters */}
        {(signalTypeFilter !== 'all' || symbolFilter !== 'all' || confidenceMin > 0) && (
          <button
            onClick={() => {
              setSignalTypeFilter('all');
              setSymbolFilter('all');
              setConfidenceMin(0);
            }}
            className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Signals List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {filteredSignals.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              <p className="mt-2 text-sm">No signals found</p>
              <p className="mt-1 text-xs text-gray-400">
                {signals.length > 0 ? 'Try adjusting filters' : isConnected ? 'Waiting for signals...' : 'Waiting for connection...'}
              </p>
            </div>
          </div>
        ) : (
          <>
            {filteredSignals.map((signal) => {
              const isExpanded = expandedSignals.has(signal.signal_id);
              return (
                <div
                  key={signal.signal_id}
                  className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow"
                >
                  {/* Signal Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`px-3 py-1 text-xs font-semibold rounded border ${getSignalTypeColor(signal.signal_type)}`}>
                          {signal.signal_type}
                        </span>
                        <span className="text-sm font-medium text-gray-900">{signal.symbol}</span>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          signal.side === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {signal.side}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatTimestamp(signal.timestamp)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-600">{getSignalTypeLabel(signal.signal_type)}</p>
                    </div>

                    {/* Confidence */}
                    <div className="text-right">
                      <div className={`text-lg font-bold ${getConfidenceColor(signal.confidence)}`}>
                        {signal.confidence.toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">Confidence</div>
                    </div>
                  </div>

                  {/* Execution Result */}
                  {signal.execution_result && (
                    <div className="mt-3 p-2 bg-gray-50 rounded border border-gray-200">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-700">Execution:</span>
                        {signal.execution_result.status === 'ORDER_CREATED' ? (
                          <span className="text-xs text-green-600 font-medium">
                            Order Created: {signal.execution_result.order_id}
                          </span>
                        ) : signal.execution_result.status === 'REJECTED' ? (
                          <span className="text-xs text-red-600 font-medium">
                            Rejected: {signal.execution_result.rejection_reason || 'Risk check failed'}
                          </span>
                        ) : (
                          <span className="text-xs text-yellow-600 font-medium">
                            Pending
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Indicator Values (Collapsible) */}
                  {signal.indicator_values && Object.keys(signal.indicator_values).length > 0 && (
                    <div className="mt-3">
                      <button
                        onClick={() => toggleExpanded(signal.signal_id)}
                        className="flex items-center justify-between w-full p-2 text-sm font-medium text-gray-700 bg-gray-50 rounded hover:bg-gray-100"
                      >
                        <span>Indicator Values</span>
                        <svg
                          className={`w-4 h-4 transition-transform ${isExpanded ? 'transform rotate-180' : ''}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 p-3 bg-gray-50 rounded border border-gray-200">
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            {Object.entries(signal.indicator_values).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="font-medium text-gray-700">{key.replace(/_/g, ' ')}:</span>
                                <span className="text-gray-900">
                                  {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={signalsEndRef} />
          </>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Total: {filteredSignals.length} signals</span>
          <span>
            S1: {filteredSignals.filter(s => s.signal_type === 'S1').length} |
            Z1: {filteredSignals.filter(s => s.signal_type === 'Z1').length} |
            ZE1: {filteredSignals.filter(s => s.signal_type === 'ZE1').length} |
            E1: {filteredSignals.filter(s => s.signal_type === 'E1').length}
          </span>
        </div>
      </div>
    </div>
  );
}
