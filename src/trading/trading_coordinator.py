"""
Trading Coordinator - Mediator Pattern Implementation
======================================================
Central coordinator eliminating circular dependency between
LiveMarketAdapter and SessionManager.

Design Pattern: Mediator
- Decouples components that would otherwise reference each other
- Centralizes coordination logic
- Uses EventBus for async communication

Event Topics:
- subscription.request -> Coordinator handles, responds via callback
- subscription.granted -> Published when subscription allowed
- subscription.denied -> Published when subscription blocked
- subscription.success -> Market adapter notifies success
- subscription.failure -> Market adapter notifies failure
- circuit_breaker.state_changed -> Session manager publishes state changes
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from ..domain.interfaces.coordination import (
    ITradingCoordinator,
    SubscriptionDecision,
)


@dataclass
class SubscriptionState:
    """Track subscription state for a symbol"""
    symbol: str
    is_subscribed: bool = False
    last_request_time: Optional[datetime] = None
    failure_count: int = 0
    last_failure_reason: Optional[str] = None


@dataclass
class RateLimitState:
    """Track rate limiting state"""
    requests_per_minute: int = 0
    last_reset_time: datetime = field(default_factory=datetime.now)
    max_requests_per_minute: int = 60


class TradingCoordinator(ITradingCoordinator):
    """
    Mediator coordinating LiveMarketAdapter and SessionManager.

    Eliminates circular dependency by:
    1. LiveMarketAdapter asks Coordinator for subscription permission
    2. Coordinator checks with SessionManager via EventBus
    3. SessionManager responds via EventBus callback
    4. Coordinator returns decision to LiveMarketAdapter

    This breaks the direct A <-> B dependency into A -> Coordinator <- B
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: StructuredLogger,
        rate_limit_per_minute: int = 60,
        default_decision_timeout: float = 5.0
    ):
        self.event_bus = event_bus
        self.logger = logger
        self._rate_limit_per_minute = rate_limit_per_minute
        self._decision_timeout = default_decision_timeout

        # State tracking
        self._subscriptions: Dict[str, SubscriptionState] = {}
        self._rate_limit = RateLimitState(max_requests_per_minute=rate_limit_per_minute)
        self._circuit_breaker_states: Dict[str, Dict[str, Any]] = {}

        # Session state (updated via EventBus)
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_manager_registered = False

        # Pending requests (for async request/response pattern)
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # Control
        self._is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger.info("trading_coordinator.initialized", {
            "rate_limit_per_minute": rate_limit_per_minute,
            "decision_timeout": default_decision_timeout
        })

    async def start(self) -> None:
        """Start coordinator and subscribe to EventBus topics"""
        if self._is_running:
            self.logger.warning("trading_coordinator.already_running")
            return

        # Subscribe to EventBus topics
        await self.event_bus.subscribe("session.registered", self._on_session_manager_registered)
        await self.event_bus.subscribe("session.started", self._on_session_started)
        await self.event_bus.subscribe("session.stopped", self._on_session_stopped)
        await self.event_bus.subscribe("circuit_breaker.state_changed", self._on_circuit_breaker_changed)
        await self.event_bus.subscribe("subscription.check_response", self._on_subscription_check_response)

        # Start cleanup task for stale requests
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_requests())

        self._is_running = True

        self.logger.info("trading_coordinator.started", {
            "subscribed_topics": [
                "session.registered",
                "session.started",
                "session.stopped",
                "circuit_breaker.state_changed",
                "subscription.check_response"
            ]
        })

    async def stop(self) -> None:
        """Stop coordinator and cleanup"""
        if not self._is_running:
            return

        self._is_running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel pending requests
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()

        self._pending_requests.clear()

        # Unsubscribe from EventBus
        await self.event_bus.unsubscribe("session.registered", self._on_session_manager_registered)
        await self.event_bus.unsubscribe("session.started", self._on_session_started)
        await self.event_bus.unsubscribe("session.stopped", self._on_session_stopped)
        await self.event_bus.unsubscribe("circuit_breaker.state_changed", self._on_circuit_breaker_changed)
        await self.event_bus.unsubscribe("subscription.check_response", self._on_subscription_check_response)

        self.logger.info("trading_coordinator.stopped")

    # =========================================================================
    # ISubscriptionCoordinator Implementation
    # =========================================================================

    async def request_subscription(
        self,
        symbol: str,
        requester_id: str = "market_adapter"
    ) -> SubscriptionDecision:
        """
        Request permission to subscribe to a symbol.
        Coordinates with SessionManager via EventBus.
        """
        # Check rate limit first (local check, no EventBus needed)
        if not self._check_rate_limit():
            self.logger.warning("trading_coordinator.rate_limited", {"symbol": symbol})
            return SubscriptionDecision.DENIED_RATE_LIMIT

        # If no session manager registered, allow by default (graceful degradation)
        if not self._session_manager_registered:
            self.logger.warning("trading_coordinator.no_session_manager", {
                "symbol": symbol,
                "decision": "allowed_no_session_manager"
            })
            return SubscriptionDecision.ALLOWED

        # Check cached circuit breaker state
        if symbol in self._circuit_breaker_states:
            cb_state = self._circuit_breaker_states[symbol]
            if cb_state.get("state") == "open":
                self.logger.info("trading_coordinator.circuit_open", {"symbol": symbol})
                return SubscriptionDecision.DENIED_CIRCUIT_OPEN

        # Request check from SessionManager via EventBus
        request_id = f"{symbol}_{datetime.now().timestamp()}"

        try:
            # Create future for response
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            self._pending_requests[request_id] = future

            # Publish request
            await self.event_bus.publish("subscription.check_request", {
                "request_id": request_id,
                "symbol": symbol,
                "requester_id": requester_id,
                "timestamp": datetime.now().isoformat()
            })

            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(future, timeout=self._decision_timeout)
                return result
            except asyncio.TimeoutError:
                self.logger.warning("trading_coordinator.check_timeout", {
                    "symbol": symbol,
                    "timeout": self._decision_timeout
                })
                # On timeout, allow subscription (fail-open for availability)
                return SubscriptionDecision.ALLOWED

        finally:
            # Cleanup pending request
            self._pending_requests.pop(request_id, None)

    async def notify_subscription_success(self, symbol: str) -> None:
        """Track successful subscription"""
        if symbol not in self._subscriptions:
            self._subscriptions[symbol] = SubscriptionState(symbol=symbol)

        self._subscriptions[symbol].is_subscribed = True
        self._subscriptions[symbol].failure_count = 0

        await self.event_bus.publish("subscription.success", {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })

        self.logger.debug("trading_coordinator.subscription_success", {"symbol": symbol})

    async def notify_subscription_failure(self, symbol: str, error: str) -> None:
        """Track failed subscription"""
        if symbol not in self._subscriptions:
            self._subscriptions[symbol] = SubscriptionState(symbol=symbol)

        state = self._subscriptions[symbol]
        state.failure_count += 1
        state.last_failure_reason = error

        await self.event_bus.publish("subscription.failure", {
            "symbol": symbol,
            "error": error,
            "failure_count": state.failure_count,
            "timestamp": datetime.now().isoformat()
        })

        self.logger.warning("trading_coordinator.subscription_failure", {
            "symbol": symbol,
            "error": error,
            "failure_count": state.failure_count
        })

    async def request_unsubscription(self, symbol: str) -> bool:
        """Handle unsubscription request"""
        if symbol in self._subscriptions:
            self._subscriptions[symbol].is_subscribed = False

        await self.event_bus.publish("subscription.unsubscribed", {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })

        return True

    # =========================================================================
    # ISessionStateProvider Implementation
    # =========================================================================

    async def is_session_active(self, session_id: Optional[str] = None) -> bool:
        """Check if session(s) are active"""
        if session_id:
            return session_id in self._active_sessions
        return len(self._active_sessions) > 0

    async def get_active_symbols(self) -> List[str]:
        """Get list of actively subscribed symbols"""
        return [
            symbol for symbol, state in self._subscriptions.items()
            if state.is_subscribed
        ]

    async def get_circuit_breaker_state(self, symbol: str) -> Dict[str, Any]:
        """Get circuit breaker state for symbol"""
        return self._circuit_breaker_states.get(symbol, {
            "state": "closed",
            "failure_count": 0
        })

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return {
            "requests_this_minute": self._rate_limit.requests_per_minute,
            "max_per_minute": self._rate_limit.max_requests_per_minute,
            "remaining": self._rate_limit.max_requests_per_minute - self._rate_limit.requests_per_minute
        }

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Return coordinator health status"""
        return {
            "healthy": self._is_running,
            "session_manager_registered": self._session_manager_registered,
            "active_sessions": len(self._active_sessions),
            "active_subscriptions": len([s for s in self._subscriptions.values() if s.is_subscribed]),
            "pending_requests": len(self._pending_requests),
            "rate_limit_status": await self.get_rate_limit_status()
        }

    # =========================================================================
    # EventBus Handlers
    # =========================================================================

    async def _on_session_manager_registered(self, data: Dict[str, Any]) -> None:
        """Handle session manager registration"""
        self._session_manager_registered = True
        self.logger.info("trading_coordinator.session_manager_registered", data)

    async def _on_session_started(self, data: Dict[str, Any]) -> None:
        """Handle session started event"""
        session_id = data.get("session_id")
        if session_id:
            self._active_sessions[session_id] = data
            self.logger.info("trading_coordinator.session_tracked", {
                "session_id": session_id
            })

    async def _on_session_stopped(self, data: Dict[str, Any]) -> None:
        """Handle session stopped event"""
        session_id = data.get("session_id")
        if session_id and session_id in self._active_sessions:
            del self._active_sessions[session_id]
            self.logger.info("trading_coordinator.session_removed", {
                "session_id": session_id
            })

    async def _on_circuit_breaker_changed(self, data: Dict[str, Any]) -> None:
        """Handle circuit breaker state change"""
        symbol = data.get("symbol")
        if symbol:
            self._circuit_breaker_states[symbol] = data
            self.logger.debug("trading_coordinator.circuit_breaker_updated", {
                "symbol": symbol,
                "state": data.get("state")
            })

    async def _on_subscription_check_response(self, data: Dict[str, Any]) -> None:
        """Handle subscription check response from SessionManager"""
        request_id = data.get("request_id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                allowed = data.get("allowed", True)
                reason = data.get("reason", "")

                if allowed:
                    future.set_result(SubscriptionDecision.ALLOWED)
                elif "rate" in reason.lower():
                    future.set_result(SubscriptionDecision.DENIED_RATE_LIMIT)
                elif "circuit" in reason.lower():
                    future.set_result(SubscriptionDecision.DENIED_CIRCUIT_OPEN)
                elif "quota" in reason.lower():
                    future.set_result(SubscriptionDecision.DENIED_QUOTA_EXCEEDED)
                else:
                    future.set_result(SubscriptionDecision.DENIED_NO_SESSION)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _check_rate_limit(self) -> bool:
        """Check local rate limit"""
        now = datetime.now()

        # Reset counter if minute has passed
        if (now - self._rate_limit.last_reset_time).total_seconds() >= 60:
            self._rate_limit.requests_per_minute = 0
            self._rate_limit.last_reset_time = now

        # Check limit
        if self._rate_limit.requests_per_minute >= self._rate_limit.max_requests_per_minute:
            return False

        self._rate_limit.requests_per_minute += 1
        return True

    async def _cleanup_stale_requests(self) -> None:
        """Periodically cleanup stale pending requests"""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                stale_requests = []
                for request_id, future in self._pending_requests.items():
                    if future.done():
                        stale_requests.append(request_id)

                for request_id in stale_requests:
                    del self._pending_requests[request_id]

                if stale_requests:
                    self.logger.debug("trading_coordinator.cleaned_stale_requests", {
                        "count": len(stale_requests)
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("trading_coordinator.cleanup_error", {"error": str(e)})
