"""
LIQUIDITY_DRAIN_INDEX Algorithm Implementation
=============================================
Detects aggressive buying by measuring liquidity drainage from order book.

During pump, aggressive buyers "eat" the ask-side liquidity, causing
liquidity to drop significantly before price rises sharply.

Formula: ((baseline_liquidity - current_liquidity) / baseline_liquidity) * 100

Where:
- current_liquidity = average total liquidity in recent window
- baseline_liquidity = average total liquidity in historical window
- total_liquidity = sum of bid and ask liquidity (USDT value)

This is an EARLY WARNING indicator - liquidity drains BEFORE major price moves.
"""

from typing import List, Optional
from .base_algorithm import (
    MultiWindowIndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_simple_average


class LiquidityDrainIndexAlgorithm(MultiWindowIndicatorAlgorithm):
    """
    LIQUIDITY_DRAIN_INDEX: Early warning via liquidity drainage detection.

    Detects when aggressive buyers are consuming order book liquidity,
    which typically precedes major price moves (pump).

    High drain percentage indicates:
    - Aggressive buying pressure
    - Liquidity being consumed
    - Potential pump incoming

    Parameters:
    - t1: Length of current liquidity window in seconds (default: 30s)
    - t2: End of current window in seconds ago (default: 0 = now)
    - t3: Start of baseline liquidity window in seconds ago (default: 600s)
    - t4: End of baseline window in seconds ago (default: 30s)
    - min_baseline: Minimum baseline to avoid division by zero (default: 100 USDT)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=30, t2=0, t3=600, t4=30:
      - Current: avg liquidity in last 30 seconds
      - Baseline: avg liquidity from 10min ago to 30s ago
      - Compares recent vs historical liquidity

    Returns:
    - Positive value: Liquidity draining (potential pump signal)
    - Negative value: Liquidity increasing
    - 0: No significant change
    - Values > 30% indicate significant drain
    """

    def get_indicator_type(self) -> str:
        return "LIQUIDITY_DRAIN_INDEX"

    def get_name(self) -> str:
        return "Liquidity Drain Index"

    def get_description(self) -> str:
        return "Detects aggressive buying via order book liquidity drainage - early pump warning"

    def get_category(self) -> str:
        return "general"  # Used in S1 Signal Detection for early warning

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
                30.0,  # Current window: last 30 seconds
                1.0,
                3600.0,
                None,
                True,
                "Length of current liquidity window in seconds"
            ),
            VariantParameter(
                "t2",
                "float",
                0.0,  # Current window ends now
                0.0,
                3600.0,
                None,
                True,
                "End of current window in seconds ago (0 = now)"
            ),
            VariantParameter(
                "t3",
                "float",
                600.0,  # Baseline: 10 minutes back
                1.0,
                86400.0,
                None,
                True,
                "Start of baseline liquidity window in seconds ago"
            ),
            VariantParameter(
                "t4",
                "float",
                30.0,  # Baseline ends 30s ago
                0.0,
                86400.0,
                None,
                True,
                "End of baseline window in seconds ago"
            ),
            VariantParameter(
                "min_baseline",
                "float",
                100.0,  # 100 USDT minimum baseline
                1.0,
                10000.0,
                None,
                False,
                "Minimum baseline liquidity (USDT) to avoid division by zero"
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
        """Default refresh: 2 seconds for liquidity monitoring."""
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
        LIQUIDITY_DRAIN_INDEX is time-driven.

        Liquidity windows slide with time and need regular recalculation
        to track order book state changes.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the two windows needed for liquidity drain calculation.

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
            WindowSpec(t1, t2),  # Current liquidity window
            WindowSpec(t3, t4),  # Baseline liquidity window
        ]

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate LIQUIDITY_DRAIN_INDEX from two orderbook windows.

        PURE FUNCTION: No engine dependency, thread-safe, easy to test.

        Algorithm:
        1. Calculate average total liquidity in current window
        2. Calculate average total liquidity in baseline window
        3. Return drain percentage: (baseline - current) / baseline * 100

        Args:
            data_windows: [current_window, baseline_window]
                         Both should contain orderbook data with liquidity info
            params: Algorithm parameters

        Returns:
            Drain percentage or None if cannot calculate
        """
        if len(data_windows) != 2:
            return None

        current_window = data_windows[0]
        baseline_window = data_windows[1]

        # Calculate average liquidity for current window
        current_liquidity = self._calculate_average_total_liquidity(
            current_window.data,
            current_window.start_ts,
            current_window.end_ts
        )

        # Calculate average liquidity for baseline window
        baseline_liquidity = self._calculate_average_total_liquidity(
            baseline_window.data,
            baseline_window.start_ts,
            baseline_window.end_ts
        )

        # Validate both calculations succeeded
        if current_liquidity is None or baseline_liquidity is None:
            return None

        # Avoid division by zero
        min_baseline = params.get_float("min_baseline", 100.0)
        if baseline_liquidity < min_baseline:
            return None

        # Calculate drain percentage
        # Positive = liquidity draining (baseline > current)
        # Negative = liquidity increasing (current > baseline)
        drain_pct = ((baseline_liquidity - current_liquidity) / baseline_liquidity) * 100.0

        return drain_pct

    def _calculate_average_total_liquidity(
        self,
        orderbook_data: List[tuple],
        start_ts: float,
        end_ts: float
    ) -> Optional[float]:
        """
        Calculate average total liquidity from orderbook data.

        Total liquidity = bid_liquidity + ask_liquidity

        For orderbook data format:
        - If tuple: (timestamp, bid_qty, ask_qty, best_bid, best_ask, ...)
        - Total liquidity approximated as: (bid_qty * best_bid) + (ask_qty * best_ask)

        Args:
            orderbook_data: List of orderbook snapshots
            start_ts: Window start timestamp
            end_ts: Window end timestamp

        Returns:
            Average total liquidity (USDT) or None if no data
        """
        if not orderbook_data:
            return None

        total_liquidity_sum = 0.0
        count = 0

        for entry in orderbook_data:
            # Handle different orderbook data formats
            if isinstance(entry, dict):
                # Dictionary format: {"timestamp": ts, "bid_qty": ..., "ask_qty": ..., ...}
                timestamp = entry.get("timestamp", 0)

                if start_ts <= timestamp <= end_ts:
                    bid_qty = float(entry.get("bid_qty", 0.0))
                    ask_qty = float(entry.get("ask_qty", 0.0))
                    best_bid = float(entry.get("best_bid", 0.0))
                    best_ask = float(entry.get("best_ask", 0.0))

                    # Calculate USDT liquidity
                    bid_liquidity = bid_qty * best_bid
                    ask_liquidity = ask_qty * best_ask
                    total_liquidity = bid_liquidity + ask_liquidity

                    total_liquidity_sum += total_liquidity
                    count += 1

            elif isinstance(entry, tuple) and len(entry) >= 5:
                # Tuple format: (timestamp, best_bid, best_ask, bid_qty, ask_qty, ...)
                timestamp = entry[0]

                if start_ts <= timestamp <= end_ts:
                    best_bid = float(entry[1])
                    best_ask = float(entry[2])
                    bid_qty = float(entry[3])
                    ask_qty = float(entry[4])

                    # Calculate USDT liquidity
                    bid_liquidity = bid_qty * best_bid
                    ask_liquidity = ask_qty * best_ask
                    total_liquidity = bid_liquidity + ask_liquidity

                    total_liquidity_sum += total_liquidity
                    count += 1

        if count == 0:
            return None

        # Return average total liquidity
        return total_liquidity_sum / count

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
            DataWindow(current_data, current_start, current_end, "orderbook"),
            DataWindow(baseline_data, baseline_start, baseline_end, "orderbook"),
        ]

        return self.calculate_from_windows(data_windows, params)

    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """
        Get two orderbook windows from engine for calculation.
        """
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)
        t3 = params.get_float("t3", 600.0)
        t4 = params.get_float("t4", 30.0)

        # Get orderbook data windows
        current_window = engine._get_orderbook_series_for_window(indicator, t1, t2)
        baseline_window = engine._get_orderbook_series_for_window(indicator, t3, t4)

        return [current_window, baseline_window]


# Create instance for auto-discovery registration
liquidity_drain_index_algorithm = LiquidityDrainIndexAlgorithm()
