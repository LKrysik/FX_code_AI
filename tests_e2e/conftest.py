"""
Shared pytest fixtures for all E2E tests
=========================================

Provides common fixtures for API testing, frontend testing, and integration tests.
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Generator
import httpx

# Import FastAPI test client
from fastapi.testclient import TestClient

# Import the unified app
from src.api.unified_server import create_unified_app


# ============================================================================
# SHARED CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Test configuration (session-scoped)"""
    return {
        "api_base_url": "http://localhost:8080",
        "frontend_base_url": "http://localhost:3000",
        "admin_username": "admin",
        "admin_password": "supersecret",
        "timeout": 30,  # seconds
    }


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to test fixtures directory"""
    return Path(__file__).parent / "fixtures"


# ============================================================================
# API FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def app():
    """Create FastAPI app instance for testing"""
    return create_unified_app()


@pytest.fixture(scope="function")
def api_client(app) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient for API testing with CSRF token.

    Usage:
        def test_endpoint(api_client):
            response = api_client.get("/health")
            assert response.status_code == 200
    """
    with TestClient(app) as client:
        # Get CSRF token for POST/PUT/DELETE requests
        csrf_token = None
        try:
            csrf_response = client.get("/csrf-token")
            if csrf_response.status_code == 200:
                csrf_data = csrf_response.json()
                csrf_token = csrf_data.get("data", {}).get("token")
        except Exception:
            # If CSRF token fetch fails, continue without it (some tests may not need it)
            pass

        if csrf_token:
            # Monkey-patch request methods to auto-include CSRF token
            original_post = client.post
            original_put = client.put
            original_patch = client.patch
            original_delete = client.delete

            def post_with_csrf(*args, **kwargs):
                kwargs.setdefault('headers', {})
                kwargs['headers']['X-CSRF-Token'] = csrf_token
                return original_post(*args, **kwargs)

            def put_with_csrf(*args, **kwargs):
                kwargs.setdefault('headers', {})
                kwargs['headers']['X-CSRF-Token'] = csrf_token
                return original_put(*args, **kwargs)

            def patch_with_csrf(*args, **kwargs):
                kwargs.setdefault('headers', {})
                kwargs['headers']['X-CSRF-Token'] = csrf_token
                return original_patch(*args, **kwargs)

            def delete_with_csrf(*args, **kwargs):
                kwargs.setdefault('headers', {})
                kwargs['headers']['X-CSRF-Token'] = csrf_token
                return original_delete(*args, **kwargs)

            client.post = post_with_csrf
            client.put = put_with_csrf
            client.patch = patch_with_csrf
            client.delete = delete_with_csrf

        yield client


@pytest.fixture(scope="function")
def authenticated_client(api_client, test_config) -> TestClient:
    """
    Authenticated API client with JWT token.

    Usage:
        def test_protected_endpoint(authenticated_client):
            response = authenticated_client.get("/api/strategies")
            assert response.status_code == 200
    """
    # Login to get access token
    login_response = api_client.post("/api/v1/auth/login", json={
        "username": test_config["admin_username"],
        "password": test_config["admin_password"]
    })

    assert login_response.status_code == 200

    data = login_response.json()
    access_token = data["data"]["access_token"]

    # Monkey-patch ALL request methods to include Authorization header
    # Store original methods (might be already patched with CSRF)
    original_request = api_client.request
    original_get = api_client.get
    original_post = api_client.post
    original_put = api_client.put
    original_patch = api_client.patch
    original_delete = api_client.delete

    def request_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_request(*args, **kwargs)

    def get_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_get(*args, **kwargs)

    def post_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_post(*args, **kwargs)

    def put_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_put(*args, **kwargs)

    def patch_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_patch(*args, **kwargs)

    def delete_with_auth(*args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = f"Bearer {access_token}"
        return original_delete(*args, **kwargs)

    api_client.request = request_with_auth
    api_client.get = get_with_auth
    api_client.post = post_with_auth
    api_client.put = put_with_auth
    api_client.patch = patch_with_auth
    api_client.delete = delete_with_auth

    return api_client


@pytest.fixture(scope="function")
def live_api_client(test_config) -> Generator[httpx.Client, None, None]:
    """
    HTTP client for testing against live backend server.

    Usage:
        def test_live_endpoint(live_api_client):
            response = live_api_client.get("/health")
            assert response.status_code == 200
    """
    with httpx.Client(base_url=test_config["api_base_url"], timeout=test_config["timeout"]) as client:
        yield client


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def valid_strategy_config() -> Dict[str, Any]:
    """Valid 5-section strategy configuration for testing"""
    return {
        "strategy_name": "Test Momentum Strategy",
        "description": "Test strategy for E2E testing",
        "direction": "LONG",  # Trading direction (LONG, SHORT, or BOTH)
        "s1_signal": {
            "conditions": [
                {
                    "id": "price_velocity_1",
                    "indicatorId": "price_velocity",
                    "operator": ">",
                    "value": 0.5
                }
            ]
        },
        "z1_entry": {
            "conditions": [
                {
                    "id": "price_velocity_entry",
                    "indicatorId": "price_velocity",
                    "operator": ">",
                    "value": 0.5
                }
            ],
            "positionSize": {
                "type": "percentage",
                "value": 10
            }
        },
        "ze1_close": {
            "conditions": [
                {
                    "id": "momentum_close",
                    "indicatorId": "momentum_reversal",
                    "operator": ">",
                    "value": 50.0
                }
            ]
        },
        "o1_cancel": {
            "timeoutSeconds": 300,
            "cooldownMinutes": 5,
            "conditions": [
                {
                    "id": "price_velocity_cancel",
                    "indicatorId": "price_velocity",
                    "operator": "<",
                    "value": -0.3
                }
            ]
        },
        "emergency_exit": {
            "conditions": [
                {
                    "id": "price_velocity_emergency",
                    "indicatorId": "price_velocity",
                    "operator": "<",
                    "value": -1.0
                }
            ],
            "cooldownMinutes": 60,
            "actions": {
                "cancelPending": True,
                "closePosition": True,
                "logEvent": True
            }
        }
    }


@pytest.fixture
def valid_short_strategy_config() -> Dict[str, Any]:
    """Valid SHORT strategy configuration for testing pump & dump detection"""
    return {
        "strategy_name": "Test SHORT Pump Dump Strategy",
        "description": "Test SHORT strategy for E2E testing",
        "direction": "SHORT",  # SHORT selling strategy
        "s1_signal": {
            "conditions": [
                {
                    "id": "pump_magnitude",
                    "indicatorId": "pump_magnitude_pct",
                    "operator": ">=",
                    "value": 15.0
                },
                {
                    "id": "volume_surge",
                    "indicatorId": "volume_surge_ratio",
                    "operator": ">=",
                    "value": 3.0
                }
            ]
        },
        "z1_entry": {
            "conditions": [],
            "positionSize": {
                "type": "percentage",
                "value": 2.0  # Conservative sizing for SHORT
            },
            "timeoutSeconds": 60
        },
        "ze1_close": {
            "conditions": [
                {
                    "id": "momentum_close",
                    "indicatorId": "momentum_reversal",
                    "operator": "<",
                    "value": -50.0
                }
            ]
        },
        "o1_cancel": {
            "timeoutSeconds": 300,
            "cooldownMinutes": 5,
            "conditions": [
                {
                    "id": "momentum_continues",
                    "indicatorId": "momentum_reversal",
                    "operator": "<",
                    "value": -20.0
                }
            ]
        },
        "emergency_exit": {
            "conditions": [
                {
                    "id": "emergency_reversal",
                    "indicatorId": "momentum_reversal",
                    "operator": ">=",
                    "value": 50.0
                }
            ],
            "cooldownMinutes": 60,
            "actions": {
                "cancelPending": True,
                "closePosition": True,
                "logEvent": True
            }
        }
    }


@pytest.fixture
def test_symbols() -> list[str]:
    """Default test symbols"""
    return ["BTC_USDT", "ETH_USDT"]


@pytest.fixture
def test_session_config() -> Dict[str, Any]:
    """Default test session configuration"""
    return {
        "symbols": ["BTC_USDT"],
        "session_type": "collect",
        "config": {
            "data_collection": {
                "duration": "30s"
            }
        }
    }


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_strategies(api_client):
    """Auto-cleanup: Delete all test strategies after each test"""
    yield

    # Cleanup after test
    try:
        # Get auth token (login)
        login_response = api_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "supersecret"
        })

        if login_response.status_code == 200:
            token = login_response.json()["data"]["access_token"]
            api_client.headers["Authorization"] = f"Bearer {token}"

            # Get all strategies
            list_response = api_client.get("/api/strategies")
            if list_response.status_code == 200:
                strategies = list_response.json()["data"]["strategies"]

                # Delete each strategy
                for strategy in strategies:
                    api_client.delete(f"/api/strategies/{strategy['id']}")
    except Exception:
        # Ignore cleanup errors
        pass


@pytest.fixture(autouse=True)
def cleanup_sessions(api_client):
    """Auto-cleanup: Stop all running sessions after each test"""
    yield

    # Cleanup after test
    try:
        # Check execution status
        status_response = api_client.get("/sessions/execution-status")
        if status_response.status_code == 200:
            status = status_response.json()["data"]

            # Stop if running
            if status.get("status") not in ("idle", "stopped", "completed"):
                session_id = status.get("session_id")
                if session_id:
                    # Login first
                    login_response = api_client.post("/api/v1/auth/login", json={
                        "username": "admin",
                        "password": "supersecret"
                    })

                    if login_response.status_code == 200:
                        token = login_response.json()["data"]["access_token"]
                        api_client.headers["Authorization"] = f"Bearer {token}"

                        # Stop session
                        api_client.post("/sessions/stop", json={"session_id": session_id})
    except Exception:
        # Ignore cleanup errors
        pass


# ============================================================================
# ASYNC EVENT LOOP - Removed (conflicts with pytest-asyncio auto mode)
# ============================================================================
# pytest-asyncio with asyncio_mode=auto provides automatic event loop management
# Custom event_loop fixture was causing conflicts and has been removed


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def load_fixture_json(fixtures_dir):
    """Load JSON fixture file"""
    def _load(filename: str) -> Dict[str, Any]:
        filepath = fixtures_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Fixture not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    return _load


@pytest.fixture
def assert_response_ok():
    """Helper to assert successful API response"""
    def _assert(response, expected_status=200):
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"

        data = response.json()
        assert "data" in data or "error_code" not in data, f"Response contains error: {data}"

        return data

    return _assert


@pytest.fixture
def assert_response_error():
    """Helper to assert error API response"""
    def _assert(response, expected_status=400, expected_error_code=None):
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"

        data = response.json()
        assert "error_code" in data, f"Expected error response, got: {data}"

        if expected_error_code:
            assert data["error_code"] == expected_error_code, f"Expected error code {expected_error_code}, got {data['error_code']}"

        return data

    return _assert
