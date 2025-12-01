"""Trace the signal flow during backtest to find where pipeline breaks."""

import asyncio
import asyncpg
import json
import sys
import time
sys.path.insert(0, ".")

from src.core.event_bus import EventBus


async def trace_signal_flow():
    """Connect to running server and trace signal flow."""

    print("=" * 70)
    print("SIGNAL FLOW TRACER - BACKTEST DIAGNOSTIC")
    print("=" * 70)

    # Connect to QuestDB to check current indicator state
    print("\n[1] Checking indicator variants in QuestDB...")
    try:
        pool = await asyncpg.create_pool(
            host='localhost',
            port=8812,
            user='admin',
            password='quest',
            database='qdb'
        )

        async with pool.acquire() as conn:
            # Check indicator variants for ARIA_USDT
            rows = await conn.fetch("""
                SELECT variant_id, indicator_type, symbol, session_id
                FROM indicator_variants
                WHERE symbol = 'ARIA_USDT'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            print(f"    Found {len(rows)} ARIA_USDT indicator variants in DB:")
            for row in rows:
                print(f"      - {row['variant_id']} ({row['indicator_type']}) session={row['session_id']}")

            # Check if there are any backtest sessions
            sessions = await conn.fetch("""
                SELECT session_id, symbols, status, start_time
                FROM data_collection_sessions
                WHERE status = 'completed'
                ORDER BY start_time DESC
                LIMIT 5
            """)

            print(f"\n    Recent completed sessions ({len(sessions)}):")
            for s in sessions:
                print(f"      - {s['session_id']}: {s['symbols']} ({s['status']})")

        await pool.close()
    except Exception as e:
        print(f"    [ERROR] Could not query QuestDB: {e}")

    # Now test with a manual event subscription
    print("\n[2] Testing EventBus indicator.updated subscription...")

    event_bus = EventBus()
    received_events = []

    async def on_indicator_update(event):
        received_events.append(event)
        if len(received_events) <= 5:
            print(f"    [EVENT] indicator.updated: {event}")

    # Subscribe
    await event_bus.subscribe("indicator.updated", on_indicator_update)
    print("    Subscribed to 'indicator.updated' events")

    # Publish a test event
    test_event = {
        "symbol": "TEST_USDT",
        "indicator": "TEST_INDICATOR",
        "indicator_type": "test_type",
        "value": 123.456,
        "timestamp": time.time()
    }

    await event_bus.publish("indicator.updated", test_event)
    await asyncio.sleep(0.1)  # Allow event to process

    if received_events:
        print(f"    [OK] EventBus working! Received {len(received_events)} events")
    else:
        print("    [ERROR] EventBus not receiving events!")

    # Check strategy manager subscription
    print("\n[3] Checking StrategyManager event subscription pattern...")

    # Read strategy_manager.py to find the subscription code
    from src.domain.services.strategy_manager import StrategyManager
    import inspect

    # Find _on_indicator_update method signature
    sig = inspect.signature(StrategyManager._on_indicator_update)
    print(f"    _on_indicator_update signature: {sig}")

    # Check if start() method subscribes to indicator.updated
    start_source = inspect.getsource(StrategyManager.start)
    if "indicator.updated" in start_source:
        print("    [OK] StrategyManager.start() subscribes to 'indicator.updated'")
    else:
        print("    [ERROR] StrategyManager.start() does NOT subscribe to 'indicator.updated'!")

    # Now check indicator engine
    print("\n[4] Checking StreamingIndicatorEngine _indicators_by_symbol...")

    from src.domain.services.streaming_indicator_engine.engine import StreamingIndicatorEngine

    # Check _track_indicator method
    track_source = inspect.getsource(StreamingIndicatorEngine._track_indicator)
    print(f"    _track_indicator populates _indicators_by_symbol: {'setdefault' in track_source}")

    # Check add_indicator_to_session
    add_source = inspect.getsource(StreamingIndicatorEngine.add_indicator_to_session)
    if "_track_indicator" in add_source:
        print("    [OK] add_indicator_to_session calls _track_indicator")
    else:
        print("    [ERROR] add_indicator_to_session does NOT call _track_indicator!")

    print("\n[5] Checking unified_trading_controller indicator registration...")

    from src.application.controllers.unified_trading_controller import UnifiedTradingController

    # Check _create_indicator_variants_for_strategy
    create_source = inspect.getsource(UnifiedTradingController._create_indicator_variants_for_strategy)

    if "add_indicator_to_session" in create_source:
        print("    [OK] _create_indicator_variants_for_strategy calls add_indicator_to_session")
    else:
        print("    [ERROR] add_indicator_to_session NOT called!")

    if "session_id" in create_source:
        print("    [OK] session_id parameter is used")
    else:
        print("    [ERROR] session_id parameter NOT used!")

    # Check _activate_strategies_for_session
    activate_source = inspect.getsource(UnifiedTradingController._activate_strategies_for_session)

    if "_create_indicator_variants_for_strategy" in activate_source:
        print("    [OK] _activate_strategies_for_session calls _create_indicator_variants_for_strategy")
    else:
        print("    [ERROR] _create_indicator_variants_for_strategy NOT called!")

    # Check start_backtest
    backtest_source = inspect.getsource(UnifiedTradingController.start_backtest)

    if "_activate_strategies_for_session" in backtest_source:
        print("    [OK] start_backtest calls _activate_strategies_for_session")
    else:
        print("    [ERROR] _activate_strategies_for_session NOT called in start_backtest!")

    print("\n[SUMMARY]")
    print("=" * 70)
    print("""
The code structure appears correct. Possible remaining issues:
1. _indicators_by_symbol might be empty if session_id is wrong/None
2. Circuit breaker might be blocking indicator calculations
3. Market data might not be reaching _on_market_data handler
4. StrategyManager might not be started (event subscription not active)

Next steps:
1. Add debug logging to _update_indicators_safe (print indicator_keys at line 1209)
2. Add debug logging to _on_indicator_update in StrategyManager
3. Verify StrategyManager.start() is called during backtest
    """)

    print("\n[DONE]")


if __name__ == "__main__":
    asyncio.run(trace_signal_flow())
