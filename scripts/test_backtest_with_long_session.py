"""
Test Backtest with Long Session Data
=====================================
Uses pump_test_20251202_220333 which has 1 hour of data (1800 records).
This session should provide enough warm-up time for 60-second window indicators.
"""

import httpx
import asyncio


async def test_backtest():
    """Test backtest with session that has sufficient data"""

    base_url = "http://localhost:8080"

    print("\n" + "="*70)
    print("  BACKTEST TEST WITH LONG SESSION DATA")
    print("="*70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Login
        print("\n[1] Login...")
        resp = await client.post(f"{base_url}/api/v1/auth/login", json={
            "username": "demo",
            "password": "demo123"
        })
        print(f"  Status: {resp.status_code}")
        login_data = resp.json()
        token = login_data.get("data", {}).get("access_token")
        if not token:
            print(f"  [FAIL] No token in response: {login_data}")
            return
        print(f"  [OK] Got JWT token")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get CSRF token
        print("\n[2] Get CSRF token...")
        resp = await client.get(f"{base_url}/csrf-token", headers=headers)
        csrf_data = resp.json()
        csrf_token = (
            csrf_data.get("data", {}).get("csrf_token") or
            csrf_data.get("data", {}).get("token") or
            csrf_data.get("csrf_token") or
            csrf_data.get("token")
        )
        if csrf_token:
            print(f"  [OK] CSRF token: {csrf_token[:20]}...")
            headers["X-CSRF-Token"] = csrf_token
        else:
            print(f"  [FAIL] No CSRF token in response: {csrf_data}")
            return

        # 3. Get strategies - find one that works with PUMP_TEST_USDT
        print("\n[3] List strategies...")
        resp = await client.get(f"{base_url}/api/strategies", headers=headers)
        strategies_data = resp.json()
        strategies = strategies_data.get("data", {}).get("strategies", [])
        print(f"  Found {len(strategies)} strategies")

        # Find E2E Pump Test strategy
        e2e_strategy = None
        for s in strategies:
            name = s.get("name") or s.get("strategy_name")
            if name == "E2E Pump Test":
                e2e_strategy = s
                break

        if not e2e_strategy:
            print(f"  [WARN] E2E Pump Test not found, using first enabled strategy")
            for s in strategies:
                if s.get("enabled"):
                    e2e_strategy = s
                    break

        strategy_name = e2e_strategy.get("name") or e2e_strategy.get("strategy_name")
        print(f"  Selected: {strategy_name}")

        # 4. Use the known good session with 1 hour of data
        data_session_id = "pump_test_20251202_220333"
        print(f"\n[4] Using session: {data_session_id}")
        print("  This session has 1800 records spanning 1 hour")
        print("  Symbol: PUMP_TEST_USDT")

        # 5. Start backtest with PUMP_TEST_USDT symbol
        print("\n[5] Start backtest...")
        backtest_params = {
            "session_type": "backtest",
            "symbols": ["PUMP_TEST_USDT"],  # Use symbol from this session
            "strategy_config": {strategy_name: ["PUMP_TEST_USDT"]},
            "config": {
                "session_id": data_session_id,
                "acceleration_factor": 50  # Faster but still allowing processing
            }
        }
        print(f"  Params: {backtest_params}")

        resp = await client.post(
            f"{base_url}/sessions/start",
            headers=headers,
            json=backtest_params
        )
        print(f"  Status: {resp.status_code}")
        backtest_data = resp.json()
        print(f"  Response: {backtest_data}")

        session_id = backtest_data.get("data", {}).get("session_id")
        if not session_id:
            print(f"  [FAIL] No session_id in response")
            return

        print(f"  [OK] Session started: {session_id}")

        # 6. Wait and poll status
        print("\n[6] Polling execution status...")
        max_polls = 60  # More polls for longer session
        last_signals = 0
        last_ticks = 0
        for i in range(max_polls):
            await asyncio.sleep(2.0)

            resp = await client.get(
                f"{base_url}/sessions/execution-status",
                headers=headers
            )
            status_data = resp.json()
            data = status_data.get("data", {})
            status = data.get("status", "unknown")
            signals = data.get("signals_generated", 0)
            trades = data.get("trades_executed", 0)
            ticks = data.get("ticks_processed", 0)

            # Only print when there's progress
            if signals != last_signals or ticks != last_ticks or i % 5 == 0:
                print(f"  [{i+1}] Status: {status}, Signals: {signals}, Trades: {trades}, Ticks: {ticks}")
                last_signals = signals
                last_ticks = ticks

            if status in ["stopped", "completed", "error"]:
                break

        # 7. Final results
        print("\n" + "="*70)
        print("  FINAL RESULTS")
        print("="*70)
        print(f"  Status: {status}")
        print(f"  Signals generated: {signals}")
        print(f"  Trades executed: {trades}")
        print(f"  Ticks processed: {ticks}")

        if signals > 0:
            print("\n  [SUCCESS] Signals were generated!")
            print("  The adaptive window fix is working.")
        else:
            print("\n  [DIAGNOSIS] No signals generated")
            print("  Possible causes:")
            print("    - Strategy thresholds may still be too high")
            print("    - Indicator values may not meet conditions")
            print("  Check backend logs for 'window_fallback_used' entries")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_backtest())
