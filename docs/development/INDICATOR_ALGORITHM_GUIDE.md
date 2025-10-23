# Indicator Algorithm Developer Guide

Complete guide for adding new indicator algorithms to FX_code_AI.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Step-by-Step Tutorial](#step-by-step-tutorial)
4. [Advanced Topics](#advanced-topics)
5. [Testing](#testing)
6. [Best Practices](#best-practices)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Algorithm Registry                         │
│  • Auto-discovers algorithms from indicators/ folder        │
│  • Registers algorithms with metadata                       │
│  • Provides algorithm instances to engines                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│ Streaming       │  │ Offline          │
│ Engine          │  │ Engine           │
│ (Real-time)     │  │ (Historical)     │
└─────────────────┘  └──────────────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ Your Algorithm   │
         │ (Calculation)    │
         └──────────────────┘
```

### Key Principles

1. **Single Source of Truth**: All algorithms live in `src/domain/services/indicators/`
2. **Auto-Discovery**: No manual registration required - just create the file
3. **Algorithm Registry**: Centralized management and metadata
4. **Unified Interface**: Same algorithm works for streaming and offline engines

---

## Quick Start

### Create a Simple Indicator in 3 Steps

**Step 1**: Create file `src/domain/services/indicators/my_indicator.py`

```python
from .base_algorithm import IndicatorAlgorithm, IndicatorParameters
from typing import List, Optional, Sequence, Tuple

class MyIndicatorAlgorithm(IndicatorAlgorithm):
    def get_indicator_type(self) -> str:
        return "MY_INDICATOR"

    def get_name(self) -> str:
        return "My Custom Indicator"

    def get_description(self) -> str:
        return "Calculates something awesome"

    def get_category(self) -> str:
        return "general"  # or "risk", "price", etc.

    def get_parameters(self) -> List:
        return []  # No parameters for now

    def calculate(self,
                 data: Sequence[Tuple[float, float]],
                 start_ts: float,
                 end_ts: float,
                 params: IndicatorParameters) -> Optional[float]:
        """
        Calculate indicator value.

        Args:
            data: List of (timestamp, price) tuples
            start_ts: Window start timestamp
            end_ts: Window end timestamp
            params: Algorithm parameters

        Returns:
            Calculated value or None
        """
        if not data:
            return None

        # Your calculation logic here
        prices = [price for _, price in data]
        return sum(prices) / len(prices)  # Example: simple average

# Export instance for auto-discovery
my_indicator_algorithm = MyIndicatorAlgorithm()
```

**Step 2**: That's it! Auto-discovery handles the rest.

**Step 3** (Optional): Register in `IndicatorType` enum (for backward compatibility):

```python
# In src/domain/services/streaming_indicator_engine.py
class IndicatorType(str, Enum):
    # ... existing indicators
    MY_INDICATOR = "MY_INDICATOR"
```

---

## Step-by-Step Tutorial

### Example: Implement EMA (Exponential Moving Average)

Let's implement a complete EMA algorithm with parameters and refresh intervals.

#### 1. Create the Algorithm File

**File**: `src/domain/services/indicators/ema.py`

```python
from __future__ import annotations
from typing import List, Optional, Sequence, Tuple
from .base_algorithm import IndicatorAlgorithm, IndicatorParameters


class EMAAlgorithm(IndicatorAlgorithm):
    """
    Exponential Moving Average Algorithm

    EMA gives more weight to recent prices, making it more responsive
    to price changes than Simple Moving Average (SMA).

    Formula: EMA = Price(t) * k + EMA(y) * (1 - k)
    Where k = 2 / (period + 1)
    """

    def get_indicator_type(self) -> str:
        return "EMA"

    def get_name(self) -> str:
        return "Exponential Moving Average"

    def get_description(self) -> str:
        return "Moving average that gives more weight to recent prices"

    def get_category(self) -> str:
        return "general"

    def get_parameters(self) -> List:
        """Define UI parameters for EMA."""
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
                name="period",
                type="int",
                default=20,
                min_value=2,
                max_value=200,
                allowed_values=None,
                required=True,
                description="Number of periods for EMA calculation"
            ),
            VariantParameter(
                name="refresh_interval_seconds",
                type="float",
                default=None,
                min_value=0.5,
                max_value=3600.0,
                allowed_values=None,
                required=False,
                description="Optional refresh interval override"
            ),
        ]

    def get_default_refresh_interval(self) -> float:
        """EMA refreshes every second by default."""
        return 1.0

    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """
        Custom refresh interval logic.

        For EMA, we refresh more frequently for shorter periods.
        """
        override = params.get_refresh_override()
        if override:
            return max(self.get_min_refresh_interval(),
                      min(self.get_max_refresh_interval(), float(override)))

        period = params.get_float("period", 20)

        # Shorter periods need more frequent updates
        if period <= 10:
            return 1.0
        elif period <= 50:
            return 2.0
        else:
            return 5.0

    def calculate(self,
                 data: Sequence[Tuple[float, float]],
                 start_ts: float,
                 end_ts: float,
                 params: IndicatorParameters) -> Optional[float]:
        """
        Calculate EMA for the given data window.

        Note: This calculates EMA at the END of the window.
        """
        if not data:
            return None

        period = int(params.get_float("period", 20))

        # Need at least 'period' data points
        if len(data) < period:
            return None

        # Extract prices
        prices = [price for _, price in data]

        # Calculate EMA
        multiplier = 2.0 / (period + 1)

        # Start with SMA for first value
        ema = sum(prices[:period]) / period

        # Apply EMA formula for remaining values
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema


# Export instance for auto-discovery
ema_algorithm = EMAAlgorithm()
```

#### 2. That's All!

The algorithm is now:
- ✅ Automatically discovered by the registry
- ✅ Available in streaming engine
- ✅ Available in offline engine
- ✅ Registered with metadata
- ✅ Has UI parameters defined
- ✅ Has custom refresh interval logic

---

## Advanced Topics

### Multi-Window Algorithms

Some algorithms need multiple time windows (e.g., TWPA_RATIO).

**Example**: TWPA Ratio = TWPA(t1,t2) / TWPA(t3,t4)

```python
from .base_algorithm import MultiWindowIndicatorAlgorithm, IndicatorParameters
from .twpa import twpa_algorithm

class TWPARatioAlgorithm(MultiWindowIndicatorAlgorithm):
    """Calculate ratio between two TWPA values."""

    def get_indicator_type(self) -> str:
        return "TWPA_RATIO"

    # ... other methods ...

    def calculate_multi_window(self,
                              windows: List[Tuple[Sequence[Tuple[float, float]], float, float]],
                              params: IndicatorParameters) -> Optional[float]:
        """
        Calculate using multiple windows.

        Args:
            windows: [(data1, start1, end1), (data2, start2, end2), ...]
            params: Algorithm parameters
        """
        if len(windows) != 2:
            return None

        # Calculate TWPA for each window
        twpa1 = twpa_algorithm._compute_twpa(*windows[0])
        twpa2 = twpa_algorithm._compute_twpa(*windows[1])

        if twpa1 is None or twpa2 is None:
            return None

        # Avoid division by zero
        min_denom = params.get_float("min_denominator", 0.001)
        if abs(twpa2) < min_denom:
            return None

        return twpa1 / twpa2

    def _get_multiple_data_windows(self, engine, indicator, params):
        """Fetch data for both windows."""
        t1 = params.get_float("t1", 300.0)
        t2 = params.get_float("t2", 60.0)
        t3 = params.get_float("t3", 1800.0)
        t4 = params.get_float("t4", 300.0)

        window1 = engine._get_price_series_for_window(indicator, t1, t2)
        window2 = engine._get_price_series_for_window(indicator, t3, t4)

        return [window1, window2]
```

### Time Window Semantics

**CRITICAL**: When working with time windows for TWPA-like indicators:

```python
# Window parameters:
# t1: seconds back from now (window start) - LARGER value
# t2: seconds back from now (window end) - SMALLER value

# Example: t1=300, t2=0 means "from 5 minutes ago to now"
# Example: t1=600, t2=300 means "from 10 minutes ago to 5 minutes ago"

# ALWAYS: t1 > t2
```

**CRITICAL REQUIREMENT for TWPA**: Your data window MUST include one transaction BEFORE `start_ts`:

```python
def _get_price_series_for_window(self, indicator, t1, t2):
    # ... calculate start_ts and end_ts ...

    # Find last transaction BEFORE window
    pre_window_point = None
    for s in series:
        if s["timestamp"] < start_ts:
            pre_window_point = (s["timestamp"], s["price"])

    # Get points IN window
    window_points = [
        (s["timestamp"], s["price"])
        for s in series
        if start_ts <= s["timestamp"] <= end_ts
    ]

    # ALWAYS prepend pre-window point
    if pre_window_point:
        window_points.insert(0, pre_window_point)

    return window_points
```

### Custom Data Sources

By default, algorithms receive price data. To use custom data:

```python
class VolumeWeightedAlgorithm(IndicatorAlgorithm):
    def _get_data_window(self, engine, indicator, params):
        """Override to fetch volume data."""
        t1 = params.get_float("t1", 60.0)
        t2 = params.get_float("t2", 0.0)

        # Get deal data instead of price data
        return engine._get_deals_for_window(indicator, t1, t2)
```

### Cache Bucket Configuration

Control caching granularity:

```python
def calculate_cache_bucket_seconds(self, t1, t2, refresh_interval):
    """
    Determine cache bucket size.

    Smaller buckets = more frequent cache invalidation
    Larger buckets = more cache hits but less precision
    """
    # Ultra-short windows: 1 second buckets
    if t2 <= 1.0:
        return 1

    # Standard: match refresh interval
    candidate = max(1, int(round(refresh_interval)))

    # Cap at 60 seconds
    return min(candidate, 60)
```

---

## Testing

### Unit Tests

Create `tests/backend/test_my_indicator.py`:

```python
import pytest
from src.domain.services.indicators.my_indicator import my_indicator_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters


class TestMyIndicator:
    def test_basic_calculation(self):
        """Test basic indicator calculation."""
        data = [
            (100.0, 1.0),
            (110.0, 2.0),
            (120.0, 3.0),
        ]
        start_ts = 100.0
        end_ts = 120.0
        params = IndicatorParameters({})

        result = my_indicator_algorithm.calculate(data, start_ts, end_ts, params)

        expected = 2.0  # Average of 1, 2, 3
        assert result == pytest.approx(expected)

    def test_empty_data(self):
        """Test that empty data returns None."""
        result = my_indicator_algorithm.calculate([], 100.0, 120.0, IndicatorParameters({}))
        assert result is None
```

### Integration Tests

Test offline vs streaming consistency:

```python
def test_offline_vs_streaming_consistency():
    """Verify both engines produce same results."""
    from src.domain.calculators.indicator_calculator import IndicatorCalculator
    from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine

    # Setup data...

    # Calculate offline
    offline_value = IndicatorCalculator.calculate_indicator_unified(
        "MY_INDICATOR",
        market_points,
        current_timestamp,
        parameters
    )

    # Calculate streaming
    streaming_value = engine._calculate_my_indicator(indicator, parameters)

    # Must match
    assert offline_value == pytest.approx(streaming_value, rel=1e-9)
```

---

## Best Practices

### 1. Algorithm Design

✅ **DO**:
- Keep algorithms stateless (no instance variables)
- Return `None` for insufficient data
- Document expected data format
- Include examples in docstrings
- Handle edge cases (empty data, single point, etc.)

❌ **DON'T**:
- Store state in algorithm instance
- Raise exceptions for normal cases (empty data)
- Assume data is sorted (always sort if needed)
- Perform I/O operations in calculate()

### 2. Performance

✅ **DO**:
- Use efficient algorithms (O(n) preferred over O(n²))
- Cache intermediate results if reused
- Return early for invalid inputs
- Use NumPy for vectorized operations when appropriate

❌ **DON'T**:
- Create unnecessary copies of large datasets
- Use nested loops when vectorization is possible
- Perform expensive operations in refresh interval calculation

### 3. Parameter Validation

```python
def calculate(self, data, start_ts, end_ts, params):
    # Validate inputs
    if not data:
        return None

    if start_ts >= end_ts:
        self.logger.warning("Invalid time window")
        return None

    period = params.get_float("period", 20)
    if period < 2:
        return None

    # ... calculation ...
```

### 4. Documentation

```python
class MyAlgorithm(IndicatorAlgorithm):
    """
    One-line summary of what indicator calculates.

    Detailed description:
    - What does it measure?
    - When is it useful?
    - How does it work?

    Example:
        data = [(100, 1.0), (110, 2.0), (120, 3.0)]
        result = algorithm.calculate(data, 100, 120, params)
        # Returns: 2.0

    References:
        - Link to paper/documentation
        - Trading strategy context
    """
```

### 5. Error Handling

```python
def calculate(self, data, start_ts, end_ts, params):
    try:
        # ... calculation ...
        return result
    except ZeroDivisionError:
        # Log and return None for mathematical errors
        return None
    except Exception as e:
        # Unexpected errors should be logged
        self.logger.error(f"Unexpected error: {e}")
        return None
```

---

## Appendix: Complete Example (TWPA)

See `src/domain/services/indicators/twpa.py` for a complete, production-ready example implementing all best practices.

---

## Questions?

- **Architecture**: See `docs/architecture/INDICATORS_SYSTEM.md` (if exists)
- **Issues**: Check existing indicators in `src/domain/services/indicators/`
- **Testing**: See `tests/backend/test_twpa_algorithm.py` for comprehensive test examples

---

**Last Updated**: 2025-01-XX (Fix TWPA pre-window transaction bug)
