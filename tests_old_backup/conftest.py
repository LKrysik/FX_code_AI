"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import asyncio
from typing import Dict, Any
import json
from pathlib import Path

# Test data fixtures
@pytest.fixture
def sample_strategy_graph():
    """Sample strategy graph for testing."""
    return {
        "name": "Test Pump Strategy",
        "version": "1.0.0",
        "description": "Test strategy for validation",
        "nodes": [
            {
                "id": "price_source_1",
                "node_type": "price_source",
                "position": {"x": 100, "y": 100},
                "parameters": {"symbol": "BTC_USDT", "update_frequency": 1000}
            },
            {
                "id": "volume_source_1",
                "node_type": "volume_source",
                "position": {"x": 100, "y": 200},
                "parameters": {"symbol": "BTC_USDT", "aggregation": "trade"}
            },
            {
                "id": "vwap_1",
                "node_type": "vwap",
                "position": {"x": 350, "y": 150},
                "parameters": {"t1": 300.0, "t2": 0.0}
            },
            {
                "id": "condition_1",
                "node_type": "threshold_condition",
                "position": {"x": 600, "y": 150},
                "parameters": {"operator": ">", "threshold": 0.5}
            },
            {
                "id": "action_1",
                "node_type": "buy_signal",
                "position": {"x": 850, "y": 150},
                "parameters": {"position_size": 100.0, "max_slippage": 0.001}
            }
        ],
        "edges": [
            {"source_node": "price_source_1", "source_port": "price", "target_node": "vwap_1", "target_port": "price"},
            {"source_node": "volume_source_1", "source_port": "volume", "target_node": "vwap_1", "target_port": "volume"},
            {"source_node": "vwap_1", "source_port": "vwap", "target_node": "condition_1", "target_port": "input"},
            {"source_node": "condition_1", "source_port": "result", "target_node": "action_1", "target_port": "trigger"}
        ]
    }

@pytest.fixture
def sample_blueprint_data(sample_strategy_graph):
    """Sample blueprint data for API testing."""
    return {
        "name": "Test Blueprint",
        "version": "1.0.0",
        "description": "Test blueprint description",
        "graph": sample_strategy_graph,
        "tags": ["test", "pump"],
        "is_template": False
    }

@pytest.fixture
def mock_auth_token():
    """Mock JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZGV2ZWxvcGVyIiwicm9sZSI6ImRldmVsb3BlciIsImV4cCI6MTY3MjU0NzIwMH0.test"

@pytest.fixture
def test_config():
    """Test configuration data."""
    return {
        "api_url": "http://localhost:8000",
        "test_user": "developer",
        "test_role": "developer"
    }

# Async test support
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test utilities
@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    import tempfile
    import os

    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.unlink(path)

@pytest.fixture
def load_json_fixture():
    """Load JSON fixture from tests/fixtures directory."""
    def _load_fixture(filename: str) -> Dict[str, Any]:
        fixture_path = Path(__file__).parent / "fixtures" / filename
        with open(fixture_path, 'r') as f:
            return json.load(f)
    return _load_fixture