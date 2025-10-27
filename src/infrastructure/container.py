"""
Dependency Injection Container - Composition Root Pattern
========================================================
Pure dependency injection container following Clean Architecture principles.
Container is created once in main.py and assembles all objects from Settings.

CRITICAL RULES:
- NO global access (no get_container() function)
- NO business logic (only object assembly)
- NO conditional logic (decisions made in Settings)
- Constructor injection only
- Created once at application startup
"""

from typing import Optional, List, Any, Dict, Set
import asyncio
import threading
from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from ..core.simple_shutdown import SimpleShutdown
from ..infrastructure.config.settings import AppSettings
from ..domain.services.pump_detector import PumpDetectionService
from ..domain.services.risk_assessment import RiskAssessmentService
from ..domain.services.strategy_manager import StrategyManager
from ..domain.services.order_manager import OrderManager
from ..domain.services.risk_manager import RiskManager
from ..application.use_cases.detect_pump_signals import DetectPumpSignalsUseCase
from ..domain.interfaces.market_data import IMarketDataProvider
from ..domain.interfaces.trading import IOrderExecutor
from ..domain.interfaces.notifications import INotificationService
from ..infrastructure.factories.market_data_factory import MarketDataProviderFactory
from ..infrastructure.factories.trade_executor_factory import TradeExecutorFactory
from ..infrastructure.factories.notification_factory import NotificationServiceFactory
from ..infrastructure.factories.pump_detection_factory import PumpDetectionServiceFactory
from ..infrastructure.factories.risk_assessment_factory import RiskAssessmentServiceFactory
from ..infrastructure.factories.position_management_factory import PositionManagementServiceFactory
from ..infrastructure.factories.symbol_config_factory import SymbolConfigurationFactory
from ..infrastructure.config.symbol_config import SymbolConfigurationManager
from ..application.orchestrators.trading_orchestrator import TradingOrchestrator
from ..application.services.position_management_service import PositionManagementService
from ..application.controllers.unified_trading_controller import UnifiedTradingController
from ..infrastructure.adapters.mexc_adapter import MexcRealAdapter
from ..infrastructure.adapters.mexc_paper_adapter import MexcPaperAdapter
from ..api.broadcast_provider import BroadcastProvider
from ..api.event_bridge import EventBridge
from ..api.execution_processor import ExecutionProcessor
from ..data.live_market_adapter import LiveMarketAdapter
from ..trading.session_manager import SessionManager
from ..monitoring.metrics_exporter import MetricsExporter


class Container:
    """
    Pure Dependency Injection Container - Composition Root Pattern
    
    This container:
    - Is created ONCE in main.py with all dependencies
    - Only assembles objects from Settings (no business logic)
    - Uses constructor injection exclusively
    - Has NO global access methods
    - Contains NO conditional logic
    - Provides proper lifecycle management and resource cleanup
    """
    
    def __init__(self, settings: AppSettings, event_bus: EventBus, logger: StructuredLogger):
        """
        Initialize container with core dependencies.
        
        Args:
            settings: Application settings (single source of truth)
            event_bus: Central communication hub
            logger: Structured logger instance
        """
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
        self.shutdown_manager = SimpleShutdown("Container")
        
        # Service tracking with strong references to prevent premature GC
        self._created_services: Set = set()
        
        # Singleton instances to prevent creating multiple instances
        self._singleton_services: Dict[str, Any] = {}
        self._singleton_creations: Dict[str, asyncio.Task] = {}
        
        # Lifecycle state tracking
        self._started_services: Set[str] = set()
        self._is_shutting_down = False
        
        # Async-safe singleton management
        self._singleton_lock = asyncio.Lock()

        # Validate configuration early
        validation = self.validate_configuration()
        if not validation["valid"]:
            raise RuntimeError(f"Configuration validation failed: {validation['errors']}")

        self.logger.info("container.init_completed", {
            "eventbus_healthy": event_bus is not None,
            "eventbus_running": getattr(event_bus, '_is_processing', False)
        })

    async def _get_or_create_singleton_async(self, service_name: str, factory_func) -> Any:
        """
        Async-safe singleton creation with double-checked locking pattern.
        Supports both synchronous and asynchronous factory functions.
        For async factories, ensures full initialization before returning.

        Args:
            service_name: Unique service identifier
            factory_func: Function to create the service instance (sync or async)

        Returns:
            Fully initialized service instance
        """
        import inspect

        if not service_name or not service_name.strip():
            raise ValueError(f"Service name cannot be empty or whitespace")

        existing_service = self._singleton_services.get(service_name)
        if existing_service is not None:
            return existing_service

        async with self._singleton_lock:
            existing_service = self._singleton_services.get(service_name)
            if existing_service is not None:
                return existing_service

            pending_task = self._singleton_creations.get(service_name)
            if pending_task is not None:
                task = pending_task
            else:
                self.logger.debug("container.service_creation_started", {
                    "service": service_name,
                    "factory_type": "async" if inspect.iscoroutinefunction(factory_func) else "sync"
                })

                if inspect.iscoroutinefunction(factory_func):
                    task = asyncio.create_task(factory_func())
                    self._singleton_creations[service_name] = task
                else:
                    try:
                        service = factory_func()
                        if service is None:
                            raise RuntimeError(f"Factory returned None for service: {service_name}")
                        self._singleton_services[service_name] = service
                        self._created_services.add(service)
                        self.logger.info("container.service_created", {
                            "service": service_name,
                            "type": service.__class__.__name__,
                            "fully_initialized": True
                        })
                        return service
                    except Exception as e:
                        self.logger.error("container.service_creation_failed", {
                            "service": service_name,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })
                        raise RuntimeError(f"Failed to create service '{service_name}': {str(e)}") from e

        if 'task' not in locals():
            raise RuntimeError(f"No factory task created for service {service_name}")

        try:
            service = await task
            if service is None:
                raise RuntimeError(f"Factory returned None for service: {service_name}")

            async with self._singleton_lock:
                self._singleton_services[service_name] = service
                self._created_services.add(service)
                self._singleton_creations.pop(service_name, None)

            self.logger.info("container.service_created", {
                "service": service_name,
                "type": service.__class__.__name__,
                "fully_initialized": True
            })

            return service

        except Exception as e:
            async with self._singleton_lock:
                self._singleton_creations.pop(service_name, None)
            self.logger.error("container.service_creation_failed", {
                "service": service_name,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise RuntimeError(f"Failed to create service '{service_name}': {str(e)}") from e

    async def create_market_data_provider(self, override_mode=None) -> IMarketDataProvider:
        """
        Create market data provider using factory pattern.
        NO conditional logic - decision delegated to factory.
        Uses singleton pattern to prevent multiple instances.

        Args:
            override_mode: Override the default trading mode

        Returns:
            Configured market data provider

        Raises:
            RuntimeError: If market data provider creation fails
        """
        def _create():
            try:
                factory = MarketDataProviderFactory(
                    settings=self.settings,
                    event_bus=self.event_bus,
                    logger=self.logger
                )
                return factory.create(override_mode=override_mode)
            except Exception as e:
                self.logger.error("container.market_data_provider_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create market data provider: {str(e)}") from e

        # Use different singleton key for different override modes
        singleton_key = f"market_data_provider_{override_mode}" if override_mode else "market_data_provider"
        return await self._get_or_create_singleton_async(singleton_key, _create)
    
    async def create_trade_executor(self) -> IOrderExecutor:
        """
        Create trade executor using factory pattern.
        NO conditional logic - decision delegated to factory.
        Uses singleton pattern to prevent multiple instances.
        
        Returns:
            Configured trade executor
            
        Raises:
            RuntimeError: If trade executor creation fails
        """
        def _create():
            try:
                factory = TradeExecutorFactory(
                    settings=self.settings,
                    event_bus=self.event_bus,
                    logger=self.logger
                )
                return factory.create()
            except Exception as e:
                self.logger.error("container.trade_executor_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create trade executor: {str(e)}") from e
        
        return await self._get_or_create_singleton_async("trade_executor", _create)
    
    def create_notification_service(self) -> Optional[INotificationService]:
        """
        Create notification service using factory pattern.
        NO conditional logic - decision delegated to factory.
        
        Returns:
            Configured notification service or None
            
        Raises:
            RuntimeError: If notification service creation fails
        """
        def _create():
            try:
                factory = NotificationServiceFactory(
                    settings=self.settings,
                    event_bus=self.event_bus,
                    logger=self.logger
                )
                return factory.create()  # Can return None for optional service
            except Exception as e:
                self.logger.error("container.notification_service_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                self.logger.warning("container.notification_service_disabled", {
                    "reason": "creation_failed"
                })
                return None  # Optional service - return None on failure
        
        # Optional services are not singletonized to allow None returns
        service = _create()
        if service:
            self._created_services.add(service)
        return service
    
    async def create_symbol_config_manager(self) -> SymbolConfigurationManager:
        """
        Create symbol configuration manager using factory pattern.
        NO conditional logic - decision delegated to factory.
        Uses singleton pattern to prevent multiple instances.
        
        Returns:
            Configured symbol configuration manager
            
        Raises:
            RuntimeError: If symbol configuration manager creation fails
        """
        def _create():
            try:
                factory = SymbolConfigurationFactory()
                return factory.create(self.settings, self.logger)
            except Exception as e:
                self.logger.error("container.symbol_config_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create symbol configuration manager: {str(e)}") from e
        
        return await self._get_or_create_singleton_async("symbol_config_manager", _create)
    
    async def create_pump_detection_service(self) -> PumpDetectionService:
        """
        Create pump detection service from Settings.
        Uses singleton pattern to prevent multiple instances.
        
        Returns:
            Configured pump detection service
            
        Raises:
            RuntimeError: If pump detection service creation fails
        """
        def _create():
            try:
                return PumpDetectionServiceFactory.create(self.settings, self.logger)
            except Exception as e:
                self.logger.error("container.pump_detection_service_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create pump detection service: {str(e)}") from e
        
        return await self._get_or_create_singleton_async("pump_detection_service", _create)
    
    async def create_risk_assessment_service(self) -> RiskAssessmentService:
        """
        Create risk assessment service from Settings.
        Uses singleton pattern to prevent multiple instances.
        
        Returns:
            Configured risk assessment service
            
        Raises:
            RuntimeError: If risk assessment service creation fails
        """
        def _create():
            try:
                return RiskAssessmentServiceFactory.create(self.settings)
            except Exception as e:
                self.logger.error("container.risk_assessment_service_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create risk assessment service: {str(e)}") from e
        
        return await self._get_or_create_singleton_async("risk_assessment_service", _create)
    
    def create_pump_detection_use_case(self,
                                     pump_detection_service: PumpDetectionService,
                                     risk_assessment_service: RiskAssessmentService,
                                     notification_service: Optional[INotificationService]) -> DetectPumpSignalsUseCase:
        """
        Create pump detection use case with explicit dependencies.
        
        Args:
            pump_detection_service: Configured pump detection service
            risk_assessment_service: Configured risk assessment service
            notification_service: Configured notification service
            
        Returns:
            Configured pump detection use case
        """
        service = DetectPumpSignalsUseCase(
            pump_detection_service=pump_detection_service,
            risk_assessment_service=risk_assessment_service,
            event_bus=self.event_bus,
            notification_service=notification_service,
            logger=self.logger
        )
        self._created_services.add(service)
        return service

    async def create_position_management_service(self) -> PositionManagementService:
        """
        Create position management service using factory pattern.
        Uses singleton pattern to prevent multiple instances.
        
        Returns:
            Configured position management service
            
        Raises:
            RuntimeError: If position management service creation fails
        """
        def _create():
            try:
                factory = PositionManagementServiceFactory()
                return factory.create(self.settings, self.event_bus, self.logger)
            except Exception as e:
                self.logger.error("container.position_management_service_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create position management service: {str(e)}") from e
        
        return await self._get_or_create_singleton_async("position_management_service", _create)
    
    async def create_order_manager(self) -> OrderManager:
        """
        Create order manager for mock trading simulation.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured order manager
        """
        def _create():
            try:
                return OrderManager(logger=self.logger)
            except Exception as e:
                self.logger.error("container.order_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create order manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("order_manager", _create)

    async def create_risk_manager(self) -> RiskManager:
        """
        Create risk manager for budget and risk management.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured risk manager
        """
        def _create():
            try:
                # Use default budget of $10,000 for simulation
                return RiskManager(logger=self.logger, total_budget=10000.0)
            except Exception as e:
                self.logger.error("container.risk_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create risk manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("risk_manager", _create)

    async def create_strategy_manager(self) -> StrategyManager:
        """
        Create strategy manager with 5-group condition architecture.
        Uses two-phase initialization with validation to prevent deadlocks.

        Returns:
            Configured strategy manager
        """
        def _create_instance_only():
            """Synchronous factory - creates instance without async dependencies"""
            try:
                # Create instance without dependencies - will be set during async initialization
                return StrategyManager(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    order_manager=None,  # Will be set during async initialization
                    risk_manager=None    # Will be set during async initialization
                )
            except Exception as e:
                self.logger.error("container.strategy_manager_instance_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create strategy manager instance: {str(e)}") from e

        # Phase 1: Get or create instance (synchronous, inside lock)
        strategy_manager = await self._get_or_create_singleton_async("strategy_manager", _create_instance_only)

        # Phase 2: Initialize asynchronously (outside lock, safe from deadlocks)
        if not hasattr(strategy_manager, '_is_initialized') or not strategy_manager._is_initialized:
            try:
                self.logger.debug("container.strategy_manager_initialization_started")

                # Create dependencies asynchronously
                order_manager = await self.create_order_manager()
                risk_manager = await self.create_risk_manager()

                # Set dependencies on strategy manager
                strategy_manager.order_manager = order_manager
                strategy_manager.risk_manager = risk_manager

                # Mark as initialized
                strategy_manager._is_initialized = True

                self.logger.info("container.strategy_manager_fully_initialized", {
                    "has_order_manager": order_manager is not None,
                    "has_risk_manager": risk_manager is not None
                })

            except Exception as e:
                self.logger.error("container.strategy_manager_initialization_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to initialize strategy manager: {str(e)}") from e

        return strategy_manager

    async def create_mexc_adapter(self):
        """
        Create MEXC adapter with real API credentials.
        Only supports real mode - no mock or virtual implementations.

        Returns:
            Configured MEXC real adapter

        Raises:
            RuntimeError: If MEXC API credentials are not configured
        """
        def _create():
            try:
                # Get API credentials from settings
                api_key = self.settings.exchanges.mexc_api_key
                api_secret = self.settings.exchanges.mexc_api_secret

                if not api_key or not api_secret or api_key == "" or api_secret == "":
                    self.logger.info("container.using_paper_adapter", {
                        "reason": "credentials_not_configured"
                    })
                    return MexcPaperAdapter(logger=self.logger)

                self.logger.info("container.creating_real_mexc_adapter")
                return MexcRealAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    logger=self.logger,
                    base_url="https://api.mexc.com"
                )

            except Exception as e:
                self.logger.error("container.mexc_adapter_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create MEXC adapter: {str(e)}") from e

        return await self._get_or_create_singleton_async("mexc_adapter", _create)

    async def create_wallet_service(self):
        """
        Create wallet service using MEXC adapter.
        Uses two-phase initialization with validation to prevent deadlocks.

        Returns:
            Configured wallet service
        """
        def _create_instance_only():
            """Synchronous factory - creates instance without async dependencies"""
            try:
                from ..application.services.wallet_service import WalletService

                # Create instance without adapter - will be set during async initialization
                return WalletService(adapter=None)
            except Exception as e:
                self.logger.error("container.wallet_service_instance_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create wallet service instance: {str(e)}") from e

        # Phase 1: Get or create instance (synchronous, inside lock)
        wallet_service = await self._get_or_create_singleton_async("wallet_service", _create_instance_only)

        # Phase 2: Initialize asynchronously (outside lock, safe from deadlocks)
        if not hasattr(wallet_service, '_is_initialized') or not wallet_service._is_initialized:
            try:
                self.logger.debug("container.wallet_service_initialization_started")

                # Create adapter asynchronously with timeout
                adapter = await asyncio.wait_for(
                    self.create_mexc_adapter(),
                    timeout=10.0  # 10 seconds for adapter initialization
                )

                # Set adapter on wallet service
                wallet_service._adapter = adapter

                # Mark as initialized
                wallet_service._is_initialized = True

                # Validate dependencies
                wallet_service.validate_dependencies()

                self.logger.info("container.wallet_service_fully_initialized", {
                    "adapter_type": type(adapter).__name__
                })

            except asyncio.TimeoutError:
                self.logger.error("container.wallet_service_initialization_timeout")
                raise RuntimeError("Wallet service initialization timeout")
            except Exception as e:
                self.logger.error("container.wallet_service_initialization_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to initialize wallet service: {str(e)}") from e

        return wallet_service

    async def create_data_collection_controller(self):
        """
        Create lightweight data collection controller.
        Only creates necessary components for data collection mode.

        Returns:
            Configured data collection controller
        """
        def _create():
            try:
                from ..application.controllers.execution_controller import ExecutionController

                # Create market data provider factory
                market_data_factory = MarketDataProviderFactory(
                    settings=self.settings,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                # Create data collection persistence service (REQUIRED for data collection)
                try:
                    from ..data.data_collection_persistence_service import DataCollectionPersistenceService
                    from ..data_feed.questdb_provider import QuestDBProvider

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

                    self.logger.info("container.db_persistence_enabled", {
                        "provider": "QuestDB"
                    })
                except Exception as e:
                    # QuestDB is REQUIRED - fail fast with clear error message
                    error_msg = (
                        f"Failed to initialize QuestDB persistence service: {str(e)}\n"
                        f"QuestDB is REQUIRED for data collection.\n"
                        f"Please ensure:\n"
                        f"  1. QuestDB is running (check http://127.0.0.1:9000)\n"
                        f"  2. Migration completed (run: python database/questdb/install_questdb.py)\n"
                        f"  3. Required packages installed (asyncpg, questdb, psycopg2-binary)"
                    )
                    self.logger.error("container.db_persistence_required", {
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    raise RuntimeError(error_msg) from e

                # Create execution controller with factory and persistence
                controller = ExecutionController(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    market_data_provider_factory=market_data_factory,
                    db_persistence_service=db_persistence_service
                )

                self.logger.info("container.data_collection_controller_created", {
                    "factory_type": type(market_data_factory).__name__,
                    "db_persistence": db_persistence_service is not None
                })

                return controller
            except Exception as e:
                self.logger.error("container.data_collection_controller_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create data collection controller: {str(e)}") from e

        return await self._get_or_create_singleton_async("data_collection_controller", _create)

    async def create_unified_trading_controller(self, data_path: str = "data", mode: str = "auto"):
        """
        Create unified trading controller with all execution components.
        Uses two-phase initialization with validation to prevent deadlocks.

        Args:
            data_path: Path to historical data directory
            mode: "auto", "real", "mock", "virtual" for wallet adapter

        Returns:
            Configured unified trading controller
        """
        def _create_instance_only():
            """Synchronous factory - creates instance without initialization"""
            try:
                from ..application.controllers.unified_trading_controller import UnifiedTradingController

                # Create wallet service and order manager based on mode
                # Note: These are created synchronously here, but their dependencies may be async
                # This is acceptable as long as the factory itself doesn't await
                wallet_service = None  # Will be set during async initialization
                order_manager = None   # Will be set during async initialization

                controller = UnifiedTradingController(
                    market_data_provider=None,  # Will be set during async initialization
                    event_bus=self.event_bus,
                    logger=self.logger,
                    data_path=data_path,
                    wallet_service=wallet_service,
                    order_manager=order_manager
                )

                return controller
            except Exception as e:
                self.logger.error("container.unified_trading_controller_instance_creation_failed", {
                    "error": str(e),
                    "mode": mode,
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create unified trading controller instance: {str(e)}") from e

        # Phase 1: Get or create instance (synchronous, inside lock)
        controller = await self._get_or_create_singleton_async(f"unified_trading_controller_{mode}", _create_instance_only)

        # Phase 2: Initialize asynchronously (outside lock, safe from deadlocks)
        if not controller._is_initialized:
            try:
                self.logger.debug("container.unified_trading_controller_initialization_started", {"mode": mode})

                # Create dependencies asynchronously
                wallet_service = await self.create_wallet_service()
                order_manager = await self.create_order_manager()
                market_data_provider = await self.create_market_data_provider()

                # Set dependencies on controller
                controller.wallet_service = wallet_service
                controller.order_manager = order_manager
                controller.market_data_provider = market_data_provider

                # Initialize the controller asynchronously
                await controller.initialize()

                self.logger.info("container.unified_trading_controller_fully_initialized", {
                    "mode": mode,
                    "has_wallet": wallet_service is not None,
                    "has_order_manager": order_manager is not None
                })

            except Exception as e:
                self.logger.error("container.unified_trading_controller_initialization_failed", {
                    "error": str(e),
                    "mode": mode,
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to initialize unified trading controller: {str(e)}") from e

        return controller

    async def create_websocket_server(self):
        """
        Create WebSocket server for real-time communication.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured WebSocket server
        """
        def _create():
            try:
                from ..api.websocket_server import WebSocketAPIServer

                server = WebSocketAPIServer(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    settings=self.settings
                )
                return server
            except Exception as e:
                self.logger.error("container.websocket_server_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create WebSocket server: {str(e)}") from e

        return await self._get_or_create_singleton_async("websocket_server", _create)

    async def create_broadcast_provider(self):
        """
        Create centralized broadcast provider for WebSocket messages.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured broadcast provider
        """
        async def _create():
            try:
                websocket_server = await self.create_websocket_server()
                provider = BroadcastProvider(
                    event_bus=self.event_bus,
                    websocket_server=websocket_server,
                    logger=self.logger,
                    max_queue_size=getattr(self.settings.websocket, 'max_broadcast_queue_size', 10000),
                    max_batch_size=getattr(self.settings.websocket, 'max_batch_size', 50),
                    latency_threshold_ms=getattr(self.settings.performance_monitoring, 'latency_threshold_ms', 100)
                )
                return provider
            except Exception as e:
                self.logger.error("container.broadcast_provider_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create broadcast provider: {str(e)}") from e

        return await self._get_or_create_singleton_async("broadcast_provider", _create)

    async def create_event_bridge(self):
        """
        Create event bridge for WebSocket communication.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured event bridge
        """
        async def _create():
            try:
                from ..api.subscription_manager import SubscriptionManager

                websocket_server = await self.create_websocket_server()
                broadcast_provider = await self.create_broadcast_provider()
                subscription_manager = SubscriptionManager(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                bridge = EventBridge(
                    event_bus=self.event_bus,
                    broadcast_provider=broadcast_provider,
                    subscription_manager=subscription_manager,
                    logger=self.logger,
                    settings=self.settings
                )

                # Wire execution processor
                execution_processor = await self.create_execution_processor()
                bridge.set_execution_processor(execution_processor)

                return bridge
            except Exception as e:
                self.logger.error("container.event_bridge_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create event bridge: {str(e)}") from e

        return await self._get_or_create_singleton_async("event_bridge", _create)

    async def create_execution_processor(self):
        """
        Create execution processor for progress tracking.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured execution processor
        """
        async def _create():
            try:
                broadcast_provider = await self.create_broadcast_provider()

                processor = ExecutionProcessor(
                    event_bus=self.event_bus,
                    broadcast_provider=broadcast_provider,
                    logger=self.logger,
                    settings=self.settings
                )
                return processor
            except Exception as e:
                self.logger.error("container.execution_processor_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create execution processor: {str(e)}") from e

        return await self._get_or_create_singleton_async("execution_processor", _create)

    async def create_live_market_adapter(self) -> LiveMarketAdapter:
        """
        Create live market adapter with session manager integration.
        Handles circular dependency by deferring session manager assignment.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured live market adapter
        """
        def _create():
            try:
                from ..data.live_market_adapter import LiveMarketAdapter

                # Create adapter with None session_manager initially
                adapter = LiveMarketAdapter(
                    settings=self.settings.exchanges,
                    event_bus=self.event_bus,
                    logger=self.logger,
                    session_manager=None  # Will be set later
                )
                return adapter
            except Exception as e:
                self.logger.error("container.live_market_adapter_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create live market adapter: {str(e)}") from e

        return await self._get_or_create_singleton_async("live_market_adapter", _create)

    async def create_session_manager(self) -> SessionManager:
        """
        Create session manager with market adapter integration.
        Sets session manager reference on live market adapter after creation.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured session manager
        """
        async def _create():
            try:
                from ..trading.session_manager import SessionManager

                market_adapter = await self.create_live_market_adapter()

                manager = SessionManager(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    market_adapter=market_adapter
                )
                market_adapter.session_manager = manager

                return manager
            except Exception as e:
                self.logger.error("container.session_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create session manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("session_manager", _create)

    async def create_metrics_exporter(self) -> MetricsExporter:
        """
        Create metrics exporter with optional component integrations.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured metrics exporter
        """
        async def _create():
            try:
                from ..monitoring.metrics_exporter import MetricsExporter

                market_adapter = await self.create_live_market_adapter()
                session_manager = await self.create_session_manager()
                exporter = MetricsExporter(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    market_adapter=market_adapter,
                    session_manager=session_manager
                )
                return exporter
            except Exception as e:
                self.logger.error("container.metrics_exporter_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create metrics exporter: {str(e)}") from e

        return await self._get_or_create_singleton_async("metrics_exporter", _create)

    async def create_strategy_blueprints_api(self):
        """
        Create strategy blueprints API for visual strategy builder.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured strategy blueprints API
        """
        async def _create():
            try:
                from ..api.strategy_blueprints import StrategyBlueprintsAPI

                websocket_server = await self.create_websocket_server()
                jwt_secret = getattr(self.settings, 'jwt_secret', None) or getattr(
                    websocket_server,
                    'jwt_secret',
                    'dev_jwt_secret_key'
                )

                api = StrategyBlueprintsAPI(
                    logger=self.logger,
                    jwt_secret=jwt_secret
                )
                return api
            except Exception as e:
                self.logger.error("container.strategy_blueprints_api_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create strategy blueprints API: {str(e)}") from e

        return await self._get_or_create_singleton_async("strategy_blueprints_api", _create)

    async def create_ops_api(self):
        """
        Create operations API for dashboard and risk controls.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured operations API
        """
        async def _create():
            try:
                from ..api.ops.ops_routes import OpsAPI

                market_adapter = await self.create_live_market_adapter() # SessionManager is created by this
                session_manager = market_adapter.session_manager
                metrics_exporter = await self.create_metrics_exporter()

                # Get JWT secret from settings or websocket server
                websocket_server = await self.create_websocket_server()
                jwt_secret = getattr(self.settings, 'jwt_secret', None) or getattr(
                    websocket_server,
                    'jwt_secret',
                    'dev_jwt_secret_key'
                )

                api = OpsAPI(
                    market_adapter=market_adapter,
                    session_manager=session_manager,
                    metrics_exporter=metrics_exporter,
                    logger=self.logger,
                    jwt_secret=jwt_secret
                )
                return api
            except Exception as e:
                self.logger.error("container.ops_api_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create operations API: {str(e)}") from e

        return await self._get_or_create_singleton_async("ops_api", _create)

    async def create_paper_trading_engine(self):
        """
        Create paper trading engine for virtual strategy execution.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured paper trading engine
        """
        async def _create():
            try:
                from ..trading.paper_trading_engine import PaperTradingEngine

                order_manager = await self.create_order_manager()
                risk_manager = await self.create_risk_manager()

                engine = PaperTradingEngine(
                    order_manager=order_manager,
                    risk_manager=risk_manager,
                    logger=self.logger
                )
                return engine
            except Exception as e:
                self.logger.error("container.paper_trading_engine_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create paper trading engine: {str(e)}") from e

        return await self._get_or_create_singleton_async("paper_trading_engine", _create)

    async def create_performance_tracker(self):
        """
        Create performance tracker for paper trading analytics.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured performance tracker
        """
        def _create():
            try:
                from ..trading.performance_tracker import PerformanceTracker

                tracker = PerformanceTracker(
                    logger=self.logger,
                    initial_balance=10000.0
                )
                return tracker
            except Exception as e:
                self.logger.error("container.performance_tracker_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create performance tracker: {str(e)}") from e

        return await self._get_or_create_singleton_async("performance_tracker", _create)

    async def create_signal_adapter(self):
        """
        Create signal adapter for strategy signal processing.
        Uses singleton pattern to prevent multiple instances.

        Returns:
            Configured signal adapter
        """
        async def _create():
            try:
                from ..trading.signal_adapter import SignalAdapter, SignalFilterConfig, SignalFilter

                paper_trading_engine = await self.create_paper_trading_engine()

                # Default filter config - only high confidence signals
                filter_config = SignalFilterConfig(
                    filter_type=SignalFilter.HIGH_CONFIDENCE,
                    min_confidence=0.5
                )

                adapter = SignalAdapter(
                    event_bus=self.event_bus,
                    paper_trading_engine=paper_trading_engine,
                    logger=self.logger,
                    filter_config=filter_config
                )
                return adapter
            except Exception as e:
                self.logger.error("container.signal_adapter_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create signal adapter: {str(e)}") from e

        return await self._get_or_create_singleton_async("signal_adapter", _create)

    async def create_trading_orchestrator(self, symbols: list = None, override_mode=None):
        """
        Create complete trading orchestrator with all dependencies injected.
        Uses singleton pattern to ensure consistent service instances.

        Args:
            symbols: List of symbols to trade (from command line args)
            override_mode: Override the default trading mode

        Returns:
            Configured trading orchestrator
        """
        async def _create():
            # Use singleton services to ensure consistency
            pump_detection_service = await self.create_pump_detection_service()
            risk_assessment_service = await self.create_risk_assessment_service()
            notification_service = self.create_notification_service()
            position_management_service = await self.create_position_management_service()

            orchestrator = TradingOrchestrator(
                market_data_provider=await self.create_market_data_provider(override_mode=override_mode),
                trade_executor=await self.create_trade_executor(),
                pump_detection_use_case=self.create_pump_detection_use_case(
                    pump_detection_service=pump_detection_service,
                    risk_assessment_service=risk_assessment_service,
                    notification_service=notification_service
                ),
                position_management_service=position_management_service,
                notification_service=notification_service,
                event_bus=self.event_bus,
                logger=self.logger,
                symbols=symbols or self.settings.trading.default_symbols
            )
            return orchestrator

        # Use singleton key based on parameters
        symbols_key = "_".join(symbols) if symbols else "default"
        singleton_key = f"trading_orchestrator_{override_mode}_{symbols_key}"
        return await self._get_or_create_singleton_async(singleton_key, _create)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate required configuration settings before service creation.
        Helps catch configuration issues early in the startup process.
        
        Returns:
            Dictionary with validation results and any issues found
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "checked_settings": []
        }
        
        try:
            # Validate trading configuration
            if not self.settings.trading.default_symbols:
                validation_result["warnings"].append("No default trading symbols configured")
            
            if self.settings.trading.mode not in ["live", "backtest", "collect"]:
                validation_result["errors"].append(f"Invalid trading mode: {self.settings.trading.mode}")
                validation_result["valid"] = False
            
            validation_result["checked_settings"].append("trading")
            
            # Validate exchange configuration
            if not any([self.settings.exchanges.mexc_enabled, self.settings.exchanges.bybit_enabled]):
                validation_result["errors"].append("No exchanges enabled")
                validation_result["valid"] = False
            
            validation_result["checked_settings"].append("exchanges")
            
            # Validate logging configuration
            if not self.settings.logging.log_dir:
                validation_result["warnings"].append("Log directory not specified, using default")
            
            validation_result["checked_settings"].append("logging")
            
            # Validate detection thresholds
            if self.settings.flash_pump_detection.min_pump_magnitude <= 0:
                validation_result["errors"].append("Pump detection magnitude must be positive")
                validation_result["valid"] = False
            
            if self.settings.position_sizing.max_position_size_usdt <= 0:
                validation_result["errors"].append("Maximum position size must be positive")
                validation_result["valid"] = False
            
            validation_result["checked_settings"].append("detection_parameters")
            
        except Exception as e:
            validation_result["errors"].append(f"Configuration validation error: {str(e)}")
            validation_result["valid"] = False
        
        # Log validation results
        if validation_result["valid"]:
            if validation_result["warnings"]:
                self.logger.warning("container.configuration_validation_warnings", {
                    "warnings": validation_result["warnings"]
                })
            else:
                self.logger.info("container.configuration_validation_passed")
        else:
            self.logger.error("container.configuration_validation_failed", {
                "errors": validation_result["errors"]
            })
        
        return validation_result
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all created services.
        Checks if services are responsive and in a healthy state.
        
        Returns:
            Dictionary with health status of all services
        """
        health_status = {
            "overall_healthy": True,
            "services": {},
            "total_services": len(self._created_services),
            "healthy_services": 0,
            "unhealthy_services": 0
        }
        
        for service in list(self._created_services):
            service_name = service.__class__.__name__
            try:
                # Check if service has a health_check method
                if hasattr(service, 'health_check'):
                    service_health = await service.health_check()
                    health_status["services"][service_name] = service_health
                    if service_health.get("healthy", False):
                        health_status["healthy_services"] += 1
                    else:
                        health_status["unhealthy_services"] += 1
                        health_status["overall_healthy"] = False
                else:
                    # Basic check - service exists and is accessible
                    health_status["services"][service_name] = {
                        "healthy": True,
                        "status": "no_health_check_method",
                        "message": "Service exists but has no health check method"
                    }
                    health_status["healthy_services"] += 1
                    
            except Exception as e:
                health_status["services"][service_name] = {
                    "healthy": False,
                    "status": "error",
                    "error": str(e)
                }
                health_status["unhealthy_services"] += 1
                health_status["overall_healthy"] = False
        
        self.logger.info("container.health_check_completed", {
            "overall_healthy": health_status["overall_healthy"],
            "total_services": health_status["total_services"],
            "healthy_services": health_status["healthy_services"],
            "unhealthy_services": health_status["unhealthy_services"]
        })
        
        return health_status
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current status of all created services.
        Provides overview of container state without performing health checks.
        
        Returns:
            Dictionary with service status information
        """
        return {
            "total_services": len(self._created_services),
            "singleton_services": len(self._singleton_services),
            "started_services": len(self._started_services),
            "is_shutting_down": self._is_shutting_down,
            "created_service_types": [
                service.__class__.__name__ 
                for service in self._created_services
            ],
            "singleton_service_names": list(self._singleton_services.keys())
        }
    
    async def shutdown(self):
        """
        Clean shutdown of all created services.
        Collects all errors and reports them properly.
        Prevents shutdown loops and ensures cleanup completion.
        """
        if self._is_shutting_down:
            self.logger.warning("container.shutdown_already_in_progress")
            return
        
        self._is_shutting_down = True
        
        self.logger.info("container.shutdown_started", {
            "services_count": len(self._created_services)
        })
        
        shutdown_errors = []
        
        # Shutdown services - try shutdown, stop, or close methods
        for service in list(self._created_services):  # Convert to list to avoid iteration issues
            shutdown_method = None
            if hasattr(service, 'shutdown'):
                shutdown_method = 'shutdown'
            elif hasattr(service, 'stop'):
                shutdown_method = 'stop'
            elif hasattr(service, 'close'):
                shutdown_method = 'close'

            if shutdown_method:
                try:
                    method = getattr(service, shutdown_method)
                    if asyncio.iscoroutinefunction(method):
                        await asyncio.wait_for(method(), timeout=5.0)
                    else:
                        # Run sync method in thread pool
                        await asyncio.get_event_loop().run_in_executor(None, method)
                    self.logger.debug("container.service_shutdown_success", {
                        "service": service.__class__.__name__,
                        "method": shutdown_method
                    })
                except Exception as e:
                    error_info = {
                        "service": service.__class__.__name__,
                        "method": shutdown_method,
                        "error": str(e)
                    }
                    shutdown_errors.append(error_info)
                    self.logger.error("container.service_shutdown_error", error_info)
        
        # Cleanup shutdown manager
        try:
            await self.shutdown_manager.cleanup()
        except Exception as e:
            shutdown_errors.append({
                "service": "SimpleShutdown",
                "error": str(e)
            })
            self.logger.error("container.shutdown_manager_error", {
                "error": str(e)
            })
        
        # Clear all references
        self._created_services.clear()
        self._singleton_services.clear()
        self._started_services.clear()
        
        # Report final status
        if shutdown_errors:
            self.logger.warning("container.shutdown_completed_with_errors", {
                "errors": shutdown_errors,
                "total_errors": len(shutdown_errors)
            })
        else:
            self.logger.info("container.shutdown_completed")
        
        self._is_shutting_down = False

    async def startup(self):
        """
        Start all created services in proper order.
        Ensures services are initialized before use.
        """
        if self._started_services:
            self.logger.warning("container.startup_already_called")
            return

        self.logger.info("container.startup_started", {
            "services_count": len(self._created_services)
        })

        startup_errors = []

        # Start services that have start method
        for service in list(self._created_services):
            if hasattr(service, 'start'):
                try:
                    method = getattr(service, 'start')
                    if asyncio.iscoroutinefunction(method):
                        await asyncio.wait_for(method(), timeout=10.0)
                    else:
                        # Run sync method in thread pool
                        await asyncio.get_event_loop().run_in_executor(None, method)
                    self._started_services.add(service.__class__.__name__)
                    self.logger.debug("container.service_startup_success", {
                        "service": service.__class__.__name__
                    })
                except Exception as e:
                    error_info = {
                        "service": service.__class__.__name__,
                        "error": str(e)
                    }
                    startup_errors.append(error_info)
                    self.logger.error("container.service_startup_error", error_info)

        # Report final status
        if startup_errors:
            self.logger.warning("container.startup_completed_with_errors", {
                "errors": startup_errors,
                "total_errors": len(startup_errors)
            })
        else:
            self.logger.info("container.startup_completed")


# NO GLOBAL ACCESS - Container is created only in main.py
# NO get_container() function - violates Composition Root pattern
# NO singleton pattern - Container is created once and passed down
