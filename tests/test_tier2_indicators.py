"""
Test Suite for Tier 2 Indicators
================================
Tests for DUMP_EXHAUSTION_SCORE, SUPPORT_LEVEL_PROXIMITY, VELOCITY_STABILIZATION_INDEX
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.services.indicators.dump_exhaustion_score import dump_exhaustion_score_algorithm
from src.domain.services.indicators.support_level_proximity import support_level_proximity_algorithm
from src.domain.services.indicators.velocity_stabilization_index import velocity_stabilization_index_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow


def test_dump_exhaustion_full():
    """Test DUMP_EXHAUSTION_SCORE detecting full exhaustion."""
    print("\n=== Testing DUMP_EXHAUSTION_SCORE (Full Exhaustion) ===")

    peak_price = 100.0
    current_price = 50.0  # 50% retracement

    # Velocity: nearly zero (30 pts)
    velocity_current = [(10.0, 50.0)]
    velocity_baseline = [(35.0, 49.9)]

    # Volume: normalized (25 pts)
    volume_current = [(10.0, 50.0, 100.0)]
    volume_baseline = [(300.0, 100.0, 1000.0)]

    # Imbalance: buyers returning (20 pts)
    imbalance_data = [{"timestamp": 10.0, "bid_qty": 70.0, "ask_qty": 30.0}]

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
    assert result >= 70.0, f"Expected exhaustion score >= 70, got {result}"

    print("✓ DUMP_EXHAUSTION_SCORE (full) test passed")
    return True


def test_dump_exhaustion_partial():
    """Test DUMP_EXHAUSTION_SCORE detecting partial exhaustion."""
    print("\n=== Testing DUMP_EXHAUSTION_SCORE (Partial Exhaustion) ===")

    peak_price = 100.0
    current_price = 60.0  # 40% retracement (25 pts)

    # Velocity: still moving (0 pts)
    velocity_current = [(10.0, 60.0)]
    velocity_baseline = [(35.0, 70.0)]

    # Volume: elevated (0 pts)
    volume_current = [(10.0, 60.0, 800.0)]
    volume_baseline = [(300.0, 100.0, 500.0)]

    # Imbalance: neutral (0 pts)
    imbalance_data = [{"timestamp": 10.0, "bid_qty": 50.0, "ask_qty": 50.0}]

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
    assert 20.0 <= result <= 30.0, f"Expected ~25 points (retracement only), got {result}"

    print("✓ DUMP_EXHAUSTION_SCORE (partial) test passed")
    return True


def test_support_level_proximity_above():
    """Test SUPPORT_LEVEL_PROXIMITY when price is above support."""
    print("\n=== Testing SUPPORT_LEVEL_PROXIMITY (Above Support) ===")

    # Current price: 55, Support: 50 -> 10% above
    current_data = [(10.0, 55.0)]
    support_data = [(1800.0, 50.0), (2000.0, 50.0)]

    windows = [
        DataWindow(current_data, 10.0, 10.0, "price"),
        DataWindow(support_data, 1800.0, 2000.0, "price"),
    ]

    params = IndicatorParameters({
        "t1": 10.0,
        "t_support_start": 3600.0,
        "t_support_end": 600.0,
    })

    result = support_level_proximity_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}%")
    assert result is not None, "Result should not be None"
    assert result > 0, f"Should be above support (positive), got {result}"
    assert 9.0 < result < 11.0, f"Expected ~10% above support, got {result}"

    print("✓ SUPPORT_LEVEL_PROXIMITY (above) test passed")
    return True


def test_support_level_proximity_at():
    """Test SUPPORT_LEVEL_PROXIMITY when price is at support."""
    print("\n=== Testing SUPPORT_LEVEL_PROXIMITY (At Support) ===")

    # Current price: 50.5, Support: 50 -> 1% above (at support)
    current_data = [(10.0, 50.5)]
    support_data = [(1800.0, 50.0)]

    windows = [
        DataWindow(current_data, 10.0, 10.0, "price"),
        DataWindow(support_data, 1800.0, 1800.0, "price"),
    ]

    params = IndicatorParameters({
        "t1": 10.0,
        "t_support_start": 3600.0,
        "t_support_end": 600.0,
    })

    result = support_level_proximity_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}%")
    assert result is not None, "Result should not be None"
    assert 0.0 < result < 2.0, f"Expected near support (~1%), got {result}"

    print("✓ SUPPORT_LEVEL_PROXIMITY (at support) test passed")
    return True


def test_support_level_proximity_below():
    """Test SUPPORT_LEVEL_PROXIMITY when price is below support."""
    print("\n=== Testing SUPPORT_LEVEL_PROXIMITY (Below Support) ===")

    # Current price: 48, Support: 50 -> -4% (overshot)
    current_data = [(10.0, 48.0)]
    support_data = [(1800.0, 50.0)]

    windows = [
        DataWindow(current_data, 10.0, 10.0, "price"),
        DataWindow(support_data, 1800.0, 1800.0, "price"),
    ]

    params = IndicatorParameters({
        "t1": 10.0,
        "t_support_start": 3600.0,
        "t_support_end": 600.0,
    })

    result = support_level_proximity_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}%")
    assert result is not None, "Result should not be None"
    assert result < 0, f"Should be below support (negative), got {result}"
    assert -5.0 < result < -3.0, f"Expected ~-4% below support, got {result}"

    print("✓ SUPPORT_LEVEL_PROXIMITY (below) test passed")
    return True


def test_velocity_stabilization_stable():
    """Test VELOCITY_STABILIZATION_INDEX detecting stable velocities."""
    print("\n=== Testing VELOCITY_STABILIZATION_INDEX (Stable) ===")

    # 3 samples with very similar velocities (low variance)
    # Sample 0: 50.0 -> 49.9
    sample0_current = [(10.0, 50.0)]
    sample0_baseline = [(35.0, 49.9)]

    # Sample 1: 50.0 -> 49.9 (5s ago)
    sample1_current = [(15.0, 50.0)]
    sample1_baseline = [(40.0, 49.9)]

    # Sample 2: 50.0 -> 49.9 (10s ago)
    sample2_current = [(20.0, 50.0)]
    sample2_baseline = [(45.0, 49.9)]

    windows = [
        DataWindow(sample0_current, 10.0, 10.0, "price"),
        DataWindow(sample0_baseline, 35.0, 35.0, "price"),
        DataWindow(sample1_current, 15.0, 15.0, "price"),
        DataWindow(sample1_baseline, 40.0, 40.0, "price"),
        DataWindow(sample2_current, 20.0, 20.0, "price"),
        DataWindow(sample2_baseline, 45.0, 45.0, "price"),
    ]

    params = IndicatorParameters({
        "num_samples": 3,
        "sample_interval": 5.0,
        "t1": 10.0,
        "t3": 40.0,
        "d": 10.0,
    })

    result = velocity_stabilization_index_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result < 0.5, f"Expected stable (< 0.5), got {result}"

    print("✓ VELOCITY_STABILIZATION_INDEX (stable) test passed")
    return True


def test_velocity_stabilization_volatile():
    """Test VELOCITY_STABILIZATION_INDEX detecting volatile velocities."""
    print("\n=== Testing VELOCITY_STABILIZATION_INDEX (Volatile) ===")

    # 3 samples with very different velocities (high variance)
    # Sample 0: 50.0 -> 60.0 (fast rise)
    sample0_current = [(10.0, 60.0)]
    sample0_baseline = [(35.0, 50.0)]

    # Sample 1: 60.0 -> 55.0 (moderate fall)
    sample1_current = [(15.0, 55.0)]
    sample1_baseline = [(40.0, 60.0)]

    # Sample 2: 55.0 -> 70.0 (fast rise again)
    sample2_current = [(20.0, 70.0)]
    sample2_baseline = [(45.0, 55.0)]

    windows = [
        DataWindow(sample0_current, 10.0, 10.0, "price"),
        DataWindow(sample0_baseline, 35.0, 35.0, "price"),
        DataWindow(sample1_current, 15.0, 15.0, "price"),
        DataWindow(sample1_baseline, 40.0, 40.0, "price"),
        DataWindow(sample2_current, 20.0, 20.0, "price"),
        DataWindow(sample2_baseline, 45.0, 45.0, "price"),
    ]

    params = IndicatorParameters({
        "num_samples": 3,
        "sample_interval": 5.0,
        "t1": 10.0,
        "t3": 40.0,
        "d": 10.0,
    })

    result = velocity_stabilization_index_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 1.0, f"Expected volatile (> 1.0), got {result}"

    print("✓ VELOCITY_STABILIZATION_INDEX (volatile) test passed")
    return True


def test_algorithm_metadata():
    """Test that Tier 2 algorithms are properly configured."""
    print("\n=== Testing Tier 2 Algorithm Metadata ===")

    algorithms = [
        (dump_exhaustion_score_algorithm, "DUMP_EXHAUSTION_SCORE", "general"),
        (support_level_proximity_algorithm, "SUPPORT_LEVEL_PROXIMITY", "close_order"),
        (velocity_stabilization_index_algorithm, "VELOCITY_STABILIZATION_INDEX", "general"),
    ]

    for algo, expected_type, expected_category in algorithms:
        indicator_type = algo.get_indicator_type()
        name = algo.get_name()
        description = algo.get_description()
        category = algo.get_category()
        is_time_driven = algo.is_time_driven()
        parameters = algo.get_parameters()

        assert indicator_type == expected_type, f"Expected {expected_type}, got {indicator_type}"
        assert category == expected_category, f"Expected category {expected_category}, got {category}"
        assert name, f"{indicator_type} has empty name"
        assert description, f"{indicator_type} has empty description"
        assert is_time_driven == True, f"{indicator_type} should be time-driven"
        assert isinstance(parameters, list), f"{indicator_type} parameters should be list"
        assert len(parameters) > 0, f"{indicator_type} should have parameters"

        print(f"✓ {indicator_type}: {name} - OK")

    print("✓ Tier 2 algorithm metadata test passed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TIER 2 INDICATORS")
    print("="*60)

    tests = [
        test_dump_exhaustion_full,
        test_dump_exhaustion_partial,
        test_support_level_proximity_above,
        test_support_level_proximity_at,
        test_support_level_proximity_below,
        test_velocity_stabilization_stable,
        test_velocity_stabilization_volatile,
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
