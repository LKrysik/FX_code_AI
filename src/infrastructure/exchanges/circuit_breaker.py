"""
Circuit Breaker Pattern Implementation
=====================================
Provides protection against cascading failures in external service calls.
"""

import time
from enum import Enum
from typing import Optional, Callable, Any
import asyncio


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failures detected, circuit open
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service failing, calls fail fast without trying
    - HALF_OPEN: Testing recovery, limited calls allowed
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 3,
        name: str = "CircuitBreaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting recovery (seconds)
            success_threshold: Number of successes needed to close circuit from half-open
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name
        
        # State tracking
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.circuit_open_count = 0
    
    def get_state(self) -> str:
        """Get current circuit breaker state as string"""
        return self.state.value
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Original exception: If function fails
        """
        self.total_calls += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {time.time() - self.last_failure_time:.1f}s ago"
                )
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.timeout
    
    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
    
    def _on_success(self) -> None:
        """Handle successful function execution"""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        else:
            # Reset failure count on success in CLOSED state
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed function execution"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (normal operation)"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state (circuit tripped)"""
        self.state = CircuitState.OPEN
        self.circuit_open_count += 1
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def force_open(self) -> None:
        """Manually open circuit breaker"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        self.circuit_open_count += 1
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        failure_rate = (self.total_failures / max(self.total_calls, 1)) * 100
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
            "success_threshold": self.success_threshold,
            "current_failures": self.failure_count,
            "current_successes": self.success_count,
            "last_failure_time": self.last_failure_time,
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time else None,
            "statistics": {
                "total_calls": self.total_calls,
                "total_failures": self.total_failures,
                "total_successes": self.total_successes,
                "failure_rate_pct": failure_rate,
                "circuit_open_count": self.circuit_open_count
            }
        }
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is in CLOSED state"""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is in OPEN state"""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is in HALF_OPEN state"""
        return self.state == CircuitState.HALF_OPEN
    
    def get_memory_stats(self) -> dict:
        """
        ✅ MANDATORY PATTERN: Memory monitoring for production readiness
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "circuit_open_count": self.circuit_open_count,
            "has_last_failure_time": self.last_failure_time is not None
        }
    
    async def health_check(self) -> dict:
        """
        ✅ MANDATORY PATTERN: Health check with memory statistics
        """
        memory_stats = self.get_memory_stats()
        
        alerts = []
        if self.state == CircuitState.OPEN:
            alerts.append(f"Circuit breaker '{self.name}' is OPEN")
        
        if self.total_calls > 0:
            failure_rate = (self.total_failures / self.total_calls) * 100
            if failure_rate > 50:
                alerts.append(f"High failure rate: {failure_rate:.1f}%")
        
        return {
            "healthy": self.state == CircuitState.CLOSED and len(alerts) == 0,
            "circuit_breaker_name": self.name,
            "memory_stats": memory_stats,
            "alerts": alerts
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
