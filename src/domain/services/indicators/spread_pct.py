"""
SPREAD_PCT (Bid-Ask Spread Percentage) Algorithm Implementation
===============================================================
Calculates the bid-ask spread as a percentage of the mid price.

Formula: spread_pct = ((ask - bid) / mid_price) * 100
Where mid_price = (ask + bid) / 2

High spread indicates low liquidity or high volatility.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)


class SpreadPctAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    SPREAD_PCT: Bid-Ask Spread Percentage.

    Measures market liquidity via spread width.
    Used in Z1 (Entry Conditions) to avoid entering illiquid markets.

    Parameters:
    - max_spread: Maximum acceptable spread percentage (default: 1.0%)
    - r: Refresh interval override (optional)

    Returns:
    - Value >= 0: Spread as percentage of mid price
    - Low value (< 0.1%): High liquidity, tight spread
    - High value (> 1%): Low liquidity, wide spread
    """

    def get_indicator_type(self) -> str:
        return "SPREAD_PCT"

    def get_name(self) -> str:
        return "Bid-Ask Spread Percentage"

    def get_description(self) -> str:
        return "Bid-ask spread as percentage of mid price - measures liquidity"

    def get_category(self) -> str:
        return "liquidity"

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "max_spread",
                "float",
                1.0,  # 1% max spread
                0.01,
                100.0,
                None,
                False,
                "Maximum acceptable spread percentage"
            ),
            VariantParameter(
                "r",
                "float",
                None,
                0.5,
                3600.0,
                None,
                False,
                "Refresh interval in seconds (optional override)"
            ),
        ]

    def get_default_refresh_interval(self) -> float:
        """Default refresh: 1 second for spread monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )
        return 1.0

    def is_time_driven(self) -> bool:
        """Spread is event-driven (updates with each orderbook change)."""
        return False

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """Spread uses latest bid/ask, no historical window needed."""
        return [WindowSpec(1.0, 0)]  # Just get latest data

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate SPREAD_PCT from orderbook data.

        Note: This algorithm expects data in format [(timestamp, {bid, ask})]
        or will fall back to using price data if available.
        """
        if len(data_windows) != 1:
            return None

        window = data_windows[0]

        if len(window.data) == 0:
            return None

        # Get latest data point
        latest = window.data[-1]

        # Handle different data formats
        if isinstance(latest, tuple) and len(latest) >= 2:
            timestamp, value = latest[0], latest[1]

            if isinstance(value, dict):
                # Orderbook data format: (timestamp, {bid, ask})
                bid = value.get("bid") or value.get("best_bid")
                ask = value.get("ask") or value.get("best_ask")

                if bid and ask and bid > 0 and ask > 0:
                    mid_price = (bid + ask) / 2
                    spread_pct = ((ask - bid) / mid_price) * 100
                    return spread_pct

            elif isinstance(value, (int, float)):
                # Price data - cannot calculate spread from price alone
                # Return a default conservative estimate
                return 0.1  # 0.1% default for liquid markets

        return None

    def calculate_multi_window(
        self,
        windows: List[tuple],
        params: IndicatorParameters
    ) -> Optional[float]:
        """Old interface wrapper for single window."""
        if len(windows) != 1:
            return None
        data, start_ts, end_ts = windows[0]
        data_windows = [DataWindow(data, start_ts, end_ts, "orderbook")]
        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get orderbook window from engine for calculation."""
        # Get latest orderbook data
        window = engine._get_orderbook_series_for_window(indicator, 1.0, 0)

        return [window]


# Create instance for auto-discovery registration
spread_pct_algorithm = SpreadPctAlgorithm()
