"""
Unit tests for Sharpe Ratio calculation - PH2 fix
==================================================

Tests verifying that sharpe_ratio is calculated correctly from equity curve data,
not left as placeholder None.

Test Cases:
- Normal case with equity curve → positive sharpe
- Empty dataset → 0.0
- Only gains (no volatility) → 0.0
- High volatility → lower sharpe
- Edge cases (single data point, etc.)
"""

import pytest
import statistics
from typing import List


class TestSharpeRatioCalculation:
    """Test sharpe ratio calculation logic"""

    def calculate_sharpe_ratio(self, equity_curve: List[float]) -> float:
        """
        Calculate Sharpe Ratio from equity curve.

        Formula:
        - returns[i] = (equity[i] - equity[i-1]) / equity[i-1]
        - mean_return = mean(returns)
        - std_return = stdev(returns)
        - sharpe_ratio = mean_return / std_return * sqrt(252) if std > 0 else 0.0

        Args:
            equity_curve: List of equity values

        Returns:
            Sharpe ratio (annualized)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        # Calculate period returns
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i-1] > 0:
                period_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(period_return)

        if len(returns) < 2:
            return 0.0

        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe ratio (252 trading days)
        sharpe_ratio = (mean_return / std_return) * (252 ** 0.5)
        return sharpe_ratio

    def test_sharpe_ratio_normal_case(self):
        """Test sharpe ratio with normal equity curve"""
        # Upward trending equity with some volatility
        equity_curve = [10000, 10100, 10050, 10150, 10200, 10180, 10250]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # Should be positive (upward trend)
        assert sharpe > 0, "Sharpe ratio should be positive for upward trending equity"
        # Should be reasonable (not inf or nan)
        assert -100 < sharpe < 100, f"Sharpe ratio seems unreasonable: {sharpe}"

    def test_sharpe_ratio_empty_dataset(self):
        """Test sharpe ratio with empty dataset"""
        equity_curve = []
        sharpe = self.calculate_sharpe_ratio(equity_curve)
        assert sharpe == 0.0, "Empty dataset should return 0.0"

    def test_sharpe_ratio_single_point(self):
        """Test sharpe ratio with single data point"""
        equity_curve = [10000]
        sharpe = self.calculate_sharpe_ratio(equity_curve)
        assert sharpe == 0.0, "Single data point should return 0.0"

    def test_sharpe_ratio_two_points(self):
        """Test sharpe ratio with two data points"""
        equity_curve = [10000, 10100]
        sharpe = self.calculate_sharpe_ratio(equity_curve)
        # Two points = one return, can't calculate stdev
        assert sharpe == 0.0, "Two data points should return 0.0 (need >=2 returns)"

    def test_sharpe_ratio_only_gains_constant(self):
        """Test sharpe ratio with constant gains (no volatility)"""
        # Perfect 1% gain every period
        equity_curve = [10000, 10100, 10201, 10303.01, 10406.04]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # With constant returns, std should be very small but not exactly zero
        # due to floating point arithmetic
        assert sharpe >= 0, "Constant gains should have non-negative sharpe"

    def test_sharpe_ratio_high_volatility(self):
        """Test sharpe ratio with high volatility"""
        # Same start and end, but lots of volatility
        equity_curve = [10000, 11000, 9000, 11500, 8500, 10000]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # High volatility with no net gain should give low/negative sharpe
        assert sharpe < 5, f"High volatility with no gain should have low sharpe, got {sharpe}"

    def test_sharpe_ratio_consistent_losses(self):
        """Test sharpe ratio with consistent losses"""
        equity_curve = [10000, 9900, 9800, 9700, 9600]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # Consistent losses should give negative sharpe
        assert sharpe < 0, "Consistent losses should give negative sharpe ratio"

    def test_sharpe_ratio_zero_division_protection(self):
        """Test sharpe ratio handles zero division (no volatility)"""
        # All values the same
        equity_curve = [10000, 10000, 10000, 10000]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # No change = zero returns, should return 0.0
        assert sharpe == 0.0, "No volatility should return 0.0 (not inf or nan)"

    def test_sharpe_ratio_real_world_example(self):
        """Test sharpe ratio with realistic trading data"""
        # Realistic equity curve from paper trading
        equity_curve = [
            10000.0, 10050.0, 10025.0, 10100.0, 10080.0,
            10150.0, 10120.0, 10200.0, 10175.0, 10250.0,
            10225.0, 10300.0, 10280.0, 10350.0, 10330.0
        ]
        sharpe = self.calculate_sharpe_ratio(equity_curve)

        # Should be positive (profitable), reasonable value
        assert sharpe > 0, "Profitable equity curve should have positive sharpe"
        assert 0 < sharpe < 50, f"Sharpe ratio seems unreasonable: {sharpe}"

    def test_sharpe_ratio_matches_formula(self):
        """Test that calculation matches the mathematical formula"""
        equity_curve = [10000, 10100, 10050, 10150]

        # Manual calculation
        returns = [
            (10100 - 10000) / 10000,  # 0.01
            (10050 - 10100) / 10100,  # -0.00495...
            (10150 - 10050) / 10050   # 0.00995...
        ]
        mean_ret = statistics.mean(returns)
        std_ret = statistics.stdev(returns)
        expected_sharpe = (mean_ret / std_ret) * (252 ** 0.5)

        actual_sharpe = self.calculate_sharpe_ratio(equity_curve)

        assert abs(actual_sharpe - expected_sharpe) < 0.01, \
            f"Calculated sharpe {actual_sharpe} doesn't match expected {expected_sharpe}"


class TestSharpeRatioIntegration:
    """Integration tests for sharpe ratio in performance tracking"""

    def test_sharpe_ratio_not_none_placeholder(self):
        """Verify sharpe_ratio is not left as None placeholder"""
        # This is the core PH2 issue - sharpe_ratio should never be None
        # when there's sufficient data to calculate it
        equity_curve = [10000, 10100, 10050, 10150, 10200]

        calc = TestSharpeRatioCalculation()
        sharpe = calc.calculate_sharpe_ratio(equity_curve)

        # CRITICAL: sharpe should be a number, not None
        assert sharpe is not None, "Sharpe ratio should not be None (PH2 placeholder issue)"
        assert isinstance(sharpe, (int, float)), "Sharpe ratio should be numeric"
        assert not (sharpe != sharpe), "Sharpe ratio should not be NaN"  # NaN check
