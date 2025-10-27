"""
Incremental Indicator System
============================
O(1) indicator calculations with ring buffers and incremental accumulators.

Per user requirements:
- asyncio scheduler co 1 s ✓
- wskaźniki liczone z ring-bufferów + inkrementalne akumulatory ✓
- Zapis wskaźników do tabeli indicators (COPY) ✓

Module structure:
- incremental_base: Base classes, RingBuffer, accumulators
- incremental_indicators: EMA, SMA, VWAP, RSI, TWPA implementations

Usage:
    from domain.services.indicators import (
        IncrementalEMA,
        create_incremental_indicator
    )

    # Create indicator
    ema = IncrementalEMA("EMA_20", "BTC_USDT", period=20)

    # Update with new price (O(1))
    value = ema.update(price=50000, timestamp=datetime.now())
"""

from .incremental_base import (
    RingBuffer,
    IncrementalMean,
    IncrementalVariance,
    IncrementalSum,
    IncrementalIndicator,
    WindowBasedIndicator,
    ExponentialIndicator,
    IndicatorState
)

from .incremental_indicators import (
    IncrementalEMA,
    IncrementalSMA,
    IncrementalVWAP,
    IncrementalRSI,
    IncrementalTWPA,
    create_incremental_indicator
)

__all__ = [
    # Base classes
    'RingBuffer',
    'IncrementalMean',
    'IncrementalVariance',
    'IncrementalSum',
    'IncrementalIndicator',
    'WindowBasedIndicator',
    'ExponentialIndicator',
    'IndicatorState',
    # Concrete indicators
    'IncrementalEMA',
    'IncrementalSMA',
    'IncrementalVWAP',
    'IncrementalRSI',
    'IncrementalTWPA',
    # Factory
    'create_incremental_indicator'
]
