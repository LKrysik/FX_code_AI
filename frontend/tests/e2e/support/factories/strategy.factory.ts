/**
 * Strategy Factory
 * =================
 *
 * Faker-based factory for generating test strategies with conditions.
 * Supports the 5-section condition system (S1→O1→Z1→ZE1→E1).
 *
 * @see TEA Knowledge Base: data-factories.md
 */

import { faker } from '@faker-js/faker';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type StrategySection = 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1';

export type Condition = {
  id: string;
  section: StrategySection;
  indicator: string;
  operator: string;
  value: string;
  logicOperator?: 'AND' | 'OR';
};

export type Strategy = {
  id: string;
  name: string;
  description: string;
  conditions: Condition[];
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
  version: number;
};

// ============================================
// INDICATOR OPTIONS (from project domain)
// ============================================

export const AVAILABLE_INDICATORS = [
  'pump_magnitude_pct',
  'price_velocity',
  'volume_surge_ratio',
  'bid_ask_imbalance',
  'liquidity_drain_index',
  'momentum_reversal_index',
  'dump_exhaustion_score',
  'velocity_cascade',
  'velocity_stabilization_index',
  'support_level_proximity',
  'twpa',
  'twpa_ratio',
  'rsi',
  'spread_pct',
  'unrealized_pnl_pct',
  'price_momentum',
] as const;

export const OPERATORS = ['>', '<', '>=', '<=', '==', '!='] as const;

// ============================================
// CONDITION FACTORY
// ============================================

/**
 * Create a single condition with sensible defaults.
 * Override any field to customize for specific test scenarios.
 */
export const createCondition = (overrides: Partial<Condition> = {}): Condition => ({
  id: faker.string.uuid(),
  section: 'S1',
  indicator: faker.helpers.arrayElement(AVAILABLE_INDICATORS),
  operator: faker.helpers.arrayElement(OPERATORS),
  value: faker.number.float({ min: 0, max: 100, fractionDigits: 2 }).toString(),
  logicOperator: 'AND',
  ...overrides,
});

/**
 * Create a set of conditions for a complete strategy.
 * By default creates entry (S1) and exit (E1) conditions.
 */
export const createConditionSet = (
  overrides: {
    s1?: Partial<Condition>[];
    o1?: Partial<Condition>[];
    z1?: Partial<Condition>[];
    ze1?: Partial<Condition>[];
    e1?: Partial<Condition>[];
  } = {}
): Condition[] => {
  const conditions: Condition[] = [];

  // S1 - Start/Entry conditions (required)
  const s1Conditions = overrides.s1 || [{}];
  s1Conditions.forEach((c) => conditions.push(createCondition({ section: 'S1', ...c })));

  // O1 - Open conditions (optional)
  if (overrides.o1) {
    overrides.o1.forEach((c) => conditions.push(createCondition({ section: 'O1', ...c })));
  }

  // Z1 - Zone conditions (optional)
  if (overrides.z1) {
    overrides.z1.forEach((c) => conditions.push(createCondition({ section: 'Z1', ...c })));
  }

  // ZE1 - Zone Exit conditions (optional)
  if (overrides.ze1) {
    overrides.ze1.forEach((c) => conditions.push(createCondition({ section: 'ZE1', ...c })));
  }

  // E1 - Exit conditions (required)
  const e1Conditions = overrides.e1 || [{}];
  e1Conditions.forEach((c) => conditions.push(createCondition({ section: 'E1', ...c })));

  return conditions;
};

// ============================================
// STRATEGY FACTORY
// ============================================

/**
 * Create a complete strategy with conditions.
 * Override any field to customize for specific test scenarios.
 *
 * @example
 * // Default strategy
 * const strategy = createStrategy();
 *
 * @example
 * // Named strategy
 * const strategy = createStrategy({ name: 'My Test Strategy' });
 *
 * @example
 * // Strategy with specific conditions
 * const strategy = createStrategy({
 *   conditions: [
 *     createCondition({ section: 'S1', indicator: 'rsi', operator: '<', value: '30' }),
 *     createCondition({ section: 'E1', indicator: 'rsi', operator: '>', value: '70' }),
 *   ],
 * });
 */
export const createStrategy = (overrides: Partial<Strategy> = {}): Strategy => {
  const now = new Date().toISOString();

  return {
    id: faker.string.uuid(),
    name: `Strategy_${faker.string.alphanumeric(6)}`,
    description: faker.lorem.sentence(),
    conditions: createConditionSet(),
    createdAt: now,
    updatedAt: now,
    isActive: true,
    version: 1,
    ...overrides,
  };
};

// ============================================
// SPECIALIZED FACTORIES
// ============================================

/**
 * Create a simple RSI-based strategy (common test case)
 */
export const createRsiStrategy = (overrides: Partial<Strategy> = {}): Strategy =>
  createStrategy({
    name: `RSI_Strategy_${faker.string.alphanumeric(4)}`,
    description: 'RSI-based entry and exit strategy',
    conditions: [
      createCondition({ section: 'S1', indicator: 'rsi', operator: '<', value: '30' }),
      createCondition({ section: 'E1', indicator: 'rsi', operator: '>', value: '70' }),
    ],
    ...overrides,
  });

/**
 * Create a pump detection strategy (project-specific)
 */
export const createPumpStrategy = (overrides: Partial<Strategy> = {}): Strategy =>
  createStrategy({
    name: `Pump_Strategy_${faker.string.alphanumeric(4)}`,
    description: 'Pump magnitude detection strategy',
    conditions: [
      createCondition({ section: 'S1', indicator: 'pump_magnitude_pct', operator: '>', value: '5' }),
      createCondition({ section: 'S1', indicator: 'volume_surge_ratio', operator: '>', value: '2' }),
      createCondition({ section: 'E1', indicator: 'dump_exhaustion_score', operator: '>', value: '0.8' }),
    ],
    ...overrides,
  });

/**
 * Create an inactive strategy (for testing filters)
 */
export const createInactiveStrategy = (overrides: Partial<Strategy> = {}): Strategy =>
  createStrategy({
    isActive: false,
    ...overrides,
  });

/**
 * Create a strategy with many conditions (stress testing)
 */
export const createComplexStrategy = (conditionCount = 10): Strategy => {
  const conditions: Condition[] = [];

  // Add multiple S1 conditions
  for (let i = 0; i < Math.floor(conditionCount / 2); i++) {
    conditions.push(createCondition({ section: 'S1' }));
  }

  // Add multiple E1 conditions
  for (let i = 0; i < Math.ceil(conditionCount / 2); i++) {
    conditions.push(createCondition({ section: 'E1' }));
  }

  return createStrategy({
    name: `Complex_Strategy_${faker.string.alphanumeric(4)}`,
    description: `Strategy with ${conditionCount} conditions`,
    conditions,
  });
};
