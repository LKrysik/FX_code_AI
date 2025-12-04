"""
Session Manager - Sprint 4 Trading Session Control
==================================================

Production-grade session management for live trading operations with rate limiting,
circuit breakers, and coordinated session lifecycle management.

Features:
- Per-symbol circuit breakers to prevent cascading failures
- Rate limiting for trading operations
- Session lifecycle coordination with market adapter
- Risk controls integration
- Incident logging for session failures
- Resource quota management

Critical Analysis Points:
1. **Circuit Breaker Coordination**: Prevents symbol-specific failures from affecting others
2. **Rate Limiting**: Protects against API throttling and ensures fair resource allocation
3. **Session Coordination**: Ensures market adapter and trading sessions are synchronized
4. **Resource Quotas**: Prevents resource exhaustion during high-volume periods
5. **Incident Correlation**: Links session failures to market data issues
6. **Graceful Degradation**: Maintains partial functionality when components fail
"""

import asyncio
import time
from typing import Dict, Any, Optional, Set, List, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger

if TYPE_CHECKING:
    from ..data.live_market_adapter import LiveMarketAdapter


class SessionState(Enum):
    """Trading session states"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    RUNNING = "running"
    THROTTLED = "throttled"
    CIRCUIT_OPEN = "circuit_open"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class SymbolCircuitBreaker:
    """Per-symbol circuit breaker"""
    symbol: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    success_count: int = 0
    next_attempt_time: Optional[float] = None

    # Configuration
    failure_threshold: int = 5
    timeout_seconds: float = 60.0
    success_threshold: int = 3

    def record_failure(self) -> None:
        """Record a failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = time.time() + self.timeout_seconds

    def record_success(self) -> None:
        """Record a success"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def can_attempt(self) -> bool:
        """Check if operation can be attempted"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() >= (self.next_attempt_time or 0):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False


@dataclass
class TradingSession:
    """Trading session with coordinated state management"""
    session_id: str
    client_id: str
    symbols: List[str]
    mode: str  # "paper" or "live"
    state: SessionState = SessionState.INITIALIZING
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    circuit_breakers: Dict[str, SymbolCircuitBreaker] = field(default_factory=dict)

    # Performance metrics
    operations_count: int = 0
    failures_count: int = 0
    throttled_count: int = 0

    # Resource usage
    active_subscriptions: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "symbols": self.symbols,
            "mode": self.mode,
            "state": self.state.value,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "operations_count": self.operations_count,
            "failures_count": self.failures_count,
            "throttled_count": self.throttled_count,
            "active_subscriptions": list(self.active_subscriptions),
            "circuit_breakers": {
                symbol: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time
                }
                for symbol, cb in self.circuit_breakers.items()
            }
        }


class SessionManager:
    """
    Production-grade session manager for Sprint 4 live operations.

    Manages trading sessions with coordinated market data access, rate limiting,
    circuit breakers, and incident correlation.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: StructuredLogger,
        market_adapter: "LiveMarketAdapter"
    ):
        self.event_bus = event_bus
        self.logger = logger
        self.market_adapter = market_adapter

        # Session management
        self.active_sessions: Dict[str, TradingSession] = {}
        self.session_lock = asyncio.Lock()

        # Rate limiting
        self.rate_limiter_config = {
            "operations_per_second": 10,  # Global operations limit
            "operations_per_minute": 300,  # Per session operations
            "burst_limit": 50  # Burst capacity
        }

        # Global rate limiting state
        # FIX P0 LEAK #1: Changed from List to deque(maxlen=1000) to prevent unbounded growth
        self._operation_timestamps: deque = deque(maxlen=1000)
        self._rate_limit_lock = asyncio.Lock()

        # Global operation counters (persist across sessions)
        self._total_operations = 0
        self._total_failures = 0

        # Circuit breaker defaults
        self.circuit_config = {
            "failure_threshold": 5,
            "timeout_seconds": 60.0,
            "success_threshold": 3
        }

        # Global circuit breakers (coordinated across sessions)
        self.global_circuit_breakers: Dict[str, SymbolCircuitBreaker] = {}

        # Resource limits
        self.resource_limits = {
            "max_sessions_per_client": 5,
            "max_symbols_per_session": 20,
            "max_total_sessions": 50
        }

        # Monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger.info("session_manager.initialized", {
            "rate_limits": self.rate_limiter_config,
            "circuit_config": self.circuit_config,
            "resource_limits": self.resource_limits
        })

    async def start_session(
        self,
        session_id: str,
        client_id: str,
        symbols: List[str],
        mode: str = "paper"
    ) -> bool:
        """
        Start a new trading session with coordinated setup.

        Args:
            session_id: Unique session identifier
            client_id: Client identifier
            symbols: List of symbols to trade
            mode: Trading mode ("paper" or "live")

        Returns:
            True if session started successfully
        """
        async with self.session_lock:
            # Check resource limits
            if not await self._check_resource_limits(client_id, symbols):
                self.logger.warning("session_manager.resource_limit_exceeded", {
                    "session_id": session_id,
                    "client_id": client_id,
                    "symbols_count": len(symbols)
                })
                return False

            # Create session
            session = TradingSession(
                session_id=session_id,
                client_id=client_id,
                symbols=symbols,
                mode=mode,
                state=SessionState.CONNECTING
            )

            # Initialize circuit breakers for symbols (both session and global)
            for symbol in symbols:
                if symbol not in self.global_circuit_breakers:
                    self.global_circuit_breakers[symbol] = SymbolCircuitBreaker(
                        symbol=symbol,
                        failure_threshold=self.circuit_config["failure_threshold"],
                        timeout_seconds=self.circuit_config["timeout_seconds"],
                        success_threshold=self.circuit_config["success_threshold"]
                    )

                session.circuit_breakers[symbol] = self.global_circuit_breakers[symbol]

            self.active_sessions[session_id] = session

        # Attempt to subscribe to symbols
        try:
            for symbol in symbols:
                if await self.market_adapter.subscribe_to_symbol(symbol):
                    session.active_subscriptions.add(symbol)
                else:
                    await self._handle_subscription_failure(session, symbol)

            if session.active_subscriptions:
                session.state = SessionState.RUNNING
                session.last_activity = datetime.now()

                self.logger.info("session_manager.session_started", {
                    "session_id": session_id,
                    "client_id": client_id,
                    "symbols": list(session.active_subscriptions),
                    "mode": mode
                })

                # Publish session started event
                await self.event_bus.publish("session.started", session.to_dict())
                return True
            else:
                # No symbols could be subscribed
                session.state = SessionState.FAILED
                await self._cleanup_session(session_id)
                return False

        except Exception as e:
            session.state = SessionState.FAILED
            await self._cleanup_session(session_id)

            self.logger.error("session_manager.session_start_failed", {
                "session_id": session_id,
                "error": str(e)
            })
            return False

    async def stop_session(self, session_id: str, client_id: str) -> bool:
        """
        Stop a trading session gracefully.

        Args:
            session_id: Session to stop
            client_id: Client requesting stop (for authorization)

        Returns:
            True if stopped successfully
        """
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session or session.client_id != client_id:
                return False

            session.state = SessionState.STOPPING

        # Unsubscribe from all symbols
        cleanup_errors = []
        try:
            for symbol in session.active_subscriptions.copy():
                try:
                    await self.market_adapter.unsubscribe_from_symbol(symbol)
                    session.active_subscriptions.discard(symbol)
                except Exception as e:
                    cleanup_errors.append((symbol, str(e)))
                    self.logger.warning("session_manager.cleanup_unsubscribe_failed", {
                        "session_id": session_id,
                        "symbol": symbol,
                        "error": str(e)
                    })

            session.state = SessionState.STOPPED
            session.last_activity = datetime.now()

            self.logger.info("session_manager.session_stopped", {
                "session_id": session_id,
                "client_id": client_id,
                "final_subscriptions": list(session.active_subscriptions),
                "cleanup_errors": len(cleanup_errors)
            })

            # Publish session stopped event
            await self.event_bus.publish("session.stopped", session.to_dict())

            # Cleanup
            await self._cleanup_session(session_id)
            return True

        except Exception as e:
            session.state = SessionState.FAILED
            self.logger.error("session_manager.session_stop_failed", {
                "session_id": session_id,
                "error": str(e)
            })
            await self._cleanup_session(session_id)
            return False

    async def can_subscribe_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol can be subscribed to (circuit breaker and rate limit check).

        Args:
            symbol: Symbol to check

        Returns:
            True if subscription is allowed
        """
        # Check global rate limits
        if not await self._check_global_rate_limit():
            return False

        # Record this check as an operation for rate limiting
        async with self._rate_limit_lock:
            current_time = time.time()
            self._operation_timestamps.append(current_time)

        # Check global circuit breaker for the symbol
        circuit_breaker = self.global_circuit_breakers.get(symbol)
        if circuit_breaker and not circuit_breaker.can_attempt():
            return False

        return True

    async def record_operation(
        self,
        session_id: str,
        symbol: str,
        success: bool,
        operation_type: str = "trade"
    ) -> None:
        """
        Record an operation result for circuit breaker and metrics.

        Args:
            session_id: Session performing operation
            symbol: Symbol operation was on
            success: Whether operation succeeded
            operation_type: Type of operation
        """
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return

            session.operations_count += 1
            session.last_activity = datetime.now()
            self._total_operations += 1

            circuit_breaker = session.circuit_breakers.get(symbol)
            if circuit_breaker:
                if success:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure()
                    session.failures_count += 1
                    self._total_failures += 1

                    # Check if session should be throttled
                    if circuit_breaker.state == CircuitBreakerState.OPEN:
                        session.state = SessionState.CIRCUIT_OPEN
                        await self.event_bus.publish("session.circuit_opened", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "circuit_breaker": {
                                "state": circuit_breaker.state.value,
                                "failure_count": circuit_breaker.failure_count
                            }
                        })

    async def get_session_status(self, session_id: str, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed session status.

        Args:
            session_id: Session to query
            client_id: Client requesting status (for authorization)

        Returns:
            Session status dict or None if not found/unauthorized
        """
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session or session.client_id != client_id:
                return None

            return session.to_dict()

    async def list_client_sessions(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List all sessions for a client.

        Args:
            client_id: Client to list sessions for

        Returns:
            List of session status dicts
        """
        async with self.session_lock:
            sessions = [
                session.to_dict()
                for session in self.active_sessions.values()
                if session.client_id == client_id
            ]
            return sessions

    async def _check_resource_limits(self, client_id: str, symbols: List[str]) -> bool:
        """Check if session creation is within resource limits"""
        client_sessions = [
            s for s in self.active_sessions.values()
            if s.client_id == client_id
        ]

        # Check per-client session limit
        if len(client_sessions) >= self.resource_limits["max_sessions_per_client"]:
            return False

        # Check total session limit
        if len(self.active_sessions) >= self.resource_limits["max_total_sessions"]:
            return False

        # Check symbols per session limit
        if len(symbols) > self.resource_limits["max_symbols_per_session"]:
            return False

        return True

    async def _check_global_rate_limit(self) -> bool:
        """Check global rate limits"""
        async with self._rate_limit_lock:
            current_time = time.time()

            # No need to clean old timestamps - deque automatically drops oldest when maxlen reached

            # Check per-second limit (sliding window)
            recent_ops = sum(1 for ts in self._operation_timestamps if ts > current_time - 1)
            if recent_ops >= self.rate_limiter_config["operations_per_second"]:
                return False

            # Check per-minute limit
            if len(self._operation_timestamps) >= self.rate_limiter_config["operations_per_minute"]:
                return False

            # Check burst limit
            if len(self._operation_timestamps) >= self.rate_limiter_config["burst_limit"]:
                return False

            return True

    async def _handle_subscription_failure(self, session: TradingSession, symbol: str) -> None:
        """Handle symbol subscription failure"""
        circuit_breaker = session.circuit_breakers.get(symbol)
        if circuit_breaker:
            circuit_breaker.record_failure()

        self.logger.warning("session_manager.subscription_failed", {
            "session_id": session.session_id,
            "symbol": symbol,
            "circuit_breaker_state": circuit_breaker.state.value if circuit_breaker else "none"
        })

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a completed session"""
        async with self.session_lock:
            session = self.active_sessions.pop(session_id, None)
            if session:
                # Unsubscribe from any remaining symbols
                for symbol in session.active_subscriptions.copy():
                    try:
                        await self.market_adapter.unsubscribe_from_symbol(symbol)
                    except Exception as e:
                        self.logger.warning("session_manager.cleanup_unsubscribe_failed", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "error": str(e)
                        })

    async def start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        self._monitoring_task = asyncio.create_task(self._monitor_sessions())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def _monitor_sessions(self) -> None:
        """Monitor active sessions for health and timeouts"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                current_time = datetime.now()
                sessions_to_check = []

                async with self.session_lock:
                    sessions_to_check = list(self.active_sessions.values())

                for session in sessions_to_check:
                    # Check for inactivity timeout (5 minutes)
                    if (current_time - session.last_activity).total_seconds() > 300:
                        self.logger.warning("session_manager.session_inactive_timeout", {
                            "session_id": session.session_id,
                            "last_activity": session.last_activity.isoformat()
                        })
                        await self.stop_session(session.session_id, session.client_id)

                    # Publish session health metrics
                    await self.event_bus.publish("session.health", session.to_dict())

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("session_manager.monitoring_error", {
                    "error": str(e)
                })

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                current_time = datetime.now()
                expired_sessions = []

                async with self.session_lock:
                    for session_id, session in self.active_sessions.items():
                        # Expire sessions older than 24 hours
                        if (current_time - session.start_time).total_seconds() > 86400:
                            expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    self.logger.info("session_manager.session_expired", {
                        "session_id": session_id
                    })
                    await self._cleanup_session(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("session_manager.cleanup_error", {
                    "error": str(e)
                })

    async def start_paper_trading_session(
        self,
        strategy_config: Dict[str, Any],
        symbols: List[str],
        user_id: str
    ) -> str:
        """Start a paper trading session (alias for start_session with paper mode)"""
        return await self.start_session(
            session_id=f"paper_{user_id}_{int(time.time())}",
            client_id=user_id,
            symbols=symbols,
            mode="paper"
        )

    async def start_live_trading_session(
        self,
        strategy_config: Dict[str, Any],
        symbols: List[str],
        user_id: str
    ) -> str:
        """Start a live trading session (alias for start_session with live mode)"""
        return await self.start_session(
            session_id=f"live_{user_id}_{int(time.time())}",
            client_id=user_id,
            symbols=symbols,
            mode="live"
        )

    async def start_backtest_session(
        self,
        strategy_config: Dict[str, Any],
        symbols: List[str],
        user_id: str
    ) -> str:
        """Start a backtest session (alias for start_session with backtest mode)"""
        return await self.start_session(
            session_id=f"backtest_{user_id}_{int(time.time())}",
            client_id=user_id,
            symbols=symbols,
            mode="backtest"
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        async with self.session_lock:
            total_sessions = len(self.active_sessions)
            running_sessions = sum(
                1 for s in self.active_sessions.values()
                if s.state == SessionState.RUNNING
            )
            failed_sessions = sum(
                1 for s in self.active_sessions.values()
                if s.state == SessionState.FAILED
            )

        return {
            "total_sessions": total_sessions,
            "running_sessions": running_sessions,
            "failed_sessions": failed_sessions,
            "total_operations": self._total_operations,
            "total_failures": self._total_failures,
            "success_rate": (self._total_operations - self._total_failures) / max(self._total_operations, 1),
            "rate_limits": self.rate_limiter_config,
            "resource_limits": self.resource_limits
        }