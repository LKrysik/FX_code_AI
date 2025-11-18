"""
E2E Tests for Chart Data API Routes
====================================

Tests for /api/chart/ohlcv and /api/chart/signals endpoints.

Coverage:
- GET /api/chart/ohlcv - Get OHLCV candlestick data
- GET /api/chart/signals - Get signal markers for chart overlay
- Interval validation
- Time filtering
"""

import pytest
from fastapi.testclient import TestClient


class TestChartOHLCVEndpoint:
    """Tests for GET /api/chart/ohlcv endpoint."""

    def test_get_ohlcv_success(self, client: TestClient, test_session_id: str):
        """Test successful retrieval of OHLCV data."""
        response = client.get(
            f"/api/chart/ohlcv?session_id={test_session_id}&symbol=BTC_USDT&interval=1m&limit=100"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "candles" in data
        assert "total_count" in data
        assert data["session_id"] == test_session_id
        assert data["symbol"] == "BTC_USDT"
        assert data["interval"] == "1m"

    def test_get_ohlcv_candle_structure(self, client: TestClient, test_session_id: str):
        """Test that candles have correct structure."""
        response = client.get(
            f"/api/chart/ohlcv?session_id={test_session_id}&symbol=BTC_USDT&interval=1m&limit=10"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        for candle in data["candles"]:
            assert "time" in candle  # Unix timestamp
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle

            # Validate OHLC relationships
            assert candle["high"] >= candle["low"]
            assert candle["high"] >= candle["open"]
            assert candle["high"] >= candle["close"]
            assert candle["low"] <= candle["open"]
            assert candle["low"] <= candle["close"]

    def test_get_ohlcv_different_intervals(self, client: TestClient, test_session_id: str):
        """Test OHLCV data with different intervals."""
        intervals = ["1m", "5m", "15m", "1h", "1d"]

        for interval in intervals:
            response = client.get(
                f"/api/chart/ohlcv?session_id={test_session_id}&symbol=BTC_USDT&interval={interval}&limit=10"
            )

            assert response.status_code == 200
            data = response.json().get("data", response.json())
            assert data["interval"] == interval

    def test_get_ohlcv_invalid_interval(self, client: TestClient, test_session_id: str):
        """Test error with invalid interval."""
        response = client.get(
            f"/api/chart/ohlcv?session_id={test_session_id}&symbol=BTC_USDT&interval=invalid&limit=10"
        )

        assert response.status_code == 400  # Bad request

    def test_get_ohlcv_limit_respected(self, client: TestClient, test_session_id: str):
        """Test that limit parameter is respected."""
        limit = 50
        response = client.get(
            f"/api/chart/ohlcv?session_id={test_session_id}&symbol=BTC_USDT&interval=1m&limit={limit}"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert len(data["candles"]) <= limit

    def test_get_ohlcv_missing_required_params(self, client: TestClient):
        """Test error when required parameters are missing."""
        # Missing session_id
        response = client.get("/api/chart/ohlcv?symbol=BTC_USDT")
        assert response.status_code == 422

        # Missing symbol
        response = client.get(f"/api/chart/ohlcv?session_id=test")
        assert response.status_code == 422


class TestChartSignalsEndpoint:
    """Tests for GET /api/chart/signals endpoint."""

    def test_get_chart_signals_success(self, client: TestClient, test_session_id: str):
        """Test successful retrieval of chart signal markers."""
        response = client.get(
            f"/api/chart/signals?session_id={test_session_id}&symbol=BTC_USDT"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        assert "markers" in data
        assert "total_count" in data
        assert data["session_id"] == test_session_id
        assert data["symbol"] == "BTC_USDT"

    def test_get_chart_signals_marker_structure(self, client: TestClient, test_session_id: str):
        """Test that signal markers have correct structure."""
        response = client.get(
            f"/api/chart/signals?session_id={test_session_id}&symbol=BTC_USDT"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        for marker in data["markers"]:
            assert "time" in marker
            assert "position" in marker  # 'aboveBar' or 'belowBar'
            assert "color" in marker
            assert "shape" in marker  # 'arrowUp', 'arrowDown', 'circle', 'square'
            assert "text" in marker
            assert "signal_id" in marker
            assert "signal_type" in marker

            # Validate position values
            assert marker["position"] in ("aboveBar", "belowBar")

            # Validate shape values
            assert marker["shape"] in ("arrowUp", "arrowDown", "circle", "square")

    def test_get_chart_signals_color_coding(self, client: TestClient, test_session_id: str):
        """Test that signal types have correct color coding."""
        response = client.get(
            f"/api/chart/signals?session_id={test_session_id}&symbol=BTC_USDT"
        )

        assert response.status_code == 200
        data = response.json().get("data", response.json())

        # Verify signal types have expected colors
        for marker in data["markers"]:
            if marker["signal_type"] == "S1":  # Entry
                assert marker["color"] == "#FFC107"  # Yellow
            elif marker["signal_type"] == "Z1":  # Zone
                assert marker["color"] == "#4CAF50"  # Green
            elif marker["signal_type"] == "ZE1":  # Zone Exit
                assert marker["color"] == "#2196F3"  # Blue
            elif marker["signal_type"] == "E1":  # Exit
                assert marker["color"] == "#F44336"  # Red
            elif marker["signal_type"] == "O1":  # Override
                assert marker["color"] == "#9C27B0"  # Purple
            elif marker["signal_type"] == "EMERGENCY":
                assert marker["color"] == "#FF5722"  # Deep Orange

    def test_get_chart_signals_missing_required_params(self, client: TestClient):
        """Test error when required parameters are missing."""
        # Missing session_id
        response = client.get("/api/chart/signals?symbol=BTC_USDT")
        assert response.status_code == 422

        # Missing symbol
        response = client.get(f"/api/chart/signals?session_id=test")
        assert response.status_code == 422


@pytest.fixture
def test_session_id():
    """Provide a test session ID (should exist in test database)."""
    return "test_session_001"
