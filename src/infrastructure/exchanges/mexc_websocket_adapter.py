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
    
    def __init__(self, settings: ExchangeSettings, event_bus: EventBus, logger: StructuredLogger):
        """
        Initialize MEXC WebSocket adapter with Clean Architecture principles.
        
        Args:
            settings: Exchange configuration
            event_bus: Central communication hub  
            logger: Structured logger
        """
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
        
        # Configuration from settings
        self.config = settings.get("mexc")
        self.ws_url = self.config.get("futures_ws_url", "wss://contract.mexc.com/edge")
        self.max_subscriptions_per_connection = self.config.get("max_subscriptions_per_connection", 30)
        self.max_connections = self.config.get("max_connections", 5)
        self.max_reconnect_attempts = self.config.get("max_reconnect_attempts", 5)
        
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
        
        # Constants for memory management - FIXED: Reduced limits for safety
        self.MAX_TRACKED_RECONNECTIONS = 20  # FIXED: Hard limit instead of soft trigger
        self.MAX_ACCESS_COUNT_ENTRIES = 2000  # Limit access count tracking
        self.MAX_CACHE_ACCESS_ORDER = 5000   # Limit LRU order tracking
        
        # Enhanced cache configuration with settings support
        self.cache_config = {
            "max_cache_size": self.config.get("max_cache_size", 1000),
            "high_water_mark": self.config.get("high_water_mark", 850),
            "cleanup_batch_size": self.config.get("cleanup_batch_size", 50),
            "priority_retention_hours": self.config.get("priority_retention_hours", 1)
        }
        
        # Validate cache configuration
        if self.cache_config["max_cache_size"] <= 0:
            raise ValueError("max_cache_size must be > 0")
        if self.cache_config["high_water_mark"] >= self.cache_config["max_cache_size"]:
            self.cache_config["high_water_mark"] = int(self.cache_config["max_cache_size"] * 0.85)
            self.logger.warning("mexc_adapter.cache_config_adjusted", {
                "high_water_mark": self.cache_config["high_water_mark"],
                "reason": "was >= max_cache_size"
            })
        
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
        
        # Market data cache - Enhanced with size-based management
        self._latest_prices: Dict[str, float] = {}  # Legacy cache for backward compatibility
        self._symbol_volumes: Dict[str, float] = {}  # Legacy cache for backward compatibility
        self._market_data_cache: Dict[str, MarketData] = {}  # Enhanced cache with MarketData objects
        self._cache_timestamps: Dict[str, float] = {}  # Track cache freshness
        self._cache_access_order: OrderedDict[str, bool] = OrderedDict()  # O(1) LRU tracking
        
        # Simplified access tracking (bounded)
        self._cache_access_count: Dict[str, int] = {}  # Track access frequency (bounded)
        
        # Cache synchronization - Simplified to single lock for consistency and performance
        self._cache_lock = asyncio.Lock()  # Single lock for all cache operations
        
        # CRITICAL FIX: Disable complex access tracking to reduce CPU usage
        # self._pending_access_updates = asyncio.Queue(maxsize=1000)  # Batch access updates
        # self._access_update_task = None  # Background task for batched updates
        # self._access_update_lock = asyncio.Lock()  # Prevent race conditions in task creation
        # self._access_batch_size = 50  # Process access updates in batches
        # self._access_flush_interval = 0.1  # Flush every 100ms
        
        # Shutdown management
        self.shutdown_manager = SimpleShutdown("MexcWebSocketAdapter")
        
        # Reconnection tracking
        self._reconnection_attempts: Dict[int, int] = {}
        self._start_time = time.time()
        self._last_cleanup_time = time.time()
        
        # Cache cleanup task
        self._cache_cleanup_task = None

        # Memory management - guaranteed cleanup for tracking structures
        self._tracking_cleanup_task = None
        self._tracking_expiry = {}  # symbol -> expiry_time for all tracking structures
        self._max_tracking_age = 3600  # 1 hour expiry for tracking data

        # O(n) operation optimization - cached intersection for hot path
        self._last_intersection_time = 0
        self._cached_intersection = set()

        # Task lifecycle management - prevent dangling tasks
        self._active_tasks = set()
        
        # Rate limiting for debug logs to prevent spam
        self._debug_log_rates = {}  # symbol -> last_log_time for price/depth updates
        self._message_count = 0  # Counter for message batching
        
        # ✅ ORDERBOOK CACHE: Maintain full state between incremental updates
        self._orderbook_cache = {}  # symbol -> {"bids": OrderedDict, "asks": OrderedDict, "version": int, "timestamp": float}
        self._orderbook_lock = asyncio.Lock()  # Ensure thread-safe updates
        self._orderbook_versions = {}  # symbol -> last_processed_version for delta synchronization
        
        # Periodic snapshot refresh to prevent drift from deltas
        self._snapshot_refresh_interval = self.config.get("snapshot_refresh_interval", 300)  # 5 minutes default
        self._snapshot_refresh_tasks = {}  # symbol -> asyncio.Task for periodic refresh

        # ✅ PERF FIX: Event batching to reduce EventBus overhead
        self._event_batching_enabled = self.config.get("event_batching_enabled", True)
        self._batch_size = self.config.get("batch_size", 100)  # Max events per batch
        self._batch_flush_interval = self.config.get("batch_flush_interval", 0.1)  # 100ms default

        # Event buffers for batching
        self._price_update_buffer: List[Dict[str, Any]] = []
        self._orderbook_update_buffer: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()  # Protect batch buffers
        self._batch_flush_task = None  # Background flush task

        self.logger.info("mexc_adapter.initialized", {
            "ws_url": self.ws_url,
            "exchange": "mexc",
            "max_subscriptions_per_connection": self.max_subscriptions_per_connection,
            "max_connections": self.max_connections,
            "circuit_breaker_enabled": True,
            "rate_limiting_enabled": True,
            "cache_config": self.cache_config,
            "event_batching_enabled": self._event_batching_enabled,
            "batch_size": self._batch_size,
            "batch_flush_interval_ms": self._batch_flush_interval * 1000
        })
    
    def get_exchange_name(self) -> str:
        """Get exchange name"""
        return "mexc"
    
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

            # Start cache cleanup task
            self._cache_cleanup_task = self._create_tracked_task(self._cleanup_stale_cache(), "cache_cleanup")

            # Start tracking cleanup task for memory leak prevention
            self._tracking_cleanup_task = self._create_tracked_task(self._cleanup_tracking_structures(), "tracking_cleanup")

            # Start pending subscriptions cleanup task
            self._pending_cleanup_task = self._create_tracked_task(self._cleanup_pending_subscriptions(), "pending_cleanup")

            # ✅ START: Orderbook refresh task for cache freshness
            self._orderbook_refresh_task = self._create_tracked_task(self._start_orderbook_refresh_task(), "orderbook_refresh")

            # ✅ PERF FIX: Start event batch flushing task
            if self._event_batching_enabled:
                self._batch_flush_task = self._create_tracked_task(self._batch_flush_loop(), "batch_flush")

            # CRITICAL FIX: Disable access update processor to reduce CPU usage
            # await self._start_access_update_processor()

            self.logger.info("mexc_adapter.connected", {
                "url": self.ws_url,
                "connections": len(self._connections),
                "cache_cleanup_enabled": True,
                "lock_free_access_tracking": True,
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
    
    async def _cleanup_stale_cache(self) -> None:
        """Clean up stale cache entries every 5 minutes and enforce intelligent size limits"""
        while self._running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                current_time = time.time()
                stale_threshold = 600  # 10 minutes
                
                stale_removed = 0
                # Time-based cleanup with proper locking
                async with self._cache_lock:
                    stale_symbols = [
                        symbol for symbol, timestamp in self._cache_timestamps.items()
                        if current_time - timestamp > stale_threshold
                    ]
                    for symbol in stale_symbols:
                        self._remove_from_cache(symbol)
                        stale_removed += 1
                
                # Intelligent size-based cleanup (has its own locking)
                size_removed = await self._perform_intelligent_cache_cleanup()
                
                # OPTIMIZED: Get cache size quickly, compute expensive metrics outside lock
                async with self._cache_lock:
                    cache_size = len(self._market_data_cache)
                    cached_symbols = set(self._market_data_cache.keys())
                
                # OPTIMIZED: Use cached intersection to avoid O(n) operation
                current_time = time.time()
                if current_time - self._last_intersection_time > 30:
                    self._cached_intersection = cached_symbols & self._subscribed_symbols
                    self._last_intersection_time = current_time

                subscribed_cached = len(self._cached_intersection)
                
                if stale_removed > 0 or size_removed > 0:
                    self.logger.info("mexc_adapter.cache_cleanup_completed", {
                        "stale_removed": stale_removed,
                        "size_removed": size_removed,
                        "total_removed": stale_removed + size_removed,
                        "cache_size_after": cache_size,
                        "max_size": self.cache_config["max_cache_size"],
                        "utilization_pct": round((cache_size / self.cache_config["max_cache_size"]) * 100, 1),
                        "subscribed_symbols_cached": subscribed_cached,
                        "cache_efficiency": round((subscribed_cached / max(cache_size, 1)) * 100, 1)
                    })
                elif cache_size > self.cache_config["high_water_mark"] * 0.8:
                    # Log warning when approaching high water mark
                    self.logger.warning("mexc_adapter.cache_size_approaching_limit", {
                        "cache_size": cache_size,
                        "high_water_mark": self.cache_config["high_water_mark"],
                        "utilization_pct": round((cache_size / self.cache_config["max_cache_size"]) * 100, 1)
                    })
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("mexc_adapter.cache_cleanup_error", {"error": str(e)})

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
                    if self._cache_access_count.pop(symbol, None) is not None:
                        removed_count += 1
                    if self._cache_access_order.pop(symbol, None) is not None:
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

                if len(self._cache_access_count) > self.MAX_ACCESS_COUNT_ENTRIES:
                    excess = len(self._cache_access_count) - int(self.MAX_ACCESS_COUNT_ENTRIES * 0.8)
                    items = sorted(self._cache_access_count.items(), key=lambda x: x[1])
                    for symbol, _ in items[:excess]:
                        self._cache_access_count.pop(symbol, None)
                        removed_count += 1

                if len(self._cache_access_order) > self.MAX_CACHE_ACCESS_ORDER:
                    excess = len(self._cache_access_order) - int(self.MAX_CACHE_ACCESS_ORDER * 0.8)
                    for _ in range(excess):
                        self._cache_access_order.popitem(last=False)
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
                        "access_count_remaining": len(self._cache_access_count),
                        "lru_order_remaining": len(self._cache_access_order),
                        "debug_rates_remaining": len(self._debug_log_rates)
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("mexc_adapter.tracking_cleanup_error", {"error": str(e)})

    def _update_tracking_expiry(self, symbol: str) -> None:
        """Update expiry time for tracking structures to prevent memory leaks"""
        self._tracking_expiry[symbol] = time.time() + self._max_tracking_age

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

    async def _batch_flush_loop(self) -> None:
        """✅ PERF FIX: Background task to periodically flush event batches"""
        try:
            while self._running:
                await asyncio.sleep(self._batch_flush_interval)
                await self._flush_event_batches()
        except asyncio.CancelledError:
            # Final flush before shutdown
            await self._flush_event_batches()
            raise
        except Exception as e:
            self.logger.error("mexc_adapter.batch_flush_loop_error", {"error": str(e)})

    async def _flush_event_batches(self) -> None:
        """✅ PERF FIX: Flush all pending event batches"""
        async with self._batch_lock:
            # Flush price updates
            if self._price_update_buffer:
                batch = list(self._price_update_buffer)
                self._price_update_buffer.clear()

                # Publish as single batch event
                await self._safe_publish_event("market.price_batch_update", {
                    "exchange": "mexc",
                    "updates": batch,
                    "count": len(batch),
                    "timestamp": time.time()
                }, max_retries=1)  # Lower retries for batch events

            # Flush orderbook updates
            if self._orderbook_update_buffer:
                batch = list(self._orderbook_update_buffer)
                self._orderbook_update_buffer.clear()

                # Publish as single batch event
                await self._safe_publish_event("market.orderbook_batch_update", {
                    "exchange": "mexc",
                    "updates": batch,
                    "count": len(batch),
                    "timestamp": time.time()
                }, max_retries=1)  # Lower retries for batch events

    async def _add_to_price_batch(self, event_data: Dict[str, Any]) -> None:
        """✅ PERF FIX: Add price update to batch buffer"""
        async with self._batch_lock:
            self._price_update_buffer.append(event_data)

            # Check if we need to flush early (size-based flush)
            if len(self._price_update_buffer) >= self._batch_size:
                # Flush immediately if buffer is full
                await self._flush_event_batches()

    async def _add_to_orderbook_batch(self, event_data: Dict[str, Any]) -> None:
        """✅ PERF FIX: Add orderbook update to batch buffer"""
        async with self._batch_lock:
            self._orderbook_update_buffer.append(event_data)

            # Check if we need to flush early (size-based flush)
            if len(self._orderbook_update_buffer) >= self._batch_size:
                # Flush immediately if buffer is full
                await self._flush_event_batches()

    def _remove_from_cache(self, symbol: str) -> None:
        """Remove a symbol from all cache structures - MUST be called with _cache_lock held"""
        self._market_data_cache.pop(symbol, None)
        self._cache_timestamps.pop(symbol, None)
        self._latest_prices.pop(symbol, None)
        self._symbol_volumes.pop(symbol, None)
        self._cache_access_count.pop(symbol, None)
        
        # Remove from LRU tracking - O(1) with OrderedDict
        self._cache_access_order.pop(symbol, None)
    
    def _update_cache_access_unsafe(self, symbol: str) -> None:
        """
        Update LRU access order and access count - MUST be called with _cache_lock held.
        Implements O(1) LRU tracking using OrderedDict to eliminate performance bottleneck.
        """
        # Update LRU order - O(1) operations only
        if symbol in self._cache_access_order:
            self._cache_access_order.move_to_end(symbol)  # O(1)
        else:
            self._cache_access_order[symbol] = True  # O(1)

        # Update access count (bounded to prevent memory growth)
        self._cache_access_count[symbol] = self._cache_access_count.get(symbol, 0) + 1

        # Update expiry for memory leak prevention
        self._update_tracking_expiry(symbol)
        
        # Keep access count strictly bounded - use configurable limit
        max_access_entries = self.MAX_ACCESS_COUNT_ENTRIES
        if len(self._cache_access_count) > max_access_entries:
            # Remove oldest entries based on cache timestamps and LRU order
            excess_count = len(self._cache_access_count) - int(max_access_entries * 0.8)  # Remove to 80% capacity
            removal_candidates = []
            
            # Prioritize removal of symbols not in cache or very old
            current_time = time.time()
            for tracked_symbol in list(self._cache_access_count.keys()):
                if tracked_symbol not in self._market_data_cache:
                    removal_candidates.append(tracked_symbol)
                elif current_time - self._cache_timestamps.get(tracked_symbol, 0) > 3600:  # 1 hour old
                    removal_candidates.append(tracked_symbol)
                
                if len(removal_candidates) >= excess_count:
                    break
            
            # Remove selected candidates
            for old_symbol in removal_candidates[:excess_count]:
                self._cache_access_count.pop(old_symbol, None)
            
            if removal_candidates:
                self.logger.debug("mexc_adapter.access_count_bounded_cleanup", {
                    "removed_entries": len(removal_candidates[:excess_count]),
                    "remaining_entries": len(self._cache_access_count),
                    "max_allowed": max_access_entries
                })
        
        # Keep LRU list strictly bounded - O(1) operations
        max_lru_entries = self.MAX_CACHE_ACCESS_ORDER
        if len(self._cache_access_order) > max_lru_entries:
            # Remove oldest 20% to avoid frequent cleanups - O(1) per removal
            keep_count = int(max_lru_entries * 0.8)
            removed_count = len(self._cache_access_order) - keep_count
            
            # Remove oldest entries efficiently
            for _ in range(removed_count):
                self._cache_access_order.popitem(last=False)  # O(1) remove oldest
            
            self.logger.debug("mexc_adapter.lru_order_bounded_cleanup", {
                "removed_entries": removed_count,
                "remaining_entries": len(self._cache_access_order),
                "max_allowed": max_lru_entries
            })
    
    async def _update_cache_access(self, symbol: str) -> None:
        """CRITICAL FIX: Disabled to reduce CPU usage"""
        # Skip all access tracking to reduce CPU overhead
        pass

    async def _start_access_update_processor(self) -> None:
        """CRITICAL FIX: Disabled to reduce CPU usage"""
        # Skip starting access update processor
        pass

    async def _process_access_updates_batch(self) -> None:
        """CRITICAL FIX: Disabled to reduce CPU usage"""
        # Skip batch processing
        pass

    async def _flush_access_batch(self, batch: List[str]) -> None:
        """Flush a batch of access updates with single lock acquisition"""
        if not batch:
            return
            
        # Deduplicate and count accesses in batch
        access_counts = {}
        for symbol in batch:
            access_counts[symbol] = access_counts.get(symbol, 0) + 1
        
        # Single lock acquisition for entire batch
        async with self._cache_lock:
            for symbol, count in access_counts.items():
                # Update access count
                self._cache_access_count[symbol] = self._cache_access_count.get(symbol, 0) + count

                # Update LRU order - O(1)
                if symbol in self._cache_access_order:
                    self._cache_access_order.move_to_end(symbol)
                else:
                    self._cache_access_order[symbol] = True

                # Update expiry for memory leak prevention
                self._update_tracking_expiry(symbol)
            
            # Periodic cleanup of tracking structures (bounded)
            if len(self._cache_access_count) > self.MAX_ACCESS_COUNT_ENTRIES:
                await self._cleanup_access_tracking_unsafe()
        
        self.logger.debug("mexc_adapter.access_batch_flushed", {
            "batch_size": len(batch),
            "unique_symbols": len(access_counts),
            "total_accesses": sum(access_counts.values())
        })

    async def _cleanup_access_tracking_unsafe(self) -> None:
        """Clean up access tracking structures - MUST be called with _cache_lock held"""
        # Remove access counts for symbols not in cache
        symbols_to_remove = [
            symbol for symbol in self._cache_access_count.keys()
            if symbol not in self._market_data_cache
        ]
        
        for symbol in symbols_to_remove[:100]:  # Limit cleanup batch size
            self._cache_access_count.pop(symbol, None)
            self._cache_access_order.pop(symbol, None)
        
        # Enforce hard limits
        if len(self._cache_access_order) > self.MAX_CACHE_ACCESS_ORDER:
            excess = len(self._cache_access_order) - int(self.MAX_CACHE_ACCESS_ORDER * 0.8)
            for _ in range(excess):
                oldest_symbol = next(iter(self._cache_access_order))
                self._cache_access_order.pop(oldest_symbol, None)

    async def _perform_intelligent_cache_cleanup(self) -> int:
        """
        Perform intelligent cache cleanup when size limits are exceeded.
        Thread-safe with proper locking.
        Returns number of symbols removed.
        """
        async with self._cache_lock:
            cache_size = len(self._market_data_cache)

            # Only cleanup if we exceed high water mark
            if cache_size < self.cache_config["high_water_mark"]:
                return 0
            
            # Calculate how many symbols to remove
            symbols_to_remove = min(
                cache_size - self.cache_config["high_water_mark"] + self.cache_config["cleanup_batch_size"],
                self.cache_config["cleanup_batch_size"]
            )
            
            if symbols_to_remove <= 0:
                return 0
            
            # Get candidates for removal using simple LRU from OrderedDict
            candidates = list(self._cache_access_order.keys())[:symbols_to_remove]
            
            # Remove selected symbols
            removed_count = 0
            removed_symbols = []
            
            for symbol in candidates:
                self._remove_from_cache(symbol)
                removed_symbols.append(symbol)
                removed_count += 1
            
            if removed_count > 0:
                self.logger.info("mexc_adapter.intelligent_cache_cleanup", {
                    "removed_count": removed_count,
                    "cache_size_before": cache_size,
                    "cache_size_after": len(self._market_data_cache),
                    "target_symbols": symbols_to_remove,
                    "high_water_mark": self.cache_config["high_water_mark"],
                    "cleanup_reason": "size_based_intelligent"
                })
            
            return removed_count
    
    async def _safe_add_to_cache(self, symbol: str, market_data: MarketData) -> None:
        """CRITICAL FIX: Simplified cache update to reduce CPU usage"""
        current_time = time.time()

        # CRITICAL FIX: Use simple lock instead of complex RWLock to reduce overhead
        async with self._cache_lock:
            cache_size = len(self._market_data_cache)

            # Simple eviction - just remove oldest if at limit
            if cache_size >= self.cache_config["max_cache_size"]:
                if self._cache_access_order:
                    # Remove oldest entry
                    oldest_symbol = next(iter(self._cache_access_order))
                    self._remove_from_cache(oldest_symbol)
                else:
                    return  # Skip if no eviction possible

            # Simple cache update
            self._market_data_cache[symbol] = market_data
            self._cache_timestamps[symbol] = current_time

            if market_data.price:
                self._latest_prices[symbol] = float(market_data.price)
            if market_data.volume:
                self._symbol_volumes[symbol] = float(market_data.volume)

            # Update LRU order
            if symbol in self._cache_access_order:
                self._cache_access_order.move_to_end(symbol)
            else:
                self._cache_access_order[symbol] = True

            # Update expiry for memory leak prevention
            self._update_tracking_expiry(symbol)

        # CRITICAL FIX: Skip access tracking to reduce CPU overhead
        # await self._update_cache_access(symbol)

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
        """Monitor connection health with precise timing and reliable ping/pong"""
        connection_info = self._connections.get(connection_id)
        if not connection_info:
            return

        # Use monotonic clock for precise timing - TRADING OPTIMIZED
        ping_interval = 20.0  # 20 seconds between pings (faster for trading)
        pong_timeout = 30.0   # 30 seconds to receive pong (must be > ping_interval)
        max_no_data = 120.0   # 2 minutes without any data (faster detection)
        consecutive_timeouts = 0
        max_consecutive_timeouts = 2  # Faster reconnection (reduced from 3)

        last_ping_time = time.monotonic()
        last_data_time = time.monotonic()

        while (self._running and
            connection_id in self._connections and
            self._connections[connection_id]["connected"]):

            try:
                current_time = time.monotonic()

                # Check if it's time to send a ping
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
                        connection_info["last_ping_sent"] = time.time()
                        last_ping_time = current_time

                        self.logger.debug("mexc_adapter.ping_sent", {
                            "connection_id": connection_id,
                            "timestamp": time.time()
                        })

                        # Wait for pong response with timeout - version-aware implementation
                        try:
                            # Check if websockets library supports wait_for_pong() (version 11.0+)
                            if hasattr(websocket, 'wait_for_pong'):
                                await asyncio.wait_for(websocket.wait_for_pong(), timeout=pong_timeout)
                                connection_info["last_pong_received"] = time.time()
                                consecutive_timeouts = 0  # Reset on successful pong

                                self.logger.debug("mexc_adapter.pong_received", {
                                    "connection_id": connection_id,
                                    "timestamp": time.time()
                                })
                            else:
                                # Fallback for older websockets versions - rely on message loop pong detection
                                # The pong will be detected by _handle_message when "pong" channel is received
                                # Wait a short time to allow pong processing, but don't block indefinitely
                                await asyncio.sleep(0.1)  # Brief wait for pong processing

                                # Check if pong was received recently (within reasonable time)
                                last_pong_age = time.time() - connection_info.get("last_pong_received", 0)
                                if last_pong_age < pong_timeout:
                                    consecutive_timeouts = 0  # Reset on recent pong
                                    self.logger.debug("mexc_adapter.pong_detected_via_message_loop", {
                                        "connection_id": connection_id,
                                        "last_pong_age": last_pong_age,
                                        "timestamp": time.time()
                                    })
                                else:
                                    # No recent pong detected
                                    consecutive_timeouts += 1
                                    self.logger.warning("mexc_adapter.no_recent_pong_detected", {
                                        "connection_id": connection_id,
                                        "last_pong_age": last_pong_age,
                                        "consecutive_timeouts": consecutive_timeouts
                                    })

                        except asyncio.TimeoutError:
                            consecutive_timeouts += 1
                            self.logger.warning("mexc_adapter.pong_timeout", {
                                "connection_id": connection_id,
                                "consecutive_timeouts": consecutive_timeouts,
                                "timeout_seconds": pong_timeout
                            })

                            if consecutive_timeouts >= max_consecutive_timeouts:
                                self.logger.error("mexc_adapter.max_pong_timeouts", {
                                    "connection_id": connection_id,
                                    "action": "closing_connection"
                                })
                                await self._close_connection(connection_id)
                                break

                    except Exception as send_error:
                        self.logger.error("mexc_adapter.ping_send_failed", {
                            "connection_id": connection_id,
                            "error": str(send_error)
                        })
                        await self._close_connection(connection_id)
                        break

                # Check for data activity (updated by message loop)
                current_wall_time = time.time()
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

    async def _safe_publish_event(self, event_type: str, data: dict, max_retries: int = 2) -> None:
        """
        Improved event publishing with trading-optimized latency management.
        Trading events bypass normal backpressure controls for zero-loss delivery.
        """
        # Determine if this is a trading-critical event
        is_trading_critical = any(keyword in event_type for keyword in ["deal", "trade", "order", "position"])
        is_high_frequency = any(keyword in event_type for keyword in ["price_update", "orderbook_update", "depth_update"])

        # Trading events get priority path with minimal latency
        if is_trading_critical:
            timeout = 0.05  # 50ms max for trading events
            max_retries = 1  # One fast attempt for trading (was 0 - causing no execution!)
        elif is_high_frequency:
            # Get queue depth for adaptive timeout (if available)
            try:
                queue_depth = await self.event_bus.get_queue_depth(event_type)
            except:
                queue_depth = 0

            # Market data events: fast but allow some queuing
            if queue_depth > 100:
                timeout = 0.1  # Very short timeout under high backpressure
                max_retries = 1  # One fast attempt (was 0 - causing no execution!)
            elif queue_depth > 50:
                timeout = 0.2
                max_retries = 1  # One fast attempt (was 0 - causing no execution!)
            else:
                timeout = 0.5
                max_retries = 1
                timeout = 1.0
                max_retries = 1
        else:
            # Low-frequency events: more tolerant
            # Get queue depth for timeout decision
            try:
                queue_depth = await self.event_bus.get_queue_depth(event_type)
            except:
                queue_depth = 0
            
            timeout = 2.0 if queue_depth < 10 else 1.0
            max_retries = max_retries
        
        # Track dropped events for monitoring
        for attempt in range(max_retries):
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
    
    async def _handle_futures_subscription_response(self, data: dict, connection_id: int) -> None:
        """Handle futures subscription/unsubscription responses"""
        channel = data.get("channel", "")
        response_data = data.get("data", "")
        
        # Handle different types of subscription responses
        if channel == "rs.sub.deal":
            if response_data == "success":
                # Find which symbol this confirmation is for
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    # Find first symbol with pending deal subscription
                    confirmed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('deal') == 'pending':
                            status['deal'] = 'confirmed'
                            confirmed_symbol = symbol
                            break

                    if confirmed_symbol:
                        # Check if both subscriptions are now confirmed
                        if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                            pending_symbols[confirmed_symbol].get('depth') == 'confirmed'):
                            # Both confirmed, remove from pending
                            del pending_symbols[confirmed_symbol]
                            if not pending_symbols:
                                del self._pending_subscriptions[connection_id]

                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": confirmed_symbol,
                            "subscription_type": "deals",
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                    else:
                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": "unknown",
                            "subscription_type": "deals",
                            "pending_count": 0
                        })
                else:
                    self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "deals",
                        "pending_count": 0
                    })
            else:
                # Handle subscription failure
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    failed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('deal') == 'pending':
                            status['deal'] = 'failed'
                            failed_symbol = symbol
                            break

                    if failed_symbol:
                        self.logger.error("mexc_adapter.futures_subscription_failed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": failed_symbol,
                            "subscription_type": "deals",
                            "error": response_data,
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                else:
                    self.logger.error("mexc_adapter.futures_subscription_failed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "deals",
                        "error": response_data,
                        "pending_count": 0
                    })
        elif channel == "rs.sub.depth":
            if response_data == "success":
                # Find which symbol this confirmation is for
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    confirmed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('depth') == 'pending':
                            status['depth'] = 'confirmed'
                            confirmed_symbol = symbol
                            break

                    if confirmed_symbol:
                        # Check if both subscriptions are now confirmed
                        if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
                            pending_symbols[confirmed_symbol].get('depth') == 'confirmed'):
                            # Both confirmed, remove from pending
                            del pending_symbols[confirmed_symbol]
                            if not pending_symbols:
                                del self._pending_subscriptions[connection_id]

                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": confirmed_symbol,
                            "subscription_type": "depth",
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                    else:
                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": "unknown",
                            "subscription_type": "depth",
                            "pending_count": 0
                        })
                else:
                    self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "depth",
                        "pending_count": 0
                    })
            else:
                # Handle depth subscription failure
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    failed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('depth') == 'pending':
                            status['depth'] = 'failed'
                            failed_symbol = symbol
                            break

                    if failed_symbol:
                        self.logger.error("mexc_adapter.futures_subscription_failed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": failed_symbol,
                            "subscription_type": "depth",
                            "error": response_data,
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                else:
                    self.logger.error("mexc_adapter.futures_subscription_failed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "depth",
                        "error": response_data,
                        "pending_count": 0
                    })
        elif channel == "rs.sub.depth.full":
            if response_data == "success":
                # Find which symbol this confirmation is for
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    confirmed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('depth_full') == 'pending':
                            status['depth_full'] = 'confirmed'
                            confirmed_symbol = symbol
                            break

                    if confirmed_symbol:
                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": confirmed_symbol,
                            "subscription_type": "depth.full",
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                        
                        # Start periodic snapshot refresh task for this symbol
                        await self._start_snapshot_refresh_task(confirmed_symbol)
                    else:
                        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": "unknown",
                            "subscription_type": "depth.full",
                            "pending_count": 0
                        })
                else:
                    self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "depth.full",
                        "pending_count": 0
                    })
            else:
                # Handle depth.full subscription failure
                pending_symbols = self._pending_subscriptions.get(connection_id, {})
                if pending_symbols:
                    failed_symbol = None
                    for symbol, status in pending_symbols.items():
                        if status.get('depth_full') == 'pending':
                            status['depth_full'] = 'failed'
                            failed_symbol = symbol
                            break

                    if failed_symbol:
                        self.logger.error("mexc_adapter.futures_subscription_failed", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "symbol": failed_symbol,
                            "subscription_type": "depth.full",
                            "error": response_data,
                            "pending_count": len([s for s, st in pending_symbols.items() if st.get('deal') == 'pending' or st.get('depth') == 'pending' or st.get('depth_full') == 'pending'])
                        })
                else:
                    self.logger.error("mexc_adapter.futures_subscription_failed", {
                        "connection_id": connection_id,
                        "channel": channel,
                        "symbol": "unknown",
                        "subscription_type": "depth.full",
                        "error": response_data,
                        "pending_count": 0
                    })
        elif channel == "rs.error":
            self.logger.error("mexc_adapter.futures_error_response", {
                "connection_id": connection_id,
                "error": response_data
            })
        elif channel.startswith("rs."):
            # Log any other rs. responses for debugging
            self.logger.debug("mexc_adapter.futures_subscription_response", {
                "connection_id": connection_id,
                "channel": channel,
                "data": response_data
            })
        else:
            # This might be a different type of message
            self.logger.debug("mexc_adapter.unknown_futures_response", {
                "connection_id": connection_id,
                "channel": channel,
                "data": response_data
            })
    
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
                    # Update legacy caches (for backward compatibility)
                    self._latest_prices[symbol] = price
                    self._symbol_volumes[symbol] = volume
                    
                    # Create market data object
                    market_data_obj = MarketData(
                        symbol=symbol,
                        price=Decimal(str(price)),
                        volume=Decimal(str(volume)),
                        timestamp=datetime.fromtimestamp(timestamp / 1000) if timestamp else datetime.now(),
                        exchange="mexc",
                        side="buy" if deal_type == 1 else "sell" if deal_type == 2 else None
                    )
                    
                    # Use thread-safe intelligent cache management
                    await self._safe_add_to_cache(symbol, market_data_obj)
                    
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
                    
                    # ✅ PERF FIX: Use batching for price updates instead of individual events
                    event_data = {
                        "exchange": "mexc",
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "quote_volume": price * volume,
                        "timestamp": event_timestamp,  # Use MEXC timestamp when available
                        "side": "buy" if deal_type == 1 else "sell",
                        "source": "futures_deal",
                        "market_data": market_data_obj,
                        "mexc_timestamp": timestamp,  # Original MEXC timestamp in ms
                        "system_timestamp": time.time()  # Our system timestamp for comparison
                    }

                    if self._event_batching_enabled:
                        # Add to batch buffer - will be flushed automatically
                        await self._add_to_price_batch(event_data)
                    else:
                        # Fallback to individual publish if batching disabled
                        await self._safe_publish_event("market.price_update", event_data)
                    
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
                    # Update cache
                    self._latest_prices[symbol] = price
                    self._symbol_volumes[symbol] = volume
                    
                    # Create market data object - for regular market data without trade side info
                    market_data_obj = MarketData(
                        symbol=symbol,
                        price=Decimal(str(price)),
                        volume=Decimal(str(volume)),
                        timestamp=datetime.fromtimestamp(timestamp / 1000) if timestamp else datetime.now(),
                        exchange="mexc",
                        side=None  # No side information in regular market data
                    )
                    
                    # Publish price update event via EventBus
                    await self._safe_publish_event("market.price_update", {
                        "exchange": "mexc",
                        "symbol": symbol,
                        "price": price,
                        "volume": volume,
                        "timestamp": time.time(),
                        "side": side,
                        "quote_volume": price * volume,
                        "source": "deals",
                        "market_data": market_data_obj
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
            async with self._orderbook_lock:
                if symbol not in self._orderbook_cache:
                    self._orderbook_cache[symbol] = {
                        "bids": [],
                        "asks": [],
                        "timestamp": time.time()
                    }
                
                cache_entry = self._orderbook_cache[symbol]
                current_time = time.time()
                
                # Update cache with new data (only if we received that side)
                if bids:  # Update bids only if MEXC sent them
                    cache_entry["bids"] = bids
                if asks:  # Update asks only if MEXC sent them  
                    cache_entry["asks"] = asks
                
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
            
            async with self._orderbook_lock:
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
            
            async with self._orderbook_lock:
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
            async with self._orderbook_lock:
                cache_entry = self._orderbook_cache.get(symbol)
                if not cache_entry:
                    return
                
                # Convert OrderedDict back to list format for publishing with numeric prices
                bids = [(float(price), qty) for price, qty in cache_entry["bids"].items()]
                asks = [(float(price), qty) for price, qty in cache_entry["asks"].items()]
                
                if not bids and not asks:
                    return

                # ✅ PERF FIX: Use batching for orderbook updates
                event_data = {
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
                }

                if self._event_batching_enabled:
                    # Add to batch buffer - will be flushed automatically
                    await self._add_to_orderbook_batch(event_data)
                else:
                    # Fallback to individual publish if batching disabled
                    await self._safe_publish_event("market.orderbook_update", event_data)
                
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
                
                # Add to pending subscriptions BEFORE sending to prevent race conditions
                if connection_id not in self._pending_subscriptions:
                    self._pending_subscriptions[connection_id] = {}
                self._pending_subscriptions[connection_id][symbol] = {'deal': 'pending', 'depth': 'pending', 'depth_full': 'pending', 'added_time': time.time()}

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
        """Send subscription message for a symbol"""
        connection_info = self._connections.get(connection_id)
        if not connection_info or not connection_info["connected"]:
            raise RuntimeError(f"Connection {connection_id} not available")

        websocket = connection_info["websocket"]
        
        # Subscribe to deals (price data)
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
        
        # Subscribe to order book depth with full snapshot first, then deltas
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
        
        Args:
            symbol: Trading symbol to unsubscribe from
        """
        symbol = symbol.upper()
        
        if symbol not in self._subscribed_symbols:
            self.logger.debug("mexc_adapter.not_subscribed", {"symbol": symbol})
            return
        
        try:
            connection_id = self._symbol_to_connection.get(symbol)
            if connection_id is not None and connection_id in self._connections:
                connection_info = self._connections[connection_id]
                
                if connection_info["connected"]:
                    # Send unsubscription messages for both channels (futures format)
                    websocket = connection_info["websocket"]
                    
                    # Unsubscribe from price/deal data
                    deal_unsubscription = {
                        "method": "unsub.deal",
                        "param": {
                            "symbol": symbol
                        }
                    }
                    await websocket.send(json.dumps(deal_unsubscription))
                    
                    # Unsubscribe from order book data
                    depth_unsubscription = {
                        "method": "unsub.depth",
                        "param": {
                            "symbol": symbol
                        }
                    }
                    await websocket.send(json.dumps(depth_unsubscription))
                
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
        
        # Clean up subscriptions
        for symbol in list(connection_info["subscriptions"]):
            self._subscribed_symbols.discard(symbol)
            self._symbol_to_connection.pop(symbol, None)
        
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
        
        # Cancel cache cleanup task
        if self._cache_cleanup_task and not self._cache_cleanup_task.done():
            self._cache_cleanup_task.cancel()

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
            
        # OPTIMIZED: Stop access update processor (disabled for CPU optimization)
        # Access update task is disabled to reduce CPU usage
        if self._cache_cleanup_task and not self._cache_cleanup_task.done():
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection_id in list(self._connections.keys()):
            await self._close_connection(connection_id)
        
        # Clear caches with proper locking
        async with self._cache_lock:
            self._market_data_cache.clear()
            self._cache_timestamps.clear()
            self._latest_prices.clear()
            self._symbol_volumes.clear()
            self._cache_access_count.clear()
            self._cache_access_order.clear()
        
        # Clear debug log rates and message counter
        self._debug_log_rates.clear()
        self._message_count = 0

        # Clear tracking structures
        self._reconnection_attempts.clear()
        self._cache_access_count.clear()
        self._cache_access_order.clear()
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
        """Lock-free read for high-performance access"""
        symbol = symbol.upper()

        # Lock-free read - acceptable in high-frequency scenarios
        # Race condition acceptable: stale data is better than blocking
        market_data = self._market_data_cache.get(symbol)

        # Skip access tracking to reduce CPU overhead
        # await self._update_cache_access(symbol)

        return market_data
    
    # Removed duplicate method definitions - using implementations at end of file
    
    async def health_check(self) -> bool:
        """Check adapter health"""
        return self._running and len(self._connections) > 0
    
    async def get_market_data_stream(self, symbol: str):
        """Get real-time market data stream - use EventBus subscription instead"""
        raise NotImplementedError("Use EventBus subscription to 'market.price_update' instead")
    
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
        
        # Add cache metrics
        cache_hit_symbols = len(self._market_data_cache)
        total_subscribed = len(self._subscribed_symbols)
        cache_hit_ratio = (cache_hit_symbols / max(total_subscribed, 1)) * 100
        
        current_time = time.time()
        fresh_cache_count = sum(
            1 for timestamp in self._cache_timestamps.values()
            if current_time - timestamp < 300  # Fresh if less than 5 minutes old
        )
        
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
            },
            "cache": {
                "cached_symbols": cache_hit_symbols,
                "cache_hit_ratio_pct": cache_hit_ratio,
                "fresh_cache_entries": fresh_cache_count,
                "stale_cache_entries": cache_hit_symbols - fresh_cache_count,
                "avg_cache_age_seconds": sum(
                    current_time - timestamp 
                    for timestamp in self._cache_timestamps.values()
                ) / max(len(self._cache_timestamps), 1),
                # OPTIMIZED: Lock contention analysis (disabled for CPU optimization)
                "access_tracking": {
                    "batched_updates": False,
                    "pending_updates": 0,
                    "access_processor_active": False,
                    "tracked_symbols": len(self._cache_access_count),
                    "lru_entries": len(self._cache_access_order),
                    "queue_utilization_pct": 0,
                    "lock_contention_mitigation": "disabled_for_cpu_optimization"
                }
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
        """Get comprehensive cache statistics for monitoring and optimization - Thread Safe"""
        current_time = time.time()
        
        # OPTIMIZED: Extract data quickly from critical section
        async with self._cache_lock:
            cache_size = len(self._market_data_cache)
            cached_symbols = set(self._market_data_cache.keys())
            cache_timestamps = dict(self._cache_timestamps)
            access_counts = dict(self._cache_access_count)
        
        # OPTIMIZED: Use cached intersection when possible
        total_subscribed = len(self._subscribed_symbols)
        current_time = time.time()
        if current_time - self._last_intersection_time > 30:
            self._cached_intersection = cached_symbols & self._subscribed_symbols
            self._last_intersection_time = current_time
        subscribed_cached = len(self._cached_intersection)
        
        # Age distribution
        age_buckets = {"<1h": 0, "1-6h": 0, "6-24h": 0, ">24h": 0}
        for timestamp in cache_timestamps.values():
            age_hours = (current_time - timestamp) / 3600
            if age_hours < 1:
                age_buckets["<1h"] += 1
            elif age_hours < 6:
                age_buckets["1-6h"] += 1
            elif age_hours < 24:
                age_buckets["6-24h"] += 1
            else:
                age_buckets[">24h"] += 1
        
        # Access frequency analysis
        avg_access = sum(access_counts.values()) / max(len(access_counts), 1)
        
        symbols_needing_cleanup = len([
            s for s, t in cache_timestamps.items()
            if current_time - t > 600  # Older than 10 minutes
        ])
        
        return {
            "size": {
                "current_size": cache_size,
                "max_size": self.cache_config["max_cache_size"],
                "utilization_pct": round((cache_size / self.cache_config["max_cache_size"]) * 100, 1),
                "high_water_mark": self.cache_config["high_water_mark"]
            },
            "efficiency": {
                "subscribed_symbols_cached": subscribed_cached,
                "total_subscribed_symbols": total_subscribed,
                "cache_hit_ratio_pct": round((subscribed_cached / max(total_subscribed, 1)) * 100, 1),
                "avg_access_per_symbol": round(avg_access, 1),
                "tracking_overhead": len(self._cache_access_count)
            },
            "age_distribution": age_buckets,
            "health": {
                "symbols_needing_cleanup": symbols_needing_cleanup,
                "memory_pressure": cache_size >= self.cache_config["high_water_mark"],
                "config_valid": self.cache_config["max_cache_size"] > 0,
                "thread_safety": "enabled"
            },
            "config": self.cache_config
        }

    # Abstract method implementations required by IMarketDataProvider
    
    async def get_market_data_stream(self, symbol: str):
        """
        Get real-time market data stream for a symbol.
        Returns an async iterator that yields market data as it arrives.
        """
        # Create a queue to buffer incoming data for this symbol
        data_queue = asyncio.Queue(maxsize=100)

        # Subscribe to market data events for this symbol
        def market_data_handler(event_type: str, data: dict):
            """Handle incoming market data events"""
            try:
                if event_type in ["market.price_update", "market.orderbook_update"]:
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
                    "event_type": event_type,
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
            try:
                # Check if subscribed before unsubscribing to avoid warnings
                subscribers = await self.event_bus.get_subscribers()
                if "market.price_update" in subscribers and market_data_handler in [s.handler_name for s in subscribers["market.price_update"]]:
                    self.event_bus.unsubscribe("market.price_update", market_data_handler)
                if "market.orderbook_update" in subscribers and market_data_handler in [s.handler_name for s in subscribers["market.orderbook_update"]]:
                    self.event_bus.unsubscribe("market.orderbook_update", market_data_handler)
            except Exception:
                pass
    
    
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
        """Refresh orderbook cache from MEXC REST API"""
        try:
            rest_url = f"https://api.mexc.com/api/v3/depth?symbol={symbol}&limit=20"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rest_url, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse REST response 
                        bids_raw = data.get("bids", [])
                        asks_raw = data.get("asks", [])
                        
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
                            async with self._orderbook_lock:
                                if symbol not in self._orderbook_cache:
                                    self._orderbook_cache[symbol] = {
                                        "bids": [],
                                        "asks": [],
                                        "timestamp": time.time()
                                    }
                                
                                cache_entry = self._orderbook_cache[symbol]
                                cache_entry["bids"] = bids
                                cache_entry["asks"] = asks
                                cache_entry["timestamp"] = time.time()
                                
                            self.logger.debug("mexc_adapter.orderbook_refreshed_from_rest", {
                                "symbol": symbol,
                                "bids_count": len(bids),
                                "asks_count": len(asks)
                            })
                    else:
                        self.logger.warning("mexc_adapter.rest_orderbook_failed", {
                            "symbol": symbol,
                            "status": response.status
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
                    async with self._orderbook_lock:
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

    async def _request_websocket_snapshot(self, symbol: str) -> bool:
        """Request fresh snapshot via WebSocket for a symbol"""
        try:
            connection_id = self._symbol_to_connection.get(symbol)
            if not connection_id or connection_id not in self._connections:
                self.logger.warning("mexc_adapter.no_connection_for_snapshot", {
                    "symbol": symbol
                })
                return False
            
            connection_info = self._connections[connection_id]
            websocket = connection_info.get("websocket")
            
            if not websocket or websocket.closed:
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

