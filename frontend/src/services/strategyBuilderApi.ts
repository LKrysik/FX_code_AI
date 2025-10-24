/**
 * Strategy Builder API Client
 * ===========================
 * Client for interacting with the strategy blueprints API endpoints.
 * Provides methods for CRUD operations on strategy graphs.
 */

import axios, { AxiosResponse } from 'axios';
import { ApiResponse } from '@/types/api';
import { config } from '@/utils/config';
import { recordApiCall } from '@/hooks/usePerformanceMonitor';
import { categorizeError, logUnifiedError, getErrorRecoveryStrategy } from '@/utils/statusUtils';

// Configure axios defaults (reuse from main api service)
axios.defaults.baseURL = config.apiUrl;

export interface StrategyBlueprint {
  id?: string;
  name: string;
  version: string;
  description?: string;
  graph: {
    name: string;
    version: string;
    description?: string;
    nodes: GraphNodeData[];
    edges: GraphEdgeData[];
  };
  tags?: string[];
  is_template?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StrategyBlueprintSummary {
  id: string;
  name: string;
  version: string;
  description?: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  is_template: boolean;
  node_count: number;
  edge_count: number;
}

export interface GraphNodeData {
  id: string;
  node_type: string;
  label: string;
  position: { x: number; y: number };
  [key: string]: any;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface BlueprintListResponse {
  blueprints: StrategyBlueprintSummary[];
  total_count: number;
  skip: number;
  limit: number;
}

export interface BlueprintResponse {
  blueprint: StrategyBlueprint;
}

export interface ValidationResponse {
  blueprint_id: string;
  validation: ValidationResult;
}

export interface MigrationResponse {
  migration: {
    success: boolean;
    blueprint_id?: string;
    errors?: Array<{ type: string; message: string; node_id?: string }>;
    warnings?: Array<{ type: string; message: string; node_id?: string }>;
  };
}

export interface TemplateListResponse {
  templates: Array<{
    id: string;
    name: string;
    description?: string;
    tags: string[];
    node_count: number;
    edge_count: number;
  }>;
}

class StrategyBuilderApiService {
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
      const unifiedError = categorizeError(error, `Strategy Builder API request: ${key}`);
      logUnifiedError(unifiedError);

      // Apply recovery strategy if applicable
      const recoveryStrategy = getErrorRecoveryStrategy(unifiedError);
      if (recoveryStrategy.shouldRetry && this.pendingRequests.has(key)) {
        console.info(`Strategy Builder API Error Recovery: ${recoveryStrategy.fallbackAction}`);
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

  // Blueprint CRUD Operations

  async listBlueprints(params?: {
    skip?: number;
    limit?: number;
    name_filter?: string;
    tag_filter?: string;
  }): Promise<BlueprintListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.name_filter) queryParams.append('name_filter', params.name_filter);
    if (params?.tag_filter) queryParams.append('tag_filter', params.tag_filter);

    const queryString = queryParams.toString();
    const key = `listBlueprints:${queryString}`;

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<BlueprintListResponse>>(
        `/api/strategy-blueprints/?${queryString}`
      );
      if (!response.data?.data) {
        throw new Error('Invalid blueprint list response format');
      }
      return response.data.data;
    });
  }

  async getBlueprint(blueprintId: string): Promise<BlueprintResponse> {
    const key = `getBlueprint:${blueprintId}`;

    return this.dedupedRequest(key, async () => {
      const response = await axios.get<ApiResponse<BlueprintResponse>>(
        `/api/strategy-blueprints/${blueprintId}`
      );
      if (!response.data?.data) {
        throw new Error('Invalid blueprint response format');
      }
      return response.data.data;
    });
  }

  async createBlueprint(blueprint: Omit<StrategyBlueprint, 'id' | 'created_at' | 'updated_at'>): Promise<BlueprintResponse> {
    const response = await axios.post<ApiResponse<BlueprintResponse>>(
      '/api/strategy-blueprints/',
      blueprint
    );
    if (!response.data?.data) {
      throw new Error('Invalid blueprint creation response format');
    }
    return response.data.data;
  }

  async updateBlueprint(blueprintId: string, updates: Partial<StrategyBlueprint>): Promise<BlueprintResponse> {
    const response = await axios.put<ApiResponse<BlueprintResponse>>(
      `/api/strategy-blueprints/${blueprintId}`,
      updates
    );
    if (!response.data?.data) {
      throw new Error('Invalid blueprint update response format');
    }
    return response.data.data;
  }

  async deleteBlueprint(blueprintId: string): Promise<{ message: string }> {
    const response = await axios.delete<ApiResponse<{ message: string }>>(
      `/api/strategy-blueprints/${blueprintId}`
    );
    if (!response.data?.data) {
      throw new Error('Invalid blueprint deletion response format');
    }
    return response.data.data;
  }

  async cloneBlueprint(blueprintId: string, cloneData: {
    name: string;
    description?: string;
    tags?: string[];
  }): Promise<BlueprintResponse> {
    const response = await axios.post<ApiResponse<BlueprintResponse>>(
      `/api/strategy-blueprints/${blueprintId}/clone`,
      cloneData
    );
    if (!response.data?.data) {
      throw new Error('Invalid blueprint clone response format');
    }
    return response.data.data;
  }

  // Validation Operations

  async validateBlueprint(blueprintId: string): Promise<ValidationResponse> {
    const response = await axios.post<ApiResponse<ValidationResponse>>(
      `/api/strategy-blueprints/${blueprintId}/validate`
    );
    if (!response.data?.data) {
      throw new Error('Invalid blueprint validation response format');
    }
    return response.data.data;
  }

  async validateGraph(graph: StrategyBlueprint['graph']): Promise<ValidationResult> {
    const response = await axios.post<ApiResponse<ValidationResponse>>(
      '/api/strategy-blueprints/validate',
      { graph }
    );
    if (!response.data?.data?.validation) {
      throw new Error('Invalid graph validation response format');
    }
    return response.data.data.validation;
  }

  // Migration Operations

  async migrateYAML(yamlConfig: any): Promise<MigrationResponse> {
    const response = await axios.post<ApiResponse<MigrationResponse>>(
      '/api/strategy-blueprints/migrate-yaml',
      yamlConfig
    );
    if (!response.data?.data) {
      throw new Error('Invalid YAML migration response format');
    }
    return response.data.data;
  }

  // Template Operations

  async listTemplates(): Promise<TemplateListResponse> {
    return this.dedupedRequest('listTemplates', async () => {
      const response = await axios.get<ApiResponse<TemplateListResponse>>(
        '/api/strategy-blueprints/templates/list'
      );
      if (!response.data?.data) {
        throw new Error('Invalid template list response format');
      }
      return response.data.data;
    });
  }

  // Utility Methods

  async exportBlueprint(blueprintId: string): Promise<StrategyBlueprint> {
    const response = await this.getBlueprint(blueprintId);
    return response.blueprint;
  }

  async importBlueprint(blueprint: StrategyBlueprint): Promise<BlueprintResponse> {
    const { id, created_at, updated_at, ...blueprintData } = blueprint;
    return this.createBlueprint(blueprintData);
  }

  // Batch Operations

  async batchValidateBlueprints(blueprintIds: string[]): Promise<ValidationResponse[]> {
    const promises = blueprintIds.map(id => this.validateBlueprint(id));
    return Promise.all(promises);
  }

  async batchDeleteBlueprints(blueprintIds: string[]): Promise<{ message: string }[]> {
    const promises = blueprintIds.map(id => this.deleteBlueprint(id));
    return Promise.all(promises);
  }

  // Search and Filter Operations

  async searchBlueprints(query: {
    name_contains?: string;
    tags_include?: string[];
    is_template?: boolean;
    created_by?: string;
    limit?: number;
    skip?: number;
  }): Promise<BlueprintListResponse> {
    const params: any = {};
    if (query.name_contains) params.name_filter = query.name_contains;
    if (query.tags_include?.length) params.tag_filter = query.tags_include[0]; // Simple implementation
    if (query.limit) params.limit = query.limit;
    if (query.skip) params.skip = query.skip;

    return this.listBlueprints(params);
  }

  // Health Check

  async healthCheck(): Promise<any> {
    return this.dedupedRequest('strategyBuilderHealth', async () => {
      try {
        const response = await axios.get('/api/strategy-blueprints/health');
        return response.data;
      } catch (error: any) {
        // Fallback to main health check if specific endpoint doesn't exist
        const response = await axios.get('/health');
        return response.data;
      }
    });
  }
}

// Create singleton instance
const strategyBuilderApiInstance = new StrategyBuilderApiService();

// Export singleton instance
export const strategyBuilderApi = strategyBuilderApiInstance;
export default strategyBuilderApiInstance;

// For test compatibility - create a module-level object that can be patched
const mockableStrategyBuilderApi = {
  listBlueprints: strategyBuilderApiInstance.listBlueprints.bind(strategyBuilderApiInstance),
  getBlueprint: strategyBuilderApiInstance.getBlueprint.bind(strategyBuilderApiInstance),
  createBlueprint: strategyBuilderApiInstance.createBlueprint.bind(strategyBuilderApiInstance),
  updateBlueprint: strategyBuilderApiInstance.updateBlueprint.bind(strategyBuilderApiInstance),
  deleteBlueprint: strategyBuilderApiInstance.deleteBlueprint.bind(strategyBuilderApiInstance),
  cloneBlueprint: strategyBuilderApiInstance.cloneBlueprint.bind(strategyBuilderApiInstance),
  validateBlueprint: strategyBuilderApiInstance.validateBlueprint.bind(strategyBuilderApiInstance),
  validateGraph: strategyBuilderApiInstance.validateGraph.bind(strategyBuilderApiInstance),
  migrateYAML: strategyBuilderApiInstance.migrateYAML.bind(strategyBuilderApiInstance),
  listTemplates: strategyBuilderApiInstance.listTemplates.bind(strategyBuilderApiInstance),
  exportBlueprint: strategyBuilderApiInstance.exportBlueprint.bind(strategyBuilderApiInstance),
  importBlueprint: strategyBuilderApiInstance.importBlueprint.bind(strategyBuilderApiInstance),
  batchValidateBlueprints: strategyBuilderApiInstance.batchValidateBlueprints.bind(strategyBuilderApiInstance),
  batchDeleteBlueprints: strategyBuilderApiInstance.batchDeleteBlueprints.bind(strategyBuilderApiInstance),
  searchBlueprints: strategyBuilderApiInstance.searchBlueprints.bind(strategyBuilderApiInstance),
  healthCheck: strategyBuilderApiInstance.healthCheck.bind(strategyBuilderApiInstance),
};

// Export for test compatibility - this creates a strategyBuilderApi property on the module
(module as any).strategyBuilderApi = mockableStrategyBuilderApi;
