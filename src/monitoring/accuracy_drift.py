"""
Accuracy Drift Watchdog - Sprint 4 Accuracy Monitoring
======================================================

Monitors strategy accuracy drift over time and compares live performance
against Sprint 2 baseline to detect degradation.

Features:
- Rolling accuracy calculation for live strategies
- Baseline comparison against Sprint 2 results
- Drift detection with configurable thresholds
- Performance regression alerts
- Historical accuracy tracking
- Integration with incident management

Critical Analysis Points:
1. **Baseline Comparison**: Accurate comparison with Sprint 2 results
2. **Drift Calculation**: Statistical methods for detecting performance changes
3. **Threshold Configuration**: Appropriate sensitivity for different strategies
4. **Historical Tracking**: Long-term accuracy trend analysis
5. **Alert Management**: Preventing alert fatigue while catching real issues
6. **Performance Attribution**: Distinguishing strategy vs market condition changes
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a strategy"""
    strategy_name: str
    total_signals: int = 0
    correct_signals: int = 0
    accuracy: float = 0.0
    last_update: float = 0.0
    baseline_accuracy: float = 0.0  # From Sprint 2
    drift_detected: bool = False
    drift_start_time: Optional[float] = None


@dataclass
class DriftAlert:
    """Accuracy drift alert"""
    strategy_name: str
    current_accuracy: float
    baseline_accuracy: float
    drift_percent: float
    threshold_percent: float
    timestamp: float
    severity: str


class AccuracyDriftWatchdog:
    """
    Monitors strategy accuracy drift for Sprint 4 operations.

    Tracks live strategy performance and compares against Sprint 2 baselines
    to detect accuracy degradation that might indicate system issues.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: StructuredLogger
    ):
        self.event_bus = event_bus
        self.logger = logger

        # Configuration
        self.config = {
            "check_interval": 300.0,      # Check every 5 minutes
            "min_signals_required": 50,   # Need minimum signals for accuracy calc
            "drift_threshold_percent": 10.0,  # 10% drop triggers alert
            "critical_drift_percent": 20.0,   # 20% drop is critical
            "baseline_tolerance": 0.02,   # 2% tolerance for baseline comparison
            "history_window": 86400.0,   # 24 hours of history
            "recovery_threshold": 5.0,   # 5% improvement to clear alert
        }

        # Sprint 2 baseline accuracies (from docs/SYSTEM_OVERVIEW.md)
        self.baseline_accuracies = {
            "pump_detection": 0.91,  # 91% from Sprint 2
            "volume_surge": 0.85,   # Estimated
            "price_velocity": 0.82, # Estimated
            "bid_ask_imbalance": 0.78, # Estimated
        }

        # Accuracy tracking
        self.strategy_metrics: Dict[str, AccuracyMetrics] = {}
        self.accuracy_history: Dict[str, deque] = {}  # strategy -> [(timestamp, accuracy), ...]

        # Alert state
        self.active_alerts: Dict[str, DriftAlert] = {}
        self.alert_history: List[DriftAlert] = []

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger.info("accuracy_drift_watchdog.initialized", {
            "baseline_accuracies": self.baseline_accuracies,
            "config": self.config
        })

    async def start_monitoring(self) -> None:
        """Start accuracy drift monitoring"""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Subscribe to strategy events
        await self.event_bus.subscribe("strategy.signal", self._handle_strategy_signal)
        await self.event_bus.subscribe("strategy.result", self._handle_strategy_result)

        self.logger.info("accuracy_drift_watchdog.started")

    async def stop_monitoring(self) -> None:
        """Stop accuracy drift monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        self.logger.info("accuracy_drift_watchdog.stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.config["check_interval"])
                await self._check_accuracy_drift()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("accuracy_drift_watchdog.monitoring_error", {
                    "error": str(e)
                })

    async def _cleanup_loop(self) -> None:
        """Cleanup old historical data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean every hour
                self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("accuracy_drift_watchdog.cleanup_error", {
                    "error": str(e)
                })

    async def _handle_strategy_signal(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle strategy signal events"""
        try:
            strategy_name = data.get("strategy_name", "unknown")
            signal_type = data.get("signal_type")  # "buy", "sell", etc.
            confidence = data.get("confidence", 0.0)

            # Initialize metrics if needed
            if strategy_name not in self.strategy_metrics:
                baseline = self.baseline_accuracies.get(strategy_name, 0.5)  # Default baseline
                self.strategy_metrics[strategy_name] = AccuracyMetrics(
                    strategy_name=strategy_name,
                    baseline_accuracy=baseline
                )
                self.accuracy_history[strategy_name] = deque()

            # For now, we track signals but need results to calculate accuracy
            # This would be enhanced with actual trade outcome tracking

        except Exception as e:
            self.logger.error("accuracy_drift_watchdog.signal_handler_error", {
                "error": str(e),
                "data": data
            })

    async def _handle_strategy_result(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle strategy result events (trade outcomes)"""
        try:
            strategy_name = data.get("strategy_name", "unknown")
            success = data.get("success", False)  # Whether the trade was profitable
            timestamp = data.get("timestamp", time.time())

            if strategy_name not in self.strategy_metrics:
                return

            metrics = self.strategy_metrics[strategy_name]
            metrics.total_signals += 1

            if success:
                metrics.correct_signals += 1

            # Update accuracy
            if metrics.total_signals > 0:
                metrics.accuracy = metrics.correct_signals / metrics.total_signals
                metrics.last_update = timestamp

                # Store in history
                self.accuracy_history[strategy_name].append((timestamp, metrics.accuracy))

        except Exception as e:
            self.logger.error("accuracy_drift_watchdog.result_handler_error", {
                "error": str(e),
                "data": data
            })

    async def _check_accuracy_drift(self) -> None:
        """Check for accuracy drift against baselines"""
        try:
            for strategy_name, metrics in self.strategy_metrics.items():
                if metrics.total_signals < self.config["min_signals_required"]:
                    continue  # Not enough data

                baseline = metrics.baseline_accuracy
                current = metrics.accuracy

                # Calculate drift
                if baseline > 0:
                    drift_percent = ((baseline - current) / baseline) * 100
                else:
                    drift_percent = 0.0

                # Check for drift
                threshold = self.config["drift_threshold_percent"]

                if drift_percent > threshold:
                    await self._handle_drift_detected(strategy_name, metrics, drift_percent)
                elif metrics.drift_detected and drift_percent < self.config["recovery_threshold"]:
                    await self._handle_drift_recovered(strategy_name, metrics, drift_percent)

                # Update metrics
                await self._publish_accuracy_metrics(strategy_name, metrics)

        except Exception as e:
            self.logger.error("accuracy_drift_watchdog.drift_check_error", {
                "error": str(e)
            })

    async def _handle_drift_detected(self, strategy_name: str, metrics: AccuracyMetrics, drift_percent: float) -> None:
        """Handle detected accuracy drift"""
        if strategy_name in self.active_alerts:
            return  # Already alerted

        severity = "high" if drift_percent > self.config["critical_drift_percent"] else "medium"

        alert = DriftAlert(
            strategy_name=strategy_name,
            current_accuracy=metrics.accuracy,
            baseline_accuracy=metrics.baseline_accuracy,
            drift_percent=drift_percent,
            threshold_percent=self.config["drift_threshold_percent"],
            timestamp=time.time(),
            severity=severity
        )

        self.active_alerts[strategy_name] = alert
        self.alert_history.append(alert)

        # Update metrics
        metrics.drift_detected = True
        if not metrics.drift_start_time:
            metrics.drift_start_time = time.time()

        # Log and alert
        self.logger.warning("accuracy_drift_watchdog.drift_detected", {
            "strategy_name": strategy_name,
            "current_accuracy": metrics.accuracy,
            "baseline_accuracy": metrics.baseline_accuracy,
            "drift_percent": drift_percent,
            "severity": severity,
            "total_signals": metrics.total_signals
        })

        # Publish alert
        await self.event_bus.publish("accuracy.drift_detected", {
            "alert": {
                "strategy_name": strategy_name,
                "current_accuracy": metrics.accuracy,
                "baseline_accuracy": metrics.baseline_accuracy,
                "drift_percent": drift_percent,
                "threshold_percent": self.config["drift_threshold_percent"],
                "severity": severity,
                "timestamp": alert.timestamp
            }
        })

    async def _handle_drift_recovered(self, strategy_name: str, metrics: AccuracyMetrics, drift_percent: float) -> None:
        """Handle drift recovery"""
        if strategy_name not in self.active_alerts:
            return

        alert = self.active_alerts.pop(strategy_name)

        # Reset metrics
        metrics.drift_detected = False
        metrics.drift_start_time = None

        # Log recovery
        self.logger.info("accuracy_drift_watchdog.drift_recovered", {
            "strategy_name": strategy_name,
            "current_accuracy": metrics.accuracy,
            "baseline_accuracy": metrics.baseline_accuracy,
            "drift_percent": drift_percent,
            "recovery_time_seconds": time.time() - alert.timestamp
        })

        # Publish recovery event
        await self.event_bus.publish("accuracy.drift_recovered", {
            "strategy_name": strategy_name,
            "current_accuracy": metrics.accuracy,
            "baseline_accuracy": metrics.baseline_accuracy,
            "drift_percent": drift_percent,
            "timestamp": time.time()
        })

    async def _publish_accuracy_metrics(self, strategy_name: str, metrics: AccuracyMetrics) -> None:
        """Publish current accuracy metrics"""
        await self.event_bus.publish("accuracy.metrics", {
            "strategy_name": strategy_name,
            "metrics": {
                "total_signals": metrics.total_signals,
                "correct_signals": metrics.correct_signals,
                "accuracy": metrics.accuracy,
                "baseline_accuracy": metrics.baseline_accuracy,
                "drift_detected": metrics.drift_detected,
                "drift_duration_seconds": (
                    time.time() - metrics.drift_start_time
                    if metrics.drift_start_time else 0
                ),
                "last_update": metrics.last_update
            },
            "timestamp": time.time()
        })

    def _cleanup_old_data(self) -> None:
        """Clean up old historical accuracy data"""
        cutoff_time = time.time() - self.config["history_window"]

        for strategy_name in list(self.accuracy_history.keys()):
            history = self.accuracy_history[strategy_name]

            # Remove old entries
            while history and history[0][0] < cutoff_time:
                history.popleft()

            # Remove empty histories
            if not history:
                del self.accuracy_history[strategy_name]

        # Clean old alerts (keep last 100)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

    def get_accuracy_report(self) -> Dict[str, Any]:
        """Get comprehensive accuracy report"""
        return {
            "strategy_metrics": {
                name: {
                    "total_signals": metrics.total_signals,
                    "correct_signals": metrics.correct_signals,
                    "accuracy": metrics.accuracy,
                    "baseline_accuracy": metrics.baseline_accuracy,
                    "drift_detected": metrics.drift_detected,
                    "drift_start_time": metrics.drift_start_time,
                    "last_update": metrics.last_update
                }
                for name, metrics in self.strategy_metrics.items()
            },
            "active_alerts": {
                name: {
                    "current_accuracy": alert.current_accuracy,
                    "baseline_accuracy": alert.baseline_accuracy,
                    "drift_percent": alert.drift_percent,
                    "threshold_percent": alert.threshold_percent,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp
                }
                for name, alert in self.active_alerts.items()
            },
            "alert_history": [
                {
                    "strategy_name": alert.strategy_name,
                    "drift_percent": alert.drift_percent,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp
                }
                for alert in self.alert_history[-20:]  # Last 20 alerts
            ],
            "config": self.config,
            "timestamp": time.time()
        }

    def update_baseline_accuracy(self, strategy_name: str, new_baseline: float) -> bool:
        """Update baseline accuracy for a strategy (admin function)"""
        try:
            if strategy_name in self.strategy_metrics:
                old_baseline = self.strategy_metrics[strategy_name].baseline_accuracy
                self.strategy_metrics[strategy_name].baseline_accuracy = new_baseline

                self.logger.info("accuracy_drift_watchdog.baseline_updated", {
                    "strategy_name": strategy_name,
                    "old_baseline": old_baseline,
                    "new_baseline": new_baseline
                })

                return True
            else:
                self.baseline_accuracies[strategy_name] = new_baseline
                return True

        except Exception as e:
            self.logger.error("accuracy_drift_watchdog.baseline_update_error", {
                "error": str(e),
                "strategy_name": strategy_name
            })
            return False

    async def inject_test_result(self, strategy_name: str, success: bool) -> bool:
        """Inject test result for testing (admin function)"""
        try:
            await self._handle_strategy_result("test", {
                "strategy_name": strategy_name,
                "success": success,
                "timestamp": time.time()
            })
            return True

        except Exception as e:
            self.logger.error("accuracy_drift_watchdog.inject_test_error", {
                "error": str(e),
                "strategy_name": strategy_name
            })
            return False

    def get_drift_statistics(self) -> Dict[str, Any]:
        """Get drift detection statistics"""
        total_strategies = len(self.strategy_metrics)
        strategies_with_drift = sum(1 for m in self.strategy_metrics.values() if m.drift_detected)
        total_alerts = len(self.alert_history)

        return {
            "total_strategies_monitored": total_strategies,
            "strategies_with_drift": strategies_with_drift,
            "drift_percentage": (strategies_with_drift / max(total_strategies, 1)) * 100,
            "total_alerts": total_alerts,
            "active_alerts": len(self.active_alerts),
            "config": self.config
        }