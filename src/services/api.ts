import axios, { AxiosResponse } from 'axios';
import {
  ApiResponse,
  Strategy,
  StrategyConfig,
  Indicator,
  Order,
  Position,
  TradingPerformance,
  WalletBalance
} from '@/types/api';
import { config } from '@/utils/config';
import { wsService } from './websocket';
import { recordApiCall } from '@/hooks/usePerformanceMonitor';
import { categorizeError, logUnifiedError, getErrorRecoveryStrategy } from '@/utils/statusUtils';

// Configure axios defaults
axios.defaults.baseURL = config.apiUrl;
axios.defaults.withCredentials = true;

// Cookie-based Authentication - HttpOnly cookies for security
class CookieAuth {
  private refreshPromise: Promise<void> | null = null;

  isAuthenticated(): boolean {
    // Since cookies are HttpOnly, we can't check directly
    // Assume authenticated if no recent 401
    return true; // Will be validated by server
  }

  async login(username: string, password: string): Promise<any> {
    try {
      const response = await axios.post('/api/v1/auth/login', {
        username,
        password
      });
      return response.data;
    } catch (error: any) {
      console.error('Login failed:', error);
      throw new Error(error.response?.data?.error_message || 'Login failed');
    }
  }

  async logout(): Promise<void> {
    try {
      await axios.post('/api/v1/auth/logout');
    } catch (error) {
      console.warn('Logout request failed:', error);
    }
  }

  async refreshTokens(): Promise<void> {
    // Return existing refresh promise if in progress
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    // Create new refresh promise
    this.refreshPromise = this.doRefresh();

    try {
      await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async doRefresh(): Promise<void> {
    try {
      await axios.post('/api/v1/auth/refresh');
    } catch (error: any) {
      console.error('Token refresh failed:', error);
      throw new Error('Session expired - please login again');
    }
  }
}

// Global cookie auth instance
const cookieAuth = new CookieAuth();

// Handle token refresh on 401 responses
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the tokens via cookies
        await cookieAuth.refreshTokens();

        // Retry the original request (cookies will be sent automatically)
        return axios(originalRequest);
      } catch (refreshError) {
        // Refresh failed - redirect to login or emit event
        console.error('Token refresh failed:', refreshError);
        // Could emit an event here to trigger login modal
        // window.dispatchEvent(new CustomEvent('auth:session-expired'));
      }
    }

    // Enhanced error handling for other API errors
    const unifiedError = categorizeError(error, 'API response interceptor');
    logUnifiedError(unifiedError);

    throw error;
  }
);

class ApiService {
  private pendingRequests = new Map<string, Promise<any>>();
  private requestTimeouts = new Map<string, NodeJS.Timeout>();

  // Authentication methods
  async login(username: string, password: string): Promise<any> {
    return cookieAuth.login(username, password);
  }

  async logout(): Promise<void> {
    return cookieAuth.logout();
  }

  isAuthenticated(): boolean {
    return cookieAuth.isAuthenticated();
  }

  private async dedupedRequest<T>(
    key: string,
    requestFn: () => Promise<T>,
    timeoutMs = 30000
  ): Promise<T> {
    // Check existing request
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key)!;
    }

    // Create timeout
    const timeoutPromise = new Promise<never>((_, reject) => {
      const timeout = setTimeout(() => {
        const timeoutError = new Error(`Request timeout: ${key}`);
        timeoutError.name = 'TimeoutError';
        reject(timeoutError);
      }, timeoutMs);
      this.requestTimeouts.set(key, timeout);
    });

    // Race between request and timeout with performance monitoring
    const startTime = performance.now();
    const promise = Promise.race([
      requestFn(),
      timeoutPromise
    ]).then((result) => {
      const duration = performance.now() - startTime;
      recordApiCall(duration, true);
      return result;
    }).catch((error) => {
      const duration = performance.now() - startTime;
      recordApiCall(duration, false);

      // Enhanced error handling with unified error categorization
      const unifiedError = categorizeError(error, `API request: ${key}`);
      logUnifiedError(unifiedError);

      // Apply recovery strategy if applicable
      const recoveryStrategy = getErrorRecoveryStrategy(unifiedError);
      if (recoveryStrategy.shouldRetry && this.pendingRequests.has(key)) {
        // For retryable errors, we could implement retry logic here
        // For now, just log the recovery suggestion
        console.info(`API Error Recovery: ${recoveryStrategy.fallbackAction}`);
      }

      throw error;
    }).finally(() => {
      this.pendingRequests.delete(key);
      if (this.requestTimeouts.has(key)) {
        clearTimeout(this.requestTimeouts.get(key)!);
        this.requestTimeouts.delete(key);
      }
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  // REST API Methods

  async getStrategies(): Promise<Strategy[]> {
    return this.dedupedRequest('getStrategies', async () => {
      const response = await axios.get<ApiResponse<{ strategies: Strategy[] }>>('/strategies');
      return response.data.data?.strategies || [];
    });
  }

  async getStrategyStatus(): Promise<Strategy[]> {
    return this.dedupedRequest('getStrategyStatus', async () => {
      const response = await axios.get<ApiResponse<{ strategies: Strategy[] }>>('/strategies/status');
      return response.data.data?.strategies || [];
    });
  }

  async getStrategy(name: string): Promise<Strategy> {
    try {
      const response = await axios.get<ApiResponse<{ strategy_data: Strategy }>>(`/strategies/${name}`);
      if (!response.data.data?.strategy_data) {
        throw new Error(`Strategy '${name}' not found or invalid response format`);
      }
      return response.data.data.strategy_data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error(`API error: GET /strategies/${name}`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get strategy '${name}': ${errorMessage}`);
    }
  }

  async createStrategy(config: StrategyConfig, validateOnly = false): Promise<any> {
    const response = await axios.post<ApiResponse>(
      '/strategies',
      {
        strategy_config: config,
        validate_only: validateOnly
      }
    );
    return response.data;
  }

  async updateStrategy(name: string, config: StrategyConfig): Promise<any> {
    return this.createStrategy({ ...config, strategy_name: name });
  }

  async deleteStrategy(name: string): Promise<any> {
    const response = await axios.delete<ApiResponse>(`/strategies/${name}`);
    return response.data;
  }

  async activateStrategy(name: string, symbol: string): Promise<any> {
    const response = await axios.post<ApiResponse>(`/strategies/${name}/activate`, { symbol });
    return response.data;
  }

  async deactivateStrategy(name: string, symbol: string): Promise<any> {
    const response = await axios.post<ApiResponse>(`/strategies/${name}/deactivate`, { symbol });
    return response.data;
  }

  // Indicator API Methods

  async getIndicators(scope?: string, symbol?: string, type?: string): Promise<Indicator[]> {
    const params = new URLSearchParams();
    if (scope) params.append('scope', scope);
    if (symbol) params.append('symbol', symbol);
    if (type) params.append('type', type);
    const queryString = params.toString();
    const key = `getIndicators:${queryString}`;

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<{ indicators: Indicator[] }>>(
        `/indicators?${queryString}`
      );
      return response.data.data?.indicators || [];
    });
  }

  async getIndicatorTypes(): Promise<string[]> {
    return this.dedupedRequest('getIndicatorTypes', async () => {
      const response = await axios.get<ApiResponse<{ types: string[] }>>('/indicators/types');
      return response.data.data?.types || [];
    });
  }

  async getSystemIndicators(): Promise<any[]> {
    return this.dedupedRequest('getSystemIndicators', async () => {
      const response = await axios.get<ApiResponse<{ indicators: any[] }>>('/api/indicators/system');
      return response.data.data?.indicators || [];
    });
  }

  async getIndicatorValuesLegacy(symbol: string): Promise<any> {
    return this.dedupedRequest(`getIndicatorValues:${symbol}`, async () => {
      const response = await axios.get<ApiResponse<any>>(`/api/v1/indicators/${symbol}`);
      return response.data.data || {};
    });
  }

  async getSymbols(): Promise<string[]> {
    return this.dedupedRequest('getSymbols', async () => {
      const response = await axios.get<ApiResponse<{ status: string; data: { symbols: string[] } }>>('/symbols');
      return response.data.data?.data?.symbols || [];
    });
  }

  async getMarketData(): Promise<any> {
    const response = await axios.get<ApiResponse<any>>('/market-data');
    return response.data;
  }

  async addIndicator(
    arg1: string | { symbol: string; indicator_type: string; period?: number; timeframe?: string; scope?: string; params?: any },
    indicatorType?: string,
    period = 20,
    timeframe = '1m',
    scope?: string
  ): Promise<any> {
    let payload: any;
    if (typeof arg1 === 'string') {
      payload = {
        symbol: arg1,
        indicator_type: indicatorType,
        period,
        timeframe,
        scope
      };
    } else {
      payload = {
        period: 20,
        timeframe: '1m',
        ...arg1,
      };
    }
    const response = await axios.post<ApiResponse>('/indicators', payload);
    return response.data;
  }

  async updateIndicator(
    key: string,
    spec: { symbol: string; indicator_type: string; period?: number; timeframe?: string; scope?: string; params?: any }
  ): Promise<any> {
    const payload = {
      period: 20,
      timeframe: '1m',
      ...spec,
    };
    const response = await axios.put<ApiResponse>(`/indicators/${key}`, payload);
    return response.data;
  }

  async deleteIndicator(key: string): Promise<any> {
    const response = await axios.delete<ApiResponse>(`/indicators/${key}`);
    return response.data;
  }

  // Generic HTTP methods for unified indicator system
  async get(url: string): Promise<any> {
    return this.dedupedRequest(`GET:${url}`, async () => {
      const response = await axios.get(url);
      return response.data;
    });
  }

  async post(url: string, data: any): Promise<any> {
    const response = await axios.post(url, data);
    return response.data;
  }

  async put(url: string, data: any): Promise<any> {
    const response = await axios.put(url, data);
    return response.data;
  }

  async delete(url: string): Promise<any> {
    const response = await axios.delete(url);
    return response.data;
  }

  // Variant API Methods

  async getVariants(type?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (type && type !== 'all') params.append('type', type);
    const queryString = params.toString();
    const key = `getVariants:${queryString}`;

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<{ variants: any[] }>>(
        `/api/indicators/variants?${queryString}`
      );
      return response.data.data?.variants || [];
    });
  }

  async createVariant(variantData: any): Promise<any> {
    const response = await axios.post<ApiResponse>('/api/indicators/variants', variantData);
    return response.data;
  }

  async updateVariant(variantId: string, variantData: any): Promise<any> {
    const response = await axios.put<ApiResponse>(`/api/indicators/variants/${variantId}`, variantData);
    return response.data;
  }

  async deleteVariant(variantId: string): Promise<any> {
    const response = await axios.delete<ApiResponse>(`/api/indicators/variants/${variantId}`);
    return response.data;
  }

  async addIndicatorToSession(
    sessionId: string,
    symbol: string,
    payload: { variant_id: string; parameters?: any; force_recalculate?: boolean }
  ): Promise<any> {
    const response = await axios.post(`/api/indicators/sessions/${sessionId}/symbols/${symbol}/indicators`, payload);
    return response.data?.data ?? response.data;
  }

  async getSessionIndicatorValues(
    sessionId: string,
    symbol: string
  ): Promise<{
    indicators: Record<string, any>;
    files: Record<string, { path: string; exists: boolean; size: number }>;
    timestamp: number;
  }> {
    const response = await axios.get(`/api/indicators/sessions/${sessionId}/symbols/${symbol}/values`);
    const data = response.data?.data ?? response.data ?? {};
    return {
      indicators: data.indicators || {},
      files: data.files || {},
      timestamp: data.timestamp || Date.now()
    };
  }

  // Trading API Methods

  async startBacktest(symbols: string[], config: any = {}): Promise<any> {
    const response = await axios.post<ApiResponse>('/sessions/start', {
      session_type: 'backtest',
      strategy_config: config.strategy_config || {},
      config: {
        acceleration_factor: config.acceleration_factor || 10,
        ...config
      }
    });
    return response.data;
  }

  async startLiveTrading(symbols: string[], config: any = {}): Promise<any> {
    const response = await axios.post<ApiResponse>('/sessions/start', {
      session_type: 'live',
      strategy_config: config.strategy_config || {},
      config
    });
    return response.data;
  }

  async stopSession(sessionId?: string): Promise<any> {
    const payload = sessionId ? { session_id: sessionId } : {};
    const response = await axios.post<ApiResponse>('/sessions/stop', payload);
    return response.data;
  }

  async getSessionStatus(sessionId: string): Promise<any> {
    try {
      const response = await axios.get<ApiResponse>(`/sessions/${sessionId}`);
      if (!response.data) {
        throw new Error(`Session '${sessionId}' not found or invalid response`);
      }
      return response.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error(`API error: GET /sessions/${sessionId}`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get session status '${sessionId}': ${errorMessage}`);
    }
  }

  async startSession(sessionData: any): Promise<any> {
    try {
      const response = await axios.post<ApiResponse>('/sessions/start', sessionData);
      return response.data;
    } catch (error: any) {
      // Handle specific authentication errors
      if (error.response?.status === 401 || error.response?.status === 403) {
        // Clear any stale cookies by logging out
        await cookieAuth.logout();
        throw new Error('Authentication failed. Please login again.');
      }

      // Handle other API errors
      const errorMessage = error?.response?.data?.error_message ||
                           error?.response?.data?.message ||
                           error?.message ||
                           'Unknown error occurred';

      console.error(`API error: POST /sessions/start`, { error: errorMessage, status: error?.response?.status });
      throw new Error(`Failed to start session: ${errorMessage}`);
    }
  }

  async getExecutionStatus(): Promise<any> {
    try {
      const response = await axios.get<ApiResponse>('/sessions/execution-status');
      if (!response.data?.data) {
        throw new Error('Invalid execution status response format');
      }
      return response.data.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error('API error: GET /sessions/execution-status', {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get execution status: ${errorMessage}`);
    }
  }

  async getDataCollectionSessions(limit: number = 50, includeStats: boolean = false): Promise<any> {
    try {
      const response = await axios.get<ApiResponse>('/api/data-collection/sessions', {
        params: { limit, include_stats: includeStats }
      });
      if (!response.data?.sessions) {
        throw new Error('Invalid sessions response format');
      }
      return response.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error('API error: GET /api/data-collection/sessions', {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get data collection sessions: ${errorMessage}`);
    }
  }

  async deleteDataCollectionSession(sessionId: string): Promise<any> {
    try {
      const response = await axios.delete<ApiResponse>(`/api/data-collection/sessions/${sessionId}`);
      return response.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error(`API error: DELETE /api/data-collection/sessions/${sessionId}`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to delete session: ${errorMessage}`);
    }
  }

  async getChartData(sessionId: string, symbol: string, maxPoints: number = 10000): Promise<any> {
    try {
      const response = await axios.get<ApiResponse>(`/api/data-collection/${sessionId}/chart-data`, {
        params: {
          symbol,
          max_points: maxPoints
        }
      });
      return response.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Unknown error';
      console.error(`API error: GET /api/data-collection/${sessionId}/chart-data`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        symbol,
        maxPoints
      });
      throw new Error(`Failed to get chart data: ${errorMessage}`);
    }
  }

  async saveStrategy(strategyConfig: any): Promise<any> {
    const response = await axios.post<ApiResponse>('/api/strategies', strategyConfig);
    return response.data;
  }

  async validateStrategy(strategyConfig: any): Promise<any> {
    const response = await axios.post<ApiResponse>('/api/strategies/validate', strategyConfig);
    return response.data;
  }

  async get4SectionStrategies(): Promise<any[]> {
    const response = await axios.get<ApiResponse<{ strategies: any[] }>>('/api/strategies');
    return response.data.data?.strategies || [];
  }

  async get4SectionStrategy(strategyId: string): Promise<any> {
    const response = await axios.get<ApiResponse<{ strategy: any }>>(`/api/strategies/${strategyId}`);
    return response.data.data?.strategy;
  }

  async update4SectionStrategy(strategyId: string, strategyConfig: any): Promise<any> {
    const response = await axios.put<ApiResponse>(`/api/strategies/${strategyId}`, strategyConfig);
    return response.data;
  }

  async delete4SectionStrategy(strategyId: string): Promise<any> {
    const response = await axios.delete<ApiResponse>(`/api/strategies/${strategyId}`);
    return response.data;
  }

  // Wallet API Methods

  async getWalletBalance(): Promise<WalletBalance> {
    return this.dedupedRequest('getWalletBalance', async () => {
      try {
        const response = await axios.get<ApiResponse<WalletBalance>>('/wallet/balance');
        if (!response.data?.data) {
          throw new Error('Invalid wallet balance response format');
        }
        return response.data.data;
      } catch (error: any) {
        const errorMessage = error?.response?.data?.error_message ||
                            error?.response?.data?.message ||
                            error?.message ||
                            'Unknown error occurred';
        console.error('API error: GET /wallet/balance', {
          error: errorMessage,
          status: error?.response?.status,
          statusText: error?.response?.statusText
        });
        throw new Error(`Failed to get wallet balance: ${errorMessage}`);
      }
    });
  }

  // Order Management API Methods

  async getOrders(): Promise<Order[]> {
    return this.dedupedRequest('getOrders', async () => {
      const response = await axios.get<ApiResponse<{ orders: Order[] }>>('/orders');
      return response.data.data?.orders || [];
    });
  }

  async getOrder(orderId: string): Promise<Order> {
    try {
      const response = await axios.get<ApiResponse<{ order: Order }>>(`/orders/${orderId}`);
      if (!response.data?.data?.order) {
        throw new Error(`Order '${orderId}' not found or invalid response format`);
      }
      return response.data.data.order;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error(`API error: GET /orders/${orderId}`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get order '${orderId}': ${errorMessage}`);
    }
  }

  async getPositions(): Promise<Position[]> {
    return this.dedupedRequest('getPositions', async () => {
      const response = await axios.get<ApiResponse<{ positions: Position[] }>>('/positions');
      return response.data.data?.positions || [];
    });
  }

  async getPosition(symbol: string): Promise<Position> {
    try {
      const response = await axios.get<ApiResponse<{ position: Position }>>(`/positions/${symbol}`);
      if (!response.data?.data?.position) {
        throw new Error(`Position for symbol '${symbol}' not found or invalid response format`);
      }
      return response.data.data.position;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error(`API error: GET /positions/${symbol}`, {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get position for '${symbol}': ${errorMessage}`);
    }
  }

  async getTradingPerformance(): Promise<TradingPerformance> {
    try {
      const response = await axios.get<ApiResponse<TradingPerformance>>('/trading/performance');
      if (!response.data?.data) {
        throw new Error('Invalid trading performance response format');
      }
      return response.data.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';
      console.error('API error: GET /trading/performance', {
        error: errorMessage,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      });
      throw new Error(`Failed to get trading performance: ${errorMessage}`);
    }
  }

  // Risk Management API Methods

  async getBudgetSummary(): Promise<any> {
    const response = await axios.get<ApiResponse>('/risk/budget');
    return response.data.data;
  }

  async allocateBudget(strategyName: string, amount: number, maxAllocationPct = 5.0): Promise<any> {
    const response = await axios.post<ApiResponse>('/risk/budget/allocate', {
      strategy_name: strategyName,
      amount,
      max_allocation_pct: maxAllocationPct
    });
    return response.data;
  }

  async assessPositionRisk(symbol: string, positionSize: number, currentPrice: number,
                          volatility = 0.02, maxDrawdown = 0.05, sharpeRatio = 1.5): Promise<any> {
    const response = await axios.post<ApiResponse>('/risk/assess-position', {
      symbol,
      position_size: positionSize,
      current_price: currentPrice,
      volatility,
      max_drawdown: maxDrawdown,
      sharpe_ratio: sharpeRatio
    });
    return response.data;
  }


  // Utility Methods

  async healthCheck(): Promise<any> {
    return this.dedupedRequest('healthCheck', async () => {
      try {
        const response = await axios.get<ApiResponse>('/health');
        if (!response.data) {
          throw new Error('Invalid health check response format');
        }
        return response.data;
      } catch (error: any) {
        const errorMessage = error?.response?.data?.error_message ||
                            error?.response?.data?.message ||
                            error?.message ||
                            'Unknown error occurred';
        console.error('API error: GET /health', {
          error: errorMessage,
          status: error?.response?.status,
          statusText: error?.response?.statusText
        });
        throw new Error(`Health check failed: ${errorMessage}`);
      }
    });
  }


  async isWebSocketConnected(): Promise<boolean> {
    try {
      const isConnected = wsService.isWebSocketConnected();
      // Additional validation - check if connection is actually responsive
      if (isConnected) {
        // Could add additional health checks here
        return true;
      }
      return false;
    } catch (error) {
      console.warn('Failed to check WebSocket connection status:', error);
      return false;
    }
  }

  async checkDataCollectionRequirements(): Promise<{
    canStart: boolean;
    issues: string[];
    requirements: string[];
  }> {
    const issues: string[] = [];
    const requirements: string[] = [];

    // Check authentication
    if (!this.isAuthenticated()) {
      issues.push('User is not authenticated');
      requirements.push('Login with valid credentials');
    }

    // Check backend connectivity
    try {
      await this.healthCheck();
    } catch (error) {
      issues.push('Backend server is not accessible');
      requirements.push('Ensure backend server is running and accessible');
    }

    // Check WebSocket connection
    try {
      const wsConnected = await this.isWebSocketConnected();
      if (!wsConnected) {
        issues.push('WebSocket connection is not established');
        requirements.push('Ensure WebSocket server is running and accessible');
      }
    } catch (error) {
      issues.push('Unable to check WebSocket status');
      requirements.push('Check WebSocket configuration');
    }

    return {
      canStart: issues.length === 0,
      issues,
      requirements
    };
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
