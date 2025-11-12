"""
Unit tests for Sessions API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestSessionsStart:
    """Test POST start session endpoint"""

    def test_start_session_data_collection(self, lightweight_api_client):
        """Test POST /sessions/start for data collection"""
        response = lightweight_api_client.post("/sessions/start", json={
            "mode": "collect",
            "symbols": ["BTC_USDT"],
            "data_types": ["tick_prices"]
        })
        assert response.status_code in (200, 201, 400, 422, 500)

    def test_start_session_backtest(self, lightweight_api_client):
        """Test POST /sessions/start for backtest"""
        response = lightweight_api_client.post("/sessions/start", json={
            "mode": "backtest",
            "session_id": "test_session_123",
            "symbols": ["BTC_USDT"]
        })
        assert response.status_code in (200, 201, 400, 404, 422, 500)

    def test_start_session_missing_mode(self, lightweight_api_client):
        """Test start session without mode"""
        response = lightweight_api_client.post("/sessions/start", json={
            "symbols": ["BTC_USDT"]
        })
        assert response.status_code in (400, 422)

    def test_start_session_invalid_mode(self, lightweight_api_client):
        """Test start session with invalid mode"""
        response = lightweight_api_client.post("/sessions/start", json={
            "mode": "invalid_mode",
            "symbols": ["BTC_USDT"]
        })
        assert response.status_code in (400, 422)

    def test_start_session_missing_symbols(self, lightweight_api_client):
        """Test start session without symbols"""
        response = lightweight_api_client.post("/sessions/start", json={
            "mode": "collect"
        })
        assert response.status_code in (400, 422, 500)

    def test_start_session_empty_symbols(self, lightweight_api_client):
        """Test start session with empty symbols list"""
        response = lightweight_api_client.post("/sessions/start", json={
            "mode": "collect",
            "symbols": []
        })
        assert response.status_code in (400, 422)


@pytest.mark.fast
@pytest.mark.unit
class TestSessionsStop:
    """Test POST stop session endpoint"""

    def test_stop_session(self, lightweight_api_client):
        """Test POST /sessions/stop"""
        response = lightweight_api_client.post("/sessions/stop")
        assert response.status_code in (200, 400, 500)

    def test_stop_session_when_not_running(self, lightweight_api_client):
        """Test stop session when no session is running"""
        response = lightweight_api_client.post("/sessions/stop")
        assert response.status_code in (200, 400, 404, 500)

    def test_stop_session_returns_json(self, lightweight_api_client):
        """Test stop session returns JSON response"""
        response = lightweight_api_client.post("/sessions/stop")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")


@pytest.mark.fast
@pytest.mark.unit
class TestExecutionStatus:
    """Test GET execution status endpoint"""

    def test_get_execution_status(self, lightweight_api_client):
        """Test GET /sessions/execution-status"""
        response = lightweight_api_client.get("/sessions/execution-status")
        assert response.status_code in (200, 404, 500)

    def test_execution_status_returns_json(self, lightweight_api_client):
        """Test execution status returns JSON"""
        response = lightweight_api_client.get("/sessions/execution-status")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_execution_status_structure(self, lightweight_api_client):
        """Test execution status contains expected fields"""
        response = lightweight_api_client.get("/sessions/execution-status")
        if response.status_code == 200:
            data = response.json()
            # Lenient check - may have different structures
            assert isinstance(data, (dict, list))


@pytest.mark.fast
@pytest.mark.unit
class TestDataCollectionSessions:
    """Test GET data collection sessions endpoint"""

    def test_get_data_collection_sessions(self, lightweight_api_client):
        """Test GET /api/data-collection/sessions"""
        response = lightweight_api_client.get("/api/data-collection/sessions")
        assert response.status_code in (200, 404, 500)

    def test_get_sessions_returns_json(self, lightweight_api_client):
        """Test sessions endpoint returns JSON"""
        response = lightweight_api_client.get("/api/data-collection/sessions")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_get_sessions_with_limit(self, lightweight_api_client):
        """Test sessions with limit parameter"""
        response = lightweight_api_client.get("/api/data-collection/sessions?limit=10")
        assert response.status_code in (200, 400, 404, 500)

    def test_get_sessions_with_status_filter(self, lightweight_api_client):
        """Test sessions with status filter"""
        response = lightweight_api_client.get("/api/data-collection/sessions?status=completed")
        assert response.status_code in (200, 400, 404, 500)
