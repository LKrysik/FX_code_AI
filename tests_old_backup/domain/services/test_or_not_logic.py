#!/usr/bin/env python3
"""
Unit Tests for OR/NOT Logic - Phase 2 Sprint 1
==============================================

Tests for _evaluate_conditions_with_logic() function which supports
AND/OR/NOT logical operators for condition evaluation.
"""

import pytest
from src.engine.strategy_evaluator_4section import StrategyEvaluator4Section, Strategy4SectionConfig
from src.core.event_bus import EventBus
from unittest.mock import AsyncMock


@pytest.fixture
def evaluator():
    """Create evaluator instance for testing."""
    event_bus = AsyncMock(spec=EventBus)
    config = Strategy4SectionConfig(
        id="test_logic",
        name="Test Logic",
        s1_signal={"conditions": []},
        z1_entry={"conditions": []},
        ze1_close={"conditions": []},
        o1_cancel={"conditions": []},
        emergency_exit={"conditions": []}
    )
    return StrategyEvaluator4Section(event_bus, config)


class TestORLogic:
    """Test OR logic evaluation."""

    def test_simple_or_both_true(self, evaluator):
        """Test OR when both conditions are TRUE."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70}
        ]
        indicator_data = {
            "rsi": {"value": 25}  # First condition TRUE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "OR should be TRUE when first condition is TRUE"

    def test_simple_or_first_true(self, evaluator):
        """Test OR when first condition is TRUE (short-circuit)."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70}
        ]
        indicator_data = {
            "rsi": {"value": 25}  # First TRUE, second FALSE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "OR should short-circuit when first condition is TRUE"

    def test_simple_or_second_true(self, evaluator):
        """Test OR when second condition is TRUE."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70}
        ]
        indicator_data = {
            "rsi": {"value": 75}  # First FALSE, second TRUE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "OR should be TRUE when second condition is TRUE"

    def test_simple_or_both_false(self, evaluator):
        """Test OR when both conditions are FALSE."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70}
        ]
        indicator_data = {
            "rsi": {"value": 50}  # Both FALSE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "OR should be FALSE when both conditions are FALSE"

    def test_multiple_or(self, evaluator):
        """Test multiple OR conditions."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70, "logic": "OR"},
            {"id": "3", "indicatorId": "rsi", "operator": "==", "value": 50}
        ]
        indicator_data = {
            "rsi": {"value": 50}  # Only third condition TRUE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "Multiple OR should be TRUE if any condition is TRUE"


class TestNOTLogic:
    """Test NOT logic evaluation."""

    def test_simple_not_true(self, evaluator):
        """Test NOT when condition is TRUE (result FALSE)."""
        conditions = [
            {"id": "1", "indicatorId": "volume", "operator": ">", "value": 1000, "logic": "NOT"}
        ]
        indicator_data = {
            "volume": {"value": 1500}  # Condition TRUE, NOT inverts to FALSE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "NOT should invert TRUE to FALSE"

    def test_simple_not_false(self, evaluator):
        """Test NOT when condition is FALSE (result TRUE)."""
        conditions = [
            {"id": "1", "indicatorId": "volume", "operator": ">", "value": 1000, "logic": "NOT"}
        ]
        indicator_data = {
            "volume": {"value": 500}  # Condition FALSE, NOT inverts to TRUE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "NOT should invert FALSE to TRUE"

    def test_not_with_and(self, evaluator):
        """Test NOT combined with AND."""
        conditions = [
            {"id": "1", "indicatorId": "volume", "operator": ">", "value": 1000, "logic": "NOT"},
            {"id": "2", "indicatorId": "price", "operator": ">", "value": 50000}
        ]
        indicator_data = {
            "volume": {"value": 500},    # Condition FALSE, NOT inverts to TRUE
            "price": {"value": 51000}    # Condition TRUE
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "NOT with AND should be TRUE when both are TRUE"


class TestComplexLogic:
    """Test complex combinations of AND/OR/NOT."""

    def test_or_then_and(self, evaluator):
        """Test: (A OR B) AND C"""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "rsi", "operator": ">", "value": 70, "logic": "AND"},
            {"id": "3", "indicatorId": "volume", "operator": ">", "value": 1000}
        ]

        # Test: RSI=25 (first TRUE), Volume=1500 (TRUE)
        indicator_data = {
            "rsi": {"value": 25},
            "volume": {"value": 1500}
        }
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "(TRUE OR ?) AND TRUE should be TRUE"

        # Test: RSI=50 (both FALSE), Volume=1500 (TRUE)
        indicator_data = {
            "rsi": {"value": 50},
            "volume": {"value": 1500}
        }
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "(FALSE OR FALSE) AND TRUE should be FALSE"

    def test_and_with_not(self, evaluator):
        """Test: A AND (NOT B) AND C"""
        conditions = [
            {"id": "1", "indicatorId": "price", "operator": ">", "value": 50000, "logic": "AND"},
            {"id": "2", "indicatorId": "volume", "operator": ">", "value": 1000, "logic": "NOT"},
            {"id": "3", "indicatorId": "rsi", "operator": "<", "value": 30}
        ]

        # Price > 50k (TRUE), Volume > 1k (FALSE, NOT=TRUE), RSI < 30 (TRUE)
        indicator_data = {
            "price": {"value": 51000},
            "volume": {"value": 500},  # NOT inverts to TRUE
            "rsi": {"value": 25}
        }
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "TRUE AND (NOT FALSE) AND TRUE should be TRUE"

    def test_or_with_not(self, evaluator):
        """Test: A OR (NOT B)"""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "volume", "operator": ">", "value": 1000, "logic": "NOT"}
        ]

        # RSI < 30 (FALSE), Volume > 1k (TRUE, NOT=FALSE)
        indicator_data = {
            "rsi": {"value": 50},
            "volume": {"value": 1500}
        }
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "FALSE OR (NOT TRUE) should be FALSE"

        # RSI < 30 (TRUE), Volume > 1k (any)
        indicator_data = {
            "rsi": {"value": 25},
            "volume": {"value": 1500}
        }
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "TRUE OR anything should be TRUE (short-circuit)"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_conditions(self, evaluator):
        """Test empty conditions list."""
        conditions = []
        indicator_data = {}

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "Empty conditions should return TRUE"

    def test_single_condition_no_logic(self, evaluator):
        """Test single condition without logic field (defaults to AND)."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 30}
        ]
        indicator_data = {
            "rsi": {"value": 25}
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "Single condition without logic should work"

    def test_missing_indicator(self, evaluator):
        """Test condition with missing indicator data."""
        conditions = [
            {"id": "1", "indicatorId": "missing_indicator", "operator": ">", "value": 100}
        ]
        indicator_data = {
            "rsi": {"value": 50}  # Different indicator
        }

        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "Missing indicator should evaluate to FALSE"

    def test_equality_operator(self, evaluator):
        """Test == operator with floating point comparison."""
        conditions = [
            {"id": "1", "indicatorId": "price", "operator": "==", "value": 50000.0}
        ]

        # Exact match
        indicator_data = {"price": {"value": 50000.0}}
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "Equality should work for exact match"

        # Very close (within epsilon)
        indicator_data = {"price": {"value": 50000.0000000001}}
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "Equality should work within epsilon"

        # Not equal
        indicator_data = {"price": {"value": 50001.0}}
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "Equality should be FALSE for different values"


class TestShortCircuit:
    """Test short-circuit optimization."""

    def test_and_short_circuit(self, evaluator):
        """Test AND stops evaluating after first FALSE."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": ">", "value": 100, "logic": "AND"},  # Always FALSE
            {"id": "2", "indicatorId": "missing", "operator": ">", "value": 0}  # Would fail if evaluated
        ]
        indicator_data = {
            "rsi": {"value": 50}  # First condition FALSE
            # 'missing' indicator not provided - would return FALSE if evaluated
        }

        # Should short-circuit after first FALSE and not check 'missing' indicator
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is False, "AND should short-circuit on first FALSE"

    def test_or_short_circuit(self, evaluator):
        """Test OR stops evaluating after first TRUE."""
        conditions = [
            {"id": "1", "indicatorId": "rsi", "operator": "<", "value": 100, "logic": "OR"},  # Always TRUE
            {"id": "2", "indicatorId": "missing", "operator": ">", "value": 0}  # Would fail if evaluated
        ]
        indicator_data = {
            "rsi": {"value": 50}  # First condition TRUE
            # 'missing' indicator not provided
        }

        # Should short-circuit after first TRUE and not check 'missing' indicator
        result = evaluator._evaluate_conditions_with_logic(conditions, indicator_data)
        assert result is True, "OR should short-circuit on first TRUE"


class TestRealWorldScenarios:
    """Test real-world strategy scenarios."""

    def test_oversold_or_overbought(self, evaluator):
        """Test: Buy when RSI < 30 OR RSI > 70 (oversold or overbought)."""
        conditions = [
            {"id": "1", "indicatorId": "RSI_14", "operator": "<", "value": 30, "logic": "OR"},
            {"id": "2", "indicatorId": "RSI_14", "operator": ">", "value": 70}
        ]

        # Oversold
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {"RSI_14": {"value": 25}}
        )
        assert result is True, "Should trigger on oversold"

        # Overbought
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {"RSI_14": {"value": 75}}
        )
        assert result is True, "Should trigger on overbought"

        # Normal
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {"RSI_14": {"value": 50}}
        )
        assert result is False, "Should NOT trigger on normal RSI"

    def test_trend_following_with_volume(self, evaluator):
        """Test: Price > EMA AND Volume > threshold (trend following)."""
        conditions = [
            {"id": "1", "indicatorId": "Price", "operator": ">", "value": 50000, "logic": "AND"},
            {"id": "2", "indicatorId": "EMA_50", "operator": "<", "value": 50000, "logic": "AND"},
            {"id": "3", "indicatorId": "Volume", "operator": ">", "value": 1000000}
        ]

        # All conditions met
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {
                "Price": {"value": 51000},
                "EMA_50": {"value": 49000},
                "Volume": {"value": 1500000}
            }
        )
        assert result is True, "All trend conditions met"

        # Price below EMA
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {
                "Price": {"value": 48000},
                "EMA_50": {"value": 49000},
                "Volume": {"value": 1500000}
            }
        )
        assert result is False, "Price not above EMA"

    def test_not_high_volume(self, evaluator):
        """Test: Buy when NOT high volume (avoid pumps)."""
        conditions = [
            {"id": "1", "indicatorId": "Price", "operator": ">", "value": 50000, "logic": "AND"},
            {"id": "2", "indicatorId": "Volume", "operator": ">", "value": 5000000, "logic": "NOT"}
        ]

        # Price good, volume low (NOT inverts)
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {
                "Price": {"value": 51000},
                "Volume": {"value": 1000000}  # Low volume, NOT condition TRUE
            }
        )
        assert result is True, "Should buy when not high volume"

        # Price good, volume too high
        result = evaluator._evaluate_conditions_with_logic(
            conditions,
            {
                "Price": {"value": 51000},
                "Volume": {"value": 6000000}  # High volume, NOT condition FALSE
            }
        )
        assert result is False, "Should NOT buy when high volume"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
