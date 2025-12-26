/**
 * Indicator Factory
 * ==================
 *
 * Faker-based factory for generating test indicators and variants.
 *
 * @see TEA Knowledge Base: data-factories.md
 */

import { faker } from '@faker-js/faker';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type IndicatorCategory = 'momentum' | 'volume' | 'trend' | 'volatility' | 'custom';

export type IndicatorParameter = {
  name: string;
  type: 'number' | 'boolean' | 'string';
  value: number | boolean | string;
  min?: number;
  max?: number;
  description?: string;
};

export type Indicator = {
  id: string;
  name: string;
  displayName: string;
  category: IndicatorCategory;
  description: string;
  parameters: IndicatorParameter[];
  isBuiltIn: boolean;
  createdAt: string;
};

export type IndicatorVariant = {
  id: string;
  indicatorId: string;
  name: string;
  parameters: Record<string, number | boolean | string>;
  isDefault: boolean;
  createdAt: string;
};

// ============================================
// BUILT-IN INDICATORS (from project domain)
// ============================================

export const BUILT_IN_INDICATORS = [
  { name: 'pump_magnitude_pct', displayName: 'Pump Magnitude %', category: 'momentum' as const },
  { name: 'price_velocity', displayName: 'Price Velocity', category: 'momentum' as const },
  { name: 'volume_surge_ratio', displayName: 'Volume Surge Ratio', category: 'volume' as const },
  { name: 'bid_ask_imbalance', displayName: 'Bid-Ask Imbalance', category: 'volume' as const },
  { name: 'liquidity_drain_index', displayName: 'Liquidity Drain Index', category: 'volume' as const },
  { name: 'momentum_reversal_index', displayName: 'Momentum Reversal Index', category: 'momentum' as const },
  { name: 'dump_exhaustion_score', displayName: 'Dump Exhaustion Score', category: 'momentum' as const },
  { name: 'rsi', displayName: 'RSI', category: 'momentum' as const },
  { name: 'twpa', displayName: 'TWPA', category: 'trend' as const },
  { name: 'spread_pct', displayName: 'Spread %', category: 'volatility' as const },
] as const;

// ============================================
// PARAMETER FACTORY
// ============================================

/**
 * Create a numeric parameter with sensible defaults
 */
export const createNumericParameter = (overrides: Partial<IndicatorParameter> = {}): IndicatorParameter => ({
  name: faker.helpers.arrayElement(['period', 'threshold', 'multiplier', 'lookback', 'smoothing']),
  type: 'number',
  value: faker.number.int({ min: 1, max: 100 }),
  min: 1,
  max: 200,
  description: faker.lorem.sentence(),
  ...overrides,
});

/**
 * Create a boolean parameter
 */
export const createBooleanParameter = (overrides: Partial<IndicatorParameter> = {}): IndicatorParameter => ({
  name: faker.helpers.arrayElement(['enabled', 'useEma', 'normalize', 'invert']),
  type: 'boolean',
  value: faker.datatype.boolean(),
  description: faker.lorem.sentence(),
  ...overrides,
});

// ============================================
// INDICATOR FACTORY
// ============================================

/**
 * Create a custom indicator with parameters
 */
export const createIndicator = (overrides: Partial<Indicator> = {}): Indicator => {
  const name = overrides.name || `custom_indicator_${faker.string.alphanumeric(6)}`;

  return {
    id: faker.string.uuid(),
    name,
    displayName: overrides.displayName || faker.helpers.fake('{{word.adjective}} {{word.noun}}'),
    category: faker.helpers.arrayElement(['momentum', 'volume', 'trend', 'volatility', 'custom'] as const),
    description: faker.lorem.sentence(),
    parameters: [
      createNumericParameter({ name: 'period', value: 14 }),
      createNumericParameter({ name: 'threshold', value: 50 }),
    ],
    isBuiltIn: false,
    createdAt: new Date().toISOString(),
    ...overrides,
  };
};

/**
 * Create a built-in indicator (from project's indicator set)
 */
export const createBuiltInIndicator = (
  indicatorName?: (typeof BUILT_IN_INDICATORS)[number]['name']
): Indicator => {
  const template = indicatorName
    ? BUILT_IN_INDICATORS.find((i) => i.name === indicatorName)!
    : faker.helpers.arrayElement(BUILT_IN_INDICATORS);

  return {
    id: faker.string.uuid(),
    name: template.name,
    displayName: template.displayName,
    category: template.category,
    description: `Built-in ${template.displayName} indicator`,
    parameters: [
      createNumericParameter({ name: 'period', value: 14 }),
      createNumericParameter({ name: 'threshold', value: 30 }),
    ],
    isBuiltIn: true,
    createdAt: new Date().toISOString(),
  };
};

// ============================================
// VARIANT FACTORY
// ============================================

/**
 * Create an indicator variant with custom parameters
 */
export const createIndicatorVariant = (
  indicatorId: string,
  overrides: Partial<IndicatorVariant> = {}
): IndicatorVariant => ({
  id: faker.string.uuid(),
  indicatorId,
  name: `Variant_${faker.string.alphanumeric(4)}`,
  parameters: {
    period: faker.number.int({ min: 5, max: 50 }),
    threshold: faker.number.int({ min: 10, max: 90 }),
  },
  isDefault: false,
  createdAt: new Date().toISOString(),
  ...overrides,
});

/**
 * Create the default variant for an indicator
 */
export const createDefaultVariant = (indicatorId: string): IndicatorVariant =>
  createIndicatorVariant(indicatorId, {
    name: 'Default',
    isDefault: true,
    parameters: { period: 14, threshold: 30 },
  });

// ============================================
// SPECIALIZED FACTORIES
// ============================================

/**
 * Create an RSI indicator with standard parameters
 */
export const createRsiIndicator = (overrides: Partial<Indicator> = {}): Indicator =>
  createIndicator({
    name: 'rsi',
    displayName: 'RSI',
    category: 'momentum',
    description: 'Relative Strength Index',
    parameters: [
      createNumericParameter({ name: 'period', value: 14, min: 2, max: 100 }),
      createNumericParameter({ name: 'overbought', value: 70, min: 50, max: 100 }),
      createNumericParameter({ name: 'oversold', value: 30, min: 0, max: 50 }),
    ],
    isBuiltIn: true,
    ...overrides,
  });

/**
 * Create a pump detection indicator (project-specific)
 */
export const createPumpIndicator = (overrides: Partial<Indicator> = {}): Indicator =>
  createIndicator({
    name: 'pump_magnitude_pct',
    displayName: 'Pump Magnitude %',
    category: 'momentum',
    description: 'Detects price pump magnitude as percentage',
    parameters: [
      createNumericParameter({ name: 'lookback', value: 60, min: 10, max: 300 }),
      createNumericParameter({ name: 'threshold', value: 5, min: 1, max: 50 }),
    ],
    isBuiltIn: true,
    ...overrides,
  });
