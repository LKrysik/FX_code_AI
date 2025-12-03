"""
E2E Tests for Transaction History API Routes
=============================================

Tests for /api/transactions/history endpoint.

Coverage:
- GET /api/transactions/history - List transactions with filtering
- Status filtering (FILLED, CANCELLED, FAILED)
- Side filtering (BUY, SELL)
- Summary statistics
"""

import pytest
from fastapi.testclient import TestClient


class TestTransactionsHistoryEndpoint:
    """Tests for GET /api/transactions/history endpoint."""

    def test_get_transaction_history_success(self, api_client: TestClient, test_session_id: str):
        """Test successful retrieval of transaction history."""
        response = api_client.get(f"/api/transactions/history?session_id={test_session_id}&limit=10")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "transactions" in data
        assert "total_count" in data
        assert "summary" in data
        assert isinstance(data["transactions"], list)
        assert data["session_id"] == test_session_id

    def test_get_transaction_history_with_status_filter(self, api_client: TestClient, test_session_id: str):
        """Test transaction history filtered by status."""
        response = api_client.get(
            f"/api/transactions/history?session_id={test_session_id}&status=FILLED&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # All returned transactions should match the filter
        for tx in data["transactions"]:
            assert tx["status"] == "FILLED"

    def test_get_transaction_history_with_side_filter(self, api_client: TestClient, test_session_id: str):
        """Test transaction history filtered by side."""
        response = api_client.get(
            f"/api/transactions/history?session_id={test_session_id}&side=BUY&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # All returned transactions should match the filter
        for tx in data["transactions"]:
            assert tx["side"] == "BUY"

    def test_get_transaction_history_failed_filter(self, api_client: TestClient, test_session_id: str):
        """Test filtering failed transactions."""
        response = api_client.get(
            f"/api/transactions/history?session_id={test_session_id}&status=FAILED&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        for tx in data["transactions"]:
            assert tx["status"] in ("FAILED", "REJECTED")

    def test_get_transaction_history_summary_statistics(self, api_client: TestClient, test_session_id: str):
        """Test that summary statistics are calculated correctly."""
        response = api_client.get(f"/api/transactions/history?session_id={test_session_id}&limit=100")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        summary = data["summary"]
        assert "total_filled" in summary
        assert "total_cancelled" in summary
        assert "total_failed" in summary
        assert "total_commission" in summary

        # Verify counts add up
        total_transactions = len(data["transactions"])
        total_counted = summary["total_filled"] + summary["total_cancelled"] + summary["total_failed"]
        assert total_counted <= total_transactions

    def test_get_transaction_history_includes_slippage(self, api_client: TestClient, test_session_id: str):
        """Test that transaction includes slippage calculation."""
        response = api_client.get(f"/api/transactions/history?session_id={test_session_id}&limit=10")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        for tx in data["transactions"]:
            # Slippage is calculated as filled_price - requested_price
            if tx["filled_price"] and tx["price"]:
                expected_slippage = tx["filled_price"] - tx["price"]
                if tx["slippage"] is not None:
                    assert abs(tx["slippage"] - expected_slippage) < 0.01

    def test_get_transaction_history_limit_respected(self, api_client: TestClient, test_session_id: str):
        """Test that limit parameter is respected."""
        limit = 5
        response = api_client.get(f"/api/transactions/history?session_id={test_session_id}&limit={limit}")

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert len(data["transactions"]) <= limit

    def test_get_transaction_history_missing_session_id(self, api_client: TestClient):
        """Test error when session_id is missing."""
        response = api_client.get("/api/transactions/history")

        assert response.status_code == 422  # Validation error


@pytest.fixture
def test_session_id():
    """Provide a test session ID (should exist in test database)."""
    return "test_session_001"
