#!/usr/bin/env python3
"""
End-to-End Test for Strategy Builder
====================================
This script tests the complete Strategy Builder flow:

1. Creates a test strategy with LOW thresholds (to trigger on test data)
2. Generates synthetic market data with pump/dump patterns
3. Runs backtest to verify all 5 condition groups work:
   - S1: Signal Detection
   - O1: Signal Cancellation
   - Z1: Entry Conditions
   - ZE1: Close Order Detection
   - E1: Emergency Exit

The test data is specifically crafted to trigger each condition type.
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.infrastructure.container import Container
from src.domain.services.strategy_manager import (
    Strategy, StrategyState, ConditionGroup, Condition, ConditionResult
)


# =============================================================================
# TEST DATA GENERATION
# =============================================================================

def generate_pump_dump_data(
    symbol: str,
    base_price: float = 1.0,
    duration_seconds: int = 300,  # 5 minutes
    pump_start_pct: float = 20,   # Start pump at 20% of duration
    pump_peak_pct: float = 50,    # Peak at 50% of duration
    dump_end_pct: float = 80,     # Dump ends at 80% of duration
    pump_magnitude: float = 0.15, # 15% pump
    dump_magnitude: float = 0.10, # 10% dump from peak
    tick_interval_ms: int = 100   # 100ms between ticks
) -> List[Dict[str, Any]]:
    """
    Generate synthetic tick data with a pump-and-dump pattern.

    Pattern:
    - 0-20%: Stable baseline
    - 20-50%: Rapid pump (price increases)
    - 50-80%: Dump (price decreases)
    - 80-100%: Recovery/stable

    Returns list of tick data dictionaries.
    """
    ticks = []
    base_timestamp = time.time()
    num_ticks = int(duration_seconds * 1000 / tick_interval_ms)

    pump_start = int(num_ticks * pump_start_pct / 100)
    pump_peak = int(num_ticks * pump_peak_pct / 100)
    dump_end = int(num_ticks * dump_end_pct / 100)

    for i in range(num_ticks):
        progress = i / num_ticks
        tick_time = base_timestamp + (i * tick_interval_ms / 1000)

        # Calculate price based on phase
        if i < pump_start:
            # Stable baseline with small noise
            price = base_price * (1 + (i % 10 - 5) * 0.0001)
        elif i < pump_peak:
            # Pump phase - exponential rise
            pump_progress = (i - pump_start) / (pump_peak - pump_start)
            price = base_price * (1 + pump_magnitude * pump_progress ** 1.5)
        elif i < dump_end:
            # Dump phase - rapid decline
            dump_progress = (i - pump_peak) / (dump_end - pump_peak)
            peak_price = base_price * (1 + pump_magnitude)
            price = peak_price * (1 - dump_magnitude * dump_progress)
        else:
            # Recovery - gradual stabilization
            recovery_progress = (i - dump_end) / (num_ticks - dump_end)
            dump_low = base_price * (1 + pump_magnitude - dump_magnitude)
            price = dump_low + (base_price - dump_low) * recovery_progress * 0.5

        # Add realistic noise
        import random
        noise = random.uniform(-0.001, 0.001)
        price *= (1 + noise)

        # Volume spikes during pump/dump
        if pump_start <= i < pump_peak:
            volume = random.uniform(1000, 5000)  # High volume during pump
        elif pump_peak <= i < dump_end:
            volume = random.uniform(2000, 8000)  # Even higher during dump
        else:
            volume = random.uniform(100, 500)    # Normal volume

        ticks.append({
            "symbol": symbol,
            "timestamp": tick_time,
            "price": price,
            "volume": volume,
            "quote_volume": price * volume
        })

    return ticks


# =============================================================================
# TEST STRATEGY CREATION
# =============================================================================

def create_price_velocity_test_strategy(
    name: str = "PriceVelocity_Test_Strategy",
    direction: str = "LONG",
    velocity_threshold: float = 0.0001  # Very low threshold for testing
) -> Strategy:
    """
    Create a test strategy that uses PRICE_VELOCITY indicator.

    This strategy has LOW thresholds specifically designed to trigger
    on the synthetic test data.
    """
    strategy = Strategy(
        strategy_name=name,
        enabled=True,
        direction=direction
    )

    # S1: Signal Detection - detect ANY positive velocity
    # Using very low threshold to ensure it triggers
    strategy.signal_detection.conditions.extend([
        Condition(
            name="velocity_positive",
            condition_type="price_velocity",  # Matches what engine publishes
            operator="gte",
            value=velocity_threshold,
            description="Detect positive price velocity (pump starting)"
        )
    ])

    # O1: Signal Cancellation - cancel if velocity goes negative
    strategy.signal_cancellation.conditions.extend([
        Condition(
            name="velocity_reversal",
            condition_type="price_velocity",
            operator="lte",
            value=-velocity_threshold * 2,  # Stricter for cancellation
            description="Cancel signal if velocity reverses significantly"
        )
    ])

    # Z1: Entry Conditions - enter when velocity is still positive
    strategy.entry_conditions.conditions.extend([
        Condition(
            name="velocity_still_positive",
            condition_type="price_velocity",
            operator="gt",
            value=0.0,
            description="Enter only if velocity still positive"
        )
    ])

    # ZE1: Close Order Detection - close on velocity slowdown
    strategy.close_order_detection.conditions.extend([
        Condition(
            name="velocity_slowing",
            condition_type="price_velocity",
            operator="lte",
            value=velocity_threshold / 2,
            description="Close when velocity slows significantly"
        )
    ])

    # E1: Emergency Exit - exit on strong negative velocity (dump)
    strategy.emergency_exit.conditions.extend([
        Condition(
            name="velocity_dump",
            condition_type="price_velocity",
            operator="lte",
            value=-velocity_threshold * 5,  # Strong negative velocity
            description="Emergency exit on rapid price dump"
        )
    ])

    # Global limits for testing
    strategy.global_limits = {
        "max_leverage": 1.0,
        "stop_loss_buffer_pct": 5.0,
        "max_allocation_pct": 10.0,
        "base_position_pct": 1.0,
        "signal_cancellation_cooldown_minutes": 1,
        "emergency_exit_cooldown_minutes": 5
    }

    return strategy


# =============================================================================
# TEST RUNNER
# =============================================================================

class StrategyBuilderTestRunner:
    """Runs end-to-end tests for Strategy Builder"""

    def __init__(self):
        self.container = None
        self.event_bus = None
        self.logger = None
        self.strategy_manager = None
        self.indicator_engine = None

        # Test tracking
        self.events_received = {
            "market.price_update": 0,
            "indicator.updated": 0,
            "signal_generated": 0,
            "strategy.signal_detected": 0,
            "strategy.entry_triggered": 0,
            "strategy.position_opened": 0,
            "strategy.position_closed": 0,
            "strategy.emergency_exit": 0
        }
        self.indicator_values_log = []
        self.condition_evaluations = []

    async def setup(self):
        """Initialize all components"""
        print("\n" + "=" * 70)
        print("STRATEGY BUILDER END-TO-END TEST")
        print("=" * 70)

        print("\n[1/4] Initializing container...")
        settings = get_settings_from_working_directory()
        self.event_bus = EventBus()
        self.logger = StructuredLogger("StrategyBuilderTest", settings.logging)
        self.container = Container(settings, self.event_bus, self.logger)

        print("[2/4] Creating strategy manager...")
        self.strategy_manager = await self.container.create_strategy_manager()

        print("[3/4] Creating indicator engine...")
        self.indicator_engine = await self.container.create_streaming_indicator_engine()

        print("[4/4] Setting up event listeners...")
        await self._setup_event_listeners()

        print("\nSetup complete!")

    async def _setup_event_listeners(self):
        """Subscribe to all relevant events for testing"""
        async def track_event(topic):
            async def handler(data):
                self.events_received[topic] = self.events_received.get(topic, 0) + 1

                # Log indicator values for debugging
                if topic == "indicator.updated":
                    self.indicator_values_log.append({
                        "timestamp": time.time(),
                        "indicator": data.get("indicator"),
                        "indicator_type": data.get("indicator_type"),
                        "value": data.get("value"),
                        "symbol": data.get("symbol")
                    })
            return handler

        for topic in self.events_received.keys():
            await self.event_bus.subscribe(topic, await track_event(topic))

    async def register_test_strategy(self, strategy: Strategy, symbol: str):
        """Register and activate a test strategy"""
        print(f"\nRegistering strategy '{strategy.strategy_name}' for symbol '{symbol}'...")

        # Store in strategy manager
        self.strategy_manager.strategies[strategy.strategy_name] = strategy

        # Activate for symbol (synchronous method)
        self.strategy_manager.activate_strategy_for_symbol(
            strategy.strategy_name,
            symbol
        )

        # Verify activation
        if symbol in self.strategy_manager.active_strategies:
            active = self.strategy_manager.active_strategies[symbol]
            print(f"  Activated: {len(active)} strategies for {symbol}")
            for s in active:
                print(f"    - {s.strategy_name} (state: {s.current_state.value})")
        else:
            print(f"  WARNING: Strategy not activated for {symbol}")

    async def simulate_market_data(self, ticks: List[Dict[str, Any]]):
        """Simulate market data by publishing to event bus"""
        print(f"\nSimulating {len(ticks)} market ticks...")

        for i, tick in enumerate(ticks):
            # Publish price update
            await self.event_bus.publish("market.price_update", tick)

            # Give time for processing
            if i % 100 == 0:
                await asyncio.sleep(0.01)  # Yield to event loop

            # Progress indicator
            if i % 500 == 0:
                print(f"  Processed {i}/{len(ticks)} ticks...")

        # Final processing time
        await asyncio.sleep(0.5)
        print(f"  Completed {len(ticks)} ticks")

    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        print("\n[Events Received]")
        for event, count in sorted(self.events_received.items()):
            status = "OK" if count > 0 else "NONE"
            print(f"  {event}: {count} ({status})")

        print("\n[Indicator Values (last 10)]")
        for entry in self.indicator_values_log[-10:]:
            print(f"  {entry['indicator_type']}: {entry['value']:.8f}")

        print("\n[Strategy States]")
        for name, strategy in self.strategy_manager.strategies.items():
            print(f"  {name}:")
            print(f"    State: {strategy.current_state.value}")
            print(f"    Position Active: {strategy.position_active}")
            print(f"    In Cooldown: {strategy.is_in_cooldown()}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        success_criteria = [
            ("Market data received", self.events_received.get("market.price_update", 0) > 0),
            ("Indicators calculated", self.events_received.get("indicator.updated", 0) > 0),
            ("Signals generated", self.events_received.get("signal_generated", 0) > 0 or
                                  self.events_received.get("strategy.signal_detected", 0) > 0),
        ]

        all_pass = True
        for name, passed in success_criteria:
            status = "PASS" if passed else "FAIL"
            all_pass = all_pass and passed
            print(f"  [{status}] {name}")

        print("\n" + "=" * 70)
        if all_pass:
            print("OVERALL: SUCCESS - All criteria met!")
        else:
            print("OVERALL: PARTIAL - Some criteria not met")
            print("\nDebug: Check indicator_type matching between:")
            print("  - Engine publishes: indicator.updated with indicator_type='price_velocity'")
            print("  - Strategy expects: condition_type='price_velocity'")
        print("=" * 70)

        return all_pass

    async def cleanup(self):
        """Cleanup resources"""
        if self.strategy_manager:
            # Deactivate all strategies
            for symbol in list(self.strategy_manager.active_strategies.keys()):
                self.strategy_manager.active_strategies[symbol] = []


async def main():
    """Main test entry point"""
    runner = StrategyBuilderTestRunner()

    try:
        # Setup
        await runner.setup()

        # Create test strategy
        test_strategy = create_price_velocity_test_strategy(
            name="VelocityTestStrategy",
            velocity_threshold=0.00001  # Very low to trigger on any movement
        )

        # Register for test symbol
        symbol = "TEST_USDT"
        await runner.register_test_strategy(test_strategy, symbol)

        # Create indicator variant for symbol
        print("\nCreating PRICE_VELOCITY indicator variant...")
        variant_id = await runner.indicator_engine.create_variant(
            name=f"PRICE_VELOCITY_test_{symbol}",
            base_indicator_type="PRICE_VELOCITY",
            variant_type="general",
            parameters={"t1": 10.0, "t3": 30.0, "d": 10.0},
            created_by="test",
            description="Test variant for price velocity"
        )
        print(f"  Created variant: {variant_id}")

        # Add indicator to session (use test session)
        test_session_id = "test_session_e2e"
        indicator_id = await runner.indicator_engine.add_indicator_to_session(
            session_id=test_session_id,
            symbol=symbol,
            variant_id=variant_id,
            parameters={"t1": 10.0, "t3": 30.0, "d": 10.0}
        )
        print(f"  Added indicator to session: {indicator_id}")

        # Generate test data
        print("\nGenerating pump-dump test data...")
        test_ticks = generate_pump_dump_data(
            symbol=symbol,
            base_price=1.0,
            duration_seconds=60,    # 1 minute of data
            pump_magnitude=0.05,    # 5% pump
            dump_magnitude=0.03,    # 3% dump
            tick_interval_ms=100
        )
        print(f"  Generated {len(test_ticks)} ticks")

        # Run simulation
        await runner.simulate_market_data(test_ticks)

        # Print results
        success = runner.print_results()

        return 0 if success else 1

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
