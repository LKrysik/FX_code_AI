"""
Position Lock Manager - Race Condition Prevention
=================================================
Provides distributed locking for position operations to prevent:
- Double-close bugs
- Incorrect P&L calculations
- Orphaned orders

SEC-0-1: Position Operation Locking
"""

import asyncio
import time
from typing import Dict, Optional
from contextlib import asynccontextmanager

from src.core.logger import get_logger
from src.core.exceptions import PositionAlreadyClosingError, PositionLockTimeoutError

logger = get_logger("position_lock_manager")


class PositionLockManager:
    """
    Manages locks for position operations.

    Ensures that only one close/modify operation can execute on a position
    at any given time. Uses asyncio.Lock for in-memory locking (single instance).

    Thread-safe and timeout-protected to handle crashes gracefully.

    Usage:
        lock_manager = PositionLockManager()

        async with lock_manager.acquire_lock("pos_123"):
            # Only one request can be here at a time for pos_123
            await close_position("pos_123")
    """

    # Singleton instance
    _instance: Optional["PositionLockManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize the lock manager.

        Args:
            default_timeout: Default lock acquisition timeout in seconds.
                            Prevents deadlocks if a lock holder crashes.
        """
        if self._initialized:
            return

        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_times: Dict[str, float] = {}
        self._lock_holders: Dict[str, str] = {}  # position_id -> operation description
        self._default_timeout = default_timeout
        self._meta_lock = asyncio.Lock()  # Protects _locks dict access
        self._initialized = True

        logger.info("position_lock_manager.initialized", {
            "default_timeout": default_timeout
        })

    @asynccontextmanager
    async def acquire_lock(
        self,
        position_id: str,
        operation: str = "close",
        timeout: Optional[float] = None
    ):
        """
        Context manager for acquiring a position lock.

        Args:
            position_id: Unique position identifier
            operation: Description of the operation (for logging)
            timeout: Optional custom timeout (uses default if not provided)

        Raises:
            PositionAlreadyClosingError: If lock is already held by another operation
            PositionLockTimeoutError: If lock acquisition times out

        Usage:
            async with lock_manager.acquire_lock("pos_123", "close"):
                await do_close_operation()
        """
        timeout = timeout or self._default_timeout
        lock = await self._get_or_create_lock(position_id)

        # Try to acquire with timeout
        acquired = False
        try:
            # Check if already locked (fast path for immediate rejection)
            if lock.locked():
                holder = self._lock_holders.get(position_id, "unknown")
                logger.warning("position_lock_manager.already_locked", {
                    "position_id": position_id,
                    "operation": operation,
                    "held_by": holder,
                    "held_since": self._lock_times.get(position_id)
                })
                raise PositionAlreadyClosingError(position_id)

            # Try to acquire with timeout
            try:
                await asyncio.wait_for(lock.acquire(), timeout=timeout)
                acquired = True
            except asyncio.TimeoutError:
                logger.error("position_lock_manager.timeout", {
                    "position_id": position_id,
                    "operation": operation,
                    "timeout": timeout
                })
                raise PositionLockTimeoutError(position_id, timeout)

            # Record lock acquisition
            self._lock_times[position_id] = time.time()
            self._lock_holders[position_id] = operation

            logger.info("position_lock_manager.acquired", {
                "position_id": position_id,
                "operation": operation
            })

            yield

        finally:
            if acquired and lock.locked():
                # Calculate hold time for metrics
                hold_time = time.time() - self._lock_times.get(position_id, time.time())

                # Release lock
                lock.release()

                # Cleanup tracking
                self._lock_times.pop(position_id, None)
                self._lock_holders.pop(position_id, None)

                logger.info("position_lock_manager.released", {
                    "position_id": position_id,
                    "operation": operation,
                    "hold_time_seconds": round(hold_time, 3)
                })

    async def _get_or_create_lock(self, position_id: str) -> asyncio.Lock:
        """Get existing lock or create new one for position."""
        async with self._meta_lock:
            if position_id not in self._locks:
                self._locks[position_id] = asyncio.Lock()
            return self._locks[position_id]

    async def is_locked(self, position_id: str) -> bool:
        """Check if a position is currently locked."""
        async with self._meta_lock:
            lock = self._locks.get(position_id)
            return lock is not None and lock.locked()

    async def get_lock_info(self, position_id: str) -> Optional[Dict]:
        """Get information about a lock if it exists."""
        async with self._meta_lock:
            if position_id not in self._locks:
                return None

            lock = self._locks[position_id]
            if not lock.locked():
                return None

            return {
                "position_id": position_id,
                "operation": self._lock_holders.get(position_id, "unknown"),
                "acquired_at": self._lock_times.get(position_id),
                "held_seconds": time.time() - self._lock_times.get(position_id, time.time())
            }

    async def cleanup_stale_locks(self, max_age_seconds: float = 300.0) -> int:
        """
        Clean up locks that have been held too long (crash recovery).

        Args:
            max_age_seconds: Maximum age before a lock is considered stale

        Returns:
            Number of locks cleaned up
        """
        cleaned = 0
        current_time = time.time()

        async with self._meta_lock:
            stale_positions = []

            for position_id, acquired_at in self._lock_times.items():
                if current_time - acquired_at > max_age_seconds:
                    stale_positions.append(position_id)

            for position_id in stale_positions:
                lock = self._locks.get(position_id)
                if lock and lock.locked():
                    try:
                        lock.release()
                        cleaned += 1
                        logger.warning("position_lock_manager.stale_lock_cleaned", {
                            "position_id": position_id,
                            "operation": self._lock_holders.get(position_id),
                            "age_seconds": current_time - self._lock_times.get(position_id, 0)
                        })
                    except RuntimeError:
                        # Lock was already released
                        pass

                self._lock_times.pop(position_id, None)
                self._lock_holders.pop(position_id, None)

        return cleaned

    async def get_metrics(self) -> Dict:
        """Get lock manager metrics for monitoring."""
        async with self._meta_lock:
            active_locks = sum(1 for lock in self._locks.values() if lock.locked())

            return {
                "total_locks_created": len(self._locks),
                "active_locks": active_locks,
                "lock_positions": list(self._lock_holders.keys()),
                "default_timeout": self._default_timeout
            }

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing only)."""
        cls._instance = None


# Singleton accessor
def get_position_lock_manager() -> PositionLockManager:
    """Get the singleton PositionLockManager instance."""
    return PositionLockManager()
