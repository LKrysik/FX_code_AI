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
import sys

# Import FastAPI test client
from fastapi.testclient import TestClient

# Import the unified app
from src.api.unified_server import create_unified_app


# ============================================================================
# PYTEST CONFIGURATION HOOK - QuestDB Health Check
# ============================================================================

def pytest_configure(config):
    """
    Run BEFORE any tests - check if QuestDB is available for integration tests.

    Skips check for unit tests (marked with @pytest.mark.fast).
    Only enforces QuestDB for integration tests (@pytest.mark.database).
    """
    # Skip health check if only running unit tests
    markers = config.option.markexpr or ""

    # Check if we're running only fast/unit tests (no database required)
    if "fast" in markers or "unit" in markers:
        if "database" not in markers and "integration" not in markers:
            print("\n[OK] Running unit tests only - QuestDB not required")
            return

    # Check if we're explicitly running integration/database tests
    running_database_tests = (
        "database" in markers or
        "integration" in markers or
        not markers  # No marker filter = running all tests
    )

    if not running_database_tests:
        return  # Don't check QuestDB for unit-only test runs

    print("\n[INFO] Checking QuestDB availability (required for integration tests)...")

    try:
        import socket

        def check_questdb_sync():
            """
            Synchronous QuestDB availability check (no asyncio).

            Uses socket connection to avoid event loop conflicts with pytest-asyncio.
            This check runs BEFORE pytest-asyncio sets up event loops.
            """
            try:
                # Try to connect to QuestDB PostgreSQL port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)  # 2 second timeout
                result = sock.connect_ex(('127.0.0.1', 8812))
                sock.close()

                if result == 0:
                    return True, None
                else:
                    return False, "Connection refused - QuestDB not running"
            except socket.timeout:
                return False, "Connection timeout - QuestDB not responding"
            except Exception as e:
                return False, f"{type(e).__name__}: {e}"

        success, error = check_questdb_sync()

        if success:
            print("[OK] QuestDB is running on port 8812\n")
        else:
            # QuestDB not available - fail with helpful message
            error_msg = (
                f"\n[FAIL] QuestDB is NOT running on port 8812\n"
                f"Error: {error}\n\n"
                f"Integration tests require QuestDB.\n\n"
                f"To start QuestDB:\n"
                f"  1. Install: python database/questdb/install_questdb.py\n"
                f"  2. Start: .\\start_all.ps1\n\n"
                f"Or run only unit tests (no database required):\n"
                f"  pytest -m fast\n"
                f"  pytest -m unit\n"
            )
            pytest.exit(error_msg, returncode=1)

    except ImportError:
        # socket is built-in, should never happen
        pytest.exit(
            "socket module not available (Python installation issue)",
            returncode=1
        )
    except Exception as e:
        # Unexpected error
        pytest.exit(
            f"QuestDB health check failed unexpectedly: {e}",
            returncode=1
        )


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
# LIGHTWEIGHT FIXTURES (for fast unit tests - no QuestDB)
# ============================================================================

@pytest.fixture(scope="session")
def mock_questdb_provider():
    """
    Lightweight QuestDB mock - no real database connection.

    Use for unit tests that don't need real data.
    For integration tests, use full stack with QuestDB.
    """
    from unittest.mock import AsyncMock, MagicMock
    from src.data_feed.questdb_provider import QuestDBProvider

    mock = MagicMock(spec=QuestDBProvider)

    # Mock async methods
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.is_healthy = AsyncMock(return_value=True)
    mock.execute_query = AsyncMock(return_value=[])
    mock.fetch_tick_prices = AsyncMock(return_value=[])
    mock.fetch_session_data = AsyncMock(return_value=[])

    # Mock attributes
    mock.pg_pool = MagicMock()
    mock._initialized = True

    return mock


@pytest.fixture(scope="session")
def test_settings():
    """
    Minimal settings for testing.

    Overrides production settings to use mock mode.
    """
    from src.infrastructure.config.settings import AppSettings, TradingMode

    settings = AppSettings()
    settings.trading.mode = TradingMode.BACKTEST  # Don't connect to real exchange
    settings.debug = True

    return settings


@pytest.fixture(scope="function")
def lightweight_container(mock_questdb_provider, test_settings):
    """
    Container with mocked QuestDB - no database required.

    Use for unit tests. For integration tests, use full container.
    """
    from src.infrastructure.container import Container
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger

    event_bus = EventBus()
    logger = StructuredLogger("Test", test_settings.logging)
    container = Container(test_settings, event_bus, logger)

    # Inject mock QuestDB provider (bypass initialization)
    container._singleton_services["questdb_provider"] = mock_questdb_provider

    return container


@pytest.fixture(scope="function")
def lightweight_app(lightweight_container):
    """
    FastAPI app with mocked dependencies - FAST (no QuestDB, no heavy initialization).

    Use for unit tests that only need to test API endpoint logic.
    For integration tests, use 'app' fixture with full initialization.

    Example:
        @pytest.mark.fast
        @pytest.mark.unit
        def test_get_indicators(lightweight_api_client):
            response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT")
            assert response.status_code == 200
    """
    from fastapi import FastAPI, Request
    from unittest.mock import MagicMock, AsyncMock
    from src.api.auth_handler import AuthHandler
    import os

    # Create minimal app (no lifespan startup)
    app = FastAPI(title="Test App", version="1.0.0")
    app.state.container = lightweight_container

    # Create mock AuthHandler for auth endpoints
    jwt_secret = os.getenv("JWT_SECRET", "test_secret_key_for_testing")
    mock_auth_handler = MagicMock(spec=AuthHandler)
    mock_auth_handler.token_expiry_hours = 24
    mock_auth_handler.refresh_token_expiry_days = 30

    # Mock authenticate_credentials to return test user
    async def mock_authenticate_credentials(username: str, password: str, client_ip: str):
        from src.api.auth_handler import AuthResult, UserSession, PermissionLevel
        from datetime import datetime, timedelta

        # Accept any credentials for unit tests
        if username and password:
            user_session = UserSession(
                user_id=f"test_user_{username}",
                username=username,
                permissions=["read_market_data"],
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                client_ip=client_ip,
                user_agent="TestClient",
                session_token="test_session_token",
                refresh_token="test_refresh_token",
                last_activity=datetime.now()
            )
            return AuthResult(
                success=True,
                user_session=user_session,
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            )
        else:
            from src.api.auth_handler import AuthResult
            return AuthResult(
                success=False,
                error_code="invalid_credentials",
                error_message="Invalid username or password"
            )

    mock_auth_handler.authenticate_credentials = mock_authenticate_credentials

    # Mock refresh_session
    async def mock_refresh_session(refresh_token: str, client_ip: str):
        from src.api.auth_handler import AuthResult, UserSession
        from datetime import datetime, timedelta

        if refresh_token:
            user_session = UserSession(
                user_id="test_user_refreshed",
                username="test_user",
                permissions=["read_market_data"],
                authenticated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                client_ip=client_ip,
                user_agent="TestClient",
                session_token="new_test_session_token",
                refresh_token="new_test_refresh_token",
                last_activity=datetime.now()
            )
            return AuthResult(
                success=True,
                user_session=user_session,
                access_token="new_test_access_token",
                refresh_token="new_test_refresh_token"
            )
        else:
            from src.api.auth_handler import AuthResult
            return AuthResult(
                success=False,
                error_code="invalid_refresh_token",
                error_message="Invalid refresh token"
            )

    mock_auth_handler.refresh_session = mock_refresh_session

    # Mock logout_session
    mock_auth_handler.logout_session = AsyncMock()

    # Create mock WebSocketAPIServer with auth_handler
    mock_ws_server = MagicMock()
    mock_ws_server.auth_handler = mock_auth_handler
    app.state.websocket_api_server = mock_ws_server

    # Register auth endpoints (inline from unified_server.py)
    from fastapi import Depends
    from fastapi.responses import JSONResponse

    def _json_ok(payload: dict, request_id: str = None) -> JSONResponse:
        """Helper to create success response"""
        body = {"type": "response", "data": payload}
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(content=body)

    def _json_error(code: str, message: str, status: int = 400, request_id: str = None) -> JSONResponse:
        """Helper to create error response"""
        body = {"type": "error", "error_code": code, "error_message": message}
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(content=body, status_code=status)

    # Register auth endpoints
    @app.post("/api/v1/auth/login")
    async def login(request: Request):
        """JWT login endpoint for testing"""
        try:
            body = await request.json()
        except Exception:
            return _json_error("validation_error", "Request body must be valid JSON", status=422)

        try:
            username = body.get("username")
            password = body.get("password")

            if not username or not password:
                return _json_error("validation_error", "username and password are required", status=422)

            client_ip = request.client.host if request.client else "127.0.0.1"
            auth_handler = app.state.websocket_api_server.auth_handler
            auth_result = await auth_handler.authenticate_credentials(username, password, client_ip)

            if not auth_result.success:
                return _json_error("authentication_failed", auth_result.error_message or "Invalid credentials", status=401)

            user_session = auth_result.user_session
            return _json_ok({
                "access_token": auth_result.access_token,
                "refresh_token": auth_result.refresh_token,
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "user_id": user_session.user_id,
                    "username": user_session.username,
                    "permissions": user_session.permissions
                }
            })
        except Exception as e:
            return _json_error("login_error", f"Login failed: {str(e)}", status=500)

    @app.post("/api/v1/auth/refresh")
    async def refresh_token_endpoint(request: Request):
        """Refresh token endpoint for testing"""
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token") or request.cookies.get("refresh_token")

            if not refresh_token:
                return _json_error("missing_refresh_token", "Refresh token not found", status=401)

            client_ip = request.client.host if request.client else "127.0.0.1"
            auth_handler = app.state.websocket_api_server.auth_handler
            auth_result = await auth_handler.refresh_session(refresh_token, client_ip)

            if not auth_result.success:
                return _json_error("refresh_failed", auth_result.error_message or "Invalid refresh token", status=401)

            user_session = auth_result.user_session
            return _json_ok({
                "access_token": auth_result.access_token,
                "refresh_token": auth_result.refresh_token,
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "user_id": user_session.user_id,
                    "username": user_session.username,
                    "permissions": user_session.permissions
                }
            })
        except Exception as e:
            return _json_error("refresh_error", f"Token refresh failed: {str(e)}", status=500)

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request):
        """Logout endpoint for testing"""
        try:
            auth_handler = app.state.websocket_api_server.auth_handler
            await auth_handler.logout_session("test_session")
            return _json_ok({"message": "Successfully logged out"})
        except Exception as e:
            return _json_error("logout_error", f"Logout failed: {str(e)}", status=500)

    # Register CSRF token endpoint
    @app.get("/csrf-token")
    async def get_csrf_token():
        """CSRF token endpoint for testing"""
        import secrets
        token = secrets.token_urlsafe(32)
        return _json_ok({"token": token})

    # ========================================================================
    # MOCK ENDPOINTS FOR UNIT TESTS
    # ========================================================================

    # Sessions endpoints
    @app.post("/sessions/start")
    async def mock_start_session(request: Request):
        """Mock start session endpoint"""
        try:
            body = await request.json()
        except Exception:
            return _json_error("validation_error", "Request body must be valid JSON", status=422)

        mode = body.get("mode")
        symbols = body.get("symbols")

        # Validate mode
        if not mode:
            return _json_error("validation_error", "mode is required", status=422)
        if mode not in ("collect", "backtest", "paper", "live", "data_collection"):
            return _json_error("validation_error", f"Invalid mode: {mode}. Must be one of: collect, backtest, paper, live", status=422)

        # Validate symbols
        if not symbols:
            return _json_error("validation_error", "symbols is required", status=422)
        if not isinstance(symbols, list) or len(symbols) == 0:
            return _json_error("validation_error", "symbols cannot be empty", status=422)

        return _json_ok({
            "session_id": "mock_session_123",
            "status": "started",
            "mode": mode,
            "symbols": symbols
        })

    @app.post("/sessions/stop")
    async def mock_stop_session(request: Request):
        """Mock stop session endpoint"""
        return _json_ok({
            "session_id": "mock_session_123",
            "status": "stopped"
        })

    @app.get("/sessions/execution-status")
    async def mock_execution_status():
        """Mock execution status endpoint"""
        return _json_ok({
            "session_id": "mock_session_123",
            "status": "idle",
            "mode": None,
            "symbols": []
        })

    # Strategies endpoints
    @app.get("/api/strategies")
    async def mock_list_strategies(enabled: bool = None):
        """Mock list strategies endpoint"""
        return _json_ok({
            "strategies": [],
            "total": 0
        })

    @app.get("/api/strategies/")
    async def mock_list_strategies_trailing_slash():
        """Mock for trailing slash - should return 404/405"""
        return _json_error("not_found", "Endpoint not found. Did you mean /api/strategies?", status=404)

    @app.post("/api/strategies")
    async def mock_create_strategy(request: Request):
        """Mock create strategy endpoint"""
        try:
            body = await request.json()
        except Exception:
            return _json_error("validation_error", "Request body must be valid JSON", status=422)

        strategy_name = body.get("strategy_name")
        direction = body.get("direction")

        # Validate name
        if not strategy_name:
            return _json_error("validation_error", "strategy_name is required", status=422)
        if not strategy_name.strip():
            return _json_error("validation_error", "strategy_name cannot be empty", status=422)

        # Validate direction if provided
        if direction and direction not in ("LONG", "SHORT", "BOTH"):
            return _json_error("validation_error", f"Invalid direction: {direction}. Must be LONG, SHORT, or BOTH", status=422)

        return JSONResponse(
            content={
                "type": "response",
                "data": {
                    "id": "strategy_123",
                    "strategy_name": strategy_name,
                    "description": body.get("description", ""),
                    "direction": direction or "LONG",
                    "enabled": body.get("enabled", False)
                }
            },
            status_code=201
        )

    @app.get("/api/strategies/{strategy_id}")
    async def mock_get_strategy(strategy_id: str):
        """Mock get strategy by ID endpoint"""
        if strategy_id == "test_strategy_id":
            return _json_ok({
                "id": strategy_id,
                "strategy_name": "Test Strategy",
                "description": "Test description",
                "direction": "LONG",
                "enabled": True
            })
        return _json_error("not_found", f"Strategy not found: {strategy_id}", status=404)

    @app.put("/api/strategies/{strategy_id}")
    async def mock_update_strategy(strategy_id: str, request: Request):
        """Mock update strategy endpoint"""
        try:
            body = await request.json()
        except Exception:
            return _json_error("validation_error", "Request body must be valid JSON", status=422)

        # Validate body is not empty
        if not body:
            return _json_error("validation_error", "Request body cannot be empty", status=422)

        # Validate direction if provided
        if "direction" in body and body["direction"] not in ("LONG", "SHORT", "BOTH"):
            return _json_error("validation_error", f"Invalid direction: {body['direction']}", status=422)

        # Validate enabled if provided
        if "enabled" in body and not isinstance(body["enabled"], bool):
            return _json_error("validation_error", "enabled must be a boolean", status=422)

        return _json_ok({
            "id": strategy_id,
            **body
        })

    @app.delete("/api/strategies/{strategy_id}")
    async def mock_delete_strategy(strategy_id: str):
        """Mock delete strategy endpoint"""
        return JSONResponse(content=None, status_code=204)

    @app.post("/api/strategies/{strategy_id}/activate")
    async def mock_activate_strategy(strategy_id: str):
        """Mock activate strategy endpoint"""
        return _json_ok({
            "id": strategy_id,
            "status": "activated",
            "enabled": True
        })

    @app.post("/api/strategies/{strategy_id}/deactivate")
    async def mock_deactivate_strategy(strategy_id: str):
        """Mock deactivate strategy endpoint"""
        return _json_ok({
            "id": strategy_id,
            "status": "deactivated",
            "enabled": False
        })

    # Indicator variants endpoints
    @app.get("/api/indicator-variants")
    async def mock_list_indicator_variants(base_indicator_type: str = None):
        """Mock list indicator variants endpoint"""
        return _json_ok({
            "variants": [],
            "total": 0
        })

    @app.post("/api/indicator-variants")
    async def mock_create_indicator_variant(request: Request):
        """Mock create indicator variant endpoint"""
        try:
            body = await request.json()
        except Exception:
            return _json_error("validation_error", "Request body must be valid JSON", status=422)

        name = body.get("name")
        base_indicator_type = body.get("base_indicator_type")
        parameters = body.get("parameters")

        # Validate name
        if not name:
            return _json_error("validation_error", "name is required", status=422)
        if not name.strip():
            return _json_error("validation_error", "name cannot be empty", status=422)

        # Validate base_indicator_type
        if not base_indicator_type:
            return _json_error("validation_error", "base_indicator_type is required", status=422)

        # Validate parameters if provided
        if parameters is not None and not isinstance(parameters, dict):
            return _json_error("validation_error", "parameters must be a dictionary", status=422)

        return JSONResponse(
            content={
                "type": "response",
                "data": {
                    "id": "variant_123",
                    "name": name,
                    "base_indicator_type": base_indicator_type,
                    "variant_type": body.get("variant_type", "custom"),
                    "parameters": parameters or {}
                }
            },
            status_code=201
        )

    @app.delete("/api/indicator-variants/{variant_id}")
    async def mock_delete_indicator_variant(variant_id: str):
        """Mock delete indicator variant endpoint"""
        return JSONResponse(content=None, status_code=204)

    # Indicator history endpoints (supplement indicators_routes.router)
    @app.get("/api/v1/indicators/{symbol}/history")
    async def mock_get_indicator_history(symbol: str, limit: int = 100):
        """Mock get indicator history endpoint"""
        # Validate limit
        if limit < 1 or limit > 10000:
            return _json_error("validation_error", f"limit must be between 1 and 10000, got {limit}", status=422)

        return _json_ok({
            "symbol": symbol,
            "history": [],
            "limit": limit
        })

    # Register routes WITHOUT heavy initialization
    # Import and include routers
    try:
        from src.api import (
            indicators_routes,
            data_analysis_routes,
        )

        app.include_router(indicators_routes.router, prefix="/api/v1/indicators", tags=["Indicators"])
        app.include_router(data_analysis_routes.router, prefix="/api/data-collection", tags=["Data Analysis"])

        # Try to import additional routes that may exist
        try:
            from src.api import monitoring_routes
            app.include_router(monitoring_routes.router, prefix="/health", tags=["Health"])
        except ImportError:
            pass

        try:
            from src.api import trading_routes
            app.include_router(trading_routes.router, prefix="/api/trading", tags=["Trading"])
        except ImportError:
            pass

        try:
            from src.api import paper_trading_routes
            app.include_router(paper_trading_routes.router, prefix="/api/paper-trading", tags=["Paper Trading"])
        except ImportError:
            pass

    except ImportError as e:
        # Some routes may not exist, that's OK for tests
        pass

    return app


@pytest.fixture(scope="function")
def lightweight_api_client(lightweight_app):
    """
    TestClient for lightweight app - FAST (no database, no auth).

    Use for unit tests. For integration tests with auth, use 'authenticated_client'.

    Example:
        @pytest.mark.fast
        def test_api_endpoint(lightweight_api_client):
            response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT")
            assert response.status_code == 200
    """
    from starlette.testclient import TestClient
    return TestClient(lightweight_app)


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

@pytest.fixture
def cleanup_strategies(api_client):
    """
    Manual cleanup for strategy tests.

    Use this fixture explicitly in tests that create strategies:
        def test_create_strategy(api_client, cleanup_strategies):
            # Test creates strategies
            # cleanup_strategies will delete them after test

    For tests that DON'T create strategies, omit this fixture.
    """
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
    except Exception as e:
        # Log cleanup failures for debugging (don't fail test)
        import logging
        logging.warning(f"Strategy cleanup failed: {type(e).__name__}: {e}")


@pytest.fixture
def cleanup_sessions(api_client):
    """
    Manual cleanup for session tests.

    Use this fixture explicitly in tests that start sessions:
        def test_start_session(api_client, cleanup_sessions):
            # Test starts a session
            # cleanup_sessions will stop it after test

    For tests that DON'T start sessions, omit this fixture.
    """
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
    except Exception as e:
        # Log cleanup failures for debugging (don't fail test)
        import logging
        logging.warning(f"Session cleanup failed: {type(e).__name__}: {e}")


# Convenience fixtures for common test patterns
@pytest.fixture
def strategy_test(api_client, cleanup_strategies):
    """
    Convenience fixture for strategy tests.

    Automatically includes cleanup_strategies.
    Use when test creates/modifies strategies.

    Example:
        def test_create_strategy(strategy_test):
            response = strategy_test.post("/api/strategies", json=strategy_data)
            assert response.status_code == 200
    """
    return api_client


@pytest.fixture
def session_test(api_client, cleanup_sessions):
    """
    Convenience fixture for session tests.

    Automatically includes cleanup_sessions.
    Use when test starts/stops sessions.

    Example:
        def test_start_session(session_test):
            response = session_test.post("/sessions/start", json=session_data)
            assert response.status_code == 200
    """
    return api_client


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

import time


@pytest.fixture(autouse=True)
def track_test_duration(request):
    """
    Track test execution time and warn on slow tests.

    Automatically runs for ALL tests.
    Logs warning if test takes > 1 second (for unit tests).
    """
    start_time = time.time()

    yield

    duration = time.time() - start_time
    test_name = request.node.nodeid

    # Get test markers
    markers = [m.name for m in request.node.iter_markers()]

    # Warn on slow tests
    if "fast" in markers and duration > 0.1:
        # Unit test should be < 100ms
        import logging
        logging.warning(
            f"SLOW UNIT TEST: {test_name} took {duration:.2f}s "
            f"(expected < 0.1s for @pytest.mark.fast tests)"
        )
    elif "unit" in markers and duration > 0.5:
        # Unit test should be < 500ms
        import logging
        logging.warning(
            f"SLOW UNIT TEST: {test_name} took {duration:.2f}s "
            f"(expected < 0.5s for @pytest.mark.unit tests)"
        )
    elif duration > 5.0:
        # Any test > 5s is concerning
        import logging
        logging.warning(
            f"SLOW TEST: {test_name} took {duration:.2f}s"
        )


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
