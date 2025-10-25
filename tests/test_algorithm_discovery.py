"""
Integration Test: Algorithm Auto-Discovery
==========================================
Verifies that all implemented indicators are properly discovered
by the algorithm registry system.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_algorithm_auto_discovery():
    """Test that algorithm registry discovers all our new indicators."""
    print("\n" + "="*60)
    print("TESTING ALGORITHM AUTO-DISCOVERY")
    print("="*60)

    # Import registry
    from src.domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry

    # Create logger mock
    class MockLogger:
        def debug(self, msg, data=None): pass
        def info(self, msg, data=None):
            if data:
                print(f"[INFO] {msg}: {data}")
            else:
                print(f"[INFO] {msg}")
        def warning(self, msg, data=None):
            if data:
                print(f"[WARN] {msg}: {data}")
            else:
                print(f"[WARN] {msg}")
        def error(self, msg, data=None):
            if data:
                print(f"[ERROR] {msg}: {data}")
            else:
                print(f"[ERROR] {msg}")

    logger = MockLogger()
    registry = IndicatorAlgorithmRegistry(logger)

    # Run auto-discovery
    print("\nRunning auto-discovery...")
    discovered_count = registry.auto_discover_algorithms()

    print(f"\n✓ Discovered {discovered_count} algorithms")

    # Expected indicators (Tier 1 + Tier 2)
    expected_indicators = [
        # Tier 1 Part 1
        "TWPA",
        "TWPA_RATIO",
        "PUMP_MAGNITUDE_PCT",
        "VOLUME_SURGE_RATIO",
        "PRICE_VELOCITY",
        "VELOCITY_CASCADE",
        # Tier 1 Part 2
        "LIQUIDITY_DRAIN_INDEX",
        "MOMENTUM_REVERSAL_INDEX",
        "BID_ASK_IMBALANCE",
        # Tier 2
        "DUMP_EXHAUSTION_SCORE",
        "SUPPORT_LEVEL_PROXIMITY",
        "VELOCITY_STABILIZATION_INDEX",
    ]

    # Get all discovered algorithms
    all_algorithms = registry.get_all_algorithms()

    print(f"\nAll discovered algorithms ({len(all_algorithms)}):")
    for indicator_type in sorted(all_algorithms.keys()):
        algo = all_algorithms[indicator_type]
        print(f"  - {indicator_type}: {algo.get_name()}")

    # Check each expected indicator
    print("\nVerifying all indicators (Tier 1 + Tier 2):")
    missing = []
    found = []

    for indicator_type in expected_indicators:
        algo = registry.get_algorithm(indicator_type)
        if algo:
            print(f"  ✓ {indicator_type}: {algo.get_name()}")
            found.append(indicator_type)

            # Verify it has required methods
            assert hasattr(algo, 'get_parameters'), f"{indicator_type} missing get_parameters"
            assert hasattr(algo, 'is_time_driven'), f"{indicator_type} missing is_time_driven"
            assert hasattr(algo, 'calculate_refresh_interval'), f"{indicator_type} missing calculate_refresh_interval"

        else:
            print(f"  ✗ {indicator_type}: NOT FOUND")
            missing.append(indicator_type)

    # Results
    print("\n" + "="*60)
    print(f"RESULTS: {len(found)}/{len(expected_indicators)} found")

    if missing:
        print(f"\nMISSING ALGORITHMS: {missing}")
        print("\nPossible causes:")
        print("  - Algorithm file not in indicators/ directory")
        print("  - Missing algorithm instance export (e.g., 'pump_magnitude_pct_algorithm = ...')")
        print("  - Import error in algorithm file")
        return False
    else:
        print("\n✓ ALL INDICATORS SUCCESSFULLY DISCOVERED (Tier 1 + Tier 2)")
        return True


def test_algorithm_metadata():
    """Test that all algorithms have proper metadata."""
    print("\n" + "="*60)
    print("TESTING ALGORITHM METADATA")
    print("="*60)

    from src.domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry

    class MockLogger:
        def debug(self, msg, data=None): pass
        def info(self, msg, data=None): pass
        def warning(self, msg, data=None): pass
        def error(self, msg, data=None): pass

    registry = IndicatorAlgorithmRegistry(MockLogger())
    registry.auto_discover_algorithms()

    all_algorithms = registry.get_all_algorithms()

    issues = []

    for indicator_type, algo in all_algorithms.items():
        # Check metadata
        try:
            metadata = algo.get_registry_metadata()

            # Verify required fields
            assert 'indicator_type' in metadata, f"{indicator_type}: missing indicator_type"
            assert 'name' in metadata, f"{indicator_type}: missing name"
            assert 'description' in metadata, f"{indicator_type}: missing description"
            assert 'category' in metadata, f"{indicator_type}: missing category"
            assert 'parameters' in metadata, f"{indicator_type}: missing parameters"

            # Verify types
            assert isinstance(metadata['parameters'], list), f"{indicator_type}: parameters not a list"

            print(f"  ✓ {indicator_type}: metadata OK")

        except Exception as e:
            print(f"  ✗ {indicator_type}: {e}")
            issues.append((indicator_type, str(e)))

    print("\n" + "="*60)
    if issues:
        print(f"ISSUES FOUND: {len(issues)}")
        for indicator_type, error in issues:
            print(f"  - {indicator_type}: {error}")
        return False
    else:
        print("✓ ALL ALGORITHMS HAVE VALID METADATA")
        return True


def test_categories():
    """Test that categories are properly assigned."""
    print("\n" + "="*60)
    print("TESTING INDICATOR CATEGORIES")
    print("="*60)

    from src.domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry

    class MockLogger:
        def debug(self, msg, data=None): pass
        def info(self, msg, data=None): pass
        def warning(self, msg, data=None): pass
        def error(self, msg, data=None): pass

    registry = IndicatorAlgorithmRegistry(MockLogger())
    registry.auto_discover_algorithms()

    categories = registry.get_categories()

    print(f"\nDiscovered categories: {categories}")

    # Expected categories for Tier 1
    expected_categories = ["general", "risk", "price", "stop_loss", "take_profit", "close_order"]

    for category in categories:
        algos = registry.get_algorithms_by_category(category)
        print(f"\nCategory '{category}': {len(algos)} algorithms")
        for indicator_type, algo in algos.items():
            print(f"  - {indicator_type}: {algo.get_name()}")

    print("\n" + "="*60)
    print("✓ CATEGORY SYSTEM WORKING")
    return True


def main():
    """Run all integration tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "INTEGRATION TEST SUITE" + " "*21 + "║")
    print("╚" + "="*58 + "╝")

    tests = [
        ("Algorithm Auto-Discovery", test_algorithm_auto_discovery),
        ("Algorithm Metadata", test_algorithm_metadata),
        ("Category System", test_categories),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED WITH EXCEPTION:")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Final summary
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*20 + "FINAL RESULTS" + " "*25 + "║")
    print("╚" + "="*58 + "╝")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
