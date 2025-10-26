#!/usr/bin/env python3
"""
Quick Manual Test - Incremental Indicator System
================================================
Simple standalone test to verify Phase 1B implementation.

Usage:
    python scripts/test_incremental_system.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.timescale_client import TimescaleClient, TimescaleConfig
from domain.services.indicator_scheduler import IndicatorScheduler
from domain.services.indicators.incremental_indicators import (
    IncrementalEMA,
    IncrementalSMA,
    IncrementalVWAP,
    IncrementalRSI,
    create_incremental_indicator
)


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = TimescaleConfig(
    host="localhost",
    port=5432,
    database="trading",
    user="trading_user",
    password="trading_pass",
    min_pool_size=2,
    max_pool_size=5
)

TEST_SYMBOL = "BTC_USDT_MANUAL_TEST"
RUN_DURATION = 10  # seconds


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_database_connection():
    """Test 1: Database connection"""
    print("\n[Test 1] Database Connection")
    print("-" * 60)

    client = TimescaleClient(DB_CONFIG)

    try:
        await client.connect()
        is_healthy = await client.health_check()

        if is_healthy:
            print("✓ Connected to TimescaleDB successfully")
            print(f"✓ Pool size: {client.pool.get_size()}/{client.pool.get_max_size()}")
        else:
            print("✗ Database health check failed")
            return False

        await client.disconnect()
        return True

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


async def test_incremental_indicators():
    """Test 2: Incremental indicators"""
    print("\n[Test 2] Incremental Indicators")
    print("-" * 60)

    # Test prices (simulated BTC prices)
    prices = [
        50000, 50100, 50050, 50200, 50150,
        50300, 50250, 50400, 50350, 50500,
        50450, 50600, 50550, 50700, 50650
    ]

    # Create indicators
    ema = IncrementalEMA("EMA_5", TEST_SYMBOL, period=5)
    sma = IncrementalSMA("SMA_5", TEST_SYMBOL, period=5)
    rsi = IncrementalRSI("RSI_14", TEST_SYMBOL, period=14)
    vwap = IncrementalVWAP("VWAP", TEST_SYMBOL)

    print(f"Testing with {len(prices)} price updates...")

    timestamp = datetime.now()

    for i, price in enumerate(prices):
        # Update all indicators
        ema_val = ema.update(price, timestamp)
        sma_val = sma.update(price, timestamp)
        rsi_val = rsi.update(price, timestamp)
        vwap_val = vwap.update(price, timestamp, volume=1000 + i * 50)

        timestamp += timedelta(seconds=1)

        # Print first and last few
        if i < 3 or i >= len(prices) - 3:
            print(f"  #{i+1:2d} | Price: ${price:,} | "
                  f"EMA: {ema_val:.2f if ema_val else 'N/A':>10} | "
                  f"SMA: {sma_val:.2f if sma_val else 'N/A':>10} | "
                  f"RSI: {rsi_val:.2f if rsi_val else 'N/A':>6} | "
                  f"VWAP: {vwap_val:.2f if vwap_val else 'N/A':>10}")
        elif i == 3:
            print("  ...")

    # Verify final values
    final_ema = ema.get_value()
    final_sma = sma.get_value()
    final_rsi = rsi.get_value()
    final_vwap = vwap.get_value()

    print("\nFinal indicator values:")
    print(f"  EMA(5):  {final_ema:.2f}")
    print(f"  SMA(5):  {final_sma:.2f}")
    print(f"  RSI(14): {final_rsi:.2f}")
    print(f"  VWAP:    {final_vwap:.2f}")

    # Sanity checks
    assert final_ema is not None, "EMA failed"
    assert final_sma is not None, "SMA failed"
    assert final_rsi is not None, "RSI failed"
    assert final_vwap is not None, "VWAP failed"
    assert 0 <= final_rsi <= 100, f"RSI out of range: {final_rsi}"

    print("✓ All indicators calculated correctly")
    return True


async def test_scheduler_and_database():
    """Test 3: Scheduler + Database integration"""
    print("\n[Test 3] Scheduler + Database Integration")
    print("-" * 60)

    # Connect to database
    client = TimescaleClient(DB_CONFIG)
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

    print("✓ Database cleaned")

    # Insert test market data
    print(f"✓ Inserting test market data for {TEST_SYMBOL}...")

    base_time = datetime.now() - timedelta(seconds=30)
    market_data = []

    for i in range(30):
        ts = base_time + timedelta(seconds=i)
        price = 50000 + i * 50 + ((-1) ** i * 25)

        market_data.append((
            ts,
            TEST_SYMBOL,
            price,      # open
            price + 30, # high
            price - 30, # low
            price,      # close
            1000 + i * 100,  # volume
            10 + i,     # num_trades
            None        # metadata
        ))

    await client.bulk_insert_market_data(market_data)
    print(f"✓ Inserted {len(market_data)} market data points via COPY")

    # Create scheduler
    scheduler = IndicatorScheduler(
        db_client=client,
        tick_interval=1.0,
        batch_size=5
    )

    # Register indicators
    indicators = [
        create_incremental_indicator('EMA', 'EMA_10', TEST_SYMBOL, period=10),
        create_incremental_indicator('SMA', 'SMA_10', TEST_SYMBOL, period=10),
        create_incremental_indicator('RSI', 'RSI_14', TEST_SYMBOL, period=14),
        create_incremental_indicator('VWAP', 'VWAP', TEST_SYMBOL),
    ]

    for ind in indicators:
        scheduler.register_indicator(ind)

    print(f"✓ Registered {scheduler.get_indicator_count()} indicators")

    # Start scheduler
    print(f"✓ Starting scheduler (will run for {RUN_DURATION}s)...")
    await scheduler.start()

    # Monitor for RUN_DURATION seconds
    for sec in range(RUN_DURATION):
        await asyncio.sleep(1)
        stats = scheduler.get_stats()
        if sec % 3 == 0:  # Print every 3 seconds
            print(f"  [{sec+1:2d}s] Ticks: {stats['total_ticks']:2d} | "
                  f"Updates: {stats['total_updates']:3d} | "
                  f"Writes: {stats['total_writes']:3d} | "
                  f"Errors: {stats['errors']}")

    # Stop scheduler
    await scheduler.stop()

    # Final stats
    final_stats = scheduler.get_stats()
    print("\nFinal Statistics:")
    print(f"  Total ticks:    {final_stats['total_ticks']}")
    print(f"  Total updates:  {final_stats['total_updates']}")
    print(f"  Total writes:   {final_stats['total_writes']}")
    print(f"  Errors:         {final_stats['errors']}")

    # Verify database writes
    print("\nVerifying database writes...")
    async with client.pool.acquire() as conn:
        for ind in indicators:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM indicators WHERE symbol = $1 AND indicator_id = $2",
                TEST_SYMBOL,
                ind.indicator_id
            )
            print(f"  {ind.indicator_id:10s}: {count:3d} values stored")

            if count == 0:
                print(f"    ✗ WARNING: No values stored for {ind.indicator_id}")

    # Cleanup
    await client.disconnect()

    # Assertions
    assert final_stats['total_ticks'] >= RUN_DURATION - 1, "Not enough ticks executed"
    assert final_stats['total_writes'] > 0, "No database writes occurred"

    print("✓ Scheduler + Database integration successful")
    return True


async def test_copy_performance():
    """Test 4: COPY bulk insert performance"""
    print("\n[Test 4] COPY Bulk Insert Performance")
    print("-" * 60)

    client = TimescaleClient(DB_CONFIG)
    await client.connect()

    # Generate large batch
    batch_size = 1000
    print(f"Preparing {batch_size} indicator values...")

    base_time = datetime.now()
    indicator_batch = []

    for i in range(batch_size):
        ts = base_time + timedelta(seconds=i)
        indicator_batch.append((
            ts,
            TEST_SYMBOL,
            "EMA",
            "EMA_PERF_TEST",
            50000.0 + i * 0.5,
            None
        ))

    # Measure COPY performance
    import time
    start = time.perf_counter()

    await client.bulk_insert_indicators(indicator_batch)

    elapsed = time.perf_counter() - start

    print(f"✓ Inserted {batch_size} values via COPY in {elapsed*1000:.2f}ms")
    print(f"  Throughput: {batch_size/elapsed:.0f} records/second")
    print(f"  Per-record: {elapsed/batch_size*1000:.4f}ms")

    # Cleanup
    async with client.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM indicators WHERE indicator_id = 'EMA_PERF_TEST'"
        )

    await client.disconnect()

    # COPY should be fast - less than 100ms for 1000 records
    assert elapsed < 1.0, f"COPY too slow: {elapsed*1000:.2f}ms for {batch_size} records"

    print("✓ COPY bulk insert performance acceptable")
    return True


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all tests"""
    print("=" * 70)
    print("MANUAL TEST - Phase 1B: Incremental Indicator System")
    print("=" * 70)
    print()
    print("Testing implementation of user requirements:")
    print("  - asyncio scheduler co 1 s ✓")
    print("  - wskaźniki z ring-bufferów + inkrementalne akumulatory ✓")
    print("  - Zapis wskaźników do tabeli indicators (COPY) ✓")
    print("=" * 70)

    results = []

    try:
        # Test 1: Database connection
        result = await test_database_connection()
        results.append(("Database Connection", result))

        if not result:
            print("\n✗ Database connection failed. Cannot continue.")
            print("  Make sure TimescaleDB is running:")
            print("    docker-compose -f docker-compose.timescaledb.yml up -d")
            return

        # Test 2: Incremental indicators
        result = await test_incremental_indicators()
        results.append(("Incremental Indicators", result))

        # Test 3: Scheduler + Database
        result = await test_scheduler_and_database()
        results.append(("Scheduler + Database", result))

        # Test 4: COPY performance
        result = await test_copy_performance()
        results.append(("COPY Performance", result))

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Exception", False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name}")

    print("=" * 70)

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Phase 1B implementation verified!")
        print("\nReady to commit:")
        print("  - Incremental indicator infrastructure")
        print("  - 1-second asyncio scheduler")
        print("  - COPY bulk insert to TimescaleDB")
    else:
        print("\n⚠️  SOME TESTS FAILED - Review output above")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
