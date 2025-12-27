/**
 * OrderHistory Component - Agent 6
 * ==================================
 * Displays order execution history with real-time updates via WebSocket.
 *
 * Features:
 * - Real-time updates via WebSocket (order_created, order_filled, order_cancelled)
 * - Fetch historical orders via REST API
 * - Filters: Status (all, pending, filled, cancelled), Symbol, Time range
 * - Pagination (20 orders per page)
 * - Color coding: GREEN=filled, YELLOW=pending, RED=cancelled/failed
 * - Slippage calculation
 * - Export to CSV button (optional)
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { Order, tradingAPI } from '@/services/TradingAPI';
import { Logger } from '@/services/frontendLogService';

// ========================================
// TypeScript Types
// ========================================

interface OrderHistoryProps {
  session_id?: string;
  className?: string;
}

type OrderStatus = 'all' | 'PENDING' | 'SUBMITTED' | 'FILLED' | 'PARTIALLY_FILLED' | 'CANCELLED' | 'FAILED';

// ========================================
// Component
// ========================================

export default function OrderHistory({
  session_id,
  className = ''
}: OrderHistoryProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<OrderStatus>('all');
  const [symbolFilter, setSymbolFilter] = useState<string>('all');
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const ordersPerPage = 20;

  const { lastMessage, isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      // Listen for order events from live_trading stream
      if (message.type === 'data' && message.stream === 'live_trading') {
        const data = message.data;
        if (data.order_id) {
          handleOrderUpdate(data);
        }
      }
      // Also listen for direct order events
      else if (
        message.type === 'order_created' ||
        message.type === 'order_filled' ||
        message.type === 'order_cancelled' ||
        message.stream === 'order_created' ||
        message.stream === 'order_filled' ||
        message.stream === 'order_cancelled'
      ) {
        handleOrderUpdate(message.data);
      }
    }
  });

  // Fetch initial orders
  useEffect(() => {
    fetchOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session_id]);

  // Apply filters
  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, statusFilter, symbolFilter]);

  // Fetch orders from REST API
  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await tradingAPI.getOrders({
        session_id,
        limit: 500 // Get more orders for filtering
      });

      setOrders(data);

      // Extract unique symbols
      const symbols = Array.from(new Set(data.map(o => o.symbol)));
      setAvailableSymbols(symbols);
    } catch (err: any) {
      Logger.error('OrderHistory.fetchOrders', 'Failed to fetch orders', { error: err });
      setError(err.message || 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  // Handle order update from WebSocket
  const handleOrderUpdate = (data: any) => {
    setOrders(prev => {
      const index = prev.findIndex(o => o.order_id === data.order_id);
      if (index >= 0) {
        // Update existing order
        const updated = [...prev];
        updated[index] = { ...updated[index], ...data };
        return updated;
      } else {
        // Add new order (prepend to show newest first)
        return [data as Order, ...prev];
      }
    });
  };

  // Apply filters to orders
  const applyFilters = () => {
    let filtered = [...orders];

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(o => o.status === statusFilter);
    }

    // Symbol filter
    if (symbolFilter !== 'all') {
      filtered = filtered.filter(o => o.symbol === symbolFilter);
    }

    // Sort by created_at descending (newest first)
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    setFilteredOrders(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  };

  // Get paginated orders
  const getPaginatedOrders = () => {
    const startIndex = (currentPage - 1) * ordersPerPage;
    const endIndex = startIndex + ordersPerPage;
    return filteredOrders.slice(startIndex, endIndex);
  };

  // Calculate total pages
  const totalPages = Math.ceil(filteredOrders.length / ordersPerPage);

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'FILLED':
        return 'text-green-600 bg-green-50 border-green-300';
      case 'PENDING':
      case 'SUBMITTED':
      case 'PARTIALLY_FILLED':
        return 'text-yellow-600 bg-yellow-50 border-yellow-300';
      case 'CANCELLED':
      case 'FAILED':
        return 'text-red-600 bg-red-50 border-red-300';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-300';
    }
  };

  // Calculate slippage percentage
  const calculateSlippage = (order: Order): number | null => {
    if (!order.average_fill_price || !order.requested_price) return null;

    const slippage = ((order.average_fill_price - order.requested_price) / order.requested_price) * 100;
    return slippage;
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

  // Export to CSV
  const exportToCSV = () => {
    const headers = ['Time', 'Symbol', 'Side', 'Type', 'Quantity', 'Price', 'Filled Price', 'Status', 'Slippage'];
    const rows = filteredOrders.map(order => [
      formatTimestamp(order.created_at),
      order.symbol,
      order.side,
      order.order_type,
      order.quantity.toString(),
      order.requested_price.toString(),
      order.average_fill_price?.toString() || 'N/A',
      order.status,
      calculateSlippage(order)?.toFixed(4) + '%' || 'N/A'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `order_history_${new Date().toISOString()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading orders...</p>
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
            onClick={fetchOrders}
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
          <h3 className="text-lg font-semibold text-gray-900">Order History</h3>
          <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-200 rounded-full">
            {filteredOrders.length}
          </span>
          {!isConnected && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-gray-400 rounded-full">
              Disconnected
            </span>
          )}
        </div>
        <div className="flex space-x-2">
          <button
            onClick={fetchOrders}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
            title="Refresh orders"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          {filteredOrders.length > 0 && (
            <button
              onClick={exportToCSV}
              className="px-3 py-1 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700"
            >
              Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4 p-3 border-b border-gray-200 bg-gray-50">
        {/* Status Filter */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as OrderStatus)}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="PENDING">Pending</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="FILLED">Filled</option>
            <option value="PARTIALLY_FILLED">Partially Filled</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="FAILED">Failed</option>
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

        {/* Reset Filters */}
        {(statusFilter !== 'all' || symbolFilter !== 'all') && (
          <button
            onClick={() => {
              setStatusFilter('all');
              setSymbolFilter('all');
            }}
            className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Orders Table */}
      <div className="flex-1 overflow-x-auto">
        {filteredOrders.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="mt-2 text-sm">No orders found</p>
              <p className="mt-1 text-xs text-gray-400">
                {orders.length > 0 ? 'Try adjusting filters' : 'Waiting for orders...'}
              </p>
            </div>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Side</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Filled Price</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Slippage</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {getPaginatedOrders().map((order) => {
                const slippage = calculateSlippage(order);
                return (
                  <tr key={order.order_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {formatTimestamp(order.created_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      {order.symbol}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        order.side === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {order.side}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {order.order_type}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                      {order.quantity.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                      {formatCurrency(order.requested_price)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm text-gray-900">
                      {order.average_fill_price ? formatCurrency(order.average_fill_price) : 'N/A'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded border ${getStatusColor(order.status)}`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm">
                      {slippage !== null ? (
                        <span className={slippage >= 0 ? 'text-red-600' : 'text-green-600'}>
                          {slippage >= 0 ? '+' : ''}{slippage.toFixed(4)}%
                        </span>
                      ) : (
                        <span className="text-gray-400">N/A</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-3 border-t border-gray-200 bg-white">
          <div className="text-sm text-gray-600">
            Showing {((currentPage - 1) * ordersPerPage) + 1} to {Math.min(currentPage * ordersPerPage, filteredOrders.length)} of {filteredOrders.length} orders
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm text-gray-700">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
