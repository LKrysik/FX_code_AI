#!/usr/bin/env python3
"""
Strategy Graph Serializer
========================

Handles serialization and deserialization of strategy graphs to/from JSON.
Ensures graph integrity and provides migration support.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from .node_catalog import get_node_definition, NodeType


class GraphNode:
    """Represents a node in the strategy graph."""

    def __init__(self, node_id: str, node_type: str, position: Dict[str, float],
                 parameters: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        self.id = node_id
        self.node_type = node_type
        self.position = position
        self.parameters = parameters
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "position": self.position,
            "parameters": self.parameters,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphNode':
        """Create node from dictionary representation."""
        return cls(
            node_id=data["id"],
            node_type=data["node_type"],
            position=data["position"],
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        )


class GraphEdge:
    """Represents a connection between nodes in the strategy graph."""

    def __init__(self, source_node: str, source_port: str,
                 target_node: str, target_port: str):
        self.source_node = source_node
        self.source_port = source_port
        self.target_node = target_node
        self.target_port = target_port

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary representation."""
        return {
            "source_node": self.source_node,
            "source_port": self.source_port,
            "target_node": self.target_node,
            "target_port": self.target_port
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphEdge':
        """Create edge from dictionary representation."""
        return cls(
            source_node=data["source_node"],
            source_port=data["source_port"],
            target_node=data["target_node"],
            target_port=data["target_port"]
        )


class StrategyGraph:
    """Represents a complete strategy graph with nodes and edges."""

    def __init__(self, name: str, version: str = "1.0.0",
                 description: str = "", nodes: Optional[List[GraphNode]] = None,
                 edges: Optional[List[GraphEdge]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.version = version
        self.description = description
        self.nodes = nodes or []
        self.edges = edges or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyGraph':
        """Create graph from dictionary representation."""
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            nodes=[GraphNode.from_dict(node_data) for node_data in data.get("nodes", [])],
            edges=[GraphEdge.from_dict(edge_data) for edge_data in data.get("edges", [])],
            metadata=data.get("metadata", {})
        )

    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID."""
        return next((node for node in self.nodes if node.id == node_id), None)

    def get_edges_for_node(self, node_id: str) -> List[GraphEdge]:
        """Get all edges connected to a node."""
        return [edge for edge in self.edges
                if edge.source_node == node_id or edge.target_node == node_id]

    def validate_topology(self) -> List[str]:
        """Validate graph topology (acyclic, valid connections)."""
        errors = []

        # Check for duplicate node IDs
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Duplicate node IDs found")

        # Check for invalid node types
        for node in self.nodes:
            if not get_node_definition(node.node_type):
                errors.append(f"Invalid node type: {node.node_type}")

        # Check for invalid connections
        for edge in self.edges:
            source_node = self.get_node_by_id(edge.source_node)
            target_node = self.get_node_by_id(edge.target_node)

            if not source_node:
                errors.append(f"Edge references non-existent source node: {edge.source_node}")
            if not target_node:
                errors.append(f"Edge references non-existent target node: {edge.target_node}")

        # Check for cycles (simplified check)
        if self._has_cycles():
            errors.append("Graph contains cycles")

        return errors

    def _has_cycles(self) -> bool:
        """Check if graph has cycles using DFS."""
        # Build adjacency list
        adj_list = {}
        for node in self.nodes:
            adj_list[node.id] = []

        for edge in self.edges:
            adj_list[edge.source_node].append(edge.target_node)

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in adj_list.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in adj_list:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False


class GraphSerializer:
    """Handles serialization of strategy graphs."""

    @staticmethod
    def serialize(graph: StrategyGraph) -> str:
        """Serialize graph to JSON string."""
        return json.dumps(graph.to_dict(), indent=2, default=str)

    @staticmethod
    def deserialize(json_str: str) -> StrategyGraph:
        """Deserialize graph from JSON string."""
        data = json.loads(json_str)
        return StrategyGraph.from_dict(data)

    @staticmethod
    def save_to_file(graph: StrategyGraph, filepath: str) -> None:
        """Save graph to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph.to_dict(), f, indent=2, default=str)

    @staticmethod
    def load_from_file(filepath: str) -> StrategyGraph:
        """Load graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return StrategyGraph.from_dict(data)