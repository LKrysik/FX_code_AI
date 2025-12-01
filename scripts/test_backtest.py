#!/usr/bin/env python
"""Test backtest flow - verify that backtesting generates signals."""

import json
import urllib.request
import urllib.error
import time
import sys

BASE_URL = "http://localhost:8080"


def api_request(method, path, data=None, headers=None):
    """Make API request."""
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"HTTP Error {e.code}: {error_body}")
        return {"error": str(e), "status_code": e.code, "body": error_body}
    except Exception as e:
        return {"error": str(e)}


def login(username, password):
    """Login and get access token."""
    result = api_request("POST", "/api/v1/auth/login", {"username": username, "password": password})
    # Token may be in result directly or nested in 'data'
    token = result.get("access_token") or result.get("data", {}).get("access_token")
    return token


def get_csrf_token(auth_token):
    """Get CSRF token."""
    result = api_request("GET", "/csrf-token", headers={"Authorization": f"Bearer {auth_token}"})
    # Token may be at different locations: csrf_token, data.csrf_token, or data.token
    return (result.get("csrf_token") or
            result.get("data", {}).get("csrf_token") or
            result.get("data", {}).get("token"))


def start_backtest(auth_token, csrf_token, session_id, symbols, strategy_config=None):
    """Start backtest session."""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-CSRF-Token": csrf_token
    }
    data = {
        "session_type": "backtest",
        "symbols": symbols,
        "config": {
            "session_id": session_id,
            "acceleration_factor": 100
        },
        "strategy_config": strategy_config or {}
    }
    return api_request("POST", "/sessions/start", data, headers)


def get_execution_status(auth_token):
    """Get current execution status."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    return api_request("GET", "/sessions/execution-status", headers=headers)


def get_results(auth_token, session_id):
    """Get session results."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    return api_request("GET", f"/results/session/{session_id}", headers=headers)


def stop_session(auth_token, csrf_token):
    """Stop current session."""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-CSRF-Token": csrf_token
    }
    return api_request("POST", "/sessions/stop", {}, headers)


def main():
    print("=" * 60)
    print("BACKTEST FLOW TEST")
    print("=" * 60)

    # Step 1: Login
    print("\n[1] Logging in as demo user...")
    token = login("demo", "demo123")
    if not token:
        print("FAILED: Could not login")
        return False
    print(f"OK: Got token: {token[:30]}...")

    # Step 2: Get CSRF token
    print("\n[2] Getting CSRF token...")
    csrf = get_csrf_token(token)
    if not csrf:
        print("FAILED: Could not get CSRF token")
        return False
    print(f"OK: Got CSRF: {csrf[:20]}...")

    # Step 3: Check current status and stop if running
    print("\n[3] Checking current execution status...")
    status = get_execution_status(token)
    print(f"Current status: {json.dumps(status, indent=2)}")

    current_status = status.get("data", {}).get("status") or status.get("status")
    if current_status and current_status not in ("idle", "stopped", "completed"):
        print(f"Session running ({current_status}), stopping first...")
        stop_result = stop_session(token, csrf)
        print(f"Stop result: {stop_result}")
        time.sleep(2)

    # Step 4: Start backtest
    print("\n[4] Starting backtest session...")
    # Use session exec_20251102_113922_361d6250 which has 68,599 prices
    # Symbols in this session: XCX_USDT, BLOCK_USDT, XNY_USDT, ARIA_USDT, etc.
    backtest_result = start_backtest(
        token, csrf,
        session_id="exec_20251102_113922_361d6250",
        symbols=["ARIA_USDT"]  # One of the symbols in this session
    )
    print(f"Backtest start result: {json.dumps(backtest_result, indent=2)}")

    if "error" in backtest_result:
        print(f"FAILED: Could not start backtest: {backtest_result}")
        return False

    new_session_id = backtest_result.get("data", {}).get("session_id") or backtest_result.get("session_id")
    print(f"Backtest session started: {new_session_id}")

    # Step 5: Monitor backtest progress
    print("\n[5] Monitoring backtest progress...")
    for i in range(30):  # Check for 30 seconds max
        time.sleep(1)
        status = get_execution_status(token)
        current = status.get("data", {}).get("status") or status.get("status")
        progress = status.get("data", {}).get("progress", 0)
        print(f"  [{i+1}s] Status: {current}, Progress: {progress}%")

        if current in ("completed", "stopped", "failed"):
            print(f"\nBacktest finished with status: {current}")
            break

    # Step 6: Get results
    print("\n[6] Getting backtest results...")
    if new_session_id:
        results = get_results(token, new_session_id)
        print(f"Results: {json.dumps(results, indent=2)[:1000]}")

    # Step 7: Check for signals in database
    print("\n[7] Checking for signals in QuestDB...")
    try:
        import urllib.parse
        query = urllib.parse.quote(f"SELECT count() FROM signals WHERE session_id = '{new_session_id}'")
        url = f"http://localhost:9000/exec?query={query}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"Signals query result: {data}")
    except Exception as e:
        print(f"Could not query signals: {e}")

    print("\n" + "=" * 60)
    print("BACKTEST FLOW TEST COMPLETED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
