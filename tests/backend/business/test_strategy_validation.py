"""
Tests for strategy graph validation logic.
"""

import pytest
from src.strategy_graph.validators import GraphValidator, ValidationError
from src.strategy_graph.serializer import StrategyGraph, GraphNode, GraphEdge

class TestGraphValidator:
    """Test suite for GraphValidator."""

    def setup_method(self):
        """Setup validator for each test."""
        self.validator = GraphValidator()

    def test_valid_graph_validation(self, sample_strategy_graph):
        """Test validation of a valid strategy graph."""
        graph = StrategyGraph.from_dict(sample_strategy_graph)

        errors, warnings = self.validator.validate(graph)

        # Should have no errors for valid graph
        assert len(errors) == 0
        # May have warnings but that's OK
        assert isinstance(warnings, list)

    def test_empty_graph_validation(self):
        """Test validation of empty graph."""
        graph = StrategyGraph("empty", nodes=[], edges=[])

        errors, warnings = self.validator.validate(graph)

        # Should have error for empty graph
        assert len(errors) > 0
        assert any("empty_graph" in error.error_type for error in errors)

    def test_duplicate_node_ids(self):
        """Test validation detects duplicate node IDs."""
        nodes = [
            GraphNode("dup", "price_source", {"x": 100, "y": 100}, {"symbol": "BTC"}),
            GraphNode("dup", "vwap", {"x": 200, "y": 100}, {"window": 300})  # Same ID
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=[])

        errors, warnings = self.validator.validate(graph)

        assert len(errors) > 0
        assert any("duplicate_node" in error.error_type for error in errors)

    def test_invalid_node_type(self):
        """Test validation detects invalid node types."""
        nodes = [
            GraphNode("invalid", "nonexistent_type", {"x": 100, "y": 100}, {})
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=[])

        errors, warnings = self.validator.validate(graph)

        assert len(errors) > 0
        assert any("invalid_node_type" in error.error_type for error in errors)

    def test_missing_required_connections(self):
        """Test validation detects missing required input connections."""
        # Create a condition node without input connection
        nodes = [
            GraphNode("condition", "threshold_condition", {"x": 100, "y": 100},
                     {"operator": ">", "threshold": 0.5})
        ]
        edges = []  # No edges, so condition has no input
        graph = StrategyGraph("test", nodes=nodes, edges=edges)

        errors, warnings = self.validator.validate(graph)

        assert len(errors) > 0
        assert any("missing_input" in error.error_type for error in errors)

    def test_cycle_detection(self):
        """Test validation detects cycles in the graph."""
        nodes = [
            GraphNode("a", "price_source", {"x": 100, "y": 100}, {"symbol": "BTC"}),
            GraphNode("b", "vwap", {"x": 200, "y": 100}, {"window": 300}),
            GraphNode("c", "threshold_condition", {"x": 300, "y": 100}, {"operator": ">", "threshold": 0.5})
        ]
        edges = [
            GraphEdge("a", "price", "b", "price"),
            GraphEdge("b", "vwap", "c", "input"),
            GraphEdge("c", "result", "a", "price")  # Creates cycle
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=edges)

        errors, warnings = self.validator.validate(graph)

        assert len(errors) > 0
        assert any("cycle_detected" in error.error_type for error in errors)

    def test_data_type_compatibility(self):
        """Test validation of data type compatibility between ports."""
        nodes = [
            GraphNode("source", "price_source", {"x": 100, "y": 100}, {"symbol": "BTC"}),
            GraphNode("indicator", "price_velocity", {"x": 200, "y": 100}, {"period": 60})
        ]
        edges = [
            GraphEdge("source", "price", "indicator", "price")  # Compatible
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=edges)

        errors, warnings = self.validator.validate(graph)

        # Should be valid
        assert len(errors) == 0

    def test_invalid_port_connection(self):
        """Test validation detects invalid port connections."""
        nodes = [
            GraphNode("source", "price_source", {"x": 100, "y": 100}, {"symbol": "BTC"}),
            GraphNode("indicator", "vwap", {"x": 200, "y": 100}, {"window": 300})
        ]
        edges = [
            GraphEdge("source", "nonexistent_port", "indicator", "price")  # Invalid source port
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=edges)

        errors, warnings = self.validator.validate(graph)

        assert len(errors) > 0
        assert any("invalid_port" in error.error_type for error in errors)

    def test_parameter_validation(self):
        """Test validation of node parameters."""
        # Test with invalid parameter value
        nodes = [
            GraphNode("source", "price_source", {"x": 100, "y": 100},
                     {"symbol": "BTC", "update_frequency": -100})  # Invalid negative value
        ]
        graph = StrategyGraph("test", nodes=nodes, edges=[])

        errors, warnings = self.validator.validate(graph)

        # Should detect invalid parameter
        assert len(errors) > 0

    def test_business_rule_validation(self):
        """Test validation of business rules."""
        # Create a large graph to test size warnings
        nodes = []
        edges = []
        for i in range(150):  # Create many nodes
            nodes.append(GraphNode(f"node_{i}", "price_source", {"x": i*10, "y": 100}, {"symbol": "BTC"}))
            if i > 0:
                edges.append(GraphEdge(f"node_{i-1}", "price", f"node_{i}", "price"))

        graph = StrategyGraph("large_test", nodes=nodes, edges=edges)

        errors, warnings = self.validator.validate(graph)

        # Should have warning about large graph
        assert len(warnings) > 0
        assert any("large_graph" in warning.error_type for warning in warnings)

class TestValidationError:
    """Test ValidationError class."""

    def test_validation_error_creation(self):
        """Test creating validation errors."""
        error = ValidationError(
            error_type="test_error",
            message="Test message",
            node_id="node1",
            severity="error"
        )

        assert error.error_type == "test_error"
        assert error.message == "Test message"
        assert error.node_id == "node1"
        assert error.severity == "error"

    def test_validation_error_to_dict(self):
        """Test converting validation error to dict."""
        error = ValidationError(
            error_type="test_error",
            message="Test message",
            node_id="node1"
        )

        error_dict = error.to_dict()
        assert error_dict["type"] == "test_error"
        assert error_dict["message"] == "Test message"
        assert error_dict["node_id"] == "node1"