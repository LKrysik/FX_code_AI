"""
Backtest Diagnostic Script
===========================
Diagnozuje cały łańcuch backtestingu:
1. Czy dane są w QuestDB?
2. Czy EventBus działa?
3. Czy StreamingIndicatorEngine subskrybuje?
4. Czy StrategyManager subskrybuje?
5. Czy BacktestOrderManager subskrybuje?
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.data.questdb_data_provider import QuestDBDataProvider
from src.data_feed.questdb_provider import QuestDBProvider
from src.infrastructure.config.settings import AppSettings


async def main():
    print("=" * 60)
    print("BACKTEST DIAGNOSTIC REPORT")
    print("=" * 60)

    # Create proper logger with config
    settings = AppSettings()
    logger = StructuredLogger("diagnostic", settings.logging)
    event_bus = EventBus()  # No arguments needed

    # Track what events are published/received
    events_log = {
        "market.price_update": {"published": 0, "received": 0},
        "indicator.updated": {"published": 0, "received": 0},
        "signal_generated": {"published": 0, "received": 0},
        "order.created": {"published": 0, "received": 0},
    }

    # Create test subscribers
    async def on_market_price_update(data):
        events_log["market.price_update"]["received"] += 1

    async def on_indicator_updated(data):
        events_log["indicator.updated"]["received"] += 1

    async def on_signal_generated(data):
        events_log["signal_generated"]["received"] += 1
        print(f"  📢 SIGNAL GENERATED: {data}")

    async def on_order_created(data):
        events_log["order.created"]["received"] += 1
        print(f"  📦 ORDER CREATED: {data}")

    # Subscribe to all events for monitoring
    await event_bus.subscribe("market.price_update", on_market_price_update)
    await event_bus.subscribe("indicator.updated", on_indicator_updated)
    await event_bus.subscribe("signal_generated", on_signal_generated)
    await event_bus.subscribe("order.created", on_order_created)

    print("\n[1] CHECKING QUESTDB DATA...")
    print("-" * 40)

    try:
        questdb_provider = QuestDBProvider(
            ilp_host='127.0.0.1',
            ilp_port=9009,
            pg_host='127.0.0.1',
            pg_port=8812
        )
        db_provider = QuestDBDataProvider(questdb_provider, logger)

        # Get sessions
        sessions = await db_provider.get_data_collection_sessions()
        print(f"  ✅ Found {len(sessions)} data collection sessions")

        if sessions:
            latest = sessions[0]
            session_id = latest.get("session_id", "unknown")
            print(f"  📊 Latest session: {session_id}")
            print(f"     Status: {latest.get('status', 'unknown')}")
            print(f"     Records: {latest.get('records_collected', 0)}")

            # Check tick data
            tick_data = await questdb_provider.query(
                f"SELECT COUNT(*) as cnt FROM tick_prices WHERE session_id = '{session_id}'"
            )
            tick_count = tick_data[0]["cnt"] if tick_data else 0
            print(f"  📈 Tick data count: {tick_count}")

            if tick_count > 0:
                # Get sample data
                sample = await questdb_provider.query(
                    f"SELECT symbol, price, volume, timestamp FROM tick_prices "
                    f"WHERE session_id = '{session_id}' LIMIT 3"
                )
                print(f"  📋 Sample data:")
                for row in sample:
                    print(f"     {row['symbol']}: price={row['price']:.6f}, vol={row['volume']:.2f}")
        else:
            print("  ⚠️ NO DATA COLLECTION SESSIONS FOUND!")
            print("     Run data collection first to get historical data.")
            return

    except Exception as e:
        print(f"  ❌ QuestDB Error: {e}")
        return

    print("\n[2] CHECKING EVENTBUS...")
    print("-" * 40)

    # Test EventBus
    test_received = {"count": 0}

    async def test_handler(data):
        test_received["count"] += 1

    await event_bus.subscribe("test_event", test_handler)
    await event_bus.publish("test_event", {"test": True})
    await asyncio.sleep(0.1)

    if test_received["count"] > 0:
        print(f"  ✅ EventBus works! Test event received.")
    else:
        print(f"  ❌ EventBus NOT WORKING! Events not delivered.")
        return

    print("\n[3] CHECKING STREAMING INDICATOR ENGINE...")
    print("-" * 40)

    try:
        from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine

        # Try to create engine - it needs Container to be properly configured
        from src.infrastructure.container import Container

        container = Container(event_bus, logger)
        await container.initialize()

        indicator_engine = await container.create_streaming_indicator_engine()

        if indicator_engine:
            print(f"  ✅ StreamingIndicatorEngine created")

            # Check if started
            await indicator_engine.start()
            print(f"  ✅ StreamingIndicatorEngine.start() called")

            # Check subscriptions on EventBus
            subscriptions = event_bus.get_subscriber_count("market.price_update")
            print(f"  📡 market.price_update subscribers: {subscriptions}")

        else:
            print(f"  ❌ StreamingIndicatorEngine is None!")

    except Exception as e:
        print(f"  ❌ StreamingIndicatorEngine Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n[4] CHECKING STRATEGY MANAGER...")
    print("-" * 40)

    try:
        strategy_manager = await container.create_strategy_manager()

        if strategy_manager:
            print(f"  ✅ StrategyManager created")

            # Check if started
            await strategy_manager.start()
            print(f"  ✅ StrategyManager.start() called")

            # Check subscriptions
            subscriptions = event_bus.get_subscriber_count("indicator.updated")
            print(f"  📡 indicator.updated subscribers: {subscriptions}")

            # List active strategies
            strategies = await strategy_manager.list_strategies()
            print(f"  📋 Active strategies: {len(strategies)}")
            for s in strategies[:3]:  # Show first 3
                print(f"     - {s.get('name', s.get('strategy_name', 'unknown'))}")

        else:
            print(f"  ❌ StrategyManager is None!")

    except Exception as e:
        print(f"  ❌ StrategyManager Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n[5] CHECKING BACKTEST ORDER MANAGER...")
    print("-" * 40)

    try:
        from src.domain.services.backtest_order_manager import BacktestOrderManager

        order_manager = await container.create_backtest_order_manager()

        if order_manager:
            print(f"  ✅ BacktestOrderManager created")

            await order_manager.start()
            print(f"  ✅ BacktestOrderManager.start() called")

            # Check subscriptions
            subscriptions = event_bus.get_subscriber_count("signal_generated")
            print(f"  📡 signal_generated subscribers: {subscriptions}")

        else:
            print(f"  ❌ BacktestOrderManager is None!")

    except Exception as e:
        print(f"  ❌ BacktestOrderManager Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n[6] SIMULATING BACKTEST DATA FLOW...")
    print("-" * 40)

    # Publish a fake market.price_update and see what happens
    print("  Publishing test market.price_update...")

    await event_bus.publish("market.price_update", {
        "symbol": "TEST_USDT",
        "price": 100.0,
        "volume": 1000.0,
        "timestamp": 1234567890.123
    })

    await asyncio.sleep(0.5)  # Wait for event propagation

    print(f"\n  Events received after test:")
    print(f"    market.price_update: {events_log['market.price_update']['received']}")
    print(f"    indicator.updated: {events_log['indicator.updated']['received']}")
    print(f"    signal_generated: {events_log['signal_generated']['received']}")
    print(f"    order.created: {events_log['order.created']['received']}")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    issues = []

    if events_log['indicator.updated']['received'] == 0:
        issues.append("StreamingIndicatorEngine NOT publishing indicator.updated events")

    if events_log['signal_generated']['received'] == 0:
        issues.append("StrategyManager NOT publishing signal_generated events")

    if events_log['order.created']['received'] == 0:
        issues.append("BacktestOrderManager NOT publishing order.created events")

    if issues:
        print("\n⚠️ ISSUES FOUND:")
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("\n✅ All components working correctly!")

    # Cleanup
    try:
        if 'order_manager' in dir() and order_manager:
            await order_manager.stop()
        if 'strategy_manager' in dir() and strategy_manager:
            await strategy_manager.shutdown()
        if 'indicator_engine' in dir() and indicator_engine:
            await indicator_engine.shutdown()
        await container.cleanup()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
