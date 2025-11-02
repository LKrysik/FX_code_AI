"""
Wallet and Orders API E2E Tests
================================

Tests for trading-related endpoints:
- GET /wallet/balance
- GET /orders
- GET /orders/{order_id}
- GET /positions
- GET /positions/{symbol}
- GET /trading/performance
"""

import pytest


@pytest.mark.api
class TestWallet:
    """Tests for wallet endpoints"""

    def test_get_wallet_balance(self, authenticated_client):
        """Test GET /wallet/balance returns balance info"""
        response = authenticated_client.get("/wallet/balance")

        # Should return 200 or 503 if service unavailable
        assert response.status_code in (200, 503)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data

    def test_wallet_balance_requires_auth(self, api_client):
        """Test wallet balance requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/wallet/balance")

        assert response.status_code == 401


@pytest.mark.api
class TestOrders:
    """Tests for orders endpoints"""

    def test_get_all_orders(self, authenticated_client):
        """Test GET /orders returns list of orders"""
        response = authenticated_client.get("/orders")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "orders" in data["data"]
        assert isinstance(data["data"]["orders"], list)

    def test_get_order_by_id_not_found(self, authenticated_client):
        """Test GET /orders/{order_id} returns 404 for non-existent order"""
        response = authenticated_client.get("/orders/non_existent_order_id")

        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        assert "not_found" in data["error_code"]

    def test_orders_require_auth(self, api_client):
        """Test orders endpoints require authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/orders")

        assert response.status_code == 401


@pytest.mark.api
class TestPositions:
    """Tests for positions endpoints"""

    def test_get_all_positions(self, authenticated_client):
        """Test GET /positions returns list of positions"""
        response = authenticated_client.get("/positions")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "positions" in data["data"]
        assert isinstance(data["data"]["positions"], list)

    def test_get_position_by_symbol(self, authenticated_client):
        """Test GET /positions/{symbol} returns position info"""
        response = authenticated_client.get("/positions/BTC_USDT")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "position" in data["data"]

        # Position can be None if no position exists
        position = data["data"]["position"]
        assert position is None or isinstance(position, dict)

    def test_positions_require_auth(self, api_client):
        """Test positions endpoints require authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/positions")

        assert response.status_code == 401


@pytest.mark.api
class TestTradingPerformance:
    """Tests for trading performance endpoint"""

    def test_get_trading_performance(self, authenticated_client):
        """Test GET /trading/performance returns performance data"""
        response = authenticated_client.get("/trading/performance")

        # Should return 200 or 503 if service unavailable
        assert response.status_code in (200, 503)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data

    def test_trading_performance_requires_auth(self, api_client):
        """Test trading performance requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/trading/performance")

        assert response.status_code == 401
