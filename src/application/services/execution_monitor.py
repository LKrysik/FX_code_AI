"""
Execution Monitor Service
=========================
Real-time monitoring and metrics collection for execution sessions.
"""

import asyncio
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import deque
from numbers import Number
from concurrent.futures import ThreadPoolExecutor

from ...core.event_bus import EventBus, EventPriority
from ...core.logger import StructuredLogger


@dataclass
class ExecutionMetrics:
    """Execution metrics snapshot"""
    session_id: str
    timestamp: datetime
    
    # Progress metrics
    progress_percent: float
    eta_seconds: Optional[float]
    processing_rate: float  # events/second
    
    # Signal detection metrics
    signals_detected: int
    signals_per_minute: float
    avg_signal_confidence: float
    detection_latency_ms: float
    
    # Trading performance
    orders_placed: int
    orders_filled: int
    orders_rejected: int
    unrealized_pnl: float
    realized_pnl: float
    
    # System performance
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    eventbus_throughput: float
    cache_hit_rate: float


@dataclass
class AlertConfig:
    """Alert configuration"""
    metric_name: str
    threshold: float
    comparison: str  # 'gt', 'lt', 'eq'
    enabled: bool = True
    cooldown_seconds: int = 60


class ExecutionMonitor:
    """
    Real-time execution monitoring service.
    Collects metrics, calculates ETA, and triggers alerts.
    """
    
    def __init__(self, event_bus: EventBus, logger: StructuredLogger):
        self.event_bus = event_bus
        self.logger = logger

        # Thread safety locks
        self._state_lock = asyncio.Lock()  # Protects shared state dictionaries
        self._metrics_lock = asyncio.Lock()  # Protects metrics operations
        self._alert_lock = asyncio.Lock()  # Protects alert system

        # Thread pool for CPU-intensive operations (psutil)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ExecutionMonitor")

        # Monitoring state
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._metrics_history: Dict[str, deque] = {}
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Performance tracking with memory limits
        self._processing_rates: Dict[str, deque] = {}
        self._signal_counts: Dict[str, int] = {}
        self._signal_timestamps: Dict[str, deque] = {}
        self._order_counts: Dict[str, Dict[str, int]] = {}
        self._pnl_tracking: Dict[str, Dict[str, float]] = {}

        # System metrics with bounded collections
        self._system_metrics = {
            "cpu_samples": deque(maxlen=60),  # 1 minute of samples
            "memory_samples": deque(maxlen=60),
            "eventbus_samples": deque(maxlen=60)
        }

        # Alert system with weak references to prevent memory leaks
        import weakref
        self._alert_configs: List[AlertConfig] = []
        self._last_alerts: Dict[str, float] = {}
        self._alert_callbacks: weakref.WeakSet = weakref.WeakSet()  # Prevents memory leaks

        # Memory management settings
        self._max_metrics_per_session = 1800  # 30 minutes at 10s intervals
        self._metrics_history_ttl = 1800  # 30 minutes TTL
        self._cleanup_interval = 300  # Cleanup every 5 minutes

        # Event subscriptions will be set up when monitoring starts
        self._subscriptions_setup = False

        # Default alert configurations
        self._setup_default_alerts()
    
    def _setup_default_alerts(self) -> None:
        """Setup default alert configurations"""
        self._alert_configs = [
            AlertConfig("cpu_percent", 80.0, "gt"),
            AlertConfig("memory_percent", 85.0, "gt"),
            AlertConfig("detection_latency_ms", 1000.0, "gt"),
            AlertConfig("orders_rejected", 10, "gt"),
            AlertConfig("unrealized_pnl", -1000.0, "lt")
        ]
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add alert callback with automatic cleanup to prevent memory leaks"""
        self._alert_callbacks.add(callback)
    
    async def start_monitoring(self) -> None:
        """Start monitoring service"""
        if self._is_monitoring:
            return
        
        # Setup event subscriptions
        if not self._subscriptions_setup:
            await self.event_bus.subscribe("execution.session_started", self._on_session_started)
            await self.event_bus.subscribe("execution.session_stopped", self._on_session_stopped)
            await self.event_bus.subscribe("execution.progress_update", self._on_progress_update)
            await self.event_bus.subscribe("signal.detected", self._on_signal_detected)
            await self.event_bus.subscribe("order.placed", self._on_order_placed)
            await self.event_bus.subscribe("order.filled", self._on_order_filled)
            await self.event_bus.subscribe("order.rejected", self._on_order_rejected)
            await self.event_bus.subscribe("position.pnl_update", self._on_pnl_update)
            self._subscriptions_setup = True
        
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("execution_monitor.started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring service with proper cleanup"""
        self._is_monitoring = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Shutdown thread pool executor
        if self._executor:
            self._executor.shutdown(wait=True)

        self.logger.info("execution_monitor.stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop with reduced frequency and memory cleanup"""
        cleanup_counter = 0

        try:
            while self._is_monitoring:
                # Collect system metrics less frequently
                await self._collect_system_metrics_async()

                # Update metrics for all active sessions (less frequently)
                async with self._state_lock:
                    active_session_ids = list(self._active_sessions.keys())

                for session_id in active_session_ids:
                    await self._update_session_metrics(session_id)

                # Check alerts
                await self._check_alerts()

                # Periodic cleanup to prevent memory leaks
                cleanup_counter += 1
                if cleanup_counter >= (self._cleanup_interval // 10):  # Every 5 minutes at 10s intervals
                    await self._cleanup_stale_metrics()
                    cleanup_counter = 0

                # CRITICAL FIX: Increased interval from 1s to 10s to reduce CPU usage
                await asyncio.sleep(10.0)  # 10 second interval instead of 1

        except asyncio.CancelledError:
            return
        except Exception as e:
            self.logger.error("execution_monitor.loop_error", {
                "error": str(e)
            })
    
    async def _collect_system_metrics_async(self) -> None:
        """Collect system performance metrics asynchronously to prevent blocking"""
        try:
            loop = asyncio.get_event_loop()

            # Run psutil calls in thread pool to prevent blocking event loop
            cpu_percent, memory_info = await asyncio.gather(
                loop.run_in_executor(self._executor, psutil.cpu_percent, None),
                loop.run_in_executor(self._executor, psutil.virtual_memory),
                return_exceptions=True
            )

            # Handle exceptions from thread pool
            if isinstance(cpu_percent, Exception):
                cpu_percent = 0.0
            if isinstance(memory_info, Exception):
                memory_info = type('MemInfo', (), {'percent': 0.0, 'used': 0})()

            async with self._metrics_lock:
                # Store CPU metrics
                self._system_metrics["cpu_samples"].append(cpu_percent)

                # Store memory metrics
                self._system_metrics["memory_samples"].append({
                    "percent": memory_info.percent,
                    "used_mb": memory_info.used / (1024 * 1024)
                })

            # EventBus metrics (already async)
            eventbus_health = await self.event_bus.health_check()
            async with self._metrics_lock:
                self._system_metrics["eventbus_samples"].append({
                    "queue_size": eventbus_health.get("total_queue_size", 0),
                    "active_subscribers": eventbus_health.get("active_subscribers", 0),
                    "processing_rate": eventbus_health.get("metrics", {}).get("total_processed", 0)
                })

        except Exception as e:
            self.logger.error("execution_monitor.system_metrics_error", {
                "error": str(e)
            })

    # Legacy method for backward compatibility
    async def _collect_system_metrics(self) -> None:
        """Legacy method - redirects to async version"""
        await self._collect_system_metrics_async()
    
    async def _update_session_metrics(self, session_id: str) -> None:
        """Update metrics for a specific session with thread safety"""
        async with self._state_lock:
            if session_id not in self._active_sessions:
                return

            session_data = self._active_sessions[session_id]

        try:
            # Calculate processing rate (thread-safe)
            processing_rate = self._calculate_processing_rate(session_id)

            # Calculate ETA (thread-safe)
            eta_seconds = self._calculate_eta(session_id, processing_rate)

            # Get signal metrics (thread-safe)
            signal_metrics = self._get_signal_metrics(session_id)

            # Get trading metrics (thread-safe)
            trading_metrics = self._get_trading_metrics(session_id)

            # Get system metrics (thread-safe)
            system_metrics = self._get_current_system_metrics()

            # Create metrics snapshot
            try:
                metrics = ExecutionMetrics(
                    session_id=session_id,
                    timestamp=datetime.now(),
                    progress_percent=float(session_data.get("progress", 0.0)),
                    eta_seconds=eta_seconds,
                    processing_rate=float(processing_rate),
                    **signal_metrics,
                    **trading_metrics,
                    **system_metrics
                )
            except Exception as e:
                # Log detailed information about the error
                self.logger.error("execution_monitor.metrics_creation_error", {
                    "session_id": session_id,
                    "session_data": session_data,
                    "eta_seconds": eta_seconds,
                    "processing_rate": processing_rate,
                    "signal_metrics": signal_metrics,
                    "trading_metrics": trading_metrics,
                    "system_metrics": system_metrics,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise

            async with self._metrics_lock:
                # Store in history with memory limits
                if session_id not in self._metrics_history:
                    self._metrics_history[session_id] = deque(maxlen=self._max_metrics_per_session)

                self._metrics_history[session_id].append(metrics)

            # Publish metrics update
            await self.event_bus.publish(
                "execution.metrics_update",
                {
                    "session_id": session_id,
                    "metrics": asdict(metrics)
                },
                priority=EventPriority.NORMAL
            )

        except Exception as e:
            self.logger.error("execution_monitor.session_metrics_error", {
                "session_id": session_id,
                "error": str(e)
            })
    
    def _calculate_processing_rate(self, session_id: str) -> float:
        """Calculate events processing rate"""
        if session_id not in self._processing_rates:
            return 0.0

        rates = self._processing_rates[session_id]
        numeric_rates = [r for r in rates if isinstance(r, Number)]
        if len(numeric_rates) < 2:
            return 0.0

        if len(numeric_rates) != len(rates):
            self._processing_rates[session_id] = deque(numeric_rates, maxlen=rates.maxlen)
            rates = self._processing_rates[session_id]
            numeric_rates = list(rates)

        # Average rate over last 10 numeric samples
        recent_rates = numeric_rates[-10:]
        return sum(recent_rates) / len(recent_rates)

    def _calculate_eta(self, session_id: str, processing_rate: float) -> Optional[float]:
        """Calculate estimated time to completion"""
        if session_id not in self._active_sessions:
            return None
        
        session_data = self._active_sessions[session_id]
        progress = session_data.get("progress", 0.0)
        
        if progress >= 100.0 or processing_rate <= 0:
            return None
        
        remaining_percent = 100.0 - progress
        eta_seconds = (remaining_percent / processing_rate) if processing_rate > 0 else None
        
        return eta_seconds
    
    def _get_signal_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get signal detection metrics"""
        signal_count = self._signal_counts.get(session_id, 0)
        
        # Calculate signals per minute
        if session_id in self._signal_timestamps:
            timestamps = self._signal_timestamps[session_id]
            now = time.time()
            recent_signals = [ts for ts in timestamps if now - ts <= 60]  # Last minute
            signals_per_minute = len(recent_signals)
        else:
            signals_per_minute = 0
        
        return {
            "signals_detected": signal_count,
            "signals_per_minute": float(signals_per_minute),
            "avg_signal_confidence": 0.75,  # Placeholder
            "detection_latency_ms": 50.0  # Placeholder
        }
    

    def _extract_progress_value(self, value: Any) -> Optional[float]:
        """Normalize various progress payload formats to a float percentage."""
        if isinstance(value, Number):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.endswith('%'):
                cleaned = cleaned[:-1]
            try:
                return float(cleaned)
            except ValueError:
                return None
        if isinstance(value, dict):
            for key in ("percentage", "value", "current", "progress", "percent"):
                if key in value:
                    extracted = self._extract_progress_value(value[key])
                    if extracted is not None:
                        return extracted
            return None
        return None

    def _get_trading_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get trading performance metrics"""
        order_counts = self._order_counts.get(session_id, {})
        pnl_data = self._pnl_tracking.get(session_id, {})
        
        return {
            "orders_placed": order_counts.get("placed", 0),
            "orders_filled": order_counts.get("filled", 0),
            "orders_rejected": order_counts.get("rejected", 0),
            "unrealized_pnl": pnl_data.get("unrealized", 0.0),
            "realized_pnl": pnl_data.get("realized", 0.0)
        }
    
    def _get_current_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_samples = self._system_metrics["cpu_samples"]
        memory_samples = self._system_metrics["memory_samples"]
        eventbus_samples = self._system_metrics["eventbus_samples"]
        
        # Calculate averages
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        
        if memory_samples:
            latest_memory = memory_samples[-1]
            avg_memory_percent = latest_memory["percent"]
            avg_memory_mb = latest_memory["used_mb"]
        else:
            avg_memory_percent = 0.0
            avg_memory_mb = 0.0
        
        if eventbus_samples:
            latest_eventbus = eventbus_samples[-1]
            eventbus_throughput = latest_eventbus["processing_rate"]
        else:
            eventbus_throughput = 0.0
        
        return {
            "cpu_percent": avg_cpu,
            "memory_percent": avg_memory_percent,
            "memory_used_mb": avg_memory_mb,
            "eventbus_throughput": eventbus_throughput,
            "cache_hit_rate": 95.0  # Placeholder
        }
    
    async def _check_alerts(self) -> None:
        """Check alert conditions and trigger if needed with thread safety"""
        now = time.time()

        async with self._state_lock:
            active_session_ids = list(self._active_sessions.keys())

        for session_id in active_session_ids:
            async with self._metrics_lock:
                if session_id not in self._metrics_history:
                    continue

                metrics_history = self._metrics_history[session_id]
                if not metrics_history:
                    continue

                latest_metrics = metrics_history[-1]

            async with self._alert_lock:
                for alert_config in self._alert_configs:
                    if not alert_config.enabled:
                        continue

                    alert_key = f"{session_id}:{alert_config.metric_name}"

                    # Check cooldown
                    if alert_key in self._last_alerts:
                        if now - self._last_alerts[alert_key] < alert_config.cooldown_seconds:
                            continue

                    # Get metric value
                    metric_value = getattr(latest_metrics, alert_config.metric_name, None)
                    if metric_value is None:
                        continue

                    # Check condition
                    triggered = False
                    if alert_config.comparison == "gt" and metric_value > alert_config.threshold:
                        triggered = True
                    elif alert_config.comparison == "lt" and metric_value < alert_config.threshold:
                        triggered = True
                    elif alert_config.comparison == "eq" and metric_value == alert_config.threshold:
                        triggered = True

                    if triggered:
                        await self._trigger_alert(session_id, alert_config, metric_value)
                        self._last_alerts[alert_key] = now
    
    async def _trigger_alert(self, session_id: str, alert_config: AlertConfig, value: Any) -> None:
        """Trigger an alert with thread-safe callback iteration"""
        alert_data = {
            "session_id": session_id,
            "metric_name": alert_config.metric_name,
            "threshold": alert_config.threshold,
            "current_value": value,
            "comparison": alert_config.comparison,
            "timestamp": datetime.now().isoformat(),
            "severity": "warning" if alert_config.comparison in ["gt", "lt"] else "info"
        }

        self.logger.warning("execution_monitor.alert_triggered", alert_data)

        # Notify callbacks (WeakSet automatically handles dead references)
        async with self._alert_lock:
            callbacks_to_notify = list(self._alert_callbacks)  # Create snapshot

        for callback in callbacks_to_notify:
            try:
                if callable(callback):  # Extra safety check
                    callback(alert_data)
            except Exception as e:
                self.logger.error("execution_monitor.alert_callback_error", {
                    "error": str(e)
                })

        # Publish alert event
        await self.event_bus.publish(
            "execution.alert",
            alert_data,
            priority=EventPriority.HIGH
        )

    async def _cleanup_stale_metrics(self) -> None:
        """Clean up old metrics to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(seconds=self._metrics_history_ttl)

        async with self._metrics_lock:
            sessions_to_remove = []
            for session_id, metrics_deque in self._metrics_history.items():
                # Check if session is no longer active
                async with self._state_lock:
                    is_active = session_id in self._active_sessions

                if not is_active:
                    # Session is no longer active
                    if not metrics_deque or metrics_deque[-1].timestamp < cutoff_time:
                        sessions_to_remove.append(session_id)
                    else:
                        # Remove old metrics from deque
                        while metrics_deque and metrics_deque[0].timestamp < cutoff_time:
                            metrics_deque.popleft()

            # Remove completely stale sessions
            for session_id in sessions_to_remove:
                del self._metrics_history[session_id]
                # Also cleanup related tracking data
                self._processing_rates.pop(session_id, None)
                self._signal_counts.pop(session_id, None)
                self._signal_timestamps.pop(session_id, None)
                self._order_counts.pop(session_id, None)
                self._pnl_tracking.pop(session_id, None)

            if sessions_to_remove:
                self.logger.info("execution_monitor.stale_sessions_cleaned", {
                    "cleaned_count": len(sessions_to_remove)
                })
    
    # Event handlers with thread safety
    async def _on_session_started(self, data: Dict[str, Any]) -> None:
        """Handle session started event with thread safety"""
        session = data.get("session", {})
        session_id = session.get("session_id")

        if session_id:
            async with self._state_lock:
                self._active_sessions[session_id] = session
                self._processing_rates[session_id] = deque(maxlen=60)
                self._signal_counts[session_id] = 0
                self._signal_timestamps[session_id] = deque(maxlen=1000)
                self._order_counts[session_id] = {"placed": 0, "filled": 0, "rejected": 0}
                self._pnl_tracking[session_id] = {"unrealized": 0.0, "realized": 0.0}

    async def _on_session_stopped(self, data: Dict[str, Any]) -> None:
        """Handle session stopped event with thread safety"""
        session = data.get("session", {})
        session_id = session.get("session_id")

        if session_id:
            async with self._state_lock:
                self._active_sessions.pop(session_id, None)
                # Note: Don't delete tracking data here - let cleanup handle it
    
    async def _on_progress_update(self, data: Dict[str, Any]) -> None:
        """Handle progress update event with thread safety"""
        session_id = data.get("session_id")
        progress_payload = data.get("progress", {})

        nested_payload = data.get("data") if session_id is None else None
        if session_id is None and isinstance(nested_payload, dict):
            session_id = nested_payload.get("session_id")
            if not progress_payload:
                progress_payload = nested_payload.get("progress", progress_payload)

        progress = self._extract_progress_value(progress_payload)
        if progress is None:
            progress = 0.0

        async with self._state_lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id]["progress"] = progress

                # Update processing rate
                if session_id in self._processing_rates:
                    self._processing_rates[session_id].append(progress)

    async def _on_signal_detected(self, data: Dict[str, Any]) -> None:
        """Handle signal detected event with thread safety"""
        session_id = data.get("session_id", "unknown")

        async with self._state_lock:
            if session_id in self._signal_counts:
                self._signal_counts[session_id] += 1
                if session_id in self._signal_timestamps:
                    self._signal_timestamps[session_id].append(time.time())

    async def _on_order_placed(self, data: Dict[str, Any]) -> None:
        """Handle order placed event with thread safety"""
        session_id = data.get("session_id", "unknown")

        async with self._state_lock:
            if session_id in self._order_counts:
                self._order_counts[session_id]["placed"] += 1

    async def _on_order_filled(self, data: Dict[str, Any]) -> None:
        """Handle order filled event with thread safety"""
        session_id = data.get("session_id", "unknown")

        async with self._state_lock:
            if session_id in self._order_counts:
                self._order_counts[session_id]["filled"] += 1

    async def _on_order_rejected(self, data: Dict[str, Any]) -> None:
        """Handle order rejected event with thread safety"""
        session_id = data.get("session_id", "unknown")

        async with self._state_lock:
            if session_id in self._order_counts:
                self._order_counts[session_id]["rejected"] += 1

    async def _on_pnl_update(self, data: Dict[str, Any]) -> None:
        """Handle P&L update event with thread safety"""
        session_id = data.get("session_id", "unknown")
        unrealized_pnl = data.get("unrealized_pnl", 0.0)
        realized_pnl = data.get("realized_pnl", 0.0)

        async with self._state_lock:
            if session_id in self._pnl_tracking:
                self._pnl_tracking[session_id]["unrealized"] = unrealized_pnl
                self._pnl_tracking[session_id]["realized"] = realized_pnl
    
    def get_session_metrics(self, session_id: str) -> Optional[ExecutionMetrics]:
        """Get latest metrics for a session"""
        if session_id not in self._metrics_history:
            return None
        
        history = self._metrics_history[session_id]
        return history[-1] if history else None
    
    def get_metrics_history(self, session_id: str, limit: int = 100) -> List[ExecutionMetrics]:
        """Get metrics history for a session"""
        if session_id not in self._metrics_history:
            return []
        
        history = self._metrics_history[session_id]
        return list(history)[-limit:]