"""
TimeManager - lightweight time utilities for consistent timing across modules.
"""

import time
from typing import Optional, Deque, Tuple


def now() -> float:
    """Return system time in seconds."""
    return time.time()


def market_time(event_ts: Optional[float], recent_trades: Optional[Deque[Tuple[float, float, float]]]) -> float:
    """Pick a consistent market timestamp: event_ts > last trade ts > system now."""
    if isinstance(event_ts, (int, float)):
        return float(event_ts)
    if recent_trades:
        try:
            return float(recent_trades[-1][0])
        except Exception:
            pass
    return now()


def is_fresh(snapshot_ts: Optional[float], current_time: Optional[float], window_seconds: int) -> bool:
    """Check if snapshot is fresh within a time window."""
    if snapshot_ts is None:
        return False
    ct = current_time if isinstance(current_time, (int, float)) else now()
    try:
        return (ct - float(snapshot_ts)) <= window_seconds
    except Exception:
        return False

