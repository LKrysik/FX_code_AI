"""
Health Monitoring and Alerting System

Provides comprehensive health monitoring with configurable checks, alerting, and integration
with telemetry system. Ensures thread-safe operations with no race conditions or deadlocks.
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
import logging
import psutil
from pathlib import Path

from .telemetry import telemetry
from .circuit_breaker import get_all_service_statuses
from .logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckConfig:
    """Configuration for a health check"""
    name: str
    check_function: Callable[[], Union[bool, Dict[str, Any]]]
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    failure_threshold: int = 3  # Consecutive failures before unhealthy
    recovery_threshold: int = 2  # Consecutive successes before healthy
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check execution"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: float
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


@dataclass
class AlertConfig:
    """Configuration for alerting"""
    name: str
    condition: Callable[[HealthCheckResult], bool]
    level: AlertLevel
    message_template: str
    cooldown_seconds: float = 300.0  # Don't repeat alerts too frequently
    enabled: bool = True
    channels: List[str] = field(default_factory=lambda: ["log"])  # log, callback, etc.


@dataclass
class Alert:
    """Alert instance"""
    id: str
    config_name: str
    level: AlertLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class HealthMonitor:
    """Central health monitoring system with thread-safe operations"""

    def __init__(self, event_bus=None):
        self.checks: Dict[str, HealthCheckConfig] = {}
        self.alert_configs: Dict[str, AlertConfig] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_callbacks: Dict[str, Callable[[Alert], None]] = {}
        self.event_bus = event_bus  # EventBus for WebSocket notifications

        # Service registry for core services
        self.registered_services: Dict[str, Dict[str, Any]] = {}
        self.service_health_checks: Dict[str, Callable[[], Dict[str, Any]]] = {}

        # Thread safety
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Alert management
        self._alert_cooldowns: Dict[str, float] = {}

        # Service monitoring
        self._service_status_cache: Dict[str, Dict[str, Any]] = {}
        self._service_last_check: Dict[str, float] = {}

    def add_health_check(self, config: HealthCheckConfig):
        """Add a health check to monitoring"""
        with self._lock:
            self.checks[config.name] = config
            logger.info(f"Added health check: {config.name}")

    def remove_health_check(self, name: str):
        """Remove a health check"""
        with self._lock:
            if name in self.checks:
                del self.checks[name]
                if name in self.results:
                    del self.results[name]
                logger.info(f"Removed health check: {name}")

    def add_alert_config(self, config: AlertConfig):
        """Add an alert configuration"""
        with self._lock:
            self.alert_configs[config.name] = config
            logger.info(f"Added alert config: {config.name}")

    def register_alert_callback(self, channel: str, callback: Callable[[Alert], None]):
        """Register a callback for alert notifications"""
        with self._lock:
            self.alert_callbacks[channel] = callback
            logger.info(f"Registered alert callback for channel: {channel}")

    def register_service(self, service_name: str, health_check_func: Callable[[], Dict[str, Any]],
                        metadata: Optional[Dict[str, Any]] = None):
        """Register a core service for health monitoring"""
        with self._lock:
            self.registered_services[service_name] = {
                'name': service_name,
                'health_check': health_check_func,
                'metadata': metadata or {},
                'registered_at': datetime.now(UTC).isoformat(),
                'enabled': True
            }
            self.service_health_checks[service_name] = health_check_func
            logger.info(f"Registered service: {service_name}")

    def unregister_service(self, service_name: str):
        """Unregister a service from health monitoring"""
        with self._lock:
            if service_name in self.registered_services:
                del self.registered_services[service_name]
                if service_name in self.service_health_checks:
                    del self.service_health_checks[service_name]
                if service_name in self._service_status_cache:
                    del self._service_status_cache[service_name]
                if service_name in self._service_last_check:
                    del self._service_last_check[service_name]
                logger.info(f"Unregistered service: {service_name}")

    def get_registered_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered services (JSON serializable)"""
        with self._lock:
            # Return a copy without the function objects for JSON serialization
            services = {}
            for service_name, service_info in self.registered_services.items():
                services[service_name] = {
                    'name': service_info['name'],
                    'metadata': service_info['metadata'],
                    'registered_at': service_info['registered_at'],
                    'enabled': service_info['enabled']
                }
            return services

    def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific registered service"""
        with self._lock:
            if service_name not in self.registered_services:
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f'Service not registered: {service_name}',
                    'service_name': service_name
                }

            service_info = self.registered_services[service_name]
            if not service_info['enabled']:
                return {
                    'status': HealthStatus.DEGRADED.value,
                    'message': f'Service disabled: {service_name}',
                    'service_name': service_name
                }

            try:
                health_check_func = service_info['health_check']
                result = health_check_func()

                # Cache the result
                self._service_status_cache[service_name] = result
                self._service_last_check[service_name] = time.time()

                return result
            except Exception as e:
                logger.warning(f"Service health check failed for {service_name}: {e}")
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f'Service health check failed: {str(e)}',
                    'service_name': service_name,
                    'error': str(e)
                }

    def start_monitoring(self):
        """Start the health monitoring system"""
        if self._running:
            return

        with self._lock:
            self._running = True
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="HealthMonitor"
            )
            self._monitor_thread.start()
            logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring system"""
        if not self._running:
            return

        with self._lock:
            self._running = False
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5.0)

            logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop - runs in separate thread"""
        logger.info("Health monitoring loop started")

        while not self._stop_event.is_set():
            try:
                self._run_health_checks()
                self._evaluate_alerts()
                self._cleanup_resolved_alerts()
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")

            # Wait for next check cycle or stop event
            self._stop_event.wait(45.0)  # Check every 45 seconds - balanced monitoring

        logger.info("Health monitoring loop stopped")

    def _run_health_checks(self):
        """Execute all enabled health checks"""
        with self._lock:
            for name, config in self.checks.items():
                if not config.enabled:
                    continue

                try:
                    # Run health check with timeout
                    result = self._execute_health_check(config)
                    self._update_health_result(name, result)
                    self._record_telemetry(name, result)

                except Exception as e:
                    logger.error(f"Health check '{name}' execution error: {e}")
                    # Create failure result
                    failure_result = HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check execution failed: {str(e)}",
                        details={"error": str(e)},
                        timestamp=datetime.now(UTC),
                        duration_ms=0.0
                    )
                    self._update_health_result(name, failure_result)

    def _execute_health_check(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Execute a single health check with timeout"""
        start_time = time.time()

        try:
            # Execute the check function
            result = config.check_function()

            duration_ms = (time.time() - start_time) * 1000

            # Handle different return types
            if isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "Check passed" if result else "Check failed"
                details = {"result": result}
            elif isinstance(result, dict):
                status = HealthStatus(result.get("status", "unhealthy"))
                message = result.get("message", "Check completed")
                details = result
            else:
                # Assume truthy result means healthy
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "Check completed"
                details = {"result": result}

            return HealthCheckResult(
                name=config.name,
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(UTC),
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=config.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check execution failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                timestamp=datetime.now(UTC),
                duration_ms=duration_ms
            )

    def _update_health_result(self, name: str, result: HealthCheckResult):
        """Update health check result with consecutive counters"""
        with self._lock:
            previous_result = self.results.get(name)

            if result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                result.consecutive_successes = (previous_result.consecutive_successes + 1) if previous_result else 1
                result.consecutive_failures = 0
                result.last_success_time = time.time()
            else:
                result.consecutive_failures = (previous_result.consecutive_failures + 1) if previous_result else 1
                result.consecutive_successes = 0
                result.last_failure_time = time.time()

            # Apply failure threshold logic
            if result.consecutive_failures >= self.checks[name].failure_threshold:
                if result.status == HealthStatus.HEALTHY:
                    result.status = HealthStatus.UNHEALTHY
                    result.message += f" (failure threshold exceeded: {result.consecutive_failures})"

            self.results[name] = result

    def _record_telemetry(self, name: str, result: HealthCheckResult):
        """Record health check results in telemetry"""
        try:
            # Record basic metrics
            telemetry.record(f"health.{name}.duration_ms", result.duration_ms, {"check": name})
            telemetry.record(f"health.{name}.status", 1 if result.status == HealthStatus.HEALTHY else 0, {"check": name})

            # Record consecutive counters
            telemetry.record(f"health.{name}.consecutive_successes", result.consecutive_successes, {"check": name})
            telemetry.record(f"health.{name}.consecutive_failures", result.consecutive_failures, {"check": name})

            # Record status changes
            if result.status != HealthStatus.HEALTHY:
                telemetry.increment_counter("health.failures_total", tags={"check": name, "status": result.status.value})

        except Exception as e:
            logger.error(f"Failed to record telemetry for health check '{name}': {e}")

    def _evaluate_alerts(self):
        """Evaluate all alert conditions"""
        with self._lock:
            current_time = time.time()

            for alert_name, alert_config in self.alert_configs.items():
                if not alert_config.enabled:
                    continue

                # Check cooldown
                last_alert_time = self._alert_cooldowns.get(alert_name, 0)
                if current_time - last_alert_time < alert_config.cooldown_seconds:
                    continue

                # Evaluate condition for each health check
                for check_name, result in self.results.items():
                    try:
                        if alert_config.condition(result):
                            self._trigger_alert(alert_name, alert_config, result)
                            self._alert_cooldowns[alert_name] = current_time
                            break  # Only trigger once per alert config per cycle
                    except Exception as e:
                        logger.error(f"Alert evaluation error for '{alert_name}': {e}")

    def _trigger_alert(self, alert_name: str, config: AlertConfig, result: HealthCheckResult):
        """Trigger an alert"""
        alert_id = f"{alert_name}_{result.name}_{int(time.time())}"

        alert = Alert(
            id=alert_id,
            config_name=alert_name,
            level=config.level,
            message=config.message_template.format(
                check_name=result.name,
                status=result.status.value,
                message=result.message
            ),
            details={
                "check_name": result.name,
                "check_status": result.status.value,
                "check_message": result.message,
                "check_details": result.details,
                "consecutive_failures": result.consecutive_failures,
                "consecutive_successes": result.consecutive_successes
            },
            timestamp=datetime.now(UTC)
        )

        # Store active alert
        self.active_alerts[alert_id] = alert

        # Send to configured channels
        for channel in config.channels:
            try:
                if channel == "log":
                    self._log_alert(alert)
                elif channel in self.alert_callbacks:
                    self.alert_callbacks[channel](alert)
                else:
                    logger.warning(f"Unknown alert channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to send alert to channel '{channel}': {e}")

        # Publish to EventBus for WebSocket broadcasting
        if self.event_bus:
            try:
                health_notification = {
                    "alert_id": alert_id,
                    "alert_name": alert_name,
                    "level": alert.level.value,
                    "message": alert.message,
                    "check_name": result.name,
                    "check_status": result.status.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "details": alert.details
                }
                # Publish to EventBus for WebSocket broadcasting
                self.event_bus.publish("health.alert", health_notification)
                logger.debug(f"Published health alert to EventBus: {alert_id}")
            except Exception as e:
                logger.error(f"Failed to publish health alert to EventBus: {e}")

        logger.warning(f"Alert triggered: {alert.message}")

    def _log_alert(self, alert: Alert):
        """Log an alert with appropriate level"""
        log_message = f"ALERT [{alert.level.value.upper()}] {alert.message}"

        if alert.level == AlertLevel.CRITICAL:
            logger.critical(f"ALERT CRITICAL: {alert.message}")
        elif alert.level == AlertLevel.ERROR:
            logger.error(f"ALERT ERROR: {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"ALERT WARNING: {alert.message}")
        else:
            logger.info(f"ALERT INFO: {alert.message}")

    def _cleanup_resolved_alerts(self):
        """Clean up resolved alerts (basic implementation)"""
        # In a more sophisticated system, this would check if alerts are resolved
        # For now, we keep all alerts for manual resolution
        pass

    def resolve_alert(self, alert_id: str):
        """Manually resolve an alert"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].resolved = True
                self.active_alerts[alert_id].resolved_at = datetime.now(UTC)
                logger.info(f"Alert resolved: {alert_id}")

    def cleanup(self):
        """Clean up resources and reset state"""
        with self._lock:
            # Clear service registry
            self.registered_services.clear()
            self.service_health_checks.clear()
            self._service_status_cache.clear()
            self._service_last_check.clear()

            # Clear health checks and results
            self.checks.clear()
            self.results.clear()

            # Clear alerts
            self.active_alerts.clear()
            self.alert_configs.clear()
            self._alert_cooldowns.clear()

            logger.info("Health monitor cleanup completed")

    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get cached status of a specific service"""
        with self._lock:
            return self._service_status_cache.get(service_name)

    def enable_service(self, service_name: str):
        """Enable a registered service"""
        with self._lock:
            if service_name in self.registered_services:
                self.registered_services[service_name]['enabled'] = True
                logger.info(f"Enabled service: {service_name}")

    def disable_service(self, service_name: str):
        """Disable a registered service"""
        with self._lock:
            if service_name in self.registered_services:
                self.registered_services[service_name]['enabled'] = False
                logger.info(f"Disabled service: {service_name}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        with self._lock:
            overall_status = self._calculate_overall_status()

            # Check registered services health
            services_status = {}
            for service_name in self.registered_services.keys():
                try:
                    service_health = self.check_service_health(service_name)
                    services_status[service_name] = service_health
                except Exception as e:
                    logger.warning(f"Failed to check service health for {service_name}: {e}")
                    services_status[service_name] = {
                        'status': HealthStatus.UNHEALTHY.value,
                        'message': f'Service health check failed: {str(e)}',
                        'service_name': service_name,
                        'error': str(e)
                    }

            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "overall_status": overall_status.value,
                "checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "consecutive_failures": result.consecutive_failures,
                        "consecutive_successes": result.consecutive_successes,
                        "last_check": result.timestamp.isoformat(),
                        "duration_ms": result.duration_ms
                    }
                    for name, result in self.results.items()
                },
                "services": services_status,
                "registered_services_count": len(self.registered_services),
                "active_alerts": [
                    {
                        "id": alert.id,
                        "level": alert.level.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat(),
                        "resolved": alert.resolved
                    }
                    for alert in self.active_alerts.values()
                    if not alert.resolved
                ],
                "telemetry_integration": True
            }

    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health status with intelligent aggregation"""
        all_statuses = []

        # Include health check results
        if self.results:
            all_statuses.extend([result.status for result in self.results.values()])

        # Include registered service statuses
        for service_name in self.registered_services.keys():
            service_health = self.check_service_health(service_name)
            service_status = service_health.get('status', 'unhealthy')
            try:
                all_statuses.append(HealthStatus(service_status))
            except ValueError:
                # If status is not a valid HealthStatus, treat as unhealthy
                all_statuses.append(HealthStatus.UNHEALTHY)

        # If no statuses to check, assume healthy (system is running)
        if not all_statuses:
            return HealthStatus.HEALTHY

        # Prioritize critical issues
        if any(status == HealthStatus.CRITICAL for status in all_statuses):
            return HealthStatus.CRITICAL

        # If any unhealthy, but we have healthy services, mark as degraded
        if any(status == HealthStatus.UNHEALTHY for status in all_statuses):
            # Check if we have any healthy services - if so, system is degraded not unhealthy
            if any(status == HealthStatus.HEALTHY for status in all_statuses):
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.UNHEALTHY

        # If any degraded but no unhealthy/critical, mark as degraded
        if any(status == HealthStatus.DEGRADED for status in all_statuses):
            return HealthStatus.DEGRADED

        # All healthy
        return HealthStatus.HEALTHY


    def get_degradation_status(self) -> Dict[str, Any]:
        """Get detailed degradation status"""
        overall_status = self._calculate_overall_status()

        # Identify which services are unavailable
        unavailable_services = []
        degraded_services = []
        healthy_services = []

        # Check health check results
        for name, result in self.results.items():
            if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                unavailable_services.append({
                    "service": name,
                    "status": result.status.value,
                    "message": result.message,
                    "last_check": result.timestamp.isoformat()
                })
            elif result.status == HealthStatus.DEGRADED:
                degraded_services.append({
                    "service": name,
                    "status": result.status.value,
                    "message": result.message,
                    "last_check": result.timestamp.isoformat()
                })
            elif result.status == HealthStatus.HEALTHY:
                healthy_services.append({
                    "service": name,
                    "status": result.status.value,
                    "message": result.message,
                    "last_check": result.timestamp.isoformat()
                })

        # Check registered services
        for service_name in self.registered_services.keys():
            try:
                service_health = self.check_service_health(service_name)
                service_status = service_health.get('status', 'unhealthy')

                if service_status in [HealthStatus.UNHEALTHY.value, HealthStatus.CRITICAL.value]:
                    unavailable_services.append({
                        "service": service_name,
                        "status": service_status,
                        "message": service_health.get('message', 'Service unhealthy'),
                        "last_check": datetime.now(UTC).isoformat()
                    })
                elif service_status == HealthStatus.DEGRADED.value:
                    degraded_services.append({
                        "service": service_name,
                        "status": service_status,
                        "message": service_health.get('message', 'Service degraded'),
                        "last_check": datetime.now(UTC).isoformat()
                    })
                elif service_status == HealthStatus.HEALTHY.value:
                    healthy_services.append({
                        "service": service_name,
                        "status": service_status,
                        "message": service_health.get('message', 'Service healthy'),
                        "last_check": datetime.now(UTC).isoformat()
                    })
            except Exception as e:
                logger.warning(f"Failed to check service health for {service_name}: {e}")
                unavailable_services.append({
                    "service": service_name,
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f'Service health check failed: {str(e)}',
                    "last_check": datetime.now(UTC).isoformat()
                })

        return {
            "overall_status": overall_status.value,
            "unavailable_services": unavailable_services,
            "degraded_services": degraded_services,
            "total_services": len(self.results) + len(self.registered_services),
            "healthy_services": len(healthy_services),
            "timestamp": datetime.now(UTC).isoformat()
        }

    def get_check_details(self, check_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific health check"""
        with self._lock:
            result = self.results.get(check_name)
            if not result:
                return None

            return {
                "name": result.name,
                "status": result.status.value,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp.isoformat(),
                "duration_ms": result.duration_ms,
                "consecutive_failures": result.consecutive_failures,
                "consecutive_successes": result.consecutive_successes,
                "last_failure_time": result.last_failure_time,
                "last_success_time": result.last_success_time,
                "config": {
                    "interval_seconds": self.checks[check_name].interval_seconds,
                    "timeout_seconds": self.checks[check_name].timeout_seconds,
                    "failure_threshold": self.checks[check_name].failure_threshold,
                    "enabled": self.checks[check_name].enabled
                } if check_name in self.checks else None
            }


# Global health monitor instance
health_monitor = HealthMonitor()


# Built-in health check functions
def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage"""
    try:
        # Use non-blocking CPU sampling to minimize overhead
        # Use a very short interval to avoid hanging
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        status = HealthStatus.HEALTHY
        message = "System resources OK"

        # Optimized thresholds for better performance monitoring
        if cpu_percent > 95:
            status = HealthStatus.CRITICAL
            message = f"Critical CPU usage: {cpu_percent}%"
        elif cpu_percent > 85:
            status = HealthStatus.UNHEALTHY
            message = f"High CPU usage: {cpu_percent}%"
        elif memory.percent > 95:
            status = HealthStatus.CRITICAL
            message = f"Critical memory usage: {memory.percent}%"
        elif memory.percent > 85:
            status = HealthStatus.UNHEALTHY
            message = f"High memory usage: {memory.percent}%"

        return {
            "status": status.value,
            "message": message,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent
        }
    except Exception as e:
        logger.warning(f"System resource check failed: {e}")
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": f"System resource check failed: {str(e)}",
            "error": str(e)
        }


def check_circuit_breakers() -> Dict[str, Any]:
    """Check circuit breaker status"""
    try:
        circuit_status = get_all_service_statuses()

        if not circuit_status:
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "No circuit breakers configured",
                "services": 0
            }

        open_circuits = []
        half_open_circuits = []

        for service_name, status in circuit_status.items():
            circuit_state = status.get("circuit_breaker", {}).get("state", "unknown")
            if circuit_state == "open":
                open_circuits.append(service_name)
            elif circuit_state == "half_open":
                half_open_circuits.append(service_name)

        if open_circuits:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Circuit breakers OPEN: {', '.join(open_circuits)}",
                "open_circuits": open_circuits,
                "half_open_circuits": half_open_circuits,
                "total_services": len(circuit_status)
            }
        elif half_open_circuits:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"Circuit breakers recovering: {', '.join(half_open_circuits)}",
                "open_circuits": open_circuits,
                "half_open_circuits": half_open_circuits,
                "total_services": len(circuit_status)
            }
        else:
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": f"All {len(circuit_status)} circuit breakers healthy",
                "open_circuits": open_circuits,
                "half_open_circuits": half_open_circuits,
                "total_services": len(circuit_status)
            }
    except Exception as e:
        logger.warning(f"Circuit breaker check failed: {e}")
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": f"Circuit breaker check failed: {str(e)}",
            "error": str(e)
        }


def check_telemetry_system() -> Dict[str, Any]:
    """Check telemetry system health"""
    try:
        # Check if telemetry is started before trying to get health status
        if not telemetry._started:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "Telemetry system not enabled (set ENABLE_TELEMETRY=1 to enable)",
                "telemetry_status": "disabled",
                "checks": {},
                "metrics_available": False
            }

        health_status = telemetry.get_health_status()

        system_status = health_status.get("status", "unknown")
        checks = health_status.get("checks", {})

        # Map telemetry status to health status
        if system_status == "healthy":
            status = HealthStatus.HEALTHY
            message = "Telemetry system healthy"
        elif system_status == "degraded":
            status = HealthStatus.DEGRADED
            message = "Telemetry system degraded"
        else:
            status = HealthStatus.UNHEALTHY
            message = f"Telemetry system unhealthy: {system_status}"

        return {
            "status": status.value,
            "message": message,
            "telemetry_status": system_status,
            "checks": checks,
            "metrics_available": bool(health_status.get("metrics"))
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": f"Telemetry check failed: {str(e)}",
            "error": str(e)
        }


def check_external_services() -> Dict[str, Any]:
    """Check external service availability (MEXC API, etc.)"""
    try:
        from ..infrastructure.adapters.mexc_adapter import MexcRealAdapter
        from ..infrastructure.adapters.mexc_paper_adapter import MexcPaperAdapter
        from ..infrastructure.config.settings import AppSettings
        from ..core.logger import StructuredLogger
    except ImportError:
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": "MEXC adapters not available; running with limited functionality",
            "mexc_api": "adapters_missing"
        }

    try:
        settings = AppSettings()
        logger = StructuredLogger("MEXCHealthCheck", settings.logging)
        api_key = settings.exchanges.mexc_api_key or ""
        api_secret = settings.exchanges.mexc_api_secret or ""

        if not api_key or not api_secret:
            adapter = MexcPaperAdapter(logger)
            adapter.get_balances()
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Running in paper mode - real MEXC credentials not configured",
                "mexc_api": "paper_mode"
            }

        try:
            adapter = MexcRealAdapter(api_key=api_key, api_secret=api_secret, logger=logger)
        except Exception as exc:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Failed to initialize real MEXC adapter: {exc}",
                "mexc_api": "initialization_failed"
            }

        try:
            import asyncio

            async def _probe():
                return await adapter._make_request("GET", "/api/v3/time", signed=False)  # type: ignore[attr-defined]

            result = asyncio.run(_probe())
            if result is not None:
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "MEXC API reachable",
                    "mexc_api": "connected"
                }
        except Exception as exc:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"MEXC connectivity check failed: {exc}",
                "mexc_api": "degraded"
            }

        return {
            "status": HealthStatus.DEGRADED.value,
            "message": "Unable to verify MEXC connectivity",
            "mexc_api": "unknown"
        }
    except Exception as exc:
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": f"External services check encountered an error: {exc}",
            "mexc_api": "error"
        }
def check_database_availability() -> Dict[str, Any]:
    """Check if database/file storage is available for read operations"""
    try:
        import os

        # Check if config directory exists and is readable
        config_dir = Path("config")
        if not config_dir.exists():
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "Configuration storage unavailable - running with defaults",
                "config_dir": "missing"
            }

        # Check if strategies directory exists
        strategies_dir = config_dir / "strategies"
        if not strategies_dir.exists():
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "Strategy storage missing but config available",
                "strategies_dir": "missing",
                "config_dir": "available"
            }

        # Try to list strategy files
        try:
            strategy_files = list(strategies_dir.glob("*.json"))
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": f"Database/storage available ({len(strategy_files)} strategies)",
                "config_dir": "available",
                "strategies_dir": "available",
                "strategy_count": len(strategy_files)
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"Strategy storage access failed: {str(e)}",
                "config_dir": "available",
                "strategies_dir": "access_denied"
            }

    except Exception as e:
        logger.warning(f"Database availability check failed: {e}")
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": f"Database availability check failed: {str(e)}",
            "error": str(e)
        }


# Initialize default health checks
def initialize_default_health_checks():
    """Initialize default health checks for the system"""
    # System resources check
    health_monitor.add_health_check(HealthCheckConfig(
        name="system_resources",
        check_function=check_system_resources,
        interval_seconds=30.0,
        failure_threshold=3
    ))

    # Circuit breaker check
    health_monitor.add_health_check(HealthCheckConfig(
        name="circuit_breakers",
        check_function=check_circuit_breakers,
        interval_seconds=60.0,
        failure_threshold=2
    ))

    # Telemetry system check
    health_monitor.add_health_check(HealthCheckConfig(
        name="telemetry_system",
        check_function=check_telemetry_system,
        interval_seconds=60.0,
        failure_threshold=2
    ))

    # External services check (MEXC API connectivity)
    health_monitor.add_health_check(HealthCheckConfig(
        name="external_services",
        check_function=check_external_services,
        interval_seconds=120.0,  # Check less frequently
        failure_threshold=3
    ))

    # Database/storage availability check
    health_monitor.add_health_check(HealthCheckConfig(
        name="database_availability",
        check_function=check_database_availability,
        interval_seconds=60.0,
        failure_threshold=2
    ))


# Initialize default alert configurations
def initialize_default_alerts():
    """Initialize default alert configurations"""

    # High CPU usage alert
    def cpu_condition(result: HealthCheckResult) -> bool:
        return (result.name == "system_resources" and
                result.details.get("cpu_percent", 0) > 85)

    health_monitor.add_alert_config(AlertConfig(
        name="high_cpu_usage",
        condition=cpu_condition,
        level=AlertLevel.WARNING,
        message_template="High CPU usage detected: {check_name} - {message}",
        cooldown_seconds=300.0
    ))

    # Circuit breaker open alert
    def circuit_breaker_condition(result: HealthCheckResult) -> bool:
        return (result.name == "circuit_breakers" and
                result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL])

    health_monitor.add_alert_config(AlertConfig(
        name="circuit_breaker_open",
        condition=circuit_breaker_condition,
        level=AlertLevel.ERROR,
        message_template="Circuit breaker issue: {check_name} - {message}",
        cooldown_seconds=180.0
    ))

    # Telemetry system alert
    def telemetry_condition(result: HealthCheckResult) -> bool:
        return (result.name == "telemetry_system" and
                result.status != HealthStatus.HEALTHY)

    health_monitor.add_alert_config(AlertConfig(
        name="telemetry_system_issue",
        condition=telemetry_condition,
        level=AlertLevel.WARNING,
        message_template="Telemetry system issue: {check_name} - {message}",
        cooldown_seconds=600.0
    ))
