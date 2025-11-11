"""
Risk Management API E2E Tests
==============================

Tests for risk management endpoints:
- GET /risk/budget
- GET /risk/budget/{strategy_name}
- POST /risk/budget/allocate
- POST /risk/emergency-stop
- POST /risk/assess-position
"""

import pytest


@pytest.mark.api
@pytest.mark.risk
class TestRiskBudget:
    """Tests for budget endpoints"""

    def test_get_budget_summary(self, authenticated_client):
        """Test GET /risk/budget returns budget summary"""
        response = authenticated_client.get("/risk/budget")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        budget_summary = data["data"]

        # Should have budget information
        assert isinstance(budget_summary, dict)
        # Budget summary should contain budget-related fields
        expected_fields = ["total_budget", "allocated", "available", "allocations", "usage"]
        has_budget_info = any(field in budget_summary for field in expected_fields)
        assert has_budget_info, "Budget summary should contain budget information"

    def test_get_strategy_budget_not_found(self, authenticated_client):
        """Test GET /risk/budget/{strategy_name} returns 404 for non-existent strategy"""
        response = authenticated_client.get("/risk/budget/non_existent_strategy")

        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        assert "not_found" in data["error_code"]


@pytest.mark.api
@pytest.mark.risk
class TestRiskBudgetAllocate:
    """Tests for budget allocation"""

    def test_allocate_budget_success(self, authenticated_client):
        """Test POST /risk/budget/allocate with valid data"""
        allocation_data = {
            "strategy_name": "test_strategy",
            "amount": 1000.0,
            "max_allocation_pct": 5.0
        }

        response = authenticated_client.post("/risk/budget/allocate", json=allocation_data)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["strategy_name"] == "test_strategy"
        assert data["data"]["amount"] == 1000.0

    def test_allocate_budget_missing_strategy_name(self, authenticated_client):
        """Test allocation fails without strategy_name"""
        allocation_data = {
            "amount": 1000.0
        }

        response = authenticated_client.post("/risk/budget/allocate", json=allocation_data)

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data
        assert "validation_error" in data["error_code"]

    def test_allocate_budget_missing_amount(self, authenticated_client):
        """Test allocation fails without amount"""
        allocation_data = {
            "strategy_name": "test_strategy"
        }

        response = authenticated_client.post("/risk/budget/allocate", json=allocation_data)

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data

    def test_allocate_budget_negative_amount(self, authenticated_client):
        """Test allocation fails with negative amount"""
        allocation_data = {
            "strategy_name": "test_strategy",
            "amount": -1000.0
        }

        response = authenticated_client.post("/risk/budget/allocate", json=allocation_data)

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data
        assert "validation_error" in data["error_code"]

    def test_allocate_budget_zero_amount(self, authenticated_client):
        """Test allocation fails with zero amount"""
        allocation_data = {
            "strategy_name": "test_strategy",
            "amount": 0
        }

        response = authenticated_client.post("/risk/budget/allocate", json=allocation_data)

        assert response.status_code == 400


@pytest.mark.api
@pytest.mark.risk
class TestRiskEmergencyStop:
    """Tests for emergency stop endpoint"""

    def test_emergency_stop_all_strategies(self, authenticated_client):
        """Test POST /risk/emergency-stop without specific strategy"""
        response = authenticated_client.post("/risk/emergency-stop", json={})

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "released_strategies" in data["data"]
        assert isinstance(data["data"]["released_strategies"], list)
        # Validate response contains emergency stop confirmation
        assert "status" in data["data"] or "message" in data["data"]

    def test_emergency_stop_specific_strategy(self, authenticated_client):
        """Test emergency stop for specific strategy"""
        response = authenticated_client.post("/risk/emergency-stop", json={
            "strategy_name": "test_strategy"
        })

        assert response.status_code == 200

        data = response.json()
        assert "data" in data


@pytest.mark.api
@pytest.mark.risk
class TestRiskAssessPosition:
    """Tests for position risk assessment"""

    def test_assess_position_risk_success(self, authenticated_client):
        """Test POST /risk/assess-position with valid data"""
        assessment_data = {
            "symbol": "BTC_USDT",
            "position_size": 100.0,
            "current_price": 50000.0,
            "volatility": 0.02,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.5
        }

        response = authenticated_client.post("/risk/assess-position", json=assessment_data)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        risk_assessment = data["data"]
        # Validate risk assessment contains assessment results
        assert isinstance(risk_assessment, dict)
        expected_fields = ["risk_score", "risk_level", "approved", "recommendation", "assessment"]
        has_assessment = any(field in risk_assessment for field in expected_fields)
        assert has_assessment, "Risk assessment should contain assessment results"
        result = data["data"]

        assert "symbol" in result
        assert result["symbol"] == "BTC_USDT"
        assert "risk_level" in result
        assert "var_95" in result
        assert "expected_return" in result
        assert "recommendation" in result

    def test_assess_position_missing_symbol(self, authenticated_client):
        """Test assessment fails without symbol"""
        assessment_data = {
            "position_size": 100.0
        }

        response = authenticated_client.post("/risk/assess-position", json=assessment_data)

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data
        assert "validation_error" in data["error_code"]

    def test_assess_position_negative_size(self, authenticated_client):
        """Test assessment fails with negative position size"""
        assessment_data = {
            "symbol": "BTC_USDT",
            "position_size": -100.0
        }

        response = authenticated_client.post("/risk/assess-position", json=assessment_data)

        assert response.status_code == 400

    def test_assess_position_zero_size(self, authenticated_client):
        """Test assessment fails with zero position size"""
        assessment_data = {
            "symbol": "BTC_USDT",
            "position_size": 0
        }

        response = authenticated_client.post("/risk/assess-position", json=assessment_data)

        assert response.status_code == 400


@pytest.mark.api
@pytest.mark.risk
class TestRiskRequiresAuth:
    """Tests that risk endpoints require authentication"""

    def test_risk_endpoints_require_auth(self, api_client):
        """Test all risk endpoints require authentication"""
        endpoints = [
            ('GET', '/risk/budget'),
            ('GET', '/risk/budget/test_strategy'),
            ('POST', '/risk/budget/allocate', {"strategy_name": "test", "amount": 100}),
            ('POST', '/risk/emergency-stop', {}),
            ('POST', '/risk/assess-position', {"symbol": "BTC_USDT", "position_size": 100}),
        ]

        # Clear auth header
        api_client.headers.pop("Authorization", None)

        for method, endpoint, *body_args in endpoints:
            body = body_args[0] if body_args else None

            if method == 'GET':
                response = api_client.get(endpoint)
            elif method == 'POST':
                response = api_client.post(endpoint, json=body)

            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"
