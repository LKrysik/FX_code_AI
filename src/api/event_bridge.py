"""
Event Bridge
============
Bridges EventBus events to WebSocket clients with intelligent filtering and batching.
Production-ready with performance optimization and memory management.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque
import time
import weakref
from weakref import WeakSet, WeakKeyDictionary
import aiofiles

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from .subscription_manager import SubscriptionManager, SubscriptionType
from .signal_processor import SignalProcessor
from .execution_processor import ExecutionProcessor
from .broadcast_provider import BroadcastProvider
from ..domain.interfaces.execution import IEventBridge
from typing import Protocol


class WebSocketServerInterface(Protocol):
    """Interface for WebSocket server communication"""

    async def broadcast_to_subscribers(self, subscription_type: str, data: dict, exclude_client: str = None) -> int:
        """Broadcast message to subscribers"""
        ...


@dataclass
class BatchUpdate:
    """Represents a batched update for efficient transmission"""

    batch_id: str
    stream_type: str
    updates: Dict[str, Any]
    timestamp: float
    size_bytes: int = 0
    client_count: int = 0

    def add_update(self, key: str, data: Dict[str, Any]):
        """Add an update to the batch"""
        self.updates[key] = data
        # Size will be calculated lazily when needed

    def should_flush(self, max_batch_size: int = 100, max_age_seconds: float = 0.1) -> bool:
        """Check if batch should be flushed"""
        age = time.monotonic() - self.timestamp
        return len(self.updates) >= max_batch_size or age >= max_age_seconds

    def calculate_size(self):
        """Calculate size bytes lazily"""
        if not hasattr(self, '_size_calculated') or not self._size_calculated:
            self.size_bytes = len(json.dumps(self.updates).encode('utf-8'))
            self._size_calculated = True

    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert batch to WebSocket message format"""
        return {
            "type": "batch_update",
            "stream": self.stream_type,
            "batch_id": self.batch_id,
            "batch_size": len(self.updates),
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "data": self.updates
        }


@dataclass
class StreamProcessor:
    """Processes events for a specific stream type"""

    stream_type: str
    event_patterns: List[str]
    batch_aggregator: Optional['BatchAggregator'] = None
    filter_function: Optional[Callable[[Dict[str, Any]], bool]] = None
    transform_function: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def matches_event(self, event_type: str) -> bool:
        """Check if this processor handles the event type"""
        return any(pattern in event_type for pattern in self.event_patterns)


class BatchAggregator:
    """Aggregates multiple updates into efficient batches"""

    def __init__(self,
                 stream_type: str,
                 flush_interval: float = 0.1,
                 max_batch_size: int = 50,
                 max_queue_size: int = 1000):
        self.stream_type = stream_type
        self.flush_interval = flush_interval
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size

        self.current_batch: Optional[BatchUpdate] = None
        self.batch_queue: asyncio.Queue[BatchUpdate] = asyncio.Queue(maxsize=max_queue_size)
        self.last_flush = time.monotonic()

        # Performance tracking
        self.total_updates_processed = 0
        self.total_batches_created = 0
        self.average_batch_size = 0.0
        self.batch_sizes: deque[int] = deque(maxlen=100)  # For moving average

        # Queue monitoring
        self.queue_full_events = 0
        self.broadcast_blocks = 0
        self.broadcast_failures = 0

    def add_update(self, key: str, data: Dict[str, Any]):
        """Add update to current batch"""
        self.total_updates_processed += 1

        # Create new batch if needed
        if not self.current_batch:
            self.current_batch = BatchUpdate(
                batch_id=f"batch_{self.stream_type}_{int(time.monotonic() * 1000)}",
                stream_type=self.stream_type,
                updates={},
                timestamp=time.monotonic()
            )

        # Add to current batch
        self.current_batch.add_update(key, data)

        # Check if batch should be flushed
        if self.current_batch.should_flush(self.max_batch_size, self.flush_interval):
            self._flush_batch()

    def _flush_batch(self):
        """Flush current batch to queue"""
        if self.current_batch and self.current_batch.updates:
            # Calculate size before putting in queue
            self.current_batch.calculate_size()

            try:
                self.batch_queue.put_nowait(self.current_batch)
                self.total_batches_created += 1

                # Update moving average batch size
                self.batch_sizes.append(len(self.current_batch.updates))
                self.average_batch_size = sum(self.batch_sizes) / len(self.batch_sizes) if self.batch_sizes else 0

                # Reset for next batch
                self.current_batch = None
                self.last_flush = time.monotonic()
            except asyncio.QueueFull:
                # Queue is full - implement backpressure strategy
                # For now, drop oldest batch to make room (could be configurable)
                self.queue_full_events += 1
                try:
                    dropped = self.batch_queue.get_nowait()
                    self.logger.warning("event_bridge.batch_queue_full", {
                        "stream_type": self.stream_type,
                        "dropped_batch_id": dropped.batch_id,
                        "queue_size": self.batch_queue.qsize(),
                        "total_queue_full_events": self.queue_full_events
                    })
                    self.batch_queue.put_nowait(self.current_batch)
                except asyncio.QueueEmpty:
                    # Should not happen, but log
                    self.logger.error("event_bridge.queue_full_but_empty", {
                        "stream_type": self.stream_type
                    })

    def get_pending_batch(self) -> Optional[BatchUpdate]:
        """Get next batch from queue"""
        try:
            return self.batch_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def force_flush(self) -> Optional[BatchUpdate]:
        """Force flush current batch"""
        if self.current_batch:
            self.current_batch.calculate_size()
            batch = self.current_batch
            self.current_batch = None
            self.last_flush = time.monotonic()
            return batch
        return None


    def get_stats(self) -> Dict[str, Any]:
        """Get batch aggregator statistics"""
        return {
            "stream_type": self.stream_type,
            "queue_size": self.batch_queue.qsize(),
            "queue_maxsize": self.batch_queue.maxsize,
            "total_updates_processed": self.total_updates_processed,
            "total_batches_created": self.total_batches_created,
            "average_batch_size": self.average_batch_size,
            "current_batch_size": len(self.current_batch.updates) if self.current_batch else 0,
            "queue_full_events": self.queue_full_events,
            "broadcast_blocks": self.broadcast_blocks,
            "broadcast_failures": self.broadcast_failures
        }


class EventBridge(IEventBridge):
    """
    Bridges EventBus events to WebSocket clients with intelligent processing.

    Features:
    - EventBus subscription and event transformation
    - Intelligent batching for performance optimization
    - Client-specific filtering based on subscriptions
    - Real-time data streaming with low latency
    - Memory-efficient processing with automatic cleanup
    """

    def __init__(self,
                 event_bus: EventBus,
                 broadcast_provider: BroadcastProvider,
                 subscription_manager: SubscriptionManager,
                 logger: Optional[StructuredLogger] = None,
                 settings: Optional[Any] = None,
                 max_concurrent_broadcasts: int = 50,
                 max_batch_size: int = 50,
                 max_queue_size: int = 1000,
                 batch_flush_interval: float = 0.1,
                 max_websocket_message_size: int = 65536):  # 64KB default
        """
        Initialize EventBridge.

        Args:
            event_bus: EventBus instance for subscribing to events
            broadcast_provider: Centralized broadcast provider for WebSocket messages
            subscription_manager: Subscription manager for client filtering
            logger: Optional logger instance
            settings: AppSettings instance for configuration
        """
        if logger:
            logger.info("event_bridge.initialized", {
                "event_bus_type": type(event_bus).__name__,
                "broadcast_provider_type": type(broadcast_provider).__name__,
                "subscription_manager_type": type(subscription_manager).__name__
            })
        else:
            print("[EVENT_BRIDGE] EventBridge initialized")

        self.event_bus = event_bus
        self.broadcast_provider = broadcast_provider
        self.subscription_manager = subscription_manager
        self.logger = logger

        # Stream processors for different data types
        self.stream_processors: Dict[str, StreamProcessor] = {}

        # Batch aggregators for performance optimization
        self.batch_aggregators: Dict[str, BatchAggregator] = {}

        # Broadcast rate limiting
        self.broadcast_semaphore = asyncio.Semaphore(max_concurrent_broadcasts)

        # ✅ PERF FIX (Problem #11): Event processing rate limiting
        # Allows concurrent processing while preventing unbounded parallelism
        # Set to 10 to match EventBus worker capacity (not 1 which serializes everything)
        self.event_processing_semaphore = asyncio.Semaphore(10)

        # Track active processing tasks for cleanup
        self._active_processing_tasks: Set[asyncio.Task] = set()

        # Batch processing tasks
        self.batch_processing_tasks: List[asyncio.Task] = []

        # Configuration
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self.batch_flush_interval = batch_flush_interval
        self.max_websocket_message_size = max_websocket_message_size

        # Signal processor for trading signals
        self.signal_processor = SignalProcessor(logger)

        # Execution processor for progress tracking (will be injected)
        self.execution_processor = None

        # Event handlers registry with WeakRef for automatic cleanup
        self.event_handlers: WeakKeyDictionary = WeakKeyDictionary()
        self._active_handlers: WeakSet = WeakSet()

        # Strong references to keep handlers alive
        self._handler_refs: List[Callable] = []

        # Track subscribed handlers for explicit unsubscription during stop
        self._subscribed_handlers: List[tuple[str, Callable]] = []

        # Performance tracking
        self.total_events_processed = 0
        self.total_messages_sent = 0
        self.average_processing_time = 0.0
        self.processing_times: deque[float] = deque(maxlen=1000)

        # Broadcast metrics
        self.broadcast_blocks = 0
        self.broadcast_failures = 0

        # Control flags
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # Initialize default stream processors
        self._setup_default_processors()

    def set_execution_processor(self, execution_processor: ExecutionProcessor):
        """Set the execution processor for progress tracking"""
        self.execution_processor = execution_processor
        if self.logger:
            self.logger.info("event_bridge.execution_processor_set", {
                "execution_processor_type": type(execution_processor).__name__ if execution_processor else None
            })
        else:
            print(f"[EVENT_BRIDGE] Execution processor set: {type(execution_processor).__name__ if execution_processor else None}")

    def register_handler(self, handler):
        """Register handler with automatic cleanup"""
        self._active_handlers.add(handler)
        return handler

    async def _handle_execution_progress_websocket_update(self, event_data: Dict[str, Any]):

        self.logger.debug("event_bridge.handler_called", {
            "handler": "_handle_execution_progress_websocket_update",
            "event_data_keys": list(event_data.keys()) if isinstance(event_data, dict) else None
        })
        # Log progress information being sent to frontend
        data = event_data.get("data", {})
        records_collected = data.get("records_collected", 0)
        progress = data.get("progress", {})
        progress_percentage = progress.get("percentage", 0.0) if isinstance(progress, dict) else 0.0

        # ✅ PERFORMANCE FIX: Changed from INFO to DEBUG
        # Progress updates are routine/frequent operations (5s interval with throttling)
        # INFO level should be reserved for significant events (session start/stop, errors)
        # This reduces log spam from hundreds of progress updates per session to DEBUG-only logging
        if self.logger:
            self.logger.debug("event_bridge.execution_progress_sent", {
                "records_collected": records_collected,
                "progress_percentage": progress_percentage,
                "session_id": data.get("session_id"),
                "command_type": data.get("command_type", "unknown")
            })
        else:
            # Console fallback also changed to be less verbose
            pass  # Skip console output for routine progress (too noisy)

        # This is already a formatted WebSocket message, broadcast directly
        success = await self.broadcast_provider.broadcast_message(
            stream_type="execution_status",
            message_type=event_data.get("type", "data"),
            data=data
        )
        if success:
            self.total_messages_sent += 1
            self.logger.debug("event_bridge.execution_progress_websocket_sent")
        else:
            self.logger.warning("event_bridge.execution_progress_broadcast_failed")

    async def _handle_execution_result_websocket_update(self, event_data: Dict[str, Any]):
        # This is already a formatted WebSocket message, broadcast directly
        success = await self.broadcast_provider.broadcast_message(
            stream_type="execution_result",
            message_type=event_data.get("type", "execution_result"),
            data=event_data.get("data", {})
        )
        if success:
            self.total_messages_sent += 1
            self.logger.debug("event_bridge.execution_result_websocket_sent")
        else:
            self.logger.warning("event_bridge.execution_result_broadcast_failed")

    async def cleanup_handlers(self):
        """Force cleanup of dead handlers"""
        initial_count = len(self._active_handlers)
        # WeakSet automatically removes dead references
        current_count = len(self._active_handlers)

        if initial_count != current_count:
            self.logger.info("event_bridge.handlers_cleaned", {
                "removed_handlers": initial_count - current_count,
                "active_handlers": current_count
            })

    def _setup_default_processors(self):
        """Setup default stream processors for common event types"""

        # Market data processor (no batching for test-friendly real-time streaming)
        market_processor = StreamProcessor(
            stream_type="market_data",
            event_patterns=["market.price_update", "market.orderbook_update", "market.trades"],
            batch_aggregator=None
        )
        self.stream_processors["market_data"] = market_processor

        # Indicator processor
        indicator_processor = StreamProcessor(
            stream_type="indicators",
            event_patterns=["indicator.updated", "streaming_indicator.updated"],
            batch_aggregator=None
        )
        self.stream_processors["indicators"] = indicator_processor

        # Signal processor
        signal_processor = StreamProcessor(
            stream_type="signals",
            event_patterns=["signal_generated", "signal.flash_pump_detected", "signal.reversal_detected", "signal.confluence_detected"],
            batch_aggregator=None
        )
        self.stream_processors["signals"] = signal_processor

        # Execution processor (no batching for immediate updates)
        execution_processor = StreamProcessor(
            stream_type="execution_status",
            event_patterns=["execution.session_started", "execution.progress_update", "execution.session_completed"]
        )
        self.stream_processors["execution_status"] = execution_processor

        # Execution result processor for completion/failure events
        execution_result_processor = StreamProcessor(
            stream_type="execution_result",
            event_patterns=["execution.result_update"]
        )
        self.stream_processors["execution_result"] = execution_result_processor

        # Health check processor for real-time health notifications
        health_processor = StreamProcessor(
            stream_type="health_check",
            event_patterns=["health.alert"]
        )
        self.stream_processors["health_check"] = health_processor

        # Paper trading processor (TIER 1.3) - Real-time updates for paper trading sessions
        paper_trading_processor = StreamProcessor(
            stream_type="paper_trading",
            event_patterns=[
                "paper_trading.order_filled",
                "paper_trading.position_updated",
                "paper_trading.performance_updated",
                "paper_trading.session_started",
                "paper_trading.session_stopped",
                "paper_trading.liquidation_warning"
            ],
            batch_aggregator=None  # No batching for immediate updates
        )
        self.stream_processors["paper_trading"] = paper_trading_processor

        # Live trading processor (Agent 6) - Real-time updates for live trading sessions
        live_trading_processor = StreamProcessor(
            stream_type="live_trading",
            event_patterns=[
                "live_trading.order_created",
                "live_trading.order_updated",
                "live_trading.order_filled",
                "live_trading.order_cancelled",
                "live_trading.order_failed",
                "live_trading.position_opened",
                "live_trading.position_updated",
                "live_trading.position_closed",
                "live_trading.position_liquidated",
                "live_trading.risk_alert",
                "live_trading.session_started",
                "live_trading.session_stopped"
            ],
            batch_aggregator=None  # No batching for critical real-time updates
        )
        self.stream_processors["live_trading"] = live_trading_processor

    async def start(self):
        """Start the EventBridge and setup event subscriptions"""
        if self.is_running:
            return

        self.is_running = True

        self.logger.info("event_bridge.starting", {
            "stream_processors": len(self.stream_processors),
            "batch_aggregators": len(self.batch_aggregators)
        })

        try:
            # Setup EventBus subscriptions
            await self._setup_event_subscriptions()

            # Start batch processing
            await self._start_batch_processing()

            # Start execution processor if available
            if self.execution_processor:
                await self.execution_processor.start()

            self.logger.info("event_bridge.started")


        except Exception as e:
            self.logger.info("event_bridge.failed_to_start")
            print(f"[EVENT_BRIDGE] Failed to start EventBridge: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def stop(self):
        """Stop the EventBridge gracefully"""
        if not self.is_running:
            return

        self.logger.info("event_bridge.stopping")
        self.is_running = False
        self._shutdown_event.set()

        # Stop execution processor if available
        if self.execution_processor:
            await self.execution_processor.stop()

        # Force flush all pending batches
        for aggregator in self.batch_aggregators.values():
            batch = aggregator.force_flush()
            if batch:
                await self._process_batch_update(batch)

        # Drain all pending batches in queues
        for aggregator in self.batch_aggregators.values():
            while not aggregator.batch_queue.empty():
                try:
                    batch = await asyncio.wait_for(aggregator.batch_queue.get(), timeout=0.1)
                    await self._process_batch_update(batch)
                except asyncio.TimeoutError:
                    break  # Queue drained

        # Cancel batch processing tasks
        for task in self.batch_processing_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except asyncio.TimeoutError:
                    pass  # Task didn't cancel cleanly

        # ✅ PERF FIX (Problem #11): Cancel active processing tasks
        active_tasks_count = len(self._active_processing_tasks)
        if active_tasks_count > 0:
            self.logger.info("event_bridge.cancelling_processing_tasks", {
                "active_tasks": active_tasks_count
            })
            for task in list(self._active_processing_tasks):
                if not task.done():
                    task.cancel()
            # Wait for all tasks with timeout
            if self._active_processing_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._active_processing_tasks, return_exceptions=True),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("event_bridge.processing_tasks_timeout", {
                        "timed_out_count": len(self._active_processing_tasks)
                    })
            self._active_processing_tasks.clear()

        # Explicitly unsubscribe all handlers to prevent warnings during cleanup
        for event_type, handler in self._subscribed_handlers:
            try:
                self.event_bus.unsubscribe(event_type, handler, silent=True)
            except Exception:
                # Ignore errors during shutdown
                pass

        self.logger.info("event_bridge.stopped", {
            "total_events_processed": self.total_events_processed,
            "total_messages_sent": self.total_messages_sent,
            "handlers_unsubscribed": len(self._subscribed_handlers)
        })

    async def _setup_event_subscriptions(self):
        """Setup EventBus subscriptions for all stream processors"""
        if self.logger:
            self.logger.debug("event_bridge.setting_up_subscriptions", {
                "execution_processor_available": self.execution_processor is not None
            })
        else:
            print(f"[EVENT_BRIDGE] Setting up subscriptions, execution_processor: {self.execution_processor is not None}")

        # Market data events
        async def handle_market_event(event_data: Dict[str, Any]):
            await self._process_event("market.price_update", event_data)

        async def handle_orderbook_event(event_data: Dict[str, Any]):
            await self._process_event("market.orderbook_update", event_data)

        # Indicator events
        async def handle_indicator_event(event_data: Dict[str, Any]):
            await self._process_event("indicator.updated", event_data)

        # Signal events
        async def handle_flash_pump_signal(event_data: Dict[str, Any]):
            processed_signal = await self.signal_processor.process_flash_pump_signal(event_data)
            if processed_signal:
                await self._process_event("signal.flash_pump_detected", processed_signal)

        async def handle_reversal_signal(event_data: Dict[str, Any]):
            processed_signal = await self.signal_processor.process_reversal_signal(event_data)
            if processed_signal:
                await self._process_event("signal.reversal_detected", processed_signal)

        async def handle_confluence_signal(event_data: Dict[str, Any]):
            processed_signal = await self.signal_processor.process_confluence_signal(event_data)
            if processed_signal:
                await self._process_event("signal.confluence_detected", processed_signal)



        # Subscribe to events
        await self.event_bus.subscribe("market.price_update", handle_market_event)
        self._subscribed_handlers.append(("market.price_update", handle_market_event))
        await self.event_bus.subscribe("market.orderbook_update", handle_orderbook_event)
        self._subscribed_handlers.append(("market.orderbook_update", handle_orderbook_event))
        await self.event_bus.subscribe("indicator.updated", handle_indicator_event)
        self._subscribed_handlers.append(("indicator.updated", handle_indicator_event))
        await self.event_bus.subscribe("streaming_indicator.updated", handle_indicator_event)
        self._subscribed_handlers.append(("streaming_indicator.updated", handle_indicator_event))
        await self.event_bus.subscribe("signal.flash_pump_detected", handle_flash_pump_signal)
        self._subscribed_handlers.append(("signal.flash_pump_detected", handle_flash_pump_signal))
        await self.event_bus.subscribe("signal.reversal_detected", handle_reversal_signal)
        self._subscribed_handlers.append(("signal.reversal_detected", handle_reversal_signal))
        await self.event_bus.subscribe("signal.confluence_detected", handle_confluence_signal)
        self._subscribed_handlers.append(("signal.confluence_detected", handle_confluence_signal))

        # Generic signal_generated handler - forwards all signals from StrategyManager
        async def handle_signal_generated(event_data: Dict[str, Any]):
            """Forward signal_generated events from StrategyManager to WebSocket clients"""
            await self._process_event("signal_generated", event_data)

        await self.event_bus.subscribe("signal_generated", handle_signal_generated)
        self._subscribed_handlers.append(("signal_generated", handle_signal_generated))

        # Execution events - only subscribe if execution processor is available
        if self.execution_processor:
            async def handle_execution_started(event_data: Dict[str, Any]):
                # Filter out WebSocket message formats (avoid double processing)
                if event_data.get("type") == "data" and "stream" in event_data:
                    return
                await self.execution_processor.process_execution_event("execution.session_started", event_data)

            async def handle_execution_progress(event_data: Dict[str, Any]):
                # Filter out WebSocket message formats (avoid double processing)
                if event_data.get("type") == "data" and "stream" in event_data:
                    return

                await self.execution_processor.process_execution_event("execution.progress_update", event_data)

            async def handle_execution_completed(event_data: Dict[str, Any]):
                # Filter out WebSocket message formats (avoid double processing)
                if event_data.get("type") == "data" and "stream" in event_data:
                    return
                await self.execution_processor.process_execution_event("execution.session_completed", event_data)

            async def handle_execution_failed(event_data: Dict[str, Any]):
                # Filter out WebSocket message formats (avoid double processing)
                if event_data.get("type") == "data" and "stream" in event_data:
                    return
                await self.execution_processor.process_execution_event("execution.session_failed", event_data)

            # Register handlers to prevent garbage collection
            self._handler_refs.append(handle_execution_started)
            self._handler_refs.append(handle_execution_progress)
            self._handler_refs.append(handle_execution_completed)
            self._handler_refs.append(handle_execution_failed)

            await self.event_bus.subscribe("execution.session_started", handle_execution_started)
            self._subscribed_handlers.append(("execution.session_started", handle_execution_started))
            await self.event_bus.subscribe("execution.progress_update", handle_execution_progress)
            self._subscribed_handlers.append(("execution.progress_update", handle_execution_progress))
            await self.event_bus.subscribe("execution.session_completed", handle_execution_completed)
            self._subscribed_handlers.append(("execution.session_completed", handle_execution_completed))
            await self.event_bus.subscribe("execution.session_failed", handle_execution_failed)
            self._subscribed_handlers.append(("execution.session_failed", handle_execution_failed))

        # Subscribe to execution updates published back by ExecutionProcessor
        progress_handler = lambda event_data: self._handle_execution_progress_websocket_update(event_data)
        result_handler = lambda event_data: self._handle_execution_result_websocket_update(event_data)
        self._handler_refs.append(progress_handler)
        self._handler_refs.append(result_handler)
        await self.event_bus.subscribe("execution.progress_websocket_update", progress_handler)
        self._subscribed_handlers.append(("execution.progress_websocket_update", progress_handler))
        await self.event_bus.subscribe("execution.result_websocket_update", result_handler)
        self._subscribed_handlers.append(("execution.result_websocket_update", result_handler))

        # Health alert handler
        async def handle_health_alert(event_data: Dict[str, Any]):
            # Filter out WebSocket message formats (avoid double processing)
            if event_data.get("type") == "data" and "stream" in event_data:
                return
            await self._process_event("health.alert", event_data)

        # Subscribe to health alerts
        await self.event_bus.subscribe("health.alert", handle_health_alert)
        self._subscribed_handlers.append(("health.alert", handle_health_alert))

    async def _start_batch_processing(self):
        """Start background batch processing tasks"""
        for stream_type, aggregator in self.batch_aggregators.items():
            task = asyncio.create_task(self._process_batches_for_stream(stream_type))
            self.batch_processing_tasks.append(task)

    async def _process_batches_for_stream(self, stream_type: str):
        """Process batches for a specific stream type"""
        aggregator = self.batch_aggregators[stream_type]

        while self.is_running:
            try:
                # Wait for next batch (backpressure-aware)
                batch = await aggregator.batch_queue.get()
                await self._process_batch_update(batch)

            except Exception as e:
                self.logger.error("event_bridge.batch_processing_error", {
                    "stream_type": stream_type,
                    "error": str(e)
                })
                # Brief pause on error to prevent tight error loops
                await asyncio.sleep(0.1)

    async def _process_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process an incoming EventBus event"""
        start_time = time.time()
        self.total_events_processed += 1

        if self.logger:
            self.logger.debug("event_bridge.processing_event", {
                "event_type": event_type,
                "event_data_keys": list(event_data.keys()) if isinstance(event_data, dict) else None
            })
        else:
            print(f"[EVENT_BRIDGE] Processing event: {event_type}")

        # Extract event publication timestamp if available
        event_publish_time = event_data.get('_publish_timestamp', start_time)

        try:
            # Find matching stream processor
            processor = None
            for stream_proc in self.stream_processors.values():
                if stream_proc.matches_event(event_type):
                    processor = stream_proc
                    break

            if not processor:
                # No processor found, log and skip
                if self.logger:
                    self.logger.warning("event_bridge.no_processor", {
                        "event_type": event_type
                    })
                else:
                    print(f"[EVENT_BRIDGE] No processor found for event: {event_type}")
                return

            # Apply filtering if configured
            if processor.filter_function and not processor.filter_function(event_data):
                return

            # Apply transformation if configured
            transformed_data = event_data
            if processor.transform_function:
                transformed_data = processor.transform_function(event_data)

            # Handle batching vs immediate processing
            if processor.batch_aggregator:
                # Add to batch aggregator
                key = self._generate_event_key(event_type, transformed_data)
                processor.batch_aggregator.add_update(key, transformed_data)
            else:
                # ✅ PERF FIX (Problem #11): Parallel processing with semaphore for flow control
                # OLD: Sequential processing (await) caused 5-10x latency amplification
                # NEW: Parallel processing with semaphore limits concurrency to 10 (not unbounded)
                # This utilizes EventBus's 11 workers instead of just 1
                task = asyncio.create_task(
                    self._process_immediate_update_with_semaphore(
                        processor.stream_type, transformed_data, event_publish_time
                    )
                )
                # Track task for cleanup
                self._active_processing_tasks.add(task)
                task.add_done_callback(self._active_processing_tasks.discard)

            # Track processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 0:
                self.average_processing_time = sum(self.processing_times) / len(self.processing_times)

            # Track full pipeline latency (from event publication to processing start)
            pipeline_latency = (start_time - event_publish_time) * 1000
            if pipeline_latency > 100:  # Log if > 100ms
                self.logger.warning("event_bridge.high_pipeline_latency", {
                    "event_type": event_type,
                    "pipeline_latency_ms": pipeline_latency,
                    "processing_time_ms": processing_time
                })

        except Exception as e:
            self.logger.error("event_bridge.event_processing_error", {
                "event_type": event_type,
                "error": str(e),
                "event_data_keys": list(event_data.keys()) if isinstance(event_data, dict) else None
            })

    async def _safe_broadcast(self, stream_type: str, batch_data: Dict[str, Any], max_retries: int = 3):
        """Broadcast with rate limiting and retry mechanism"""
        async with self.broadcast_semaphore:
            for attempt in range(max_retries):
                try:
                    success = await self.broadcast_provider.broadcast_batch_update(
                        stream_type=stream_type,
                        batch_data=batch_data
                    )
                    if success:
                        return True
                    else:
                        self.broadcast_failures += 1
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                except Exception as e:
                    self.broadcast_failures += 1
                    self.logger.error("event_bridge.broadcast_error", {
                        "stream_type": stream_type,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error": str(e)
                    })
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

            # All retries failed
            self.logger.error("event_bridge.broadcast_failed_all_retries", {
                "stream_type": stream_type,
                "max_retries": max_retries,
                "total_broadcast_failures": self.broadcast_failures
            })
            return False

    def _split_large_batch(self, batch: BatchUpdate) -> List[BatchUpdate]:
        """Split batch if message size exceeds limit"""
        message_data = batch.to_websocket_message()
        message_size = len(json.dumps(message_data).encode('utf-8'))

        if message_size <= self.max_websocket_message_size:
            return [batch]

        # Split batch into smaller chunks
        chunks = []
        current_chunk = {}
        current_size = 0
        base_message = {
            "type": "batch_update",
            "stream": batch.stream_type,
            "batch_size": 0,  # Will be updated
            "timestamp": batch.timestamp.isoformat() if hasattr(batch.timestamp, 'isoformat') else batch.timestamp
        }

        for key, data in batch.updates.items():
            item_size = len(json.dumps({key: data}).encode('utf-8'))

            if current_size + item_size > self.max_websocket_message_size and current_chunk:
                # Create chunk
                chunk_message = base_message.copy()
                chunk_message["data"] = current_chunk
                chunk_message["batch_size"] = len(current_chunk)
                chunk_message["batch_id"] = f"{batch.batch_id}_chunk_{len(chunks)}"

                chunk_batch = BatchUpdate(
                    batch_id=chunk_message["batch_id"],
                    stream_type=batch.stream_type,
                    updates=current_chunk.copy(),
                    timestamp=batch.timestamp
                )
                chunks.append(chunk_batch)

                current_chunk = {}
                current_size = 0

            current_chunk[key] = data
            current_size += item_size

        # Add remaining items
        if current_chunk:
            chunk_message = base_message.copy()
            chunk_message["data"] = current_chunk
            chunk_message["batch_size"] = len(current_chunk)
            chunk_message["batch_id"] = f"{batch.batch_id}_chunk_{len(chunks)}"

            chunk_batch = BatchUpdate(
                batch_id=chunk_message["batch_id"],
                stream_type=batch.stream_type,
                updates=current_chunk.copy(),
                timestamp=batch.timestamp
            )
            chunks.append(chunk_batch)

        return chunks

    async def _process_batch_update(self, batch: BatchUpdate):
        """Process a batch update by broadcasting to subscribed clients"""
        try:
            # Check if batch needs splitting due to size
            batches_to_send = self._split_large_batch(batch)

            for batch_chunk in batches_to_send:
                # Use rate-limited broadcast with retry
                success = await self._safe_broadcast(
                    stream_type=batch_chunk.stream_type,
                    batch_data=batch_chunk.to_websocket_message()
                )

                if success:
                    batch_chunk.client_count = 1  # Provider handles client counting internally
                    self.total_messages_sent += 1

                    self.logger.debug("event_bridge.batch_processed", {
                        "stream_type": batch_chunk.stream_type,
                        "batch_id": batch_chunk.batch_id,
                        "batch_size": len(batch_chunk.updates),
                        "processing_time_ms": (time.monotonic() - batch_chunk.timestamp) * 1000,
                        "is_split": len(batches_to_send) > 1
                    })
                else:
                    self.logger.warning("event_bridge.batch_broadcast_failed", {
                        "batch_id": batch_chunk.batch_id,
                        "stream_type": batch_chunk.stream_type,
                        "is_split": len(batches_to_send) > 1
                    })

        except Exception as e:
            self.logger.error("event_bridge.batch_processing_error", {
                "batch_id": batch.batch_id,
                "stream_type": batch.stream_type,
                "error": str(e)
            })

    async def _process_immediate_update_with_semaphore(self, stream_type: str, data: Dict[str, Any], event_publish_time: Optional[float] = None):
        """✅ PERF FIX (Problem #11): Process immediate update with concurrency control

        This is a wrapper around _process_immediate_update that adds semaphore-based
        flow control to prevent unbounded parallelism while still allowing concurrent processing.
        """
        async with self.event_processing_semaphore:
            await self._process_immediate_update(stream_type, data, event_publish_time)

    async def _process_immediate_update(self, stream_type: str, data: Dict[str, Any], event_publish_time: Optional[float] = None):
        """Process an immediate update (no batching)"""
        broadcast_start_time = time.time()

        try:
            # Use centralized broadcast provider based on stream type
            if stream_type == "market_data":
                success = await self.broadcast_provider.broadcast_market_data(data)
            elif stream_type == "indicators":
                success = await self.broadcast_provider.broadcast_indicator_data(data)
            elif stream_type == "health_check":
                success = await self.broadcast_provider.broadcast_health_update(data)
            else:
                # Generic broadcast for other stream types
                success = await self.broadcast_provider.broadcast_message(
                    stream_type=stream_type,
                    message_type="data",
                    data=data
                )

            if success:
                self.total_messages_sent += 1

                # Track full pipeline latency (from event publication to WebSocket broadcast completion)
                if event_publish_time:
                    full_pipeline_latency = (time.time() - event_publish_time) * 1000
                    if full_pipeline_latency > 200:  # Log if > 200ms for full pipeline
                        self.logger.warning("event_bridge.high_full_pipeline_latency", {
                            "stream_type": stream_type,
                            "full_pipeline_latency_ms": full_pipeline_latency,
                            "broadcast_time_ms": (time.time() - broadcast_start_time) * 1000
                        })

                self.logger.debug("event_bridge.immediate_processed", {
                    "stream_type": stream_type
                })
            else:
                self.logger.warning("event_bridge.immediate_broadcast_failed", {
                    "stream_type": stream_type
                })

        except Exception as e:
            self.logger.error("event_bridge.immediate_processing_error", {
                "stream_type": stream_type,
                "error": str(e)
            })

    def _generate_event_key(self, event_type: str, data: Dict[str, Any]) -> str:
        """Generate a unique key for batching events"""
        # Use symbol as primary key for market data
        if "symbol" in data:
            return f"{event_type}:{data['symbol']}"
        elif "indicator_type" in data:
            symbol = data.get("symbol", "unknown")
            return f"{event_type}:{symbol}:{data['indicator_type']}"
        else:
            # Fallback to timestamp-based key
            return f"{event_type}:{int(time.time() * 1000000)}"

    def add_stream_processor(self,
                           stream_type: str,
                           event_patterns: List[str],
                           batch_enabled: bool = True,
                           filter_function: Optional[Callable] = None,
                           transform_function: Optional[Callable] = None):
        """Add a custom stream processor"""
        processor = StreamProcessor(
            stream_type=stream_type,
            event_patterns=event_patterns,
            filter_function=filter_function,
            transform_function=transform_function
        )

        if batch_enabled:
            processor.batch_aggregator = BatchAggregator(
                stream_type=stream_type,
                flush_interval=self.batch_flush_interval,
                max_batch_size=self.max_batch_size,
                max_queue_size=self.max_queue_size
            )
            self.batch_aggregators[stream_type] = processor.batch_aggregator

        self.stream_processors[stream_type] = processor

        self.logger.info("event_bridge.stream_processor_added", {
            "stream_type": stream_type,
            "event_patterns": event_patterns,
            "batch_enabled": batch_enabled
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get EventBridge statistics"""
        batch_stats = {}
        for stream_type, aggregator in self.batch_aggregators.items():
            batch_stats[stream_type] = aggregator.get_stats()

        return {
            "is_running": self.is_running,
            "total_events_processed": self.total_events_processed,
            "total_messages_sent": self.total_messages_sent,
            "average_processing_time_ms": self.average_processing_time,
            "stream_processors_count": len(self.stream_processors),
            "batch_aggregators_count": len(self.batch_aggregators),
            "batch_aggregators": batch_stats,
            "broadcast_blocks": self.broadcast_blocks,
            "broadcast_failures": self.broadcast_failures,
            "configuration": {
                "max_concurrent_broadcasts": self.broadcast_semaphore._value,
                "max_batch_size": self.max_batch_size,
                "max_queue_size": self.max_queue_size,
                "batch_flush_interval": self.batch_flush_interval,
                "max_websocket_message_size": self.max_websocket_message_size
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": self.is_running,
            "component": "EventBridge",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
