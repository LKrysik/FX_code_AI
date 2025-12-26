/**
 * Merged Fixtures
 * ================
 *
 * Composable fixture system using mergeTests pattern.
 * Import from here to get all test capabilities in one import.
 *
 * @example
 * import { test, expect } from '../support/fixtures';
 *
 * test('my test', async ({ page, apiClient, network, cleanup, console }) => {
 *   // All fixtures available
 * });
 *
 * @see TEA Knowledge Base: fixture-architecture.md
 */

import { mergeTests, expect } from '@playwright/test';
import { test as apiTest, type ApiClient, type ApiFixtures } from './api.fixture';
import { test as cleanupTest, type CleanupManager, type CleanupFixtures } from './cleanup.fixture';
import { test as networkTest, type NetworkManager, type NetworkFixtures } from './network.fixture';
import { test as consoleTest, type ConsoleManager, type ConsoleFixtures } from './console.fixture';

// ============================================
// MERGED TEST EXPORT
// ============================================

/**
 * Merged test with all fixtures available:
 * - apiClient: Typed HTTP client for backend API calls
 * - apiUrl: Base URL for API requests
 * - cleanup: Auto-cleanup tracking for test isolation
 * - network: Network interception and mocking
 * - console: Console error tracking and assertions
 * - consoleErrors: Legacy string array of errors
 */
export const test = mergeTests(apiTest, cleanupTest, networkTest, consoleTest);

// ============================================
// TYPE EXPORTS
// ============================================

export type TestFixtures = ApiFixtures & CleanupFixtures & NetworkFixtures & ConsoleFixtures;

// Re-export expect
export { expect };

// Re-export types for convenience
export type { ApiClient, CleanupManager, NetworkManager, ConsoleManager };

// Re-export individual fixtures for selective use
export { test as apiTest } from './api.fixture';
export { test as cleanupTest } from './cleanup.fixture';
export { test as networkTest } from './network.fixture';
export { test as consoleTest } from './console.fixture';
