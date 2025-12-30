/**
 * Quick Start Template Strategy
 * =============================
 * Story 1A-8: Quick Start Option (AC2, AC3, AC5)
 *
 * Pre-configured pump detection strategy with sensible defaults.
 * Designed for new traders to immediately see signals without configuration.
 *
 * Non-destructive: This template is loaded into session memory only,
 * not saved to user's strategy list unless explicitly requested.
 */

export interface QuickStartStrategyCondition {
  indicator: string;
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  value: number;
}

export interface QuickStartStrategySection {
  name: string;
  conditions: QuickStartStrategyCondition[];
}

export interface QuickStartStrategy {
  strategy_name: string;
  version: string;
  is_template: boolean;
  description: string;
  sections: {
    S1: QuickStartStrategySection;
    O1: QuickStartStrategySection;
    Z1: QuickStartStrategySection;
    ZE1: QuickStartStrategySection;
    E1: QuickStartStrategySection;
  };
}

/**
 * Default Quick Start Strategy Configuration
 * Pump Detection with sensible defaults per AC3:
 * - S1: pump_magnitude > 7%, volume_surge > 3x
 * - O1: pump_magnitude < 3% (false alarm)
 * - Z1: spread < 0.5% (entry confirmation)
 * - ZE1: unrealized_pnl > 5% (take profit)
 * - E1: unrealized_pnl < -3% (stop loss)
 */
export const QUICK_START_STRATEGY: QuickStartStrategy = {
  strategy_name: 'Quick Start - Pump Detection',
  version: '1.0',
  is_template: true,
  description: 'Demo strategy for detecting pump signals. Uses sensible defaults for immediate testing.',
  sections: {
    S1: {
      name: 'Signal Detection',
      conditions: [
        { indicator: 'pump_magnitude_pct', operator: '>', value: 7 },
        { indicator: 'volume_surge_ratio', operator: '>', value: 3 },
      ],
    },
    O1: {
      name: 'Cancellation',
      conditions: [
        { indicator: 'pump_magnitude_pct', operator: '<', value: 3 },
      ],
    },
    Z1: {
      name: 'Entry Confirmation',
      conditions: [
        { indicator: 'spread_pct', operator: '<', value: 0.5 },
      ],
    },
    ZE1: {
      name: 'Exit with Profit',
      conditions: [
        { indicator: 'unrealized_pnl_pct', operator: '>', value: 5 },
      ],
    },
    E1: {
      name: 'Emergency Exit',
      conditions: [
        { indicator: 'unrealized_pnl_pct', operator: '<', value: -3 },
      ],
    },
  },
};

/**
 * Get the Quick Start strategy configuration
 * Returns a fresh copy to prevent mutations
 */
export function getQuickStartStrategy(): QuickStartStrategy {
  return JSON.parse(JSON.stringify(QUICK_START_STRATEGY));
}

/**
 * Check if a strategy is the Quick Start template
 */
export function isQuickStartStrategy(strategyName: string): boolean {
  return strategyName === QUICK_START_STRATEGY.strategy_name;
}

export default QUICK_START_STRATEGY;
