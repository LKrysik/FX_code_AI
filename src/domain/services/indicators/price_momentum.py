"""
PRICE_MOMENTUM Algorithm Implementation
=======================================
Calculates price momentum as rate of change with EMA smoothing.

Formula: ((current_ema - baseline_ema) / baseline_ema) * 100

Where:
- current_ema = EMA of recent prices in window (t1, t2)
- baseline_ema = EMA of historical prices in window (t3, t4)

This measures the directional strength of price movement.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_simple_average


class PriceMomentumAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    PRICE_MOMENTUM: Directional strength of price movement.

    Measures momentum by comparing:
    - Current price level (EMA over recent window)
    - Baseline price level (EMA over historical window)

    Positive momentum indicates upward price pressure (bullish).
    Negative momentum indicates downward price pressure (bearish).

    Used in S1 (Signal Detection) and Z1 (Entry Conditions).

    Parameters:
    - t1: Start of current window in seconds ago (default: 30s)
    - t2: End of current window in seconds ago (default: 0s = now)
    - t3: Start of baseline window in seconds ago (default: 120s = 2min)
    - t4: End of baseline window in seconds ago (default: 30s)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=30, t2=0, t3=120, t4=30 means:
      - Current: price average from last 30 seconds
      - Baseline: price average from 2min ago to 30s ago
      - Compares recent price direction vs historical

    Returns:
    - Positive value: Upward momentum (bullish)
    - Negative value: Downward momentum (bearish)
    - ~0: No significant momentum
    - Units: Percentage change
    """

    def get_indicator_type(self) -> str:
        return "PRICE_MOMENTUM"

    def get_name(self) -> str:
        return "Price Momentum"

    def get_description(self) -> str:
        return "Directional strength of price movement as percentage change"

    def get_category(self) -> str:
        return "general"  # Used in S1 Signal Detection and Z1 Entry

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "t1",
                "float",
                30.0,  # 30 seconds current window
                1.0,
                3600.0,
                None,
                True,
                "Start of current price window in seconds ago"
            ),
            VariantParameter(
                "t2",
                "float",
                0.0,  # End at now
                0.0,
                3600.0,
                None,
                True,
                "End of current price window in seconds ago (0 = now)"
            ),
            VariantParameter(
                "t3",
                "float",
                120.0,  # Look back 2 minutes for baseline
                1.0,
                86400.0,
                None,
                True,
                "Start of baseline window in seconds ago"
            ),
            VariantParameter(
                "t4",
                "float",
                30.0,  # Baseline ends 30s ago
                0.0,
                86400.0,
                None,
                True,
                "End of baseline window in seconds ago"
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
        """Default refresh: 2 seconds for momentum tracking."""
        return 2.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Momentum should be refreshed frequently for trend detection
        t1 = params.get_float("t1", 30.0)

        if t1 <= 30.0:
            return 2.0
        elif t1 <= 60.0:
            return 3.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        PRICE_MOMENTUM is time-driven.

        Momentum measures rate of change over time, requiring regular
        recalculation to track sliding time windows.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for momentum calculation.

        Returns:
            Two WindowSpec objects: [current_window, baseline_window]
        """
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)
        t3 = params.get_float("t3", 120.0)
        t4 = params.get_float("t4", 30.0)

        # Validate windows don't overlap
        if t4 < t1:
            # Overlap detected - baseline end overlaps with current start
            # Adjust t4 to not overlap
            t4 = t1

        return [
            WindowSpec(t1, t2),      # Current window (recent prices)
            WindowSpec(t3, t4),      # Baseline window (historical prices)
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate PRICE_MOMENTUM from two price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate average price in current window
        2. Calculate average price in baseline window
        3. Return percentage change: ((current - baseline) / baseline) * 100

        Args:
            data_windows: [current_window, baseline_window]
            params: Algorithm parameters

        Returns:
            Price momentum (percentage) or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        baseline_window = data_windows[1]

        # Calculate averages for both windows
        current_avg = compute_simple_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        baseline_avg = compute_simple_average(
            baseline_window.data,
            baseline_window.start_ts,
            baseline_window.end_ts
        )

        # Validate both averages calculated successfully
        if current_avg is None or baseline_avg is None:
            return None

        # Avoid division by zero
        if baseline_avg == 0:
            return None

        # Calculate percentage momentum
        momentum = ((current_avg - baseline_avg) / baseline_avg) * 100.0

        return momentum

    def calculate_multi_window(
        self,
        windows: List[tuple],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        OLD INTERFACE: Backward compatibility wrapper.
        """
        if len(windows) != 2:
            return None

        # Convert to DataWindow format
        current_data, current_start, current_end = windows[0]
        baseline_data, baseline_start, baseline_end = windows[1]

        data_windows = [
            DataWindow(current_data, current_start, current_end, "price"),
            DataWindow(baseline_data, baseline_start, baseline_end, "price"),
        ]

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get two price windows from engine for calculation."""
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)
        t3 = params.get_float("t3", 120.0)
        t4 = params.get_float("t4", 30.0)

        # Get both windows from engine
        current_window = engine._get_price_series_for_window(indicator, t1, t2)
        baseline_window = engine._get_price_series_for_window(indicator, t3, t4)

        return [current_window, baseline_window]


# Create instance for auto-discovery registration
price_momentum_algorithm = PriceMomentumAlgorithm()
