"""
Miscellaneous API E2E Tests
============================

Tests for other endpoints:
- GET /symbols
- GET /metrics
- GET /metrics/health
- GET /alerts
- POST /alerts/{alert_id}/resolve
- GET /market-data
- GET /strategies/status
- GET /csrf-token
"""

import pytest


@pytest.mark.api
class TestSymbols:
    """Tests for symbols endpoint"""

    def test_get_symbols(self, api_client):
        """Test GET /symbols returns list of trading symbols"""
        response = api_client.get("/symbols")

        assert response.status_code == 200

        response_json = response.json()
        # Response format: {"status": "symbols", "data": {"symbols": [...]}}
        # Extract the data field which contains symbols
        data = response_json.get("data", response_json)

        print(f"DEBUG: response_json type: {type(response_json)}")
        print(f"DEBUG: response_json keys: {response_json.keys() if isinstance(response_json, dict) else 'N/A'}")
        print(f"DEBUG: data type: {type(data)}")
        print(f"DEBUG: data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
        print(f"DEBUG: 'data' in response_json: {'data' in response_json if isinstance(response_json, dict) else 'N/A'}")
        print(f"DEBUG: data is response_json: {data is response_json}")

        assert "symbols" in data
        assert isinstance(data["symbols"], list)

        # Should have at least some symbols
        symbols = data["symbols"]
        if len(symbols) > 0:
            # Symbols should be uppercase strings
            assert all(isinstance(s, str) for s in symbols)


@pytest.mark.api
class TestMetrics:
    """Tests for metrics endpoints"""

    def test_get_metrics_health(self, api_client):
        """Test GET /metrics/health returns health metrics"""
        response = api_client.get("/metrics/health")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        # Validate health metrics structure
        metrics_data = data["data"]
        # Health metrics should contain system health information
        assert isinstance(metrics_data, dict)
        # Common health metric fields
        expected_fields = ["status", "checks", "components", "uptime"]
        has_health_fields = any(field in metrics_data for field in expected_fields)
        assert has_health_fields, "Health metrics should contain at least one health-related field"


@pytest.mark.api
class TestAlerts:
    """Tests for alerts endpoints"""

    def test_get_active_alerts(self, api_client):
        """Test GET /alerts returns active alerts"""
        response = api_client.get("/alerts")

        assert response.status_code == 200

        response_json = response.json()
        # Response format: {"status": "active_alerts", "data": {"alerts": []}}
        # Extract the data field which contains alerts
        data = response_json.get("data", response_json)

        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_resolve_alert_not_found(self, api_client):
        """Test POST /alerts/{alert_id}/resolve for non-existent alert"""
        response = api_client.post("/alerts/non_existent_alert/resolve")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response


@pytest.mark.api
class TestMarketData:
    """Tests for market data endpoint"""

    def test_get_market_data(self, api_client):
        """Test GET /market-data returns market data"""
        response = api_client.get("/market-data")

        assert response.status_code == 200

        response_json = response.json()
        # Response format: {"status": "market_data", "data": [...]}
        # The data field contains the list directly
        market_data = response_json.get("data", response_json) if isinstance(response_json, dict) else response_json

        assert isinstance(market_data, list)

        # Market data should be list of symbol data
        if len(market_data) > 0:
            market_item = market_data[0]
            assert "symbol" in market_item


@pytest.mark.api
class TestStrategiesStatus:
    """Tests for strategies status endpoint"""

    def test_get_strategies_status(self, api_client):
        """Test GET /strategies/status returns strategy status"""
        response = api_client.get("/strategies/status")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "strategies" in data["data"]
        assert isinstance(data["data"]["strategies"], list)


@pytest.mark.api
class TestCSRF:
    """Tests for CSRF token endpoint"""

    def test_get_csrf_token(self, api_client):
        """Test GET /csrf-token returns CSRF token"""
        response = api_client.get("/csrf-token")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "token" in data["data"]
        assert isinstance(data["data"]["token"], str)
        assert len(data["data"]["token"]) > 0

    def test_csrf_tokens_are_unique(self, api_client):
        """Test that CSRF tokens are unique"""
        response1 = api_client.get("/csrf-token")
        response2 = api_client.get("/csrf-token")

        assert response1.status_code == 200
        assert response2.status_code == 200

        token1 = response1.json()["data"]["token"]
        token2 = response2.json()["data"]["token"]

        # Tokens should be different (randomly generated)
        assert token1 != token2
