"""
Container-based Diagnostic
===========================
Uses actual Container components to test the full backtest flow.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def diagnose():
    """Run diagnostic using real Container components"""

    print("\n" + "="*70)
    print("  CONTAINER-BASED DIAGNOSTIC")
    print("="*70)

    from src.infrastructure.container import Container
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger
    from src.infrastructure.config.settings import AppSettings

    # Create container with proper dependencies
    print("\n[1] Creating Container...")
    settings = AppSettings()
    event_bus = EventBus()
    logger = StructuredLogger("diagnose", settings.logging)

    container = Container(
        settings=settings,
        event_bus=event_bus,
        logger=logger
    )
    print(f"  [OK] Container created")

    # Get components (skip unified_controller which requires market_data_provider)
    print("\n[2] Getting components from Container...")
    event_bus = container.event_bus
    strategy_manager = await container.create_strategy_manager()
    indicator_engine = await container.create_streaming_indicator_engine()
    print(f"  [OK] Components obtained")

    # Check EventBus subscriptions
    print(f"\n[3] Checking EventBus subscriptions...")
    for topic in ["market.price_update", "indicator.updated", "signal_generated"]:
        subs = event_bus._subscribers.get(topic, [])
        print(f"  - {topic}: {len(subs)} subscribers")

    # Load strategies
    print("\n[4] Loading strategies...")
    count = await strategy_manager.load_strategies_from_db()
    print(f"  [OK] Loaded {count} strategies")

    # Find the E2E Pump Test strategy
    strategy_name = "E2E Pump Test"
    symbol = "PUMP_TEST_USDT"

    if strategy_name not in strategy_manager.strategies:
        print(f"  [FAIL] Strategy '{strategy_name}' not found!")
        available = list(strategy_manager.strategies.keys())[:5]
        print(f"  Available: {available}")
        await container.cleanup()
        return

    strat = strategy_manager.strategies[strategy_name]
    print(f"\n[5] Strategy analysis: {strategy_name}")
    print(f"  Direction: {strat.direction}")
    print(f"  Enabled: {strat.enabled}")
    if strat.signal_detection:
        print(f"  S1 conditions:")
        for cond in strat.signal_detection.conditions:
            print(f"    - {cond.condition_type} {cond.operator} {cond.value}")

    # Test indicator variant creation manually
    print(f"\n[6] Creating indicator variants manually...")
    session_id = "diag_test_123"

    # First activate strategy
    print(f"  Activating strategy for {symbol}...")
    result = strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)
    print(f"  Activation result: {result}")

    # Extract required indicator types from strategy
    indicator_types_needed = set()
    for group_name in ['signal_detection', 'signal_cancellation', 'entry_conditions', 'close_order_detection', 'emergency_exit']:
        grp = getattr(strat, group_name, None)
        if grp and hasattr(grp, 'conditions'):
            for cond in grp.conditions:
                if cond.condition_type:
                    indicator_types_needed.add(cond.condition_type.upper())

    print(f"  Indicator types needed: {indicator_types_needed}")

    # Create variants for each indicator type
    variants_created = 0
    for indicator_type in indicator_types_needed:
        try:
            print(f"\n  Creating variant for {indicator_type}...")
            variant_id = await indicator_engine.create_variant(
                name=f"{indicator_type}_default_{symbol}",
                base_indicator_type=indicator_type,
                variant_type="price",
                description=f"Test variant for {indicator_type}",
                parameters={},
                created_by="diagnose_script"
            )
            print(f"    [OK] Variant created: {variant_id}")

            # Add to session
            indicator_id = await indicator_engine.add_indicator_to_session(
                session_id=session_id,
                symbol=symbol,
                variant_id=variant_id,
                parameters={}
            )
            print(f"    [OK] Added to session: {indicator_id}")
            variants_created += 1
        except Exception as e:
            print(f"    [FAIL] Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n  Total variants created: {variants_created}")

    # Check if indicators were registered
    print(f"\n[7] Checking indicator registration...")
    indicators_for_symbol = indicator_engine._indicators_by_symbol.get(symbol, [])
    print(f"  Indicators registered for {symbol}: {len(indicators_for_symbol)}")
    for ind_key in indicators_for_symbol[:5]:
        print(f"    - {ind_key}")

    if not indicators_for_symbol:
        print(f"  [FAIL] No indicators registered! This is the root cause.")
        print(f"  Engine _indicators_by_symbol keys: {list(indicator_engine._indicators_by_symbol.keys())[:10]}")
        print(f"  Engine _indicators count: {len(indicator_engine._indicators)}")
        print(f"  Engine _variants count: {len(indicator_engine._variants)}")
        print(f"  Session indicators: {indicator_engine._session_indicators}")

    # Test publishing market data
    print(f"\n[8] Testing indicator.updated event flow...")

    signals_received = []
    async def capture_signal(data):
        signals_received.append(data)
        print(f"    [SIGNAL] {data.get('signal_type')} for {data.get('strategy_name')}")

    await event_bus.subscribe("signal_generated", capture_signal)

    # Publish a fake indicator update to test signal generation
    from datetime import datetime
    await event_bus.publish("indicator.updated", {
        "symbol": symbol,
        "indicator": "test_indicator",
        "indicator_type": "price_velocity",
        "value": 0.05,  # High value to trigger signal
        "timestamp": datetime.now().isoformat()
    })

    await asyncio.sleep(1.0)

    print(f"\n  Signals received: {len(signals_received)}")
    if signals_received:
        print("  [OK] Signal generation works when indicator.updated is published")
    else:
        print("  Checking indicator cache...")
        cached = strategy_manager.indicator_values.get(symbol, {})
        print(f"  Cached for {symbol}: {cached}")

        # Manual evaluation
        if strat.signal_detection and cached:
            result = strat.evaluate_signal_detection(cached)
            print(f"  Manual S1 evaluation: {result}")

    # Cleanup
    print("\n[9] Cleanup...")
    await container.cleanup()

    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(diagnose())
