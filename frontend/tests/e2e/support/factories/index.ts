/**
 * Factory Exports
 * ================
 *
 * Central export point for all test data factories.
 * Import from here to access all factory functions.
 *
 * @example
 * import { createStrategy, createIndicator, createPaperSession } from '../support/factories';
 *
 * @see TEA Knowledge Base: data-factories.md
 */

// Strategy factories
export {
  createCondition,
  createConditionSet,
  createStrategy,
  createRsiStrategy,
  createPumpStrategy,
  createInactiveStrategy,
  createComplexStrategy,
  AVAILABLE_INDICATORS,
  OPERATORS,
  type Strategy,
  type Condition,
  type StrategySection,
} from './strategy.factory';

// Indicator factories
export {
  createIndicator,
  createBuiltInIndicator,
  createIndicatorVariant,
  createDefaultVariant,
  createRsiIndicator,
  createPumpIndicator,
  createNumericParameter,
  createBooleanParameter,
  BUILT_IN_INDICATORS,
  type Indicator,
  type IndicatorVariant,
  type IndicatorParameter,
  type IndicatorCategory,
} from './indicator.factory';

// Trading session factories
export {
  createSessionConfig,
  createTradingSession,
  createPaperSession,
  createLiveSession,
  createBacktestSession,
  createRunningSession,
  createCompletedSession,
  createSessionForMode,
  createMinimalSessionConfig,
  createSymbol,
  createSymbols,
  createSessionStats,
  COMMON_SYMBOLS,
  type TradingSession,
  type TradingSessionConfig,
  type TradingMode,
  type SessionStatus,
  type SessionStats,
} from './trading-session.factory';
