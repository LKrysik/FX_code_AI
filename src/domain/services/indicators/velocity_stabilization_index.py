"""
VELOCITY_STABILIZATION_INDEX Algorithm Implementation
====================================================
Detects when price velocity is stabilizing (variance decreasing).

Measures velocity variance across multiple time points to identify when
price movement is slowing and becoming more predictable (dump ending).

Formula: Standard deviation of recent velocities / mean absolute velocity

Where each velocity is calculated as:
velocity_i = ((TWPA_current_i - TWPA_baseline_i) / TWPA_baseline_i * 100) / time_diff

Lower index = more stable (velocities converging)
Higher index = still volatile (velocities varying)

This indicator signals dump exhaustion when velocity variance drops significantly.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class VelocityStabilizationIndexAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    VELOCITY_STABILIZATION_INDEX: Velocity variance detector.

    Calculates variance of price velocities across multiple time points
    to detect when market is stabilizing (dump ending).

    Parameters:
    - num_samples: Number of velocity samples to analyze (default: 3)
    - sample_interval: Time between samples in seconds (default: 5s)
    - t1: Velocity current window length (default: 10s)
    - t3: Velocity baseline lookback (default: 40s)
    - d: Velocity baseline window length (default: 10s)
    - r: Refresh interval override (optional)

    Example Configuration:
    - num_samples=3, sample_interval=5s:
      - Calculates 3 velocities: now, 5s ago, 10s ago
      - Measures variance across these 3 measurements

    Algorithm:
    1. Calculate N velocities at different time offsets
    2. Compute standard deviation of velocities
    3. Normalize by mean absolute velocity
    4. Return coefficient of variation

    Returns:
    - Value < 0.5: Highly stable (dump exhausting)
    - Value 0.5-1.5: Moderate stability
    - Value > 1.5: High volatility (dump still active)
    """

    def get_indicator_type(self) -> str:
        return "VELOCITY_STABILIZATION_INDEX"

    def get_name(self) -> str:
        return "Velocity Stabilization Index"

    def get_description(self) -> str:
        return "Velocity variance detector - identifies dump exhaustion via stabilizing velocity"

    def get_category(self) -> str:
        return "general"  # Used across sections for dump exhaustion detection

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "num_samples",
                "int",
                3,
                2,
                10,
                None,
                True,
                "Number of velocity samples to analyze for variance"
            ),
            VariantParameter(
                "sample_interval",
                "float",
                5.0,
                1.0,
                60.0,
                None,
                True,
                "Time between velocity samples in seconds"
            ),
            VariantParameter(
                "t1",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Velocity current window length (seconds)"
            ),
            VariantParameter(
                "t3",
                "float",
                40.0,
                1.0,
                86400.0,
                None,
                True,
                "Velocity baseline lookback (seconds)"
            ),
            VariantParameter(
                "d",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Velocity baseline window length (seconds)"
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
        """Default refresh: 2 seconds for stability monitoring."""
        return 2.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use sample interval to determine refresh rate
        sample_interval = params.get_float("sample_interval", 5.0)

        if sample_interval <= 5.0:
            return 1.0
        elif sample_interval <= 10.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        VELOCITY_STABILIZATION_INDEX is time-driven.

        Needs regular recalculation to track velocity variance changes.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify windows needed for velocity variance calculation.

        For num_samples=3, we need 6 windows (2 per velocity measurement):
        - Sample 0 (now): current + baseline
        - Sample 1 (sample_interval ago): current + baseline
        - Sample 2 (2*sample_interval ago): current + baseline

        Returns:
            List of WindowSpec objects (2 * num_samples windows)
        """
        num_samples = params.get("num_samples", 3)
        sample_interval = params.get_float("sample_interval", 5.0)
        t1 = params.get_float("t1", 10.0)
        t3 = params.get_float("t3", 40.0)
        d = params.get_float("d", 10.0)

        windows = []

        for i in range(num_samples):
            # Time offset for this sample
            offset = i * sample_interval

            # Current window for this sample
            windows.append(WindowSpec(offset + t1, offset))

            # Baseline window for this sample
            windows.append(WindowSpec(offset + t3, offset + t3 - d))

        return windows

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate VELOCITY_STABILIZATION_INDEX from multiple velocity samples.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate velocity for each sample (pairs of windows)
        2. Compute standard deviation of velocities
        3. Normalize by mean absolute velocity (coefficient of variation)
        4. Return stabilization index

        Args:
            data_windows: List of DataWindow objects (2 per sample)
                         [current_0, baseline_0, current_1, baseline_1, ...]
            params: Algorithm parameters

        Returns:
            Stabilization index or None if cannot calculate
        """
        num_samples = params.get("num_samples", 3)

        if len(data_windows) != num_samples * 2:
            return None

        # Calculate velocity for each sample
        velocities = []

        for i in range(num_samples):
            current_window = data_windows[i * 2]
            baseline_window = data_windows[i * 2 + 1]

            velocity = self._calculate_velocity(current_window, baseline_window)

            if velocity is not None:
                velocities.append(velocity)

        # Need at least 2 velocities for variance calculation
        if len(velocities) < 2:
            return None

        # Calculate statistics
        mean_velocity = sum(velocities) / len(velocities)
        mean_abs_velocity = sum(abs(v) for v in velocities) / len(velocities)

        # Calculate standard deviation
        variance = sum((v - mean_velocity) ** 2 for v in velocities) / len(velocities)
        std_dev = variance ** 0.5

        # Avoid division by zero
        if mean_abs_velocity < 0.001:
            # Velocities near zero = highly stable
            return 0.0

        # Calculate coefficient of variation (normalized variance)
        # Lower value = more stable
        stabilization_index = std_dev / mean_abs_velocity

        return stabilization_index

    def _calculate_velocity(
        self,
        current_window: DataWindow,
        baseline_window: DataWindow
    ) -> Optional[float]:
        """
        Calculate velocity from two price windows.

        Same calculation as PRICE_VELOCITY indicator.
        """
        # Calculate TWPA for current
        current_twpa = compute_time_weighted_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        # Calculate TWPA for baseline
        baseline_twpa = compute_time_weighted_average(
            baseline_window.data,
            baseline_window.start_ts,
            baseline_window.end_ts
        )

        if current_twpa is None or baseline_twpa is None or baseline_twpa == 0:
            return None

        # Calculate percentage price change
        price_change_pct = ((current_twpa - baseline_twpa) / baseline_twpa) * 100.0

        # Calculate time difference between window centers
        current_center = (current_window.start_ts + current_window.end_ts) / 2.0
        baseline_center = (baseline_window.start_ts + baseline_window.end_ts) / 2.0
        time_diff = current_center - baseline_center

        if time_diff <= 0:
            return None

        # Calculate velocity (% per second)
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
        num_samples = params.get("num_samples", 3)

        if len(windows) != num_samples * 2:
            return None

        # Convert to DataWindow format
        data_windows = []
        for window_data, start_ts, end_ts in windows:
            data_windows.append(DataWindow(window_data, start_ts, end_ts, "price"))

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get multiple price windows from engine for calculation."""
        num_samples = params.get("num_samples", 3)
        sample_interval = params.get_float("sample_interval", 5.0)
        t1 = params.get_float("t1", 10.0)
        t3 = params.get_float("t3", 40.0)
        d = params.get_float("d", 10.0)

        windows = []

        for i in range(num_samples):
            offset = i * sample_interval

            # Current window
            current_window = engine._get_price_series_for_window(
                indicator, offset + t1, offset
            )
            windows.append(current_window)

            # Baseline window
            baseline_window = engine._get_price_series_for_window(
                indicator, offset + t3, offset + t3 - d
            )
            windows.append(baseline_window)

        return windows


# Create instance for auto-discovery registration
velocity_stabilization_index_algorithm = VelocityStabilizationIndexAlgorithm()
