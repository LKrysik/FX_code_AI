"""
Diagnose Signal Generation Flow
================================
This script checks each step of the signal generation flow to identify where it breaks.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
import json


async def diagnose():
    """Run diagnostic checks"""

    print("\n" + "="*70)
    print("  DIAGNOSTIC: Signal Generation Flow")
    print("="*70)

    # Step 1: Check EventBus
    print("\n[1] EventBus Check")
    try:
        from src.core.event_bus import EventBus
        event_bus = EventBus()
        events_received = []

        async def capture_event(data):
            events_received.append(data)

        await event_bus.subscribe("test_event", capture_event)
        await event_bus.publish("test_event", {"test": True})
        await asyncio.sleep(0.1)

        if events_received:
            print("  [OK] EventBus works - events are delivered")
        else:
            print("  [FAIL] EventBus doesn't deliver events")
    except Exception as e:
        print(f"  [FAIL] EventBus error: {e}")

    # Step 2: Check StrategyManager initialization
    print("\n[2] StrategyManager Initialization")
    try:
        from src.domain.services.strategy_manager import StrategyManager
        from unittest.mock import MagicMock

        mock_logger = MagicMock()
        mock_risk_manager = MagicMock()
        mock_risk_manager.can_open_position_sync = MagicMock(return_value=MagicMock(can_proceed=True))
        mock_risk_manager.use_budget = MagicMock(return_value=True)

        sm = StrategyManager(
            event_bus=event_bus,
            logger=mock_logger,
            risk_manager=mock_risk_manager
        )
        await sm.start()
        print(f"  [OK] StrategyManager created and started")
        print(f"       Subscriptions: {len(event_bus._subscribers.get('indicator.updated', []))} for indicator.updated")
    except Exception as e:
        print(f"  [FAIL] StrategyManager error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Load strategies from DB
    print("\n[3] Load Strategies from Database")
    try:
        import asyncpg
        pool = await asyncpg.create_pool(
            host='127.0.0.1',
            port=8812,
            user='admin',
            password='quest',
            database='qdb',
            min_size=1,
            max_size=2
        )
        sm.db_pool = pool

        count = await sm.load_strategies_from_db()
        print(f"  [OK] Loaded {count} strategies from database")
        print(f"       Strategy names: {list(sm.strategies.keys())[:5]}")
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        import traceback
        traceback.print_exc()

    # Step 4: Activate strategy for symbol
    print("\n[4] Activate Strategy for Symbol")
    symbol = "PUMP_TEST_USDT"
    strategy_name = None

    # Find an enabled strategy
    for name, strat in sm.strategies.items():
        if strat.enabled:
            strategy_name = name
            break

    if not strategy_name:
        print(f"  [FAIL] No enabled strategies found")
        return

    try:
        result = sm.activate_strategy_for_symbol(strategy_name, symbol)
        print(f"  [OK] Strategy '{strategy_name}' activated for {symbol}: {result}")

        active = sm.active_strategies.get(symbol, [])
        print(f"       Active strategies for {symbol}: {len(active)}")
    except Exception as e:
        print(f"  [FAIL] Activation error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Check strategy conditions
    print("\n[5] Strategy Condition Analysis")
    strat = sm.strategies.get(strategy_name)
    if strat:
        print(f"  Strategy: {strat.strategy_name}")
        print(f"  Direction: {strat.direction}")
        print(f"  Enabled: {strat.enabled}")

        # Analyze signal detection conditions
        if strat.signal_detection:
            print(f"  Signal Detection (S1) conditions:")
            for cond in strat.signal_detection.conditions:
                print(f"    - {cond.condition_type} {cond.operator} {cond.value}")
        else:
            print(f"  [WARN] No signal detection conditions!")

    # Step 6: Simulate indicator update
    print("\n[6] Simulate Indicator Update")
    try:
        signals_received = []

        async def capture_signal(data):
            signals_received.append(data)
            print(f"    [SIGNAL] {data.get('signal_type')} for {data.get('strategy_name')}")

        await event_bus.subscribe("signal_generated", capture_signal)

        # Get the condition types from strategy
        condition_types = set()
        for group_name in ['signal_detection', 'signal_cancellation', 'entry_conditions', 'close_order_detection', 'emergency_exit']:
            group = getattr(strat, group_name, None)
            if group and hasattr(group, 'conditions'):
                for cond in group.conditions:
                    if cond.condition_type:
                        condition_types.add(cond.condition_type)

        print(f"  Required indicator types: {condition_types}")

        # Publish indicator updates for each required type
        for indicator_type in condition_types:
            test_value = 1.0  # Value above typical thresholds

            await event_bus.publish("indicator.updated", {
                "symbol": symbol,
                "indicator": f"{indicator_type.upper()}_test",
                "indicator_type": indicator_type,
                "value": test_value,
                "timestamp": datetime.now().isoformat()
            })
            print(f"  Published: {indicator_type} = {test_value}")

        await asyncio.sleep(1.0)  # Give time for processing

        print(f"\n  Indicator values cached for {symbol}:")
        cached = sm.indicator_values.get(symbol, {})
        for k, v in cached.items():
            print(f"    - {k}: {v}")

        print(f"\n  Signals received: {len(signals_received)}")

        if not signals_received:
            # Manual evaluation
            print("\n  Manual condition evaluation:")
            if strat.signal_detection and cached:
                result = strat.evaluate_signal_detection(cached)
                print(f"    S1 (Signal Detection) result: {result}")

                # Check each condition
                for cond in strat.signal_detection.conditions:
                    cond_type = cond.condition_type.lower()
                    value = cached.get(cond_type)
                    if value is None:
                        print(f"    - {cond.name}: MISSING indicator value for '{cond_type}'")
                    else:
                        eval_result = cond.evaluate(cached)
                        print(f"    - {cond.name}: {cond_type}={value} {cond.operator} {cond.value} = {eval_result}")

    except Exception as e:
        print(f"  [FAIL] Simulation error: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    await sm.stop()
    if pool:
        await pool.close()

    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(diagnose())
