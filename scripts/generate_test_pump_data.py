#!/usr/bin/env python3
"""
Test Data Generator with Pump/Dump Patterns
============================================

Generates 1 hour of realistic test data for a single symbol with:
- Tick prices every 2 seconds (1800 ticks)
- Order book snapshots every 2 seconds
- Multiple pump/dump patterns to test strategy detection

This data is specifically designed to test Strategy Builder functionality:
- S1: Signal Detection (pump magnitude, volume surge)
- O1: Signal Cancellation (price reversal)
- Z1: Entry Conditions (RSI, spread)
- ZE1: Close Order Detection (profit target, momentum fade)
- E1: Emergency Exit (rapid dump)

Usage:
    python scripts/generate_test_pump_data.py
"""

import asyncio
import sys
import os
import random
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_feed.questdb_provider import QuestDBProvider


# =============================================================================
# CONFIGURATION
# =============================================================================

TEST_SYMBOL = "PUMP_TEST_USDT"  # Unique test symbol
SESSION_ID = f"pump_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
DURATION_SECONDS = 3600  # 1 hour
TICK_INTERVAL_SECONDS = 2  # Every 2 seconds
BASE_PRICE = 1.0  # Starting price in USDT

# Pump/Dump pattern configuration
PATTERNS = [
    # Pattern 1: Classic pump and dump (at 10 minutes)
    {
        "start_pct": 16.7,   # 10/60 = 16.7%
        "duration_pct": 8.3,  # 5 minutes
        "pump_magnitude": 0.15,  # 15% pump
        "dump_magnitude": 0.12,  # 12% dump
        "volume_surge": 5.0,     # 5x volume
    },
    # Pattern 2: Flash pump (at 25 minutes)
    {
        "start_pct": 41.7,   # 25/60 = 41.7%
        "duration_pct": 3.3,  # 2 minutes
        "pump_magnitude": 0.08,  # 8% pump
        "dump_magnitude": 0.05,  # 5% dump
        "volume_surge": 8.0,     # 8x volume
    },
    # Pattern 3: Slow pump with sharp dump (at 40 minutes)
    {
        "start_pct": 66.7,   # 40/60 = 66.7%
        "duration_pct": 10.0,  # 6 minutes
        "pump_magnitude": 0.20,  # 20% pump
        "dump_magnitude": 0.18,  # 18% dump
        "volume_surge": 3.0,     # 3x volume
    },
]


# =============================================================================
# DATA GENERATION FUNCTIONS
# =============================================================================

def calculate_price_at_tick(
    tick_index: int,
    total_ticks: int,
    base_price: float,
    patterns: List[Dict]
) -> Tuple[float, float, bool]:
    """
    Calculate price and volume at a specific tick index.

    Returns:
        (price, volume_multiplier, is_pump_phase)
    """
    progress = tick_index / total_ticks
    current_price = base_price
    volume_multiplier = 1.0
    is_pump = False

    # Apply patterns
    for pattern in patterns:
        pattern_start = pattern["start_pct"] / 100
        pattern_duration = pattern["duration_pct"] / 100
        pattern_end = pattern_start + pattern_duration

        if pattern_start <= progress <= pattern_end:
            # We're in a pattern
            pattern_progress = (progress - pattern_start) / pattern_duration
            pump_peak = 0.4  # Peak at 40% of pattern

            if pattern_progress < pump_peak:
                # Pump phase
                pump_progress = pattern_progress / pump_peak
                price_change = pattern["pump_magnitude"] * (pump_progress ** 1.5)
                current_price = base_price * (1 + price_change)
                volume_multiplier = 1.0 + (pattern["volume_surge"] - 1.0) * pump_progress
                is_pump = True
            else:
                # Dump phase
                dump_progress = (pattern_progress - pump_peak) / (1 - pump_peak)
                # Start from peak, dump down
                peak_price = base_price * (1 + pattern["pump_magnitude"])
                price_drop = pattern["dump_magnitude"] * (dump_progress ** 0.8)
                current_price = peak_price * (1 - price_drop)
                volume_multiplier = pattern["volume_surge"] * (1 - dump_progress * 0.5)
                is_pump = False
            break

    # Add natural noise (0.1% random walk)
    noise = random.gauss(0, 0.001)
    current_price *= (1 + noise)

    return current_price, volume_multiplier, is_pump


def generate_tick_data(
    symbol: str,
    session_id: str,
    duration_seconds: int,
    tick_interval: int,
    base_price: float,
    patterns: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Generate tick price data with pump/dump patterns.

    Returns list of tick dictionaries ready for QuestDB insertion.
    """
    ticks = []
    total_ticks = duration_seconds // tick_interval
    start_time = time.time()

    # Track running price for realistic order book
    running_price = base_price

    for i in range(total_ticks):
        tick_time = start_time + (i * tick_interval)

        price, volume_mult, is_pump = calculate_price_at_tick(
            i, total_ticks, base_price, patterns
        )

        # Base volume with pattern multiplier
        base_volume = random.uniform(100, 500)
        volume = base_volume * volume_mult

        ticks.append({
            "session_id": session_id,
            "symbol": symbol,
            "timestamp": tick_time,
            "price": price,
            "volume": volume,
            "quote_volume": price * volume,
        })

        running_price = price

    return ticks


def generate_orderbook_data(
    symbol: str,
    session_id: str,
    tick_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate order book snapshots based on tick data.

    Creates 3-level order book with realistic spread behavior:
    - Wider spread during high volatility (pump/dump)
    - Tighter spread during stable periods
    """
    orderbooks = []

    for i, tick in enumerate(tick_data):
        price = tick["price"]
        volume = tick["volume"]

        # Calculate spread based on volatility
        # Higher volume = higher volatility = wider spread
        base_spread_pct = 0.001  # 0.1% base spread
        volatility_factor = min(volume / 200, 5)  # Cap at 5x
        spread_pct = base_spread_pct * volatility_factor

        spread = price * spread_pct
        mid_price = price

        # 3 levels of order book
        levels = 3
        orderbook = {
            "session_id": session_id,
            "symbol": symbol,
            "timestamp": tick["timestamp"],
        }

        for level in range(1, levels + 1):
            # Bid prices (below mid)
            bid_price = mid_price - (spread / 2) * level
            bid_qty = random.uniform(10, 100) / level  # Less quantity at worse prices

            # Ask prices (above mid)
            ask_price = mid_price + (spread / 2) * level
            ask_qty = random.uniform(10, 100) / level

            orderbook[f"bid_price_{level}"] = bid_price
            orderbook[f"bid_qty_{level}"] = bid_qty
            orderbook[f"ask_price_{level}"] = ask_price
            orderbook[f"ask_qty_{level}"] = ask_qty

        orderbooks.append(orderbook)

    return orderbooks


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def create_test_session(provider: QuestDBProvider, session_id: str, symbol: str) -> bool:
    """Create a data collection session in QuestDB."""
    try:
        await provider.initialize()

        # Check if table exists
        try:
            check_query = "SELECT COUNT(*) FROM data_collection_sessions LIMIT 1"
            await provider.pg_pool.fetchval(check_query)
        except Exception:
            # Table might not exist, try to create it
            print("  Warning: data_collection_sessions table may not exist")
            print("  Skipping session record creation (data will still be inserted)")
            return True

        # Create session record
        query = """
        INSERT INTO data_collection_sessions (
            session_id, status, symbols, data_types,
            start_time, exchange, notes, created_at, updated_at, is_deleted
        ) VALUES (
            $1, 'completed', $2, $3,
            NOW(), 'test', 'Pump/dump test data session', NOW(), NOW(), false
        )
        """

        await provider.pg_pool.execute(
            query,
            session_id,
            f'["{symbol}"]',
            '["prices", "orderbook"]'
        )

        print(f"  Created session: {session_id}")
        return True

    except Exception as e:
        print(f"  Error creating session (non-critical): {e}")
        return True  # Continue anyway - data insertion is what matters


async def save_tick_data(provider: QuestDBProvider, ticks: List[Dict[str, Any]]) -> int:
    """Save tick price data to QuestDB using ILP."""
    try:
        inserted = await provider.insert_tick_prices_batch(ticks)
        return inserted
    except Exception as e:
        print(f"  Error saving tick data: {e}")
        return 0


async def save_orderbook_data(provider: QuestDBProvider, orderbooks: List[Dict[str, Any]]) -> int:
    """Save order book data to QuestDB using ILP."""
    try:
        inserted = await provider.insert_orderbook_snapshots_batch(orderbooks)
        return inserted
    except Exception as e:
        print(f"  Error saving orderbook data: {e}")
        return 0


async def update_session_stats(
    provider: QuestDBProvider,
    session_id: str,
    prices_count: int,
    orderbook_count: int,
    duration_seconds: int
) -> bool:
    """Update session with final statistics."""
    try:
        query = """
        UPDATE data_collection_sessions SET
            end_time = NOW(),
            duration_seconds = $1,
            records_collected = $2,
            prices_count = $3,
            orderbook_count = $4,
            status = 'completed',
            updated_at = NOW()
        WHERE session_id = $5
        """

        await provider.pg_pool.execute(
            query,
            duration_seconds,
            prices_count + orderbook_count,
            prices_count,
            orderbook_count,
            session_id
        )

        return True

    except Exception as e:
        print(f"  Error updating session stats: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point for test data generation."""
    print("\n" + "=" * 70)
    print("PUMP/DUMP TEST DATA GENERATOR")
    print("=" * 70)

    print(f"\nConfiguration:")
    print(f"  Symbol: {TEST_SYMBOL}")
    print(f"  Session ID: {SESSION_ID}")
    print(f"  Duration: {DURATION_SECONDS} seconds ({DURATION_SECONDS // 60} minutes)")
    print(f"  Tick interval: {TICK_INTERVAL_SECONDS} seconds")
    print(f"  Expected ticks: {DURATION_SECONDS // TICK_INTERVAL_SECONDS}")
    print(f"  Patterns: {len(PATTERNS)}")

    for i, p in enumerate(PATTERNS, 1):
        start_min = (p["start_pct"] / 100) * (DURATION_SECONDS / 60)
        print(f"    Pattern {i}: starts at {start_min:.1f}min, "
              f"pump +{p['pump_magnitude']*100:.0f}%, "
              f"dump -{p['dump_magnitude']*100:.0f}%")

    # Connect to QuestDB
    print("\n[1/5] Connecting to QuestDB...")
    provider = QuestDBProvider()

    try:
        await provider.initialize()
        print("  Connected successfully!")

        # Create session
        print("\n[2/5] Creating test session...")
        if not await create_test_session(provider, SESSION_ID, TEST_SYMBOL):
            print("  Failed to create session!")
            return 1

        # Generate tick data
        print("\n[3/5] Generating tick data...")
        ticks = generate_tick_data(
            TEST_SYMBOL, SESSION_ID,
            DURATION_SECONDS, TICK_INTERVAL_SECONDS,
            BASE_PRICE, PATTERNS
        )
        print(f"  Generated {len(ticks)} ticks")

        # Analyze generated data
        prices = [t["price"] for t in ticks]
        print(f"  Price range: {min(prices):.4f} - {max(prices):.4f}")
        print(f"  Price change: {((max(prices) - min(prices)) / min(prices) * 100):.1f}%")

        # Generate orderbook data
        print("\n[4/5] Generating orderbook data...")
        orderbooks = generate_orderbook_data(TEST_SYMBOL, SESSION_ID, ticks)
        print(f"  Generated {len(orderbooks)} orderbook snapshots")

        # Save to database
        print("\n[5/5] Saving to QuestDB...")

        # Save in batches to avoid memory issues
        batch_size = 500

        print("  Saving tick prices...")
        total_ticks = 0
        for i in range(0, len(ticks), batch_size):
            batch = ticks[i:i+batch_size]
            inserted = await save_tick_data(provider, batch)
            total_ticks += inserted
            if (i + batch_size) % 1000 == 0:
                print(f"    Saved {total_ticks} ticks...")
        print(f"  Total ticks saved: {total_ticks}")

        print("  Saving orderbook snapshots...")
        total_orderbooks = 0
        for i in range(0, len(orderbooks), batch_size):
            batch = orderbooks[i:i+batch_size]
            inserted = await save_orderbook_data(provider, batch)
            total_orderbooks += inserted
        print(f"  Total orderbooks saved: {total_orderbooks}")

        # Update session stats
        await update_session_stats(
            provider, SESSION_ID,
            total_ticks, total_orderbooks,
            DURATION_SECONDS
        )

        # Summary
        print("\n" + "=" * 70)
        print("DATA GENERATION COMPLETE")
        print("=" * 70)
        print(f"\nSession ID: {SESSION_ID}")
        print(f"Symbol: {TEST_SYMBOL}")
        print(f"Records:")
        print(f"  - Tick prices: {total_ticks}")
        print(f"  - Orderbook snapshots: {total_orderbooks}")
        print(f"  - Total: {total_ticks + total_orderbooks}")

        print("\nPump/Dump Patterns:")
        for i, p in enumerate(PATTERNS, 1):
            start_min = (p["start_pct"] / 100) * (DURATION_SECONDS / 60)
            print(f"  Pattern {i}:")
            print(f"    - Starts at: {start_min:.1f} minutes")
            print(f"    - Pump: +{p['pump_magnitude']*100:.0f}%")
            print(f"    - Dump: -{p['dump_magnitude']*100:.0f}%")
            print(f"    - Volume surge: {p['volume_surge']}x")

        print("\nNext steps:")
        print("  1. Run backtest on this session using the Strategy Builder")
        print("  2. Test indicator calculations (price_velocity, volume_surge)")
        print("  3. Verify signal generation at pump/dump points")
        print(f"\nQuery in QuestDB Web UI (http://localhost:9000):")
        print(f"  SELECT * FROM tick_prices WHERE session_id = '{SESSION_ID}' LIMIT 100;")

        return 0

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await provider.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
