/**
 * Helper Exports
 * ===============
 *
 * Central export point for all test helper utilities.
 *
 * @example
 * import { waitForElementStable, seedStrategy } from '../support/helpers';
 */

// Wait helpers (deterministic waiting)
export {
  waitForElementStable,
  waitForAnimationsComplete,
  waitForNetworkSettled,
  waitForElementAfterAction,
  waitForDialogOpen,
  waitForDialogClose,
  waitForInteractive,
  waitForModeSwitch,
  waitForCheckboxState,
  waitForFormValidation,
  clickAndWaitForResponse,
  gotoAndWaitForApi,
} from '../wait-helpers';

// Seed helpers (API-first data setup)
export {
  seedStrategy,
  seedStrategies,
  seedIndicator,
  seedIndicatorVariant,
  seedTradingSession,
  seedSessionConfig,
  seedTradingSetup,
  deleteResource,
  checkApiHealth,
  getStrategies,
  getIndicators,
} from './seed-helpers';
