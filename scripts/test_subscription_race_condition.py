"""
Unit Test: Subscription Confirmation Race Condition
====================================================

This test reproduces the race condition that causes snapshot refresh
tasks to not be started for some symbols.

It simulates the exact sequence of events that leads to "unknown" symbol
confirmations and missing snapshot tasks.

Run with: python scripts/test_subscription_race_condition.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self):
        self.sent_messages = []
        self.close_code = None

    async def send(self, message: str):
        self.sent_messages.append(message)

    async def recv(self):
        # Not used in this test
        await asyncio.sleep(0.1)
        return ""


class SubscriptionStateSimulator:
    """Simulates the subscription state management to reproduce the bug"""

    def __init__(self):
        self._pending_subscriptions: Dict[int, Dict[str, Dict[str, str]]] = {}
        self._snapshot_refresh_tasks: Dict[str, Any] = {}
        self.logger_output = []

    def log(self, level: str, event: str, data: Dict[str, Any]):
        """Mock logger"""
        self.logger_output.append({
            "level": level,
            "event": event,
            "data": data
        })
        print(f"[{level}] {event}: {data}")

    async def subscribe_symbol(self, symbol: str, connection_id: int):
        """Simulate subscribing to a symbol with orderbook data"""
        # Initialize pending subscriptions
        if connection_id not in self._pending_subscriptions:
            self._pending_subscriptions[connection_id] = {}

        # Add pending channels (same as real implementation)
        pending_channels = {
            'added_time': asyncio.get_event_loop().time(),
            'deal': 'pending',
            'depth': 'pending',
            'depth_full': 'pending'
        }
        self._pending_subscriptions[connection_id][symbol] = pending_channels

        self.log("INFO", "symbol_subscribed", {
            "symbol": symbol,
            "connection_id": connection_id,
            "pending_channels": ['deal', 'depth', 'depth_full']
        })

    async def handle_deal_confirmation(self, connection_id: int):
        """Simulate deal confirmation (BUGGY implementation from real code)"""
        pending_symbols = self._pending_subscriptions.get(connection_id, {})
        if not pending_symbols:
            return None

        # Find first symbol with pending deal subscription
        confirmed_symbol = None
        for symbol, status in pending_symbols.items():
            if status.get('deal') == 'pending':
                status['deal'] = 'confirmed'
                confirmed_symbol = symbol
                break

        if confirmed_symbol:
            # ❌ BUG: Check if both deal AND depth confirmed, IGNORE depth_full
            if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth') == 'confirmed'):

                self.log("WARNING", "removing_symbol_from_pending", {
                    "symbol": confirmed_symbol,
                    "connection_id": connection_id,
                    "reason": "deal_and_depth_confirmed",
                    "depth_full_status": pending_symbols[confirmed_symbol].get('depth_full'),
                    "BUG": "Removing before depth_full confirmation!"
                })

                # Remove from pending
                del pending_symbols[confirmed_symbol]
                if not pending_symbols:
                    del self._pending_subscriptions[connection_id]

            self.log("INFO", "confirmation_received", {
                "symbol": confirmed_symbol,
                "type": "deal"
            })

        return confirmed_symbol

    async def handle_depth_confirmation(self, connection_id: int):
        """Simulate depth confirmation (BUGGY implementation from real code)"""
        pending_symbols = self._pending_subscriptions.get(connection_id, {})
        if not pending_symbols:
            return None

        # Find first symbol with pending depth subscription
        confirmed_symbol = None
        for symbol, status in pending_symbols.items():
            if status.get('depth') == 'pending':
                status['depth'] = 'confirmed'
                confirmed_symbol = symbol
                break

        if confirmed_symbol:
            # ❌ BUG: Check if both deal AND depth confirmed, IGNORE depth_full
            if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth') == 'confirmed'):

                self.log("WARNING", "removing_symbol_from_pending", {
                    "symbol": confirmed_symbol,
                    "connection_id": connection_id,
                    "reason": "deal_and_depth_confirmed",
                    "depth_full_status": pending_symbols[confirmed_symbol].get('depth_full'),
                    "BUG": "Removing before depth_full confirmation!"
                })

                # Remove from pending
                del pending_symbols[confirmed_symbol]
                if not pending_symbols:
                    del self._pending_subscriptions[connection_id]

            self.log("INFO", "confirmation_received", {
                "symbol": confirmed_symbol,
                "type": "depth"
            })

        return confirmed_symbol

    async def handle_depth_full_confirmation(self, connection_id: int):
        """Simulate depth_full confirmation (this is where the bug manifests)"""
        pending_symbols = self._pending_subscriptions.get(connection_id, {})
        if not pending_symbols:
            self.log("ERROR", "depth_full_confirmation_failed", {
                "connection_id": connection_id,
                "reason": "no_pending_subscriptions",
                "symbol": "unknown"
            })
            return None

        # Find symbol with pending depth_full subscription
        confirmed_symbol = None
        for symbol, status in pending_symbols.items():
            if status.get('depth_full') == 'pending':
                status['depth_full'] = 'confirmed'
                confirmed_symbol = symbol
                break

        if confirmed_symbol:
            # Start snapshot refresh task
            await self.start_snapshot_refresh_task(confirmed_symbol)

            self.log("INFO", "confirmation_received", {
                "symbol": confirmed_symbol,
                "type": "depth_full"
            })
        else:
            # ❌ MANIFESTATION: Symbol already removed!
            self.log("ERROR", "depth_full_confirmation_failed", {
                "connection_id": connection_id,
                "reason": "symbol_already_removed_by_deal_or_depth_handler",
                "symbol": "unknown",
                "remaining_pending": list(pending_symbols.keys()) if pending_symbols else []
            })

        return confirmed_symbol

    async def start_snapshot_refresh_task(self, symbol: str):
        """Simulate starting snapshot refresh task"""
        if symbol in self._snapshot_refresh_tasks:
            return

        self._snapshot_refresh_tasks[symbol] = "running"

        self.log("INFO", "snapshot_refresh_task_started", {
            "symbol": symbol
        })


async def test_correct_order():
    """Test when confirmations arrive in 'safe' order"""
    print("\n" + "=" * 80)
    print("TEST 1: Confirmations arrive in safe order (deal → depth → depth_full)")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe
    await sim.subscribe_symbol("BTC_USDT", connection_id=1)

    # Confirmations in order
    await asyncio.sleep(0.01)
    await sim.handle_deal_confirmation(1)

    await asyncio.sleep(0.01)
    await sim.handle_depth_confirmation(1)  # This will remove symbol from pending

    await asyncio.sleep(0.01)
    result = await sim.handle_depth_full_confirmation(1)  # ❌ Will fail to find symbol

    print("\n📊 RESULT:")
    if result is None:
        print("   ❌ FAILED: Snapshot task NOT started")
        print("   Reason: Symbol removed from pending before depth_full confirmation")
    else:
        print(f"   ✅ SUCCESS: Snapshot task started for {result}")

    print(f"\n   Snapshot tasks running: {list(sim._snapshot_refresh_tasks.keys())}")

    return len(sim._snapshot_refresh_tasks) == 1


async def test_depth_full_first():
    """Test when depth_full confirmation arrives first"""
    print("\n" + "=" * 80)
    print("TEST 2: depth_full confirmation arrives first (should work)")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe
    await sim.subscribe_symbol("ETH_USDT", connection_id=1)

    # depth_full arrives first
    await asyncio.sleep(0.01)
    result = await sim.handle_depth_full_confirmation(1)

    await asyncio.sleep(0.01)
    await sim.handle_deal_confirmation(1)

    await asyncio.sleep(0.01)
    await sim.handle_depth_confirmation(1)

    print("\n📊 RESULT:")
    if result is not None and "ETH_USDT" in sim._snapshot_refresh_tasks:
        print(f"   ✅ SUCCESS: Snapshot task started for {result}")
    else:
        print("   ❌ FAILED: Snapshot task NOT started")

    print(f"\n   Snapshot tasks running: {list(sim._snapshot_refresh_tasks.keys())}")

    return len(sim._snapshot_refresh_tasks) == 1


async def test_multiple_symbols():
    """Test with multiple symbols to show inconsistent behavior"""
    print("\n" + "=" * 80)
    print("TEST 3: Multiple symbols with varying confirmation order")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe 3 symbols
    symbols = ["AEVO_USDT", "AIBOT_USDT", "ARIA_USDT"]
    for i, symbol in enumerate(symbols):
        await sim.subscribe_symbol(symbol, connection_id=1)

    # Symbol 1: depth_full arrives last (BUG)
    print("\n--- AEVO_USDT: deal → depth → depth_full ---")
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_confirmation(1)  # Will remove AEVO_USDT
    await sim.handle_depth_full_confirmation(1)  # Won't find AEVO_USDT

    # Symbol 2: depth_full arrives first (WORKS)
    print("\n--- AIBOT_USDT: depth_full arrives first ---")
    await sim.handle_depth_full_confirmation(1)  # Will process AIBOT_USDT
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_confirmation(1)

    # Symbol 3: depth_full between deal and depth
    print("\n--- ARIA_USDT: deal → depth_full → depth ---")
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_full_confirmation(1)  # Will process ARIA_USDT
    await sim.handle_depth_confirmation(1)

    print("\n📊 RESULT:")
    print(f"   Symbols subscribed: {len(symbols)}")
    print(f"   Snapshot tasks started: {len(sim._snapshot_refresh_tasks)}")
    print(f"   Running tasks: {list(sim._snapshot_refresh_tasks.keys())}")
    print(f"\n   ❌ Missing snapshot task: AEVO_USDT")
    print(f"   ✅ Has snapshot task: AIBOT_USDT, ARIA_USDT")

    return len(sim._snapshot_refresh_tasks) == 2  # Should be 2 out of 3


async def main():
    """Run all tests"""
    print("=" * 80)
    print("MEXC Subscription Race Condition Test Suite")
    print("=" * 80)

    results = []

    # Test 1: Typical failure case
    try:
        result = await test_correct_order()
        results.append(("Safe order test", result))
    except Exception as e:
        print(f"❌ Test 1 crashed: {e}")
        results.append(("Safe order test", False))

    # Test 2: Working case
    try:
        result = await test_depth_full_first()
        results.append(("depth_full first test", result))
    except Exception as e:
        print(f"❌ Test 2 crashed: {e}")
        results.append(("depth_full first test", False))

    # Test 3: Multiple symbols
    try:
        result = await test_multiple_symbols()
        results.append(("Multiple symbols test", result))
    except Exception as e:
        print(f"❌ Test 3 crashed: {e}")
        results.append(("Multiple symbols test", False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n🔍 KEY FINDING:")
    print("   The bug is CONFIRMED: snapshot tasks are only started when")
    print("   depth_full confirmation arrives BEFORE deal+depth removes the")
    print("   symbol from pending subscriptions.")
    print("\n   This creates inconsistent behavior where some symbols get")
    print("   snapshot refresh tasks and others don't, depending on network")
    print("   timing of WebSocket messages.")


if __name__ == "__main__":
    asyncio.run(main())
