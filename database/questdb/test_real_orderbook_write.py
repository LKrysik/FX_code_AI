"""
Test orderbook writes with realistic data scenarios to reproduce the bug.

This test simulates actual data collection scenarios that might cause
"Sender is closed" errors, including:
1. Invalid float values (NaN, infinity)
2. Missing fields
3. Empty bids/asks arrays
4. Concurrent writes
5. High-frequency batch writes
"""

import asyncio
import time
import math
from typing import List, Dict, Any
from src.data.data_collection_persistence_service import DataCollectionPersistenceService
from src.data_feed.questdb_provider import QuestDBProvider


async def test_scenario_1_valid_data():
    """Test 1: Valid data (should work - baseline)"""
    print("\n" + "=" * 80)
    print("TEST 1: Valid orderbook data (baseline)")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    # Test direct QuestDB write (skip session layer)
    batch = [{
        'session_id': 'test_valid_data',
        'symbol': 'BTC_USDT',
        'timestamp': time.time(),
        'bid_price_1': 50000.0,
        'bid_qty_1': 1.0,
        'bid_price_2': 49999.0,
        'bid_qty_2': 2.0,
        'bid_price_3': 49998.0,
        'bid_qty_3': 3.0,
        'ask_price_1': 50001.0,
        'ask_qty_1': 1.0,
        'ask_price_2': 50002.0,
        'ask_qty_2': 2.0,
        'ask_price_3': 50003.0,
        'ask_qty_3': 3.0,
    }]

    try:
        count = await db_provider.insert_orderbook_snapshots_batch(batch)
        print(f"✅ Valid data: {count} records written")
        return True
    except Exception as e:
        print(f"❌ Valid data FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_provider.close()


async def test_scenario_2_empty_bids_asks():
    """Test 2: Empty bids/asks arrays (edge case)"""
    print("\n" + "=" * 80)
    print("TEST 2: Empty bids/asks arrays")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    # All zeros (simulates empty orderbook)
    batch = [{
        'session_id': 'test_empty',
        'symbol': 'BTC_USDT',
        'timestamp': time.time(),
        'bid_price_1': 0.0,
        'bid_qty_1': 0.0,
        'bid_price_2': 0.0,
        'bid_qty_2': 0.0,
        'bid_price_3': 0.0,
        'bid_qty_3': 0.0,
        'ask_price_1': 0.0,
        'ask_qty_1': 0.0,
        'ask_price_2': 0.0,
        'ask_qty_2': 0.0,
        'ask_price_3': 0.0,
        'ask_qty_3': 0.0,
    }]

    try:
        count = await db_provider.insert_orderbook_snapshots_batch(batch)
        print(f"✅ Empty bids/asks: {count} records written (all zeros)")
        return True
    except Exception as e:
        print(f"❌ Empty bids/asks FAILED: {e}")
        print("   This might be the issue if MEXC sends empty orderbooks!")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_provider.close()


async def test_scenario_3_invalid_floats():
    """Test 3: Invalid float values (NaN, infinity)"""
    print("\n" + "=" * 80)
    print("TEST 3: Invalid float values (NaN, infinity)")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    # Test NaN
    batch_nan = [{
        'session_id': 'test_nan',
        'symbol': 'BTC_USDT',
        'timestamp': time.time(),
        'bid_price_1': float('nan'),  # NaN!
        'bid_qty_1': 1.0,
        'bid_price_2': 49999.0,
        'bid_qty_2': 2.0,
        'bid_price_3': 0.0,
        'bid_qty_3': 0.0,
        'ask_price_1': 50001.0,
        'ask_qty_1': 1.0,
        'ask_price_2': 0.0,
        'ask_qty_2': 0.0,
        'ask_price_3': 0.0,
        'ask_qty_3': 0.0,
    }]

    try:
        count = await db_provider.insert_orderbook_snapshots_batch(batch_nan)
        print(f"⚠️  NaN value: {count} records written (QuestDB accepted NaN?)")
        nan_ok = True
    except Exception as e:
        print(f"❌ NaN value FAILED: {e}")
        print("   QuestDB rejects NaN values!")
        import traceback
        traceback.print_exc()
        nan_ok = False

    # Test Infinity
    batch_inf = [{
        'session_id': 'test_inf',
        'symbol': 'BTC_USDT',
        'timestamp': time.time() + 1,
        'bid_price_1': float('inf'),  # Infinity!
        'bid_qty_1': 1.0,
        'bid_price_2': 49999.0,
        'bid_qty_2': 2.0,
        'bid_price_3': 0.0,
        'bid_qty_3': 0.0,
        'ask_price_1': 50001.0,
        'ask_qty_1': 1.0,
        'ask_price_2': 0.0,
        'ask_qty_2': 0.0,
        'ask_price_3': 0.0,
        'ask_qty_3': 0.0,
    }]

    try:
        count = await db_provider.insert_orderbook_snapshots_batch(batch_inf)
        print(f"⚠️  Infinity value: {count} records written (QuestDB accepted infinity?)")
        inf_ok = True
    except Exception as e:
        print(f"❌ Infinity value FAILED: {e}")
        print("   QuestDB rejects infinity values!")
        import traceback
        traceback.print_exc()
        inf_ok = False

    await db_provider.close()
    return nan_ok and inf_ok


async def test_scenario_4_string_values():
    """Test 4: String values instead of floats"""
    print("\n" + "=" * 80)
    print("TEST 4: String values converted to floats")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    # MEXC sends strings - test float() conversion
    try:
        batch = [{
            'session_id': 'test_strings',
            'symbol': 'BTC_USDT',
            'timestamp': time.time(),
            'bid_price_1': float("50000.00"),  # String converted
            'bid_qty_1': float("1.0"),
            'bid_price_2': float("49999.50"),
            'bid_qty_2': float("2.0"),
            'bid_price_3': 0.0,
            'bid_qty_3': 0.0,
            'ask_price_1': float("50001.00"),
            'ask_qty_1': float("1.0"),
            'ask_price_2': 0.0,
            'ask_qty_2': 0.0,
            'ask_price_3': 0.0,
            'ask_qty_3': 0.0,
        }]

        count = await db_provider.insert_orderbook_snapshots_batch(batch)
        print(f"✅ String values: {count} records written (float() conversion works)")
        return True
    except Exception as e:
        print(f"❌ String values FAILED: {e}")
        print("   float() conversion failed on MEXC string format!")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_provider.close()


async def test_scenario_5_high_frequency():
    """Test 5: High-frequency batch writes (stress test)"""
    print("\n" + "=" * 80)
    print("TEST 5: High-frequency batch writes (10 batches x 50 records)")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    try:
        for batch_num in range(10):
            batch = []
            base_time = time.time()
            for i in range(50):
                batch.append({
                    'session_id': 'test_high_freq',
                    'symbol': 'BTC_USDT',
                    'timestamp': base_time + i * 0.001,  # 1ms apart
                    'bid_price_1': 50000.0 + i,
                    'bid_qty_1': 1.0,
                    'bid_price_2': 49999.0,
                    'bid_qty_2': 2.0,
                    'bid_price_3': 0.0,
                    'bid_qty_3': 0.0,
                    'ask_price_1': 50001.0,
                    'ask_qty_1': 1.0,
                    'ask_price_2': 0.0,
                    'ask_qty_2': 0.0,
                    'ask_price_3': 0.0,
                    'ask_qty_3': 0.0,
                })

            count = await db_provider.insert_orderbook_snapshots_batch(batch)
            print(f"  Batch {batch_num + 1}/10: {count} records written")

        print(f"✅ High-frequency writes: All batches succeeded")
        return True
    except Exception as e:
        print(f"❌ High-frequency writes FAILED at batch {batch_num + 1}: {e}")
        print("   Sender pool exhaustion or connection issue!")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_provider.close()


async def test_scenario_6_missing_fields():
    """Test 6: Missing optional fields (all zeros)"""
    print("\n" + "=" * 80)
    print("TEST 6: Incomplete orderbook (only level 1)")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    # Only level 1 data, rest zeros (simulates thin orderbook)
    batch = [{
        'session_id': 'test_incomplete',
        'symbol': 'BTC_USDT',
        'timestamp': time.time(),
        'bid_price_1': 50000.0,
        'bid_qty_1': 1.0,
        'bid_price_2': 0.0,  # Missing level 2
        'bid_qty_2': 0.0,
        'bid_price_3': 0.0,  # Missing level 3
        'bid_qty_3': 0.0,
        'ask_price_1': 50001.0,
        'ask_qty_1': 1.0,
        'ask_price_2': 0.0,  # Missing level 2
        'ask_qty_2': 0.0,
        'ask_price_3': 0.0,  # Missing level 3
        'ask_qty_3': 0.0,
    }]

    try:
        count = await db_provider.insert_orderbook_snapshots_batch(batch)
        print(f"✅ Incomplete orderbook: {count} records written (zeros for missing levels)")
        return True
    except Exception as e:
        print(f"❌ Incomplete orderbook FAILED: {e}")
        print("   Code doesn't handle partial orderbook!")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_provider.close()


async def run_all_tests():
    """Run all test scenarios"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "ORDERBOOK WRITE DIAGNOSTICS" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")

    results = {}

    results['valid_data'] = await test_scenario_1_valid_data()
    results['empty_arrays'] = await test_scenario_2_empty_bids_asks()
    results['invalid_floats'] = await test_scenario_3_invalid_floats()
    results['string_values'] = await test_scenario_4_string_values()
    results['high_frequency'] = await test_scenario_5_high_frequency()
    results['missing_fields'] = await test_scenario_6_missing_fields()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    failed_tests = [name for name, passed in results.items() if not passed]

    if failed_tests:
        print("\n⚠️  FAILED TESTS INDICATE ROOT CAUSE:")
        for test_name in failed_tests:
            if test_name == 'invalid_floats':
                print("   • MEXC might be sending NaN or Infinity values")
                print("     → Need to add validation/sanitization before write")
            elif test_name == 'string_values':
                print("   • float() conversion failing on MEXC string format")
                print("     → Check MEXC adapter data parsing")
            elif test_name == 'high_frequency':
                print("   • Sender pool exhaustion under load")
                print("     → Need to increase pool size or add rate limiting")
            elif test_name == 'empty_arrays':
                print("   • Empty orderbook handling issue")
                print("     → MEXC sends empty orderbooks during low liquidity")
            elif test_name == 'missing_fields':
                print("   • Data structure from MEXC doesn't match expected format")
                print("     → Check MEXC adapter orderbook transformation")
    else:
        print("\n✅ ALL TESTS PASSED")
        print("   Issue might be environmental (QuestDB config, network, etc.)")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
