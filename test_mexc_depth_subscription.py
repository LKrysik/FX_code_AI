#!/usr/bin/env python3
"""
Test MEXC WebSocket Depth Subscription Behavior
================================================

Test to determine:
1. Does sub.depth send initial snapshot?
2. Does sub.depth.full send continuous updates or just one snapshot?
3. Are both needed or just one?

Usage:
    python test_mexc_depth_subscription.py
"""

import asyncio
import json
import websockets
from datetime import datetime

WS_URL = "wss://contract.mexc.com/edge"
TEST_SYMBOL = "BTC_USDT"


async def test_sub_depth_only():
    """Test 1: Subscribe ONLY to sub.depth"""
    print("\n" + "="*70)
    print("TEST 1: Subscribing ONLY to sub.depth")
    print("="*70)

    async with websockets.connect(WS_URL) as ws:
        # Subscribe to sub.depth
        subscription = {
            "method": "sub.depth",
            "param": {"symbol": TEST_SYMBOL}
        }
        await ws.send(json.dumps(subscription))
        print(f"[{datetime.now()}] Sent: {subscription}")

        # Collect first 10 messages
        message_count = 0
        for i in range(10):
            msg = await ws.recv()
            data = json.loads(msg)
            message_count += 1

            channel = data.get("channel", "")
            symbol = data.get("symbol", "")

            if channel == "push.depth" or channel == "push.depth.full":
                depth_data = data.get("data", {})
                bids_count = len(depth_data.get("bids", []))
                asks_count = len(depth_data.get("asks", []))
                version = depth_data.get("version", 0)

                print(f"\n[{datetime.now()}] Message #{message_count}")
                print(f"  Channel: {channel}")
                print(f"  Symbol: {symbol}")
                print(f"  Bids: {bids_count} levels")
                print(f"  Asks: {asks_count} levels")
                print(f"  Version: {version}")

                # Check if this is a full snapshot (>=20 levels) or delta (fewer levels)
                if bids_count >= 20 or asks_count >= 20:
                    print(f"  >>> LOOKS LIKE SNAPSHOT (full orderbook)")
                else:
                    print(f"  >>> LOOKS LIKE DELTA (partial update)")
            elif channel.startswith("rs."):
                print(f"\n[{datetime.now()}] Subscription response: {data}")
            else:
                print(f"\n[{datetime.now()}] Other message: {channel}")


async def test_sub_depth_full_only():
    """Test 2: Subscribe ONLY to sub.depth.full"""
    print("\n" + "="*70)
    print("TEST 2: Subscribing ONLY to sub.depth.full")
    print("="*70)

    async with websockets.connect(WS_URL) as ws:
        # Subscribe to sub.depth.full
        subscription = {
            "method": "sub.depth.full",
            "param": {
                "symbol": TEST_SYMBOL,
                "limit": 20
            }
        }
        await ws.send(json.dumps(subscription))
        print(f"[{datetime.now()}] Sent: {subscription}")

        # Collect messages for 10 seconds to see if we get continuous updates
        message_count = 0
        try:
            for i in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                message_count += 1

                channel = data.get("channel", "")

                if channel == "push.depth" or channel == "push.depth.full":
                    depth_data = data.get("data", {})
                    bids_count = len(depth_data.get("bids", []))
                    asks_count = len(depth_data.get("asks", []))

                    print(f"\n[{datetime.now()}] Message #{message_count}")
                    print(f"  Channel: {channel}")
                    print(f"  Bids: {bids_count} levels")
                    print(f"  Asks: {asks_count} levels")

                    if bids_count >= 20 or asks_count >= 20:
                        print(f"  >>> SNAPSHOT (full orderbook)")
                    else:
                        print(f"  >>> DELTA (partial)")
                elif channel.startswith("rs."):
                    print(f"\n[{datetime.now()}] Subscription response: {data}")
                else:
                    print(f"\n[{datetime.now()}] Other message: {channel}")
        except asyncio.TimeoutError:
            print(f"\n[{datetime.now()}] No more messages after {message_count} messages")
            print(">>> sub.depth.full probably sends ONLY ONE snapshot!")


async def test_both_subscriptions():
    """Test 3: Subscribe to BOTH sub.depth.full AND sub.depth"""
    print("\n" + "="*70)
    print("TEST 3: Subscribing to BOTH sub.depth.full AND sub.depth")
    print("="*70)

    async with websockets.connect(WS_URL) as ws:
        # Subscribe to both
        sub1 = {
            "method": "sub.depth.full",
            "param": {
                "symbol": TEST_SYMBOL,
                "limit": 20
            }
        }
        sub2 = {
            "method": "sub.depth",
            "param": {"symbol": TEST_SYMBOL}
        }

        await ws.send(json.dumps(sub1))
        print(f"[{datetime.now()}] Sent: sub.depth.full")

        await ws.send(json.dumps(sub2))
        print(f"[{datetime.now()}] Sent: sub.depth")

        # Collect first 10 messages
        message_count = 0
        for i in range(15):
            msg = await ws.recv()
            data = json.loads(msg)
            message_count += 1

            channel = data.get("channel", "")

            if channel == "push.depth" or channel == "push.depth.full":
                depth_data = data.get("data", {})
                bids_count = len(depth_data.get("bids", []))
                asks_count = len(depth_data.get("asks", []))

                print(f"\n[{datetime.now()}] Message #{message_count}")
                print(f"  Channel: {channel}")
                print(f"  Bids: {bids_count} levels")
                print(f"  Asks: {asks_count} levels")

                if bids_count >= 20 or asks_count >= 20:
                    print(f"  >>> SNAPSHOT (full orderbook)")
                else:
                    print(f"  >>> DELTA (partial)")
            elif channel.startswith("rs."):
                print(f"\n[{datetime.now()}] Subscription response: {data}")


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MEXC WebSocket Depth Subscription Test")
    print("="*70)
    print("\nThis test will help determine:")
    print("1. Does sub.depth send initial snapshot?")
    print("2. Does sub.depth.full send continuous updates?")
    print("3. Do we get duplicate snapshots if we use both?")

    try:
        # Test 1: Only sub.depth
        await test_sub_depth_only()
        await asyncio.sleep(2)

        # Test 2: Only sub.depth.full
        await test_sub_depth_full_only()
        await asyncio.sleep(2)

        # Test 3: Both subscriptions
        await test_both_subscriptions()

        print("\n" + "="*70)
        print("TESTS COMPLETED")
        print("="*70)
        print("\nConclusions to draw:")
        print("- If Test 1 shows 20 levels in first message → sub.depth includes snapshot")
        print("- If Test 2 stops after 1 message → sub.depth.full sends only ONE snapshot")
        print("- If Test 3 shows duplicate snapshots → both subscriptions are redundant")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
