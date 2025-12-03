"""
Test Backtest API Flow with Authentication
==========================================
This script tests the complete API backtest flow to diagnose
why signals are not generated.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime


BASE_URL = "http://localhost:8080"


async def test_backtest_flow():
    """Test complete backtest flow via API"""

    print(f"\n{'='*60}")
    print("  TEST: Backtest API Signal Generation Flow")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Login
        print("[1] Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "demo", "password": "demo123"}
        )

        if login_response.status_code != 200:
            print(f"  [FAIL] Login failed: {login_response.status_code} - {login_response.text}")
            return

        token_data = login_response.json()
        access_token = token_data.get("access_token")
        print(f"  [OK] Login successful, got token")

        # Get CSRF token
        csrf_response = await client.get(f"{BASE_URL}/csrf-token")
        csrf_token = ""
        if csrf_response.status_code == 200:
            csrf_data = csrf_response.json()
            # Token is in "data.token" or just "token"
            if "data" in csrf_data:
                csrf_token = csrf_data["data"].get("token", "")
            else:
                csrf_token = csrf_data.get("token", "")
            print(f"  [OK] Got CSRF token: {csrf_token[:20]}...")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token
        }

        # Step 2: Check available data sessions
        print("\n[2] Checking available data sessions...")
        sessions_response = await client.get(
            f"{BASE_URL}/api/data-collection/sessions",
            headers=headers
        )

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            # Handle dict with "sessions" key or direct list
            sessions = sessions_data.get("sessions", sessions_data) if isinstance(sessions_data, dict) else sessions_data
            if isinstance(sessions, list) and len(sessions) > 0:
                print(f"  [OK] Found {len(sessions)} sessions")
                # Find pump_test session
                pump_session = None
                for s in sessions:
                    if "pump_test" in s.get("session_id", "").lower():
                        pump_session = s
                        break
                if pump_session:
                    print(f"  [OK] Found pump_test session: {pump_session['session_id']}")
                else:
                    print(f"  [WARN] No pump_test session found, using first: {sessions[0].get('session_id')}")
                    pump_session = sessions[0]
                session_id = pump_session.get("session_id", "pump_test_20251202_220333")
            else:
                print(f"  [WARN] No sessions via API, using hardcoded: pump_test_20251202_220333")
                session_id = "pump_test_20251202_220333"
        else:
            print(f"  [WARN] Could not get sessions: {sessions_response.status_code}, using hardcoded")
            session_id = "pump_test_20251202_220333"

        # Step 3: Check available strategies
        print("\n[3] Checking available strategies...")
        strategies_response = await client.get(
            f"{BASE_URL}/api/strategies",
            headers=headers
        )

        available_strategies = []
        if strategies_response.status_code == 200:
            strategies_data = strategies_response.json()
            # Handle wrapped response: {"type":"response","data":{"strategies":[...]}}
            if "data" in strategies_data:
                available_strategies = strategies_data["data"].get("strategies", [])
            elif isinstance(strategies_data, dict):
                available_strategies = strategies_data.get("strategies", [])
            elif isinstance(strategies_data, list):
                available_strategies = strategies_data
            print(f"  [OK] Found {len(available_strategies)} strategies")
            for s in available_strategies[:3]:
                print(f"       - {s.get('strategy_name', s.get('name', 'unknown'))} (id: {s.get('id', '?')[:8]}...)")
        else:
            print(f"  [WARN] Could not get strategies: {strategies_response.status_code}")

        # Step 4: Start backtest
        print(f"\n[4] Starting backtest with session_id: {session_id}...")

        backtest_request = {
            "session_type": "backtest",
            "symbols": ["PUMP_TEST_USDT"],
            "config": {
                "session_id": session_id,
                "acceleration_factor": 100.0  # Fast replay
            }
        }

        if available_strategies:
            # Include strategy IDs for activation (not names - backend expects IDs)
            # Filter to enabled strategies that might work for our test data
            enabled_strategies = [s for s in available_strategies if s.get("enabled", True)]

            # Prefer "E2E Pump Test" or "Pump Detection Strategy" if available
            preferred = ["E2E Pump Test", "Pump Detection Strategy"]
            selected = None
            for pref in preferred:
                for s in enabled_strategies:
                    if s.get("strategy_name") == pref:
                        selected = s
                        break
                if selected:
                    break

            if not selected and enabled_strategies:
                selected = enabled_strategies[0]

            if selected:
                strategy_id = selected.get("id")
                strategy_name = selected.get("strategy_name")
                backtest_request["config"]["selected_strategies"] = [strategy_name]
                print(f"  Selected strategy: {strategy_name} (id: {strategy_id})")

        start_response = await client.post(
            f"{BASE_URL}/sessions/start",
            headers=headers,
            json=backtest_request
        )

        if start_response.status_code != 200:
            print(f"  [FAIL] Backtest start failed: {start_response.status_code}")
            print(f"  Response: {start_response.text}")
            return

        start_data = start_response.json()
        # session_id is in data.session_id
        if "data" in start_data:
            backtest_session_id = start_data["data"].get("session_id")
        else:
            backtest_session_id = start_data.get("session_id")
        print(f"  [OK] Backtest started: {backtest_session_id}")
        print(f"  Response: {json.dumps(start_data, indent=2)}")

        # Step 5: Poll for completion and results
        print("\n[5] Monitoring backtest progress...")

        max_wait = 30  # seconds
        start_time = time.time()
        last_progress = -1

        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"{BASE_URL}/sessions/execution-status",
                headers=headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                # Handle wrapped response
                status = status_data.get("data", status_data)
                progress = status.get("progress", 0)
                state = status.get("status", "unknown")
                metrics = status.get("metrics", {})

                if progress != last_progress:
                    signals = metrics.get("signals_detected", 0)
                    ticks = metrics.get("ticks_processed", 0)
                    print(f"  Progress: {progress:.1f}% | State: {state} | Signals: {signals} | Ticks: {ticks}")
                    last_progress = progress

                if state in ["stopped", "completed", "error"]:
                    print(f"\n  [DONE] Backtest finished with state: {state}")
                    break

            await asyncio.sleep(0.5)

        # Step 6: Get final results
        print("\n[6] Getting final results...")

        final_status = await client.get(
            f"{BASE_URL}/sessions/execution-status",
            headers=headers
        )

        if final_status.status_code == 200:
            final_data = final_status.json()
            final = final_data.get("data", final_data)
            print(f"\n  Final Status:")
            print(f"  - State: {final.get('status')}")
            print(f"  - Progress: {final.get('progress')}%")

            metrics = final.get("metrics", {})
            print(f"\n  Metrics:")
            print(f"  - Ticks Processed: {metrics.get('ticks_processed', 0)}")
            print(f"  - Signals Detected: {metrics.get('signals_detected', 0)}")
            print(f"  - Orders Placed: {metrics.get('orders_placed', 0)}")
            print(f"  - Orders Filled: {metrics.get('orders_filled', 0)}")
            print(f"  - Realized PnL: {metrics.get('realized_pnl', 0)}")

            if metrics.get("signals_detected", 0) == 0:
                print(f"\n  [DIAGNOSIS] No signals detected!")
                print(f"  Possible causes:")
                print(f"  1. Strategy not activated for symbol")
                print(f"  2. Indicators not calculated")
                print(f"  3. Strategy thresholds too high")
                print(f"  4. StrategyManager not subscribed to indicator.updated events")
        else:
            print(f"  [FAIL] Could not get final status: {final_status.status_code}")

        print(f"\n{'='*60}")
        print("  TEST COMPLETE")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_backtest_flow())
