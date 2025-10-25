"""
Simple Test for New Pump Detection Indicators
=============================================
Basic validation that indicators calculate correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.services.indicators.pump_magnitude_pct import pump_magnitude_pct_algorithm
from src.domain.services.indicators.volume_surge_ratio import volume_surge_ratio_algorithm
from src.domain.services.indicators.price_velocity import price_velocity_algorithm
from src.domain.services.indicators.velocity_cascade import velocity_cascade_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow


def test_pump_magnitude_pct():
    """Test PUMP_MAGNITUDE_PCT basic calculation."""
    print("\n=== Testing PUMP_MAGNITUDE_PCT ===")

    # Price increasing from 100 to 110 (10% pump)
    current_data = [
        (100.0, 105.0),
        (105.0, 110.0),
    ]
    baseline_data = [
        (160.0, 100.0),
        (145.0, 100.0),
        (130.0, 100.0),
    ]

    windows = [
        DataWindow(current_data, 100.0, 110.0, "price"),
        DataWindow(baseline_data, 160.0, 130.0, "price"),
    ]

    params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

    result = pump_magnitude_pct_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 0, "Should detect positive pump"
    assert 8.0 < result < 12.0, f"Expected ~10%, got {result}"

    print("✓ PUMP_MAGNITUDE_PCT test passed")
    return True


def test_volume_surge_ratio():
    """Test VOLUME_SURGE_RATIO basic calculation."""
    print("\n=== Testing VOLUME_SURGE_RATIO ===")

    # Current volume: high
    current_data = [
        (100.0, 10.0),
        (101.0, 10.0),
        (102.0, 10.0),
    ]

    # Baseline volume: normal
    baseline_data = [
        (200.0, 2.0),
        (201.0, 2.0),
        (202.0, 2.0),
    ]

    windows = [
        DataWindow(current_data, 100.0, 103.0, "volume"),
        DataWindow(baseline_data, 200.0, 203.0, "volume"),
    ]

    params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "t3": 600.0, "t4": 30.0})

    result = volume_surge_ratio_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 3.0, f"Should detect surge, got {result}"

    print("✓ VOLUME_SURGE_RATIO test passed")
    return True


def test_price_velocity():
    """Test PRICE_VELOCITY basic calculation."""
    print("\n=== Testing PRICE_VELOCITY ===")

    # Price increasing
    current_data = [(100.0, 110.0)]
    baseline_data = [(160.0, 100.0), (145.0, 100.0)]

    windows = [
        DataWindow(current_data, 100.0, 105.0, "price"),
        DataWindow(baseline_data, 160.0, 145.0, "price"),
    ]

    params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

    result = price_velocity_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert result > 0, f"Should detect positive velocity, got {result}"

    print("✓ PRICE_VELOCITY test passed")
    return True


def test_velocity_cascade():
    """Test VELOCITY_CASCADE basic calculation."""
    print("\n=== Testing VELOCITY_CASCADE ===")

    # Create simple acceleration pattern
    ultra_short_current = [(5.0, 115.0)]
    ultra_short_baseline = [(15.0, 110.0)]

    short_current = [(10.0, 110.0)]
    short_baseline = [(40.0, 105.0)]

    medium_current = [(20.0, 105.0)]
    medium_baseline = [(80.0, 100.0)]

    windows = [
        DataWindow(ultra_short_current, 5.0, 5.0, "price"),
        DataWindow(ultra_short_baseline, 15.0, 15.0, "price"),
        DataWindow(short_current, 10.0, 10.0, "price"),
        DataWindow(short_baseline, 40.0, 40.0, "price"),
        DataWindow(medium_current, 20.0, 20.0, "price"),
        DataWindow(medium_baseline, 80.0, 80.0, "price"),
    ]

    params = IndicatorParameters({
        "windows": [
            {"t1": 5, "t3": 15, "d": 5},
            {"t1": 10, "t3": 40, "d": 10},
            {"t1": 20, "t3": 80, "d": 20}
        ]
    })

    result = velocity_cascade_algorithm.calculate_from_windows(windows, params)

    print(f"Result: {result}")
    assert result is not None, "Result should not be None"
    assert -1.0 <= result <= 1.0, f"Result should be in [-1, 1], got {result}"

    print("✓ VELOCITY_CASCADE test passed")
    return True


def test_algorithm_registry():
    """Test that algorithms are properly configured for registry."""
    print("\n=== Testing Algorithm Registry Compatibility ===")

    algorithms = [
        pump_magnitude_pct_algorithm,
        volume_surge_ratio_algorithm,
        price_velocity_algorithm,
        velocity_cascade_algorithm
    ]

    for algo in algorithms:
        # Test required methods
        assert hasattr(algo, 'get_indicator_type'), f"{algo} missing get_indicator_type"
        assert hasattr(algo, 'get_name'), f"{algo} missing get_name"
        assert hasattr(algo, 'get_description'), f"{algo} missing get_description"
        assert hasattr(algo, 'get_category'), f"{algo} missing get_category"
        assert hasattr(algo, 'get_parameters'), f"{algo} missing get_parameters"
        assert hasattr(algo, 'is_time_driven'), f"{algo} missing is_time_driven"

        # Test method calls
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
    print("TESTING NEW PUMP DETECTION INDICATORS")
    print("="*60)

    tests = [
        test_pump_magnitude_pct,
        test_volume_surge_ratio,
        test_price_velocity,
        test_velocity_cascade,
        test_algorithm_registry
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
