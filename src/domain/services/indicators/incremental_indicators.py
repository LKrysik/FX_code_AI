"""
Concrete Incremental Indicator Implementations
==============================================
O(1) indicator updates without full recalculations.

Implemented:
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- VWAP (Volume-Weighted Average Price)
- RSI (Relative Strength Index)
- Incremental TWPA (Time-Weighted Price Average)

Per user requirement: "inkrementalne akumulatory (EMA/RSI/VWAP bez pełnych przeliczeń)"
"""

from typing import Optional
from datetime import datetime
from .incremental_base import (
    IncrementalIndicator,
    ExponentialIndicator,
    WindowBasedIndicator,
    RingBuffer,
    IncrementalSum
)


# ============================================================================
# EMA - Exponential Moving Average
# ============================================================================

class IncrementalEMA(ExponentialIndicator):
    """
    Incremental EMA calculation.

    Formula: EMA(t) = α * Price(t) + (1 - α) * EMA(t-1)
    Where: α = 2 / (period + 1)

    Complexity: O(1) per update ✓
    Memory: O(1) - only stores current EMA value
    """

    def __init__(self, indicator_id: str, symbol: str, period: int):
        """
        Initialize EMA indicator.

        Args:
            period: EMA period (e.g., 20 for EMA-20)

        Example:
            ema = IncrementalEMA("EMA_20", "BTC_USDT", period=20)
            ema.update(50000, datetime.now())
            print(ema.get_value())  # EMA value
        """
        super().__init__(indicator_id, symbol, period)

    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update EMA with new price (O(1)).

        Args:
            price: Current price
            timestamp: Timestamp
            **kwargs: Ignored

        Returns:
            Updated EMA value
        """
        self.last_update = timestamp
        return self._update_ema(price)

    def get_value(self) -> Optional[float]:
        """Get current EMA value"""
        return self.ema_value


# ============================================================================
# SMA - Simple Moving Average
# ============================================================================

class IncrementalSMA(WindowBasedIndicator):
    """
    Incremental SMA using ring buffer.

    Formula: SMA = sum(last N prices) / N

    Complexity: O(1) per update ✓
    - Ring buffer auto-ejects oldest value
    - Maintains running sum

    Memory: O(N) - stores last N values
    """

    def __init__(self, indicator_id: str, symbol: str, period: int):
        """
        Initialize SMA indicator.

        Args:
            period: SMA period (e.g., 20 for SMA-20)
        """
        super().__init__(indicator_id, symbol, window_size=period)
        self.sum = 0.0
        self.period = period

    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update SMA with new price (O(1)).

        Args:
            price: Current price
            timestamp: Timestamp
            **kwargs: Ignored

        Returns:
            Updated SMA value (or None if not ready)
        """
        self.last_update = timestamp

        # If buffer full, subtract oldest value
        if self.buffer.is_full():
            oldest = self.buffer.get_all()[0]
            self.sum -= oldest

        # Add new value
        self.buffer.append(price)
        self.sum += price

        if self.buffer.is_full():
            self._initialized = True
            return self.sum / self.period

        return None

    def get_value(self) -> Optional[float]:
        """Get current SMA value"""
        if self.is_ready():
            return self.sum / self.period
        return None

    def reset(self):
        """Reset SMA"""
        super().reset()
        self.sum = 0.0


# ============================================================================
# VWAP - Volume-Weighted Average Price
# ============================================================================

class IncrementalVWAP(IncrementalIndicator):
    """
    Incremental VWAP calculation.

    Formula: VWAP = Σ(price * volume) / Σ(volume)

    Complexity: O(1) per update ✓
    Memory: O(1) - only cumulative sums

    Can be reset daily/hourly for rolling VWAP.
    """

    def __init__(self, indicator_id: str, symbol: str, reset_period: Optional[int] = None):
        """
        Initialize VWAP indicator.

        Args:
            reset_period: Optional - reset after N updates (for rolling VWAP)
                         None = cumulative VWAP from start
        """
        super().__init__(indicator_id, symbol)
        self.reset_period = reset_period
        self.update_count = 0

        self.cumulative_pv = 0.0  # price * volume
        self.cumulative_volume = 0.0

    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update VWAP with new price and volume (O(1)).

        Args:
            price: Current price
            timestamp: Timestamp
            **kwargs: Must contain 'volume'

        Returns:
            Updated VWAP value
        """
        volume = kwargs.get('volume', 0.0)
        if volume <= 0:
            return self.get_value()  # Skip zero-volume updates

        self.last_update = timestamp
        self.update_count += 1

        # Reset if period reached
        if self.reset_period and self.update_count > self.reset_period:
            self.reset()
            self.update_count = 1

        # Update cumulative sums
        self.cumulative_pv += price * volume
        self.cumulative_volume += volume

        self._initialized = True
        return self.get_value()

    def get_value(self) -> Optional[float]:
        """Get current VWAP value"""
        if not self._initialized or self.cumulative_volume == 0:
            return None
        return self.cumulative_pv / self.cumulative_volume

    def reset(self):
        """Reset VWAP"""
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0
        self.update_count = 0
        self.last_update = None
        self._initialized = False


# ============================================================================
# RSI - Relative Strength Index
# ============================================================================

class IncrementalRSI(ExponentialIndicator):
    """
    Incremental RSI using Wilder's smoothing (EMA-based).

    Formula:
    1. Calculate gain/loss for each period
    2. Smooth gains and losses with EMA
    3. RS = avg_gain / avg_loss
    4. RSI = 100 - (100 / (1 + RS))

    Complexity: O(1) per update ✓
    Memory: O(1) - only EMA values
    """

    def __init__(self, indicator_id: str, symbol: str, period: int = 14):
        """
        Initialize RSI indicator.

        Args:
            period: RSI period (default: 14)
        """
        super().__init__(indicator_id, symbol, period)
        self.previous_price: Optional[float] = None
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None

    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update RSI with new price (O(1)).

        Args:
            price: Current price
            timestamp: Timestamp
            **kwargs: Ignored

        Returns:
            Updated RSI value (0-100) or None if not ready
        """
        self.last_update = timestamp

        # Need previous price to calculate change
        if self.previous_price is None:
            self.previous_price = price
            return None

        # Calculate gain/loss
        change = price - self.previous_price
        gain = max(change, 0)
        loss = max(-change, 0)

        # Update smoothed averages (Wilder's EMA)
        if self.avg_gain is None:
            # First calculation
            self.avg_gain = gain
            self.avg_loss = loss
        else:
            # Wilder's smoothing
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period

        self.previous_price = price
        self._initialized = True

        return self.get_value()

    def get_value(self) -> Optional[float]:
        """Get current RSI value (0-100)"""
        if not self._initialized or self.avg_loss == 0:
            return None

        if self.avg_loss == 0:
            return 100.0  # No losses = max RSI

        rs = self.avg_gain / self.avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def reset(self):
        """Reset RSI"""
        super().reset()
        self.previous_price = None
        self.avg_gain = None
        self.avg_loss = None


# ============================================================================
# TWPA - Time-Weighted Price Average (Incremental)
# ============================================================================

class IncrementalTWPA(WindowBasedIndicator):
    """
    Incremental Time-Weighted Price Average.

    Uses ring buffer to store (timestamp, price) tuples.
    Recalculates TWPA when needed but maintains fixed window.

    Note: TWPA requires time weights, so we store timestamps.
    Still O(N) for window but buffer is fixed size.

    For true O(1), would need approximation or different formula.
    This is "incremental" in terms of fixed memory (O(window_size)).
    """

    def __init__(self, indicator_id: str, symbol: str, window_seconds: float):
        """
        Initialize incremental TWPA.

        Args:
            window_seconds: Time window in seconds (e.g., 60 for 1-minute TWPA)
        """
        # Use fixed-size buffer for efficiency
        # Assume max 1 update per second → window_seconds = max buffer size
        max_points = max(int(window_seconds * 2), 10)  # 2x for safety
        super().__init__(indicator_id, symbol, window_size=max_points)

        self.window_seconds = window_seconds

    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update TWPA with new (timestamp, price) point.

        Args:
            price: Current price
            timestamp: Timestamp
            **kwargs: Ignored

        Returns:
            Updated TWPA value
        """
        self.last_update = timestamp

        # Store (timestamp, price) tuple
        self.buffer.append((timestamp, price))

        # Clean old data points outside window
        self._clean_old_points(timestamp)

        if self.buffer.size() >= 2:
            self._initialized = True
            return self._calculate_twpa(timestamp)

        return None

    def _clean_old_points(self, current_time: datetime):
        """Remove points outside time window"""
        cutoff_time = current_time.timestamp() - self.window_seconds

        # Remove old points from front of buffer
        while self.buffer.size() > 0:
            oldest_ts, _ = self.buffer.get_all()[0]
            if oldest_ts.timestamp() < cutoff_time:
                # Remove by creating new buffer without first element
                all_points = self.buffer.get_all()[1:]
                self.buffer.clear()
                for point in all_points:
                    self.buffer.append(point)
            else:
                break

    def _calculate_twpa(self, end_time: datetime) -> float:
        """
        Calculate TWPA from buffer points.

        Complexity: O(N) where N = points in window
        But N is bounded by window_seconds × update_rate
        """
        points = self.buffer.get_all()
        if len(points) < 2:
            return points[0][1] if points else 0.0

        total_weight = 0.0
        weighted_sum = 0.0
        end_ts = end_time.timestamp()

        for i in range(len(points) - 1):
            t1, p1 = points[i]
            t2, p2 = points[i + 1]

            # Time weight for this segment
            weight = t2.timestamp() - t1.timestamp()

            # Use average price for segment
            avg_price = (p1 + p2) / 2

            weighted_sum += avg_price * weight
            total_weight += weight

        # Handle last point to end_time
        if points:
            last_ts, last_price = points[-1]
            final_weight = end_ts - last_ts.timestamp()
            if final_weight > 0:
                weighted_sum += last_price * final_weight
                total_weight += final_weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def get_value(self) -> Optional[float]:
        """Get current TWPA value"""
        if not self._initialized or not self.last_update:
            return None
        return self._calculate_twpa(self.last_update)

    def reset(self):
        """Reset TWPA"""
        super().reset()


# ============================================================================
# FACTORY - Create indicators by type
# ============================================================================

def create_incremental_indicator(
    indicator_type: str,
    indicator_id: str,
    symbol: str,
    **params
) -> IncrementalIndicator:
    """
    Factory function to create incremental indicators.

    Args:
        indicator_type: "EMA", "SMA", "VWAP", "RSI", "TWPA"
        indicator_id: Unique ID
        symbol: Trading symbol
        **params: Type-specific parameters

    Returns:
        Incremental indicator instance

    Example:
        ema = create_incremental_indicator("EMA", "EMA_20", "BTC_USDT", period=20)
    """
    indicator_type = indicator_type.upper()

    if indicator_type == "EMA":
        period = params.get('period', 20)
        return IncrementalEMA(indicator_id, symbol, period)

    elif indicator_type == "SMA":
        period = params.get('period', 20)
        return IncrementalSMA(indicator_id, symbol, period)

    elif indicator_type == "VWAP":
        reset_period = params.get('reset_period', None)
        return IncrementalVWAP(indicator_id, symbol, reset_period)

    elif indicator_type == "RSI":
        period = params.get('period', 14)
        return IncrementalRSI(indicator_id, symbol, period)

    elif indicator_type == "TWPA":
        window_seconds = params.get('window_seconds', 60.0)
        return IncrementalTWPA(indicator_id, symbol, window_seconds)

    else:
        raise ValueError(f"Unknown indicator type: {indicator_type}")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'IncrementalEMA',
    'IncrementalSMA',
    'IncrementalVWAP',
    'IncrementalRSI',
    'IncrementalTWPA',
    'create_incremental_indicator'
]
