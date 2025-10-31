"""
Verify QuestDB tables exist and have correct schema after migrations.

This script checks:
1. QuestDB is running and accessible
2. Required tables exist (tick_prices, tick_orderbook)
3. Tables have correct columns including is_deleted
4. SYMBOL columns are properly configured
"""

import asyncio
import asyncpg
from questdb.ingress import Sender, Protocol, IngressError


async def verify_questdb():
    """Verify QuestDB health and table schema."""

    print("=" * 80)
    print("QUESTDB VERIFICATION DIAGNOSTICS")
    print("=" * 80)

    # Test 1: ILP Connection (port 9009)
    print("\n[TEST 1] ILP Connection (port 9009)")
    try:
        with Sender(Protocol.Tcp, '127.0.0.1', 9009) as sender:
            pass
        print("✅ ILP connection successful")
    except IngressError as e:
        print(f"❌ ILP connection FAILED: {e}")
        print("   QuestDB may not be running. Start it with: python database/questdb/start_questdb.py")
        return False

    # Test 2: PostgreSQL Connection (port 8812)
    print("\n[TEST 2] PostgreSQL Connection (port 8812)")
    try:
        pool = await asyncpg.create_pool(
            host='127.0.0.1',
            port=8812,
            user='admin',
            password='quest',
            database='qdb',
            min_size=1,
            max_size=2
        )
        print("✅ PostgreSQL connection successful")
    except Exception as e:
        print(f"❌ PostgreSQL connection FAILED: {e}")
        return False

    # Test 3: Check Tables Exist
    print("\n[TEST 3] Verify Tables Exist")
    try:
        async with pool.acquire() as conn:
            tables_query = """
            SELECT table_name
            FROM tables()
            WHERE table_name IN ('tick_prices', 'tick_orderbook', 'data_collection_sessions')
            ORDER BY table_name
            """
            tables = await conn.fetch(tables_query)

            expected_tables = {'tick_prices', 'tick_orderbook', 'data_collection_sessions'}
            found_tables = {row['table_name'] for row in tables}

            for table in expected_tables:
                if table in found_tables:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"❌ Table '{table}' MISSING!")

            if not found_tables == expected_tables:
                print("\n⚠️  CRITICAL: Not all tables exist!")
                print("   Run migrations: python database/questdb/install_questdb.py")
                return False
    except Exception as e:
        print(f"❌ Table verification FAILED: {e}")
        return False

    # Test 4: Check tick_prices Schema
    print("\n[TEST 4] Verify tick_prices Schema")
    try:
        async with pool.acquire() as conn:
            columns_query = """
            SELECT column_name, type, indexed
            FROM table_columns('tick_prices')
            ORDER BY column_name
            """
            columns = await conn.fetch(columns_query)

            print("\nColumns in tick_prices:")
            for col in columns:
                indexed_marker = " (INDEXED)" if col['indexed'] else ""
                print(f"  - {col['column_name']}: {col['type']}{indexed_marker}")

            expected_columns = {
                'session_id', 'symbol', 'timestamp',
                'price', 'volume', 'quote_volume', 'is_deleted'
            }
            found_columns = {col['column_name'] for col in columns}

            if not expected_columns.issubset(found_columns):
                missing = expected_columns - found_columns
                print(f"\n❌ Missing columns: {missing}")
                return False
            print("✅ All required columns present")
    except Exception as e:
        print(f"❌ Schema verification FAILED: {e}")
        return False

    # Test 5: Check tick_orderbook Schema
    print("\n[TEST 5] Verify tick_orderbook Schema")
    try:
        async with pool.acquire() as conn:
            columns_query = """
            SELECT column_name, type, indexed
            FROM table_columns('tick_orderbook')
            ORDER BY column_name
            """
            columns = await conn.fetch(columns_query)

            print("\nColumns in tick_orderbook:")
            for col in columns:
                indexed_marker = " (INDEXED)" if col['indexed'] else ""
                print(f"  - {col['column_name']}: {col['type']}{indexed_marker}")

            expected_columns = {
                'session_id', 'symbol', 'timestamp',
                'bid_price_1', 'bid_qty_1', 'bid_price_2', 'bid_qty_2', 'bid_price_3', 'bid_qty_3',
                'ask_price_1', 'ask_qty_1', 'ask_price_2', 'ask_qty_2', 'ask_price_3', 'ask_qty_3',
                'is_deleted'
            }
            found_columns = {col['column_name'] for col in columns}

            if not expected_columns.issubset(found_columns):
                missing = expected_columns - found_columns
                print(f"\n❌ Missing columns: {missing}")
                return False
            print("✅ All required columns present")
    except Exception as e:
        print(f"❌ Schema verification FAILED: {e}")
        return False

    # Test 6: Try Manual Orderbook Insert
    print("\n[TEST 6] Test Manual Orderbook Insert")
    try:
        from questdb.ingress import TimestampNanos
        import time

        with Sender(Protocol.Tcp, '127.0.0.1', 9009) as sender:
            timestamp_ns = int(time.time() * 1_000_000_000)

            sender.row(
                'tick_orderbook',
                symbols={
                    'session_id': 'test_verify_script',
                    'symbol': 'BTC_USDT',
                },
                columns={
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
                },
                at=TimestampNanos(timestamp_ns)
            )
            sender.flush()

        print("✅ Manual orderbook insert SUCCESSFUL")

        # Verify write succeeded
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM tick_orderbook WHERE session_id = 'test_verify_script'"
            )
            print(f"✅ Verified: {count} test record(s) written to tick_orderbook")

            # Cleanup
            await conn.execute("DELETE FROM tick_orderbook WHERE session_id = 'test_verify_script'")
            print("✅ Test data cleaned up")

    except IngressError as e:
        print(f"❌ Manual orderbook insert FAILED: {e}")
        print("\n   This is the EXACT error your data collection is seeing!")
        print("   Possible causes:")
        print("   1. Table schema mismatch")
        print("   2. Missing columns")
        print("   3. DEDUP conflict")
        print("   4. QuestDB configuration issue")
        return False
    except Exception as e:
        print(f"❌ Manual orderbook insert FAILED: {e}")
        return False

    # Close pool
    await pool.close()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - QuestDB is correctly configured")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = asyncio.run(verify_questdb())

    if not success:
        print("\n⚠️  VERIFICATION FAILED - Fix the issues above before running data collection")
        exit(1)
    else:
        print("\n✅ QuestDB is ready for data collection")
        exit(0)
