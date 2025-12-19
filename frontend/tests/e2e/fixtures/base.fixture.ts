/**
 * Base Fixtures for Playwright Tests
 * ===================================
 *
 * Composable fixtures following the pattern:
 * pure function → fixture → merge
 *
 * Usage:
 *   import { test } from '../fixtures/base.fixture';
 *   test('my test', async ({ page, apiClient }) => { ... });
 */

import { test as base, expect, Page, APIRequestContext } from '@playwright/test';

// ============================================
// TYPE DEFINITIONS
// ============================================

export interface ApiClient {
  get: (endpoint: string) => Promise<any>;
  post: (endpoint: string, data?: any) => Promise<any>;
  put: (endpoint: string, data?: any) => Promise<any>;
  delete: (endpoint: string) => Promise<any>;
}

export interface TestConfig {
  baseURL: string;
  apiURL: string;
  timeout: number;
}

export interface MockedWebSocket {
  messages: any[];
  send: (message: any) => void;
  close: () => void;
  simulateMessage: (message: any) => void;
}

// ============================================
// FIXTURE DEFINITIONS
// ============================================

type TestFixtures = {
  // API client for backend calls
  apiClient: ApiClient;

  // Test configuration
  testConfig: TestConfig;

  // WebSocket mock for real-time testing
  mockedWebSocket: MockedWebSocket;

  // Page with error tracking
  trackedPage: Page;

  // Console errors collector
  consoleErrors: string[];
};

// ============================================
// EXTENDED TEST
// ============================================

export const test = base.extend<TestFixtures>({
  // ----------------------------------------
  // Test Configuration
  // ----------------------------------------
  testConfig: async ({}, use) => {
    const config: TestConfig = {
      baseURL: process.env.TEST_BASE_URL || 'http://localhost:3000',
      apiURL: process.env.TEST_API_URL || 'http://localhost:8080',
      timeout: 30000,
    };
    await use(config);
  },

  // ----------------------------------------
  // API Client
  // ----------------------------------------
  apiClient: async ({ request, testConfig }, use) => {
    const apiURL = testConfig.apiURL;

    const client: ApiClient = {
      get: async (endpoint: string) => {
        const response = await request.get(`${apiURL}${endpoint}`);
        if (!response.ok()) {
          throw new Error(`API GET ${endpoint} failed: ${response.status()}`);
        }
        return response.json();
      },

      post: async (endpoint: string, data?: any) => {
        const response = await request.post(`${apiURL}${endpoint}`, { data });
        if (!response.ok()) {
          throw new Error(`API POST ${endpoint} failed: ${response.status()}`);
        }
        return response.json();
      },

      put: async (endpoint: string, data?: any) => {
        const response = await request.put(`${apiURL}${endpoint}`, { data });
        if (!response.ok()) {
          throw new Error(`API PUT ${endpoint} failed: ${response.status()}`);
        }
        return response.json();
      },

      delete: async (endpoint: string) => {
        const response = await request.delete(`${apiURL}${endpoint}`);
        if (!response.ok()) {
          throw new Error(`API DELETE ${endpoint} failed: ${response.status()}`);
        }
        return response.json();
      },
    };

    await use(client);
  },

  // ----------------------------------------
  // Console Errors Collector
  // ----------------------------------------
  consoleErrors: async ({ page }, use) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      errors.push(`PageError: ${err.message}`);
    });

    await use(errors);
  },

  // ----------------------------------------
  // Page with Error Tracking
  // ----------------------------------------
  trackedPage: async ({ page, consoleErrors }, use) => {
    await use(page);

    // After test: report critical errors
    const criticalErrors = consoleErrors.filter(
      (e) =>
        e.includes('TypeError') ||
        e.includes('ReferenceError') ||
        e.includes('Cannot read') ||
        e.includes('is not a function')
    );

    if (criticalErrors.length > 0) {
      console.warn(`\n⚠️ Critical JS errors detected (${criticalErrors.length}):`);
      criticalErrors.slice(0, 5).forEach((e) => console.warn(`  - ${e.substring(0, 200)}`));
    }
  },

  // ----------------------------------------
  // WebSocket Mock
  // ----------------------------------------
  mockedWebSocket: async ({ page }, use) => {
    const messages: any[] = [];
    let messageHandler: ((msg: any) => void) | null = null;

    // Inject WebSocket mock into page
    await page.addInitScript(() => {
      (window as any).__mockWebSocket = {
        messages: [] as any[],
        handlers: [] as ((msg: any) => void)[],
      };

      const OriginalWebSocket = window.WebSocket;

      (window as any).WebSocket = class MockWebSocket {
        url: string;
        readyState = 1; // OPEN

        constructor(url: string) {
          this.url = url;
          setTimeout(() => {
            if (this.onopen) this.onopen({} as Event);
          }, 100);
        }

        send(data: string) {
          (window as any).__mockWebSocket.messages.push(JSON.parse(data));
        }

        close() {
          this.readyState = 3; // CLOSED
          if (this.onclose) this.onclose({} as CloseEvent);
        }

        onopen: ((ev: Event) => void) | null = null;
        onclose: ((ev: CloseEvent) => void) | null = null;
        onmessage: ((ev: MessageEvent) => void) | null = null;
        onerror: ((ev: Event) => void) | null = null;
      };
    });

    const mock: MockedWebSocket = {
      messages,
      send: (message: any) => {
        messages.push(message);
      },
      close: () => {},
      simulateMessage: async (message: any) => {
        await page.evaluate((msg) => {
          const wsInstances = (window as any).__wsInstances || [];
          wsInstances.forEach((ws: any) => {
            if (ws.onmessage) {
              ws.onmessage({ data: JSON.stringify(msg) } as MessageEvent);
            }
          });
        }, message);
      },
    };

    await use(mock);
  },
});

// Re-export expect for convenience
export { expect };
