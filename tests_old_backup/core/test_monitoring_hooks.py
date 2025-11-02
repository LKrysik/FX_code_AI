import pytest

from src.monitoring.indicator_consistency_monitor import (
    IndicatorConsistencyMonitor,
    IndicatorDriftDetected,
    PerformanceRegressionDetected,
    PerformanceThresholds,
)


class RecorderLogger:
    def __init__(self):
        self.entries = []

    def info(self, message, payload=None):
        self.entries.append(("info", message, payload))

    def error(self, message, payload=None):
        self.entries.append(("error", message, payload))


def test_consistency_monitor_detects_drift_and_logs():
    logger = RecorderLogger()

    monitor = IndicatorConsistencyMonitor(
        offline_resolver=lambda ctx: ctx["expected"],
        streaming_resolver=lambda ctx: ctx["expected"] + 0.5,
        tolerance=0.1,
        logger=logger,
    )

    with pytest.raises(IndicatorDriftDetected):
        monitor.evaluate({"expected": 10.0})

    assert any(level == "error" for level, _msg, _payload in logger.entries)


def test_performance_monitor_thresholds():
    monitor = IndicatorConsistencyMonitor(
        offline_resolver=lambda ctx: ctx["value"],
        streaming_resolver=lambda ctx: ctx["value"],
    )

    thresholds = PerformanceThresholds(min_batch_points_per_second=500.0, max_live_latency_ms=120.0)
    metrics = monitor.validate_performance(
        batch_points_per_second=520.0,
        live_latency_ms=100.0,
        thresholds=thresholds,
    )
    assert metrics["batch_points_per_second"] == 520.0

    with pytest.raises(PerformanceRegressionDetected):
        monitor.validate_performance(
            batch_points_per_second=100.0,
            live_latency_ms=200.0,
            thresholds=thresholds,
        )
