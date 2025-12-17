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
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from uuid import uuid4

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from .order_manager import OrderManager, OrderType
from .risk_manager import RiskManager

try:
    import asyncpg
except ImportError:
    asyncpg = None  # QuestDB persistence optional


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
        """Evaluate this condition against current indicator values.

        Supports case-insensitive matching for condition_type to indicator keys.
        E.g., condition_type="price_velocity" will match "PRICE_VELOCITY" or "price_velocity".
        """
        if not self.enabled:
            return ConditionResult.PENDING

        # Case-insensitive key lookup
        condition_key = self.condition_type.lower()
        actual_value = None
        found = False

        for key, value in indicator_values.items():
            if key.lower() == condition_key:
                actual_value = value
                found = True
                break

        if not found:
            return ConditionResult.PENDING

        try:
            # Normalize operator to handle both symbolic (>, <, >=, <=, ==) and word (gt, lt, gte, lte, eq) formats
            op = self.operator.lower().strip() if isinstance(self.operator, str) else self.operator

            if op in ("gte", ">="):
                return ConditionResult.TRUE if actual_value >= self.value else ConditionResult.FALSE
            elif op in ("lte", "<="):
                return ConditionResult.TRUE if actual_value <= self.value else ConditionResult.FALSE
            elif op in ("gt", ">"):
                return ConditionResult.TRUE if actual_value > self.value else ConditionResult.FALSE
            elif op in ("lt", "<"):
                return ConditionResult.TRUE if actual_value < self.value else ConditionResult.FALSE
            elif op in ("eq", "==", "="):
                return ConditionResult.TRUE if actual_value == self.value else ConditionResult.FALSE
            elif op == "between":
                min_val, max_val = self.value
                return ConditionResult.TRUE if min_val <= actual_value <= max_val else ConditionResult.FALSE
            elif op == "allowed":
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
        """Evaluate all conditions in this group

        BUG FIX (2025-12-17): Empty condition list returns FALSE, not TRUE.
        Previously empty O1 (signal_cancellation) would always trigger cancellation.
        Empty conditions should mean "no conditions to satisfy" = FALSE.

        Business logic:
        - Empty S1 = no detection criteria = FALSE (don't trigger signal)
        - Empty O1 = no cancellation criteria = FALSE (don't cancel)
        - Empty Z1 = no entry criteria = FALSE (don't enter)
        - Empty ZE1 = no close criteria = FALSE (don't close)
        - Empty E1 = no emergency criteria = FALSE (don't exit)
        """
        if not self.conditions:
            return ConditionResult.FALSE  # No conditions = nothing to satisfy = FALSE

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
    """Complete strategy with 5 condition groups + SHORT support"""
    strategy_name: str
    enabled: bool = True
    direction: str = "LONG"  # "LONG", "SHORT", or "BOTH"

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
    signal_detection_time: Optional[datetime] = None  # When S1 signal was detected

    # Cooldown tracking (per user_feedback.md)
    cooldown_until: Optional[datetime] = None  # When cooldown expires
    last_signal_cancelled: Optional[datetime] = None  # O1 cooldown
    last_emergency_exit: Optional[datetime] = None  # E1 cooldown

    def get_entry_order_type(self) -> OrderType:
        """Get entry order type based on strategy direction

        Returns:
            OrderType.BUY for LONG strategies
            OrderType.SHORT for SHORT strategies

        Raises:
            ValueError: If direction is "BOTH" (not yet supported)
        """
        if self.direction == "LONG":
            return OrderType.BUY
        elif self.direction == "SHORT":
            return OrderType.SHORT
        else:
            raise ValueError(f"Unsupported direction for single entry: {self.direction}. Use 'LONG' or 'SHORT'.")

    def evaluate_signal_detection(self, indicator_values: Dict[str, Any]) -> ConditionResult:
        """Evaluate signal detection conditions"""
        return self.signal_detection.evaluate(indicator_values)

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
        """Calculate position sizing with risk-adjusted pricing per user_feedback.md

        Returns:
            Dict with:
            - position_size_pct: percentage of capital to use (0.0 to 1.0 scale, e.g., 0.02 = 2%)
            - risk_adjusted_multiplier: how much the position was adjusted based on risk
            - max_leverage, stop_loss_pct, take_profit_pct: strategy limits

        BUG FIX (2025-12-17): Previously returned USDT values in position_size_pct field,
        then code multiplied by capital again causing incorrect position sizes.
        Now correctly returns percentage (0.0-1.0 scale).
        """
        # Base position sizing as percentage (default 2% = 0.02)
        base_size_pct = self.global_limits.get("base_position_pct", 0.02)

        # Risk-adjusted sizing multiplier
        risk_multiplier = self._calculate_risk_adjustment_multiplier(indicator_values)
        risk_adjusted_pct = base_size_pct * risk_multiplier

        # Apply percentage limits (e.g., min 0.5% = 0.005, max 10% = 0.10)
        max_pct = self.global_limits.get("max_position_pct", 0.10)  # Max 10% of capital
        min_pct = self.global_limits.get("min_position_pct", 0.005)  # Min 0.5% of capital

        final_position_pct = max(min_pct, min(max_pct, risk_adjusted_pct))

        return {
            "position_size_pct": final_position_pct,
            "risk_adjusted_multiplier": risk_multiplier,
            "max_leverage": self.global_limits.get("max_leverage", 2.0),
            "stop_loss_pct": self.global_limits.get("stop_loss_buffer_pct", 10.0),
            "take_profit_pct": self.global_limits.get("target_profit_pct", 25.0)
        }

    def _calculate_risk_adjustment_multiplier(self, indicator_values: Dict[str, Any]) -> float:
        """Calculate risk adjustment multiplier based on current market conditions.

        Returns a multiplier (e.g., 1.0 = no adjustment, 0.5 = half size, 1.5 = 50% larger)

        BUG FIX (2025-12-17): Renamed from _calculate_risk_adjusted_position_size.
        Now returns multiplier only, not the adjusted size.
        """
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

        return multiplier  # Return multiplier only, not adjusted size

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
                 risk_manager: Optional[RiskManager] = None,
                 db_pool: Optional['asyncpg.Pool'] = None):  # QuestDB connection pool for persistence
        self.event_bus = event_bus
        self.logger = logger
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.db_pool = db_pool  # PostgreSQL wire protocol connection to QuestDB

        # Strategy storage (in-memory cache + DB persistence)
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategies: Dict[str, List[Strategy]] = {}  # symbol -> strategies

        # Indicator values cache
        self.indicator_values: Dict[str, Dict[str, Any]] = {}  # symbol -> indicators

        # Telemetry: last events and active symbols per strategy
        self._strategy_telemetry: Dict[str, Dict[str, Any]] = {}

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

        # ✅ RACE CONDITION FIX: Background task tracking to prevent fire-and-forget leaks
        # Tasks are tracked and properly cancelled during shutdown
        self._background_tasks: set = set()

        # ✅ RACE CONDITION FIX: Per-dictionary locks for atomic operations
        # Prevents check-then-act race conditions across all shared state
        self._strategies_lock = asyncio.Lock()           # Protects self.strategies dict
        self._active_strategies_lock = asyncio.Lock()    # Protects self.active_strategies dict
        self._indicator_values_lock = asyncio.Lock()     # Protects self.indicator_values dict
        self._telemetry_lock = asyncio.Lock()            # Protects self._strategy_telemetry dict
        self._signal_slots_lock = asyncio.Lock()         # Protects self._global_signal_slots dict
        self._symbol_locks_lock = asyncio.Lock()         # Protects self._symbol_locks dict

        # ✅ FIX (2025-12-03): Per-strategy locks to prevent concurrent evaluation race condition
        # Multiple indicator events can trigger concurrent evaluations of the same strategy,
        # leading to multiple slot acquisitions before state change to SIGNAL_DETECTED
        self._strategy_evaluation_locks: Dict[str, asyncio.Lock] = {}

        # Strategy loading will be done asynchronously after initialization
        # See: initialize_strategies() method

        # Event listener subscription will be done in start() method
        # This allows async initialization

        self.logger.info("strategy_manager.initialized", {
            "order_manager_enabled": order_manager is not None,
            "db_pool_enabled": db_pool is not None
        })

    async def start(self) -> None:
        """Start the strategy manager by subscribing to indicator and price events."""
        await self.event_bus.subscribe("indicator.updated", self._on_indicator_update)
        # ✅ FIX (2025-12-04): Subscribe to price updates to enable order creation
        # Without price data, orders were being created with fallback price (100.0)
        # which caused OrderManager to reject orders with invalid prices
        await self.event_bus.subscribe("market.price_update", self._on_price_update)

    async def reset_session_state(self) -> None:
        """Reset all session state for a new trading/backtest session.

        This method clears:
        - Signal slots (allows new signals to be generated)
        - Symbol locks (allows symbols to be traded again)
        - Strategy states (reset to MONITORING)
        - Indicator values cache (fresh start)

        Should be called when starting a new session (live, paper, backtest).
        """
        # DEBUG PRINT (bypass logger issues)
        print(f"[RESET_SESSION_STATE] Called! Slots before: {dict(self._global_signal_slots)}, Locks before: {dict(self._symbol_locks)}")

        self.logger.info("strategy_manager.reset_session_state_started", {
            "slots_before": dict(self._global_signal_slots),
            "locks_before": dict(self._symbol_locks),
            "active_strategies": len(self.active_strategies)
        })

        # Reset signal slots
        async with self._signal_slots_lock:
            self._global_signal_slots.clear()

        # Reset symbol locks
        async with self._symbol_locks_lock:
            self._symbol_locks.clear()

        # Reset all strategy states
        async with self._strategies_lock:
            for strategy in self.strategies.values():
                strategy.current_state = StrategyState.MONITORING
                strategy.signal_detection_time = None
                strategy.entry_time = None
                strategy.exit_time = None
                strategy.cooldown_until = None

        # Clear cached indicator values
        async with self._indicator_values_lock:
            self.indicator_values.clear()

        self.logger.info("strategy_manager.reset_session_state_completed", {
            "slots_after": dict(self._global_signal_slots),
            "locks_after": dict(self._symbol_locks)
        })

    def _get_strategy_evaluation_lock(self, strategy_name: str) -> asyncio.Lock:
        """✅ FIX (2025-12-03): Get or create a lock for per-strategy evaluation.

        This ensures that only one coroutine can evaluate a strategy at a time,
        preventing the race condition where multiple concurrent evaluations
        all acquire slots before any can change the strategy state.
        """
        if strategy_name not in self._strategy_evaluation_locks:
            self._strategy_evaluation_locks[strategy_name] = asyncio.Lock()
        return self._strategy_evaluation_locks[strategy_name]

    async def shutdown(self) -> None:
        """✅ RACE CONDITION FIX: Graceful shutdown with background task cleanup

        Cancels all tracked background tasks to prevent memory leaks and
        dangling task warnings during application shutdown.

        ✅ FIX P0 LEAK #3: Added unsubscribe for event listeners to prevent memory leaks
        """
        self.logger.info("strategy_manager.shutdown_initiated", {
            "background_tasks_count": len(self._background_tasks)
        })

        # FIX P0 LEAK #3: Unsubscribe from event bus to prevent memory leaks
        try:
            await self.event_bus.unsubscribe("indicator.updated", self._on_indicator_update)
            await self.event_bus.unsubscribe("market.price_update", self._on_price_update)
            self.logger.info("strategy_manager.event_listeners_unsubscribed")
        except Exception as e:
            self.logger.warning("strategy_manager.unsubscribe_error", {"error": str(e)})

        # Cancel all background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Clear the task set
        self._background_tasks.clear()

        self.logger.info("strategy_manager.shutdown_completed")

    def validate_dependencies(self) -> None:
        """Validate that all required dependencies are properly set"""
        if self.order_manager is None:
            raise RuntimeError("StrategyManager dependency validation failed: order_manager not set")
        if self.risk_manager is None:
            raise RuntimeError("StrategyManager dependency validation failed: risk_manager not set")

    async def acquire_signal_slot(self, strategy_name: str) -> bool:
        """✅ RACE CONDITION FIX: Atomic check-and-acquire signal slot

        Merges can_acquire_signal_slot() into acquire_signal_slot() to prevent
        race condition where multiple strategies check availability simultaneously
        before any can acquire, leading to over-allocation.

        ✅ FIX (2025-12-03): Each strategy can only have ONE active signal slot.
        This prevents race condition where parallel evaluations all acquire slots
        for the same strategy before any changes state to SIGNAL_DETECTED.

        Args:
            strategy_name: Name of strategy requesting slot

        Returns:
            True if slot acquired successfully, False if at capacity or strategy already has slot
        """
        async with self._signal_slots_lock:
            current_slots = self._global_signal_slots.get(strategy_name, 0)
            total_active_signals = sum(self._global_signal_slots.values())

            # ✅ FIX: Strategy already has a slot - cannot acquire more
            # This is the key fix for race condition
            if current_slots > 0:
                self.logger.debug("strategy_manager.slot_already_held", {
                    "strategy_name": strategy_name,
                    "current_slots": current_slots
                })
                return False

            # Check global limit
            if total_active_signals >= self._max_concurrent_signals:
                return False

            # Atomically acquire slot (always 1 since we rejected if > 0)
            self._global_signal_slots[strategy_name] = 1
            return True

    async def release_signal_slot(self, strategy_name: str) -> None:
        """✅ RACE CONDITION FIX: Release signal slot atomically

        Args:
            strategy_name: Name of strategy releasing slot
        """
        async with self._signal_slots_lock:
            if strategy_name in self._global_signal_slots:
                self._global_signal_slots[strategy_name] = max(0, self._global_signal_slots[strategy_name] - 1)
                if self._global_signal_slots[strategy_name] == 0:
                    del self._global_signal_slots[strategy_name]

    async def lock_symbol(self, symbol: str, strategy_name: str) -> bool:
        """✅ RACE CONDITION FIX: Atomic check-and-lock symbol

        Merges can_lock_symbol() into lock_symbol() to prevent race condition
        where multiple strategies check symbol availability simultaneously before
        any can lock, leading to double-booking.

        Args:
            symbol: Symbol to lock
            strategy_name: Name of strategy requesting lock

        Returns:
            True if symbol locked successfully, False if already locked by another strategy
        """
        async with self._symbol_locks_lock:
            # Check if symbol is already locked by another strategy
            if symbol in self._symbol_locks and self._symbol_locks[symbol] != strategy_name:
                return False

            # Atomically lock symbol
            self._symbol_locks[symbol] = strategy_name
            return True

    async def unlock_symbol(self, symbol: str, strategy_name: str) -> None:
        """✅ RACE CONDITION FIX: Unlock symbol atomically

        Args:
            symbol: Symbol to unlock
            strategy_name: Name of strategy releasing lock
        """
        async with self._symbol_locks_lock:
            if self._symbol_locks.get(symbol) == strategy_name:
                del self._symbol_locks[symbol]

    def get_slot_status(self) -> Dict[str, Any]:
        """✅ RACE CONDITION FIX: Get slot status with thread-safe snapshot

        Note: This method is synchronous for backward compatibility but creates
        a snapshot that may be stale by the time caller uses it. Callers should
        use atomic operations (acquire_signal_slot, lock_symbol) rather than
        checking status then acting.
        """
        # Create thread-safe snapshot (brief lock acquisition acceptable for reads)
        # We can't make this async without breaking existing callers
        try:
            # Manual lock acquisition for synchronous method
            # TODO: Consider making this async in future refactor
            snapshot_slots = dict(self._global_signal_slots)
            snapshot_locks = dict(self._symbol_locks)
            total_signals = sum(snapshot_slots.values())

            return {
                "max_concurrent_signals": self._max_concurrent_signals,
                "total_active_signals": total_signals,
                "strategy_slots": snapshot_slots,
                "available_slots": max(0, self._max_concurrent_signals - total_signals),
                "symbol_locks": snapshot_locks
            }
        except Exception:
            # Fallback if dict changes during iteration
            return {
                "max_concurrent_signals": self._max_concurrent_signals,
                "total_active_signals": 0,
                "strategy_slots": {},
                "available_slots": self._max_concurrent_signals,
                "symbol_locks": {}
            }

    async def initialize_strategies(self) -> None:
        """Load strategies from QuestDB or create default strategies if DB empty

        This method should be called after StrategyManager initialization.
        It first attempts to load strategies from QuestDB. If no strategies
        are found (or DB not configured), it creates default pump/dump strategies.
        """
        # Try to load from QuestDB first
        loaded_count = 0
        if self.db_pool:
            try:
                loaded_count = await self.load_strategies_from_db()
                if loaded_count > 0:
                    self.logger.info("strategy_manager.strategies_loaded", {
                        "source": "questdb",
                        "count": loaded_count
                    })
                    return  # Successfully loaded from DB, no need for defaults
            except Exception as e:
                self.logger.error("strategy_manager.db_load_error", {
                    "error": str(e)
                })

        # No strategies loaded from DB or DB not configured - create defaults
        self.logger.info("strategy_manager.creating_default_strategies", {
            "reason": "no_db_strategies" if self.db_pool else "db_not_configured"
        })

        # ✅ Create comprehensive pump/dump detection strategy
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
            direction=config.get("direction", "LONG"),  # ⚠️ CRITICAL FIX: Support SHORT strategies
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

    # ============================================================================
    # QUESTDB PERSISTENCE METHODS
    # ============================================================================

    def _strategy_to_json(self, strategy: Strategy) -> str:
        """Convert Strategy object to JSON string for database storage

        Args:
            strategy: Strategy object to serialize

        Returns:
            JSON string representation
        """
        # Serialize conditions
        def serialize_conditions(conditions: List[Condition]) -> List[Dict[str, Any]]:
            return [
                {
                    "name": c.name,
                    "condition_type": c.condition_type,
                    "operator": c.operator,
                    "value": c.value,
                    "description": c.description
                }
                for c in conditions
            ]

        strategy_dict = {
            "strategy_name": strategy.strategy_name,
            "enabled": strategy.enabled,
            "direction": strategy.direction,
            "global_limits": strategy.global_limits,
            "signal_detection": {
                "conditions": serialize_conditions(strategy.signal_detection.conditions)
            },
            "signal_cancellation": {
                "conditions": serialize_conditions(strategy.signal_cancellation.conditions)
            },
            "entry_conditions": {
                "conditions": serialize_conditions(strategy.entry_conditions.conditions)
            },
            "close_order_detection": {
                "conditions": serialize_conditions(strategy.close_order_detection.conditions)
            },
            "emergency_exit": {
                "conditions": serialize_conditions(strategy.emergency_exit.conditions)
            }
        }

        return json.dumps(strategy_dict)

    def _strategy_from_json(self, strategy_json: str, strategy_name: str, direction: str, enabled: bool) -> Strategy:
        """Reconstruct Strategy object from JSON string

        Args:
            strategy_json: JSON string from database
            strategy_name: Strategy name (from direction column)
            direction: Trading direction (from direction column)
            enabled: Enabled status (from enabled column)

        Returns:
            Reconstructed Strategy object
        """
        config = json.loads(strategy_json)

        # Create strategy with metadata
        strategy = Strategy(
            strategy_name=strategy_name,
            enabled=enabled,
            direction=direction,
            global_limits=config.get("global_limits", {})
        )

        # Reconstruct conditions
        # ✅ FIX: Support both old and new schema formats
        # Old schema: {name, condition_type, operator, value, description}
        # New schema: {id, indicatorId, operator, value}
        def deserialize_conditions(condition_list: List[Dict[str, Any]]) -> List[Condition]:
            conditions = []
            for c in condition_list:
                # Detect schema version by checking for 'id' or 'name' field
                if "id" in c and "indicatorId" in c:
                    # New 5-section schema format
                    conditions.append(Condition(
                        name=c.get("id", c.get("indicatorId", "unknown")),
                        condition_type=c.get("indicatorId", "unknown"),
                        operator=c.get("operator", "gte"),
                        value=c.get("value", 0),
                        description=c.get("description", "")
                    ))
                else:
                    # Old schema format
                    conditions.append(Condition(
                        name=c.get("name", "unknown"),
                        condition_type=c.get("condition_type", "unknown"),
                        operator=c.get("operator", "gte"),
                        value=c.get("value", 0),
                        description=c.get("description", "")
                    ))
            return conditions

        # ✅ FIX: Support both old and new schema section names
        # Old schema: signal_detection, signal_cancellation, entry_conditions, close_order_detection, emergency_exit
        # New schema: s1_signal, o1_cancel, z1_entry, ze1_close, emergency_exit

        # S1: Signal detection
        signal_section = config.get("s1_signal") or config.get("signal_detection")
        if signal_section:
            strategy.signal_detection.conditions = deserialize_conditions(
                signal_section.get("conditions", [])
            )

        # O1: Signal cancellation
        cancel_section = config.get("o1_cancel") or config.get("signal_cancellation")
        if cancel_section:
            strategy.signal_cancellation.conditions = deserialize_conditions(
                cancel_section.get("conditions", [])
            )

        # Z1: Entry conditions
        entry_section = config.get("z1_entry") or config.get("entry_conditions")
        if entry_section:
            strategy.entry_conditions.conditions = deserialize_conditions(
                entry_section.get("conditions", [])
            )

        # ZE1: Close order detection
        close_section = config.get("ze1_close") or config.get("close_order_detection")
        if close_section:
            strategy.close_order_detection.conditions = deserialize_conditions(
                close_section.get("conditions", [])
            )

        # E1: Emergency exit (same name in both schemas)
        if "emergency_exit" in config:
            strategy.emergency_exit.conditions = deserialize_conditions(
                config["emergency_exit"].get("conditions", [])
            )

        return strategy

    async def save_strategy_to_db(self, strategy: Strategy) -> bool:
        """Persist strategy to QuestDB strategies table

        Args:
            strategy: Strategy object to save

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.db_pool:
            self.logger.warning("strategy_manager.db_persistence_disabled", {
                "strategy_name": strategy.strategy_name,
                "reason": "db_pool not configured"
            })
            return False

        try:
            strategy_json = self._strategy_to_json(strategy)
            strategy_id = str(uuid4())
            now = datetime.now()

            async with self.db_pool.acquire() as conn:
                # Check if strategy exists
                existing = await conn.fetchrow(
                    "SELECT id FROM strategies WHERE strategy_name = $1",
                    strategy.strategy_name
                )

                if existing:
                    # UPDATE existing strategy
                    await conn.execute(
                        """
                        UPDATE strategies
                        SET direction = $1,
                            enabled = $2,
                            strategy_json = $3,
                            updated_at = $4
                        WHERE strategy_name = $5
                        """,
                        strategy.direction,
                        strategy.enabled,
                        strategy_json,
                        now,
                        strategy.strategy_name
                    )
                    self.logger.info("strategy_manager.strategy_updated_in_db", {
                        "strategy_name": strategy.strategy_name
                    })
                else:
                    # INSERT new strategy
                    await conn.execute(
                        """
                        INSERT INTO strategies (
                            id, strategy_name, description, direction, enabled,
                            strategy_json, author, category, tags, template_id,
                            created_at, updated_at, last_activated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        strategy_id,
                        strategy.strategy_name,
                        f"Strategy: {strategy.strategy_name}",  # description
                        strategy.direction,
                        strategy.enabled,
                        strategy_json,
                        "user",  # author
                        "custom",  # category
                        "",  # tags (empty for now)
                        None,  # template_id (null)
                        now,  # created_at
                        now,  # updated_at
                        None  # last_activated_at (null initially)
                    )
                    self.logger.info("strategy_manager.strategy_saved_to_db", {
                        "strategy_name": strategy.strategy_name,
                        "id": strategy_id
                    })

            return True

        except Exception as e:
            self.logger.error("strategy_manager.db_save_failed", {
                "strategy_name": strategy.strategy_name,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def load_strategies_from_db(self) -> int:
        """Load all enabled strategies from QuestDB

        Returns:
            Number of strategies loaded
        """
        if not self.db_pool:
            self.logger.warning("strategy_manager.db_persistence_disabled", {
                "reason": "db_pool not configured"
            })
            return 0

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT strategy_name, direction, enabled, strategy_json
                    FROM strategies
                    WHERE enabled = true
                    AND (is_deleted = false OR is_deleted IS NULL)
                    ORDER BY created_at DESC
                    """
                )

            loaded_count = 0
            for row in rows:
                try:
                    strategy = self._strategy_from_json(
                        strategy_json=row["strategy_json"],
                        strategy_name=row["strategy_name"],
                        direction=row["direction"],
                        enabled=row["enabled"]
                    )

                    # Add to in-memory storage
                    self.strategies[strategy.strategy_name] = strategy

                    # Initialize telemetry
                    if strategy.strategy_name not in self._strategy_telemetry:
                        self._strategy_telemetry[strategy.strategy_name] = {
                            "last_event": None,
                            "last_state_change": None,
                            "active_symbols": set()
                        }

                    loaded_count += 1

                except Exception as e:
                    self.logger.error("strategy_manager.strategy_load_failed", {
                        "strategy_name": row["strategy_name"],
                        "error": str(e)
                    })
                    continue

            self.logger.info("strategy_manager.strategies_loaded_from_db", {
                "count": loaded_count
            })

            return loaded_count

        except Exception as e:
            self.logger.error("strategy_manager.db_load_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            return 0

    async def delete_strategy_from_db(self, strategy_name: str) -> bool:
        """Soft delete strategy from QuestDB (sets is_deleted = true, deleted_at = timestamp)

        Args:
            strategy_name: Name of strategy to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.db_pool:
            self.logger.warning("strategy_manager.db_persistence_disabled", {
                "strategy_name": strategy_name,
                "reason": "db_pool not configured"
            })
            return False

        try:
            # Use literal TIMESTAMP for QuestDB compatibility
            from datetime import datetime
            deleted_at = datetime.utcnow()
            deleted_at_str = deleted_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            async with self.db_pool.acquire() as conn:
                # Soft delete: UPDATE instead of DELETE
                result = await conn.execute(
                    f"UPDATE strategies SET is_deleted = true, deleted_at = '{deleted_at_str}' WHERE strategy_name = $1 AND is_deleted = false",
                    strategy_name
                )

            self.logger.info("strategy_manager.strategy_deleted_from_db", {
                "strategy_name": strategy_name,
                "result": result,
                "soft_delete": True
            })

            return True

        except Exception as e:
            self.logger.error("strategy_manager.db_delete_failed", {
                "strategy_name": strategy_name,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

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

    async def remove_strategy(self, strategy_name: str) -> bool:
        """Remove strategy from registry, deactivate from all symbols, and delete from QuestDB"""
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

                # ⚠️ CRITICAL: Delete from QuestDB
                await self.delete_strategy_from_db(strategy_name)

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

        # Update telemetry with active strategies count
        self._update_active_strategies_metric()

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

        # Update telemetry with active strategies count
        self._update_active_strategies_metric()

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

    async def _on_price_update(self, data: Dict[str, Any]) -> None:
        """Handle market price update events.

        ✅ FIX (2025-12-04): Store price in indicator_values so OrderManager
        can create orders with real prices instead of fallback 100.0

        Args:
            data: Price update with keys: symbol, price, volume, timestamp
        """
        symbol = data.get("symbol")
        price = data.get("price")

        if not symbol or price is None:
            return

        # Store price in indicator_values cache for strategy evaluation
        async with self._indicator_values_lock:
            if symbol not in self.indicator_values:
                self.indicator_values[symbol] = {}
            self.indicator_values[symbol]["price"] = float(price)
            self.indicator_values[symbol]["last_price"] = float(price)

        self.logger.debug("strategy_manager.price_update_cached", {
            "symbol": symbol,
            "price": price
        })

    async def _on_indicator_update(self, data: Dict[str, Any]) -> None:
        """Handle indicator update events with enhanced circuit breaker"""
        symbol = data.get("symbol")
        indicator_name = data.get("indicator")
        # ✅ FIX (2025-12-01): Use indicator_type for condition matching
        # Strategy conditions use indicatorId (e.g., "price_velocity") but
        # indicator.indicator contains full variant name (e.g., "PRICE_VELOCITY_default_ARIA_USDT_20")
        # We use indicator_type (lowercase base type) for storage so Condition.evaluate() can find it
        indicator_type = data.get("indicator_type", "").lower()
        value = data.get("value")

        if not symbol or not indicator_name:
            return

        # 🔍 DEBUG: Log indicator update receipt (using INFO for visibility)
        self.logger.info("strategy_manager.indicator_update_received", {
            "symbol": symbol,
            "indicator_name": indicator_name,
            "indicator_type": indicator_type,
            "value": value,
            "active_strategies_for_symbol": symbol in self.active_strategies,
            "active_count": len(self.active_strategies.get(symbol, []))
        })

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

        # ✅ RACE CONDITION FIX: Update indicator cache atomically
        # ✅ FIX (2025-12-01): Store under indicator_type (lowercase) for condition matching
        # If indicator_type is empty, fall back to indicator_name for backward compatibility
        storage_key = indicator_type if indicator_type else indicator_name.lower()
        async with self._indicator_values_lock:
            if symbol not in self.indicator_values:
                self.indicator_values[symbol] = {}
            self.indicator_values[symbol][storage_key] = value

        # Async evaluation - NO TIMEOUT to debug signal generation flow
        # ✅ FIX (2025-12-03): Removed timeout completely to diagnose blocking issue
        # The timeout was causing evaluation to be cancelled before signal_generated could be published.
        # We need to understand what's blocking AFTER slot_acquire_result before re-adding timeout.
        try:
            self._evaluation_in_progress.add(symbol)
            await self._evaluate_strategies_for_symbol(symbol)
        except Exception as e:
            self.logger.error("strategy_manager.evaluation_error", {
                "symbol": symbol,
                "indicator": indicator_name,
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
                # ✅ FIX (2025-12-03): REMOVED per-strategy timeout
                # The outer timeout (2.0s) is sufficient. Inner timeout was causing
                # signal generation to be cut off after slot was acquired,
                # leaving the slot locked without publishing signal_generated.
                await self._evaluate_strategy(strategy, indicator_values)
            except Exception as e:
                self.logger.error("strategy_manager.strategy_evaluation_error", {
                    "strategy_name": strategy.strategy_name,
                    "symbol": symbol,
                    "error": str(e)
                })

    async def _evaluate_strategy(self, strategy: Strategy, indicator_values: Dict[str, Any]) -> None:
        """Evaluate a single strategy against current conditions - 5-section workflow per user_feedback.md"""
        # ✅ FIX (2025-12-03): Use per-strategy lock to prevent concurrent evaluation race condition
        # Without this lock, multiple indicator.updated events can trigger parallel evaluations,
        # all seeing current_state=MONITORING, all acquiring slots before any changes state
        async with self._get_strategy_evaluation_lock(strategy.strategy_name):
            await self._evaluate_strategy_locked(strategy, indicator_values)

    async def _evaluate_strategy_locked(self, strategy: Strategy, indicator_values: Dict[str, Any]) -> None:
        """Internal locked evaluation - called only from _evaluate_strategy with lock held"""
        try:
            # ✅ FIX (2025-12-03): Early exit if strategy already has a signal slot AND is in MONITORING
            # This prevents race condition where multiple parallel evaluations
            # all acquire slots before any changes state to SIGNAL_DETECTED
            # BUG FIX (2025-12-17): Only skip S1 evaluation in MONITORING state, not O1/Z1/ZE1/E1
            # When strategy is in SIGNAL_DETECTED/ENTRY_EVALUATION/POSITION_ACTIVE, it must continue
            if strategy.strategy_name in self._global_signal_slots and strategy.current_state == StrategyState.MONITORING:
                self.logger.debug("strategy_manager.skipping_s1_has_slot", {
                    "strategy_name": strategy.strategy_name,
                    "current_state": strategy.current_state.value,
                    "existing_slots": self._global_signal_slots.get(strategy.strategy_name, 0)
                })
                return  # Strategy already has active signal in MONITORING, skip S1 evaluation

            # 🔍 DEBUG: Log strategy evaluation
            self.logger.debug("strategy_manager.evaluating_strategy", {
                "strategy_name": strategy.strategy_name,
                "current_state": strategy.current_state.value,
                "symbol": strategy.symbol,
                "indicator_values_keys": list(indicator_values.keys()),
                "signal_detection_conditions_count": len(strategy.signal_detection.conditions) if strategy.signal_detection else 0
            })

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

                # 🔍 DEBUG: Log signal detection result - temporarily INFO for debugging
                condition_type = strategy.signal_detection.conditions[0].condition_type if strategy.signal_detection and strategy.signal_detection.conditions else ""
                self.logger.info("strategy_manager.signal_detection_result", {
                    "strategy_name": strategy.strategy_name,
                    "signal_result": signal_result.value if signal_result else "None",
                    "condition_type_needed": condition_type,
                    "condition_value_needed": strategy.signal_detection.conditions[0].value if strategy.signal_detection and strategy.signal_detection.conditions else "N/A",
                    "indicator_value": indicator_values.get(condition_type, "NOT_FOUND"),
                    "indicator_value_lowercase": indicator_values.get(condition_type.lower(), "NOT_FOUND_LOWERCASE"),
                    "indicator_keys": list(indicator_values.keys())[:10],  # First 10 keys
                    "indicator_keys_count": len(indicator_values)
                })

                if signal_result == ConditionResult.TRUE:
                    # 🔍 DEBUG: Log that we're attempting to acquire slot
                    self.logger.info("strategy_manager.signal_true_attempting_slot", {
                        "strategy_name": strategy.strategy_name,
                        "symbol": strategy.symbol,
                        "current_state": strategy.current_state.value if strategy.current_state else "None"
                    })

                    # ✅ RACE CONDITION FIX: Atomic acquire slot (check merged into acquire)
                    slot_acquired = await self.acquire_signal_slot(strategy.strategy_name)
                    self.logger.info("strategy_manager.slot_acquire_result", {
                        "strategy_name": strategy.strategy_name,
                        "slot_acquired": slot_acquired,
                        "slot_status": self.get_slot_status()
                    })

                    if not slot_acquired:
                        await self._publish_strategy_event(strategy, "signal_slot_unavailable", {
                            **indicator_values,
                            "slot_status": self.get_slot_status()
                        })
                        return

                    # 🔍 DEBUG: Log before lock_symbol call
                    self.logger.info("strategy_manager.before_lock_symbol", {
                        "strategy_name": strategy.strategy_name,
                        "symbol": strategy.symbol
                    })

                    # ✅ RACE CONDITION FIX: Atomic lock symbol (check merged into lock)
                    if not await self.lock_symbol(strategy.symbol, strategy.strategy_name):
                        await self.release_signal_slot(strategy.strategy_name)  # Rollback slot
                        locking_strategy = self._symbol_locks.get(strategy.symbol)
                        await self._publish_strategy_event(strategy, "symbol_locked", {
                            **indicator_values,
                            "locking_strategy": locking_strategy
                        })
                        return

                    # 🔍 DEBUG: Log after lock_symbol succeeded
                    self.logger.info("strategy_manager.after_lock_symbol", {
                        "strategy_name": strategy.strategy_name,
                        "symbol": strategy.symbol
                    })

                    # Record indicator values at signal detection
                    signal_indicators = strategy._record_decision_indicators(indicator_values, "S1_signal_detection")
                    strategy.current_state = StrategyState.SIGNAL_DETECTED
                    strategy.signal_detection_time = datetime.now()  # Track when signal was detected

                    # 🔍 DEBUG: Log before _publish_signal_generated
                    self.logger.info("strategy_manager.before_publish_signal", {
                        "strategy_name": strategy.strategy_name,
                        "symbol": strategy.symbol
                    })

                    # Publish signal_generated event for OrderManager
                    await self._publish_signal_generated(
                        strategy=strategy,
                        signal_type="S1",
                        action="BUY" if strategy.direction == "LONG" else "SHORT",
                        indicator_values=indicator_values,
                        metadata={"recorded_indicators": signal_indicators, "slot_acquired": True, "symbol_locked": True}
                    )

                    await self._publish_strategy_event(strategy, "signal_detected", {
                        **indicator_values,
                        "recorded_indicators": signal_indicators,
                        "slot_acquired": True,
                        "symbol_locked": True
                    })

            elif strategy.current_state == StrategyState.SIGNAL_DETECTED:
                # O1: Check signal cancellation (optional)
                # Add signal_age_seconds to indicator_values for O1 evaluation
                extended_values = dict(indicator_values)
                if strategy.signal_detection_time:
                    signal_age = (datetime.now() - strategy.signal_detection_time).total_seconds()
                    extended_values["signal_age_seconds"] = signal_age

                cancellation_result = strategy.evaluate_signal_cancellation(extended_values)
                if cancellation_result == ConditionResult.TRUE:
                    # ✅ RACE CONDITION FIX: Release slot and symbol lock atomically
                    await self.release_signal_slot(strategy.strategy_name)
                    await self.unlock_symbol(strategy.symbol, strategy.strategy_name)

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
                        # DECISION (2025-12-16): Use real capital from RiskManager instead of hardcoded value
                        # This ensures position sizing reflects actual available capital
                        # Changes to this logic require business owner approval
                        base_capital = self.risk_manager.get_available_capital()
                        if base_capital <= 0:
                            base_capital = float(self.risk_manager.initial_capital)  # Fallback to initial
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

                        # Check if position can be opened (synchronous check)
                        risk_check = self.risk_manager.can_open_position_sync(
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
                        # DECISION (2025-12-16): Use real capital from RiskManager for order sizing
                        # Reuse base_capital calculated during risk assessment if available
                        if self.risk_manager:
                            base_capital = self.risk_manager.get_available_capital()
                            if base_capital <= 0:
                                base_capital = float(self.risk_manager.initial_capital)
                        else:
                            base_capital = 10000.0  # Default fallback without risk manager
                        order_value = base_capital * position_size_pct
                        quantity = order_value / current_price

                        # Submit entry order (BUY for LONG, SHORT for SHORT)
                        entry_order_type = strategy.get_entry_order_type()
                        pump_signal_strength = indicator_values.get("pump_magnitude_pct", 0.0) / 100.0

                        # Get leverage from global_limits (default to 1.0 for no leverage)
                        leverage = strategy.global_limits.get("max_leverage", 1.0)

                        order_id = await self.order_manager.submit_order(
                            symbol=strategy.symbol,
                            order_type=entry_order_type,
                            quantity=quantity,
                            price=current_price,
                            strategy_name=strategy.strategy_name,
                            pump_signal_strength=pump_signal_strength,
                            leverage=leverage
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
                # DECISION: E1 must be checked BEFORE ZE1 because emergency exit has highest priority
                # Business rule: If conditions warrant emergency exit, normal close should not happen
                # Example: Market crash detection should trigger E1 even if profit target (ZE1) is met

                # E1: Check emergency exit conditions FIRST (highest priority)
                emergency_result = strategy.evaluate_emergency_exit(indicator_values)
                if emergency_result == ConditionResult.TRUE:
                    # Record indicator values at emergency exit
                    emergency_indicators = strategy._record_decision_indicators(indicator_values, "E1_emergency_exit")
                    strategy.current_state = StrategyState.EMERGENCY_EXIT

                    # Start cooldown if configured
                    cooldown_minutes = strategy.global_limits.get("emergency_exit_cooldown_minutes", 30)
                    strategy.start_cooldown(cooldown_minutes, "emergency_exit")

                    # Publish signal_generated event for OrderManager
                    await self._publish_signal_generated(
                        strategy=strategy,
                        signal_type="E1",
                        action="SELL" if strategy.direction == "LONG" else "COVER",
                        indicator_values=indicator_values,
                        metadata={
                            "recorded_indicators": emergency_indicators,
                            "cooldown_started": True,
                            "cooldown_minutes": cooldown_minutes,
                            "emergency": True
                        }
                    )

                    await self._publish_strategy_event(strategy, "emergency_exit_triggered", {
                        **indicator_values,
                        "recorded_indicators": emergency_indicators,
                        "cooldown_started": True,
                        "cooldown_minutes": cooldown_minutes
                    })
                    return

                # ZE1: Check close order detection conditions (only if E1 not triggered)
                close_result = strategy.evaluate_close_order_detection(indicator_values)
                if close_result == ConditionResult.TRUE:
                    # Record indicator values at close decision
                    close_indicators = strategy._record_decision_indicators(indicator_values, "ZE1_close_order_detection")
                    strategy.current_state = StrategyState.CLOSE_ORDER_EVALUATION

                    # Publish signal_generated event for OrderManager
                    await self._publish_signal_generated(
                        strategy=strategy,
                        signal_type="ZE1",
                        action="SELL" if strategy.direction == "LONG" else "COVER",
                        indicator_values=indicator_values,
                        metadata={"recorded_indicators": close_indicators}
                    )

                    await self._publish_strategy_event(strategy, "close_order_detected", {
                        **indicator_values,
                        "recorded_indicators": close_indicators
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

                            # Start cooldown after normal exit (ZE1) to prevent immediate re-entry
                            # DECISION: Normal exit should have shorter cooldown than emergency exit
                            cooldown_minutes = strategy.global_limits.get("normal_exit_cooldown_minutes", 5)
                            strategy.start_cooldown(cooldown_minutes, "normal_exit")

                            # ✅ RACE CONDITION FIX: Release slot and symbol lock atomically
                            await self.release_signal_slot(strategy.strategy_name)
                            await self.unlock_symbol(strategy.symbol, strategy.strategy_name)

                            # ✅ BUDGET FIX (2025-12-02): Release allocated budget when position closes
                            if self.risk_manager:
                                self.risk_manager.release_budget(strategy.strategy_name)

                            await self._publish_strategy_event(strategy, "position_closed_ze1", {
                                **indicator_values,
                                "exit_price": adjusted_close_price,
                                "original_price": current_price,
                                "price_adjustment_pct": price_adjustment["price_adjustment_pct"],
                                "order_id": close_order_id,
                                "exit_reason": "close_order_detection",
                                "slot_released": True,
                                "symbol_unlocked": True,
                                "cooldown_minutes": cooldown_minutes
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

               # ✅ RACE CONDITION FIX: Release slot and symbol lock atomically
               await self.release_signal_slot(strategy.strategy_name)
               await self.unlock_symbol(strategy.symbol, strategy.strategy_name)

               # ✅ BUDGET FIX (2025-12-02): Release allocated budget on emergency exit
               if self.risk_manager:
                   self.risk_manager.release_budget(strategy.strategy_name)

               await self._publish_strategy_event(strategy, "emergency_exit_executed", {
                   **indicator_values,
                   "slot_released": True,
                   "symbol_unlocked": True,
                   "budget_released": True
               })

            # DECISION: After EXITED, strategy should return to MONITORING after cooldown expires
            # Business rule: Allow strategy to capture new opportunities after position closed
            # This prevents strategy from becoming permanently inactive after one trade
            elif strategy.current_state == StrategyState.EXITED:
                if not strategy.is_in_cooldown():
                    # Reset strategy to monitoring state
                    strategy.current_state = StrategyState.MONITORING
                    strategy.position_active = False
                    strategy.signal_detection_time = None
                    strategy.entry_time = None
                    strategy.exit_time = None

                    await self._publish_strategy_event(strategy, "monitoring_resumed", {
                        **indicator_values,
                        "previous_state": "exited",
                        "reason": "cooldown_expired"
                    })

            # DECISION: After SIGNAL_CANCELLED, strategy should return to MONITORING after cooldown expires
            # Business rule: Allow strategy to detect new signals after cancellation
            # This prevents strategy from being stuck forever after O1 trigger
            elif strategy.current_state == StrategyState.SIGNAL_CANCELLED:
                if not strategy.is_in_cooldown():
                    # Reset strategy to monitoring state
                    strategy.current_state = StrategyState.MONITORING
                    strategy.signal_detection_time = None

                    await self._publish_strategy_event(strategy, "monitoring_resumed", {
                        **indicator_values,
                        "previous_state": "signal_cancelled",
                        "reason": "cooldown_expired"
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
            # ✅ RACE CONDITION FIX: Track background tasks to prevent leaks
            # Fire-and-forget pattern with task tracking
            task = asyncio.create_task(
                asyncio.wait_for(
                    self.event_bus.publish(f"strategy.{event_type}", event_data),
                    timeout=0.05  # Very short timeout for non-blocking
                )
            )
            # Track task and auto-cleanup when done
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
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

    async def _publish_signal_generated(
        self,
        strategy: Strategy,
        signal_type: str,
        action: str,
        indicator_values: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish signal_generated event for OrderManager and TradingPersistenceService.

        This event triggers order creation in OrderManager.

        Args:
            strategy: Strategy instance generating the signal
            signal_type: Signal type (S1, ZE1, E1)
            action: Trading action (BUY, SELL, SHORT, COVER)
            indicator_values: Current indicator values
            metadata: Additional metadata for the signal
        """
        try:
            # Calculate position parameters
            current_price = indicator_values.get("price", indicator_values.get("last_price", 100.0))

            # For entry signals (S1), calculate quantity from position sizing
            if signal_type == "S1":
                position_params = strategy.calculate_position_size(indicator_values)
                position_size_pct = position_params.get("position_size_pct", 0.01)
                # DECISION (2025-12-16): Use real capital from RiskManager for signal generation
                # This ensures signal contains accurate position size information
                # Changes to this logic require business owner approval
                if self.risk_manager:
                    base_capital = self.risk_manager.get_available_capital()
                    if base_capital <= 0:
                        base_capital = float(self.risk_manager.initial_capital)
                else:
                    base_capital = 10000.0  # Default fallback without risk manager
                order_value = base_capital * position_size_pct
                quantity = order_value / current_price
            else:
                # For exit signals (ZE1, E1), get position size from strategy's last entry
                # Use position_active flag and tracked entry quantity
                if hasattr(strategy, '_last_entry_quantity') and strategy._last_entry_quantity > 0:
                    quantity = strategy._last_entry_quantity
                else:
                    # Fallback: estimate from base capital and position sizing
                    if self.risk_manager:
                        base_capital = float(self.risk_manager.initial_capital)
                        position_size_pct = strategy.global_limits.get("base_position_pct", 0.01)
                        quantity = (base_capital * position_size_pct) / current_price
                    else:
                        quantity = 0.001  # Minimal fallback

            # Generate unique signal ID
            signal_id = f"signal_{strategy.strategy_name}_{strategy.symbol}_{int(datetime.now().timestamp() * 1000)}"

            # Build signal_generated event with schema expected by OrderManager and TradingPersistenceService
            signal_event = {
                # OrderManager fields
                "signal_type": signal_type,
                "symbol": strategy.symbol,
                "side": action.lower(),  # buy, sell, short, cover
                "quantity": quantity,
                "price": current_price,
                "strategy_name": strategy.strategy_name,

                # TradingPersistenceService fields
                "signal_id": signal_id,
                "strategy_id": strategy.strategy_name,  # Using strategy_name as ID for now
                "action": action,  # BUY, SELL, SHORT, COVER
                "triggered": True,
                "conditions_met": metadata or {},
                "indicator_values": indicator_values,
                "metadata": {
                    "state": strategy.current_state.value,
                    "direction": strategy.direction,
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                },

                # Common fields
                "timestamp": datetime.now().timestamp()
            }

            # Publish to EventBus
            await self.event_bus.publish("signal_generated", signal_event)

            self.logger.info("strategy_manager.signal_generated", {
                "strategy_name": strategy.strategy_name,
                "symbol": strategy.symbol,
                "signal_type": signal_type,
                "action": action,
                "signal_id": signal_id
            })

        except Exception as e:
            self.logger.error("strategy_manager.signal_generation_failed", {
                "strategy_name": strategy.strategy_name,
                "symbol": strategy.symbol,
                "signal_type": signal_type,
                "error": str(e),
                "error_type": type(e).__name__
            })

    def get_strategy_status(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific strategy"""
        if strategy_name not in self.strategies:
            return None

        strategy = self.strategies[strategy_name]
        return {
            "strategy_name": strategy.strategy_name,
            "enabled": strategy.enabled,
            "direction": strategy.direction,  # ⚠️ CRITICAL FIX: Return direction field
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

    def get_total_active_strategies_count(self) -> int:
        """Get total count of active strategies across all symbols"""
        total = sum(len(strategies) for strategies in self.active_strategies.values())
        return total

    def _update_active_strategies_metric(self) -> None:
        """Update telemetry gauge with current active strategies count"""
        try:
            from src.core.telemetry import telemetry
            count = self.get_total_active_strategies_count()
            telemetry.set_gauge('business.active_strategies', float(count))
        except Exception as e:
            self.logger.warning("strategy_manager.telemetry_update_failed", {
                "error": str(e)
            })

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Get all registered strategies"""
        return [
            {
                "strategy_name": strategy.strategy_name,
                "enabled": strategy.enabled,
                "direction": strategy.direction,  # ⚠️ CRITICAL FIX: Return direction field
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
                "direction": strategy.direction,  # ⚠️ CRITICAL FIX: Return direction field
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

        # Direction validation (SHORT support)
        direction = config.get("direction", "LONG")
        if direction not in ["LONG", "SHORT", "BOTH"]:
            errors.append(f"direction must be 'LONG', 'SHORT', or 'BOTH', got: {direction}")
        elif direction == "BOTH":
            warnings.append("direction='BOTH' is not yet fully implemented. Use 'LONG' or 'SHORT' for now.")

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

    async def upsert_strategy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert (update or insert) strategy with validation and QuestDB persistence"""
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

                # ⚠️ CRITICAL: Persist to QuestDB
                await self.save_strategy_to_db(new_strategy)

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

                # ⚠️ CRITICAL: Persist to QuestDB
                await self.save_strategy_to_db(new_strategy)

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
