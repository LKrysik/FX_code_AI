"""
Market Data Provider Factory
============================
Handles conditional logic for creating market data providers.
Isolates exchange selection logic from Container.

✅ REMOVED: FileConnector and FileMarketDataProvider (file-based backtest deprecated)
Use QuestDBHistoricalDataSource instead for backtesting.
"""

import asyncio
from typing import TYPE_CHECKING, Optional
from ...domain.interfaces.market_data import IMarketDataProvider
from ...infrastructure.config.settings import TradingMode
# ✅ REMOVED: FileConnector import (deprecated, file removed)
# ✅ REMOVED: FileMarketDataProvider import (deprecated)

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
    
    def create(self, override_mode: TradingMode = None, data_types: Optional[list] = None) -> IMarketDataProvider:
        """
        Create market data provider with underlying exchange connector.

        Args:
            override_mode: Override the default trading mode for this provider
            data_types: List of data types to subscribe to ('prices', 'orderbook'). Defaults to both.

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
            "mexc_enabled": self.settings.exchanges.mexc_enabled,
            "data_types": data_types
        })

        # Check if we're in backtest mode
        if effective_mode == TradingMode.BACKTEST:
            raise NotImplementedError(
                "File-based backtest is deprecated. FileConnector has been removed. "
                "Use QuestDBHistoricalDataSource instead for backtesting with historical data."
            )

        # For data collection or live trading, use real market data providers
        if effective_mode in (TradingMode.COLLECT, TradingMode.LIVE):
            if self.settings.exchanges.mexc_enabled:
                return self._create_mexc_provider(data_types=data_types)
            else:
                raise ValueError("MEXC exchange must be enabled for COLLECT/LIVE modes")

        raise ValueError(f"No supported exchange is enabled for mode {effective_mode} - MEXC exchange must be configured")

    # ✅ REMOVED: _create_backtest_provider() method (38 lines)
    # File-based backtest is deprecated - use QuestDBHistoricalDataSource instead

    def _create_mexc_provider(self, data_types: Optional[list] = None) -> IMarketDataProvider:
        """
        Create clean MEXC WebSocket adapter for live trading.

        Args:
            data_types: List of data types to subscribe to ('prices', 'orderbook'). Defaults to both.

        Returns:
            Configured MexcWebSocketAdapter implementing IMarketDataProvider
        """
        from ...infrastructure.exchanges.mexc_websocket_adapter import MexcWebSocketAdapter

        # Create clean MEXC adapter directly implementing the interface
        provider = MexcWebSocketAdapter(
            settings=self.settings.exchanges,
            event_bus=self.event_bus,
            logger=self.logger,
            data_types=data_types  # ✅ FIX: Pass data_types to adapter
        )

        self.logger.info("market_data_factory.mexc_adapter_created", {
            "exchange": "mexc",
            "implementation": "clean_websocket_adapter",
            "data_types": data_types or ['prices', 'orderbook']
        })

        return provider

