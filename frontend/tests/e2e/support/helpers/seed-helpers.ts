/**
 * Seed Helpers
 * =============
 *
 * API-first test data seeding utilities.
 * Use these to create test data via API before running UI tests.
 *
 * @example
 * test('user can select strategy', async ({ apiClient, cleanup, page }) => {
 *   // Seed strategy via API (fast!)
 *   const strategy = await seedStrategy(apiClient, cleanup, { name: 'My Strategy' });
 *
 *   // Now test UI
 *   await page.goto('/strategy-builder');
 *   await expect(page.getByText(strategy.name)).toBeVisible();
 * });
 *
 * @see TEA Knowledge Base: data-factories.md
 */

import type { ApiClient } from '../fixtures/api.fixture';
import type { CleanupManager } from '../fixtures/cleanup.fixture';
import {
  createStrategy,
  createIndicator,
  createIndicatorVariant,
  createTradingSession,
  createSessionConfig,
  type Strategy,
  type Indicator,
  type IndicatorVariant,
  type TradingSession,
  type TradingSessionConfig,
} from '../factories';

// ============================================
// STRATEGY SEEDING
// ============================================

/**
 * Seed a strategy via API
 */
export async function seedStrategy(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  overrides: Partial<Strategy> = {}
): Promise<Strategy> {
  const strategy = createStrategy(overrides);

  try {
    const response = await apiClient.post<Strategy>('/api/strategies', strategy);
    cleanup.track('strategies', response.id || strategy.id);
    return response;
  } catch (error) {
    // If API doesn't return the created object, return our factory object
    cleanup.track('strategies', strategy.id);
    return strategy;
  }
}

/**
 * Seed multiple strategies at once
 */
export async function seedStrategies(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  count: number,
  overrides: Partial<Strategy> = {}
): Promise<Strategy[]> {
  const strategies: Strategy[] = [];

  for (let i = 0; i < count; i++) {
    const strategy = await seedStrategy(apiClient, cleanup, {
      name: `Strategy_${i + 1}`,
      ...overrides,
    });
    strategies.push(strategy);
  }

  return strategies;
}

// ============================================
// INDICATOR SEEDING
// ============================================

/**
 * Seed an indicator via API
 */
export async function seedIndicator(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  overrides: Partial<Indicator> = {}
): Promise<Indicator> {
  const indicator = createIndicator(overrides);

  try {
    const response = await apiClient.post<Indicator>('/api/indicators', indicator);
    cleanup.track('indicators', response.id || indicator.id);
    return response;
  } catch (error) {
    cleanup.track('indicators', indicator.id);
    return indicator;
  }
}

/**
 * Seed an indicator variant via API
 */
export async function seedIndicatorVariant(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  indicatorId: string,
  overrides: Partial<IndicatorVariant> = {}
): Promise<IndicatorVariant> {
  const variant = createIndicatorVariant(indicatorId, overrides);

  try {
    const response = await apiClient.post<IndicatorVariant>(`/api/indicators/${indicatorId}/variants`, variant);
    cleanup.track('variants', response.id || variant.id, `/api/indicators/${indicatorId}/variants/${variant.id}`);
    return response;
  } catch (error) {
    cleanup.track('variants', variant.id, `/api/indicators/${indicatorId}/variants/${variant.id}`);
    return variant;
  }
}

// ============================================
// SESSION SEEDING
// ============================================

/**
 * Seed a trading session via API
 */
export async function seedTradingSession(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  overrides: Partial<TradingSession> = {}
): Promise<TradingSession> {
  const session = createTradingSession(overrides);

  try {
    const response = await apiClient.post<TradingSession>('/api/sessions', session);
    cleanup.track('sessions', response.id || session.id);
    return response;
  } catch (error) {
    cleanup.track('sessions', session.id);
    return session;
  }
}

/**
 * Seed session config (without creating session) via API
 */
export async function seedSessionConfig(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  overrides: Partial<TradingSessionConfig> = {}
): Promise<TradingSessionConfig> {
  const config = createSessionConfig(overrides);

  try {
    const response = await apiClient.post<TradingSessionConfig>('/api/sessions/config', config);
    // Config may not have cleanup - it's part of session
    return response;
  } catch (error) {
    return config;
  }
}

// ============================================
// COMPOSITE SEEDING
// ============================================

/**
 * Seed a complete trading setup: strategies + session
 */
export async function seedTradingSetup(
  apiClient: ApiClient,
  cleanup: CleanupManager,
  options: {
    strategyCount?: number;
    symbols?: string[];
    mode?: 'Live' | 'Paper' | 'Backtest';
  } = {}
): Promise<{
  strategies: Strategy[];
  session: TradingSession;
}> {
  const { strategyCount = 1, symbols = ['BTCUSDT'], mode = 'Paper' } = options;

  // Seed strategies first
  const strategies = await seedStrategies(apiClient, cleanup, strategyCount);

  // Seed session with those strategies
  const session = await seedTradingSession(apiClient, cleanup, {
    config: createSessionConfig({
      mode,
      strategies: strategies.map((s) => s.id),
      symbols,
    }),
  });

  return { strategies, session };
}

// ============================================
// DIRECT API HELPERS (no factory, for specific data)
// ============================================

/**
 * Delete a resource directly (bypass cleanup tracking)
 */
export async function deleteResource(
  apiClient: ApiClient,
  resourceType: string,
  resourceId: string
): Promise<void> {
  try {
    await apiClient.delete(`/api/${resourceType}/${resourceId}`);
  } catch (error) {
    console.warn(`Failed to delete ${resourceType}/${resourceId}:`, error);
  }
}

/**
 * Check if API is healthy
 */
export async function checkApiHealth(apiClient: ApiClient): Promise<boolean> {
  try {
    await apiClient.get('/api/health');
    return true;
  } catch {
    return false;
  }
}

/**
 * Get current strategies from API
 */
export async function getStrategies(apiClient: ApiClient): Promise<Strategy[]> {
  try {
    return await apiClient.get<Strategy[]>('/api/strategies');
  } catch {
    return [];
  }
}

/**
 * Get current indicators from API
 */
export async function getIndicators(apiClient: ApiClient): Promise<Indicator[]> {
  try {
    return await apiClient.get<Indicator[]>('/api/indicators');
  } catch {
    return [];
  }
}
