#!/usr/bin/env python3
"""
Strategy Graph Node Catalog
===========================

Canonical definitions for all node types in the strategy graph system.
Provides strongly typed node definitions with metadata contracts.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid


class NodeType(Enum):
    """Strategy graph node types."""
    DATA_SOURCE = "data_source"
    INDICATOR = "indicator"
    CONDITION = "condition"
    COMPOSITION = "composition"
    ACTION = "action"


class DataType(Enum):
    """Data types that can flow between nodes."""
    PRICE = "price"
    VOLUME = "volume"
    INDICATOR_VALUE = "indicator_value"
    BOOLEAN = "boolean"
    SIGNAL = "signal"


class PortDirection(Enum):
    """Port direction for node connections."""
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class PortDefinition:
    """Definition of a node port."""
    name: str
    data_type: DataType
    direction: PortDirection
    required: bool = True
    description: str = ""


@dataclass
class ParameterDefinition:
    """Definition of a node parameter."""
    name: str
    type: str  # Python type hint as string
    default: Any = None
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class NodeDefinition:
    """Complete definition of a strategy graph node."""
    id: str
    name: str
    type: NodeType
    category: str
    description: str
    version: str = "1.0.0"
    ports: List[PortDefinition] = field(default_factory=list)
    parameters: List[ParameterDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_input_ports(self) -> List[PortDefinition]:
        """Get all input ports."""
        return [p for p in self.ports if p.direction == PortDirection.INPUT]

    def get_output_ports(self) -> List[PortDefinition]:
        """Get all output ports."""
        return [p for p in self.ports if p.direction == PortDirection.OUTPUT]

    def get_required_parameters(self) -> List[ParameterDefinition]:
        """Get required parameters."""
        return [p for p in self.parameters if p.required]


# Data Source Nodes
DATA_SOURCE_NODES = [
    NodeDefinition(
        id="price_source",
        name="Price Source",
        type=NodeType.DATA_SOURCE,
        category="Market Data",
        description="Provides real-time price data from exchange",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.OUTPUT,
                         description="Current price data")
        ],
        parameters=[
            ParameterDefinition("symbol", "str", required=True,
                              description="Trading symbol (e.g., BTC_USDT)"),
            ParameterDefinition("update_frequency", "int", default=1000, required=False,
                              min_value=100, max_value=10000,
                              description="Update frequency in milliseconds")
        ]
    ),
    NodeDefinition(
        id="volume_source",
        name="Volume Source",
        type=NodeType.DATA_SOURCE,
        category="Market Data",
        description="Provides real-time volume data from exchange",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.OUTPUT,
                         description="Volume data")
        ],
        parameters=[
            ParameterDefinition("symbol", "str", required=True,
                              description="Trading symbol"),
            ParameterDefinition("aggregation", "str", default="trade", required=False,
                              description="Volume aggregation method")
        ]
    ),
    NodeDefinition(
        id="orderbook_source",
        name="Order Book Source",
        type=NodeType.DATA_SOURCE,
        category="Market Data",
        description="Provides order book depth data",
        ports=[
            PortDefinition("bid_ask", DataType.INDICATOR_VALUE, PortDirection.OUTPUT,
                         description="Bid/ask spread data")
        ],
        parameters=[
            ParameterDefinition("symbol", "str", required=True),
            ParameterDefinition("depth", "int", default=10, required=False, min_value=1, max_value=50)
        ]
    )
]

# Indicator Nodes
INDICATOR_NODES = [
    # GRUPA A: Fundamental Aggregators
    NodeDefinition(
        id="max_price",
        name="Max Price",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="Maximum price in time window",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("max_price", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="min_price",
        name="Min Price",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="Minimum price in time window",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("min_price", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="first_price",
        name="First Price",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="First price in time window",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("first_price", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="last_price",
        name="Last Price",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="Last price in time window",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("last_price", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="twpa",
        name="TWPA",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="Time-Weighted Price Average",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("twpa", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="vwap",
        name="VWAP",
        type=NodeType.INDICATOR,
        category="Price Indicators",
        description="Volume Weighted Average Price",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("vwap", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="sum_volume",
        name="Sum Volume",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Total volume in time window",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("sum_volume", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="avg_volume",
        name="Average Volume",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Average volume per deal in time window",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("avg_volume", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="count_deals",
        name="Count Deals",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Number of deals in time window",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("count_deals", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("t1", "float", default=300.0, required=False, min_value=0.0, max_value=86400.0,
                              description="Start time (seconds ago)"),
            ParameterDefinition("t2", "float", default=0.0, required=False, min_value=0.0, max_value=86400.0,
                              description="End time (seconds ago)")
        ]
    ),
    NodeDefinition(
        id="volume_surge_ratio",
        name="Volume Surge Ratio",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Detects volume surges relative to baseline",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("vsr", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("baseline_window", "int", default=3600, required=False,
                              description="Baseline calculation window"),
            ParameterDefinition("surge_threshold", "float", default=2.0, required=False, min_value=1.1,
                              description="Surge multiplier threshold")
        ]
    ),
    NodeDefinition(
        id="price_velocity",
        name="Price Velocity",
        type=NodeType.INDICATOR,
        category="Momentum Indicators",
        description="Rate of price change",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("velocity", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("period", "int", default=60, required=False, min_value=10,
                              description="Velocity calculation period")
        ]
    ),
    NodeDefinition(
        id="bid_ask_imbalance",
        name="Bid-Ask Imbalance",
        type=NodeType.INDICATOR,
        category="Order Book Indicators",
        description="Order book imbalance indicator",
        ports=[
            PortDefinition("orderbook", DataType.INDICATOR_VALUE, PortDirection.INPUT, required=True),
            PortDefinition("imbalance", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("depth_levels", "int", default=5, required=False, min_value=1, max_value=20)
        ]
    ),
    NodeDefinition(
        id="volume_spike_ratio",
        name="Volume Spike Ratio",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Detects volume surges relative to baseline",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("vsr", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("current_window_seconds", "int", default=30, required=False, min_value=10, max_value=300),
            ParameterDefinition("baseline_window_seconds", "int", default=1800, required=False, min_value=300, max_value=3600)
        ]
    ),
    NodeDefinition(
        id="trade_frequency_spike",
        name="Trade Frequency Spike",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Detects surges in trade frequency",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("tfs", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("current_window_seconds", "int", default=30, required=False, min_value=10, max_value=300),
            ParameterDefinition("baseline_window_seconds", "int", default=1800, required=False, min_value=300, max_value=3600)
        ]
    ),
    NodeDefinition(
        id="price_acceleration",
        name="Price Acceleration",
        type=NodeType.INDICATOR,
        category="Momentum Indicators",
        description="Rate of price change (velocity/acceleration)",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("acceleration", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("window_seconds", "int", default=60, required=False, min_value=30, max_value=300),
            ParameterDefinition("derivative_order", "int", default=1, required=False, min_value=1, max_value=2)
        ]
    ),
    NodeDefinition(
        id="momentum_decay",
        name="Momentum Decay",
        type=NodeType.INDICATOR,
        category="Momentum Indicators",
        description="Loss of momentum relative to recent peak",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("decay", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("peak_lookback_seconds", "int", default=300, required=False, min_value=60, max_value=1800)
        ]
    ),
    NodeDefinition(
        id="spread_widening_ratio",
        name="Spread Widening Ratio",
        type=NodeType.INDICATOR,
        category="Order Book Indicators",
        description="Detects spread expansion relative to baseline",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("swr", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("current_window_seconds", "int", default=30, required=False, min_value=10, max_value=300),
            ParameterDefinition("baseline_window_seconds", "int", default=1800, required=False, min_value=300, max_value=3600)
        ]
    ),
    NodeDefinition(
        id="liquidity_drain",
        name="Liquidity Drain",
        type=NodeType.INDICATOR,
        category="Order Book Indicators",
        description="Analyzes changes in market liquidity",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("drain", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("window_seconds", "int", default=60, required=False, min_value=30, max_value=300)
        ]
    ),

    # GRUPA B: Velocity Indicators
    NodeDefinition(
        id="velocity",
        name="Price Velocity",
        type=NodeType.INDICATOR,
        category="Velocity Indicators",
        description="Price velocity between current and baseline windows",
        ports=[
            PortDefinition("price", DataType.PRICE, PortDirection.INPUT, required=True),
            PortDefinition("velocity", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("current_window", "dict", default={"t1": 60.0, "t2": 0.0}, required=False,
                              description="Current time window parameters"),
            ParameterDefinition("baseline_window", "dict", default={"t1": 300.0, "t2": 0.0}, required=False,
                              description="Baseline time window parameters"),
            ParameterDefinition("price_method", "str", default="LAST_PRICE", required=False,
                              validation_rules=["one_of: LAST_PRICE, TWPA, VTWPA, TW_MIDPRICE"],
                              description="Price calculation method")
        ]
    ),

    NodeDefinition(
        id="volume_surge",
        name="Volume Surge",
        type=NodeType.INDICATOR,
        category="Volume Indicators",
        description="Volume surge ratio between current and baseline windows",
        ports=[
            PortDefinition("volume", DataType.VOLUME, PortDirection.INPUT, required=True),
            PortDefinition("surge", DataType.INDICATOR_VALUE, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("current_window", "dict", default={"t1": 300.0, "t2": 0.0}, required=False,
                              description="Current time window parameters"),
            ParameterDefinition("baseline_window", "dict", default={"t1": 3600.0, "t2": 300.0}, required=False,
                              description="Baseline time window parameters")
        ]
    )
]

# Condition Nodes
CONDITION_NODES = [
    NodeDefinition(
        id="threshold_condition",
        name="Threshold Condition",
        type=NodeType.CONDITION,
        category="Basic Conditions",
        description="Compares indicator value against threshold",
        ports=[
            PortDefinition("input", DataType.INDICATOR_VALUE, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("operator", "str", default=">", required=True,
                              validation_rules=["one_of: >, <, >=, <=, =="]),
            ParameterDefinition("threshold", "float", required=True,
                              description="Comparison threshold value")
        ]
    ),
    NodeDefinition(
        id="duration_condition",
        name="Duration Condition",
        type=NodeType.CONDITION,
        category="Temporal Conditions",
        description="Condition that must hold for specified duration",
        ports=[
            PortDefinition("input", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("duration_seconds", "int", default=30, required=False, min_value=1,
                              description="Required duration in seconds"),
            ParameterDefinition("reset_on_false", "bool", default=True, required=False,
                              description="Reset timer when condition becomes false")
        ]
    ),
    NodeDefinition(
        id="sequence_condition",
        name="Sequence Condition",
        type=NodeType.CONDITION,
        category="Temporal Conditions",
        description="Requires specific sequence of conditions",
        ports=[
            PortDefinition("input", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("sequence_length", "int", default=3, required=False, min_value=2,
                              description="Number of consecutive true values required"),
            ParameterDefinition("max_gap_seconds", "int", default=10, required=False,
                              description="Maximum gap between sequence elements")
        ]
    )
]

# Composition Nodes
COMPOSITION_NODES = [
    NodeDefinition(
        id="and_composition",
        name="AND Composition",
        type=NodeType.COMPOSITION,
        category="Logic Operators",
        description="Logical AND of multiple conditions",
        ports=[
            PortDefinition("input1", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("input2", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("min_inputs", "int", default=2, required=False, min_value=2,
                              description="Minimum number of inputs required")
        ]
    ),
    NodeDefinition(
        id="or_composition",
        name="OR Composition",
        type=NodeType.COMPOSITION,
        category="Logic Operators",
        description="Logical OR of multiple conditions",
        ports=[
            PortDefinition("input1", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("input2", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[]
    ),
    NodeDefinition(
        id="weighted_composition",
        name="Weighted Composition",
        type=NodeType.COMPOSITION,
        category="Advanced Logic",
        description="Weighted combination of conditions",
        ports=[
            PortDefinition("input1", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("input2", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("result", DataType.BOOLEAN, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("weight1", "float", default=0.5, required=False, min_value=0.0, max_value=1.0),
            ParameterDefinition("weight2", "float", default=0.5, required=False, min_value=0.0, max_value=1.0),
            ParameterDefinition("threshold", "float", default=0.6, required=False, min_value=0.0, max_value=1.0)
        ]
    )
]

# Action Nodes
ACTION_NODES = [
    NodeDefinition(
        id="buy_signal",
        name="Buy Signal",
        type=NodeType.ACTION,
        category="Trading Actions",
        description="Generates buy trading signal",
        ports=[
            PortDefinition("trigger", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("signal", DataType.SIGNAL, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("position_size", "float", default=100.0, required=False, min_value=1.0,
                              description="Position size in base currency"),
            ParameterDefinition("max_slippage", "float", default=0.001, required=False, min_value=0.0, max_value=0.1,
                              description="Maximum allowed slippage")
        ]
    ),
    NodeDefinition(
        id="sell_signal",
        name="Sell Signal",
        type=NodeType.ACTION,
        category="Trading Actions",
        description="Generates sell trading signal",
        ports=[
            PortDefinition("trigger", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("signal", DataType.SIGNAL, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("position_size", "float", default=100.0, required=False, min_value=1.0),
            ParameterDefinition("take_profit_pct", "float", default=0.02, required=False, min_value=0.0)
        ]
    ),
    NodeDefinition(
        id="alert_action",
        name="Alert Action",
        type=NodeType.ACTION,
        category="Notification Actions",
        description="Sends alert notification",
        ports=[
            PortDefinition("trigger", DataType.BOOLEAN, PortDirection.INPUT, required=True)
        ],
        parameters=[
            ParameterDefinition("message", "str", default="Strategy condition met", required=False,
                              description="Alert message"),
            ParameterDefinition("priority", "str", default="medium", required=False,
                              validation_rules=["one_of: low, medium, high, critical"])
        ]
    ),
    NodeDefinition(
        id="emergency_exit",
        name="Emergency Exit",
        type=NodeType.ACTION,
        category="Risk Management",
        description="Emergency position exit",
        ports=[
            PortDefinition("trigger", DataType.BOOLEAN, PortDirection.INPUT, required=True),
            PortDefinition("signal", DataType.SIGNAL, PortDirection.OUTPUT)
        ],
        parameters=[
            ParameterDefinition("reason", "str", default="Emergency condition", required=False,
                              description="Exit reason for logging")
        ]
    )
]

# Complete node catalog
ALL_NODES = DATA_SOURCE_NODES + INDICATOR_NODES + CONDITION_NODES + COMPOSITION_NODES + ACTION_NODES


def get_node_definition(node_id: str) -> Optional[NodeDefinition]:
    """Get node definition by ID."""
    for node in ALL_NODES:
        if node.id == node_id:
            return node
    return None


def get_nodes_by_type(node_type: NodeType) -> List[NodeDefinition]:
    """Get all nodes of a specific type."""
    return [node for node in ALL_NODES if node.type == node_type]


def get_nodes_by_category(category: str) -> List[NodeDefinition]:
    """Get all nodes in a specific category."""
    return [node for node in ALL_NODES if node.category == category]


def validate_node_parameters(node_id: str, parameters: Dict[str, Any]) -> List[str]:
    """Validate parameters against node definition."""
    node = get_node_definition(node_id)
    if not node:
        return [f"Unknown node type: {node_id}"]

    errors = []

    # Check required parameters
    for param_def in node.get_required_parameters():
        if param_def.name not in parameters:
            errors.append(f"Missing required parameter: {param_def.name}")

    # Validate parameter values
    for param_name, param_value in parameters.items():
        param_def = next((p for p in node.parameters if p.name == param_name), None)
        if not param_def:
            errors.append(f"Unknown parameter: {param_name}")
            continue

        # Type validation (basic)
        if param_def.type == "int" and not isinstance(param_value, int):
            errors.append(f"Parameter {param_name} must be integer")
        elif param_def.type == "float" and not isinstance(param_value, (int, float)):
            errors.append(f"Parameter {param_name} must be numeric")
        elif param_def.type == "str" and not isinstance(param_value, str):
            errors.append(f"Parameter {param_name} must be string")
        elif param_def.type == "bool" and not isinstance(param_value, bool):
            errors.append(f"Parameter {param_name} must be boolean")

        # Range validation
        if param_def.min_value is not None and param_value < param_def.min_value:
            errors.append(f"Parameter {param_name} must be >= {param_def.min_value}")
        if param_def.max_value is not None and param_value > param_def.max_value:
            errors.append(f"Parameter {param_name} must be <= {param_def.max_value}")

        # Custom validation rules
        for rule in param_def.validation_rules:
            if rule.startswith("one_of:"):
                allowed_values = [v.strip() for v in rule[7:].split(",")]
                if str(param_value) not in allowed_values:
                    errors.append(f"Parameter {param_name} must be one of: {allowed_values}")

    return errors