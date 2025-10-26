"""
SUPPORT_LEVEL_PROXIMITY Algorithm Implementation
================================================
Measures distance to support level to identify dump bottom.

During dump, price falls toward pre-pump baseline (support level).
When proximity approaches zero, it signals potential dump completion.

Formula: ((current_price - support_level) / support_level) * 100

Where:
- current_price = TWPA(t1, 0)
- support_level = TWPA(t_support_start, t_support_end) from pre-pump period

This indicator signals:
- Value > 5%: Still far from support (dump continuing)
- Value 0-5%: Approaching support (prepare to exit short)
- Value < 0%: Below support (overshot, quick recovery likely)

Critical for SHORT strategy: Exit when proximity < threshold.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class SupportLevelProximityAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    SUPPORT_LEVEL_PROXIMITY: Distance to support level indicator.

    Calculates percentage distance from current price to identified
    support level (pre-pump baseline). Essential for detecting dump bottom.

    Parameters:
    - t1: Current price window length (default: 10s)
    - t_support_start: Support level window start in seconds ago (default: 3600s = 1 hour before)
    - t_support_end: Support level window end in seconds ago (default: 600s = 10 min before)
    - proximity_threshold: "At support" threshold percentage (default: 2%)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=10, t_support_start=3600, t_support_end=600:
      - Current: avg price in last 10 seconds
      - Support: avg price from 1 hour to 10 min ago (pre-pump baseline)

    Returns:
    - Value > 5%: Far from support
    - Value 0-5%: Near support (exit signal)
    - Value < 0%: Below support (overshot)
    """

    def get_indicator_type(self) -> str:
        return "SUPPORT_LEVEL_PROXIMITY"

    def get_name(self) -> str:
        return "Support Level Proximity"

    def get_description(self) -> str:
        return "Distance to support level - detects dump bottom via proximity to pre-pump baseline"

    def get_category(self) -> str:
        return "close_order"  # Used in ZE1 Close section for exit signals

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        try:
            from ..streaming_indicator_engine import VariantParameter
        except ImportError:
            from typing import NamedTuple

            class VariantParameter(NamedTuple):
                name: str
                type: str
                default: float
                min_value: float
                max_value: float
                allowed_values: Optional[List] = None
                required: bool = True
                description: str = ""

        return [
            VariantParameter(
                "t1",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Current price window length in seconds"
            ),
            VariantParameter(
                "t_support_start",
                "float",
                3600.0,  # 1 hour ago
                60.0,
                86400.0,
                None,
                True,
                "Support level window start in seconds ago (pre-pump period)"
            ),
            VariantParameter(
                "t_support_end",
                "float",
                600.0,  # 10 minutes ago
                30.0,
                86400.0,
                None,
                True,
                "Support level window end in seconds ago"
            ),
            VariantParameter(
                "proximity_threshold",
                "float",
                2.0,  # 2% proximity threshold
                0.1,
                10.0,
                None,
                False,
                "Proximity threshold for 'at support' signal (percentage)"
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
        """Default refresh: 1 second for proximity monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use current price window for refresh rate
        t1 = params.get_float("t1", 10.0)

        if t1 <= 10.0:
            return 1.0
        elif t1 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        SUPPORT_LEVEL_PROXIMITY is time-driven.

        Price changes over time and needs regular recalculation to track
        proximity to support level.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for proximity calculation.

        Returns:
            Two WindowSpec objects: [current_window, support_window]
        """
        t1 = params.get_float("t1", 10.0)
        t_support_start = params.get_float("t_support_start", 3600.0)
        t_support_end = params.get_float("t_support_end", 600.0)

        # Validate window semantics
        if t_support_start < t_support_end:
            raise ValueError(
                f"Invalid support window: t_support_start ({t_support_start}) "
                f"must be >= t_support_end ({t_support_end})"
            )

        return [
            WindowSpec(t1, 0),                              # Current price
            WindowSpec(t_support_start, t_support_end),     # Support level
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate SUPPORT_LEVEL_PROXIMITY from two price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate current price TWPA from window[0]
        2. Calculate support level TWPA from window[1]
        3. Return proximity: (current - support) / support * 100

        Args:
            data_windows: [current_window, support_window]
            params: Algorithm parameters

        Returns:
            Proximity percentage or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        support_window = data_windows[1]

        # Calculate current price
        current_price = compute_time_weighted_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        # Calculate support level
        support_level = compute_time_weighted_average(
            support_window.data,
            support_window.start_ts,
            support_window.end_ts
        )

        # Validate both calculations succeeded
        if current_price is None or support_level is None:
            return None

        # Avoid division by zero
        if support_level == 0:
            return None

        # Calculate proximity percentage
        # Positive = above support (can fall more)
        # Zero = at support (dump bottom)
        # Negative = below support (overshot)
        proximity_pct = ((current_price - support_level) / support_level) * 100.0

        return proximity_pct

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
        support_data, support_start, support_end = windows[1]

        data_windows = [
            DataWindow(current_data, current_start, current_end, "price"),
            DataWindow(support_data, support_start, support_end, "price"),
        ]

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get two price windows from engine for calculation."""
        t1 = params.get_float("t1", 10.0)
        t_support_start = params.get_float("t_support_start", 3600.0)
        t_support_end = params.get_float("t_support_end", 600.0)

        # Get current price window
        current_window = engine._get_price_series_for_window(indicator, t1, 0)

        # Get support level window
        support_window = engine._get_price_series_for_window(
            indicator, t_support_start, t_support_end
        )

        return [current_window, support_window]


# Create instance for auto-discovery registration
support_level_proximity_algorithm = SupportLevelProximityAlgorithm()
