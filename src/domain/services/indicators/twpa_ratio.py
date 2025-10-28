"""
TWPA Ratio Algorithm Implementation
==================================
Calculates ratio between two TWPA values: TWPA(t1,t2) / TWPA(t3,t4)
"""

from typing import List, Optional, Sequence, Tuple
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .twpa import twpa_algorithm


class TWPARatioAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    TWPA Ratio Algorithm: TWPA(t1,t2) / TWPA(t3,t4)
    
    Calculates the ratio between two time-weighted price averages over different windows.
    Useful for comparing recent vs historical price trends.
    
    Parameters:
    - t1, t2: First TWPA window (numerator)
    - t3, t4: Second TWPA window (denominator) 
    - r: Refresh interval override
    """
    
    def get_indicator_type(self) -> str:
        return "TWPA_RATIO"
    
    def get_name(self) -> str:
        return "TWPA Ratio"
    
    def get_description(self) -> str:
        return "Ratio between two Time-Weighted Price Averages: TWPA(t1,t2) / TWPA(t3,t4)"
    
    def get_category(self) -> str:
        return "general"
    
    def get_parameters(self) -> List:
        """Return parameter definitions for TWPA Ratio."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "t1",
                "float", 
                300.0,
                1.0,
                86400.0,
                None,
                True,
                "First window start time in seconds ago (numerator)"
            ),
            VariantParameter(
                "t2", 
                "float",
                60.0,
                0.0,
                86400.0,
                None,
                True,
                "First window end time in seconds ago (numerator)"
            ),
            VariantParameter(
                "t3",
                "float",
                1800.0,  # 30 minutes
                1.0,
                86400.0,
                None,
                True,
                "Second window start time in seconds ago (denominator)"
            ),
            VariantParameter(
                "t4",
                "float",
                300.0,   # 5 minutes
                0.0,
                86400.0,
                None,
                True,
                "Second window end time in seconds ago (denominator)"
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
            VariantParameter(
                "min_denominator",
                "float",
                0.001,
                0.0001,
                1.0,
                None,
                False,
                "Minimum denominator value to avoid division by zero"
            )
        ]
    
    def get_default_refresh_interval(self) -> float:
        """Default refresh based on shortest window."""
        return 2.0  # Reasonable default for ratio calculations
    
    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """
        Calculate refresh interval based on window parameters.

        For ratio calculations, use the more frequent of the two TWPA intervals.
        """
        override = params.get_refresh_override()
        if override:
            return max(self.get_min_refresh_interval(),
                      min(self.get_max_refresh_interval(), float(override)))

        # Calculate recommended intervals for both windows
        t1 = params.get_float("t1", 300.0)
        t2 = params.get_float("t2", 60.0)
        t3 = params.get_float("t3", 1800.0)
        t4 = params.get_float("t4", 300.0)

        interval1 = twpa_algorithm.calculate_refresh_interval(IndicatorParameters({"t1": t1, "t2": t2}))
        interval2 = twpa_algorithm.calculate_refresh_interval(IndicatorParameters({"t1": t3, "t2": t4}))

        # Use the more frequent interval (shorter time)
        return min(interval1, interval2)

    def is_time_driven(self) -> bool:
        """
        TWPA_RATIO MUST be time-driven.

        TWPA_RATIO calculates the ratio between two TWPA values, and since TWPA
        is time-driven, TWPA_RATIO must also be time-driven to maintain consistency.

        Both component TWPAs require regular recalculation on wall-clock schedule,
        therefore the ratio must be recalculated on the same schedule.

        Returns:
            Always True - TWPA_RATIO requires time-driven scheduling
        """
        return True

    # ========================================
    # NEW PURE FUNCTION INTERFACE
    # ========================================

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for TWPA ratio calculation.

        Returns:
            Two WindowSpec objects: [numerator_window, denominator_window]
        """
        t1 = params.get_float("t1", 300.0)
        t2 = params.get_float("t2", 60.0)
        t3 = params.get_float("t3", 1800.0)
        t4 = params.get_float("t4", 300.0)

        return [
            WindowSpec(t1, t2),  # Window 1: numerator
            WindowSpec(t3, t4),  # Window 2: denominator
        ]

    def calculate_from_windows(self,
                               data_windows: List[DataWindow],
                               params: IndicatorParameters) -> Optional[float]:
        """
        Calculate TWPA ratio using two pre-prepared data windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Args:
            data_windows: [window1, window2] pre-prepared by engine
            params: Algorithm parameters

        Returns:
            TWPA ratio or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        window1 = data_windows[0]
        window2 = data_windows[1]

        # Calculate both TWPA values using pure function
        twpa1 = twpa_algorithm._compute_twpa(window1.data, window1.start_ts, window1.end_ts)
        twpa2 = twpa_algorithm._compute_twpa(window2.data, window2.start_ts, window2.end_ts)

        if twpa1 is None or twpa2 is None:
            return None

        # Avoid division by zero
        min_denominator = params.get_float("min_denominator", 0.001)
        if abs(twpa2) < min_denominator:
            return None

        return twpa1 / twpa2

    # ========================================
    # OLD INTERFACE (kept for backward compatibility)
    # ========================================

    def calculate_multi_window(self, 
                              windows: List[Tuple[Sequence[Tuple[float, float]], float, float]], 
                              params: IndicatorParameters) -> Optional[float]:
        """
        Calculate TWPA ratio using two windows.
        
        Args:
            windows: [(window1_data, start1, end1), (window2_data, start2, end2)]
            params: Algorithm parameters
        """
        if len(windows) != 2:
            return None
        
        window1_data, start1, end1 = windows[0]
        window2_data, start2, end2 = windows[1]
        
        # Calculate both TWPA values
        twpa1 = twpa_algorithm._compute_twpa(window1_data, start1, end1)
        twpa2 = twpa_algorithm._compute_twpa(window2_data, start2, end2)
        
        if twpa1 is None or twpa2 is None:
            return None
        
        # Avoid division by zero
        min_denominator = params.get_float("min_denominator", 0.001)
        if abs(twpa2) < min_denominator:
            return None
        
        return twpa1 / twpa2
    
    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get two data windows for TWPA ratio calculation."""
        t1 = params.get_float("t1", 300.0)
        t2 = params.get_float("t2", 60.0)
        t3 = params.get_float("t3", 1800.0)
        t4 = params.get_float("t4", 300.0)
        
        # Get both windows
        window1 = engine._get_price_series_for_window(indicator, t1, t2)
        window2 = engine._get_price_series_for_window(indicator, t3, t4)
        
        return [window1, window2]


# Create instance for registration
twpa_ratio_algorithm = TWPARatioAlgorithm()