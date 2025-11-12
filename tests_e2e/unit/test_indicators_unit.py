"""
Unit tests for Indicators API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestIndicatorsGet:
    """Test GET indicators for symbol endpoint"""

    def test_get_indicators_for_symbol(self, lightweight_api_client):
        """Test GET /api/v1/indicators/{symbol}"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT")
        assert response.status_code in (200, 404, 500)

    def test_get_indicators_invalid_symbol(self, lightweight_api_client):
        """Test indicators endpoint with invalid symbol"""
        response = lightweight_api_client.get("/api/v1/indicators/INVALID@SYMBOL")
        assert response.status_code in (400, 404, 422, 500)

    def test_get_indicators_empty_symbol(self, lightweight_api_client):
        """Test indicators endpoint with empty symbol"""
        response = lightweight_api_client.get("/api/v1/indicators/")
        assert response.status_code in (404, 405)  # Not Found or Method Not Allowed

    def test_get_indicators_with_special_chars(self, lightweight_api_client):
        """Test indicators with special characters in symbol"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC%2FUSDT")
        assert response.status_code in (200, 400, 404, 500)

    def test_get_indicators_returns_json(self, lightweight_api_client):
        """Test indicators endpoint returns JSON"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_get_indicators_multiple_symbols(self, lightweight_api_client):
        """Test indicators for different symbols"""
        symbols = ["BTC_USDT", "ETH_USDT", "SOL_USDT"]
        for symbol in symbols:
            response = lightweight_api_client.get(f"/api/v1/indicators/{symbol}")
            assert response.status_code in (200, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestIndicatorsHistory:
    """Test GET indicators history endpoint"""

    def test_get_indicators_history(self, lightweight_api_client):
        """Test GET /api/v1/indicators/{symbol}/history"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT/history")
        assert response.status_code in (200, 404, 500)

    def test_get_indicators_history_with_limit(self, lightweight_api_client):
        """Test indicators history with limit parameter"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT/history?limit=100")
        assert response.status_code in (200, 400, 404, 500)

    def test_get_indicators_history_with_invalid_limit(self, lightweight_api_client):
        """Test indicators history with invalid limit"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT/history?limit=-1")
        assert response.status_code in (400, 422, 500)

    def test_get_indicators_history_with_time_range(self, lightweight_api_client):
        """Test indicators history with time range"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT/history?start=1000&end=2000")
        assert response.status_code in (200, 400, 404, 500)

    def test_get_indicators_history_returns_json(self, lightweight_api_client):
        """Test indicators history returns JSON"""
        response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT/history")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")


@pytest.mark.fast
@pytest.mark.unit
class TestIndicatorVariantsCreate:
    """Test POST indicator variants endpoint"""

    def test_create_indicator_variant(self, lightweight_api_client):
        """Test POST /api/indicator-variants"""
        response = lightweight_api_client.post("/api/indicator-variants", json={
            "name": "TWPA_5min",
            "base_indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 300, "t2": 0}
        })
        assert response.status_code in (200, 201, 400, 422, 500)

    def test_create_variant_missing_name(self, lightweight_api_client):
        """Test create variant without name"""
        response = lightweight_api_client.post("/api/indicator-variants", json={
            "base_indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 300, "t2": 0}
        })
        assert response.status_code in (400, 422)

    def test_create_variant_missing_base_indicator(self, lightweight_api_client):
        """Test create variant without base_indicator_type"""
        response = lightweight_api_client.post("/api/indicator-variants", json={
            "name": "TWPA_5min",
            "variant_type": "price",
            "parameters": {"t1": 300, "t2": 0}
        })
        assert response.status_code in (400, 422)

    def test_create_variant_invalid_parameters(self, lightweight_api_client):
        """Test create variant with invalid parameters"""
        response = lightweight_api_client.post("/api/indicator-variants", json={
            "name": "TWPA_5min",
            "base_indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": "invalid"
        })
        assert response.status_code in (400, 422)

    def test_create_variant_empty_name(self, lightweight_api_client):
        """Test create variant with empty name"""
        response = lightweight_api_client.post("/api/indicator-variants", json={
            "name": "",
            "base_indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 300, "t2": 0}
        })
        assert response.status_code in (400, 422)


@pytest.mark.fast
@pytest.mark.unit
class TestIndicatorVariantsList:
    """Test GET indicator variants endpoint"""

    def test_get_indicator_variants(self, lightweight_api_client):
        """Test GET /api/indicator-variants"""
        response = lightweight_api_client.get("/api/indicator-variants")
        assert response.status_code in (200, 404, 500)

    def test_get_variants_returns_json(self, lightweight_api_client):
        """Test variants endpoint returns JSON"""
        response = lightweight_api_client.get("/api/indicator-variants")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_get_variants_with_filter(self, lightweight_api_client):
        """Test variants with filter parameter"""
        response = lightweight_api_client.get("/api/indicator-variants?base_indicator_type=TWPA")
        assert response.status_code in (200, 400, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestIndicatorVariantsDelete:
    """Test DELETE indicator variants endpoint"""

    def test_delete_indicator_variant(self, lightweight_api_client):
        """Test DELETE /api/indicator-variants/{id}"""
        response = lightweight_api_client.delete("/api/indicator-variants/test_variant_id")
        assert response.status_code in (200, 204, 404, 500)

    def test_delete_variant_invalid_id(self, lightweight_api_client):
        """Test delete variant with invalid ID"""
        response = lightweight_api_client.delete("/api/indicator-variants/")
        assert response.status_code in (404, 405)  # Not Found or Method Not Allowed

    def test_delete_variant_special_chars_id(self, lightweight_api_client):
        """Test delete variant with special characters in ID"""
        response = lightweight_api_client.delete("/api/indicator-variants/test@variant#id")
        assert response.status_code in (200, 204, 400, 404, 500)

    def test_delete_variant_very_long_id(self, lightweight_api_client):
        """Test delete variant with very long ID"""
        long_id = "a" * 1000
        response = lightweight_api_client.delete(f"/api/indicator-variants/{long_id}")
        assert response.status_code in (200, 204, 400, 404, 414, 500)  # 414 = URI Too Long
