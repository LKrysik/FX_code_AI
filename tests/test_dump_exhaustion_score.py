"""
Test Suite for DUMP_EXHAUSTION_SCORE Indicator
==============================================
Tests multi-factor dump exhaustion detection.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.services.indicators.dump_exhaustion_score import dump_exhaustion_score_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow


def test_full_dump_exhaustion():
    """Test DUMP_EXHAUSTION_SCORE when all factors indicate exhaustion."""
    print("\n=== Testing Full Dump Exhaustion (Score >= 70) ===")

    # Peak price: 100, Current price: 50 -> 50% retracement (25 pts)
    peak_price = 100.0
    current_price = 50.0

    # Velocity: nearly zero (30 pts)
    # Current TWPA: 50.0, Baseline TWPA: 49.9 -> minimal velocity
    velocity_current = [(10.0, 50.0)]
    velocity_baseline = [(35.0, 49.9)]

    # Volume: normalized (25 pts)
    # Current: low volume, Baseline: high volume
    volume_current = [(10.0, 50.0, 100.0)]  # (timestamp, price, volume)
    volume_baseline = [(300.0, 100.0, 1000.0)]  # Much higher baseline volume

    # Imbalance: buyers returning (20 pts)
    # Positive imbalance = more bids than asks
    imbalance_data = [
        {"timestamp": 10.0, "bid_qty": 70.0, "ask_qty": 30.0},  # +40% imbalance
    ]

    windows = [
        DataWindow(velocity_current, 10.0, 10.0, "price"),      # [0] Velocity current
        DataWindow(velocity_baseline, 35.0, 35.0, "price"),     # [1] Velocity baseline
        DataWindow(volume_current, 10.0, 11.0, "volume"),       # [2] Volume current
        DataWindow(volume_baseline, 300.0, 301.0, "volume"),    # [3] Volume baseline
        DataWindow(imbalance_data, 10.0, 11.0, "orderbook"),    # [4] Imbalance
    ]

    params = IndicatorParameters({
        "velocity_t1": 10.0,
        "velocity_t3": 40.0,
        "velocity_d": 10.0,
        "volume_t1": 30.0,
        "volume_t2": 0.0,
        "volume_t3": 600.0,
        "volume_t4": 30.0,
        "imbalance_t1": 30.0,
        "imbalance_t2": 0.0,
        "peak_price": peak_price,
        "current_price": current_price,
        "velocity_threshold": 0.1,
        "volume_threshold": 0.8,
        "retracement_threshold": 40.0,
        "imbalance_threshold": -10.0,
    })

    result = dump_exhaustion_score_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result >= 70.0, f"Expected exhaustion score >= 70, got {result}"

    print("✓ Full dump exhaustion test passed")
    return True


def test_partial_dump_exhaustion():
    """Test DUMP_EXHAUSTION_SCORE when some factors indicate exhaustion."""
    print("\n=== Testing Partial Dump Exhaustion (Score ~50) ===")

    # Peak: 100, Current: 60 -> 40% retracement (25 pts)
    peak_price = 100.0
    current_price = 60.0

    # Velocity: still moving (0 pts)
    # Significant velocity indicates dump still active
    velocity_current = [(10.0, 60.0)]
    velocity_baseline = [(35.0, 70.0)]  # Large price change

    # Volume: still elevated (0 pts)
    volume_current = [(10.0, 60.0, 800.0)]
    volume_baseline = [(300.0, 100.0, 500.0)]  # Current higher than baseline

    # Imbalance: neutral (0 pts)
    imbalance_data = [
        {"timestamp": 10.0, "bid_qty": 50.0, "ask_qty": 50.0},  # Balanced
    ]

    windows = [
        DataWindow(velocity_current, 10.0, 10.0, "price"),
        DataWindow(velocity_baseline, 35.0, 35.0, "price"),
        DataWindow(volume_current, 10.0, 11.0, "volume"),
        DataWindow(volume_baseline, 300.0, 301.0, "volume"),
        DataWindow(imbalance_data, 10.0, 11.0, "orderbook"),
    ]

    params = IndicatorParameters({
        "velocity_t1": 10.0,
        "velocity_t3": 40.0,
        "velocity_d": 10.0,
        "volume_t1": 30.0,
        "volume_t2": 0.0,
        "volume_t3": 600.0,
        "volume_t4": 30.0,
        "imbalance_t1": 30.0,
        "imbalance_t2": 0.0,
        "peak_price": peak_price,
        "current_price": current_price,
        "velocity_threshold": 0.1,
        "volume_threshold": 0.8,
        "retracement_threshold": 40.0,
        "imbalance_threshold": -10.0,
    })

    result = dump_exhaustion_score_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    # Should get 25 points from retracement only
    assert 20.0 <= result <= 30.0, f"Expected score ~25 (retracement only), got {result}"

    print("✓ Partial dump exhaustion test passed")
    return True


def test_active_dump():
    """Test DUMP_EXHAUSTION_SCORE during active dump."""
    print("\n=== Testing Active Dump (Score < 50) ===")

    # Peak: 100, Current: 95 -> 5% retracement (0 pts)
    peak_price = 100.0
    current_price = 95.0

    # Velocity: high (0 pts)
    velocity_current = [(10.0, 95.0)]
    velocity_baseline = [(35.0, 100.0)]

    # Volume: very high (0 pts)
    volume_current = [(10.0, 95.0, 2000.0)]
    volume_baseline = [(300.0, 100.0, 500.0)]

    # Imbalance: strong sell pressure (0 pts)
    imbalance_data = [
        {"timestamp": 10.0, "bid_qty": 20.0, "ask_qty": 80.0},  # -60% imbalance
    ]

    windows = [
        DataWindow(velocity_current, 10.0, 10.0, "price"),
        DataWindow(velocity_baseline, 35.0, 35.0, "price"),
        DataWindow(volume_current, 10.0, 11.0, "volume"),
        DataWindow(volume_baseline, 300.0, 301.0, "volume"),
        DataWindow(imbalance_data, 10.0, 11.0, "orderbook"),
    ]

    params = IndicatorParameters({
        "velocity_t1": 10.0,
        "velocity_t3": 40.0,
        "velocity_d": 10.0,
        "volume_t1": 30.0,
        "volume_t2": 0.0,
        "volume_t3": 600.0,
        "volume_t4": 30.0,
        "imbalance_t1": 30.0,
        "imbalance_t2": 0.0,
        "peak_price": peak_price,
        "current_price": current_price,
    })

    result = dump_exhaustion_score_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result < 50.0, f"Expected low score during active dump, got {result}"

    print("✓ Active dump test passed")
    return True


def test_algorithm_metadata():
    """Test DUMP_EXHAUSTION_SCORE metadata and configuration."""
    print("\n=== Testing Algorithm Metadata ===")

    assert dump_exhaustion_score_algorithm.get_indicator_type() == "DUMP_EXHAUSTION_SCORE"
    assert dump_exhaustion_score_algorithm.get_name() == "Dump Exhaustion Score"
    assert dump_exhaustion_score_algorithm.get_category() == "general"
    assert dump_exhaustion_score_algorithm.is_time_driven() == True

    params_def = dump_exhaustion_score_algorithm.get_parameters()
    assert len(params_def) > 0, "Should have parameter definitions"

    # Verify critical parameters exist
    param_names = [p.name for p in params_def]
    assert "peak_price" in param_names
    assert "current_price" in param_names
    assert "velocity_threshold" in param_names
    assert "volume_threshold" in param_names
    assert "retracement_threshold" in param_names
    assert "imbalance_threshold" in param_names

    print("✓ Algorithm metadata test passed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING DUMP_EXHAUSTION_SCORE INDICATOR")
    print("="*60)

    tests = [
        test_full_dump_exhaustion,
        test_partial_dump_exhaustion,
        test_active_dump,
        test_algorithm_metadata,
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
