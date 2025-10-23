"""
Concurrent Load Testing for Indicator Variants System
====================================================

Tests the system's ability to handle 100+ concurrent users with comprehensive
performance validation and stability monitoring.
"""

import asyncio
import time
import pytest
from typing import Dict, Any

try:
    from src.testing.load_test_framework import (
        LoadTestFramework,
        LoadTestScenarios,
        run_comprehensive_load_test,
        LoadTestResult
    )
    from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger
except ImportError:
    # Mock for testing
    pass


class TestConcurrentLoad:
    """Test suite for concurrent load testing"""

    @pytest.fixture
    async def load_test_setup(self):
        """Setup load testing framework"""
        # This would be replaced with actual service initialization
        event_bus = EventBus()
        logger = StructuredLogger("load_test")
        engine = StreamingIndicatorEngine(event_bus, logger)

        framework = LoadTestFramework(engine, event_bus, logger)

        yield framework, engine, event_bus, logger

        # Cleanup
        # Note: In real testing, you might want to reset the engine state

    @pytest.mark.asyncio
    async def test_light_load_scenario(self, load_test_setup):
        """Test light load scenario (10 concurrent users)"""
        framework, engine, event_bus, logger = load_test_setup

        scenario = LoadTestScenarios.light_load_test()

        start_time = time.time()
        result = await framework.run_load_test(scenario)
        duration = time.time() - start_time

        # Validate results
        assert result.success, f"Light load test failed: {result.error_rate_pct}% error rate"
        assert result.error_rate_pct < 1.0, f"Error rate too high: {result.error_rate_pct}%"
        assert result.avg_response_time_ms < 200, f"Average response time too slow: {result.avg_response_time_ms}ms"
        assert result.p99_response_time_ms < 1000, f"P99 response time too slow: {result.p99_response_time_ms}ms"
        assert result.throughput_ops_per_sec > 10, f"Throughput too low: {result.throughput_ops_per_sec} ops/sec"

        print(f"Light load test completed in {duration:.2f}s")
        print(f"Operations: {result.total_operations}, Errors: {result.failed_operations} ({result.error_rate_pct:.2f}%)")
        print(f"Avg response time: {result.avg_response_time_ms:.2f}ms, Throughput: {result.throughput_ops_per_sec:.2f} ops/sec")

    @pytest.mark.asyncio
    async def test_medium_load_scenario(self, load_test_setup):
        """Test medium load scenario (50 concurrent users)"""
        framework, engine, event_bus, logger = load_test_setup

        scenario = LoadTestScenarios.medium_load_test()

        start_time = time.time()
        result = await framework.run_load_test(scenario)
        duration = time.time() - start_time

        # Validate results with slightly relaxed criteria for medium load
        assert result.success, f"Medium load test failed: {result.error_rate_pct}% error rate"
        assert result.error_rate_pct < 3.0, f"Error rate too high: {result.error_rate_pct}%"
        assert result.avg_response_time_ms < 300, f"Average response time too slow: {result.avg_response_time_ms}ms"
        assert result.p99_response_time_ms < 1500, f"P99 response time too slow: {result.p99_response_time_ms}ms"
        assert result.throughput_ops_per_sec > 25, f"Throughput too low: {result.throughput_ops_per_sec} ops/sec"

        print(f"Medium load test completed in {duration:.2f}s")
        print(f"Operations: {result.total_operations}, Errors: {result.failed_operations} ({result.error_rate_pct:.2f}%)")
        print(f"Avg response time: {result.avg_response_time_ms:.2f}ms, Throughput: {result.throughput_ops_per_sec:.2f} ops/sec")

    @pytest.mark.asyncio
    async def test_heavy_load_scenario(self, load_test_setup):
        """Test heavy load scenario (100 concurrent users)"""
        framework, engine, event_bus, logger = load_test_setup

        scenario = LoadTestScenarios.heavy_load_test()

        start_time = time.time()
        result = await framework.run_load_test(scenario)
        duration = time.time() - start_time

        # Validate results for heavy load
        assert result.success, f"Heavy load test failed: {result.error_rate_pct}% error rate"
        assert result.error_rate_pct < 5.0, f"Error rate too high: {result.error_rate_pct}%"
        assert result.avg_response_time_ms < 500, f"Average response time too slow: {result.avg_response_time_ms}ms"
        assert result.p99_response_time_ms < 2000, f"P99 response time too slow: {result.p99_response_time_ms}ms"
        assert result.throughput_ops_per_sec > 50, f"Throughput too low: {result.throughput_ops_per_sec} ops/sec"

        print(f"Heavy load test completed in {duration:.2f}s")
        print(f"Operations: {result.total_operations}, Errors: {result.failed_operations} ({result.error_rate_pct:.2f}%)")
        print(f"Avg response time: {result.avg_response_time_ms:.2f}ms, Throughput: {result.throughput_ops_per_sec:.2f} ops/sec")

    @pytest.mark.asyncio
    async def test_comprehensive_load_suite(self, load_test_setup):
        """Run comprehensive load test suite"""
        framework, engine, event_bus, logger = load_test_setup

        # Run comprehensive test suite
        results = await run_comprehensive_load_test(engine, event_bus, logger)

        # Validate all scenarios passed
        assert "light_load" in results
        assert "medium_load" in results
        assert "heavy_load" in results

        for scenario_name, result in results.items():
            assert result.success, f"Scenario {scenario_name} failed: {result.error_rate_pct}% error rate"
            print(f"{scenario_name}: {result.total_operations} ops, {result.error_rate_pct:.2f}% errors, {result.avg_response_time_ms:.2f}ms avg response")

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(self, load_test_setup):
        """Test memory stability during load testing"""
        framework, engine, event_bus, logger = load_test_setup

        # Get initial memory state
        initial_health = engine.get_health_status()
        initial_memory = initial_health.get("memory_stability", {}).get("memory_stats", {}).get("current_mb", 0)

        # Run medium load test
        scenario = LoadTestScenarios.medium_load_test()
        result = await framework.run_load_test(scenario)

        # Check memory stability after load
        final_health = engine.get_health_status()
        final_memory = final_health.get("memory_stability", {}).get("memory_stats", {}).get("current_mb", 0)

        memory_growth = final_memory - initial_memory
        stability_score = final_health.get("memory_stability", {}).get("stability_score", 0)

        # Memory should not grow excessively and stability should be maintained
        assert memory_growth < 100, f"Memory growth too high: {memory_growth}MB"
        assert stability_score > 70, f"Memory stability too low: {stability_score}%"

        print(f"Memory stability test: Growth {memory_growth:.2f}MB, Stability {stability_score:.2f}%")

    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self, load_test_setup):
        """Test cache performance during concurrent load"""
        framework, engine, event_bus, logger = load_test_setup

        # Get initial cache stats
        initial_health = engine.get_health_status()
        initial_cache_stats = initial_health.get("cache_stats", {})
        initial_hit_rate = initial_cache_stats.get("overall_hit_rate", 0)

        # Run load test with cache-intensive operations
        scenario = LoadTestScenarios.medium_load_test()
        result = await framework.run_load_test(scenario)

        # Check cache performance after load
        final_health = engine.get_health_status()
        final_cache_stats = final_health.get("cache_stats", {})
        final_hit_rate = final_cache_stats.get("overall_hit_rate", 0)

        # Cache hit rate should improve or maintain high performance
        assert final_hit_rate >= initial_hit_rate * 0.9, f"Cache hit rate degraded: {initial_hit_rate:.3f} -> {final_hit_rate:.3f}"
        assert final_hit_rate > 0.85, f"Cache hit rate too low under load: {final_hit_rate:.3f}"

        print(f"Cache performance under load: Hit rate {final_hit_rate:.3f}, Cache size {final_cache_stats.get('cache_size', 0)}")


# Standalone test runner for manual execution
async def run_load_tests():
    """Standalone load test runner"""
    print("Starting comprehensive load testing...")

    # Initialize services (simplified for testing)
    event_bus = EventBus()
    logger = StructuredLogger("load_test")
    engine = StreamingIndicatorEngine(event_bus, logger)

    try:
        # Run comprehensive test suite
        results = await run_comprehensive_load_test(engine, event_bus, logger)

        # Print results summary
        print("\n" + "="*60)
        print("LOAD TEST RESULTS SUMMARY")
        print("="*60)

        all_passed = True
        for scenario_name, result in results.items():
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{scenario_name.upper():12} | {status} | {result.total_operations:4} ops | {result.error_rate_pct:5.2f}% err | {result.avg_response_time_ms:6.1f}ms avg | {result.throughput_ops_per_sec:6.1f} ops/sec")
            if not result.success:
                all_passed = False

        print("="*60)
        print(f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

        # Print system resource usage
        final_health = engine.get_health_status()
        memory_stats = final_health.get("memory_stability", {}).get("memory_stats", {})
        cache_stats = final_health.get("cache_stats", {})

        print("
Final System State:")
        print(".1f")
        print(".1f")
        print(".3f")
        print(f"Cache Size: {cache_stats.get('cache_size', 0)} entries")

        return all_passed

    except Exception as e:
        print(f"Load testing failed with error: {e}")
        return False


if __name__ == "__main__":
    # Run standalone load tests
    success = asyncio.run(run_load_tests())
    exit(0 if success else 1)