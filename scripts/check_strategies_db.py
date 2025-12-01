"""Check strategies in QuestDB - diagnose why no strategies may be loading."""

import asyncio
import asyncpg
import json
import sys
sys.path.insert(0, ".")


async def check_strategies():
    """Check what strategies exist in QuestDB."""

    print("=" * 70)
    print("QUESTDB STRATEGY DIAGNOSTIC")
    print("=" * 70)

    # Connect to QuestDB
    try:
        pool = await asyncpg.create_pool(
            host='localhost',
            port=8812,
            user='admin',
            password='quest',
            database='qdb'
        )
    except Exception as e:
        print(f"\n[ERROR] Could not connect to QuestDB: {e}")
        print("Make sure QuestDB is running on port 8812")
        return

    async with pool.acquire() as conn:
        # Check if strategies table exists
        print("\n[1] Checking strategies table...")
        try:
            rows = await conn.fetch("SELECT * FROM strategies LIMIT 10")
            print(f"    Found {len(rows)} strategies in first 10 rows")
        except Exception as e:
            print(f"    [ERROR] Could not query strategies: {e}")
            await pool.close()
            return

        # Check all strategies status
        print("\n[2] Strategy status breakdown:")
        all_rows = await conn.fetch("""
            SELECT
                strategy_name,
                enabled,
                is_deleted,
                direction,
                LENGTH(strategy_json) as json_length
            FROM strategies
        """)

        for row in all_rows:
            print(f"\n    - {row['strategy_name']}:")
            print(f"        enabled: {row['enabled']}")
            print(f"        is_deleted: {row['is_deleted']}")
            print(f"        direction: {row['direction']}")
            print(f"        json_length: {row['json_length']}")

        # Check the FIXED query that load_strategies_from_db uses
        print("\n[3] Testing FIXED load_strategies_from_db query...")
        enabled_rows = await conn.fetch("""
            SELECT strategy_name, direction, enabled, strategy_json
            FROM strategies
            WHERE enabled = true
            AND (is_deleted = false OR is_deleted IS NULL)
            ORDER BY created_at DESC
        """)
        print(f"    Query returned {len(enabled_rows)} strategies with enabled=true AND not deleted")

        for row in enabled_rows:
            print(f"    - {row['strategy_name']}: enabled={row['enabled']}, direction={row['direction']}")

        # Check strategies that aren't deleted
        print("\n[4] Checking non-deleted strategies...")
        non_deleted_rows = await conn.fetch("""
            SELECT strategy_name, enabled, is_deleted
            FROM strategies
            WHERE is_deleted = false OR is_deleted IS NULL
        """)
        print(f"    Found {len(non_deleted_rows)} non-deleted strategies")

        for row in non_deleted_rows:
            print(f"    - {row['strategy_name']}: enabled={row['enabled']}")

        # Check strategy_json structure for ALL enabled, non-deleted strategies
        print("\n[5] Checking signal detection conditions for each enabled strategy...")
        strategies_with_conditions = 0
        for row in enabled_rows:
            strategy_name = row['strategy_name']
            strategy_json = row.get('strategy_json', '{}')
            try:
                config = json.loads(strategy_json)

                # Check for signal_detection conditions
                signal_section = config.get("s1_signal") or config.get("signal_detection")
                if signal_section:
                    conditions = signal_section.get("conditions", [])
                    condition_count = len(conditions)
                    if condition_count > 0:
                        strategies_with_conditions += 1
                        print(f"\n    [OK] {strategy_name}: {condition_count} conditions")
                        for c in conditions[:2]:  # First 2
                            indicator_id = c.get('indicatorId', c.get('condition_type', '?'))
                            operator = c.get('operator', '?')
                            value = c.get('value', '?')
                            print(f"        - {indicator_id} {operator} {value}")
                    else:
                        print(f"\n    [WARN] {strategy_name}: 0 conditions (empty array)")
                else:
                    print(f"\n    [WARN] {strategy_name}: No signal_detection section!")
            except json.JSONDecodeError as e:
                print(f"\n    [ERROR] {strategy_name}: Invalid JSON - {e}")

        print(f"\n[SUMMARY] {strategies_with_conditions}/{len(enabled_rows)} strategies have signal detection conditions")

    await pool.close()
    print("\n[DONE] QuestDB check complete")


if __name__ == "__main__":
    asyncio.run(check_strategies())
