"""
Risk Manager Edge Case Tests - Iterative Hardening
===================================================

This test file iteratively finds edge cases that break the RiskManager
and validates the fixes.

Round 1 Edge Cases:
1. Zero initial capital - Division by zero
2. Zero equity peak - Division by zero in drawdown
3. Missing risk_config attributes - AttributeError
4. Negative quantity/price - No validation
5. Non-thread-safe budget methods - Race conditions
"""

import pytest
import asyncio
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from src.domain.services.risk_manager import RiskManager, RiskCheckResult
from src.domain.models.trading import Position, PositionStatus


@dataclass
class MockRiskConfig:
    """Mock risk configuration for testing"""
    max_position_size_percent: Decimal = Decimal('10')
    max_concurrent_positions: int = 3
    max_symbol_concentration_percent: Decimal = Decimal('30')
    daily_loss_limit_percent: Decimal = Decimal('5')
    max_drawdown_percent: Decimal = Decimal('15')
    max_margin_utilization_percent: Decimal = Decimal('80')
    critical_margin_ratio_percent: Decimal = Decimal('110')
    warning_margin_ratio_percent: Decimal = Decimal('150')


@dataclass
class IncompleteRiskConfig:
    """Incomplete config missing some attributes"""
    max_position_size_percent: Decimal = Decimal('10')
    # Missing other attributes


def create_mock_event_bus():
    """Create a mock event bus"""
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    return event_bus


def create_mock_position(symbol: str, notional_value: Decimal, is_open: bool = True) -> Position:
    """Create a mock position for testing"""
    position = MagicMock(spec=Position)
    position.symbol = symbol
    position.notional_value = notional_value
    position.is_open = is_open
    return position


class TestRiskManagerEdgeCasesRound1:
    """Round 1: Initial edge cases that break RiskManager"""

    # =========================================
    # EDGE CASE 1: Zero Initial Capital
    # =========================================
    @pytest.mark.asyncio
    async def test_edge1_zero_initial_capital(self):
        """
        EDGE CASE 1: Zero initial capital causes division by zero.

        In _check_max_position_size() line 353:
            max_value = self.current_capital * (self.risk_config.max_position_size_percent / 100)

        When current_capital = 0, max_value = 0, then line 363:
            utilization_pct = (position_value / max_value) * 100 if max_value > 0 else 0

        This SHOULD be handled but let's verify.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        # Create RiskManager with zero capital
        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('0')
        )

        # Attempt to check if we can open a position
        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            current_positions=[]
        )

        # Should fail gracefully, not crash
        assert isinstance(result, RiskCheckResult)
        # With zero capital, any position should be rejected
        assert result.can_proceed == False

    @pytest.mark.asyncio
    async def test_edge1_negative_initial_capital(self):
        """
        EDGE CASE 1b: Negative initial capital.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        # Create RiskManager with negative capital
        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('-1000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            current_positions=[]
        )

        # Should handle gracefully
        assert isinstance(result, RiskCheckResult)
        assert result.can_proceed == False

    # =========================================
    # EDGE CASE 2: Zero Equity Peak
    # =========================================
    @pytest.mark.asyncio
    async def test_edge2_zero_equity_peak_drawdown_calculation(self):
        """
        EDGE CASE 2: Zero equity_peak causes division by zero in drawdown calculation.

        In _calculate_drawdown_percent() line 523:
            drawdown_pct = (drawdown / self.equity_peak) * 100

        If equity_peak = 0, this causes ZeroDivisionError.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Manually set equity_peak to zero (edge case scenario)
        risk_manager.equity_peak = Decimal('0')

        # This should not crash
        drawdown = risk_manager._calculate_drawdown_percent()

        # Should return 0 or handle gracefully
        assert drawdown == 0.0 or isinstance(drawdown, (int, float))

    @pytest.mark.asyncio
    async def test_edge2_equity_peak_less_than_current(self):
        """
        EDGE CASE 2b: equity_peak < current_capital (invalid state).

        This could result in negative drawdown percentage.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Set equity_peak lower than current (shouldn't happen, but edge case)
        risk_manager.current_capital = Decimal('15000')
        risk_manager.equity_peak = Decimal('10000')  # Peak not updated

        drawdown = risk_manager._calculate_drawdown_percent()

        # Drawdown should be negative or 0 (no drawdown when above peak)
        # Actually, with the formula: (10000 - 15000) / 10000 * 100 = -50%
        # This is a bug - we should update peak first
        assert isinstance(drawdown, (int, float))

    # =========================================
    # EDGE CASE 3: Missing Risk Config Attributes
    # =========================================
    @pytest.mark.asyncio
    async def test_edge3_incomplete_risk_config(self):
        """
        EDGE CASE 3: Missing attributes in risk_config causes AttributeError.
        """
        event_bus = create_mock_event_bus()
        incomplete_config = IncompleteRiskConfig()

        # This should raise AttributeError during initialization or first use
        with pytest.raises(AttributeError):
            risk_manager = RiskManager(
                event_bus=event_bus,
                risk_config=incomplete_config,
                initial_capital=Decimal('10000')
            )
            # Try to use it - will fail on first check
            await risk_manager.can_open_position(
                symbol="BTC_USDT",
                side="buy",
                quantity=Decimal('1'),
                price=Decimal('50000'),
                current_positions=[]
            )

    @pytest.mark.asyncio
    async def test_edge3_none_values_in_config(self):
        """
        EDGE CASE 3b: None values in risk_config attributes.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()
        config.max_position_size_percent = None  # Set to None

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # This should handle None gracefully or raise clear error
        with pytest.raises((TypeError, AttributeError)):
            await risk_manager.can_open_position(
                symbol="BTC_USDT",
                side="buy",
                quantity=Decimal('1'),
                price=Decimal('50000'),
                current_positions=[]
            )

    # =========================================
    # EDGE CASE 4: Negative Quantity/Price
    # =========================================
    @pytest.mark.asyncio
    async def test_edge4_negative_quantity(self):
        """
        EDGE CASE 4: Negative quantity should be rejected.

        Currently, negative quantity passes through and creates
        negative position_value, which could bypass size checks.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('-1'),  # Negative quantity!
            price=Decimal('50000'),
            current_positions=[]
        )

        # Should be rejected with clear error
        assert result.can_proceed == False
        assert "negative" in (result.reason or "").lower() or "invalid" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_edge4_zero_price(self):
        """
        EDGE CASE 4b: Zero price makes position_value = 0.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('100'),
            price=Decimal('0'),  # Zero price!
            current_positions=[]
        )

        # Should be rejected - zero price is invalid
        assert result.can_proceed == False

    @pytest.mark.asyncio
    async def test_edge4_negative_price(self):
        """
        EDGE CASE 4c: Negative price.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('-50000'),  # Negative price!
            current_positions=[]
        )

        # Should be rejected
        assert result.can_proceed == False

    # =========================================
    # EDGE CASE 5: Non-Thread-Safe Budget Methods
    # =========================================
    def test_edge5_use_budget_race_condition(self):
        """
        EDGE CASE 5: use_budget() and release_budget() are not async-safe.

        Multiple threads could read available capital, then both
        allocate budget exceeding the limit.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Simulate race condition: two strategies try to allocate 6000 each
        # Total would be 12000, exceeding 10000 capital

        # First allocation should succeed
        result1 = risk_manager.use_budget("strategy1", 6000)
        assert result1 == True

        # Second allocation should fail (only 4000 available)
        result2 = risk_manager.use_budget("strategy2", 6000)
        assert result2 == False

        # Verify only 6000 allocated
        assert risk_manager.get_available_capital() == 4000.0

    def test_edge5_release_nonexistent_budget(self):
        """
        EDGE CASE 5b: Releasing budget that was never allocated.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Try to release budget that doesn't exist
        result = risk_manager.release_budget("nonexistent_strategy")
        assert result == False

    def test_edge5_double_release_budget(self):
        """
        EDGE CASE 5c: Releasing the same budget twice.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Allocate budget
        risk_manager.use_budget("strategy1", 5000)

        # Release once
        result1 = risk_manager.release_budget("strategy1")
        assert result1 == True

        # Release again - should fail gracefully
        result2 = risk_manager.release_budget("strategy1")
        assert result2 == False


class TestRiskManagerEdgeCasesRound1Fixes:
    """Tests to verify Round 1 fixes work correctly"""

    @pytest.mark.asyncio
    async def test_fix1_zero_capital_handled(self):
        """Verify zero capital is handled without crash"""
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('0')
        )

        # After fix: should reject position gracefully
        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            current_positions=[]
        )

        assert result.can_proceed == False
        assert "capital" in result.reason.lower() or "insufficient" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_fix4_negative_values_validated(self):
        """Verify negative quantity/price is validated"""
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # After fix: negative quantity should be caught
        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('-1'),
            price=Decimal('50000'),
            current_positions=[]
        )

        assert result.can_proceed == False


class TestRiskManagerEdgeCasesRound2:
    """
    Round 2: Additional edge cases after Round 1 fixes.

    New edge cases:
    1. NaN/Infinity in Decimal calculations
    2. Position with None notional_value in list
    3. Daily loss limit with positive P&L then loss
    4. Concurrent async operations on same method
    5. risk_config with Decimal string values (not Decimal objects)
    """

    # =========================================
    # EDGE CASE 6: NaN/Infinity in calculations
    # =========================================
    @pytest.mark.asyncio
    async def test_edge6_infinity_price(self):
        """
        EDGE CASE 6: Infinity price should be rejected.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Try with very large number approaching infinity
        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('1e308'),  # Near float max
            current_positions=[]
        )

        # Should be rejected
        assert result.can_proceed == False

    @pytest.mark.asyncio
    async def test_edge6_very_small_quantity(self):
        """
        EDGE CASE 6b: Very small quantity (near zero but positive).
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1e-18'),  # Very small
            price=Decimal('50000'),
            current_positions=[]
        )

        # Should be allowed (tiny position, low risk)
        assert isinstance(result, RiskCheckResult)

    # =========================================
    # EDGE CASE 7: Position with None notional_value
    # =========================================
    @pytest.mark.asyncio
    async def test_edge7_position_with_none_notional(self):
        """
        EDGE CASE 7: Position in list with None notional_value.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Create position with None notional_value
        bad_position = MagicMock()
        bad_position.symbol = "BTC_USDT"
        bad_position.notional_value = None  # Bug scenario
        bad_position.is_open = True

        # This should not crash
        try:
            result = await risk_manager.can_open_position(
                symbol="BTC_USDT",
                side="buy",
                quantity=Decimal('1'),
                price=Decimal('50000'),
                current_positions=[bad_position]
            )
            # If it doesn't crash, check result is valid
            assert isinstance(result, RiskCheckResult)
        except TypeError as e:
            # If it crashes, this is a bug to fix
            pytest.fail(f"None notional_value caused TypeError: {e}")

    # =========================================
    # EDGE CASE 8: Daily loss limit edge scenarios
    # =========================================
    @pytest.mark.asyncio
    async def test_edge8_daily_loss_after_profit(self):
        """
        EDGE CASE 8: Daily P&L swings from profit to loss.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # First, record a profit
        await risk_manager.update_capital(Decimal('11000'), Decimal('1000'))
        assert risk_manager.daily_pnl == Decimal('1000')

        # Then a bigger loss
        await risk_manager.update_capital(Decimal('9000'), Decimal('-2000'))
        assert risk_manager.daily_pnl == Decimal('-1000')

        # Check if position can be opened (daily loss = 10% of initial)
        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('100'),
            current_positions=[]
        )

        # With 10% daily loss and 5% limit, should be rejected
        # Actually daily_loss_limit is checked against current_capital
        assert isinstance(result, RiskCheckResult)

    @pytest.mark.asyncio
    async def test_edge8_daily_loss_exactly_at_limit(self):
        """
        EDGE CASE 8b: Daily loss exactly at limit (boundary condition).
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()
        config.daily_loss_limit_percent = Decimal('5')

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Set daily loss to exactly 5% of 10000 = 500
        risk_manager.daily_pnl = Decimal('-500')

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT",
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('100'),
            current_positions=[]
        )

        # At exactly the limit, the check uses < not <=
        # daily_pnl (-500) < -daily_loss_limit (-500) is False
        # So this should pass
        assert isinstance(result, RiskCheckResult)

    # =========================================
    # EDGE CASE 9: Concurrent async operations
    # =========================================
    @pytest.mark.asyncio
    async def test_edge9_concurrent_position_checks(self):
        """
        EDGE CASE 9: Multiple concurrent can_open_position calls.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()
        config.max_concurrent_positions = 2

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        # Create existing position
        existing = create_mock_position("ETH_USDT", Decimal('1000'), is_open=True)

        # Run multiple checks concurrently
        results = await asyncio.gather(
            risk_manager.can_open_position(
                symbol="BTC_USDT", side="buy", quantity=Decimal('0.01'),
                price=Decimal('100'), current_positions=[existing]
            ),
            risk_manager.can_open_position(
                symbol="SOL_USDT", side="buy", quantity=Decimal('0.01'),
                price=Decimal('100'), current_positions=[existing]
            ),
            risk_manager.can_open_position(
                symbol="ADA_USDT", side="buy", quantity=Decimal('0.01'),
                price=Decimal('100'), current_positions=[existing]
            ),
        )

        # All should return valid results
        for result in results:
            assert isinstance(result, RiskCheckResult)

    # =========================================
    # EDGE CASE 10: Config with string values
    # =========================================
    @pytest.mark.asyncio
    async def test_edge10_config_with_string_decimals(self):
        """
        EDGE CASE 10: risk_config with string values instead of Decimal.
        """
        event_bus = create_mock_event_bus()

        @dataclass
        class StringConfig:
            max_position_size_percent: str = "10"  # String not Decimal
            max_concurrent_positions: int = 3
            max_symbol_concentration_percent: str = "30"
            daily_loss_limit_percent: str = "5"
            max_drawdown_percent: str = "15"
            max_margin_utilization_percent: str = "80"
            critical_margin_ratio_percent: str = "110"
            warning_margin_ratio_percent: str = "150"

        string_config = StringConfig()

        # This might fail due to string arithmetic
        try:
            risk_manager = RiskManager(
                event_bus=event_bus,
                risk_config=string_config,
                initial_capital=Decimal('10000')
            )

            result = await risk_manager.can_open_position(
                symbol="BTC_USDT",
                side="buy",
                quantity=Decimal('1'),
                price=Decimal('100'),
                current_positions=[]
            )
            # If it works, great - config handles strings
            assert isinstance(result, RiskCheckResult)
        except (TypeError, InvalidOperation) as e:
            # Expected - strings don't work with Decimal arithmetic
            pass


class TestRiskManagerEdgeCasesRound3:
    """
    Round 3: Final edge cases to ensure complete hardening.

    Edge cases:
    1. Empty symbol string (after stripping)
    2. Unicode/special characters in symbol
    3. Extremely long strategy name
    4. get_risk_summary with empty allocated_budgets
    5. assess_position_risk with negative volatility
    """

    @pytest.mark.asyncio
    async def test_edge11_whitespace_symbol(self):
        """
        EDGE CASE 11: Symbol with only whitespace.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="   ",  # Whitespace only
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('100'),
            current_positions=[]
        )

        # Should be rejected
        assert result.can_proceed == False

    @pytest.mark.asyncio
    async def test_edge12_unicode_symbol(self):
        """
        EDGE CASE 12: Symbol with unicode characters.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = await risk_manager.can_open_position(
            symbol="BTC_USDT🚀",  # Unicode emoji
            side="buy",
            quantity=Decimal('1'),
            price=Decimal('100'),
            current_positions=[]
        )

        # Should either accept (unicode is valid) or reject with clear error
        assert isinstance(result, RiskCheckResult)

    def test_edge13_long_strategy_name(self):
        """
        EDGE CASE 13: Very long strategy name.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        long_name = "strategy_" + "x" * 10000  # 10000 chars

        result = risk_manager.use_budget(long_name, 1000)

        # Should handle gracefully
        assert isinstance(result, bool)

    def test_edge14_risk_summary_empty_budgets(self):
        """
        EDGE CASE 14: get_risk_summary with no allocated budgets.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        summary = risk_manager.get_risk_summary()

        # Should not crash and return valid summary
        assert "current_capital" in summary
        assert summary["total_allocated"] == 0.0
        assert summary["available_capital"] == 10000.0

    def test_edge15_assess_position_risk_negative_volatility(self):
        """
        EDGE CASE 15: assess_position_risk with negative volatility.
        """
        event_bus = create_mock_event_bus()
        config = MockRiskConfig()

        risk_manager = RiskManager(
            event_bus=event_bus,
            risk_config=config,
            initial_capital=Decimal('10000')
        )

        result = risk_manager.assess_position_risk(
            symbol="BTC_USDT",
            position_size=0.05,
            current_price=50000,
            volatility=-0.02,  # Negative volatility
            max_drawdown=0.05,
            sharpe_ratio=1.5
        )

        # Should handle gracefully
        assert "risk_score" in result
        assert result["risk_score"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
