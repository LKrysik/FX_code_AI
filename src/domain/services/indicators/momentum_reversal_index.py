"""
MOMENTUM_REVERSAL_INDEX Algorithm Implementation
===============================================
Detects momentum reversal from pump peak to potential dump.

Measures the change in velocity to identify when pump momentum shifts:
- Peak velocity: highest velocity observed during pump
- Current velocity: current rate of price change
- Reversal = significant drop in velocity from peak

Formula: ((current_velocity - peak_velocity) / abs(peak_velocity)) * 100

This indicator signals:
- Strong negative values: pump losing momentum (potential reversal)
- Values near 0: maintaining momentum
- Positive values: accelerating (unlikely after peak)

Key insight: Velocity drops BEFORE price drops significantly.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class MomentumReversalIndexAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    MOMENTUM_REVERSAL_INDEX: Detects pump-to-dump momentum shift.

    Compares current price velocity to peak velocity to identify
    when pump is losing momentum (early dump signal).

    Parameters:
    - t1_current: Length of current price window (default: 10s)
    - t3_current: Baseline lookback for current velocity (default: 40s)
    - d_current: Baseline window length for current velocity (default: 10s)
    - t1_peak: Length of peak price window (default: 5s)
    - t3_peak: Baseline lookback for peak velocity (default: 20s)
    - d_peak: Baseline window length for peak velocity (default: 5s)
    - r: Refresh interval override (optional)

    The peak velocity uses shorter windows to capture the highest momentum,
    while current velocity uses longer windows for stability.

    Example Configuration:
    - Peak velocity: ultra-fast window (5s vs 20-15s ago)
    - Current velocity: normal window (10s vs 40-30s ago)

    Returns:
    - Value < -50%: Strong reversal (dump likely starting)
    - Value < -30%: Moderate reversal (momentum weakening)
    - Value ~ 0: Stable momentum
    - Value > 0: Accelerating (rare after peak)
    """

    def get_indicator_type(self) -> str:
        return "MOMENTUM_REVERSAL_INDEX"

    def get_name(self) -> str:
        return "Momentum Reversal Index"

    def get_description(self) -> str:
        return "Detects pump-to-dump transition via velocity momentum shift analysis"

    def get_category(self) -> str:
        return "general"  # Used in O1 Cancel and ZE1 Close sections

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
            # Current velocity parameters
            VariantParameter(
                "t1_current",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Length of current price window in seconds"
            ),
            VariantParameter(
                "t3_current",
                "float",
                40.0,
                1.0,
                86400.0,
                None,
                True,
                "Baseline lookback for current velocity in seconds"
            ),
            VariantParameter(
                "d_current",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Baseline window length for current velocity in seconds"
            ),
            # Peak velocity parameters
            VariantParameter(
                "t1_peak",
                "float",
                5.0,
                1.0,
                3600.0,
                None,
                True,
                "Length of peak price window in seconds (shorter = captures peak better)"
            ),
            VariantParameter(
                "t3_peak",
                "float",
                20.0,
                1.0,
                86400.0,
                None,
                True,
                "Baseline lookback for peak velocity in seconds"
            ),
            VariantParameter(
                "d_peak",
                "float",
                5.0,
                1.0,
                3600.0,
                None,
                True,
                "Baseline window length for peak velocity in seconds"
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
        """Default refresh: 1 second for momentum monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use shortest window for refresh
        t1_current = params.get_float("t1_current", 10.0)
        t1_peak = params.get_float("t1_peak", 5.0)
        min_t1 = min(t1_current, t1_peak)

        if min_t1 <= 10.0:
            return 1.0
        elif min_t1 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        MOMENTUM_REVERSAL_INDEX is time-driven.

        Requires regular recalculation to track velocity changes.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the four windows needed for momentum reversal calculation.

        Returns:
            Four WindowSpec objects:
            [current_window, current_baseline, peak_window, peak_baseline]
        """
        t1_current = params.get_float("t1_current", 10.0)
        t3_current = params.get_float("t3_current", 40.0)
        d_current = params.get_float("d_current", 10.0)

        t1_peak = params.get_float("t1_peak", 5.0)
        t3_peak = params.get_float("t3_peak", 20.0)
        d_peak = params.get_float("d_peak", 5.0)

        return [
            # Current velocity windows
            WindowSpec(t1_current, 0),                          # Current window
            WindowSpec(t3_current, t3_current - d_current),     # Current baseline

            # Peak velocity windows
            WindowSpec(t1_peak, 0),                             # Peak window
            WindowSpec(t3_peak, t3_peak - d_peak),              # Peak baseline
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate MOMENTUM_REVERSAL_INDEX from four price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate current velocity from windows[0] and windows[1]
        2. Calculate peak velocity from windows[2] and windows[3]
        3. Return reversal index: (current - peak) / abs(peak) * 100

        Args:
            data_windows: [current_window, current_baseline, peak_window, peak_baseline]
            params: Algorithm parameters

        Returns:
            Reversal index percentage or None if cannot calculate
        """
        if len(data_windows) != 4:
            return None

        # Windows for current velocity
        current_window = data_windows[0]
        current_baseline = data_windows[1]

        # Windows for peak velocity
        peak_window = data_windows[2]
        peak_baseline = data_windows[3]

        # Calculate current velocity
        current_velocity = self._calculate_velocity(
            current_window,
            current_baseline
        )

        # Calculate peak velocity
        peak_velocity = self._calculate_velocity(
            peak_window,
            peak_baseline
        )

        if current_velocity is None or peak_velocity is None:
            return None

        # Avoid division by zero
        if abs(peak_velocity) < 0.001:
            return None

        # Calculate reversal index
        # Negative = current velocity lower than peak (reversal)
        # Positive = current velocity higher than peak (unlikely)
        reversal_index = ((current_velocity - peak_velocity) / abs(peak_velocity)) * 100.0

        return reversal_index

    def _calculate_velocity(
        self,
        current_window: DataWindow,
        baseline_window: DataWindow
    ) -> Optional[float]:
        """
        Calculate velocity from two price windows.

        This is the same calculation as PRICE_VELOCITY indicator.
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

        # Calculate velocity
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
        if len(windows) != 4:
            return None

        # Convert to DataWindow format
        data_windows = []
        for window_data, start_ts, end_ts in windows:
            data_windows.append(DataWindow(window_data, start_ts, end_ts, "price"))

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get four price windows from engine for calculation."""
        t1_current = params.get_float("t1_current", 10.0)
        t3_current = params.get_float("t3_current", 40.0)
        d_current = params.get_float("d_current", 10.0)

        t1_peak = params.get_float("t1_peak", 5.0)
        t3_peak = params.get_float("t3_peak", 20.0)
        d_peak = params.get_float("d_peak", 5.0)

        # Get windows for current velocity
        current_window = engine._get_price_series_for_window(indicator, t1_current, 0)
        current_baseline = engine._get_price_series_for_window(
            indicator, t3_current, t3_current - d_current
        )

        # Get windows for peak velocity
        peak_window = engine._get_price_series_for_window(indicator, t1_peak, 0)
        peak_baseline = engine._get_price_series_for_window(
            indicator, t3_peak, t3_peak - d_peak
        )

        return [current_window, current_baseline, peak_window, peak_baseline]


# Create instance for auto-discovery registration
momentum_reversal_index_algorithm = MomentumReversalIndexAlgorithm()
