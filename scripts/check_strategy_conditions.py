"""
Check E2E Pump Test strategy S1 conditions
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def check():
    from src.infrastructure.persistence.questdb_provider import QuestDBProvider
    from src.infrastructure.config.settings import AppSettings
    import json

    settings = AppSettings()
    provider = QuestDBProvider(settings.questdb)
    await provider.connect()

    print("\n[1] Fetching E2E Pump Test strategy...")
    rows = await provider.fetch(
        "SELECT strategy_name, signal_detection, signal_cancellation, entry_conditions FROM strategies WHERE strategy_name = 'E2E Pump Test' LIMIT 1"
    )

    for row in rows:
        print(f"\nStrategy: {row[0]}")
        print(f"\n[S1] Signal Detection:")
        if row[1]:
            sd = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            print(json.dumps(sd, indent=2))

        print(f"\n[O1] Signal Cancellation:")
        if row[2]:
            sc = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            print(json.dumps(sc, indent=2))

        print(f"\n[Z1] Entry Conditions:")
        if row[3]:
            ec = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            print(json.dumps(ec, indent=2))

    print("\n[2] Checking PUMP_TEST_USDT tick price range...")
    rows = await provider.fetch(
        "SELECT MIN(price), MAX(price), AVG(price), COUNT(*) FROM tick_prices WHERE symbol = 'PUMP_TEST_USDT' AND session_id = 'pump_test_20251202_220333'"
    )
    for row in rows:
        print(f"  Min price: {row[0]}")
        print(f"  Max price: {row[1]}")
        print(f"  Avg price: {row[2]}")
        print(f"  Records: {row[3]}")
        if row[0] and row[1]:
            price_change_pct = (row[1] - row[0]) / row[0] * 100
            print(f"  Price change range: {price_change_pct:.2f}%")

    await provider.disconnect()
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(check())
