#!/usr/bin/env python3
"""
Tests for 4-Section Strategy Evaluator
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.engine.strategy_evaluator_4section import (
    StrategyEvaluator4Section,
    Strategy4SectionConfig,
    Strategy4SectionSignal,
    SignalType,
    SectionState,
    SymbolState
)
from src.core.event_bus import EventBus


@pytest.fixture
def event_bus():
    """Mock EventBus for testing."""
    bus = AsyncMock(spec=EventBus)
    return bus


@pytest.fixture
def sample_strategy_config():
    """Sample 4-section strategy configuration."""
    return Strategy4SectionConfig(
        id="test_strategy_001",
        name="Test 4-Section Strategy",
        s1_signal={
            "conditions": [
                {
                    "id": "vwap_above_100",
                    "indicatorId": "vwap",
                    "operator": ">",
                    "value": 100.0
                },
                {
                    "id": "volume_surge",
                    "indicatorId": "volume_surge_ratio",
                    "operator": ">=",
                    "value": 1.5
                }
            ]
        },
        z1_entry={
            "conditions": [
                {
                    "id": "price_velocity_positive",
                    "indicatorId": "price_velocity",
                    "operator": ">",
                    "value": 0.001
                }
            ],
            "positionSize": {
                "type": "fixed",
                "value": 1000.0
            }
        },
        o1_cancel={
            "timeoutSeconds": 300,  # 5 minutes
            "conditions": [
                {
                    "id": "vwap_below_95",
                    "indicatorId": "vwap",
                    "operator": "<",
                    "value": 95.0
                }
            ]
        },
        emergency_exit={
            "conditions": [
                {
                    "id": "extreme_volume",
                    "indicatorId": "volume_surge_ratio",
                    "operator": ">",
                    "value": 5.0
                }
            ],
            "cooldownMinutes": 60
        }
    )


@pytest.fixture
def evaluator(event_bus, sample_strategy_config):
    """Create a StrategyEvaluator4Section instance."""
    evaluator = StrategyEvaluator4Section(event_bus, sample_strategy_config)
    return evaluator


class TestStrategyEvaluator4Section:
    """Test suite for 4-Section Strategy Evaluator."""

    @pytest.mark.asyncio
    async def test_initialization(self, evaluator, sample_strategy_config):
        """Test evaluator initializes correctly."""
        assert evaluator.config == sample_strategy_config
        assert evaluator.running == False
        assert evaluator.symbol_states == {}
        assert evaluator.indicator_state == {}

    @pytest.mark.asyncio
    async def test_start_stop(self, evaluator, event_bus):
        """Test evaluator can start and stop."""
        # Start
        await evaluator.start()
        assert evaluator.running == True
        event_bus.subscribe.assert_called_once()

        # Stop
        await evaluator.stop()
        assert evaluator.running == False

    @pytest.mark.asyncio
    async def test_indicator_update_processing(self, evaluator):
        """Test indicator updates are processed correctly."""
        await evaluator.start()

        # Send indicator update
        indicator_data = {
            "indicator": "vwap",
            "value": 105.0,
            "timestamp": 1000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(indicator_data)

        # Check indicator state was updated
        assert "BTC_USDT" in evaluator.indicator_state
        assert evaluator.indicator_state["BTC_USDT"]["vwap"]["value"] == 105.0

    @pytest.mark.asyncio
    async def test_s1_signal_detection(self, evaluator, event_bus):
        """Test S1 signal detection with AND logic."""
        await evaluator.start()

        # Send indicators that should trigger S1
        indicators = [
            {"indicator": "vwap", "value": 105.0, "timestamp": 1000, "symbol": "BTC_USDT"},
            {"indicator": "volume_surge_ratio", "value": 2.0, "timestamp": 1000, "symbol": "BTC_USDT"}
        ]

        for indicator in indicators:
            await evaluator._handle_indicator_update(indicator)

        # Check that signal was published
        event_bus.publish.assert_called()
        call_args = event_bus.publish.call_args
        assert call_args[0][0] == "strategy.4section.signal"

        signal_data = call_args[0][1]
        assert signal_data["signal_type"] == "LOCK_SYMBOL"
        assert signal_data["section"] == "s1"
        assert len(signal_data["conditions_met"]) == 2

        # Check symbol state
        assert "BTC_USDT" in evaluator.symbol_states
        assert evaluator.symbol_states["BTC_USDT"].current_state == SectionState.S1_ACTIVE

    @pytest.mark.asyncio
    async def test_s1_signal_partial_conditions(self, evaluator, event_bus):
        """Test S1 signal requires all conditions (AND logic)."""
        await evaluator.start()

        # Send only one indicator (should not trigger)
        indicator_data = {
            "indicator": "vwap",
            "value": 105.0,
            "timestamp": 1000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(indicator_data)

        # No signal should be published (missing volume_surge_ratio)
        event_bus.publish.assert_not_called()

        # Symbol should remain idle
        assert evaluator.symbol_states.get("BTC_USDT", SymbolState()).current_state == SectionState.IDLE

    @pytest.mark.asyncio
    async def test_z1_order_placement(self, evaluator, event_bus):
        """Test Z1 order placement after S1 active."""
        await evaluator.start()

        # First trigger S1
        s1_indicators = [
            {"indicator": "vwap", "value": 105.0, "timestamp": 1000, "symbol": "BTC_USDT"},
            {"indicator": "volume_surge_ratio", "value": 2.0, "timestamp": 1000, "symbol": "BTC_USDT"}
        ]

        for indicator in s1_indicators:
            await evaluator._handle_indicator_update(indicator)

        # Reset mock to check Z1 signal
        event_bus.publish.reset_mock()

        # Now send Z1 condition
        z1_indicator = {
            "indicator": "price_velocity",
            "value": 0.002,
            "timestamp": 2000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(z1_indicator)

        # Check Z1 signal was published
        event_bus.publish.assert_called()
        signal_data = event_bus.publish.call_args[0][1]
        assert signal_data["signal_type"] == "PLACE_ORDER"
        assert signal_data["section"] == "z1"

        # Check state progressed
        assert evaluator.symbol_states["BTC_USDT"].current_state == SectionState.Z1_ACTIVE
        assert evaluator.symbol_states["BTC_USDT"].position_active == True

    @pytest.mark.asyncio
    async def test_o1_cancellation_timeout(self, evaluator, event_bus):
        """Test O1 cancellation by timeout."""
        await evaluator.start()

        # Trigger S1 to get to active state
        s1_indicators = [
            {"indicator": "vwap", "value": 105.0, "timestamp": 1000, "symbol": "BTC_USDT"},
            {"indicator": "volume_surge_ratio", "value": 2.0, "timestamp": 1000, "symbol": "BTC_USDT"}
        ]

        for indicator in s1_indicators:
            await evaluator._handle_indicator_update(indicator)

        # Manually set old signal start time to simulate timeout
        from datetime import timedelta
        evaluator.symbol_states["BTC_USDT"].signal_start_time = datetime.now() - timedelta(seconds=evaluator.config.o1_cancel["timeoutSeconds"] + 10)

        # Reset mock
        event_bus.publish.reset_mock()

        # Send any indicator update to trigger evaluation
        indicator_data = {
            "indicator": "vwap",
            "value": 100.0,
            "timestamp": 3000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(indicator_data)

        # Check O1 cancellation signal
        event_bus.publish.assert_called()
        signal_data = event_bus.publish.call_args[0][1]
        assert signal_data["signal_type"] == "UNLOCK_SYMBOL"
        assert signal_data["section"] == "o1"

        # Check state reset
        assert evaluator.symbol_states["BTC_USDT"].current_state == SectionState.IDLE

    @pytest.mark.asyncio
    async def test_emergency_exit(self, evaluator, event_bus):
        """Test emergency exit conditions (highest priority)."""
        await evaluator.start()

        # Send emergency condition
        emergency_indicator = {
            "indicator": "volume_surge_ratio",
            "value": 6.0,  # Above emergency threshold
            "timestamp": 1000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(emergency_indicator)

        # Check emergency signal published
        event_bus.publish.assert_called()
        signal_data = event_bus.publish.call_args[0][1]
        assert signal_data["signal_type"] == "EMERGENCY_EXIT"
        assert signal_data["section"] == "emergency"

        # Check emergency cooldown set (emergency exit creates state entry)
        assert "BTC_USDT" in evaluator.symbol_states
        state = evaluator.symbol_states["BTC_USDT"]
        assert state.emergency_cooldown_until is not None
        assert state.last_emergency_trigger is not None

    @pytest.mark.asyncio
    async def test_emergency_cooldown(self, evaluator, event_bus):
        """Test emergency cooldown prevents repeated triggers."""
        await evaluator.start()

        # First emergency trigger
        emergency_indicator = {
            "indicator": "volume_surge_ratio",
            "value": 6.0,
            "timestamp": 1000,
            "symbol": "BTC_USDT"
        }

        await evaluator._handle_indicator_update(emergency_indicator)

        # Reset mock
        event_bus.publish.reset_mock()

        # Try to trigger emergency again (should be blocked by cooldown)
        await evaluator._handle_indicator_update(emergency_indicator)

        # No new signal should be published
        event_bus.publish.assert_not_called()

    def test_condition_evaluation(self, evaluator):
        """Test individual condition evaluation."""
        indicator_data = {
            "vwap": {"value": 105.0, "timestamp": 1000},
            "volume_surge_ratio": {"value": 2.0, "timestamp": 1000}
        }

        # Test greater than condition
        condition_gt = {
            "indicatorId": "vwap",
            "operator": ">",
            "value": 100.0
        }
        assert evaluator._evaluate_condition(condition_gt, indicator_data) == True

        # Test less than condition
        condition_lt = {
            "indicatorId": "vwap",
            "operator": "<",
            "value": 100.0
        }
        assert evaluator._evaluate_condition(condition_lt, indicator_data) == False

        # Test equals condition
        condition_eq = {
            "indicatorId": "volume_surge_ratio",
            "operator": "==",
            "value": 2.0
        }
        assert evaluator._evaluate_condition(condition_eq, indicator_data) == True

    def test_strategy_status(self, evaluator):
        """Test strategy status reporting."""
        # Set up some test state
        evaluator.symbol_states["BTC_USDT"] = SymbolState(
            current_state=SectionState.S1_ACTIVE,
            position_active=False
        )
        evaluator.indicator_state["BTC_USDT"] = {
            "vwap": {"value": 105.0, "timestamp": 1000}
        }

        status = evaluator.get_strategy_status()

        assert status["strategy_id"] == "test_strategy_001"
        assert status["strategy_name"] == "Test 4-Section Strategy"
        assert "BTC_USDT" in status["active_symbols"]
        assert status["symbol_states"]["BTC_USDT"]["state"] == "s1_active"
        assert status["indicator_counts"]["BTC_USDT"] == 1