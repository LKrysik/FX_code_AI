"""
DUMP_EXHAUSTION_SCORE Algorithm Implementation
=============================================
Multi-factor score to detect when dump is exhausting (ending).

Combines multiple signals to identify dump completion:
- Velocity near zero (price stabilizing)
- Volume returned to baseline (selling pressure ended)
- Deep retracement achieved (40-60% typical)
- Bid-ask imbalance neutral or positive (buyers returning)

Formula: Weighted score from 4 factors, range [0, 100]

High score (>= 70) indicates dump likely complete, good time to close short.
"""

from typing import List, Optional
from .base_algorithm import (
    IndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import (
    compute_time_weighted_average,
    compute_volume_average,
    compute_volume_median
)


class DumpExhaustionScoreAlgorithm(IndicatorAlgorithm):
    """
    DUMP_EXHAUSTION_SCORE: Multi-factor detection of dump completion.

    Analyzes 4 key factors to determine if dump has exhausted:

    1. Velocity Stabilization (30 points):
       - Velocity close to 0 = price movement stopped
       - Threshold: abs(velocity) < 0.1% per second

    2. Volume Normalization (25 points):
       - Volume returned to baseline levels
       - Threshold: current_volume < baseline * 0.8

    3. Retracement Depth (25 points):
       - Sufficient price correction from peak
       - Threshold: retracement >= 40%

    4. Bid-Ask Balance (20 points):
       - Selling pressure dissipated
       - Threshold: imbalance > -10%

    Score >= 70: Dump exhaustion confirmed
    Score >= 50: Dump weakening
    Score < 50: Dump still active

    Parameters:
    - velocity_t1, velocity_t3, velocity_d: Velocity calculation windows
    - volume_t1, volume_t2: Current volume window
    - volume_t3, volume_t4: Baseline volume window
    - imbalance_t1, imbalance_t2: Imbalance window
    - peak_price: Peak price to calculate retracement (required)
    - current_price: Current price (required)
    - r: Refresh interval override

    Returns:
    - Score 0-100 indicating dump exhaustion level
    """

    def get_indicator_type(self) -> str:
        return "DUMP_EXHAUSTION_SCORE"

    def get_name(self) -> str:
        return "Dump Exhaustion Score"

    def get_description(self) -> str:
        return "Multi-factor score detecting dump completion - combines velocity, volume, retracement, and imbalance"

    def get_category(self) -> str:
        return "general"  # Used in ZE1 Close section

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            # Velocity parameters
            VariantParameter(
                "velocity_t1",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Velocity current window length (seconds)"
            ),
            VariantParameter(
                "velocity_t3",
                "float",
                40.0,
                1.0,
                86400.0,
                None,
                True,
                "Velocity baseline lookback (seconds)"
            ),
            VariantParameter(
                "velocity_d",
                "float",
                10.0,
                1.0,
                3600.0,
                None,
                True,
                "Velocity baseline window length (seconds)"
            ),

            # Volume parameters
            VariantParameter(
                "volume_t1",
                "float",
                30.0,
                1.0,
                3600.0,
                None,
                True,
                "Current volume window start (seconds ago)"
            ),
            VariantParameter(
                "volume_t2",
                "float",
                0.0,
                0.0,
                3600.0,
                None,
                True,
                "Current volume window end (seconds ago)"
            ),
            VariantParameter(
                "volume_t3",
                "float",
                600.0,
                1.0,
                86400.0,
                None,
                True,
                "Baseline volume window start (seconds ago)"
            ),
            VariantParameter(
                "volume_t4",
                "float",
                30.0,
                0.0,
                86400.0,
                None,
                True,
                "Baseline volume window end (seconds ago)"
            ),

            # Imbalance parameters
            VariantParameter(
                "imbalance_t1",
                "float",
                30.0,
                1.0,
                3600.0,
                None,
                True,
                "Imbalance window length (seconds)"
            ),
            VariantParameter(
                "imbalance_t2",
                "float",
                0.0,
                0.0,
                3600.0,
                None,
                True,
                "Imbalance window end (seconds ago)"
            ),

            # Price context (for retracement calculation)
            VariantParameter(
                "peak_price",
                "float",
                None,
                None,
                None,
                None,
                True,
                "Peak price for retracement calculation (required)"
            ),
            VariantParameter(
                "current_price",
                "float",
                None,
                None,
                None,
                None,
                True,
                "Current price for retracement calculation (required)"
            ),

            # Thresholds (tunable)
            VariantParameter(
                "velocity_threshold",
                "float",
                0.1,
                0.01,
                1.0,
                None,
                False,
                "Velocity stabilization threshold (% per second)"
            ),
            VariantParameter(
                "volume_threshold",
                "float",
                0.8,
                0.1,
                2.0,
                None,
                False,
                "Volume normalization threshold (ratio to baseline)"
            ),
            VariantParameter(
                "retracement_threshold",
                "float",
                40.0,
                10.0,
                90.0,
                None,
                False,
                "Minimum retracement percentage for points"
            ),
            VariantParameter(
                "imbalance_threshold",
                "float",
                -10.0,
                -50.0,
                50.0,
                None,
                False,
                "Bid-ask imbalance threshold (sell pressure dissipated)"
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
        """Default refresh: 2 seconds for exhaustion monitoring."""
        return 2.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Use shortest window for refresh
        velocity_t1 = params.get_float("velocity_t1", 10.0)
        if velocity_t1 <= 10.0:
            return 1.0
        elif velocity_t1 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        DUMP_EXHAUSTION_SCORE is time-driven.

        Requires regular recalculation to track changing market conditions.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify windows needed for exhaustion score calculation.

        Returns:
            List of WindowSpec objects for:
            - Velocity current/baseline (2 windows)
            - Volume current/baseline (2 windows)
            - Imbalance (1 window)
            - Orderbook (1 window)
        """
        # Velocity windows
        v_t1 = params.get_float("velocity_t1", 10.0)
        v_t3 = params.get_float("velocity_t3", 40.0)
        v_d = params.get_float("velocity_d", 10.0)

        # Volume windows
        vol_t1 = params.get_float("volume_t1", 30.0)
        vol_t2 = params.get_float("volume_t2", 0.0)
        vol_t3 = params.get_float("volume_t3", 600.0)
        vol_t4 = params.get_float("volume_t4", 30.0)

        # Imbalance window
        imb_t1 = params.get_float("imbalance_t1", 30.0)
        imb_t2 = params.get_float("imbalance_t2", 0.0)

        return [
            # Velocity windows (price data)
            WindowSpec(v_t1, 0),           # [0] Velocity current
            WindowSpec(v_t3, v_t3 - v_d),  # [1] Velocity baseline

            # Volume windows (volume data)
            WindowSpec(vol_t1, vol_t2),    # [2] Volume current
            WindowSpec(vol_t3, vol_t4),    # [3] Volume baseline

            # Imbalance window (orderbook data)
            WindowSpec(imb_t1, imb_t2),    # [4] Imbalance window
        ]

    def calculate(self, data, start_ts, end_ts, params: IndicatorParameters) -> Optional[float]:
        """Not used - use calculate_from_windows instead."""
        raise NotImplementedError("Use calculate_from_windows for DUMP_EXHAUSTION_SCORE")

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate DUMP_EXHAUSTION_SCORE from multiple data windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Args:
            data_windows: List of DataWindow objects
                [0, 1]: Price windows for velocity
                [2, 3]: Volume windows
                [4]: Orderbook window for imbalance
            params: Algorithm parameters

        Returns:
            Exhaustion score (0-100) or None if cannot calculate
        """
        if len(data_windows) < 5:
            return None

        # Extract required parameters
        peak_price = params.get_float("peak_price", None)
        current_price = params.get_float("current_price", None)

        if peak_price is None or current_price is None:
            return None

        # Initialize score
        total_score = 0.0

        # Factor 1: Velocity Stabilization (30 points)
        velocity_score = self._calculate_velocity_score(
            data_windows[0], data_windows[1], params
        )
        if velocity_score is not None:
            total_score += velocity_score

        # Factor 2: Volume Normalization (25 points)
        volume_score = self._calculate_volume_score(
            data_windows[2], data_windows[3], params
        )
        if volume_score is not None:
            total_score += volume_score

        # Factor 3: Retracement Depth (25 points)
        retracement_score = self._calculate_retracement_score(
            peak_price, current_price, params
        )
        total_score += retracement_score

        # Factor 4: Bid-Ask Balance (20 points)
        imbalance_score = self._calculate_imbalance_score(
            data_windows[4], params
        )
        if imbalance_score is not None:
            total_score += imbalance_score

        return total_score

    def _calculate_velocity_score(
        self,
        current_window: DataWindow,
        baseline_window: DataWindow,
        params: IndicatorParameters
    ) -> Optional[float]:
        """Calculate velocity stabilization score (0-30 points)."""
        # Calculate current velocity
        current_twpa = compute_time_weighted_average(
            current_window.data, current_window.start_ts, current_window.end_ts
        )
        baseline_twpa = compute_time_weighted_average(
            baseline_window.data, baseline_window.start_ts, baseline_window.end_ts
        )

        if current_twpa is None or baseline_twpa is None or baseline_twpa == 0:
            return None

        # Calculate velocity
        price_change_pct = ((current_twpa - baseline_twpa) / baseline_twpa) * 100.0
        current_center = (current_window.start_ts + current_window.end_ts) / 2.0
        baseline_center = (baseline_window.start_ts + baseline_window.end_ts) / 2.0
        time_diff = current_center - baseline_center

        if time_diff <= 0:
            return None

        velocity = abs(price_change_pct / time_diff)

        # Score: lower velocity = higher score
        threshold = params.get_float("velocity_threshold", 0.1)

        if velocity < threshold:
            return 30.0  # Full points - velocity stabilized
        elif velocity < threshold * 2:
            return 15.0  # Half points - velocity decreasing
        else:
            return 0.0   # No points - still moving fast

    def _calculate_volume_score(
        self,
        current_window: DataWindow,
        baseline_window: DataWindow,
        params: IndicatorParameters
    ) -> Optional[float]:
        """Calculate volume normalization score (0-25 points)."""
        # Calculate volume averages
        current_volume = compute_volume_average(
            current_window.data, current_window.start_ts, current_window.end_ts
        )
        baseline_volume = compute_volume_median(
            baseline_window.data, baseline_window.start_ts, baseline_window.end_ts
        )

        if current_volume is None or baseline_volume is None or baseline_volume == 0:
            return None

        # Calculate ratio
        volume_ratio = current_volume / baseline_volume

        # Score: volume returned to baseline = higher score
        threshold = params.get_float("volume_threshold", 0.8)

        if volume_ratio < threshold:
            return 25.0  # Full points - volume normalized
        elif volume_ratio < threshold * 1.5:
            return 12.5  # Half points - volume decreasing
        else:
            return 0.0   # No points - volume still high

    def _calculate_retracement_score(
        self,
        peak_price: float,
        current_price: float,
        params: IndicatorParameters
    ) -> float:
        """Calculate retracement depth score (0-25 points)."""
        if peak_price == 0:
            return 0.0

        # Calculate retracement percentage
        retracement_pct = ((peak_price - current_price) / peak_price) * 100.0

        # Score: deeper retracement = higher score
        threshold = params.get_float("retracement_threshold", 40.0)

        if retracement_pct >= threshold:
            return 25.0  # Full points - deep retracement
        elif retracement_pct >= threshold * 0.7:
            return 12.5  # Half points - moderate retracement
        else:
            return 0.0   # No points - shallow retracement

    def _calculate_imbalance_score(
        self,
        imbalance_window: DataWindow,
        params: IndicatorParameters
    ) -> Optional[float]:
        """Calculate bid-ask balance score (0-20 points)."""
        # Calculate average imbalance
        if not imbalance_window.data:
            return None

        total_imbalance = 0.0
        count = 0

        for entry in imbalance_window.data:
            if isinstance(entry, dict):
                timestamp = entry.get("timestamp", 0)
                bid_qty = float(entry.get("bid_qty", 0.0))
                ask_qty = float(entry.get("ask_qty", 0.0))
            elif isinstance(entry, tuple) and len(entry) >= 5:
                timestamp = entry[0]
                bid_qty = float(entry[3])
                ask_qty = float(entry[4])
            else:
                continue

            # Only within window
            if imbalance_window.start_ts <= timestamp <= imbalance_window.end_ts:
                total_qty = bid_qty + ask_qty
                if total_qty > 0:
                    imbalance = ((bid_qty - ask_qty) / total_qty) * 100.0
                    total_imbalance += imbalance
                    count += 1

        if count == 0:
            return None

        avg_imbalance = total_imbalance / count

        # Score: imbalance > threshold = buyers returning
        threshold = params.get_float("imbalance_threshold", -10.0)

        if avg_imbalance > threshold:
            return 20.0  # Full points - sell pressure gone
        elif avg_imbalance > threshold - 20.0:
            return 10.0  # Half points - sell pressure weakening
        else:
            return 0.0   # No points - still strong sell pressure


# Create instance for auto-discovery registration
dump_exhaustion_score_algorithm = DumpExhaustionScoreAlgorithm()
