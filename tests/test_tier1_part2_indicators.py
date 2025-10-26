"""
Test Suite for Tier 1 Part 2 Indicators
======================================
Tests for LIQUIDITY_DRAIN_INDEX, MOMENTUM_REVERSAL_INDEX, BID_ASK_IMBALANCE
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.services.indicators.liquidity_drain_index import liquidity_drain_index_algorithm
from src.domain.services.indicators.momentum_reversal_index import momentum_reversal_index_algorithm
from src.domain.services.indicators.bid_ask_imbalance import bid_ask_imbalance_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow


def test_liquidity_drain_index():
    """Test LIQUIDITY_DRAIN_INDEX basic calculation."""
    print("\n=== Testing LIQUIDITY_DRAIN_INDEX ===")

    # Current liquidity: low (500 USDT)
    # Format: dict with timestamp, bid_qty, ask_qty, best_bid, best_ask
    current_data = [
        {"timestamp": 100.0, "bid_qty": 10.0, "ask_qty": 10.0, "best_bid": 25.0, "best_ask": 25.0},
        # Total liquidity: (10*25) + (10*25) = 500 USDT
    ]

    # Baseline liquidity: normal (1000 USDT)
    baseline_data = [
        {"timestamp": 200.0, "bid_qty": 20.0, "ask_qty": 20.0, "best_bid": 25.0, "best_ask": 25.0},
        # Total liquidity: (20*25) + (20*25) = 1000 USDT
    ]

    windows = [
        DataWindow(current_data, 100.0, 101.0, "orderbook"),
        DataWindow(baseline_data, 200.0, 201.0, "orderbook"),
    ]

    params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "t3": 600.0, "t4": 30.0})

    result = liquidity_drain_index_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 0, f"Should detect liquidity drain (positive value), got {result}"
    assert 40.0 < result < 60.0, f"Expected ~50% drain, got {result}"

    print("✓ LIQUIDITY_DRAIN_INDEX test passed")
    return True


def test_momentum_reversal_index():
    """Test MOMENTUM_REVERSAL_INDEX basic calculation."""
    print("\n=== Testing MOMENTUM_REVERSAL_INDEX ===")

    # Peak velocity: high (price rising fast)
    # Peak current: 120
    peak_current = [(5.0, 120.0)]
    # Peak baseline: 100
    peak_baseline = [(20.0, 100.0)]
    # Peak velocity = (120-100)/100 * 100 / time_diff ~= 20% per 12.5s = 1.6% per second

    # Current velocity: moderate (price rising slower)
    # Current: 115
    current_current = [(10.0, 115.0)]
    # Current baseline: 110
    current_baseline = [(40.0, 110.0)]
    # Current velocity = (115-110)/110 * 100 / time_diff ~= 4.5% per 25s = 0.18% per second

    # Reversal index should be negative (current < peak)

    windows = [
        DataWindow(current_current, 10.0, 10.0, "price"),
        DataWindow(current_baseline, 40.0, 40.0, "price"),
        DataWindow(peak_current, 5.0, 5.0, "price"),
        DataWindow(peak_baseline, 20.0, 20.0, "price"),
    ]

    params = IndicatorParameters({
        "t1_current": 10.0,
        "t3_current": 40.0,
        "d_current": 10.0,
        "t1_peak": 5.0,
        "t3_peak": 20.0,
        "d_peak": 5.0
    })

    result = momentum_reversal_index_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result < 0, f"Should detect momentum reversal (negative value), got {result}"

    print("✓ MOMENTUM_REVERSAL_INDEX test passed")
    return True


def test_bid_ask_imbalance():
    """Test BID_ASK_IMBALANCE basic calculation."""
    print("\n=== Testing BID_ASK_IMBALANCE ===")

    # Strong buy pressure: more bids than asks
    orderbook_data = [
        {"timestamp": 100.0, "bid_qty": 80.0, "ask_qty": 20.0},  # 60% imbalance
        {"timestamp": 101.0, "bid_qty": 70.0, "ask_qty": 30.0},  # 40% imbalance
    ]

    windows = [
        DataWindow(orderbook_data, 100.0, 102.0, "orderbook"),
    ]

    params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "smoothing": False})

    result = bid_ask_imbalance_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 0, f"Should detect buy pressure (positive value), got {result}"
    assert result > 30.0, f"Expected strong buy pressure > 30%, got {result}"

    print("✓ BID_ASK_IMBALANCE test passed")
    return True


def test_bid_ask_imbalance_sell_pressure():
    """Test BID_ASK_IMBALANCE detects sell pressure."""
    print("\n=== Testing BID_ASK_IMBALANCE (Sell Pressure) ===")

    # Strong sell pressure: more asks than bids
    orderbook_data = [
        {"timestamp": 100.0, "bid_qty": 20.0, "ask_qty": 80.0},  # -60% imbalance
        {"timestamp": 101.0, "bid_qty": 30.0, "ask_qty": 70.0},  # -40% imbalance
    ]

    windows = [
        DataWindow(orderbook_data, 100.0, 102.0, "orderbook"),
    ]

    params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "smoothing": False})

    result = bid_ask_imbalance_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result < 0, f"Should detect sell pressure (negative value), got {result}"
    assert result < -30.0, f"Expected strong sell pressure < -30%, got {result}"

    print("✓ BID_ASK_IMBALANCE (sell pressure) test passed")
    return True


def test_algorithm_registry_compatibility():
    """Test that new algorithms are properly configured."""
    print("\n=== Testing Algorithm Registry Compatibility ===")

    algorithms = [
        liquidity_drain_index_algorithm,
        momentum_reversal_index_algorithm,
        bid_ask_imbalance_algorithm
    ]

    for algo in algorithms:
        # Test required methods
        indicator_type = algo.get_indicator_type()
        name = algo.get_name()
        description = algo.get_description()
        category = algo.get_category()
        parameters = algo.get_parameters()
        is_time_driven = algo.is_time_driven()

        assert indicator_type, f"{algo} has empty indicator_type"
        assert name, f"{algo} has empty name"
        assert description, f"{algo} has empty description"
        assert category, f"{algo} has empty category"
        assert isinstance(parameters, list), f"{algo} parameters should be list"
        assert isinstance(is_time_driven, bool), f"{algo} is_time_driven should be bool"

        print(f"✓ {indicator_type}: {name} - OK")

    print("✓ Algorithm registry compatibility test passed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TIER 1 PART 2 INDICATORS")
    print("="*60)

    tests = [
        test_liquidity_drain_index,
        test_momentum_reversal_index,
        test_bid_ask_imbalance,
        test_bid_ask_imbalance_sell_pressure,
        test_algorithm_registry_compatibility
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
