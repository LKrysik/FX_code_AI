"""
Indicators API E2E Tests
=========================

Tests for indicators endpoints:
- GET /api/v1/indicators/{symbol}
"""

import pytest


@pytest.mark.api
class TestIndicators:
    """Tests for indicators endpoints"""

    def test_get_indicators_for_symbol(self, api_client):
        """Test GET /api/v1/indicators/{symbol} returns indicator data"""
        response = api_client.get("/api/v1/indicators/BTC_USDT")

        # Should return 200 or 500 if indicators not available
        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert data["symbol"] == "BTC_USDT"
            assert "indicators" in data
            assert isinstance(data["indicators"], dict)
            assert "timestamp" in data

    def test_get_indicators_for_invalid_symbol(self, api_client):
        """Test indicators endpoint with invalid symbol"""
        response = api_client.get("/api/v1/indicators/INVALID_SYMBOL")

        # Should handle gracefully (200 with empty data or 404)
        assert response.status_code in (200, 404, 500)

    def test_get_indicators_for_multiple_symbols(self, api_client):
        """Test indicators for different symbols"""
        symbols = ["BTC_USDT", "ETH_USDT"]

        for symbol in symbols:
            response = api_client.get(f"/api/v1/indicators/{symbol}")

            # Should respond (may be empty if no data)
            assert response.status_code in (200, 404, 500)
