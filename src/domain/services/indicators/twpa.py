"""Dedicated implementation for the Time-Weighted Price Average indicator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple, List, Any, Dict
from .base_algorithm import IndicatorAlgorithm, IndicatorParameters


@dataclass(frozen=True)
class TWPAComputationContext:
    """Encapsulate window metadata for TWPA calculations."""

    t1: float
    t2: float
    refresh_override: Optional[float] = None

    @property
    def window_span(self) -> float:
        return max(0.0, self.t1 - self.t2)


class TWPAAlgorithm(IndicatorAlgorithm):
    """
    Time-Weighted Price Average Algorithm
    ===================================
    Unified implementation using the algorithm interface.
    
    This is the ONLY way to use TWPA - no legacy static methods.
    """
    
    def get_indicator_type(self) -> str:
        return "TWPA"
    
    def get_name(self) -> str:
        return "Time Weighted Price Average"
    
    def get_description(self) -> str:
        return "Average price weighted by time over specified window"
    
    def get_category(self) -> str:
        return "general"
    
    def get_parameters(self) -> List:
        """Return variant parameter definitions for registration."""
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
                "Start time window in seconds ago (e.g., 300 = 5 minutes ago). Minimum 1 second.",
            ),
            VariantParameter(
                "t2",
                "float",
                0.0,
                0.0,
                86400.0,
                None,
                True,
                "End time window in seconds ago (e.g., 0 = now)",
            ),
            VariantParameter(
                "refresh_interval_seconds",
                "float",
                None,
                0.5,
                3600.0,
                None,
                False,
                "Optional manual override for refresh cadence in seconds",
            ),
        ]
    
    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate TWPA-specific refresh interval based on window parameters."""
        override = params.get_refresh_override()
        if override:
            return max(self.get_min_refresh_interval(), 
                      min(self.get_max_refresh_interval(), float(override)))
        
        t1 = params.get_float("t1", 60.0)
        t2 = params.get_float("t2", 0.0)
        
        return self._calculate_recommended_refresh_interval(t1, t2)
    
    def _calculate_recommended_refresh_interval(self, t1: float, t2: float) -> float:
        """
        Determine refresh cadence in seconds for a TWPA window.
        
        Rules:
        - Touching present (t2 == 0) must refresh every second
        - Short offsets refresh frequently, longer look-backs can refresh less often
        """
        if t2 <= 1.0:
            return 1.0
        if t2 <= 30.0:
            return 2.0
        if t2 <= 120.0:
            return 5.0
        if t2 <= 600.0:
            return 10.0
        if t2 <= 1800.0:
            return 15.0
        return 30.0
    
    def calculate_cache_bucket_seconds(self, t1: float, t2: float, refresh_interval: float) -> int:
        """
        Select cache bucket granularity for TWPA.

        Ensures buckets never exceed the refresh cadence so the scheduler
        can observe fresh values on each recompute.
        """
        candidate = max(1, int(round(refresh_interval)))

        # Ultra-short windows should never use buckets larger than one second
        if t2 <= 1.0:
            return 1

        # Cap cache buckets to 60 seconds
        return min(candidate, 60)

    def is_time_driven(self) -> bool:
        """
        TWPA MUST be time-driven.

        TWPA calculates time-weighted price averages over sliding time windows.
        It MUST be recalculated on a regular schedule (e.g., every second) to provide
        continuous time-series data, independent of whether new market data arrives.

        Example:
            If refresh_interval=1s, TWPA should be calculated at:
            t=0s, t=1s, t=2s, t=3s, ...
            even if market data only arrives at t=0s, t=5s, t=10s

        Returns:
            Always True - TWPA requires time-driven scheduling
        """
        return True

    def calculate(self, 
                 data: Sequence[Tuple[float, float]], 
                 start_ts: float, 
                 end_ts: float, 
                 params: IndicatorParameters) -> Optional[float]:
        """Calculate TWPA value using the unified interface."""
        return self._compute_twpa(data, start_ts, end_ts)
    
    @staticmethod
    def _compute_twpa(window_points: Sequence[Tuple[float, float]], start_ts: float, end_ts: float) -> Optional[float]:
        """
        Compute the time-weighted average price over the inclusive window [start_ts, end_ts].

        CRITICAL REQUIREMENT: window_points MUST include one transaction before start_ts.
        This is required to calculate the duration of the first price in the window.

        Algorithm:
        1. For each price point, calculate how long that price was valid in the window
        2. Weight each price by its duration
        3. Return weighted average

        Example:
            Data: [(50, 1.00), (110, 2.00), (130, 3.00)]
            Window: [100, 120]

            Point 50 (before window):
                - Valid from max(50, 100) = 100 to min(110, 120) = 110
                - Duration: 10s, Price: 1.00

            Point 110 (in window):
                - Valid from max(110, 100) = 110 to 120 (end)
                - Duration: 10s, Price: 2.00

            TWPA = (1.00*10 + 2.00*10) / 20 = 1.50

        Parameters
        ----------
        window_points:
            Iterable of (timestamp, price) tuples sorted in ascending timestamp order.
            MUST include at least one point before start_ts (if such point exists).
        start_ts:
            Inclusive start of the evaluation range (epoch seconds).
        end_ts:
            Inclusive end of the evaluation range (epoch seconds).

        Returns
        -------
        float or None:
            Time-weighted average price, or None if insufficient data.
        """
        if not window_points:
            return None

        weighted_sum = 0.0
        total_weight = 0.0

        for idx, (timestamp, price) in enumerate(window_points):
            # Clip timestamp to window start (handles pre-window point)
            ts_i = max(timestamp, start_ts)

            # Determine when this price stops being valid
            if idx == len(window_points) - 1:
                # Last point: valid until end of window
                ts_next = end_ts
            else:
                # Middle point: valid until next price or end of window
                ts_next = min(window_points[idx + 1][0], end_ts)

            # Skip if this point doesn't contribute to the window
            if ts_next <= ts_i:
                continue

            # Calculate time-weighted contribution
            duration = ts_next - ts_i
            total_weight += duration
            weighted_sum += price * duration

        if total_weight <= 0.0 or math.isclose(total_weight, 0.0, abs_tol=1e-12):
            return None

        return weighted_sum / total_weight


# Export ONLY the algorithm instance - no static class!
twpa_algorithm = TWPAAlgorithm()
