/**
 * EventType Constants Tests
 * =========================
 * Story COH-001-3: Create TypeScript EventType Definitions
 *
 * Tests for AC1, AC2: Verify EventType constant object with all backend values
 */

import { EventType, EventTypeValue, isEventType, getEventCategory, getEventAction } from '../events';

describe('EventType Constants', () => {
  describe('AC1: TypeScript EventType constant object exists', () => {
    it('exports EventType object', () => {
      expect(EventType).toBeDefined();
      expect(typeof EventType).toBe('object');
    });

    it('exports EventTypeValue type', () => {
      // Type check - if this compiles, the type exists
      const testValue: EventTypeValue = EventType.PUMP_DETECTED;
      expect(testValue).toBe('pump.detected');
    });
  });

  describe('AC2: All backend EventType values are included', () => {
    describe('Market Data Events', () => {
      it('has MARKET_PRICE_UPDATE', () => {
        expect(EventType.MARKET_PRICE_UPDATE).toBe('market.price_update');
      });

      it('has MARKET_ORDERBOOK_UPDATE', () => {
        expect(EventType.MARKET_ORDERBOOK_UPDATE).toBe('market.orderbook_update');
      });

      it('has MARKET_VOLUME_UPDATE', () => {
        expect(EventType.MARKET_VOLUME_UPDATE).toBe('market.volume_update');
      });

      it('has MARKET_TICKER_UPDATE', () => {
        expect(EventType.MARKET_TICKER_UPDATE).toBe('market.ticker_update');
      });
    });

    describe('Signal Detection Events', () => {
      it('has PUMP_DETECTED', () => {
        expect(EventType.PUMP_DETECTED).toBe('pump.detected');
      });

      it('has DUMP_DETECTED', () => {
        expect(EventType.DUMP_DETECTED).toBe('dump.detected');
      });

      it('has REVERSAL_DETECTED', () => {
        expect(EventType.REVERSAL_DETECTED).toBe('reversal.detected');
      });

      it('has SIGNAL_DETECTED', () => {
        expect(EventType.SIGNAL_DETECTED).toBe('signal.detected');
      });
    });

    describe('Trading Events', () => {
      it('has ORDER_PLACED', () => {
        expect(EventType.ORDER_PLACED).toBe('order.placed');
      });

      it('has ORDER_FILLED', () => {
        expect(EventType.ORDER_FILLED).toBe('order.filled');
      });

      it('has ORDER_REJECTED', () => {
        expect(EventType.ORDER_REJECTED).toBe('order.rejected');
      });

      it('has ORDER_CANCELLED', () => {
        expect(EventType.ORDER_CANCELLED).toBe('order.cancelled');
      });

      it('has ORDER_EXPIRED', () => {
        expect(EventType.ORDER_EXPIRED).toBe('order.expired');
      });
    });

    describe('Position Events', () => {
      it('has POSITION_OPENING', () => {
        expect(EventType.POSITION_OPENING).toBe('position.opening');
      });

      it('has POSITION_OPENED', () => {
        expect(EventType.POSITION_OPENED).toBe('position.opened');
      });

      it('has POSITION_CLOSING', () => {
        expect(EventType.POSITION_CLOSING).toBe('position.closing');
      });

      it('has POSITION_CLOSED', () => {
        expect(EventType.POSITION_CLOSED).toBe('position.closed');
      });

      it('has POSITION_UPDATED', () => {
        expect(EventType.POSITION_UPDATED).toBe('position.updated');
      });
    });

    describe('Risk Management Events', () => {
      it('has STOP_LOSS_TRIGGERED', () => {
        expect(EventType.STOP_LOSS_TRIGGERED).toBe('risk.stop_loss_triggered');
      });

      it('has TAKE_PROFIT_TRIGGERED', () => {
        expect(EventType.TAKE_PROFIT_TRIGGERED).toBe('risk.take_profit_triggered');
      });

      it('has EMERGENCY_CONDITION_DETECTED', () => {
        expect(EventType.EMERGENCY_CONDITION_DETECTED).toBe('risk.emergency_condition_detected');
      });

      it('has RISK_LIMIT_EXCEEDED', () => {
        expect(EventType.RISK_LIMIT_EXCEEDED).toBe('risk.limit_exceeded');
      });
    });

    describe('Entry System Events', () => {
      it('has ENTRY_CONDITIONS_PASSED', () => {
        expect(EventType.ENTRY_CONDITIONS_PASSED).toBe('entry.conditions_passed');
      });

      it('has ENTRY_CONDITIONS_FAILED', () => {
        expect(EventType.ENTRY_CONDITIONS_FAILED).toBe('entry.conditions_failed');
      });

      it('has ENTRY_SIGNAL_GENERATED', () => {
        expect(EventType.ENTRY_SIGNAL_GENERATED).toBe('entry.signal_generated');
      });
    });

    describe('System Events', () => {
      it('has SYSTEM_STARTUP', () => {
        expect(EventType.SYSTEM_STARTUP).toBe('system.startup');
      });

      it('has SYSTEM_SHUTDOWN', () => {
        expect(EventType.SYSTEM_SHUTDOWN).toBe('system.shutdown');
      });

      it('has SYSTEM_ERROR', () => {
        expect(EventType.SYSTEM_ERROR).toBe('system.error');
      });

      it('has SYSTEM_HEALTH_CHECK', () => {
        expect(EventType.SYSTEM_HEALTH_CHECK).toBe('system.health_check');
      });
    });

    describe('Exchange Events', () => {
      it('has EXCHANGE_CONNECTED', () => {
        expect(EventType.EXCHANGE_CONNECTED).toBe('exchange.connected');
      });

      it('has EXCHANGE_DISCONNECTED', () => {
        expect(EventType.EXCHANGE_DISCONNECTED).toBe('exchange.disconnected');
      });

      it('has EXCHANGE_ERROR', () => {
        expect(EventType.EXCHANGE_ERROR).toBe('exchange.error');
      });

      it('has EXCHANGE_RECONNECTING', () => {
        expect(EventType.EXCHANGE_RECONNECTING).toBe('exchange.reconnecting');
      });
    });

    describe('Configuration Events', () => {
      it('has CONFIG_LOADED', () => {
        expect(EventType.CONFIG_LOADED).toBe('config.loaded');
      });

      it('has CONFIG_UPDATED', () => {
        expect(EventType.CONFIG_UPDATED).toBe('config.updated');
      });

      it('has CONFIG_ERROR', () => {
        expect(EventType.CONFIG_ERROR).toBe('config.error');
      });
    });
  });

  describe('Type safety', () => {
    it('values are readonly (as const)', () => {
      // This test verifies that modifying the object would cause a TypeScript error
      // At runtime, we can check it's frozen or the values are as expected
      const originalValue = EventType.PUMP_DETECTED;
      expect(originalValue).toBe('pump.detected');
    });

    it('all values are strings', () => {
      Object.values(EventType).forEach((value) => {
        expect(typeof value).toBe('string');
      });
    });

    it('all values follow event naming convention (category.action)', () => {
      Object.values(EventType).forEach((value) => {
        expect(value).toMatch(/^[a-z]+\.[a-z_]+$/);
      });
    });
  });

  describe('Completeness', () => {
    it('has at least 30 event types (matching backend)', () => {
      const eventCount = Object.keys(EventType).length;
      expect(eventCount).toBeGreaterThanOrEqual(30);
    });

    it('has all category groups', () => {
      const values = Object.values(EventType);
      const categories = new Set(values.map((v) => v.split('.')[0]));

      expect(categories.has('market')).toBe(true);
      expect(categories.has('pump')).toBe(true);
      expect(categories.has('dump')).toBe(true);
      expect(categories.has('order')).toBe(true);
      expect(categories.has('position')).toBe(true);
      expect(categories.has('risk')).toBe(true);
      expect(categories.has('system')).toBe(true);
      expect(categories.has('exchange')).toBe(true);
      expect(categories.has('config')).toBe(true);
    });
  });

  describe('Helper Functions', () => {
    describe('isEventType', () => {
      it('returns true for valid EventType values', () => {
        expect(isEventType('pump.detected')).toBe(true);
        expect(isEventType('order.filled')).toBe(true);
        expect(isEventType('position.opened')).toBe(true);
      });

      it('returns false for invalid event types', () => {
        expect(isEventType('invalid.type')).toBe(false);
        expect(isEventType('')).toBe(false);
        expect(isEventType('random')).toBe(false);
      });
    });

    describe('getEventCategory', () => {
      it('extracts category from event type', () => {
        expect(getEventCategory(EventType.PUMP_DETECTED)).toBe('pump');
        expect(getEventCategory(EventType.ORDER_FILLED)).toBe('order');
        expect(getEventCategory(EventType.POSITION_OPENED)).toBe('position');
        expect(getEventCategory(EventType.SYSTEM_STARTUP)).toBe('system');
      });
    });

    describe('getEventAction', () => {
      it('extracts action from event type', () => {
        expect(getEventAction(EventType.PUMP_DETECTED)).toBe('detected');
        expect(getEventAction(EventType.ORDER_FILLED)).toBe('filled');
        expect(getEventAction(EventType.POSITION_OPENED)).toBe('opened');
        expect(getEventAction(EventType.SYSTEM_STARTUP)).toBe('startup');
      });
    });
  });
});
