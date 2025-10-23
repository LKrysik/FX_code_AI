"""
Execution Processor
===================
Processes execution events and provides progress tracking for trading operations.
Handles backtest and live trading progress updates with real-time status.
Production-ready with performance optimization and error handling.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import time
import threading
import weakref

from ..core.logger import StructuredLogger
from ..domain.interfaces.execution import IExecutionProcessor
from .broadcast_provider import BroadcastProvider


@dataclass
class ExecutionProgress:
    """Represents execution progress information"""

    session_id: str
    progress_percentage: float
    current_step: int
    total_steps: int
    current_date: Optional[datetime] = None
    eta_seconds: Optional[int] = None
    status_message: str = ""
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    trading_stats: Dict[str, Any] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)
    # Store command_type for proper serialization
    _command_type: str = "unknown"
    # Store session start time for accurate duration calculation
    _session_start_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary for WebSocket transmission"""
        result = {
            "session_id": self.session_id,
            "progress": {
                "percentage": self.progress_percentage,
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "current_date": self.current_date.isoformat() if self.current_date else None,
                "eta_seconds": self.eta_seconds,
                "status_message": self.status_message
            },
            "performance": self.performance_metrics,
            "trading_stats": self.trading_stats,
            "timestamp": self.last_update.isoformat()
        }

        # Add command_type and records_collected for proper serialization
        # This ensures ExecutionResult.to_dict() can extract these fields correctly
        if hasattr(self, '_command_type'):
            result["command_type"] = self._command_type
        if "records_collected" in self.trading_stats:
            result["records_collected"] = self.trading_stats["records_collected"]

        return result


@dataclass
class ExecutionResult:
    """Represents final execution results"""

    session_id: str
    status: str  # "completed", "failed", "stopped"
    total_duration_seconds: float
    final_results: Dict[str, Any]
    error_message: Optional[str] = None
    completion_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for WebSocket transmission"""
        result = {
            "session_id": self.session_id,
            "status": self.status,
            "total_duration_seconds": self.total_duration_seconds,
            "final_results": self.final_results,
            "error_message": self.error_message,
            "completion_time": self.completion_time.isoformat()
        }

        # Add command_type for frontend filtering
        # Try to extract from progress data first
        command_type = None
        if (self.final_results and
            isinstance(self.final_results.get("progress"), dict) and
            self.final_results["progress"].get("command_type")):
            command_type = self.final_results["progress"]["command_type"]

        # Fallback: try to infer from other sources or use unknown
        if not command_type:
            # Could be enhanced to extract from ExecutionProgress._command_type if available
            command_type = "unknown"  # More accurate than assuming "collect"

        result["command_type"] = command_type

        return result


class ExecutionProcessor(IExecutionProcessor):
    """
    Processes execution events and provides progress tracking.

    Features:
    - Real-time progress updates for backtests and live trading
    - Performance metrics collection and reporting
    - Trading statistics aggregation
    - ETA calculation and status messaging
    - Event-driven progress broadcasting
    - Memory-efficient progress storage
    """

    def __init__(self,
                 event_bus: Any,
                 broadcast_provider: BroadcastProvider,
                 logger: StructuredLogger,
                 settings: Optional[Any] = None):
        """
        Initialize ExecutionProcessor.

        Args:
            event_bus: EventBus for publishing progress updates
            broadcast_provider: Centralized broadcast provider for WebSocket messages
            logger: Optional logger instance
            settings: AppSettings instance for configuration
        """
        self.event_bus = event_bus
        self.broadcast_provider = broadcast_provider
        self.logger = logger
        self.settings = settings
        self._background_tasks: weakref.WeakSet = weakref.WeakSet()

        # Thread safety locks - OPTIMIZED: Only async locks for consistency
        self._progress_lock = asyncio.Lock()  # Protects active_progress dictionary
        self._results_lock = asyncio.Lock()   # Protects completed_results deque  
        self._stats_lock = asyncio.Lock()     # Protects statistics (async-only for consistency)

        # Progress tracking with memory limits
        self.active_progress: Dict[str, ExecutionProgress] = {}
        self.completed_results: deque[ExecutionResult] = deque(maxlen=1000)

        # Progress update settings
        self.progress_update_interval = settings.websocket.progress_update_interval_seconds if settings else 1.0
        self.max_progress_history = 1000
        self.max_broadcast_queue_size = settings.websocket.max_broadcast_queue_size if settings else 5000

        # Latency monitoring for performance tracking - TRADING OPTIMIZED
        self.latency_threshold_ms = settings.performance_monitoring.latency_threshold_ms if settings else 50  # Reduced from 100
        self.latency_measurements = deque(maxlen=settings.performance_monitoring.max_latency_measurements if settings else 1000)

        # Memory leak prevention - TTL and cleanup
        self.session_ttl_hours = settings.performance_monitoring.session_ttl_hours if settings else 24
        self.cleanup_interval_seconds = settings.performance_monitoring.cleanup_interval_seconds if settings else 300
        self._last_cleanup = datetime.now()

        # Performance tracking with atomic operations
        self._events_processed = 0
        self._progress_updates_sent = 0
        self._average_processing_time = 0.0
        self._processing_times: deque[float] = deque(maxlen=1000)

        # ✅ OBSERVABILITY: Advanced metrics for monitoring
        self._handler_execution_times: deque[float] = deque(maxlen=1000)
        self._synthetic_events_generated = 0
        self._broadcast_latencies: deque[float] = deque(maxlen=1000)
        self._serialization_times: deque[float] = deque(maxlen=1000)
        self._event_publish_failures = 0
        self._cpu_offload_times: deque[float] = deque(maxlen=1000)

        # Shutdown event for graceful stop
        self._shutdown_event = asyncio.Event()

    # Atomic property accessors for thread-safe statistics - OPTIMIZED: Async-only
    async def get_events_processed(self) -> int:
        async with self._stats_lock:
            return self._events_processed

    async def set_events_processed(self, value: int):
        async with self._stats_lock:
            self._events_processed = value

    async def increment_events_processed(self):
        async with self._stats_lock:
            self._events_processed += 1

    async def get_progress_updates_sent(self) -> int:
        async with self._stats_lock:
            return self._progress_updates_sent

    async def set_progress_updates_sent(self, value: int):
        async with self._stats_lock:
            self._progress_updates_sent = value

    async def increment_progress_updates_sent(self):
        async with self._stats_lock:
            self._progress_updates_sent += 1

    async def get_average_processing_time(self) -> float:
        async with self._stats_lock:
            return self._average_processing_time

    async def set_average_processing_time(self, value: float):
        async with self._stats_lock:
            self._average_processing_time = value

    @property
    def processing_times(self) -> deque[float]:
        # Lock-free read for performance - deque operations are atomic in CPython
        return self._processing_times

    async def start(self):
        """Start the execution processor"""
        self.logger.info("execution_processor.started")

    async def stop(self):
        """Stop the execution processor gracefully with deadlock prevention"""
        self._shutdown_event.set()
        self.logger.info("execution_processor.stopped")

    async def process_execution_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Process an execution event from the EventBus.

        Args:
            event_type: Type of execution event
            event_data: Event data payload
        """
        start_time = time.time()
        # Lock-free atomic increment for performance
        self._events_processed += 1

        try:
            # Normalize event data by flattening potential nested payloads.
            # This handles cases where event data is wrapped in keys like "session" or "data".
            # The first matching key found will be flattened.
            normalized_data = self._flatten_payload(event_data, keys_to_flatten=["session", "data"])
            session_id = normalized_data.get("session_id")

            if not session_id:
                self.logger.warning("execution_processor.missing_session_id", {
                    "event_type": event_type,
                    "original_keys": list(event_data.keys())
                })
                return

            self.logger.debug(f"Processing {event_type} for session: {session_id}")

            # ✅ OBSERVABILITY: Track handler execution time
            handler_start = time.time()
            if event_type == "execution.session_started":
                await self._handle_session_started(normalized_data)
            elif event_type == "execution.progress_update":
                await self._handle_progress_update(normalized_data)
            elif event_type == "execution.session_completed":
                await self._handle_session_completed(normalized_data)
            elif event_type == "execution.session_failed":
                await self._handle_session_failed(normalized_data)
            else:
                self.logger.warning("execution_processor.unknown_event_type", {
                    "event_type": event_type,
                    "session_id": session_id
                })

            handler_time = (time.time() - handler_start) * 1000
            # Lock-free append - deque operations are atomic in CPython
            self._handler_execution_times.append(handler_time)

            # Track total processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            # Lock-free update of average processing time
            self._average_processing_time = sum(self.processing_times) / len(self.processing_times)

        except Exception as e:
            self.logger.error("execution_processor.event_processing_error", {
                "event_type": event_type,
                "error": str(e),
                "session_id": event_data.get("session_id")
            })

    def _flatten_payload(self, payload: Dict[str, Any], keys_to_flatten: List[str]) -> Dict[str, Any]:
        """
        Flattens a nested dictionary from a list of possible keys.
        The first key found in the payload will be used as the source for flattening.
        Top-level keys in the original payload will overwrite nested keys.
        """
        for key in keys_to_flatten:
            if key in payload and isinstance(payload[key], dict):
                nested_data = payload[key]
                # Merge nested data with top-level data, preferring top-level values
                flattened = {**nested_data, **payload}
                flattened.pop(key, None)
                return flattened
        return payload

    def _normalize_command_type(self, command_type_raw: Any) -> str:
        """Normalize command_type from various formats (enum, string, etc.) to string"""
        if command_type_raw is None or command_type_raw == "unknown":
            return "unknown"

        command_type_str = str(command_type_raw)

        # Handle enum format like "ExecutionMode.DATA_COLLECTION"
        if "." in command_type_str:
            command_type_str = command_type_str.split(".")[-1]

        # Convert to lowercase with underscores
        return command_type_str.lower()

    async def _handle_session_started(self, event_data: Dict[str, Any]):
        """Handle session started event with thread safety"""
        session_id = event_data["session_id"]
        # Normalize command_type properly
        command_type_raw = event_data.get("command_type") or event_data.get("session_type") or event_data.get("mode") or "unknown"
        command_type = self._normalize_command_type(command_type_raw)

        # Calculate total steps based on command type
        total_steps = self._calculate_total_steps(event_data)

        session_start_time = datetime.now()
        progress = ExecutionProgress(
            session_id=session_id,
            progress_percentage=0.0,
            current_step=0,
            total_steps=total_steps,
            status_message=f"{command_type.replace('_', ' ').title()} session started",
            performance_metrics={
                "processing_rate": 0.0,
                "memory_usage_mb": 0.0,
                "cpu_usage_pct": 0.0
            },
            trading_stats={
                "signals_detected": 0,
                "positions_opened": 0,
                "positions_closed": 0,
                "current_open_positions": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0
            },
            _command_type=command_type,
            _session_start_time=session_start_time
        )

        async with self._progress_lock:
            self.active_progress[session_id] = progress

        # Broadcast initial progress
        self._schedule_progress_broadcast(progress)

        self.logger.info("execution_processor.session_started", {
            "session_id": session_id,
            "command_type": command_type,
            "total_steps": total_steps
        })

    async def _update_collect_progress(self, progress: ExecutionProgress, payload: Dict[str, Any]):
        """Update progress for a 'collect' type session."""
        progress_payload = payload.get("progress", {})
        records_collected = payload.get("records_collected")

        percentage = progress_payload.get("percentage")
        if isinstance(percentage, (int, float)):
            progress.progress_percentage = float(percentage)

        current_step = progress_payload.get("current_step")
        if isinstance(current_step, (int, float)):
            progress.current_step = int(current_step)

        eta_seconds = progress_payload.get("eta_seconds")
        progress.eta_seconds = int(eta_seconds) if isinstance(eta_seconds, (int, float)) else None

        if records_collected is None:
            records_collected = progress.current_step
        if isinstance(records_collected, (int, float)):
            records_int = int(records_collected)
        else:
            records_int = progress.trading_stats.get("records_collected", 0)

        progress.trading_stats["records_collected"] = records_int
        progress.status_message = f"Data collection active - {records_int:,} records collected"

        print(f"[PROCESSOR DEBUG] Updated collect progress: percentage={progress.progress_percentage}%, records={records_int}")

    async def _update_backtest_progress(self, progress: ExecutionProgress, payload: Dict[str, Any]):
        """Update progress for a 'backtest' or similar type session."""
        progress_payload = payload.get("progress", {})
        performance_payload = payload.get("performance", {})
        trading_payload = payload.get("trading_stats", {})

        percentage = progress_payload.get("percentage")
        if isinstance(percentage, (int, float)):
            progress.progress_percentage = float(percentage)

        processed_candles = progress_payload.get("processed_candles")
        if isinstance(processed_candles, (int, float)):
            progress.current_step = int(processed_candles)

        total_steps = progress_payload.get("total_steps")
        if isinstance(total_steps, (int, float)):
            progress.total_steps = int(total_steps)

        current_date_str = progress_payload.get("current_date")
        if isinstance(current_date_str, str):
            try:
                progress.current_date = datetime.fromisoformat(current_date_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        eta_seconds = progress_payload.get("eta_seconds")
        progress.eta_seconds = int(eta_seconds) if isinstance(eta_seconds, (int, float)) else None

        progress.status_message = self._generate_status_message(progress)

        if isinstance(performance_payload, dict) and performance_payload:
            progress.performance_metrics.update({
                "processing_rate": performance_payload.get("processing_rate", progress.performance_metrics.get("processing_rate", 0.0)),
                "memory_usage_mb": performance_payload.get("memory_usage_mb", progress.performance_metrics.get("memory_usage_mb", 0.0)),
                "cpu_usage_pct": performance_payload.get("cpu_usage_pct", progress.performance_metrics.get("cpu_usage_pct", 0.0))
            })

        if isinstance(trading_payload, dict) and trading_payload:
            progress.trading_stats.update({
                "signals_detected": trading_payload.get("signals_detected", progress.trading_stats.get("signals_detected", 0)),
                "positions_opened": trading_payload.get("positions_opened", progress.trading_stats.get("positions_opened", 0)),
                "positions_closed": trading_payload.get("positions_closed", progress.trading_stats.get("positions_closed", 0)),
                "current_open_positions": trading_payload.get("current_open_positions", progress.trading_stats.get("current_open_positions", 0)),
                "total_pnl": trading_payload.get("total_pnl", progress.trading_stats.get("total_pnl", 0.0)),
                "win_rate": trading_payload.get("win_rate", progress.trading_stats.get("win_rate", 0.0)),
                "max_drawdown": trading_payload.get("max_drawdown", progress.trading_stats.get("max_drawdown", 0.0))
            })

    async def _handle_progress_update(self, event_data: Dict[str, Any]):
        """Handle progress update event with thread safety"""
        # Periodic cleanup of expired sessions to prevent memory leaks from stale sessions
        await self.cleanup_expired_sessions()

        payload = event_data.get("data") if isinstance(event_data.get("data"), dict) else event_data
        session_id = payload.get("session_id") or event_data.get("session_id")

        if not session_id:
            self.logger.warning("execution_processor.progress_update_missing_session", {
                "event_keys": list(event_data.keys())
            })
            return

        # Normalize command_type properly
        command_type_raw = payload.get("command_type") or payload.get("mode") or "unknown"
        command_type = self._normalize_command_type(command_type_raw)

        # Propagate status field from controller events (pause/stop transitions)
        controller_status = payload.get("status")

        async with self._progress_lock:
            if session_id not in self.active_progress:
                if command_type == "collect":
                    session_start_time = datetime.now()
                    progress = ExecutionProgress(
                        session_id=session_id,
                        progress_percentage=0.0,
                        current_step=0,
                        total_steps=0,
                        status_message="Data collection in progress",
                        performance_metrics={
                            "processing_rate": 0.0,
                            "memory_usage_mb": 0.0,
                            "cpu_usage_pct": 0.0
                        },
                        trading_stats={
                            "signals_detected": 0,
                            "positions_opened": 0,
                            "positions_closed": 0,
                            "current_open_positions": 0,
                            "total_pnl": 0.0,
                            "win_rate": 0.0,
                            "max_drawdown": 0.0,
                            "records_collected": 0
                        },
                        _command_type=command_type,  # Store command_type for serialization
                        _session_start_time=session_start_time  # Set session start time for accurate duration calculation
                    )
                    self.active_progress[session_id] = progress
                else:
                    self.logger.warning("execution_processor.progress_update_unknown_session", {
                        "session_id": session_id
                    })
                    return

            progress = self.active_progress[session_id]

            if command_type == "collect":
                await self._update_collect_progress(progress, payload)
            else:
                await self._update_backtest_progress(progress, payload)

            progress.last_update = datetime.now()

        if command_type != "collect":
            try:
                symbols = []
                if isinstance(payload.get("parameters"), dict):
                    symbols = payload["parameters"].get("symbols", [])
                if not symbols and isinstance(payload.get("results"), dict):
                    symbols = payload["results"].get("symbols", [])
                if not symbols:
                    symbols = payload.get("symbols", [])

                if not symbols:
                    self.logger.warning("execution_processor.synthetic_updates_missing_symbols", {
                        "session_id": session_id,
                        "event_keys": list(payload.keys())
                    })
                else:
                    # ✅ PERFORMANCE: Offload CPU-bound synthetic event generation to thread pool
                    asyncio.create_task(self._generate_synthetic_events_offloaded(symbols[:10], progress))

            except Exception as e:
                self.logger.error("execution_processor.synthetic_events_error", {
                    "session_id": session_id,
                    "error": str(e)
                })

        # Broadcast progress based on session type
        if command_type == "data_collection":
            # For data collection, broadcast every update to ensure real-time feedback
            self._schedule_progress_broadcast(progress, terminal_status=controller_status)
            self.logger.debug("execution_processor.data_collection_progress", {
                "session_id": session_id,
                "progress_percentage": progress.progress_percentage,
                "records_collected": progress.trading_stats.get("records_collected", 0),
                "eta_seconds": progress.eta_seconds
            })
        else:
            # For other types, broadcast and log based on progress milestones
            self._schedule_progress_broadcast(progress, terminal_status=controller_status)
            if progress.progress_percentage % 10 == 0:
                self.logger.info("execution_processor.progress_update", {
                    "session_id": session_id,
                    "progress_percentage": progress.progress_percentage,
                    "current_step": progress.current_step,
                    "eta_seconds": progress.eta_seconds
                })

    async def _generate_synthetic_events_offloaded(self, symbols: List[str], progress: ExecutionProgress):
        """Generate synthetic events in thread pool to avoid blocking event loop"""
        try:
            loop = asyncio.get_running_loop()
            offload_start = time.time()

            # Offload CPU-bound calculations to thread pool
            synthetic_data = await loop.run_in_executor(
                None,  # Use default thread pool
                self._calculate_synthetic_payloads,
                symbols,
                progress.current_step
            )

            offload_time = (time.time() - offload_start) * 1000
            # Lock-free operations - deque append and atomic increment
            self._cpu_offload_times.append(offload_time)
            self._synthetic_events_generated += len(synthetic_data) * 2  # market + indicators

            # Publish events asynchronously (fire-and-forget)
            for market_payload, indicators_payload in synthetic_data:
                asyncio.create_task(self.event_bus.publish("market.price_update", market_payload))
                asyncio.create_task(self.event_bus.publish("indicator.updated", indicators_payload))

        except Exception as e:
            # Lock-free atomic increment for error counter
            self._event_publish_failures += 1
            self.logger.error("execution_processor.synthetic_generation_failed", {
                "session_id": progress.session_id,
                "symbol_count": len(symbols),
                "error": str(e)
            })

    def _calculate_synthetic_payloads(self, symbols: List[str], current_step: int) -> List[tuple]:
        """CPU-bound calculation of synthetic market data - runs in thread pool"""
        now_iso = datetime.now().isoformat()
        results = []

        for idx, sym in enumerate(symbols):
            # These calculations are CPU-bound and would block the event loop
            price = 100.0 + ((current_step + idx) % 50)
            volume = 500.0 + ((current_step + idx) % 200)

            market_payload = {
                "symbol": sym,
                "price": float(price),
                "volume": float(volume),
                "timestamp": now_iso
            }

            indicators_payload = {
                "indicators": [
                    {"name": "RSI", "value": 55.0, "symbol": sym, "timestamp": now_iso, "used_by_strategies": ["flash_pump_detection"]},
                    {"name": "PUMP_MAGNITUDE_PCT", "value": 2.5, "symbol": sym, "timestamp": now_iso, "used_by_strategies": ["flash_pump_detection"]},
                    {"name": "VOLUME_SURGE_RATIO", "value": 3.6, "symbol": sym, "timestamp": now_iso, "used_by_strategies": ["flash_pump_detection"]}
                ]
            }

            results.append((market_payload, indicators_payload))

        return results

    async def _handle_session_completed(self, event_data: Dict[str, Any]):
        """Handle session completed event with thread safety"""
        session_id = event_data["session_id"]
        status = event_data.get("status", "completed")

        async with self._progress_lock:
            if session_id not in self.active_progress:
                self.logger.warning("execution_processor.completion_unknown_session", {
                    "session_id": session_id
                })
                return

            progress = self.active_progress[session_id]

            # Broadcast final execution_status update before removing entry
            # This ensures the UI sees the terminal status instead of staying in "running"
            command_type_display = progress._command_type.replace('_', ' ').title() if progress._command_type != "unknown" else "Execution"
            progress.status_message = f"{command_type_display} completed"
            progress.progress_percentage = 100.0

            # ✅ Preserve original last_update for accurate duration calculation
            original_last_update = progress.last_update
            progress.last_update = datetime.now()  # Update for broadcast timestamp only

            # ✅ Ensure records_collected is preserved in final broadcast
            if "records_collected" not in progress.trading_stats:
                progress.trading_stats["records_collected"] = 0

            self._schedule_progress_broadcast(progress, terminal_status="completed")

            # ✅ Restore original timestamp for duration calculation
            progress.last_update = original_last_update

            # Create final result with accurate duration calculation
            # Use session start time from progress object for accurate duration
            session_start_time = getattr(progress, '_session_start_time', progress.last_update)
            total_duration_seconds = (datetime.now() - session_start_time).total_seconds()

            result = ExecutionResult(
                session_id=session_id,
                status=status,
                total_duration_seconds=total_duration_seconds,
                final_results={
                    "progress": progress.to_dict(),
                    "final_stats": progress.trading_stats,
                    "performance_summary": progress.performance_metrics
                }
            )

            # Remove from active progress
            del self.active_progress[session_id]

        async with self._results_lock:
            # Store completed result
            self.completed_results.append(result)

        # Broadcast final result (execution_result stream)
        self._schedule_result_broadcast(result)

        self.logger.info("execution_processor.session_completed", {
            "session_id": session_id,
            "status": status,
            "total_duration_seconds": result.total_duration_seconds,
            "final_pnl": progress.trading_stats.get("total_pnl", 0)
        })

    async def _handle_session_failed(self, event_data: Dict[str, Any]):
        """Handle session failed event with thread safety"""
        session_id = event_data["session_id"]
        error_message = event_data.get("error_message", "Unknown error")

        async with self._progress_lock:
            if session_id not in self.active_progress:
                self.logger.warning("execution_processor.failure_unknown_session", {
                    "session_id": session_id
                })
                return

            progress = self.active_progress[session_id]

            # Broadcast final execution_status update before removing entry
            # This ensures the UI sees the terminal status instead of staying in "running"
            command_type_display = progress._command_type.replace('_', ' ').title() if progress._command_type != "unknown" else "Execution"
            progress.status_message = f"{command_type_display} failed: {error_message}"
            progress.progress_percentage = progress.progress_percentage  # Keep current progress

            # ✅ Preserve original last_update for accurate duration calculation
            original_last_update = progress.last_update
            progress.last_update = datetime.now()  # Update for broadcast timestamp only

            # ✅ Ensure records_collected is preserved in final broadcast
            if "records_collected" not in progress.trading_stats:
                progress.trading_stats["records_collected"] = 0

            self._schedule_progress_broadcast(progress, terminal_status="failed", error_message=error_message)

            # ✅ Restore original timestamp for duration calculation
            progress.last_update = original_last_update

            # Create failure result with accurate duration calculation
            # Use session start time from progress object for accurate duration
            session_start_time = getattr(progress, '_session_start_time', progress.last_update)
            total_duration_seconds = (datetime.now() - session_start_time).total_seconds()

            result = ExecutionResult(
                session_id=session_id,
                status="failed",
                total_duration_seconds=total_duration_seconds,
                final_results={
                    "progress": progress.to_dict(),
                    "failure_point": progress.progress_percentage,
                    "error_context": progress.trading_stats
                },
                error_message=error_message
            )

            # Remove from active progress
            del self.active_progress[session_id]

        async with self._results_lock:
            # Store failed result
            self.completed_results.append(result)

        # Broadcast failure result (execution_result stream)
        self._schedule_result_broadcast(result)

        self.logger.error("execution_processor.session_failed", {
            "session_id": session_id,
            "error_message": error_message,
            "progress_at_failure": progress.progress_percentage
        })

    def _calculate_total_steps(self, event_data: Dict[str, Any]) -> int:
        """Calculate total steps for execution based on parameters"""
        command_type = event_data.get("command_type", "backtest")
        params = event_data.get("parameters", {})

        if command_type == "backtest":
            # Calculate based on date range and symbols
            symbols = params.get("symbols", [])
            date_range = params.get("date_range", {})
            timeframe = params.get("timeframe", "1h")

            try:
                start = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))
                days = (end - start).days

                # Timeframe multipliers
                timeframe_multipliers = {
                    "1m": 1440,  # Minutes per day
                    "5m": 288,
                    "15m": 96,
                    "1h": 24,
                    "4h": 6,
                    "1d": 1
                }

                return days * timeframe_multipliers.get(timeframe, 24) * len(symbols)
            except:
                return 1000  # Default fallback

        elif command_type == "live_trading":
            # Live trading doesn't have fixed steps
            return 0

        return 100  # Default

    def _generate_status_message(self, progress: ExecutionProgress) -> str:
        """Generate human-readable status message"""
        if progress.progress_percentage >= 100:
            return "Execution completed"
        elif progress.progress_percentage >= 90:
            return "Finalizing execution"
        elif progress.progress_percentage >= 75:
            return "Processing remaining data"
        elif progress.progress_percentage >= 50:
            return "Execution in progress"
        elif progress.progress_percentage >= 25:
            return "Gathering momentum"
        elif progress.progress_percentage >= 10:
            return "Initializing execution"
        else:
            return "Starting execution"

    def _prepare_progress_payload(self, progress: ExecutionProgress, terminal_status: Optional[str] = None, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Prepare the progress data payload for broadcasting."""
        progress_data = progress.to_dict()

        # Use terminal status if provided (for completion/failure)
        if terminal_status:
            progress_data["status"] = terminal_status
        
        # Always include error_message if provided
        if error_message:
            progress_data["error_message"] = error_message

        # Always include command_type from progress object for frontend filtering
        if hasattr(progress, '_command_type') and progress._command_type != "unknown":
            progress_data["command_type"] = progress._command_type

        # Always normalize records_collected to top-level for frontend compatibility
        records_collected = progress.trading_stats.get("records_collected", 0)
        if records_collected > 0 or progress._command_type == "collect":
            progress_data["records_collected"] = records_collected
            
        return progress_data

    def _schedule_background_task(self, coro: Awaitable[Any], task_name: str) -> None:
        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)

        def _on_done(completed_task: asyncio.Task, name: str = task_name):
            try:
                completed_task.result()
            except Exception as e:
                self.logger.error("execution_processor.background_task_error", {
                    "task": name,
                    "error": str(e)
                })

        task.add_done_callback(_on_done)

    def _schedule_progress_broadcast(self, progress: ExecutionProgress, terminal_status: Optional[str] = None, error_message: Optional[str] = None) -> None:
        self._schedule_background_task(
            self._broadcast_progress(progress, terminal_status, error_message),
            f"execution-progress-{progress.session_id}"
        )

    def _schedule_result_broadcast(self, result: ExecutionResult) -> None:
        self._schedule_background_task(
            self._broadcast_result(result),
            f"execution-result-{result.session_id}"
        )

    async def _broadcast_progress(self, progress: ExecutionProgress, terminal_status: Optional[str] = None, error_message: Optional[str] = None):
        """Broadcast progress update to WebSocket clients with optimized serialization"""
        start_time = time.time()  # Start latency measurement
        success = False

        try:
            # ✅ PERFORMANCE: Prepare payload once - BroadcastProvider handles serialization
            progress_payload = self._prepare_progress_payload(progress, terminal_status, error_message)
        except Exception as e:
            self.logger.error("execution_processor.progress_data_error", {
                    "session_id": progress.session_id if 'progress' in locals() else "unknown",
                    "terminal_status": terminal_status,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            return # Do not proceed if payload preparation fails

        # Use centralized broadcast provider if available
        if self.broadcast_provider:
            try:
                success = await asyncio.wait_for(
                    self.broadcast_provider.broadcast_execution_progress(
                        session_id=progress.session_id,
                        progress_data=progress_payload  # Pass dict, let BroadcastProvider handle serialization
                    ),
                    timeout=1.0  # Reduced timeout for trading (was 5.0)
                )
            except asyncio.TimeoutError:
                self.logger.warning("execution_processor.broadcast_timeout", {
                    "session_id": progress.session_id,
                    "timeout_seconds": 1.0  # Updated timeout value
                })
                success = False
        elif not self.broadcast_provider:
            self.logger.error("execution_processor.broadcast_provider_missing", {
                "session_id": progress.session_id
            })
            success = False

        if success:
            # Lock-free atomic increment for performance
            self._progress_updates_sent += 1
            latency_ms = (time.time() - start_time) * 1000
            self.latency_measurements.append(latency_ms)
            # Lock-free append - deque operations are atomic in CPython
            self._broadcast_latencies.append(latency_ms)

            if latency_ms > self.latency_threshold_ms:
                self.logger.warning("execution_processor.high_latency", {
                    "session_id": progress.session_id,
                    "latency_ms": latency_ms,
                    "threshold_ms": self.latency_threshold_ms,
                    "operation": "broadcast_progress"
                })
        else:
            # Lock-free atomic increment for error counter
            self._event_publish_failures += 1
            self.logger.warning("execution_processor.broadcast_progress_failed", {
                "session_id": progress.session_id
            })



    async def _broadcast_result(self, result: ExecutionResult):
        """Broadcast execution result to WebSocket clients"""
        try:
            # Use centralized broadcast provider if available
            # Use centralized broadcast provider
            if self.broadcast_provider:
                success = await self.broadcast_provider.broadcast_execution_result(
                    session_id=result.session_id,
                    result_data=result.to_dict()
                )

                if not success:
                    self.logger.warning("execution_processor.broadcast_result_failed", {
                        "session_id": result.session_id
                    })
            elif not self.broadcast_provider:
                self.logger.error("execution_processor.broadcast_provider_missing_for_result", {
                    "session_id": result.session_id
                })

        except Exception as e:
            self.logger.error("execution_processor.broadcast_result_error", {
                "session_id": result.session_id,
                "error": str(e)
            })

    async def get_session_progress_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session - async version"""
        async with self._progress_lock:
            if session_id in self.active_progress:
                return self.active_progress[session_id].to_dict()
        return None

    async def get_session_result_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get final result for a completed session - async version"""
        async with self._results_lock:
            for result in self.completed_results:
                if result.session_id == session_id:
                    return result.to_dict()
        return None

    async def get_active_sessions_async(self) -> List[Dict[str, Any]]:
        """Get all active execution sessions - async version"""
        async with self._progress_lock:
            return [progress.to_dict() for progress in self.active_progress.values()]

    async def get_completed_sessions_async(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent completed execution sessions - async version"""
        async with self._results_lock:
            return [result.to_dict() for result in list(self.completed_results)[-limit:]]

    # Legacy sync methods for backward compatibility - delegate to async versions
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session - LEGACY: Use get_session_progress_async"""
        try:
            # Try to get running event loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, delegate to async method
            return loop.run_until_complete(self.get_session_progress_async(session_id))
        except RuntimeError:
            # No running loop, use sync lock (not ideal but maintains compatibility)
            with self._progress_lock_sync:
                if session_id in self.active_progress:
                    return self.active_progress[session_id].to_dict()
            return None

    def get_session_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get final result for a completed session - LEGACY: Use get_session_result_async"""
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(self.get_session_result_async(session_id))
        except RuntimeError:
            with self._results_lock_sync:
                for result in self.completed_results:
                    if result.session_id == session_id:
                        return result.to_dict()
            return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active execution sessions - LEGACY: Use get_active_sessions_async"""
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(self.get_active_sessions_async())
        except RuntimeError:
            with self._progress_lock_sync:
                return [progress.to_dict() for progress in self.active_progress.values()]

    def get_completed_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent completed execution sessions - LEGACY: Use get_completed_sessions_async"""
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(self.get_completed_sessions_async(limit))
        except RuntimeError:
            with self._results_lock_sync:
                return [result.to_dict() for result in list(self.completed_results)[-limit:]]

    async def cleanup_expired_sessions(self):
        """Cleanup expired active sessions automatically"""
        now = datetime.now()
        if (now - self._last_cleanup).seconds < self.cleanup_interval_seconds:
            return

        cutoff_time = now - timedelta(hours=self.session_ttl_hours)
        expired_sessions = []

        async with self._progress_lock:
            for session_id, progress in list(self.active_progress.items()):
                if progress.last_update < cutoff_time:
                    expired_sessions.append(session_id)
                    del self.active_progress[session_id]

        if expired_sessions:
            self.logger.info("execution_processor.expired_sessions_cleaned", {
                "expired_count": len(expired_sessions),
                "session_ids": expired_sessions
            })
        self._last_cleanup = now

    def get_stats(self) -> Dict[str, Any]:
        """Get ExecutionProcessor statistics with comprehensive observability metrics - LOCK-FREE READ"""
        # Lock-free reads for performance (minor race conditions acceptable for stats)
        active_count = len(self.active_progress)
        completed_count = len(self.completed_results)

        # Lock-free stats access - snapshot view
        latency_stats = {
            "avg_latency_ms": sum(self.latency_measurements) / len(self.latency_measurements) if self.latency_measurements else 0,
            "max_latency_ms": max(self.latency_measurements) if self.latency_measurements else 0,
            "measurements_count": len(self.latency_measurements)
        }

        # Handler execution statistics
        handler_stats = {
            "avg_handler_time_ms": sum(self._handler_execution_times) / len(self._handler_execution_times) if self._handler_execution_times else 0,
            "max_handler_time_ms": max(self._handler_execution_times) if self._handler_execution_times else 0,
            "handler_executions_count": len(self._handler_execution_times)
        }

        # Broadcast performance statistics
        broadcast_stats = {
            "avg_broadcast_latency_ms": sum(self._broadcast_latencies) / len(self._broadcast_latencies) if self._broadcast_latencies else 0,
            "max_broadcast_latency_ms": max(self._broadcast_latencies) if self._broadcast_latencies else 0,
            "broadcast_count": len(self._broadcast_latencies)
        }

        # CPU offloading statistics
        cpu_stats = {
            "avg_cpu_offload_time_ms": sum(self._cpu_offload_times) / len(self._cpu_offload_times) if self._cpu_offload_times else 0,
            "max_cpu_offload_time_ms": max(self._cpu_offload_times) if self._cpu_offload_times else 0,
            "cpu_offloads_count": len(self._cpu_offload_times)
        }

        # EventBus health (if available)
        eventbus_stats = {}
        if self.event_bus:
            try:
                # Try to get EventBus memory stats asynchronously
                loop = asyncio.get_running_loop()
                eventbus_stats = loop.run_until_complete(self.event_bus.get_memory_stats())
            except:
                eventbus_stats = {"error": "Could not retrieve EventBus stats"}

        return {
            "events_processed": self._events_processed,
            "progress_updates_sent": self._progress_updates_sent,
            "active_sessions": active_count,
            "completed_sessions": completed_count,
            "average_processing_time_ms": self._average_processing_time,
            "processing_times_count": len(self._processing_times),

            # Observability metrics
            "latency_stats": latency_stats,
            "handler_stats": handler_stats,
            "broadcast_stats": broadcast_stats,
            "cpu_offload_stats": cpu_stats,
            "synthetic_events_generated": self._synthetic_events_generated,
            "event_publish_failures": self._event_publish_failures,
            "eventbus_health": eventbus_stats
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "ExecutionProcessor",
            "stats": await asyncio.get_event_loop().run_in_executor(None, self.get_stats),
            "timestamp": datetime.now().isoformat()
        }
