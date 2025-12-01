"""Test strategy deserialization from QuestDB JSON"""

import asyncio
import asyncpg
import json
import sys
sys.path.insert(0, ".")

from src.domain.services.strategy_manager import Strategy, Condition, ConditionGroup

async def test_deserialization():
    """Test if strategies are being deserialized correctly"""

    # Connect to QuestDB
    pool = await asyncpg.create_pool(
        host='localhost',
        port=8812,
        user='admin',
        password='quest',
        database='qdb'
    )

    async with pool.acquire() as conn:
        # Get a strategy with conditions
        rows = await conn.fetch("""
            SELECT strategy_name, direction, enabled, strategy_json
            FROM strategies
            WHERE is_deleted = false
            AND strategy_json IS NOT NULL
            LIMIT 3
        """)

        for row in rows:
            strategy_name = row['strategy_name']
            direction = row['direction']
            enabled = row['enabled']
            strategy_json = row['strategy_json']

            print(f"\n{'='*60}")
            print(f"Strategy: {strategy_name}")
            print(f"Direction: {direction}")
            print(f"Enabled: {enabled}")
            print(f"{'='*60}")

            # Parse JSON
            config = json.loads(strategy_json)

            # Show raw JSON structure
            print(f"\nRaw JSON keys: {list(config.keys())}")

            # Check for s1_signal
            if "s1_signal" in config:
                s1 = config["s1_signal"]
                print(f"\ns1_signal section: {json.dumps(s1, indent=2)[:500]}")

            if "signal_detection" in config:
                sd = config["signal_detection"]
                print(f"\nsignal_detection section: {json.dumps(sd, indent=2)[:500]}")

            # Now test deserialization
            strategy = _strategy_from_json(strategy_json, strategy_name, direction, enabled)

            print(f"\n--- After Deserialization ---")
            print(f"signal_detection.conditions: {len(strategy.signal_detection.conditions)}")
            for c in strategy.signal_detection.conditions:
                print(f"  - {c.name}: type={c.condition_type}, op={c.operator}, value={c.value}")

            print(f"signal_cancellation.conditions: {len(strategy.signal_cancellation.conditions)}")
            for c in strategy.signal_cancellation.conditions:
                print(f"  - {c.name}: type={c.condition_type}, op={c.operator}, value={c.value}")

            print(f"entry_conditions.conditions: {len(strategy.entry_conditions.conditions)}")
            for c in strategy.entry_conditions.conditions:
                print(f"  - {c.name}: type={c.condition_type}, op={c.operator}, value={c.value}")

    await pool.close()

def _strategy_from_json(strategy_json: str, strategy_name: str, direction: str, enabled: bool) -> Strategy:
    """Copy of StrategyManager._strategy_from_json for testing"""
    from typing import List, Dict, Any

    config = json.loads(strategy_json)

    # Create strategy with metadata
    strategy = Strategy(
        strategy_name=strategy_name,
        enabled=enabled,
        direction=direction,
        global_limits=config.get("global_limits", {})
    )

    def deserialize_conditions(condition_list: List[Dict[str, Any]]) -> List[Condition]:
        conditions = []
        for c in condition_list:
            # Detect schema version by checking for 'id' or 'name' field
            if "id" in c and "indicatorId" in c:
                # New 5-section schema format
                conditions.append(Condition(
                    name=c.get("id", c.get("indicatorId", "unknown")),
                    condition_type=c.get("indicatorId", "unknown"),
                    operator=c.get("operator", "gte"),
                    value=c.get("value", 0),
                    description=c.get("description", "")
                ))
            else:
                # Old schema format
                conditions.append(Condition(
                    name=c.get("name", "unknown"),
                    condition_type=c.get("condition_type", "unknown"),
                    operator=c.get("operator", "gte"),
                    value=c.get("value", 0),
                    description=c.get("description", "")
                ))
        return conditions

    # S1: Signal detection
    signal_section = config.get("s1_signal") or config.get("signal_detection")
    if signal_section:
        strategy.signal_detection.conditions = deserialize_conditions(
            signal_section.get("conditions", [])
        )

    # O1: Signal cancellation
    cancel_section = config.get("o1_cancel") or config.get("signal_cancellation")
    if cancel_section:
        strategy.signal_cancellation.conditions = deserialize_conditions(
            cancel_section.get("conditions", [])
        )

    # Z1: Entry conditions
    entry_section = config.get("z1_entry") or config.get("entry_conditions")
    if entry_section:
        strategy.entry_conditions.conditions = deserialize_conditions(
            entry_section.get("conditions", [])
        )

    # ZE1: Close order detection
    close_section = config.get("ze1_close") or config.get("close_order_detection")
    if close_section:
        strategy.close_order_detection.conditions = deserialize_conditions(
            close_section.get("conditions", [])
        )

    # E1: Emergency exit (same name in both schemas)
    if "emergency_exit" in config:
        strategy.emergency_exit.conditions = deserialize_conditions(
            config["emergency_exit"].get("conditions", [])
        )

    return strategy

if __name__ == "__main__":
    asyncio.run(test_deserialization())
