#!/usr/bin/env python3
"""
Strategy Graph Schema Registry
==============================

Manages schema versions, migrations, and backward compatibility for strategy graphs.
Ensures smooth evolution of graph schemas over time.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from .serializer import StrategyGraph, GraphNode, GraphEdge


@dataclass
class SchemaVersion:
    """Represents a schema version with migration capabilities."""
    version: str
    description: str
    release_date: str
    is_current: bool = False

    # Migration functions
    upgrade_from_previous: Optional[Callable[[StrategyGraph], StrategyGraph]] = None
    downgrade_to_previous: Optional[Callable[[StrategyGraph], StrategyGraph]] = None


class SchemaMigrationError(Exception):
    """Raised when schema migration fails."""
    pass


class SchemaRegistry:
    """
    Registry for managing strategy graph schema versions and migrations.

    Handles:
    - Schema version tracking
    - Automatic migrations between versions
    - Backward compatibility
    - Default parameter hydration for legacy nodes
    """

    def __init__(self):
        self.versions: Dict[str, SchemaVersion] = {}
        self._current_version = "1.0.0"
        self._register_versions()

    def _register_versions(self):
        """Register all known schema versions."""

        # Version 1.0.0 - Initial release
        self.versions["1.0.0"] = SchemaVersion(
            version="1.0.0",
            description="Initial strategy graph schema with basic node types",
            release_date="2025-10-16",
            is_current=True
        )

        # Future versions can be added here as the schema evolves
        # Example:
        # self.versions["1.1.0"] = SchemaVersion(
        #     version="1.1.0",
        #     description="Added advanced composition nodes",
        #     release_date="2025-11-01",
        #     upgrade_from_previous=self._upgrade_1_0_0_to_1_1_0,
        #     downgrade_to_previous=self._downgrade_1_1_0_to_1_0_0
        # )

    def get_current_version(self) -> str:
        """Get the current schema version."""
        return self._current_version

    def is_valid_version(self, version: str) -> bool:
        """Check if a version is valid."""
        return version in self.versions

    def migrate_graph(self, graph: StrategyGraph, target_version: Optional[str] = None) -> StrategyGraph:
        """
        Migrate a graph to a target version.

        Args:
            graph: The graph to migrate
            target_version: Target version (defaults to current)

        Returns:
            Migrated graph

        Raises:
            SchemaMigrationError: If migration fails
        """
        if target_version is None:
            target_version = self._current_version

        current_version = graph.metadata.get("schema_version", "1.0.0")

        if current_version == target_version:
            # Still set the version if it's not set
            if "schema_version" not in graph.metadata:
                graph.metadata["schema_version"] = target_version
            return graph

        # For now, only support migration to current version
        # In the future, implement proper version comparison and chaining
        if target_version != self._current_version:
            raise SchemaMigrationError(f"Migration to version {target_version} not supported")

        # Apply migrations step by step
        migrated_graph = graph

        # Set schema version in metadata
        migrated_graph.metadata["schema_version"] = target_version

        return migrated_graph

    def hydrate_default_parameters(self, graph: StrategyGraph) -> StrategyGraph:
        """
        Hydrate default parameters for nodes that don't have them specified.

        This ensures backward compatibility when new parameters are added to node types.
        """
        from .node_catalog import get_node_definition

        for node in graph.nodes:
            node_def = get_node_definition(node.node_type)
            if not node_def:
                continue

            # Ensure parameters dict exists
            if not hasattr(node, 'parameters') or node.parameters is None:
                node.parameters = {}

            # Add default values for missing parameters
            for param_def in node_def.parameters:
                if param_def.name not in node.parameters:
                    node.parameters[param_def.name] = param_def.default

        return graph

    def validate_schema_version(self, graph: StrategyGraph) -> List[str]:
        """
        Validate that a graph conforms to its declared schema version.

        Returns:
            List of validation errors
        """
        schema_version = graph.metadata.get("schema_version", "1.0.0")

        if not self.is_valid_version(schema_version):
            return [f"Unknown schema version: {schema_version}"]

        # Version-specific validations can be added here
        errors = []

        if schema_version == "1.0.0":
            errors.extend(self._validate_v1_0_0_schema(graph))

        return errors

    def _validate_v1_0_0_schema(self, graph: StrategyGraph) -> List[str]:
        """Validate graph against v1.0.0 schema requirements."""
        errors = []

        # Check that all nodes have required fields
        for node in graph.nodes:
            if not hasattr(node, 'id') or not node.id:
                errors.append("Node missing required 'id' field")
            if not hasattr(node, 'node_type') or not node.node_type:
                errors.append(f"Node {node.id} missing required 'node_type' field")
            if not hasattr(node, 'position') or not node.position:
                errors.append(f"Node {node.id} missing required 'position' field")

        # Check that all edges have required fields
        for edge in graph.edges:
            required_fields = ['source_node', 'source_port', 'target_node', 'target_port']
            for field in required_fields:
                if not hasattr(edge, field) or not getattr(edge, field):
                    errors.append(f"Edge missing required '{field}' field")

        return errors

    def get_version_info(self, version: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a schema version."""
        if version is None:
            version = self._current_version

        schema_version = self.versions.get(version)
        if not schema_version:
            return {"error": f"Unknown version: {version}"}

        return {
            "version": schema_version.version,
            "description": schema_version.description,
            "release_date": schema_version.release_date,
            "is_current": schema_version.is_current
        }

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all registered schema versions."""
        return [
            {
                "version": v.version,
                "description": v.description,
                "release_date": v.release_date,
                "is_current": v.is_current
            }
            for v in self.versions.values()
        ]

    # Future migration functions (examples)
    def _upgrade_1_0_0_to_1_1_0(self, graph: StrategyGraph) -> StrategyGraph:
        """Example migration function."""
        # Add new fields, transform data structures, etc.
        # This is a placeholder for future schema evolution
        return graph

    def _downgrade_1_1_0_to_1_0_0(self, graph: StrategyGraph) -> StrategyGraph:
        """Example downgrade function."""
        # Remove new fields, revert transformations, etc.
        return graph


# Global schema registry instance
schema_registry = SchemaRegistry()


def migrate_graph_to_current(graph: StrategyGraph) -> StrategyGraph:
    """Convenience function to migrate a graph to the current schema version."""
    return schema_registry.migrate_graph(graph)


def validate_graph_schema(graph: StrategyGraph) -> List[str]:
    """Convenience function to validate a graph's schema."""
    return schema_registry.validate_schema_version(graph)


def hydrate_graph_defaults(graph: StrategyGraph) -> StrategyGraph:
    """Convenience function to hydrate default parameters."""
    return schema_registry.hydrate_default_parameters(graph)