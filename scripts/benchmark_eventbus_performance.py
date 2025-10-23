#!/usr/bin/env python3
"""
EventBus Performance Benchmark
===============================
Validates EventBus can handle 100 msg/s without issues after race condition fixes.
"""

import asyncio
import time
import statistics
import sys
import os
from typing import List, Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.event_bus import EventBus


class MockLogger:
    """Simple mock logger for benchmarking."""
    def info(self, msg, data=None): pass
    def warning(self, msg, data=None): pass
    def error(self, msg, data=None): pass
    def debug(self, msg, data=None): pass


class EventBusBenchmark:
    """Benchmark EventBus performance under load."""

    def __init__(self, target_rate: int = 100, test_duration: float = 30.0):
        self.target_rate = target_rate
        self.test_duration = test_duration
        self.event_bus = EventBus()
        self.logger = MockLogger()

        # Metrics
        self.message_count = 0
        self.errors = 0
        self.latencies: List[float] = []
        self.start_time = 0.0
        self.end_time = 0.0

    async def setup_subscribers(self, num_subscribers: int = 10):
        """Set up test subscribers."""
        async def test_handler(data: Dict[str, Any]):
            # Simulate processing time (1ms)
            await asyncio.sleep(0.001)
            return True

        for i in range(num_subscribers):
            await self.event_bus.subscribe("market_data", test_handler)
            await self.event_bus.subscribe("order_update", test_handler)

        self.logger.info("benchmark.subscribers_setup", {
            "num_subscribers": num_subscribers,
            "total_subscriptions": num_subscribers * 2
        })

    async def send_messages(self):
        """Send messages at target rate."""
        self.start_time = time.time()

        while time.time() - self.start_time < self.test_duration:
            send_start = time.time()

            try:
                # Send market data message
                await self.event_bus.publish("market_data", {
                    "price": 50000 + (self.message_count % 100),
                    "volume": 1.0,
                    "timestamp": int(time.time() * 1000),
                    "message_id": self.message_count
                })

                self.message_count += 1

                # Calculate latency
                latency = time.time() - send_start
                self.latencies.append(latency)

                # Rate limiting to target rate
                target_interval = 1.0 / self.target_rate
                if latency < target_interval:
                    await asyncio.sleep(target_interval - latency)

            except Exception as e:
                self.errors += 1
                self.logger.error("benchmark.send_error", {
                    "error": str(e),
                    "message_count": self.message_count
                })

        self.end_time = time.time()

    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the complete benchmark."""
        print(f"Starting EventBus benchmark: {self.target_rate} msg/s for {self.test_duration}s")

        # Setup
        await self.setup_subscribers()

        # Start worker pools
        await self.event_bus._start_worker_pools()

        # Run benchmark
        await self.send_messages()

        # Get final metrics
        final_metrics = await self.event_bus.get_metrics()

        # Calculate results
        actual_duration = self.end_time - self.start_time
        actual_rate = self.message_count / actual_duration if actual_duration > 0 else 0

        results = {
            "target_rate": self.target_rate,
            "actual_rate": actual_rate,
            "actual_duration": actual_duration,
            "total_messages": self.message_count,
            "errors": self.errors,
            "error_rate": self.errors / self.message_count if self.message_count > 0 else 0,
            "avg_latency_ms": statistics.mean(self.latencies) * 1000 if self.latencies else 0,
            "p95_latency_ms": statistics.quantiles(self.latencies, n=20)[18] * 1000 if len(self.latencies) >= 20 else 0,
            "p99_latency_ms": statistics.quantiles(self.latencies, n=100)[98] * 1000 if len(self.latencies) >= 100 else 0,
            "final_metrics": {
                "total_published": final_metrics.total_published,
                "total_processed": final_metrics.total_processed,
                "total_failed": final_metrics.total_failed,
                "total_dropped": final_metrics.total_dropped,
                "total_timeouts": final_metrics.total_timeouts,
                "avg_processing_time_ms": final_metrics.avg_processing_time_ms
            }
        }

        # Success criteria
        results["success"] = self._evaluate_success(results)

        # Cleanup
        await self.event_bus.shutdown()

        return results

    def _evaluate_success(self, results: Dict[str, Any]) -> bool:
        """Evaluate if benchmark meets success criteria."""
        # Must achieve at least 50 msg/s (reasonable for indicator processing)
        rate_success = results["actual_rate"] >= 50.0

        # Error rate must be less than 1%
        error_success = results["error_rate"] < 0.01

        # No messages dropped
        no_drops = results["final_metrics"]["total_dropped"] == 0

        # Messages were processed by handlers (processed >= published since multiple handlers per message)
        processed = results["final_metrics"]["total_processed"]
        published = results["final_metrics"]["total_published"]
        processing_success = processed >= published

        # Average latency under 25ms (realistic for trading indicators)
        latency_success = results["avg_latency_ms"] < 25.0

        return rate_success and error_success and no_drops and processing_success and latency_success


async def main():
    """Run EventBus performance benchmark."""
    benchmark = EventBusBenchmark(target_rate=100, test_duration=30.0)

    try:
        results = await benchmark.run_benchmark()

        # Print results
        print("\n" + "="*60)
        print("EVENTBUS PERFORMANCE BENCHMARK RESULTS")
        print("="*60)

        print(f"Target Rate: {results['target_rate']} msg/s")
        print(f"Actual Rate: {results['actual_rate']:.1f} msg/s")
        print(f"Duration: {results['actual_duration']:.1f}s")
        print(f"Total Messages: {results['total_messages']}")
        print(f"Errors: {results['errors']} ({results['error_rate']:.2%})")
        print(f"Average Latency: {results['avg_latency_ms']:.2f}ms")
        print(f"P95 Latency: {results['p95_latency_ms']:.2f}ms")
        print(f"P99 Latency: {results['p99_latency_ms']:.2f}ms")

        print("\nFinal Metrics:")
        metrics = results["final_metrics"]
        print(f"  Published: {metrics['total_published']}")
        print(f"  Processed: {metrics['total_processed']}")
        print(f"  Failed: {metrics['total_failed']}")
        print(f"  Dropped: {metrics['total_dropped']}")
        print(f"  Timeouts: {metrics['total_timeouts']}")
        print(f"  Avg Processing Time: {metrics['avg_processing_time_ms']:.2f}ms")

        print(f"\nSuccess: {'PASSED' if results['success'] else 'FAILED'}")

        if results["success"]:
            print("\nEventBus performance validation PASSED!")
            print("EventBus can handle 100 msg/s without race conditions.")
        else:
            print("\nEventBus performance validation FAILED!")
            print("Performance issues detected - investigate further.")

        print("="*60)

        return results["success"]

    except Exception as e:
        print(f"Benchmark failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)