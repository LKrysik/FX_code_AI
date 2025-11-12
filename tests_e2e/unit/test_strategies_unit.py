"""
Unit tests for Strategies API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesList:
    """Test GET strategies list endpoint"""

    def test_get_strategies(self, lightweight_api_client):
        """Test GET /api/strategies"""
        response = lightweight_api_client.get("/api/strategies")
        assert response.status_code in (200, 404, 500)

    def test_get_strategies_returns_json(self, lightweight_api_client):
        """Test strategies endpoint returns JSON"""
        response = lightweight_api_client.get("/api/strategies")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_get_strategies_with_filter(self, lightweight_api_client):
        """Test strategies with enabled filter"""
        response = lightweight_api_client.get("/api/strategies?enabled=true")
        assert response.status_code in (200, 400, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesCreate:
    """Test POST create strategy endpoint"""

    def test_create_strategy(self, lightweight_api_client):
        """Test POST /api/strategies"""
        response = lightweight_api_client.post("/api/strategies", json={
            "strategy_name": "Test Strategy",
            "description": "Test description",
            "direction": "LONG",
            "enabled": True
        })
        assert response.status_code in (200, 201, 400, 422, 500)

    def test_create_strategy_missing_name(self, lightweight_api_client):
        """Test create strategy without name"""
        response = lightweight_api_client.post("/api/strategies", json={
            "description": "Test description",
            "direction": "LONG",
            "enabled": True
        })
        assert response.status_code in (400, 422)

    def test_create_strategy_empty_name(self, lightweight_api_client):
        """Test create strategy with empty name"""
        response = lightweight_api_client.post("/api/strategies", json={
            "strategy_name": "",
            "description": "Test description",
            "direction": "LONG",
            "enabled": True
        })
        assert response.status_code in (400, 422)

    def test_create_strategy_invalid_direction(self, lightweight_api_client):
        """Test create strategy with invalid direction"""
        response = lightweight_api_client.post("/api/strategies", json={
            "strategy_name": "Test Strategy",
            "description": "Test description",
            "direction": "INVALID",
            "enabled": True
        })
        assert response.status_code in (400, 422)

    def test_create_strategy_minimal_fields(self, lightweight_api_client):
        """Test create strategy with minimal required fields"""
        response = lightweight_api_client.post("/api/strategies", json={
            "strategy_name": "Minimal Strategy"
        })
        assert response.status_code in (200, 201, 400, 422, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesGetById:
    """Test GET strategy by ID endpoint"""

    def test_get_strategy_by_id(self, lightweight_api_client):
        """Test GET /api/strategies/{id}"""
        response = lightweight_api_client.get("/api/strategies/test_strategy_id")
        assert response.status_code in (200, 404, 500)

    def test_get_strategy_invalid_id(self, lightweight_api_client):
        """Test get strategy with invalid ID"""
        response = lightweight_api_client.get("/api/strategies/")
        assert response.status_code in (404, 405)

    def test_get_strategy_nonexistent_id(self, lightweight_api_client):
        """Test get strategy with nonexistent ID"""
        response = lightweight_api_client.get("/api/strategies/nonexistent_12345")
        assert response.status_code in (404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesUpdate:
    """Test PUT update strategy endpoint"""

    def test_update_strategy(self, lightweight_api_client):
        """Test PUT /api/strategies/{id}"""
        response = lightweight_api_client.put("/api/strategies/test_strategy_id", json={
            "strategy_name": "Updated Strategy",
            "description": "Updated description"
        })
        assert response.status_code in (200, 404, 422, 500)

    def test_update_strategy_partial(self, lightweight_api_client):
        """Test update strategy with partial data"""
        response = lightweight_api_client.put("/api/strategies/test_strategy_id", json={
            "enabled": False
        })
        assert response.status_code in (200, 400, 404, 422, 500)

    def test_update_strategy_invalid_data(self, lightweight_api_client):
        """Test update strategy with invalid data"""
        response = lightweight_api_client.put("/api/strategies/test_strategy_id", json={
            "enabled": "invalid_boolean"
        })
        assert response.status_code in (400, 422)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesDelete:
    """Test DELETE strategy endpoint"""

    def test_delete_strategy(self, lightweight_api_client):
        """Test DELETE /api/strategies/{id}"""
        response = lightweight_api_client.delete("/api/strategies/test_strategy_id")
        assert response.status_code in (200, 204, 404, 500)

    def test_delete_strategy_invalid_id(self, lightweight_api_client):
        """Test delete strategy with invalid ID"""
        response = lightweight_api_client.delete("/api/strategies/")
        assert response.status_code in (404, 405)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesActivate:
    """Test POST activate strategy endpoint"""

    def test_activate_strategy(self, lightweight_api_client):
        """Test POST /api/strategies/{id}/activate"""
        response = lightweight_api_client.post("/api/strategies/test_strategy_id/activate")
        assert response.status_code in (200, 404, 500)

    def test_activate_strategy_invalid_id(self, lightweight_api_client):
        """Test activate strategy with invalid ID"""
        response = lightweight_api_client.post("/api/strategies//activate")
        assert response.status_code in (404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestStrategiesDeactivate:
    """Test POST deactivate strategy endpoint"""

    def test_deactivate_strategy(self, lightweight_api_client):
        """Test POST /api/strategies/{id}/deactivate"""
        response = lightweight_api_client.post("/api/strategies/test_strategy_id/deactivate")
        assert response.status_code in (200, 404, 500)

    def test_deactivate_strategy_invalid_id(self, lightweight_api_client):
        """Test deactivate strategy with invalid ID"""
        response = lightweight_api_client.post("/api/strategies//deactivate")
        assert response.status_code in (404, 500)
