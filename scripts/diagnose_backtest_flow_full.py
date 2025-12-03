"""
Diagnose Full Backtest Flow
============================
Simulates what happens in the API backtest to find where signals are lost.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def diagnose():
    """Diagnose the full backtest flow"""

    print("\n" + "="*70)
    print("  FULL BACKTEST FLOW DIAGNOSTIC")
    print("="*70)

    # Step 1: Create components like Container does
    print("\n[1] Creating components...")

    from src.core.event_bus import EventBus
    from unittest.mock import MagicMock

    event_bus = EventBus()
    mock_logger = MagicMock()

    # Step 2: Create StrategyManager
    print("\n[2] Creating StrategyManager...")
    from src.domain.services.strategy_manager import StrategyManager

    mock_risk_manager = MagicMock()
    mock_risk_manager.can_open_position_sync = MagicMock(return_value=MagicMock(can_proceed=True))
    mock_risk_manager.use_budget = MagicMock(return_value=True)

    strategy_manager = StrategyManager(
        event_bus=event_bus,
        logger=mock_logger,
        risk_manager=mock_risk_manager
    )
    await strategy_manager.start()
    print(f"  [OK] StrategyManager started")

    # Step 3: Load strategies from DB (like _activate_strategies_for_session does)
    print("\n[3] Loading strategies from database...")
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
    strategy_manager.db_pool = pool

    count = await strategy_manager.load_strategies_from_db()
    print(f"  [OK] Loaded {count} strategies")
    print(f"  Strategy keys: {list(strategy_manager.strategies.keys())[:5]}")

    # Step 4: Simulate selected_strategies from API
    selected_strategies = ["E2E Pump Test"]  # What API sends
    symbol = "PUMP_TEST_USDT"

    print(f"\n[4] Simulating activation for selected_strategies={selected_strategies}")
    print(f"    Symbol: {symbol}")

    # Check if strategy exists
    for strategy_name in selected_strategies:
        if strategy_name in strategy_manager.strategies:
            print(f"  [OK] Strategy '{strategy_name}' found in strategies dict")
            strat = strategy_manager.strategies[strategy_name]
            print(f"       Enabled: {strat.enabled}")
            print(f"       Direction: {strat.direction}")
            if strat.signal_detection:
                print(f"       S1 conditions: {len(strat.signal_detection.conditions)}")
                for cond in strat.signal_detection.conditions:
                    print(f"         - {cond.condition_type} {cond.operator} {cond.value}")
        else:
            print(f"  [FAIL] Strategy '{strategy_name}' NOT found in strategies dict")
            print(f"         Available keys: {list(strategy_manager.strategies.keys())}")

    # Step 5: Activate strategy
    print(f"\n[5] Activating strategy for symbol...")
    for strategy_name in selected_strategies:
        if strategy_name in strategy_manager.strategies:
            result = strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)
            print(f"  Activation result: {result}")
            print(f"  Active strategies for {symbol}: {strategy_manager.active_strategies.get(symbol, [])}")

    # Step 6: Check subscriptions
    print(f"\n[6] Checking EventBus subscriptions...")
    indicator_subs = event_bus._subscribers.get("indicator.updated", [])
    print(f"  Subscribers for 'indicator.updated': {len(indicator_subs)}")
    for sub in indicator_subs:
        print(f"    - {sub}")

    # Step 7: Simulate indicator update (what StreamingIndicatorEngine would do)
    print(f"\n[7] Simulating indicator.updated event...")

    signals_received = []
    async def capture_signal(data):
        signals_received.append(data)
        print(f"    [SIGNAL] {data.get('signal_type')} for {data.get('strategy_name')}")

    await event_bus.subscribe("signal_generated", capture_signal)

    # Publish indicator update
    from datetime import datetime
    await event_bus.publish("indicator.updated", {
        "symbol": symbol,
        "indicator": "PRICE_VELOCITY_test",
        "indicator_type": "price_velocity",
        "value": 0.05,  # Well above 0.0001 threshold
        "timestamp": datetime.now().isoformat()
    })

    await asyncio.sleep(1.0)

    print(f"\n  Indicator values cached:")
    cached = strategy_manager.indicator_values.get(symbol, {})
    for k, v in cached.items():
        print(f"    - {k}: {v}")

    print(f"\n  Signals received: {len(signals_received)}")

    if not signals_received:
        print("\n  [DIAGNOSIS]")

        # Check if strategy is in expected state
        if selected_strategies[0] in strategy_manager.strategies:
            strat = strategy_manager.strategies[selected_strategies[0]]
            if hasattr(strat, 'current_state'):
                print(f"  Strategy state: {strat.current_state}")

            # Try manual evaluation
            if cached:
                result = strat.evaluate_signal_detection(cached)
                print(f"  Manual S1 evaluation: {result}")

    # Cleanup
    await pool.close()

    print("\n" + "="*70)
    print("  DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(diagnose())
