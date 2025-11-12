"""
Strategy CRUD API E2E Tests
============================

Tests for strategy management endpoints:
- POST /api/strategies (create)
- GET /api/strategies (list)
- GET /api/strategies/{id} (read)
- PUT /api/strategies/{id} (update)
- DELETE /api/strategies/{id} (delete)
- POST /api/strategies/validate (validate)
"""

import pytest
from datetime import datetime


@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyAuthRequirements:
    """Tests for authentication requirements across strategy endpoints"""

    @pytest.mark.parametrize("endpoint,method,payload_required", [
        ("/api/strategies", "POST", True),
        ("/api/strategies", "GET", False),
        ("/api/strategies/any-id", "GET", False),
        ("/api/strategies/any-id", "PUT", True),
        ("/api/strategies/any-id", "DELETE", False),
        ("/api/strategies/validate", "POST", True),
    ])
    def test_endpoints_require_authentication(self, api_client, valid_strategy_config, endpoint, method, payload_required):
        """Test that protected strategy endpoints require authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        if method == "GET":
            response = api_client.get(endpoint)
        elif method == "POST":
            payload = valid_strategy_config if payload_required else {}
            response = api_client.post(endpoint, json=payload)
        elif method == "PUT":
            payload = valid_strategy_config if payload_required else {}
            response = api_client.put(endpoint, json=payload)
        elif method == "DELETE":
            response = api_client.delete(endpoint)

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyCreate:
    """Tests for creating strategies"""

    def test_create_strategy_success(self, authenticated_client, valid_strategy_config):
        """Test successful strategy creation"""
        response = authenticated_client.post("/api/strategies", json=valid_strategy_config)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "strategy" in data["data"]

        strategy = data["data"]["strategy"]
        assert "id" in strategy
        assert strategy["strategy_name"] == valid_strategy_config["strategy_name"]
        assert "created_at" in strategy

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(strategy["created_at"])

    def test_create_strategy_validates_required_fields(self, authenticated_client):
        """Test that strategy creation validates required fields"""
        invalid_strategy = {
            "strategy_name": "Incomplete Strategy",
            # Missing required sections
        }

        response = authenticated_client.post("/api/strategies", json=invalid_strategy)

        assert response.status_code == 400

        data = response.json()
        assert "error_code" in data
        assert "error_message" in data

    def test_create_strategy_validates_5_sections(self, authenticated_client):
        """Test that all 5 sections are required"""
        incomplete_strategy = {
            "strategy_name": "Incomplete Strategy",
            "s1_signal": {},
            "z1_entry": {},
            # Missing ze1_close, o1_cancel and emergency_exit
        }

        response = authenticated_client.post("/api/strategies", json=incomplete_strategy)

        assert response.status_code == 400

        data = response.json()
        assert "All 5 sections" in data["error_message"]

    def test_create_strategy_validates_section_structure(self, authenticated_client):
        """Test that section structure is validated"""
        invalid_strategy = {
            "strategy_name": "Invalid Strategy",
            "s1_signal": {},  # Empty section (invalid)
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        response = authenticated_client.post("/api/strategies", json=invalid_strategy)

        assert response.status_code == 400

        data = response.json()
        assert "validation_error" in data["error_code"]


@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyList:
    """Tests for listing strategies"""

    def test_list_strategies_empty(self, authenticated_client):
        """Test listing strategies when none exist"""
        response = authenticated_client.get("/api/strategies")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "strategies" in data["data"]
        assert isinstance(data["data"]["strategies"], list)

    def test_list_strategies_after_creating_one(self, authenticated_client, valid_strategy_config):
        """Test listing strategies after creating one"""
        # Create a strategy first
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        # List strategies
        list_response = authenticated_client.get("/api/strategies")
        assert list_response.status_code == 200

        data = list_response.json()
        strategies = data["data"]["strategies"]

        assert len(strategies) >= 1

        # Verify strategy summary structure
        strategy = strategies[0]
        assert "id" in strategy
        assert "strategy_name" in strategy
        assert "created_at" in strategy



@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyRead:
    """Tests for reading individual strategies"""

    def test_get_strategy_by_id_success(self, authenticated_client, valid_strategy_config):
        """Test getting a strategy by ID"""
        # Create a strategy first
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Get the strategy
        get_response = authenticated_client.get(f"/api/strategies/{strategy_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert "data" in data
        assert "strategy" in data["data"]

        strategy = data["data"]["strategy"]
        assert strategy["strategy_name"] == valid_strategy_config["strategy_name"]

        # Verify all 5 sections are present
        assert "s1_signal" in strategy
        assert "z1_entry" in strategy
        assert "ze1_close" in strategy
        assert "o1_cancel" in strategy
        assert "emergency_exit" in strategy

    def test_get_strategy_not_found(self, authenticated_client):
        """Test getting a non-existent strategy returns 404"""
        response = authenticated_client.get("/api/strategies/non-existent-id")

        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        assert "not_found" in data["error_code"]



@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyUpdate:
    """Tests for updating strategies"""

    def test_update_strategy_success(self, authenticated_client, valid_strategy_config):
        """Test successful strategy update"""
        # Create a strategy first
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Update the strategy
        update_data = {
            **valid_strategy_config,
            "strategy_name": "Updated Strategy Name",
            "description": "Updated description"
        }

        update_response = authenticated_client.put(f"/api/strategies/{strategy_id}", json=update_data)
        assert update_response.status_code == 200

        data = update_response.json()
        assert "data" in data
        assert "strategy" in data["data"]
        assert data["data"]["strategy"]["strategy_name"] == "Updated Strategy Name"

    def test_update_strategy_validates_config(self, authenticated_client, valid_strategy_config):
        """Test that updates are validated"""
        # Create a strategy first
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Try to update with invalid config
        invalid_update = {
            "strategy_name": "Updated",
            "s1_signal": {},  # Invalid empty section
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        update_response = authenticated_client.put(f"/api/strategies/{strategy_id}", json=invalid_update)

        assert update_response.status_code == 400

        data = update_response.json()
        assert "validation_error" in data["error_code"]

    def test_update_strategy_not_found(self, authenticated_client, valid_strategy_config):
        """Test updating non-existent strategy returns 404"""
        response = authenticated_client.put("/api/strategies/non-existent-id", json=valid_strategy_config)

        assert response.status_code == 404

        data = response.json()
        assert "not_found" in data["error_code"]



@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyDelete:
    """Tests for deleting strategies"""

    def test_delete_strategy_success(self, authenticated_client, valid_strategy_config):
        """Test successful strategy deletion"""
        # Create a strategy first
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Delete the strategy
        delete_response = authenticated_client.delete(f"/api/strategies/{strategy_id}")
        assert delete_response.status_code == 200

        data = delete_response.json()
        assert "data" in data
        assert "message" in data["data"]
        assert data["data"]["strategy_id"] == strategy_id

        # Verify it's actually deleted
        get_response = authenticated_client.get(f"/api/strategies/{strategy_id}")
        assert get_response.status_code == 404

    def test_delete_strategy_not_found(self, authenticated_client):
        """Test deleting non-existent strategy returns 404"""
        response = authenticated_client.delete("/api/strategies/non-existent-id")

        assert response.status_code == 404

        data = response.json()
        assert "not_found" in data["error_code"]



@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.integration
@pytest.mark.database
class TestStrategyValidate:
    """Tests for strategy validation endpoint"""

    def test_validate_valid_strategy(self, authenticated_client, valid_strategy_config):
        """Test validation of valid strategy"""
        response = authenticated_client.post("/api/strategies/validate", json=valid_strategy_config)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is True
        assert "errors" in data["data"]
        assert len(data["data"]["errors"]) == 0
        assert "warnings" in data["data"]

    def test_validate_invalid_strategy(self, authenticated_client):
        """Test validation of invalid strategy"""
        invalid_strategy = {
            "strategy_name": "Invalid",
            "s1_signal": {},
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        response = authenticated_client.post("/api/strategies/validate", json=invalid_strategy)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is False
        assert len(data["data"]["errors"]) > 0



@pytest.mark.api
@pytest.mark.strategies
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.database
class TestStrategyCRUDIntegration:
    """Integration tests for complete CRUD flow"""

    def test_complete_crud_flow(self, authenticated_client, valid_strategy_config):
        """Test complete CRUD flow: create → read → update → delete"""

        # Step 1: Create
        create_response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Step 2: Read
        read_response = authenticated_client.get(f"/api/strategies/{strategy_id}")
        assert read_response.status_code == 200
        strategy = read_response.json()["data"]["strategy"]
        assert strategy["strategy_name"] == valid_strategy_config["strategy_name"]

        # Step 3: Update
        update_data = {
            **valid_strategy_config,
            "description": "Updated description"
        }
        update_response = authenticated_client.put(f"/api/strategies/{strategy_id}", json=update_data)
        assert update_response.status_code == 200

        # Step 4: Verify update
        read_response2 = authenticated_client.get(f"/api/strategies/{strategy_id}")
        assert read_response2.status_code == 200
        updated_strategy = read_response2.json()["data"]["strategy"]
        assert updated_strategy["description"] == "Updated description"

        # Step 5: Delete
        delete_response = authenticated_client.delete(f"/api/strategies/{strategy_id}")
        assert delete_response.status_code == 200

        # Step 6: Verify deletion
        get_after_delete = authenticated_client.get(f"/api/strategies/{strategy_id}")
        assert get_after_delete.status_code == 404
