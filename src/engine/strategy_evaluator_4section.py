#!/usr/bin/env python3
"""
5-Section Strategy Evaluator
============================

Real-time strategy evaluation engine for 5-section strategies (S1/Z1/ZE1/O1/Emergency).
Implements section-based logic with symbol locking and sequence enforcement.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from src.core.event_bus import EventBus


class SignalType(Enum):
    """Trading signal types for 5-section strategies."""
    LOCK_SYMBOL = "LOCK_SYMBOL"  # S1: Lock symbol for trading
    PLACE_ORDER = "PLACE_ORDER"  # Z1: Place buy/sell order
    CLOSE_ORDER = "CLOSE_ORDER"  # ZE1: Close existing position
    UNLOCK_SYMBOL = "UNLOCK_SYMBOL"  # O1: Unlock symbol (cancel signal)
    EMERGENCY_EXIT = "EMERGENCY_EXIT"  # Emergency: Force exit all positions


class SectionState(Enum):
    """5-section strategy states."""
    IDLE = "idle"  # No active signal
    S1_ACTIVE = "s1_active"  # Signal detected, symbol locked
    Z1_ACTIVE = "z1_active"  # Order placed, position active
    ZE1_ACTIVE = "ze1_active"  # Close order conditions active
    O1_ACTIVE = "o1_active"  # Cancellation conditions active
    EMERGENCY = "emergency"  # Emergency exit triggered


@dataclass
class SymbolState:
    """State tracking for each symbol in 4-section strategy."""
    current_state: SectionState = SectionState.IDLE
    signal_start_time: Optional[datetime] = None
    order_placed_time: Optional[datetime] = None
    position_active: bool = False
    emergency_cooldown_until: Optional[datetime] = None
    last_emergency_trigger: Optional[datetime] = None


@dataclass
class Strategy4SectionSignal:
    """4-section strategy signal with section-specific data."""
    symbol: str
    signal_type: SignalType
    section: str  # 's1', 'z1', 'o1', 'emergency'
    confidence: float  # 0.0 to 1.0
    conditions_met: List[str]  # Which conditions triggered the signal
    indicator_values: Dict[str, float]  # Current indicator values
    timestamp: int
    reason: str


@dataclass
class Strategy4SectionConfig:
    """5-section strategy configuration."""
    id: str
    name: str
    s1_signal: Dict[str, Any]
    z1_entry: Dict[str, Any]
    ze1_close: Dict[str, Any]
    o1_cancel: Dict[str, Any]
    emergency_exit: Dict[str, Any]


class StrategyEvaluator4Section:
    """
    5-Section Strategy Evaluation Engine.

    Processes indicator updates through 5-section strategy logic:
    - S1 (Signal Detection): AND conditions to lock symbol
    - Z1 (Order Entry): AND conditions + order config to place orders
    - ZE1 (Order Closing): AND conditions to close existing positions
    - O1 (Cancellation): OR conditions + timeout to unlock symbol
    - Emergency Exit: OR conditions for immediate emergency actions
    """

    def __init__(self, event_bus: EventBus, strategy_config: Strategy4SectionConfig):
        self.event_bus = event_bus
        self.config = strategy_config
        self.running = False
        self.tasks: List[asyncio.Task] = []

        # Symbol state tracking
        self.symbol_states: Dict[str, SymbolState] = {}

        # Indicator state storage (latest values per symbol)
        self.indicator_state: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """Start the 4-section strategy evaluator."""
        if self.running:
            return

        self.running = True

        # Subscribe to indicator updates
        await self.event_bus.subscribe("indicator.updated", self._handle_indicator_update)

        print(f"StrategyEvaluator5Section started for strategy: {self.config.name}")

    async def stop(self) -> None:
        """Stop the 4-section strategy evaluator."""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        self.tasks = []
        print("StrategyEvaluator5Section stopped")

    async def _handle_indicator_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming indicator updates from EventBus."""
        if not isinstance(data, dict) or not self.running:
            return

        # Validate required fields
        required_fields = ["indicator", "value", "timestamp", "symbol"]
        if not all(field in data for field in required_fields):
            return

        # Extract indicator data
        indicator_name = data["indicator"]
        value = data["value"]
        timestamp = data["timestamp"]
        symbol = data["symbol"]

        # Update indicator state
        if symbol not in self.indicator_state:
            self.indicator_state[symbol] = {}

        self.indicator_state[symbol][indicator_name] = {
            "value": value,
            "timestamp": timestamp
        }

        # Evaluate strategy for this symbol
        await self._evaluate_strategy_for_symbol(symbol)

    async def _evaluate_strategy_for_symbol(self, symbol: str) -> None:
        """Evaluate 4-section strategy for a specific symbol."""
        if symbol not in self.indicator_state:
            return

        indicator_data = self.indicator_state[symbol]
        state = self.symbol_states.get(symbol, SymbolState())

        # Emergency Exit - highest priority, always checked
        emergency_signal = self._check_emergency_conditions(symbol, indicator_data, state)
        if emergency_signal:
            # Store updated state with cooldown
            self.symbol_states[symbol] = state
            await self._publish_signal(emergency_signal)
            return

        # State-based evaluation
        if state.current_state == SectionState.IDLE:
            # Check S1 conditions to lock symbol
            s1_signal = self._check_s1_conditions(symbol, indicator_data)
            if s1_signal:
                # Update state
                state.current_state = SectionState.S1_ACTIVE
                state.signal_start_time = datetime.now()
                self.symbol_states[symbol] = state

                await self._publish_signal(s1_signal)

        elif state.current_state == SectionState.S1_ACTIVE:
            # Check Z1 conditions to place order
            z1_signal = self._check_z1_conditions(symbol, indicator_data)
            if z1_signal:
                # Update state
                state.current_state = SectionState.Z1_ACTIVE
                state.order_placed_time = datetime.now()
                state.position_active = True
                self.symbol_states[symbol] = state

                await self._publish_signal(z1_signal)

            # Also check O1 conditions (can cancel signal before order)
            elif self._check_o1_conditions(symbol, indicator_data, state):
                # Reset to idle
                state.current_state = SectionState.IDLE
                state.signal_start_time = None
                self.symbol_states[symbol] = state

                unlock_signal = Strategy4SectionSignal(
                    symbol=symbol,
                    signal_type=SignalType.UNLOCK_SYMBOL,
                    section="o1",
                    confidence=1.0,
                    conditions_met=["o1_conditions"],
                    indicator_values={k: v["value"] for k, v in indicator_data.items()},
                    timestamp=int(time.time() * 1000),
                    reason="O1 cancellation conditions met"
                )
                await self._publish_signal(unlock_signal)

        elif state.current_state == SectionState.Z1_ACTIVE:
            # Check ZE1 conditions to close position
            ze1_signal = self._check_ze1_conditions(symbol, indicator_data)
            if ze1_signal:
                # Update state
                state.current_state = SectionState.ZE1_ACTIVE
                self.symbol_states[symbol] = state

                await self._publish_signal(ze1_signal)

            # Check O1 conditions to unlock symbol (can still cancel)
            elif self._check_o1_conditions(symbol, indicator_data, state):
                # Reset to idle
                state.current_state = SectionState.IDLE
                state.signal_start_time = None
                state.order_placed_time = None
                state.position_active = False
                self.symbol_states[symbol] = state

                unlock_signal = Strategy4SectionSignal(
                    symbol=symbol,
                    signal_type=SignalType.UNLOCK_SYMBOL,
                    section="o1",
                    confidence=1.0,
                    conditions_met=["o1_conditions"],
                    indicator_values={k: v["value"] for k, v in indicator_data.items()},
                    timestamp=int(time.time() * 1000),
                    reason="O1 cancellation conditions met"
                )
                await self._publish_signal(unlock_signal)

        elif state.current_state == SectionState.ZE1_ACTIVE:
            # Check O1 conditions to unlock symbol after position is closed
            if self._check_o1_conditions(symbol, indicator_data, state):
                # Reset to idle
                state.current_state = SectionState.IDLE
                state.signal_start_time = None
                state.order_placed_time = None
                state.position_active = False
                self.symbol_states[symbol] = state

                unlock_signal = Strategy4SectionSignal(
                    symbol=symbol,
                    signal_type=SignalType.UNLOCK_SYMBOL,
                    section="o1",
                    confidence=1.0,
                    conditions_met=["o1_conditions"],
                    indicator_values={k: v["value"] for k, v in indicator_data.items()},
                    timestamp=int(time.time() * 1000),
                    reason="O1 cancellation conditions met after position close"
                )
                await self._publish_signal(unlock_signal)

    def _check_emergency_conditions(self, symbol: str, indicator_data: Dict[str, Any],
                                  state: SymbolState) -> Optional[Strategy4SectionSignal]:
        """
        Check emergency exit conditions (highest priority).

        Phase 2 Sprint 1: Now supports OR/NOT/AND logic via _evaluate_conditions_with_logic
        """
        # Check cooldown period
        now = datetime.now()
        if state.emergency_cooldown_until and now < state.emergency_cooldown_until:
            return None

        emergency_config = self.config.emergency_exit
        conditions = emergency_config.get("conditions", [])

        if not conditions:
            return None

        # Phase 2: Use new logic evaluation function
        if self._evaluate_conditions_with_logic(conditions, indicator_data):
            met_conditions = [cond.get("id", f"condition_{i}") for i, cond in enumerate(conditions)]

            # Update cooldown
            cooldown_minutes = emergency_config.get("cooldownMinutes", 60)
            state.emergency_cooldown_until = now + timedelta(minutes=cooldown_minutes)
            state.last_emergency_trigger = now

            return Strategy4SectionSignal(
                symbol=symbol,
                signal_type=SignalType.EMERGENCY_EXIT,
                section="emergency",
                confidence=1.0,
                conditions_met=met_conditions,
                indicator_values={k: v["value"] for k, v in indicator_data.items()},
                timestamp=int(time.time() * 1000),
                reason=f"Emergency conditions met: {len(conditions)} conditions evaluated to TRUE"
            )

        return None

    def _check_s1_conditions(self, symbol: str, indicator_data: Dict[str, Any]) -> Optional[Strategy4SectionSignal]:
        """
        Check S1 signal detection conditions.

        Phase 2 Sprint 1: Now supports OR/NOT/AND logic via _evaluate_conditions_with_logic
        """
        s1_config = self.config.s1_signal
        conditions = s1_config.get("conditions", [])

        if not conditions:
            return None

        # Phase 2: Use new logic evaluation function
        if self._evaluate_conditions_with_logic(conditions, indicator_data):
            met_conditions = [cond.get("id", f"condition_{i}") for i, cond in enumerate(conditions)]

            return Strategy4SectionSignal(
                symbol=symbol,
                signal_type=SignalType.LOCK_SYMBOL,
                section="s1",
                confidence=1.0,
                conditions_met=met_conditions,
                indicator_values={k: v["value"] for k, v in indicator_data.items()},
                timestamp=int(time.time() * 1000),
                reason=f"S1 signal detected: {len(conditions)} conditions evaluated to TRUE"
            )

        return None

    def _check_z1_conditions(self, symbol: str, indicator_data: Dict[str, Any]) -> Optional[Strategy4SectionSignal]:
        """
        Check Z1 order entry conditions.

        Phase 2 Sprint 1: Now supports OR/NOT/AND logic via _evaluate_conditions_with_logic
        """
        z1_config = self.config.z1_entry
        conditions = z1_config.get("conditions", [])

        if not conditions:
            return None

        # Phase 2: Use new logic evaluation function
        if self._evaluate_conditions_with_logic(conditions, indicator_data):
            met_conditions = [cond.get("id", f"condition_{i}") for i, cond in enumerate(conditions)]

            return Strategy4SectionSignal(
                symbol=symbol,
                signal_type=SignalType.PLACE_ORDER,
                section="z1",
                confidence=1.0,
                conditions_met=met_conditions,
                indicator_values={k: v["value"] for k, v in indicator_data.items()},
                timestamp=int(time.time() * 1000),
                reason=f"Z1 order entry: {len(conditions)} conditions evaluated to TRUE"
            )

        return None

    def _check_ze1_conditions(self, symbol: str, indicator_data: Dict[str, Any]) -> Optional[Strategy4SectionSignal]:
        """
        Check ZE1 order closing conditions.

        Phase 2 Sprint 1: Now supports OR/NOT/AND logic via _evaluate_conditions_with_logic
        """
        ze1_config = self.config.ze1_close
        conditions = ze1_config.get("conditions", [])

        if not conditions:
            return None

        # Phase 2: Use new logic evaluation function
        if self._evaluate_conditions_with_logic(conditions, indicator_data):
            met_conditions = [cond.get("id", f"condition_{i}") for i, cond in enumerate(conditions)]

            return Strategy4SectionSignal(
                symbol=symbol,
                signal_type=SignalType.CLOSE_ORDER,
                section="ze1",
                confidence=1.0,
                conditions_met=met_conditions,
                indicator_values={k: v["value"] for k, v in indicator_data.items()},
                timestamp=int(time.time() * 1000),
                reason=f"ZE1 order close: {len(conditions)} conditions evaluated to TRUE"
            )

        return None

    def _check_o1_conditions(self, symbol: str, indicator_data: Dict[str, Any], state: SymbolState) -> bool:
        """
        Check O1 cancellation conditions.

        Phase 2 Sprint 1: Now supports OR/NOT/AND logic via _evaluate_conditions_with_logic
        """
        o1_config = self.config.o1_cancel
        conditions = o1_config.get("conditions", [])
        timeout_seconds = o1_config.get("timeoutSeconds", 300)  # 5 minutes default

        # Check timeout
        if state.signal_start_time:
            elapsed = (datetime.now() - state.signal_start_time).total_seconds()
            if elapsed >= timeout_seconds:
                return True

        # Phase 2: Use new logic evaluation function for conditions
        if conditions and self._evaluate_conditions_with_logic(conditions, indicator_data):
            return True

        return False

    def _evaluate_conditions_with_logic(self, conditions: List[Dict[str, Any]], indicator_data: Dict[str, Any]) -> bool:
        """
        Evaluate list of conditions with OR/NOT/AND logic support.

        Phase 2 Sprint 1: New function for complex logic evaluation.

        Logic rules:
        - Each condition has optional 'logic' field: 'AND' (default), 'OR', 'NOT'
        - Logic connector applies to NEXT condition
        - NOT inverts the result of current condition
        - Evaluation order: left to right with short-circuit

        Examples:
        - [A, B, C] with no logic = A AND B AND C
        - [A(OR), B, C] = A OR (B AND C)
        - [A, B(NOT), C] = A AND (NOT B) AND C
        - [A(OR), B(NOT), C] = A OR (NOT B) AND C
        """
        if not conditions:
            return True

        result = True
        next_logic = 'AND'  # Start with AND

        for i, condition in enumerate(conditions):
            # Evaluate this condition
            cond_result = self._evaluate_condition(condition, indicator_data)

            # Get logic operator for this condition (applies to next)
            current_logic = condition.get('logic', 'AND')

            # Apply NOT if current logic is NOT
            if current_logic == 'NOT':
                cond_result = not cond_result

            # Combine with previous result using next_logic
            if i == 0:
                result = cond_result
            else:
                if next_logic == 'AND':
                    result = result and cond_result
                    if not result:  # Short-circuit AND
                        return False
                elif next_logic == 'OR':
                    result = result or cond_result
                    if result:  # Short-circuit OR
                        return True
                elif next_logic == 'NOT':
                    # NOT was already applied above
                    result = result and cond_result

            # Set next logic operator (from current condition)
            if current_logic in ['AND', 'OR']:
                next_logic = current_logic
            # If current is NOT, keep previous next_logic

        return result

    def _evaluate_condition(self, condition: Dict[str, Any], indicator_data: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition against indicator data.

        Phase 2 Sprint 1: Added support for '==' operator.
        """
        indicator_id = condition.get("indicatorId")
        operator = condition.get("operator")
        value = condition.get("value")

        # Phase 2: Support '==' operator
        if not indicator_id or operator not in [">", "<", ">=", "<=", "=="]:
            return False

        # Get indicator value
        if indicator_id not in indicator_data:
            return False

        indicator_value = indicator_data[indicator_id]["value"]

        # Evaluate condition
        if operator == ">":
            return indicator_value > value
        elif operator == "<":
            return indicator_value < value
        elif operator == ">=":
            return indicator_value >= value
        elif operator == "<=":
            return indicator_value <= value
        elif operator == "==":
            # Phase 2: Equality comparison (with small epsilon for floating point)
            return abs(indicator_value - value) < 1e-9

        return False

    async def _publish_signal(self, signal: Strategy4SectionSignal) -> None:
        """Publish 4-section strategy signal via EventBus."""
        signal_data = {
            "type": "strategy_4section_signal",
            "strategy_id": self.config.id,
            "strategy_name": self.config.name,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type.value,
            "section": signal.section,
            "confidence": signal.confidence,
            "conditions_met": signal.conditions_met,
            "indicator_values": signal.indicator_values,
            "timestamp": signal.timestamp,
            "reason": signal.reason
        }

        await self.event_bus.publish("strategy.4section.signal", signal_data)

    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current 5-section strategy evaluation status."""
        return {
            "strategy_id": self.config.id,
            "strategy_name": self.config.name,
            "active_symbols": list(self.symbol_states.keys()),
            "symbol_states": {
                symbol: {
                    "state": state.current_state.value,
                    "signal_start_time": state.signal_start_time.isoformat() if state.signal_start_time else None,
                    "position_active": state.position_active
                }
                for symbol, state in self.symbol_states.items()
            },
            "indicator_counts": {symbol: len(data) for symbol, data in self.indicator_state.items()},
            "last_evaluation": int(time.time() * 1000)
        }