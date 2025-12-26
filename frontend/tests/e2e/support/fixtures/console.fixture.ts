/**
 * Console Fixture
 * ================
 *
 * Console error tracking and assertion utilities.
 * Captures JavaScript errors for test assertions.
 *
 * @see TEA Knowledge Base: test-quality.md
 */

import { test as base, Page, ConsoleMessage } from '@playwright/test';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type ConsoleLevel = 'log' | 'info' | 'warn' | 'error' | 'debug';

export interface ConsoleEntry {
  level: ConsoleLevel;
  message: string;
  timestamp: number;
  location?: string;
}

export interface ConsoleManager {
  /**
   * Get all captured console messages
   */
  getAll: () => ConsoleEntry[];

  /**
   * Get only errors (console.error + page errors)
   */
  getErrors: () => ConsoleEntry[];

  /**
   * Get only warnings
   */
  getWarnings: () => ConsoleEntry[];

  /**
   * Check if any critical JS errors occurred
   * Critical: TypeError, ReferenceError, Cannot read, is not a function
   */
  getCriticalErrors: () => ConsoleEntry[];

  /**
   * Check if console has no errors
   */
  hasNoErrors: () => boolean;

  /**
   * Check if console has no critical errors
   */
  hasNoCriticalErrors: () => boolean;

  /**
   * Clear captured messages
   */
  clear: () => void;

  /**
   * Filter messages by pattern
   */
  filter: (pattern: string | RegExp) => ConsoleEntry[];
}

export interface ConsoleFixtures {
  console: ConsoleManager;
  consoleErrors: string[]; // Legacy compatibility
}

// ============================================
// CRITICAL ERROR PATTERNS
// ============================================

const CRITICAL_PATTERNS = [
  /TypeError/i,
  /ReferenceError/i,
  /Cannot read/i,
  /is not a function/i,
  /is not defined/i,
  /Uncaught/i,
  /SyntaxError/i,
  /RangeError/i,
];

// ============================================
// CONSOLE MANAGER FACTORY
// ============================================

export function createConsoleManager(page: Page): ConsoleManager {
  const entries: ConsoleEntry[] = [];

  // Listen for console messages
  page.on('console', (msg: ConsoleMessage) => {
    entries.push({
      level: msg.type() as ConsoleLevel,
      message: msg.text(),
      timestamp: Date.now(),
      location: msg.location()?.url,
    });
  });

  // Listen for page errors (uncaught exceptions)
  page.on('pageerror', (error: Error) => {
    entries.push({
      level: 'error',
      message: `PageError: ${error.message}`,
      timestamp: Date.now(),
    });
  });

  const isCritical = (entry: ConsoleEntry): boolean =>
    CRITICAL_PATTERNS.some((pattern) => pattern.test(entry.message));

  return {
    getAll: () => [...entries],

    getErrors: () => entries.filter((e) => e.level === 'error'),

    getWarnings: () => entries.filter((e) => e.level === 'warn'),

    getCriticalErrors: () => entries.filter((e) => e.level === 'error' && isCritical(e)),

    hasNoErrors: () => entries.filter((e) => e.level === 'error').length === 0,

    hasNoCriticalErrors: () => entries.filter((e) => e.level === 'error' && isCritical(e)).length === 0,

    clear: () => {
      entries.length = 0;
    },

    filter: (pattern: string | RegExp) => {
      if (typeof pattern === 'string') {
        return entries.filter((e) => e.message.includes(pattern));
      }
      return entries.filter((e) => pattern.test(e.message));
    },
  };
}

// ============================================
// PLAYWRIGHT FIXTURE
// ============================================

export const test = base.extend<ConsoleFixtures>({
  console: async ({ page }, use) => {
    const manager = createConsoleManager(page);
    await use(manager);

    // Report critical errors after test (warning, not failure)
    const criticalErrors = manager.getCriticalErrors();
    if (criticalErrors.length > 0) {
      console.warn(`\n⚠️ Critical JS errors detected (${criticalErrors.length}):`);
      criticalErrors.slice(0, 5).forEach((e) => console.warn(`  - ${e.message.substring(0, 200)}`));
    }
  },

  // Legacy compatibility with existing tests
  consoleErrors: async ({ console: consoleManager }, use) => {
    await use(consoleManager.getErrors().map((e) => e.message));
  },
});

export { expect } from '@playwright/test';
