"""
VOLUME_SURGE_RATIO Algorithm Implementation
==========================================
Calculates volume surge as ratio between current and baseline volume averages.

Formula: current_volume_avg / baseline_volume_median

Where:
- current_volume_avg = average volume per second in window (t1, t2)
- baseline_volume_median = median volume in baseline window (t3, t4)

This detects significant volume increases indicating pump activity.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import (
    compute_volume_average,
    compute_volume_median
)


class VolumeSurgeRatioAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    VOLUME_SURGE_RATIO: Volume surge detection via current vs baseline comparison.

    Detects pump conditions by comparing:
    - Current volume flow rate (volume per second in recent window)
    - Baseline volume median (typical volume in historical window)

    A high ratio (e.g., > 3.5x) indicates abnormal volume surge typical of pump.

    Parameters:
    - t1: Start of current volume window in seconds ago (default: 30s)
    - t2: End of current volume window in seconds ago (default: 0s = now)
    - t3: Start of baseline volume window in seconds ago (default: 600s = 10min)
    - t4: End of baseline volume window in seconds ago (default: 30s)
    - min_baseline: Minimum baseline to avoid division by zero (default: 0.001)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=30, t2=0, t3=600, t4=30 means:
      - Current: volume flow in last 30 seconds
      - Baseline: median volume from 10min ago to 30s ago
      - Compares recent spike vs historical normal

    Returns:
    - Value > 1.0: Volume higher than baseline (potential pump)
    - Value = 1.0: Volume at baseline level
    - Value < 1.0: Volume lower than baseline
    """

    def get_indicator_type(self) -> str:
        return "VOLUME_SURGE_RATIO"

    def get_name(self) -> str:
        return "Volume Surge Ratio"

    def get_description(self) -> str:
        return "Ratio of current volume flow to baseline volume median - detects volume spikes"

    def get_category(self) -> str:
        return "general"  # Used in S1 Signal Detection

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "t1",
                "float",
                30.0,  # Current window: last 30 seconds
                1.0,
                3600.0,
                None,
                True,
                "Start of current volume window in seconds ago"
            ),
            VariantParameter(
                "t2",
                "float",
                0.0,  # Current window ends now
                0.0,
                3600.0,
                None,
                True,
                "End of current volume window in seconds ago (0 = now)"
            ),
            VariantParameter(
                "t3",
                "float",
                600.0,  # Baseline: 10 minutes back
                1.0,
                86400.0,
                None,
                True,
                "Start of baseline volume window in seconds ago"
            ),
            VariantParameter(
                "t4",
                "float",
                30.0,  # Baseline ends 30s ago (to avoid overlap with current)
                0.0,
                86400.0,
                None,
                True,
                "End of baseline volume window in seconds ago"
            ),
            VariantParameter(
                "min_baseline",
                "float",
                0.001,
                0.0001,
                1.0,
                None,
                False,
                "Minimum baseline volume to avoid division by zero"
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
        """Default refresh: 2 seconds for volume monitoring."""
        return 2.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use current window end (t2) to determine refresh rate
        t2 = params.get_float("t2", 0.0)

        if t2 <= 1.0:
            return 1.0  # Real-time monitoring
        elif t2 <= 30.0:
            return 2.0
        elif t2 <= 60.0:
            return 5.0
        else:
            return 10.0

    def is_time_driven(self) -> bool:
        """
        VOLUME_SURGE_RATIO is time-driven.

        Volume windows slide with time and need regular recalculation
        even if no new trades arrive (to update the time-averaged values).
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for volume surge calculation.

        Returns:
            Two WindowSpec objects: [current_window, baseline_window]
        """
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)
        t3 = params.get_float("t3", 600.0)
        t4 = params.get_float("t4", 30.0)

        # Validate window semantics
        if t1 < t2:
            raise ValueError(
                f"Invalid current window: t1 ({t1}) must be >= t2 ({t2})"
            )

        if t3 < t4:
            raise ValueError(
                f"Invalid baseline window: t3 ({t3}) must be >= t4 ({t4})"
            )

        return [
            WindowSpec(t1, t2),  # Current volume window
            WindowSpec(t3, t4),  # Baseline volume window
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate VOLUME_SURGE_RATIO from two volume windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate current volume average (volume per second)
        2. Calculate baseline volume median (typical volume level)
        3. Return ratio: current / baseline

        Args:
            data_windows: [current_window, baseline_window]
                         Both should contain (timestamp, volume) tuples
            params: Algorithm parameters

        Returns:
            Volume surge ratio or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        baseline_window = data_windows[1]

        # Calculate current volume average (volume per second)
        current_volume_avg = compute_volume_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        # Calculate baseline volume median (robust against outliers)
        baseline_volume_median = compute_volume_median(
            baseline_window.data,
            baseline_window.start_ts,
            baseline_window.end_ts
        )

        # Validate both calculations succeeded
        if current_volume_avg is None or baseline_volume_median is None:
            return None

        # Avoid division by zero
        min_baseline = params.get_float("min_baseline", 0.001)
        if baseline_volume_median < min_baseline:
            return None

        # Calculate surge ratio
        surge_ratio = current_volume_avg / baseline_volume_median

        return surge_ratio

    def calculate_multi_window(
        self,
        windows: List[tuple],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        OLD INTERFACE: Backward compatibility wrapper.

        Note: This assumes engine provides volume data in the windows.
        The engine needs to support _get_volume_series_for_window() method.
        """
        if len(windows) != 2:
            return None

        # Convert to DataWindow format
        current_data, current_start, current_end = windows[0]
        baseline_data, baseline_start, baseline_end = windows[1]

        data_windows = [
            DataWindow(current_data, current_start, current_end, "volume"),
            DataWindow(baseline_data, baseline_start, baseline_end, "volume"),
        ]

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """
        Get two volume windows from engine for calculation.

        Note: This requires engine to implement _get_volume_series_for_window()
        or similar method to extract volume data. For now, we'll use deal_data
        which contains volume information.
        """
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)
        t3 = params.get_float("t3", 600.0)
        t4 = params.get_float("t4", 30.0)

        # Try to get volume data from engine
        # If engine doesn't have dedicated volume method, fallback to deal data
        if hasattr(engine, '_get_volume_series_for_window'):
            current_window = engine._get_volume_series_for_window(indicator, t1, t2)
            baseline_window = engine._get_volume_series_for_window(indicator, t3, t4)
        elif hasattr(engine, '_get_deal_series_for_window'):
            # Extract volume from deal data
            current_window = engine._get_deal_series_for_window(indicator, t1, t2)
            baseline_window = engine._get_deal_series_for_window(indicator, t3, t4)
        else:
            # Fallback: empty windows (engine needs implementation)
            import time
            now = time.time()
            current_window = ([], now - t1, now - t2)
            baseline_window = ([], now - t3, now - t4)

        return [current_window, baseline_window]


# Create instance for auto-discovery registration
volume_surge_ratio_algorithm = VolumeSurgeRatioAlgorithm()
