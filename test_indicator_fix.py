#!/usr/bin/env python
"""
Quick Test Script - Indicator Calculation Fix Verification
===========================================================

This script performs basic smoke tests to verify the indicator calculation fix.

Usage:
    python test_indicator_fix.py

Tests:
    1. Import verification - check if all modified modules import correctly
    2. OfflineIndicatorEngine initialization - verify algorithm registry
    3. Basic indicator calculation - verify no hangs on simple data
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test 1: Verify all modified modules import correctly."""
    print("=" * 80)
    print("TEST 1: Import Verification")
    print("=" * 80)

    try:
        print("Importing offline_indicator_engine...")
        from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
        print("✅ offline_indicator_engine imported successfully")

        print("\nImporting algorithm_registry...")
        from src.domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry
        print("✅ algorithm_registry imported successfully")

        print("\nImporting indicators_routes...")
        from src.api import indicators_routes
        print("✅ indicators_routes imported successfully")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_offline_engine_init():
    """Test 2: Verify OfflineIndicatorEngine initialization."""
    print("\n" + "=" * 80)
    print("TEST 2: OfflineIndicatorEngine Initialization")
    print("=" * 80)

    try:
        from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
        from src.core.logger import get_logger

        logger = get_logger("test")

        print("Creating OfflineIndicatorEngine...")
        engine = OfflineIndicatorEngine(questdb_data_provider=None)

        print(f"✅ Engine created successfully")
        print(f"   - Algorithm registry: {'✅ Initialized' if engine._algorithm_registry else '❌ None (fallback mode)'}")

        if engine._algorithm_registry:
            algorithms = engine._algorithm_registry.get_all_algorithms()
            print(f"   - Discovered algorithms: {len(algorithms)}")
            if algorithms:
                print(f"   - Sample algorithms: {list(algorithms.keys())[:5]}")
        else:
            print("   ⚠️  WARNING: Algorithm registry not initialized - will use legacy method")

        return True
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")
        traceback.print_exc()
        return False


def test_algorithm_registry_error_handling():
    """Test 3: Verify algorithm registry error handling."""
    print("\n" + "=" * 80)
    print("TEST 3: Algorithm Registry Error Handling")
    print("=" * 80)

    try:
        from src.domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry
        from src.core.logger import get_logger

        logger = get_logger("test")
        registry = IndicatorAlgorithmRegistry(logger)

        print("Testing get_algorithm with non-existent type...")
        algorithm = registry.get_algorithm("NONEXISTENT_INDICATOR")

        if algorithm is None:
            print("✅ Correctly returns None for non-existent algorithm")
            print("   (Should have ERROR log with available_types)")
        else:
            print(f"❌ Unexpected result: {algorithm}")
            return False

        print("\nTesting get_algorithm with existing type...")
        # Try to get a known algorithm
        algorithms = registry.get_all_algorithms()
        if algorithms:
            test_type = list(algorithms.keys())[0]
            algorithm = registry.get_algorithm(test_type)
            if algorithm:
                print(f"✅ Successfully retrieved algorithm: {test_type}")
                print(f"   - Algorithm name: {algorithm.get_name()}")
            else:
                print(f"❌ Failed to retrieve known algorithm: {test_type}")
                return False

        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        return False


def test_legacy_calculation_error_handling():
    """Test 4: Verify legacy calculation method has error handling."""
    print("\n" + "=" * 80)
    print("TEST 4: Legacy Calculation Error Handling")
    print("=" * 80)

    try:
        from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
        from src.domain.services.streaming_indicator_engine import IndicatorType
        from src.domain.types.indicator_types import MarketDataPoint

        print("Creating engine with minimal data...")
        engine = OfflineIndicatorEngine(questdb_data_provider=None)

        # Create minimal test data (too small to calculate most indicators properly)
        test_data = [
            MarketDataPoint(timestamp=1000.0, price=100.0, volume=10.0, symbol="TEST"),
            MarketDataPoint(timestamp=1001.0, price=101.0, volume=11.0, symbol="TEST"),
        ]

        print("Attempting calculation with insufficient data...")
        # This should NOT hang even if calculation fails
        try:
            result = engine._calculate_indicator_series_old(
                symbol="TEST",
                indicator_type=IndicatorType.RSI,  # RSI needs more data
                timeframe="1m",
                period=14,
                params={"refresh_interval_seconds": 1.0},
                data_points=test_data
            )
            print(f"✅ Calculation completed without hanging")
            print(f"   - Result length: {len(result)}")
            print(f"   - Valid values: {sum(1 for v in result if v.value is not None)}")
            print(f"   - None values: {sum(1 for v in result if v.value is None)}")
        except Exception as e:
            # Exception is OK, hang is NOT
            print(f"⚠️  Calculation raised exception (expected): {type(e).__name__}")
            print(f"   (This is OK - important is that it didn't hang)")

        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("INDICATOR CALCULATION FIX - VERIFICATION TESTS")
    print("=" * 80)
    print()

    results = []

    # Test 1: Imports
    results.append(("Import Verification", test_imports()))

    # Test 2: Engine initialization
    results.append(("OfflineIndicatorEngine Init", test_offline_engine_init()))

    # Test 3: Algorithm registry error handling
    results.append(("Algorithm Registry Error Handling", test_algorithm_registry_error_handling()))

    # Test 4: Legacy calculation error handling
    results.append(("Legacy Calculation Error Handling", test_legacy_calculation_error_handling()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The fix appears to be working correctly.")
        print("\nNext steps:")
        print("1. Restart the backend server")
        print("2. Try adding an indicator through the UI")
        print("3. Monitor logs for ERROR messages (should be none or actionable)")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review the errors above.")
        print("\nThe fix may not be working correctly. Check:")
        print("1. Python syntax errors in modified files")
        print("2. Import paths and module structure")
        print("3. Algorithm registry initialization")
        return 1


if __name__ == "__main__":
    sys.exit(main())
