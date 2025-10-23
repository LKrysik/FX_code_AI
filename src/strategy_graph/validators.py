#!/usr/bin/env python3
"""
Strategy Graph Validators
========================

Comprehensive validation for strategy graphs including structural,
logical, and business rule validation.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from .serializer import StrategyGraph, GraphNode, GraphEdge
from .node_catalog import get_node_definition, validate_node_parameters, NodeType, DataType


class ValidationError:
    """Represents a validation error with context."""

    def __init__(self, error_type: str, message: str, node_id: Optional[str] = None,
                 edge_id: Optional[str] = None, severity: str = "error"):
        self.error_type = error_type
        self.message = message
        self.node_id = node_id
        self.edge_id = edge_id
        self.severity = severity  # "error", "warning", "info"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "type": self.error_type,
            "message": self.message,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "severity": self.severity
        }


class GraphValidator:
    """Validates strategy graphs comprehensively."""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate(self, graph: StrategyGraph) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Perform complete validation of the strategy graph."""
        self.errors = []
        self.warnings = []

        # Structural validation
        self._validate_structure(graph)

        # Node validation
        self._validate_nodes(graph)

        # Edge validation
        self._validate_edges(graph)

        # Logical validation
        self._validate_logic(graph)

        # Business rule validation
        self._validate_business_rules(graph)

        return self.errors, self.warnings

    def _validate_structure(self, graph: StrategyGraph) -> None:
        """Validate basic graph structure."""
        # Check for empty graph
        if not graph.nodes:
            self.errors.append(ValidationError(
                "empty_graph", "Graph contains no nodes", severity="error"
            ))
            return

        # Check for duplicate node IDs
        node_ids = [node.id for node in graph.nodes]
        duplicates = set([x for x in node_ids if node_ids.count(x) > 1])
        for dup_id in duplicates:
            self.errors.append(ValidationError(
                "duplicate_node", f"Duplicate node ID: {dup_id}", severity="error"
            ))

        # Check for duplicate edges (same source/target/port combination)
        edge_signatures = []
        for i, edge in enumerate(graph.edges):
            signature = f"{edge.source_node}:{edge.source_port}->{edge.target_node}:{edge.target_port}"
            if signature in edge_signatures:
                self.errors.append(ValidationError(
                    "duplicate_edge", f"Duplicate edge: {signature}",
                    edge_id=f"edge_{i}", severity="warning"
                ))
            edge_signatures.append(signature)

    def _validate_nodes(self, graph: StrategyGraph) -> None:
        """Validate individual nodes."""
        for node in graph.nodes:
            # Check node type exists
            node_def = get_node_definition(node.node_type)
            if not node_def:
                self.errors.append(ValidationError(
                    "invalid_node_type", f"Unknown node type: {node.node_type}",
                    node_id=node.id, severity="error"
                ))
                continue

            # Validate parameters
            param_errors = validate_node_parameters(node.node_type, node.parameters)
            for error in param_errors:
                self.errors.append(ValidationError(
                    "invalid_parameter", error, node_id=node.id, severity="error"
                ))

            # Check for required connections based on node type
            self._validate_node_connectivity(graph, node, node_def)

    def _validate_node_connectivity(self, graph: StrategyGraph, node: GraphNode,
                                   node_def) -> None:
        """Validate that node has required connections."""
        edges = graph.get_edges_for_node(node.id)

        # Check input connections
        incoming_edges = [e for e in edges if e.target_node == node.id]
        required_inputs = [p for p in node_def.ports if p.direction.name == "INPUT" and p.required]

        for req_port in required_inputs:
            has_connection = any(e.target_port == req_port.name for e in incoming_edges)
            if not has_connection:
                self.errors.append(ValidationError(
                    "missing_input", f"Required input '{req_port.name}' not connected",
                    node_id=node.id, severity="error"
                ))

        # Check output connections for action nodes (should have consumers)
        if node_def.type == NodeType.ACTION:
            outgoing_edges = [e for e in edges if e.source_node == node.id]
            if not outgoing_edges:
                self.warnings.append(ValidationError(
                    "unused_output", "Action node has no output connections",
                    node_id=node.id, severity="warning"
                ))

    def _validate_edges(self, graph: StrategyGraph) -> None:
        """Validate edges and their connections."""
        for edge in graph.edges:
            source_node = graph.get_node_by_id(edge.source_node)
            target_node = graph.get_node_by_id(edge.target_node)

            # Check nodes exist
            if not source_node:
                self.errors.append(ValidationError(
                    "invalid_edge", f"Source node does not exist: {edge.source_node}",
                    severity="error"
                ))
                continue
            if not target_node:
                self.errors.append(ValidationError(
                    "invalid_edge", f"Target node does not exist: {edge.target_node}",
                    severity="error"
                ))
                continue

            # Check port compatibility
            source_def = get_node_definition(source_node.node_type)
            target_def = get_node_definition(target_node.node_type)

            if source_def and target_def:
                self._validate_port_compatibility(edge, source_def, target_def)

    def _validate_port_compatibility(self, edge: GraphEdge, source_def, target_def) -> None:
        """Validate that connected ports have compatible data types."""
        # Find source port
        source_port = None
        for port in source_def.ports:
            if port.name == edge.source_port and port.direction.name == "OUTPUT":
                source_port = port
                break

        # Find target port
        target_port = None
        for port in target_def.ports:
            if port.name == edge.target_port and port.direction.name == "INPUT":
                target_port = port
                break

        if not source_port:
            self.errors.append(ValidationError(
                "invalid_port", f"Source port '{edge.source_port}' does not exist",
                severity="error"
            ))
            return

        if not target_port:
            self.errors.append(ValidationError(
                "invalid_port", f"Target port '{edge.target_port}' does not exist",
                severity="error"
            ))
            return

        # Check data type compatibility
        if source_port.data_type != target_port.data_type:
            # Allow some automatic conversions
            compatible_types = {
                DataType.PRICE: [DataType.INDICATOR_VALUE],
                DataType.VOLUME: [DataType.INDICATOR_VALUE],
                DataType.INDICATOR_VALUE: [DataType.PRICE, DataType.VOLUME]
            }

            if target_port.data_type not in compatible_types.get(source_port.data_type, []):
                self.errors.append(ValidationError(
                    "type_mismatch",
                    f"Data type mismatch: {source_port.data_type.value} -> {target_port.data_type.value}",
                    severity="error"
                ))

    def _validate_logic(self, graph: StrategyGraph) -> None:
        """Validate logical consistency of the graph."""
        # Check for cycles
        if self._has_cycles(graph):
            self.errors.append(ValidationError(
                "cycle_detected", "Graph contains cycles", severity="error"
            ))

        # Check for disconnected components
        components = self._find_connected_components(graph)
        if len(components) > 1:
            self.warnings.append(ValidationError(
                "disconnected_components",
                f"Graph has {len(components)} disconnected components",
                severity="warning"
            ))

        # Validate data flow paths
        self._validate_data_flow(graph)

    def _has_cycles(self, graph: StrategyGraph) -> bool:
        """Check if graph has cycles."""
        # Build adjacency list
        adj_list = {node.id: [] for node in graph.nodes}
        for edge in graph.edges:
            adj_list[edge.source_node].append(edge.target_node)

        # DFS cycle detection
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

    def _find_connected_components(self, graph: StrategyGraph) -> List[Set[str]]:
        """Find connected components in the graph."""
        adj_list = {node.id: set() for node in graph.nodes}
        for edge in graph.edges:
            adj_list[edge.source_node].add(edge.target_node)
            adj_list[edge.target_node].add(edge.source_node)

        visited = set()
        components = []

        def dfs(node_id: str, component: Set[str]) -> None:
            visited.add(node_id)
            component.add(node_id)
            for neighbor in adj_list.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor, component)

        for node in graph.nodes:
            if node.id not in visited:
                component = set()
                dfs(node.id, component)
                components.append(component)

        return components

    def _validate_data_flow(self, graph: StrategyGraph) -> None:
        """Validate that data can flow from sources to sinks."""
        # Find data sources and sinks
        sources = []
        sinks = []

        for node in graph.nodes:
            node_def = get_node_definition(node.node_type)
            if not node_def:
                continue

            has_inputs = any(p.direction.name == "INPUT" for p in node_def.ports)
            has_outputs = any(p.direction.name == "OUTPUT" for p in node_def.ports)

            if not has_inputs and has_outputs:
                sources.append(node.id)
            elif has_inputs and not has_outputs:
                sinks.append(node.id)

        # Check that all sinks are reachable from sources
        reachable = set()
        for source in sources:
            self._find_reachable_nodes(graph, source, reachable)

        unreachable_sinks = [sink for sink in sinks if sink not in reachable]
        for sink in unreachable_sinks:
            self.warnings.append(ValidationError(
                "unreachable_sink", f"Sink node '{sink}' is not reachable from any source",
                node_id=sink, severity="warning"
            ))

    def _find_reachable_nodes(self, graph: StrategyGraph, start_node: str,
                             reachable: Set[str]) -> None:
        """Find all nodes reachable from start_node."""
        if start_node in reachable:
            return

        reachable.add(start_node)
        for edge in graph.edges:
            if edge.source_node == start_node:
                self._find_reachable_nodes(graph, edge.target_node, reachable)

    def _validate_business_rules(self, graph: StrategyGraph) -> None:
        """Validate business rules and best practices."""
        # Check for reasonable graph size
        if len(graph.nodes) > 100:
            self.warnings.append(ValidationError(
                "large_graph", f"Graph has {len(graph.nodes)} nodes, consider simplifying",
                severity="warning"
            ))

        # Check for nodes with too many connections
        for node in graph.nodes:
            connections = len(graph.get_edges_for_node(node.id))
            if connections > 10:
                self.warnings.append(ValidationError(
                    "high_connectivity", f"Node '{node.id}' has {connections} connections",
                    node_id=node.id, severity="warning"
                ))

        # Validate trading strategy patterns
        self._validate_trading_patterns(graph)

    def _validate_trading_patterns(self, graph: StrategyGraph) -> None:
        """Validate common trading strategy patterns."""
        action_nodes = [node for node in graph.nodes
                       if get_node_definition(node.node_type) and
                       get_node_definition(node.node_type).type == NodeType.ACTION]

        # Check for conflicting actions
        buy_signals = [n for n in action_nodes if n.node_type == "buy_signal"]
        sell_signals = [n for n in action_nodes if n.node_type == "sell_signal"]

        if len(buy_signals) > 1:
            self.warnings.append(ValidationError(
                "multiple_buy_signals", f"Multiple buy signals ({len(buy_signals)}) may conflict",
                severity="warning"
            ))

        if len(sell_signals) > 1:
            self.warnings.append(ValidationError(
                "multiple_sell_signals", f"Multiple sell signals ({len(sell_signals)}) may conflict",
                severity="warning"
            ))

        # Check for risk management
        has_emergency_exit = any(n.node_type == "emergency_exit" for n in action_nodes)
        if not has_emergency_exit:
            self.warnings.append(ValidationError(
                "no_emergency_exit", "Strategy lacks emergency exit mechanism",
                severity="warning"
            ))