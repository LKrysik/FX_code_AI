/**
 * TradingAPI Service - Agent 6
 * =============================
 * TypeScript service for live trading REST API calls.
 *
 * Endpoints:
 * - GET /api/trading/positions - Query live positions
 * - POST /api/trading/positions/:id/close - Close a position
 * - GET /api/trading/orders - Query live orders
 * - POST /api/trading/orders/:id/cancel - Cancel an order
 * - GET /api/trading/performance/:session_id - Get session performance
 */

import { csrfService } from './csrfService';
import { Logger } from './frontendLogService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// ========================================
// TypeScript Types
// ========================================

export interface Position {
  session_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  current_price: number;
  liquidation_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  margin: number;
  leverage: number;
  margin_ratio: number;
  opened_at: string;
  updated_at: string;
  status: 'OPEN' | 'CLOSED' | 'LIQUIDATED';

  // Risk management (optional - may not be set)
  stop_loss_price?: number;
  take_profit_price?: number;
}

export interface Order {
  session_id: string;
  order_id: string;
  exchange_order_id?: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT';
  quantity: number;
  requested_price: number;
  filled_quantity: number;
  average_fill_price?: number;
  status: 'PENDING' | 'SUBMITTED' | 'FILLED' | 'PARTIALLY_FILLED' | 'CANCELLED' | 'FAILED';
  error_message?: string;
  slippage?: number;
  commission?: number;
  created_at: string;
  updated_at: string;
  filled_at?: string;
}

export interface Performance {
  session_id: string;
  total_pnl: number;
  total_pnl_pct: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio?: number;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
}

export interface ClosePositionResponse {
  success: boolean;
  message: string;
  order_id?: string;
  closed_pnl?: number;
}

export interface CancelOrderResponse {
  success: boolean;
  message: string;
  order_id: string;
  cancelled_at: string;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// ========================================
// API Error Handling
// ========================================

export class TradingAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'TradingAPIError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new TradingAPIError(
      errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData
    );
  }

  const data = await response.json();
  return data;
}

// ========================================
// TradingAPI Class
// ========================================

export class TradingAPI {
  private baseUrl: string;
  private headers: HeadersInit;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json'
    };
  }

  /**
   * Set authentication token for API requests
   */
  setAuthToken(token: string) {
    this.headers = {
      ...this.headers,
      'Authorization': `Bearer ${token}`
    };
  }

  /**
   * Get headers with CSRF token for state-changing requests
   */
  private async getHeadersWithCsrf(): Promise<HeadersInit> {
    try {
      const csrfToken = await csrfService.getToken();
      return {
        ...this.headers,
        'X-CSRF-Token': csrfToken
      };
    } catch (error) {
      Logger.warn('trading_api.csrf_token_failed', { error: String(error) });
      return this.headers;
    }
  }

  /**
   * GET /api/trading/positions
   * Query live positions with optional filters
   */
  async getPositions(params?: {
    session_id?: string;
    symbol?: string;
    status?: 'OPEN' | 'CLOSED' | 'LIQUIDATED';
  }): Promise<Position[]> {
    const queryParams = new URLSearchParams();
    if (params?.session_id) queryParams.append('session_id', params.session_id);
    if (params?.symbol) queryParams.append('symbol', params.symbol);
    if (params?.status) queryParams.append('status', params.status);

    const url = `${this.baseUrl}/api/trading/positions${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.headers
    });

    const data = await handleResponse<{ success: boolean; positions: Position[]; count: number }>(response);
    return data.positions;
  }

  /**
   * POST /api/trading/positions/:position_id/close
   * Close a live position
   *
   * @param position_id - Format: "session_id:symbol" (e.g., "live_20251107_abc:BTC_USDT")
   * @param reason - Reason for closing (default: "USER_REQUESTED")
   */
  async closePosition(position_id: string, reason: string = 'USER_REQUESTED'): Promise<ClosePositionResponse> {
    const url = `${this.baseUrl}/api/trading/positions/${encodeURIComponent(position_id)}/close`;
    const headers = await this.getHeadersWithCsrf();

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ reason })
    });

    return handleResponse<ClosePositionResponse>(response);
  }

  /**
   * GET /api/trading/orders
   * Query live orders with optional filters
   */
  async getOrders(params?: {
    session_id?: string;
    symbol?: string;
    status?: string;
    limit?: number;
  }): Promise<Order[]> {
    const queryParams = new URLSearchParams();
    if (params?.session_id) queryParams.append('session_id', params.session_id);
    if (params?.symbol) queryParams.append('symbol', params.symbol);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const url = `${this.baseUrl}/api/trading/orders${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.headers
    });

    const data = await handleResponse<{ success: boolean; orders: Order[]; count: number }>(response);
    return data.orders;
  }

  /**
   * POST /api/trading/orders/:order_id/cancel
   * Cancel a pending or partially filled order
   */
  async cancelOrder(order_id: string): Promise<CancelOrderResponse> {
    const url = `${this.baseUrl}/api/trading/orders/${encodeURIComponent(order_id)}/cancel`;
    const headers = await this.getHeadersWithCsrf();

    const response = await fetch(url, {
      method: 'POST',
      headers
    });

    return handleResponse<CancelOrderResponse>(response);
  }

  /**
   * GET /api/trading/performance/:session_id
   * Get session performance metrics
   */
  async getPerformance(session_id: string): Promise<Performance> {
    const url = `${this.baseUrl}/api/trading/performance/${encodeURIComponent(session_id)}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.headers
    });

    return handleResponse<Performance>(response);
  }
}

// Export singleton instance
export const tradingAPI = new TradingAPI();

// Export default
export default tradingAPI;
