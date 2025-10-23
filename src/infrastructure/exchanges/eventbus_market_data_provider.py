"""
EventBus-backed Market Data Provider
===================================
Lightweight adapter implementing IMarketDataProvider by subscribing to
EventBus events (e.g., "price_update") emitted by existing connectors.
"""

import asyncio
import time
from typing import AsyncIterator, Optional, Dict, Any, Set
from datetime import datetime

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.models.market_data import MarketData


class EventBusMarketDataProvider(IMarketDataProvider):
    def __init__(self, event_bus: EventBus, logger: StructuredLogger, exchange_name: str = "generic"):
        self._event_bus = event_bus
        self._logger = logger
        self._exchange = exchange_name
        self._connected = False
        
        # MEMORY SAFE: Controlled resource creation instead of defaultdict
        self._queues: Dict[str, asyncio.Queue] = {}  # No defaultdict to prevent memory leaks
        self._allowed_symbols: Set[str] = set()  # Explicit symbol allowlist
        self._last_activity: Dict[str, float] = {}  # Track last activity for TTL
        self._queue_ttl = 3600  # 1 hour TTL for inactive queues
        self._last_cleanup_time = time.time()
        
        # Safety limits to prevent resource exhaustion
        self.MAX_SYMBOLS = 1000
        self.MAX_QUEUE_SIZE = 1000
        self.CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

    async def connect(self) -> None:
        if self._connected:
            return
        # Subscribe once; route events by symbol into per-symbol queues
        import asyncio
        asyncio.create_task(self._event_bus.subscribe("price_update", self._on_price_update))
        self._connected = True
        self._logger.info("market_data_provider.connected", {"exchange": self._exchange})

    async def disconnect(self) -> None:
        """
        Proper disconnect with resource cleanup.
        MEMORY SAFE: Cleans up all resources during disconnect.
        """
        self._connected = False
        
        # Cleanup all resources
        before_count = len(self._queues)
        
        # Drain all queues before cleanup
        total_drained = 0
        for symbol, queue in self._queues.items():
            drained_count = 0
            while not queue.empty():
                try:
                    queue.get_nowait()
                    drained_count += 1
                except asyncio.QueueEmpty:
                    break
            total_drained += drained_count
        
        # Clear all tracking structures
        self._queues.clear()
        self._allowed_symbols.clear()
        
        self._logger.info("market_data_provider.disconnected", {
            "exchange": self._exchange,
            "queues_cleaned": before_count,
            "events_drained": total_drained
        })

    async def subscribe_to_symbol(self, symbol: str) -> None:
        """
        Controlled queue creation - only for explicitly requested symbols.
        MEMORY SAFE: Explicit business logic controls resource creation.
        """
        # Check symbol limits to prevent resource exhaustion
        if len(self._queues) >= self.MAX_SYMBOLS:
            raise ValueError(f"Too many symbols subscribed: {len(self._queues)}/{self.MAX_SYMBOLS}")
        
        # Controlled resource creation - only when explicitly requested
        if symbol not in self._queues:
            self._queues[symbol] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            self._allowed_symbols.add(symbol)
            self._logger.info("market_data_provider.symbol_subscribed", {
                "symbol": symbol,
                "total_symbols": len(self._queues)
            })
        
        self._logger.debug("market_data_provider.subscribe", {"symbol": symbol})

    async def unsubscribe_from_symbol(self, symbol: str) -> None:
        """
        Proper resource cleanup with verification.
        MEMORY SAFE: Explicit cleanup removes resources completely.
        """
        if symbol in self._queues:
            # Drain queue before removal to prevent memory leaks
            queue = self._queues[symbol]
            drained_count = 0
            while not queue.empty():
                try:
                    queue.get_nowait()
                    drained_count += 1
                except asyncio.QueueEmpty:
                    break
            
            # Remove from tracking structures
            del self._queues[symbol]
            self._allowed_symbols.discard(symbol)
            
            self._logger.info("market_data_provider.symbol_unsubscribed", {
                "symbol": symbol,
                "drained_events": drained_count,
                "remaining_symbols": len(self._queues)
            })
        else:
            self._logger.warning("market_data_provider.unsubscribe_unknown_symbol", {
                "symbol": symbol
            })
        
        self._logger.debug("market_data_provider.unsubscribe", {"symbol": symbol})

    async def get_market_data_stream(self, symbol: str) -> AsyncIterator[MarketData]:
        """
        Get market data stream with periodic cleanup.
        MEMORY SAFE: Includes cleanup checks during normal operation.
        """
        if symbol not in self._queues:
            self._logger.warning("market_data_provider.stream_requested_unsubscribed_symbol", {
                "symbol": symbol
            })
            return
        
        q = self._queues[symbol]
        while self._connected:
            # Periodic cleanup during operation
            if self._should_cleanup():
                await self._cleanup_resources()
            
            try:
                event = await asyncio.wait_for(q.get(), timeout=1.0)  # Add timeout to allow periodic cleanup
            except asyncio.TimeoutError:
                continue  # Allow cleanup check
            
            try:
                # Map event payload - handle both dataclass and dict formats
                if hasattr(event, "price"):  # dataclass PriceEvent
                    price = float(event.price)
                    volume = float(event.volume)
                    ts = event.timestamp_local
                    volume_24h = getattr(event, "volume_24h_usdt", 0.0)
                else:  # dict format
                    price = float(event.get("price"))
                    volume = float(event.get("volume", 0))
                    ts = event.get("timestamp")
                    volume_24h = event.get("volume_24h_usdt")

                md = MarketData(
                    symbol=symbol,
                    exchange=self._exchange,
                    timestamp=datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow(),
                    price=price,
                    volume=volume,
                    volume_24h_usdt=volume_24h,
                )
                yield md
            except Exception as e:
                self._logger.error("market_data_provider.event_parse_error", {"error": str(e)})

    async def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        # Best-effort: non-blocking get if available
        q = self._queues.get(symbol)
        if not q or q.empty():
            return None
        try:
            event = q.get_nowait()
        except Exception:
            return None
        # Reuse converter via a tiny wrapper
        try:
            # Handle both dataclass and dict formats
            if hasattr(event, "price"):  # dataclass PriceEvent
                price = float(event.price)
                volume = float(event.volume)
                ts = event.timestamp_local
                volume_24h = getattr(event, "volume_24h_usdt", 0.0)
            else:  # dict format
                price = float(event.get("price"))
                volume = float(event.get("volume", 0))
                ts = event.get("timestamp")
                volume_24h = event.get("volume_24h_usdt")
            
            return MarketData(
                symbol=symbol,
                exchange=self._exchange,
                timestamp=datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow(),
                price=price,
                volume=volume,
                volume_24h_usdt=volume_24h,
            )
        except Exception:
            return None

    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        # Not tracked centrally; return None
        return None

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        return None

    async def is_symbol_active(self, symbol: str) -> bool:
        return True

    def get_exchange_name(self) -> str:
        return self._exchange

    async def health_check(self) -> bool:
        """Legacy health check method for backward compatibility"""
        health_status = await self.health_check()
        return health_status.get("healthy", False)

    async def _on_price_update(self, event: Any):
        """
        Process price updates with controlled resource access.
        MEMORY SAFE: Only processes events for explicitly allowed symbols.
        """
        try:
            symbol = getattr(event, "symbol", None) or event.get("symbol")
            if not symbol:
                return
            
            # CRITICAL: Only process events for explicitly subscribed symbols
            if symbol not in self._allowed_symbols:
                return  # Ignore events for non-subscribed symbols
            
            # Enqueue event only if queue exists (defensive check)
            if symbol in self._queues:
                queue = self._queues[symbol]
                try:
                    await asyncio.wait_for(queue.put(event), timeout=0.1)  # Prevent blocking
                    self._last_activity[symbol] = time.time()  # Update activity timestamp
                except asyncio.TimeoutError:
                    self._logger.warning("market_data_provider.queue_full", {
                        "symbol": symbol,
                        "queue_size": queue.qsize()
                    })
        except Exception as e:
            self._logger.error("market_data_provider.enqueue_error", {"error": str(e)})
    
    def _should_cleanup(self) -> bool:
        """Check if periodic cleanup should be performed"""
        return time.time() - self._last_cleanup_time > self.CLEANUP_INTERVAL_SECONDS
    
    async def _cleanup_resources(self):
        """
        Periodic cleanup of resources.
        MEMORY SAFE: Removes empty queues and orphaned resources.
        """
        before_count = len(self._queues)
        
        # Remove empty queues for symbols that are no longer needed
        empty_queues = [
            symbol for symbol, queue in self._queues.items()
            if queue.empty() and symbol not in self._allowed_symbols
        ]
        # Add TTL check
        inactive_queues = [
            symbol for symbol in self._queues.keys()
            if time.time() - self._last_activity.get(symbol, 0) > self._queue_ttl
        ]
        empty_queues.extend(inactive_queues)
        
        for symbol in empty_queues:
            del self._queues[symbol]
        
        # Cleanup allowed symbols that no longer have queues
        orphaned_symbols = self._allowed_symbols - set(self._queues.keys())
        for symbol in orphaned_symbols:
            self._allowed_symbols.discard(symbol)
        
        after_count = len(self._queues)
        self._last_cleanup_time = time.time()
        
        if empty_queues or orphaned_symbols:
            self._logger.info("market_data_provider.cleanup_completed", {
                "empty_queues_removed": len(empty_queues),
                "orphaned_symbols_removed": len(orphaned_symbols),
                "queues_before": before_count,
                "queues_after": after_count
            })
    
    def get_memory_stats(self) -> Dict[str, int]:
        """
        MANDATORY PATTERN: Memory monitoring for production readiness.
        """
        return {
            "queues_count": len(self._queues),
            "allowed_symbols_count": len(self._allowed_symbols),
            "total_queue_sizes": sum(queue.qsize() for queue in self._queues.values()),
            "max_queue_size": max((queue.qsize() for queue in self._queues.values()), default=0)
        }
    
    async def get_detailed_health_status(self) -> Dict[str, Any]:
        """
        MANDATORY PATTERN: Detailed health check with memory statistics.
        """
        memory_stats = self.get_memory_stats()
        
        # Check for potential memory issues
        alerts = []
        if memory_stats["queues_count"] > self.MAX_SYMBOLS * 0.8:
            alerts.append(f"High symbol count: {memory_stats['queues_count']}/{self.MAX_SYMBOLS}")
        
        if memory_stats["max_queue_size"] > self.MAX_QUEUE_SIZE * 0.8:
            alerts.append(f"Large queue detected: {memory_stats['max_queue_size']}")
        
        return {
            "healthy": self._connected and len(alerts) == 0,
            "connected": self._connected,
            "exchange": self._exchange,
            "memory_stats": memory_stats,
            "alerts": alerts
        }
    
    async def health_check(self) -> bool:
        """Interface-required health check method"""
        health_status = await self.get_detailed_health_status()
        return health_status.get("healthy", False)

