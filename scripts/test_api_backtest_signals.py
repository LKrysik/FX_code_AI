"""
API Backtest Signal Test
========================
Tests the actual API endpoint to verify signals are generated.
Uses requests library to call the real backend.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8080"

def get_auth_token():
    """Get JWT token for authenticated requests"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "admin", "password": "supersecret"},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        if data.get("type") == "response":
            return data.get("data", {}).get("access_token")
        return data.get("access_token")
    print(f"  [WARN] Auth failed: {resp.status_code} - {resp.text[:200]}")
    return None

def get_csrf_token(headers):
    """Get CSRF token for state-changing requests"""
    resp = requests.get(f"{BASE_URL}/csrf-token", headers=headers, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("type") == "response":
            return data.get("data", {}).get("token")  # Field is "token", not "csrf_token"
        return data.get("token")
    print(f"  [WARN] CSRF failed: {resp.status_code} - {resp.text[:200]}")
    return None

def test_api_backtest_signals():
    """Test real API backtest flow"""

    print("\n" + "="*70)
    print("  API BACKTEST SIGNAL TEST")
    print("="*70)

    # Step 1: Check backend health
    print("\n[1] Checking backend health...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print(f"  [OK] Backend healthy")
        else:
            print(f"  [FAIL] Backend returned {resp.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to backend at localhost:8080")
        return

    # Step 1b: Get auth token
    print("\n[1b] Authenticating...")
    token = get_auth_token()
    if token:
        print(f"  [OK] Got auth token: {token[:20]}...")
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print("  [WARN] No token, continuing without auth")
        headers = {}

    # Step 1c: Get CSRF token
    print("\n[1c] Getting CSRF token...")
    csrf = get_csrf_token(headers)
    if csrf:
        print(f"  [OK] Got CSRF token: {csrf[:20]}...")
        headers["X-CSRF-Token"] = csrf
    else:
        print("  [WARN] No CSRF token")

    # Step 2: Get available strategies
    print("\n[2] Fetching strategies...")
    # Try multiple endpoints
    resp = requests.get(f"{BASE_URL}/api/strategies", headers=headers)
    strategies = []
    if resp.status_code == 200:
        data = resp.json()
        if data.get("type") == "response":
            strategies = data.get("data", {}).get("strategies", [])
        else:
            strategies = data.get("strategies", [])

    if not strategies:
        # Try alternative endpoint
        resp = requests.get(f"{BASE_URL}/api/v1/strategies", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("type") == "response":
                strategies = data.get("data", {}).get("strategies", [])
            else:
                strategies = data.get("strategies", [])

    print(f"  [OK] Found {len(strategies)} strategies")

    # Find E2E Pump Test strategy
    e2e_strategy = None
    for s in strategies:
        strat_name = s.get("strategy_name") or s.get("name", "")
        if "E2E Pump Test" in strat_name:
            e2e_strategy = s
            break

    if e2e_strategy:
        strat_name = e2e_strategy.get("strategy_name") or e2e_strategy.get("name")
        print(f"  Found: {strat_name}")
        # Show S1 conditions
        if e2e_strategy.get("signal_detection"):
            conds = e2e_strategy["signal_detection"].get("conditions", [])
            for c in conds:
                print(f"    S1: {c.get('condition_type')} {c.get('operator')} {c.get('value')}")
    else:
        print("  [WARN] E2E Pump Test not found, using first enabled strategy")
        for s in strategies:
            if s.get("enabled"):
                e2e_strategy = s
                break

    if not e2e_strategy and strategies:
        e2e_strategy = strategies[0]
        strat_name = e2e_strategy.get("strategy_name") or e2e_strategy.get("name")
        print(f"  Using first strategy: {strat_name}")

    # Step 2b: Get available data collection sessions for backtest
    print("\n[2b] Fetching data collection sessions...")
    resp = requests.get(f"{BASE_URL}/api/data-collection/sessions", headers=headers)
    data_sessions = []
    if resp.status_code == 200:
        data = resp.json()
        if data.get("type") == "response":
            data_sessions = data.get("data", {}).get("sessions", [])
        else:
            data_sessions = data.get("sessions", [])

    if data_sessions:
        print(f"  [OK] Found {len(data_sessions)} data collection sessions")
        for s in data_sessions[:3]:
            print(f"    - {s.get('session_id', s.get('id'))}: {s.get('name', 'unnamed')}")
        # Use first session
        session_for_backtest = data_sessions[0].get("session_id") or data_sessions[0].get("id")
    else:
        print("  [FAIL] No data collection sessions found!")
        print("  Need to create a data collection session first")
        return

    # Step 3: Create a test backtest session
    print("\n[3] Starting backtest session...")

    strategy_name = e2e_strategy.get("strategy_name") or e2e_strategy.get("name") if e2e_strategy else None

    # Use PUMP_TEST_USDT symbol which has data and matches E2E Pump Test strategy
    # Symbol format in QuestDB uses underscore: PUMP_TEST_USDT
    test_symbol = "PUMP_TEST_USDT"

    # Use session with most PUMP_TEST_USDT data: pump_test_20251202_220333 (1800 records)
    # or fall back to first session if not found
    best_session = "pump_test_20251202_220333"
    session_for_backtest = best_session if any(
        s.get("session_id") == best_session or s.get("id") == best_session
        for s in data_sessions
    ) else session_for_backtest

    backtest_config = {
        "session_type": "backtest",
        "name": f"API_Signal_Test_{int(time.time())}",
        "symbols": [test_symbol],  # Use PUMP_TEST_USDT which has test data
        "strategy_config": {strategy_name: [test_symbol]} if strategy_name else {},
        "config": {
            "session_id": session_for_backtest,  # Session with PUMP_TEST_USDT data
            "replay_speed": 100  # Fast replay
        }
    }

    print(f"  Config: {json.dumps(backtest_config, indent=2)}")

    resp = requests.post(
        f"{BASE_URL}/sessions/start",
        json=backtest_config,
        headers=headers,
        timeout=30
    )

    if resp.status_code != 200:
        print(f"  [FAIL] Start session failed: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        return

    result = resp.json()
    print(f"  Raw response: {json.dumps(result, indent=2)[:500]}")

    # Parse response - handle wrapped format
    if result.get("type") == "response":
        session_id = result.get("data", {}).get("session_id")
    else:
        session_id = result.get("session_id")

    if not session_id:
        print("  [FAIL] No session_id in response!")
        return

    print(f"  [OK] Session started: {session_id}")

    # Step 4: Wait for backtest to complete
    print("\n[4] Waiting for backtest to complete...")
    max_wait = 120  # seconds - backtest can take time
    start = time.time()
    final_status = None

    while time.time() - start < max_wait:
        resp = requests.get(f"{BASE_URL}/sessions/execution-status", headers=headers, timeout=5)
        if resp.status_code == 200:
            status_data = resp.json()
            # Handle wrapped response
            if status_data.get("type") == "response":
                status = status_data.get("data", {})
            else:
                status = status_data

            state = status.get("state", status.get("status", "unknown"))
            signals = status.get("signals_count", status.get("signals", 0))
            print(f"  Status: {state}, Signals: {signals}")

            if state in ["completed", "stopped", "failed", "error", "idle"]:
                final_status = status
                if state == "idle" and start + 5 < time.time():
                    # If idle after some time, backtest may have finished
                    break
                elif state != "idle":
                    break
        else:
            print(f"  Status check failed: {resp.status_code}")
        time.sleep(2)

    if not final_status:
        print("  [WARN] Timeout waiting for completion")
        # Try to stop the session
        requests.post(f"{BASE_URL}/sessions/stop", json={"session_id": session_id}, headers=headers)

    # Step 5: Get backtest results
    print("\n[5] Getting execution status (final)...")
    resp = requests.get(f"{BASE_URL}/sessions/execution-status", headers=headers, timeout=10)

    if resp.status_code == 200:
        result_data = resp.json()
        # Handle wrapped response
        if result_data.get("type") == "response":
            results = result_data.get("data", {})
        else:
            results = result_data

        print(f"  Results: {json.dumps(results, indent=2)[:1500]}")

        # Check for signals
        signals_count = results.get("signals_count", 0)
        trades_count = results.get("trades_count", 0)
        signals = results.get("signals", [])

        print(f"\n[6] SUMMARY:")
        print(f"  Signals generated: {signals_count or len(signals)}")
        print(f"  Trades executed: {trades_count}")

        if signals_count or signals:
            print("  [OK] Signals were generated!")
            for sig in signals[:5]:
                print(f"    - {sig.get('signal_type')}: {sig.get('symbol')} @ {sig.get('price')}")
        else:
            print("  [FAIL] No signals generated!")
            print("  Check backend logs for diagnostic messages")
            print(f"  Full status: {json.dumps(results, indent=2)}")
    else:
        print(f"  [FAIL] Get results failed: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_api_backtest_signals()
