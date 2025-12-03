#!/usr/bin/env python3
"""
Test Strategy Builder on Pump/Dump Test Data
=============================================

End-to-end test that:
1. Loads test data from QuestDB
2. Calculates indicators on the data
3. Runs strategy evaluation
4. Verifies signal generation at pump/dump points

This script validates that the complete pipeline works:
tick_prices -> IndicatorEngine -> StrategyManager -> signals

Usage:
    python scripts/test_strategy_on_pump_data.py [session_id]
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_feed.questdb_provider import QuestDBProvider
from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
from src.domain.services.streaming_indicator_engine.core.types import IndicatorType
from src.domain.services.strategy_manager import (
    Strategy, StrategyState, ConditionGroup, Condition, ConditionResult
)


# =============================================================================
# CONFIGURATION
# =============================================================================

TEST_SYMBOL = "PUMP_TEST_USDT"

# Expected pump patterns (from generate_test_pump_data.py)
EXPECTED_PUMPS = [
    {"minute": 10, "magnitude": 15},  # Pattern 1
    {"minute": 25, "magnitude": 8},   # Pattern 2
    {"minute": 40, "magnitude": 20},  # Pattern 3
]


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

async def get_latest_session_id(provider: QuestDBProvider) -> Optional[str]:
    """Get the latest pump_test session ID"""
    await provider.initialize()
    query = """
    SELECT session_id
    FROM data_collection_sessions
    WHERE (is_deleted = false OR is_deleted IS NULL)
    AND session_id LIKE 'pump_test_%'
    ORDER BY created_at DESC
    LIMIT 1
    """
    result = await provider.execute_query(query)
    if result:
        return result[0]['session_id']
    return None


async def load_test_data(provider: QuestDBProvider, session_id: str) -> List[Dict[str, Any]]:
    """Load tick prices from QuestDB"""
    await provider.initialize()
    query = f"""
    SELECT timestamp, price, volume, quote_volume
    FROM tick_prices
    WHERE session_id = '{session_id}'
    ORDER BY timestamp ASC
    """
    return await provider.execute_query(query)


def create_pump_detection_strategy() -> Strategy:
    """Create a strategy optimized for pump detection"""
    strategy = Strategy(
        strategy_name="pump_test_strategy",
        enabled=True,
        direction="LONG",
        global_limits={
            "base_position_pct": 0.3,
            "max_position_size_usdt": 500,
            "stop_loss_buffer_pct": 15.0,
            "target_profit_pct": 20.0,
        }
    )

    # S1: Signal Detection - detect pump
    # Lower thresholds for test data
    strategy.signal_detection.conditions.extend([
        Condition(
            name="price_velocity",
            condition_type="price_velocity",  # Must match indicator_type
            operator="gte",
            value=0.0001,  # Very low threshold for testing
            description="Price velocity threshold"
        ),
    ])

    # Z1: Entry Conditions
    strategy.entry_conditions.conditions.extend([
        Condition(
            name="spread_pct",
            condition_type="spread_pct",
            operator="lte",
            value=1.0,
            description="Maximum spread"
        )
    ])

    return strategy


async def test_indicator_calculation(session_id: str) -> Dict[str, Any]:
    """Test indicator calculation on session data"""
    print("\n" + "=" * 60)
    print("TESTING INDICATOR CALCULATION")
    print("=" * 60)

    engine = OfflineIndicatorEngine()

    # Add PRICE_VELOCITY indicator with session_id
    key = engine.add_indicator(
        symbol=TEST_SYMBOL,
        indicator_type=IndicatorType.PRICE_VELOCITY,
        timeframe="1s",
        period=10,
        session_id=session_id,  # Now supports session_id!
        t1=60.0,
        t2=0.0,
        refresh_interval_seconds=2.0
    )

    print(f"\n[1] Added indicator: {key}")

    # Get indicator info
    info = engine.get_indicator_value(key)
    if info:
        print(f"[2] Data points: {info.get('data_points', 0)}")
        print(f"[3] Current value: {info.get('current_value', 'N/A')}")
        print(f"[4] Valid points: {info.get('valid_points', 0)}")

        if info.get('data_points', 0) > 0:
            print("\n[OK] Indicator calculation SUCCESSFUL")
            return {"success": True, "key": key, "info": info}
        else:
            print("\n[FAIL] No data points loaded")
            return {"success": False, "error": "No data points loaded"}
    else:
        print("\n[FAIL] Could not get indicator info")
        return {"success": False, "error": "Could not get indicator info"}


async def test_strategy_evaluation_flow() -> Dict[str, Any]:
    """Test strategy evaluation logic"""
    print("\n" + "=" * 60)
    print("TESTING STRATEGY EVALUATION FLOW")
    print("=" * 60)

    strategy = create_pump_detection_strategy()
    results = []

    # Test case 1: Signal detection with matching indicator
    print("\n[Test 1] Signal detection with price_velocity = 0.001")
    indicators_match = {"price_velocity": 0.001}
    result1 = strategy.evaluate_signal_detection(indicators_match)
    passed1 = result1 == ConditionResult.TRUE
    print(f"  Result: {result1.value} (expected: true)")
    print(f"  Status: {'PASS' if passed1 else 'FAIL'}")
    results.append(passed1)

    # Test case 2: Signal detection with low value
    print("\n[Test 2] Signal detection with price_velocity = 0.00001 (below threshold)")
    indicators_low = {"price_velocity": 0.00001}
    result2 = strategy.evaluate_signal_detection(indicators_low)
    passed2 = result2 == ConditionResult.FALSE
    print(f"  Result: {result2.value} (expected: false)")
    print(f"  Status: {'PASS' if passed2 else 'FAIL'}")
    results.append(passed2)

    # Test case 3: Missing indicator
    print("\n[Test 3] Signal detection with missing indicator")
    indicators_missing = {"other_indicator": 0.01}
    result3 = strategy.evaluate_signal_detection(indicators_missing)
    passed3 = result3 in [ConditionResult.FALSE, ConditionResult.PENDING]
    print(f"  Result: {result3.value} (expected: false or pending)")
    print(f"  Status: {'PASS' if passed3 else 'FAIL'}")
    results.append(passed3)

    # Test case 4: Entry conditions
    print("\n[Test 4] Entry conditions with spread_pct = 0.5")
    indicators_entry = {"spread_pct": 0.5}
    result4 = strategy.evaluate_entry_conditions(indicators_entry)
    passed4 = result4 == ConditionResult.TRUE
    print(f"  Result: {result4.value} (expected: true)")
    print(f"  Status: {'PASS' if passed4 else 'FAIL'}")
    results.append(passed4)

    # Summary
    total = len(results)
    passed = sum(results)
    print(f"\n[SUMMARY] {passed}/{total} tests passed")

    return {
        "success": all(results),
        "passed": passed,
        "total": total
    }


async def test_full_backtest(session_id: str, provider: QuestDBProvider) -> Dict[str, Any]:
    """Test full backtesting flow with indicators and strategy"""
    print("\n" + "=" * 60)
    print("TESTING FULL BACKTEST FLOW")
    print("=" * 60)

    # Load data
    print("\n[1] Loading test data...")
    data = await load_test_data(provider, session_id)
    print(f"    Loaded {len(data)} ticks")

    if not data:
        return {"success": False, "error": "No test data found"}

    # Calculate price statistics
    prices = [float(d['price']) for d in data]
    print(f"    Price range: {min(prices):.4f} - {max(prices):.4f}")

    # Calculate velocity manually to verify
    print("\n[2] Calculating price velocity manually...")
    velocities = []
    for i in range(30, len(prices)):  # Start after warmup
        window_start = i - 30  # 60 seconds / 2s interval = 30 ticks
        start_price = prices[window_start]
        end_price = prices[i]
        if start_price > 0:
            velocity = (end_price - start_price) / start_price
            velocities.append(velocity)

    if velocities:
        max_velocity = max(velocities)
        min_velocity = min(velocities)
        print(f"    Velocity range: {min_velocity:.6f} - {max_velocity:.6f}")

    # Create strategy
    print("\n[3] Creating pump detection strategy...")
    strategy = create_pump_detection_strategy()
    print(f"    Strategy: {strategy.strategy_name}")
    print(f"    Direction: {strategy.direction}")
    print(f"    Signal detection conditions: {len(strategy.signal_detection.conditions)}")

    # Simulate strategy evaluation
    print("\n[4] Simulating strategy evaluation...")
    signals_detected = 0
    signal_points = []

    for i, velocity in enumerate(velocities):
        indicators = {"price_velocity": velocity}
        result = strategy.evaluate_signal_detection(indicators)
        if result == ConditionResult.TRUE:
            signals_detected += 1
            signal_points.append({
                "index": i + 30,
                "velocity": velocity,
                "price": prices[i + 30]
            })

    print(f"    Total signals detected: {signals_detected}")

    if signal_points:
        print("\n[5] Signal detection points:")
        for i, sp in enumerate(signal_points[:10]):  # Show first 10
            print(f"    Signal {i+1}: index={sp['index']}, velocity={sp['velocity']:.6f}, price={sp['price']:.4f}")

        # Check if signals match expected pump locations
        print("\n[6] Matching signals to expected pumps...")
        for pump in EXPECTED_PUMPS:
            expected_minute = pump['minute']
            expected_index = expected_minute * 30  # 60 seconds / 2s interval = 30 ticks per minute
            matching_signals = [s for s in signal_points if abs(s['index'] - expected_index) < 60]
            if matching_signals:
                print(f"    Pump at minute {expected_minute}: DETECTED ({len(matching_signals)} signals)")
            else:
                print(f"    Pump at minute {expected_minute}: NOT DETECTED")

    return {
        "success": signals_detected > 0,
        "signals_detected": signals_detected,
        "signal_points": signal_points[:10]
    }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main test entry point"""
    print("\n" + "=" * 80)
    print("STRATEGY BUILDER TEST ON PUMP/DUMP DATA")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")

    # Get session ID from args or find latest
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    provider = QuestDBProvider()

    if not session_id:
        print("\n[INIT] Finding latest pump_test session...")
        session_id = await get_latest_session_id(provider)
        if session_id:
            print(f"       Found: {session_id}")
        else:
            print("       No sessions found. Run generate_test_pump_data.py first.")
            return 1

    # Run tests
    results = {}

    # Test 1: Indicator calculation
    try:
        results['indicator'] = await test_indicator_calculation(session_id)
    except Exception as e:
        import traceback
        print(f"\n[ERROR] Indicator test failed: {e}")
        traceback.print_exc()
        results['indicator'] = {"success": False, "error": str(e)}

    # Test 2: Strategy evaluation flow
    try:
        results['evaluation'] = await test_strategy_evaluation_flow()
    except Exception as e:
        import traceback
        print(f"\n[ERROR] Evaluation test failed: {e}")
        traceback.print_exc()
        results['evaluation'] = {"success": False, "error": str(e)}

    # Test 3: Full backtest
    try:
        results['backtest'] = await test_full_backtest(session_id, provider)
    except Exception as e:
        import traceback
        print(f"\n[ERROR] Backtest test failed: {e}")
        traceback.print_exc()
        results['backtest'] = {"success": False, "error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, result in results.items():
        status = "PASS" if result.get('success') else "FAIL"
        print(f"  {test_name}: {status}")
        if not result.get('success'):
            all_passed = False
            if 'error' in result:
                print(f"    Error: {result['error']}")

    print("\n" + "=" * 80)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 80)

    await provider.close()
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
