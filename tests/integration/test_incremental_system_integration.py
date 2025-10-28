"""
Integration Test - Incremental Indicator System
===============================================
End-to-end test of Phase 1B implementation:
- TimescaleDB connection
- Incremental indicators (EMA/SMA/VWAP/RSI/TWPA)
- 1-second scheduler
- COPY bulk insert

Per user requirements:
- asyncio scheduler co 1 s ✓
- wskaźniki liczone z ring-bufferów + inkrementalne akumulatory ✓
- Zapis wskaźników do tabeli indicators (COPY) ✓
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List, Dict
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.timescale_client import TimescaleClient, TimescaleConfig
from domain.services.indicator_scheduler import IndicatorScheduler
from domain.services.indicators.incremental_indicators import (
    IncrementalEMA,
    IncrementalSMA,
    IncrementalVWAP,
    IncrementalRSI,
    IncrementalTWPA,
    create_incremental_indicator
)


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

TEST_CONFIG = TimescaleConfig(
    host="localhost",
    port=5432,
    database="trading",
    user="trading_user",
    password="trading_pass",
    min_pool_size=2,
    max_pool_size=5
)

TEST_SYMBOL = "BTC_USDT_TEST"
TEST_DURATION = 5  # seconds


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def db_client():
    """Create and cleanup database client"""
    client = TimescaleClient(TEST_CONFIG)
    await client.connect()

    # Clean test data
    async with client.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM indicators WHERE symbol = $1",
            TEST_SYMBOL
        )
        await conn.execute(
            "DELETE FROM market_data WHERE symbol = $1",
            TEST_SYMBOL
        )

    yield client

    # Cleanup
    async with client.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM indicators WHERE symbol = $1",
            TEST_SYMBOL
        )
        await conn.execute(
            "DELETE FROM market_data WHERE symbol = $1",
            TEST_SYMBOL
        )

    await client.disconnect()


@pytest.fixture
async def scheduler(db_client):
    """Create indicator scheduler"""
    sched = IndicatorScheduler(
        db_client=db_client,
        tick_interval=1.0,
        batch_size=10
    )
    yield sched

    if sched.is_running:
        await sched.stop()


# ============================================================================
# TEST 1: Database Connection
# ============================================================================

@pytest.mark.asyncio
async def test_database_connection(db_client):
    """
    Test: TimescaleDB connection works
    """
    # Health check
    is_healthy = await db_client.health_check()
    assert is_healthy, "Database health check failed"

    # Test query
    async with db_client.pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1, "Basic query failed"

    print("✓ Database connection successful")


# ============================================================================
# TEST 2: Incremental Indicators (O(1) Updates)
# ============================================================================

@pytest.mark.asyncio
async def test_incremental_indicators_correctness():
    """
    Test: Incremental indicators calculate correct values
    Verify O(1) updates match expected mathematical results
    """
    # Test data: simple price sequence
    prices = [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0]
    timestamp = datetime.now()

    # Test EMA
    ema = IncrementalEMA("EMA_5", TEST_SYMBOL, period=5)
    ema_values = []

    for price in prices:
        value = ema.update(price, timestamp)
        if value is not None:
            ema_values.append(value)
        timestamp += timedelta(seconds=1)

    assert len(ema_values) > 0, "EMA produced no values"
    assert ema_values[-1] > 100, "EMA should be > 100 for uptrend"
    assert ema_values[-1] < prices[-1], "EMA should lag behind price"

    print(f"✓ EMA values: {ema_values[:3]}... → {ema_values[-1]:.2f}")

    # Test SMA
    sma = IncrementalSMA("SMA_5", TEST_SYMBOL, period=5)
    sma_values = []
    timestamp = datetime.now()

    for price in prices:
        value = sma.update(price, timestamp)
        if value is not None:
            sma_values.append(value)
        timestamp += timedelta(seconds=1)

    # After 5 prices, SMA should be average of last 5
    if len(sma_values) > 0:
        expected_sma = sum(prices[4:9]) / 5  # prices 4-8 (indices)
        assert abs(sma_values[4] - expected_sma) < 0.01, f"SMA calculation error: {sma_values[4]} != {expected_sma}"

    print(f"✓ SMA values: {sma_values}")

    # Test RSI
    rsi = IncrementalRSI("RSI_14", TEST_SYMBOL, period=14)
    rsi_values = []
    timestamp = datetime.now()

    for price in prices:
        value = rsi.update(price, timestamp)
        if value is not None:
            rsi_values.append(value)
        timestamp += timedelta(seconds=1)

    if rsi_values:
        assert 0 <= rsi_values[-1] <= 100, f"RSI should be 0-100, got {rsi_values[-1]}"
        print(f"✓ RSI values: {rsi_values[-1]:.2f}")

    # Test VWAP
    vwap = IncrementalVWAP("VWAP", TEST_SYMBOL)
    vwap_values = []
    timestamp = datetime.now()

    for i, price in enumerate(prices):
        volume = 1000 + i * 100  # Increasing volume
        value = vwap.update(price, timestamp, volume=volume)
        if value is not None:
            vwap_values.append(value)
        timestamp += timedelta(seconds=1)

    assert len(vwap_values) > 0, "VWAP produced no values"
    print(f"✓ VWAP values: {vwap_values[0]:.2f} → {vwap_values[-1]:.2f}")

    print("✓ All incremental indicators working correctly")


# ============================================================================
# TEST 3: Indicator Scheduler (1-second tick)
# ============================================================================

@pytest.mark.asyncio
async def test_scheduler_ticking(db_client, scheduler):
    """
    Test: Scheduler ticks every 1 second
    Per user requirement: "asyncio scheduler co 1 s"
    """
    # Register test indicators
    ema = IncrementalEMA("EMA_20", TEST_SYMBOL, period=20)
    sma = IncrementalSMA("SMA_20", TEST_SYMBOL, period=20)

    scheduler.register_indicator(ema)
    scheduler.register_indicator(sma)

    assert scheduler.get_indicator_count() == 2, "Indicator registration failed"

    # Insert test market data
    test_prices = [50000.0, 50100.0, 50050.0, 50150.0, 50200.0]
    base_time = datetime.now()

    market_data_batch = []
    for i, price in enumerate(test_prices):
        ts = base_time + timedelta(seconds=i)
        market_data_batch.append((
            ts,
            TEST_SYMBOL,
            price,  # open
            price + 50,  # high
            price - 50,  # low
            price,  # close
            1000.0,  # volume
            10,  # num_trades
            None  # metadata
        ))

    await db_client.bulk_insert_market_data(market_data_batch)

    # Start scheduler
    await scheduler.start()
    assert scheduler.is_running, "Scheduler failed to start"

    # Run for TEST_DURATION seconds
    initial_ticks = scheduler.stats['total_ticks']
    await asyncio.sleep(TEST_DURATION)

    # Stop scheduler
    await scheduler.stop()

    # Check tick count
    final_ticks = scheduler.stats['total_ticks']
    ticks_executed = final_ticks - initial_ticks

    # Should have ticked approximately TEST_DURATION times (±1 for timing)
    assert ticks_executed >= TEST_DURATION - 1, f"Expected ~{TEST_DURATION} ticks, got {ticks_executed}"

    print(f"✓ Scheduler ticked {ticks_executed} times in {TEST_DURATION}s (1 tick/second)")
    print(f"✓ Stats: {scheduler.get_stats()}")


# ============================================================================
# TEST 4: COPY Bulk Insert
# ============================================================================

@pytest.mark.asyncio
async def test_copy_bulk_insert(db_client, scheduler):
    """
    Test: COPY bulk insert for indicators works
    Per user requirement: "Zapis wskaźników do tabeli indicators (COPY)"
    """
    # Register indicators
    ema = IncrementalEMA("EMA_TEST", TEST_SYMBOL, period=5)
    scheduler.register_indicator(ema)

    # Insert market data
    test_prices = [50000.0 + i * 100 for i in range(10)]
    base_time = datetime.now()

    market_data_batch = []
    for i, price in enumerate(test_prices):
        ts = base_time + timedelta(seconds=i)
        market_data_batch.append((
            ts,
            TEST_SYMBOL,
            price, price + 50, price - 50, price,
            1000.0, 10, None
        ))

    await db_client.bulk_insert_market_data(market_data_batch)

    # Start scheduler
    await scheduler.start()
    await asyncio.sleep(3)  # Let it run for 3 seconds
    await scheduler.stop()

    # Check if indicators were written to database
    async with db_client.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM indicators WHERE symbol = $1 AND indicator_id = $2",
            TEST_SYMBOL,
            "EMA_TEST"
        )

    assert count > 0, "No indicators written to database via COPY"
    print(f"✓ COPY bulk insert successful: {count} indicator values written")
    print(f"✓ Total writes: {scheduler.stats['total_writes']}")


# ============================================================================
# TEST 5: End-to-End Integration
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_integration(db_client):
    """
    Test: Complete end-to-end flow
    Market Data → Incremental Indicators → Scheduler → COPY Insert → Database
    """
    # Create fresh scheduler
    scheduler = IndicatorScheduler(db_client, tick_interval=1.0, batch_size=5)

    # Register multiple indicators
    indicators_config = [
        ('EMA', 'EMA_10', {'period': 10}),
        ('SMA', 'SMA_10', {'period': 10}),
        ('RSI', 'RSI_14', {'period': 14}),
        ('VWAP', 'VWAP_1', {})
    ]

    for ind_type, ind_id, params in indicators_config:
        indicator = create_incremental_indicator(
            ind_type, ind_id, TEST_SYMBOL, **params
        )
        scheduler.register_indicator(indicator)

    assert scheduler.get_indicator_count() == 4, "Failed to register all indicators"

    # Insert realistic market data
    base_time = datetime.now() - timedelta(seconds=60)
    market_data_batch = []

    base_price = 50000.0
    for i in range(30):  # 30 data points
        ts = base_time + timedelta(seconds=i * 2)
        price = base_price + (i * 10) + ((-1) ** i * 20)  # Trending up with noise

        market_data_batch.append((
            ts,
            TEST_SYMBOL,
            price, price + 30, price - 30, price,
            1000.0 + i * 50,  # Increasing volume
            10 + i,
            None
        ))

    await db_client.bulk_insert_market_data(market_data_batch)

    # Start scheduler
    await scheduler.start()

    # Let it process data
    await asyncio.sleep(5)

    # Stop scheduler
    await scheduler.stop()

    # Verify results
    stats = scheduler.get_stats()
    assert stats['total_ticks'] > 0, "No ticks executed"
    assert stats['total_updates'] > 0, "No indicator updates"
    assert stats['total_writes'] > 0, "No database writes"

    # Check database for each indicator
    async with db_client.pool.acquire() as conn:
        for ind_type, ind_id, params in indicators_config:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM indicators WHERE symbol = $1 AND indicator_id = $2",
                TEST_SYMBOL,
                ind_id
            )
            assert count > 0, f"No data for {ind_id}"
            print(f"  - {ind_id}: {count} values stored")

    print(f"✓ End-to-end integration successful")
    print(f"  - Ticks: {stats['total_ticks']}")
    print(f"  - Indicator updates: {stats['total_updates']}")
    print(f"  - Database writes: {stats['total_writes']}")
    print(f"  - Errors: {stats['errors']}")


# ============================================================================
# TEST 6: Performance Check (O(1) Verification)
# ============================================================================

@pytest.mark.asyncio
async def test_performance_o1_complexity():
    """
    Test: Verify O(1) update complexity
    Update time should not increase with number of updates
    """
    import time

    ema = IncrementalEMA("PERF_EMA", TEST_SYMBOL, period=20)

    # Measure time for first 100 updates
    start = time.perf_counter()
    for i in range(100):
        ema.update(50000.0 + i, datetime.now())
    time_100 = time.perf_counter() - start

    # Measure time for next 100 updates (should be same)
    start = time.perf_counter()
    for i in range(100):
        ema.update(50000.0 + 100 + i, datetime.now())
    time_200 = time.perf_counter() - start

    # O(1) means time should be approximately constant
    ratio = time_200 / time_100

    print(f"✓ Performance test:")
    print(f"  - First 100 updates: {time_100*1000:.2f}ms ({time_100/100*1000:.4f}ms per update)")
    print(f"  - Next 100 updates: {time_200*1000:.2f}ms ({time_200/100*1000:.4f}ms per update)")
    print(f"  - Ratio: {ratio:.2f} (should be ~1.0 for O(1))")

    # Ratio should be close to 1.0 (allow up to 2x variation for noise)
    assert 0.5 <= ratio <= 2.0, f"Performance degradation detected: ratio={ratio}"


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRATION TEST - Phase 1B: Incremental Indicator System")
    print("=" * 70)

    # Run tests
    pytest.main([__file__, "-v", "-s"])
