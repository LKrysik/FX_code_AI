"""
MEXC Subscription Registry
==========================
BUG-008-5: Subscription Lifecycle Management

Provides:
- SubscriptionState enum with lifecycle states
- SubscriptionInfo dataclass for subscription tracking
- SubscriptionRegistry for managing subscription states
- Auto-resubscription on expiration with retry logic

State Machine:
    [PENDING] ──confirmation──► [ACTIVE] ──TTL expired──► [EXPIRED]
         │                          │                          │
         │                          │                          │
     timeout                    unsubscribe              retry initiated
         │                          │                          │
         ▼                          ▼                          ▼
    [EXPIRED] ◄─────────────── [INACTIVE]              [RETRYING]
         │                                                  │
         │                                             success/fail
         │                                                  │
         ▼                                                  ▼
    [RETRYING] ──max retries──► [FAILED]            [ACTIVE]/[FAILED]
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Callable, Awaitable, Any
from .....core.logger import StructuredLogger, get_logger


class SubscriptionState(Enum):
    """
    BUG-008-5 AC5: Subscription lifecycle states.
    """
    PENDING = "pending"      # Subscription request sent, awaiting confirmation
    ACTIVE = "active"        # Subscription confirmed and receiving data
    EXPIRED = "expired"      # Subscription TTL exceeded, needs resubscription
    RETRYING = "retrying"    # Resubscription in progress
    FAILED = "failed"        # Max retries exceeded, subscription failed
    INACTIVE = "inactive"    # Explicitly unsubscribed


# Valid state transitions
VALID_SUBSCRIPTION_TRANSITIONS = {
    None: [SubscriptionState.PENDING],  # Initial state
    SubscriptionState.PENDING: [
        SubscriptionState.ACTIVE,   # Confirmation received
        SubscriptionState.EXPIRED,  # TTL exceeded
        SubscriptionState.FAILED    # Immediate failure
    ],
    SubscriptionState.ACTIVE: [
        SubscriptionState.EXPIRED,   # TTL exceeded (no data)
        SubscriptionState.INACTIVE   # Explicit unsubscribe
    ],
    SubscriptionState.EXPIRED: [
        SubscriptionState.RETRYING,  # Retry initiated
        SubscriptionState.FAILED     # Skip to failed (optional)
    ],
    SubscriptionState.RETRYING: [
        SubscriptionState.PENDING,   # Resubscription sent
        SubscriptionState.ACTIVE,    # Late confirmation accepted
        SubscriptionState.FAILED     # Max retries exceeded
    ],
    SubscriptionState.FAILED: [],     # Terminal state
    SubscriptionState.INACTIVE: [
        SubscriptionState.PENDING    # Re-subscribe
    ]
}


@dataclass
class SubscriptionInfo:
    """
    BUG-008-5 AC6: Subscription tracking information.
    """
    symbol: str
    channel: str  # 'deal', 'depth', 'depth_full'
    connection_id: int
    state: SubscriptionState = SubscriptionState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    next_retry_at: Optional[float] = None  # Unix timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API."""
        return {
            "symbol": self.symbol,
            "channel": self.channel,
            "connection_id": self.connection_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "retry_count": self.retry_count,
            "last_error": self.last_error
        }


# Configuration constants
SUBSCRIPTION_TTL_SECONDS = 30  # Time to wait for confirmation
SUBSCRIPTION_MAX_RETRIES = 3
SUBSCRIPTION_RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff


class SubscriptionRegistry:
    """
    BUG-008-5: Manages subscription lifecycle across all connections.

    Features:
    - Tracks subscription state per (symbol, channel) tuple
    - Auto-resubscription on expiration (AC1)
    - Retry logic with exponential backoff (AC2, AC3)
    - Late confirmation handling (AC4)
    - Active subscriptions query (AC6)
    """

    def __init__(
        self,
        logger: Optional[StructuredLogger] = None,
        resubscribe_callback: Optional[Callable[[str, int], Awaitable[bool]]] = None,
        max_retries: int = SUBSCRIPTION_MAX_RETRIES,
        retry_delays: List[float] = None,
        ttl_seconds: float = SUBSCRIPTION_TTL_SECONDS
    ):
        """
        Initialize subscription registry.

        Args:
            logger: Structured logger instance
            resubscribe_callback: Async callback to resubscribe (symbol, connection_id) -> success
            max_retries: Maximum retry attempts before marking as failed
            retry_delays: List of delays between retries (seconds)
            ttl_seconds: Time to wait for confirmation before expiring
        """
        self.logger = logger or get_logger("subscription_registry")
        self._resubscribe = resubscribe_callback
        self.max_retries = max_retries
        self.retry_delays = retry_delays or SUBSCRIPTION_RETRY_DELAYS
        self.ttl_seconds = ttl_seconds

        # Registry: (symbol, channel) -> SubscriptionInfo
        self._subscriptions: Dict[Tuple[str, str], SubscriptionInfo] = {}

        # Lock for thread-safe access
        self._lock = asyncio.Lock()

        # Background task for TTL checking
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start background TTL cleanup task."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._ttl_cleanup_loop())
        self.logger.info("subscription_registry.started", {
            "ttl_seconds": self.ttl_seconds,
            "max_retries": self.max_retries
        })

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("subscription_registry.stopped", {
            "subscriptions_count": len(self._subscriptions)
        })

    # =========================================================================
    # Public API
    # =========================================================================

    async def register_subscription(
        self,
        symbol: str,
        channel: str,
        connection_id: int
    ) -> SubscriptionInfo:
        """
        Register a new subscription (PENDING state).

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel ('deal', 'depth', 'depth_full')
            connection_id: WebSocket connection ID

        Returns:
            Created SubscriptionInfo
        """
        async with self._lock:
            key = (symbol, channel)

            # Check if already exists
            if key in self._subscriptions:
                existing = self._subscriptions[key]
                # If failed or inactive, allow re-registration
                if existing.state in (SubscriptionState.FAILED, SubscriptionState.INACTIVE):
                    self.logger.info("subscription_registry.reregistering", {
                        "symbol": symbol,
                        "channel": channel,
                        "old_state": existing.state.value
                    })
                else:
                    self.logger.warning("subscription_registry.already_registered", {
                        "symbol": symbol,
                        "channel": channel,
                        "current_state": existing.state.value
                    })
                    return existing

            # Create new subscription
            info = SubscriptionInfo(
                symbol=symbol,
                channel=channel,
                connection_id=connection_id,
                state=SubscriptionState.PENDING
            )
            self._subscriptions[key] = info

            self.logger.info("subscription_registry.registered", {
                "symbol": symbol,
                "channel": channel,
                "connection_id": connection_id
            })

            return info

    async def confirm_subscription(
        self,
        symbol: str,
        channel: str
    ) -> bool:
        """
        Confirm subscription (PENDING/RETRYING → ACTIVE).

        BUG-008-5 AC4: Late confirmations handled gracefully.

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel

        Returns:
            True if confirmation processed, False if not found
        """
        async with self._lock:
            key = (symbol, channel)
            info = self._subscriptions.get(key)

            if not info:
                # BUG-008-5 AC4: Late confirmation for unknown subscription
                self.logger.info("subscription_registry.late_confirmation_no_subscription", {
                    "symbol": symbol,
                    "channel": channel,
                    "action": "ignored"
                })
                return False

            old_state = info.state

            # Accept confirmation from PENDING, RETRYING, or EXPIRED
            if info.state in (SubscriptionState.PENDING, SubscriptionState.RETRYING, SubscriptionState.EXPIRED):
                info.state = SubscriptionState.ACTIVE
                info.confirmed_at = datetime.now(timezone.utc)
                info.last_activity_at = datetime.now(timezone.utc)
                info.retry_count = 0  # Reset on success
                info.next_retry_at = None

                self.logger.info("subscription_registry.confirmed", {
                    "symbol": symbol,
                    "channel": channel,
                    "old_state": old_state.value,
                    "new_state": info.state.value
                })
                return True

            # Already active or failed - just log
            self.logger.info("subscription_registry.confirmation_ignored", {
                "symbol": symbol,
                "channel": channel,
                "current_state": info.state.value,
                "reason": "already_in_terminal_or_active_state"
            })
            return False

    async def mark_expired(
        self,
        symbol: str,
        channel: str,
        reason: str = "TTL_exceeded"
    ) -> bool:
        """
        Mark subscription as expired.

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel
            reason: Expiration reason

        Returns:
            True if marked, False if not found
        """
        async with self._lock:
            key = (symbol, channel)
            info = self._subscriptions.get(key)

            if not info:
                return False

            if info.state in (SubscriptionState.PENDING, SubscriptionState.ACTIVE):
                old_state = info.state
                info.state = SubscriptionState.EXPIRED
                info.last_error = reason

                self.logger.warning("subscription_registry.expired", {
                    "symbol": symbol,
                    "channel": channel,
                    "old_state": old_state.value,
                    "reason": reason
                })
                return True

            return False

    async def mark_failed(
        self,
        symbol: str,
        channel: str,
        error: str
    ) -> bool:
        """
        BUG-008-5 AC3: Mark subscription as failed after max retries.

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel
            error: Error message

        Returns:
            True if marked, False if not found
        """
        async with self._lock:
            key = (symbol, channel)
            info = self._subscriptions.get(key)

            if not info:
                return False

            old_state = info.state
            info.state = SubscriptionState.FAILED
            info.last_error = error

            self.logger.error("subscription_registry.failed", {
                "symbol": symbol,
                "channel": channel,
                "old_state": old_state.value,
                "error": error,
                "retry_count": info.retry_count
            })
            return True

    async def unsubscribe(
        self,
        symbol: str,
        channel: str
    ) -> bool:
        """
        Mark subscription as inactive (explicit unsubscribe).

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel

        Returns:
            True if marked, False if not found
        """
        async with self._lock:
            key = (symbol, channel)
            info = self._subscriptions.get(key)

            if not info:
                return False

            old_state = info.state
            info.state = SubscriptionState.INACTIVE

            self.logger.info("subscription_registry.unsubscribed", {
                "symbol": symbol,
                "channel": channel,
                "old_state": old_state.value
            })
            return True

    def record_activity(self, symbol: str, channel: str) -> None:
        """
        Record data activity for subscription (non-blocking).

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel
        """
        key = (symbol, channel)
        info = self._subscriptions.get(key)
        if info and info.state == SubscriptionState.ACTIVE:
            info.last_activity_at = datetime.now(timezone.utc)

    # =========================================================================
    # BUG-008-5 AC6: Query Methods
    # =========================================================================

    def get_active_subscriptions(self) -> List[SubscriptionInfo]:
        """
        BUG-008-5 AC6: Get list of active subscriptions.

        Returns:
            List of active SubscriptionInfo objects
        """
        return [
            info for info in self._subscriptions.values()
            if info.state == SubscriptionState.ACTIVE
        ]

    def get_subscription_state(
        self,
        symbol: str,
        channel: str
    ) -> Optional[SubscriptionState]:
        """
        Get current state of a subscription.

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel

        Returns:
            Current state or None if not found
        """
        key = (symbol, channel)
        info = self._subscriptions.get(key)
        return info.state if info else None

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get all subscriptions as dictionaries.

        Returns:
            List of subscription dictionaries
        """
        return [info.to_dict() for info in self._subscriptions.values()]

    def get_subscriptions_by_state(
        self,
        state: SubscriptionState
    ) -> List[SubscriptionInfo]:
        """
        Get subscriptions in specific state.

        Args:
            state: State to filter by

        Returns:
            List of matching SubscriptionInfo objects
        """
        return [
            info for info in self._subscriptions.values()
            if info.state == state
        ]

    # =========================================================================
    # BUG-008-5 AC1, AC2: Auto-resubscription
    # =========================================================================

    async def _ttl_cleanup_loop(self) -> None:
        """
        Background task to check TTL and trigger resubscription.

        BUG-008-5 AC1: Expired subscriptions trigger automatic resubscription.
        """
        while self._running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                await self._check_and_resubscribe()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("subscription_registry.cleanup_error", {
                    "error": str(e) if str(e) else type(e).__name__,
                    "error_type": type(e).__name__
                })

    async def _check_and_resubscribe(self) -> None:
        """
        Check for expired/retrying subscriptions and handle them.
        """
        current_time = time.time()
        to_retry: List[Tuple[str, str, SubscriptionInfo]] = []

        async with self._lock:
            for key, info in self._subscriptions.items():
                symbol, channel = key

                # Check PENDING subscriptions for TTL expiration
                if info.state == SubscriptionState.PENDING:
                    age = (datetime.now(timezone.utc) - info.created_at).total_seconds()
                    if age > self.ttl_seconds:
                        info.state = SubscriptionState.EXPIRED
                        info.last_error = "TTL_exceeded"
                        self.logger.warning("subscription_registry.ttl_expired", {
                            "symbol": symbol,
                            "channel": channel,
                            "age_seconds": age
                        })
                        to_retry.append((symbol, channel, info))

                # Check EXPIRED subscriptions for retry
                elif info.state == SubscriptionState.EXPIRED:
                    if info.retry_count < self.max_retries:
                        to_retry.append((symbol, channel, info))
                    else:
                        # Max retries exceeded
                        info.state = SubscriptionState.FAILED
                        self.logger.error("subscription_registry.max_retries_exceeded", {
                            "symbol": symbol,
                            "channel": channel,
                            "retry_count": info.retry_count
                        })

                # Check RETRYING subscriptions for next retry time
                elif info.state == SubscriptionState.RETRYING:
                    if info.next_retry_at and current_time >= info.next_retry_at:
                        to_retry.append((symbol, channel, info))

        # Process retries outside lock
        for symbol, channel, info in to_retry:
            await self._attempt_resubscription(symbol, channel, info)

    async def _attempt_resubscription(
        self,
        symbol: str,
        channel: str,
        info: SubscriptionInfo
    ) -> None:
        """
        BUG-008-5 AC2: Attempt resubscription with backoff.

        Args:
            symbol: Trading pair symbol
            channel: Subscription channel
            info: Subscription info
        """
        if not self._resubscribe:
            self.logger.warning("subscription_registry.no_resubscribe_callback", {
                "symbol": symbol,
                "channel": channel
            })
            return

        # Calculate delay based on retry count
        retry_index = min(info.retry_count, len(self.retry_delays) - 1)
        delay = self.retry_delays[retry_index]

        # Update state
        async with self._lock:
            info.state = SubscriptionState.RETRYING
            info.retry_count += 1
            info.next_retry_at = time.time() + delay

        self.logger.info("subscription_registry.retrying", {
            "symbol": symbol,
            "channel": channel,
            "retry_count": info.retry_count,
            "delay_seconds": delay
        })

        # Wait for backoff delay
        await asyncio.sleep(delay)

        # Attempt resubscription
        try:
            success = await self._resubscribe(symbol, info.connection_id)

            if success:
                async with self._lock:
                    info.state = SubscriptionState.PENDING
                    info.created_at = datetime.now(timezone.utc)
                    info.next_retry_at = None

                self.logger.info("subscription_registry.resubscription_sent", {
                    "symbol": symbol,
                    "channel": channel,
                    "retry_count": info.retry_count
                })
            else:
                # Check if max retries exceeded
                if info.retry_count >= self.max_retries:
                    await self.mark_failed(symbol, channel, "resubscription_failed_max_retries")
                else:
                    async with self._lock:
                        info.state = SubscriptionState.EXPIRED
                        info.last_error = "resubscription_failed"

        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            self.logger.error("subscription_registry.resubscription_error", {
                "symbol": symbol,
                "channel": channel,
                "error": error_msg,
                "retry_count": info.retry_count
            })

            if info.retry_count >= self.max_retries:
                await self.mark_failed(symbol, channel, f"resubscription_error: {error_msg}")
            else:
                async with self._lock:
                    info.state = SubscriptionState.EXPIRED
                    info.last_error = error_msg

    # =========================================================================
    # Cleanup
    # =========================================================================

    def clear(self) -> None:
        """Clear all subscriptions."""
        self._subscriptions.clear()
        self.logger.info("subscription_registry.cleared", {})

    def remove_connection_subscriptions(self, connection_id: int) -> int:
        """
        Remove all subscriptions for a connection.

        Args:
            connection_id: Connection ID to remove

        Returns:
            Number of subscriptions removed
        """
        to_remove = [
            key for key, info in self._subscriptions.items()
            if info.connection_id == connection_id
        ]

        for key in to_remove:
            del self._subscriptions[key]

        if to_remove:
            self.logger.info("subscription_registry.connection_removed", {
                "connection_id": connection_id,
                "removed_count": len(to_remove)
            })

        return len(to_remove)
