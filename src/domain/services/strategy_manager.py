"""
Strategy Manager - 5-Group Condition Architecture
===============================================
Implements the complete strategy system with 5 groups of conditions:
1. Signal Detection Conditions
2. Risk Assessment Conditions
3. Entry Conditions
4. Position Sizing Rules
5. Emergency Exit Conditions
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from .order_manager import OrderManager, OrderType
from .risk_manager import RiskManager, RiskMetrics


class StrategyState(Enum):
    """Strategy execution states - 5-section workflow per user_feedback.md"""
    INACTIVE = "inactive"
    MONITORING = "monitoring"
    SIGNAL_DETECTED = "signal_detected"  # S1 detected
    SIGNAL_CANCELLED = "signal_cancelled"  # O1 triggered
    ENTRY_EVALUATION = "entry_evaluation"  # Z1 evaluation
    POSITION_ACTIVE = "position_active"  # Position opened
    CLOSE_ORDER_EVALUATION = "close_order_evaluation"  # ZE1 evaluation
    EMERGENCY_EXIT = "emergency_exit"  # E1 triggered
    EXITED = "exited"  # Position closed


class ConditionResult(Enum):
    """Result of condition evaluation"""
    TRUE = "true"
    FALSE = "false"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class Condition:
    """Represents a single condition in a strategy"""
    name: str
    condition_type: str  # e.g., "pump_magnitude_pct", "volume_surge_ratio"
    operator: str  # e.g., "gte", "lte", "eq", "between"
    value: Any
    enabled: bool = True
    description: str = ""

    def evaluate(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate this condition against current indicator values"""
        if not self.enabled:
            return ConditionResult.PENDING

        if self.condition_type not in indicator_values:
            return ConditionResult.PENDING

        actual_value = indicator_values[self.condition_type]

        try:
            if self.operator == "gte":
                return ConditionResult.TRUE if actual_value >= self.value else ConditionResult.FALSE
            elif self.operator == "lte":
                return ConditionResult.TRUE if actual_value <= self.value else ConditionResult.FALSE
            elif self.operator == "gt":
                return ConditionResult.TRUE if actual_value > self.value else ConditionResult.FALSE
            elif self.operator == "lt":
                return ConditionResult.TRUE if actual_value < self.value else ConditionResult.FALSE
            elif self.operator == "eq":
                return ConditionResult.TRUE if actual_value == self.value else ConditionResult.FALSE
            elif self.operator == "between":
                min_val, max_val = self.value
                return ConditionResult.TRUE if min_val <= actual_value <= max_val else ConditionResult.FALSE
            elif self.operator == "allowed":
                return ConditionResult.TRUE if actual_value in self.value else ConditionResult.FALSE
            else:
                return ConditionResult.ERROR

        except Exception:
            return ConditionResult.ERROR


@dataclass
class ConditionGroup:
    """A group of conditions that must all be true"""
    name: str
    conditions: List[Condition] = field(default_factory=list)
    require_all: bool = True  # If True, all conditions must be true; if False, any condition can be true

    def evaluate(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate all conditions in this group"""
        if not self.conditions:
            return ConditionResult.TRUE

        results = []
        for condition in self.conditions:
            result = condition.evaluate(indicator_values)
            if result == ConditionResult.ERROR:
                return ConditionResult.ERROR
            results.append(result)

        if self.require_all:
            # All conditions must be TRUE
            return ConditionResult.TRUE if all(r == ConditionResult.TRUE for r in results) else ConditionResult.FALSE
        else:
            # Any condition can be TRUE
            return ConditionResult.TRUE if any(r == ConditionResult.TRUE for r in results) else ConditionResult.FALSE


@dataclass
class Strategy:
    """Complete strategy with 5 condition groups"""
    strategy_name: str
    enabled: bool = True

    # 5 Groups of Conditions (user_feedback.md specification)
    signal_detection: ConditionGroup = field(default_factory=lambda: ConditionGroup("signal_detection"))  # S1
    signal_cancellation: ConditionGroup = field(default_factory=lambda: ConditionGroup("signal_cancellation"))  # O1
    entry_conditions: ConditionGroup = field(default_factory=lambda: ConditionGroup("entry_conditions"))  # Z1
    close_order_detection: ConditionGroup = field(default_factory=lambda: ConditionGroup("close_order_detection"))  # ZE1
    emergency_exit: ConditionGroup = field(default_factory=lambda: ConditionGroup("emergency_exit"))  # E1

    # Global limits
    global_limits: Dict[str, Any] = field(default_factory=dict)

    # State tracking
    current_state: StrategyState = StrategyState.INACTIVE
    symbol: str = ""
    position_active: bool = False
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None

    # Cooldown tracking (per user_feedback.md)
    cooldown_until: Optional[datetime] = None  # When cooldown expires
    last_signal_cancelled: Optional[datetime] = None  # O1 cooldown
    last_emergency_exit: Optional[datetime] = None  # E1 cooldown

    def evaluate_signal_detection(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate signal detection conditions"""
        return self.signal_detection.evaluate(indicator_values)

    def evaluate_risk_assessment(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate risk assessment conditions"""
        return self.risk_assessment.evaluate(indicator_values)

    def evaluate_entry_conditions(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate entry conditions"""
        return self.entry_conditions.evaluate(indicator_values)

    def evaluate_signal_cancellation(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate signal cancellation conditions (O1)"""
        return self.signal_cancellation.evaluate(indicator_values)

    def evaluate_close_order_detection(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate close order detection conditions (ZE1)"""
        return self.close_order_detection.evaluate(indicator_values)

    def evaluate_emergency_exit(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate emergency exit conditions"""
        return self.emergency_exit.evaluate(indicator_values)

    def is_in_cooldown(self) -> bool:
        """Check if strategy is currently in cooldown period"""
        if self.cooldown_until is None:
            return False
        return datetime.now() < self.cooldown_until

    def start_cooldown(self, cooldown_minutes: int, reason: str = "general") -> None:
        """Start a cooldown period for the strategy"""
        self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)

        # Track cooldown reason
        if reason == "signal_cancelled":
            self.last_signal_cancelled = datetime.now()
        elif reason == "emergency_exit":
            self.last_emergency_exit = datetime.now()

    def get_cooldown_status(self) -> Dict[str, Any]:
        """Get current cooldown status"""
        now = datetime.now()
        return {
            "in_cooldown": self.is_in_cooldown(),
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "remaining_seconds": max(0, int((self.cooldown_until - now).total_seconds())) if self.cooldown_until and self.cooldown_until > now else 0,
            "last_signal_cancelled": self.last_signal_cancelled.isoformat() if self.last_signal_cancelled else None,
            "last_emergency_exit": self.last_emergency_exit.isoformat() if self.last_emergency_exit else None
        }

    def _record_decision_indicators(self, indicator_values: Dict[str, Any], decision_point: str) -> Dict[str, Any]:
        """Record indicator values at decision points per user_feedback.md requirement"""
        # Define which indicators to record at each decision point
        recording_config = {
            "S1_signal_detection": ["pump_magnitude_pct", "volume_surge_ratio", "price_momentum"],
            "O1_signal_cancellation": ["pump_magnitude_pct"],
            "Z1_entry_conditions": ["rsi", "spread_pct", "price_momentum"],
            "ZE1_close_order_detection": ["unrealized_pnl_pct", "price_momentum", "pump_magnitude_pct"],
            "E1_emergency_exit": ["pump_magnitude_pct", "volume_surge_ratio"]
        }

        indicators_to_record = recording_config.get(decision_point, [])
        recorded_values = {}

        for indicator_name in indicators_to_record:
            if indicator_name in indicator_values:
                recorded_values[indicator_name] = indicator_values[indicator_name]

        # Add timestamp and decision point
        recorded_values["_timestamp"] = datetime.now().isoformat()
        recorded_values["_decision_point"] = decision_point

        return recorded_values

    def calculate_position_size(self, indicator_values: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate position sizing with risk-adjusted pricing per user_feedback.md"""
        # Base position sizing
        base_size = self.global_limits.get("base_position_pct", 0.5)

        # Risk-adjusted sizing for Z1 (entry orders)
        risk_adjusted_size = self._calculate_risk_adjusted_position_size(indicator_values, base_size)

        # Apply limits
        max_size = self.global_limits.get("max_position_size_usdt", 1000)
        min_size = self.global_limits.get("min_position_size_usdt", 10)

        final_position_size = max(min_size, min(max_size, risk_adjusted_size))

        return {
            "position_size_pct": final_position_size,
            "risk_adjusted_multiplier": risk_adjusted_size / base_size if base_size > 0 else 1.0,
            "max_leverage": self.global_limits.get("max_leverage", 2.0),
            "stop_loss_pct": self.global_limits.get("stop_loss_buffer_pct", 10.0),
            "take_profit_pct": self.global_limits.get("target_profit_pct", 25.0)
        }

    def _calculate_risk_adjusted_position_size(self, indicator_values: Dict[str, Any], base_size: float) -> float:
        """Calculate risk-adjusted position size per user_feedback.md specification"""
        # Get risk indicator value (default to moderate risk if not available)
        risk_value = indicator_values.get("risk_indicator", 50.0)  # Assume 0-100 scale

        # Define risk adjustment points (configurable via strategy limits)
        risk_points = self.global_limits.get("risk_adjustment_points", [
            {"risk_value": 20, "position_size_multiplier": 1.2},  # Low risk = larger position
            {"risk_value": 70, "position_size_multiplier": 0.55}  # High risk = smaller position
        ])

        # Linear interpolation between risk points
        if risk_value <= risk_points[0]["risk_value"]:
            # Below minimum risk point - use minimum multiplier
            multiplier = risk_points[0]["position_size_multiplier"]
        elif risk_value >= risk_points[-1]["risk_value"]:
            # Above maximum risk point - use maximum multiplier
            multiplier = risk_points[-1]["position_size_multiplier"]
        else:
            # Interpolate between points
            for i in range(len(risk_points) - 1):
                if risk_points[i]["risk_value"] <= risk_value <= risk_points[i + 1]["risk_value"]:
                    # Linear interpolation
                    risk_range = risk_points[i + 1]["risk_value"] - risk_points[i]["risk_value"]
                    multiplier_range = risk_points[i + 1]["position_size_multiplier"] - risk_points[i]["position_size_multiplier"]

                    if risk_range > 0:
                        ratio = (risk_value - risk_points[i]["risk_value"]) / risk_range
                        multiplier = risk_points[i]["position_size_multiplier"] + (ratio * multiplier_range)
                    else:
                        multiplier = risk_points[i]["position_size_multiplier"]
                    break
            else:
                multiplier = 1.0  # Fallback

        return base_size * multiplier

    def calculate_close_price_adjustment(self, indicator_values: Dict[str, Any], base_close_price: float) -> Dict[str, Any]:
        """Calculate risk-adjusted close price per user_feedback.md ZE1 specification"""
        # Get risk indicator value
        risk_value = indicator_values.get("risk_indicator", 50.0)

        # Define close price adjustment points (similar to position sizing)
        adjustment_points = self.global_limits.get("close_price_adjustment_points", [
            {"risk_value": 30, "price_adjustment_pct": 10.0},  # Low risk = better price (higher for longs)
            {"risk_value": 120, "price_adjustment_pct": -5.0}   # High risk = worse price (lower for longs)
        ])

        # Linear interpolation between adjustment points
        if risk_value <= adjustment_points[0]["risk_value"]:
            adjustment_pct = adjustment_points[0]["price_adjustment_pct"]
        elif risk_value >= adjustment_points[-1]["risk_value"]:
            adjustment_pct = adjustment_points[-1]["price_adjustment_pct"]
        else:
            for i in range(len(adjustment_points) - 1):
                if adjustment_points[i]["risk_value"] <= risk_value <= adjustment_points[i + 1]["risk_value"]:
                    risk_range = adjustment_points[i + 1]["risk_value"] - adjustment_points[i]["risk_value"]
                    adj_range = adjustment_points[i + 1]["price_adjustment_pct"] - adjustment_points[i]["price_adjustment_pct"]

                    if risk_range > 0:
                        ratio = (risk_value - adjustment_points[i]["risk_value"]) / risk_range
                        adjustment_pct = adjustment_points[i]["price_adjustment_pct"] + (ratio * adj_range)
                    else:
                        adjustment_pct = adjustment_points[i]["price_adjustment_pct"]
                    break
            else:
                adjustment_pct = 0.0  # No adjustment

        # Apply adjustment to base close price
        adjusted_price = base_close_price * (1 + adjustment_pct / 100)

        return {
            "adjusted_close_price": adjusted_price,
            "price_adjustment_pct": adjustment_pct,
            "risk_based_adjustment": True
        }


class StrategyManager:
    """
    Manages multiple strategies with 5-group condition architecture.
    Handles strategy lifecycle, condition evaluation, and state transitions.
    """

    def __init__(self,
                 event_bus: EventBus,
                 logger: StructuredLogger,
                 order_manager: Optional[OrderManager] = None,
                 risk_manager: Optional[RiskManager] = None):
        self.event_bus = event_bus
        self.logger = logger
        self.order_manager = order_manager
        self.risk_manager = risk_manager

        # Strategy storage
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategies: Dict[str, List[Strategy]] = {}  # symbol -> strategies

        # Indicator values cache
        self.indicator_values: Dict[str, Dict[str, Any]] = {}  # symbol -> indicators

        # Telemetry: last events and active symbols per strategy
        self._strategy_telemetry: Dict[str, Dict[str, Any]] = {}

        # Subscribe to indicator updates with timeout protection
        import asyncio
        asyncio.create_task(self.event_bus.subscribe("indicator.updated", self._on_indicator_update))

        # Enhanced circuit breaker for event loops
        self._evaluation_in_progress = set()  # Track symbols being evaluated
        self._max_evaluations_per_second = 50  # Reduced rate limit
        self._last_evaluation_reset = datetime.now()
        self._evaluation_count = 0
        self._event_loop_detector = {}  # Track event patterns

        # Slot management for concurrent signals (Phase 3 requirement)
        self._global_signal_slots = {}  # strategy_name -> active_signals_count
        self._max_concurrent_signals = 3  # Configurable global limit
        self._symbol_locks = {}  # symbol -> locking_strategy_name

        # Load default strategies
        self._load_default_strategies()

        self.logger.info("strategy_manager.initialized", {
            "order_manager_enabled": order_manager is not None
        })

    def validate_dependencies(self) -> None:
        """Validate that all required dependencies are properly set"""
        if self.order_manager is None:
            raise RuntimeError("StrategyManager dependency validation failed: order_manager not set")
        if self.risk_manager is None:
            raise RuntimeError("StrategyManager dependency validation failed: risk_manager not set")

    def can_acquire_signal_slot(self, strategy_name: str) -> bool:
        """Check if strategy can acquire a signal slot (Phase 3 requirement)"""
        current_slots = self._global_signal_slots.get(strategy_name, 0)
        total_active_signals = sum(self._global_signal_slots.values())

        # Check global limit
        if total_active_signals >= self._max_concurrent_signals:
            return False

        # Allow strategy to have multiple signals if within global limit
        return current_slots < self._max_concurrent_signals

    def acquire_signal_slot(self, strategy_name: str) -> bool:
        """Acquire a signal slot for the strategy"""
        if not self.can_acquire_signal_slot(strategy_name):
            return False

        self._global_signal_slots[strategy_name] = self._global_signal_slots.get(strategy_name, 0) + 1
        return True

    def release_signal_slot(self, strategy_name: str) -> None:
        """Release a signal slot for the strategy"""
        if strategy_name in self._global_signal_slots:
            self._global_signal_slots[strategy_name] = max(0, self._global_signal_slots[strategy_name] - 1)
            if self._global_signal_slots[strategy_name] == 0:
                del self._global_signal_slots[strategy_name]

    def can_lock_symbol(self, symbol: str, strategy_name: str) -> bool:
        """Check if strategy can lock a symbol (Phase 3 requirement)"""
        # Symbol is already locked by another strategy
        if symbol in self._symbol_locks and self._symbol_locks[symbol] != strategy_name:
            return False

        return True

    def lock_symbol(self, symbol: str, strategy_name: str) -> bool:
        """Lock symbol for exclusive use by strategy"""
        if not self.can_lock_symbol(symbol, strategy_name):
            return False

        self._symbol_locks[symbol] = strategy_name
        return True

    def unlock_symbol(self, symbol: str, strategy_name: str) -> None:
        """Unlock symbol if locked by this strategy"""
        if self._symbol_locks.get(symbol) == strategy_name:
            del self._symbol_locks[symbol]

    def get_slot_status(self) -> Dict[str, Any]:
        """Get current slot management status"""
        return {
            "max_concurrent_signals": self._max_concurrent_signals,
            "total_active_signals": sum(self._global_signal_slots.values()),
            "strategy_slots": dict(self._global_signal_slots),
            "available_slots": max(0, self._max_concurrent_signals - sum(self._global_signal_slots.values())),
            "symbol_locks": dict(self._symbol_locks)
        }

    def _load_default_strategies(self) -> None:
        """Load default strategies from configuration files"""
        # ✅ CRITICAL FIX: Create comprehensive pump/dump detection strategy
        try:
            # Create advanced pump_dump_detection strategy
            pump_strategy = Strategy(
                strategy_name="pump_dump_detection",
                enabled=True,
                global_limits={
                    "base_position_pct": 0.3,  # More conservative position sizing
                    "max_position_size_usdt": 500,  # Smaller max position
                    "min_position_size_usdt": 20,
                    "max_leverage": 1.5,  # Lower leverage for safety
                    "stop_loss_buffer_pct": 15.0,  # Wider stop loss
                    "target_profit_pct": 20.0,  # Realistic profit target
                    "max_allocation_pct": 5.0,  # Max 5% of portfolio
                    # Risk-adjusted sizing points per user_feedback.md
                    "risk_adjustment_points": [
                        {"risk_value": 20, "position_size_multiplier": 1.2},  # Low risk = larger position
                        {"risk_value": 70, "position_size_multiplier": 0.55}  # High risk = smaller position
                    ],
                    # Close price adjustment points per user_feedback.md
                    "close_price_adjustment_points": [
                        {"risk_value": 30, "price_adjustment_pct": 10.0},  # Low risk = better price
                        {"risk_value": 120, "price_adjustment_pct": -5.0}   # High risk = worse price
                    ],
                    # Cooldown settings per user_feedback.md
                    "signal_cancellation_cooldown_minutes": 5,
                    "emergency_exit_cooldown_minutes": 30
                }
            )

            # S1 Signal Detection - Multiple conditions for robust pump detection
            pump_strategy.signal_detection.conditions.extend([
                Condition(
                    name="pump_magnitude_pct",
                    condition_type="pump_magnitude_pct",
                    operator="gte",
                    value=8.0,  # Higher threshold for significant pumps
                    description="Minimum pump magnitude for detection"
                ),
                Condition(
                    name="volume_surge_ratio",
                    condition_type="volume_surge_ratio",
                    operator="gte",
                    value=3.0,  # 3x volume surge indicates manipulation
                    description="Volume surge ratio threshold"
                ),
                Condition(
                    name="price_momentum",
                    condition_type="price_momentum",
                    operator="gte",
                    value=5.0,  # Positive momentum confirmation
                    description="Price momentum threshold"
                )
            ])

            # O1 Signal Cancellation - Conditions to cancel signal (optional timeout)
            pump_strategy.signal_cancellation.conditions.extend([
                Condition(
                    name="pump_magnitude_pct_drop",
                    condition_type="pump_magnitude_pct",
                    operator="lte",
                    value=-2.0,  # Signal cancelled if pump reverses
                    description="Cancel signal on pump reversal"
                )
            ])

            # Z1 Entry Conditions - Precise timing for order placement
            pump_strategy.entry_conditions.conditions.extend([
                Condition(
                    name="rsi",
                    condition_type="rsi",
                    operator="between",
                    value=(40, 80),  # Avoid overbought conditions
                    description="RSI range for entry"
                ),
                Condition(
                    name="spread_pct",
                    condition_type="spread_pct",
                    operator="lte",
                    value=1.0,  # Tight spread for better execution
                    description="Maximum spread percentage"
                )
            ])

            # ZE1 Close Order Detection - Profit-taking conditions
            pump_strategy.close_order_detection.conditions.extend([
                Condition(
                    name="profit_target_pct",
                    condition_type="unrealized_pnl_pct",
                    operator="gte",
                    value=15.0,  # Take profit at 15% gain
                    description="Profit target for order closing"
                ),
                Condition(
                    name="pump_momentum_fade",
                    condition_type="price_momentum",
                    operator="lte",
                    value=1.0,  # Close when momentum fades
                    description="Close order when pump momentum fades"
                )
            ])

            # E1 Emergency Exit - Fast exit on dump signals
            pump_strategy.emergency_exit.conditions.extend([
                Condition(
                    name="pump_dump_signal",
                    condition_type="pump_magnitude_pct",
                    operator="lte",
                    value=-5.0,  # Significant price drop triggers emergency
                    description="Emergency exit on price dump"
                ),
                Condition(
                    name="extreme_volume_surge",
                    condition_type="volume_surge_ratio",
                    operator="gte",
                    value=5.0,  # Extreme volume may indicate panic selling
                    description="Emergency exit on extreme volume surge"
                )
            ])

            self.add_strategy(pump_strategy)

            # Create a simpler flash pump strategy for quick detection
            flash_strategy = Strategy(
                strategy_name="flash_pump_detection",
                enabled=True,
                global_limits={
                    "base_position_pct": 0.2,
                    "max_position_size_usdt": 300,
                    "min_position_size_usdt": 10,
                    "max_leverage": 1.2,
                    "stop_loss_buffer_pct": 12.0,
                    "target_profit_pct": 15.0,
                    "max_allocation_pct": 3.0,
                    # Risk-adjusted sizing for flash strategy
                    "risk_adjustment_points": [
                        {"risk_value": 25, "position_size_multiplier": 1.1},  # Low risk = slightly larger
                        {"risk_value": 60, "position_size_multiplier": 0.7}   # High risk = smaller position
                    ],
                    # Close price adjustment for flash strategy
                    "close_price_adjustment_points": [
                        {"risk_value": 35, "price_adjustment_pct": 5.0},   # Low risk = better price
                        {"risk_value": 100, "price_adjustment_pct": -8.0}  # High risk = worse price
                    ],
                    # Cooldown settings for flash strategy
                    "signal_cancellation_cooldown_minutes": 3,  # Shorter cooldown
                    "emergency_exit_cooldown_minutes": 15       # Shorter emergency cooldown
                }
            )

            # S1 Signal Detection - Quick pump detection
            flash_strategy.signal_detection.conditions.append(
                Condition(
                    name="pump_magnitude_pct",
                    condition_type="pump_magnitude_pct",
                    operator="gte",
                    value=5.0,
                    description="Quick pump detection threshold"
                )
            )

            # O1 Signal Cancellation - Simple timeout-based cancellation
            flash_strategy.signal_cancellation.conditions.append(
                Condition(
                    name="signal_age_seconds",
                    condition_type="signal_age_seconds",
                    operator="gte",
                    value=300.0,  # Cancel after 5 minutes
                    description="Cancel signal after timeout"
                )
            )

            # Z1 Entry Conditions - Quick entry on momentum
            flash_strategy.entry_conditions.conditions.append(
                Condition(
                    name="price_momentum",
                    condition_type="price_momentum",
                    operator="gte",
                    value=3.0,
                    description="Minimum momentum for entry"
                )
            )

            # ZE1 Close Order Detection - Quick profit taking
            flash_strategy.close_order_detection.conditions.append(
                Condition(
                    name="quick_profit_target",
                    condition_type="unrealized_pnl_pct",
                    operator="gte",
                    value=8.0,  # Take profit at 8% gain
                    description="Quick profit target for flash strategy"
                )
            )

            # E1 Emergency Exit - Fast exit on reversal
            flash_strategy.emergency_exit.conditions.append(
                Condition(
                    name="pump_reversal",
                    condition_type="pump_magnitude_pct",
                    operator="lte",
                    value=-3.0,  # Exit on significant reversal
                    description="Emergency exit on pump reversal"
                )
            )

            self.add_strategy(flash_strategy)

            self.logger.info("strategy_manager.default_strategies_created", {
                "strategies": ["pump_dump_detection", "flash_pump_detection"]
            })

        except Exception as e:
            self.logger.error("strategy_manager.default_strategy_creation_error", {
                "error": str(e)
            })

    def create_strategy_from_config(self, config: Dict[str, Any]) -> Strategy:
        """Create a strategy from configuration dictionary"""
        strategy = Strategy(
            strategy_name=config.get("strategy_name", "unnamed_strategy"),
            enabled=config.get("enabled", True),
            global_limits=config.get("global_limits", {})
        )

        # Build S1 signal detection conditions
        if "signal_detection_conditions" in config:
            for key, condition_config in config["signal_detection_conditions"].items():
                if isinstance(condition_config, dict):
                    if "min" in condition_config and "max" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="between",
                            value=(condition_config["min"], condition_config["max"])
                        )
                    elif "min" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="gte",
                            value=condition_config["min"]
                        )
                    elif "allowed" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="allowed",
                            value=condition_config["allowed"]
                        )
                    strategy.signal_detection.conditions.append(condition)

        # Build O1 signal cancellation conditions
        if "signal_cancellation_conditions" in config:
            for key, condition_config in config["signal_cancellation_conditions"].items():
                if isinstance(condition_config, dict):
                    if "max" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="lte",
                            value=condition_config["max"]
                        )
                    elif "min" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="gte",
                            value=condition_config["min"]
                        )
                    strategy.signal_cancellation.conditions.append(condition)

        # Build Z1 entry conditions
        if "entry_conditions" in config:
            for key, condition_config in config["entry_conditions"].items():
                if isinstance(condition_config, dict):
                    if "min" in condition_config and "max" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="between",
                            value=(condition_config["min"], condition_config["max"])
                        )
                    elif "max" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="lte",
                            value=condition_config["max"]
                        )
                    strategy.entry_conditions.conditions.append(condition)

        # Build ZE1 close order detection conditions
        if "close_order_detection_conditions" in config:
            for key, condition_config in config["close_order_detection_conditions"].items():
                if isinstance(condition_config, dict):
                    if "min" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="gte",
                            value=condition_config["min"]
                        )
                    elif "max" in condition_config:
                        condition = Condition(
                            name=key,
                            condition_type=key,
                            operator="lte",
                            value=condition_config["max"]
                        )
                    strategy.close_order_detection.conditions.append(condition)

        # Build E1 emergency exit conditions
        if "emergency_exit_conditions" in config:
            for key, condition_config in config["emergency_exit_conditions"].items():
                condition = Condition(
                    name=key,
                    condition_type=key,
                    operator="gte" if isinstance(condition_config, (int, float)) else "eq",
                    value=condition_config
                )
                strategy.emergency_exit.conditions.append(condition)

        return strategy

    def add_strategy(self, strategy: Strategy) -> None:
        """Add a strategy to the manager"""
        self.strategies[strategy.strategy_name] = strategy
        if strategy.strategy_name not in self._strategy_telemetry:
            self._strategy_telemetry[strategy.strategy_name] = {
                "last_event": None,
                "last_state_change": None,
                "active_symbols": set(),
            }
        self.logger.info("strategy_manager.strategy_added", {
            "strategy_name": strategy.strategy_name
        })

    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove strategy from registry and deactivate from all symbols"""
        # Deactivate across all symbols
        try:
            for symbol, strategies in list(self.active_strategies.items()):
                self.active_strategies[symbol] = [s for s in strategies if s.strategy_name != strategy_name]
        except Exception as e:
            self.logger.warning("strategy_manager.strategy_deactivation_error", {
                "strategy_name": strategy_name,
                "error": str(e)
            })
        removed = False
        if strategy_name in self.strategies:
            try:
                self.strategies.pop(strategy_name, None)
                removed = True
            except Exception:
                removed = False
        if removed:
            self.logger.info("strategy_manager.strategy_removed", {"strategy_name": strategy_name})
        return removed

    def activate_strategy_for_symbol(self, strategy_name: str, symbol: str) -> bool:
        """Activate a strategy for a specific symbol"""
        if strategy_name not in self.strategies:
            return False

        strategy = self.strategies[strategy_name]
        strategy.symbol = symbol
        strategy.current_state = StrategyState.MONITORING

        if symbol not in self.active_strategies:
            self.active_strategies[symbol] = []

        if strategy not in self.active_strategies[symbol]:
            self.active_strategies[symbol].append(strategy)

        # Telemetry update
        try:
            tel = self._strategy_telemetry.setdefault(strategy_name, {"last_event": None, "last_state_change": None, "active_symbols": set()})
            tel["active_symbols"].add(symbol)
            tel["last_event"] = {"event_type": "strategy_activated", "timestamp": datetime.now().isoformat()}
            tel["last_state_change"] = datetime.now().isoformat()
        except Exception as e:
            self.logger.warning("strategy_manager.telemetry_update_error", {
                "strategy_name": strategy_name,
                "symbol": symbol,
                "error": str(e)
            })

        self.logger.info("strategy_manager.strategy_activated", {
            "strategy_name": strategy_name,
            "symbol": symbol
        })

        return True

    def deactivate_strategy_for_symbol(self, strategy_name: str, symbol: str) -> bool:
        """Deactivate a strategy for a specific symbol"""
        if symbol not in self.active_strategies:
            return False

        self.active_strategies[symbol] = [
            s for s in self.active_strategies[symbol]
            if s.strategy_name != strategy_name
        ]

        if strategy_name in self.strategies:
            self.strategies[strategy_name].current_state = StrategyState.INACTIVE

        self.logger.info("strategy_manager.strategy_deactivated", {
            "strategy_name": strategy_name,
            "symbol": symbol
        })

        # Telemetry update
        try:
            tel = self._strategy_telemetry.setdefault(strategy_name, {"last_event": None, "last_state_change": None, "active_symbols": set()})
            if symbol in tel["active_symbols"]:
                tel["active_symbols"].remove(symbol)
            tel["last_event"] = {"event_type": "strategy_deactivated", "timestamp": datetime.now().isoformat()}
            tel["last_state_change"] = datetime.now().isoformat()
        except Exception as e:
            self.logger.warning("strategy_manager.telemetry_update_error", {
                "strategy_name": strategy_name,
                "symbol": symbol,
                "error": str(e)
            })

        return True

    async def _on_indicator_update(self, data: Dict[str, Any]) -> None:
        """Handle indicator update events with enhanced circuit breaker"""
        symbol = data.get("symbol")
        indicator_name = data.get("indicator")
        value = data.get("value")

        if not symbol or not indicator_name:
            return

        # Enhanced rate limiting with exponential backoff
        now = datetime.now()
        if (now - self._last_evaluation_reset).total_seconds() > 1.0:
            self._evaluation_count = 0
            self._last_evaluation_reset = now
        
        if self._evaluation_count >= self._max_evaluations_per_second:
            self.logger.debug("strategy_manager.rate_limit_exceeded", {
                "symbol": symbol,
                "count": self._evaluation_count
            })
            return
        
        self._evaluation_count += 1

        # Enhanced circuit breaker - prevent cascading evaluations
        if symbol in self._evaluation_in_progress:
            return

        # Prevent event loops by checking if this is a strategy-generated event
        event_source = data.get("source", "external")
        if event_source == "strategy_manager":
            return  # Skip self-generated events to prevent loops

        # Update indicator cache (non-blocking)
        if symbol not in self.indicator_values:
            self.indicator_values[symbol] = {}
        self.indicator_values[symbol][indicator_name] = value

        # Async evaluation with enhanced error handling
        try:
            self._evaluation_in_progress.add(symbol)
            await asyncio.wait_for(
                self._evaluate_strategies_for_symbol(symbol),
                timeout=0.8  # Reduced timeout to prevent blocking
            )
        except asyncio.TimeoutError:
            self.logger.warning("strategy_manager.evaluation_timeout", {
                "symbol": symbol,
                "indicator": indicator_name
            })
        except Exception as e:
            self.logger.error("strategy_manager.evaluation_error", {
                "symbol": symbol,
                "error": str(e)
            })
        finally:
            self._evaluation_in_progress.discard(symbol)

    async def _evaluate_strategies_for_symbol(self, symbol: str) -> None:
        """Evaluate all active strategies for a symbol with timeout protection"""
        if symbol not in self.active_strategies:
            return

        indicator_values = self.indicator_values.get(symbol, {})
        
        # ✅ CRITICAL FIX: Limit number of strategies evaluated per call
        strategies_to_evaluate = [s for s in self.active_strategies[symbol] if s.enabled][:5]  # Max 5 strategies

        for strategy in strategies_to_evaluate:
            try:
                # ✅ CRITICAL FIX: Timeout for individual strategy evaluation
                await asyncio.wait_for(
                    self._evaluate_strategy(strategy, indicator_values),
                    timeout=0.5  # 500ms timeout per strategy
                )
            except asyncio.TimeoutError:
                self.logger.warning("strategy_manager.strategy_evaluation_timeout", {
                    "strategy_name": strategy.strategy_name,
                    "symbol": symbol
                })
            except Exception as e:
                self.logger.error("strategy_manager.strategy_evaluation_error", {
                    "strategy_name": strategy.strategy_name,
                    "symbol": symbol,
                    "error": str(e)
                })

    async def _evaluate_strategy(self, strategy: Strategy, indicator_values: Dict[str, Any]) -> None:
        """Evaluate a single strategy against current conditions - 5-section workflow per user_feedback.md"""
        try:
            # Check cooldown first - strategy cannot operate while in cooldown
            if strategy.is_in_cooldown():
                cooldown_status = strategy.get_cooldown_status()
                await self._publish_strategy_event(strategy, "cooldown_active", {
                    **indicator_values,
                    **cooldown_status
                })
                return

            if strategy.current_state == StrategyState.MONITORING:
                # S1: Check signal detection
                signal_result = strategy.evaluate_signal_detection(indicator_values)
                if signal_result == ConditionResult.TRUE:
                    # Phase 3: Check slot availability before proceeding
                    if not self.can_acquire_signal_slot(strategy.strategy_name):
                        await self._publish_strategy_event(strategy, "signal_slot_unavailable", {
                            **indicator_values,
                            "slot_status": self.get_slot_status()
                        })
                        return

                    # Phase 3: Check symbol lock availability
                    if not self.can_lock_symbol(strategy.symbol, strategy.strategy_name):
                        locking_strategy = self._symbol_locks.get(strategy.symbol)
                        await self._publish_strategy_event(strategy, "symbol_locked", {
                            **indicator_values,
                            "locking_strategy": locking_strategy
                        })
                        return

                    # Acquire slot and lock symbol
                    if not self.acquire_signal_slot(strategy.strategy_name):
                        await self._publish_strategy_event(strategy, "signal_slot_acquisition_failed", indicator_values)
                        return

                    if not self.lock_symbol(strategy.symbol, strategy.strategy_name):
                        self.release_signal_slot(strategy.strategy_name)  # Rollback slot
                        await self._publish_strategy_event(strategy, "symbol_lock_failed", indicator_values)
                        return

                    # Record indicator values at signal detection
                    signal_indicators = strategy._record_decision_indicators(indicator_values, "S1_signal_detection")
                    strategy.current_state = StrategyState.SIGNAL_DETECTED
                    await self._publish_strategy_event(strategy, "signal_detected", {
                        **indicator_values,
                        "recorded_indicators": signal_indicators,
                        "slot_acquired": True,
                        "symbol_locked": True
                    })

            elif strategy.current_state == StrategyState.SIGNAL_DETECTED:
                # O1: Check signal cancellation (optional)
                cancellation_result = strategy.evaluate_signal_cancellation(indicator_values)
                if cancellation_result == ConditionResult.TRUE:
                    # Phase 3: Release slot and symbol lock on cancellation
                    self.release_signal_slot(strategy.strategy_name)
                    self.unlock_symbol(strategy.symbol, strategy.strategy_name)

                    # Record indicator values at cancellation
                    cancel_indicators = strategy._record_decision_indicators(indicator_values, "O1_signal_cancellation")
                    strategy.current_state = StrategyState.SIGNAL_CANCELLED

                    # Start cooldown if configured
                    cooldown_minutes = strategy.global_limits.get("signal_cancellation_cooldown_minutes", 5)
                    strategy.start_cooldown(cooldown_minutes, "signal_cancelled")

                    await self._publish_strategy_event(strategy, "signal_cancelled", {
                        **indicator_values,
                        "recorded_indicators": cancel_indicators,
                        "cooldown_started": True,
                        "cooldown_minutes": cooldown_minutes,
                        "slot_released": True,
                        "symbol_unlocked": True
                    })
                    return

                # Z1: Check entry conditions
                entry_result = strategy.evaluate_entry_conditions(indicator_values)
                if entry_result == ConditionResult.TRUE:
                    # Record indicator values at entry decision
                    entry_indicators = strategy._record_decision_indicators(indicator_values, "Z1_entry_conditions")
                    strategy.current_state = StrategyState.ENTRY_EVALUATION
                    await self._publish_strategy_event(strategy, "entry_conditions_met", {
                        **indicator_values,
                        "recorded_indicators": entry_indicators
                    })
                elif entry_result == ConditionResult.FALSE:
                    # Continue monitoring for better entry timing
                    await self._publish_strategy_event(strategy, "entry_conditions_not_met", indicator_values)

            elif strategy.current_state == StrategyState.ENTRY_EVALUATION:
                # Calculate position sizing
                position_params = strategy.calculate_position_size(indicator_values)

                # Perform risk assessment if risk manager is available
                risk_approved = True
                risk_warnings = []

                if self.risk_manager:
                    try:
                        current_price = indicator_values.get("price", indicator_values.get("last_price", 100.0))
                        position_size_pct = position_params.get("position_size_pct", 0.01)
                        # Assume $1000 base capital for simulation
                        base_capital = 1000.0
                        position_size_usdt = base_capital * position_size_pct

                        # Assess risk metrics
                        volatility = indicator_values.get("volatility", 0.02)
                        max_drawdown = indicator_values.get("max_drawdown", 0.05)
                        sharpe_ratio = indicator_values.get("sharpe_ratio", 1.5)

                        risk_metrics = self.risk_manager.assess_position_risk(
                            symbol=strategy.symbol,
                            position_size=position_size_pct,
                            current_price=current_price,
                            volatility=volatility,
                            max_drawdown=max_drawdown,
                            sharpe_ratio=sharpe_ratio
                        )

                        # Check if position can be opened
                        risk_check = self.risk_manager.can_open_position(
                            strategy_name=strategy.strategy_name,
                            symbol=strategy.symbol,
                            position_size_usdt=position_size_usdt,
                            risk_metrics=risk_metrics
                        )

                        risk_approved = risk_check["approved"]
                        risk_warnings = risk_check["warnings"]

                        if not risk_approved:
                            self.logger.warning("strategy_manager.position_rejected", {
                                "strategy_name": strategy.strategy_name,
                                "symbol": strategy.symbol,
                                "reasons": risk_check["reasons"]
                            })
                            # Reset to monitoring state
                            strategy.current_state = StrategyState.MONITORING
                            await self._publish_strategy_event(strategy, "position_rejected", {
                                **indicator_values,
                                "reasons": risk_check["reasons"],
                                "warnings": risk_warnings
                            })
                            return

                        # Reserve budget
                        if not self.risk_manager.use_budget(strategy.strategy_name, position_size_usdt):
                            self.logger.warning("strategy_manager.budget_insufficient", {
                                "strategy_name": strategy.strategy_name,
                                "symbol": strategy.symbol,
                                "requested": position_size_usdt
                            })
                            strategy.current_state = StrategyState.MONITORING
                            return

                    except Exception as e:
                        self.logger.error("strategy_manager.risk_assessment_error", {
                            "strategy_name": strategy.strategy_name,
                            "symbol": strategy.symbol,
                            "error": str(e)
                        })
                        # Continue without risk check if error occurs

                # Submit buy order if order manager is available and risk approved
                if self.order_manager and risk_approved:
                    try:
                        current_price = indicator_values.get("price", indicator_values.get("last_price", 100.0))
                        position_size_pct = position_params.get("position_size_pct", 0.01)
                        base_capital = 1000.0
                        order_value = base_capital * position_size_pct
                        quantity = order_value / current_price

                        # Submit buy order
                        pump_signal_strength = indicator_values.get("pump_magnitude_pct", 0.0) / 100.0
                        order_id = await self.order_manager.submit_order(
                            symbol=strategy.symbol,
                            order_type=OrderType.BUY,
                            quantity=quantity,
                            price=current_price,
                            strategy_name=strategy.strategy_name,
                            pump_signal_strength=pump_signal_strength
                        )

                        # Update position params with order info
                        position_params["order_id"] = order_id
                        position_params["order_quantity"] = quantity
                        position_params["order_price"] = current_price
                        position_params["risk_warnings"] = risk_warnings

                    except Exception as e:
                        self.logger.error("strategy_manager.order_submission_error", {
                            "strategy_name": strategy.strategy_name,
                            "symbol": strategy.symbol,
                            "error": str(e)
                        })

                strategy.current_state = StrategyState.POSITION_ACTIVE
                strategy.position_active = True
                strategy.entry_time = datetime.now()

                await self._publish_strategy_event(strategy, "position_opened", {
                    **indicator_values,
                    **position_params
                })

            elif strategy.current_state == StrategyState.POSITION_ACTIVE:
                # ZE1: Check close order detection conditions
                close_result = strategy.evaluate_close_order_detection(indicator_values)
                if close_result == ConditionResult.TRUE:
                    # Record indicator values at close decision
                    close_indicators = strategy._record_decision_indicators(indicator_values, "ZE1_close_order_detection")
                    strategy.current_state = StrategyState.CLOSE_ORDER_EVALUATION
                    await self._publish_strategy_event(strategy, "close_order_detected", {
                        **indicator_values,
                        "recorded_indicators": close_indicators
                    })
                    return

                # E1: Check emergency exit conditions (higher priority than ZE1)
                emergency_result = strategy.evaluate_emergency_exit(indicator_values)
                if emergency_result == ConditionResult.TRUE:
                    # Record indicator values at emergency exit
                    emergency_indicators = strategy._record_decision_indicators(indicator_values, "E1_emergency_exit")
                    strategy.current_state = StrategyState.EMERGENCY_EXIT

                    # Start cooldown if configured
                    cooldown_minutes = strategy.global_limits.get("emergency_exit_cooldown_minutes", 30)
                    strategy.start_cooldown(cooldown_minutes, "emergency_exit")

                    await self._publish_strategy_event(strategy, "emergency_exit_triggered", {
                        **indicator_values,
                        "recorded_indicators": emergency_indicators,
                        "cooldown_started": True,
                        "cooldown_minutes": cooldown_minutes
                    })
                    return

            elif strategy.current_state == StrategyState.CLOSE_ORDER_EVALUATION:
                # Execute close order based on ZE1 detection with risk-adjusted pricing
                if self.order_manager:
                    try:
                        current_price = indicator_values.get("price", indicator_values.get("last_price", 100.0))

                        # Apply risk-adjusted close pricing per user_feedback.md
                        price_adjustment = strategy.calculate_close_price_adjustment(indicator_values, current_price)
                        adjusted_close_price = price_adjustment["adjusted_close_price"]

                        close_order_id = await self.order_manager.close_position(strategy.symbol, adjusted_close_price)
                        if close_order_id:
                            strategy.current_state = StrategyState.EXITED
                            strategy.position_active = False
                            strategy.exit_time = datetime.now()

                            # Phase 3: Release slot and symbol lock on completion
                            self.release_signal_slot(strategy.strategy_name)
                            self.unlock_symbol(strategy.symbol, strategy.strategy_name)

                            await self._publish_strategy_event(strategy, "position_closed_ze1", {
                                **indicator_values,
                                "exit_price": adjusted_close_price,
                                "original_price": current_price,
                                "price_adjustment_pct": price_adjustment["price_adjustment_pct"],
                                "order_id": close_order_id,
                                "exit_reason": "close_order_detection",
                                "slot_released": True,
                                "symbol_unlocked": True
                            })
                            return
                    except Exception as e:
                        self.logger.error("strategy_manager.close_order_error", {
                            "strategy_name": strategy.strategy_name,
                            "symbol": strategy.symbol,
                            "error": str(e)
                        })

            elif strategy.current_state == StrategyState.EMERGENCY_EXIT:
               # Execute emergency exit
               if self.order_manager:
                   try:
                       current_price = indicator_values.get("price", indicator_values.get("last_price", 100.0))
                       exit_order_id = await self.order_manager.emergency_exit(strategy.symbol, current_price)

                       if exit_order_id:
                           await self._publish_strategy_event(strategy, "emergency_exit_executed", {
                               **indicator_values,
                               "exit_price": current_price,
                               "order_id": exit_order_id
                           })
                   except Exception as e:
                       self.logger.error("strategy_manager.emergency_exit_error", {
                           "strategy_name": strategy.strategy_name,
                           "symbol": strategy.symbol,
                           "error": str(e)
                       })

               strategy.current_state = StrategyState.EXITED
               strategy.position_active = False
               strategy.exit_time = datetime.now()

               # Phase 3: Release slot and symbol lock on emergency exit
               self.release_signal_slot(strategy.strategy_name)
               self.unlock_symbol(strategy.symbol, strategy.strategy_name)

               await self._publish_strategy_event(strategy, "emergency_exit_executed", {
                   **indicator_values,
                   "slot_released": True,
                   "symbol_unlocked": True
               })

        except Exception as e:
            self.logger.error("strategy_manager.evaluation_error", {
                "strategy_name": strategy.strategy_name,
                "symbol": strategy.symbol,
                "error": str(e)
            })

    async def _publish_strategy_event(self, strategy: Strategy, event_type: str, data: Dict[str, Any]) -> None:
        """Publish strategy-related events with loop prevention"""
        event_data = {
            "strategy_name": strategy.strategy_name,
            "symbol": strategy.symbol,
            "event_type": event_type,
            "state": strategy.current_state.value,
            "timestamp": datetime.now().isoformat(),
            "source": "strategy_manager",  # Mark as strategy-generated to prevent loops
            **data
        }

        try:
            # Fire-and-forget pattern to prevent blocking
            asyncio.create_task(
                asyncio.wait_for(
                    self.event_bus.publish(f"strategy.{event_type}", event_data),
                    timeout=0.05  # Very short timeout for non-blocking
                )
            )
        except Exception as e:
            self.logger.error("strategy_manager.event_publish_error", {
                "strategy_name": strategy.strategy_name,
                "event_type": event_type,
                "error": str(e)
            })

        # Update telemetry (last event and state change)
        try:
            tel = self._strategy_telemetry.setdefault(strategy.strategy_name, {"last_event": None, "last_state_change": None, "active_symbols": set()})
            tel["last_event"] = {"event_type": event_type, "timestamp": event_data["timestamp"]}
            tel["last_state_change"] = event_data["timestamp"]
        except Exception as e:
            self.logger.warning("strategy_manager.telemetry_update_error", {
                "strategy_name": strategy.strategy_name,
                "event_type": event_type,
                "error": str(e)
            })

    def get_strategy_status(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific strategy"""
        if strategy_name not in self.strategies:
            return None

        strategy = self.strategies[strategy_name]
        return {
            "strategy_name": strategy.strategy_name,
            "enabled": strategy.enabled,
            "current_state": strategy.current_state.value,
            "symbol": strategy.symbol,
            "position_active": strategy.position_active,
            "entry_time": strategy.entry_time.isoformat() if strategy.entry_time else None,
            "exit_time": strategy.exit_time.isoformat() if strategy.exit_time else None
        }

    def get_active_strategies_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all active strategies for a symbol"""
        if symbol not in self.active_strategies:
            return []

        return [
            {
                "strategy_name": strategy.strategy_name,
                "current_state": strategy.current_state.value,
                "position_active": strategy.position_active
            }
            for strategy in self.active_strategies[symbol]
        ]

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Get all registered strategies"""
        return [
            {
                "strategy_name": strategy.strategy_name,
                "enabled": strategy.enabled,
                "current_state": strategy.current_state.value,
                "symbol": strategy.symbol
            }
            for strategy in self.strategies.values()
        ]

    def get_all_strategies_status(self) -> List[Dict[str, Any]]:
        """Get enriched status for all strategies"""
        results: List[Dict[str, Any]] = []
        for name, strategy in self.strategies.items():
            tel = self._strategy_telemetry.get(name, {"last_event": None, "last_state_change": None, "active_symbols": set()})
            results.append({
                "strategy_name": name,
                "enabled": strategy.enabled,
                "current_state": strategy.current_state.value,
                "symbol": strategy.symbol,
                "active_symbols_count": len(tel.get("active_symbols", set())),
                "last_event": tel.get("last_event"),
                "last_state_change": tel.get("last_state_change"),
            })
        return results

    def validate_strategy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy configuration for UI support"""
        errors = []
        warnings = []

        # Required fields
        if not config.get("strategy_name"):
            errors.append("strategy_name is required")
        elif not isinstance(config.get("strategy_name"), str) or len(config.get("strategy_name", "")) < 3:
            errors.append("strategy_name must be a string with at least 3 characters")

        # Global limits validation
        global_limits = config.get("global_limits", {})
        if not isinstance(global_limits, dict):
            errors.append("global_limits must be a dictionary")
        else:
            # Validate numeric limits
            numeric_limits = [
                ("base_position_pct", 0.01, 1.0),
                ("max_position_size_usdt", 1, 10000),
                ("min_position_size_usdt", 1, 1000),
                ("max_leverage", 1.0, 10.0),
                ("stop_loss_buffer_pct", 1.0, 50.0),
                ("target_profit_pct", 1.0, 100.0),
                ("max_allocation_pct", 0.1, 20.0)
            ]

            for limit_name, min_val, max_val in numeric_limits:
                if limit_name in global_limits:
                    value = global_limits[limit_name]
                    if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                        errors.append(f"{limit_name} must be between {min_val} and {max_val}")

        # Validate condition groups - 5-section structure per user_feedback.md
        condition_groups = ["signal_detection", "signal_cancellation", "entry_conditions", "close_order_detection", "emergency_exit"]
        for group_name in condition_groups:
            if group_name in config:
                group_config = config[group_name]
                if not isinstance(group_config, dict):
                    errors.append(f"{group_name} must be a dictionary")
                    continue

                conditions = group_config.get("conditions", [])
                if not isinstance(conditions, list):
                    errors.append(f"{group_name}.conditions must be a list")
                    continue

                for i, condition in enumerate(conditions):
                    if not isinstance(condition, dict):
                        errors.append(f"{group_name}.conditions[{i}] must be a dictionary")
                        continue

                    required_fields = ["name", "condition_type", "operator", "value"]
                    for field in required_fields:
                        if field not in condition:
                            errors.append(f"{group_name}.conditions[{i}] missing required field: {field}")

                    # Validate operator
                    valid_operators = ["gte", "lte", "gt", "lt", "eq", "between", "allowed"]
                    if condition.get("operator") not in valid_operators:
                        errors.append(f"{group_name}.conditions[{i}] invalid operator: {condition.get('operator')}")

        # Warnings for best practices
        if not global_limits.get("stop_loss_buffer_pct"):
            warnings.append("Consider setting stop_loss_buffer_pct for risk management")

        if not global_limits.get("max_allocation_pct"):
            warnings.append("Consider setting max_allocation_pct to limit portfolio exposure")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def upsert_strategy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert (update or insert) strategy with validation"""
        # Validate configuration first
        validation_result = self.validate_strategy_config(config)
        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            }

        strategy_name = config["strategy_name"]

        try:
            # Check if strategy exists
            if strategy_name in self.strategies:
                # Update existing strategy
                existing_strategy = self.strategies[strategy_name]

                # Deactivate if currently active
                if existing_strategy.symbol:
                    self.deactivate_strategy_for_symbol(strategy_name, existing_strategy.symbol)

                # Create new strategy from config
                new_strategy = self.create_strategy_from_config(config)

                # Preserve some runtime state if appropriate
                new_strategy.current_state = StrategyState.INACTIVE
                new_strategy.symbol = ""  # Reset symbol

                # Replace in registry
                self.strategies[strategy_name] = new_strategy

                self.logger.info("strategy_manager.strategy_updated", {
                    "strategy_name": strategy_name
                })

                return {
                    "success": True,
                    "action": "updated",
                    "strategy_name": strategy_name,
                    "warnings": validation_result["warnings"]
                }
            else:
                # Create new strategy
                new_strategy = self.create_strategy_from_config(config)
                self.add_strategy(new_strategy)

                self.logger.info("strategy_manager.strategy_created", {
                    "strategy_name": strategy_name
                })

                return {
                    "success": True,
                    "action": "created",
                    "strategy_name": strategy_name,
                    "warnings": validation_result["warnings"]
                }

        except Exception as e:
            self.logger.error("strategy_manager.upsert_error", {
                "strategy_name": strategy_name,
                "error": str(e)
            })
            return {
                "success": False,
                "errors": [f"Failed to upsert strategy: {str(e)}"],
                "warnings": validation_result["warnings"]
            }
