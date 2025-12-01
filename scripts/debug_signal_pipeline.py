"""Direct test of signal generation pipeline - bypasses API to debug signals_detected=0 issue."""

import asyncio
import json
import sys
sys.path.insert(0, ".")

from src.domain.services.strategy_manager import Strategy, Condition, ConditionGroup, StrategyState, ConditionResult


def test_condition_evaluation():
    """Test Condition.evaluate() directly."""

    print("=" * 70)
    print("CONDITION EVALUATION DIAGNOSTIC TEST")
    print("=" * 70)

    # 1. Create a simple condition: price_velocity >= 0.001
    condition = Condition(
        name="velocity_check",
        condition_type="price_velocity",  # lowercase to match what engine publishes
        operator="gte",
        value=0.001,
        description="Test velocity condition"
    )

    print(f"\n[1] Created condition:")
    print(f"    - name: {condition.name}")
    print(f"    - condition_type: '{condition.condition_type}'")
    print(f"    - operator: '{condition.operator}'")
    print(f"    - value: {condition.value}")

    # 2. Test condition evaluation with different indicator values
    print("\n[2] Testing condition evaluation:")

    test_cases = [
        {"price_velocity": 0.0005},  # Below threshold - should fail
        {"price_velocity": 0.001},   # Equal to threshold - should pass (gte)
        {"price_velocity": 0.002},   # Above threshold - should pass
        {"PRICE_VELOCITY": 0.002},   # Wrong case - should fail (key mismatch)
        {},                          # Empty - should be PENDING (no data)
    ]

    for i, indicator_values in enumerate(test_cases):
        result = condition.evaluate(indicator_values)
        print(f"\n    Test #{i+1}: indicator_values={indicator_values}")
        print(f"            result={result}")

        # Also test if condition_type is in the values
        print(f"            '{condition.condition_type}' in values: {condition.condition_type in indicator_values}")

    # 3. Create a test strategy
    print("\n" + "=" * 70)
    print("[3] Testing Strategy.evaluate_signal_detection()")
    print("=" * 70)

    strategy = Strategy(
        strategy_name="test_velocity_strategy",
        enabled=True,
        direction="LONG"
    )
    strategy.symbol = "BTC_USDT"
    strategy.current_state = StrategyState.MONITORING  # MUST be MONITORING!

    # Add condition to signal_detection
    strategy.signal_detection.conditions = [condition]

    print(f"\n    Strategy state: {strategy.current_state}")
    print(f"    Signal detection conditions: {len(strategy.signal_detection.conditions)}")

    # Test signal detection with passing values
    indicator_values = {"price_velocity": 0.002}
    result = strategy.evaluate_signal_detection(indicator_values)
    print(f"\n    Test with passing values ({indicator_values}):")
    print(f"    evaluate_signal_detection() = {result}")

    # Test signal detection with failing values
    indicator_values = {"price_velocity": 0.0005}
    result = strategy.evaluate_signal_detection(indicator_values)
    print(f"\n    Test with failing values ({indicator_values}):")
    print(f"    evaluate_signal_detection() = {result}")

    # 4. Test the indicator_values_by_symbol pattern used in StrategyManager
    print("\n" + "=" * 70)
    print("[4] Testing indicator_values_by_symbol pattern")
    print("=" * 70)

    indicator_values_by_symbol = {}

    # Simulate what _on_indicator_update does:
    # Storage key is indicator_type (lowercase)
    symbol = "BTC_USDT"
    indicator_type = "price_velocity"  # from event["indicator_type"]
    value = 0.002

    if symbol not in indicator_values_by_symbol:
        indicator_values_by_symbol[symbol] = {}

    indicator_values_by_symbol[symbol][indicator_type] = value

    print(f"\n    After storing: indicator_values_by_symbol = {indicator_values_by_symbol}")

    # Test retrieval for condition evaluation
    vals = indicator_values_by_symbol.get("BTC_USDT", {})
    print(f"    Values for BTC_USDT: {vals}")
    print(f"    condition_type '{condition.condition_type}' in vals: {condition.condition_type in vals}")

    # Evaluate
    result = condition.evaluate(vals)
    print(f"    condition.evaluate(vals) = {result}")

    # 5. Check ConditionResult enum values
    print("\n" + "=" * 70)
    print("[5] ConditionResult enum values")
    print("=" * 70)
    print(f"    PENDING = {ConditionResult.PENDING}")
    print(f"    MET = {ConditionResult.MET}")
    print(f"    NOT_MET = {ConditionResult.NOT_MET}")

    print("\n[DONE] Basic condition evaluation works!")


if __name__ == "__main__":
    test_condition_evaluation()
