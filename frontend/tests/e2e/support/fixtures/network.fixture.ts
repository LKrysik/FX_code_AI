/**
 * Network Fixture
 * ================
 *
 * Network interception utilities for mocking API responses.
 * Follows network-first pattern: intercept before navigate.
 *
 * @see TEA Knowledge Base: network-first.md
 */

import { test as base, Page, Route, Request } from '@playwright/test';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface MockedRoute {
  method: HttpMethod;
  urlPattern: string | RegExp;
  response: unknown;
  status?: number;
  headers?: Record<string, string>;
}

export interface CapturedRequest {
  method: string;
  url: string;
  body: unknown;
  headers: Record<string, string>;
  timestamp: number;
}

export interface NetworkManager {
  /**
   * Mock a specific API endpoint with a custom response
   */
  mock: (config: MockedRoute) => Promise<void>;

  /**
   * Mock multiple endpoints at once
   */
  mockMany: (configs: MockedRoute[]) => Promise<void>;

  /**
   * Capture requests matching a pattern for later assertion
   */
  captureRequests: (urlPattern: string | RegExp) => void;

  /**
   * Get all captured requests
   */
  getCapturedRequests: () => CapturedRequest[];

  /**
   * Wait for a specific request to be made
   */
  waitForRequest: (urlPattern: string | RegExp, timeout?: number) => Promise<CapturedRequest>;

  /**
   * Clear all mocks and captured requests
   */
  clear: () => Promise<void>;

  /**
   * Simulate network error for endpoint
   */
  simulateError: (urlPattern: string | RegExp, errorCode?: number) => Promise<void>;

  /**
   * Simulate slow network for endpoint
   */
  simulateDelay: (urlPattern: string | RegExp, delayMs: number) => Promise<void>;
}

export interface NetworkFixtures {
  network: NetworkManager;
}

// ============================================
// NETWORK MANAGER FACTORY
// ============================================

export function createNetworkManager(page: Page): NetworkManager {
  const capturedRequests: CapturedRequest[] = [];
  const activeRoutes: string[] = [];

  const captureRequest = (request: Request): CapturedRequest => ({
    method: request.method(),
    url: request.url(),
    body: request.postDataJSON() || request.postData(),
    headers: request.headers(),
    timestamp: Date.now(),
  });

  return {
    mock: async (config: MockedRoute) => {
      const { method, urlPattern, response, status = 200, headers = {} } = config;

      await page.route(urlPattern, async (route: Route) => {
        if (route.request().method() === method) {
          await route.fulfill({
            status,
            contentType: 'application/json',
            headers,
            body: JSON.stringify(response),
          });
        } else {
          await route.continue();
        }
      });

      activeRoutes.push(urlPattern.toString());
    },

    mockMany: async (configs: MockedRoute[]) => {
      for (const config of configs) {
        await createNetworkManager(page).mock(config);
      }
    },

    captureRequests: (urlPattern: string | RegExp) => {
      page.on('request', (request) => {
        if (typeof urlPattern === 'string' ? request.url().includes(urlPattern) : urlPattern.test(request.url())) {
          capturedRequests.push(captureRequest(request));
        }
      });
    },

    getCapturedRequests: () => [...capturedRequests],

    waitForRequest: async (urlPattern: string | RegExp, timeout = 10000): Promise<CapturedRequest> => {
      const request = await page.waitForRequest(urlPattern, { timeout });
      return captureRequest(request);
    },

    clear: async () => {
      capturedRequests.length = 0;
      // Note: Playwright doesn't have a built-in way to clear routes
      // Routes are cleared when page context is destroyed
    },

    simulateError: async (urlPattern: string | RegExp, errorCode = 500) => {
      await page.route(urlPattern, async (route: Route) => {
        await route.fulfill({
          status: errorCode,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Simulated error', code: errorCode }),
        });
      });
    },

    simulateDelay: async (urlPattern: string | RegExp, delayMs: number) => {
      await page.route(urlPattern, async (route: Route) => {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        await route.continue();
      });
    },
  };
}

// ============================================
// PLAYWRIGHT FIXTURE
// ============================================

export const test = base.extend<NetworkFixtures>({
  network: async ({ page }, use) => {
    const manager = createNetworkManager(page);
    await use(manager);
    await manager.clear();
  },
});

export { expect } from '@playwright/test';
