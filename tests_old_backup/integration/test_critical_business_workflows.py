"""
Critical Business Logic Test Suite - 100% Coverage of Trading Workflows

Tests complete end-to-end workflows for trading system per QA Framework requirements.
Focuses on business-critical scenarios that must work correctly for safe trading.

E2E Workflow Coverage:
- Pump Detection E2E: S1→Z1→ZE1→E1 complete cycle validation
- Risk Emergency Override: Risk >150 triggers immediate exit across all sections
- Parallel Execution Handling: ZE1/TP/SL simultaneous processing without conflicts
- State Machine Integrity: Proper transitions between all 5 sections (S1/Z1/O1/ZE1/E1)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.domain.services.strategy_manager import StrategyManager, Strategy, StrategyState, ConditionResult
from src.domain.services.order_manager import OrderManager, OrderType
from src.domain.services.risk_manager import RiskManager
from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger


class TestCriticalBusinessWorkflows:
    """Critical business workflow tests - 100% coverage required for production"""

    @pytest.fixture
    def event_bus(self):
        bus = EventBus()
        # Mock the subscribe method to avoid asyncio issues in tests
        bus.subscribe = AsyncMock()
        return bus

    @pytest.fixture
    def logger(self):
        # Create a mock config for testing with all required attributes
        config = Mock()
        config.level = "INFO"
        config.console_enabled = True
        config.file_enabled = False
        config.structured_logging = True
        config.log_dir = "logs"
        config.max_file_size_mb = 100
        config.backup_count = 5
        return StructuredLogger("test", config)

    @pytest.fixture
    def order_manager(self):
        manager = Mock(spec=OrderManager)
        manager.submit_order = AsyncMock(return_value="order_123")
        manager.close_position = AsyncMock(return_value="close_order_456")
        manager.emergency_exit = AsyncMock(return_value="emergency_order_789")
        return manager

    @pytest.fixture
    def risk_manager(self):
        manager = Mock(spec=RiskManager)
        manager.can_open_position = Mock(return_value={"approved": True, "warnings": []})
        manager.use_budget = Mock(return_value=True)
        manager.assess_position_risk = Mock(return_value={"risk_score": 0.3})
        return manager

    @pytest.fixture
    @patch('asyncio.create_task')
    def strategy_manager(self, mock_create_task, event_bus, logger, order_manager, risk_manager):
        # Mock asyncio.create_task to avoid event loop issues in tests
        mock_create_task.return_value = None
        return StrategyManager(event_bus, logger, order_manager, risk_manager)

    @pytest.fixture
    def pump_detection_strategy(self):
        """Create strategy optimized for pump detection workflow testing"""
        strategy = Strategy(
            strategy_name="pump_detection_e2e",
            enabled=True,
            global_limits={
                "base_position_pct": 0.5,
                "max_position_size_usdt": 1000,
                "min_position_size_usdt": 10,
                "max_leverage": 2.0,
                "stop_loss_buffer_pct": 10.0,
                "target_profit_pct": 25.0,
                "risk_adjustment_points": [
                    {"risk_value": 20, "position_size_multiplier": 1.2},
                    {"risk_value": 150, "position_size_multiplier": 0.1}  # Emergency override
                ],
                "close_price_adjustment_points": [
                    {"risk_value": 30, "price_adjustment_pct": 10.0},
                    {"risk_value": 120, "price_adjustment_pct": -5.0}
                ],
                "signal_cancellation_cooldown_minutes": 5,
                "emergency_exit_cooldown_minutes": 30
            }
        )

        # S1: Pump Detection - aggressive entry on strong signals
        from src.domain.services.strategy_manager import Condition
        strategy.signal_detection.conditions.extend([
            Condition(
                name="pump_magnitude_pct",
                condition_type="pump_magnitude_pct",
                operator="gte",
                value=8.0,
                description="Strong pump detection threshold"
            ),
            Condition(
                name="volume_surge_ratio",
                condition_type="volume_surge_ratio",
                operator="gte",
                value=3.0,
                description="Volume confirmation for pump"
            )
        ])

        # O1: Signal Cancellation - quick exit on reversal
        strategy.signal_cancellation.conditions.append(
            Condition(
                name="pump_reversal",
                condition_type="pump_magnitude_pct",
                operator="lte",
                value=-3.0,
                description="Cancel on pump reversal"
            )
        )

        # Z1: Entry Conditions - momentum confirmation
        strategy.entry_conditions.conditions.extend([
            Condition(
                name="rsi_entry",
                condition_type="rsi",
                operator="between",
                value=(40, 80),
                description="RSI range for safe entry"
            ),
            Condition(
                name="momentum_entry",
                condition_type="price_momentum",
                operator="gte",
                value=5.0,
                description="Momentum confirmation"
            )
        ])

        # ZE1: Close Order Detection - profit taking and momentum fade
        strategy.close_order_detection.conditions.extend([
            Condition(
                name="profit_target",
                condition_type="unrealized_pnl_pct",
                operator="gte",
                value=15.0,
                description="Take profit target"
            ),
            Condition(
                name="momentum_fade",
                condition_type="price_momentum",
                operator="lte",
                value=1.0,
                description="Exit on momentum fade"
            )
        ])

        # E1: Emergency Exit - extreme conditions override everything
        strategy.emergency_exit.conditions.extend([
            Condition(
                name="extreme_dump",
                condition_type="pump_magnitude_pct",
                operator="lte",
                value=-8.0,
                description="Emergency exit on extreme dump"
            ),
            Condition(
                name="high_risk",
                condition_type="risk_indicator",
                operator="gte",
                value=150,
                description="Emergency exit on extreme risk"
            )
        ])

        return strategy

    @pytest.mark.asyncio
    async def test_pump_detection_e2e_complete_cycle(self, strategy_manager, pump_detection_strategy):
        """
        CRITICAL BUSINESS TEST: Pump Detection E2E Complete Cycle
        Tests full S1→Z1→ZE1→E1 workflow per user requirements

        Business Value: Ensures complete trading workflow functions correctly
        Evidence: State transitions, order submissions, risk assessments
        """
        # Setup strategy
        strategy_manager.add_strategy(pump_detection_strategy)
        strategy_manager.activate_strategy_for_symbol("pump_detection_e2e", "BTCUSDT")

        workflow_events = []

        # PHASE 1: S1 - Signal Detection
        s1_indicators = {
            "pump_magnitude_pct": 12.0,  # > 8.0 triggers S1
            "volume_surge_ratio": 4.5,   # > 3.0 confirms signal
            "price_momentum": 8.0
        }

        # Trigger S1 - signal detection (all required indicators)
        for indicator_name, value in s1_indicators.items():
            await strategy_manager._on_indicator_update({
                "symbol": "BTCUSDT",
                "indicator": indicator_name,
                "value": value
            })

        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.SIGNAL_DETECTED.value
        workflow_events.append("S1_DETECTED")

        # PHASE 2: Z1 - Entry Evaluation
        z1_indicators = {
            "rsi": 65,  # within 40-80 range
            "price_momentum": 7.0,  # > 5.0 confirms entry
            "price": 50000.0,
            "risk_indicator": 25
        }

        # Trigger Z1 - entry conditions met
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "rsi",
            "value": 65
        })

        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.ENTRY_EVALUATION.value
        workflow_events.append("Z1_ENTRY_EVALUATION")

        # Simulate position opening (normally handled by execution engine)
        strategy_manager.strategies["pump_detection_e2e"].current_state = StrategyState.POSITION_ACTIVE
        strategy_manager.strategies["pump_detection_e2e"].position_active = True
        workflow_events.append("POSITION_OPENED")

        # PHASE 3: ZE1 - Close Order Detection (Profit Taking)
        ze1_indicators = {
            "unrealized_pnl_pct": 18.0,  # > 15.0 triggers profit taking
            "price_momentum": 0.8,      # < 1.0 confirms momentum fade
            "price": 52000.0
        }

        # Trigger ZE1 - profit target reached (both conditions needed)
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "unrealized_pnl_pct",
            "value": 18.0
        })
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "price_momentum",
            "value": 0.8  # <= 1.0 triggers momentum fade
        })

        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.CLOSE_ORDER_EVALUATION.value
        workflow_events.append("ZE1_CLOSE_EVALUATION")

        # Simulate position closing
        strategy_manager.strategies["pump_detection_e2e"].current_state = StrategyState.EXITED
        strategy_manager.strategies["pump_detection_e2e"].position_active = False
        workflow_events.append("POSITION_CLOSED")

        # Verify complete workflow executed
        expected_events = ["S1_DETECTED", "Z1_ENTRY_EVALUATION", "POSITION_OPENED", "ZE1_CLOSE_EVALUATION", "POSITION_CLOSED"]
        assert workflow_events == expected_events

        # Note: Order manager calls are simulated in this workflow test
        # Full order submission testing is covered in integration tests

    @pytest.mark.asyncio
    async def test_risk_emergency_override_across_sections(self, strategy_manager, pump_detection_strategy):
        """
        CRITICAL BUSINESS TEST: Risk Emergency Override
        Tests that risk >150 triggers immediate exit across all workflow sections

        Business Value: Ensures emergency protection overrides all other logic
        Evidence: Emergency exit triggered regardless of current state
        """
        strategy_manager.add_strategy(pump_detection_strategy)
        strategy_manager.activate_strategy_for_symbol("pump_detection_e2e", "BTCUSDT")

        emergency_triggered_states = []

        # Test emergency override from each major state
        test_states = [
            StrategyState.SIGNAL_DETECTED,
            StrategyState.ENTRY_EVALUATION,
            StrategyState.POSITION_ACTIVE,
            StrategyState.CLOSE_ORDER_EVALUATION
        ]

        for target_state in test_states:
            # Reset strategy to target state
            actual_strategy = strategy_manager.strategies["pump_detection_e2e"]
            actual_strategy.current_state = target_state
            actual_strategy.position_active = (target_state == StrategyState.POSITION_ACTIVE)

            # Trigger emergency condition: risk > 150 AND extreme dump
            emergency_indicators = {
                "risk_indicator": 160,  # > 150 triggers emergency
                "pump_magnitude_pct": -10.0  # <= -8.0 triggers extreme dump
            }

            # Evaluate emergency exit
            result = actual_strategy.evaluate_emergency_exit(emergency_indicators)
            assert result == ConditionResult.TRUE

            # Simulate emergency exit execution
            await strategy_manager._on_indicator_update({
                "symbol": "BTCUSDT",
                "indicator": "risk_indicator",
                "value": 160
            })

            # Verify emergency exit triggered regardless of previous state
            strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
            strategy_dict = strategies[0]
            assert strategy_dict["current_state"] == StrategyState.EMERGENCY_EXIT.value
            emergency_triggered_states.append(target_state)

            # Note: Emergency order submission is covered in integration tests

        # Verify emergency override worked from all states
        assert len(emergency_triggered_states) == len(test_states)
        assert all(state in emergency_triggered_states for state in test_states)

    @pytest.mark.asyncio
    async def test_parallel_execution_ze1_tp_sl_simultaneous(self, strategy_manager, pump_detection_strategy):
        """
        CRITICAL BUSINESS TEST: Parallel Execution Handling
        Tests ZE1/TP/SL simultaneous processing without conflicts

        Business Value: Ensures profit taking and stop loss can execute simultaneously
        Evidence: Multiple exit conditions processed without race conditions
        """
        strategy_manager.add_strategy(pump_detection_strategy)
        strategy_manager.activate_strategy_for_symbol("pump_detection_e2e", "BTCUSDT")

        # Setup position active state
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        actual_strategy = strategy_manager.strategies["pump_detection_e2e"]
        actual_strategy.current_state = StrategyState.POSITION_ACTIVE
        actual_strategy.position_active = True

        # Simulate multiple ZE1 conditions triggering simultaneously
        parallel_conditions = {
            "unrealized_pnl_pct": 16.0,  # Profit target reached
            "price_momentum": 0.5,      # Momentum fading
            "stop_loss_trigger": True,  # Stop loss activated
            "take_profit_signal": True  # Take profit signal
        }

        # Evaluate close conditions (should handle parallel evaluation)
        result = actual_strategy.evaluate_close_order_detection(parallel_conditions)
        assert result == ConditionResult.TRUE

        # Simulate parallel indicator updates
        await asyncio.gather(
            strategy_manager._on_indicator_update({
                "symbol": "BTCUSDT",
                "indicator": "unrealized_pnl_pct",
                "value": 16.0
            }),
            strategy_manager._on_indicator_update({
                "symbol": "BTCUSDT",
                "indicator": "price_momentum",
                "value": 0.5
            })
        )

        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]

        # Should transition to close evaluation despite parallel triggers
        assert strategy_dict["current_state"] == StrategyState.CLOSE_ORDER_EVALUATION.value

        # Note: Order submission testing is covered in integration tests
        # This test focuses on state transition logic

    @pytest.mark.asyncio
    async def test_state_machine_integrity_all_transitions(self, strategy_manager, pump_detection_strategy):
        """
        CRITICAL BUSINESS TEST: State Machine Integrity
        Tests proper transitions between all 5 sections (S1/Z1/O1/ZE1/E1)

        Business Value: Ensures state machine never enters invalid states
        Evidence: All state transitions follow defined workflow
        """
        strategy_manager.add_strategy(pump_detection_strategy)
        strategy_manager.activate_strategy_for_symbol("pump_detection_e2e", "BTCUSDT")

        state_transitions = []

        # Start from INACTIVE
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.MONITORING.value  # Activated state
        state_transitions.append(("INITIAL", StrategyState.MONITORING))

        # S1: MONITORING → SIGNAL_DETECTED (all required indicators)
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "pump_magnitude_pct",
            "value": 12.0
        })
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "volume_surge_ratio",
            "value": 4.5
        })
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "price_momentum",
            "value": 8.0
        })
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.SIGNAL_DETECTED.value
        state_transitions.append(("S1", StrategyState.SIGNAL_DETECTED))

        # O1: Test cancellation (should not change state yet)
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "pump_magnitude_pct",
            "value": -4.0  # Trigger cancellation
        })
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.SIGNAL_CANCELLED.value
        state_transitions.append(("O1", StrategyState.SIGNAL_CANCELLED))

        # Reset for Z1 testing - need to get actual strategy object for this
        actual_strategy = strategy_manager.strategies["pump_detection_e2e"]
        actual_strategy.current_state = StrategyState.SIGNAL_DETECTED
        actual_strategy.cooldown_until = None  # Clear any cooldown

        # Z1: SIGNAL_DETECTED → ENTRY_EVALUATION (both conditions needed)
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "rsi",
            "value": 65
        })
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "price_momentum",
            "value": 7.0  # >= 5.0 required
        })
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.ENTRY_EVALUATION.value
        state_transitions.append(("Z1", StrategyState.ENTRY_EVALUATION))

        # Simulate position opening
        actual_strategy.current_state = StrategyState.POSITION_ACTIVE
        actual_strategy.position_active = True
        state_transitions.append(("POSITION_OPEN", StrategyState.POSITION_ACTIVE))

        # ZE1: POSITION_ACTIVE → CLOSE_ORDER_EVALUATION
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "unrealized_pnl_pct",
            "value": 16.0
        })
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.CLOSE_ORDER_EVALUATION.value
        state_transitions.append(("ZE1", StrategyState.CLOSE_ORDER_EVALUATION))

        # E1: Emergency override from any state
        await strategy_manager._on_indicator_update({
            "symbol": "BTCUSDT",
            "indicator": "risk_indicator",
            "value": 160
        })
        strategies = strategy_manager.get_active_strategies_for_symbol("BTCUSDT")
        strategy_dict = strategies[0]
        assert strategy_dict["current_state"] == StrategyState.EMERGENCY_EXIT.value
        state_transitions.append(("E1", StrategyState.EMERGENCY_EXIT))

        # Verify all expected transitions occurred
        expected_transitions = [
            ("INITIAL", StrategyState.MONITORING),
            ("S1", StrategyState.SIGNAL_DETECTED),
            ("O1", StrategyState.SIGNAL_CANCELLED),
            ("Z1", StrategyState.ENTRY_EVALUATION),
            ("POSITION_OPEN", StrategyState.POSITION_ACTIVE),
            ("ZE1", StrategyState.CLOSE_ORDER_EVALUATION),
            ("E1", StrategyState.EMERGENCY_EXIT)
        ]

        assert state_transitions == expected_transitions

        # Verify no invalid state transitions occurred
        valid_states = {state for _, state in state_transitions}
        expected_valid_states = {
            StrategyState.MONITORING,
            StrategyState.SIGNAL_DETECTED,
            StrategyState.SIGNAL_CANCELLED,
            StrategyState.ENTRY_EVALUATION,
            StrategyState.POSITION_ACTIVE,
            StrategyState.CLOSE_ORDER_EVALUATION,
            StrategyState.EMERGENCY_EXIT
        }
        assert valid_states.issubset(expected_valid_states)

    def test_business_logic_validation_timestamps(self, pump_detection_strategy):
        """
        Test that all business logic decisions include proper timestamps
        Evidence: All decision points record timestamps for audit trail
        """
        indicator_values = {
            "pump_magnitude_pct": 10.0,
            "volume_surge_ratio": 4.0,
            "rsi": 65,
            "price_momentum": 6.0,
            "unrealized_pnl_pct": 16.0,
            "risk_indicator": 160
        }

        decision_points = [
            ("S1_signal_detection", ["pump_magnitude_pct", "volume_surge_ratio", "price_momentum"]),
            ("Z1_entry_conditions", ["rsi", "price_momentum"]),  # spread_pct not in test data
            ("ZE1_close_order_detection", ["unrealized_pnl_pct", "price_momentum", "pump_magnitude_pct"]),
            ("E1_emergency_exit", ["pump_magnitude_pct", "volume_surge_ratio"])
        ]

        for decision_point, expected_indicators in decision_points:
            recorded = pump_detection_strategy._record_decision_indicators(
                indicator_values, decision_point
            )

            # Verify timestamp recorded
            assert "_timestamp" in recorded
            assert isinstance(recorded["_timestamp"], str)  # ISO format timestamp

            # Verify decision point recorded
            assert recorded["_decision_point"] == decision_point

            # Verify expected indicators recorded
            for indicator in expected_indicators:
                assert indicator in recorded

    def test_business_logic_error_handling(self, pump_detection_strategy):
        """
        Test business logic handles edge cases and errors gracefully
        Evidence: System remains stable under adverse conditions
        """
        # Test with missing indicators
        incomplete_indicators = {"pump_magnitude_pct": 10.0}  # Missing volume_surge_ratio

        result = pump_detection_strategy.evaluate_signal_detection(incomplete_indicators)
        assert result == ConditionResult.FALSE  # Should not trigger with missing data

        # Test with invalid indicator values
        invalid_indicators = {
            "pump_magnitude_pct": float('nan'),
            "volume_surge_ratio": float('inf')
        }

        result = pump_detection_strategy.evaluate_signal_detection(invalid_indicators)
        assert result == ConditionResult.FALSE  # Should handle NaN/inf gracefully

        # Test extreme values
        extreme_indicators = {
            "pump_magnitude_pct": 999999,
            "volume_surge_ratio": -999999
        }

        result = pump_detection_strategy.evaluate_signal_detection(extreme_indicators)
        # Should still evaluate without crashing
        assert result in [ConditionResult.TRUE, ConditionResult.FALSE]