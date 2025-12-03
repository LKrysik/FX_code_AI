"""
Test API Backtest Flow
======================
Tests the full backtest flow through API.
"""

import httpx
import asyncio
import time


async def test_backtest():
    """Test backtest through API"""

    base_url = "http://localhost:8080"

    print("\n" + "="*70)
    print("  API BACKTEST TEST")
    print("="*70)

    async with httpx.AsyncClient(timeout=60.0) as client:
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
        print(f"  CSRF Response type: {csrf_data.get('type', 'unknown')}")
        # Handle multiple response formats
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

        # 3. Get strategies
        print("\n[3] List strategies...")
        resp = await client.get(f"{base_url}/api/strategies", headers=headers)
        strategies_data = resp.json()
        strategies = strategies_data.get("data", {}).get("strategies", [])
        print(f"  Found {len(strategies)} strategies")

        # Find E2E Pump Test
        e2e_strategy = None
        for s in strategies:
            if s.get("name") == "E2E Pump Test" or s.get("strategy_name") == "E2E Pump Test":
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

        # 4. Get data collection sessions (need session_id for backtest)
        print("\n[4] Get data collection sessions...")
        resp = await client.get(f"{base_url}/api/data-collection/sessions", headers=headers)
        sessions_data = resp.json()
        # Handle both response formats: {sessions: [...]} and {data: {sessions: [...]}}
        sessions = sessions_data.get("sessions", []) or sessions_data.get("data", {}).get("sessions", [])
        print(f"  Found {len(sessions)} data collection sessions")

        # Pick the first session with data
        data_session_id = None
        for sess in sessions:
            # Status can be "stopped" or "completed", both are valid
            if sess.get("status") in ("completed", "stopped") and sess.get("records_collected", 0) > 0:
                data_session_id = sess.get("session_id")
                print(f"  Selected session: {data_session_id} ({sess.get('records_collected')} records)")
                break

        if not data_session_id and sessions:
            data_session_id = sessions[0].get("session_id")
            print(f"  [WARN] No completed session, using first: {data_session_id}")

        if not data_session_id:
            print("  [FAIL] No data collection sessions available for backtest")
            return

        # 5. Start backtest
        print("\n[5] Start backtest...")
        backtest_params = {
            "session_type": "backtest",
            "symbols": ["BTC_USDT"],  # Use common symbol
            "strategy_config": {strategy_name: ["BTC_USDT"]},
            "config": {
                "session_id": data_session_id,
                "acceleration_factor": 100
            }
        }
        print(f"  Params: {backtest_params}")

        resp = await client.post(
            f"{base_url}/sessions/start",  # Correct endpoint!
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
        max_polls = 30
        for i in range(max_polls):
            await asyncio.sleep(2.0)

            resp = await client.get(
                f"{base_url}/sessions/execution-status",  # Correct endpoint!
                headers=headers
            )
            status_data = resp.json()
            data = status_data.get("data", {})
            status = data.get("status", "unknown")
            signals = data.get("signals_generated", 0)
            trades = data.get("trades_executed", 0)
            ticks = data.get("ticks_processed", 0)

            print(f"  [{i+1}] Status: {status}, Signals: {signals}, Trades: {trades}, Ticks: {ticks}")

            if status in ["stopped", "completed", "error"]:
                break

        # 7. Final results
        print("\n[7] Final Results:")
        print(f"  Status: {status}")
        print(f"  Signals generated: {signals}")
        print(f"  Trades executed: {trades}")
        print(f"  Ticks processed: {ticks}")

        if signals == 0:
            print("\n  [DIAGNOSIS] No signals generated!")
            print("  Check backend logs for:")
            print("    - 'variants_created' in strategy_activation log")
            print("    - 'indicator_added_to_session' events")
            print("    - '_indicators_by_symbol' population")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_backtest())
