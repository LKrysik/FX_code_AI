"""
Tests for 4-Section Strategy CRUD Operations
Tests the REST API endpoints for creating, reading, updating, and deleting 4-section strategies.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.api.unified_server import create_unified_app


@pytest.fixture
def test_client():
    """Create test client for API testing"""
    app = create_unified_app()
    return TestClient(app)


@pytest.fixture
def sample_4section_strategy():
    """Sample valid 4-section strategy for testing"""
    return {
        "strategy_name": "Test Momentum Strategy",
        "description": "A test strategy for momentum trading",
        "s1_signal": {
            "logic": "AND",
            "conditions": [
                {
                    "id": "rsi_oversold",
                    "indicatorId": "rsi",
                    "operator": ">",
                    "value": 70
                },
                {
                    "id": "volume_surge",
                    "indicatorId": "volume_surge_ratio",
                    "operator": ">",
                    "value": 1.5
                }
            ]
        },
        "z1_entry": {
            "logic": "AND",
            "conditions": [
                {
                    "id": "price_above_sma",
                    "indicatorId": "sma_20",
                    "operator": ">",
                    "value": 0
                }
            ],
            "positionSize": {
                "type": "percentage",
                "value": 10
            },
            "stopLoss": {
                "enabled": True,
                "offsetPercent": 2
            },
            "takeProfit": {
                "enabled": True,
                "offsetPercent": 5
            }
        },
        "o1_cancel": {
            "logic": "OR",
            "timeoutSeconds": 300,
            "conditions": [
                {
                    "id": "rsi_oversold_cancel",
                    "indicatorId": "rsi",
                    "operator": "<",
                    "value": 30
                }
            ]
        },
        "emergency_exit": {
            "logic": "OR",
            "cooldownMinutes": 60,
            "conditions": [
                {
                    "id": "sharp_drop",
                    "indicatorId": "price_velocity",
                    "operator": "<",
                    "value": -0.05
                }
            ],
            "actions": {
                "cancelPending": True,
                "closePosition": True,
                "logEvent": True
            }
        }
    }


class TestStrategyCRUD:
    """Test suite for 4-section strategy CRUD operations"""

    def test_create_strategy_valid(self, test_client, sample_4section_strategy):
        """Test creating a valid 4-section strategy"""
        response = test_client.post("/api/strategies", json=sample_4section_strategy)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "strategy" in data["data"]
        assert "id" in data["data"]["strategy"]
        assert data["data"]["strategy"]["strategy_name"] == "Test Momentum Strategy"

    def test_create_strategy_missing_required_section(self, test_client):
        """Test creating strategy with missing required section fails"""
        invalid_strategy = {
            "strategy_name": "Invalid Strategy",
            "s1_signal": {"logic": "AND", "conditions": []},
            "z1_entry": {"logic": "AND", "conditions": []},
            # Missing o1_cancel and emergency_exit
        }

        response = test_client.post("/api/strategies", json=invalid_strategy)
        assert response.status_code == 400
        data = response.json()
        assert "error_message" in data
        assert "required" in data["error_message"].lower()

    def test_create_strategy_invalid_section_format(self, test_client):
        """Test creating strategy with invalid section format fails"""
        invalid_strategy = {
            "strategy_name": "Invalid Strategy",
            "s1_signal": "not_an_object",  # Should be object
            "z1_entry": {"logic": "AND", "conditions": []},
            "o1_cancel": {"logic": "OR", "conditions": []},
            "emergency_exit": {"logic": "OR", "conditions": []}
        }

        response = test_client.post("/api/strategies", json=invalid_strategy)
        assert response.status_code == 400
        data = response.json()
        assert "error_message" in data
        assert "s1_signal" in data["error_message"]

    def test_get_strategies_list(self, test_client, sample_4section_strategy):
        """Test listing all strategies"""
        # Create a strategy first
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200

        # List strategies
        response = test_client.get("/api/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "strategies" in data["data"]
        assert len(data["data"]["strategies"]) >= 1

        # Check strategy summary format
        strategy = data["data"]["strategies"][0]
        assert "id" in strategy
        assert "strategy_name" in strategy
        assert "created_at" in strategy

    def test_get_strategy_by_id(self, test_client, sample_4section_strategy):
        """Test getting a specific strategy by ID"""
        # Create a strategy first
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Get the strategy
        response = test_client.get(f"/api/strategies/{strategy_id}")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "strategy" in data["data"]
        assert data["data"]["strategy"]["id"] == strategy_id
        assert data["data"]["strategy"]["strategy_name"] == "Test Momentum Strategy"

        # Verify all 4 sections are present
        strategy = data["data"]["strategy"]
        assert "s1_signal" in strategy
        assert "z1_entry" in strategy
        assert "o1_cancel" in strategy
        assert "emergency_exit" in strategy

    def test_get_strategy_not_found(self, test_client):
        """Test getting non-existent strategy returns 404"""
        response = test_client.get("/api/strategies/non-existent-id")
        assert response.status_code == 404
        data = response.json()
        assert "error_message" in data
        assert "not found" in data["error_message"].lower()

    def test_update_strategy_valid(self, test_client, sample_4section_strategy):
        """Test updating a strategy with valid changes"""
        # Create a strategy first
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Update the strategy
        updated_strategy = sample_4section_strategy.copy()
        updated_strategy["strategy_name"] = "Updated Test Strategy"
        updated_strategy["description"] = "Updated description"

        response = test_client.put(f"/api/strategies/{strategy_id}", json=updated_strategy)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "strategy" in data["data"]
        assert data["data"]["strategy"]["strategy_name"] == "Updated Test Strategy"

    def test_update_strategy_not_found(self, test_client, sample_4section_strategy):
        """Test updating non-existent strategy returns 404"""
        response = test_client.put("/api/strategies/non-existent-id", json=sample_4section_strategy)
        assert response.status_code == 404
        data = response.json()
        assert "error_message" in data
        assert "not found" in data["error_message"].lower()

    def test_update_strategy_invalid(self, test_client, sample_4section_strategy):
        """Test updating strategy with invalid data fails"""
        # Create a strategy first
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Try to update with invalid data
        invalid_update = sample_4section_strategy.copy()
        invalid_update["s1_signal"] = "not_an_object"

        response = test_client.put(f"/api/strategies/{strategy_id}", json=invalid_update)
        assert response.status_code == 400
        data = response.json()
        assert "error_message" in data
        assert "validation" in data["error_message"].lower()

    def test_delete_strategy(self, test_client, sample_4section_strategy):
        """Test deleting a strategy"""
        # Create a strategy first
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Delete the strategy
        response = test_client.delete(f"/api/strategies/{strategy_id}")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "message" in data["data"]
        assert "deleted successfully" in data["data"]["message"].lower()

        # Verify it's gone
        get_response = test_client.get(f"/api/strategies/{strategy_id}")
        assert get_response.status_code == 404

    def test_delete_strategy_not_found(self, test_client):
        """Test deleting non-existent strategy returns 404"""
        response = test_client.delete("/api/strategies/non-existent-id")
        assert response.status_code == 404
        data = response.json()
        assert "error_message" in data
        assert "not found" in data["error_message"].lower()

    def test_validate_strategy_endpoint(self, test_client, sample_4section_strategy):
        """Test strategy validation endpoint"""
        response = test_client.post("/api/strategies/validate", json=sample_4section_strategy)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is True
        assert data["data"]["errors"] == []
        assert "warnings" in data["data"]

    def test_validate_strategy_invalid(self, test_client):
        """Test strategy validation endpoint with invalid strategy"""
        invalid_strategy = {
            "strategy_name": "Invalid",
            "s1_signal": "not_an_object",
            "z1_entry": {"conditions": []},
            "o1_cancel": {"conditions": []},
            "emergency_exit": {"conditions": []}
        }

        response = test_client.post("/api/strategies/validate", json=invalid_strategy)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is False
        assert len(data["data"]["errors"]) > 0

    def test_strategy_persistence_across_requests(self, test_client, sample_4section_strategy):
        """Test that strategies persist across different API calls"""
        # Create strategy
        create_response = test_client.post("/api/strategies", json=sample_4section_strategy)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Get it back
        get_response = test_client.get(f"/api/strategies/{strategy_id}")
        assert get_response.status_code == 200
        retrieved = get_response.json()["data"]["strategy"]

        # Verify data integrity
        assert retrieved["strategy_name"] == sample_4section_strategy["strategy_name"]
        assert retrieved["s1_signal"]["logic"] == sample_4section_strategy["s1_signal"]["logic"]
        assert retrieved["z1_entry"]["positionSize"]["type"] == sample_4section_strategy["z1_entry"]["positionSize"]["type"]
        assert retrieved["o1_cancel"]["timeoutSeconds"] == sample_4section_strategy["o1_cancel"]["timeoutSeconds"]
        assert retrieved["emergency_exit"]["cooldownMinutes"] == sample_4section_strategy["emergency_exit"]["cooldownMinutes"]