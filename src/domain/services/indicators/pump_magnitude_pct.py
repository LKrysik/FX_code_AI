"""
PUMP_MAGNITUDE_PCT Algorithm Implementation
==========================================
Calculates pump magnitude as percentage change between current and baseline TWPA.

Formula: ((current_twpa - baseline_twpa) / baseline_twpa) * 100

Where:
- current_twpa = TWPA(t1, 0)  - recent price average
- baseline_twpa = TWPA(t3, t3-d) - historical baseline price

This uses TWPA instead of raw prices to reduce noise and false signals.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class PumpMagnitudePctAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    PUMP_MAGNITUDE_PCT: Percentage price increase from baseline to current.

    Detects pump conditions by comparing:
    - Current price level (TWPA over recent window)
    - Baseline price level (TWPA over historical window)

    Parameters:
    - t1: Length of current price window in seconds (default: 10s)
    - t3: How far back to look for baseline start (default: 60s)
    - d: Length of baseline window in seconds (default: 30s)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=10, t3=60, d=30 means:
      - Current: TWPA from 10s ago to now
      - Baseline: TWPA from 60s ago to 30s ago
      - Compares recent 10s vs historical 30s window

    Returns:
    - Positive value: Price increased (pump detected)
    - Negative value: Price decreased
    - ~0: No significant change
    """

    def get_indicator_type(self) -> str:
        return "PUMP_MAGNITUDE_PCT"

    def get_name(self) -> str:
        return "Pump Magnitude Percentage"

    def get_description(self) -> str:
        return "Percentage price change from baseline TWPA to current TWPA - detects pump conditions"

    def get_category(self) -> str:
        return "general"  # Used in S1 Signal Detection

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
                10.0,  # 10 seconds current window
                1.0,
                3600.0,
                None,
                True,
                "Length of current price window in seconds (e.g., 10 = last 10 seconds)"
            ),
            VariantParameter(
                "t3",
                "float",
                60.0,  # Look back 60 seconds for baseline
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
        """Default refresh: 1 second for real-time pump detection."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use shortest window for refresh cadence
        t1 = params.get_float("t1", 10.0)

        # For very short windows, refresh every second
        if t1 <= 10.0:
            return 1.0
        elif t1 <= 30.0:
            return 2.0
        elif t1 <= 60.0:
            return 5.0
        else:
            return 10.0

    def is_time_driven(self) -> bool:
        """
        PUMP_MAGNITUDE_PCT is time-driven.

        Uses TWPAs which require regular time-based recalculation
        to track sliding windows accurately.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for pump magnitude calculation.

        Returns:
            Two WindowSpec objects: [current_window, baseline_window]
        """
        t1 = params.get_float("t1", 10.0)
        t3 = params.get_float("t3", 60.0)
        d = params.get_float("d", 30.0)

        # Validate: baseline window must be in the past
        if t3 < d:
            raise ValueError(
                f"Invalid window configuration: t3 ({t3}) must be >= d ({d}). "
                f"Baseline window would extend into future."
            )

        return [
            WindowSpec(t1, 0),      # Current window: t1 seconds ago to now
            WindowSpec(t3, t3 - d), # Baseline window: t3 seconds ago to (t3-d) seconds ago
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate PUMP_MAGNITUDE_PCT from two price windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Args:
            data_windows: [current_window, baseline_window]
            params: Algorithm parameters

        Returns:
            Pump magnitude percentage or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        baseline_window = data_windows[1]

        # Calculate TWPA for current price
        current_twpa = compute_time_weighted_average(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        # Calculate TWPA for baseline price
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

        # Calculate percentage change
        magnitude_pct = ((current_twpa - baseline_twpa) / baseline_twpa) * 100.0

        return magnitude_pct

    def calculate_multi_window(
        self,
        windows: List[tuple],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        OLD INTERFACE: Backward compatibility wrapper.

        Converts old-style windows to new DataWindow format and delegates
        to calculate_from_windows().
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
pump_magnitude_pct_algorithm = PumpMagnitudePctAlgorithm()
