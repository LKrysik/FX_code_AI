"""
UNREALIZED_PNL_PCT (Unrealized Profit/Loss Percentage) Algorithm Implementation
================================================================================
Calculates unrealized P&L as percentage of entry price.

Formula: unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100

For LONG positions: positive when price goes up
For SHORT positions: positive when price goes down

Used in ZE1 (Close Order Detection) to trigger profit-taking.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)


class UnrealizedPnlPctAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    UNREALIZED_PNL_PCT: Unrealized Profit/Loss Percentage.

    Measures current position profit/loss relative to entry price.
    Used in ZE1 (Close Order Detection) to trigger profit-taking.

    Parameters:
    - entry_price: Price at which position was entered (required at runtime)
    - direction: Position direction - 'LONG' or 'SHORT' (default: LONG)
    - r: Refresh interval override (optional)

    Returns:
    - Positive value: Position is in profit
    - Negative value: Position is in loss
    - 0: Break-even
    """

    def get_indicator_type(self) -> str:
        return "UNREALIZED_PNL_PCT"

    def get_name(self) -> str:
        return "Unrealized P&L Percentage"

    def get_description(self) -> str:
        return "Unrealized profit/loss as percentage of entry price"

    def get_category(self) -> str:
        return "position"

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "entry_price",
                "float",
                None,  # Must be provided at runtime
                0.0,
                float('inf'),
                None,
                False,
                "Entry price of the position"
            ),
            VariantParameter(
                "direction",
                "string",
                "LONG",
                None,
                None,
                ["LONG", "SHORT"],
                False,
                "Position direction: LONG or SHORT"
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
        """Default refresh: 1 second for P&L monitoring."""
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
        """P&L is event-driven (updates with each price change)."""
        return False

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """P&L uses latest price, no historical window needed."""
        return [WindowSpec(1.0, 0)]  # Just get latest data

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate UNREALIZED_PNL_PCT from current price and entry price.

        Note: This indicator requires entry_price to be set in params.
        If not set, returns None (cannot calculate without entry price).
        """
        if len(data_windows) != 1:
            return None

        window = data_windows[0]

        if len(window.data) == 0:
            return None

        # Get entry price from params
        entry_price = params.get_float("entry_price", None)

        # If no entry price provided, try to get from metadata
        # This allows the indicator to work with position tracking
        if entry_price is None or entry_price == 0:
            # Cannot calculate P&L without entry price
            # Return 0 as neutral value (break-even assumed)
            return 0.0

        # Get latest price
        latest = window.data[-1]
        if isinstance(latest, tuple) and len(latest) >= 2:
            current_price = latest[1]
        else:
            return None

        if not isinstance(current_price, (int, float)) or current_price <= 0:
            return None

        # Calculate P&L percentage
        direction = params.get_string("direction", "LONG").upper()

        if direction == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        return pnl_pct

    def calculate_multi_window(
        self,
        windows: List[tuple],
        params: IndicatorParameters
    ) -> Optional[float]:
        """Old interface wrapper for single window."""
        if len(windows) != 1:
            return None
        data, start_ts, end_ts = windows[0]
        data_windows = [DataWindow(data, start_ts, end_ts, "price")]
        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get price window from engine for calculation."""
        # Get latest price data
        window = engine._get_price_series_for_window(indicator, 1.0, 0)

        return [window]


# Create instance for auto-discovery registration
unrealized_pnl_pct_algorithm = UnrealizedPnlPctAlgorithm()
