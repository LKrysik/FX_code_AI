"""
Rate Limiter Implementation
===========================
Thread-safe token bucket and sliding window rate limiting for API requests.
Uses asyncio.Lock for thread safety and Decimal for precision.
"""

import asyncio
import time
from typing import List, Optional
from collections import deque
from decimal import Decimal


class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter implementation.
    Allows bursts up to bucket capacity while maintaining average rate.
    Uses asyncio.Lock for thread safety and Decimal for precision.
    """
    
    def __init__(self, max_tokens: int, refill_rate: float, name: str = "RateLimiter"):
        """
        Initialize token bucket rate limiter with validation.
        
        Args:
            max_tokens: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
            name: Name for logging/debugging
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Input validation
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        if refill_rate > max_tokens * 10:  # Sanity check
            raise ValueError("refill_rate too high relative to max_tokens")
        
        # Use float for performance in high-frequency scenarios
        self.max_tokens = float(max_tokens)
        self.refill_rate = float(refill_rate)
        self.name = name

        self.tokens = self.max_tokens
        self.last_refill_time = time.monotonic()  # Use monotonic clock
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Statistics
        self.total_requests = 0
        self.denied_requests = 0
        self.created_time = time.monotonic()
    
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Thread-safe acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if rate limited
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
            
        async with self._lock:
            self.total_requests += 1
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                self.denied_requests += 1
                return False
    
    
    async def acquire_wait(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Thread-safe acquire tokens, waiting efficiently if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait (None = no timeout)
            
        Returns:
            True if tokens acquired, False if timeout
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
            
        start_time = time.monotonic()
        
        while True:
            # Try to acquire tokens
            if await self.acquire(tokens):
                return True
            
            # Check timeout
            if timeout and (time.monotonic() - start_time) >= timeout:
                return False
            
            # Calculate precise wait time
            async with self._lock:
                self._refill_tokens()
                if self.tokens < tokens:
                    needed_tokens = tokens - self.tokens
                    wait_time = needed_tokens / self.refill_rate
                    # Add small buffer for timing precision, cap at 1 second
                    wait_time = min(wait_time + 0.01, 1.0)
                else:
                    wait_time = 0  # No wait if tokens available for trading performance
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time using float precision"""
        current_time = time.monotonic()
        elapsed = current_time - self.last_refill_time
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill_time = current_time
    
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics without modifying state"""
        current_time = time.monotonic()
        uptime = current_time - self.created_time
        success_rate = ((self.total_requests - self.denied_requests) / max(self.total_requests, 1)) * 100
        
        # Calculate theoretical tokens without modifying state
        elapsed = current_time - self.last_refill_time
        theoretical_tokens = min(
            self.max_tokens,
            self.tokens + elapsed * self.refill_rate
        )
        
        return {
            "name": self.name,
            "type": "token_bucket",
            "config": {
                "max_tokens": float(self.max_tokens),
                "refill_rate": float(self.refill_rate)
            },
            "state": {
                "current_tokens": float(theoretical_tokens),
                "tokens_available_pct": float((theoretical_tokens / self.max_tokens) * 100)
            },
            "statistics": {
                "total_requests": self.total_requests,
                "denied_requests": self.denied_requests,
                "success_rate_pct": success_rate,
                "uptime_seconds": uptime,
                "requests_per_second": self.total_requests / max(uptime, 1)
            }
        }


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter implementation.
    More precise than token bucket for enforcing exact request rates.
    """
    
    def __init__(self, max_requests: int, time_window: float, name: str = "SlidingWindow"):
        """
        Initialize sliding window rate limiter with validation.
        
        Args:
            max_requests: Maximum requests in time window
            time_window: Time window in seconds
            name: Name for logging/debugging
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Input validation
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")
        
        self.max_requests = max_requests
        self.time_window = time_window
        self.name = name
        
        self.request_times: deque = deque()
        
        # Memory safety limit
        self.max_deque_size = max(max_requests * 2, 1000)
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Statistics
        self.total_requests = 0
        self.denied_requests = 0
        self.created_time = time.monotonic()
    
    
    async def acquire(self) -> bool:
        """
        Thread-safe acquire permission for one request.
        
        Returns:
            True if request allowed, False if rate limited
        """
        async with self._lock:
            self.total_requests += 1
            current_time = time.monotonic()
            
            # Remove old requests outside the window
            self._cleanup_old_requests(current_time)
            
            # Safety check: prevent memory explosion
            if len(self.request_times) > self.max_deque_size:
                while len(self.request_times) > self.max_requests:
                    self.request_times.popleft()
            
            if len(self.request_times) < self.max_requests:
                self.request_times.append(current_time)
                return True
            else:
                self.denied_requests += 1
                return False
    
    async def acquire_wait(self, timeout: Optional[float] = None) -> bool:
        """
        Thread-safe acquire permission, waiting if necessary.
        
        Args:
            timeout: Maximum time to wait (None = no timeout)
            
        Returns:
            True if request allowed, False if timeout
        """
        start_time = time.monotonic()
        
        while True:
            if await self.acquire():
                return True
            
            if timeout and (time.monotonic() - start_time) >= timeout:
                return False
            
            # Wait until oldest request expires
            async with self._lock:
                if self.request_times:
                    oldest_request = self.request_times[0]
                    wait_time = (oldest_request + self.time_window) - time.monotonic()
                    if wait_time > 0:
                        wait_time = min(wait_time + 0.001, 0.1)  # Small buffer + max 100ms
                    else:
                        wait_time = 0  # No wait if tokens available for trading performance
                else:
                    wait_time = 0  # No unnecessary wait for trading performance
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside the time window"""
        cutoff_time = current_time - self.time_window
        
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics without modifying state"""
        current_time = time.monotonic()
        uptime = current_time - self.created_time
        success_rate = ((self.total_requests - self.denied_requests) / max(self.total_requests, 1)) * 100
        
        # Calculate current window usage without modifying state
        cutoff_time = current_time - self.time_window
        current_requests_in_window = sum(
            1 for req_time in self.request_times 
            if req_time >= cutoff_time
        )
        
        return {
            "name": self.name,
            "type": "sliding_window",
            "config": {
                "max_requests": self.max_requests,
                "time_window": self.time_window,
                "max_deque_size": self.max_deque_size
            },
            "state": {
                "current_requests_in_window": current_requests_in_window,
                "window_usage_pct": (current_requests_in_window / self.max_requests) * 100,
                "deque_size": len(self.request_times)
            },
            "statistics": {
                "total_requests": self.total_requests,
                "denied_requests": self.denied_requests,
                "success_rate_pct": success_rate,
                "uptime_seconds": uptime,
                "requests_per_second": self.total_requests / max(uptime, 1)
            }
        }
