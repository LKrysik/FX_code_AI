"""
Quick check of QuestDB data for backtest session
"""
import asyncio
import asyncpg

async def check():
    pool = await asyncpg.create_pool(
        host='127.0.0.1', port=8812, user='admin',
        password='quest', database='qdb', min_size=1, max_size=2
    )

    print("\n[0] Listing all tables in QuestDB...")
    try:
        rows = await pool.fetch("SHOW TABLES")
        print(f"  Found {len(rows)} tables:")
        for r in rows:
            print(f"    - {r[0]}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[1] Checking tick_prices table...")
    try:
        rows = await pool.fetch("SELECT DISTINCT symbol FROM tick_prices LIMIT 20")
        print(f"  Found {len(rows)} distinct symbols:")
        for r in rows:
            print(f"    - {r[0]}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[2] Checking tick_prices columns...")
    try:
        row = await pool.fetchrow("SELECT * FROM tick_prices LIMIT 1")
        if row:
            print(f"  Columns: {list(row.keys())}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[3] Checking data_collection_sessions...")
    try:
        rows = await pool.fetch(
            "SELECT session_id, name, created_at FROM data_collection_sessions ORDER BY created_at DESC LIMIT 10"
        )
        print(f"  Recent sessions:")
        for r in rows:
            print(f"    - {r[0]}: {r[1]} ({r[2]})")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[4] Checking tick_prices for session_id column...")
    try:
        row = await pool.fetchrow("SELECT COUNT(*) FROM tick_prices")
        print(f"  Total tick_prices records: {row[0]}")
        rows = await pool.fetch("SELECT DISTINCT session_id FROM tick_prices LIMIT 10")
        print(f"  Distinct session_ids in tick_prices: {len(rows)}")
        for r in rows:
            print(f"    - {r[0]}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[5] Checking PUMP_TEST_USDT data...")
    try:
        rows = await pool.fetch("SELECT session_id, COUNT(*) as cnt FROM tick_prices WHERE symbol = 'PUMP_TEST_USDT' GROUP BY session_id")
        print(f"  Sessions with PUMP_TEST_USDT data:")
        for r in rows:
            print(f"    - {r[0]}: {r[1]} records")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[6] Checking BTC_USDT data...")
    try:
        rows = await pool.fetch("SELECT session_id, COUNT(*) as cnt FROM tick_prices WHERE symbol = 'BTC_USDT' GROUP BY session_id")
        print(f"  Sessions with BTC_USDT data:")
        for r in rows:
            print(f"    - {r[0]}: {r[1]} records")
    except Exception as e:
        print(f"  Error: {e}")

    await pool.close()
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(check())
