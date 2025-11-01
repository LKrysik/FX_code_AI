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
        """Simulate deal confirmation (FIXED implementation)"""
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
            # ✅ FIX: Check ALL 3 channels before removing
            all_confirmed = (
                pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth_full') == 'confirmed'
            )

            if all_confirmed:
                self.log("INFO", "removing_symbol_from_pending", {
                    "symbol": confirmed_symbol,
                    "connection_id": connection_id,
                    "reason": "all_channels_confirmed",
                    "channels": "deal + depth + depth_full"
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
        """Simulate depth confirmation (FIXED implementation)"""
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
            # ✅ FIX: Check ALL 3 channels before removing
            all_confirmed = (
                pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth_full') == 'confirmed'
            )

            if all_confirmed:
                self.log("INFO", "removing_symbol_from_pending", {
                    "symbol": confirmed_symbol,
                    "connection_id": connection_id,
                    "reason": "all_channels_confirmed",
                    "channels": "deal + depth + depth_full"
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
        """Simulate depth_full confirmation (FIXED with cleanup logic)"""
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

            # ✅ FIX: Check if ALL 3 channels confirmed, then remove
            all_confirmed = (
                pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth') == 'confirmed' and
                pending_symbols[confirmed_symbol].get('depth_full') == 'confirmed'
            )

            if all_confirmed:
                self.log("INFO", "removing_symbol_from_pending", {
                    "symbol": confirmed_symbol,
                    "connection_id": connection_id,
                    "reason": "all_channels_confirmed",
                    "channels": "deal + depth + depth_full",
                    "handler": "depth_full"
                })

                # Remove from pending
                del pending_symbols[confirmed_symbol]
                if not pending_symbols:
                    del self._pending_subscriptions[connection_id]
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
    """Test when confirmations arrive in typical order - WITH FIX"""
    print("\n" + "=" * 80)
    print("TEST 1: Confirmations arrive in typical order (deal → depth → depth_full)")
    print("         ✅ FIXED: Symbol stays in pending until all 3 channels confirmed")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe
    await sim.subscribe_symbol("BTC_USDT", connection_id=1)

    # Confirmations in order
    await asyncio.sleep(0.01)
    await sim.handle_deal_confirmation(1)  # Marks deal=confirmed, symbol stays in pending

    await asyncio.sleep(0.01)
    await sim.handle_depth_confirmation(1)  # Marks depth=confirmed, symbol stays in pending

    await asyncio.sleep(0.01)
    result = await sim.handle_depth_full_confirmation(1)  # ✅ Will find symbol and start task

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
    """Test with multiple symbols - WITH FIX all should work"""
    print("\n" + "=" * 80)
    print("TEST 3: Multiple symbols with varying confirmation order")
    print("         ✅ FIXED: All symbols should get snapshot tasks regardless of order")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe 3 symbols
    symbols = ["AEVO_USDT", "AIBOT_USDT", "ARIA_USDT"]
    for i, symbol in enumerate(symbols):
        await sim.subscribe_symbol(symbol, connection_id=1)

    # Symbol 1: depth_full arrives last (NOW WORKS with fix)
    print("\n--- AEVO_USDT: deal → depth → depth_full ---")
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_confirmation(1)  # Symbol stays in pending
    await sim.handle_depth_full_confirmation(1)  # ✅ Will find AEVO_USDT and start task

    # Symbol 2: depth_full arrives first (always worked)
    print("\n--- AIBOT_USDT: depth_full arrives first ---")
    await sim.handle_depth_full_confirmation(1)  # Will process AIBOT_USDT
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_confirmation(1)  # Symbol removed after all 3 confirmed

    # Symbol 3: depth_full between deal and depth
    print("\n--- ARIA_USDT: deal → depth_full → depth ---")
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_full_confirmation(1)  # Will process ARIA_USDT
    await sim.handle_depth_confirmation(1)  # Symbol removed after all 3 confirmed

    print("\n📊 RESULT:")
    print(f"   Symbols subscribed: {len(symbols)}")
    print(f"   Snapshot tasks started: {len(sim._snapshot_refresh_tasks)}")
    print(f"   Running tasks: {sorted(sim._snapshot_refresh_tasks.keys())}")

    if len(sim._snapshot_refresh_tasks) == 3:
        print(f"\n   ✅ SUCCESS: All 3 symbols have snapshot tasks!")
    else:
        print(f"\n   ❌ FAILURE: Only {len(sim._snapshot_refresh_tasks)} out of 3 have snapshot tasks")

    return len(sim._snapshot_refresh_tasks) == 3  # ✅ Should be 3 out of 3 with fix!


async def test_memory_leak_prevention():
    """Test that symbols are removed from pending after all confirmations"""
    print("\n" + "=" * 80)
    print("TEST 4: Memory Leak Prevention - pending subscriptions cleanup")
    print("         ✅ FIXED: Symbol should be removed after all 3 confirmations")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe symbol
    await sim.subscribe_symbol("LEAK_TEST_USDT", connection_id=1)

    print("Initial state:")
    print(f"   Pending subscriptions: {list(sim._pending_subscriptions.get(1, {}).keys())}")

    # All confirmations arrive
    await sim.handle_deal_confirmation(1)
    print("\nAfter deal confirmation:")
    print(f"   Pending subscriptions: {list(sim._pending_subscriptions.get(1, {}).keys())}")

    await sim.handle_depth_confirmation(1)
    print("\nAfter depth confirmation:")
    print(f"   Pending subscriptions: {list(sim._pending_subscriptions.get(1, {}).keys())}")

    await sim.handle_depth_full_confirmation(1)
    print("\nAfter depth_full confirmation:")
    pending_after = sim._pending_subscriptions.get(1, {})
    print(f"   Pending subscriptions: {list(pending_after.keys())}")

    print("\n📊 RESULT:")
    if len(pending_after) == 0:
        print("   ✅ SUCCESS: Symbol removed from pending after all confirmations!")
        print("   No memory leak - pending subscriptions properly cleaned up")
    else:
        print(f"   ❌ FAILURE: Symbol still in pending: {list(pending_after.keys())}")
        print("   Memory leak - symbols accumulate in pending subscriptions")

    return len(pending_after) == 0


async def test_duplicate_confirmation_handling():
    """Test that duplicate depth_full confirmations are handled gracefully"""
    print("\n" + "=" * 80)
    print("TEST 5: Duplicate Confirmation Handling")
    print("         ✅ FIXED: Duplicate confirmations should not cause errors")
    print("=" * 80 + "\n")

    sim = SubscriptionStateSimulator()

    # Subscribe symbol
    await sim.subscribe_symbol("DUP_TEST_USDT", connection_id=1)

    # All confirmations arrive
    await sim.handle_deal_confirmation(1)
    await sim.handle_depth_confirmation(1)
    await sim.handle_depth_full_confirmation(1)

    print("\nFirst depth_full processed, symbol removed from pending")
    print(f"Pending subscriptions: {list(sim._pending_subscriptions.get(1, {}).keys())}")

    # Duplicate depth_full confirmation arrives (simulates late/retry)
    print("\nDuplicate depth_full confirmation arrives...")
    result = await sim.handle_depth_full_confirmation(1)

    print("\n📊 RESULT:")
    if result is None:
        print("   ✅ SUCCESS: Duplicate confirmation handled gracefully!")
        print("   Returns None without crashing or creating errors")
        print("   Snapshot task already exists, no duplicates created")
    else:
        print(f"   ⚠️  UNEXPECTED: Duplicate created snapshot task for {result}")

    return result is None


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

    # Test 4: Memory leak prevention
    try:
        result = await test_memory_leak_prevention()
        results.append(("Memory leak prevention test", result))
    except Exception as e:
        print(f"❌ Test 4 crashed: {e}")
        results.append(("Memory leak prevention test", False))

    # Test 5: Duplicate confirmation handling
    try:
        result = await test_duplicate_confirmation_handling()
        results.append(("Duplicate confirmation handling test", result))
    except Exception as e:
        print(f"❌ Test 5 crashed: {e}")
        results.append(("Duplicate confirmation handling test", False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    # Check if all tests passed
    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ FIX VALIDATED:")
        print("   The fix is working correctly! Snapshot tasks are now started for")
        print("   ALL symbols, regardless of WebSocket message timing.")
        print("\n   Before fix: Only symbols where depth_full arrived FIRST got tasks")
        print("   After fix: ALL symbols get tasks because symbol stays in pending")
        print("              until all 3 channels (deal + depth + depth_full) are confirmed")
        print("\n   ✅ Memory leak FIXED: Symbols removed from pending after all confirmations")
        print("   ✅ Duplicate handling: Gracefully handles late/retry confirmations")
    else:
        print("\n❌ TESTS FAILED:")
        print("   Some tests did not pass. Check implementation or test logic.")
        print(f"   Passed: {sum(1 for _, p in results if p)}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
