"""
Trading Module - Order, Position, Risk, Session Management
===========================================================

Container module for trading-related dependency injection.
Extracted from monolithic container.py for maintainability.

Responsibilities:
- Order management (live, paper, backtest)
- Position management and synchronization
- Risk management and assessment
- Session management
- Trading orchestration
- Wallet service
"""

from typing import Optional, TYPE_CHECKING
from .base import ContainerModule

if TYPE_CHECKING:
    from ..container import Container


class TradingModule(ContainerModule):
    """
    Trading domain container module.

    Factory methods for all trading-related services.
    """

    async def create_order_manager(self) -> 'OrderManager':
        """
        Create order manager for general order operations.

        Returns:
            Configured OrderManager singleton
        """
        async def _create():
            try:
                from ...domain.services.order_manager import OrderManager

                trade_executor = await self._parent.create_trade_executor()
                questdb_provider = await self._parent.create_questdb_provider()

                order_manager = OrderManager(
                    executor=trade_executor,
                    event_bus=self.event_bus,
                    persistence_service=questdb_provider,
                    logger=self.logger
                )

                self.logger.info("trading_module.order_manager_created")
                return order_manager

            except Exception as e:
                self.logger.error("trading_module.order_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create order manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("order_manager", _create)

    async def create_live_order_manager(self) -> 'LiveOrderManager':
        """
        Create live order manager for real trading.

        Returns:
            Configured LiveOrderManager singleton
        """
        async def _create():
            try:
                from ...domain.services.order_manager_live import LiveOrderManager

                mexc_adapter = await self._parent.create_mexc_futures_adapter()
                questdb = await self._parent.create_questdb_provider()
                risk_manager = await self.create_risk_manager()

                order_manager = LiveOrderManager(
                    exchange_adapter=mexc_adapter,
                    event_bus=self.event_bus,
                    persistence_service=questdb,
                    risk_manager=risk_manager,
                    logger=self.logger
                )

                self.logger.info("trading_module.live_order_manager_created")
                return order_manager

            except Exception as e:
                self.logger.error("trading_module.live_order_manager_creation_failed", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                raise RuntimeError(f"Failed to create live order manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("live_order_manager", _create)

    async def create_backtest_order_manager(
        self,
        session_id: str,
        initial_capital: float = 10000.0,
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0004
    ) -> 'BacktestOrderManager':
        """
        Create backtest order manager for strategy testing.

        Args:
            session_id: Unique session identifier
            initial_capital: Starting capital for backtest
            maker_fee: Maker fee rate
            taker_fee: Taker fee rate

        Returns:
            New BacktestOrderManager instance (not singleton - per session)
        """
        try:
            from ...domain.services.backtest_order_manager import BacktestOrderManager

            questdb = await self._parent.create_questdb_provider()

            order_manager = BacktestOrderManager(
                session_id=session_id,
                initial_capital=initial_capital,
                questdb_provider=questdb,
                maker_fee=maker_fee,
                taker_fee=taker_fee,
                event_bus=self.event_bus,
                logger=self.logger
            )

            self.logger.info("trading_module.backtest_order_manager_created", {
                "session_id": session_id,
                "initial_capital": initial_capital
            })
            return order_manager

        except Exception as e:
            self.logger.error("trading_module.backtest_order_manager_creation_failed", {
                "error": str(e),
                "session_id": session_id
            })
            raise RuntimeError(f"Failed to create backtest order manager: {str(e)}") from e

    async def create_risk_manager(self, initial_capital: float = 10000.0) -> 'RiskManager':
        """
        Create risk manager for trade validation and limits.

        Args:
            initial_capital: Starting capital for risk calculations

        Returns:
            Configured RiskManager singleton
        """
        async def _create():
            try:
                from ...domain.services.risk_manager import RiskManager

                risk_config = getattr(self.settings, 'risk', None)
                if risk_config is None:
                    risk_config = {
                        'max_position_size_pct': 0.1,
                        'max_daily_loss_pct': 0.05,
                        'max_drawdown_pct': 0.15
                    }

                risk_manager = RiskManager(
                    initial_capital=initial_capital,
                    config=risk_config,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.risk_manager_created", {
                    "initial_capital": initial_capital
                })
                return risk_manager

            except Exception as e:
                self.logger.error("trading_module.risk_manager_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create risk manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("risk_manager", _create)

    async def create_risk_assessment_service(self) -> 'RiskAssessmentService':
        """
        Create risk assessment service for evaluating trade risk.

        Returns:
            Configured RiskAssessmentService singleton
        """
        async def _create():
            try:
                from ...domain.services.risk_assessment import RiskAssessmentService

                service = RiskAssessmentService(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.risk_assessment_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.risk_assessment_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create risk assessment service: {str(e)}") from e

        return await self._get_or_create_singleton_async("risk_assessment_service", _create)

    async def create_position_management_service(self) -> 'PositionManagementService':
        """
        Create position management service.

        Returns:
            Configured PositionManagementService singleton
        """
        async def _create():
            try:
                from ...application.services.position_management_service import PositionManagementService

                questdb = await self._parent.create_questdb_provider()

                service = PositionManagementService(
                    questdb_provider=questdb,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.position_management_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.position_management_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create position management service: {str(e)}") from e

        return await self._get_or_create_singleton_async("position_management_service", _create)

    async def create_position_sync_service(self) -> 'PositionSyncService':
        """
        Create position synchronization service.

        Returns:
            Configured PositionSyncService singleton
        """
        async def _create():
            try:
                from ...domain.services.position_sync_service import PositionSyncService

                mexc_adapter = await self._parent.create_mexc_futures_adapter()
                questdb = await self._parent.create_questdb_provider()

                service = PositionSyncService(
                    exchange_adapter=mexc_adapter,
                    questdb_provider=questdb,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.position_sync_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.position_sync_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create position sync service: {str(e)}") from e

        return await self._get_or_create_singleton_async("position_sync_service", _create)

    async def create_trading_coordinator(self) -> 'TradingCoordinator':
        """
        Create TradingCoordinator - Mediator eliminating circular dependency.

        Returns:
            Configured TradingCoordinator singleton
        """
        async def _create():
            try:
                from ...trading.trading_coordinator import TradingCoordinator

                coordinator = TradingCoordinator(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    rate_limit_per_minute=60,
                    default_decision_timeout=5.0
                )

                await coordinator.start()

                self.logger.info("trading_module.trading_coordinator_created", {
                    "status": "started",
                    "pattern": "mediator"
                })
                return coordinator

            except Exception as e:
                self.logger.error("trading_module.trading_coordinator_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create trading coordinator: {str(e)}") from e

        return await self._get_or_create_singleton_async("trading_coordinator", _create)

    async def create_session_manager(self) -> 'SessionManager':
        """
        Create session manager with TradingCoordinator integration.

        Returns:
            Configured SessionManager singleton
        """
        async def _create():
            try:
                from ...trading.session_manager import SessionManager

                trading_coordinator = await self.create_trading_coordinator()

                manager = SessionManager(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    market_adapter=None,
                    trading_coordinator=trading_coordinator
                )

                await manager.register_with_coordinator()

                self.logger.info("trading_module.session_manager_created", {
                    "uses_coordinator": True
                })
                return manager

            except Exception as e:
                self.logger.error("trading_module.session_manager_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create session manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("session_manager", _create)

    async def create_session_service(self) -> 'SessionService':
        """
        Create unified session lookup service.

        Returns:
            Configured SessionService singleton
        """
        async def _create():
            try:
                from ...domain.services.session_service import SessionService

                questdb = await self._parent.create_questdb_provider()

                service = SessionService(
                    questdb_provider=questdb,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.session_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.session_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create session service: {str(e)}") from e

        return await self._get_or_create_singleton_async("session_service", _create)

    async def create_paper_trading_engine(self) -> 'PaperTradingEngine':
        """
        Create paper trading engine for simulated trading.

        Returns:
            Configured PaperTradingEngine singleton
        """
        async def _create():
            try:
                from ...trading.paper_trading_engine import PaperTradingEngine

                questdb = await self._parent.create_questdb_provider()
                risk_manager = await self.create_risk_manager()

                engine = PaperTradingEngine(
                    questdb_provider=questdb,
                    risk_manager=risk_manager,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.paper_trading_engine_created")
                return engine

            except Exception as e:
                self.logger.error("trading_module.paper_trading_engine_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create paper trading engine: {str(e)}") from e

        return await self._get_or_create_singleton_async("paper_trading_engine", _create)

    async def create_performance_tracker(self) -> 'PerformanceTracker':
        """
        Create performance tracker for P&L monitoring.

        Returns:
            Configured PerformanceTracker singleton
        """
        async def _create():
            try:
                from ...trading.performance_tracker import PerformanceTracker

                tracker = PerformanceTracker(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.performance_tracker_created")
                return tracker

            except Exception as e:
                self.logger.error("trading_module.performance_tracker_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create performance tracker: {str(e)}") from e

        return await self._get_or_create_singleton_async("performance_tracker", _create)

    async def create_wallet_service(self) -> 'WalletService':
        """
        Create wallet service for balance management.

        Returns:
            Configured WalletService singleton
        """
        async def _create():
            try:
                from ...application.services.wallet_service import WalletService

                mexc_adapter = await self._parent.create_mexc_futures_adapter()

                service = WalletService(
                    exchange_adapter=mexc_adapter,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.wallet_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.wallet_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create wallet service: {str(e)}") from e

        return await self._get_or_create_singleton_async("wallet_service", _create)

    async def create_trading_persistence_service(
        self,
        session_id: Optional[str] = None
    ) -> 'TradingPersistenceService':
        """
        Create trading persistence service.

        Args:
            session_id: Optional session ID for filtering

        Returns:
            Configured TradingPersistenceService
        """
        async def _create():
            try:
                from ...domain.services.paper_trading_persistence import TradingPersistenceService

                questdb = await self._parent.create_questdb_provider()

                service = TradingPersistenceService(
                    questdb_provider=questdb,
                    session_id=session_id,
                    logger=self.logger
                )

                self.logger.info("trading_module.trading_persistence_service_created", {
                    "session_id": session_id
                })
                return service

            except Exception as e:
                self.logger.error("trading_module.trading_persistence_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create trading persistence service: {str(e)}") from e

        # Not singleton if session_id provided
        if session_id:
            return await _create()
        return await self._get_or_create_singleton_async("trading_persistence_service", _create)

    async def create_paper_trading_persistence_service(self) -> 'PaperTradingPersistenceService':
        """
        Create paper trading persistence service.

        Returns:
            Configured PaperTradingPersistenceService singleton
        """
        async def _create():
            try:
                from ...domain.services.paper_trading_persistence import PaperTradingPersistenceService

                questdb = await self._parent.create_questdb_provider()

                service = PaperTradingPersistenceService(
                    questdb_provider=questdb,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("trading_module.paper_trading_persistence_service_created")
                return service

            except Exception as e:
                self.logger.error("trading_module.paper_trading_persistence_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create paper trading persistence service: {str(e)}") from e

        return await self._get_or_create_singleton_async("paper_trading_persistence_service", _create)
