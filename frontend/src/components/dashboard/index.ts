/**
 * Dashboard Components Exports
 */

export { default as StateBadge } from './StateBadge';
export type { StateBadgeProps, StateMachineState } from './StateBadge';

export { default as StateOverviewTable } from './StateOverviewTable';
export type { StateOverviewTableProps, StateInstance } from './StateOverviewTable';

export { default as TransitionLog } from './TransitionLog';
export type {
  TransitionLogProps,
  Transition,
  TransitionCondition
} from './TransitionLog';

export { default as ConditionProgress } from './ConditionProgress';
export type { ConditionProgressProps, Condition, ConditionGroup } from './ConditionProgress';

export { default as ConditionProgressIntegration } from './ConditionProgress.integration';

export { default as TransitionLogIntegration } from './TransitionLog.integration';

// Export other dashboard components when created
// export { default as CandlestickChart } from './CandlestickChart';
// export { default as SymbolWatchlist } from './SymbolWatchlist';
// etc.
