"""
RSI (Relative Strength Index) Algorithm Implementation
=======================================================
Standard RSI indicator using price changes to measure overbought/oversold conditions.

Formula: RSI = 100 - (100 / (1 + RS))
Where RS = Average Gain / Average Loss over the period

RSI oscillates between 0 and 100:
- RSI > 70: Overbought (potential sell signal)
- RSI < 30: Oversold (potential buy signal)
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)


class RSIAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    RSI: Relative Strength Index.

    Measures momentum by comparing recent gains vs losses.
    Used in Z1 (Entry Conditions) to avoid entering overbought positions.

    Parameters:
    - period: Number of data points for RSI calculation (default: 14)
    - t1: Time window in seconds (default: 60s)
    - r: Refresh interval override (optional)

    Returns:
    - Value 0-100: RSI oscillator value
    - > 70: Overbought
    - < 30: Oversold
    - ~50: Neutral
    """

    def get_indicator_type(self) -> str:
        return "RSI"

    def get_name(self) -> str:
        return "Relative Strength Index"

    def get_description(self) -> str:
        return "Momentum oscillator measuring overbought/oversold conditions (0-100)"

    def get_category(self) -> str:
        return "technical"

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "period",
                "int",
                14,
                2,
                100,
                None,
                True,
                "RSI calculation period (number of price points)"
            ),
            VariantParameter(
                "t1",
                "float",
                60.0,  # 60 seconds window
                1.0,
                3600.0,
                None,
                True,
                "Time window in seconds"
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
        """Default refresh: 2 seconds for RSI."""
        return 2.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )
        return 2.0

    def is_time_driven(self) -> bool:
        """RSI is price-driven but can be time-driven for regular updates."""
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """Specify the window needed for RSI calculation."""
        t1 = params.get_float("t1", 60.0)
        return [WindowSpec(t1, 0)]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate RSI from price window.

        Algorithm:
        1. Calculate price changes between consecutive points
        2. Separate gains and losses
        3. Calculate average gain and average loss
        4. Calculate RS = avg_gain / avg_loss
        5. Calculate RSI = 100 - (100 / (1 + RS))
        """
        if len(data_windows) != 1:
            return None

        window = data_windows[0]
        period = params.get_int("period", 14)

        # Need at least period+1 data points to calculate price changes
        if len(window.data) < period + 1:
            return None

        # Sort by timestamp and extract prices
        sorted_data = sorted(window.data, key=lambda x: x[0])
        prices = [p[1] for p in sorted_data]

        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]

        # Use last 'period' changes
        recent_changes = changes[-period:]

        if len(recent_changes) < period:
            return None

        # Separate gains and losses
        gains = [c if c > 0 else 0 for c in recent_changes]
        losses = [-c if c < 0 else 0 for c in recent_changes]

        # Calculate averages
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Avoid division by zero
        if avg_loss == 0:
            return 100.0  # All gains, no losses = max RSI

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

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
        t1 = params.get_float("t1", 60.0)

        # Get single window from engine
        window = engine._get_price_series_for_window(indicator, t1, 0)

        return [window]


# Create instance for auto-discovery registration
rsi_algorithm = RSIAlgorithm()
