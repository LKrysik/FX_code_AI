"""
Tests for Strategy Blueprints API endpoints (isolated FastAPI app).
"""

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.logger import StructuredLogger
from src.infrastructure.config.settings import AppSettings
from src.api.strategy_blueprints import StrategyBlueprintsAPI, router as blueprints_router


@pytest.fixture(scope="module")
def blueprint_client():
    """Provide a TestClient with blueprint routes and simple health check."""
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    settings = AppSettings()
    logger = StructuredLogger("TestBlueprints", settings.logging)
    api = StrategyBlueprintsAPI(logger=logger)

    # Replace module-level instance so router uses our injected API
    import src.api.strategy_blueprints as blueprints_module
    blueprints_module.blueprints_api = api

    app.include_router(blueprints_router)
    return TestClient(app)


def test_health_endpoint(blueprint_client: TestClient):
    response = blueprint_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/strategy-blueprints/",
        "/api/strategy-blueprints/templates/list",
    ],
)
def test_blueprint_endpoints_require_auth(blueprint_client: TestClient, endpoint: str):
    response = blueprint_client.get(endpoint)
    assert response.status_code in {401, 403}


def test_create_blueprint_validation(blueprint_client: TestClient, sample_blueprint_data):
    with patch(
        "src.api.strategy_blueprints.blueprints_api.authenticate_user",
        return_value={"user_id": "test_user", "role": "developer", "permissions": ["read", "write"]},
    ):
        response = blueprint_client.post(
            "/api/strategy-blueprints/",
            json=sample_blueprint_data,
            headers={"Authorization": "Bearer test-token"},
        )

        if response.status_code == 200:
            data = response.json()
            assert "blueprint" in data
            assert data["blueprint"]["name"] == sample_blueprint_data["name"]
        else:
            assert response.status_code in {400, 422}


def test_blueprint_serialization(sample_blueprint_data):
    assert "name" in sample_blueprint_data
    assert "graph" in sample_blueprint_data
    assert "nodes" in sample_blueprint_data["graph"]
    assert "edges" in sample_blueprint_data["graph"]

    json_str = json.dumps(sample_blueprint_data)
    deserialized = json.loads(json_str)
    assert deserialized == sample_blueprint_data


def test_blueprint_validation_endpoint(blueprint_client: TestClient, sample_strategy_graph):
    with patch(
        "src.api.strategy_blueprints.blueprints_api.authenticate_user",
        return_value={"user_id": "test_user", "role": "developer", "permissions": ["read", "write"]},
    ):
        response = blueprint_client.post(
            "/api/strategy-blueprints/validate",
            json=sample_strategy_graph,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code in {200, 400}
        if response.status_code == 200:
            data = response.json()
            assert "validation" in data
            assert any(key in data["validation"] for key in {"isValid", "valid"})


class TestStrategyGraphSerialization:
    """Strategy graph serialization tests remain unchanged."""

    def test_graph_node_serialization(self):
        from src.strategy_graph.serializer import GraphNode

        node = GraphNode(
            node_id="test_1",
            node_type="price_source",
            position={"x": 100, "y": 200},
            parameters={"symbol": "BTC_USDT"}
        )

        node_dict = node.to_dict()
        assert node_dict["id"] == "test_1"
        assert node_dict["node_type"] == "price_source"
        assert node_dict["position"]["x"] == 100

        node2 = GraphNode.from_dict(node_dict)
        assert node2.id == node.id
        assert node2.node_type == node.node_type

    def test_graph_edge_serialization(self):
        from src.strategy_graph.serializer import GraphEdge

        edge = GraphEdge(
            source_node="node1",
            source_port="output",
            target_node="node2",
            target_port="input"
        )

        edge_dict = edge.to_dict()
        assert edge_dict["source_node"] == "node1"
        assert edge_dict["target_node"] == "node2"

        edge2 = GraphEdge.from_dict(edge_dict)
        assert edge2.source_node == edge.source_node

    def test_strategy_graph_serialization(self, sample_strategy_graph):
        from src.strategy_graph.serializer import StrategyGraph

        graph = StrategyGraph.from_dict(sample_strategy_graph)

        graph_dict = graph.to_dict()
        assert graph_dict["name"] == sample_strategy_graph["name"]
        assert len(graph_dict["nodes"]) == len(sample_strategy_graph["nodes"])
        assert len(graph_dict["edges"]) == len(sample_strategy_graph["edges"])

        graph2 = StrategyGraph.from_dict(graph_dict)
        assert graph2.name == graph.name
        assert len(graph2.nodes) == len(graph.nodes)
        assert len(graph2.edges) == len(graph.edges)
