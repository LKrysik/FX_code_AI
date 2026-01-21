"""
Data Module - Market Data, Indicators, QuestDB Providers
=========================================================

Container module for data-related dependency injection.
Extracted from monolithic container.py for maintainability.

Responsibilities:
- Market data providers
- QuestDB connection and queries
- Indicator algorithms and engines
- Signal detection and processing
- Data collection controllers
"""

from typing import Optional, List, TYPE_CHECKING
from .base import ContainerModule

if TYPE_CHECKING:
    from ..container import Container


class DataModule(ContainerModule):
    """
    Data domain container module.

    Factory methods for all data-related services.
    """

    async def create_questdb_provider(self) -> 'QuestDBProvider':
        """
        Create QuestDB provider singleton.

        Returns:
            Configured QuestDBProvider singleton
        """
        async def _create():
            try:
                from ...data_feed.questdb_provider import QuestDBProvider

                provider = QuestDBProvider(
                    host=getattr(self.settings, 'questdb_host', 'localhost'),
                    port=getattr(self.settings, 'questdb_port', 8812),
                    logger=self.logger
                )

                # Health check
                if await provider.health_check():
                    self.logger.info("data_module.questdb_provider_created", {
                        "status": "connected"
                    })
                else:
                    self.logger.warning("data_module.questdb_provider_unhealthy")

                return provider

            except Exception as e:
                self.logger.error("data_module.questdb_provider_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create QuestDB provider: {str(e)}") from e

        return await self._get_or_create_singleton_async("questdb_provider", _create)

    async def create_market_data_provider(self, override_mode=None) -> 'IMarketDataProvider':
        """
        Create market data provider based on trading mode.

        Args:
            override_mode: Override trading mode if specified

        Returns:
            Configured market data provider
        """
        async def _create():
            try:
                from ...domain.interfaces.market_data import IMarketDataProvider

                mode = override_mode or getattr(self.settings, 'trading_mode', 'paper')

                if mode == 'live':
                    # Use live market adapter
                    provider = await self.create_live_market_adapter()
                else:
                    # Use QuestDB for historical/paper
                    provider = await self.create_questdb_provider()

                self.logger.info("data_module.market_data_provider_created", {
                    "mode": mode
                })
                return provider

            except Exception as e:
                self.logger.error("data_module.market_data_provider_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create market data provider: {str(e)}") from e

        return await self._get_or_create_singleton_async("market_data_provider", _create)

    async def create_live_market_adapter(self) -> 'LiveMarketAdapter':
        """
        Create live market adapter with TradingCoordinator integration.

        Returns:
            Configured LiveMarketAdapter singleton
        """
        async def _create():
            try:
                from ...data.live_market_adapter import LiveMarketAdapter

                trading_coordinator = await self._parent.trading.create_trading_coordinator()

                adapter = LiveMarketAdapter(
                    settings=self.settings.exchanges,
                    event_bus=self.event_bus,
                    logger=self.logger,
                    trading_coordinator=trading_coordinator,
                    session_manager=None
                )

                self.logger.info("data_module.live_market_adapter_created", {
                    "uses_coordinator": True
                })
                return adapter

            except Exception as e:
                self.logger.error("data_module.live_market_adapter_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create live market adapter: {str(e)}") from e

        return await self._get_or_create_singleton_async("live_market_adapter", _create)

    async def create_pump_detection_service(self) -> 'PumpDetectionService':
        """
        Create pump detection service.

        Returns:
            Configured PumpDetectionService singleton
        """
        async def _create():
            try:
                from ...domain.services.pump_detector import PumpDetectionService

                indicator_engine = await self.create_streaming_indicator_engine()

                service = PumpDetectionService(
                    indicator_engine=indicator_engine,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("data_module.pump_detection_service_created")
                return service

            except Exception as e:
                self.logger.error("data_module.pump_detection_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create pump detection service: {str(e)}") from e

        return await self._get_or_create_singleton_async("pump_detection_service", _create)

    async def create_signal_adapter(self) -> 'SignalAdapter':
        """
        Create signal adapter for signal processing.

        Returns:
            Configured SignalAdapter singleton
        """
        async def _create():
            try:
                from ...trading.signal_adapter import SignalAdapter

                adapter = SignalAdapter(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("data_module.signal_adapter_created")
                return adapter

            except Exception as e:
                self.logger.error("data_module.signal_adapter_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create signal adapter: {str(e)}") from e

        return await self._get_or_create_singleton_async("signal_adapter", _create)

    async def create_indicator_algorithm_registry(self) -> 'IndicatorAlgorithmRegistry':
        """
        Create indicator algorithm registry.

        Returns:
            Configured IndicatorAlgorithmRegistry singleton
        """
        async def _create():
            try:
                from ...domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry

                registry = IndicatorAlgorithmRegistry(logger=self.logger)

                # Register built-in algorithms
                await registry.register_builtin_algorithms()

                self.logger.info("data_module.indicator_algorithm_registry_created", {
                    "registered_count": len(registry.list_algorithms())
                })
                return registry

            except Exception as e:
                self.logger.error("data_module.indicator_algorithm_registry_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create indicator algorithm registry: {str(e)}") from e

        return await self._get_or_create_singleton_async("indicator_algorithm_registry", _create)

    async def create_offline_indicator_engine(self) -> 'OfflineIndicatorEngine':
        """
        Create offline indicator engine with SHARED algorithm registry.

        This ensures OfflineIndicatorEngine uses the same algorithm registry
        as StreamingIndicatorEngine for consistent calculations.

        Returns:
            Configured OfflineIndicatorEngine singleton
        """
        async def _create():
            try:
                from ...domain.services.offline_indicator_engine import OfflineIndicatorEngine
                from ...data.questdb_data_provider import QuestDBDataProvider

                questdb = await self.create_questdb_provider()
                questdb_data_provider = QuestDBDataProvider(questdb, self.logger)
                algorithm_registry = await self.create_indicator_algorithm_registry()

                engine = OfflineIndicatorEngine(
                    questdb_data_provider=questdb_data_provider,
                    algorithm_registry=algorithm_registry  # SHARED registry
                )

                self.logger.info("data_module.offline_indicator_engine_created", {
                    "algorithm_registry_shared": True,
                    "algorithms_count": len(algorithm_registry.list_algorithms())
                })
                return engine

            except Exception as e:
                self.logger.error("data_module.offline_indicator_engine_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create offline indicator engine: {str(e)}") from e

        return await self._get_or_create_singleton_async("offline_indicator_engine", _create)

    async def create_indicator_variant_repository(self) -> 'IndicatorVariantRepository':
        """
        Create indicator variant repository with SHARED algorithm registry.

        The repository stores the algorithm registry so that StreamingIndicatorEngine
        can access algorithms via variant_repository.algorithms (single source of truth).

        Returns:
            Configured IndicatorVariantRepository singleton
        """
        async def _create():
            try:
                from ...domain.repositories.indicator_variant_repository import IndicatorVariantRepository

                questdb = await self.create_questdb_provider()
                algorithm_registry = await self.create_indicator_algorithm_registry()

                repository = IndicatorVariantRepository(
                    questdb_provider=questdb,
                    algorithm_registry=algorithm_registry,
                    logger=self.logger
                )

                self.logger.info("data_module.indicator_variant_repository_created", {
                    "algorithm_registry_shared": True,
                    "algorithms_count": len(algorithm_registry.get_all_algorithms())
                })
                return repository

            except Exception as e:
                self.logger.error("data_module.indicator_variant_repository_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create indicator variant repository: {str(e)}") from e

        return await self._get_or_create_singleton_async("indicator_variant_repository", _create)

    async def create_streaming_indicator_engine(self) -> 'StreamingIndicatorEngine':
        """
        Create streaming indicator engine for real-time calculations.

        ARCHITECTURE: Engine gets algorithm_registry from variant_repository.algorithms
        (single source of truth pattern). Do NOT pass algorithm_registry directly.

        Returns:
            Configured StreamingIndicatorEngine singleton
        """
        async def _create():
            try:
                from ...domain.services.streaming_indicator_engine import StreamingIndicatorEngine

                # variant_repository contains algorithm_registry as .algorithms attribute
                # Engine will access it via variant_repository.algorithms (single source of truth)
                variant_repository = await self.create_indicator_variant_repository()

                engine = StreamingIndicatorEngine(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    variant_repository=variant_repository
                )

                self.logger.info("data_module.streaming_indicator_engine_created", {
                    "algorithms_source": "variant_repository.algorithms",
                    "algorithms_count": len(variant_repository.algorithms.get_all_algorithms())
                })
                return engine

            except Exception as e:
                self.logger.error("data_module.streaming_indicator_engine_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create streaming indicator engine: {str(e)}") from e

        return await self._get_or_create_singleton_async("streaming_indicator_engine", _create)

    async def create_indicator_persistence_service(self) -> 'IndicatorPersistenceService':
        """
        Create indicator persistence service.

        Returns:
            Configured IndicatorPersistenceService singleton
        """
        async def _create():
            try:
                from ...domain.services.indicator_persistence_service import IndicatorPersistenceService

                questdb = await self.create_questdb_provider()

                service = IndicatorPersistenceService(
                    questdb_provider=questdb,
                    logger=self.logger
                )

                self.logger.info("data_module.indicator_persistence_service_created")
                return service

            except Exception as e:
                self.logger.error("data_module.indicator_persistence_service_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create indicator persistence service: {str(e)}") from e

        return await self._get_or_create_singleton_async("indicator_persistence_service", _create)

    async def create_symbol_config_manager(self) -> 'SymbolConfigurationManager':
        """
        Create symbol configuration manager.

        Returns:
            Configured SymbolConfigurationManager singleton
        """
        async def _create():
            try:
                from ...infrastructure.config.symbol_config import SymbolConfigurationManager

                manager = SymbolConfigurationManager(
                    settings=self.settings,
                    logger=self.logger
                )

                self.logger.info("data_module.symbol_config_manager_created")
                return manager

            except Exception as e:
                self.logger.error("data_module.symbol_config_manager_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create symbol config manager: {str(e)}") from e

        return await self._get_or_create_singleton_async("symbol_config_manager", _create)

    async def create_data_collection_controller(self) -> 'DataCollectionController':
        """
        Create data collection controller.

        Returns:
            Configured DataCollectionController singleton
        """
        async def _create():
            try:
                from ...data.data_collection_persistence_service import DataCollectionController

                questdb = await self.create_questdb_provider()

                controller = DataCollectionController(
                    questdb_provider=questdb,
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("data_module.data_collection_controller_created")
                return controller

            except Exception as e:
                self.logger.error("data_module.data_collection_controller_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create data collection controller: {str(e)}") from e

        return await self._get_or_create_singleton_async("data_collection_controller", _create)
