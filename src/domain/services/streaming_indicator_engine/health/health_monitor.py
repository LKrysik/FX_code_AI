"""
Health Monitor - Extracted from StreamingIndicatorEngine
=========================================================
Health tracking and circuit breaker pattern for calculation protection.

Features:
- Circuit breaker (CLOSED → OPEN → HALF_OPEN states)
- Calculation timeout protection
- Error rate tracking
- Performance monitoring
- Health status reporting
"""

import time
import asyncio
from typing import Dict, Any, Optional
from collections import deque
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Too many failures, block requests
    HALF_OPEN = "HALF_OPEN"  # Testing if system recovered


class HealthMonitor:
    """
    Monitors system health and implements circuit breaker pattern.

    Extracted from StreamingIndicatorEngine to follow Single Responsibility Principle.
    Protects against cascading failures in calculation pipeline.
    """

    def __init__(self, logger):
        """
        Initialize health monitor.

        Args:
            logger: StructuredLogger instance
        """
        self.logger = logger

        # Circuit breaker configuration
        self._circuit_breaker_config = {
            "failure_threshold": 10,  # Open circuit after 10 failures
            "success_threshold": 3,  # Close circuit after 3 successes in HALF_OPEN
            "timeout_seconds": 5.0,  # Calculation timeout
            "recovery_timeout": 60.0  # Wait 60s before trying HALF_OPEN
        }

        # Circuit breaker state
        self._circuit_breaker_state = {
            "state": "CLOSED",
            "failure_count": 0,
            "success_count": 0,
            "last_failure_time": 0.0,
            "next_attempt_time": 0.0
        }

        # Health monitoring
        self._health_monitoring = {
            "health_status": "UNKNOWN",
            "last_health_check": time.time(),
            "calculation_times": deque(maxlen=1000),
            "error_counts": {},
            "total_calculations": 0,
            "total_errors": 0
        }

    def is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open (blocking requests).

        Returns:
            True if circuit is OPEN, False otherwise
        """
        state = self._circuit_breaker_state["state"]

        if state == "OPEN":
            current_time = time.time()
            next_attempt = self._circuit_breaker_state["next_attempt_time"]

            # Check if recovery timeout elapsed
            if current_time >= next_attempt:
                # Transition to HALF_OPEN
                self._circuit_breaker_state["state"] = "HALF_OPEN"
                self._circuit_breaker_state["success_count"] = 0
                self.logger.info("health_monitor.circuit_half_open", {
                    "recovery_timeout": self._circuit_breaker_config["recovery_timeout"]
                })
                return False

            return True  # Still OPEN

        return False  # CLOSED or HALF_OPEN

    def record_success(self) -> None:
        """Record successful calculation."""
        state = self._circuit_breaker_state

        if state["state"] == "HALF_OPEN":
            state["success_count"] += 1

            # Check if enough successes to close circuit
            if state["success_count"] >= self._circuit_breaker_config["success_threshold"]:
                state["state"] = "CLOSED"
                state["failure_count"] = 0
                state["success_count"] = 0
                self.logger.info("health_monitor.circuit_closed", {
                    "success_threshold": self._circuit_breaker_config["success_threshold"]
                })

        elif state["state"] == "CLOSED":
            # Reset failure count on success
            state["failure_count"] = max(0, state["failure_count"] - 1)

        # Update health metrics
        self._health_monitoring["total_calculations"] += 1

    def record_failure(self, error: Exception) -> None:
        """
        Record calculation failure.

        Args:
            error: Exception that occurred
        """
        current_time = time.time()
        state = self._circuit_breaker_state
        config = self._circuit_breaker_config

        # Update failure tracking
        state["failure_count"] += 1
        state["last_failure_time"] = current_time

        # Track error types
        error_type = type(error).__name__
        self._health_monitoring["error_counts"][error_type] = \
            self._health_monitoring["error_counts"].get(error_type, 0) + 1
        self._health_monitoring["total_errors"] += 1

        # Circuit breaker logic
        if state["state"] == "HALF_OPEN":
            # Any failure in HALF_OPEN goes back to OPEN
            state["state"] = "OPEN"
            state["next_attempt_time"] = current_time + config["recovery_timeout"]
            self.logger.warning("health_monitor.circuit_reopened", {
                "error_type": error_type,
                "failure_count": state["failure_count"]
            })

        elif state["failure_count"] >= config["failure_threshold"] and state["state"] == "CLOSED":
            # Open the circuit
            state["state"] = "OPEN"
            state["next_attempt_time"] = current_time + config["recovery_timeout"]
            self.logger.warning("health_monitor.circuit_opened", {
                "failure_threshold": config["failure_threshold"],
                "failure_count": state["failure_count"],
                "error_type": error_type
            })

    async def execute_with_protection(self, coro, context: str) -> Optional[Any]:
        """
        Execute coroutine with circuit breaker and timeout protection.

        Args:
            coro: Coroutine to execute
            context: Context string for logging

        Returns:
            Result if successful, None if failed or circuit open
        """
        # Check circuit breaker
        if self.is_circuit_open():
            self.logger.debug("health_monitor.circuit_open_blocking", {
                "context": context,
                "state": self._circuit_breaker_state["state"]
            })
            return None

        # Execute with timeout
        try:
            start_time = time.time()
            timeout = self._circuit_breaker_config["timeout_seconds"]

            result = await asyncio.wait_for(coro, timeout=timeout)

            # Record success
            calculation_time = time.time() - start_time
            self._health_monitoring["calculation_times"].append(calculation_time)
            self.record_success()

            return result

        except asyncio.TimeoutError:
            error = TimeoutError(f"Timeout after {timeout}s")
            self.record_failure(error)
            self.logger.warning("health_monitor.timeout", {
                "context": context,
                "timeout_seconds": timeout
            })
            return None

        except Exception as e:
            self.record_failure(e)
            self.logger.error("health_monitor.execution_error", {
                "context": context,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    def update_health_status(self) -> None:
        """Update overall health status based on metrics."""
        current_time = time.time()

        # Only update periodically
        if current_time - self._health_monitoring["last_health_check"] < 60:
            return  # Check every minute

        self._health_monitoring["last_health_check"] = current_time

        # Calculate health metrics
        calculation_times = list(self._health_monitoring["calculation_times"])
        total_calcs = self._health_monitoring["total_calculations"]
        total_errors = self._health_monitoring["total_errors"]

        if not calculation_times:
            self._health_monitoring["health_status"] = "UNKNOWN"
            return

        # Calculate averages
        avg_calc_time = sum(calculation_times) / len(calculation_times)
        error_rate = total_errors / max(1, total_calcs)

        # Determine health status
        if avg_calc_time > 1.0 or error_rate > 0.1:  # >1s avg or >10% errors
            self._health_monitoring["health_status"] = "UNHEALTHY"
        elif avg_calc_time > 0.5 or error_rate > 0.05:  # >500ms avg or >5% errors
            self._health_monitoring["health_status"] = "DEGRADED"
        else:
            self._health_monitoring["health_status"] = "HEALTHY"

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.

        Returns:
            Dictionary with health metrics
        """
        self.update_health_status()

        # Calculate performance metrics
        calculation_times = list(self._health_monitoring["calculation_times"])
        avg_calc_time_ms = 0.0
        if calculation_times:
            avg_calc_time_ms = (sum(calculation_times) / len(calculation_times)) * 1000

        total_calcs = self._health_monitoring["total_calculations"]
        total_errors = self._health_monitoring["total_errors"]
        error_rate = (total_errors / max(1, total_calcs)) * 100

        return {
            "overall_status": self._health_monitoring["health_status"],
            "circuit_breaker": {
                "state": self._circuit_breaker_state["state"],
                "failure_count": self._circuit_breaker_state["failure_count"],
                "success_count": self._circuit_breaker_state["success_count"]
            },
            "performance": {
                "avg_calculation_time_ms": avg_calc_time_ms,
                "total_calculations": total_calcs,
                "total_errors": total_errors,
                "error_rate_pct": error_rate,
                "error_counts": self._health_monitoring["error_counts"].copy()
            }
        }

    def get_circuit_state(self) -> str:
        """
        Get current circuit breaker state.

        Returns:
            Circuit state string (CLOSED, OPEN, HALF_OPEN)
        """
        return self._circuit_breaker_state["state"]

    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._circuit_breaker_state = {
            "state": "CLOSED",
            "failure_count": 0,
            "success_count": 0,
            "last_failure_time": 0.0,
            "next_attempt_time": 0.0
        }
        self.logger.info("health_monitor.circuit_reset")
