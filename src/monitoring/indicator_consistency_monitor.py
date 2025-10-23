"""
Indicator Consistency Monitor
=============================

Provides lightweight monitoring utilities for verifying alignment between the
historical/offline indicator pipeline and the live streaming pipeline.  The
monitor supports value drift detection as well as basic performance threshold
checks so nightly recomputations can raise actionable alerts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional


class IndicatorDriftDetected(RuntimeError):
    """Raised when indicator values diverge beyond the configured tolerance."""


class PerformanceRegressionDetected(RuntimeError):
    """Raised when performance metrics fall outside of acceptable bounds."""


@dataclass(frozen=True)
class PerformanceThresholds:
    """Configuration for performance validation."""

    min_batch_points_per_second: float
    max_live_latency_ms: float


class _NullLogger:
    """Fallback logger to avoid optional dependency issues in tests."""

    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


class IndicatorConsistencyMonitor:
    """
    Compare offline and streaming indicator outputs and raise alerts on drift.

    Parameters
    ----------
    offline_resolver:
        Callable returning the canonical/offline indicator value for a context.
    streaming_resolver:
        Callable returning the live/streaming indicator value for a context.
    tolerance:
        Absolute tolerance for acceptable deviation between both values.
    logger:
        Optional structured logger.  If omitted an inert logger is used.
    """

    def __init__(
        self,
        offline_resolver: Callable[[Dict[str, Any]], float],
        streaming_resolver: Callable[[Dict[str, Any]], float],
        tolerance: float = 1e-9,
        logger: Optional[Any] = None,
    ) -> None:
        self._offline_resolver = offline_resolver
        self._streaming_resolver = streaming_resolver
        self._tolerance = tolerance
        self._logger = logger or _NullLogger()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare offline and streaming indicator outputs for the supplied context.
        """
        offline_value = float(self._offline_resolver(context))
        streaming_value = float(self._streaming_resolver(context))
        diff = abs(offline_value - streaming_value)

        payload = {
            "context": context,
            "offline_value": offline_value,
            "streaming_value": streaming_value,
            "diff": diff,
            "tolerance": self._tolerance,
        }

        if diff > self._tolerance:
            self._logger.error("indicator_consistency_monitor.drift_detected", payload)
            raise IndicatorDriftDetected(
                f"Drift detected for {context}: |offline - streaming|={diff}"
            )

        self._logger.info("indicator_consistency_monitor.drift_within_tolerance", payload)
        return {"status": "ok", **payload}

    def validate_performance(
        self,
        batch_points_per_second: float,
        live_latency_ms: float,
        thresholds: PerformanceThresholds,
    ) -> Dict[str, float]:
        """
        Validate performance metrics against configured thresholds.
        """
        metrics = {
            "batch_points_per_second": batch_points_per_second,
            "live_latency_ms": live_latency_ms,
        }

        if batch_points_per_second < thresholds.min_batch_points_per_second:
            self._logger.error("indicator_consistency_monitor.batch_regression", metrics)
            raise PerformanceRegressionDetected(
                f"Batch throughput {batch_points_per_second}pps below "
                f"threshold {thresholds.min_batch_points_per_second}pps"
            )

        if live_latency_ms > thresholds.max_live_latency_ms:
            self._logger.error("indicator_consistency_monitor.latency_regression", metrics)
            raise PerformanceRegressionDetected(
                f"Live latency {live_latency_ms}ms exceeds "
                f"threshold {thresholds.max_live_latency_ms}ms"
            )

        self._logger.info("indicator_consistency_monitor.performance_ok", metrics)
        return metrics


__all__ = [
    "IndicatorConsistencyMonitor",
    "IndicatorDriftDetected",
    "PerformanceRegressionDetected",
    "PerformanceThresholds",
]
