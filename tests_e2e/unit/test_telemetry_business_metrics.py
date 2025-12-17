"""
Test Business Metrics in Telemetry System

Verifies that TODO1 fix works correctly:
- active_strategies metric reflects real data from StrategyManager
- total_trades metric reflects real data from PaperTradingEngine
- success_rate is calculated correctly from winning/losing trades
- total_pnl is tracked correctly

Tests:
1. test_telemetry_active_strategies_metric - verify active_strategies gauge
2. test_telemetry_total_trades_counter - verify total_trades counter
3. test_telemetry_success_rate_calculation - verify success_rate formula
4. test_telemetry_business_metrics_integration - end-to-end test
"""

import pytest
from src.core.telemetry import TelemetryService, MetricsCollector
from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger


@pytest.fixture
def telemetry_service():
    """Create fresh TelemetryService for each test"""
    service = TelemetryService()
    # Clear any existing data
    service.collector.gauges.clear()
    service.collector.counters.clear()
    return service


class TestTelemetryBusinessMetrics:
    """Test suite for telemetry business metrics (TODO1 fix)"""

    def test_telemetry_active_strategies_from_gauge(self, telemetry_service):
        """
        Test that active_strategies is read from gauge set by StrategyManager.

        GIVEN: TelemetryService with gauge 'business.active_strategies' set to 3
        WHEN: _get_business_metrics() is called
        THEN: active_strategies should be 3
        """
        # Arrange
        telemetry_service.set_gauge('business.active_strategies', 3.0)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['active_strategies'] == 3, \
            f"Expected 3 active strategies, got {business_metrics['active_strategies']}"

    def test_telemetry_total_trades_from_counter(self, telemetry_service):
        """
        Test that total_trades is read from counter set by PaperTradingEngine.

        GIVEN: TelemetryService with counter 'business.total_trades' incremented 5 times
        WHEN: _get_business_metrics() is called
        THEN: total_trades should be 5
        """
        # Arrange
        for _ in range(5):
            telemetry_service.increment_counter('business.total_trades', 1)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['total_trades'] == 5, \
            f"Expected 5 total trades, got {business_metrics['total_trades']}"

    def test_telemetry_success_rate_calculation(self, telemetry_service):
        """
        Test that success_rate is calculated correctly from winning/losing trades.

        GIVEN: 7 winning trades and 3 losing trades (total 10)
        WHEN: _get_business_metrics() is called
        THEN: success_rate should be 70.0%
        """
        # Arrange
        telemetry_service.increment_counter('business.winning_trades', 7)
        telemetry_service.increment_counter('business.total_trades', 10)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['success_rate'] == 70.0, \
            f"Expected 70.0% success rate, got {business_metrics['success_rate']}"
        assert business_metrics['total_trades'] == 10, \
            f"Expected 10 total trades, got {business_metrics['total_trades']}"

    def test_telemetry_success_rate_zero_trades(self, telemetry_service):
        """
        Test that success_rate handles zero trades (edge case).

        GIVEN: 0 trades
        WHEN: _get_business_metrics() is called
        THEN: success_rate should be 0.0 (not crash with division by zero)
        """
        # Arrange - no trades

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['success_rate'] == 0.0, \
            f"Expected 0.0% success rate for zero trades, got {business_metrics['success_rate']}"
        assert business_metrics['total_trades'] == 0

    def test_telemetry_total_pnl_from_gauge(self, telemetry_service):
        """
        Test that total_pnl is read from gauge set by PaperTradingEngine.

        GIVEN: total_pnl gauge set to 1250.50
        WHEN: _get_business_metrics() is called
        THEN: total_pnl should be 1250.50
        """
        # Arrange
        telemetry_service.set_gauge('business.total_pnl', 1250.50)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['total_pnl'] == 1250.50, \
            f"Expected 1250.50 total PnL, got {business_metrics['total_pnl']}"

    def test_telemetry_business_metrics_integration(self, telemetry_service):
        """
        End-to-end test: multiple metrics set and retrieved together.

        GIVEN: All business metrics are set
        WHEN: get_metrics_summary() is called
        THEN: All metrics should be present in summary
        """
        # Arrange
        telemetry_service.set_gauge('business.active_strategies', 5.0)
        telemetry_service.increment_counter('business.total_trades', 20)
        telemetry_service.increment_counter('business.winning_trades', 12)
        telemetry_service.set_gauge('business.total_pnl', 3450.75)

        # Act
        summary = telemetry_service.get_metrics()
        business = summary.get('business', {})

        # Assert
        assert business['active_strategies'] == 5, \
            f"Expected 5 active strategies, got {business['active_strategies']}"
        assert business['total_trades'] == 20, \
            f"Expected 20 total trades, got {business['total_trades']}"
        assert business['success_rate'] == 60.0, \
            f"Expected 60.0% success rate (12/20), got {business['success_rate']}"
        assert business['total_pnl'] == 3450.75, \
            f"Expected 3450.75 total PnL, got {business['total_pnl']}"

    def test_telemetry_no_placeholders(self, telemetry_service):
        """
        Test that TODO1 is fixed - no hardcoded placeholders.

        GIVEN: Fresh TelemetryService with NO metrics set
        WHEN: _get_business_metrics() is called
        THEN: Defaults should be 0/0.0, NOT placeholders
        """
        # Arrange - no metrics set

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert - verify no placeholders, only proper defaults
        assert business_metrics['active_strategies'] == 0, \
            "active_strategies should default to 0, not placeholder"
        assert business_metrics['total_trades'] == 0, \
            "total_trades should default to 0, not placeholder"
        assert business_metrics['success_rate'] == 0.0, \
            "success_rate should default to 0.0, not placeholder"
        assert business_metrics['total_pnl'] == 0.0, \
            "total_pnl should default to 0.0, not placeholder"

    def test_telemetry_multiple_strategies_counters(self, telemetry_service):
        """
        Test handling multiple counters with similar names.

        GIVEN: Multiple trade counters
        WHEN: _get_business_metrics() aggregates them
        THEN: total_trades should sum all relevant counters
        """
        # Arrange
        telemetry_service.increment_counter('business.total_trades', 10)
        telemetry_service.increment_counter('business.trades_total', 5)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['total_trades'] == 15, \
            f"Expected 15 total trades (10+5), got {business_metrics['total_trades']}"

    def test_telemetry_gauge_overwrites(self, telemetry_service):
        """
        Test that gauge values are overwritten (not accumulated).

        GIVEN: active_strategies gauge set to 3, then updated to 5
        WHEN: _get_business_metrics() is called
        THEN: active_strategies should be 5 (latest value)
        """
        # Arrange
        telemetry_service.set_gauge('business.active_strategies', 3.0)
        telemetry_service.set_gauge('business.active_strategies', 5.0)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['active_strategies'] == 5, \
            f"Expected 5 active strategies (latest), got {business_metrics['active_strategies']}"


# Edge cases and negative tests
class TestTelemetryEdgeCases:
    """Test edge cases and error handling"""

    def test_telemetry_negative_pnl(self, telemetry_service):
        """Test handling negative PnL (losses)"""
        # Arrange
        telemetry_service.set_gauge('business.total_pnl', -500.25)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['total_pnl'] == -500.25, \
            f"Expected -500.25 total PnL (loss), got {business_metrics['total_pnl']}"

    def test_telemetry_100_percent_success_rate(self, telemetry_service):
        """Test 100% success rate (all winning trades)"""
        # Arrange
        telemetry_service.increment_counter('business.winning_trades', 10)
        telemetry_service.increment_counter('business.total_trades', 10)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['success_rate'] == 100.0, \
            f"Expected 100.0% success rate, got {business_metrics['success_rate']}"

    def test_telemetry_zero_percent_success_rate(self, telemetry_service):
        """Test 0% success rate (all losing trades)"""
        # Arrange
        telemetry_service.increment_counter('business.winning_trades', 0)
        telemetry_service.increment_counter('business.total_trades', 10)

        # Act
        business_metrics = telemetry_service.collector._get_business_metrics()

        # Assert
        assert business_metrics['success_rate'] == 0.0, \
            f"Expected 0.0% success rate, got {business_metrics['success_rate']}"
