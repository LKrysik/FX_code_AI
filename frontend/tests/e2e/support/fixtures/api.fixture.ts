/**
 * API Fixture
 * ============
 *
 * Typed HTTP client for backend API calls.
 * Provides GET, POST, PUT, DELETE methods with error handling.
 *
 * @see TEA Knowledge Base: fixture-architecture.md
 */

import { test as base, APIRequestContext } from '@playwright/test';

// ============================================
// TYPE DEFINITIONS
// ============================================

export interface ApiClient {
  baseUrl: string;
  get: <T = unknown>(endpoint: string) => Promise<T>;
  post: <T = unknown>(endpoint: string, data?: unknown) => Promise<T>;
  put: <T = unknown>(endpoint: string, data?: unknown) => Promise<T>;
  patch: <T = unknown>(endpoint: string, data?: unknown) => Promise<T>;
  delete: <T = unknown>(endpoint: string) => Promise<T>;
  request: APIRequestContext;
}

export interface ApiFixtures {
  apiClient: ApiClient;
  apiUrl: string;
}

// ============================================
// PURE FUNCTION (testable without Playwright)
// ============================================

export function createApiClient(request: APIRequestContext, baseUrl: string): ApiClient {
  const handleResponse = async <T>(response: Awaited<ReturnType<APIRequestContext['get']>>): Promise<T> => {
    if (!response.ok()) {
      const body = await response.text().catch(() => 'Unknown error');
      throw new Error(`API request failed: ${response.status()} ${response.statusText()} - ${body}`);
    }

    const contentType = response.headers()['content-type'] || '';
    if (contentType.includes('application/json')) {
      return response.json() as Promise<T>;
    }

    return response.text() as unknown as T;
  };

  return {
    baseUrl,
    request,

    get: async <T = unknown>(endpoint: string): Promise<T> => {
      const response = await request.get(`${baseUrl}${endpoint}`);
      return handleResponse<T>(response);
    },

    post: async <T = unknown>(endpoint: string, data?: unknown): Promise<T> => {
      const response = await request.post(`${baseUrl}${endpoint}`, {
        data,
        headers: { 'Content-Type': 'application/json' },
      });
      return handleResponse<T>(response);
    },

    put: async <T = unknown>(endpoint: string, data?: unknown): Promise<T> => {
      const response = await request.put(`${baseUrl}${endpoint}`, {
        data,
        headers: { 'Content-Type': 'application/json' },
      });
      return handleResponse<T>(response);
    },

    patch: async <T = unknown>(endpoint: string, data?: unknown): Promise<T> => {
      const response = await request.patch(`${baseUrl}${endpoint}`, {
        data,
        headers: { 'Content-Type': 'application/json' },
      });
      return handleResponse<T>(response);
    },

    delete: async <T = unknown>(endpoint: string): Promise<T> => {
      const response = await request.delete(`${baseUrl}${endpoint}`);
      return handleResponse<T>(response);
    },
  };
}

// ============================================
// PLAYWRIGHT FIXTURE
// ============================================

export const test = base.extend<ApiFixtures>({
  apiUrl: async ({}, use) => {
    const url = process.env.TEST_API_URL || process.env.API_URL || 'http://localhost:8080';
    await use(url);
  },

  apiClient: async ({ request, apiUrl }, use) => {
    const client = createApiClient(request, apiUrl);
    await use(client);
  },
});

export { expect } from '@playwright/test';
