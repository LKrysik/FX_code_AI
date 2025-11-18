"""
E2E Tests for Signal History API Routes
========================================

Tests for /api/signals/history and /api/signals/{signal_id} endpoints.

Coverage:
- GET /api/signals/history - List signals with filtering
- GET /api/signals/{signal_id} - Get signal detail with linked order/position
"""

import pytest
from fastapi.testclient import TestClient


class TestSignalsHistoryEndpoint:
    """Tests for GET /api/signals/history endpoint."""

    def test_get_signal_history_success(self, client: TestClient, test_session_id: str):
        """Test successful retrieval of signal history."""
        response = client.get(f"/api/signals/history?session_id={test_session_id}&limit=10")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "signals" in data
        assert "total_count" in data
        assert isinstance(data["signals"], list)
        assert data["session_id"] == test_session_id

    def test_get_signal_history_with_symbol_filter(self, client: TestClient, test_session_id: str):
        """Test signal history filtered by symbol."""
        response = client.get(
            f"/api/signals/history?session_id={test_session_id}&symbol=BTC_USDT&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # All returned signals should match the filter
        for signal in data["signals"]:
            assert signal["symbol"] == "BTC_USDT"

    def test_get_signal_history_with_signal_type_filter(self, client: TestClient, test_session_id: str):
        """Test signal history filtered by signal type."""
        response = client.get(
            f"/api/signals/history?session_id={test_session_id}&signal_type=S1&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # All returned signals should match the filter
        for signal in data["signals"]:
            assert signal["signal_type"] == "S1"

    def test_get_signal_history_with_triggered_filter(self, client: TestClient, test_session_id: str):
        """Test signal history filtered by triggered status."""
        response = client.get(
            f"/api/signals/history?session_id={test_session_id}&triggered=true&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # All returned signals should match the filter
        for signal in data["signals"]:
            assert signal["triggered"] is True

    def test_get_signal_history_limit_respected(self, client: TestClient, test_session_id: str):
        """Test that limit parameter is respected."""
        limit = 5
        response = client.get(f"/api/signals/history?session_id={test_session_id}&limit={limit}")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert len(data["signals"]) <= limit

    def test_get_signal_history_missing_session_id(self, client: TestClient):
        """Test error when session_id is missing."""
        response = client.get("/api/signals/history")

        assert response.status_code == 422  # Validation error


class TestSignalDetailEndpoint:
    """Tests for GET /api/signals/{signal_id} endpoint."""

    def test_get_signal_detail_success(self, client: TestClient, test_signal_id: str):
        """Test successful retrieval of signal detail."""
        response = client.get(f"/api/signals/{test_signal_id}")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "signal" in data
        assert data["signal"]["signal_id"] == test_signal_id
        assert "indicator_values" in data["signal"]
        assert "conditions_met" in data["signal"]

    def test_get_signal_detail_with_linked_order(self, client: TestClient, test_signal_with_order_id: str):
        """Test signal detail includes linked order when available."""
        response = client.get(f"/api/signals/{test_signal_with_order_id}")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "order" in data
        if data["order"]:  # Order might not exist yet
            assert "order_id" in data["order"]
            assert "status" in data["order"]

    def test_get_signal_detail_not_found(self, client: TestClient):
        """Test error when signal does not exist."""
        response = client.get("/api/signals/nonexistent_signal_id")

        assert response.status_code == 404


@pytest.fixture
def test_session_id():
    """Provide a test session ID (should exist in test database)."""
    return "test_session_001"


@pytest.fixture
def test_signal_id():
    """Provide a test signal ID (should exist in test database)."""
    return "sig_test_001"


@pytest.fixture
def test_signal_with_order_id():
    """Provide a test signal ID that has a linked order."""
    return "sig_test_002"
