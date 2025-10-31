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

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    orderbook_data = [{
        'timestamp': time.time(),
        'bids': [[50000.0, 1.0], [49999.0, 2.0], [49998.0, 3.0]],
        'asks': [[50001.0, 1.0], [50002.0, 2.0], [50003.0, 3.0]]
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data
        )
        print(f"✅ Valid data: {count} records written")
        return True
    except Exception as e:
        print(f"❌ Valid data FAILED: {e}")
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

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    orderbook_data = [{
        'timestamp': time.time(),
        'bids': [],  # Empty!
        'asks': []   # Empty!
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data
        )
        print(f"✅ Empty bids/asks: {count} records written (all zeros)")
        return True
    except Exception as e:
        print(f"❌ Empty bids/asks FAILED: {e}")
        print("   This might be the issue if MEXC sends empty orderbooks!")
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

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    # Test NaN
    orderbook_data_nan = [{
        'timestamp': time.time(),
        'bids': [[float('nan'), 1.0], [49999.0, 2.0]],  # NaN price!
        'asks': [[50001.0, 1.0]]
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data_nan
        )
        print(f"⚠️  NaN value: {count} records written (QuestDB accepted NaN?)")
        nan_ok = True
    except Exception as e:
        print(f"❌ NaN value FAILED: {e}")
        print("   QuestDB rejects NaN values!")
        nan_ok = False

    # Test Infinity
    orderbook_data_inf = [{
        'timestamp': time.time() + 1,
        'bids': [[float('inf'), 1.0], [49999.0, 2.0]],  # Infinity price!
        'asks': [[50001.0, 1.0]]
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data_inf
        )
        print(f"⚠️  Infinity value: {count} records written (QuestDB accepted infinity?)")
        inf_ok = True
    except Exception as e:
        print(f"❌ Infinity value FAILED: {e}")
        print("   QuestDB rejects infinity values!")
        inf_ok = False

    await db_provider.close()
    return nan_ok and inf_ok


async def test_scenario_4_string_values():
    """Test 4: String values instead of floats"""
    print("\n" + "=" * 80)
    print("TEST 4: String values in bids/asks")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    # MEXC sends strings like "50000.00"
    orderbook_data = [{
        'timestamp': time.time(),
        'bids': [["50000.00", "1.0"], ["49999.50", "2.0"]],  # Strings!
        'asks': [["50001.00", "1.0"]]
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data
        )
        print(f"✅ String values: {count} records written (float() conversion works)")
        return True
    except Exception as e:
        print(f"❌ String values FAILED: {e}")
        print("   float() conversion failed on MEXC string format!")
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

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    try:
        for batch_num in range(10):
            orderbook_data = []
            for i in range(50):
                orderbook_data.append({
                    'timestamp': time.time() + i * 0.001,  # 1ms apart
                    'bids': [[50000.0 + i, 1.0], [49999.0, 2.0]],
                    'asks': [[50001.0, 1.0]]
                })

            count = await persistence.persist_orderbook_snapshots(
                session_id=session_id,
                symbol='BTC_USDT',
                orderbook_data=orderbook_data
            )
            print(f"  Batch {batch_num + 1}/10: {count} records written")

        print(f"✅ High-frequency writes: All batches succeeded")
        return True
    except Exception as e:
        print(f"❌ High-frequency writes FAILED at batch {batch_num + 1}: {e}")
        print("   Sender pool exhaustion or connection issue!")
        return False
    finally:
        await db_provider.close()


async def test_scenario_6_missing_fields():
    """Test 6: Missing required fields"""
    print("\n" + "=" * 80)
    print("TEST 6: Missing required fields")
    print("=" * 80)

    db_provider = QuestDBProvider()
    await db_provider.initialize()

    persistence = DataCollectionPersistenceService(db_provider=db_provider)
    session_id = await persistence.create_session(
        symbols=['BTC_USDT'],
        data_types=['orderbook'],
        collection_mode='live'
    )

    # Missing 'bids' and 'asks' keys
    orderbook_data = [{
        'timestamp': time.time(),
        # Missing bids and asks entirely!
    }]

    try:
        count = await persistence.persist_orderbook_snapshots(
            session_id=session_id,
            symbol='BTC_USDT',
            orderbook_data=orderbook_data
        )
        print(f"✅ Missing fields: {count} records written (defaults to empty arrays)")
        return True
    except Exception as e:
        print(f"❌ Missing fields FAILED: {e}")
        print("   Code doesn't handle missing bids/asks keys!")
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
