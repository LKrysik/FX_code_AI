"""
Strategy Graph Module
====================

Visual strategy building system for trading strategies.
Provides graph-based representation of trading logic with DAG execution.
"""

from .node_catalog import (
    NodeDefinition, NodeType, DataType, PortDirection,
    PortDefinition, ParameterDefinition,
    get_node_definition, get_nodes_by_type, get_nodes_by_category,
    validate_node_parameters, ALL_NODES
)

from .serializer import (
    GraphNode, GraphEdge, StrategyGraph, GraphSerializer
)

from .validators import (
    ValidationError, GraphValidator
)

from .schema_registry import (
    SchemaRegistry, SchemaVersion, SchemaMigrationError, schema_registry,
    migrate_graph_to_current, validate_graph_schema, hydrate_graph_defaults
)

__all__ = [
    # Node catalog
    'NodeDefinition', 'NodeType', 'DataType', 'PortDirection',
    'PortDefinition', 'ParameterDefinition',
    'get_node_definition', 'get_nodes_by_type', 'get_nodes_by_category',
    'validate_node_parameters', 'ALL_NODES',
    # Serialization
    'GraphNode', 'GraphEdge', 'StrategyGraph', 'GraphSerializer',
    # Validation
    'ValidationError', 'GraphValidator',
    # Schema management
    'SchemaRegistry', 'SchemaVersion', 'SchemaMigrationError', 'schema_registry',
    'migrate_graph_to_current', 'validate_graph_schema', 'hydrate_graph_defaults'
]