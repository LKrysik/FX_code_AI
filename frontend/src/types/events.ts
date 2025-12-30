/**
 * EventType Constants - Centralized Event Type Definitions
 * =========================================================
 * Story COH-001-3: Create TypeScript EventType Definitions
 *
 * Single source of truth for all event type names used across the frontend.
 * Mirrors backend `src/core/events.py` EventType class.
 *
 * Benefits:
 * - IDE autocompletion for event types
 * - Type safety prevents typos
 * - Single reference for available events
 * - Easy to discover what events exist
 *
 * @example
 * ```typescript
 * import { EventType } from '@/types/events';
 *
 * // Before (hardcoded string - error prone)
 * if (message.type === 'pump.detected') { ... }
 *
 * // After (with constant - type safe)
 * if (message.type === EventType.PUMP_DETECTED) { ... }
 * ```
 */

export const EventType = {
  // ============================================================================
  // Market Data Events
  // ============================================================================
  MARKET_PRICE_UPDATE: 'market.price_update',
  MARKET_ORDERBOOK_UPDATE: 'market.orderbook_update',
  MARKET_VOLUME_UPDATE: 'market.volume_update',
  MARKET_TICKER_UPDATE: 'market.ticker_update',

  // ============================================================================
  // Signal Detection Events
  // ============================================================================
  PUMP_DETECTED: 'pump.detected',
  DUMP_DETECTED: 'dump.detected',
  REVERSAL_DETECTED: 'reversal.detected',
  SIGNAL_DETECTED: 'signal.detected',

  // ============================================================================
  // Trading Events
  // ============================================================================
  ORDER_PLACED: 'order.placed',
  ORDER_FILLED: 'order.filled',
  ORDER_REJECTED: 'order.rejected',
  ORDER_CANCELLED: 'order.cancelled',
  ORDER_EXPIRED: 'order.expired',

  // ============================================================================
  // Position Events
  // ============================================================================
  POSITION_OPENING: 'position.opening',
  POSITION_OPENED: 'position.opened',
  POSITION_CLOSING: 'position.closing',
  POSITION_CLOSED: 'position.closed',
  POSITION_UPDATED: 'position.updated',

  // ============================================================================
  // Risk Management Events
  // ============================================================================
  STOP_LOSS_TRIGGERED: 'risk.stop_loss_triggered',
  TAKE_PROFIT_TRIGGERED: 'risk.take_profit_triggered',
  EMERGENCY_CONDITION_DETECTED: 'risk.emergency_condition_detected',
  RISK_LIMIT_EXCEEDED: 'risk.limit_exceeded',

  // ============================================================================
  // Entry System Events
  // ============================================================================
  ENTRY_CONDITIONS_PASSED: 'entry.conditions_passed',
  ENTRY_CONDITIONS_FAILED: 'entry.conditions_failed',
  ENTRY_SIGNAL_GENERATED: 'entry.signal_generated',

  // ============================================================================
  // System Events
  // ============================================================================
  SYSTEM_STARTUP: 'system.startup',
  SYSTEM_SHUTDOWN: 'system.shutdown',
  SYSTEM_ERROR: 'system.error',
  SYSTEM_HEALTH_CHECK: 'system.health_check',

  // ============================================================================
  // Exchange Events
  // ============================================================================
  EXCHANGE_CONNECTED: 'exchange.connected',
  EXCHANGE_DISCONNECTED: 'exchange.disconnected',
  EXCHANGE_ERROR: 'exchange.error',
  EXCHANGE_RECONNECTING: 'exchange.reconnecting',

  // ============================================================================
  // Configuration Events
  // ============================================================================
  CONFIG_LOADED: 'config.loaded',
  CONFIG_UPDATED: 'config.updated',
  CONFIG_ERROR: 'config.error',
} as const;

/**
 * Type representing any valid EventType value.
 * Use this for type-safe event handling.
 *
 * @example
 * ```typescript
 * function handleEvent(type: EventTypeValue, data: unknown) {
 *   switch (type) {
 *     case EventType.PUMP_DETECTED:
 *       // Handle pump detection
 *       break;
 *     case EventType.ORDER_FILLED:
 *       // Handle order fill
 *       break;
 *   }
 * }
 * ```
 */
export type EventTypeValue = (typeof EventType)[keyof typeof EventType];

/**
 * Type guard to check if a string is a valid EventType value.
 *
 * @param value - String to check
 * @returns true if value is a valid EventType
 *
 * @example
 * ```typescript
 * if (isEventType(message.type)) {
 *   // message.type is now typed as EventTypeValue
 * }
 * ```
 */
export function isEventType(value: string): value is EventTypeValue {
  return Object.values(EventType).includes(value as EventTypeValue);
}

/**
 * Get the category from an event type string.
 *
 * @param eventType - Event type string (e.g., 'pump.detected')
 * @returns Category string (e.g., 'pump')
 */
export function getEventCategory(eventType: EventTypeValue): string {
  return eventType.split('.')[0];
}

/**
 * Get the action from an event type string.
 *
 * @param eventType - Event type string (e.g., 'pump.detected')
 * @returns Action string (e.g., 'detected')
 */
export function getEventAction(eventType: EventTypeValue): string {
  return eventType.split('.')[1];
}

export default EventType;
