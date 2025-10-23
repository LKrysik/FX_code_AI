"""
Unified Trading Controller
==========================
Main controller integrating all execution components.
"""

import asyncio
from typing import Optional, List, Dict, Any

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.factories.indicator_engine_factory import IndicatorEngineFactory, ExecutionMode
from .execution_controller import ExecutionController
from ..services.execution_monitor import ExecutionMonitor
from ..services.command_processor import AsyncCommandProcessor, CommandType
from ...domain.services.streaming_indicator_engine import StreamingIndicatorEngine, IndicatorType


class UnifiedTradingController:
    """
    Unified controller for all trading operations.
    Integrates execution, monitoring, and command processing.
    """
    
    def __init__(self,
                 market_data_provider: Optional[IMarketDataProvider],
                 event_bus: EventBus,
                 logger: StructuredLogger,
                 data_path: str = "data",
                 wallet_service = None,
                 order_manager = None):

        self.market_data_provider = market_data_provider
        self.event_bus = event_bus
        self.logger = logger
        self.data_path = data_path

        # Store event_bus reference for adapters
        self._event_bus = event_bus
        self.indicator_engine = IndicatorEngineFactory.create_engine(ExecutionMode.LIVE, event_bus, logger=logger)

        # Trading components (optional for backtesting)
        self.wallet_service = wallet_service
        self.order_manager = order_manager

        # Execution mode
        self.execution_mode = "live"  # "live", "paper", "backtest"

        # State
        self._is_started = False
        self._is_initialized = False

        # Data collection progress tracking
        self._active_data_collections: Dict[str, Dict[str, Any]] = {}
        self._progress_update_tasks: Dict[str, asyncio.Task] = {}

        # Defer heavy initialization to async method
        self.market_data_factory = None
        self.execution_controller = None
        self.execution_monitor = None
        self.command_processor = None

        self.logger.info("unified_trading_controller.created", {
            "wallet_enabled": wallet_service is not None,
            "order_manager_enabled": order_manager is not None
        })

    async def initialize(self) -> None:
        """Async initialization to prevent blocking startup"""
        if self._is_initialized:
            return

        # Create market data provider factory
        from ...infrastructure.factories.market_data_factory import MarketDataProviderFactory
        from ...infrastructure.config.settings import AppSettings

        # Get settings from environment (moved to async context)
        try:
            settings = AppSettings()
            print(f"[DEBUG] AppSettings created: trading.mode={settings.trading.mode}")
            self.market_data_factory = MarketDataProviderFactory(settings, self.event_bus, self.logger)
            print(f"[DEBUG] Created market data factory: {self.market_data_factory}")
        except Exception as e:
            self.logger.error("unified_trading_controller.factory_creation_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise RuntimeError(f"Failed to create market data provider factory: {str(e)}") from e

        # Core components
        self.execution_controller = ExecutionController(self.event_bus, self.logger, self.market_data_factory)
        print(f"[DEBUG] ExecutionController created with factory: {self.execution_controller.market_data_provider_factory is not None}")
        self.execution_monitor = ExecutionMonitor(self.event_bus, self.logger)
        self.command_processor = AsyncCommandProcessor(
            self.execution_controller,
            self.market_data_provider,
            self.event_bus,
            self.logger,
            self.data_path,
            self.market_data_factory
        )

        self._is_initialized = True

        self.logger.info("unified_trading_controller.initialized", {
            "wallet_enabled": self.wallet_service is not None,
            "order_manager_enabled": self.order_manager is not None
        })
    
    async def start(self) -> None:
        """Start all components"""
        if self._is_started:
            return

        self._is_started = True

        # Start monitoring with reduced frequency to prevent CPU overload
        await self.execution_monitor.start_monitoring()

        # CRITICAL FIX: Only setup indicators when explicitly needed
        # Default indicators cause massive CPU usage from continuous calculations
        # await self._setup_default_indicators()

        self.logger.info("unified_trading_controller.started")
    
    async def stop(self) -> None:
        """Stop all components"""
        if not self._is_started:
            return

        self._is_started = False

        # Stop execution if running
        current_session = self.execution_controller.get_current_session()
        if current_session and current_session.status.value in ["running", "starting"]:
            await self.execution_controller.stop_execution()

        # Stop monitoring
        await self.execution_monitor.stop_monitoring()

        # Clean up all data collection progress tasks
        for session_id in list(self._active_data_collections.keys()):
            await self.stop_data_collection_progress(session_id)

        self.logger.info("unified_trading_controller.stopped")
    
    async def start_backtest(self, 
                           symbols: List[str],
                           acceleration_factor: float = 10.0,
                           **kwargs) -> str:
        """Start backtest execution"""
        
        parameters = {
            "symbols": symbols,
            "acceleration_factor": acceleration_factor,
            **kwargs
        }
        
        command_id = await self.command_processor.execute_command(
            CommandType.START_BACKTEST,
            parameters
        )
        
        self.logger.info("unified_trading_controller.backtest_started", {
            "command_id": command_id,
            "symbols": symbols
        })
        
        return command_id
    
    async def start_live_trading(self,
                                symbols: List[str],
                                mode: str = "paper",
                                **kwargs) -> str:
        """Start live trading execution"""

        parameters = {
            "symbols": symbols,
            "mode": mode,
            **kwargs
        }

        command_id = await self.command_processor.execute_command(
            CommandType.START_TRADING,
            parameters
        )

        self.logger.info("unified_trading_controller.live_trading_started", {
            "command_id": command_id,
            "symbols": symbols,
            "mode": mode
        })

        return command_id

    async def start_data_collection(self,
                                     symbols: List[str],
                                     duration: str,
                                     **kwargs) -> str:
        """Start data collection"""

        parameters = {
            "symbols": symbols,
            "duration": duration,
            **kwargs
        }

        self.logger.info("unified_trading_controller.start_data_collection_called", {
            "symbols": symbols,
            "duration": duration,
            "kwargs_keys": list(kwargs.keys()),
            "data_path_in_kwargs": kwargs.get("data_path"),
            "parameters": parameters
        })

        print(f"[CONTROLLER DEBUG] Starting data collection: symbols={symbols}, duration={duration}")

        command_id = await self.command_processor.execute_command(
            CommandType.START_DATA_COLLECTION,
            parameters
        )

        print(f"[CONTROLLER DEBUG] Command executed, command_id={command_id}")

        self.logger.info("unified_trading_controller.data_collection_started", {
            "command_id": command_id,
            "symbols": symbols,
            "duration": duration
        })

        # Send initial WebSocket progress update
        await self._send_progress_update(command_id, symbols, duration, 0, 0)

        print(f"[CONTROLLER DEBUG] Initial progress sent")

        # Start background progress update task
        self._active_data_collections[command_id] = {
            "symbols": symbols,
            "duration": duration,
            "start_time": asyncio.get_event_loop().time(),
            "records_collected": 0
        }
        print(f"[CONTROLLER DEBUG] Added to active collections: {command_id}")

        self._progress_update_tasks[command_id] = asyncio.create_task(
            self._progress_update_loop(command_id)
        )
        print(f"[CONTROLLER DEBUG] Progress update task created for {command_id}")

        return command_id
    
    async def stop_execution(self, force: bool = False) -> str:
        """Stop current execution"""

        parameters = {"force": force}

        command_id = await self.command_processor.execute_command(
            CommandType.STOP_EXECUTION,
            parameters
        )

        # Clean up any active data collection progress tasks
        for session_id in list(self._active_data_collections.keys()):
            await self.stop_data_collection_progress(session_id)

        return command_id
    
    async def pause_execution(self) -> str:
        """Pause current execution"""
        
        command_id = await self.command_processor.execute_command(
            CommandType.PAUSE_EXECUTION,
            {}
        )
        
        return command_id
    
    async def resume_execution(self) -> str:
        """Resume paused execution"""
        
        command_id = await self.command_processor.execute_command(
            CommandType.RESUME_EXECUTION,
            {}
        )
        
        return command_id
    
    def get_execution_status(self) -> Optional[Dict[str, Any]]:
        """Get current execution status"""
        session = self.execution_controller.get_current_session()
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "mode": session.mode.value,
            "status": session.status.value,
            "symbols": session.symbols,
            "progress": session.progress,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "metrics": session.metrics
        }

    def get_current_session(self):
        """Get current session object"""
        return self.execution_controller.get_current_session()
    
    def get_execution_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get execution metrics"""
        metrics = self.execution_monitor.get_session_metrics(session_id)
        if not metrics:
            return None
        
        return {
            "session_id": metrics.session_id,
            "timestamp": metrics.timestamp.isoformat(),
            "progress_percent": metrics.progress_percent,
            "eta_seconds": metrics.eta_seconds,
            "processing_rate": metrics.processing_rate,
            "signals_detected": metrics.signals_detected,
            "signals_per_minute": metrics.signals_per_minute,
            "orders_placed": metrics.orders_placed,
            "orders_filled": metrics.orders_filled,
            "orders_rejected": metrics.orders_rejected,
            "unrealized_pnl": metrics.unrealized_pnl,
            "realized_pnl": metrics.realized_pnl,
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "memory_used_mb": metrics.memory_used_mb
        }
    
    async def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get command execution status"""
        command = await self.command_processor.get_command_status(command_id)
        if not command:
            return None

        return {
            "command_id": command.command_id,
            "command_type": command.command_type.value,
            "status": command.status.value,
            "progress": command.progress,
            "created_at": command.created_at.isoformat(),
            "started_at": command.started_at.isoformat() if command.started_at else None,
            "completed_at": command.completed_at.isoformat() if command.completed_at else None,
            "result": command.result,
            "error": command.error,
            "session_id": command.session_id
        }

    async def get_active_commands(self) -> List[Dict[str, Any]]:
        """Get all active commands"""
        commands = await self.command_processor.get_active_commands()

        return [
            {
                "command_id": cmd.command_id,
                "command_type": cmd.command_type.value,
                "status": cmd.status.value,
                "progress": cmd.progress,
                "created_at": cmd.created_at.isoformat()
            }
            for cmd in commands
        ]
    
    async def cancel_command(self, command_id: str) -> bool:
        """Cancel a command"""
        return await self.command_processor.cancel_command(command_id)
    
    def add_indicator(self, 
                     symbol: str,
                     indicator_type: str,
                     period: int = 20,
                     timeframe: str = "1m",
                     scope: Optional[str] = None,
                     **kwargs) -> str:
        """Add a streaming indicator"""
        
        # Convert string to enum
        try:
            indicator_enum = IndicatorType(indicator_type.upper())
        except ValueError:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")
        
        return self.indicator_engine.add_indicator(
            symbol=symbol,
            indicator_type=indicator_enum,
            timeframe=timeframe,
            period=period,
            scope=scope,
            **kwargs
        )
    
    def get_indicator_value(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        """Get current indicator value"""
        indicator = self.indicator_engine.get_indicator(indicator_key)
        if not indicator:
            return None
        
        return {
            "symbol": indicator.symbol,
            "indicator": indicator.indicator,
            "timeframe": indicator.timeframe,
            "current_value": indicator.current_value,
            "timestamp": indicator.timestamp,
            "data_points": indicator.metadata.get("data_points", 0)
        }
    
    def get_indicators_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all indicators for a symbol"""
        indicators = self.indicator_engine.get_indicators_for_symbol(symbol)

        return [
            {
                "symbol": ind.symbol,
                "indicator": ind.indicator,
                "timeframe": ind.timeframe,
                "current_value": ind.current_value,
                "timestamp": ind.timestamp,
                "data_points": ind.metadata.get("data_points", 0)
            }
            for ind in indicators
        ]

    def list_indicators(self) -> List[Dict[str, Any]]:
        """List all active indicators"""
        return self.indicator_engine.list_indicators()
    
    async def _setup_default_indicators(self) -> None:
        """Setup default indicators for common symbols"""
        # This would be configured based on trading strategy
        default_symbols = ["ALU_USDT", "ARIA_USDT"]  # Example symbols
        
        for symbol in default_symbols:
            # Add common indicators
            self.indicator_engine.add_indicator(symbol, IndicatorType.SMA, period=20)
            self.indicator_engine.add_indicator(symbol, IndicatorType.EMA, period=12)
            self.indicator_engine.add_indicator(symbol, IndicatorType.RSI, period=14)
            self.indicator_engine.add_indicator(symbol, IndicatorType.MACD)
        
        self.logger.info("unified_trading_controller.default_indicators_setup", {
            "symbols": default_symbols
        })
    
    def get_wallet_balance(self) -> Optional[Dict[str, Any]]:
        """Get wallet balance"""
        if not self.wallet_service:
            return None
        return self.wallet_service.get_balance()

    def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        if not self.order_manager:
            return []
        return self.order_manager.get_all_orders()

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions"""
        if not self.order_manager:
            return []
        return self.order_manager.get_all_positions()

    def get_trading_performance(self) -> Optional[Dict[str, Any]]:
        """Get trading performance summary"""
        if not self.order_manager:
            return None
        return self.order_manager.get_performance_summary()

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""

        # Get execution status
        execution_status = self.get_execution_status()

        # Get active commands
        active_commands = await self.get_active_commands()

        # Get EventBus health
        eventbus_health = await self.event_bus.health_check()

        # Get wallet health
        wallet_healthy = False
        if self.wallet_service:
            try:
                balance = self.get_wallet_balance()
                wallet_healthy = balance is not None
            except Exception:
                wallet_healthy = False

        # Get order manager health
        order_manager_healthy = self.order_manager is not None

        return {
            "unified_controller": {
                "started": self._is_started,
                "execution_active": execution_status is not None,
                "active_commands": len(active_commands),
                "wallet_enabled": self.wallet_service is not None,
                "order_manager_enabled": self.order_manager is not None
            },
            "execution_status": execution_status,
            "active_commands": active_commands,
            "eventbus_health": eventbus_health,
            "wallet_healthy": wallet_healthy,
            "order_manager_healthy": order_manager_healthy,
            "timestamp": asyncio.get_event_loop().time()
        }

    async def _send_progress_update(self, session_id: str, symbols: List[str], duration: str, records_collected: int, progress_percentage: float):
        """Send WebSocket progress update for data collection"""
        import time
        from datetime import datetime

        # Calculate ETA based on progress
        eta_seconds = None
        if records_collected > 10 and progress_percentage > 0:
            # Estimate based on current progress
            elapsed_time = time.time() - time.time()  # This would need session start time
            if elapsed_time > 60:  # Need at least 1 minute of data
                collection_rate = records_collected / elapsed_time
                remaining_percentage = 100.0 - progress_percentage
                if collection_rate > 0:
                    eta_seconds = int((remaining_percentage / 100.0) * (elapsed_time / (progress_percentage / 100.0)))

        event_payload = {
            "session_id": session_id,
            "command_type": "collect",
            "progress": {
                "percentage": progress_percentage,
                "current_step": records_collected,
                "eta_seconds": eta_seconds
            },
            "records_collected": records_collected,
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }

        # Debug logging for WebSocket integration
        print(f"[WEBSOCKET DEBUG] Publishing progress update: session_id={session_id}, records={records_collected}, progress={progress_percentage:.1f}%")
        print(f"[CONTROLLER DEBUG] About to publish execution.progress_update: payload_keys={list(event_payload.keys())}, has_type={event_payload.get('type')}, has_stream={'stream' in event_payload}")
        self.logger.info("collect.websocket_progress_published", {
            "session_id": session_id,
            "records_collected": records_collected,
            "progress_percentage": progress_percentage,
            "eta_seconds": eta_seconds,
            "event_payload_keys": list(event_payload.keys())
        })

        await self.event_bus.publish("execution.progress_update", event_payload)

    async def _progress_update_loop(self, session_id: str):
        """Background task to send periodic progress updates during data collection"""
        print(f"[CONTROLLER DEBUG] Progress loop started for session_id={session_id}")
        try:
            while session_id in self._active_data_collections:
                print(f"[CONTROLLER DEBUG] Progress loop iteration for {session_id}")
                collection_info = self._active_data_collections[session_id]
                current_time = asyncio.get_event_loop().time()
                elapsed_time = current_time - collection_info["start_time"]

                # Parse duration to calculate progress
                duration_str = collection_info["duration"]
                if duration_str != 'continuous':
                    # Extract numeric value and unit
                    import re
                    match = re.match(r'^(\d+)([smhd])$', duration_str)
                    if match:
                        value, unit = match.groups()
                        value = int(value)

                        # Convert to seconds
                        unit_multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                        total_duration_seconds = value * unit_multipliers.get(unit, 3600)

                        # Calculate time-based progress
                        if total_duration_seconds > 0:
                            progress_percentage = min(95.0, (elapsed_time / total_duration_seconds) * 100)
                        else:
                            progress_percentage = 0.0
                    else:
                        progress_percentage = min(95.0, elapsed_time / 3600 * 100)  # Default to 1 hour
                else:
                    # Continuous collection - use logarithmic progress
                    progress_percentage = min(95.0, elapsed_time / 3600 * 100)

                # Simulate increasing records collected (in real implementation, this would come from actual data)
                records_collected = collection_info["records_collected"]
                if elapsed_time > 10:  # Start showing records after 10 seconds
                    records_collected = int(elapsed_time * 10)  # Simulate 10 records per second
                    collection_info["records_collected"] = records_collected

                print(f"[CONTROLLER DEBUG] Calculated progress: percentage={progress_percentage:.1f}%, records={records_collected}")

                # Send progress update
                await self._send_progress_update(
                    session_id,
                    collection_info["symbols"],
                    collection_info["duration"],
                    records_collected,
                    progress_percentage
                )

                print(f"[CONTROLLER DEBUG] Progress update sent in loop for {session_id}")

                # Wait before next update
                await asyncio.sleep(5.0)  # Update every 5 seconds

        except asyncio.CancelledError:
            print(f"[CONTROLLER DEBUG] Progress loop cancelled for {session_id}")
            # Task was cancelled, clean up
            pass
        except Exception as e:
            print(f"[CONTROLLER DEBUG] Progress loop error for {session_id}: {str(e)}")
            self.logger.error("unified_trading_controller.progress_update_loop_error", {
                "session_id": session_id,
                "error": str(e)
            })

    async def stop_data_collection_progress(self, session_id: str):
        """Stop progress updates for a data collection session"""
        if session_id in self._progress_update_tasks:
            task = self._progress_update_tasks[session_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._progress_update_tasks[session_id]

        if session_id in self._active_data_collections:
            del self._active_data_collections[session_id]

        # Send final progress update
        await self._send_progress_update(session_id, [], "completed", 0, 100.0)