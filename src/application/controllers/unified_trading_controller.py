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
                 order_manager = None,
                 indicator_engine = None,
                 trading_persistence_service = None):  # ✅ NEW: DI parameter for trading persistence

        self.market_data_provider = market_data_provider
        self.event_bus = event_bus
        self.logger = logger
        self.data_path = data_path

        # Store event_bus reference for adapters
        self._event_bus = event_bus

        # ✅ FIX: Indicator engine injected via Container instead of Factory
        # Factory is DEPRECATED and creates incomplete engine (no variant_repository)
        # Container creates engine with full configuration (variant persistence, shared registry)
        self.indicator_engine = indicator_engine  # Will be set during Container initialization

        # Trading components (optional for backtesting)
        self.wallet_service = wallet_service
        self.order_manager = order_manager
        self.trading_persistence_service = trading_persistence_service

        # Execution mode
        self.execution_mode = "live"  # "live", "paper", "backtest"

        # State
        self._is_started = False
        self._is_initialized = False

        # ✅ REMOVED: Duplicate progress tracking (now handled by ExecutionController with throttling)
        # Previous implementation had duplicate progress update loops causing excessive EventBus traffic
        # ExecutionController now has built-in throttling for progress events (5s interval)

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

        # ✅ VALIDATION: Indicator engine must be injected by Container
        if self.indicator_engine is None:
            raise RuntimeError(
                "indicator_engine is required but was not injected. "
                "UnifiedTradingController must be created via Container.create_unified_trading_controller() "
                "to ensure proper dependency injection with variant persistence."
            )

        # Create market data provider factory
        from ...infrastructure.factories.market_data_factory import MarketDataProviderFactory
        from ...infrastructure.config.settings import AppSettings

        # Get settings from environment (moved to async context)
        try:
            settings = AppSettings()
            self.market_data_factory = MarketDataProviderFactory(settings, self.event_bus, self.logger)
            self.logger.debug("unified_trading_controller.factory_created", {
                "trading_mode": settings.trading.mode,
                "factory_type": type(self.market_data_factory).__name__
            })
        except Exception as e:
            self.logger.error("unified_trading_controller.factory_creation_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise RuntimeError(f"Failed to create market data provider factory: {str(e)}") from e

        # Core components
        # Create data collection persistence service (optional - for QuestDB integration)
        db_persistence_service = None
        try:
            from ...data.data_collection_persistence_service import DataCollectionPersistenceService
            from ...data_feed.questdb_provider import QuestDBProvider

            # Create QuestDB provider
            questdb_provider = QuestDBProvider(
                ilp_host='127.0.0.1',
                ilp_port=9009,
                pg_host='127.0.0.1',
                pg_port=8812
            )

            # Create persistence service
            db_persistence_service = DataCollectionPersistenceService(
                db_provider=questdb_provider,
                logger=self.logger
            )

            self.logger.info("unified_trading_controller.db_persistence_enabled", {
                "provider": "QuestDB"
            })
        except Exception as e:
            # Optional feature - log but don't fail
            self.logger.warning("unified_trading_controller.db_persistence_disabled", {
                "error": str(e),
                "reason": "QuestDB persistence service could not be initialized"
            })

        self.execution_controller = ExecutionController(
            self.event_bus,
            self.logger,
            self.market_data_factory,
            db_persistence_service
        )
        self.logger.debug("unified_trading_controller.execution_controller_created", {
            "has_market_data_factory": self.execution_controller.market_data_provider_factory is not None,
            "has_db_persistence": self.execution_controller.db_persistence_service is not None
        })
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

        # Start order manager (subscribes to EventBus signals)
        if self.order_manager and hasattr(self.order_manager, 'start'):
            await self.order_manager.start()
            self.logger.info("unified_trading_controller.order_manager_started")

        # Start trading persistence (subscribes to EventBus signals/orders/positions)
        if self.trading_persistence_service:
            await self.trading_persistence_service.start()
            self.logger.info("unified_trading_controller.trading_persistence_started")

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

        # Stop order manager (unsubscribe from EventBus)
        if self.order_manager and hasattr(self.order_manager, 'stop'):
            await self.order_manager.stop()
            self.logger.info("unified_trading_controller.order_manager_stopped")

        # Stop trading persistence (unsubscribe from EventBus)
        if self.trading_persistence_service:
            await self.trading_persistence_service.stop()
            self.logger.info("unified_trading_controller.trading_persistence_stopped")

        # Stop monitoring
        await self.execution_monitor.stop_monitoring()

        # ✅ REMOVED: Progress task cleanup (no longer needed - ExecutionController handles progress)

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

        # ✅ FIX: Use execute_command_with_result to get session_id immediately
        try:
            result = await self.command_processor.execute_command_with_result(
                CommandType.START_BACKTEST,
                parameters,
                timeout=5.0
            )

            session_id = result.get("session_id")

            if not session_id:
                # Fallback to old behavior
                command_id = await self.command_processor.execute_command(
                    CommandType.START_BACKTEST,
                    parameters
                )
                return command_id

            self.logger.info("unified_trading_controller.backtest_started", {
                "session_id": session_id,
                "symbols": symbols
            })

            return session_id

        except ValueError as e:
            # CRITICAL: Re-raise validation errors so endpoint can return 400
            # Validation errors (missing session_id, invalid parameters) must fail fast
            error_msg = str(e)

            # Check if this is a validation error by looking for validation-related keywords
            # Catches: "session_id parameter is required" and "session not found" and similar errors
            if ("session" in error_msg.lower() and
                ("required" in error_msg.lower() or
                 "not found" in error_msg.lower() or
                 "validation" in error_msg.lower())):
                # Re-raise validation errors related to session for endpoint to handle (400 response)
                self.logger.error("unified_trading_controller.backtest_validation_failed", {
                    "error": error_msg
                })
                raise  # Let endpoint return 400

            # For other ValueErrors, use fallback
            self.logger.error("unified_trading_controller.backtest_execute_with_result_failed", {
                "error": error_msg,
                "fallback": "using execute_command"
            })

            command_id = await self.command_processor.execute_command(
                CommandType.START_BACKTEST,
                parameters
            )

            self.logger.info("unified_trading_controller.backtest_started_fallback", {
                "command_id": command_id,
                "symbols": symbols
            })

            return command_id

        except TimeoutError as e:
            # Fallback to async command execution on timeout
            self.logger.error("unified_trading_controller.backtest_timeout", {
                "error": str(e),
                "fallback": "using execute_command"
            })

            command_id = await self.command_processor.execute_command(
                CommandType.START_BACKTEST,
                parameters
            )

            self.logger.info("unified_trading_controller.backtest_started_fallback", {
                "command_id": command_id,
                "symbols": symbols
            })

            return command_id
    
    async def start_live_trading(self,
                                symbols: List[str],
                                mode: str = "paper",
                                **kwargs) -> str:
        """
        Start live or paper trading execution.

        Architecture:
        - mode="live": Uses LiveOrderManager (real MEXC exchange)
        - mode="paper": Uses OrderManager (simulated execution with slippage)
        - Both modes use MarketDataProviderAdapter (live market data via EventBus)
        - Order manager is configured once at Container startup via live_trading_enabled setting

        Args:
            symbols: List of trading symbols
            mode: "live" or "paper" (must match Container configuration)
            **kwargs: Additional parameters

        Returns:
            Session ID for tracking

        Raises:
            ValueError: If mode doesn't match Container configuration
        """
        # Validate mode matches Container configuration
        # Container creates either LiveOrderManager (live) or OrderManager (paper)
        from ...domain.services.order_manager_live import LiveOrderManager
        from ...domain.services.order_manager import OrderManager

        is_live_manager = isinstance(self.order_manager, LiveOrderManager)
        is_paper_manager = isinstance(self.order_manager, OrderManager) and not isinstance(self.order_manager, LiveOrderManager)

        if mode == "live" and not is_live_manager:
            raise ValueError(
                "Cannot start live trading: Container is configured with paper OrderManager. "
                "Set trading.live_trading_enabled=true in configuration to enable live trading."
            )
        elif mode == "paper" and not is_paper_manager:
            raise ValueError(
                "Cannot start paper trading: Container is configured with live OrderManager. "
                "Set trading.live_trading_enabled=false in configuration to enable paper trading."
            )

        # Map mode to ExecutionMode
        from .execution_controller import ExecutionMode
        execution_mode = ExecutionMode.LIVE if mode == "live" else ExecutionMode.PAPER

        # Create session via ExecutionController (uses MarketDataProviderAdapter)
        session_id = await self.execution_controller.create_session(
            mode=execution_mode,
            symbols=symbols,
            config={
                "mode": mode,
                **kwargs
            }
        )

        # Start session (connects to exchange, subscribes to EventBus)
        await self.execution_controller.start_session(session_id)

        self.logger.info("unified_trading_controller.trading_started", {
            "session_id": session_id,
            "mode": mode,
            "symbols": symbols,
            "live_trading": mode == "live"
        })

        return session_id

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

        # ✅ SESSION-005 FIX: Always return session_id, never command_id
        # Increased timeout and removed fallback to prevent client lookup failures
        try:
            result = await self.command_processor.execute_command_with_result(
                CommandType.START_DATA_COLLECTION,
                parameters,
                timeout=15.0  # ✅ SESSION-005: Increased from 5s to 15s for DB persistence
            )

            session_id = result.get("session_id")

            if not session_id:
                # ✅ SESSION-005: Raise error instead of fallback to command_id
                self.logger.error("unified_trading_controller.no_session_id_in_result", {
                    "result_keys": list(result.keys()) if result else [],
                    "result": result,
                    "symbols": symbols,
                    "duration": duration
                })
                raise RuntimeError(
                    f"Session creation failed: No session_id returned. "
                    f"Result keys: {list(result.keys()) if result else 'None'}. "
                    f"This indicates a critical issue in ExecutionController."
                )

            self.logger.info("unified_trading_controller.data_collection_started", {
                "session_id": session_id,
                "symbols": symbols,
                "duration": duration
            })

            return session_id

        except TimeoutError as e:
            # ✅ SESSION-005: Timeout is a real error - don't fallback
            self.logger.error("unified_trading_controller.session_creation_timeout", {
                "error": str(e),
                "timeout_seconds": 15.0,
                "symbols": symbols,
                "duration": duration,
                "action": "Check QuestDB connectivity and ExecutionController health"
            })
            raise RuntimeError(
                f"Session creation timed out after 15 seconds. "
                f"This may indicate QuestDB connectivity issues or ExecutionController deadlock. "
                f"Symbols: {symbols}, Duration: {duration}"
            ) from e

        except Exception as e:
            # ✅ SESSION-005: Any error is critical - propagate with context
            self.logger.error("unified_trading_controller.session_creation_failed", {
                "error": str(e),
                "error_type": type(e).__name__,
                "symbols": symbols,
                "duration": duration
            })
            raise RuntimeError(
                f"Session creation failed: {str(e)}. "
                f"Symbols: {symbols}, Duration: {duration}"
            ) from e
    
    async def stop_execution(self, force: bool = False) -> str:
        """Stop current execution"""

        parameters = {"force": force}

        command_id = await self.command_processor.execute_command(
            CommandType.STOP_EXECUTION,
            parameters
        )

        # ✅ REMOVED: Progress task cleanup (ExecutionController handles lifecycle)

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

    # ✅ REMOVED: Duplicate progress update methods (_send_progress_update, _progress_update_loop, stop_data_collection_progress)
    # These methods were creating duplicate progress updates alongside ExecutionController's own progress tracking.
    # This caused:
    # 1. Duplicate EventBus publishes (2 sources publishing same events)
    # 2. Excessive logging (10+ progress logs per second)
    # 3. Unnecessary WebSocket traffic
    # 4. Complex state management (two parallel progress tracking systems)
    #
    # ExecutionController now has built-in throttled progress updates (5s interval) that handle:
    # - Progress calculation based on actual data collection metrics
    # - Time-based ETA estimation
    # - EventBus publishing with rate limiting
    # - WebSocket broadcasting via ExecutionProcessor/EventBridge
    #
    # Migration impact: NONE - ExecutionController provides same functionality with better performance