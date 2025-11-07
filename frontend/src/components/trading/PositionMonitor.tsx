/**
 * PositionMonitor Component - Agent 6
 * ====================================
 * Real-time position monitoring with margin ratio tracking and liquidation warnings.
 *
 * Features:
 * - Real-time position updates via WebSocket
 * - Margin ratio gauge (< 15% = red alert)
 * - Liquidation price display
 * - Close position button
 * - P&L color-coding (green = profit, red = loss)
 * - Auto-refresh every 1s
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { Position, tradingAPI } from '@/services/TradingAPI';

// ========================================
// TypeScript Types
// ========================================

interface PositionMonitorProps {
  session_id?: string;
  className?: string;
}

// ========================================
// Component
// ========================================

export default function PositionMonitor({
  session_id,
  className = ''
}: PositionMonitorProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [closingPositionId, setClosingPositionId] = useState<string | null>(null);

  const { lastMessage, isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      // Listen for position updates from live_trading stream
      if (message.type === 'data' && message.stream === 'live_trading') {
        const data = message.data;
        if (data.symbol && (data.unrealized_pnl !== undefined || data.margin_ratio !== undefined)) {
          // This is a position update
          handlePositionUpdate(data);
        }
      }
      // Also listen for direct position_update events
      else if (message.type === 'position_update' || message.stream === 'position_update') {
        handlePositionUpdate(message.data);
      }
    }
  });

  // Fetch initial positions
  useEffect(() => {
    fetchPositions();
  }, [session_id]);

  // Fetch positions from REST API
  const fetchPositions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await tradingAPI.getPositions({
        session_id,
        status: 'OPEN'
      });
      setPositions(data);
    } catch (err: any) {
      console.error('[PositionMonitor] Failed to fetch positions:', err);
      setError(err.message || 'Failed to load positions');
    } finally {
      setLoading(false);
    }
  };

  // Handle position update from WebSocket
  const handlePositionUpdate = (data: any) => {
    setPositions(prev => {
      const index = prev.findIndex(p => p.symbol === data.symbol && p.session_id === data.session_id);
      if (index >= 0) {
        // Update existing position
        const updated = [...prev];
        updated[index] = { ...updated[index], ...data };
        return updated;
      } else {
        // Add new position
        return [...prev, data as Position];
      }
    });
  };

  // Close position
  const handleClosePosition = async (position: Position) => {
    const position_id = `${position.session_id}:${position.symbol}`;
    if (closingPositionId || !confirm(`Close position ${position.symbol}?`)) {
      return;
    }

    try {
      setClosingPositionId(position_id);
      const result = await tradingAPI.closePosition(position_id, 'USER_REQUESTED');
      console.log('[PositionMonitor] Position close order submitted:', result);
      // Position will be removed from list via WebSocket update
      setTimeout(fetchPositions, 1000);  // Refresh after 1s
    } catch (err: any) {
      console.error('[PositionMonitor] Failed to close position:', err);
      alert(`Failed to close position: ${err.message}`);
    } finally {
      setClosingPositionId(null);
    }
  };

  // Get margin ratio color
  const getMarginRatioColor = (ratio: number) => {
    if (ratio < 15) return 'text-red-600 font-bold';
    if (ratio < 25) return 'text-yellow-600 font-semibold';
    return 'text-green-600';
  };

  // Get PnL color
  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600';
    if (pnl < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format percentage
  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading positions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <button
            onClick={fetchPositions}
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
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold text-gray-900">Open Positions</h3>
          <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-200 rounded-full">
            {positions.length}
          </span>
          {!isConnected && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-gray-400 rounded-full">
              Disconnected
            </span>
          )}
        </div>
        <button
          onClick={fetchPositions}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
          title="Refresh positions"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Positions Table */}
      <div className="flex-1 overflow-x-auto">
        {positions.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="mt-2 text-sm">No open positions</p>
              <p className="mt-1 text-xs text-gray-400">Waiting for signals...</p>
            </div>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Side</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Entry</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Current</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">P&L</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Margin Ratio</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Liquidation</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {positions.map((position) => (
                <tr key={`${position.session_id}:${position.symbol}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{position.symbol}</div>
                    <div className="text-xs text-gray-500">{position.leverage}x</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      position.side === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {position.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                    {position.quantity.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                    {formatCurrency(position.entry_price)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                    {formatCurrency(position.current_price)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className={`text-sm font-medium ${getPnLColor(position.unrealized_pnl)}`}>
                      {formatCurrency(position.unrealized_pnl)}
                    </div>
                    <div className={`text-xs ${getPnLColor(position.unrealized_pnl_pct)}`}>
                      {formatPercent(position.unrealized_pnl_pct)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className={`text-sm font-medium ${getMarginRatioColor(position.margin_ratio)}`}>
                      {position.margin_ratio.toFixed(1)}%
                    </div>
                    {position.margin_ratio < 25 && (
                      <div className="text-xs text-red-500">⚠️ Low margin</div>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                    {formatCurrency(position.liquidation_price)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-center">
                    <button
                      onClick={() => handleClosePosition(position)}
                      disabled={closingPositionId === `${position.session_id}:${position.symbol}`}
                      className="px-3 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {closingPositionId === `${position.session_id}:${position.symbol}` ? 'Closing...' : 'Close'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer Stats */}
      {positions.length > 0 && (
        <div className="p-3 border-t border-gray-200 bg-white">
          <div className="flex items-center justify-between text-xs">
            <div className="flex space-x-4">
              <span className="text-gray-600">
                Total P&L:
                <span className={`ml-1 font-medium ${getPnLColor(positions.reduce((sum, p) => sum + p.unrealized_pnl, 0))}`}>
                  {formatCurrency(positions.reduce((sum, p) => sum + p.unrealized_pnl, 0))}
                </span>
              </span>
              <span className="text-gray-600">
                Avg Margin:
                <span className={`ml-1 font-medium ${getMarginRatioColor(positions.reduce((sum, p) => sum + p.margin_ratio, 0) / positions.length)}`}>
                  {(positions.reduce((sum, p) => sum + p.margin_ratio, 0) / positions.length).toFixed(1)}%
                </span>
              </span>
            </div>
            <span className="text-gray-400">
              Updated: {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
