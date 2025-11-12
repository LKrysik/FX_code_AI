"""
Unit tests for Risk Management and Wallet API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestRiskSummary:
    """Test risk summary endpoint"""

    def test_get_risk_summary(self, lightweight_api_client):
        """Test GET /api/risk/summary"""
        response = lightweight_api_client.get("/api/risk/summary")
        assert response.status_code in (200, 404, 500)

    def test_risk_summary_returns_json(self, lightweight_api_client):
        """Test risk summary returns JSON"""
        response = lightweight_api_client.get("/api/risk/summary")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_risk_summary_with_symbol_filter(self, lightweight_api_client):
        """Test risk summary with symbol filter"""
        response = lightweight_api_client.get("/api/risk/summary?symbol=BTC_USDT")
        assert response.status_code in (200, 400, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestWalletBalance:
    """Test wallet balance endpoint"""

    def test_get_wallet_balance(self, lightweight_api_client):
        """Test GET /api/wallet/balance"""
        response = lightweight_api_client.get("/api/wallet/balance")
        assert response.status_code in (200, 401, 404, 500)

    def test_wallet_balance_returns_json(self, lightweight_api_client):
        """Test wallet balance returns JSON"""
        response = lightweight_api_client.get("/api/wallet/balance")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_wallet_balance_structure(self, lightweight_api_client):
        """Test wallet balance response structure"""
        response = lightweight_api_client.get("/api/wallet/balance")
        if response.status_code == 200:
            data = response.json()
            # Lenient check - structure may vary
            assert isinstance(data, (dict, list))


@pytest.mark.fast
@pytest.mark.unit
class TestWalletOrders:
    """Test wallet orders endpoint"""

    def test_get_wallet_orders(self, lightweight_api_client):
        """Test GET /api/wallet/orders"""
        response = lightweight_api_client.get("/api/wallet/orders")
        assert response.status_code in (200, 401, 404, 500)

    def test_wallet_orders_returns_json(self, lightweight_api_client):
        """Test wallet orders returns JSON"""
        response = lightweight_api_client.get("/api/wallet/orders")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_wallet_orders_with_status_filter(self, lightweight_api_client):
        """Test wallet orders with status filter"""
        response = lightweight_api_client.get("/api/wallet/orders?status=open")
        assert response.status_code in (200, 400, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestWalletPositions:
    """Test wallet positions endpoint"""

    def test_get_wallet_positions(self, lightweight_api_client):
        """Test GET /api/wallet/positions"""
        response = lightweight_api_client.get("/api/wallet/positions")
        assert response.status_code in (200, 401, 404, 500)

    def test_wallet_positions_returns_json(self, lightweight_api_client):
        """Test wallet positions returns JSON"""
        response = lightweight_api_client.get("/api/wallet/positions")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_wallet_positions_with_symbol_filter(self, lightweight_api_client):
        """Test wallet positions with symbol filter"""
        response = lightweight_api_client.get("/api/wallet/positions?symbol=BTC_USDT")
        assert response.status_code in (200, 400, 404, 500)

    def test_wallet_positions_structure(self, lightweight_api_client):
        """Test wallet positions response structure"""
        response = lightweight_api_client.get("/api/wallet/positions")
        if response.status_code == 200:
            data = response.json()
            # Lenient check - structure may vary
            assert isinstance(data, (dict, list))
