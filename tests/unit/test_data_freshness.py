"""
Unit Tests for Data Freshness Detection (BUG-008-9)
====================================================

Tests for stale data detection, freshness classification,
and metrics tracking.

Test Coverage:
- AC1: Data older than 60s is flagged as "stale" in metadata
- AC2: Data older than 300s (5 min) is rejected/filtered
- AC3: Stale data triggers subscription refresh attempt (rate limited)
- AC4: API responses include data_age_seconds field
- AC6: Monitoring metric tracks stale data frequency per symbol

Note: AC5 (frontend indicator) is covered by existing tests in
frontend/src/hooks/__tests__/useDataFreshness.test.ts
"""

import pytest
import time
from unittest.mock import patch

from src.core.data_freshness import (
    FreshnessStatus,
    FRESHNESS_THRESHOLDS,
    check_data_freshness,
    FreshnessMetadata,
    FreshnessMetrics,
    FreshnessTracker,
    get_freshness_tracker,
    reset_freshness_tracker,
)


class TestFreshnessStatus:
    """Test FreshnessStatus enum"""

    def test_status_values(self):
        """Verify all status values are defined"""
        assert FreshnessStatus.FRESH.value == "fresh"
        assert FreshnessStatus.WARN.value == "warn"
        assert FreshnessStatus.STALE.value == "stale"
        assert FreshnessStatus.REJECT.value == "reject"

    def test_default_thresholds(self):
        """Verify default threshold values match requirements"""
        assert FRESHNESS_THRESHOLDS[FreshnessStatus.FRESH] == 30
        assert FRESHNESS_THRESHOLDS[FreshnessStatus.WARN] == 60
        assert FRESHNESS_THRESHOLDS[FreshnessStatus.STALE] == 300


class TestCheckDataFreshness:
    """Test check_data_freshness function"""

    def test_fresh_data(self):
        """AC1: Data < 30s old is FRESH"""
        now = time.time()
        status, age = check_data_freshness(now - 10, now)

        assert status == FreshnessStatus.FRESH
        assert 9 < age < 11

    def test_warn_data(self):
        """Data 30-60s old is WARN"""
        now = time.time()
        status, age = check_data_freshness(now - 45, now)

        assert status == FreshnessStatus.WARN
        assert 44 < age < 46

    def test_stale_data(self):
        """AC1: Data 60-300s old is STALE"""
        now = time.time()
        status, age = check_data_freshness(now - 120, now)

        assert status == FreshnessStatus.STALE
        assert 119 < age < 121

    def test_reject_data(self):
        """AC2: Data > 300s (5 min) old is REJECT"""
        now = time.time()
        status, age = check_data_freshness(now - 600, now)

        assert status == FreshnessStatus.REJECT
        assert 599 < age < 601

    def test_boundary_fresh_to_warn(self):
        """Test boundary at 30s"""
        now = time.time()

        # Just under 30s - should be FRESH
        status, _ = check_data_freshness(now - 29.9, now)
        assert status == FreshnessStatus.FRESH

        # Just over 30s - should be WARN
        status, _ = check_data_freshness(now - 30.1, now)
        assert status == FreshnessStatus.WARN

    def test_boundary_warn_to_stale(self):
        """Test boundary at 60s"""
        now = time.time()

        # Just under 60s - should be WARN
        status, _ = check_data_freshness(now - 59.9, now)
        assert status == FreshnessStatus.WARN

        # Just over 60s - should be STALE
        status, _ = check_data_freshness(now - 60.1, now)
        assert status == FreshnessStatus.STALE

    def test_boundary_stale_to_reject(self):
        """AC2: Test boundary at 300s (5 minutes)"""
        now = time.time()

        # Just under 300s - should be STALE
        status, _ = check_data_freshness(now - 299.9, now)
        assert status == FreshnessStatus.STALE

        # Just over 300s - should be REJECT
        status, _ = check_data_freshness(now - 300.1, now)
        assert status == FreshnessStatus.REJECT

    def test_future_timestamp_is_fresh(self):
        """Future timestamps (clock skew) should be treated as FRESH"""
        now = time.time()
        status, age = check_data_freshness(now + 10, now)

        assert status == FreshnessStatus.FRESH
        assert age == 0.0

    def test_custom_thresholds(self):
        """AC1: Thresholds should be configurable"""
        now = time.time()
        custom = {
            FreshnessStatus.FRESH: 10,
            FreshnessStatus.WARN: 20,
            FreshnessStatus.STALE: 60,
        }

        # 15s old with custom thresholds should be WARN (not FRESH)
        status, _ = check_data_freshness(now - 15, now, custom)
        assert status == FreshnessStatus.WARN

    def test_very_old_data(self):
        """AC2: Data 55 minutes old (from bug report) is definitely REJECT"""
        now = time.time()
        status, age = check_data_freshness(now - 3351, now)  # 55 minutes

        assert status == FreshnessStatus.REJECT
        assert age > 3350


class TestFreshnessMetadata:
    """Test FreshnessMetadata class"""

    def test_from_timestamp_fresh(self):
        """AC4: Metadata includes age for fresh data"""
        now = time.time()
        meta = FreshnessMetadata.from_timestamp(now - 5, now)

        assert meta.status == FreshnessStatus.FRESH
        assert 4 < meta.age_seconds < 6
        assert meta.is_displayable is True
        assert meta.source_timestamp == now - 5
        assert meta.processed_timestamp == now

    def test_from_timestamp_reject(self):
        """AC2: REJECT status marks data as not displayable"""
        now = time.time()
        meta = FreshnessMetadata.from_timestamp(now - 600, now)

        assert meta.status == FreshnessStatus.REJECT
        assert meta.is_displayable is False

    def test_to_dict_format(self):
        """AC4: API response format includes required fields"""
        now = time.time()
        meta = FreshnessMetadata.from_timestamp(now - 45, now)
        data = meta.to_dict()

        assert "freshness_status" in data
        assert "data_age_seconds" in data
        assert "source_timestamp" in data
        assert "processed_timestamp" in data
        assert "is_displayable" in data

        assert data["freshness_status"] == "warn"
        assert isinstance(data["data_age_seconds"], float)


class TestFreshnessMetrics:
    """Test FreshnessMetrics class (AC6)"""

    def test_initial_state(self):
        """New metrics start at zero"""
        metrics = FreshnessMetrics()

        assert metrics.fresh_count == 0
        assert metrics.warn_count == 0
        assert metrics.stale_count == 0
        assert metrics.reject_count == 0
        assert metrics.total_count == 0

    def test_record_fresh(self):
        """AC6: Fresh data is counted"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.FRESH, 10.0)

        assert metrics.fresh_count == 1
        assert metrics.total_count == 1

    def test_record_stale(self):
        """AC6: Stale data is counted and timestamped"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.STALE, 120.0)

        assert metrics.stale_count == 1
        assert metrics.last_stale_timestamp is not None

    def test_record_reject(self):
        """AC6: Rejected data is counted"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.REJECT, 600.0)

        assert metrics.reject_count == 1

    def test_stale_rate_calculation(self):
        """AC6: Stale rate percentage is calculated correctly"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.FRESH, 5.0)
        metrics.record(FreshnessStatus.FRESH, 5.0)
        metrics.record(FreshnessStatus.FRESH, 5.0)
        metrics.record(FreshnessStatus.FRESH, 5.0)
        metrics.record(FreshnessStatus.STALE, 120.0)

        # 1 stale out of 5 = 20%
        assert metrics.stale_rate == 20.0

    def test_average_age(self):
        """AC6: Average age is tracked"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.FRESH, 10.0)
        metrics.record(FreshnessStatus.FRESH, 20.0)
        metrics.record(FreshnessStatus.FRESH, 30.0)

        assert metrics.average_age == 20.0

    def test_max_age(self):
        """AC6: Maximum age is tracked"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.FRESH, 10.0)
        metrics.record(FreshnessStatus.STALE, 150.0)
        metrics.record(FreshnessStatus.FRESH, 20.0)

        assert metrics.max_age_seconds == 150.0

    def test_to_dict(self):
        """AC6: Metrics can be exported for monitoring"""
        metrics = FreshnessMetrics()
        metrics.record(FreshnessStatus.FRESH, 10.0)
        metrics.record(FreshnessStatus.STALE, 120.0)

        data = metrics.to_dict()

        assert "fresh_count" in data
        assert "stale_count" in data
        assert "stale_rate_pct" in data
        assert "average_age_seconds" in data
        assert "max_age_seconds" in data


class TestFreshnessTracker:
    """Test FreshnessTracker class"""

    def test_check_and_record(self):
        """Tracker records metrics per symbol"""
        tracker = FreshnessTracker()
        now = time.time()

        status, age, should_refresh = tracker.check_and_record("BTCUSDT", now - 10, now)

        assert status == FreshnessStatus.FRESH
        assert 9 < age < 11
        assert should_refresh is False

    def test_refresh_triggered_on_stale(self):
        """AC3: Stale data triggers refresh"""
        tracker = FreshnessTracker()
        now = time.time()

        status, age, should_refresh = tracker.check_and_record("BTCUSDT", now - 120, now)

        assert status == FreshnessStatus.STALE
        assert should_refresh is True

    def test_refresh_rate_limited(self):
        """AC3: Refresh is rate limited to max 1 per 30s per symbol"""
        tracker = FreshnessTracker(refresh_cooldown_seconds=30.0)
        now = time.time()

        # First stale check - should trigger refresh
        _, _, should_refresh1 = tracker.check_and_record("BTCUSDT", now - 120, now)
        assert should_refresh1 is True

        # Second stale check immediately - should NOT trigger refresh
        _, _, should_refresh2 = tracker.check_and_record("BTCUSDT", now - 120, now)
        assert should_refresh2 is False

    def test_refresh_cooldown_per_symbol(self):
        """AC3: Refresh cooldown is per-symbol"""
        tracker = FreshnessTracker(refresh_cooldown_seconds=30.0)
        now = time.time()

        # BTCUSDT triggers refresh
        _, _, should_refresh1 = tracker.check_and_record("BTCUSDT", now - 120, now)
        assert should_refresh1 is True

        # Different symbol - should also trigger refresh
        _, _, should_refresh2 = tracker.check_and_record("ETHUSDT", now - 120, now)
        assert should_refresh2 is True

    def test_get_metrics_per_symbol(self):
        """AC6: Metrics are tracked per symbol"""
        tracker = FreshnessTracker()
        now = time.time()

        tracker.check_and_record("BTCUSDT", now - 10, now)
        tracker.check_and_record("BTCUSDT", now - 120, now)
        tracker.check_and_record("ETHUSDT", now - 10, now)

        btc_metrics = tracker.get_metrics("BTCUSDT")
        eth_metrics = tracker.get_metrics("ETHUSDT")

        assert btc_metrics.total_count == 2
        assert btc_metrics.stale_count == 1
        assert eth_metrics.total_count == 1
        assert eth_metrics.fresh_count == 1

    def test_get_problematic_symbols(self):
        """AC6: Can identify symbols with high stale rate"""
        tracker = FreshnessTracker()
        now = time.time()

        # BTCUSDT: 20% stale
        for _ in range(4):
            tracker.check_and_record("BTCUSDT", now - 10, now)
        tracker.check_and_record("BTCUSDT", now - 120, now)

        # ETHUSDT: 0% stale
        for _ in range(5):
            tracker.check_and_record("ETHUSDT", now - 10, now)

        # BADUSDT: 100% stale
        for _ in range(5):
            tracker.check_and_record("BADUSDT", now - 120, now)

        problematic = tracker.get_problematic_symbols(stale_rate_threshold=10.0)

        assert "BADUSDT" in problematic
        assert "BTCUSDT" in problematic
        assert "ETHUSDT" not in problematic

    def test_reset_metrics(self):
        """Metrics can be reset"""
        tracker = FreshnessTracker()
        now = time.time()

        tracker.check_and_record("BTCUSDT", now - 10, now)
        assert tracker.get_metrics("BTCUSDT").total_count == 1

        tracker.reset_metrics("BTCUSDT")
        assert tracker.get_metrics("BTCUSDT").total_count == 0


class TestGlobalTracker:
    """Test global tracker singleton"""

    def setup_method(self):
        """Reset global tracker before each test"""
        reset_freshness_tracker()

    def test_get_freshness_tracker(self):
        """Global tracker is created on first access"""
        tracker = get_freshness_tracker()
        assert tracker is not None
        assert isinstance(tracker, FreshnessTracker)

    def test_singleton_behavior(self):
        """Same tracker is returned on subsequent calls"""
        tracker1 = get_freshness_tracker()
        tracker2 = get_freshness_tracker()
        assert tracker1 is tracker2

    def test_reset_creates_new_instance(self):
        """Reset clears the global tracker"""
        tracker1 = get_freshness_tracker()
        now = time.time()
        tracker1.check_and_record("BTCUSDT", now - 10, now)

        reset_freshness_tracker()
        tracker2 = get_freshness_tracker()

        assert tracker1 is not tracker2
        assert tracker2.get_metrics("BTCUSDT").total_count == 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_timestamp(self):
        """Zero timestamp (Unix epoch) should be REJECT"""
        now = time.time()
        status, age = check_data_freshness(0, now)

        assert status == FreshnessStatus.REJECT
        assert age > 1700000000  # Definitely very old

    def test_none_current_time_uses_now(self):
        """None current_time should use time.time()"""
        recent = time.time() - 5
        status, age = check_data_freshness(recent)

        assert status == FreshnessStatus.FRESH
        assert 4 < age < 7  # Allow some tolerance

    def test_empty_tracker_metrics(self):
        """Getting metrics for unknown symbol returns empty metrics"""
        tracker = FreshnessTracker()
        metrics = tracker.get_metrics("UNKNOWN")

        assert metrics.total_count == 0
        assert metrics.stale_rate == 0.0

    def test_metrics_division_by_zero(self):
        """Stale rate handles zero total count"""
        metrics = FreshnessMetrics()
        assert metrics.stale_rate == 0.0
        assert metrics.average_age == 0.0
