/**
 * 4-Section Strategies API Client
 * ===============================
 * Client for interacting with the 4-section strategy CRUD endpoints.
 * Provides methods for create, read, update, delete operations on 4-section strategies.
 */

import axios, { AxiosResponse } from 'axios';
import { ApiResponse } from '@/types/api';
import { config } from '@/utils/config';
import { recordApiCall } from '@/hooks/usePerformanceMonitor';
import { categorizeError, logUnifiedError, getErrorRecoveryStrategy } from '@/utils/statusUtils';

// Configure axios defaults (reuse from main api service)
axios.defaults.baseURL = config.apiUrl;

export interface FourSectionStrategy {
  id?: string;
  strategy_name: string;
  description?: string;
  s1_signal: any; // Signal detection section
  z1_entry: any;  // Order entry section
  o1_cancel: any; // Cancellation section
  emergency_exit: any; // Emergency exit section
  created_at?: string;
  updated_at?: string;
  created_by?: string;
}

export interface StrategyListResponse {
  strategies: Array<{
    id: string;
    strategy_name: string;
    created_at?: string;
    updated_at?: string;
    created_by?: string;
  }>;
}

export interface StrategyResponse {
  strategy: FourSectionStrategy;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ValidationResponse {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

class StrategiesApiService {
  private pendingRequests = new Map<string, Promise<any>>();
  private requestTimeouts = new Map<string, NodeJS.Timeout>();

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
      const unifiedError = categorizeError(error, `4-Section Strategies API request: ${key}`);
      logUnifiedError(unifiedError);

      // Apply recovery strategy if applicable
      const recoveryStrategy = getErrorRecoveryStrategy(unifiedError);
      if (recoveryStrategy.shouldRetry && this.pendingRequests.has(key)) {
        console.info(`4-Section Strategies API Error Recovery: ${recoveryStrategy.fallbackAction}`);
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

  // Strategy CRUD Operations

  async listStrategies(): Promise<StrategyListResponse> {
    const key = 'listStrategies';

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<StrategyListResponse>>(
        '/api/strategies'
      );
      if (!response.data?.data) {
        throw new Error('Invalid strategies list response format');
      }
      return response.data.data;
    });
  }

  async getStrategy(strategyId: string): Promise<StrategyResponse> {
    const key = `getStrategy:${strategyId}`;

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<StrategyResponse>>(
        `/api/strategies/${strategyId}`
      );
      if (!response.data?.data) {
        throw new Error('Invalid strategy response format');
      }
      return response.data.data;
    });
  }

  async createStrategy(strategy: Omit<FourSectionStrategy, 'id' | 'created_at' | 'updated_at' | 'created_by'>): Promise<StrategyResponse> {
    const response = await axios.post<ApiResponse<StrategyResponse>>(
      '/api/strategies',
      strategy
    );
    if (!response.data?.data) {
      throw new Error('Invalid strategy creation response format');
    }
    return response.data.data;
  }

  async updateStrategy(strategyId: string, updates: Partial<FourSectionStrategy>): Promise<StrategyResponse> {
    const response = await axios.put<ApiResponse<StrategyResponse>>(
      `/api/strategies/${strategyId}`,
      updates
    );
    if (!response.data?.data) {
      throw new Error('Invalid strategy update response format');
    }
    return response.data.data;
  }

  async deleteStrategy(strategyId: string): Promise<{ message: string; strategy_id: string; strategy_name: string }> {
    const response = await axios.delete<ApiResponse<{ message: string; strategy_id: string; strategy_name: string }>>(
      `/api/strategies/${strategyId}`
    );
    if (!response.data?.data) {
      throw new Error('Invalid strategy deletion response format');
    }
    return response.data.data;
  }

  // Validation Operations

  async validateStrategy(strategy: FourSectionStrategy): Promise<ValidationResult> {
    const response = await axios.post<ApiResponse<ValidationResponse>>(
      '/api/strategies/validate',
      strategy
    );
    if (!response.data?.data) {
      throw new Error('Invalid strategy validation response format');
    }
    const validation = response.data.data;
    return {
      isValid: validation.isValid,
      errors: validation.errors || [],
      warnings: validation.warnings || []
    };
  }

  // Utility Methods

  async exportStrategy(strategyId: string): Promise<FourSectionStrategy> {
    const response = await this.getStrategy(strategyId);
    return response.strategy;
  }

  async importStrategy(strategy: FourSectionStrategy): Promise<StrategyResponse> {
    const { id, created_at, updated_at, created_by, ...strategyData } = strategy;
    return this.createStrategy(strategyData);
  }

  // Batch Operations

  async batchValidateStrategies(strategies: FourSectionStrategy[]): Promise<ValidationResult[]> {
    const promises = strategies.map(strategy => this.validateStrategy(strategy));
    return Promise.all(promises);
  }

  async batchDeleteStrategies(strategyIds: string[]): Promise<{ message: string; strategy_id: string; strategy_name: string }[]> {
    const promises = strategyIds.map(id => this.deleteStrategy(id));
    return Promise.all(promises);
  }

  // Search and Filter Operations

  async searchStrategies(query: {
    name_contains?: string;
    created_by?: string;
    limit?: number;
    skip?: number;
  }): Promise<StrategyListResponse> {
    // For now, fetch all and filter client-side
    // In production, this would be server-side filtering
    const allStrategies = await this.listStrategies();

    let filtered = allStrategies.strategies;

    if (query.name_contains) {
      filtered = filtered.filter(s =>
        s.strategy_name.toLowerCase().includes(query.name_contains!.toLowerCase())
      );
    }

    if (query.created_by) {
      filtered = filtered.filter(s => s.created_by === query.created_by);
    }

    // Apply pagination
    if (query.skip) {
      filtered = filtered.slice(query.skip);
    }
    if (query.limit) {
      filtered = filtered.slice(0, query.limit);
    }

    return { strategies: filtered };
  }

  // Health Check

  async healthCheck(): Promise<any> {
    return this.dedupedRequest('strategiesApiHealth', async () => {
      try {
        const response = await axios.get('/api/strategies');
        return { status: 'healthy', endpoint: 'strategies' };
      } catch (error: any) {
        // Fallback to main health check if specific endpoint fails
        const response = await axios.get('/health');
        return { status: 'degraded', fallback: true };
      }
    });
  }
}

// Create singleton instance
const strategiesApiInstance = new StrategiesApiService();

// Export singleton instance
export const strategiesApi = strategiesApiInstance;
export default strategiesApiInstance;

// For test compatibility - create a module-level object that can be patched
const mockableStrategiesApi = {
  listStrategies: strategiesApiInstance.listStrategies.bind(strategiesApiInstance),
  getStrategy: strategiesApiInstance.getStrategy.bind(strategiesApiInstance),
  createStrategy: strategiesApiInstance.createStrategy.bind(strategiesApiInstance),
  updateStrategy: strategiesApiInstance.updateStrategy.bind(strategiesApiInstance),
  deleteStrategy: strategiesApiInstance.deleteStrategy.bind(strategiesApiInstance),
  validateStrategy: strategiesApiInstance.validateStrategy.bind(strategiesApiInstance),
  exportStrategy: strategiesApiInstance.exportStrategy.bind(strategiesApiInstance),
  importStrategy: strategiesApiInstance.importStrategy.bind(strategiesApiInstance),
  batchValidateStrategies: strategiesApiInstance.batchValidateStrategies.bind(strategiesApiInstance),
  batchDeleteStrategies: strategiesApiInstance.batchDeleteStrategies.bind(strategiesApiInstance),
  searchStrategies: strategiesApiInstance.searchStrategies.bind(strategiesApiInstance),
  healthCheck: strategiesApiInstance.healthCheck.bind(strategiesApiInstance),
};

// Export for test compatibility - this creates a strategiesApi property on the module
(module as any).strategiesApi = mockableStrategiesApi;