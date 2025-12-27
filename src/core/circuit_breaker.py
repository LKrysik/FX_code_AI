"""
Circuit Breaker and Retry Patterns Implementation

Provides resilient error handling with circuit breaker pattern and exponential backoff retry logic.
Prevents cascading failures and system overload during service degradation.
"""

import asyncio
import time
import threading
from typing import Any, Callable, Dict, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
import statistics

from src.core.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    expected_exception: tuple = (Exception,)  # Exception types to count as failures
    success_threshold: int = 3  # Successes needed to close circuit in half-open state
    timeout: float = 10.0  # Request timeout
    name: str = "default"


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker operation"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """Circuit breaker implementation with thread-safe operations"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._last_state_change = time.time()
        self._test_request_allowed = False

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (time.time() - self._last_state_change) >= self.config.recovery_timeout

    def _record_success(self):
        """Record successful operation"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.consecutive_successes += 1
            self.metrics.consecutive_failures = 0
            self.metrics.last_success_time = time.time()

            # Transition from half-open to closed on success threshold
            if (self.state == CircuitBreakerState.HALF_OPEN and
                self.metrics.consecutive_successes >= self.config.success_threshold):
                self._change_state(CircuitBreakerState.CLOSED)

    def _record_failure(self, exception: Exception):
        """Record failed operation"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.consecutive_failures += 1
            self.metrics.consecutive_successes = 0
            self.metrics.last_failure_time = time.time()

            # Open circuit if failure threshold exceeded
            if (self.state == CircuitBreakerState.CLOSED and
                self.metrics.consecutive_failures >= self.config.failure_threshold):
                self._change_state(CircuitBreakerState.OPEN)

            # Fail immediately in half-open state
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self._change_state(CircuitBreakerState.OPEN)

    def _change_state(self, new_state: CircuitBreakerState):
        """Change circuit breaker state"""
        with self._lock:
            if self.state != new_state:
                logger.info(f"Circuit breaker '{self.config.name}' state change: {self.state.value} -> {new_state.value}")
                self.state = new_state
                self._last_state_change = time.time()
                self.metrics.state_changes += 1

                # Reset consecutive counters on state change
                if new_state == CircuitBreakerState.HALF_OPEN:
                    self.metrics.consecutive_successes = 0
                    self.metrics.consecutive_failures = 0

    def _can_attempt_request(self) -> bool:
        """Check if request can be attempted"""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._change_state(CircuitBreakerState.HALF_OPEN)
                    return True
                return False
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return True
            return False

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if not self._can_attempt_request():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.config.name}' is OPEN")

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            self._record_success()
            return result

        except self.config.expected_exception as e:
            self._record_failure(e)
            raise
        except asyncio.TimeoutError as e:
            self._record_failure(e)
            raise CircuitBreakerTimeoutException(f"Request timeout after {self.config.timeout}s") from e

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker protection"""
        if not self._can_attempt_request():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.config.name}' is OPEN")

        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Check for timeout (approximate for sync calls)
            if execution_time > self.config.timeout:
                raise CircuitBreakerTimeoutException(f"Request timeout after {execution_time:.2f}s")

            self._record_success()
            return result

        except self.config.expected_exception as e:
            self._record_failure(e)
            raise
        except Exception as e:
            # For sync calls, treat all exceptions as failures if not in expected types
            if isinstance(e, self.config.expected_exception):
                self._record_failure(e)
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self._lock:
            success_rate = (self.metrics.successful_requests / max(self.metrics.total_requests, 1)) * 100

            return {
                'name': self.config.name,
                'state': self.state.value,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'recovery_timeout': self.config.recovery_timeout,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout
                },
                'metrics': {
                    'total_requests': self.metrics.total_requests,
                    'successful_requests': self.metrics.successful_requests,
                    'failed_requests': self.metrics.failed_requests,
                    'rejected_requests': self.metrics.rejected_requests,
                    'success_rate_percent': round(success_rate, 2),
                    'consecutive_failures': self.metrics.consecutive_failures,
                    'consecutive_successes': self.metrics.consecutive_successes,
                    'state_changes': self.metrics.state_changes,
                    'last_failure_time': self.metrics.last_failure_time,
                    'last_success_time': self.metrics.last_success_time,
                    'time_since_last_failure': time.time() - (self.metrics.last_failure_time or time.time()),
                    'time_since_last_success': time.time() - (self.metrics.last_success_time or time.time())
                }
            }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerTimeoutException(Exception):
    """Exception raised when request times out"""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0     # Maximum delay between retries
    backoff_factor: float = 2.0 # Exponential backoff multiplier
    jitter: bool = True         # Add random jitter to prevent thundering herd
    retry_on: tuple = (Exception,)  # Exception types to retry on
    name: str = "default"


class RetryHandler:
    """Retry handler with exponential backoff and jitter"""

    def __init__(self, config: RetryConfig):
        self.config = config
        self._attempts = 0

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using exponential backoff"""
        delay = min(
            self.config.initial_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )

        if self.config.jitter:
            # Add random jitter (±25% of delay)
            import random
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)  # Ensure non-negative delay

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except self.config.retry_on as e:
                last_exception = e
                self._attempts = attempt + 1

                if attempt < self.config.max_attempts - 1:  # Not the last attempt
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Retry attempt {attempt + 1}/{self.config.max_attempts} for '{self.config.name}' failed: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} retry attempts failed for '{self.config.name}': {e}")

        raise last_exception

    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except self.config.retry_on as e:
                last_exception = e
                self._attempts = attempt + 1

                if attempt < self.config.max_attempts - 1:  # Not the last attempt
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Retry attempt {attempt + 1}/{self.config.max_attempts} for '{self.config.name}' failed: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} retry attempts failed for '{self.config.name}': {e}")

        raise last_exception


class ResilientService:
    """Service that combines circuit breaker and retry patterns"""

    def __init__(self, name: str, circuit_config: Optional[CircuitBreakerConfig] = None,
                 retry_config: Optional[RetryConfig] = None):
        self.name = name
        self.circuit_breaker = CircuitBreaker(
            circuit_config or CircuitBreakerConfig(name=name)
        )
        self.retry_handler = RetryHandler(
            retry_config or RetryConfig(name=name)
        )

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with both circuit breaker and retry protection"""
        async def wrapped_call():
            return await self.retry_handler.execute_async(func, *args, **kwargs)

        return await self.circuit_breaker.call_async(wrapped_call)

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with both circuit breaker and retry protection"""
        def wrapped_call():
            return self.retry_handler.execute_sync(func, *args, **kwargs)

        return self.circuit_breaker.call_sync(wrapped_call)

    def get_status(self) -> Dict[str, Any]:
        """Get combined status of circuit breaker and retry handler"""
        return {
            'service_name': self.name,
            'circuit_breaker': self.circuit_breaker.get_metrics(),
            'retry_config': {
                'max_attempts': self.retry_handler.config.max_attempts,
                'backoff_factor': self.retry_handler.config.backoff_factor,
                'max_delay': self.retry_handler.config.max_delay
            }
        }


# Global service registry for managing resilient services
_service_registry: Dict[str, ResilientService] = {}
_registry_lock = threading.Lock()


def get_or_create_service(name: str, circuit_config: Optional[CircuitBreakerConfig] = None,
                         retry_config: Optional[RetryConfig] = None) -> ResilientService:
    """Get or create a resilient service instance"""
    with _registry_lock:
        if name not in _service_registry:
            _service_registry[name] = ResilientService(name, circuit_config, retry_config)
        return _service_registry[name]


def get_service_status(name: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific service"""
    with _registry_lock:
        service = _service_registry.get(name)
        return service.get_status() if service else None


def get_all_service_statuses() -> Dict[str, Dict[str, Any]]:
    """Get status of all registered services"""
    with _registry_lock:
        return {name: service.get_status() for name, service in _service_registry.items()}


# Decorators for easy integration
def resilient_service(name: str, circuit_config: Optional[CircuitBreakerConfig] = None,
                     retry_config: Optional[RetryConfig] = None):
    """Decorator to make a function resilient with circuit breaker and retry"""
    service = get_or_create_service(name, circuit_config, retry_config)

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await service.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return service.call_sync(func, *args, **kwargs)
            return sync_wrapper
    return decorator