"""
Core utilities for the crypto monitor application
"""

import asyncio
import statistics
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Literal


# =============================================================================
# BUG-DV-024 FIX: Timezone-aware datetime utilities
# =============================================================================

def utc_now() -> datetime:
    """
    Get current UTC time with timezone awareness.

    BUG-DV-024: datetime.now() returns naive datetime which can cause
    issues when comparing with timezone-aware timestamps from databases
    or external APIs.

    Returns:
        datetime: Current UTC time with tzinfo set to UTC

    Examples:
        >>> now = utc_now()
        >>> now.tzinfo is not None
        True
    """
    return datetime.now(timezone.utc)


def ensure_timezone_aware(dt: Optional[datetime], default_tz: timezone = timezone.utc) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware.

    BUG-DV-024: Many places use naive datetimes which can cause comparison issues.
    This function ensures consistent timezone handling.

    Args:
        dt: Datetime to make timezone-aware (can be None)
        default_tz: Timezone to use if datetime is naive (default: UTC)

    Returns:
        Timezone-aware datetime or None if input is None

    Examples:
        >>> naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo is not None
        True
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt


# =============================================================================
# BUG-DV-003 FIX: Order Side Normalization
# =============================================================================
# Canonical values for order sides - UPPERCASE for consistency with MEXC API

OrderSide = Literal["BUY", "SELL"]
PositionSide = Literal["LONG", "SHORT"]


def normalize_order_side(side: str) -> OrderSide:
    """
    Normalize order side to UPPERCASE for consistency.

    BUG-DV-003: Mixed case usage across codebase causes comparison failures.
    MEXC API uses UPPERCASE, so we standardize on that.

    Args:
        side: Order side in any case ("buy", "BUY", "Buy", etc.)

    Returns:
        Normalized UPPERCASE side ("BUY" or "SELL")

    Raises:
        ValueError: If side is not a valid order side

    Examples:
        >>> normalize_order_side("buy")
        "BUY"
        >>> normalize_order_side("SELL")
        "SELL"
    """
    normalized = side.upper().strip()
    if normalized not in ("BUY", "SELL"):
        raise ValueError(f"Invalid order side: '{side}'. Must be 'BUY' or 'SELL'.")
    return normalized  # type: ignore


def normalize_position_side(side: str) -> PositionSide:
    """
    Normalize position side to UPPERCASE for consistency.

    BUG-DV-003: Mixed case usage across codebase causes comparison failures.

    Args:
        side: Position side in any case ("long", "LONG", "Long", etc.)

    Returns:
        Normalized UPPERCASE side ("LONG" or "SHORT")

    Raises:
        ValueError: If side is not a valid position side

    Examples:
        >>> normalize_position_side("long")
        "LONG"
        >>> normalize_position_side("SHORT")
        "SHORT"
    """
    normalized = side.upper().strip()
    if normalized not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid position side: '{side}'. Must be 'LONG' or 'SHORT'.")
    return normalized  # type: ignore


async def cooperative_async_sleep(delay: float, check_interval: float = 0.1) -> bool:
    """
    A cooperative sleep function that checks for cancellation periodically.
    
    Args:
        delay: Total delay time in seconds
        check_interval: Interval to check for cancellation in seconds
        
    Returns:
        True if sleep completed normally, False if cancelled
    """
    if delay <= 0:
        return True

    remaining = delay
    while remaining > 0:
        # Sleep for the smaller of remaining time or check interval
        sleep_time = min(remaining, check_interval)
        await asyncio.sleep(sleep_time)
        remaining -= sleep_time
        
        # Check if we were cancelled during the sleep
        if asyncio.current_task().cancelled():
            return False

    return True


def calculate_volatility(values: List[float]) -> float:
    """
    Calculate volatility (standard deviation) of a series of values.

    Args:
        values: List of numeric values

    Returns:
        Volatility as a float (0.0 if insufficient data)
    """
    if len(values) < 2:
        return 0.0

    try:
        return statistics.stdev(values)
    except statistics.StatisticsError:
        return 0.0


def calculate_distribution(values: List[float]) -> Dict[str, float]:
    """
    Calculate distribution statistics for a series of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with distribution statistics
    """
    if not values:
        return {
            'mean': 0.0,
            'median': 0.0,
            'std_dev': 0.0,
            'min': 0.0,
            'max': 0.0,
            'q25': 0.0,
            'q75': 0.0
        }

    try:
        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if n > 1 else 0.0,
            'min': min(values),
            'max': max(values),
            'q25': sorted_values[int(n * 0.25)],
            'q75': sorted_values[int(n * 0.75)]
        }
    except (statistics.StatisticsError, IndexError):
        return {
            'mean': sum(values) / len(values) if values else 0.0,
            'median': sorted(values)[len(values) // 2] if values else 0.0,
            'std_dev': 0.0,
            'min': min(values) if values else 0.0,
            'max': max(values) if values else 0.0,
            'q25': 0.0,
            'q75': 0.0
        }
