"""
Telemetry and Metrics Collection System

Provides comprehensive monitoring and metrics collection for the trading system.
Includes performance metrics, business metrics, and health monitoring.
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
import json
import logging
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Represents a single metric measurement"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series data for a metric"""
    name: str
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)

    def add_value(self, value: float, timestamp: Optional[datetime] = None):
        """Add a new value to the series"""
        if timestamp is None:
            timestamp = datetime.now(UTC)
        self.values.append(MetricValue(self.name, value, timestamp, self.tags.copy()))

    def get_recent(self, seconds: int = 60) -> List[MetricValue]:
        """Get values from the last N seconds"""
        cutoff = datetime.now(UTC).timestamp() - seconds
        return [v for v in self.values if v.timestamp.timestamp() > cutoff]

    def get_stats(self, seconds: int = 60) -> Dict[str, float]:
        """Get statistical summary of recent values"""
        recent = self.get_recent(seconds)
        if not recent:
            return {}

        values = [v.value for v in recent]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'stddev': statistics.stdev(values) if len(values) > 1 else 0,
            'latest': values[-1]
        }


class MetricsCollector:
    """✅ PERF FIX: Central metrics collection system with bounded structures to prevent memory leaks"""

    # ✅ PERF FIX: Maximum sizes to prevent unbounded growth
    MAX_SERIES = 1000
    MAX_COUNTERS = 10000
    MAX_GAUGES = 5000
    MAX_HISTOGRAMS = 1000
    MAX_HISTOGRAM_VALUES = 1000

    def __init__(self):
        self.series: Dict[str, MetricSeries] = {}
        self.counters: Dict[str, int] = {}  # ✅ PERF FIX: Removed defaultdict, using explicit dict
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}  # ✅ PERF FIX: Removed defaultdict
        self._lock = threading.Lock()
        self._system_monitoring = False

    def create_series(self, name: str, tags: Dict[str, str] = None) -> MetricSeries:
        """✅ PERF FIX: Create a new metric series with bounded limit"""
        if name not in self.series:
            # ✅ PERF FIX: Enforce max series limit
            if len(self.series) >= self.MAX_SERIES:
                # Remove oldest series (simple FIFO)
                oldest_key = next(iter(self.series))
                del self.series[oldest_key]
            self.series[name] = MetricSeries(name, tags=tags or {})
        return self.series[name]

    def record(self, name: str, value: float, tags: Dict[str, str] = None):
        """✅ PERF FIX: Record a metric value with bounded series limit"""
        with self._lock:
            if name not in self.series:
                # ✅ PERF FIX: Enforce max series limit
                if len(self.series) >= self.MAX_SERIES:
                    oldest_key = next(iter(self.series))
                    del self.series[oldest_key]
                self.series[name] = MetricSeries(name, tags=tags or {})
            self.series[name].add_value(value)

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """✅ PERF FIX: Increment a counter metric with bounded limit"""
        with self._lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            # ✅ PERF FIX: Enforce max counters limit
            if key not in self.counters:
                if len(self.counters) >= self.MAX_COUNTERS:
                    # Remove oldest counter (simple FIFO)
                    oldest_key = next(iter(self.counters))
                    del self.counters[oldest_key]
                self.counters[key] = 0
            self.counters[key] += value

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """✅ PERF FIX: Set a gauge metric with bounded limit"""
        with self._lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            # ✅ PERF FIX: Enforce max gauges limit
            if key not in self.gauges and len(self.gauges) >= self.MAX_GAUGES:
                # Remove oldest gauge (simple FIFO)
                oldest_key = next(iter(self.gauges))
                del self.gauges[oldest_key]
            self.gauges[key] = value

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """✅ PERF FIX: Record a value in a histogram with bounded limits"""
        with self._lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            # ✅ PERF FIX: Enforce max histograms limit
            if key not in self.histograms:
                if len(self.histograms) >= self.MAX_HISTOGRAMS:
                    # Remove oldest histogram
                    oldest_key = next(iter(self.histograms))
                    del self.histograms[oldest_key]
                self.histograms[key] = []

            self.histograms[key].append(value)
            # ✅ PERF FIX: Keep only last MAX_HISTOGRAM_VALUES
            if len(self.histograms[key]) > self.MAX_HISTOGRAM_VALUES:
                self.histograms[key] = self.histograms[key][-self.MAX_HISTOGRAM_VALUES:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self._lock:
            summary = {
                'timestamp': datetime.now(UTC).isoformat(),
                'system': self._get_system_metrics(),
                'application': self._get_application_metrics(),
                'business': self._get_business_metrics()
            }
            return summary

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used_mb': psutil.virtual_memory().used / 1024 / 1024,
                'memory_available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    def _get_application_metrics(self) -> Dict[str, Any]:
        """Get application-level metrics"""
        metrics = {}

        # Series statistics
        for name, series in self.series.items():
            if series.values:
                stats = series.get_stats(300)  # Last 5 minutes
                if stats:
                    metrics[f"series_{name}"] = stats

        # Counters
        for key, value in self.counters.items():
            name = key.split(':')[0]
            metrics[f"counter_{name}"] = value

        # Gauges
        for key, value in self.gauges.items():
            name = key.split(':')[0]
            metrics[f"gauge_{name}"] = value

        # Histograms
        for key, values in self.histograms.items():
            if values:
                name = key.split(':')[0]
                metrics[f"histogram_{name}"] = {
                    'count': len(values),
                    'avg': statistics.mean(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                }

        return metrics

    def _get_business_metrics(self) -> Dict[str, Any]:
        """Get business-level metrics"""
        # This would include trading-specific metrics
        return {
            'active_strategies': 0,  # TODO: Implement
            'total_trades': 0,       # TODO: Implement
            'success_rate': 0.0,     # TODO: Implement
            'total_pnl': 0.0,        # TODO: Implement
        }

    def start_system_monitoring(self):
        """Start automatic system metrics collection"""
        if self._system_monitoring:
            return

        self._system_monitoring = True

        def monitor_system():
            while self._system_monitoring:
                try:
                    # CPU metrics - optimized interval to minimize CPU impact
                    self.record('system.cpu_percent', psutil.cpu_percent(interval=0.5))

                    # Memory metrics
                    mem = psutil.virtual_memory()
                    self.record('system.memory_percent', mem.percent)
                    self.record('system.memory_used_mb', mem.used / 1024 / 1024)

                    # Network metrics
                    net = psutil.net_io_counters()
                    self.record('system.network_bytes_sent', net.bytes_sent)
                    self.record('system.network_bytes_recv', net.bytes_recv)

                    time.sleep(30)  # Collect every 30 seconds - balanced monitoring

                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    time.sleep(10)

        thread = threading.Thread(target=monitor_system, daemon=True)
        thread.start()
        logger.info("System monitoring started")

    def stop_system_monitoring(self):
        """Stop automatic system metrics collection"""
        self._system_monitoring = False
        logger.info("System monitoring stopped")


class TelemetryService:
    """High-level telemetry service"""

    def __init__(self):
        self.collector = MetricsCollector()
        self._started = False

    def start(self):
        """Start telemetry collection"""
        if self._started:
            return

        self._started = True
        # System monitoring with optimized settings to prevent CPU overload
        self.collector.start_system_monitoring()
        logger.info("Telemetry service started (system monitoring disabled)")

    def stop(self):
        """Stop telemetry collection"""
        if not self._started:
            return

        self._started = False
        self.collector.stop_system_monitoring()
        logger.info("Telemetry service stopped")

    def record_api_call(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Record API call metrics"""
        self.collector.record(
            'api.response_time',
            duration_ms,
            {'endpoint': endpoint, 'method': method}
        )
        self.collector.increment_counter(
            'api.requests_total',
            tags={'endpoint': endpoint, 'method': method, 'status': str(status_code)}
        )

    def record_websocket_message(self, message_type: str, size_bytes: int):
        """Record WebSocket message metrics"""
        self.collector.record('websocket.message_size', size_bytes, {'type': message_type})
        self.collector.increment_counter('websocket.messages_total', tags={'type': message_type})

    def record_strategy_execution(self, strategy_name: str, execution_time_ms: float, success: bool):
        """Record strategy execution metrics"""
        self.collector.record(
            'strategy.execution_time',
            execution_time_ms,
            {'strategy': strategy_name, 'success': str(success)}
        )
        self.collector.increment_counter(
            'strategy.executions_total',
            tags={'strategy': strategy_name, 'success': str(success)}
        )

    def record_error(self, error_type: str, component: str, message: str = ""):
        """Record error metrics"""
        self.collector.increment_counter(
            'errors_total',
            tags={'type': error_type, 'component': component}
        )

    def record(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value (delegate to collector)"""
        self.collector.record(name, value, tags)

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter (delegate to collector)"""
        self.collector.increment_counter(name, value, tags)

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge value (delegate to collector)"""
        self.collector.set_gauge(name, value, tags)

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status based on metrics"""
        metrics = self.collector.get_metrics_summary()

        # Simple health checks
        health_status = {
            'status': 'healthy',
            'checks': {},
            'metrics': metrics
        }

        # CPU health check
        cpu_percent = metrics.get('system', {}).get('cpu_percent', 0)
        if cpu_percent > 99:
            health_status['status'] = 'unhealthy'
            health_status['checks']['cpu'] = 'high_usage'
        else:
            health_status['checks']['cpu'] = 'ok'

        # Memory health check
        mem_percent = metrics.get('system', {}).get('memory_percent', 0)
        if mem_percent > 99:
            health_status['status'] = 'unhealthy'
            health_status['checks']['memory'] = 'high_usage'
        else:
            health_status['checks']['memory'] = 'ok'

        return health_status

    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return self.collector.get_metrics_summary()


# Global telemetry instance
telemetry = TelemetryService()


def record_api_metrics(endpoint: str, method: str = "GET"):
    """Decorator to record API call metrics"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Try to get status code from response
                status_code = getattr(result, 'status_code', 200) if hasattr(result, '__dict__') else 200

                telemetry.record_api_call(endpoint, method, duration_ms, status_code)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                telemetry.record_api_call(endpoint, method, duration_ms, 500)
                telemetry.record_error('api_exception', endpoint, str(e))
                raise
        return wrapper
    return decorator