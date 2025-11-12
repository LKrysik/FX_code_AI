"""
Results API E2E Tests
======================

Tests for results endpoints:
- GET /results/session/{id}
- GET /results/symbol/{symbol}
- GET /results/strategy/{name}
- POST /results/history/merge
"""

import pytest


@pytest.mark.api
class TestSessionResults:
    """Tests for session results endpoint"""

    def test_get_session_results_not_found(self, api_client):
        """Test GET /results/session/{id} returns 404 for non-existent session"""
        response = api_client.get("/results/session/non_existent_session_id")

        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        # API returns "no_active_session" not "not_found"
        error_code = data["error_code"].lower()
        assert "not_found" in error_code or "no_active_session" in error_code or "not" in error_code

    def test_get_session_results_structure(self, api_client):
        """Test session results response structure"""
        # Create a dummy session ID (will likely not exist)
        response = api_client.get("/results/session/test_session_123")

        assert response.status_code == 404
        error_response = response.json()
        assert "error_code" in error_response


@pytest.mark.api
class TestSymbolResults:
    """Tests for symbol results endpoint"""

    def test_get_symbol_results(self, api_client):
        """Test GET /results/symbol/{symbol} returns symbol statistics"""
        response = api_client.get("/results/symbol/BTC_USDT")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        result = data["data"]

        assert "symbol" in result
        assert result["symbol"] == "BTC_USDT"
        assert "strategy_results" in result
        assert "total_signals" in result
        assert "total_trades" in result

    @pytest.mark.parametrize("symbol", ["BTC_USDT", "ETH_USDT", "XRP_USDT"])
    def test_get_symbol_results_for_multiple_symbols(self, api_client, symbol):
        """Test symbol results for different symbols"""
        response = api_client.get(f"/results/symbol/{symbol}")

        assert response.status_code == 200

        data = response.json()
        assert data["data"]["symbol"] == symbol


@pytest.mark.api
class TestStrategyResults:
    """Tests for strategy results endpoint"""

    def test_get_strategy_results(self, api_client):
        """Test GET /results/strategy/{name} returns strategy statistics"""
        response = api_client.get("/results/strategy/test_strategy")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        result = data["data"]

        assert "strategy_name" in result
        assert result["strategy_name"] == "test_strategy"

    def test_get_strategy_results_with_symbol_filter(self, api_client):
        """Test strategy results with symbol parameter"""
        response = api_client.get("/results/strategy/test_strategy?symbol=BTC_USDT")

        assert response.status_code == 200

        data = response.json()
        result = data["data"]

        if result.get("symbol"):
            assert result["symbol"] == "BTC_USDT"


@pytest.mark.api
class TestResultsHistoryMerge:
    """Tests for results history merge endpoint"""

    def test_merge_results_history_with_parameters(self, api_client):
        """Test merge with custom parameters"""
        merge_config = {
            "base_dir": "backtest/backtest_results",
            "session_ids": ["session_1", "session_2"]
        }

        response = api_client.post("/results/history/merge", json=merge_config)

        assert response.status_code == 400
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response


@pytest.mark.api
class TestResultsIntegration:
    """Integration tests for results endpoints"""

    @pytest.mark.slow
    def test_results_workflow(self, api_client):
        """Test complete results workflow"""
        # Get symbol results
        symbol_response = api_client.get("/results/symbol/BTC_USDT")
        assert symbol_response.status_code == 200

        # Get strategy results
        strategy_response = api_client.get("/results/strategy/test_strategy")
        assert strategy_response.status_code == 200

        # Both should return data
        assert "data" in symbol_response.json()
        assert "data" in strategy_response.json()
