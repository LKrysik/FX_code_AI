"""
Market Data Provider Factory
============================
Handles conditional logic for creating market data providers.
Isolates exchange selection logic from Container.
"""

import asyncio
from typing import TYPE_CHECKING, Optional
from ...domain.interfaces.market_data import IMarketDataProvider
from ...infrastructure.config.settings import TradingMode
from ...exchanges.file_connector import FileConnector
from ...infrastructure.exchanges.file_market_data_provider import FileMarketDataProvider

if TYPE_CHECKING:
    from ...core.event_bus import EventBus
    from ...core.logger import StructuredLogger
    from ...infrastructure.config.settings import AppSettings


class MarketDataProviderFactory:
    """Factory for creating market data providers based on settings"""
    
    def __init__(self, settings: 'AppSettings', event_bus: 'EventBus', logger: 'StructuredLogger'):
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
        self._underlying_connector: Optional[object] = None
    
    def create(self, override_mode: TradingMode = None) -> IMarketDataProvider:
        """
        Create market data provider with underlying exchange connector.

        Args:
            override_mode: Override the default trading mode for this provider

        Returns:
            Configured market data provider

        Raises:
            ValueError: If no supported exchange is enabled
        """
        # Use override mode if provided, otherwise use settings mode
        effective_mode = override_mode or self.settings.trading.mode

        # Debug logging to see what mode we have
        self.logger.info("market_data_factory.mode_check", {
            "trading_mode": self.settings.trading.mode,
            "effective_mode": effective_mode,
            "override_mode": override_mode,
            "trading_mode_value": self.settings.trading.mode.value if self.settings.trading.mode else None,
            "effective_mode_value": effective_mode.value if effective_mode else None,
            "is_backtest": effective_mode == TradingMode.BACKTEST,
            "is_collect": effective_mode == TradingMode.COLLECT,
            "is_live": effective_mode == TradingMode.LIVE,
            "mexc_enabled": self.settings.exchanges.mexc_enabled
        })

        # Check if we're in backtest mode
        if effective_mode == TradingMode.BACKTEST:
            return self._create_backtest_provider()

        # For data collection or live trading, use real market data providers
        if effective_mode in (TradingMode.COLLECT, TradingMode.LIVE):
            if self.settings.exchanges.mexc_enabled:
                return self._create_mexc_provider()
            else:
                raise ValueError("MEXC exchange must be enabled for COLLECT/LIVE modes")

        raise ValueError(f"No supported exchange is enabled for mode {effective_mode} - MEXC exchange must be configured")
    
    def _create_backtest_provider(self) -> IMarketDataProvider:
        """
        Create file-based market data provider for backtest mode.
        Uses time_scale_factor from backtest settings for playback speed.
        
        Returns:
            Configured FileMarketDataProvider with backtest settings
        """
        backtest_config = {
            'enabled': True,
            'path': self.settings.backtest.data_directory,
            'playback_speed': float(self.settings.backtest.time_scale_factor),
            'loop': False,
            'start_from_beginning': True
        }
        
        # Create FileConnector with backtest settings
        file_connector = FileConnector(
            config=backtest_config,
            event_bus=self.event_bus,
            logger=self.logger
        )
        
        # Wrap in adapter that implements IMarketDataProvider
        provider = FileMarketDataProvider(
            file_connector=file_connector,
            event_bus=self.event_bus,
            logger=self.logger
        )
        
        self.logger.info("market_data_factory.backtest_provider_created", {
            "data_directory": self.settings.backtest.data_directory,
            "time_scale_factor": self.settings.backtest.time_scale_factor,
            "playback_speed": backtest_config['playback_speed']
        })
        
        return provider
    
    def _create_mexc_provider(self) -> IMarketDataProvider:
        """
        Create clean MEXC WebSocket adapter for live trading.
        
        Returns:
            Configured MexcWebSocketAdapter implementing IMarketDataProvider
        """
        from ...infrastructure.exchanges.mexc_websocket_adapter import MexcWebSocketAdapter
        
        # Create clean MEXC adapter directly implementing the interface
        provider = MexcWebSocketAdapter(
            settings=self.settings.exchanges,
            event_bus=self.event_bus,
            logger=self.logger
        )
        
        self.logger.info("market_data_factory.mexc_adapter_created", {
            "exchange": "mexc",
            "implementation": "clean_websocket_adapter"
        })
        
        return provider

