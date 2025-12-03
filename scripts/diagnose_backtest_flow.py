"""
Diagnose Backtest -> Signal Generation Flow
============================================
This script tests the complete flow from backtest data to signal generation
to identify where the chain breaks.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime

def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def print_result(test_name: str, passed: bool, details: str = ""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"       -> {details}")


async def test_flow():
    """Test the complete backtest -> signal flow"""

    print_header("DIAGNOSTIC: Backtest Signal Generation Flow")

    # Step 1: Check if we can import required modules
    print_header("Step 1: Import Test")
    try:
        from src.domain.services.strategy_manager import StrategyManager, Strategy, Condition, ConditionGroup
        from src.domain.services.streaming_indicator_engine.core.types import IndicatorType
        from src.core.event_bus import EventBus
        print_result("Import StrategyManager", True)
    except Exception as e:
        print_result("Import StrategyManager", False, str(e))
        return

    # Step 2: Create mock EventBus
    print_header("Step 2: Initialize Components")
    try:
        event_bus = EventBus()
        # EventBus doesn't need start() - it's ready immediately
        print_result("EventBus created", True)
    except Exception as e:
        print_result("EventBus created", False, str(e))
        return

    # Step 3: Create StrategyManager
    try:
        from unittest.mock import MagicMock, AsyncMock

        # Create mock dependencies
        mock_logger = MagicMock()
        mock_risk_manager = MagicMock()
        mock_risk_manager.can_open_position_sync = MagicMock(return_value=MagicMock(can_proceed=True))
        mock_risk_manager.use_budget = MagicMock(return_value=True)

        strategy_manager = StrategyManager(
            event_bus=event_bus,
            logger=mock_logger,
            risk_manager=mock_risk_manager
        )
        await strategy_manager.start()
        print_result("StrategyManager started", True)
    except Exception as e:
        print_result("StrategyManager started", False, str(e))
        return

    # Step 4: Create a test strategy with low thresholds
    print_header("Step 3: Create Test Strategy")
    try:
        test_strategy = Strategy(
            strategy_id="test_pump_strategy",
            strategy_name="Test Pump Strategy",
            description="Low threshold strategy for testing",
            direction="LONG",
            enabled=True,
            signal_detection=ConditionGroup(
                name="s1_signal",
                conditions=[
                    Condition(
                        name="vel_high",
                        condition_type="price_velocity",  # lowercase to match indicator
                        operator=">",
                        value=0.00001,  # Very low threshold
                        enabled=True
                    )
                ]
            ),
            signal_cancellation=ConditionGroup(
                name="o1_cancel",
                conditions=[
                    Condition(
                        name="vel_cancel",
                        condition_type="signal_age_seconds",
                        operator=">",
                        value=300,
                        enabled=True
                    )
                ]
            ),
            entry_conditions=ConditionGroup(
                name="z1_entry",
                conditions=[
                    Condition(
                        name="vel_entry",
                        condition_type="price_velocity",
                        operator=">",
                        value=0.000005,  # Very low threshold
                        enabled=True
                    )
                ]
            ),
            close_conditions=ConditionGroup(
                name="ze1_close",
                conditions=[
                    Condition(
                        name="vel_close",
                        condition_type="price_velocity",
                        operator="<",
                        value=-0.00001,
                        enabled=True
                    )
                ]
            ),
            emergency_exit=ConditionGroup(
                name="emergency_exit",
                conditions=[
                    Condition(
                        name="vel_emergency",
                        condition_type="price_velocity",
                        operator="<",
                        value=-0.001,
                        enabled=True
                    )
                ]
            )
        )

        # Add strategy to manager
        strategy_manager.strategies["test_pump_strategy"] = test_strategy
        print_result("Test strategy created", True, f"ID: {test_strategy.strategy_id}")
    except Exception as e:
        print_result("Test strategy created", False, str(e))
        import traceback
        traceback.print_exc()
        return

    # Step 5: Activate strategy for symbol
    print_header("Step 4: Activate Strategy for Symbol")
    try:
        symbol = "PUMP_TEST_USDT"
        result = await strategy_manager.activate_strategy_for_symbol("test_pump_strategy", symbol)
        print_result("Strategy activated", result, f"Symbol: {symbol}")

        # Check active strategies
        active = strategy_manager.active_strategies.get(symbol, [])
        print_result("Active strategies count", len(active) > 0, f"Count: {len(active)}")
    except Exception as e:
        print_result("Strategy activated", False, str(e))
        import traceback
        traceback.print_exc()
        return

    # Step 6: Simulate indicator update
    print_header("Step 5: Simulate Indicator Updates")

    # Capture any signals generated
    signals_generated = []
    async def capture_signal(data):
        signals_generated.append(data)
        print(f"  [SIGNAL] {data.get('signal_type', 'unknown')} for {data.get('strategy_name', 'unknown')}")

    await event_bus.subscribe("signal_generated", capture_signal)

    # Simulate a price velocity update that should trigger S1
    test_indicator_values = [
        {"indicator_type": "price_velocity", "value": 0.0005},  # Above threshold
        {"indicator_type": "price_velocity", "value": 0.001},   # Higher
        {"indicator_type": "price_velocity", "value": -0.0005}, # Below (should trigger close)
    ]

    for i, indicator_data in enumerate(test_indicator_values):
        print(f"\n  Simulating update #{i+1}: {indicator_data}")

        # Publish indicator update event
        await event_bus.publish("indicator.updated", {
            "symbol": symbol,
            "indicator": f"PRICE_VELOCITY_test_{i}",
            "indicator_type": indicator_data["indicator_type"],
            "value": indicator_data["value"],
            "timestamp": datetime.now().isoformat()
        })

        # Give time for event processing
        await asyncio.sleep(0.5)

        # Check indicator values cache
        cached_values = strategy_manager.indicator_values.get(symbol, {})
        print(f"  Cached indicator values: {cached_values}")

    # Final results
    print_header("RESULTS")
    print_result("Signals generated", len(signals_generated) > 0, f"Count: {len(signals_generated)}")

    if signals_generated:
        print("\n  Signals:")
        for sig in signals_generated:
            print(f"    - Type: {sig.get('signal_type')}, Strategy: {sig.get('strategy_name')}")
    else:
        print("\n  No signals generated!")
        print("\n  Diagnosis:")
        print(f"  - Active strategies for {symbol}: {len(strategy_manager.active_strategies.get(symbol, []))}")
        print(f"  - Indicator values cached: {strategy_manager.indicator_values.get(symbol, {})}")
        print(f"  - Strategy state: {test_strategy.state}")

        # Try manual evaluation
        print("\n  Manual condition evaluation:")
        indicator_vals = strategy_manager.indicator_values.get(symbol, {})
        if indicator_vals:
            s1_result = test_strategy.evaluate_signal_detection(indicator_vals)
            print(f"  - S1 (Signal Detection) result: {s1_result}")

    # Cleanup
    await strategy_manager.stop()
    # EventBus doesn't have stop() either

    return len(signals_generated) > 0


if __name__ == "__main__":
    result = asyncio.run(test_flow())
    print(f"\n{'='*60}")
    if result:
        print("  OVERALL: Backtest flow is WORKING")
    else:
        print("  OVERALL: Backtest flow is BROKEN - investigate above")
    print('='*60)
