#!/usr/bin/env python3
"""
4-Section Strategy CRUD API Tests
==================================
Comprehensive test suite for 4-section strategy create, read, update, delete operations.
Tests all acceptance criteria from SPRINT_8G_PLAN.md.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi.testclient import TestClient

from src.api.unified_server import create_unified_app
from src.domain.services.strategy_schema import validate_strategy_config


class TestStrategyCRUD:
    """Test suite for 4-section strategy CRUD operations"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_unified_app()
        # Initialize strategies storage for testing
        if not hasattr(app.state, 'strategies'):
            app.state.strategies = {}
        return TestClient(app)

    def _mock_auth(self, client, user_id="test_user"):
        """Helper to mock authentication for tests"""
        mock_user = MagicMock()
        mock_user.user_id = user_id

        async def mock_get_current_user():
            return mock_user

        client.app.dependency_overrides[client.app.state.get_current_user_dependency] = mock_get_current_user
        return mock_user

    @pytest.fixture
    def valid_4section_strategy(self):
        """Valid 4-section strategy for testing"""
        return {
            "strategy_name": "Test Momentum Strategy",
            "description": "Test strategy for momentum trading",
            "s1_signal": {
                "conditions": [
                    {"id": "price_velocity_1", "indicatorId": "price_velocity", "operator": ">", "value": 0.5}
                ]
            },
            "z1_entry": {
                "conditions": [
                    {"id": "price_velocity_entry", "indicatorId": "price_velocity", "operator": ">", "value": 0.5}
                ],
                "positionSize": {"type": "percentage", "value": 10}
            },
            "o1_cancel": {
                "timeoutSeconds": 300,
                "conditions": [
                    {"id": "price_velocity_cancel", "indicatorId": "price_velocity", "operator": "<", "value": -0.3}
                ]
            },
            "emergency_exit": {
                "conditions": [
                    {"id": "price_velocity_emergency", "indicatorId": "price_velocity", "operator": "<", "value": -1.0}
                ],
                "cooldownMinutes": 60,
                "actions": {
                    "cancelPending": True,
                    "closePosition": True,
                    "logEvent": True
                }
            }
        }

    def test_post_strategies_accepts_4section_format(self, client, valid_4section_strategy):
        """Test POST /api/strategies accepts 4-section format directly"""
        self._mock_auth(client)

        response = client.post('/api/strategies', json=valid_4section_strategy)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure (envelope format)
        assert "data" in data
        assert "strategy" in data["data"]
        assert "id" in data["data"]["strategy"]
        assert data["data"]["strategy"]["strategy_name"] == valid_4section_strategy["strategy_name"]

        # Verify strategy was stored (access via client.app.state)
        strategy_id = data["data"]["strategy"]["id"]
        assert strategy_id in client.app.state.strategies

        stored_strategy = client.app.state.strategies[strategy_id]
        assert stored_strategy["strategy_name"] == valid_4section_strategy["strategy_name"]
        assert "s1_signal" in stored_strategy
        assert "z1_entry" in stored_strategy
        assert "o1_cancel" in stored_strategy
        assert "emergency_exit" in stored_strategy

    def test_post_strategies_validates_required_sections(self, client):
        """Test POST /api/strategies validates all 4 sections are required"""
        # Test missing s1_signal
        invalid_strategy = {
            "strategy_name": "Invalid Strategy",
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        self._mock_auth(client)

        response = client.post('/api/strategies', json=invalid_strategy)
        assert response.status_code == 400
        data = response.json()
        assert "All 4 sections" in data["error_message"]

    def test_post_strategies_validates_strategy_config(self, client):
        """Test POST /api/strategies validates strategy configuration"""
        # Invalid strategy (missing required fields in sections)
        invalid_strategy = {
            "strategy_name": "Invalid Strategy",
            "s1_signal": {},  # Empty section
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        self._mock_auth(client)

        response = client.post('/api/strategies', json=invalid_strategy)
        assert response.status_code == 400
        data = response.json()
        assert "validation_error" in data["error_code"]

    def test_get_strategies_returns_list(self, client, valid_4section_strategy):
        """Test GET /api/strategies returns list of strategies"""
        # First create a strategy
        self._mock_auth(client)

        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        # Now get the list
        list_response = client.get('/api/strategies')
        assert list_response.status_code == 200

        data = list_response.json()
        assert "data" in data
        assert "strategies" in data["data"]
        assert len(data["data"]["strategies"]) >= 1

        # Verify strategy summary structure
        strategy_summary = data["data"]["strategies"][0]
        assert "id" in strategy_summary
        assert "strategy_name" in strategy_summary
        assert "created_at" in strategy_summary

    def test_get_strategies_by_id_returns_full_strategy(self, client, valid_4section_strategy):
        """Test GET /api/strategies/{id} returns complete 4-section strategy"""
        # Create a strategy first
        self._mock_auth(client)

        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Get the full strategy
        get_response = client.get(f'/api/strategies/{strategy_id}')
        assert get_response.status_code == 200

        data = get_response.json()
        assert "data" in data
        assert "strategy" in data["data"]

        strategy = data["data"]["strategy"]
        assert strategy["strategy_name"] == valid_4section_strategy["strategy_name"]
        assert "s1_signal" in strategy
        assert "z1_entry" in strategy
        assert "o1_cancel" in strategy
        assert "emergency_exit" in strategy

    def test_get_strategies_by_id_not_found(self, client):
        """Test GET /api/strategies/{id} returns 404 for non-existent strategy"""
        self._mock_auth(client)

        response = client.get('/api/strategies/non-existent-id')
        assert response.status_code == 404
        data = response.json()
        assert "not_found" in data["error_code"]

    def test_put_strategies_updates_strategy(self, client, valid_4section_strategy):
        """Test PUT /api/strategies/{id} updates existing strategy"""
        # Create a strategy first
        self._mock_auth(client)

        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Update the strategy
        update_data = {
            "strategy_name": "Updated Strategy Name",
            "description": "Updated description"
        }

        update_response = client.put(f'/api/strategies/{strategy_id}', json=update_data)
        assert update_response.status_code == 200

        data = update_response.json()
        assert "data" in data
        assert "strategy" in data["data"]
        assert data["data"]["strategy"]["strategy_name"] == "Updated Strategy Name"

        # Verify in storage
        stored_strategy = client.app.state.strategies[strategy_id]
        assert stored_strategy["strategy_name"] == "Updated Strategy Name"
        assert "updated_at" in stored_strategy

    def test_put_strategies_validates_updates(self, client, valid_4section_strategy):
        """Test PUT /api/strategies/{id} validates updated configuration"""
        # Create a strategy first
        self._mock_auth(client)

        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Try to update with invalid config
        invalid_update = {
            "s1_signal": {}  # Invalid empty section
        }

        update_response = client.put(f'/api/strategies/{strategy_id}', json=invalid_update)
        assert update_response.status_code == 400
        data = update_response.json()
        assert "validation_error" in data["error_code"]

    def test_put_strategies_not_found(self, client):
        """Test PUT /api/strategies/{id} returns 404 for non-existent strategy"""
        self._mock_auth(client)

        update_data = {"strategy_name": "Updated Name"}
        response = client.put('/api/strategies/non-existent-id', json=update_data)
        assert response.status_code == 404
        data = response.json()
        assert "not_found" in data["error_code"]

    def test_delete_strategies_removes_strategy(self, client, valid_4section_strategy):
        """Test DELETE /api/strategies/{id} removes strategy"""
        # Create a strategy first
        self._mock_auth(client)

        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Delete the strategy
        delete_response = client.delete(f'/api/strategies/{strategy_id}')
        assert delete_response.status_code == 200

        data = delete_response.json()
        assert "data" in data
        assert "message" in data["data"]
        assert data["data"]["strategy_id"] == strategy_id

        # Verify removed from storage
        assert strategy_id not in client.app.state.strategies

    def test_delete_strategies_not_found(self, client):
        """Test DELETE /api/strategies/{id} returns 404 for non-existent strategy"""
        self._mock_auth(client)

        response = client.delete('/api/strategies/non-existent-id')
        assert response.status_code == 404
        data = response.json()
        assert "not_found" in data["error_code"]

    def test_post_strategies_validate_endpoint(self, client, valid_4section_strategy):
        """Test POST /api/strategies/validate validates strategy configuration"""
        self._mock_auth(client)

        # Test valid strategy
        response = client.post('/api/strategies/validate', json=valid_4section_strategy)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is True
        assert "errors" in data["data"]
        assert "warnings" in data["data"]

        # Test invalid strategy
        invalid_strategy = {
            "strategy_name": "Invalid",
            "s1_signal": {},
            "z1_entry": {},
            "o1_cancel": {},
            "emergency_exit": {}
        }

        response = client.post('/api/strategies/validate', json=invalid_strategy)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["isValid"] is False
        assert len(data["data"]["errors"]) > 0

    def test_strategies_require_authentication(self, client, valid_4section_strategy):
        """Test that all strategy endpoints require authentication"""
        endpoints = [
            ('POST', '/api/strategies', valid_4section_strategy),
            ('GET', '/api/strategies', None),
            ('GET', '/api/strategies/test-id', None),
            ('PUT', '/api/strategies/test-id', {"strategy_name": "Updated"}),
            ('DELETE', '/api/strategies/test-id', None),
            ('POST', '/api/strategies/validate', valid_4section_strategy),
        ]

        for method, endpoint, data in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint, json=data)
            elif method == 'PUT':
                response = client.put(endpoint, json=data)
            elif method == 'DELETE':
                response = client.delete(endpoint)

            # Should return 401 without authentication
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"

    def test_strategy_metadata_fields(self, client, valid_4section_strategy):
        """Test that strategy metadata fields are properly set"""
        self._mock_auth(client, "test_user_123")

        response = client.post('/api/strategies', json=valid_4section_strategy)
        assert response.status_code == 200

        data = response.json()
        strategy = data["data"]["strategy"]

        # Check metadata fields
        assert "id" in strategy
        assert "created_at" in strategy

        # Verify timestamps are valid ISO format
        datetime.fromisoformat(strategy["created_at"])

    def test_strategy_storage_persistence(self, client, valid_4section_strategy):
        """Test that strategies persist across operations"""
        self._mock_auth(client)

        # Create strategy
        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        strategy_id = create_response.json()["data"]["strategy"]["id"]

        # Update strategy
        update_response = client.put(f'/api/strategies/{strategy_id}', json={
            "description": "Updated description"
        })
        assert update_response.status_code == 200

        # Verify update persisted
        get_response = client.get(f'/api/strategies/{strategy_id}')
        assert get_response.status_code == 200

        strategy = get_response.json()["data"]["strategy"]
        assert strategy["description"] == "Updated description"
        assert strategy["updated_at"] != strategy["created_at"]  # Should be different

    def test_strategy_validation_integration(self, client, valid_4section_strategy):
        """Test integration between validation and CRUD operations"""
        self._mock_auth(client)

        # First validate the strategy
        validate_response = client.post('/api/strategies/validate', json=valid_4section_strategy)
        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["data"]["isValid"] is True

        # Then create it
        create_response = client.post('/api/strategies', json=valid_4section_strategy)
        assert create_response.status_code == 200

        # Verify the created strategy matches validation
        strategy_id = create_response.json()["data"]["strategy"]["id"]
        get_response = client.get(f'/api/strategies/{strategy_id}')
        assert get_response.status_code == 200

        stored_strategy = get_response.json()["data"]["strategy"]

        # Remove metadata fields for comparison
        stored_clean = {k: v for k, v in stored_strategy.items()
                       if k not in ['id', 'created_at', 'updated_at', 'created_by']}

        assert stored_clean == valid_4section_strategy