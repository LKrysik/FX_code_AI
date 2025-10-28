"""
VELOCITY_CASCADE Algorithm Implementation
========================================
Calculates multiple price velocities across different time windows and analyzes
their relationship to detect acceleration/deceleration patterns.

This indicator detects:
- Acceleration: Short-term velocity > Medium-term velocity > Long-term velocity
- Deceleration: Velocity decreasing across time scales
- Momentum shifts: Changes in velocity patterns

Formula: Calculates multiple PRICE_VELOCITY values and computes cascade index

Cascade Index Interpretation:
- Index > 0.5: Strong acceleration (pump gaining momentum)
- Index > 0: Moderate acceleration
- Index ~0: Stable velocity
- Index < 0: Deceleration (pump weakening)
- Index < -0.5: Strong deceleration (potential reversal)
"""

import math
from typing import List, Optional, Dict, Any
from .base_algorithm import (
    IndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class VelocityCascadeAlgorithm(IndicatorAlgorithm):
    """
    VELOCITY_CASCADE: Multi-timeframe velocity analysis for acceleration detection.

    Calculates price velocity across multiple time windows and analyzes
    the relationship between them to detect:
    - Pump acceleration (velocities increasing)
    - Pump deceleration (velocities decreasing)
    - Momentum shifts

    Parameters:
    - windows: JSON array of window configurations, each with:
      - t1: Current window length
      - t3: Baseline lookback
      - d: Baseline window length
      - label: Optional label for this window (e.g., "short", "medium", "long")
    - r: Refresh interval override (optional)

    Example Configuration:
    ```json
    {
        "windows": [
            {"t1": 5, "t3": 15, "d": 5, "label": "ultra_short"},
            {"t1": 10, "t3": 40, "d": 10, "label": "short"},
            {"t1": 20, "t3": 80, "d": 20, "label": "medium"}
        ]
    }
    ```

    Returns:
    - Cascade index: -1.0 to +1.0
    - Positive: Acceleration (pump strengthening)
    - Negative: Deceleration (pump weakening)
    - Metadata includes individual velocities for analysis
    """

    def get_indicator_type(self) -> str:
        return "VELOCITY_CASCADE"

    def get_name(self) -> str:
        return "Velocity Cascade"

    def get_description(self) -> str:
        return "Multi-timeframe velocity analysis to detect acceleration/deceleration patterns"

    def get_category(self) -> str:
        return "general"  # Used for advanced pump detection

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        # Default 3-window configuration
        default_windows = [
            {"t1": 5, "t3": 15, "d": 5, "label": "ultra_short"},
            {"t1": 10, "t3": 40, "d": 10, "label": "short"},
            {"t1": 20, "t3": 80, "d": 20, "label": "medium"}
        ]

        return [
            VariantParameter(
                "windows",
                "json",  # JSON array of window configs
                default_windows,
                None,
                None,
                None,
                True,
                "Array of window configurations. Each must have t1, t3, d, and optional label."
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
        """Default refresh: 1 second for velocity cascade monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on shortest window."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use shortest window for refresh cadence
        windows = params.get("windows", [])
        if not windows:
            return 1.0

        # Find shortest t1 across all windows
        min_t1 = min((w.get("t1", 10.0) for w in windows), default=10.0)

        if min_t1 <= 10.0:
            return 1.0
        elif min_t1 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        VELOCITY_CASCADE is time-driven.

        Requires regular recalculation to track sliding velocity windows.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Generate window specs for all configured velocity calculations.

        For N velocity windows, we need 2*N data windows (current + baseline for each).
        """
        windows_config = params.get("windows", [])
        if not windows_config:
            # Fallback to default if no configuration provided
            windows_config = [
                {"t1": 5, "t3": 15, "d": 5},
                {"t1": 10, "t3": 40, "d": 10},
                {"t1": 20, "t3": 80, "d": 20}
            ]

        window_specs = []
        for config in windows_config:
            t1 = float(config.get("t1", 10.0))
            t3 = float(config.get("t3", 60.0))
            d = float(config.get("d", 30.0))

            # Add current and baseline windows for this velocity calculation
            window_specs.append(WindowSpec(t1, 0))      # Current window
            window_specs.append(WindowSpec(t3, t3 - d)) # Baseline window

        return window_specs

    def calculate(self, data, start_ts, end_ts, params: IndicatorParameters) -> Optional[float]:
        """
        Not used for VELOCITY_CASCADE - use calculate_from_windows instead.
        """
        raise NotImplementedError("Use calculate_from_windows for VELOCITY_CASCADE")

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate VELOCITY_CASCADE from multiple price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. For each window pair, calculate velocity
        2. Compute cascade index from velocity relationships
        3. Return cascade index with metadata

        Args:
            data_windows: List of DataWindow objects (pairs of current/baseline for each velocity)
            params: Algorithm parameters including windows configuration

        Returns:
            Cascade index (-1.0 to +1.0) or None if cannot calculate
        """
        windows_config = params.get("windows", [])
        if not windows_config:
            return None

        # Should have 2 windows per velocity calculation (current + baseline)
        expected_windows = len(windows_config) * 2
        if len(data_windows) != expected_windows:
            return None

        # Calculate velocity for each window pair
        velocities = []
        for i, config in enumerate(windows_config):
            # Get current and baseline windows for this velocity
            current_window = data_windows[i * 2]
            baseline_window = data_windows[i * 2 + 1]

            # Calculate TWPA for both windows
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

            if current_twpa is None or baseline_twpa is None or baseline_twpa == 0:
                # Cannot calculate this velocity - skip it
                velocities.append(None)
                continue

            # Calculate percentage price change
            price_change_pct = ((current_twpa - baseline_twpa) / baseline_twpa) * 100.0

            # Calculate time difference between window centers
            current_center = (current_window.start_ts + current_window.end_ts) / 2.0
            baseline_center = (baseline_window.start_ts + baseline_window.end_ts) / 2.0
            time_diff = current_center - baseline_center

            if time_diff <= 0:
                velocities.append(None)
                continue

            # Calculate velocity
            velocity = price_change_pct / time_diff
            velocities.append(velocity)

        # Filter out None values
        valid_velocities = [v for v in velocities if v is not None]

        if len(valid_velocities) < 2:
            # Need at least 2 velocities to compute cascade
            return None

        # Compute cascade index
        cascade_index = self._compute_cascade_index(valid_velocities)

        return cascade_index

    def _compute_cascade_index(self, velocities: List[float]) -> float:
        """
        Compute cascade index from velocity sequence.

        Algorithm:
        1. Calculate pairwise differences between consecutive velocities
        2. Weight more recent (shorter timeframe) differences higher
        3. Apply consistency bonus if all differences have same sign
        4. Normalize to [-1, +1] range using tanh

        Args:
            velocities: List of velocities from shortest to longest timeframe

        Returns:
            Cascade index in range [-1, +1]
        """
        if len(velocities) < 2:
            return 0.0

        # Calculate relative differences between consecutive velocities
        diffs = []
        for i in range(len(velocities) - 1):
            v_current = velocities[i]       # Shorter timeframe (more recent)
            v_next = velocities[i + 1]      # Longer timeframe

            # Relative difference (avoid division by zero)
            epsilon = 0.01
            rel_diff = (v_current - v_next) / max(abs(v_next), epsilon)
            diffs.append(rel_diff)

        # Weight more recent differences higher
        weights = [2.0 ** i for i in range(len(diffs))]
        weighted_diff = sum(d * w for d, w in zip(diffs, weights)) / sum(weights)

        # Consistency bonus: if all differences have same sign
        all_positive = all(d > 0 for d in diffs)
        all_negative = all(d < 0 for d in diffs)
        consistency_bonus = 1.2 if (all_positive or all_negative) else 1.0

        weighted_diff *= consistency_bonus

        # Normalize using tanh to get value in [-1, +1]
        scale_factor = 2.0
        cascade_index = math.tanh(weighted_diff / scale_factor)

        return cascade_index

    def _create_engine_hook(self):
        """
        Create hook for engine integration.

        This is more complex for VELOCITY_CASCADE because it needs
        multiple window pairs.
        """
        def compute_indicator_value(engine, indicator, params):
            """Hook for VELOCITY_CASCADE calculation."""
            from .base_algorithm import IndicatorParameters

            wrapped_params = IndicatorParameters(params)
            windows_config = wrapped_params.get("windows", [])

            if not windows_config:
                return None

            # Get all required data windows
            all_windows = []
            for config in windows_config:
                t1 = float(config.get("t1", 10.0))
                t3 = float(config.get("t3", 60.0))
                d = float(config.get("d", 30.0))

                # Get current and baseline windows
                current_window = engine._get_price_series_for_window(indicator, t1, 0)
                baseline_window = engine._get_price_series_for_window(indicator, t3, t3 - d)

                all_windows.append(current_window)
                all_windows.append(baseline_window)

            # Convert to DataWindow format
            data_windows = []
            for window_data, start_ts, end_ts in all_windows:
                data_windows.append(DataWindow(window_data, start_ts, end_ts, "price"))

            # Calculate cascade index
            return self.calculate_from_windows(data_windows, wrapped_params)

        return compute_indicator_value


# Create instance for auto-discovery registration
velocity_cascade_algorithm = VelocityCascadeAlgorithm()
