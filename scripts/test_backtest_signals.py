#!/usr/bin/env python3
"""
Test script to verify signal generation during backtest.
This script directly tests the signal pipeline without requiring HTTP authentication.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.infrastructure.container import Container
from src.application.controllers.execution_controller import ExecutionMode

async def main():
    """Run backtest and verify signals are generated."""
    print("=" * 60)
    print("BACKTEST SIGNAL GENERATION TEST")
    print("=" * 60)

    container = None
    try:
        # Initialize dependencies (same pattern as unified_server.py)
        print("\n[1/5] Initializing container...")
        settings = get_settings_from_working_directory()
        event_bus = EventBus()
        logger = StructuredLogger("BacktestTest", settings.logging)
        container = Container(settings, event_bus, logger)

        # Get unified trading controller
        print("[2/5] Getting unified trading controller...")
        controller = await container.create_unified_trading_controller()

        # CRITICAL: Start the controller to initialize OrderManager and services
        print("      Starting controller services...")
        await controller.start()

        # Get strategy manager to check loaded strategies
        print("[3/5] Checking strategy manager...")
        strategy_manager = await container.create_strategy_manager()
        print(f"      Strategies loaded: {len(strategy_manager.strategies)}")
        for name, strategy in strategy_manager.strategies.items():
            print(f"        - {name} (enabled={strategy.enabled})")

        # DEBUG: Check EventBus subscribers
        print("\n[DEBUG] EventBus subscriber counts:")
        eb_subscribers = event_bus._subscribers
        for topic in ["market.price_update", "indicator.updated", "signal_generated"]:
            count = len(eb_subscribers.get(topic, []))
            print(f"      {topic}: {count} subscribers")

        # DEBUG: Add test subscriber to verify events are being published
        test_tick_count = [0]  # Use list to allow mutation in closure

        async def debug_price_subscriber(data):
            test_tick_count[0] += 1
            if test_tick_count[0] <= 3:
                print(f"[DEBUG] market.price_update received: tick #{test_tick_count[0]}, price={data.get('price')}")

        await event_bus.subscribe("market.price_update", debug_price_subscriber)
        print("      [Added debug subscriber for market.price_update]")

        # Get indicator engine
        print("[4/5] Checking indicator engine...")
        indicator_engine = await container.create_streaming_indicator_engine()
        print(f"      Indicator engine ready: {indicator_engine is not None}")
        print(f"      Variants loaded: {len(indicator_engine._variants)}")

        # Start backtest
        print("[5/5] Starting backtest...")
        data_session_id = "exec_20251102_113922_361d6250"  # Session with 68K price records
        symbols = ["ARIA_USDT"]

        session_id = await controller.start_backtest(
            symbols=symbols,
            acceleration_factor=100.0,
            session_id=data_session_id
        )
        print(f"      Backtest session started: {session_id}")

        # Wait for backtest to complete (with timeout)
        print("\n[WAITING] Backtest running... (max 60 seconds)")
        for i in range(120):  # 120 * 0.5s = 60 seconds
            await asyncio.sleep(0.5)

            status = controller.get_execution_status()
            if status:
                current_status = status.get("status", "unknown")
                status_metrics = status.get("metrics", {})
                ticks = status_metrics.get("ticks_processed", 0)
                signals = status_metrics.get("signals_detected", 0)

                if i % 10 == 0:  # Log every 5 seconds
                    print(f"      Status: {current_status}, Ticks: {ticks}, Signals: {signals}")

                if current_status in ("stopped", "completed", "error", "failed"):
                    break

        # Get final status
        print("\n" + "=" * 60)
        print("FINAL STATUS")
        print("=" * 60)

        final_status = controller.get_execution_status()
        if final_status:
            metrics = final_status.get('metrics', {})
            print(f"Status: {final_status.get('status')}")
            print(f"Ticks processed (controller): {metrics.get('ticks_processed', 0)}")
            print(f"Ticks received (debug subscriber): {test_tick_count[0]}")
            print(f"Records collected: {metrics.get('records_collected', 0)}")
            print(f"SIGNALS DETECTED: {metrics.get('signals_detected', 0)}")

            signals_detected = metrics.get('signals_detected', 0)
            if signals_detected > 0:
                print("\n" + "=" * 60)
                print("SUCCESS: Signals are being generated!")
                print("=" * 60)
                return 0
            else:
                print("\n" + "=" * 60)
                print("FAILURE: No signals detected during backtest")
                print("=" * 60)

                # Debug: Check indicator state
                print("\n[DEBUG] Checking indicator state...")
                print(f"  _indicators_by_symbol keys: {list(indicator_engine._indicators_by_symbol.keys())[:5]}")
                print(f"  _indicators count: {len(indicator_engine._indicators)}")
                print(f"  _session_indicators: {list(indicator_engine._session_indicators.keys())[:5]}")

                return 1
        else:
            print("ERROR: Could not get execution status")
            return 1

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if container:
            try:
                controller = await container.create_unified_trading_controller()
                await controller.stop_execution()
            except:
                pass

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
