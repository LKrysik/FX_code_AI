/**
 * State Vocabulary Transformation
 * ================================
 * Story 1A-4: Human Vocabulary Labels
 *
 * Centralized mapping from technical state codes to human-readable labels.
 * This is UI-ONLY - API/WebSocket/database contracts remain unchanged (AC2).
 *
 * AC4: Single source of truth for all dashboard components
 */

// ============================================================================
// TYPES
// ============================================================================

export interface StateVocabulary {
  label: string;
  icon: string;
  description: string;
  color: string;
}

/**
 * State Machine States matching backend trading state machine
 */
export type StateMachineState =
  | 'INACTIVE'
  | 'MONITORING'
  | 'S1'
  | 'O1'
  | 'Z1'
  | 'POSITION_ACTIVE'
  | 'ZE1'
  | 'E1'
  // Legacy states for backwards compatibility
  | 'SIGNAL_DETECTED'
  | 'EXITED'
  | 'ERROR';

/**
 * Signal types used in trading
 */
export type SignalType = 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1' | 'pump' | 'dump';

// ============================================================================
// STATE VOCABULARY MAPPING (AC1, AC3)
// ============================================================================

/**
 * Human vocabulary for state machine states
 * From UX Design Specification - Vocabulary Transformation section
 *
 * Colors from UX Spec:
 * - Slate (#64748B): Neutral/watching states
 * - Amber (#F59E0B): Signal detected/entering
 * - Gray (#6B7280): Cancelled/inactive
 * - Blue (#3B82F6): Position active
 * - Green (#10B981): Profit/success
 * - Red (#EF4444): Emergency/error
 */
export const STATE_VOCABULARY: Record<StateMachineState, StateVocabulary> = {
  // Primary trading states
  MONITORING: {
    label: 'Watching',
    icon: '👀',
    description: 'Actively scanning markets for trading signals',
    color: '#64748B', // Slate
  },
  S1: {
    label: 'Found!',
    icon: '🔥',
    description: 'Trading signal detected - evaluating entry conditions',
    color: '#F59E0B', // Amber
  },
  O1: {
    label: 'False Alarm',
    icon: '❌',
    description: 'Signal cancelled - conditions not met',
    color: '#6B7280', // Gray
  },
  Z1: {
    label: 'Entering',
    icon: '🎯',
    description: 'Entry confirmed - opening position',
    color: '#F59E0B', // Amber
  },
  POSITION_ACTIVE: {
    label: 'In Position',
    icon: '📈',
    description: 'Active position open - monitoring exit conditions',
    color: '#3B82F6', // Blue
  },
  ZE1: {
    label: 'Taking Profit',
    icon: '💰',
    description: 'Exit with profit - closing position',
    color: '#10B981', // Green
  },
  E1: {
    label: 'Stopping Loss',
    icon: '🛑',
    description: 'Emergency exit - stopping loss',
    color: '#EF4444', // Red
  },
  // Legacy states for backwards compatibility
  INACTIVE: {
    label: 'Inactive',
    icon: '⏸️',
    description: 'System is not actively monitoring markets',
    color: '#9CA3AF', // Gray
  },
  SIGNAL_DETECTED: {
    label: 'Found!',
    icon: '🔥',
    description: 'Trading signal detected - evaluating entry conditions',
    color: '#F59E0B', // Amber (maps to S1)
  },
  EXITED: {
    label: 'Exited',
    icon: '✓',
    description: 'Position closed successfully',
    color: '#10B981', // Green
  },
  ERROR: {
    label: 'Error',
    icon: '⚠️',
    description: 'System error detected - check logs',
    color: '#EF4444', // Red
  },
};

// ============================================================================
// SIGNAL TYPE VOCABULARY
// ============================================================================

/**
 * Human vocabulary for signal types
 * Maps technical signal codes to human-readable labels
 */
export const SIGNAL_TYPE_VOCABULARY: Record<SignalType, StateVocabulary> = {
  S1: {
    label: 'Entry Signal',
    icon: '🔥',
    description: 'Trading opportunity detected',
    color: '#F59E0B', // Amber
  },
  O1: {
    label: 'Cancelled',
    icon: '❌',
    description: 'Signal invalidated - conditions no longer met',
    color: '#6B7280', // Gray
  },
  Z1: {
    label: 'Position Opened',
    icon: '🎯',
    description: 'Entry executed - position active',
    color: '#3B82F6', // Blue
  },
  ZE1: {
    label: 'Profit Exit',
    icon: '💰',
    description: 'Profit target reached - closing position',
    color: '#10B981', // Green
  },
  E1: {
    label: 'Stop Loss',
    icon: '🛑',
    description: 'Emergency exit triggered',
    color: '#EF4444', // Red
  },
  pump: {
    label: 'Pump Detected',
    icon: '📈',
    description: 'Upward price movement detected',
    color: '#10B981', // Green
  },
  dump: {
    label: 'Dump Detected',
    icon: '📉',
    description: 'Downward price movement detected',
    color: '#EF4444', // Red
  },
};

// ============================================================================
// HELPER FUNCTIONS (AC4 - exported for component use)
// ============================================================================

/**
 * Get human-readable label for a state code
 * @param state - Technical state code (e.g., 'S1', 'MONITORING')
 * @returns Human label (e.g., 'Found!', 'Watching')
 */
export function getHumanLabel(state: string): string {
  return STATE_VOCABULARY[state as StateMachineState]?.label || state;
}

/**
 * Get icon/emoji for a state code
 * @param state - Technical state code
 * @returns Emoji icon
 */
export function getStateIcon(state: string): string {
  return STATE_VOCABULARY[state as StateMachineState]?.icon || '❓';
}

/**
 * Get description for a state code
 * @param state - Technical state code
 * @returns Human-readable description
 */
export function getStateDescription(state: string): string {
  return STATE_VOCABULARY[state as StateMachineState]?.description || 'Unknown state';
}

/**
 * Get color for a state code
 * @param state - Technical state code
 * @returns Hex color code
 */
export function getStateColor(state: string): string {
  return STATE_VOCABULARY[state as StateMachineState]?.color || '#6B7280';
}

/**
 * Get full vocabulary entry for a state
 * @param state - Technical state code
 * @returns Complete StateVocabulary object or default
 */
export function getStateVocabulary(state: string): StateVocabulary {
  return STATE_VOCABULARY[state as StateMachineState] || {
    label: state,
    icon: '❓',
    description: 'Unknown state',
    color: '#6B7280',
  };
}

/**
 * Get human-readable label for a signal type
 * @param signalType - Technical signal type (e.g., 'S1', 'pump')
 * @returns Human label
 */
export function getSignalLabel(signalType: string): string {
  return SIGNAL_TYPE_VOCABULARY[signalType as SignalType]?.label || signalType;
}

/**
 * Get icon for a signal type
 * @param signalType - Technical signal type
 * @returns Emoji icon
 */
export function getSignalIcon(signalType: string): string {
  return SIGNAL_TYPE_VOCABULARY[signalType as SignalType]?.icon || '❓';
}

/**
 * Get color for a signal type
 * @param signalType - Technical signal type
 * @returns Hex color code
 */
export function getSignalColor(signalType: string): string {
  return SIGNAL_TYPE_VOCABULARY[signalType as SignalType]?.color || '#6B7280';
}

/**
 * Get full vocabulary entry for a signal type
 * @param signalType - Technical signal type
 * @returns Complete StateVocabulary object or default
 */
export function getSignalVocabulary(signalType: string): StateVocabulary {
  return SIGNAL_TYPE_VOCABULARY[signalType as SignalType] || {
    label: signalType,
    icon: '❓',
    description: 'Unknown signal type',
    color: '#6B7280',
  };
}
