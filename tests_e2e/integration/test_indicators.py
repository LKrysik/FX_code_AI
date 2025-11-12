"""
Indicators API E2E Tests
=========================

Tests for indicators endpoints:
- GET /api/v1/indicators/{symbol}
"""

import pytest


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestIndicators:
    """Tests for indicators endpoints"""

    def test_get_indicators_for_symbol(self, api_client):
        """Test GET /api/v1/indicators/{symbol} returns indicator data"""
        response = api_client.get("/api/v1/indicators/BTC_USDT")

        assert response.status_code == 200
        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "symbol" in data
        assert data["symbol"] == "BTC_USDT"
        assert "indicators" in data
        assert isinstance(data["indicators"], dict)
        assert "timestamp" in data

    def test_get_indicators_for_invalid_symbol(self, api_client):
        """Test indicators endpoint with invalid symbol"""
        response = api_client.get("/api/v1/indicators/INVALID_SYMBOL")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    @pytest.mark.parametrize("symbol", ["BTC_USDT", "ETH_USDT"])
    def test_get_indicators_for_multiple_symbols(self, api_client, symbol):
        """Test indicators for different symbols"""
        response = api_client.get(f"/api/v1/indicators/{symbol}")

        assert response.status_code == 200
        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "symbol" in data
        assert data["symbol"] == symbol
        assert "indicators" in data
        assert isinstance(data["indicators"], dict)
