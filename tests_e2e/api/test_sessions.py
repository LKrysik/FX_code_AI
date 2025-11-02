"""
Session Management API E2E Tests
=================================

Tests for session management endpoints:
- POST /sessions/start
- POST /sessions/stop
- GET /sessions/execution-status
- GET /sessions/{id}
"""

import pytest
import time


@pytest.mark.api
@pytest.mark.sessions
class TestSessionStart:
    """Tests for starting sessions"""

    def test_start_data_collection_session(self, authenticated_client, test_symbols):
        """Test starting a data collection session"""
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "30s"
                }
            }
        }

        response = authenticated_client.post("/sessions/start", json=session_config)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "session_id" in data["data"]
        assert "session_type" in data["data"]
        assert data["data"]["session_type"] == "collect"

    def test_start_session_requires_auth(self, api_client, test_symbols):
        """Test that starting a session requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {}
        }

        response = api_client.post("/sessions/start", json=session_config)

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.sessions
class TestSessionStop:
    """Tests for stopping sessions"""

    def test_stop_running_session(self, authenticated_client, test_symbols):
        """Test stopping a running session"""
        # Start a session first
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "5m"
                }
            }
        }

        start_response = authenticated_client.post("/sessions/start", json=session_config)
        assert start_response.status_code == 200

        session_id = start_response.json()["data"]["session_id"]

        # Wait a moment for session to initialize
        time.sleep(2)

        # Stop the session
        stop_response = authenticated_client.post("/sessions/stop", json={"session_id": session_id})

        assert stop_response.status_code == 200

        data = stop_response.json()
        assert "data" in data
        assert data["data"]["session_id"] == session_id

    def test_stop_non_existent_session_fails(self, authenticated_client):
        """Test stopping a non-existent session"""
        response = authenticated_client.post("/sessions/stop", json={"session_id": "non-existent-id"})

        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        assert "session_not_found" in data["error_code"]

    def test_stop_without_session_id_fails(self, authenticated_client):
        """Test stopping without session_id parameter"""
        response = authenticated_client.post("/sessions/stop", json={})

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data
        assert "invalid_request" in data["error_code"]

    def test_stop_session_requires_auth(self, api_client):
        """Test that stopping a session requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.post("/sessions/stop", json={"session_id": "any-id"})

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.sessions
class TestSessionExecutionStatus:
    """Tests for execution status endpoint"""

    def test_get_execution_status_idle(self, api_client):
        """Test getting execution status when no session is running"""
        response = api_client.get("/sessions/execution-status")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "status" in data["data"]
        # Should be idle when no session running
        assert data["data"]["status"] in ("idle", "stopped", "completed")

    def test_get_execution_status_running(self, authenticated_client, test_symbols):
        """Test getting execution status when session is running"""
        # Start a session
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "2m"
                }
            }
        }

        start_response = authenticated_client.post("/sessions/start", json=session_config)
        assert start_response.status_code == 200

        session_id = start_response.json()["data"]["session_id"]

        # Wait for session to start
        time.sleep(2)

        # Get execution status
        status_response = api_client.get("/sessions/execution-status")

        assert status_response.status_code == 200

        data = status_response.json()
        assert "data" in data
        status = data["data"]

        assert "status" in status
        assert status["status"] in ("running", "starting")
        assert "session_id" in status
        assert status["session_id"] == session_id

        # Cleanup: stop the session
        authenticated_client.post("/sessions/stop", json={"session_id": session_id})


@pytest.mark.api
@pytest.mark.sessions
class TestSessionDetails:
    """Tests for session details endpoint"""

    def test_get_session_by_id(self, authenticated_client, test_symbols):
        """Test getting session details by ID"""
        # Start a session
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "1m"
                }
            }
        }

        start_response = authenticated_client.post("/sessions/start", json=session_config)
        assert start_response.status_code == 200

        session_id = start_response.json()["data"]["session_id"]

        # Wait for session to initialize
        time.sleep(1)

        # Get session details
        details_response = api_client.get(f"/sessions/{session_id}")

        assert details_response.status_code == 200

        data = details_response.json()
        assert "data" in data or "status" in data

        # Cleanup
        authenticated_client.post("/sessions/stop", json={"session_id": session_id})

    def test_get_non_existent_session(self, api_client):
        """Test getting details for non-existent session"""
        response = api_client.get("/sessions/non-existent-id")

        assert response.status_code == 200

        data = response.json()
        # Should return no_active_session status
        assert "status" in data


@pytest.mark.api
@pytest.mark.sessions
@pytest.mark.slow
class TestSessionIntegration:
    """Integration tests for session lifecycle"""

    def test_session_lifecycle(self, authenticated_client, test_symbols):
        """Test complete session lifecycle: start → monitor → stop"""

        # Step 1: Verify idle state
        status1 = api_client.get("/sessions/execution-status")
        assert status1.status_code == 200

        # Step 2: Start session
        session_config = {
            "symbols": test_symbols,
            "session_type": "collect",
            "config": {
                "data_collection": {
                    "duration": "30s"
                }
            }
        }

        start_response = authenticated_client.post("/sessions/start", json=session_config)
        assert start_response.status_code == 200

        session_id = start_response.json()["data"]["session_id"]

        # Step 3: Wait for session to start
        time.sleep(2)

        # Step 4: Monitor execution status
        status2 = api_client.get("/sessions/execution-status")
        assert status2.status_code == 200

        running_status = status2.json()["data"]
        assert running_status["status"] in ("running", "starting")
        assert running_status["session_id"] == session_id

        # Step 5: Stop session
        stop_response = authenticated_client.post("/sessions/stop", json={"session_id": session_id})
        assert stop_response.status_code == 200

        # Step 6: Wait for cleanup
        time.sleep(1)

        # Step 7: Verify stopped state
        status3 = api_client.get("/sessions/execution-status")
        assert status3.status_code == 200

        final_status = status3.json()["data"]
        assert final_status["status"] in ("idle", "stopped", "completed")
