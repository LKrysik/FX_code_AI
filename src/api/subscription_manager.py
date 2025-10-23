"""
Subscription Manager
===================
Manages client subscriptions to real-time data streams with intelligent filtering.
Production-ready with performance optimization and memory management.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import time
import re

from ..core.logger import StructuredLogger


class SubscriptionType(str, Enum):
    """Available subscription types"""

    # Market data
    MARKET_DATA = "market_data"
    ORDERBOOK = "orderbook"
    TRADES = "trades"

    # Technical analysis
    INDICATORS = "indicators"
    SIGNALS = "signals"

    # Trading
    POSITIONS = "positions"
    ORDERS = "orders"
    PORTFOLIO = "portfolio"

    # Execution
    EXECUTION_STATUS = "execution_status"
    EXECUTION_METRICS = "execution_metrics"

    # System
    SYSTEM_HEALTH = "system_health"
    LOGS = "logs"


@dataclass
class SubscriptionFilter:
    """Filter criteria for subscriptions"""

    # Symbol filtering
    symbols: Optional[List[str]] = None
    exclude_symbols: Optional[List[str]] = None

    # Data type filtering
    data_types: Optional[List[str]] = None

    # Timeframe filtering
    timeframes: Optional[List[str]] = None

    # Indicator specific
    indicator_types: Optional[List[str]] = None
    indicator_periods: Optional[List[int]] = None

    # Signal filtering
    signal_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None

    # Performance filters
    min_volume: Optional[float] = None
    min_price_change: Optional[float] = None

    # Custom filters
    custom_filters: Dict[str, Any] = field(default_factory=dict)

    def matches_symbol(self, symbol: str) -> bool:
        """Check if symbol matches filter criteria"""
        if self.exclude_symbols and symbol in self.exclude_symbols:
            return False

        if self.symbols:
            return symbol in self.symbols

        return True

    def matches_data_type(self, data_type: str) -> bool:
        """Check if data type matches filter"""
        if not self.data_types:
            return True
        return data_type in self.data_types

    def matches_timeframe(self, timeframe: str) -> bool:
        """Check if timeframe matches filter"""
        if not self.timeframes:
            return True
        return timeframe in self.timeframes

    def matches_indicator(self, indicator_type: str, period: Optional[int] = None) -> bool:
        """Check if indicator matches filter"""
        if self.indicator_types and indicator_type not in self.indicator_types:
            return False

        if self.indicator_periods and period and period not in self.indicator_periods:
            return False

        return True

    def matches_signal(self, signal_type: str, confidence: Optional[float] = None) -> bool:
        """Check if signal matches filter"""
        if self.signal_types and signal_type not in self.signal_types:
            return False

        if confidence is not None:
            if self.min_confidence and confidence < self.min_confidence:
                return False
            if self.max_confidence and confidence > self.max_confidence:
                return False

        return True

    def matches_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """Check if market data matches filter"""
        if not self.matches_symbol(symbol):
            return False

        # Volume filter
        if self.min_volume:
            volume = data.get('volume', 0)
            if volume < self.min_volume:
                return False

        # Price change filter
        if self.min_price_change:
            price_change = abs(data.get('change_24h', 0))
            if price_change < self.min_price_change:
                return False

        return True


@dataclass
class ClientSubscription:
    """Client subscription with metadata"""

    client_id: str
    subscription_type: str
    filters: SubscriptionFilter
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_active: bool = True
    awaiting_confirmation: bool = False

    # Performance tracking
    messages_sent: int = 0
    messages_filtered: int = 0
    bandwidth_used: int = 0

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def record_message(self, size_bytes: int, filtered: bool = False):
        """Record message delivery"""
        self.message_count += 1
        self.messages_sent += 1
        self.bandwidth_used += size_bytes

        if filtered:
            self.messages_filtered += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        return {
            "messages_sent": self.messages_sent,
            "messages_filtered": self.messages_filtered,
            "bandwidth_used": self.bandwidth_used,
            "efficiency": (self.messages_sent - self.messages_filtered) / max(self.messages_sent, 1),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class SubscriptionManager:
    """
    Manages client subscriptions with intelligent filtering and performance optimization.

    Features:
    - Subscription lifecycle management
    - Intelligent filtering based on client preferences
    - Performance monitoring and optimization
    - Memory-efficient storage
    - Automatic cleanup of inactive subscriptions
    """

    def __init__(self,
                 max_subscriptions_per_client: int = 100,
                 cleanup_interval_seconds: int = 300,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize SubscriptionManager.

        Args:
            max_subscriptions_per_client: Maximum subscriptions per client
            cleanup_interval_seconds: Interval for cleanup operations
            logger: Optional logger instance
        """
        self.max_subscriptions_per_client = max_subscriptions_per_client
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.logger = logger

        # Subscription storage - client_id -> subscription_type -> ClientSubscription
        self.client_subscriptions: Dict[str, Dict[str, ClientSubscription]] = {}

        # Reverse lookup - subscription_type -> set of client_ids
        self.subscription_clients: Dict[str, Set[str]] = {}

        # Thread safety for subscription operations
        self._subscription_lock = asyncio.Lock()

        # Performance tracking
        self.total_subscriptions_created = 0
        self.total_subscriptions_removed = 0
        self.total_messages_processed = 0
        self.total_messages_filtered = 0

        # Cleanup management
        self.cleanup_task: Optional[asyncio.Task] = None
        self._is_shutting_down = False
        self._last_cleanup_time = time.time()

    async def start(self):
        """Start subscription manager"""
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_subscriptions())
        if self.logger:
            self.logger.info("subscription_manager.started", {
                "max_subscriptions_per_client": self.max_subscriptions_per_client,
                "cleanup_interval": self.cleanup_interval_seconds
            })

    async def stop(self):
        """Stop subscription manager"""
        self._is_shutting_down = True
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear all subscriptions
        self.client_subscriptions.clear()
        self.subscription_clients.clear()

        if self.logger:
            self.logger.info("subscription_manager.stopped")

    async def subscribe_client(self,
                              client_id: str,
                              subscription_type: str,
                              filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Subscribe client to data stream with thread-safe operations.

        Args:
            client_id: Client ID
            subscription_type: Type of data to subscribe to
            filters: Optional filter criteria

        Returns:
            True if subscription successful, False otherwise
        """
        async with self._subscription_lock:
            # Check subscription limits
            if client_id in self.client_subscriptions:
                current_count = len(self.client_subscriptions[client_id])
                if current_count >= self.max_subscriptions_per_client:
                    if self.logger:
                        self.logger.warning("subscription_manager.limit_exceeded", {
                            "client_id": client_id,
                            "current_subscriptions": current_count,
                            "max_subscriptions": self.max_subscriptions_per_client
                        })
                    return False

            # Check if already subscribed
            if (client_id in self.client_subscriptions and
                subscription_type in self.client_subscriptions[client_id]):
                # Update existing subscription
                existing = self.client_subscriptions[client_id][subscription_type]
                if filters:
                    existing.filters = self._parse_filters(filters)
                existing.update_activity()
                return True

            # Parse filters
            subscription_filters = self._parse_filters(filters or {})

            # Create subscription
            subscription = ClientSubscription(
                client_id=client_id,
                subscription_type=subscription_type,
                filters=subscription_filters,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                awaiting_confirmation=True
            )

            # Store subscription
            if client_id not in self.client_subscriptions:
                self.client_subscriptions[client_id] = {}
            self.client_subscriptions[client_id][subscription_type] = subscription

            # Update reverse lookup
            if subscription_type not in self.subscription_clients:
                self.subscription_clients[subscription_type] = set()
            self.subscription_clients[subscription_type].add(client_id)

            # Update metrics
            self.total_subscriptions_created += 1

        if self.logger:
            self.logger.info("subscription_manager.client_subscribed", {
                "client_id": client_id,
                "subscription_type": subscription_type,
                "filters": filters,
                "total_subscribers": len(self.subscription_clients.get(subscription_type, set()))
            })

        return True

    def confirm_subscription(self, client_id: str, subscription_type: str) -> None:
        """Mark subscription as confirmed so data can start flowing"""
        try:
            sub = self.client_subscriptions.get(client_id, {}).get(subscription_type)
            if sub:
                sub.awaiting_confirmation = False
                sub.update_activity()
        except Exception:
            pass

    async def unsubscribe_client(self, client_id: str, subscription_type: str) -> bool:
        """
        Unsubscribe client from data stream with thread-safe operations.

        Args:
            client_id: Client ID
            subscription_type: Subscription type to remove

        Returns:
            True if unsubscribed successfully, False otherwise
        """
        async with self._subscription_lock:
            if (client_id not in self.client_subscriptions or
                subscription_type not in self.client_subscriptions[client_id]):
                return False

            # Remove subscription
            del self.client_subscriptions[client_id][subscription_type]

            # Update reverse lookup
            if subscription_type in self.subscription_clients:
                self.subscription_clients[subscription_type].discard(client_id)
                if not self.subscription_clients[subscription_type]:
                    del self.subscription_clients[subscription_type]

            # Clean up empty client entries
            if not self.client_subscriptions[client_id]:
                del self.client_subscriptions[client_id]

            # Update metrics
            self.total_subscriptions_removed += 1

        if self.logger:
            self.logger.info("subscription_manager.client_unsubscribed", {
                "client_id": client_id,
                "subscription_type": subscription_type,
                "remaining_subscribers": len(self.subscription_clients.get(subscription_type, set()))
            })

        return True

    async def unsubscribe_all_client(self, client_id: str):
        """Unsubscribe client from all subscriptions"""
        if client_id not in self.client_subscriptions:
            return

        subscriptions = list(self.client_subscriptions[client_id].keys())
        for subscription_type in subscriptions:
            await self.unsubscribe_client(client_id, subscription_type)

    def get_subscribers(self, subscription_type: str) -> Set[str]:
        """Get all clients subscribed to specific type"""
        return self.subscription_clients.get(subscription_type, set()).copy()

    def should_send_to_client(self,
                            client_id: str,
                            subscription_type: str,
                            data: Dict[str, Any]) -> bool:
        """
        Check if data should be sent to client based on filters.

        Args:
            client_id: Client ID
            subscription_type: Subscription type
            data: Data to be sent

        Returns:
            True if data should be sent, False otherwise
        """
        # Check if client is subscribed
        if (client_id not in self.client_subscriptions or
            subscription_type not in self.client_subscriptions[client_id]):
            return False

        subscription = self.client_subscriptions[client_id][subscription_type]

        # Check if subscription is active
        if not subscription.is_active:
            return False

        # Apply filters based on subscription type
        filters = subscription.filters

        try:
            # Hold back data until subscription confirmation response is sent
            if getattr(subscription, 'awaiting_confirmation', False):
                return False
            if subscription_type == SubscriptionType.MARKET_DATA:
                return self._apply_market_data_filters(filters, data)
            elif subscription_type == SubscriptionType.INDICATORS:
                return self._apply_indicator_filters(filters, data)
            elif subscription_type == SubscriptionType.SIGNALS:
                return self._apply_signal_filters(filters, data)
            elif subscription_type == SubscriptionType.ORDERBOOK:
                return self._apply_orderbook_filters(filters, data)
            elif subscription_type == SubscriptionType.TRADES:
                return self._apply_trade_filters(filters, data)
            else:
                # No specific filtering for other types
                return True

        except Exception as e:
            if self.logger:
                self.logger.error("subscription_manager.filter_error", {
                    "client_id": client_id,
                    "subscription_type": subscription_type,
                    "error": str(e)
                })
            return False

    def _parse_filters(self, filters_dict: Dict[str, Any]) -> SubscriptionFilter:
        """Parse filter dictionary into SubscriptionFilter object"""
        return SubscriptionFilter(
            symbols=filters_dict.get("symbols"),
            exclude_symbols=filters_dict.get("exclude_symbols"),
            data_types=filters_dict.get("data_types"),
            timeframes=filters_dict.get("timeframes"),
            indicator_types=filters_dict.get("indicator_types"),
            indicator_periods=filters_dict.get("indicator_periods"),
            signal_types=filters_dict.get("signal_types"),
            min_confidence=filters_dict.get("min_confidence"),
            max_confidence=filters_dict.get("max_confidence"),
            min_volume=filters_dict.get("min_volume"),
            min_price_change=filters_dict.get("min_price_change"),
            custom_filters=filters_dict.get("custom_filters", {})
        )

    def _apply_market_data_filters(self, filters: SubscriptionFilter, data: Dict[str, Any]) -> bool:
        """Apply filters for market data"""
        symbol = data.get("symbol", "")
        return filters.matches_market_data(symbol, data)

    def _apply_indicator_filters(self, filters: SubscriptionFilter, data: Dict[str, Any]) -> bool:
        """Apply filters for indicators"""
        symbol = data.get("symbol", "")
        if not filters.matches_symbol(symbol):
            return False

        indicator_type = data.get("indicator_type", "")
        period = data.get("period")
        timeframe = data.get("timeframe", "")

        if not filters.matches_timeframe(timeframe):
            return False

        return filters.matches_indicator(indicator_type, period)

    def _apply_signal_filters(self, filters: SubscriptionFilter, data: Dict[str, Any]) -> bool:
        """Apply filters for signals"""
        symbol = data.get("symbol", "")
        if not filters.matches_symbol(symbol):
            return False

        signal_type = data.get("signal_type", "")
        confidence = data.get("confidence")

        return filters.matches_signal(signal_type, confidence)

    def _apply_orderbook_filters(self, filters: SubscriptionFilter, data: Dict[str, Any]) -> bool:
        """Apply filters for orderbook data"""
        symbol = data.get("symbol", "")
        return filters.matches_symbol(symbol)

    def _apply_trade_filters(self, filters: SubscriptionFilter, data: Dict[str, Any]) -> bool:
        """Apply filters for trade data"""
        symbol = data.get("symbol", "")
        if not filters.matches_symbol(symbol):
            return False

        # Apply volume filter if specified
        if filters.min_volume:
            volume = data.get("volume", 0)
            if volume < filters.min_volume:
                return False

        return True

    async def record_message_delivery(self,
                                    client_id: str,
                                    subscription_type: str,
                                    message_size: int,
                                    filtered: bool = False):
        """Record message delivery for performance tracking"""
        if (client_id in self.client_subscriptions and
            subscription_type in self.client_subscriptions[client_id]):

            subscription = self.client_subscriptions[client_id][subscription_type]
            subscription.record_message(message_size, filtered)

            # Update global metrics
            self.total_messages_processed += 1
            if filtered:
                self.total_messages_filtered += 1

    def get_client_subscriptions(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a client"""
        if client_id not in self.client_subscriptions:
            return []

        subscriptions = []
        for subscription_type, subscription in self.client_subscriptions[client_id].items():
            subscriptions.append({
                "type": subscription_type,
                "created_at": subscription.created_at.isoformat(),
                "last_activity": subscription.last_activity.isoformat(),
                "is_active": subscription.is_active,
                "stats": subscription.get_stats(),
                "filters": self._filters_to_dict(subscription.filters)
            })

        return subscriptions

    def _filters_to_dict(self, filters: SubscriptionFilter) -> Dict[str, Any]:
        """Convert SubscriptionFilter to dictionary"""
        return {
            "symbols": filters.symbols,
            "exclude_symbols": filters.exclude_symbols,
            "data_types": filters.data_types,
            "timeframes": filters.timeframes,
            "indicator_types": filters.indicator_types,
            "indicator_periods": filters.indicator_periods,
            "signal_types": filters.signal_types,
            "min_confidence": filters.min_confidence,
            "max_confidence": filters.max_confidence,
            "min_volume": filters.min_volume,
            "min_price_change": filters.min_price_change,
            "custom_filters": filters.custom_filters
        }

    async def _cleanup_inactive_subscriptions(self):
        """Background task to cleanup inactive subscriptions"""
        while not self._is_shutting_down:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)

                current_time = time.time()
                inactive_subscriptions = []

                # Find inactive subscriptions (no activity for 1 hour)
                for client_id, subscriptions in self.client_subscriptions.items():
                    for subscription_type, subscription in subscriptions.items():
                        if subscription.is_active:
                            last_activity_seconds = (datetime.now() - subscription.last_activity).total_seconds()
                            if last_activity_seconds > 3600:  # 1 hour
                                inactive_subscriptions.append((client_id, subscription_type))

                # Mark inactive subscriptions
                for client_id, subscription_type in inactive_subscriptions:
                    if (client_id in self.client_subscriptions and
                        subscription_type in self.client_subscriptions[client_id]):
                        self.client_subscriptions[client_id][subscription_type].is_active = False

                self._last_cleanup_time = current_time

                if self.logger and inactive_subscriptions:
                    self.logger.info("subscription_manager.cleanup_completed", {
                        "inactive_subscriptions": len(inactive_subscriptions)
                    })

            except Exception as e:
                if self.logger:
                    self.logger.error("subscription_manager.cleanup_error", {"error": str(e)})

    def get_stats(self) -> Dict[str, Any]:
        """Get subscription manager statistics"""
        total_active_subscriptions = sum(
            len(subs) for subs in self.client_subscriptions.values()
        )

        total_clients = len(self.client_subscriptions)
        total_subscription_types = len(self.subscription_clients)

        return {
            "total_clients": total_clients,
            "total_active_subscriptions": total_active_subscriptions,
            "total_subscription_types": total_subscription_types,
            "total_subscriptions_created": self.total_subscriptions_created,
            "total_subscriptions_removed": self.total_subscriptions_removed,
            "total_messages_processed": self.total_messages_processed,
            "total_messages_filtered": self.total_messages_filtered,
            "filter_efficiency": (self.total_messages_processed - self.total_messages_filtered) / max(self.total_messages_processed, 1),
            "subscription_types_breakdown": {
                sub_type: len(clients) for sub_type, clients in self.subscription_clients.items()
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "SubscriptionManager",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
