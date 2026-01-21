#!/usr/bin/env python3
"""
Graph Adapter - Strategy Graph to Execution Plan Translation
===========================================================

Translates visual strategy graphs into executable plans for the StrategyEvaluator.
Handles graph traversal, dependency resolution, and state machine setup for temporal conditions.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..strategy_graph.serializer import StrategyGraph, GraphNode, GraphEdge
from ..strategy_graph.node_catalog import get_node_definition, NodeType
from .strategy_evaluator import StrategyConfig, PumpSignal, SignalType, RiskLevel
from ..core.state_persistence_manager import StatePersistenceManager
from ..domain.services.streaming_indicator_engine import StreamingIndicatorEngine, IndicatorType
from ..core.event_bus import EventBus


class ExecutionNodeType(Enum):
    """Types of nodes in the execution plan."""
    DATA_SOURCE = "data_source"
    INDICATOR = "indicator"
    CONDITION = "condition"
    COMPOSITION = "composition"
    ACTION = "action"


class ExecutionState(Enum):
    """Execution states for nodes."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionNode:
    """A node in the execution plan."""
    id: str
    node_type: ExecutionNodeType
    graph_node: GraphNode
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    state: ExecutionState = ExecutionState.PENDING
    result: Any = None
    error: Optional[str] = None
    execution_order: int = 0


@dataclass
class ExecutionPlan:
    """Complete execution plan for a strategy graph."""
    id: str
    name: str
    symbol: str = "BTCUSDT"  # FIX F5: Primary trading symbol for signal generation
    nodes: Dict[str, ExecutionNode] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    state_machine_nodes: Dict[str, Any] = field(default_factory=dict)  # For temporal conditions
    data_flow: Dict[str, Any] = field(default_factory=dict)  # Data routing between nodes


class GraphAdapterError(Exception):
    """Raised when graph adaptation fails."""
    pass


class GraphAdapter:
    """
    Adapts strategy graphs to executable plans.

    Converts the visual DAG representation into a topologically sorted execution plan
    that the StrategyEvaluator can process in real-time.
    """

    def __init__(self,
                 state_persistence_manager: Optional[StatePersistenceManager] = None,
                 indicator_engine: Optional[StreamingIndicatorEngine] = None,
                 event_bus: Optional[EventBus] = None):
        self.state_machines: Dict[str, Any] = {}  # For temporal condition state
        self.state_persistence = state_persistence_manager
        self.indicator_engine = indicator_engine
        self.event_bus = event_bus
        self.strategy_name: Optional[str] = None  # Will be set when adapting graph
        self._indicator_subscriptions: Dict[str, Any] = {}  # Track indicator subscriptions

    async def adapt_graph(self, graph: StrategyGraph, symbol: str = "BTCUSDT") -> ExecutionPlan:
        """
        Convert a strategy graph to an execution plan.

        Args:
            graph: The strategy graph to adapt
            symbol: Trading symbol for state recovery

        Returns:
            Execution plan ready for execution

        Raises:
            GraphAdapterError: If adaptation fails
        """
        try:
            # Set strategy name for state persistence
            self.strategy_name = graph.name

            # Validate graph structure
            validation_errors = graph.validate_topology()
            if validation_errors:
                raise GraphAdapterError(f"Invalid graph topology: {validation_errors}")

            # Create execution nodes
            execution_nodes = self._create_execution_nodes(graph)

            # Build dependency graph
            self._build_dependencies(execution_nodes, graph)

            # Perform topological sort
            execution_order = self._topological_sort(execution_nodes)

            # Set up state machines for temporal conditions (with recovery)
            state_machines = await self._setup_state_machines(execution_nodes, symbol)

            # Create data flow mapping
            data_flow = self._create_data_flow_mapping(execution_nodes, graph)

            # Create execution plan
            # FIX F5 + #159 Transitive Dependency: Pass symbol to ExecutionPlan
            plan = ExecutionPlan(
                id=str(uuid.uuid4()),
                name=graph.name,
                symbol=symbol,  # FIX F5: Propagate symbol through execution plan
                nodes=execution_nodes,
                execution_order=execution_order,
                state_machine_nodes=state_machines,
                data_flow=data_flow
            )

            return plan

        except Exception as e:
            raise GraphAdapterError(f"Failed to adapt graph: {str(e)}") from e

    def _create_execution_nodes(self, graph: StrategyGraph) -> Dict[str, ExecutionNode]:
        """Create execution nodes from graph nodes."""
        execution_nodes = {}

        for graph_node in graph.nodes:
            # Determine execution node type
            node_type = self._map_node_type(graph_node.node_type)

            execution_node = ExecutionNode(
                id=graph_node.id,
                node_type=node_type,
                graph_node=graph_node
            )

            execution_nodes[graph_node.id] = execution_node

        return execution_nodes

    def _map_node_type(self, graph_node_type: str) -> ExecutionNodeType:
        """Map graph node type to execution node type."""
        type_mapping = {
            "price_source": ExecutionNodeType.DATA_SOURCE,
            "volume_source": ExecutionNodeType.DATA_SOURCE,
            "orderbook_source": ExecutionNodeType.DATA_SOURCE,
            "vwap": ExecutionNodeType.INDICATOR,
            "volume_surge_ratio": ExecutionNodeType.INDICATOR,
            "price_velocity": ExecutionNodeType.INDICATOR,
            "bid_ask_imbalance": ExecutionNodeType.INDICATOR,
            "threshold_condition": ExecutionNodeType.CONDITION,
            "duration_condition": ExecutionNodeType.CONDITION,
            "sequence_condition": ExecutionNodeType.CONDITION,
            "and_composition": ExecutionNodeType.COMPOSITION,
            "or_composition": ExecutionNodeType.COMPOSITION,
            "weighted_composition": ExecutionNodeType.COMPOSITION,
            "buy_signal": ExecutionNodeType.ACTION,
            "sell_signal": ExecutionNodeType.ACTION,
            "alert_action": ExecutionNodeType.ACTION,
            "emergency_exit": ExecutionNodeType.ACTION,
        }

        execution_type = type_mapping.get(graph_node_type)
        if not execution_type:
            raise GraphAdapterError(f"Unknown node type: {graph_node_type}")

        return execution_type

    def _build_dependencies(self, execution_nodes: Dict[str, ExecutionNode],
                           graph: StrategyGraph) -> None:
        """Build dependency relationships between execution nodes."""
        # Create adjacency list from edges
        for edge in graph.edges:
            source_node = execution_nodes.get(edge.source_node)
            target_node = execution_nodes.get(edge.target_node)

            if source_node and target_node:
                # Source must execute before target
                target_node.dependencies.add(edge.source_node)
                source_node.dependents.add(edge.target_node)

    def _topological_sort(self, execution_nodes: Dict[str, ExecutionNode]) -> List[str]:
        """
        Perform topological sort to determine execution order.

        Returns:
            List of node IDs in execution order
        """
        # Kahn's algorithm
        result = []
        queue = []
        in_degree = {}

        # Calculate in-degrees
        for node in execution_nodes.values():
            in_degree[node.id] = len(node.dependencies)
            if in_degree[node.id] == 0:
                queue.append(node.id)

        while queue:
            current_id = queue.pop(0)
            result.append(current_id)

            current_node = execution_nodes[current_id]
            for dependent_id in current_node.dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for cycles
        if len(result) != len(execution_nodes):
            raise GraphAdapterError("Graph contains cycles")

        return result

    async def _setup_state_machines(self, execution_nodes: Dict[str, ExecutionNode], symbol: str) -> Dict[str, Any]:
        """Set up state machines for temporal conditions with state recovery."""
        state_machines = {}

        for node in execution_nodes.values():
            if node.node_type == ExecutionNodeType.CONDITION:
                graph_node = node.graph_node

                if graph_node.node_type in ["duration_condition", "sequence_condition"]:
                    # Try to recover existing state first
                    existing_state = None
                    if self.state_persistence and self.strategy_name:
                        existing_state = await self.state_persistence.recover_temporal_state(
                            self.strategy_name, symbol, node.id
                        )

                    # Create state machine for temporal conditions
                    state_machine = self._create_temporal_state_machine(graph_node, existing_state)
                    state_machines[node.id] = state_machine

        return state_machines

    def _create_temporal_state_machine(self, graph_node: GraphNode, existing_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a state machine for temporal conditions with optional state recovery."""
        if graph_node.node_type == "duration_condition":
            # Use existing state if available, otherwise create default
            default_state = {
                "active": False,
                "start_time": None,
                "elapsed": 0
            }
            state = existing_state.get("state", default_state) if existing_state else default_state

            return {
                "type": "duration",
                "duration_seconds": graph_node.parameters.get("duration_seconds", 30),
                "reset_on_false": graph_node.parameters.get("reset_on_false", True),
                "state": state
            }
        elif graph_node.node_type == "sequence_condition":
            # Use existing state if available, otherwise create default
            default_state = {
                "sequence": [],
                "last_trigger": None
            }
            state = existing_state.get("state", default_state) if existing_state else default_state

            return {
                "type": "sequence",
                "sequence_length": graph_node.parameters.get("sequence_length", 3),
                "max_gap_seconds": graph_node.parameters.get("max_gap_seconds", 10),
                "state": state
            }

        return {}

    def _create_data_flow_mapping(self, execution_nodes: Dict[str, ExecutionNode],
                                 graph: StrategyGraph) -> Dict[str, Any]:
        """Create data flow mapping for efficient data routing."""
        data_flow = {
            "data_sources": {},
            "indicators": {},
            "conditions": {},
            "actions": {}
        }

        for node in execution_nodes.values():
            if node.node_type == ExecutionNodeType.DATA_SOURCE:
                data_flow["data_sources"][node.id] = {
                    "symbol": node.graph_node.parameters.get("symbol"),
                    "data_type": node.graph_node.node_type.replace("_source", "")
                }
            elif node.node_type == ExecutionNodeType.INDICATOR:
                data_flow["indicators"][node.id] = {
                    "type": node.graph_node.node_type,
                    "parameters": node.graph_node.parameters,
                    "inputs": []  # Will be populated from edges
                }
            elif node.node_type == ExecutionNodeType.CONDITION:
                data_flow["conditions"][node.id] = {
                    "type": node.graph_node.node_type,
                    "parameters": node.graph_node.parameters,
                    "inputs": []
                }
            elif node.node_type == ExecutionNodeType.ACTION:
                data_flow["actions"][node.id] = {
                    "type": node.graph_node.node_type,
                    "parameters": node.graph_node.parameters,
                    "inputs": []
                }

        # Populate input mappings from edges
        for edge in graph.edges:
            target_node = execution_nodes.get(edge.target_node)
            if target_node:
                if target_node.node_type == ExecutionNodeType.INDICATOR:
                    data_flow["indicators"][target_node.id]["inputs"].append({
                        "source": edge.source_node,
                        "port": edge.source_port
                    })
                elif target_node.node_type == ExecutionNodeType.CONDITION:
                    data_flow["conditions"][target_node.id]["inputs"].append({
                        "source": edge.source_node,
                        "port": edge.source_port
                    })
                elif target_node.node_type == ExecutionNodeType.ACTION:
                    data_flow["actions"][target_node.id]["inputs"].append({
                        "source": edge.source_node,
                        "port": edge.source_port
                    })

        return data_flow

    async def execute_plan(self, plan: ExecutionPlan, market_data: Dict[str, Any]) -> List[PumpSignal]:
        """
        Execute an execution plan with market data.

        Args:
            plan: The execution plan to run
            market_data: Current market data

        Returns:
            List of signals generated
        """
        signals = []
        node_results = {}

        # Execute nodes in topological order
        for node_id in plan.execution_order:
            node = plan.nodes[node_id]

            try:
                # Gather inputs from dependencies
                inputs = {}
                for dep_id in node.dependencies:
                    if dep_id in node_results:
                        inputs[dep_id] = node_results[dep_id]

                # Execute node
                result = await self._execute_node(node, inputs, market_data, plan)
                node_results[node_id] = result

                # Collect signals from action nodes
                if node.node_type == ExecutionNodeType.ACTION and result:
                    if isinstance(result, list):
                        signals.extend(result)
                    else:
                        signals.append(result)

                node.state = ExecutionState.COMPLETED
                node.result = result

            except Exception as e:
                node.state = ExecutionState.FAILED
                node.error = str(e)
                # Continue execution for other nodes

        return signals

    async def _execute_node(self, node: ExecutionNode, inputs: Dict[str, Any],
                           market_data: Dict[str, Any], plan: ExecutionPlan) -> Any:
        """Execute a single node."""
        if node.node_type == ExecutionNodeType.DATA_SOURCE:
            return await self._execute_data_source(node, market_data)
        elif node.node_type == ExecutionNodeType.INDICATOR:
            return await self._execute_indicator(node, inputs, market_data)
        elif node.node_type == ExecutionNodeType.CONDITION:
            return await self._execute_condition(node, inputs, plan)
        elif node.node_type == ExecutionNodeType.ACTION:
            return await self._execute_action(node, inputs, plan)  # FIX F5: Pass plan for symbol access
        else:
            raise GraphAdapterError(f"Unsupported node type: {node.node_type}")

    async def _execute_data_source(self, node: ExecutionNode, market_data: Dict[str, Any]) -> Any:
        """Execute a data source node."""
        symbol = node.graph_node.parameters.get("symbol")
        if not symbol:
            raise GraphAdapterError(f"Data source {node.id} missing symbol parameter")

        # Return relevant market data for the symbol
        return market_data.get(symbol, {})

    async def _execute_indicator(self, node: ExecutionNode, inputs: Dict[str, Any],
                                market_data: Dict[str, Any]) -> Any:
        """Execute an indicator node using live StreamingIndicatorEngine."""
        if not self.indicator_engine:
            # Fallback to mock values if no indicator engine available
            return await self._execute_indicator_mock(node, inputs, market_data)

        indicator_type = node.graph_node.node_type
        parameters = node.graph_node.parameters
        symbol = parameters.get("symbol", "BTCUSDT")

        try:
            # Map graph node types to IndicatorType enum
            indicator_type_map = {
                "vwap": IndicatorType.VWAP,
                "volume_surge_ratio": IndicatorType.VOLUME_SURGE_RATIO,
                "price_velocity": IndicatorType.PRICE_VELOCITY,
                "bid_ask_imbalance": IndicatorType.BID_ASK_IMBALANCE,
                "pump_magnitude_pct": IndicatorType.PUMP_MAGNITUDE_PCT,
                "volume_surge": IndicatorType.VOLUME_SURGE,
                "price_momentum": IndicatorType.PRICE_MOMENTUM,
                "volatility": IndicatorType.VOLATILITY
            }

            engine_indicator_type = indicator_type_map.get(indicator_type)
            if not engine_indicator_type:
                raise ValueError(f"Unsupported indicator type: {indicator_type}")

            # Add indicator to engine if not already present
            period = parameters.get('period', 20)
            indicator_key = f"{symbol}_{indicator_type}_{period}"
            if indicator_key not in self._indicator_subscriptions:
                # Subscribe to indicator updates for real-time execution
                await self._subscribe_to_indicator_updates(symbol, engine_indicator_type, period, parameters)

            # Get current indicator value
            indicator = self.indicator_engine.get_indicator(indicator_key)
            if indicator:
                return indicator.current_value

            # If indicator not ready, return None (will be retried on next update)
            return None

        except Exception as e:
            # Log error and fallback to mock
            print(f"Error executing live indicator {indicator_type}: {e}")
            return await self._execute_indicator_mock(node, inputs, market_data)

    async def _execute_indicator_mock(self, node: ExecutionNode, inputs: Dict[str, Any],
                                     market_data: Dict[str, Any]) -> Any:
        """Fallback mock indicator execution."""
        indicator_type = node.graph_node.node_type

        if indicator_type == "vwap":
            return 50000.0
        elif indicator_type == "volume_surge_ratio":
            return 2.5
        elif indicator_type == "price_velocity":
            return 1500.0
        elif indicator_type == "bid_ask_imbalance":
            return 0.3
        elif indicator_type == "pump_magnitude_pct":
            return 5.0
        elif indicator_type == "volume_surge":
            return 3.0
        elif indicator_type == "price_momentum":
            return 2.0
        elif indicator_type == "volatility":
            return 0.05

        return None

    async def _subscribe_to_indicator_updates(self, symbol: str, indicator_type: IndicatorType,
                                            period: int, parameters: Dict[str, Any]) -> None:
        """Subscribe to indicator updates for real-time execution."""
        if not self.event_bus:
            return

        indicator_key = f"{symbol}_{indicator_type.value}_{period}"

        # Add indicator to engine
        try:
            # Remove period and symbol from parameters to avoid duplicate keyword arguments
            filtered_params = {k: v for k, v in parameters.items() if k not in ['period', 'symbol']}
            key = self.indicator_engine.add_indicator(
                symbol=symbol,
                indicator_type=indicator_type,
                period=period,
                **filtered_params
            )
            self._indicator_subscriptions[indicator_key] = key
        except Exception as e:
            print(f"Failed to add indicator {indicator_type.value} for {symbol}: {e}")

    async def _execute_condition(self, node: ExecutionNode, inputs: Dict[str, Any],
                                plan: ExecutionPlan) -> bool:
        """Execute a condition node."""
        condition_type = node.graph_node.node_type
        parameters = node.graph_node.parameters

        # Get state machine if it exists
        state_machine = plan.state_machine_nodes.get(node.id)

        if condition_type == "threshold_condition":
            # Simple threshold comparison
            threshold = parameters.get("threshold", 0.0)
            operator = parameters.get("operator", ">")

            # Get input value (from first input)
            input_values = list(inputs.values())
            if not input_values:
                return False

            value = input_values[0]
            if operator == ">":
                return value > threshold
            elif operator == "<":
                return value < threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "=":
                return value == threshold

        elif condition_type == "duration_condition" and state_machine:
            # Temporal duration condition
            duration = parameters.get("duration_seconds", 30)
            reset_on_false = parameters.get("reset_on_false", True)

            # Get input value
            input_values = list(inputs.values())
            current_value = input_values[0] if input_values else False

            # Update state machine
            state = state_machine["state"]
            current_time = asyncio.get_event_loop().time()

            if current_value:
                if not state["active"]:
                    state["active"] = True
                    state["start_time"] = current_time
                    state["elapsed"] = 0
                else:
                    state["elapsed"] = current_time - state["start_time"]
            elif reset_on_false:
                state["active"] = False
                state["start_time"] = None
                state["elapsed"] = 0

            # Persist state after update
            if self.state_persistence and self.strategy_name:
                await self.state_persistence.persist_temporal_state(
                    self.strategy_name, "BTCUSDT", node.id, state_machine
                )

            return state["elapsed"] >= duration

        return False

    async def _execute_action(self, node: ExecutionNode, inputs: Dict[str, Any],
                              plan: ExecutionPlan) -> Optional[PumpSignal]:
        """Execute an action node.

        FIX F5 + #71 First Principles: Symbol now flows from plan, not hardcoded.
        Risk mitigation: #61 Pre-mortem - prevents wrong-symbol signal generation.
        """
        action_type = node.graph_node.node_type
        parameters = node.graph_node.parameters

        # Check if condition inputs are true
        input_values = list(inputs.values())
        if not input_values or not all(input_values):
            return None

        # FIX F5: Use symbol from execution plan instead of hardcoded value
        # #79 Operational Definition: Symbol is operationally defined as plan.symbol
        symbol = plan.symbol

        # Create signal based on action type
        if action_type == "buy_signal":
            return PumpSignal(
                symbol=symbol,  # FIX F5: Use plan.symbol
                signal_type=SignalType.BUY,
                confidence=0.8,
                position_size=parameters.get("position_size", 100.0),
                risk_level=RiskLevel.MEDIUM,
                indicators={},
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                reason=f"Graph-based buy signal for {symbol}"
            )
        elif action_type == "sell_signal":
            return PumpSignal(
                symbol=symbol,  # FIX F5: Use plan.symbol
                signal_type=SignalType.SELL,
                confidence=0.7,
                position_size=parameters.get("position_size", 100.0),
                risk_level=RiskLevel.LOW,
                indicators={},
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                reason=f"Graph-based sell signal for {symbol}"
            )

        return None


@dataclass
class LiveExecutionSession:
    """Represents a live execution session for a strategy."""
    session_id: str
    strategy_name: str
    plan: ExecutionPlan
    symbol: str
    active: bool = True
    last_execution: Optional[float] = None
    execution_count: int = 0
    signals_generated: List[PumpSignal] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class LiveGraphExecutor:
    """
    Executes strategy graphs in real-time with live indicator data.

    Manages live execution sessions that continuously evaluate strategies
    as indicators update, providing real-time trading signals.
    """

    def __init__(self, graph_adapter: GraphAdapter, event_bus: EventBus):
        self.graph_adapter = graph_adapter
        self.event_bus = event_bus
        self.sessions: Dict[str, LiveExecutionSession] = {}
        self._indicator_handler_task: Optional[asyncio.Task] = None
        self.logger = None  # Will be set if available

    async def start(self) -> None:
        """Start the live executor and subscribe to indicator updates."""
        if self._indicator_handler_task is None:
            self._indicator_handler_task = await self.event_bus.subscribe(
                "indicator.updated", self._handle_indicator_update
            )

    async def stop(self) -> None:
        """Stop the live executor and cancel all sessions."""
        # Stop all sessions
        for session in self.sessions.values():
            session.active = False

        # Cancel handler task
        if self._indicator_handler_task:
            await self.event_bus.unsubscribe(self._indicator_handler_task)
            self._indicator_handler_task = None

        self.sessions.clear()

    async def start_live_session(self, strategy_name: str, graph: StrategyGraph,
                                symbol: str = "BTCUSDT") -> str:
        """Start a live execution session for a strategy."""
        # Adapt graph to execution plan
        plan = await self.graph_adapter.adapt_graph(graph, symbol)

        # Create session
        session_id = f"{strategy_name}_{symbol}_{int(asyncio.get_event_loop().time())}"
        session = LiveExecutionSession(
            session_id=session_id,
            strategy_name=strategy_name,
            plan=plan,
            symbol=symbol
        )

        self.sessions[session_id] = session

        if self.logger:
            self.logger.info("live_execution.session_started", {
                "session_id": session_id,
                "strategy": strategy_name,
                "symbol": symbol
            })

        return session_id

    async def stop_live_session(self, session_id: str) -> bool:
        """Stop a live execution session."""
        if session_id in self.sessions:
            self.sessions[session_id].active = False
            del self.sessions[session_id]
            return True
        return False

    async def _handle_indicator_update(self, data: Dict[str, Any]) -> None:
        """Handle indicator updates and trigger strategy re-evaluation."""
        if not isinstance(data, dict):
            return

        symbol = data.get("symbol")
        if not symbol:
            return

        # Find active sessions for this symbol
        relevant_sessions = [
            session for session in self.sessions.values()
            if session.active and session.symbol == symbol
        ]

        if not relevant_sessions:
            return

        # Re-evaluate each relevant session
        for session in relevant_sessions:
            try:
                await self._evaluate_session(session, data)
            except Exception as e:
                error_msg = f"Session {session.session_id} evaluation error: {e}"
                session.errors.append(error_msg)
                if self.logger:
                    self.logger.error("live_execution.session_error", {
                        "session_id": session.session_id,
                        "error": str(e)
                    })

    async def _evaluate_session(self, session: LiveExecutionSession, indicator_data: Dict[str, Any]) -> None:
        """Evaluate a session with current indicator data."""
        # Create market data dict from indicator update
        market_data = {
            session.symbol: {
                "indicators": indicator_data,
                "timestamp": indicator_data.get("timestamp", asyncio.get_event_loop().time())
            }
        }

        # Execute the plan
        signals = await self.graph_adapter.execute_plan(session.plan, market_data)

        # Update session stats
        session.last_execution = asyncio.get_event_loop().time()
        session.execution_count += 1

        # Collect signals
        if signals:
            session.signals_generated.extend(signals)

            # Publish signals via event bus
            for signal in signals:
                await self.event_bus.publish("signal_generated", {
                    "session_id": session.session_id,
                    "strategy_name": session.strategy_name,
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "position_size": signal.position_size,
                    "risk_level": signal.risk_level.value,
                    "indicators": signal.indicators,
                    "timestamp": signal.timestamp,
                    "reason": signal.reason,
                    # OrderManager required fields
                    "side": "buy" if signal.signal_type.value == "BUY" else "sell",
                    "quantity": signal.position_size,
                    "price": signal.indicators.get("price", 0.0),
                    # TradingPersistenceService fields
                    # FIX F4: signal.timestamp is already in ms, no need to multiply
                    "signal_id": f"signal_{session.strategy_name}_{signal.symbol}_{int(signal.timestamp)}",
                    "strategy_id": session.strategy_name,
                    "action": signal.signal_type.value,
                    "triggered": True,
                    "conditions_met": {"confidence": signal.confidence, "risk_level": signal.risk_level.value},
                    "indicator_values": signal.indicators,
                    "metadata": {"reason": signal.reason, "session_id": session.session_id}
                })

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a live execution session."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "strategy_name": session.strategy_name,
            "symbol": session.symbol,
            "active": session.active,
            "execution_count": session.execution_count,
            "last_execution": session.last_execution,
            "signals_generated": len(session.signals_generated),
            "error_count": len(session.errors),
            "recent_errors": session.errors[-5:] if session.errors else []
        }

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active live execution sessions."""
        return [
            self.get_session_status(session_id)
            for session_id in self.sessions.keys()
            if self.sessions[session_id].active
        ]


# Global instances - will be initialized when needed
graph_adapter: Optional[GraphAdapter] = None
live_executor: Optional[LiveGraphExecutor] = None

def get_graph_adapter(indicator_engine: Optional['StreamingIndicatorEngine'] = None) -> GraphAdapter:
    """Get or create the global graph adapter instance.

    BUG-DV-020 FIX: Accept indicator_engine as parameter for proper DI.
    When called from Container, indicator_engine should be provided.
    When called without (fallback), indicator_engine will be None.

    Args:
        indicator_engine: Optional StreamingIndicatorEngine instance from Container.
                         If None, graph-based indicator calculations will not work.
    """
    global graph_adapter
    if graph_adapter is None:
        # ✅ REFACTORING FIX: Don't try to import global singletons that no longer exist
        # StreamingIndicatorEngine is now created via Container, not as a global instance
        # This fallback pattern creates GraphAdapter without dependencies
        try:
            from ..core.state_persistence_manager import state_persistence_manager
            from ..core.event_bus import event_bus

            graph_adapter = GraphAdapter(
                state_persistence_manager=state_persistence_manager,
                indicator_engine=indicator_engine,  # BUG-DV-020 FIX: Use injected engine
                event_bus=event_bus
            )
        except ImportError:
            # Fallback without dependencies
            graph_adapter = GraphAdapter(indicator_engine=indicator_engine)

    # BUG-DV-020 FIX: Update indicator_engine if provided and current is None
    elif indicator_engine is not None and graph_adapter.indicator_engine is None:
        graph_adapter.indicator_engine = indicator_engine

    return graph_adapter

def get_live_executor(event_bus=None, indicator_engine=None) -> LiveGraphExecutor:
    """Get or create the global live executor instance.

    BUG-DV-020 FIX: Accept indicator_engine to pass to graph_adapter.

    Args:
        event_bus: Optional EventBus for event propagation
        indicator_engine: Optional StreamingIndicatorEngine from Container
    """
    global live_executor
    if live_executor is None:
        adapter = get_graph_adapter(indicator_engine=indicator_engine)
        if event_bus is None:
            # Try to import global event_bus for backward compatibility
            try:
                from ..core.event_bus import event_bus
            except ImportError:
                # This should not happen in production
                raise RuntimeError("EventBus not available for live execution - must be passed as parameter")
        live_executor = LiveGraphExecutor(adapter, event_bus)

    return live_executor