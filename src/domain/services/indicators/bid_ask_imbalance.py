"""
BID_ASK_IMBALANCE Algorithm Implementation
=========================================
Measures order book pressure by comparing bid vs ask quantities.

During pump: bid_qty >> ask_qty (strong buy pressure)
Before dump: ask_qty >> bid_qty (strong sell pressure)

Formula: ((bid_qty - ask_qty) / (bid_qty + ask_qty)) * 100

This indicator:
- Positive values: More bids than asks (buy pressure)
- Negative values: More asks than bids (sell pressure)
- Values near 0: Balanced order book

Uses time-weighted averaging to smooth out orderbook noise.
"""

from typing import List, Optional
from .base_algorithm import (
    IndicatorAlgorithm,
    IndicatorParameters,
    DataWindow,
    WindowSpec
)
from .window_calculations import compute_time_weighted_average


class BidAskImbalanceAlgorithm(IndicatorAlgorithm):
    """
    BID_ASK_IMBALANCE: Order book pressure indicator.

    Measures the imbalance between bid and ask quantities in the
    order book to detect buying/selling pressure.

    High positive values indicate:
    - Strong buy pressure (pump conditions)
    - Bids dominating the book
    - Potential price increase

    High negative values indicate:
    - Strong sell pressure (dump conditions)
    - Asks dominating the book
    - Potential price decrease

    Parameters:
    - t1: Window length in seconds (default: 30s)
    - t2: Window end in seconds ago (default: 0 = now)
    - smoothing: Apply time-weighted smoothing (default: true)
    - r: Refresh interval override (optional)

    Example Configuration:
    - t1=30, t2=0: Average imbalance over last 30 seconds

    Returns:
    - Value > +40%: Strong buy pressure (pump signal)
    - Value > +20%: Moderate buy pressure
    - Value ~0: Balanced
    - Value < -20%: Moderate sell pressure
    - Value < -40%: Strong sell pressure (dump signal)
    """

    def get_indicator_type(self) -> str:
        return "BID_ASK_IMBALANCE"

    def get_name(self) -> str:
        return "Bid-Ask Imbalance"

    def get_description(self) -> str:
        return "Order book pressure indicator via bid/ask quantity imbalance"

    def get_category(self) -> str:
        return "general"  # Used for pump/dump detection across all sections

    def get_parameters(self) -> List:
        """Return parameter definitions."""
        from ...types.indicator_types import VariantParameter

        return [
            VariantParameter(
                "t1",
                "float",
                30.0,  # 30 second window
                1.0,
                3600.0,
                None,
                True,
                "Window length in seconds for imbalance calculation"
            ),
            VariantParameter(
                "t2",
                "float",
                0.0,  # Now
                0.0,
                3600.0,
                None,
                True,
                "Window end in seconds ago (0 = now)"
            ),
            VariantParameter(
                "smoothing",
                "boolean",
                True,
                None,
                None,
                None,
                False,
                "Apply time-weighted smoothing to reduce noise"
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
        """Default refresh: 1 second for real-time pressure monitoring."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """Calculate refresh interval based on parameters."""
        override = params.get_refresh_override()
        if override:
            return max(
                self.get_min_refresh_interval(),
                min(self.get_max_refresh_interval(), float(override))
            )

        # Real-time pressure monitoring
        t2 = params.get_float("t2", 0.0)

        if t2 <= 1.0:
            return 1.0
        elif t2 <= 30.0:
            return 2.0
        else:
            return 5.0

    def is_time_driven(self) -> bool:
        """
        BID_ASK_IMBALANCE is time-driven.

        Order book state changes over time and needs regular recalculation.
        """
        return True

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify the window needed for imbalance calculation.

        Returns:
            Single WindowSpec object
        """
        t1 = params.get_float("t1", 30.0)
        t2 = params.get_float("t2", 0.0)

        return [WindowSpec(t1, t2)]

    def calculate(
        self,
        data: any,
        start_ts: float,
        end_ts: float,
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate BID_ASK_IMBALANCE from orderbook data.

        Args:
            data: Orderbook data sequence
            start_ts: Window start timestamp
            end_ts: Window end timestamp
            params: Algorithm parameters

        Returns:
            Imbalance percentage or None if cannot calculate
        """
        if not data:
            return None

        smoothing = params.get("smoothing", True)

        if smoothing:
            # Use time-weighted averaging for smooth imbalance
            return self._calculate_time_weighted_imbalance(data, start_ts, end_ts)
        else:
            # Use simple average for faster calculation
            return self._calculate_simple_imbalance(data, start_ts, end_ts)

    def _calculate_time_weighted_imbalance(
        self,
        orderbook_data: List,
        start_ts: float,
        end_ts: float
    ) -> Optional[float]:
        """
        Calculate time-weighted average of bid-ask imbalance.

        This smooths out orderbook noise by weighting each imbalance
        value by how long it was valid.
        """
        if not orderbook_data:
            return None

        # Convert orderbook snapshots to (timestamp, imbalance) pairs
        imbalance_series = []

        for entry in orderbook_data:
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

            # Calculate imbalance for this snapshot
            total_qty = bid_qty + ask_qty
            if total_qty > 0:
                imbalance = ((bid_qty - ask_qty) / total_qty) * 100.0
                imbalance_series.append((timestamp, imbalance))

        if not imbalance_series:
            return None

        # Apply time-weighted averaging to imbalance series
        time_weighted_imbalance = compute_time_weighted_average(
            imbalance_series,
            start_ts,
            end_ts
        )

        return time_weighted_imbalance

    def _calculate_simple_imbalance(
        self,
        orderbook_data: List,
        start_ts: float,
        end_ts: float
    ) -> Optional[float]:
        """
        Calculate simple average of bid-ask imbalance.

        Faster but noisier than time-weighted version.
        """
        if not orderbook_data:
            return None

        total_imbalance = 0.0
        count = 0

        for entry in orderbook_data:
            if isinstance(entry, dict):
                timestamp = entry.get("timestamp", 0)

                if start_ts <= timestamp <= end_ts:
                    bid_qty = float(entry.get("bid_qty", 0.0))
                    ask_qty = float(entry.get("ask_qty", 0.0))

                    total_qty = bid_qty + ask_qty
                    if total_qty > 0:
                        imbalance = ((bid_qty - ask_qty) / total_qty) * 100.0
                        total_imbalance += imbalance
                        count += 1

            elif isinstance(entry, tuple) and len(entry) >= 5:
                timestamp = entry[0]

                if start_ts <= timestamp <= end_ts:
                    bid_qty = float(entry[3])
                    ask_qty = float(entry[4])

                    total_qty = bid_qty + ask_qty
                    if total_qty > 0:
                        imbalance = ((bid_qty - ask_qty) / total_qty) * 100.0
                        total_imbalance += imbalance
                        count += 1

        if count == 0:
            return None

        return total_imbalance / count

    def calculate_from_windows(
        self,
        data_windows: List[DataWindow],
        params: IndicatorParameters
    ) -> Optional[float]:
        """
        Calculate from DataWindow format (new interface).
        """
        if len(data_windows) != 1:
            return None

        window = data_windows[0]
        return self.calculate(window.data, window.start_ts, window.end_ts, params)

    def _create_engine_hook(self):
        """Create hook for engine integration."""
        def compute_indicator_value(engine, indicator, params):
            """Hook for BID_ASK_IMBALANCE calculation."""
            from .base_algorithm import IndicatorParameters

            wrapped_params = IndicatorParameters(params)

            t1 = wrapped_params.get_float("t1", 30.0)
            t2 = wrapped_params.get_float("t2", 0.0)

            # Get orderbook data window
            window_data, start_ts, end_ts = engine._get_orderbook_series_for_window(
                indicator, t1, t2
            )

            return self.calculate(window_data, start_ts, end_ts, wrapped_params)

        return compute_indicator_value


# Create instance for auto-discovery registration
bid_ask_imbalance_algorithm = BidAskImbalanceAlgorithm()
