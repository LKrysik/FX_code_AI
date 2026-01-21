/**
 * Backtest API Service
 * ====================
 * API client for backtest-related operations.
 * Story: 1b-1-backtest-session-setup
 *
 * Provides methods for:
 * - Checking data availability for backtesting
 * - Starting backtest sessions
 * - Getting historical data info
 */

import axios from 'axios';
import { config } from '@/utils/config';
import { Logger } from './frontendLogService';
import { ApiResponse } from '@/types/api';

// Configure axios defaults
axios.defaults.baseURL = config.apiUrl;
axios.defaults.withCredentials = true;

// =============================================================================
// Types
// =============================================================================

export interface DataAvailabilityRequest {
  symbol: string;
  start_date: string; // ISO format: YYYY-MM-DD
  end_date: string;   // ISO format: YYYY-MM-DD
}

export interface DataAvailabilityResponse {
  available: boolean;
  symbol: string;
  start_date: string;
  end_date: string;
  coverage_pct: number;
  total_records: number;
  expected_records: number;
  missing_ranges: Array<{
    start: string;
    end: string;
    gap_hours: number;
  }>;
  data_quality: 'good' | 'warning' | 'error';
  quality_issues: string[];
}

export interface BacktestStartRequest {
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  session_id?: string;  // Data collection session ID (for QuestDB historical data)
  config?: {
    acceleration_factor?: number;
    initial_balance?: number;
    stop_loss_percent?: number;
    take_profit_percent?: number;
  };
}

export interface BacktestStartResponse {
  session_id: string;
  status: 'started' | 'pending';
  symbol: string;
  strategy_id: string;
  start_date: string;
  end_date: string;
  estimated_duration_seconds?: number;
}

export interface StrategyListItem {
  id: string;
  strategy_name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DataCollectionSession {
  session_id: string;
  symbols: string[];
  status: string;
  start_time?: string;
  end_time?: string;
  records_collected?: number;
  prices_count?: number;
  orderbook_count?: number;
  duration_seconds?: number;
  created_at: string;
}

// =============================================================================
// API Service
// =============================================================================

class BacktestApiService {
  /**
   * Check data availability for a given symbol and date range.
   *
   * AC4: System validates that historical data exists for the selected range
   * AC5: Warning shows if data is incomplete or missing for the range
   */
  async checkDataAvailability(
    request: DataAvailabilityRequest
  ): Promise<DataAvailabilityResponse> {
    try {
      const response = await axios.get<ApiResponse<DataAvailabilityResponse>>(
        '/api/backtest/data-availability',
        {
          params: {
            symbol: request.symbol,
            start_date: request.start_date,
            end_date: request.end_date,
          },
        }
      );

      if (!response.data?.data) {
        throw new Error('Invalid data availability response format');
      }

      return response.data.data;
    } catch (error: any) {
      Logger.error('backtestApi.checkDataAvailability', {
        symbol: request.symbol,
        start_date: request.start_date,
        end_date: request.end_date,
        error: error.message,
      }, error);

      // Return a default "unavailable" response on error
      return {
        available: false,
        symbol: request.symbol,
        start_date: request.start_date,
        end_date: request.end_date,
        coverage_pct: 0,
        total_records: 0,
        expected_records: 0,
        missing_ranges: [],
        data_quality: 'error',
        quality_issues: [error.message || 'Failed to check data availability'],
      };
    }
  }

  /**
   * Start a backtest session with the given configuration.
   *
   * AC6: "Start Backtest" button starts the session and redirects to dashboard
   */
  async startBacktest(request: BacktestStartRequest): Promise<BacktestStartResponse> {
    try {
      const response = await axios.post<ApiResponse<BacktestStartResponse>>(
        '/api/backtest/start',
        {
          strategy_id: request.strategy_id,
          symbol: request.symbol,
          start_date: request.start_date,
          end_date: request.end_date,
          session_id: request.session_id,
          config: request.config || {},
        }
      );

      if (!response.data?.data) {
        throw new Error('Invalid backtest start response format');
      }

      Logger.info('backtestApi.startBacktest', {
        session_id: response.data.data.session_id,
        strategy_id: request.strategy_id,
        symbol: request.symbol,
      });

      return response.data.data;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          error?.message ||
                          'Unknown error occurred';

      Logger.error('backtestApi.startBacktest', {
        strategy_id: request.strategy_id,
        symbol: request.symbol,
        error: errorMessage,
        status: error?.response?.status,
      }, error);

      throw new Error(`Failed to start backtest: ${errorMessage}`);
    }
  }

  /**
   * Get list of available strategies for backtesting.
   *
   * AC1: Setup form allows selecting a strategy from saved strategies
   */
  async getStrategies(): Promise<StrategyListItem[]> {
    try {
      const response = await axios.get<ApiResponse<{ strategies: StrategyListItem[] }>>(
        '/api/strategies'
      );

      if (!response.data?.data?.strategies) {
        return [];
      }

      return response.data.data.strategies;
    } catch (error: any) {
      Logger.error('backtestApi.getStrategies', {
        error: error.message,
        status: error?.response?.status,
      }, error);

      throw new Error('Failed to fetch strategies');
    }
  }

  /**
   * Get list of available trading symbols.
   *
   * AC2: Setup form allows selecting a trading symbol
   */
  async getSymbols(): Promise<string[]> {
    try {
      const response = await axios.get<ApiResponse<{ symbols: string[] }>>(
        '/api/exchange/symbols'
      );

      // Handle various response formats
      const symbols = response.data?.data?.symbols ||
                     (response.data as any)?.symbols ||
                     [];

      return symbols;
    } catch (error: any) {
      Logger.error('backtestApi.getSymbols', {
        error: error.message,
        status: error?.response?.status,
      }, error);

      // Return common symbols as fallback
      return [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'AVAXUSDT',
      ];
    }
  }

  /**
   * Get list of data collection sessions available for backtesting.
   *
   * Used to select historical data source for backtest.
   */
  async getDataCollectionSessions(
    limit: number = 50,
    includeStats: boolean = true
  ): Promise<DataCollectionSession[]> {
    try {
      const response = await axios.get<{ sessions: DataCollectionSession[] }>(
        '/api/data-collection/sessions',
        {
          params: { limit, include_stats: includeStats },
        }
      );

      const sessions = response.data?.sessions || [];

      // Filter only completed sessions (valid for backtest)
      return sessions.filter(
        (s) => s.status === 'completed' && (s.records_collected || 0) > 0
      );
    } catch (error: any) {
      Logger.error('backtestApi.getDataCollectionSessions', {
        error: error.message,
        status: error?.response?.status,
      }, error);

      return [];
    }
  }

  /**
   * Validate backtest configuration before starting.
   *
   * Returns validation errors if any.
   */
  validateBacktestConfig(config: {
    strategy_id?: string;
    symbol?: string;
    start_date?: string;
    end_date?: string;
    session_id?: string;
  }): { isValid: boolean; errors: Record<string, string> } {
    const errors: Record<string, string> = {};

    // AC7: Validation errors highlight missing fields
    if (!config.strategy_id) {
      errors.strategy_id = 'Please select a strategy';
    }

    if (!config.symbol) {
      errors.symbol = 'Please select a trading symbol';
    }

    if (!config.start_date) {
      errors.start_date = 'Please select a start date';
    }

    if (!config.end_date) {
      errors.end_date = 'Please select an end date';
    }

    // Validate date range
    if (config.start_date && config.end_date) {
      const startDate = new Date(config.start_date);
      const endDate = new Date(config.end_date);

      if (startDate >= endDate) {
        errors.end_date = 'End date must be after start date';
      }

      // Check for reasonable date range (max 1 year)
      const daysDiff = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
      if (daysDiff > 365) {
        errors.end_date = 'Date range cannot exceed 365 days';
      }

      // Check for future dates
      const now = new Date();
      if (endDate > now) {
        errors.end_date = 'End date cannot be in the future';
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  }
}

// Create singleton instance
export const backtestApi = new BacktestApiService();
export default backtestApi;
