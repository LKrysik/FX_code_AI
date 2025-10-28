"""
PRICE_VELOCITY Algorithm Implementation
======================================
Calculates price velocity as percentage change per second between two TWPA windows.

Formula: ((current_twpa - baseline_twpa) / baseline_twpa) * 100 / time_diff

Where:
- current_twpa = TWPA(t1, 0) - recent price level
- baseline_twpa = TWPA(t3-d, t3) - historical price level
- time_diff = time distance between window centers (in seconds)

This measures the RATE of price change (velocity) using TWPA to reduce noise.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class PriceVelocityAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    PRICE_VELOCITY: Rate of price change (percentage per second).

    Detects the TEMPO of price movement by comparing:
    - Current price level (TWPA over recent window)
    - Baseline price level (TWPA over historical window)
    - Time distance between them

    High velocity indicates rapid price movement (pump or dump).
    Using TWPA instead of raw prices reduces false signals from single spikes.

    Parameters:
    - t1: Length of current price window in seconds (default: 10s)
    - t3: How far back to look for baseline start (default: 60s)
    - d: Length of baseline window in seconds (default: 30s)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=10, t3=60, d=30 means:
      - Current: TWPA from 10s ago to now (center at 5s ago)
      - Baseline: TWPA from 60s ago to 30s ago (center at 45s ago)
      - Time diff: 45s - 5s = 40s
      - Velocity = price_change% / 40s

    Returns:
    - Positive value: Price increasing (upward velocity)
    - Negative value: Price decreasing (downward velocity)
    - ~0: No significant price movement
    - Units: Percentage change per second
    """

    def get_indicator_type(self) -> str:
        return "PRICE_VELOCITY"

    def get_name(self) -> str:
        return "Price Velocity"

    def get_description(self) -> str:
        return "Rate of price change (% per second) using TWPA - detects tempo of movement"

    def get_category(self) -> str:
        return "general"  # Used in S1 Signal Detection and trend analysis

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "t1",
                "float",
                10.0,  # 10 seconds current window
                1.0,
                3600.0,
                None,
                True,
                "Length of current price window in seconds"
            ),
            VariantParameter(
                "t3",
                "float",
                60.0,  # Look back 60 seconds
                1.0,
                86400.0,
                None,
                True,
                "How far back to look for baseline start in seconds"
            ),
            VariantParameter(
                "d",
                "float",
                30.0,  # 30 seconds baseline window
                1.0,
                3600.0,
                None,
                True,
                "Length of baseline window in seconds"
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
        """Default refresh: 1 second for velocity monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Velocity should be refreshed frequently for real-time detection
        t1 = params.get_float("t1", 10.0)

        if t1 <= 10.0:
            return 1.0
        elif t1 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        PRICE_VELOCITY is time-driven.

        Velocity measures rate of change over time, requiring regular
        recalculation to track sliding time windows.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for velocity calculation.

        Returns:
            Two WindowSpec objects: [current_window, baseline_window]
        """
        t1 = params.get_float("t1", 10.0)
        t3 = params.get_float("t3", 60.0)
        d = params.get_float("d", 30.0)

        # Validate windows don't overlap
        baseline_end = t3 - d
        if baseline_end < 0:
            raise ValueError(
                f"Invalid window configuration: baseline extends into future. "
                f"t3 ({t3}) - d ({d}) = {baseline_end} < 0"
            )

        # Warn if windows overlap (might be intentional but unusual)
        if baseline_end < t1:
            # Overlap detected but allow it (user might want this)
            pass

        return [
            WindowSpec(t1, 0),      # Current window
            WindowSpec(t3, t3 - d), # Baseline window
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate PRICE_VELOCITY from two price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate current TWPA and baseline TWPA
        2. Calculate percentage price change
        3. Calculate time difference between window centers
        4. Return velocity = price_change% / time_diff

        Args:
            data_windows: [current_window, baseline_window]
            params: Algorithm parameters

        Returns:
            Price velocity (% per second) or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        baseline_window = data_windows[1]

        # Calculate TWPAs for both windows
        current_twpa = compute_time_weighted_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        baseline_twpa = compute_time_weighted_average(
            baseline_window.data,
            baseline_window.start_ts,
            baseline_window.end_ts
        )

        # Validate both TWPAs calculated successfully
        if current_twpa is None or baseline_twpa is None:
            return None

        # Avoid division by zero
        if baseline_twpa == 0:
            return None

        # Calculate percentage price change
        price_change_pct = ((current_twpa - baseline_twpa) / baseline_twpa) * 100.0

        # Calculate time difference between window centers
        # Center of current window: (start + end) / 2
        current_center = (current_window.start_ts + current_window.end_ts) / 2.0

        # Center of baseline window
        baseline_center = (baseline_window.start_ts + baseline_window.end_ts) / 2.0

        # Time difference (should always be positive since baseline is further back)
        time_diff = current_center - baseline_center

        if time_diff <= 0:
            # Windows are reversed or overlapping - invalid configuration
            return None

        # Calculate velocity: percentage change per second
        velocity = price_change_pct / time_diff

        return velocity

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
        t1 = params.get_float("t1", 10.0)
        t3 = params.get_float("t3", 60.0)
        d = params.get_float("d", 30.0)

        # Get both windows from engine
        current_window = engine._get_price_series_for_window(indicator, t1, 0)
        baseline_window = engine._get_price_series_for_window(indicator, t3, t3 - d)

        return [current_window, baseline_window]


# Create instance for auto-discovery registration
price_velocity_algorithm = PriceVelocityAlgorithm()
