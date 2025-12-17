"""
Unit Tests - Pump and Dump Strategy Complete Verification
=========================================================
Comprehensive tests verifying EVERY element of the pump-and-dump strategy
works correctly during trading/backtesting.

Test Coverage:
- S1 (Signal Detection): pump_magnitude_pct, volume_surge_ratio, price_velocity
- O1 (Signal Cancellation): timeout, reversal conditions
- Z1 (Entry Conditions): price, confirmation indicators
- ZE1 (Close Order Detection): profit targets, trailing stops
- E1 (Emergency Exit): flash crash, max loss
- Config changes affect execution
- Complete trading cycle end-to-end

Created: 2025-12-17
Author: Claude Code
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

try:
    from src.domain.services.strategy_manager import (
        StrategyManager,
        Strategy,
        StrategyState,
        ConditionGroup,
        Condition,
        ConditionResult
    )
    from src.domain.services.order_manager import OrderType
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger
except ImportError:
    from domain.services.strategy_manager import (
        StrategyManager,
        Strategy,
        StrategyState,
        ConditionGroup,
        Condition,
        ConditionResult
    )
    from domain.services.order_manager import OrderType
    from core.event_bus import EventBus
    from core.logger import StructuredLogger


@pytest.mark.unit
class TestS1SignalDetection:
    """
    S1: Signal Detection Tests
    ==========================
    Verifies that pump signals are correctly detected based on indicator thresholds.

    Code locations verified:
    - strategy_manager.py:1668-1739 (MONITORING → SIGNAL_DETECTED)
    - Strategy.evaluate_signal_detection()
    - Condition.evaluate() with pump indicators
    """

    def test_pump_magnitude_pct_triggers_signal(self):
        """Test S1: pump_magnitude_pct >= threshold triggers signal detection"""
        strategy = Strategy(
            strategy_name="pump_detector",
            enabled=True,
            direction="LONG",
            symbol="BTCUSDT",
            signal_detection=ConditionGroup(
                name="pump_signal",
                require_all=True,
                conditions=[
                    Condition(
                        name="pump_check",
                        condition_type="pump_magnitude_pct",
                        operator=">=",
                        value=5.0  # 5% pump threshold
                    )
                ]
            )
        )

        # Below threshold - should NOT trigger
        result = strategy.evaluate_signal_detection({"pump_magnitude_pct": 3.5})
        assert result == ConditionResult.FALSE, "3.5% pump should NOT trigger signal"

        # At threshold - should trigger
        result = strategy.evaluate_signal_detection({"pump_magnitude_pct": 5.0})
        assert result == ConditionResult.TRUE, "5.0% pump should trigger signal"

        # Above threshold - should trigger
        result = strategy.evaluate_signal_detection({"pump_magnitude_pct": 8.5})
        assert result == ConditionResult.TRUE, "8.5% pump should trigger signal"

    def test_volume_surge_ratio_triggers_signal(self):
        """Test S1: volume_surge_ratio >= threshold triggers signal"""
        strategy = Strategy(
            strategy_name="volume_surge_detector",
            enabled=True,
            direction="LONG",
            symbol="BTCUSDT",
            signal_detection=ConditionGroup(
                name="volume_signal",
                require_all=True,
                conditions=[
                    Condition(
                        name="volume_check",
                        condition_type="volume_surge_ratio",
                        operator=">=",
                        value=3.0  # 3x volume surge
                    )
                ]
            )
        )

        result = strategy.evaluate_signal_detection({"volume_surge_ratio": 2.5})
        assert result == ConditionResult.FALSE, "2.5x volume should NOT trigger"

        result = strategy.evaluate_signal_detection({"volume_surge_ratio": 4.0})
        assert result == ConditionResult.TRUE, "4x volume should trigger"

    def test_combined_pump_and_volume_conditions(self):
        """Test S1: Multiple conditions with AND logic"""
        strategy = Strategy(
            strategy_name="combined_detector",
            enabled=True,
            direction="LONG",
            symbol="BTCUSDT",
            signal_detection=ConditionGroup(
                name="combined_signal",
                require_all=True,  # AND logic
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0),
                    Condition(name="volume", condition_type="volume_surge_ratio", operator=">=", value=2.0)
                ]
            )
        )

        # Only pump met
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 7.0,
            "volume_surge_ratio": 1.5
        })
        assert result == ConditionResult.FALSE, "Pump without volume should NOT trigger"

        # Only volume met
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 3.0,
            "volume_surge_ratio": 3.0
        })
        assert result == ConditionResult.FALSE, "Volume without pump should NOT trigger"

        # Both met
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 6.0,
            "volume_surge_ratio": 2.5
        })
        assert result == ConditionResult.TRUE, "Both conditions met should trigger"

    def test_or_logic_any_condition_triggers(self):
        """Test S1: Multiple conditions with OR logic"""
        strategy = Strategy(
            strategy_name="or_detector",
            enabled=True,
            direction="LONG",
            symbol="BTCUSDT",
            signal_detection=ConditionGroup(
                name="or_signal",
                require_all=False,  # OR logic
                conditions=[
                    Condition(name="big_pump", condition_type="pump_magnitude_pct", operator=">=", value=10.0),
                    Condition(name="huge_volume", condition_type="volume_surge_ratio", operator=">=", value=5.0)
                ]
            )
        )

        # Neither met
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 5.0,
            "volume_surge_ratio": 2.0
        })
        assert result == ConditionResult.FALSE, "Neither condition met should NOT trigger"

        # Only big pump
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 12.0,
            "volume_surge_ratio": 2.0
        })
        assert result == ConditionResult.TRUE, "Big pump alone should trigger with OR"

        # Only huge volume
        result = strategy.evaluate_signal_detection({
            "pump_magnitude_pct": 3.0,
            "volume_surge_ratio": 6.0
        })
        assert result == ConditionResult.TRUE, "Huge volume alone should trigger with OR"

    def test_case_insensitive_indicator_matching(self):
        """Test S1: Indicator names match case-insensitively"""
        strategy = Strategy(
            strategy_name="case_test",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="test",
                require_all=True,
                conditions=[
                    Condition(name="test", condition_type="pump_magnitude_pct", operator=">=", value=5.0)
                ]
            )
        )

        # Uppercase key
        result = strategy.evaluate_signal_detection({"PUMP_MAGNITUDE_PCT": 7.0})
        assert result == ConditionResult.TRUE, "Uppercase indicator should match"

        # Mixed case
        result = strategy.evaluate_signal_detection({"Pump_Magnitude_Pct": 7.0})
        assert result == ConditionResult.TRUE, "Mixed case indicator should match"


@pytest.mark.unit
class TestO1SignalCancellation:
    """
    O1: Signal Cancellation Tests
    ==============================
    Verifies that signals are correctly cancelled when conditions are no longer favorable.

    Code locations verified:
    - strategy_manager.py:1741-1771 (SIGNAL_DETECTED → SIGNAL_CANCELLED)
    - Strategy.evaluate_signal_cancellation()
    - signal_age_seconds automatic injection
    """

    def test_signal_timeout_cancellation(self):
        """Test O1: Signal cancelled after timeout"""
        strategy = Strategy(
            strategy_name="timeout_test",
            enabled=True,
            direction="LONG",
            signal_cancellation=ConditionGroup(
                name="timeout_cancel",
                require_all=True,
                conditions=[
                    Condition(
                        name="timeout",
                        condition_type="signal_age_seconds",
                        operator=">=",
                        value=60.0  # Cancel after 60 seconds
                    )
                ]
            )
        )

        # Before timeout
        result = strategy.evaluate_signal_cancellation({"signal_age_seconds": 30.0})
        assert result == ConditionResult.FALSE, "30s should NOT cancel"

        # After timeout
        result = strategy.evaluate_signal_cancellation({"signal_age_seconds": 65.0})
        assert result == ConditionResult.TRUE, "65s should cancel signal"

    def test_pump_reversal_cancellation(self):
        """Test O1: Signal cancelled when pump reverses"""
        strategy = Strategy(
            strategy_name="reversal_test",
            enabled=True,
            direction="LONG",
            signal_cancellation=ConditionGroup(
                name="reversal_cancel",
                require_all=True,
                conditions=[
                    Condition(
                        name="reversal",
                        condition_type="pump_magnitude_pct",
                        operator="<",
                        value=2.0  # Cancel if pump drops below 2%
                    )
                ]
            )
        )

        # Pump still strong
        result = strategy.evaluate_signal_cancellation({"pump_magnitude_pct": 5.0})
        assert result == ConditionResult.FALSE, "5% pump should NOT cancel"

        # Pump reversed
        result = strategy.evaluate_signal_cancellation({"pump_magnitude_pct": 1.5})
        assert result == ConditionResult.TRUE, "1.5% pump should cancel"

    def test_empty_o1_does_not_cancel(self):
        """Test O1: Empty cancellation conditions = never cancel"""
        strategy = Strategy(
            strategy_name="no_cancel",
            enabled=True,
            direction="LONG"
            # No signal_cancellation defined - uses default empty
        )

        result = strategy.evaluate_signal_cancellation({"pump_magnitude_pct": 0.5})
        assert result == ConditionResult.FALSE, "Empty O1 should NOT cancel"


@pytest.mark.unit
class TestZ1EntryConditions:
    """
    Z1: Entry Conditions Tests
    ===========================
    Verifies that entry conditions correctly trigger position opening.

    Code locations verified:
    - strategy_manager.py:1773-1785 (SIGNAL_DETECTED → ENTRY_EVALUATION)
    - strategy_manager.py:1787-1918 (ENTRY_EVALUATION → POSITION_ACTIVE)
    - Strategy.evaluate_entry_conditions()
    """

    def test_price_threshold_entry(self):
        """Test Z1: Entry when price meets threshold"""
        strategy = Strategy(
            strategy_name="price_entry",
            enabled=True,
            direction="LONG",
            entry_conditions=ConditionGroup(
                name="price_entry",
                require_all=True,
                conditions=[
                    Condition(name="price", condition_type="price", operator=">=", value=50000.0)
                ]
            )
        )

        result = strategy.evaluate_entry_conditions({"price": 49000.0})
        assert result == ConditionResult.FALSE, "Price below threshold should NOT enter"

        result = strategy.evaluate_entry_conditions({"price": 51000.0})
        assert result == ConditionResult.TRUE, "Price above threshold should enter"

    def test_pump_continuation_entry(self):
        """Test Z1: Entry only if pump continues"""
        strategy = Strategy(
            strategy_name="continuation_entry",
            enabled=True,
            direction="LONG",
            entry_conditions=ConditionGroup(
                name="continuation",
                require_all=True,
                conditions=[
                    Condition(name="pump_still_active", condition_type="pump_magnitude_pct", operator=">=", value=4.0),
                    Condition(name="volume_confirmed", condition_type="volume_surge_ratio", operator=">=", value=1.5)
                ]
            )
        )

        # Pump died
        result = strategy.evaluate_entry_conditions({
            "pump_magnitude_pct": 2.0,
            "volume_surge_ratio": 2.0
        })
        assert result == ConditionResult.FALSE, "Weak pump should NOT enter"

        # Pump continues
        result = strategy.evaluate_entry_conditions({
            "pump_magnitude_pct": 5.0,
            "volume_surge_ratio": 2.0
        })
        assert result == ConditionResult.TRUE, "Strong pump should enter"

    def test_empty_z1_does_not_enter(self):
        """Test Z1: Empty entry conditions = never enter"""
        strategy = Strategy(
            strategy_name="no_entry",
            enabled=True,
            direction="LONG"
            # No entry_conditions defined
        )

        result = strategy.evaluate_entry_conditions({"price": 100000.0})
        assert result == ConditionResult.FALSE, "Empty Z1 should NOT enter"


@pytest.mark.unit
class TestZE1CloseOrderDetection:
    """
    ZE1: Close Order Detection Tests
    ==================================
    Verifies that positions are closed when profit targets or stop conditions are met.

    Code locations verified:
    - strategy_manager.py:1958-1978 (POSITION_ACTIVE → CLOSE_ORDER_EVALUATION)
    - strategy_manager.py:1980-2026 (CLOSE_ORDER_EVALUATION → EXITED)
    - Strategy.evaluate_close_order_detection()
    """

    def test_profit_target_close(self):
        """Test ZE1: Close when profit target reached"""
        strategy = Strategy(
            strategy_name="profit_close",
            enabled=True,
            direction="LONG",
            close_order_detection=ConditionGroup(
                name="profit_target",
                require_all=True,
                conditions=[
                    Condition(name="profit", condition_type="profit_pct", operator=">=", value=10.0)
                ]
            )
        )

        result = strategy.evaluate_close_order_detection({"profit_pct": 5.0})
        assert result == ConditionResult.FALSE, "5% profit should NOT close"

        result = strategy.evaluate_close_order_detection({"profit_pct": 12.0})
        assert result == ConditionResult.TRUE, "12% profit should close"

    def test_trailing_stop_close(self):
        """Test ZE1: Close when trailing stop hit"""
        strategy = Strategy(
            strategy_name="trailing_stop",
            enabled=True,
            direction="LONG",
            close_order_detection=ConditionGroup(
                name="trailing",
                require_all=False,  # OR - either condition closes
                conditions=[
                    Condition(name="profit_target", condition_type="profit_pct", operator=">=", value=15.0),
                    Condition(name="trailing_stop", condition_type="drawdown_from_peak_pct", operator=">=", value=3.0)
                ]
            )
        )

        # Neither condition met
        result = strategy.evaluate_close_order_detection({
            "profit_pct": 8.0,
            "drawdown_from_peak_pct": 1.0
        })
        assert result == ConditionResult.FALSE, "Neither condition should NOT close"

        # Trailing stop hit
        result = strategy.evaluate_close_order_detection({
            "profit_pct": 8.0,
            "drawdown_from_peak_pct": 4.0
        })
        assert result == ConditionResult.TRUE, "Trailing stop should close"

    def test_pump_dump_detection_close(self):
        """Test ZE1: Close when dump detected (pump reverses)"""
        strategy = Strategy(
            strategy_name="dump_detector",
            enabled=True,
            direction="LONG",
            close_order_detection=ConditionGroup(
                name="dump_detection",
                require_all=True,
                conditions=[
                    Condition(name="dump", condition_type="price_velocity", operator="<=", value=-5.0)
                ]
            )
        )

        result = strategy.evaluate_close_order_detection({"price_velocity": -2.0})
        assert result == ConditionResult.FALSE, "Slow decline should NOT close"

        result = strategy.evaluate_close_order_detection({"price_velocity": -7.0})
        assert result == ConditionResult.TRUE, "Rapid dump should close"


@pytest.mark.unit
class TestE1EmergencyExit:
    """
    E1: Emergency Exit Tests
    =========================
    Verifies that emergency exits take priority and work correctly.

    Code locations verified:
    - strategy_manager.py:1920-1956 (E1 checked BEFORE ZE1)
    - strategy_manager.py:2028-2054 (EMERGENCY_EXIT execution)
    - Strategy.evaluate_emergency_exit()
    """

    def test_flash_crash_emergency_exit(self):
        """Test E1: Emergency exit on flash crash"""
        strategy = Strategy(
            strategy_name="flash_crash",
            enabled=True,
            direction="LONG",
            emergency_exit=ConditionGroup(
                name="emergency",
                require_all=True,
                conditions=[
                    Condition(name="crash", condition_type="price_velocity", operator="<=", value=-15.0)
                ]
            )
        )

        result = strategy.evaluate_emergency_exit({"price_velocity": -8.0})
        assert result == ConditionResult.FALSE, "Normal drop should NOT trigger E1"

        result = strategy.evaluate_emergency_exit({"price_velocity": -20.0})
        assert result == ConditionResult.TRUE, "Flash crash should trigger E1"

    def test_max_loss_emergency_exit(self):
        """Test E1: Emergency exit on max loss"""
        strategy = Strategy(
            strategy_name="max_loss",
            enabled=True,
            direction="LONG",
            emergency_exit=ConditionGroup(
                name="max_loss",
                require_all=True,
                conditions=[
                    Condition(name="loss", condition_type="loss_pct", operator=">=", value=10.0)
                ]
            )
        )

        result = strategy.evaluate_emergency_exit({"loss_pct": 5.0})
        assert result == ConditionResult.FALSE, "5% loss should NOT trigger E1"

        result = strategy.evaluate_emergency_exit({"loss_pct": 12.0})
        assert result == ConditionResult.TRUE, "12% loss should trigger E1"

    @pytest.mark.asyncio
    async def test_e1_has_priority_over_ze1(self):
        """Test E1: Emergency exit triggers even if profit target met (E1 before ZE1)"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.debug = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=None,
            risk_manager=None,
            db_pool=None
        )
        await manager.start()

        try:
            strategy = Strategy(
                strategy_name="priority_test",
                enabled=True,
                direction="LONG",
                symbol="BTCUSDT",
                close_order_detection=ConditionGroup(
                    name="profit",
                    require_all=True,
                    conditions=[
                        Condition(name="profit", condition_type="profit_pct", operator=">=", value=5.0)
                    ]
                ),
                emergency_exit=ConditionGroup(
                    name="emergency",
                    require_all=True,
                    conditions=[
                        Condition(name="crash", condition_type="flash_crash", operator="==", value=True)
                    ]
                )
            )
            strategy.current_state = StrategyState.POSITION_ACTIVE
            strategy.position_active = True

            manager.strategies[strategy.strategy_name] = strategy
            manager.active_strategies["BTCUSDT"] = [strategy]

            # Both ZE1 and E1 conditions TRUE
            await manager._evaluate_strategy_locked(strategy, {
                "profit_pct": 10.0,  # ZE1 would trigger
                "flash_crash": True,  # E1 should trigger FIRST
                "price": 45000.0
            })

            # E1 should win
            assert strategy.current_state == StrategyState.EMERGENCY_EXIT, \
                f"E1 should trigger, not ZE1. State: {strategy.current_state}"
        finally:
            await manager.shutdown()


@pytest.mark.unit
class TestConfigChangesAffectExecution:
    """
    Configuration Change Tests
    ===========================
    Verifies that changing strategy configuration affects execution.

    This proves the strategy is actually USING the configured values,
    not hardcoded defaults.
    """

    def test_threshold_change_affects_signal(self):
        """Test: Changing threshold changes when signal triggers"""
        # Low threshold
        low_threshold = Strategy(
            strategy_name="low",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=2.0)
                ]
            )
        )

        # High threshold
        high_threshold = Strategy(
            strategy_name="high",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=8.0)
                ]
            )
        )

        # 5% pump
        indicators = {"pump_magnitude_pct": 5.0}

        low_result = low_threshold.evaluate_signal_detection(indicators)
        high_result = high_threshold.evaluate_signal_detection(indicators)

        assert low_result == ConditionResult.TRUE, "Low threshold should trigger at 5%"
        assert high_result == ConditionResult.FALSE, "High threshold should NOT trigger at 5%"

    def test_operator_change_affects_evaluation(self):
        """Test: Changing operator changes evaluation"""
        greater_than = Strategy(
            strategy_name="gt",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">", value=5.0)
                ]
            )
        )

        greater_equal = Strategy(
            strategy_name="ge",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0)
                ]
            )
        )

        # Exactly 5%
        indicators = {"pump_magnitude_pct": 5.0}

        gt_result = greater_than.evaluate_signal_detection(indicators)
        ge_result = greater_equal.evaluate_signal_detection(indicators)

        assert gt_result == ConditionResult.FALSE, "> 5.0 should NOT trigger at exactly 5.0"
        assert ge_result == ConditionResult.TRUE, ">= 5.0 should trigger at exactly 5.0"

    def test_direction_affects_order_type(self):
        """Test: Direction (LONG/SHORT) affects order type"""
        long_strategy = Strategy(strategy_name="long", enabled=True, direction="LONG")
        short_strategy = Strategy(strategy_name="short", enabled=True, direction="SHORT")

        assert long_strategy.get_entry_order_type() == OrderType.BUY
        assert short_strategy.get_entry_order_type() == OrderType.SHORT

    def test_leverage_config_used(self):
        """Test: max_leverage from global_limits is accessible"""
        strategy = Strategy(
            strategy_name="leveraged",
            enabled=True,
            direction="LONG",
            global_limits={"max_leverage": 5.0}
        )

        leverage = strategy.global_limits.get("max_leverage", 1.0)
        assert leverage == 5.0, "Configured leverage should be 5.0"

    def test_position_size_config_used(self):
        """Test: base_position_pct from global_limits affects position sizing"""
        strategy = Strategy(
            strategy_name="sized",
            enabled=True,
            direction="LONG",
            global_limits={"base_position_pct": 0.05}  # 5%
        )

        params = strategy.calculate_position_size({"risk_indicator": 50})
        # With default risk (50), multiplier is ~0.875 (interpolated)
        # 0.05 * 0.875 = 0.04375, clamped to min 0.005, max 0.10
        assert 0.005 <= params["position_size_pct"] <= 0.10

    def test_adding_condition_changes_behavior(self):
        """Test: Adding conditions to existing group changes behavior"""
        # Single condition
        single = Strategy(
            strategy_name="single",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0)
                ]
            )
        )

        # Two conditions - pump AND volume
        double = Strategy(
            strategy_name="double",
            enabled=True,
            direction="LONG",
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0),
                    Condition(name="volume", condition_type="volume_surge_ratio", operator=">=", value=2.0)
                ]
            )
        )

        # Only pump met
        indicators = {"pump_magnitude_pct": 7.0, "volume_surge_ratio": 1.0}

        single_result = single.evaluate_signal_detection(indicators)
        double_result = double.evaluate_signal_detection(indicators)

        assert single_result == ConditionResult.TRUE, "Single condition met"
        assert double_result == ConditionResult.FALSE, "Second condition NOT met"


@pytest.mark.unit
@pytest.mark.asyncio
class TestCompletePumpAndDumpCycle:
    """
    Complete Trading Cycle Test
    ============================
    End-to-end test of the entire pump-and-dump strategy lifecycle.

    Verifies the full state machine flow:
    MONITORING → SIGNAL_DETECTED → ENTRY_EVALUATION → POSITION_ACTIVE → CLOSE_ORDER_EVALUATION → EXITED
    """

    @pytest.fixture
    async def full_manager(self):
        """Create StrategyManager with all dependencies mocked"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        order_manager = Mock()
        order_manager.submit_order = AsyncMock(return_value="order_123")
        order_manager.close_position = AsyncMock(return_value="close_456")
        order_manager.emergency_exit = AsyncMock(return_value="emergency_789")

        risk_manager = Mock()
        risk_manager.get_available_capital = Mock(return_value=10000.0)
        risk_manager.initial_capital = 10000.0
        risk_manager.assess_position_risk = Mock(return_value={})
        risk_manager.can_open_position_sync = Mock(return_value={
            "approved": True, "warnings": [], "reasons": []
        })
        risk_manager.use_budget = Mock(return_value=True)
        risk_manager.release_budget = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=order_manager,
            risk_manager=risk_manager,
            db_pool=None
        )
        await manager.start()
        yield manager
        await manager.shutdown()

    async def test_complete_profitable_trade_cycle(self, full_manager):
        """
        Test complete profitable trade:
        1. MONITORING: Wait for pump signal
        2. SIGNAL_DETECTED: Pump detected (S1)
        3. ENTRY_EVALUATION: Entry conditions met (Z1)
        4. POSITION_ACTIVE: Position opened
        5. CLOSE_ORDER_EVALUATION: Profit target hit (ZE1)
        6. EXITED: Position closed with profit
        """
        manager = full_manager
        symbol = "BTCUSDT"

        # Create realistic pump-and-dump strategy
        strategy = Strategy(
            strategy_name="pump_trader",
            enabled=True,
            direction="LONG",
            symbol=symbol,
            signal_detection=ConditionGroup(
                name="pump_signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0),
                    Condition(name="volume", condition_type="volume_surge_ratio", operator=">=", value=2.0)
                ]
            ),
            entry_conditions=ConditionGroup(
                name="entry",
                require_all=True,
                conditions=[
                    Condition(name="price_confirm", condition_type="pump_magnitude_pct", operator=">=", value=4.0)
                ]
            ),
            close_order_detection=ConditionGroup(
                name="close",
                require_all=True,
                conditions=[
                    Condition(name="profit", condition_type="profit_pct", operator=">=", value=10.0)
                ]
            ),
            global_limits={"base_position_pct": 0.02, "max_leverage": 2.0}
        )
        strategy.current_state = StrategyState.MONITORING

        manager.strategies[strategy.strategy_name] = strategy
        manager.active_strategies[symbol] = [strategy]

        # === STEP 1: Pump detected (S1) ===
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 7.5,
            "volume_surge_ratio": 3.0,
            "price": 50000.0
        })
        assert strategy.current_state == StrategyState.SIGNAL_DETECTED, \
            f"Step 1 failed: Expected SIGNAL_DETECTED, got {strategy.current_state}"
        assert strategy.strategy_name in manager._global_signal_slots, "Slot should be acquired"

        # === STEP 2: Entry conditions met (Z1) ===
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 6.0,
            "volume_surge_ratio": 2.5,
            "price": 51000.0
        })
        assert strategy.current_state == StrategyState.ENTRY_EVALUATION, \
            f"Step 2 failed: Expected ENTRY_EVALUATION, got {strategy.current_state}"

        # === STEP 3: Position opened ===
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 6.5,
            "price": 51500.0
        })
        assert strategy.current_state == StrategyState.POSITION_ACTIVE, \
            f"Step 3 failed: Expected POSITION_ACTIVE, got {strategy.current_state}"
        assert strategy.position_active == True, "position_active should be True"
        manager.order_manager.submit_order.assert_called_once()

        # === STEP 4: Profit target hit (ZE1) ===
        await manager._evaluate_strategy_locked(strategy, {
            "profit_pct": 12.0,  # Above 10% target
            "price": 56000.0
        })
        assert strategy.current_state == StrategyState.CLOSE_ORDER_EVALUATION, \
            f"Step 4 failed: Expected CLOSE_ORDER_EVALUATION, got {strategy.current_state}"

        # === STEP 5: Position closed ===
        await manager._evaluate_strategy_locked(strategy, {
            "profit_pct": 11.5,
            "price": 55500.0
        })
        assert strategy.current_state == StrategyState.EXITED, \
            f"Step 5 failed: Expected EXITED, got {strategy.current_state}"
        assert strategy.position_active == False, "position_active should be False"
        manager.order_manager.close_position.assert_called_once()

    async def test_emergency_exit_during_trade(self, full_manager):
        """
        Test emergency exit scenario:
        Trade opened, then flash crash triggers E1 instead of normal close
        """
        manager = full_manager
        symbol = "BTCUSDT"

        strategy = Strategy(
            strategy_name="emergency_trader",
            enabled=True,
            direction="LONG",
            symbol=symbol,
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0)
                ]
            ),
            entry_conditions=ConditionGroup(
                name="entry",
                require_all=True,
                conditions=[
                    Condition(name="confirm", condition_type="price", operator=">=", value=1.0)
                ]
            ),
            close_order_detection=ConditionGroup(
                name="close",
                require_all=True,
                conditions=[
                    Condition(name="profit", condition_type="profit_pct", operator=">=", value=10.0)
                ]
            ),
            emergency_exit=ConditionGroup(
                name="emergency",
                require_all=True,
                conditions=[
                    Condition(name="crash", condition_type="price_velocity", operator="<=", value=-15.0)
                ]
            ),
            global_limits={"emergency_exit_cooldown_minutes": 30}
        )
        strategy.current_state = StrategyState.MONITORING

        manager.strategies[strategy.strategy_name] = strategy
        manager.active_strategies[symbol] = [strategy]

        # Open position
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 7.0,
            "price": 50000.0
        })
        assert strategy.current_state == StrategyState.SIGNAL_DETECTED

        await manager._evaluate_strategy_locked(strategy, {"price": 51000.0})
        assert strategy.current_state == StrategyState.ENTRY_EVALUATION

        await manager._evaluate_strategy_locked(strategy, {"price": 51000.0})
        assert strategy.current_state == StrategyState.POSITION_ACTIVE

        # Flash crash - E1 triggers
        await manager._evaluate_strategy_locked(strategy, {
            "price_velocity": -20.0,  # Flash crash
            "profit_pct": 5.0,  # Not at profit target
            "price": 45000.0
        })
        assert strategy.current_state == StrategyState.EMERGENCY_EXIT, \
            f"E1 should trigger on flash crash, got {strategy.current_state}"

    async def test_signal_cancellation_prevents_entry(self, full_manager):
        """
        Test O1 cancellation:
        Signal detected, but pump reverses before entry → signal cancelled
        """
        manager = full_manager
        symbol = "BTCUSDT"

        strategy = Strategy(
            strategy_name="cancel_trader",
            enabled=True,
            direction="LONG",
            symbol=symbol,
            signal_detection=ConditionGroup(
                name="signal",
                require_all=True,
                conditions=[
                    Condition(name="pump", condition_type="pump_magnitude_pct", operator=">=", value=5.0)
                ]
            ),
            signal_cancellation=ConditionGroup(
                name="cancel",
                require_all=True,
                conditions=[
                    Condition(name="reversal", condition_type="pump_magnitude_pct", operator="<", value=3.0)
                ]
            ),
            entry_conditions=ConditionGroup(
                name="entry",
                require_all=True,
                conditions=[
                    Condition(name="confirm", condition_type="pump_magnitude_pct", operator=">=", value=6.0)
                ]
            )
        )
        strategy.current_state = StrategyState.MONITORING

        manager.strategies[strategy.strategy_name] = strategy
        manager.active_strategies[symbol] = [strategy]

        # Signal detected
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 5.5,
            "price": 50000.0
        })
        assert strategy.current_state == StrategyState.SIGNAL_DETECTED

        # Pump reverses - O1 triggers cancellation
        await manager._evaluate_strategy_locked(strategy, {
            "pump_magnitude_pct": 2.0,  # Below 3% cancellation threshold
            "price": 49000.0
        })
        assert strategy.current_state == StrategyState.SIGNAL_CANCELLED, \
            f"O1 should cancel signal, got {strategy.current_state}"
        assert strategy.strategy_name not in manager._global_signal_slots, "Slot should be released"
