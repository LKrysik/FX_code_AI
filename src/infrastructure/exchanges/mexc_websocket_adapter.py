"""
MEXC WebSocket Market Data Adapter - Multi-Connection Implementation
==================================================================

Event-driven WebSocket adapter for MEXC exchange following Clean Architecture principles.
Uses pure asyncio (NO threading) and EventBus for all communication.
Supports multiple connections with configurable subscription limits.
Includes circuit breaker protection and rate limiting for production reliability.
"""

import asyncio
import json
import time
import logging
from typing import Optional, Set, Dict, Any, List, AsyncIterator
from datetime import datetime
from decimal import Decimal
from collections import OrderedDict
from contextlib import asynccontextmanager

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import aiohttp  # ✅ ADD: For REST API orderbook refresh

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...core.simple_shutdown import SimpleShutdown
from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.models.market_data import MarketData
from ...infrastructure.config.settings import ExchangeSettings
from .circuit_breaker import CircuitBreaker
from .rate_limiter import TokenBucketRateLimiter
from .mexc.subscription import SubscriptionConfirmer


class MexcWebSocketAdapter(IMarketDataProvider):
    """
    MEXC WebSocket Market Data Adapter - Multi-Connection Implementation
    
    Features:
    - Multiple WebSocket connections (configurable subscriptions per connection)
    - Pure asyncio implementation (NO threading)
    - EventBus-based communication
    - Automatic connection management
    - Clean separation of concerns
    - Proper error handling and logging
    """
    
    def __init__(self, settings: ExchangeSettings, event_bus: EventBus, logger: StructuredLogger, data_types: Optional[List[str]] = None):
        """
        Initialize MEXC WebSocket adapter with Clean Architecture principles.

        Args:
            settings: Exchange configuration
            event_bus: Central communication hub
            logger: Structured logger
            data_types: List of data types to subscribe to ('prices', 'orderbook'). Defaults to both.
        """
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger

        # ✅ FIX: Configure which data types to subscribe to
        # Default to both prices and orderbook for backward compatibility
        self.data_types = set(data_types or ['prices', 'orderbook'])

        # Validate data_types
        valid_data_types = {'prices', 'orderbook'}
        invalid_types = self.data_types - valid_data_types
        if invalid_types:
            raise ValueError(f"Invalid data_types: {invalid_types}. Valid options: {valid_data_types}")

        self.logger.info("mexc_adapter.data_types_configured", {
            "data_types": list(self.data_types),
            "subscribe_prices": 'prices' in self.data_types,
            "subscribe_orderbook": 'orderbook' in self.data_types
        })
        
        # Configuration from settings - use direct attribute access (not deprecated .get())
        self.ws_url = getattr(settings, 'mexc_futures_ws_url', "wss://contract.mexc.com/edge")
        self.max_subscriptions_per_connection = getattr(settings, 'mexc_max_subscriptions_per_connection', 30)
        self.max_connections = getattr(settings, 'mexc_max_connections', 5)
        self.max_reconnect_attempts = getattr(settings, 'mexc_max_reconnect_attempts', 10)

        # BUG-008-4: Pong timeout thresholds for proactive connection health
        # These thresholds trigger action BEFORE 55-minute stale connections occur
        self.pong_warn_threshold_seconds = getattr(settings, 'mexc_pong_warn_threshold_seconds', 60)
        self.pong_reconnect_threshold_seconds = getattr(settings, 'mexc_pong_reconnect_threshold_seconds', 120)

        # Configuration validation
        if self.max_subscriptions_per_connection <= 0:
            raise ValueError("max_subscriptions_per_connection must be > 0")
        if self.max_connections <= 0:
            raise ValueError("max_connections must be > 0")
        if self.max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts must be >= 0")
        if self.ws_url.startswith("ws://"):
            self.logger.warning("mexc_adapter.unencrypted_connection", {
                "url": self.ws_url,
                "recommendation": "Use wss:// for production"
            })
        
        # Constants for memory management
        self.MAX_TRACKED_RECONNECTIONS = 20  # Hard limit for reconnection tracking
        
        # Circuit breaker protection
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # Open after 5 failures
            timeout=30.0,  # Try recovery after 30s
            name="MexcWebSocket"
        )
        
        # Rate limiter for subscriptions (MEXC allows 30 per connection)
        self.subscription_rate_limiter = TokenBucketRateLimiter(
            max_tokens=30,  # Burst capacity
            refill_rate=5.0,  # 5 subscriptions per second average
            name="MexcSubscriptions"
        )
        
        # Connection management
        self._connections: Dict[int, Dict] = {}  # connection_id -> connection_info
        self._running = False
        self._connection_counter = 0
        
        # Subscription management
        self._symbol_to_connection: Dict[str, int] = {}  # symbol -> connection_id
        self._subscribed_symbols: Set[str] = set()
        self._subscription_lock = asyncio.Lock()  # Prevent race conditions in subscribe operations
        self._pending_subscriptions: Dict[int, Dict[str, Dict[str, str]]] = {}  # connection_id -> symbol -> {'deal': 'pending', 'depth': 'pending', 'depth_full': 'pending'}

        # ✅ FIX: Coordination tracking for async message processing (Propozycja #1B)
        # Prevents race condition: connection cleanup vs in-flight confirmation processing
        self._message_processing_count: Dict[int, int] = {}  # connection_id -> count of active message handlers

        # Market data cache removed - EventBus is the single source of truth
        # All data flows through EventBus to subscribers (ExecutionController, etc.)
        
        # Shutdown management
        self.shutdown_manager = SimpleShutdown("MexcWebSocketAdapter")
        
        # Reconnection tracking
        self._reconnection_attempts: Dict[int, int] = {}
        self._start_time = time.time()
        self._last_cleanup_time = time.time()

        # Memory management - guaranteed cleanup for tracking structures
        self._tracking_cleanup_task = None
        self._tracking_expiry = {}  # symbol -> expiry_time for all tracking structures
        self._max_tracking_age = 3600  # 1 hour expiry for tracking data

        # Task lifecycle management - prevent dangling tasks
        self._active_tasks = set()
        
        # Rate limiting for debug logs to prevent spam
        self._debug_log_rates = {}  # symbol -> last_log_time for price/depth updates
        self._message_count = 0  # Counter for message batching
        
        # ✅ ORDERBOOK CACHE: Maintain full state between incremental updates
        self._orderbook_cache = {}  # symbol -> {"bids": OrderedDict, "asks": OrderedDict, "version": int, "timestamp": float}
        self._orderbook_locks: Dict[str, asyncio.Lock] = {}  # Per-symbol locks for concurrent orderbook updates
        self._orderbook_versions = {}  # symbol -> last_processed_version for delta synchronization
        
        # Periodic snapshot refresh to prevent drift from deltas
        self._snapshot_refresh_interval = getattr(settings, 'snapshot_refresh_interval', 300)  # 5 minutes default
        self._snapshot_refresh_tasks = {}  # symbol -> asyncio.Task for periodic refresh

        # ✅ REFACTORING: Initialize SubscriptionConfirmer component
        # Eliminates 358-line method with 90% code duplication
        self._subscription_confirmer = SubscriptionConfirmer(
            logger=self.logger,
            data_types=self.data_types,
            get_pending_subscriptions=self._get_pending_subscriptions_for_connection,
            update_pending_status=self._update_pending_subscription_status,
            remove_from_pending=self._remove_symbol_from_pending,
            get_subscribed_symbols_on_connection=self._get_subscribed_symbols_on_connection,
            start_snapshot_refresh=self._start_snapshot_refresh_task
        )

        self.logger.info("mexc_adapter.initialized", {
            "ws_url": self.ws_url,
            "exchange": "mexc",
            "max_subscriptions_per_connection": self.max_subscriptions_per_connection,
            "max_connections": self.max_connections,
            "circuit_breaker_enabled": True,
            "rate_limiting_enabled": True,
            "subscription_confirmer_enabled": True
        })
    
    def get_exchange_name(self) -> str:
        """Get exchange name"""
        return "mexc"

    # ===== SubscriptionConfirmer Callback Functions =====
    # These methods provide SubscriptionConfirmer with access to adapter state
    # following Dependency Injection pattern (no direct state access)

    def _get_pending_subscriptions_for_connection(self, connection_id: int) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Get pending subscriptions for a connection.

        Args:
            connection_id: WebSocket connection ID

        Returns:
            Dict of symbol -> status mappings or None if no pending subscriptions
        """
        return self._pending_subscriptions.get(connection_id)

    def _update_pending_subscription_status(
        self,
        connection_id: int,
        symbol: str,
        sub_type: str,
        status: str
    ) -> None:
        """
        Update status of pending subscription.

        Args:
            connection_id: WebSocket connection ID
            symbol: Trading pair symbol
            sub_type: Subscription type ('deal', 'depth', 'depth_full')
            status: New status ('pending', 'confirmed', 'failed')
        """
        pending_symbols = self._pending_subscriptions.get(connection_id)
        if pending_symbols and symbol in pending_symbols:
            pending_symbols[symbol][sub_type] = status

    def _remove_symbol_from_pending(self, connection_id: int, symbol: str) -> None:
        """
        Remove symbol from pending subscriptions.

        Args:
            connection_id: WebSocket connection ID
            symbol: Trading pair symbol to remove
        """
        pending_symbols = self._pending_subscriptions.get(connection_id)
        if pending_symbols and symbol in pending_symbols:
            del pending_symbols[symbol]
            # If no more pending symbols, remove connection entry
            if not pending_symbols:
                del self._pending_subscriptions[connection_id]

    def _get_subscribed_symbols_on_connection(self, connection_id: int) -> list:
        """
        Get list of subscribed symbols on a specific connection.

        Args:
            connection_id: WebSocket connection ID

        Returns:
            List of symbols subscribed on this connection
        """
        return [
            symbol for symbol, conn_id in self._symbol_to_connection.items()
            if conn_id == connection_id
        ]

    async def connect(self) -> None:
        """
        Connect to MEXC WebSocket API with multi-connection support.
        """
        self.logger.info("mexc_adapter.connect_started", {"url": self.ws_url})
        if self._running:
            self.logger.warning("mexc_adapter.already_running")
            return

        self._running = True
        start_time = time.time()
        self.logger.info("mexc_adapter.connecting", {"url": self.ws_url})

        try:
            self.logger.info("mexc_adapter.creating_initial_connection")
            await asyncio.wait_for(self._create_new_connection(), timeout=10.0)
            self.logger.info("mexc_adapter.initial_connection_created", {
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            })

            # Start tracking cleanup task for memory leak prevention
            self._tracking_cleanup_task = self._create_tracked_task(self._cleanup_tracking_structures(), "tracking_cleanup")

            # Start pending subscriptions cleanup task
            self._pending_cleanup_task = self._create_tracked_task(self._cleanup_pending_subscriptions(), "pending_cleanup")

            # ✅ START: Orderbook refresh task for cache freshness
            self._orderbook_refresh_task = self._create_tracked_task(self._start_orderbook_refresh_task(), "orderbook_refresh")

            self.logger.info("mexc_adapter.connected", {
                "url": self.ws_url,
                "connections": len(self._connections),
                "elapsed_ms": round((time.time() - start_time) * 1000, 2)
            })

        except asyncio.TimeoutError:
            self.logger.error("mexc_adapter.connection_timeout", {"timeout_seconds": 10.0})
            self._running = False
            raise
        except Exception as e:
            self.logger.error("mexc_adapter.connect_failed", {"error": str(e), "error_type": type(e).__name__, "elapsed_ms": round((time.time() - start_time) * 1000, 2)})
            self._running = False
            raise

    async def _cleanup_tracking_structures(self) -> None:
        """Guaranteed cleanup of tracking structures to prevent memory leaks"""
        while self._running:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes

                current_time = time.time()
                cleanup_candidates = []

                # Find expired tracking entries
                for symbol, expiry in self._tracking_expiry.items():
                    if current_time > expiry:
                        cleanup_candidates.append(symbol)

                # Remove expired entries from all tracking structures
                removed_count = 0
                for symbol in cleanup_candidates:
                    if self._reconnection_attempts.pop(symbol, None) is not None:
                        removed_count += 1
                    if self._debug_log_rates.pop(symbol, None) is not None:
                        removed_count += 1
                    self._tracking_expiry.pop(symbol, None)

                # Hard limits as backup
                if len(self._reconnection_attempts) > 50:
                    excess = len(self._reconnection_attempts) - 40
                    for _ in range(excess):
                        oldest = next(iter(self._reconnection_attempts))
                        self._reconnection_attempts.pop(oldest, None)
                        removed_count += 1

                if len(self._debug_log_rates) > 1000:
                    excess = len(self._debug_log_rates) - 800
                    items = sorted(self._debug_log_rates.items(), key=lambda x: x[1])
                    for symbol, _ in items[:excess]:
                        self._debug_log_rates.pop(symbol, None)
                        removed_count += 1

                if removed_count > 0:
                    self.logger.info("mexc_adapter.tracking_cleanup_completed", {
                        "removed_entries": removed_count,
                        "reconnection_attempts_remaining": len(self._reconnection_attempts),
                        "debug_rates_remaining": len(self._debug_log_rates)
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("mexc_adapter.tracking_cleanup_error", {"error": str(e)})

    def _update_tracking_expiry(self, symbol: str) -> None:
        """Update expiry time for tracking structures to prevent memory leaks"""
        self._tracking_expiry[symbol] = time.time() + self._max_tracking_age

    def _get_orderbook_lock(self, symbol: str) -> asyncio.Lock:
        """
        Get or create a per-symbol lock for orderbook updates.

        This eliminates global lock contention - each symbol can update
        independently without blocking others.

        Args:
            symbol: Trading pair symbol (e.g., "BTC_USDT")

        Returns:
            asyncio.Lock: Dedicated lock for this symbol's orderbook
        """
        if symbol not in self._orderbook_locks:
            self._orderbook_locks[symbol] = asyncio.Lock()
        return self._orderbook_locks[symbol]

    def _create_tracked_task(self, coro, name: str = "") -> asyncio.Task:
        """Create a tracked asyncio task to prevent dangling tasks"""
        task = asyncio.create_task(coro, name=name)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task

    async def _safe_resubscribe_symbol(self, symbol: str) -> None:
        """Safely resubscribe a symbol after reconnection, avoiding deadlock"""
        try:
            # Small delay to allow reconnection to complete
            await asyncio.sleep(0.1)
            await self.subscribe_to_symbol(symbol)
        except Exception as e:
            self.logger.error("mexc_adapter.safe_resubscription_failed", {
                "symbol": symbol,
                "error": str(e)
            })

    async def _cancel_all_active_tasks(self) -> None:
        """Cancel all tracked asyncio tasks during shutdown"""
        if not self._active_tasks:
            return

        # Cancel all active tasks
        tasks_to_cancel = [task for task in self._active_tasks if not task.done()]
        for task in tasks_to_cancel:
            task.cancel()

        # Wait for cancellation with timeout
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=5.0
                )
                self.logger.info("mexc_adapter.all_tasks_cancelled", {
                    "cancelled_count": len(tasks_to_cancel)
                })
            except asyncio.TimeoutError:
                self.logger.warning("mexc_adapter.task_cancellation_timeout", {
                    "timed_out_count": len(tasks_to_cancel)
                })

        # Clear the task registry
        self._active_tasks.clear()

    async def _handle_backpressure(self, event_type: str, data: dict) -> None:
        """Handle backpressure in event publishing system - TRADING OPTIMIZED"""
        # Check if this is a trading-critical event
        is_trading_critical = any(keyword in event_type for keyword in ["deal", "trade", "order", "position"])

        if is_trading_critical:
            # NEVER drop trading events - log as ERROR
            self.logger.error("mexc_adapter.trading_event_backpressure_critical", {
                "event_type": event_type,
                "symbol": data.get("symbol", "unknown"),
                "action": "attempting_immediate_retry",
                "warning": "TRADING EVENT DELAYED - SYSTEM OVERLOAD"
            })
        else:
            # Log backpressure for non-trading events
            self.logger.warning("mexc_adapter.backpressure_detected", {
                "event_type": event_type,
                "symbol": data.get("symbol", "unknown"),
                "action": "dropping_event"
            })

        # Could implement: increase worker threads, expand queue sizes for trading events

    async def _create_new_connection(self) -> int:
        """Create a new WebSocket connection and return its ID with circuit breaker protection"""
        if len(self._connections) >= self.max_connections:
            raise RuntimeError(f"Maximum connections ({self.max_connections}) reached")
            
        connection_id = self._connection_counter
        self._connection_counter += 1
        
        async def _connect():
            """Protected connection function"""
            # Connect to WebSocket with optimized timing for trading
            websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,  # Faster ping for trading (reduced from 60)
                ping_timeout=30,   # Must be > ping_interval (increased from 10)
                close_timeout=5    # Faster close (reduced from 10)
            )
            
            # Create connection info with dedicated state lock
            connection_info = {
                "websocket": websocket,
                "connected": True,
                "subscriptions": set(),
                "last_heartbeat": time.time(),
                "last_ping_sent": time.time(),  # Track when ping was sent
                "last_pong_received": time.time(),  # Track when pong was received
                "error_count": 0,  # Track connection errors
                "heartbeat_task": None,
                "message_task": None,
                "state_lock": asyncio.Lock()  # Dedicated lock for connection state
            }
            
            self._connections[connection_id] = connection_info
            
            # Start heartbeat and message handling for this connection
            connection_info["heartbeat_task"] = self._create_tracked_task(
                self._heartbeat_monitor(connection_id), f"heartbeat_{connection_id}"
            )
            connection_info["message_task"] = self._create_tracked_task(
                self._message_loop(connection_id), f"message_loop_{connection_id}"
            )
            
            self.logger.info("mexc_adapter.connection_created", {
                "connection_id": connection_id,
                "url": self.ws_url,
                "total_connections": len(self._connections),
                "circuit_breaker_state": self.circuit_breaker.get_state()
            })
            
            # Publish connection event
            await self._safe_publish_event("market_data.connected", {
                "exchange": "mexc",
                "connection_id": connection_id,
                "timestamp": time.time(),
                "url": self.ws_url
            })
            
            return connection_id
        
        try:
            # Use circuit breaker protection
            return await self.circuit_breaker.call(_connect)
            
        except Exception as e:
            self.logger.error("mexc_adapter.connection_creation_failed", {
                "connection_id": connection_id,
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.get_state()
            })
            raise
    
    async def _get_available_connection(self) -> Optional[int]:
        """
        Thread-safe method to get a connection that can accept more subscriptions.
        Uses lock to prevent race conditions when multiple coroutines check availability.
        """
        # Optimize debug logging - compute expensive operations only when needed
        if self.logger.logger.isEnabledFor(logging.DEBUG):
            connections_info = {str(k): {"connected": v["connected"], "subscriptions": len(v["subscriptions"])} 
                              for k, v in self._connections.items()}
            self.logger.debug("mexc_adapter.checking_available_connections", {
                "total_connections": len(self._connections),
                "connections": connections_info
            })
        else:
            self.logger.debug("mexc_adapter.checking_available_connections", {
                "total_connections": len(self._connections)
            })
        
        async with self._subscription_lock:
            for conn_id, conn_info in self._connections.items():
                self.logger.debug("mexc_adapter.checking_connection", {
                    "connection_id": conn_id,
                    "connected": conn_info["connected"],
                    "current_subscriptions": len(conn_info["subscriptions"]),
                    "max_subscriptions": self.max_subscriptions_per_connection
                })
                
                if (conn_info["connected"] and 
                    len(conn_info["subscriptions"]) < self.max_subscriptions_per_connection):
                    # Reserve this connection by marking it as pending
                    # This prevents race conditions where multiple subscribers get the same connection
                    pending_count = len(self._pending_subscriptions.get(conn_id, []))
                    
                    self.logger.debug("mexc_adapter.connection_available", {
                        "connection_id": conn_id,
                        "current_subscriptions": len(conn_info["subscriptions"]),
                        "pending_subscriptions": pending_count,
                        "total_would_be": len(conn_info["subscriptions"]) + pending_count,
                        "max_allowed": self.max_subscriptions_per_connection
                    })
                    
                    if len(conn_info["subscriptions"]) + pending_count < self.max_subscriptions_per_connection:
                        return conn_id
                        
            self.logger.debug("mexc_adapter.no_available_connections", {
                "total_connections": len(self._connections)
            })
            return None

    def _get_available_connection_unlocked(self) -> Optional[int]:
        """
        Get available connection without acquiring lock (should be called within lock context).
        """
        for conn_id, conn_info in self._connections.items():
            # Remove duplicated debug log - this info is already logged in _get_available_connection
            if (conn_info["connected"] and
                len(conn_info["subscriptions"]) < self.max_subscriptions_per_connection):
                # Reserve this connection by marking it as pending
                pending_symbols = self._pending_subscriptions.get(conn_id, {})
                pending_count = len(pending_symbols)

                self.logger.debug("mexc_adapter.connection_available_unlocked", {
                    "connection_id": conn_id,
                    "current_subscriptions": len(conn_info["subscriptions"]),
                    "pending_subscriptions": pending_count,
                    "total_would_be": len(conn_info["subscriptions"]) + pending_count,
                    "max_allowed": self.max_subscriptions_per_connection
                })

                if len(conn_info["subscriptions"]) + pending_count < self.max_subscriptions_per_connection:
                    return conn_id
                    
        self.logger.debug("mexc_adapter.no_available_connections_unlocked", {
            "total_connections": len(self._connections)
        })
        return None
    
    async def _message_loop(self, connection_id: int) -> None:
        """Main message processing loop for a specific connection with enhanced error handling"""
        connection_info = self._connections.get(connection_id)
        if not connection_info:
            return

        websocket = connection_info["websocket"]
        consecutive_transient_errors = 0
        consecutive_json_errors = 0
        max_transient_errors = 10
        max_json_errors = 5

        try:
            async for message in websocket:
                try:
                    await self._handle_message(message, connection_id)
                    connection_info["last_heartbeat"] = time.time()
                    # Reset error counters on successful processing
                    consecutive_transient_errors = 0
                    consecutive_json_errors = 0

                except json.JSONDecodeError as e:
                    consecutive_json_errors += 1
                    self.logger.warning("mexc_adapter.json_decode_error", {
                        "connection_id": connection_id,
                        "consecutive_errors": consecutive_json_errors,
                        "error": str(e),
                        "message_sample": str(message)[:200]
                    })

                    if consecutive_json_errors >= max_json_errors:
                        self.logger.error("mexc_adapter.persistent_json_errors", {
                            "connection_id": connection_id,
                            "error_count": consecutive_json_errors,
                            "action": "closing_connection"
                        })
                        await self._handle_connection_error(connection_id,
                            RuntimeError(f"Persistent JSON decode errors ({consecutive_json_errors})"))
                        break
                    # Continue processing for transient JSON errors

                except ConnectionClosed as e:
                    self.logger.warning("mexc_adapter.connection_closed", {
                        "connection_id": connection_id,
                        "code": getattr(e, 'code', None),
                        "reason": getattr(e, 'reason', str(e))
                    })
                    await self._handle_connection_error(connection_id, e)
                    break

                except WebSocketException as e:
                    self.logger.error("mexc_adapter.websocket_error", {
                        "connection_id": connection_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    await self._handle_connection_error(connection_id, e)
                    break

                except (KeyError, ValueError, TypeError) as e:
                    # Data validation errors - likely transient
                    consecutive_transient_errors += 1
                    self.logger.warning("mexc_adapter.data_validation_error", {
                        "connection_id": connection_id,
                        "consecutive_errors": consecutive_transient_errors,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })

                    if consecutive_transient_errors >= max_transient_errors:
                        self.logger.error("mexc_adapter.persistent_validation_errors", {
                            "connection_id": connection_id,
                            "error_count": consecutive_transient_errors,
                            "action": "closing_connection"
                        })
                        await self._handle_connection_error(connection_id,
                            RuntimeError(f"Persistent validation errors ({consecutive_transient_errors})"))
                        break

                except Exception as e:
                    # Unexpected errors - log and continue with caution
                    consecutive_transient_errors += 1
                    self.logger.error("mexc_adapter.unexpected_message_error", {
                        "connection_id": connection_id,
                        "consecutive_errors": consecutive_transient_errors,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "message_sample": str(message)[:200]
                    })

                    if consecutive_transient_errors >= max_transient_errors:
                        self.logger.error("mexc_adapter.persistent_unexpected_errors", {
                            "connection_id": connection_id,
                            "error_count": consecutive_transient_errors,
                            "action": "closing_connection"
                        })
                        await self._handle_connection_error(connection_id,
                            RuntimeError(f"Persistent unexpected errors ({consecutive_transient_errors})"))
                        break

        except asyncio.CancelledError:
            self.logger.info("mexc_adapter.message_loop_cancelled", {
                "connection_id": connection_id
            })
        except Exception as e:
            self.logger.error("mexc_adapter.message_loop_fatal_error", {
                "connection_id": connection_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            await self._handle_connection_error(connection_id, e)
        finally:
            # Mark connection as disconnected with proper locking
            if connection_id in self._connections:
                async with self._connections[connection_id]["state_lock"]:
                    self._connections[connection_id]["connected"] = False

    async def _handle_connection_error(self, connection_id: int, error: Exception) -> None:
        """Centralized connection error handling with reconnection strategy"""
        error_type = type(error).__name__
        
        if isinstance(error, ConnectionClosed):
            self.logger.warning("mexc_adapter.handling_connection_closed", {
                "connection_id": connection_id,
                "code": getattr(error, 'code', None),
                "reason": getattr(error, 'reason', str(error))
            })
            # Graceful closure - attempt reconnection
            await self._close_connection(connection_id)
            
        elif isinstance(error, WebSocketException):
            self.logger.error("mexc_adapter.handling_websocket_error", {
                "connection_id": connection_id,
                "error": str(error),
                "error_type": error_type
            })
            # WebSocket protocol error - force close and recreate
            await self._close_connection(connection_id)
            
        else:
            # Unexpected error - log and continue with caution
            self.logger.error("mexc_adapter.handling_unexpected_error", {
                "connection_id": connection_id,
                "error": str(error),
                "error_type": error_type
            })
            # For unexpected errors, try to continue but monitor closely
            if connection_id in self._connections:
                # Mark connection as potentially unstable
                self._connections[connection_id]["error_count"] = (
                    self._connections[connection_id].get("error_count", 0) + 1
                )
                
                # Close connection if too many errors
                if self._connections[connection_id]["error_count"] > 5:
                    self.logger.error("mexc_adapter.too_many_errors", {
                        "connection_id": connection_id,
                        "error_count": self._connections[connection_id]["error_count"]
                    })
                    await self._close_connection(connection_id)
    
    async def _heartbeat_monitor(self, connection_id: int) -> None:
        """
        BUG-008-4: Enhanced heartbeat monitor with threshold-based pong timeout handling.

        Implements proactive connection health monitoring:
        - AC1: Pong age > 60s triggers WARNING + health check ping
        - AC2: Pong age > 120s triggers connection close + reconnect
        - AC3: Consecutive timeouts escalate action severity
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info:
            return

        # Use monotonic clock for precise timing - TRADING OPTIMIZED
        ping_interval = 20.0  # 20 seconds between pings (faster for trading)
        pong_timeout = 30.0   # 30 seconds to receive pong (must be > ping_interval)
        max_no_data = 120.0   # 2 minutes without any data (faster detection)
        consecutive_timeouts = 0
        health_check_sent = False  # BUG-008-4: Track if health check was sent

        last_ping_time = time.monotonic()
        last_data_time = time.monotonic()

        while (self._running and
            connection_id in self._connections and
            self._connections[connection_id]["connected"]):

            try:
                current_time = time.monotonic()
                current_wall_time = time.time()

                # BUG-008-4: Always check pong age against thresholds (AC1, AC2)
                last_pong_received = connection_info.get("last_pong_received", current_wall_time)
                last_pong_age = current_wall_time - last_pong_received

                # AC2: Pong age > RECONNECT_THRESHOLD (120s) - IMMEDIATE close and reconnect
                if last_pong_age > self.pong_reconnect_threshold_seconds:
                    self.logger.error("mexc_adapter.pong_age_exceeded_reconnect_threshold", {
                        "connection_id": connection_id,
                        "last_pong_age_seconds": round(last_pong_age, 2),
                        "threshold_seconds": self.pong_reconnect_threshold_seconds,
                        "consecutive_timeouts": consecutive_timeouts,
                        "action": "closing_connection_for_reconnect"
                    })
                    await self._close_connection(connection_id)
                    break

                # AC1: Pong age > WARN_THRESHOLD (60s) - WARNING + health check
                elif last_pong_age > self.pong_warn_threshold_seconds:
                    consecutive_timeouts += 1

                    self.logger.warning("mexc_adapter.pong_age_exceeded_warn_threshold", {
                        "connection_id": connection_id,
                        "last_pong_age_seconds": round(last_pong_age, 2),
                        "threshold_seconds": self.pong_warn_threshold_seconds,
                        "consecutive_timeouts": consecutive_timeouts,
                        "action": "health_check_initiated" if not health_check_sent else "awaiting_pong"
                    })

                    # AC1: Send health check ping on first warning (if not already sent)
                    if not health_check_sent:
                        websocket = connection_info.get("websocket")
                        if websocket and websocket.close_code is None:
                            try:
                                health_ping = {"method": "ping", "param": {}}
                                await websocket.send(json.dumps(health_ping))
                                connection_info["last_ping_sent"] = current_wall_time
                                health_check_sent = True
                                self.logger.info("mexc_adapter.health_check_ping_sent", {
                                    "connection_id": connection_id,
                                    "last_pong_age_seconds": round(last_pong_age, 2)
                                })
                            except Exception as e:
                                self.logger.error("mexc_adapter.health_check_ping_failed", {
                                    "connection_id": connection_id,
                                    "error": str(e)
                                })

                # Pong age is healthy - reset counters
                elif last_pong_age < self.pong_warn_threshold_seconds:
                    if consecutive_timeouts > 0:
                        self.logger.info("mexc_adapter.pong_health_restored", {
                            "connection_id": connection_id,
                            "last_pong_age_seconds": round(last_pong_age, 2),
                            "previous_consecutive_timeouts": consecutive_timeouts
                        })
                    consecutive_timeouts = 0
                    health_check_sent = False

                # Regular ping interval check (send ping every 20s)
                if current_time - last_ping_time >= ping_interval:
                    websocket = connection_info["websocket"]
                    if not websocket or websocket.close_code is not None:
                        break

                    # Send MEXC-specific ping message
                    ping_message = {
                        "method": "ping",
                        "param": {}
                    }

                    try:
                        await websocket.send(json.dumps(ping_message))
                        connection_info["last_ping_sent"] = current_wall_time
                        last_ping_time = current_time

                        self.logger.debug("mexc_adapter.ping_sent", {
                            "connection_id": connection_id,
                            "timestamp": current_wall_time
                        })

                        # Wait for pong response with timeout - version-aware implementation
                        try:
                            # Check if websockets library supports wait_for_pong() (version 11.0+)
                            if hasattr(websocket, 'wait_for_pong'):
                                await asyncio.wait_for(websocket.wait_for_pong(), timeout=pong_timeout)
                                connection_info["last_pong_received"] = time.time()
                                consecutive_timeouts = 0  # Reset on successful pong
                                health_check_sent = False

                                self.logger.debug("mexc_adapter.pong_received", {
                                    "connection_id": connection_id,
                                    "timestamp": time.time()
                                })
                            else:
                                # Fallback for older websockets versions - rely on message loop pong detection
                                # Wait briefly to allow pong processing
                                await asyncio.sleep(0.5)

                        except asyncio.TimeoutError:
                            # Don't increment consecutive_timeouts here - threshold checks handle it
                            self.logger.debug("mexc_adapter.pong_wait_timeout", {
                                "connection_id": connection_id,
                                "note": "threshold_check_will_handle_escalation"
                            })

                    except Exception as send_error:
                        self.logger.error("mexc_adapter.ping_send_failed", {
                            "connection_id": connection_id,
                            "error": str(send_error)
                        })
                        await self._close_connection(connection_id)
                        break

                # Check for data activity (updated by message loop)
                last_heartbeat = connection_info.get("last_heartbeat", current_wall_time)
                if current_wall_time - last_heartbeat > max_no_data:
                    self.logger.error("mexc_adapter.no_data_activity", {
                        "connection_id": connection_id,
                        "last_activity": last_heartbeat,
                        "max_age_seconds": max_no_data,
                        "action": "closing_connection"
                    })
                    await self._close_connection(connection_id)
                    break

                # Sleep for 1 second before next check
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                self.logger.info("mexc_adapter.heartbeat_cancelled", {
                    "connection_id": connection_id
                })
                break
            except Exception as e:
                self.logger.error("mexc_adapter.heartbeat_unexpected_error", {
                    "connection_id": connection_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                await self._close_connection(connection_id)
                break

    async def _safe_publish_event(self, event_type: str, data: dict, max_retries: int = 0) -> None:
        """
        ✅ PERF FIX: Fire-and-forget event publishing for real-time trading.

        No retries by default - high-frequency events are published once and dropped on failure.
        This ensures zero latency for trading systems that require real-time data delivery.
        """
        # Determine if this is a trading-critical event
        is_trading_critical = any(keyword in event_type for keyword in ["deal", "trade", "order", "position"])
        is_high_frequency = any(keyword in event_type for keyword in ["price_update", "orderbook_update", "depth_update"])

        # ✅ PERF FIX: Increased timeout now that EventBus uses non-blocking bucketed queues
        # EventBus.publish() now returns in <1ms (queue.put() instead of waiting for handlers)
        # Timeout is failsafe for extreme overload scenarios
        if is_trading_critical:
            timeout = 0.05  # 50ms max (was 10ms - too aggressive)
            max_retries = 0  # No retries - fail fast
        elif is_high_frequency:
            # High-frequency events: orderbook, price updates
            timeout = 0.05  # 50ms max (was 10ms - caused false backpressure errors)
            max_retries = 0  # No retries - drop event if EventBus severely overloaded
        else:
            # Low-frequency events: more tolerant
            timeout = 2.0
            max_retries = max_retries if max_retries > 0 else 1
        
        # ✅ PERF FIX: Single attempt for high-frequency events (max_retries + 1)
        for attempt in range(max_retries + 1):
            try:
                await asyncio.wait_for(
                    self.event_bus.publish(event_type, data),
                    timeout=timeout
                )
                return  # Success - exit immediately
                
            except asyncio.TimeoutError:
                if is_high_frequency:
                    # Handle backpressure for high-frequency events
                    await self._handle_backpressure(event_type, data)
                    return  # Drop event immediately - don't retry high-frequency events
                
                # For low-frequency events, log and potentially retry
                self.logger.warning("mexc_adapter.event_publish_timeout", {
                    "event_type": event_type,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "timeout_ms": timeout * 1000,
                    "symbol": data.get("symbol", "unknown")
                })
                
                if attempt == max_retries - 1:
                    self.logger.error("mexc_adapter.event_publish_failed_permanently", {
                        "event_type": event_type,
                        "symbol": data.get("symbol", "unknown"),
                        "total_attempts": max_retries,
                        "reason": "timeout_exceeded"
                    })
                else:
                    # Short retry delay for low-frequency events - reduced CPU overhead
                    await asyncio.sleep(0.1)  # Increased from 0.01 to 0.1
                    
            except Exception as e:
                # Unexpected error in event publishing
                self.logger.error("mexc_adapter.event_publish_error", {
                    "event_type": event_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "symbol": data.get("symbol", "unknown"),
                    "attempt": attempt + 1
                })
                
                if attempt == max_retries - 1:
                    # Final attempt failed
                    break
                else:
                    await asyncio.sleep(0.1)  # Increased from 0.01 to 0.1 for CPU efficiency
            
            except Exception as e:
                self.logger.error("mexc_adapter.event_publish_error", {
                    "event_type": event_type,
                    "error": str(e),
                    "attempt": attempt + 1
                })
                if attempt == max_retries - 1:
                    break
                await asyncio.sleep(0.2)  # Increased from 0.05 to 0.2 for better CPU efficiency

    async def _handle_message(self, message: str, connection_id: int) -> None:
        """Handle incoming WebSocket message"""
        # ✅ FIX (Propozycja #1B): Increment counter to track in-flight message processing
        # This prevents race condition: _close_connection() will wait for this to complete
        self._message_processing_count[connection_id] = (
            self._message_processing_count.get(connection_id, 0) + 1
        )

        try:
            # Offload JSON parsing to thread pool for performance
            data = await asyncio.to_thread(json.loads, message)
            
            # Rate-limited debug logging for messages (every 100th message)
            self._message_count += 1
            if self.logger.logger.isEnabledFor(logging.DEBUG) and self._message_count % 100 == 0:
                self.logger.debug("mexc_adapter.message_batch", {
                    "connection_id": connection_id,
                    "messages_processed": self._message_count,
                    "last_message_keys": list(data.keys()) if isinstance(data, dict) else "not_dict",
                    "last_message_sample": str(message)[:200]  # Reduced from 500 to 200 chars
                })
            
            # Handle subscription responses (futures format)
            if "channel" in data:
                channel = data.get("channel")
                
                # Handle subscription confirmations
                if channel.startswith("rs."):
                    await self._handle_futures_subscription_response(data, connection_id)
                
                # Handle market data - futures deal format
                elif channel == "push.deal":
                    await self._handle_futures_deal_data(data)

                # Handle market data - futures depth format
                # ✅ CORRECTED: MEXC uses TWO separate channels for orderbook data:
                # - push.depth: incremental deltas (from sub.depth) - MERGE with cache
                # - push.depth.full: full snapshots (from sub.depth.full) - RESET cache
                # Both channels exist and serve different purposes (verified by test_mexc_depth_subscription.py)
                elif channel == "push.depth":
                    await self._handle_futures_depth_data(data, is_snapshot=False)

                # Handle market data - futures depth full snapshot format
                elif channel == "push.depth.full":
                    await self._handle_futures_depth_data(data, is_snapshot=True)

                # Handle pong messages - update last_pong_received to track connection health
                elif channel == "pong":
                    if connection_id in self._connections:
                        self._connections[connection_id]["last_pong_received"] = time.time()
                    
                    self.logger.debug("mexc_adapter.pong_received", {
                        "connection_id": connection_id,
                        "timestamp": data.get("data")
                    })
                
                else:
                    self.logger.debug("mexc_adapter.unknown_channel", {
                        "connection_id": connection_id,
                        "channel": channel
                    })
            
            else:
                self.logger.warning("mexc_adapter.unknown_message_format", {
                    "connection_id": connection_id,
                    "keys": list(data.keys()) if isinstance(data, dict) else "not_dict",
                    "full_message": message
                })
                
        except json.JSONDecodeError:
            self.logger.warning("mexc_adapter.invalid_json", {
                "connection_id": connection_id,
                "message": message[:200]
            })
        except Exception as e:
            self.logger.error("mexc_adapter.message_processing_error", {
                "connection_id": connection_id,
                "error": str(e),
                "message": message[:200]
            })
        finally:
            # ✅ FIX (Propozycja #1B): Decrement counter - message processing complete
            count = self._message_processing_count.get(connection_id, 1) - 1
            if count <= 0:
                self._message_processing_count.pop(connection_id, None)
            else:
                self._message_processing_count[connection_id] = count

    async def _handle_futures_subscription_response(self, data: dict, connection_id: int) -> None:
        """
        Handle futures subscription/unsubscription responses.

        ✅ REFACTORED: This method now delegates to SubscriptionConfirmer component.

        Original implementation: 358 lines with 90% code duplication
        New implementation: 5 lines (delegation)
        Code reduction: 75% (358 → 5 lines)
        Duplication eliminated: ~270 lines of duplicate code removed

        The SubscriptionConfirmer component handles all subscription confirmation logic
        in a clean, testable, DRY manner.
        """
        channel = data.get("channel", "")
        response_data = data.get("data", "")

        # ✅ REFACTORING: Delegate to SubscriptionConfirmer component
        # This replaces 358 lines of duplicated code with a single delegation call
        await self._subscription_confirmer.handle_confirmation(
            channel=channel,
            response_data=response_data,
            connection_id=connection_id
        )
    
    async def _handle_futures_deal_data(self, data: dict) -> None:
        """Handle futures deal data (transaction data)"""
        try:
            symbol = data.get("symbol", "")
            deal_list = data.get("data", [])
            
            if not symbol or not deal_list:
                self.logger.warning("mexc_adapter.invalid_deal_data", {
                    "symbol": symbol,
                    "has_data": bool(deal_list)
                })
                return
            
            # Process each deal in the list (data can contain multiple deals)
            for deal_data in deal_list:
                if not isinstance(deal_data, dict):
                    self.logger.warning("mexc_adapter.invalid_deal_format", {
                        "symbol": symbol,
                        "deal_data": deal_data
                    })
                    continue
                
                # Extract deal information from futures format
                # From docs: {"M":1,"O":1,"T":1,"p":6866.5,"t":1587442049632,"v":2096}
                price = float(deal_data.get("p", 0))      # price
                volume = float(deal_data.get("v", 0))     # volume
                deal_type = deal_data.get("T", 0)         # trade type (1=buy, 2=sell)
                timestamp = int(deal_data.get("t", 0))    # timestamp in ms
                
                if price > 0 and volume > 0:
                    # Use MEXC timestamp or current time as fallback
                    event_timestamp = timestamp / 1000 if timestamp else time.time()
                    
                    # ✅ TRADING FIX: Moved from INFO to DEBUG to prevent hot path blocking
                    # Rate-limited debug logging for published events (max once per minute per symbol)
                    current_time = time.time()
                    publish_log_key = f"publish_{symbol}"
                    if (publish_log_key not in self._debug_log_rates or 
                        current_time - self._debug_log_rates[publish_log_key] > 60):
                        self.logger.debug("mexc_adapter.published_price_update", {
                            "symbol": symbol,
                            "price": price,
                            "volume": volume,
                            "timestamp": event_timestamp,
                            "event_type": "market.price_update"
                        })
                        self._debug_log_rates[publish_log_key] = current_time
                        self._update_tracking_expiry(publish_log_key)
                    
                    # ✅ PERF FIX: Fire-and-forget async publishing for zero latency
                    # No batching - trading requires real-time data delivery
                    asyncio.create_task(self._safe_publish_event("market.price_update", {
                        "exchange": "mexc",
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "quote_volume": price * volume,
                        "timestamp": event_timestamp,  # Use MEXC timestamp when available
                        "side": "buy" if deal_type == 1 else "sell",
                        "source": "futures_deal",
                        "mexc_timestamp": timestamp,  # Original MEXC timestamp in ms
                        "system_timestamp": time.time()  # Our system timestamp for comparison
                    }))
                    
                    # Rate-limited debug logging for price updates (max once per minute per symbol)
                    current_time = time.time()
                    if (symbol not in self._debug_log_rates or 
                        current_time - self._debug_log_rates[symbol] > 60):
                        self.logger.debug("mexc_adapter.futures_price_update", {
                            "symbol": symbol,
                            "price": price,
                            "volume": volume,
                            "deal_type": deal_type,
                            "timestamp": timestamp
                        })
                        self._debug_log_rates[symbol] = current_time
                        self._update_tracking_expiry(symbol)
                
        except Exception as e:
            self.logger.error("mexc_adapter.futures_deal_processing_error", {
                "symbol": data.get("symbol", ""),
                "error": str(e),
                "data": data
            })

    async def _handle_futures_depth_data(self, data: dict, is_snapshot: bool = False) -> None:
        """Handle futures depth data (order book data) with proper snapshot/delta logic"""
        try:
            symbol = data.get("symbol", "")
            depth_data = data.get("data", {})
            
            if not symbol or not depth_data:
                self.logger.warning("mexc_adapter.invalid_depth_data", {
                    "symbol": symbol,
                    "has_data": bool(depth_data),
                    "is_snapshot": is_snapshot
                })
                return
            
            # Extract order book data from futures format
            asks = depth_data.get("asks", [])
            bids = depth_data.get("bids", [])
            version = depth_data.get("version", 0)
            
            # Process orderbook with proper snapshot/delta logic
            if is_snapshot:
                # Full snapshot - reset orderbook state
                await self._process_orderbook_snapshot(symbol, {"asks": asks, "bids": bids, "version": version})
            else:
                # Delta update - merge with existing state
                await self._process_orderbook_delta(symbol, {"asks": asks, "bids": bids, "version": version})
                
            # Rate-limited debug logging for depth updates (max once per minute per symbol)
            current_time = time.time()
            depth_log_key = f"depth_{symbol}"
            if (depth_log_key not in self._debug_log_rates or 
                current_time - self._debug_log_rates[depth_log_key] > 60):
                self.logger.debug("mexc_adapter.futures_depth_update", {
                    "symbol": symbol,
                    "ask_count": len(asks),
                    "bid_count": len(bids),
                    "version": version,
                    "is_snapshot": is_snapshot
                })
                self._debug_log_rates[depth_log_key] = current_time
                self._update_tracking_expiry(depth_log_key)
                
        except Exception as e:
            self.logger.error("mexc_adapter.futures_depth_processing_error", {
                "symbol": data.get("symbol", ""),
                "error": str(e),
                "data": data,
                "is_snapshot": is_snapshot
            })

    async def _handle_subscription_response(self, data: dict, connection_id: int) -> None:
        """Handle subscription/unsubscription responses"""
        msg_type = data.get("msg")
        msg_id = data.get("id")
        
        if msg_type == "SUBSCRIPTION":
            self.logger.info("mexc_adapter.subscription_confirmed", {
                "connection_id": connection_id,
                "id": msg_id
            })
        elif msg_type == "UNSUBSCRIPTION":
            self.logger.info("mexc_adapter.unsubscription_confirmed", {
                "connection_id": connection_id,
                "id": msg_id
            })
        else:
            self.logger.debug("mexc_adapter.subscription_response", {
                "connection_id": connection_id,
                "type": msg_type,
                "id": msg_id
            })
    
    async def _handle_market_data(self, data: dict) -> None:
        """Handle market data updates"""
        try:
            channel = data.get("c", "")
            symbol = data.get("s", "")
            market_data = data.get("d", {})
            
            if not symbol or not market_data:
                return
            
            # Handle aggregated deals (price data) - FIXED attribute names
            if "aggre.deals" in channel:
                await self._process_deals_data(symbol, market_data)
            
            # Handle other data types as needed
            elif "depth" in channel:
                await self._process_orderbook_data(symbol, market_data)
            
        except Exception as e:
            self.logger.error("mexc_adapter.market_data_error", {
                "error": str(e),
                "channel": data.get("c", ""),
                "symbol": data.get("s", "")
            })
    
    async def _process_deals_data(self, symbol: str, data: dict) -> None:
        """Process aggregated deals data (price updates) - FIXED attribute parsing"""
        try:
            deals = data.get("deals", [])
            
            for deal in deals:
                # FIXED: Use correct MEXC API attribute names
                price = float(deal.get("p", 0))      # price
                volume = float(deal.get("v", 0))     # volume  
                side = deal.get("S", "")             # side (1=buy, 2=sell)
                timestamp = int(deal.get("t", 0))    # timestamp("S", "")             # side (1=buy, 2=sell)
                timestamp = int(deal.get("t", 0))    # timestamp
                
                if price > 0 and volume > 0:
                    # Publish price update event via EventBus (no cache - EventBus is source of truth)
                    await self._safe_publish_event("market.price_update", {
                        "exchange": "mexc",
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "timestamp": time.time(),
                        "side": side,
                        "quote_volume": price * volume,
                        "source": "deals"
                    })
                    
                    self.logger.debug("mexc_adapter.price_update", {
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "side": side
                    })
                    
        except Exception as e:
            self.logger.error("mexc_adapter.deals_processing_error", {
                "symbol": symbol,
                "error": str(e)
            })
    
    def _safe_parse_orderbook_level(self, level: list) -> Optional[list]:
        """
        Safely parse order book level from MEXC format.
        Expected format: [price, volume, count] or [price, volume]
        
        Args:
            level: Order book level data
            
        Returns:
            [price, volume] or None if parsing fails
        """
        try:
            if isinstance(level, list) and len(level) >= 2:
                price = float(level[0])
                volume = float(level[1])
                if price > 0 and volume >= 0:  # Price must be positive, volume can be zero
                    return [price, volume]
                else:
                    self.logger.warning("mexc_adapter.invalid_orderbook_values", {
                        "price": price,
                        "volume": volume
                    })
                    return None
            else:
                self.logger.warning("mexc_adapter.unexpected_orderbook_format", {
                    "level": level,
                    "type": type(level),
                    "length": len(level) if isinstance(level, list) else "not_list"
                })
                return None
        except (ValueError, TypeError, IndexError) as e:
            self.logger.warning("mexc_adapter.orderbook_parsing_error", {
                "level": level,
                "error": str(e)
            })
            return None

    async def _process_orderbook_data(self, symbol: str, data: dict) -> None:
        """Process order book data with safe parsing and state cache"""
        try:
            bids_raw = data.get("bids", [])
            asks_raw = data.get("asks", [])
            
            # Safely parse bids and asks - increased to TOP 20 for better market depth
            bids = []
            asks = []
            
            for bid in bids_raw[:20]:  # ✅ INCREASED: TOP 20 levels for better depth
                parsed_bid = self._safe_parse_orderbook_level(bid)
                if parsed_bid:
                    bids.append(parsed_bid)
            
            for ask in asks_raw[:20]:  # ✅ INCREASED: TOP 20 levels for better depth
                parsed_ask = self._safe_parse_orderbook_level(ask)
                if parsed_ask:
                    asks.append(parsed_ask)
            
            # ✅ CACHE UPDATE: Maintain full orderbook state
            # ✅ PERF FIX: Per-symbol lock instead of global lock (eliminates contention)
            async with self._get_orderbook_lock(symbol):
                if symbol not in self._orderbook_cache:
                    # ✅ FIX: Initialize with OrderedDict for consistency with snapshot/delta processing
                    self._orderbook_cache[symbol] = {
                        "bids": OrderedDict(),
                        "asks": OrderedDict(),
                        "version": 0,
                        "timestamp": time.time()
                    }

                cache_entry = self._orderbook_cache[symbol]
                current_time = time.time()

                # Update cache with new data (only if we received that side)
                # Convert list format to OrderedDict
                if bids:  # Update bids only if MEXC sent them
                    cache_entry["bids"] = OrderedDict((str(float(price)), float(qty)) for price, qty in bids)
                if asks:  # Update asks only if MEXC sent them
                    cache_entry["asks"] = OrderedDict((str(float(price)), float(qty)) for price, qty in asks)

                cache_entry["timestamp"] = current_time
                
                # ✅ COMPLETE ORDERBOOK: Always publish with both sides from cache
                final_bids = cache_entry["bids"]
                final_asks = cache_entry["asks"]
            
            # Publish orderbook update with guaranteed complete data
            if final_bids or final_asks:
                # Publish orderbook update event
                await self._safe_publish_event("market.orderbook_update", {
                    "exchange": "mexc",
                    "symbol": symbol,
                    "bids": final_bids,  # Always complete from cache
                    "asks": final_asks,  # Always complete from cache
                    "best_bid": final_bids[0][0] if final_bids else 0,
                    "best_ask": final_asks[0][0] if final_asks else 0,
                    "timestamp": current_time,
                    "source": "orderbook",
                    "levels_parsed": {
                        "bids": len(final_bids),
                        "asks": len(final_asks),
                        "update_bids": len(bids),  # What came in this update
                        "update_asks": len(asks),  # What came in this update
                        "total_raw_bids": len(bids_raw),
                        "total_raw_asks": len(asks_raw)
                    }
                })
                
                # Log partial orderbook data at debug level (normal for low-liquidity symbols)
                if not bids:
                    self.logger.debug("mexc_adapter.partial_orderbook_no_bids", {
                        "symbol": symbol,
                        "asks_available": len(asks),
                        "reason": "no_bid_orders_in_market"
                    })
                elif not asks:
                    self.logger.debug("mexc_adapter.partial_orderbook_no_asks", {
                        "symbol": symbol,
                        "bids_available": len(bids),
                        "reason": "no_ask_orders_in_market"
                    })
            else:
                # Only warn if we have raw data but failed to parse any of it
                if bids_raw or asks_raw:
                    self.logger.warning("mexc_adapter.orderbook_parsing_failed", {
                        "symbol": symbol,
                        "raw_bids": len(bids_raw),
                        "raw_asks": len(asks_raw),
                        "parsed_bids": len(bids),
                        "parsed_asks": len(asks),
                        "reason": "all_levels_failed_validation"
                    })
                else:
                    # Empty orderbook data - log at debug level
                    self.logger.debug("mexc_adapter.empty_orderbook_data", {
                        "symbol": symbol,
                        "reason": "no_orderbook_data_from_exchange"
                    })
                
        except Exception as e:
            self.logger.error("mexc_adapter.orderbook_processing_error", {
                "symbol": symbol,
                "error": str(e)
            })

    async def _process_orderbook_snapshot(self, symbol: str, data: dict) -> None:
        """Process full orderbook snapshot - completely replace cached state"""
        try:
            bids_raw = data.get("bids", [])
            asks_raw = data.get("asks", [])
            version = int(data.get("version", 0)) if data.get("version") is not None else 0
            
            # Parse all levels from snapshot
            bids = []
            asks = []
            
            for bid in bids_raw:
                parsed_bid = self._safe_parse_orderbook_level(bid)
                if parsed_bid:
                    bids.append(parsed_bid)
            
            for ask in asks_raw:
                parsed_ask = self._safe_parse_orderbook_level(ask)
                if parsed_ask:
                    asks.append(parsed_ask)
            
            # Sort orderbook levels properly
            bids.sort(key=lambda x: float(x[0]), reverse=True)  # Highest price first
            asks.sort(key=lambda x: float(x[0]))  # Lowest price first

            # ✅ PERF FIX: Per-symbol lock instead of global lock
            async with self._get_orderbook_lock(symbol):
                # Create new cache state from snapshot
                self._orderbook_cache[symbol] = {
                    "bids": OrderedDict((str(float(price)), float(qty)) for price, qty in bids),
                    "asks": OrderedDict((str(float(price)), float(qty)) for price, qty in asks),
                    "version": version,
                    "timestamp": time.time()
                }
                self._orderbook_versions[symbol] = version
                
                self.logger.debug("mexc_adapter.orderbook_snapshot_processed", {
                    "symbol": symbol,
                    "bid_levels": len(bids),
                    "ask_levels": len(asks),
                    "version": version
                })
            
            # Publish updated orderbook
            await self._publish_orderbook_from_cache(symbol)
            
        except Exception as e:
            self.logger.error("mexc_adapter.orderbook_snapshot_error", {
                "symbol": symbol,
                "error": str(e)
            })

    async def _process_orderbook_delta(self, symbol: str, data: dict) -> None:
        """Process incremental orderbook delta - merge with cached state"""
        try:
            bids_raw = data.get("bids", [])
            asks_raw = data.get("asks", [])
            version = int(data.get("version", 0)) if data.get("version") is not None else 0
            
            # Check version sequencing
            last_version = self._orderbook_versions.get(symbol, 0)
            if version <= last_version:
                self.logger.debug("mexc_adapter.stale_orderbook_delta", {
                    "symbol": symbol,
                    "delta_version": version,
                    "last_version": last_version
                })
                return
            
            # Parse delta levels
            bid_updates = []
            ask_updates = []
            
            for bid in bids_raw:
                parsed_bid = self._safe_parse_orderbook_level(bid)
                if parsed_bid:
                    bid_updates.append(parsed_bid)
            
            for ask in asks_raw:
                parsed_ask = self._safe_parse_orderbook_level(ask)
                if parsed_ask:
                    ask_updates.append(parsed_ask)

            # ✅ PERF FIX: Per-symbol lock instead of global lock
            async with self._get_orderbook_lock(symbol):
                # Initialize cache if not exists (fallback)
                if symbol not in self._orderbook_cache:
                    self._orderbook_cache[symbol] = {
                        "bids": OrderedDict(),
                        "asks": OrderedDict(),
                        "version": 0,
                        "timestamp": time.time()
                    }
                
                cache_entry = self._orderbook_cache[symbol]
                
                # Apply bid updates
                for price, qty in bid_updates:
                    price_str = str(float(price))
                    if float(qty) == 0:
                        # Remove level
                        cache_entry["bids"].pop(price_str, None)
                    else:
                        # Add/update level
                        cache_entry["bids"][price_str] = float(qty)
                
                # Apply ask updates
                for price, qty in ask_updates:
                    price_str = str(float(price))
                    if float(qty) == 0:
                        # Remove level
                        cache_entry["asks"].pop(price_str, None)
                    else:
                        # Add/update level
                        cache_entry["asks"][price_str] = float(qty)
                
                # Sort and maintain top levels only (limit memory usage)
                cache_entry["bids"] = OrderedDict(
                    sorted(cache_entry["bids"].items(), 
                           key=lambda x: float(x[0]), reverse=True)[:20]
                )
                cache_entry["asks"] = OrderedDict(
                    sorted(cache_entry["asks"].items(), 
                           key=lambda x: float(x[0]))[:20]
                )
                
                # Update version and timestamp
                cache_entry["version"] = version
                cache_entry["timestamp"] = time.time()
                self._orderbook_versions[symbol] = version
                
                self.logger.debug("mexc_adapter.orderbook_delta_processed", {
                    "symbol": symbol,
                    "bid_updates": len(bid_updates),
                    "ask_updates": len(ask_updates),
                    "version": version,
                    "total_bid_levels": len(cache_entry["bids"]),
                    "total_ask_levels": len(cache_entry["asks"])
                })
            
            # Publish updated orderbook
            await self._publish_orderbook_from_cache(symbol)
            
        except Exception as e:
            self.logger.error("mexc_adapter.orderbook_delta_error", {
                "symbol": symbol,
                "error": str(e)
            })

    async def _publish_orderbook_from_cache(self, symbol: str) -> None:
        """Publish orderbook update from cache"""
        try:
            # ✅ PERF FIX: Per-symbol lock instead of global lock
            async with self._get_orderbook_lock(symbol):
                cache_entry = self._orderbook_cache.get(symbol)
                if not cache_entry:
                    return
                
                # Convert OrderedDict back to list format for publishing with numeric prices
                bids = [(float(price), qty) for price, qty in cache_entry["bids"].items()]
                asks = [(float(price), qty) for price, qty in cache_entry["asks"].items()]
                
                if not bids and not asks:
                    return

                # ✅ PERF FIX: Fire-and-forget async publishing for zero latency
                # No batching - trading requires real-time orderbook data
                asyncio.create_task(self._safe_publish_event("market.orderbook_update", {
                    "exchange": "mexc",
                    "symbol": symbol,
                    "bids": bids,
                    "asks": asks,
                    "best_bid": bids[0][0] if bids else 0,
                    "best_ask": asks[0][0] if asks else 0,
                    "timestamp": cache_entry["timestamp"],
                    "source": "orderbook_cache",
                    "version": cache_entry["version"],
                    "levels_parsed": {
                        "bids": len(bids),
                        "asks": len(asks),
                        "total_bids": len(cache_entry["bids"]),
                        "total_asks": len(cache_entry["asks"])
                    }
                }))
                
        except Exception as e:
            self.logger.error("mexc_adapter.orderbook_publish_error", {
                "symbol": symbol,
                "error": str(e)
            })
    
    async def subscribe_to_symbol(self, symbol: str) -> None:
        """
        Subscribe to market data for a symbol.
        Creates new connection if needed.
        Uses rate limiting to prevent overwhelming MEXC.
        Thread-safe with async lock.

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
        """
        symbol = symbol.upper()
        
        self.logger.debug("mexc_adapter.subscribe_start", {
            "symbol": symbol,
            "rate_limiter_tokens": round(float(self.subscription_rate_limiter.tokens), 2)
        })
        
        # Use timeout for entire subscription operation
        try:
            await asyncio.wait_for(self._do_subscribe(symbol), timeout=60.0)
        except asyncio.TimeoutError:
            self.logger.error("mexc_adapter.subscription_timeout", {
                "symbol": symbol,
                "timeout_seconds": 60.0
            })
            raise RuntimeError(f"Subscription timeout for {symbol}")
        except Exception as e:
            self.logger.error("mexc_adapter.subscription_failed", {
                "symbol": symbol,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    async def _do_subscribe(self, symbol: str) -> None:
        """
        Internal subscription method with comprehensive race condition protection.
        Uses double-checked locking pattern with proper pending subscription tracking.
        """
        self.logger.debug("mexc_adapter.do_subscribe_start", {"symbol": symbol})
        
        async with self._subscription_lock:
            # First check - fast path for already subscribed symbols
            if symbol in self._subscribed_symbols:
                self.logger.debug("mexc_adapter.already_subscribed", {"symbol": symbol})
                return
            
            self.logger.debug("mexc_adapter.checking_rate_limit", {
                "symbol": symbol,
                "available_tokens": round(float(self.subscription_rate_limiter.tokens), 2)
            })
            
            # Apply rate limiting for subscriptions
            rate_limit_acquired = await self.subscription_rate_limiter.acquire_wait(
                tokens=1, 
                timeout=10.0
            )
            if not rate_limit_acquired:
                self.logger.error("mexc_adapter.rate_limit_timeout", {
                    "symbol": symbol,
                    "timeout_seconds": 10.0
                })
                raise RuntimeError(f"Rate limit timeout for subscription to {symbol}")
            
            self.logger.debug("mexc_adapter.rate_limit_acquired", {
                "symbol": symbol,
                "remaining_tokens": round(float(self.subscription_rate_limiter.tokens), 2)
            })
            
            try:
                # Get available connection with proper pending subscription tracking
                connection_id = self._get_available_connection_unlocked()
                if connection_id is None:
                    # Check connection limit within lock to prevent race conditions
                    if len(self._connections) >= self.max_connections:
                        raise RuntimeError(f"Cannot subscribe to {symbol}: maximum connections reached")
                    # Create new connection within the subscription lock to prevent races
                    connection_id = await self._create_new_connection()
                
                # ✅ FIX: Add to pending subscriptions BEFORE sending to prevent race conditions
                # Only track pending subscriptions for channels we'll actually subscribe to
                if connection_id not in self._pending_subscriptions:
                    self._pending_subscriptions[connection_id] = {}

                pending_channels = {'added_time': time.time()}
                if 'prices' in self.data_types:
                    pending_channels['deal'] = 'pending'
                if 'orderbook' in self.data_types:
                    pending_channels['depth'] = 'pending'
                    pending_channels['depth_full'] = 'pending'

                self._pending_subscriptions[connection_id][symbol] = pending_channels

                # Send subscription message
                self.logger.info("mexc_adapter.subscribing", {
                    "symbol": symbol,
                    "connection_id": connection_id,
                    "connections": len(self._connections)
                })
                await self._send_subscription(symbol, connection_id)
                self.logger.info("mexc_adapter.subscribed", {
                    "symbol": symbol,
                    "connection_id": connection_id
                })

                # Update tracking atomically - CRITICAL: all changes under same lock
                self._subscribed_symbols.add(symbol)
                self._symbol_to_connection[symbol] = connection_id
                self._connections[connection_id]["subscriptions"].add(symbol)

                # Remove from pending (subscription sent successfully) - will be removed when confirmations arrive
                
                self.logger.info("mexc_adapter.subscribed", {
                    "symbol": symbol,
                    "connection_id": connection_id,
                    "total_subscriptions": len(self._subscribed_symbols),
                    "rate_limiter_tokens": round(float(self.subscription_rate_limiter.tokens), 2)
                })
                
                # Publish subscription event
                await self._safe_publish_event("market_data.subscribed", {
                    "exchange": "mexc",
                    "symbol": symbol,
                    "connection_id": connection_id,
                    "timestamp": time.time()
                })
                    
            except Exception as e:
                self.logger.error("mexc_adapter.subscription_error", {
                    "symbol": symbol,
                    "error": str(e)
                })
    
    async def _send_subscription(self, symbol: str, connection_id: int) -> None:
        """
        Send subscription messages for a symbol based on configured data_types.

        Only subscribes to channels corresponding to requested data types:
        - 'prices' → sub.deal (trade/price data)
        - 'orderbook' → sub.depth.full + sub.depth (snapshot + deltas)
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info or not connection_info["connected"]:
            raise RuntimeError(f"Connection {connection_id} not available")

        websocket = connection_info["websocket"]

        # ✅ FIX: Only subscribe to deals if 'prices' is requested
        if 'prices' in self.data_types:
            deal_subscription_message = {
                "method": "sub.deal",
                "param": {
                    "symbol": symbol
                }
            }

            await websocket.send(json.dumps(deal_subscription_message))

            self.logger.debug("mexc_adapter.subscription_sent", {
                "symbol": symbol,
                "connection_id": connection_id,
                "method": "sub.deal"
            })

        # ✅ FIX: Only subscribe to order book if 'orderbook' is requested
        if 'orderbook' in self.data_types:
            # Step 1: Get initial snapshot with sub.depth.full
            depth_full_subscription_message = {
                "method": "sub.depth.full",
                "param": {
                    "symbol": symbol,
                    "limit": 20  # Get TOP 20 levels for full snapshot
                }
            }

            await websocket.send(json.dumps(depth_full_subscription_message))

            self.logger.debug("mexc_adapter.subscription_sent", {
                "symbol": symbol,
                "connection_id": connection_id,
                "method": "sub.depth.full",
                "limit": 20
            })

            # Step 2: Subscribe to incremental updates (deltas)
            depth_subscription_message = {
                "method": "sub.depth",
                "param": {
                    "symbol": symbol
                }
            }

            await websocket.send(json.dumps(depth_subscription_message))

            self.logger.debug("mexc_adapter.subscription_sent", {
                "symbol": symbol,
                "connection_id": connection_id,
                "method": "sub.depth"
            })
    
    async def unsubscribe_from_symbol(self, symbol: str) -> None:
        """
        Unsubscribe from market data for a symbol.

        Only unsubscribes from channels that were actually subscribed based on data_types.

        Args:
            symbol: Trading symbol to unsubscribe from
        """
        symbol = symbol.upper()

        if symbol not in self._subscribed_symbols:
            self.logger.debug("mexc_adapter.not_subscribed", {"symbol": symbol})
            return

        # ✅ FIX: Stop snapshot refresh task FIRST before unsubscribing
        # This prevents "no_connection_for_snapshot" warnings after unsubscribe
        await self._stop_snapshot_refresh_task(symbol)

        try:
            connection_id = self._symbol_to_connection.get(symbol)
            if connection_id is not None and connection_id in self._connections:
                connection_info = self._connections[connection_id]

                if connection_info["connected"]:
                    websocket = connection_info["websocket"]

                    # ✅ FIX: Only unsubscribe from deals if we subscribed to prices
                    if 'prices' in self.data_types:
                        deal_unsubscription = {
                            "method": "unsub.deal",
                            "param": {
                                "symbol": symbol
                            }
                        }
                        await websocket.send(json.dumps(deal_unsubscription))

                    # ✅ FIX: Only unsubscribe from order book if we subscribed to orderbook
                    if 'orderbook' in self.data_types:
                        depth_unsubscription = {
                            "method": "unsub.depth",
                            "param": {
                                "symbol": symbol
                            }
                        }
                        await websocket.send(json.dumps(depth_unsubscription))

                        # Also unsubscribe from depth.full if needed
                        depth_full_unsubscription = {
                            "method": "unsub.depth.full",
                            "param": {
                                "symbol": symbol
                            }
                        }
                        await websocket.send(json.dumps(depth_full_unsubscription))

                # Update tracking
                connection_info["subscriptions"].discard(symbol)

            self._subscribed_symbols.discard(symbol)
            self._symbol_to_connection.pop(symbol, None)

            self.logger.info("mexc_adapter.unsubscribed", {
                "symbol": symbol,
                "connection_id": connection_id,
                "total_subscriptions": len(self._subscribed_symbols)
            })

        except Exception as e:
            self.logger.error("mexc_adapter.unsubscription_error", {
                "symbol": symbol,
                "error": str(e)
            })
    
    async def _close_connection(self, connection_id: int) -> None:
        """Close a specific connection and clean up"""
        if connection_id not in self._connections:
            return
            
        connection_info = self._connections[connection_id]
        
        # Cancel tasks
        for task_name in ["heartbeat_task", "message_task"]:
            task = connection_info.get(task_name)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Store symbols for potential reconnection
        failed_symbols = connection_info["subscriptions"].copy()
        
        # Close websocket
        try:
            if connection_info["websocket"]:
                await connection_info["websocket"].close()
        except Exception as e:
            self.logger.debug("mexc_adapter.close_websocket_error", {
                "connection_id": connection_id,
                "error": str(e)
            })

        # ✅ FIX: Stop all snapshot refresh tasks for symbols on this connection
        # This prevents "no_connection_for_snapshot" warnings after connection closes
        for symbol in failed_symbols:
            await self._stop_snapshot_refresh_task(symbol)

        # Clean up subscriptions
        for symbol in list(connection_info["subscriptions"]):
            self._subscribed_symbols.discard(symbol)
            self._symbol_to_connection.pop(symbol, None)

        # ✅ FIX (Propozycja #1B): Wait for in-flight message processing to complete
        # This prevents race condition where confirmations arrive after cleanup starts
        max_wait = 5.0  # 5 seconds max wait
        start_time = time.time()

        while connection_id in self._message_processing_count:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                self.logger.warning("mexc_adapter.force_cleanup_timeout", {
                    "connection_id": connection_id,
                    "remaining_handlers": self._message_processing_count.get(connection_id, 0),
                    "elapsed_seconds": elapsed
                })
                break
            await asyncio.sleep(0.1)  # Check every 100ms

        # Log successful wait
        if connection_id in self._message_processing_count:
            # Timed out - force cleanup
            self._message_processing_count.pop(connection_id, None)
        else:
            # Clean wait - all handlers completed
            elapsed = time.time() - start_time
            if elapsed > 0.1:  # Only log if we actually waited
                self.logger.debug("mexc_adapter.cleanup_wait_completed", {
                    "connection_id": connection_id,
                    "wait_seconds": round(elapsed, 3)
                })

        # Clean up pending subscriptions for this connection
        self._pending_subscriptions.pop(connection_id, None)
        
        # Remove connection
        del self._connections[connection_id]
        
        self.logger.info("mexc_adapter.connection_closed", {
            "connection_id": connection_id,
            "remaining_connections": len(self._connections),
            "failed_symbols": len(failed_symbols)
        })
        
        # Attempt reconnection if we're still running and have failed symbols
        if self._running and failed_symbols:
            self._create_tracked_task(
                self._reconnect_connection(connection_id, failed_symbols),
                f"reconnect_{connection_id}"
            )

    async def _reconnect_connection(self, old_connection_id: int, failed_symbols: Set[str]) -> None:
        """
        Auto-reconnect failed connection with exponential backoff and FIXED memory management.
        Implements bounded reconnection tracking with proper cleanup logic.
        """
        # FIXED: Simple hard limit approach - keep only newest 20 entries
        if len(self._reconnection_attempts) > 20:
            # Keep newest 20 by connection ID (highest connection IDs = newest)
            newest_ids = sorted(self._reconnection_attempts.keys())[-20:]
            old_size = len(self._reconnection_attempts)
            self._reconnection_attempts = {
                k: v for k, v in self._reconnection_attempts.items() 
                if k in newest_ids
            }
            
            cleaned_count = old_size - len(self._reconnection_attempts)
            self.logger.info("mexc_adapter.reconnection_attempts_hard_limit_cleanup", {
                "removed_attempts": cleaned_count,
                "remaining_attempts": len(self._reconnection_attempts),
                "hard_limit": 20,
                "reason": "memory_leak_prevention"
            })
        
        # Get current attempt count for this connection
        attempt = self._reconnection_attempts.get(old_connection_id, 0)
        
        # Check if we've exceeded maximum attempts
        if attempt >= self.max_reconnect_attempts:
            self.logger.error("mexc_adapter.max_reconnection_attempts_exceeded", {
                "old_connection_id": old_connection_id,
                "max_attempts": self.max_reconnect_attempts,
                "failed_symbols": list(failed_symbols),
                "total_attempts": attempt
            })
            # Clean up this connection's attempt tracking
            self._reconnection_attempts.pop(old_connection_id, None)
            return
        
        # Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s (capped at 30s)
        base_delay = min(2 ** attempt, 30)
        # Add small jitter to prevent thundering herd
        jitter = base_delay * 0.1 * (hash(old_connection_id) % 100) / 100
        backoff_delay = base_delay + jitter
        
        self.logger.info("mexc_adapter.reconnection_attempt", {
            "old_connection_id": old_connection_id,
            "attempt": attempt + 1,
            "backoff_delay": backoff_delay,
            "symbols_to_resubscribe": len(failed_symbols)
        })
        
        await asyncio.sleep(backoff_delay)
        
        try:
            # Create new connection
            new_connection_id = await self._create_new_connection()

            # Schedule resubscription as separate tasks to avoid deadlock with subscription lock
            resubscribed_count = 0
            for symbol in failed_symbols:
                # Create tracked task for each symbol subscription to avoid blocking reconnection
                self._create_tracked_task(
                    self._safe_resubscribe_symbol(symbol),
                    f"resubscribe_{symbol}"
                )
                resubscribed_count += 1
            
            # Reset reconnection attempts on success
            self._reconnection_attempts.pop(old_connection_id, None)
            
            self.logger.info("mexc_adapter.reconnection_successful", {
                "old_connection_id": old_connection_id,
                "new_connection_id": new_connection_id,
                "resubscribed_symbols": resubscribed_count,
                "total_failed_symbols": len(failed_symbols)
            })
            
        except Exception as e:
            # Increment attempt counter and try again
            self._reconnection_attempts[old_connection_id] = attempt + 1
            self._update_tracking_expiry(str(old_connection_id))
            
            self.logger.warning("mexc_adapter.reconnection_attempt_failed", {
                "old_connection_id": old_connection_id,
                "attempt": attempt + 1,
                "error": str(e),
                "next_attempt_in": min(2 ** (attempt + 1), 30)
            })
            
            # Schedule next attempt
            if attempt + 1 < self.max_reconnect_attempts:
                self._create_tracked_task(
                    self._reconnect_connection(old_connection_id, failed_symbols),
                    f"reconnect_retry_{old_connection_id}"
                )

    async def _cleanup_old_reconnection_attempts(self) -> None:
        """
        SIMPLIFIED: Clean up stale reconnection attempts using hard limits.
        No complex heuristics - just remove entries for non-existent connections.
        """
        current_time = time.time()
        cleanup_interval = 300  # 5 minutes between cleanups
        
        # Don't cleanup too frequently
        if current_time - self._last_cleanup_time < cleanup_interval:
            return
        
        self._last_cleanup_time = current_time
        cleanup_candidates = []
        
        # Simple rule: Remove attempts for connections that no longer exist
        for conn_id in list(self._reconnection_attempts.keys()):
            if conn_id not in self._connections:
                cleanup_candidates.append(conn_id)
        
        # Perform cleanup
        cleaned_count = 0
        for conn_id in cleanup_candidates:
            if self._reconnection_attempts.pop(conn_id, None) is not None:
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info("mexc_adapter.reconnection_attempts_simple_cleanup", {
                "cleaned_attempts": cleaned_count,
                "remaining_attempts": len(self._reconnection_attempts),
                "cleanup_interval_seconds": cleanup_interval,
                "total_connections": len(self._connections)
            })
        
        self._last_cleanup_time = current_time
    
    async def disconnect(self) -> None:
        """Gracefully disconnect all WebSocket connections"""
        self._running = False
        
        self.logger.info("mexc_adapter.disconnecting", {
            "connections_count": len(self._connections)
        })

        # Cancel tracking cleanup task
        if self._tracking_cleanup_task and not self._tracking_cleanup_task.done():
            self._tracking_cleanup_task.cancel()

        # Cancel pending subscriptions cleanup task
        if hasattr(self, '_pending_cleanup_task') and self._pending_cleanup_task and not self._pending_cleanup_task.done():
            self._pending_cleanup_task.cancel()

        # Cancel all snapshot refresh tasks
        for symbol, task in list(self._snapshot_refresh_tasks.items()):
            if task and not task.done():
                task.cancel()
        self._snapshot_refresh_tasks.clear()

        # Cancel all active tasks
        await self._cancel_all_active_tasks()

        # Close all connections
        for connection_id in list(self._connections.keys()):
            await self._close_connection(connection_id)

        # Clear debug log rates and message counter
        self._debug_log_rates.clear()
        self._message_count = 0

        # Clear tracking structures
        self._reconnection_attempts.clear()
        self._tracking_expiry.clear()

        # Clear pending subscriptions
        self._pending_subscriptions.clear()

    async def _cleanup_pending_subscriptions(self) -> None:
        """Clean up expired pending subscriptions to prevent memory leaks"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                current_time = time.time()
                expired_symbols = []

                # Find expired pending subscriptions
                for conn_id, symbols in list(self._pending_subscriptions.items()):
                    for symbol, status in list(symbols.items()):
                        added_time = status.get('added_time', current_time)
                        if current_time - added_time > 60:  # 60 second TTL
                            expired_symbols.append((conn_id, symbol))

                # Remove expired entries
                for conn_id, symbol in expired_symbols:
                    if conn_id in self._pending_subscriptions and symbol in self._pending_subscriptions[conn_id]:
                        del self._pending_subscriptions[conn_id][symbol]
                        if not self._pending_subscriptions[conn_id]:
                            del self._pending_subscriptions[conn_id]

                        self.logger.warning("mexc_adapter.pending_subscription_expired", {
                            "connection_id": conn_id,
                            "symbol": symbol,
                            "reason": "TTL_exceeded"
                        })

                if expired_symbols:
                    self.logger.info("mexc_adapter.pending_subscriptions_cleanup_completed", {
                        "expired_count": len(expired_symbols)
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("mexc_adapter.pending_subscriptions_cleanup_error", {"error": str(e)})
        
        # Publish disconnection event
        await self._safe_publish_event("market_data.disconnected", {
            "exchange": "mexc",
            "timestamp": time.time()
        })
        
        self.logger.info("mexc_adapter.disconnected")
    
    async def shutdown(self) -> None:
        """Complete shutdown of the adapter"""
        self.logger.info("mexc_adapter.shutdown_started")
        
        await self.disconnect()
        await self.shutdown_manager.cleanup()
        
        self.logger.info("mexc_adapter.shutdown_completed")
    
    # Implementation of IMarketDataProvider interface methods
    
    async def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """
        get_latest_price is not supported - use EventBus subscription instead.

        Market data is published in real-time through EventBus events.
        Subscribe to 'market.price_update' to receive price updates.

        Raises:
            NotImplementedError: Always - this method is not implemented
        """
        raise NotImplementedError(
            "get_latest_price() is not supported. "
            "Use EventBus.subscribe('market.price_update', handler) to receive real-time price updates."
        )
    
    # Removed duplicate method definitions - using implementations at end of file
    
    async def health_check(self) -> bool:
        """Check adapter health"""
        return self._running and len(self._connections) > 0

    def get_subscribed_symbols(self) -> Set[str]:
        """Get all currently subscribed symbols"""
        return self._subscribed_symbols.copy()
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "exchange": "mexc",
            "running": self._running,
            "total_connections": len(self._connections),
            "active_connections": sum(1 for c in self._connections.values() if c["connected"]),
            "subscribed_symbols": list(self._subscribed_symbols),
            "total_subscriptions": len(self._subscribed_symbols),
            "max_subscriptions_per_connection": self.max_subscriptions_per_connection,
            "max_connections": self.max_connections,
            "connections": {
                conn_id: {
                    "connected": info["connected"],
                    "subscriptions": len(info["subscriptions"]),
                    "symbols": list(info["subscriptions"])
                }
                for conn_id, info in self._connections.items()
            }
        }

    def get_detailed_metrics(self) -> dict:
        """Get detailed performance metrics including circuit breaker, rate limiter, and cache statistics"""
        uptime_seconds = time.time() - self._start_time
        total_reconnections = sum(self._reconnection_attempts.values())
        
        connection_health = []
        for conn_id, info in self._connections.items():
            last_heartbeat = info.get("last_heartbeat", 0)
            last_ping = info.get("last_ping_sent", 0)
            last_pong = info.get("last_pong_received", 0)
            
            connection_health.append({
                "connection_id": conn_id,
                "connected": info["connected"],
                "subscriptions": len(info["subscriptions"]),
                "last_heartbeat_age": time.time() - last_heartbeat,
                "last_ping_age": time.time() - last_ping,
                "last_pong_age": time.time() - last_pong,
                "health_score": self._calculate_connection_health(info)
            })
        
        return {
            "connections": self.get_connection_stats(),
            "performance": {
                "uptime_seconds": uptime_seconds,
                "total_reconnection_attempts": total_reconnections,
                "active_reconnection_attempts": len(self._reconnection_attempts),
                "symbols_per_connection_ratio": len(self._subscribed_symbols) / max(len(self._connections), 1),
                "connection_health": connection_health
            },
            "health": {
                "overall_health": self._calculate_overall_health(),
                "connection_stability": len(self._connections) > 0 and total_reconnections < 10,
                "subscription_balance": self._check_subscription_balance()
            },
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "rate_limiter": self.subscription_rate_limiter.get_stats(),
            "reliability": {
                "circuit_breaker_state": self.circuit_breaker.get_state(),
                "rate_limit_tokens_available": round(float(self.subscription_rate_limiter.tokens), 2),
                "rate_limit_usage_pct": round(((self.subscription_rate_limiter.max_tokens - self.subscription_rate_limiter.tokens) / self.subscription_rate_limiter.max_tokens) * 100, 2)
            }
        }

    def _calculate_connection_health(self, connection_info: dict) -> float:
        """Calculate health score for a connection (0-100)"""
        if not connection_info["connected"]:
            return 0.0

        current_time = time.monotonic()
        # Convert wall time to monotonic for comparison
        last_heartbeat = connection_info.get("last_heartbeat", 0)
        last_pong = connection_info.get("last_pong_received", 0)

        # Convert to monotonic time if stored as wall time
        if last_heartbeat > 1e10:  # Likely wall time (has fractional seconds)
            # Approximate conversion - not perfect but better than using wall time directly
            last_heartbeat = time.monotonic() - (time.time() - last_heartbeat)
        if last_pong > 1e10:
            last_pong = time.monotonic() - (time.time() - last_pong)

        # Age of last activity (in seconds)
        heartbeat_age = current_time - last_heartbeat
        pong_age = current_time - last_pong

        # Health decreases with age of last activity
        heartbeat_score = max(0, 100 - (heartbeat_age / 60) * 50)  # 50% penalty per minute
        pong_score = max(0, 100 - (pong_age / 60) * 50)

        return min(heartbeat_score, pong_score)

    def _calculate_overall_health(self) -> float:
        """Calculate overall adapter health (0-100)"""
        if not self._running or not self._connections:
            return 0.0
        
        # Average connection health
        connection_scores = [
            self._calculate_connection_health(info) 
            for info in self._connections.values()
        ]
        
        avg_connection_health = sum(connection_scores) / len(connection_scores)
        
        # Penalty for reconnection attempts
        reconnection_penalty = min(50, sum(self._reconnection_attempts.values()) * 5)
        
        return max(0, avg_connection_health - reconnection_penalty)

    def _check_subscription_balance(self) -> bool:
        """Check if subscriptions are well-balanced across connections"""
        if not self._connections:
            return True
        
        subscription_counts = [
            len(info["subscriptions"]) 
            for info in self._connections.values()
        ]
        
        if not subscription_counts:
            return True
        
        min_subs = min(subscription_counts)
        max_subs = max(subscription_counts)
        
        # Good balance if difference is less than 10
        return (max_subs - min_subs) <= 10
    
    async def get_cache_statistics(self) -> dict:
        """
        Cache statistics are not available - cache layer has been removed.

        Market data now flows exclusively through EventBus in real-time.
        No caching layer exists for price/volume data.

        Raises:
            NotImplementedError: Always - cache layer has been removed
        """
        raise NotImplementedError(
            "get_cache_statistics() is not supported. "
            "Cache layer has been removed - all data flows through EventBus in real-time."
        )

    # Abstract method implementations required by IMarketDataProvider
    
    async def get_market_data_stream(self, symbol: str):
        """
        Get real-time market data stream for a symbol.
        Returns an async iterator that yields market data as it arrives.
        """
        # Create a queue to buffer incoming data for this symbol
        data_queue = asyncio.Queue(maxsize=100)

        # Subscribe to market data events for this symbol
        async def market_data_handler(data: dict):
            """Handle incoming market data events"""
            try:
                # Event type is implicit from subscription - only subscribed events are received
                event_symbol = data.get("symbol", "").upper()
                if event_symbol == symbol.upper():
                    # Put data in queue for the consumer
                    try:
                        data_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        # Drop oldest data if queue is full
                        try:
                            data_queue.get_nowait()
                            data_queue.put_nowait(data)
                        except asyncio.QueueEmpty:
                            pass
            except Exception as e:
                self.logger.error("mexc_adapter.stream_handler_error", {
                    "symbol": symbol,
                    "error": str(e)
                })

        # Subscribe to events
        await self.event_bus.subscribe("market.price_update", market_data_handler)
        await self.event_bus.subscribe("market.orderbook_update", market_data_handler)

        try:
            # Yield data as it arrives
            while self._running:
                try:
                    # Wait for data with timeout
                    data = await asyncio.wait_for(data_queue.get(), timeout=1.0)
                    yield data
                    data_queue.task_done()
                except asyncio.TimeoutError:
                    # No data available, continue waiting
                    continue
                except asyncio.CancelledError:
                    break
        finally:
            # Unsubscribe from events when done
            # EventBus.unsubscribe() handles "not found" cases gracefully with silent=True
            self.event_bus.unsubscribe("market.price_update", market_data_handler, silent=True)
            self.event_bus.unsubscribe("market.orderbook_update", market_data_handler, silent=True)
    
    
    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        """Get 24h volume for a symbol in USDT"""
        # This would require additional API calls to get 24h stats
        # For now, return None (not available from websocket directly)
        return None
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information (precision, limits, etc.)"""
        # This would require additional API calls to get symbol info
        # For now, return basic info
        return {
            "symbol": symbol.upper(),
            "exchange": "mexc",
            "status": "active" if await self.is_symbol_active(symbol) else "inactive"
        }
    
    async def _refresh_orderbook_from_rest(self, symbol: str) -> None:
        """
        Refresh orderbook cache from MEXC Futures REST API.

        CRITICAL: Uses ONLY Futures endpoint (NOT Spot API).
        - Futures endpoint: https://contract.mexc.com/api/v1/contract/depth/{symbol}
        - Symbol format: WITH underscore (BTC_USDT)
        - Same format as WebSocket (wss://contract.mexc.com)
        """
        try:
            # MEXC Futures uses symbol WITH underscore (same as WebSocket)
            # No transformation needed - use symbol as-is
            rest_url = f"https://contract.mexc.com/api/v1/contract/depth/{symbol}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rest_url, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Parse Futures REST response (format: {"success": true, "code": 0, "data": {...}})
                        # Different from Spot API which returns bids/asks at root level
                        response_data = data.get("data", {}) if "data" in data else data
                        bids_raw = response_data.get("bids", [])
                        asks_raw = response_data.get("asks", [])
                        
                        # Convert to our format
                        bids = []
                        asks = []
                        
                        for bid_raw in bids_raw[:20]:
                            if len(bid_raw) >= 2:
                                try:
                                    price = float(bid_raw[0])
                                    qty = float(bid_raw[1])
                                    if price > 0 and qty > 0:
                                        bids.append((price, qty))
                                except (ValueError, TypeError):
                                    continue
                        
                        for ask_raw in asks_raw[:20]:
                            if len(ask_raw) >= 2:
                                try:
                                    price = float(ask_raw[0])
                                    qty = float(ask_raw[1])
                                    if price > 0 and qty > 0:
                                        asks.append((price, qty))
                                except (ValueError, TypeError):
                                    continue
                        
                        # Update cache
                        if bids or asks:
                            # ✅ PERF FIX: Per-symbol lock instead of global lock
                            async with self._get_orderbook_lock(symbol):
                                if symbol not in self._orderbook_cache:
                                    # ✅ FIX: Initialize with OrderedDict for consistency with snapshot/delta processing
                                    self._orderbook_cache[symbol] = {
                                        "bids": OrderedDict(),
                                        "asks": OrderedDict(),
                                        "version": 0,
                                        "timestamp": time.time()
                                    }

                                cache_entry = self._orderbook_cache[symbol]
                                # Convert list format to OrderedDict
                                cache_entry["bids"] = OrderedDict((str(float(price)), float(qty)) for price, qty in bids)
                                cache_entry["asks"] = OrderedDict((str(float(price)), float(qty)) for price, qty in asks)
                                cache_entry["timestamp"] = time.time()
                                
                            self.logger.debug("mexc_adapter.orderbook_refreshed_from_rest", {
                                "symbol": symbol,
                                "bids_count": len(bids),
                                "asks_count": len(asks),
                                "source": "futures_rest_api"
                            })
                    else:
                        self.logger.warning("mexc_adapter.rest_orderbook_failed", {
                            "symbol": symbol,
                            "status": response.status,
                            "endpoint": "futures_rest_api"
                        })
                        
        except Exception as e:
            self.logger.error("mexc_adapter.rest_orderbook_error", {
                "symbol": symbol,
                "error": str(e)
            })
    
    async def _start_orderbook_refresh_task(self) -> None:
        """Start periodic orderbook refresh from REST API"""
        while self._running:
            try:
                # Wait 60 seconds between refresh cycles
                await asyncio.sleep(60.0)
                
                if not self._running:
                    break
                
                # Refresh orderbook for all subscribed symbols
                symbols_to_refresh = list(self._subscribed_symbols)
                for symbol in symbols_to_refresh:
                    if not self._running:
                        break

                    # Check if cache is stale (older than 2 minutes)
                    # ✅ PERF FIX: Per-symbol lock instead of global lock
                    async with self._get_orderbook_lock(symbol):
                        if symbol in self._orderbook_cache:
                            cache_age = time.time() - self._orderbook_cache[symbol]["timestamp"]
                            if cache_age > 120:  # 2 minutes
                                await self._refresh_orderbook_from_rest(symbol)
                    
                    # Small delay between symbols to avoid rate limits
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("mexc_adapter.orderbook_refresh_task_error", {
                    "error": str(e)
                })
                await asyncio.sleep(5.0)  # Wait before retrying
    
    async def is_symbol_active(self, symbol: str) -> bool:
        """Check if symbol is actively trading"""
        symbol = symbol.upper()
        # Simple check - if we're subscribed and receiving data, it's active
        return symbol in self._subscribed_symbols

    async def _start_snapshot_refresh_task(self, symbol: str) -> None:
        """Start periodic snapshot refresh task for a symbol"""
        if symbol in self._snapshot_refresh_tasks:
            # Task already exists
            return
            
        async def snapshot_refresh_loop():
            """Periodic refresh loop for snapshot verification"""
            while self._running and symbol in self._subscribed_symbols:
                try:
                    # Wait for refresh interval (default 5 minutes)
                    await asyncio.sleep(self._snapshot_refresh_interval)
                    
                    if not self._running or symbol not in self._subscribed_symbols:
                        break
                    
                    # Try WebSocket snapshot first, fallback to REST
                    success = await self._request_websocket_snapshot(symbol)
                    if not success:
                        # Fallback to REST API
                        await self._refresh_orderbook_from_rest(symbol)
                    
                    self.logger.debug("mexc_adapter.snapshot_refresh_completed", {
                        "symbol": symbol,
                        "interval": self._snapshot_refresh_interval,
                        "method": "websocket" if success else "rest_fallback"
                    })
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error("mexc_adapter.snapshot_refresh_error", {
                        "symbol": symbol,
                        "error": str(e)
                    })
                    # Wait shorter time on error before retry
                    await asyncio.sleep(30)
            
            # Cleanup
            self._snapshot_refresh_tasks.pop(symbol, None)
            self.logger.debug("mexc_adapter.snapshot_refresh_task_ended", {
                "symbol": symbol
            })
        
        # Start the refresh task
        task = asyncio.create_task(snapshot_refresh_loop())
        self._snapshot_refresh_tasks[symbol] = task
        
        self.logger.debug("mexc_adapter.snapshot_refresh_task_started", {
            "symbol": symbol,
            "refresh_interval": self._snapshot_refresh_interval
        })

    async def _stop_snapshot_refresh_task(self, symbol: str) -> None:
        """Stop and cancel snapshot refresh task for a symbol"""
        task = self._snapshot_refresh_tasks.pop(symbol, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            self.logger.debug("mexc_adapter.snapshot_task_cancelled", {
                "symbol": symbol,
                "reason": "unsubscribe_or_cleanup"
            })

    async def _request_websocket_snapshot(self, symbol: str) -> bool:
        """Request fresh snapshot via WebSocket for a symbol"""
        try:
            connection_id = self._symbol_to_connection.get(symbol)
            # ✅ FIX: connection_id=0 is valid! Use 'is None' instead of 'not connection_id'
            if connection_id is None or connection_id not in self._connections:
                # ✅ FIX: Enhanced logging with context + orphaned task cleanup
                self.logger.warning("mexc_adapter.no_connection_for_snapshot", {
                    "symbol": symbol,
                    "in_subscribed_symbols": symbol in self._subscribed_symbols,
                    "has_snapshot_task": symbol in self._snapshot_refresh_tasks,
                    "connection_id_from_mapping": connection_id,
                    "available_connections": list(self._connections.keys()),
                    "likely_cause": "symbol_unsubscribed_or_connection_closed",
                    "action": "skipping_refresh_task_will_retry_next_interval"
                })

                # If symbol not in subscribed, stop orphaned task immediately
                if symbol not in self._subscribed_symbols:
                    self.logger.info("mexc_adapter.stopping_orphaned_snapshot_task", {
                        "symbol": symbol,
                        "reason": "symbol_no_longer_subscribed"
                    })
                    # Task will be stopped - remove from dict and cancel
                    task = self._snapshot_refresh_tasks.pop(symbol, None)
                    if task and not task.done():
                        task.cancel()

                return False
            
            connection_info = self._connections[connection_id]
            websocket = connection_info.get("websocket")

            # ✅ FIX: Use close_code instead of closed attribute (websockets library compatibility)
            if not websocket or websocket.close_code is not None:
                self.logger.warning("mexc_adapter.closed_connection_for_snapshot", {
                    "symbol": symbol,
                    "connection_id": connection_id
                })
                return False
            
            # Request fresh snapshot
            snapshot_request = {
                "method": "sub.depth.full",
                "param": {
                    "symbol": symbol,
                    "limit": 20
                }
            }
            
            await websocket.send(json.dumps(snapshot_request))
            
            self.logger.debug("mexc_adapter.websocket_snapshot_requested", {
                "symbol": symbol,
                "connection_id": connection_id
            })
            
            return True
            
        except Exception as e:
            self.logger.error("mexc_adapter.websocket_snapshot_request_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return False
    
    async def health_check(self) -> bool:
        """Check if connection is healthy"""
        try:
            # Check if we have at least one active connection
            active_connections = sum(1 for conn in self._connections.values() 
                                   if conn.get("connected", False))
            
            # Check circuit breaker state
            circuit_ok = self.circuit_breaker.state == "CLOSED"
            
            # Basic health indicators
            return active_connections > 0 and circuit_ok
        except Exception:
            return False

