"""
Metrics Exporter - Sprint 4 Monitoring Integration
==================================================

Production-grade metrics export for monitoring dashboards with Prometheus/Grafana
integration and real-time performance tracking.

Features:
- Prometheus-compatible metrics export
- Real-time latency and throughput monitoring
- Circuit breaker and rate limiter metrics
- Session performance tracking
- Alert threshold configuration
- Historical metrics aggregation

Critical Analysis Points:
1. **Metrics Granularity**: Balances detail with performance impact
2. **Alert Thresholds**: Configurable thresholds prevent alert fatigue
3. **Historical Aggregation**: Efficient storage of time-series data
4. **Export Performance**: Non-blocking metrics collection and export
5. **Monitoring Coverage**: Comprehensive system observability
6. **Integration Compatibility**: Standards-compliant metrics format
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import threading

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from ..data.live_market_adapter import LiveMarketAdapter
from ..trading.session_manager import SessionManager


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series for a metric"""
    name: str
    help_text: str
    type: str  # "counter", "gauge", "histogram", "summary"
    points: deque = field(default_factory=lambda: deque(maxlen=1000))


class MetricsExporter:
    """
    Production-grade metrics exporter for Sprint 4 monitoring.

    Exports metrics in Prometheus format for Grafana dashboards and alerting.
    Provides real-time monitoring of system performance and health.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: StructuredLogger,
        market_adapter: Optional[LiveMarketAdapter] = None,
        session_manager: Optional[SessionManager] = None
    ):
        self.event_bus = event_bus
        self.logger = logger
        self.market_adapter = market_adapter
        self.session_manager = session_manager

        # Metrics storage
        self.metrics: Dict[str, MetricSeries] = {}
        self._metrics_lock = threading.RLock()  # Thread-safe for async operations

        # Configuration
        self.config = {
            "export_interval": 15.0,  # Export every 15 seconds
            "retention_period": 3600.0,  # Keep 1 hour of data
            "max_points_per_metric": 1000,
            "alert_thresholds": {
                "latency_p95": 500.0,  # ms
                "error_rate": 0.05,    # 5%
                "reconnect_count": 10,  # per hour
                "circuit_breaker_open": 1  # any open breakers
            }
        }

        # Background tasks
        self._export_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Initialize standard metrics
        self._initialize_metrics()

        self.logger.info("metrics_exporter.initialized", {
            "config": self.config,
            "standard_metrics_count": len(self.metrics)
        })

    def _initialize_metrics(self) -> None:
        """Initialize standard metric series"""
        # System metrics
        self._create_metric("system_uptime_seconds", "System uptime in seconds", "gauge")
        self._create_metric("system_memory_usage_mb", "Memory usage in MB", "gauge")
        self._create_metric("system_cpu_usage_percent", "CPU usage percentage", "gauge")

        # Market adapter metrics
        self._create_metric("market_adapter_connections_active", "Active WebSocket connections", "gauge")
        self._create_metric("market_adapter_reconnects_total", "Total reconnection attempts", "counter")
        self._create_metric("market_adapter_latency_p95_ms", "95th percentile latency in ms", "gauge")
        self._create_metric("market_adapter_uptime_percent", "Adapter uptime percentage", "gauge")
        self._create_metric("market_adapter_incidents_active", "Active incidents count", "gauge")

        # Session manager metrics
        self._create_metric("session_manager_sessions_active", "Active trading sessions", "gauge")
        self._create_metric("session_manager_sessions_running", "Running trading sessions", "gauge")
        self._create_metric("session_manager_sessions_failed", "Failed trading sessions", "gauge")
        self._create_metric("session_manager_operations_total", "Total operations performed", "counter")
        self._create_metric("session_manager_operations_failed", "Failed operations", "counter")
        self._create_metric("session_manager_circuit_breakers_open", "Open circuit breakers", "gauge")

        # Rate limiting metrics
        self._create_metric("rate_limiter_operations_throttled", "Throttled operations", "counter")
        self._create_metric("rate_limiter_tokens_available", "Available rate limit tokens", "gauge")

        # Cache metrics
        self._create_metric("cache_hit_ratio_percent", "Cache hit ratio percentage", "gauge")
        self._create_metric("cache_size_current", "Current cache size", "gauge")
        self._create_metric("cache_evictions_total", "Total cache evictions", "counter")

        # Alert metrics
        self._create_metric("alerts_fired_total", "Total alerts fired", "counter")
        self._create_metric("alerts_active", "Currently active alerts", "gauge")

    def _create_metric(self, name: str, help_text: str, metric_type: str) -> None:
        """Create a new metric series"""
        self.metrics[name] = MetricSeries(
            name=name,
            help_text=help_text,
            type=metric_type
        )

    async def start_export(self) -> None:
        """Start metrics export"""
        self._export_task = asyncio.create_task(self._export_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Subscribe to monitoring events
        await self.event_bus.subscribe("monitoring.metrics", self._handle_monitoring_event)
        await self.event_bus.subscribe("incident.alert", self._handle_incident_event)
        await self.event_bus.subscribe("session.health", self._handle_session_event)

        self.logger.info("metrics_exporter.started")

    async def stop_export(self) -> None:
        """Stop metrics export"""
        if self._export_task:
            self._export_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        self.logger.info("metrics_exporter.stopped")

    async def _export_loop(self) -> None:
        """Main export loop"""
        while True:
            try:
                await asyncio.sleep(self.config["export_interval"])
                await self._collect_and_export_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("metrics_exporter.export_error", {
                    "error": str(e)
                })

    async def _cleanup_loop(self) -> None:
        """Cleanup old metrics data"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes
                self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("metrics_exporter.cleanup_error", {
                    "error": str(e)
                })

    async def _collect_and_export_metrics(self) -> None:
        """Collect metrics from components and export"""
        try:
            # Collect system metrics
            await self._collect_system_metrics()

            # Collect component metrics
            if self.market_adapter:
                await self._collect_market_adapter_metrics()
            if self.session_manager:
                await self._collect_session_manager_metrics()

            # Check alert thresholds
            await self._check_alert_thresholds()

            # Export to monitoring stack
            await self._export_to_monitoring_stack()

        except Exception as e:
            self.logger.error("metrics_exporter.collection_error", {
                "error": str(e)
            })

    async def _collect_system_metrics(self) -> None:
        """Collect basic system metrics"""
        import psutil

        try:
            # Uptime
            uptime = time.time() - psutil.boot_time()
            self._record_metric("system_uptime_seconds", uptime)

            # Memory
            memory = psutil.virtual_memory()
            self._record_metric("system_memory_usage_mb", memory.used / 1024 / 1024)

            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric("system_cpu_usage_percent", cpu_percent)

        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            self.logger.warning("metrics_exporter.system_metrics_error", {
                "error": str(e)
            })

    async def _collect_market_adapter_metrics(self) -> None:
        """Collect metrics from market adapter"""
        try:
            metrics = await self.market_adapter._collect_metrics()

            # Connection metrics
            self._record_metric("market_adapter_connections_active",
                              metrics.get("connections", {}).get("active_connections", 0))

            # Reconnection metrics
            self._record_metric("market_adapter_reconnects_total",
                              metrics.get("reconnect_count", 0))

            # Performance metrics
            self._record_metric("market_adapter_latency_p95_ms",
                              metrics.get("performance", {}).get("latency_p95", 0))

            # Uptime
            self._record_metric("market_adapter_uptime_percent",
                              metrics.get("uptime_percent", 100))

            # Incidents
            self._record_metric("market_adapter_incidents_active",
                              metrics.get("active_incidents", 0))

        except Exception as e:
            self.logger.error("metrics_exporter.market_adapter_metrics_error", {
                "error": str(e)
            })

    async def _collect_session_manager_metrics(self) -> None:
        """Collect metrics from session manager"""
        try:
            stats = await self.session_manager.get_stats()

            # Session metrics
            self._record_metric("session_manager_sessions_active", stats["total_sessions"])
            self._record_metric("session_manager_sessions_running", stats["running_sessions"])
            self._record_metric("session_manager_sessions_failed", stats["failed_sessions"])

            # Operation metrics
            self._record_metric("session_manager_operations_total", stats["total_operations"])
            self._record_metric("session_manager_operations_failed", stats["total_failures"])

            # Circuit breaker metrics (simplified - count open breakers)
            open_breakers = 0
            async with self.session_manager.session_lock:
                for session in self.session_manager.active_sessions.values():
                    open_breakers += sum(
                        1 for cb in session.circuit_breakers.values()
                        if cb.state.name == "OPEN"
                    )
            self._record_metric("session_manager_circuit_breakers_open", open_breakers)

        except Exception as e:
            self.logger.error("metrics_exporter.session_manager_metrics_error", {
                "error": str(e)
            })

    async def _check_alert_thresholds(self) -> None:
        """Check metrics against alert thresholds"""
        alerts_fired = 0

        # Check latency
        latency_metric = self.metrics.get("market_adapter_latency_p95_ms")
        if latency_metric and latency_metric.points:
            latest_latency = latency_metric.points[-1].value
            if latest_latency > self.config["alert_thresholds"]["latency_p95"]:
                alerts_fired += 1
                await self._fire_alert("high_latency", {
                    "metric": "latency_p95_ms",
                    "value": latest_latency,
                    "threshold": self.config["alert_thresholds"]["latency_p95"]
                })

        # Check error rate
        operations_total = self._get_latest_metric_value("session_manager_operations_total")
        operations_failed = self._get_latest_metric_value("session_manager_operations_failed")
        if operations_total and operations_total > 0:
            error_rate = operations_failed / operations_total
            if error_rate > self.config["alert_thresholds"]["error_rate"]:
                alerts_fired += 1
                await self._fire_alert("high_error_rate", {
                    "error_rate": error_rate,
                    "threshold": self.config["alert_thresholds"]["error_rate"]
                })

        # Check reconnects
        reconnects = self._get_latest_metric_value("market_adapter_reconnects_total")
        if reconnects and reconnects > self.config["alert_thresholds"]["reconnect_count"]:
            alerts_fired += 1
            await self._fire_alert("high_reconnects", {
                "reconnects": reconnects,
                "threshold": self.config["alert_thresholds"]["reconnect_count"]
            })

        # Check circuit breakers
        open_breakers = self._get_latest_metric_value("session_manager_circuit_breakers_open")
        if open_breakers and open_breakers >= self.config["alert_thresholds"]["circuit_breaker_open"]:
            alerts_fired += 1
            await self._fire_alert("circuit_breakers_open", {
                "open_count": open_breakers
            })

        if alerts_fired > 0:
            self._record_metric("alerts_fired_total", alerts_fired, increment=True)

    async def _fire_alert(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Fire an alert through the event bus"""
        await self.event_bus.publish("alert.fired", {
            "alert_type": alert_type,
            "severity": "warning",  # Could be configurable
            "details": details,
            "timestamp": time.time()
        })

        self.logger.warning("metrics_exporter.alert_fired", {
            "alert_type": alert_type,
            "details": details
        })

    def _record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        increment: bool = False
    ) -> None:
        """Record a metric value"""
        with self._metrics_lock:
            if name not in self.metrics:
                self.logger.warning("metrics_exporter.unknown_metric", {
                    "metric_name": name
                })
                return

            metric = self.metrics[name]

            if increment and metric.points:
                # For counters, increment from last value
                value = metric.points[-1].value + value

            point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            )

            metric.points.append(point)

    def _get_latest_metric_value(self, name: str) -> Optional[float]:
        """Get the latest value for a metric"""
        with self._metrics_lock:
            metric = self.metrics.get(name)
            if metric and metric.points:
                return metric.points[-1].value
        return None

    def _cleanup_old_data(self) -> None:
        """Remove old metric data points"""
        cutoff_time = time.time() - self.config["retention_period"]

        with self._metrics_lock:
            for metric in self.metrics.values():
                # Remove old points
                while metric.points and metric.points[0].timestamp < cutoff_time:
                    metric.points.popleft()

    async def _export_to_monitoring_stack(self) -> None:
        """Export metrics to Prometheus/Grafana"""
        # This would integrate with actual monitoring stack
        # For now, just publish as event
        prometheus_format = self._format_prometheus_metrics()

        await self.event_bus.publish("metrics.export", {
            "format": "prometheus",
            "data": prometheus_format,
            "timestamp": time.time()
        })

    def _format_prometheus_metrics(self) -> str:
        """Format metrics in Prometheus exposition format"""
        lines = []

        for metric in self.metrics.values():
            if not metric.points:
                continue

            # HELP and TYPE lines
            lines.append(f"# HELP {metric.name} {metric.help_text}")
            lines.append(f"# TYPE {metric.name} {metric.type}")

            # Latest value
            latest_point = metric.points[-1]
            label_str = ""
            if latest_point.labels:
                labels = [f'{k}="{v}"' for k, v in latest_point.labels.items()]
                label_str = "{" + ",".join(labels) + "}"

            lines.append(f"{metric.name}{label_str} {latest_point.value} {int(latest_point.timestamp * 1000)}")

        return "\n".join(lines)

    async def _handle_monitoring_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle monitoring events from components"""
        try:
            # Extract metrics from event data and record them
            component = data.get("component", "unknown")
            metrics_data = data.get("metrics", {})

            for metric_name, value in metrics_data.items():
                if isinstance(value, (int, float)):
                    full_name = f"{component}_{metric_name}"
                    self._record_metric(full_name, float(value))

        except Exception as e:
            self.logger.error("metrics_exporter.monitoring_event_error", {
                "error": str(e),
                "event_data": data
            })

    async def _handle_incident_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle incident events"""
        try:
            severity = data.get("incident", {}).get("severity", "low")

            # Record incident metrics
            if severity == "critical":
                self._record_metric("alerts_active", 1, increment=True)
            elif severity == "high":
                self._record_metric("alerts_active", 1, increment=True)

        except Exception as e:
            self.logger.error("metrics_exporter.incident_event_error", {
                "error": str(e)
            })

    async def _handle_session_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle session health events"""
        try:
            # Record session health metrics
            session_state = data.get("state")
            if session_state == "running":
                self._record_metric("session_manager_sessions_running", 1, increment=True)
            elif session_state == "failed":
                self._record_metric("session_manager_sessions_failed", 1, increment=True)

        except Exception as e:
            self.logger.error("metrics_exporter.session_event_error", {
                "error": str(e)
            })

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics"""
        with self._metrics_lock:
            summary = {}
            for name, metric in self.metrics.items():
                if metric.points:
                    latest = metric.points[-1]
                    summary[name] = {
                        "value": latest.value,
                        "timestamp": latest.timestamp,
                        "type": metric.type,
                        "points_count": len(metric.points)
                    }
            return summary

    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status"""
        alerts_active = self._get_latest_metric_value("alerts_active") or 0
        alerts_fired = self._get_latest_metric_value("alerts_fired_total") or 0

        return {
            "alerts_active": alerts_active,
            "alerts_fired_total": alerts_fired,
            "alert_thresholds": self.config["alert_thresholds"]
        }