"""
Data Freshness Detection & Handling (BUG-008-9)
================================================

Provides utilities for detecting and handling stale data in real-time
trading systems. Ensures users never see outdated information presented
as current.

Freshness Levels:
- FRESH (0-30s): Normal processing
- WARN (30-60s): Add warning flag, still process
- STALE (60-300s): Flag as stale, trigger subscription refresh
- REJECT (>300s): Filter out, don't display to user

Usage:
    from src.core.data_freshness import check_data_freshness, FreshnessStatus

    status, age = check_data_freshness(data_timestamp)
    if status == FreshnessStatus.REJECT:
        # Don't process this data
        pass
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple
from collections import defaultdict


class FreshnessStatus(Enum):
    """
    Data freshness classification.

    Each status indicates how fresh the data is and what action should be taken.
    """
    FRESH = "fresh"      # 0-30s: Normal processing
    WARN = "warn"        # 30-60s: Process with warning flag
    STALE = "stale"      # 60-300s: Flag + trigger refresh
    REJECT = "reject"    # >300s: Don't process or display


# Default threshold values in seconds
FRESHNESS_THRESHOLDS = {
    FreshnessStatus.FRESH: 30,   # Data is fresh if < 30s old
    FreshnessStatus.WARN: 60,    # Warning if 30-60s old
    FreshnessStatus.STALE: 300,  # Stale if 60-300s old
    # REJECT: anything > 300s
}


def check_data_freshness(
    data_timestamp: float,
    current_time: Optional[float] = None,
    thresholds: Optional[Dict[FreshnessStatus, int]] = None
) -> Tuple[FreshnessStatus, float]:
    """
    Check data freshness and return status with age.

    Args:
        data_timestamp: Unix timestamp of the data source
        current_time: Optional current time (defaults to time.time())
        thresholds: Optional custom thresholds (defaults to FRESHNESS_THRESHOLDS)

    Returns:
        Tuple of (FreshnessStatus, age_in_seconds)

    Example:
        >>> status, age = check_data_freshness(time.time() - 45)
        >>> status
        FreshnessStatus.WARN
        >>> 44 < age < 46
        True
    """
    now = current_time if current_time is not None else time.time()
    age = now - data_timestamp

    # Handle future timestamps (clock skew)
    if age < 0:
        return FreshnessStatus.FRESH, 0.0

    thresh = thresholds or FRESHNESS_THRESHOLDS

    if age < thresh[FreshnessStatus.FRESH]:
        return FreshnessStatus.FRESH, age
    elif age < thresh[FreshnessStatus.WARN]:
        return FreshnessStatus.WARN, age
    elif age < thresh[FreshnessStatus.STALE]:
        return FreshnessStatus.STALE, age
    else:
        return FreshnessStatus.REJECT, age


@dataclass
class FreshnessMetadata:
    """
    Metadata about data freshness to include in API responses.

    Provides all information needed for frontend to display
    appropriate freshness indicators.
    """
    status: FreshnessStatus
    age_seconds: float
    source_timestamp: float
    processed_timestamp: float
    is_displayable: bool = True  # False for REJECT status

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "freshness_status": self.status.value,
            "data_age_seconds": round(self.age_seconds, 2),
            "source_timestamp": self.source_timestamp,
            "processed_timestamp": self.processed_timestamp,
            "is_displayable": self.is_displayable,
        }

    @classmethod
    def from_timestamp(
        cls,
        source_timestamp: float,
        current_time: Optional[float] = None
    ) -> "FreshnessMetadata":
        """
        Create FreshnessMetadata from a source timestamp.

        Args:
            source_timestamp: Unix timestamp from data source
            current_time: Optional current time (defaults to time.time())

        Returns:
            FreshnessMetadata instance
        """
        now = current_time if current_time is not None else time.time()
        status, age = check_data_freshness(source_timestamp, now)

        return cls(
            status=status,
            age_seconds=age,
            source_timestamp=source_timestamp,
            processed_timestamp=now,
            is_displayable=(status != FreshnessStatus.REJECT)
        )


@dataclass
class FreshnessMetrics:
    """
    Tracks staleness metrics per symbol for monitoring (AC6).

    Collects statistics on data freshness to identify symbols
    with frequent staleness issues.
    """
    stale_count: int = 0
    reject_count: int = 0
    warn_count: int = 0
    fresh_count: int = 0
    total_age_seconds: float = 0.0
    max_age_seconds: float = 0.0
    last_stale_timestamp: Optional[float] = None

    def record(self, status: FreshnessStatus, age: float) -> None:
        """Record a freshness check result."""
        if status == FreshnessStatus.FRESH:
            self.fresh_count += 1
        elif status == FreshnessStatus.WARN:
            self.warn_count += 1
        elif status == FreshnessStatus.STALE:
            self.stale_count += 1
            self.last_stale_timestamp = time.time()
        elif status == FreshnessStatus.REJECT:
            self.reject_count += 1
            self.last_stale_timestamp = time.time()

        self.total_age_seconds += age
        if age > self.max_age_seconds:
            self.max_age_seconds = age

    @property
    def total_count(self) -> int:
        """Total number of data points checked."""
        return self.fresh_count + self.warn_count + self.stale_count + self.reject_count

    @property
    def stale_rate(self) -> float:
        """Percentage of data points that were stale or rejected."""
        if self.total_count == 0:
            return 0.0
        return (self.stale_count + self.reject_count) / self.total_count * 100

    @property
    def average_age(self) -> float:
        """Average age of all data points in seconds."""
        if self.total_count == 0:
            return 0.0
        return self.total_age_seconds / self.total_count

    def to_dict(self) -> Dict:
        """Convert to dictionary for monitoring/logging."""
        return {
            "fresh_count": self.fresh_count,
            "warn_count": self.warn_count,
            "stale_count": self.stale_count,
            "reject_count": self.reject_count,
            "total_count": self.total_count,
            "stale_rate_pct": round(self.stale_rate, 2),
            "average_age_seconds": round(self.average_age, 2),
            "max_age_seconds": round(self.max_age_seconds, 2),
            "last_stale_timestamp": self.last_stale_timestamp,
        }


class FreshnessTracker:
    """
    Tracks data freshness across multiple symbols.

    Provides centralized tracking of freshness metrics and
    handles subscription refresh rate limiting.
    """

    def __init__(
        self,
        refresh_cooldown_seconds: float = 30.0,
        thresholds: Optional[Dict[FreshnessStatus, int]] = None
    ):
        """
        Initialize the freshness tracker.

        Args:
            refresh_cooldown_seconds: Minimum time between refresh attempts per symbol
            thresholds: Optional custom freshness thresholds
        """
        self._metrics: Dict[str, FreshnessMetrics] = defaultdict(FreshnessMetrics)
        self._last_refresh_time: Dict[str, float] = {}
        self._refresh_cooldown = refresh_cooldown_seconds
        self._thresholds = thresholds or FRESHNESS_THRESHOLDS

    def check_and_record(
        self,
        symbol: str,
        data_timestamp: float,
        current_time: Optional[float] = None
    ) -> Tuple[FreshnessStatus, float, bool]:
        """
        Check freshness, record metrics, and determine if refresh is needed.

        Args:
            symbol: Trading symbol
            data_timestamp: Source data timestamp
            current_time: Optional current time

        Returns:
            Tuple of (status, age_seconds, should_refresh)
        """
        status, age = check_data_freshness(
            data_timestamp,
            current_time,
            self._thresholds
        )

        # Record metrics
        self._metrics[symbol].record(status, age)

        # Determine if we should trigger a refresh
        should_refresh = False
        if status in (FreshnessStatus.STALE, FreshnessStatus.REJECT):
            should_refresh = self._should_trigger_refresh(symbol)

        return status, age, should_refresh

    def _should_trigger_refresh(self, symbol: str) -> bool:
        """
        Check if we should trigger a subscription refresh (rate limited).

        AC3: Rate limit to max 1 refresh per symbol per 30s.
        """
        now = time.time()
        last_refresh = self._last_refresh_time.get(symbol, 0)

        if now - last_refresh >= self._refresh_cooldown:
            self._last_refresh_time[symbol] = now
            return True
        return False

    def get_metrics(self, symbol: str) -> FreshnessMetrics:
        """Get metrics for a specific symbol."""
        return self._metrics[symbol]

    def get_all_metrics(self) -> Dict[str, Dict]:
        """Get metrics for all symbols."""
        return {
            symbol: metrics.to_dict()
            for symbol, metrics in self._metrics.items()
        }

    def get_problematic_symbols(self, stale_rate_threshold: float = 5.0) -> Dict[str, Dict]:
        """
        Get symbols with stale rate above threshold.

        Args:
            stale_rate_threshold: Minimum stale rate percentage to be considered problematic

        Returns:
            Dict of symbol -> metrics for problematic symbols
        """
        return {
            symbol: metrics.to_dict()
            for symbol, metrics in self._metrics.items()
            if metrics.stale_rate > stale_rate_threshold
        }

    def reset_metrics(self, symbol: Optional[str] = None) -> None:
        """Reset metrics for a symbol or all symbols."""
        if symbol:
            self._metrics[symbol] = FreshnessMetrics()
        else:
            self._metrics.clear()


# Global tracker instance for convenience
_global_tracker: Optional[FreshnessTracker] = None


def get_freshness_tracker() -> FreshnessTracker:
    """Get or create the global freshness tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = FreshnessTracker()
    return _global_tracker


def reset_freshness_tracker() -> None:
    """Reset the global freshness tracker (mainly for testing)."""
    global _global_tracker
    _global_tracker = None
