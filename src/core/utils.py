"""
Core utilities for the crypto monitor application
"""

import asyncio
import statistics
from typing import Optional, List, Dict, Any, Tuple


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
