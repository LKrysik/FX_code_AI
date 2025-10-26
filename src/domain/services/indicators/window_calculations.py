"""
Pure Functions for Window-Based Calculations
============================================
Reusable calculation functions for different data types.
All functions are pure (no side effects) and thread-safe.
"""

import math
from typing import Optional, Sequence, Tuple


def compute_time_weighted_average(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute time-weighted average over a time window.

    Works for any time-series data: price, volume, liquidity, etc.

    CRITICAL REQUIREMENT: window_points MUST include one point before start_ts
    to calculate the duration of the first value in the window.

    Algorithm:
    1. For each data point, calculate how long that value was valid
    2. Weight each value by its duration
    3. Return weighted average

    Args:
        window_points: Sequence of (timestamp, value) tuples sorted ascending
        start_ts: Inclusive start of evaluation range (epoch seconds)
        end_ts: Inclusive end of evaluation range (epoch seconds)

    Returns:
        Time-weighted average or None if insufficient data

    Example:
        Data: [(50, 100.0), (110, 200.0), (130, 300.0)]
        Window: [100, 120]

        Point 50 (before window):
            - Valid from max(50, 100) = 100 to min(110, 120) = 110
            - Duration: 10s, Value: 100.0

        Point 110 (in window):
            - Valid from max(110, 100) = 110 to 120 (end)
            - Duration: 10s, Value: 200.0

        TWA = (100.0*10 + 200.0*10) / 20 = 150.0
    """
    if not window_points:
        return None

    weighted_sum = 0.0
    total_weight = 0.0

    for idx, (timestamp, value) in enumerate(window_points):
        # Clip timestamp to window start
        ts_i = max(timestamp, start_ts)

        # Determine when this value stops being valid
        if idx == len(window_points) - 1:
            # Last point: valid until end of window
            ts_next = end_ts
        else:
            # Middle point: valid until next value or end of window
            ts_next = min(window_points[idx + 1][0], end_ts)

        # Skip if this point doesn't contribute to the window
        if ts_next <= ts_i:
            continue

        # Calculate time-weighted contribution
        duration = ts_next - ts_i
        total_weight += duration
        weighted_sum += value * duration

    if total_weight <= 0.0 or math.isclose(total_weight, 0.0, abs_tol=1e-12):
        return None

    return weighted_sum / total_weight


def compute_volume_average(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute average volume per second over a time window.

    Formula: sum(volumes_in_window) / (end_ts - start_ts)

    This gives volume flow rate (volume per second).

    Args:
        window_points: Sequence of (timestamp, volume) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Average volume per second or None if no data
    """
    if not window_points:
        return None

    window_duration = end_ts - start_ts
    if window_duration <= 0:
        return None

    total_volume = 0.0
    count = 0

    for timestamp, volume in window_points:
        # Only include points within window
        if start_ts <= timestamp <= end_ts:
            total_volume += volume
            count += 1

    if count == 0:
        return None

    # Return volume per second
    return total_volume / window_duration


def compute_median(values: Sequence[float]) -> Optional[float]:
    """
    Compute median of a sequence of values.

    Args:
        values: Sequence of numeric values

    Returns:
        Median value or None if empty sequence
    """
    if not values:
        return None

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n % 2 == 0:
        # Even number: average of two middle values
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0
    else:
        # Odd number: middle value
        return sorted_values[n // 2]


def compute_volume_median(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute median volume from points in time window.

    Args:
        window_points: Sequence of (timestamp, volume) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Median volume or None if no data
    """
    if not window_points:
        return None

    volumes = []
    for timestamp, volume in window_points:
        if start_ts <= timestamp <= end_ts:
            volumes.append(volume)

    return compute_median(volumes)


def compute_sum(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute sum of values in time window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Sum of values or None if no data
    """
    if not window_points:
        return None

    total = 0.0
    count = 0

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            total += value
            count += 1

    if count == 0:
        return None

    return total


def compute_simple_average(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute simple arithmetic average of values in window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Average value or None if no data
    """
    if not window_points:
        return None

    total = 0.0
    count = 0

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            total += value
            count += 1

    if count == 0:
        return None

    return total / count


def compute_max(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Find maximum value in time window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Maximum value or None if no data
    """
    if not window_points:
        return None

    max_value = None

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            if max_value is None or value > max_value:
                max_value = value

    return max_value


def compute_min(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Find minimum value in time window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Minimum value or None if no data
    """
    if not window_points:
        return None

    min_value = None

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            if min_value is None or value < min_value:
                min_value = value

    return min_value


def compute_first(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Get first value in time window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        First value or None if no data
    """
    if not window_points:
        return None

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            return value

    return None


def compute_last(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Get last value in time window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Last value or None if no data
    """
    if not window_points:
        return None

    last_value = None

    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            last_value = value

    return last_value


def compute_standard_deviation(
    window_points: Sequence[Tuple[float, float]],
    start_ts: float,
    end_ts: float
) -> Optional[float]:
    """
    Compute standard deviation of values in window.

    Args:
        window_points: Sequence of (timestamp, value) tuples
        start_ts: Window start timestamp
        end_ts: Window end timestamp

    Returns:
        Standard deviation or None if insufficient data
    """
    if not window_points:
        return None

    values = []
    for timestamp, value in window_points:
        if start_ts <= timestamp <= end_ts:
            values.append(value)

    if len(values) < 2:
        return None

    # Calculate mean
    mean = sum(values) / len(values)

    # Calculate variance
    variance = sum((x - mean) ** 2 for x in values) / len(values)

    # Return standard deviation
    return math.sqrt(variance)
