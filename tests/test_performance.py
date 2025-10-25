"""
Performance Testing Suite
=========================
Measures calculation times for all indicators to identify bottlenecks.
"""

import sys
import os
import time
from typing import List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow

# Import all algorithm instances
from src.domain.services.indicators.pump_magnitude_pct import pump_magnitude_pct_algorithm
from src.domain.services.indicators.volume_surge_ratio import volume_surge_ratio_algorithm
from src.domain.services.indicators.price_velocity import price_velocity_algorithm
from src.domain.services.indicators.velocity_cascade import velocity_cascade_algorithm
from src.domain.services.indicators.liquidity_drain_index import liquidity_drain_index_algorithm
from src.domain.services.indicators.momentum_reversal_index import momentum_reversal_index_algorithm
from src.domain.services.indicators.bid_ask_imbalance import bid_ask_imbalance_algorithm
from src.domain.services.indicators.dump_exhaustion_score import dump_exhaustion_score_algorithm
from src.domain.services.indicators.support_level_proximity import support_level_proximity_algorithm
from src.domain.services.indicators.velocity_stabilization_index import velocity_stabilization_index_algorithm


def generate_price_data(num_points: int, start_ts: float = 0.0, interval: float = 0.1) -> List[Tuple[float, float]]:
    """Generate synthetic price data for testing."""
    data = []
    price = 100.0
    for i in range(num_points):
        timestamp = start_ts + i * interval
        price += (i % 10 - 5) * 0.1  # Simple oscillation
        data.append((timestamp, price))
    return data


def generate_volume_data(num_points: int, start_ts: float = 0.0, interval: float = 0.1) -> List[Tuple[float, float, float]]:
    """Generate synthetic volume data for testing."""
    data = []
    price = 100.0
    volume = 1000.0
    for i in range(num_points):
        timestamp = start_ts + i * interval
        price += (i % 10 - 5) * 0.1
        volume += (i % 20 - 10) * 10.0
        data.append((timestamp, price, volume))
    return data


def generate_orderbook_data(num_points: int, start_ts: float = 0.0, interval: float = 0.1) -> List[dict]:
    """Generate synthetic orderbook data for testing."""
    data = []
    for i in range(num_points):
        timestamp = start_ts + i * interval
        data.append({
            "timestamp": timestamp,
            "bid_qty": 100.0 + i % 50,
            "ask_qty": 100.0 + (i + 10) % 50,
            "best_bid": 99.9,
            "best_ask": 100.1,
        })
    return data


def benchmark_algorithm(name: str, algorithm, windows: List[DataWindow], params: IndicatorParameters, iterations: int = 1000):
    """Benchmark an algorithm's calculation performance."""
    start_time = time.perf_counter()

    results = []
    for _ in range(iterations):
        result = algorithm.calculate_from_windows(windows, params)
        results.append(result)

    end_time = time.perf_counter()
    total_time = end_time - start_time
    avg_time_ms = (total_time / iterations) * 1000

    # Verify we got valid results
    valid_results = sum(1 for r in results if r is not None)

    return {
        "name": name,
        "total_time_s": total_time,
        "avg_time_ms": avg_time_ms,
        "iterations": iterations,
        "valid_results": valid_results,
        "success_rate": (valid_results / iterations) * 100
    }


def test_pump_magnitude_pct_performance():
    """Benchmark PUMP_MAGNITUDE_PCT."""
    print("\n--- PUMP_MAGNITUDE_PCT ---")

    current_data = generate_price_data(100, start_ts=0.0)
    baseline_data = generate_price_data(100, start_ts=30.0)

    windows = [
        DataWindow(current_data, 0.0, 10.0, "price"),
        DataWindow(baseline_data, 30.0, 40.0, "price"),
    ]

    params = IndicatorParameters({"t1": 10.0, "t3": 40.0, "d": 10.0})

    result = benchmark_algorithm("PUMP_MAGNITUDE_PCT", pump_magnitude_pct_algorithm, windows, params)

    print(f"  Average time: {result['avg_time_ms']:.4f} ms")
    print(f"  Success rate: {result['success_rate']:.1f}%")

    return result


def test_volume_surge_ratio_performance():
    """Benchmark VOLUME_SURGE_RATIO."""
    print("\n--- VOLUME_SURGE_RATIO ---")

    current_data = generate_volume_data(300, start_ts=0.0)
    baseline_data = generate_volume_data(5700, start_ts=300.0)

    windows = [
        DataWindow(current_data, 0.0, 30.0, "volume"),
        DataWindow(baseline_data, 300.0, 600.0, "volume"),
    ]

    params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "t3": 600.0, "t4": 30.0})

    result = benchmark_algorithm("VOLUME_SURGE_RATIO", volume_surge_ratio_algorithm, windows, params)

    print(f"  Average time: {result['avg_time_ms']:.4f} ms")
    print(f"  Success rate: {result['success_rate']:.1f}%")

    return result


def test_velocity_cascade_performance():
    """Benchmark VELOCITY_CASCADE."""
    print("\n--- VELOCITY_CASCADE ---")

    # 6 windows (3 velocities x 2 windows each)
    windows = []
    for i in range(3):
        offset = i * 10.0
        current_data = generate_price_data(100, start_ts=offset)
        baseline_data = generate_price_data(100, start_ts=offset + 20.0)
        windows.append(DataWindow(current_data, offset, offset + 10.0, "price"))
        windows.append(DataWindow(baseline_data, offset + 20.0, offset + 30.0, "price"))

    params = IndicatorParameters({
        "windows": [
            {"t1": 10, "t3": 30, "d": 10, "label": "short"},
            {"t1": 20, "t3": 60, "d": 20, "label": "medium"},
            {"t1": 40, "t3": 120, "d": 40, "label": "long"}
        ]
    })

    result = benchmark_algorithm("VELOCITY_CASCADE", velocity_cascade_algorithm, windows, params)

    print(f"  Average time: {result['avg_time_ms']:.4f} ms")
    print(f"  Success rate: {result['success_rate']:.1f}%")

    return result


def test_dump_exhaustion_score_performance():
    """Benchmark DUMP_EXHAUSTION_SCORE."""
    print("\n--- DUMP_EXHAUSTION_SCORE ---")

    velocity_current = generate_price_data(100, start_ts=0.0)
    velocity_baseline = generate_price_data(100, start_ts=30.0)
    volume_current = generate_volume_data(300, start_ts=0.0)
    volume_baseline = generate_volume_data(5700, start_ts=300.0)
    imbalance_data = generate_orderbook_data(300, start_ts=0.0)

    windows = [
        DataWindow(velocity_current, 0.0, 10.0, "price"),
        DataWindow(velocity_baseline, 30.0, 40.0, "price"),
        DataWindow(volume_current, 0.0, 30.0, "volume"),
        DataWindow(volume_baseline, 300.0, 600.0, "volume"),
        DataWindow(imbalance_data, 0.0, 30.0, "orderbook"),
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
        "peak_price": 100.0,
        "current_price": 50.0,
    })

    result = benchmark_algorithm("DUMP_EXHAUSTION_SCORE", dump_exhaustion_score_algorithm, windows, params)

    print(f"  Average time: {result['avg_time_ms']:.4f} ms")
    print(f"  Success rate: {result['success_rate']:.1f}%")

    return result


def test_velocity_stabilization_index_performance():
    """Benchmark VELOCITY_STABILIZATION_INDEX."""
    print("\n--- VELOCITY_STABILIZATION_INDEX ---")

    # 6 windows (3 samples x 2 windows each)
    windows = []
    for i in range(3):
        offset = i * 5.0
        current_data = generate_price_data(100, start_ts=offset)
        baseline_data = generate_price_data(100, start_ts=offset + 30.0)
        windows.append(DataWindow(current_data, offset, offset + 10.0, "price"))
        windows.append(DataWindow(baseline_data, offset + 30.0, offset + 40.0, "price"))

    params = IndicatorParameters({
        "num_samples": 3,
        "sample_interval": 5.0,
        "t1": 10.0,
        "t3": 40.0,
        "d": 10.0,
    })

    result = benchmark_algorithm("VELOCITY_STABILIZATION_INDEX", velocity_stabilization_index_algorithm, windows, params)

    print(f"  Average time: {result['avg_time_ms']:.4f} ms")
    print(f"  Success rate: {result['success_rate']:.1f}%")

    return result


def main():
    """Run all performance tests."""
    print("="*60)
    print("PERFORMANCE TESTING SUITE")
    print("="*60)
    print("\nBenchmarking all indicators with 1000 iterations each...")

    results = []

    # Run benchmarks
    tests = [
        test_pump_magnitude_pct_performance,
        test_volume_surge_ratio_performance,
        test_velocity_cascade_performance,
        test_dump_exhaustion_score_performance,
        test_velocity_stabilization_index_performance,
    ]

    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)

    results_sorted = sorted(results, key=lambda x: x['avg_time_ms'])

    print(f"\n{'Algorithm':<35} {'Avg Time (ms)':<15} {'Success Rate':<15}")
    print("-" * 65)

    for result in results_sorted:
        print(f"{result['name']:<35} {result['avg_time_ms']:<15.4f} {result['success_rate']:<15.1f}%")

    # Performance analysis
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS")
    print("="*60)

    fastest = results_sorted[0]
    slowest = results_sorted[-1]
    avg_time = sum(r['avg_time_ms'] for r in results) / len(results)

    print(f"\nFastest: {fastest['name']} ({fastest['avg_time_ms']:.4f} ms)")
    print(f"Slowest: {slowest['name']} ({slowest['avg_time_ms']:.4f} ms)")
    print(f"Average: {avg_time:.4f} ms")

    # Check for performance issues
    slow_threshold = 1.0  # 1ms threshold
    slow_indicators = [r for r in results if r['avg_time_ms'] > slow_threshold]

    if slow_indicators:
        print(f"\n⚠️  SLOW INDICATORS (> {slow_threshold} ms):")
        for result in slow_indicators:
            print(f"  - {result['name']}: {result['avg_time_ms']:.4f} ms")
    else:
        print(f"\n✓ All indicators perform well (< {slow_threshold} ms)")

    # Real-time capability assessment
    print("\n" + "="*60)
    print("REAL-TIME CAPABILITY ASSESSMENT")
    print("="*60)

    # Assume we need to calculate all indicators every 1 second
    total_time_per_cycle = sum(r['avg_time_ms'] for r in results) / 1000  # Convert to seconds

    print(f"\nTotal calculation time (all indicators): {total_time_per_cycle*1000:.4f} ms")
    print(f"Target refresh interval: 1000 ms")
    print(f"Overhead percentage: {(total_time_per_cycle*1000/1000)*100:.2f}%")

    if total_time_per_cycle < 0.1:  # Less than 100ms for all indicators
        print("\n✓ EXCELLENT: System can handle real-time updates with low latency")
    elif total_time_per_cycle < 0.5:  # Less than 500ms
        print("\n✓ GOOD: System can handle real-time updates")
    else:
        print("\n⚠️  WARNING: System may struggle with real-time updates")

    print("\n" + "="*60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
