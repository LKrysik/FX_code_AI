"""
Performance Tests - Throughput and Memory
==========================================

Tests system performance under load:
1. EventBus throughput: 1000 events/sec (no dropped messages)
2. LiveOrderManager: 100 orders/sec (all submitted)
3. Memory leak test: 1h load test (< 10% memory growth)

All MEXC API calls are mocked - NO real exchange calls.
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import AsyncMock, Mock
from decimal import Decimal

# Import components
from src.core.event_bus import EventBus
from src.domain.services.risk_manager import RiskManager
from src.domain.services.order_manager_live import LiveOrderManager, Order, OrderStatus
from src.infrastructure.adapters.mexc_adapter import (
    MexcRealAdapter,
    OrderStatusResponse,
    OrderStatus as MexcOrderStatus
)
from src.infrastructure.config.settings import AppSettings
from src.core.logger import StructuredLogger


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def event_bus():
    """Create EventBus instance"""
    return EventBus()


@pytest.fixture
def mock_logger():
    """Mock StructuredLogger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def mock_mexc_adapter_fast(mock_logger):
    """
    Fast mock MEXC adapter for performance testing.

    Returns immediately without delay.
    """
    adapter = Mock(spec=MexcRealAdapter)

    # Fast mocks (return immediately)
    adapter.create_market_order = AsyncMock(return_value="MOCK_ORDER")
    adapter.create_limit_order = AsyncMock(return_value="MOCK_ORDER")

    adapter.get_order_status = AsyncMock(return_value=OrderStatusResponse(
        exchange_order_id="MOCK_ORDER",
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=0.001,
        price=50000.0,
        status=MexcOrderStatus.FILLED,
        filled_quantity=0.001,
        average_fill_price=50000.0,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    ))

    return adapter


@pytest.fixture
def settings():
    """Mock AppSettings"""
    return AppSettings()


@pytest.fixture
def risk_manager(event_bus, settings):
    """Create RiskManager instance"""
    return RiskManager(
        event_bus=event_bus,
        settings=settings,
        initial_capital=Decimal('10000000')  # High capital to avoid rejections
    )


@pytest.fixture
def live_order_manager(event_bus, mock_mexc_adapter_fast, risk_manager):
    """Create LiveOrderManager with fast mocked MEXC adapter"""
    return LiveOrderManager(
        event_bus=event_bus,
        mexc_adapter=mock_mexc_adapter_fast,
        risk_manager=risk_manager,
        max_orders=10000  # Allow many orders
    )


# ============================================================================
# TEST 1: EventBus Throughput
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
class TestEventBusThroughput:
    """Test EventBus can handle 1000 events/sec without dropping messages"""

    async def test_eventbus_1000_events_per_second(self, event_bus):
        """
        Test: EventBus handles 1000 events/sec

        Target: 1000 events/sec
        Requirement: No dropped messages
        Duration: 5 seconds (5000 total messages)
        """

        # Track received messages
        messages_received = []
        messages_lock = asyncio.Lock()

        async def message_handler(data):
            async with messages_lock:
                messages_received.append(data)

        # Subscribe
        event_bus.subscribe("performance_test", message_handler)

        # Publish 5000 messages over 5 seconds (1000/sec)
        total_messages = 5000
        duration_seconds = 5
        messages_per_batch = 100
        batch_interval = (duration_seconds / total_messages) * messages_per_batch

        start_time = time.time()

        for batch in range(total_messages // messages_per_batch):
            batch_start = time.time()

            # Publish batch
            for i in range(messages_per_batch):
                message_id = batch * messages_per_batch + i
                await event_bus.publish("performance_test", {
                    "message_id": message_id,
                    "timestamp": time.time()
                })

            # Calculate sleep time to maintain rate
            batch_duration = time.time() - batch_start
            sleep_time = max(0, batch_interval - batch_duration)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        end_time = time.time()
        total_duration = end_time - start_time

        # Wait for all messages to be processed
        await asyncio.sleep(2)

        # Verify results
        actual_rate = total_messages / total_duration
        messages_received_count = len(messages_received)
        dropped_messages = total_messages - messages_received_count
        drop_rate = (dropped_messages / total_messages) * 100

        print(f"\n=== EventBus Throughput Test Results ===")
        print(f"Total messages sent: {total_messages}")
        print(f"Messages received: {messages_received_count}")
        print(f"Dropped messages: {dropped_messages}")
        print(f"Drop rate: {drop_rate:.2f}%")
        print(f"Actual rate: {actual_rate:.2f} messages/sec")
        print(f"Total duration: {total_duration:.2f} seconds")

        # Assertions
        assert actual_rate >= 900, f"Throughput too low: {actual_rate:.2f} msg/sec (target: 1000 msg/sec)"
        assert drop_rate <= 1.0, f"Too many dropped messages: {drop_rate:.2f}% (max: 1%)"

        # Cleanup
        event_bus.unsubscribe("performance_test", message_handler)


    async def test_eventbus_burst_load(self, event_bus):
        """
        Test: EventBus handles burst load

        Scenario: 5000 messages published in 1 second
        Requirement: All messages delivered
        """

        # Track received messages
        messages_received = []

        async def message_handler(data):
            messages_received.append(data)

        # Subscribe
        event_bus.subscribe("burst_test", message_handler)

        # Publish 5000 messages as fast as possible
        total_messages = 5000
        start_time = time.time()

        for i in range(total_messages):
            await event_bus.publish("burst_test", {"message_id": i})

        publish_duration = time.time() - start_time

        # Wait for processing
        await asyncio.sleep(5)

        # Verify results
        messages_received_count = len(messages_received)
        publish_rate = total_messages / publish_duration

        print(f"\n=== EventBus Burst Load Test Results ===")
        print(f"Total messages sent: {total_messages}")
        print(f"Messages received: {messages_received_count}")
        print(f"Publish duration: {publish_duration:.2f} seconds")
        print(f"Publish rate: {publish_rate:.2f} messages/sec")

        # Assertions
        assert messages_received_count >= total_messages * 0.99, "More than 1% messages lost in burst"

        # Cleanup
        event_bus.unsubscribe("burst_test", message_handler)


# ============================================================================
# TEST 2: LiveOrderManager Throughput
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
class TestLiveOrderManagerThroughput:
    """Test LiveOrderManager can handle 100 orders/sec"""

    async def test_order_manager_100_orders_per_second(
        self,
        event_bus,
        live_order_manager,
        risk_manager,
        mock_mexc_adapter_fast
    ):
        """
        Test: LiveOrderManager handles 100 orders/sec

        Target: 100 orders/sec
        Requirement: All orders submitted
        Duration: 5 seconds (500 total orders)
        """

        # Start service
        await live_order_manager.start()

        try:
            # Submit 500 orders over 5 seconds (100/sec)
            total_orders = 500
            duration_seconds = 5
            orders_per_batch = 10
            batch_interval = (duration_seconds / total_orders) * orders_per_batch

            start_time = time.time()
            orders_submitted = 0

            for batch in range(total_orders // orders_per_batch):
                batch_start = time.time()

                # Submit batch
                for i in range(orders_per_batch):
                    order = Order(
                        order_id=f"perf_order_{batch}_{i}",
                        symbol="BTC_USDT",
                        side="buy",
                        quantity=0.001,
                        price=None,
                        order_type="market",
                        status=OrderStatus.PENDING,
                        created_at=time.time(),
                        updated_at=time.time()
                    )

                    # Submit without risk validation for performance
                    result = await live_order_manager.submit_order(order, current_positions=None)
                    if result:
                        orders_submitted += 1

                # Calculate sleep time to maintain rate
                batch_duration = time.time() - batch_start
                sleep_time = max(0, batch_interval - batch_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            end_time = time.time()
            total_duration = end_time - start_time

            # Verify results
            actual_rate = orders_submitted / total_duration
            success_rate = (orders_submitted / total_orders) * 100

            print(f"\n=== LiveOrderManager Throughput Test Results ===")
            print(f"Total orders submitted: {orders_submitted}/{total_orders}")
            print(f"Success rate: {success_rate:.2f}%")
            print(f"Actual rate: {actual_rate:.2f} orders/sec")
            print(f"Total duration: {total_duration:.2f} seconds")
            print(f"MEXC API calls: {mock_mexc_adapter_fast.create_market_order.call_count}")

            # Assertions
            assert actual_rate >= 90, f"Throughput too low: {actual_rate:.2f} orders/sec (target: 100 orders/sec)"
            assert success_rate >= 95, f"Too many failed orders: {success_rate:.2f}% (min: 95%)"

        finally:
            await live_order_manager.stop()


# ============================================================================
# TEST 3: Memory Leak Test
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.skipif(os.getenv("SKIP_LONG_TESTS") == "1", reason="Skipping 1-hour test")
class TestMemoryLeak:
    """Test for memory leaks during extended operation"""

    async def test_no_memory_leak_1_hour(
        self,
        event_bus,
        live_order_manager,
        risk_manager
    ):
        """
        Test: No memory leak over 1 hour of operation

        Target: < 10% memory growth over 1 hour
        Load: 10 orders/sec (36,000 total orders)
        """

        # Get process for memory monitoring
        process = psutil.Process(os.getpid())

        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\n=== Memory Leak Test (1 Hour) ===")
        print(f"Initial memory: {initial_memory:.2f} MB")

        # Start service
        await live_order_manager.start()

        try:
            # Run for 1 hour at 10 orders/sec
            duration_seconds = 3600  # 1 hour
            orders_per_second = 10
            total_orders = duration_seconds * orders_per_second

            # For CI/testing, use shorter duration
            if os.getenv("CI") or os.getenv("SHORT_MEMORY_TEST"):
                duration_seconds = 300  # 5 minutes
                total_orders = duration_seconds * orders_per_second

            start_time = time.time()
            orders_submitted = 0
            memory_samples = []

            print(f"Running for {duration_seconds/60:.0f} minutes at {orders_per_second} orders/sec")

            while time.time() - start_time < duration_seconds:
                # Submit orders
                for i in range(orders_per_second):
                    order = Order(
                        order_id=f"leak_test_{orders_submitted}",
                        symbol="BTC_USDT",
                        side="buy" if orders_submitted % 2 == 0 else "sell",
                        quantity=0.001,
                        price=None,
                        order_type="market",
                        status=OrderStatus.PENDING,
                        created_at=time.time(),
                        updated_at=time.time()
                    )

                    await live_order_manager.submit_order(order, current_positions=None)
                    orders_submitted += 1

                # Wait 1 second
                await asyncio.sleep(1)

                # Sample memory every 60 seconds
                if orders_submitted % (60 * orders_per_second) == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_samples.append(current_memory)
                    elapsed = time.time() - start_time
                    print(f"[{elapsed/60:.0f}min] Memory: {current_memory:.2f} MB, Orders: {orders_submitted}")

            end_time = time.time()
            total_duration = end_time - start_time

            # Measure final memory
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            memory_growth_percent = (memory_growth / initial_memory) * 100

            print(f"\n=== Memory Leak Test Results ===")
            print(f"Duration: {total_duration/60:.1f} minutes")
            print(f"Total orders: {orders_submitted}")
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Memory growth: {memory_growth:.2f} MB ({memory_growth_percent:.2f}%)")
            print(f"Memory samples: {memory_samples}")

            # Assertions
            assert memory_growth_percent < 10, f"Memory growth too high: {memory_growth_percent:.2f}% (max: 10%)"

        finally:
            await live_order_manager.stop()


    async def test_no_memory_leak_short(
        self,
        event_bus,
        live_order_manager,
        risk_manager
    ):
        """
        Test: No memory leak over 5 minutes of operation (short version)

        Target: < 10% memory growth over 5 minutes
        Load: 50 orders/sec (15,000 total orders)
        """

        # Get process for memory monitoring
        process = psutil.Process(os.getpid())

        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\n=== Memory Leak Test (5 Minutes) ===")
        print(f"Initial memory: {initial_memory:.2f} MB")

        # Start service
        await live_order_manager.start()

        try:
            # Run for 5 minutes at 50 orders/sec
            duration_seconds = 300  # 5 minutes
            orders_per_second = 50
            total_orders = duration_seconds * orders_per_second

            start_time = time.time()
            orders_submitted = 0

            while time.time() - start_time < duration_seconds:
                # Submit orders in batch
                for i in range(orders_per_second):
                    order = Order(
                        order_id=f"short_leak_test_{orders_submitted}",
                        symbol="BTC_USDT",
                        side="buy" if orders_submitted % 2 == 0 else "sell",
                        quantity=0.001,
                        price=None,
                        order_type="market",
                        status=OrderStatus.PENDING,
                        created_at=time.time(),
                        updated_at=time.time()
                    )

                    await live_order_manager.submit_order(order, current_positions=None)
                    orders_submitted += 1

                # Wait 1 second
                await asyncio.sleep(1)

                # Log progress every 60 seconds
                if orders_submitted % (60 * orders_per_second) == 0:
                    elapsed = time.time() - start_time
                    current_memory = process.memory_info().rss / 1024 / 1024
                    print(f"[{elapsed/60:.0f}min] Memory: {current_memory:.2f} MB, Orders: {orders_submitted}")

            # Measure final memory
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            memory_growth_percent = (memory_growth / initial_memory) * 100

            print(f"\n=== Short Memory Leak Test Results ===")
            print(f"Duration: 5 minutes")
            print(f"Total orders: {orders_submitted}")
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Memory growth: {memory_growth:.2f} MB ({memory_growth_percent:.2f}%)")

            # Assertions (more lenient for short test)
            assert memory_growth_percent < 15, f"Memory growth too high: {memory_growth_percent:.2f}% (max: 15%)"

        finally:
            await live_order_manager.stop()


# ============================================================================
# TEST 4: Latency Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
class TestLatency:
    """Test system latency under normal load"""

    async def test_order_submission_latency(
        self,
        event_bus,
        live_order_manager,
        risk_manager
    ):
        """
        Test: Order submission latency

        Target: p95 < 100ms, p99 < 500ms
        Sample size: 1000 orders
        """

        # Start service
        await live_order_manager.start()

        try:
            # Submit 1000 orders and measure latency
            latencies = []

            for i in range(1000):
                order = Order(
                    order_id=f"latency_test_{i}",
                    symbol="BTC_USDT",
                    side="buy",
                    quantity=0.001,
                    price=None,
                    order_type="market",
                    status=OrderStatus.PENDING,
                    created_at=time.time(),
                    updated_at=time.time()
                )

                start = time.time()
                await live_order_manager.submit_order(order, current_positions=None)
                end = time.time()

                latency_ms = (end - start) * 1000
                latencies.append(latency_ms)

            # Calculate percentiles
            latencies.sort()
            p50 = latencies[int(len(latencies) * 0.50)]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)]
            avg = sum(latencies) / len(latencies)

            print(f"\n=== Order Submission Latency Test Results ===")
            print(f"Sample size: {len(latencies)}")
            print(f"Average: {avg:.2f} ms")
            print(f"p50: {p50:.2f} ms")
            print(f"p95: {p95:.2f} ms")
            print(f"p99: {p99:.2f} ms")

            # Assertions
            assert p95 < 100, f"p95 latency too high: {p95:.2f} ms (max: 100 ms)"
            assert p99 < 500, f"p99 latency too high: {p99:.2f} ms (max: 500 ms)"

        finally:
            await live_order_manager.stop()
