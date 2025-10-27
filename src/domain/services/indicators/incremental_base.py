"""
Incremental Indicator Infrastructure
====================================
Base classes and utilities for O(1) incremental indicator calculations.

Per user requirement:
- Ring buffers for window-based indicators
- Incremental accumulators (EMA/RSI/VWAP)
- No full recalculations on each tick
"""

from abc import ABC, abstractmethod
from collections import deque
from typing import Optional, List, Any, Dict
from dataclasses import dataclass
from datetime import datetime
import math


# ============================================================================
# RING BUFFER - Fixed-size FIFO buffer for window-based indicators
# ============================================================================

class RingBuffer:
    """
    Fixed-size ring buffer with O(1) append and access.

    Per user requirement: "ring-bufferów + inkrementalne akumulatory"

    Use case: Store last N values for moving averages, windows, etc.
    """

    def __init__(self, maxlen: int):
        """
        Initialize ring buffer with fixed size.

        Args:
            maxlen: Maximum number of elements (automatically ejects oldest)
        """
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")

        self.maxlen = maxlen
        self.buffer = deque(maxlen=maxlen)  # O(1) append with auto-eject

    def append(self, value: Any):
        """Append value (O(1) - auto-ejects oldest if full)"""
        self.buffer.append(value)

    def get_all(self) -> List[Any]:
        """Get all values as list (oldest to newest)"""
        return list(self.buffer)

    def get_last(self, n: int = 1) -> List[Any]:
        """Get last N values"""
        if n <= 0:
            return []
        return list(self.buffer)[-n:]

    def is_full(self) -> bool:
        """Check if buffer is at capacity"""
        return len(self.buffer) == self.maxlen

    def size(self) -> int:
        """Current number of elements"""
        return len(self.buffer)

    def clear(self):
        """Remove all elements"""
        self.buffer.clear()

    def __len__(self):
        return len(self.buffer)

    def __repr__(self):
        return f"RingBuffer(maxlen={self.maxlen}, size={len(self.buffer)})"


# ============================================================================
# INCREMENTAL ACCUMULATORS - O(1) updates for statistics
# ============================================================================

class IncrementalMean:
    """
    Incremental mean calculation (Welford's algorithm).
    Updates in O(1) without storing all values.
    """

    def __init__(self):
        self.count = 0
        self.mean = 0.0

    def update(self, value: float):
        """Update mean with new value (O(1))"""
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count

    def get_value(self) -> Optional[float]:
        """Get current mean"""
        return self.mean if self.count > 0 else None

    def reset(self):
        """Reset to initial state"""
        self.count = 0
        self.mean = 0.0


class IncrementalVariance:
    """
    Incremental variance calculation (Welford's algorithm).
    Updates in O(1) without storing all values.
    """

    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0  # Sum of squared differences

    def update(self, value: float):
        """Update variance with new value (O(1))"""
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    def get_variance(self) -> Optional[float]:
        """Get sample variance"""
        if self.count < 2:
            return None
        return self.m2 / (self.count - 1)

    def get_std_dev(self) -> Optional[float]:
        """Get standard deviation"""
        var = self.get_variance()
        return math.sqrt(var) if var is not None else None

    def reset(self):
        """Reset to initial state"""
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0


class IncrementalSum:
    """
    Incremental sum with optional windowing.
    For VWAP: cumulative sum of price*volume.
    """

    def __init__(self, window_size: Optional[int] = None):
        """
        Args:
            window_size: If set, maintains rolling sum of last N values
        """
        self.window_size = window_size
        self.total = 0.0

        if window_size:
            self.buffer = RingBuffer(window_size)

    def update(self, value: float):
        """Add value to sum (O(1))"""
        if self.window_size:
            # Rolling window sum
            if self.buffer.is_full():
                # Subtract oldest value
                oldest = self.buffer.get_all()[0]
                self.total -= oldest

            self.buffer.append(value)
            self.total += value
        else:
            # Cumulative sum
            self.total += value

    def get_value(self) -> float:
        """Get current sum"""
        return self.total

    def reset(self):
        """Reset to initial state"""
        self.total = 0.0
        if self.window_size:
            self.buffer.clear()


# ============================================================================
# BASE CLASS - IncrementalIndicator
# ============================================================================

@dataclass
class IndicatorState:
    """State snapshot for serialization/debugging"""
    timestamp: datetime
    value: Optional[float]
    metadata: Dict[str, Any]


class IncrementalIndicator(ABC):
    """
    Abstract base class for incremental indicators.

    Per user requirement: "inkrementalne akumulatory (EMA/RSI/VWAP bez pełnych przeliczeń)"

    Key principles:
    1. O(1) update complexity (not O(n))
    2. Maintains internal state
    3. No full recalculations
    4. Thread-safe (if needed)

    Subclasses must implement:
    - update(price, timestamp, **kwargs): Update indicator with new data
    - get_value(): Get current indicator value
    - reset(): Reset to initial state
    """

    def __init__(self, indicator_id: str, symbol: str):
        """
        Initialize incremental indicator.

        Args:
            indicator_id: Unique identifier
            symbol: Trading symbol (e.g., "BTC_USDT")
        """
        self.indicator_id = indicator_id
        self.symbol = symbol
        self.last_update: Optional[datetime] = None
        self._initialized = False

    @abstractmethod
    def update(self, price: float, timestamp: datetime, **kwargs) -> Optional[float]:
        """
        Update indicator with new data point (O(1) complexity).

        Args:
            price: Current price
            timestamp: Timestamp of data point
            **kwargs: Additional data (volume, trades, etc.)

        Returns:
            Updated indicator value (or None if not ready)
        """
        pass

    @abstractmethod
    def get_value(self) -> Optional[float]:
        """
        Get current indicator value.

        Returns:
            Current value or None if not initialized
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset indicator to initial state"""
        pass

    def is_ready(self) -> bool:
        """Check if indicator has enough data to produce valid values"""
        return self._initialized

    def get_state(self) -> IndicatorState:
        """Get current state snapshot"""
        return IndicatorState(
            timestamp=self.last_update or datetime.now(),
            value=self.get_value(),
            metadata=self._get_metadata()
        )

    def _get_metadata(self) -> Dict[str, Any]:
        """Get indicator-specific metadata (override in subclass)"""
        return {
            'indicator_id': self.indicator_id,
            'symbol': self.symbol,
            'is_ready': self.is_ready()
        }

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.indicator_id}, symbol={self.symbol}, value={self.get_value()})"


# ============================================================================
# HELPER - Window-Based Indicator Base
# ============================================================================

class WindowBasedIndicator(IncrementalIndicator):
    """
    Base class for indicators that need a window of historical values.
    Uses RingBuffer internally.

    Examples: SMA, Bollinger Bands, ATR
    """

    def __init__(self, indicator_id: str, symbol: str, window_size: int):
        """
        Args:
            window_size: Number of periods for the window
        """
        super().__init__(indicator_id, symbol)

        if window_size <= 0:
            raise ValueError("window_size must be positive")

        self.window_size = window_size
        self.buffer = RingBuffer(window_size)

    def is_ready(self) -> bool:
        """Ready when buffer is full"""
        return self.buffer.is_full()

    def reset(self):
        """Reset buffer"""
        self.buffer.clear()
        self.last_update = None
        self._initialized = False


# ============================================================================
# HELPER - Exponential Moving Average Base
# ============================================================================

class ExponentialIndicator(IncrementalIndicator):
    """
    Base class for exponential indicators (EMA, MACD, RSI).
    Uses exponential smoothing with alpha parameter.

    Formula: new_value = alpha * current + (1 - alpha) * previous
    """

    def __init__(self, indicator_id: str, symbol: str, period: int):
        """
        Args:
            period: EMA period (e.g., 20 for EMA-20)
        """
        super().__init__(indicator_id, symbol)

        if period <= 0:
            raise ValueError("period must be positive")

        self.period = period
        self.alpha = 2.0 / (period + 1)  # Standard EMA alpha
        self.ema_value: Optional[float] = None

    def is_ready(self) -> bool:
        """Ready after first value"""
        return self.ema_value is not None

    def reset(self):
        """Reset EMA"""
        self.ema_value = None
        self.last_update = None
        self._initialized = False

    def _update_ema(self, new_value: float) -> float:
        """
        Update EMA with new value (O(1)).

        Returns:
            Updated EMA value
        """
        if self.ema_value is None:
            # First value: initialize EMA
            self.ema_value = new_value
            self._initialized = True
        else:
            # Exponential smoothing
            self.ema_value = self.alpha * new_value + (1 - self.alpha) * self.ema_value

        return self.ema_value


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'RingBuffer',
    'IncrementalMean',
    'IncrementalVariance',
    'IncrementalSum',
    'IncrementalIndicator',
    'WindowBasedIndicator',
    'ExponentialIndicator',
    'IndicatorState'
]
