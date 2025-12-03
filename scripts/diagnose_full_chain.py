"""
Full Chain Diagnostic: Market Data -> Indicator -> Signal
==========================================================
This traces the complete chain in backtest to find where it breaks.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def diagnose():
    """Full chain diagnostic"""

    print("\n" + "="*70)
    print("  FULL CHAIN DIAGNOSTIC: market.price_update -> signal_generated")
    print("="*70)

    from src.core.event_bus import EventBus
    from unittest.mock import MagicMock
    from datetime import datetime

    event_bus = EventBus()

    # Track all events
    events_log = []

    async def log_event(topic, data):
        events_log.append({"topic": topic, "data": data, "time": datetime.now().isoformat()})
        print(f"  [EVENT] {topic}: {list(data.keys()) if isinstance(data, dict) else data}")

    # Subscribe to all relevant events
    for topic in ["market.price_update", "indicator.updated", "signal_generated"]:
        await event_bus.subscribe(topic, lambda d, t=topic: log_event(t, d))

    print("\n[1] EventBus subscriptions ready")

    # Create Strategy Manager
    print("\n[2] Creating StrategyManager...")
    from src.domain.services.strategy_manager import StrategyManager

    mock_logger = MagicMock()
    mock_risk = MagicMock()
    mock_risk.can_open_position_sync = MagicMock(return_value=MagicMock(can_proceed=True))
    mock_risk.use_budget = MagicMock(return_value=True)

    strategy_manager = StrategyManager(
        event_bus=event_bus,
        logger=mock_logger,
        risk_manager=mock_risk
    )
    await strategy_manager.start()
    print(f"  [OK] StrategyManager started")

    # Load strategies from DB
    print("\n[3] Loading strategies from DB...")
    import asyncpg
    pool = await asyncpg.create_pool(
        host='127.0.0.1', port=8812, user='admin',
        password='quest', database='qdb', min_size=1, max_size=2
    )
    strategy_manager.db_pool = pool
    count = await strategy_manager.load_strategies_from_db()
    print(f"  [OK] Loaded {count} strategies")

    # Create Streaming Indicator Engine
    print("\n[4] Creating StreamingIndicatorEngine...")
    from src.domain.services.streaming_indicator_engine.engine import StreamingIndicatorEngine

    # Mock variant repository
    mock_variant_repo = MagicMock()
    mock_variant_repo.get_all_variants = MagicMock(return_value=[])
    mock_variant_repo.save_variant = MagicMock(return_value=None)

    engine = StreamingIndicatorEngine(
        event_bus=event_bus,
        logger=mock_logger,
        variant_repository=mock_variant_repo
    )
    await engine.start()
    print(f"  [OK] StreamingIndicatorEngine started")

    # Check subscriptions
    print(f"\n[5] Checking EventBus subscriptions...")
    for topic in ["market.price_update", "indicator.updated"]:
        subs = event_bus._subscribers.get(topic, [])
        print(f"  - {topic}: {len(subs)} subscribers")

    # Simulate the backtest flow
    symbol = "PUMP_TEST_USDT"
    session_id = "test_session_123"
    strategy_name = "E2E Pump Test"  # From DB

    print(f"\n[6] Activating strategy '{strategy_name}' for {symbol}...")

    if strategy_name not in strategy_manager.strategies:
        print(f"  [FAIL] Strategy not found! Available: {list(strategy_manager.strategies.keys())}")
        await pool.close()
        return

    result = strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)
    print(f"  Activation result: {result}")

    strat = strategy_manager.strategies[strategy_name]
    print(f"  Strategy conditions:")
    if strat.signal_detection:
        for cond in strat.signal_detection.conditions:
            print(f"    - S1: {cond.condition_type} {cond.operator} {cond.value}")

    # Create indicator variant (like _create_indicator_variants_for_strategy does)
    print(f"\n[7] Creating indicator variants for strategy...")
    indicator_types_needed = set()
    for group in ['signal_detection', 'signal_cancellation', 'entry_conditions', 'close_order_detection', 'emergency_exit']:
        grp = getattr(strat, group, None)
        if grp and hasattr(grp, 'conditions'):
            for cond in grp.conditions:
                if cond.condition_type:
                    indicator_types_needed.add(cond.condition_type.upper())

    print(f"  Indicator types needed: {indicator_types_needed}")

    for indicator_type in indicator_types_needed:
        try:
            variant_id = await engine.create_variant(
                name=f"{indicator_type}_default_{symbol}",
                base_indicator_type=indicator_type,
                variant_type="price",
                description=f"Test variant",
                parameters={},
                created_by="test"
            )
            print(f"  Created variant: {variant_id}")

            indicator_id = await engine.add_indicator_to_session(
                session_id=session_id,
                symbol=symbol,
                variant_id=variant_id,
                parameters={}
            )
            print(f"  Added to session: {indicator_id}")
        except Exception as e:
            print(f"  [ERROR] Failed to create {indicator_type}: {e}")

    # Check if indicators registered
    print(f"\n[8] Checking _indicators_by_symbol...")
    indicators_for_symbol = engine._indicators_by_symbol.get(symbol, [])
    print(f"  Indicators for {symbol}: {len(indicators_for_symbol)}")
    for ind_key in indicators_for_symbol[:5]:
        print(f"    - {ind_key}")

    if not indicators_for_symbol:
        print("  [FAIL] No indicators registered for symbol! market.price_update will be ignored!")

    # Publish market data update (like QuestDBHistoricalDataSource does)
    print(f"\n[9] Publishing market.price_update events...")

    import time
    base_time = time.time()
    test_prices = [
        {"price": 1.0, "volume": 100, "offset": 0},
        {"price": 1.1, "volume": 150, "offset": 1},  # 10% up - should trigger price_velocity
        {"price": 1.2, "volume": 200, "offset": 2},  # 20% up
        {"price": 1.3, "volume": 250, "offset": 3},  # 30% up
    ]

    events_log.clear()

    for tick in test_prices:
        await event_bus.publish("market.price_update", {
            "symbol": symbol,
            "price": tick["price"],
            "volume": tick["volume"],
            "timestamp": base_time + tick["offset"],
            "source": "test"
        })
        await asyncio.sleep(0.1)  # Give time for processing

    print(f"  Published {len(test_prices)} market updates")

    # Wait for indicator processing
    await asyncio.sleep(2.0)

    # Check cached indicator values
    print(f"\n[10] Checking indicator values cache...")
    cached = strategy_manager.indicator_values.get(symbol, {})
    print(f"  Cached for {symbol}: {cached}")

    # Check if signals generated
    print(f"\n[11] Events logged during test:")
    for evt in events_log:
        print(f"  [{evt['topic']}] {evt['time']}")

    signal_events = [e for e in events_log if e['topic'] == 'signal_generated']
    indicator_events = [e for e in events_log if e['topic'] == 'indicator.updated']

    print(f"\n[12] RESULTS:")
    print(f"  market.price_update published: {len(test_prices)}")
    print(f"  indicator.updated received: {len(indicator_events)}")
    print(f"  signal_generated received: {len(signal_events)}")

    if not indicator_events:
        print("\n  [DIAGNOSIS] NO indicator.updated events!")
        print("  Possible causes:")
        print("    1. StreamingIndicatorEngine not processing market.price_update")
        print("    2. No indicators registered for symbol in _indicators_by_symbol")
        print("    3. Indicator calculation not publishing events")

        # Check engine internals
        print(f"\n  Engine internal state:")
        print(f"    _indicators count: {len(engine._indicators)}")
        print(f"    _indicators_by_symbol keys: {list(engine._indicators_by_symbol.keys())}")
        print(f"    _session_indicators: {engine._session_indicators}")

    # Cleanup
    await engine.stop()
    await strategy_manager.stop()
    await pool.close()

    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(diagnose())
